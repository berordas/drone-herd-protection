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

MODELO DE AMENAZA = "DAR LA CARA" (no apiñamiento): las vacas adultas no se apiñan;
plantan cara (giran a encarar al lobo y lo mantienen a raya por delante). El lobo
respeta ese cono frontal y ataca por el FLANCO; un lobo solo no puede tumbar a una
adulta (regla de número mínimo), una manada sí (flanqueo simultáneo). Vacas y lobos
con INERCIA (velocidad en el estado) -> movimiento firme. Drones quietos; batería
como mecánica. Pendiente: terneros/defensores, escolta, observación real y MARL.
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
        cow_spread: float | None = None,      # radio del área de pasto
        dt: float = 0.1,
        max_steps: int = 600,
        drone_speed: float = 6.0,     # m/s, escala/tope de las acciones de los drones
        # --- Vaca adulta: pastar DISPERSO + DAR LA CARA (confrontación direccional) + inercia ---
        cow_speed: float = 1.2,            # m/s base, < wolf_speed (no escapan a la carrera). TUNE
        cow_speed_jitter: float = 0.4,     # heterogeneidad ±frac por vaca -> emerge la débil (la lenta). TUNE
        cow_spawn_min_sep: float | None = None,  # m, separación mínima al nacer (default ~0.25*cow_spread)
        k_separation: float = 3.0,         # peso de separación entre vacas (SIEMPRE activa). TUNE
        r_separation: float | None = None, # m, radio de separación (default ~0.4*cow_spread). TUNE
        wander_calm: float = 1.0,          # magnitud del deambular al pastar. TUNE
        wander_drift: float = 0.12,        # rad/paso: giro del rumbo de pasto (paseo angular lento -> firme). TUNE
        k_fence: float = 1.5,              # rigidez de la valla blanda (la "correa"). TUNE
        r_notice: float | None = None,     # m: percibe/encara al lobo dentro de esto (default 0.20*min). TUNE
        cone_half_angle: float = np.pi / 4,  # semiángulo del cono de seguridad frontal (45°). TUNE
        r_face_safe: float | None = None,  # m: mantiene al lobo FRONTAL a esta distancia (default 0.06*min). TUNE
        face_cooldown: float = 1.0,        # s: tras encarar a un lobo, espera esto antes de re-encarar a otro. TUNE
        turn_rate: float = 2.0,            # rad/s: velocidad angular máx al girar a encarar (firme, no salto). TUNE
        cow_inertia: float = 0.25,         # suavizado de velocidad de la vaca (firmeza; bajo = más inercia). TUNE
        # --- Lobo (reutilizado, ahora DIRECCIONAL): cono frontal + flanqueo + nº mínimo ---
        wolf_speed: float = 4.0,                       # m/s del lobo
        wolf_repulsion_radius: float | None = None,    # reparto angular de la manada (pincer; default 2*r_face_safe)
        wolf_repulsion_strength: float = 1.0,          # peso de la repulsión entre lobos
        n_min_adult: int = 2,              # nº mínimo de lobos para tumbar a una adulta. TUNE
        r_standoff: float | None = None,   # m: standoff AMPLIO del lobo solo (default 2*r_face_safe). TUNE
        prey_abandon_dist: float | None = None,  # m: la manada abandona la presa si escapa > esto del lobo más cercano (default 0.3*min). TUNE
        cone_band: float = 0.12,           # rad: banda muerta del cono (anti entra-sale-entra). TUNE
        wolf_inertia: float = 0.35,        # suavizado de velocidad del lobo. TUNE
        capture_radius: float | None = None,  # m, a qué distancia (un flanqueador) puede tumbar (default 0.03*min)
        teleport_guard: bool = False,      # log si una entidad se desplaza > su máx por paso * motion_tol
        motion_tol: float = 1.5,           # tolerancia de desplazamiento por paso (guardia)
        # --- DEPRECATED: modelo anterior (apiñamiento + Muro-pounce). Se ACEPTAN para no romper
        #     baseline.py v1 (los pasa explícitos) pero se IGNORAN en la dinámica nueva. ---
        k_cohesion_calm: float = 0.0, k_cohesion_panic: float = 0.0, wander_panic: float = 0.0,
        r_alarm: float | None = None, r_calm: float | None = None, r_fear: float | None = None,
        d_safe: float | None = None, wolf_speed_near: float | None = None,
        wolf_engage_band: float | None = None, iso_sustain_steps: int = 0,
        pounce_margin: float = 0.0, pounce_factor: float = 0.0, wolf_pounce_isolation: float | None = None,
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
        self.cow_spread = cow_spread if cow_spread is not None else 0.15 * m  # área de pasto (disperso)

        self.dt = dt
        self.max_steps = max_steps
        self.drone_speed = drone_speed

        # --- Vaca adulta (la valla blanda usa la zona de pasto: cow_spawn/cow_spread) ---
        self.cow_speed = cow_speed
        self.cow_speed_jitter = cow_speed_jitter
        self.cow_spawn_min_sep = (
            cow_spawn_min_sep if cow_spawn_min_sep is not None else 0.25 * self.cow_spread
        )
        self.k_separation = k_separation
        self.r_separation = r_separation if r_separation is not None else 0.4 * self.cow_spread
        self.wander_calm = wander_calm
        self.wander_drift = wander_drift
        self.k_fence = k_fence
        # Confrontación: encara al lobo dentro de r_notice; lo mantiene a r_face_safe si cae en
        # el cono frontal (±cone_half_angle); gira a turn_rate; tras encarar, face_cooldown antes
        # de cambiar de objetivo (la ventana que la manada explota por el flanco).
        self.r_notice = r_notice if r_notice is not None else 0.20 * m
        self.cone_half_angle = cone_half_angle
        self.r_face_safe = r_face_safe if r_face_safe is not None else 0.06 * m
        self.face_cooldown = face_cooldown
        self.turn_rate = turn_rate
        self.cow_inertia = cow_inertia

        # --- Lobo direccional ---
        self.wolf_speed = wolf_speed
        self.n_min_adult = n_min_adult
        self.r_standoff = r_standoff if r_standoff is not None else 2.0 * self.r_face_safe
        self.prey_abandon_dist = prey_abandon_dist if prey_abandon_dist is not None else 0.3 * m
        self.cone_band = cone_band
        self.wolf_inertia = wolf_inertia
        self.wolf_repulsion_radius = (
            wolf_repulsion_radius if wolf_repulsion_radius is not None else 2.0 * self.r_face_safe
        )
        self.wolf_repulsion_strength = wolf_repulsion_strength

        # capture_radius = a qué distancia un FLANQUEADOR puede tumbar (no mata de pasada: hace
        # falta n_min_adult flanqueadores a la vez fuera del cono). Derivado de la geometría.
        self.capture_radius = capture_radius if capture_radius is not None else 0.03 * m
        self.teleport_guard = teleport_guard
        self.motion_tol = motion_tol

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
        self.cow_vel: np.ndarray | None = None       # (n_cows,2) velocidad (inercia; bandera #1 para vacas)
        self.cow_heading: np.ndarray | None = None   # (n_cows,) ángulo de confrontación (a dónde "mira")
        self.cow_speeds: np.ndarray | None = None    # (n_cows,) velocidad máx por vaca (heterogénea, por episodio)
        self.cow_target_wolf: np.ndarray | None = None  # (n_cows,) lobo que encara ahora (-1 = ninguno)
        self.cow_face_cd: np.ndarray | None = None   # (n_cows,) enfriamiento antes de re-encarar a otro
        self._cow_graze_dir: np.ndarray | None = None  # (n_cows,) rumbo de pasto (paseo angular lento -> firme)
        self.wolves: np.ndarray | None = None
        self.wolf_vel: np.ndarray | None = None      # (n_wolves,2) velocidad (inercia)
        self.drones: np.ndarray | None = None
        self.battery: np.ndarray | None = None          # (n_drones,) fracción [0,1]
        self.drone_state: np.ndarray | None = None      # (n_drones,) ACTIVE/RETURNING/CHARGING/READY
        self.battery_activity: np.ndarray | None = None # (n_drones,) HOOK persecución (bandera #7): multiplica el drenaje
        self.drone_stranded: np.ndarray | None = None   # (n_drones,) HOOK "dron tirado" (sin travel-time no se activa)
        self._wolf_attacking: bool = False              # ¿la manada flanquea de verdad este paso? (instrumentación)
        self.pack_prey: int = -1                        # presa COMÚN fijada de la manada (-1 = ninguna)
        self._ever_committed: bool = False              # ¿se fijó ya alguna presa este episodio?
        self.n_refix: int = 0                           # re-fijaciones de presa (commitment; debe ser bajo)
        self.max_simul_targets: int = 0                 # máx nº de vacas atacadas a la vez (coordinación; ~1 ideal)
        self._simul_sum: int = 0                        # acumulador para la media de vacas atacadas a la vez
        self._simul_steps: int = 0
        self.flank_first_quorum: dict | None = None     # primer quórum de flanqueadores {step, flankers, killed}
        self.touch_breakdown: dict | None = None        # desglose de 'toques' que NO matan (diagnóstico de #3)
        self._prey_close_count: int = 0                 # lobos dentro de capture_radius de la presa (este paso)
        self._prey_flanker_count: int = 0               # de ésos, flanqueadores válidos (fuera del cono)
        self._prev_cows: np.ndarray | None = None       # posiciones previas (guardia de teletransporte)
        self._prev_wolves: np.ndarray | None = None
        self.capture_info: dict | None = None           # procedencia de la última captura (flanqueo)
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
        self.cow_vel = np.zeros((self.n_cows, 2))
        self.cow_heading = self.rng.uniform(0.0, 2 * np.pi, size=self.n_cows)  # mirada inicial cualquiera
        self.cow_target_wolf = np.full(self.n_cows, -1, dtype=int)
        self.cow_face_cd = np.zeros(self.n_cows)
        self._cow_graze_dir = self.rng.uniform(0.0, 2 * np.pi, size=self.n_cows)

        # Heterogeneidad leve: cada vaca con una velocidad algo distinta (una vez por episodio).
        # La más LENTA es la débil -> objetivo del lobo (sin terneros aún).
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
        self.wolf_vel = np.zeros((self.n_wolves, 2))

        # Batería a plena carga al reset (NO se aleatoriza en episodio: solo importa cuando los
        # drones actúan). HOOK: stagger=True (battery_check) reparte fases para operación continua.
        self._init_battery(stagger=False)

        self._wolf_attacking = False
        self.pack_prey = -1
        self._ever_committed = False
        self.n_refix = 0
        self.max_simul_targets = 0
        self._simul_sum = 0
        self._simul_steps = 0
        self.flank_first_quorum = None
        self.touch_breakdown = {"quorum": 0, "cerca_en_cono": 0, "solo_1_flanqueador": 0}
        self._prey_close_count = 0
        self._prey_flanker_count = 0
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
        self._prev_cows = self.cows.copy()   # para la guardia de teletransporte
        self._prev_wolves = self.wolves.copy()
        self._apply_drone_actions(actions)  # fase 1: control
        self._update_cows()                 # fase 2: pastar + encarar + inercia
        self._update_wolves()               #         lobo direccional + flanqueo + inercia
        self._enforce_face_cones()          #         la vaca planta cara: empuja al lobo frontal a r_face_safe
        self._step_battery()                # fase 3: batería/relevos (independiente de vacas/lobo)
        self.step_count += 1
        self._instrument_flanking()         # mide el flanqueo sobre la presa fijada (#3; no cambia la regla)
        self._update_instrumentation()      # guardia de teletransporte

        terminated, truncated = self._check_terminal()
        # Enlace de #3: en el PRIMER paso con quórum de flanqueadores, ¿disparó la muerte?
        if self.flank_first_quorum is not None and self.flank_first_quorum["killed"] is None:
            self.flank_first_quorum["killed"] = (self.status == "predation")
        reward = self._compute_reward(terminated, truncated)
        info = {"status": self.status}
        return self.get_observation(), reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    # Dinámicas
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

    # ------------------------------------------------------------------ #
    # Vacas adultas: pastar disperso + dar la cara (confrontación) + inercia
    # ------------------------------------------------------------------ #
    def _heading_units(self) -> np.ndarray:
        """Vector unitario de la mirada de cada vaca (a partir de cow_heading)."""
        return np.column_stack([np.cos(self.cow_heading), np.sin(self.cow_heading)])

    @staticmethod
    def _rotate_toward(current: np.ndarray, target: np.ndarray, max_step: float) -> np.ndarray:
        """Gira `current` hacia `target` (ángulos, rad) como mucho `max_step` por llamada."""
        diff = (target - current + np.pi) % (2 * np.pi) - np.pi   # diferencia envuelta a [-pi, pi]
        return current + np.clip(diff, -max_step, max_step)

    def _update_cow_headings(self) -> None:
        """Actualiza a quién encara cada vaca (heading) con enfriamiento.

        Encara al lobo más amenazante (el más cercano que se ACERCA) dentro de r_notice, girando
        a turn_rate. Una vez comprometida con un lobo, no cambia de objetivo hasta que pase
        face_cooldown -> mientras está fijada en uno, el flanco queda abierto a los demás.
        """
        self.cow_face_cd = np.maximum(self.cow_face_cd - self.dt, 0.0)
        if self.n_wolves == 0:
            return
        rel = self.wolves[None, :, :] - self.cows[:, None, :]        # (nc, nw, 2) lobo - vaca
        dist = np.linalg.norm(rel, axis=2)                           # (nc, nw)
        within = dist <= self.r_notice
        # ¿se acerca el lobo? proyección de la velocidad relativa sobre la dirección vaca<-lobo.
        relvel = self.wolf_vel[None, :, :] - self.cow_vel[:, None, :]   # (nc, nw, 2)
        toward_cow = -rel / np.maximum(dist[:, :, None], 1e-9)
        closing = np.sum(relvel * toward_cow, axis=2)               # (nc, nw) >0 = acercándose

        turn = self.turn_rate * self.dt
        for i in range(self.n_cows):
            near = np.where(within[i])[0]
            if near.size == 0:
                continue   # sin lobo cerca: mantiene la mirada (no re-orienta)
            tgt = self.cow_target_wolf[i]
            if tgt >= 0 and within[i, tgt] and self.cow_face_cd[i] > 0.0:
                chosen = tgt   # comprometida: sigue al mismo lobo (enfriamiento activo)
            else:
                appr = near[closing[i, near] > 0.0]      # los que se acercan
                pool = appr if appr.size else near       # si ninguno se acerca, el más cercano
                chosen = int(pool[np.argmin(dist[i, pool])])
                if chosen != self.cow_target_wolf[i]:
                    self.cow_target_wolf[i] = chosen
                    self.cow_face_cd[i] = self.face_cooldown
            desired_ang = np.arctan2(rel[i, chosen, 1], rel[i, chosen, 0])
            self.cow_heading[i] = self._rotate_toward(self.cow_heading[i], desired_ang, turn)

    def _update_cows(self) -> None:
        """Vaca adulta: pasta DISPERSA y planta cara (no se apiña). Velocidad con INERCIA.

        Pasto: separación + deambular (deriva lenta OU, no aleatorio fresco) + valla blanda.
        SIN cohesión/apiñamiento y SIN huida del lobo. Confrontación: gira a encarar (heading)
        en _update_cow_headings; el cono frontal se impone sobre el lobo en _enforce_face_cones.
        """
        cows = self.cows

        # 1) A quién encara cada vaca (mirada + enfriamiento).
        self._update_cow_headings()

        # 2) Separación: empuje desde vecinas dentro de r_separation (no se solapan).
        delta = cows[:, None, :] - cows[None, :, :]                    # (n,n,2): i - j
        dd = np.linalg.norm(delta, axis=2)
        close = (dd < self.r_separation) & (dd > 1e-9)
        push = np.where(
            close[:, :, None],
            delta / np.maximum(dd[:, :, None], 1e-9) * (1.0 - dd[:, :, None] / self.r_separation),
            0.0,
        )
        separation = self.k_separation * push.sum(axis=1)             # (n,2)

        # 3) Deambular como PASEO ANGULAR LENTO del rumbo de pasto: el vector siempre es unitario
        #    (no colapsa a cero como un OU de fuerza, que al normalizar haría girar la dirección)
        #    y el rumbo deriva poco a poco -> trayectorias firmes, sin temblor.
        self._cow_graze_dir = self._cow_graze_dir + self.rng.normal(0.0, self.wander_drift, size=self.n_cows)
        wander = self.wander_calm * np.column_stack([np.cos(self._cow_graze_dir),
                                                     np.sin(self._cow_graze_dir)])

        # 4) Valla blanda ("correa"): retorno hacia la zona de pasto SOLO si salen de ella.
        off = cows - self.cow_spawn
        dist_f = np.linalg.norm(off, axis=1, keepdims=True)
        excess = np.maximum(dist_f - self.cow_spread, 0.0)
        fence = -self.k_fence * off / np.maximum(dist_f, 1e-9) * excess

        # 5) Dirección deseada -> velocidad con INERCIA (suavizado), desplazamiento directo.
        total = separation + wander + fence
        norm = np.linalg.norm(total, axis=1, keepdims=True)
        desired_dir = np.where(norm > 1e-9, total / np.maximum(norm, 1e-9), 0.0)
        desired_vel = desired_dir * self.cow_speeds[:, None]
        self.cow_vel += self.cow_inertia * (desired_vel - self.cow_vel)
        self.cows = cows + self.cow_vel * self.dt

        # Contención DURA solo en límites reales (parcela + zonas prohibidas). La zona de pasto
        # la contiene la valla BLANDA, no un clamp.
        self._clip_to_parcel(self.cows)
        self._push_outside_circle(self.cows, self.safe_zone)
        self._push_outside_circle(self.cows, self.central_station)

    def _update_wolves(self) -> None:
        """Lobo DIRECCIONAL con PRESA COMÚN de la manada (corazón del flanqueo).

        La manada comparte UNA presa fijada (self.pack_prey) y la MANTIENE (histéresis): no se
        recalcula cada paso. Sin presa común no hay confluencia -> N duelos 1-contra-1, no pincer.
          - Fijación: en modo caza (>= n_min_adult lobos y alguno cruza r_notice del rebaño) se elige
            la presa (_select_prey) y TODA la manada va a por ESA.
          - Re-fijación SOLO si se vuelve inviable (_prey_viable): se refugia/entra en zona prohibida,
            o se aleja > prey_abandon_dist del lobo más cercano (escapó).
          - Sin presa (lobo solo, o manada aún sin comprometer): standoff AMPLIO a la vaca más cercana.
        Reparto de roles EMERGENTE: repulsión entre lobos alrededor de la presa única -> uno de frente
        (ella lo encara), los demás a los flancos/grupa. Velocidad con INERCIA.
        """
        if self.n_wolves == 0:
            self.pack_prey = -1
            self._wolf_attacking = False
            return

        d_wc = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)  # (nw, nc)
        hunt = self.n_wolves >= self.n_min_adult

        # --- Compromiso de manada (commitment) con HISTÉRESIS ---
        # Fija SOLO si un lobo ya está sobre la presa elegida (a <= r_notice); abandona a
        # > prey_abandon_dist (banda de histéresis: prey_abandon_dist > r_notice). Así no se
        # compromete con una presa lejana ni baila de objetivo cada paso.
        if self.pack_prey >= 0 and not self._prey_viable(self.pack_prey):
            self.pack_prey = -1                          # presa perdida (refugiada o escapada)
        if self.pack_prey < 0 and hunt:
            cand = self._select_prey()
            if cand >= 0 and float(d_wc[:, cand].min()) <= self.r_notice:
                if self._ever_committed:
                    self.n_refix += 1                    # re-fijación (debe ser rara)
                self.pack_prey = cand
                self._ever_committed = True

        if self.pack_prey < 0:
            # Rondar sin comprometerse: standoff amplio a la vaca más cercana de cada lobo.
            nearest = self.cows[d_wc.argmin(axis=1)]
            rel = self.wolves - nearest
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            desired = -rhat * (dist - self.r_standoff)
            self._wolf_attacking = False
        else:
            prey = self.cows[self.pack_prey]
            f = self._heading_units()[self.pack_prey]    # mirada de la presa común
            rel = self.wolves - prey
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            cosphi = rhat @ f
            at_flank = cosphi < np.cos(self.cone_half_angle + self.cone_band)   # fuera del cono (banda muerta)
            close_in = -rel                              # hacia la presa (cerrar a matar)
            cross = f[0] * rhat[:, 1] - f[1] * rhat[:, 0]    # signo de phi -> circular hacia el flanco
            tang = np.where((cross >= 0.0)[:, None],
                            np.column_stack([-rhat[:, 1], rhat[:, 0]]),
                            np.column_stack([rhat[:, 1], -rhat[:, 0]]))
            radial_hold = -rhat * (dist - self.r_face_safe)
            circle = tang + radial_hold
            desired = np.where(at_flank[:, None], close_in, circle)
            self._wolf_attacking = bool(np.any(at_flank & (dist.ravel() <= self.r_face_safe)))

        # Repulsión entre lobos cerca del rebaño -> reparto angular alrededor de la presa (pincer).
        engaged_w = d_wc.min(axis=1) <= self.r_notice
        dd_w = self.wolves[:, None, :] - self.wolves[None, :, :]
        ddn = np.linalg.norm(dd_w, axis=2)
        near = (ddn < self.wolf_repulsion_radius) & engaged_w[None, :]
        np.fill_diagonal(near, False)
        rep_units = dd_w / np.maximum(ddn[:, :, None], 1e-9)
        repulsion = (rep_units * near[:, :, None]).sum(axis=1) * engaged_w[:, None] * self.wolf_repulsion_strength
        desired = desired + repulsion

        # Dirección deseada -> velocidad con INERCIA (suavizado, sin saltos).
        dn = np.linalg.norm(desired, axis=1, keepdims=True)
        desired_dir = np.where(dn > 1e-9, desired / np.maximum(dn, 1e-9), 0.0)
        self.wolf_vel += self.wolf_inertia * (desired_dir * self.wolf_speed - self.wolf_vel)
        self.wolves = self.wolves + self.wolf_vel * self.dt
        self._clip_to_parcel(self.wolves)
        self._push_outside_circle(self.wolves, self.safe_zone)
        self._push_outside_circle(self.wolves, self.central_station)

    def _in_forbidden(self, pts: np.ndarray) -> np.ndarray:
        """Máscara (N,): puntos dentro del establo o la central (zonas prohibidas = refugio)."""
        in_safe = np.linalg.norm(pts - self.safe_zone[:2], axis=1) < self.safe_zone[2]
        in_station = np.linalg.norm(pts - self.central_station[:2], axis=1) < self.central_station[2]
        return in_safe | in_station

    def _select_prey(self) -> int:
        """Presa COMÚN de la manada (FACTORIZADA para enchufar terneros luego sin reescribir).

        Sin terneros: la adulta VIABLE que minimiza la distancia al CENTROIDE de los lobos (la que
        la manada tiene 'más rodeada' = oportunista). La lentitud importa EMERGENTE: la lenta se
        descuelga -> acaba siendo la más rodeada, sin que el lobo 'sepa' que es la débil.
        HUECO terneros: cuando los haya, la presa será un ternero (debilidad visible); con varios, el
        más accesible. Esa preferencia iría AQUÍ, antes del fallback a adultas."""
        viable = ~self._in_forbidden(self.cows)
        if not viable.any():
            return -1
        wolves_centroid = self.wolves.mean(axis=0)
        d = np.linalg.norm(self.cows - wolves_centroid, axis=1)
        d[~viable] = np.inf
        return int(np.argmin(d))

    def _prey_viable(self, idx: int) -> bool:
        """¿Sigue cazable la presa fijada? Inviable si se refugia (zona prohibida) o si escapó
        (lobo más cercano > prey_abandon_dist). Es la histéresis que sostiene el compromiso."""
        if bool(self._in_forbidden(self.cows[idx:idx + 1])[0]):
            return False
        nearest_wolf = float(np.linalg.norm(self.wolves - self.cows[idx], axis=1).min())
        return nearest_wolf <= self.prey_abandon_dist

    def _enforce_face_cones(self) -> None:
        """La vaca PLANTA CARA: cualquier lobo dentro de su cono frontal (±cone_half_angle) y a
        menos de r_face_safe es EMPUJADO radialmente hacia r_face_safe (no se mete por la cabeza).
        Fuera del cono (flancos/grupa) no hay repulsión: el lobo entra. El empuje está ACOTADO al
        desplazamiento máximo del lobo por paso (no teletransporta -> firme y sin saltos en render);
        mientras está en el cono nunca cuenta como flanqueador, así que empujarlo poco a poco es seguro."""
        if self.n_wolves == 0:
            return
        cos_cone = np.cos(self.cone_half_angle)
        max_push = self.wolf_speed * self.dt        # tope por paso = no salta (guardia limpia)
        f = self._heading_units()
        for i in range(self.n_cows):
            rel = self.wolves - self.cows[i]
            dist = np.linalg.norm(rel, axis=1)
            rhat = rel / np.maximum(dist[:, None], 1e-9)
            in_cone = (rhat @ f[i] >= cos_cone) & (dist < self.r_face_safe)
            if in_cone.any():
                target = self.cows[i] + rhat[in_cone] * self.r_face_safe   # punto en el borde del cono
                delta = target - self.wolves[in_cone]
                dn = np.linalg.norm(delta, axis=1, keepdims=True)
                self.wolves[in_cone] += delta / np.maximum(dn, 1e-9) * np.minimum(dn, max_push)

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
        # 1) Depredación por FLANQUEO: una vaca con >= n_min_adult lobos a la vez dentro de
        #    capture_radius y FUERA de su cono (no puede dar la cara a todos). Con 1 lobo, va
        #    encarado -> 0 flanqueadores -> no muere.
        if self.n_wolves > 0:
            cos_cone = np.cos(self.cone_half_angle)
            f = self._heading_units()                                  # (nc, 2)
            rel = self.wolves[None, :, :] - self.cows[:, None, :]      # (nc, nw, 2)
            dist = np.linalg.norm(rel, axis=2)                         # (nc, nw)
            rhat = rel / np.maximum(dist[:, :, None], 1e-9)
            cosphi = np.einsum('ij,ikj->ik', f, rhat)                 # (nc, nw)
            flankers = (dist <= self.capture_radius) & (cosphi < cos_cone)
            count = flankers.sum(axis=1)                              # flanqueadores por vaca
            if count.max() >= self.n_min_adult:
                self.status = "predation"
                self._record_capture(dist, flankers, count)
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

    def _record_capture(self, dist: np.ndarray, flankers: np.ndarray, count: np.ndarray) -> None:
        """Procedencia de la captura por flanqueo: qué vaca, cuántos flanqueadores, si era la débil."""
        ci = int(np.argmax(count))                       # vaca tumbada
        fl = np.where(flankers[ci])[0]
        self.capture_info = {
            "step": self.step_count, "prey_idx": ci,
            "n_flankers": int(count[ci]), "flankers": fl.tolist(),
            "is_pack_prey": bool(ci == self.pack_prey),
            "is_weakest": bool(ci == int(np.argmin(self.cow_speeds))),
            "min_wolf_dist": float(dist[ci].min()),
        }

    # ------------------------------------------------------------------ #
    # Instrumentación (NO usa RNG) + spawn
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

    def _instrument_flanking(self) -> None:
        """Instrumenta la muerte por flanqueo SOBRE la presa fijada (NO cambia la regla, solo MIDE).

        Cada paso cuenta lobos dentro de capture_radius de la presa y cuántos son flanqueadores
        VÁLIDOS (fuera del cono = la condición de muerte). Registra el primer quórum, el máximo de
        vacas atacadas a la vez (coordinación), y desglosa los 'toques' que NO matan para diagnóstico.
        """
        if self.pack_prey < 0 or self.n_wolves == 0:
            self._prey_close_count = self._prey_flanker_count = 0
            return
        prey = self.cows[self.pack_prey]
        f = self._heading_units()[self.pack_prey]
        rel = self.wolves - prey
        dist = np.linalg.norm(rel, axis=1)
        cosphi = (rel / np.maximum(dist[:, None], 1e-9)) @ f
        close = dist <= self.capture_radius
        out_cone = cosphi < np.cos(self.cone_half_angle)
        n_close = int(close.sum())
        n_flank = int((close & out_cone).sum())          # flanqueadores válidos (= regla de muerte)
        self._prey_close_count, self._prey_flanker_count = n_close, n_flank

        # Coordinación: nº de vacas distintas atacadas a la vez (un lobo dentro de r_face_safe).
        d_all = np.linalg.norm(self.cows[:, None, :] - self.wolves[None, :, :], axis=2)
        n_targets = int((d_all.min(axis=1) <= self.r_face_safe).sum())
        self.max_simul_targets = max(self.max_simul_targets, n_targets)
        self._simul_sum += n_targets
        self._simul_steps += 1

        # Primer instante de quórum: la muerte DEBERÍA dispararse aquí (se rellena 'killed' tras terminal).
        if n_flank >= self.n_min_adult and self.flank_first_quorum is None:
            self.flank_first_quorum = {"step": self.step_count, "flankers": n_flank, "killed": None}

        # Desglose de 'toques' (algún lobo dentro de capture_radius) que NO son quórum.
        if n_close >= 1:
            n_front = int((close & ~out_cone).sum())     # tocó por el FRENTE (dentro del cono)
            if n_flank >= self.n_min_adult:
                self.touch_breakdown["quorum"] += 1
            elif n_front >= 1:
                self.touch_breakdown["cerca_en_cono"] += 1   # close pero dentro del cono (2º en cono / frente)
            else:
                self.touch_breakdown["solo_1_flanqueador"] += 1

    def _update_instrumentation(self) -> None:
        """Guardia de teletransporte: log si una entidad se desplaza más que su máximo por paso
        (con la inercia, |vel| <= velocidad máx, así que nunca debería saltar)."""
        if not self.teleport_guard:
            return
        cow_disp = np.linalg.norm(self.cows - self._prev_cows, axis=1)
        cow_max = self.cow_speeds * self.dt * self.motion_tol
        for i in np.where(cow_disp > cow_max)[0]:
            self.guard_violations.append({"entity": "cow", "idx": int(i), "step": self.step_count,
                                          "disp": float(cow_disp[i]), "max": float(cow_max[i])})
        # El lobo puede moverse hasta wolf_speed*dt (velocidad) Y ser empujado otro tanto por el
        # cono frontal (ambos acotados) -> presupuesto 2x. Un teletransporte real (bug) sería de
        # varios metros, muy por encima, así que la guardia sigue siendo útil.
        wolf_disp = np.linalg.norm(self.wolves - self._prev_wolves, axis=1)
        wolf_max = 2.0 * self.wolf_speed * self.dt * self.motion_tol
        for w in np.where(wolf_disp > wolf_max)[0]:
            self.guard_violations.append({"entity": "wolf", "idx": int(w), "step": self.step_count,
                                          "disp": float(wolf_disp[w]), "max": float(wolf_max)})

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
        """Copia del estado para el render. Copias obligatorias: los arrays mutan.
        Incluye cow_heading para dibujar la mirada (el render solo LEE, nunca avanza)."""
        return {
            "step": self.step_count,
            "t": self.step_count * self.dt,
            "cows": self.cows.copy(),
            "cow_heading": self.cow_heading.copy(),
            "wolves": self.wolves.copy(),
            "drones": self.drones.copy(),
            "pack_prey": int(self.pack_prey),
            "status": self.status,
        }
