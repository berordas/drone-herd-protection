"""
world.py — Núcleo de la simulación.

El World es la ÚNICA fuente de verdad del estado y de la dinámica. NO depende de
matplotlib, PettingZoo ni ROS: esos serán adaptadores finos por encima. Aquí solo
hay NumPy.

Convenciones de diseño:
  - Unidades SI: posiciones en metros, tiempo en segundos.
  - El suelo es un plano 2D (x, y). Es una sim 2.5D porque los drones "vuelan",
    pero la altura aún NO es estado (no influye en ninguna dinámica de esta versión).
  - Cada grupo de entidades es un array de NumPy (N, 2) -> vectorizable y trivial
    de trocear por agente cuando llegue el MARL.
  - Toda la aleatoriedad pasa por self.rng -> episodios reproducibles con seed.

ESTADO: vacas con cohesión + miedo (apiñamiento, rezagado emergente) contenidas por
valla blanda; lobos con caza de Muro et al. (2011); drones quietos. Pendiente:
escolta/conducción al refugio, batería/carga, observación real y MARL.
"""

from __future__ import annotations
import numpy as np

# Estados de batería de cada dron (máquina de estados del MUNDO, distinta del futuro
# coordinador FSM). RETURNING existe para el vuelo de vuelta real cuando haya movimiento;
# por ahora es instantáneo (se colapsa dentro del relevo).
ACTIVE, RETURNING, CHARGING, READY = 0, 1, 2, 3
DRONE_STATE_NAMES = {ACTIVE: "ACTIVE", RETURNING: "RETURNING", CHARGING: "CHARGING", READY: "READY"}


class World:
    def __init__(
        self,
        n_active_drones: int = 4,
        n_reserve_drones: int = 4,
        n_cows: int = 6,
        wolves_min: int = 1,            # nº de lobos sorteado en reset() ...
        wolves_max: int = 5,            # ... entre [wolves_min, wolves_max]
        parcel_size: tuple[float, float] = (100.0, 100.0),
        safe_radius: float | None = None,     # establo (centro del campo)
        station_radius: float | None = None,  # estación central de carga
        station_gap: float | None = None,     # separación establo<->estación
        station_dir: tuple[float, float] = (0.0, 1.0),  # dirección estación respecto al establo
        cow_spawn: tuple[float, float] | None = None,   # punto de aparición del rebaño (esquina)
        cow_spread: float | None = None,      # radio del cluster de vacas (límite provisional)
        dt: float = 0.1,
        max_steps: int = 600,
        drone_speed: float = 6.0,     # m/s, escala/tope de las acciones de los drones
        # --- Comportamiento de las vacas: pastar DISPERSO + miedo de rebaño por distancia ---
        cow_speed: float = 1.2,            # m/s base, < wolf_speed (no escapan a la carrera). TUNE
        cow_speed_jitter: float = 0.4,     # heterogeneidad ±frac por vaca -> emerge el rezagado. TUNE
        cow_spawn_min_sep: float | None = None,  # m, separación mínima al nacer (default ~0.25*cow_spread)
        k_cohesion_calm: float = 0.0,      # SIN tirón al centroide en calma (no se juntan solas). TUNE
        k_cohesion_panic: float = 1.2,     # cohesión en miedo (apiñamiento). TUNE
        k_separation: float = 3.0,         # peso de separación (SIEMPRE activa). TUNE
        r_separation: float | None = None, # m, radio de separación (default ~0.4*cow_spread). TUNE
        wander_calm: float = 1.0,          # paseo aleatorio en calma. TUNE
        wander_panic: float = 0.35,        # paseo residual en pánico (rebaño móvil -> rezagado). TUNE
        r_alarm: float | None = None,      # m: lobo a < r_alarm de una vaca ALARMA al rebaño (default 0.12*min). TUNE
        r_calm: float | None = None,       # m: el rebaño se calma solo si el lobo > r_calm (histéresis). TUNE
        r_fear: float | None = None,       # DEPRECATED: sustituido por r_alarm/r_calm (se mantiene por baseline.py v1)
        k_fence: float = 1.5,              # rigidez de la valla blanda (la "correa"). TUNE
        # --- Instrumentación (verificación de procedencia de capturas) ---
        iso_sustain_steps: int = 10,       # K: pasos de aislamiento sostenido para "captura limpia"
        teleport_guard: bool = False,      # log si una entidad se desplaza > su máx por paso * motion_tol
        motion_tol: float = 1.5,           # tolerancia de desplazamiento por paso (salto/sobrepaso/guardia)
        capture_radius: float | None = None,  # m, a qué distancia MATA (default derivado de geometría)
        # --- Modelo de caza de Muro et al. (2011) ---
        wolf_speed: float = 4.0,                       # m/s del lobo (lejos de la presa)
        wolf_speed_near: float | None = None,          # m/s cerca de la presa (None -> = wolf_speed)
        d_safe: float | None = None,                   # distancia de seguridad lobo-presa
        wolf_repulsion_radius: float | None = None,    # alcance de la repulsión entre lobos
        wolf_repulsion_strength: float = 1.0,          # peso del término de repulsión
        wolf_engage_band: float | None = None,         # margen sobre d_safe para contar como "en el anillo"
        pounce_factor: float = 1.2,                    # umbral de remate = pounce_factor * r_separation (>1). TUNE
        wolf_pounce_isolation: float | None = None,    # m: si None, = pounce_factor * r_separation. TUNE
        # --- Batería y cola de carga (operación continua; ver battery_check.py) ---
        battery_capacity: float = 600.0,   # s de vuelo a plena carga (batería ~10 min)
        charge_full: float = 300.0,        # s para cargar de 0 a full (~5 min) -> ratio vuelo:carga 2:1
        announce_threshold: float = 0.20,  # fracción de batería a la que se pide relevo. TUNE
        charge_capacity: int | None = None,  # puestos de carga en paralelo (default = nº de reserva)
        seed: int | None = None,
    ):
        # --- configuración (inmutable durante el episodio) ---
        self.n_active = n_active_drones
        self.n_reserve = n_reserve_drones
        self.n_drones = n_active_drones + n_reserve_drones
        self.n_cows = n_cows
        self.wolves_min = wolves_min
        self.wolves_max = wolves_max
        self.W, self.H = parcel_size
        m = min(self.W, self.H)  # escala de referencia para los defaults (sin números mágicos)

        # Geometría central: establo en el centro del campo; estación pegada a su
        # borde pero SIN solaparse (son cosas distintas).
        self.safe_radius = safe_radius if safe_radius is not None else 0.12 * m
        self.station_radius = station_radius if station_radius is not None else 0.05 * m
        self.station_gap = station_gap if station_gap is not None else 0.01 * m
        safe_center = np.array([self.W / 2.0, self.H / 2.0])
        self.safe_zone = np.array([safe_center[0], safe_center[1], self.safe_radius])

        d = np.asarray(station_dir, dtype=float)
        d = d / max(np.linalg.norm(d), 1e-9)
        station_center = safe_center + d * (self.safe_radius + self.station_radius + self.station_gap)
        self.central_station = np.array([station_center[0], station_center[1], self.station_radius])

        # Rebaño: aparece agrupado lejos del centro (por defecto, hacia una esquina).
        self.cow_spawn = np.asarray(
            cow_spawn if cow_spawn is not None else (0.25 * self.W, 0.75 * self.H),
            dtype=float,
        )
        self.cow_spread = cow_spread if cow_spread is not None else 0.15 * m  # área de pasto (mayor: dispersa)

        self.dt = dt
        self.max_steps = max_steps
        self.drone_speed = drone_speed

        # Comportamiento de las vacas (la valla blanda usa la zona de pasto: cow_spawn/cow_spread).
        self.cow_speed = cow_speed
        self.cow_speed_jitter = cow_speed_jitter
        self.cow_spawn_min_sep = (
            cow_spawn_min_sep if cow_spawn_min_sep is not None else 0.25 * self.cow_spread
        )
        self.k_cohesion_calm = k_cohesion_calm
        self.k_cohesion_panic = k_cohesion_panic
        self.k_separation = k_separation
        self.r_separation = r_separation if r_separation is not None else 0.4 * self.cow_spread
        self.wander_calm = wander_calm
        self.wander_panic = wander_panic
        self.r_alarm = r_alarm if r_alarm is not None else 0.12 * m
        self.r_calm = r_calm if r_calm is not None else 0.20 * m
        self.r_fear = r_fear  # DEPRECATED: no se usa (superseded por r_alarm/r_calm)
        self.k_fence = k_fence
        self.iso_sustain_steps = iso_sustain_steps
        self.teleport_guard = teleport_guard
        self.motion_tol = motion_tol

        # capture_radius (a qué distancia MATA) y d_safe (a qué distancia se ATREVE a
        # quedarse) son INDEPENDIENTES: cada uno derivado de la geometría del campo,
        # no uno del otro. d_safe > capture_radius para que el cerco no mate de pasada.
        self.capture_radius = capture_radius if capture_radius is not None else 0.03 * m
        self.d_safe = d_safe if d_safe is not None else 0.06 * m

        # Muro et al. (2011): radio/banda del anillo derivados de d_safe (la regla 2 no cambia).
        self.wolf_speed = wolf_speed
        self.wolf_speed_near = wolf_speed_near if wolf_speed_near is not None else wolf_speed
        self.wolf_repulsion_radius = (
            wolf_repulsion_radius if wolf_repulsion_radius is not None else 2.0 * self.d_safe
        )
        self.wolf_repulsion_strength = wolf_repulsion_strength
        self.wolf_engage_band = wolf_engage_band if wolf_engage_band is not None else 0.5 * self.d_safe
        # Remate ("pounce"): la presa cuenta como CORTADA si su vaca más próxima está a más de
        # esto. Anclado a r_separation (NO a cow_spread): "aislada" = más separada de lo normal al
        # pastar. (Con cow_spread = radio de PASTO, 0.25*cow_spread caía por debajo del pasto y el
        # lobo entraba en remate permanente -> 99%.) El umbral sigue estático (una vez, aquí).
        self.pounce_factor = pounce_factor
        if wolf_pounce_isolation is not None:
            self.wolf_pounce_isolation = wolf_pounce_isolation   # override explícito (p.ej. baseline v1)
        else:
            self.wolf_pounce_isolation = self.pounce_factor * self.r_separation
            # Asersión de seguridad: una vaca PASTANDO no puede contar como aislada (pounce_factor > 1).
            assert self.wolf_pounce_isolation > self.r_separation, (
                "wolf_pounce_isolation (%.2f) debe ser > r_separation (%.2f): el umbral debe superar "
                "el pasto (pounce_factor > 1)." % (self.wolf_pounce_isolation, self.r_separation)
            )

        # Batería: tasas DERIVADAS de las capacidades (sin números mágicos). La batería es
        # una fracción [0,1]; drena 1->0 en battery_capacity s, carga 0->1 en charge_full s.
        self.battery_capacity = battery_capacity
        self.charge_full = charge_full
        self.drain_rate_active = 1.0 / battery_capacity   # fracción por segundo (patrulla)
        self.charge_rate = 1.0 / charge_full              # fracción por segundo
        self.announce_threshold = announce_threshold
        self.charge_capacity = (
            charge_capacity if charge_capacity is not None else self.n_drones - self.n_active
        )
        self.relay_travel_time = 0.0   # HOOK: tiempo de vuelo del relevo (0 = instantáneo por ahora)

        self._seed = seed

        # --- estado mutable (se inicializa en reset) ---
        self.rng: np.random.Generator | None = None
        self.cows: np.ndarray | None = None
        self.cow_speeds: np.ndarray | None = None   # velocidad por vaca (heterogénea, por episodio)
        self.wolves: np.ndarray | None = None
        self.drones: np.ndarray | None = None
        self.battery: np.ndarray | None = None          # (n_drones,) fracción [0,1]
        self.drone_state: np.ndarray | None = None      # (n_drones,) ACTIVE/RETURNING/CHARGING/READY
        self.battery_activity: np.ndarray | None = None # (n_drones,) HOOK persecución (bandera #7): multiplica el drenaje
        self.drone_stranded: np.ndarray | None = None   # (n_drones,) HOOK "dron tirado" (sin travel-time no se activa)
        self.herd_alarmed: bool = False                 # alarma de rebaño (miedo) con histéresis
        self._iso_streak: np.ndarray | None = None      # (n_cows,) pasos seguidos de aislamiento >= umbral pounce
        self._cow_isolation: np.ndarray | None = None   # (n_cows,) dist a la vaca más cercana (instrumentación)
        self._wolf_pounce: bool = False                 # ¿el lobo iba en remate este paso? (instrumentación)
        self._prev_cows: np.ndarray | None = None       # posiciones previas (saltos/guardia)
        self._prev_wolves: np.ndarray | None = None
        self.capture_info: dict | None = None           # procedencia de la última captura
        self.guard_violations: list = []                # log de la guardia de teletransporte
        self.n_wolves: int = 0          # se sortea en cada reset
        self.step_count: int = 0
        self.status: str = "running"    # running | success | predation | timeout
        self.reset()

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def reset(self, seed: int | None = None) -> dict:
        if seed is not None:
            self._seed = seed
        self.rng = np.random.default_rng(self._seed)

        # Vacas: REPARTIDAS por el área de pasto (dispersas, no apiñadas), con separación
        # mínima al nacer y fuera de establo/central. Determinista con la seed.
        self.cows = self._spawn_cows()

        # Heterogeneidad leve: cada vaca con una velocidad algo distinta (una vez por
        # episodio). La más lenta se rezaga al apiñarse -> queda expuesta = presa del lobo.
        self.cow_speeds = self.cow_speed * self.rng.uniform(
            1.0 - self.cow_speed_jitter, 1.0 + self.cow_speed_jitter, size=self.n_cows
        )

        # Drones activos: en las esquinas del bounding box INICIAL del rebaño.
        # (Solo posición de partida; cuando haya coordinación, las decidirá el coordinador.)
        xmin, ymin, xmax, ymax = self.cows_bbox(self.cows)
        corners = np.array([[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]])
        active = corners[np.arange(self.n_active) % 4]

        # Drones de reserva: en fila recta dentro de la central, como cola de espera
        # (preparado para la futura lógica de cola de carga; sin comportamiento aún).
        scx, scy, sr = self.central_station
        half = 0.7 * sr  # margen para no salirse de la región central
        reserve = np.column_stack([np.linspace(scx - half, scx + half, self.n_reserve),
                                   np.full(self.n_reserve, scy)])
        self.drones = np.vstack([active, reserve])  # filas [0:n_active] activos, resto reserva

        # Lobos: nº aleatorio por episodio; cada uno aparece en el perímetro del campo.
        self.n_wolves = int(self.rng.integers(self.wolves_min, self.wolves_max + 1))
        self.wolves = self._random_perimeter_points(self.n_wolves)

        # Batería a plena carga al reset (NO se aleatoriza en episodio: solo importa cuando los
        # drones actúan). HOOK: stagger=True (battery_check) reparte fases para operación continua.
        self._init_battery(stagger=False)

        # Estado de miedo (alarma de rebaño con histéresis) e instrumentación.
        self.herd_alarmed = False
        self._iso_streak = np.zeros(self.n_cows, dtype=int)
        self._cow_isolation = np.full(self.n_cows, np.inf)
        self._wolf_pounce = False
        self._prev_cows = self.cows.copy()
        self._prev_wolves = self.wolves.copy()
        self.capture_info = None
        self.guard_violations = []

        self.step_count = 0
        self.status = "running"
        return self.get_observation()

    # ------------------------------------------------------------------ #
    # Observación (cruda y global; se troceará por agente con el MARL)
    # ------------------------------------------------------------------ #
    def get_observation(self) -> dict:
        return {
            "drones": self.drones.copy(),
            "cows": self.cows.copy(),
            "wolves": self.wolves.copy(),
            "step": self.step_count,
        }

    # ------------------------------------------------------------------ #
    # Step: una transición de la dinámica (firma estilo gym/PettingZoo)
    # ------------------------------------------------------------------ #
    def step(self, actions):
        """
        Avanza dt. `actions`: array (n_drones, 2) = velocidad deseada en m/s
        (se recorta a drone_speed). Devuelve la 5-tupla estilo gym:
            (obs, reward, terminated, truncated, info)
        """
        self._prev_cows = self.cows.copy()   # para la instrumentación (saltos/teletransporte)
        self._prev_wolves = self.wolves.copy()
        self._apply_drone_actions(actions)  # fase 1: control
        self._update_cows()                 # fase 2: dinámica del entorno
        self._update_wolves()
        self._step_battery()                # fase 3: batería/relevos (independiente de vacas/lobo)
        self.step_count += 1
        self._update_instrumentation()      # aislamiento sostenido + guardia de teletransporte

        terminated, truncated = self._check_terminal()
        reward = self._compute_reward(terminated, truncated)
        info = {"status": self.status}
        return self.get_observation(), reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    # Dinámicas (deliberadamente tontas en esta versión)
    # ------------------------------------------------------------------ #
    def _apply_drone_actions(self, actions) -> None:
        if actions is None:
            return
        vel = np.asarray(actions, dtype=float).reshape(self.n_drones, 2)
        speed = np.linalg.norm(vel, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.drone_speed / np.maximum(speed, 1e-9))
        self.drones = self.drones + vel * scale * self.dt
        self._clip_to_parcel(self.drones)

    # ------------------------------------------------------------------ #
    # Batería y cola de carga (mecánica del MUNDO, automática por umbral)
    # ------------------------------------------------------------------ #
    def _init_battery(self, stagger: bool = False) -> None:
        """Inicializa batería/estado de los drones. Los primeros n_active son los puestos
        activos; el resto, en la central. stagger=True reparte fases con el RNG (operación
        continua); stagger=False = todos a plena carga (reset de episodio)."""
        n, na = self.n_drones, self.n_active
        self.battery = np.ones(n)
        self.drone_state = np.full(n, READY, dtype=int)
        self.drone_state[:na] = ACTIVE
        self.battery_activity = np.ones(n)        # HOOK persecución (1.0 = patrulla)
        self.drone_stranded = np.zeros(n, dtype=bool)  # HOOK "dron tirado" (no se activa sin travel-time)
        if not stagger:
            return

        # Arranque escalonado (RNG sembrado) -> depleciones/relevos repartidos, no simultáneos.
        a = self.announce_threshold
        # Activos: baterías equiespaciadas en (a, 1], en orden RNG -> se vacían a tiempos distintos.
        self.battery[:na] = a + (1.0 - a) * (self.rng.permutation(na) + 1) / na
        # Central: mitad listos a tope, mitad cargando a niveles repartidos (quién es quién, RNG).
        central = np.arange(na, n)
        self.rng.shuffle(central)
        n_ready = central.size // 2
        self.drone_state[central[:n_ready]] = READY
        self.battery[central[:n_ready]] = 1.0
        self.drone_state[central[n_ready:]] = CHARGING
        self.battery[central[n_ready:]] = self.rng.uniform(a, 1.0, size=central.size - n_ready)

    def _step_battery(self) -> None:
        """Avanza la batería y resuelve los relevos. Independiente de vacas/lobo: solo toca
        batería/estado/posición de drones (drivable en aislado para battery_check.py).
        NO usa el RNG (determinista) -> no perturba el stream de vacas/lobo (baseline intacto)."""
        st, bat = self.drone_state, self.battery

        # 1) Drenaje de activos. HOOK persecución (bandera #7): battery_activity multiplica.
        active = st == ACTIVE
        bat[active] -= self.drain_rate_active * self.battery_activity[active] * self.dt

        # 2) Carga en paralelo hasta charge_capacity (si sobran, cargan los más vacíos).
        charging = np.where(st == CHARGING)[0]
        if charging.size:
            slots = (charging if charging.size <= self.charge_capacity
                     else charging[np.argsort(bat[charging])][:self.charge_capacity])
            bat[slots] += self.charge_rate * self.dt
        np.clip(bat, 0.0, 1.0, out=bat)

        # 3) Cargado a tope -> READY (ni drena ni carga, espera puesto libre).
        st[(st == CHARGING) & (bat >= 1.0 - 1e-9)] = READY

        # 4) Activo bajo umbral -> relevo automático (regla del mundo; SEAM: exponer como
        #    acción "pedir relevo" del coordinador más adelante).
        for i in np.where(active & (bat <= self.announce_threshold))[0]:
            central = np.where((st == CHARGING) | (st == READY))[0]
            if central.size == 0:
                break  # invariante: n_drones > n_active -> siempre hay drones en central
            j = central[np.argmax(bat[central])]   # el MÁS cargado (no espera al 100%)
            # Relevo INSTANTÁNEO = swap de rol + puesto (posición). HOOK travel-time
            # (relay_travel_time): con movimiento, el saliente iría por RETURNING dejando el
            # puesto descubierto (hueco de cobertura) y el entrante tardaría en llegar.
            self.drones[[i, j]] = self.drones[[j, i]]
            st[i] = CHARGING   # saliente -> central (carga desde ~announce_threshold)
            st[j] = ACTIVE     # entrante cubre el puesto liberado

    def _update_cows(self) -> None:
        """Comportamiento del rebaño (desplazamiento directo, sin velocidad en estado).

        Calma: pastan DISPERSAS = paseo + separación + valla blanda. SIN tirón al centroide
        (k_cohesion_calm=0): no se juntan solas, solo reaccionando.
        Miedo: ALARMA DE REBAÑO por distancia con histéresis (contagio del susto: reacciona
        el grupo entero). Con la alarma activa se enciende la cohesión de pánico y se mantiene
        el paseo de pánico; la vaca más lenta se descuelga y queda expuesta. SIN huida del lobo.
        """
        cows = self.cows

        # --- Alarma de rebaño por distancia, con histéresis (enclavamiento) ---
        if self.n_wolves > 0:
            nearest_wolf = float(np.linalg.norm(
                self.wolves[None, :, :] - cows[:, None, :], axis=2).min())
        else:
            nearest_wolf = np.inf
        if not self.herd_alarmed and nearest_wolf < self.r_alarm:
            self.herd_alarmed = True            # se enciende el miedo para TODO el rebaño
        elif self.herd_alarmed and nearest_wolf > self.r_calm:
            self.herd_alarmed = False           # solo se calma si el lobo se aleja > r_calm

        # Ganancias según la alarma (binario; añadir rampa solo si el salto se ve mal en render).
        if self.herd_alarmed:
            k_coh, wander_mag = self.k_cohesion_panic, self.wander_panic
        else:
            k_coh, wander_mag = self.k_cohesion_calm, self.wander_calm   # k_cohesion_calm = 0

        # Cohesión hacia el centroide (nula en calma; pánico cuando hay alarma).
        cohesion = k_coh * (cows.mean(axis=0) - cows)

        # Separación: SIEMPRE activa (empuje desde vecinas dentro de r_separation).
        delta = cows[:, None, :] - cows[None, :, :]                    # (n,n,2): i - j
        dd = np.linalg.norm(delta, axis=2)                            # (n,n)
        close = (dd < self.r_separation) & (dd > 1e-9)
        push = np.where(
            close[:, :, None],
            delta / np.maximum(dd[:, :, None], 1e-9) * (1.0 - dd[:, :, None] / self.r_separation),
            0.0,
        )
        separation = self.k_separation * push.sum(axis=1)             # (n,2)

        # Paseo aleatorio (magnitud calma o pánico).
        wander = self.rng.normal(0.0, 1.0, size=cows.shape) * wander_mag

        # Valla blanda ("correa"): retorno hacia la zona de pasto SOLO si salen de ella.
        off = cows - self.cow_spawn
        dist_f = np.linalg.norm(off, axis=1, keepdims=True)
        excess = np.maximum(dist_f - self.cow_spread, 0.0)
        fence = -self.k_fence * off / np.maximum(dist_f, 1e-9) * excess

        # Combinación -> dirección, normalizada a la velocidad (heterogénea) de cada vaca.
        total = cohesion + separation + wander + fence
        norm = np.linalg.norm(total, axis=1, keepdims=True)
        move = np.where(norm > 1e-9, total / np.maximum(norm, 1e-9) * self.cow_speeds[:, None] * self.dt, 0.0)
        self.cows = cows + move

        # Contención DURA solo en límites reales (parcela + zonas prohibidas), reutilizando
        # el clamp existente. La zona de pasto la contiene la valla BLANDA, no un clamp.
        self._clip_to_parcel(self.cows)
        self._push_outside_circle(self.cows, self.safe_zone)
        self._push_outside_circle(self.cows, self.central_station)

    def _update_wolves(self) -> None:
        """Modelo de caza de Muro et al. (2011) + remate ("pounce") biológico.

        Reglas descentralizadas por lobo (sin comunicación ni jerarquía):
          1. Mantener d_safe respecto al rebaño (versión simétrica: se acerca si lejos,
             retrocede si una vaca entra) -> cerca desde fuera sin atravesar.
          2. Repulsión entre lobos en el anillo -> reparto angular (cerco emergente).
        Remate: si la PRESA está realmente cortada del rebaño (su vaca más próxima a más
        de wolf_pounce_isolation), la jauría abandona el standoff y CIERRA A MATAR
        (persecución pura). Solo se dispara con una vaca de verdad aislada -> captura a
        tasa sensata, no por atravesar el grupo. NO hay busca-huecos ni evasión de drones.
        """
        if self.n_wolves == 0:
            return

        # --- Capa biológica: selección de presa (la vaca más expuesta) ---
        centroid = self.cows.mean(axis=0)
        exposure = np.linalg.norm(self.cows - centroid, axis=1)
        prey_idx = int(np.argmax(exposure))
        prey = self.cows[prey_idx]                                  # (2,)

        to_prey = prey - self.wolves                                # (n_wolves, 2)
        dist_prey = np.linalg.norm(to_prey, axis=1, keepdims=True)  # (n_wolves, 1)
        dir_prey = to_prey / np.maximum(dist_prey, 1e-9)

        # ¿Presa cortada del rebaño? Distancia de la presa a su vaca más próxima del resto.
        if self.n_cows > 1:
            d_prey_cows = np.linalg.norm(self.cows - prey, axis=1)
            d_prey_cows[prey_idx] = np.inf
            prey_isolation = float(d_prey_cows.min())
        else:
            prey_isolation = np.inf
        pounce = prey_isolation > self.wolf_pounce_isolation
        self._wolf_pounce = bool(pounce)   # instrumentación: ¿remate o standoff?

        # "engaged": lobo en el anillo (para la repulsión y el hook de velocidad).
        engaged = (dist_prey <= self.d_safe + self.wolf_engage_band).ravel()   # (n_wolves,)

        if pounce:
            # --- REMATE: persecución pura a la presa aislada (sin standoff ni repulsión) ---
            action = np.broadcast_to(dir_prey, self.wolves.shape).copy()
        else:
            # --- Regla 1 (simétrica): MANTENER d_safe respecto a la vaca más próxima ---
            d_cows = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)
            nearest = self.cows[d_cows.argmin(axis=1)]
            to_nearest = nearest - self.wolves
            dist_nearest = np.linalg.norm(to_nearest, axis=1, keepdims=True)
            dir_nearest = to_nearest / np.maximum(dist_nearest, 1e-9)
            approach = dir_prey * (dist_nearest > self.d_safe) - dir_nearest * (dist_nearest < self.d_safe)

            # --- Regla 2: repulsión entre lobos en el anillo -> cerco emergente ---
            delta = self.wolves[:, None, :] - self.wolves[None, :, :]          # (n,n,2): i - j
            dd = np.linalg.norm(delta, axis=2)                                 # (n,n)
            near = (dd < self.wolf_repulsion_radius) & engaged[None, :]
            np.fill_diagonal(near, False)
            rep_units = delta / np.maximum(dd[:, :, None], 1e-9)
            repulsion = (rep_units * near[:, :, None]).sum(axis=1)
            repulsion *= engaged[:, None] * self.wolf_repulsion_strength
            action = approach + repulsion

        # --- Desplazamiento, normalizado a la velocidad del lobo ---
        norm = np.linalg.norm(action, axis=1, keepdims=True)
        move_dir = action / np.maximum(norm, 1e-9)
        speed = np.where(engaged[:, None], self.wolf_speed_near, self.wolf_speed)
        self.wolves = self.wolves + move_dir * speed * self.dt
        self._clip_to_parcel(self.wolves)

        # Zonas prohibidas (clamp geométrico por paso, NO navegación ni evasión):
        # si un lobo terminaría dentro del establo o de la central, se le desliza
        # radialmente al borde para que quede fuera. Misma idea que el límite de las vacas.
        self._push_outside_circle(self.wolves, self.safe_zone)
        self._push_outside_circle(self.wolves, self.central_station)

    # ------------------------------------------------------------------ #
    # Recompensa (placeholder de equipo; per-agente vendrá con el MARL)
    # ------------------------------------------------------------------ #
    def _compute_reward(self, terminated: bool, truncated: bool) -> float:
        reward = -0.01  # penalización por paso (incentiva resolver rápido)
        if self.status == "success":
            reward += 1.0
        elif self.status == "predation":
            reward += -1.0
        return reward

    # ------------------------------------------------------------------ #
    # Condiciones terminales
    # ------------------------------------------------------------------ #
    def _check_terminal(self) -> tuple[bool, bool]:
        # 1) Depredación: algún lobo a <= capture_radius de alguna vaca.
        d = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)  # (n_wolves, n_cows)
        if d.min() <= self.capture_radius:
            self.status = "predation"
            self._record_capture(d)
            return True, False

        # 2) Éxito: todas las vacas dentro de la zona segura y todos los lobos fuera.
        cows_safe = self._in_safe_zone(self.cows).all()
        wolves_out = (~self._in_safe_zone(self.wolves)).all()
        if cows_safe and wolves_out:
            self.status = "success"
            return True, False

        # 3) Fin por tiempo.
        if self.step_count >= self.max_steps:
            self.status = "timeout"
            return False, True

        return False, False

    # ------------------------------------------------------------------ #
    # Instrumentación (verificación de procedencia; NO usa RNG)
    # ------------------------------------------------------------------ #
    def _spawn_cows(self) -> np.ndarray:
        """Reparte n_cows por el área de pasto (radio cow_spread alrededor de cow_spawn),
        con separación mínima al nacer y fuera de establo/central. Rejection sampling con
        el RNG del World -> disperso y reproducible (determinista con la seed)."""
        pts = np.empty((self.n_cows, 2))
        placed, tries = 0, 0
        max_tries = 200 * self.n_cows

        def _candidate():
            ang = self.rng.uniform(0.0, 2 * np.pi)
            rad = self.cow_spread * np.sqrt(self.rng.uniform(0.0, 1.0))
            return self.cow_spawn + np.array([rad * np.cos(ang), rad * np.sin(ang)])

        def _in_zone(p):
            return (np.linalg.norm(p - self.safe_zone[:2]) < self.safe_zone[2]
                    or np.linalg.norm(p - self.central_station[:2]) < self.central_station[2])

        while placed < self.n_cows and tries < max_tries:
            tries += 1
            p = _candidate()
            if _in_zone(p):
                continue
            if placed > 0 and np.linalg.norm(pts[:placed] - p, axis=1).min() < self.cow_spawn_min_sep:
                continue
            pts[placed] = p
            placed += 1
        # Si la separación mínima impidió colocar todas (raro), rellena sin esa restricción.
        while placed < self.n_cows:
            p = _candidate()
            if _in_zone(p):
                continue
            pts[placed] = p
            placed += 1
        return pts

    def _update_instrumentation(self) -> None:
        """Aislamiento por vaca + racha sostenida; y guardia de teletransporte (si activa)."""
        if self.n_cows > 1:
            d = np.linalg.norm(self.cows[:, None, :] - self.cows[None, :, :], axis=2)
            np.fill_diagonal(d, np.inf)
            iso = d.min(axis=1)
        else:
            iso = np.full(self.n_cows, np.inf)
        self._cow_isolation = iso
        isolated = iso >= self.wolf_pounce_isolation
        self._iso_streak = np.where(isolated, self._iso_streak + 1, 0)

        if self.teleport_guard:
            cow_disp = np.linalg.norm(self.cows - self._prev_cows, axis=1)
            cow_max = self.cow_speeds * self.dt * self.motion_tol
            for i in np.where(cow_disp > cow_max)[0]:
                self.guard_violations.append({"entity": "cow", "idx": int(i), "step": self.step_count,
                                              "disp": float(cow_disp[i]), "max": float(cow_max[i])})
            wolf_disp = np.linalg.norm(self.wolves - self._prev_wolves, axis=1)
            wolf_max = max(self.wolf_speed, self.wolf_speed_near) * self.dt * self.motion_tol
            for w in np.where(wolf_disp > wolf_max)[0]:
                self.guard_violations.append({"entity": "wolf", "idx": int(w), "step": self.step_count,
                                              "disp": float(wolf_disp[w]), "max": float(wolf_max)})

    def _record_capture(self, d: np.ndarray) -> None:
        """Procedencia de la captura: aislamiento sostenido, persecución, salto/sobrepaso."""
        wi, ci = np.unravel_index(int(d.argmin()), d.shape)   # lobo captor, vaca presa
        streak = int(self._iso_streak[ci])
        sustained = streak >= self.iso_sustain_steps
        pouncing = bool(self._wolf_pounce)
        prey_jump = float(np.linalg.norm(self.cows[ci] - self._prev_cows[ci]))
        prey_jump_flag = prey_jump > self.cow_speeds[ci] * self.dt * self.motion_tol
        wolf_over = float(np.linalg.norm(self.wolves[wi] - self._prev_wolves[wi]))
        wolf_over_flag = wolf_over > max(self.wolf_speed, self.wolf_speed_near) * self.dt * self.motion_tol
        self.capture_info = {
            "step": self.step_count, "prey_idx": int(ci), "captor_idx": int(wi),
            "isolation": float(self._cow_isolation[ci]),
            "pounce_threshold": float(self.wolf_pounce_isolation),
            "iso_streak": streak, "iso_sustained": bool(sustained),
            "wolf_pouncing": pouncing,
            "prey_jump": prey_jump, "prey_jump_flag": bool(prey_jump_flag),
            "wolf_overshoot": wolf_over, "wolf_overshoot_flag": bool(wolf_over_flag),
            "clean": bool(sustained and pouncing and not prey_jump_flag and not wolf_over_flag),
        }

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    def _in_safe_zone(self, points: np.ndarray) -> np.ndarray:
        center, radius = self.safe_zone[:2], self.safe_zone[2]
        return np.linalg.norm(points - center, axis=1) <= radius

    def _clip_to_parcel(self, pts: np.ndarray) -> None:
        np.clip(pts[:, 0], 0.0, self.W, out=pts[:, 0])
        np.clip(pts[:, 1], 0.0, self.H, out=pts[:, 1])

    def _push_outside_circle(self, pts: np.ndarray, circle: np.ndarray) -> None:
        """Clamp geométrico (NO navegación ni evasión): empuja al borde los puntos
        que caen dentro del círculo (cx, cy, r), deslizándolos radialmente hacia fuera."""
        center, r = circle[:2], circle[2]
        off = pts - center
        dist = np.linalg.norm(off, axis=1, keepdims=True)
        inside = (dist < r).ravel()
        if inside.any():
            d_in = dist[inside]
            # dirección radial; si el punto cae justo en el centro (off=0), empuja en +x.
            direction = np.where(d_in > 1e-9, off[inside] / np.maximum(d_in, 1e-9),
                                 np.array([1.0, 0.0]))
            pts[inside] = center + direction * (r * (1.0 + 1e-6))

    def _random_perimeter_points(self, n: int) -> np.ndarray:
        """n puntos aleatorios sobre el perímetro de la parcela [0,W]x[0,H]."""
        side = self.rng.integers(0, 4, size=n)   # 0 abajo, 1 arriba, 2 izq, 3 der
        t = self.rng.uniform(0.0, 1.0, size=n)
        pts = np.empty((n, 2))
        pts[side == 0] = np.column_stack([t[side == 0] * self.W, np.zeros((side == 0).sum())])
        pts[side == 1] = np.column_stack([t[side == 1] * self.W, np.full((side == 1).sum(), self.H)])
        pts[side == 2] = np.column_stack([np.zeros((side == 2).sum()), t[side == 2] * self.H])
        pts[side == 3] = np.column_stack([np.full((side == 3).sum(), self.W), t[side == 3] * self.H])
        return pts

    @staticmethod
    def cows_bbox(cows: np.ndarray) -> tuple[float, float, float, float]:
        """Bounding box (derivado) de las vacas: (x_min, y_min, x_max, y_max).
        Cantidad SOLO para dibujar y para colocar drones; no encierra a nadie."""
        xmin, ymin = cows.min(axis=0)
        xmax, ymax = cows.max(axis=0)
        return float(xmin), float(ymin), float(xmax), float(ymax)

    def herd_centroid(self) -> np.ndarray:
        return self.cows.mean(axis=0)

    def snapshot(self) -> dict:
        """Copia del estado para el render. Copias obligatorias: los arrays mutan."""
        return {
            "step": self.step_count,
            "t": self.step_count * self.dt,
            "cows": self.cows.copy(),
            "wolves": self.wolves.copy(),
            "drones": self.drones.copy(),
            "status": self.status,
        }
