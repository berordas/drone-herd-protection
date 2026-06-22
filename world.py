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
adulta (regla de número mínimo), una manada sí (flanqueo simultáneo). Hay TERNEROS
(objetivo blando preferente) con una adulta DEFENSORA cada uno: el flanco que la madre
no cubre llega a la cría. Vacas y lobos con INERCIA (velocidad en el estado) ->
movimiento firme. Drones quietos; batería como mecánica. Pendiente: escolta, MARL.
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
        r_separation: float | None = None, # m, espacio personal al pastar (default ~0.55*cow_spread; sube = más repartidas). TUNE
        wander_calm: float = 0.2,          # velocidad de pastoreo en calma (~m/s; baja = casi quietas). TUNE
        wander_drift: float = 0.12,        # rad/paso: giro del rumbo de pasto (paseo angular lento -> firme). TUNE
        k_fence: float = 1.5,              # rigidez de la valla blanda (la "correa"). TUNE
        r_notice: float | None = None,     # m: percibe/encara al lobo dentro de esto (default 0.20*min). TUNE
        cone_half_angle: float = np.pi / 4,  # semiángulo del cono de seguridad frontal (45°). TUNE
        r_face_safe: float | None = None,  # m: mantiene al lobo FRONTAL a esta distancia (default 0.06*min). TUNE
        face_cooldown: float = 1.0,        # s: tras encarar a un lobo, espera esto antes de re-encarar a otro. TUNE
        turn_rate: float = 2.0,            # rad/s: velocidad angular máx al girar a encarar (firme, no salto). TUNE
        cow_inertia: float = 0.25,         # suavizado de velocidad de la vaca (firmeza; bajo = más inercia). TUNE
        # --- Terneros (0/1/2) + defensoras: objetivo blando preferente del lobo ---
        calf_count_probs: tuple[float, float, float] = (1/3, 1/3, 1/3),  # prob de 0 / 1 / 2 terneros por episodio. TUNE
        k_calf_cohesion: float = 1.0,      # cohesión ternero->defensora (se pega a la madre). TUNE
        k_defender_anchor: float = 0.6,    # cohesión defensora->su ternero (se queda con la cría). TUNE
        calf_personal_space: float | None = None,  # m: separación ternero<->defensora (AL LADO, no encima; default 0.5*capture_radius). TUNE
        # --- Lobo (reutilizado, ahora DIRECCIONAL): cono frontal + flanqueo + nº mínimo ---
        wolf_speed: float = 4.0,                       # m/s del lobo
        wolf_repulsion_radius: float | None = None,    # reparto angular de la manada (pincer; default 2*r_face_safe)
        wolf_repulsion_strength: float = 1.0,          # peso de la repulsión entre lobos
        wolf_spawn_dispersion: float | None = None,    # m: dispersión del cúmulo de spawn (salen JUNTOS de un sector; default 0.05*min). TUNE
        wolf_skirt_gain: float = 1.5,                  # ganancia de la componente TANGENCIAL para BORDEAR el rebaño (no atravesarlo). TUNE
        wolf_skirt_margin: float | None = None,        # m: holgura sobre la extensión del rebaño-obstáculo (default = r_face_safe). TUNE
        n_min_adult: int = 2,              # nº mínimo de lobos para tumbar a una adulta. TUNE
        r_standoff: float | None = None,   # m: standoff AMPLIO del lobo solo (default 2*r_face_safe). TUNE
        prey_abandon_dist: float | None = None,  # DEPRECATED: abandono por distancia. La presa se fija en t=0 y solo se suelta si se refugia; se ACEPTA pero NO se usa.
        cone_band: float = 0.12,           # rad: banda muerta del cono (anti entra-sale-entra). TUNE
        wolf_inertia: float = 0.35,        # suavizado de velocidad del lobo. TUNE
        capture_radius: float | None = None,  # m, a qué distancia (un flanqueador) puede tumbar (default 0.03*min)
        teleport_guard: bool = False,      # log si una entidad se desplaza > su máx por paso * motion_tol
        motion_tol: float = 1.5,           # tolerancia de desplazamiento por paso (guardia)
        # --- Escolta / terminal del episodio (máquina de fases VIGILANCIA->ESCOLTA + refugio) ---
        r_detect: float = 100.0,                 # m: alcance de DETECCIÓN de un dron en vuelo -> dispara ESCOLTA. TUNE
        episode_time_factor: float = 4.0,        # holgura del límite de tiempo (~k * diag / cow_speed). TUNE
        max_episode_steps: int | None = None,    # límite de pasos (default DERIVADO de geometría/cow_speed; ver __init__)
        refuge_margin: float | None = None,      # m: histéresis de borde del establo para contar "refugiada" (default 0.1*safe_radius). TUNE
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
        self.cow_spread = cow_spread if cow_spread is not None else 0.20 * m  # área de pasto (disperso, repartido)

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
        self.r_separation = r_separation if r_separation is not None else 0.55 * self.cow_spread
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

        # --- Terneros + defensoras ---
        self.calf_count_probs = np.asarray(calf_count_probs, dtype=float)
        self.calf_count_probs = self.calf_count_probs / self.calf_count_probs.sum()  # normaliza
        self.k_calf_cohesion = k_calf_cohesion
        self.k_defender_anchor = k_defender_anchor

        # --- Lobo direccional ---
        self.wolf_speed = wolf_speed
        self.n_min_adult = n_min_adult
        self.r_standoff = r_standoff if r_standoff is not None else 2.0 * self.r_face_safe
        self.prey_abandon_dist = prey_abandon_dist  # DEPRECATED (ya no se usa: presa fijada en t=0)
        self.cone_band = cone_band
        self.wolf_inertia = wolf_inertia
        self.wolf_repulsion_radius = (
            wolf_repulsion_radius if wolf_repulsion_radius is not None else 2.0 * self.r_face_safe
        )
        self.wolf_repulsion_strength = wolf_repulsion_strength
        # Spawn por sector (cúmulo) + rodeo del rebaño-obstáculo.
        self.wolf_spawn_dispersion = wolf_spawn_dispersion if wolf_spawn_dispersion is not None else 0.05 * m
        self.wolf_skirt_gain = wolf_skirt_gain
        self.wolf_skirt_margin = wolf_skirt_margin if wolf_skirt_margin is not None else self.r_face_safe

        # capture_radius = a qué distancia un FLANQUEADOR puede tumbar (no mata de pasada: hace
        # falta n_min_adult flanqueadores a la vez fuera del cono). Derivado de la geometría.
        self.capture_radius = capture_radius if capture_radius is not None else 0.03 * m
        # El ternero se coloca AL LADO de la defensora (no superpuesto): se pega a un anillo a esta
        # distancia, no a su posición exacta. Atado a la geometría (media capture_radius ~1.5 m).
        self.calf_personal_space = (
            calf_personal_space if calf_personal_space is not None else 0.5 * self.capture_radius
        )
        self.teleport_guard = teleport_guard
        self.motion_tol = motion_tol

        # --- Escolta / terminal del episodio ---
        # Disparador VIGILANCIA->ESCOLTA = DETECCIÓN por dron: un dron EN VUELO (ACTIVE) ve un lobo a
        # <= r_detect (distancia horizontal 2D). r_detect=100 m sale del criterio DRI de Johnson a nivel
        # reconocer/identificar (~8-13 px sobre un lobo de ~1,2 m) con GSD anclado a imágenes reales de
        # dron (~1,2 cm/px a ~52 m AGL) y patrulla a ~40-50 m, con margen por ángulo oblicuo/movimiento/
        # contraste -> ~80-120 m. Es horizontal porque la z del dron aún es conceptual (flag #2): r_detect
        # absorbe el rango oblicuo a la altura de patrulla. Candidato a eje de la rejilla de robustez (§5.1).
        self.r_detect = r_detect
        # Límite de tiempo: holgura (~episode_time_factor) para que el rebaño cruce el campo a cow_speed.
        # Derivado de la diagonal y cow_speed (sin número mágico): k * diag / cow_speed / dt pasos.
        self.episode_time_factor = episode_time_factor
        self.max_episode_steps = (
            max_episode_steps if max_episode_steps is not None
            else int(self.episode_time_factor * np.hypot(self.W, self.H) / self.cow_speed / self.dt)
        )
        # Histéresis de borde del establo: se cuenta "refugiada" al estar refuge_margin DENTRO del borde
        # (latched: una vez a salvo, sigue a salvo) -> sin parpadeo en la frontera.
        self.refuge_margin = refuge_margin if refuge_margin is not None else 0.1 * self.safe_radius

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
        self.n_calves: int = 0                       # nº de terneros este episodio (0/1/2, RNG)
        self.calves: np.ndarray | None = None        # (n_calves,2) posición de los terneros
        self.calf_vel: np.ndarray | None = None      # (n_calves,2) velocidad (inercia)
        self.calf_defender: np.ndarray | None = None # (n_calves,) índice de la adulta defensora ("madre")
        self.adult_calf: np.ndarray | None = None    # (n_cows,) ternero que defiende cada adulta (-1 = ninguno)
        self._calf_graze_dir: np.ndarray | None = None  # (n_calves,) deambular leve del ternero
        self.wolves: np.ndarray | None = None
        self.wolf_vel: np.ndarray | None = None      # (n_wolves,2) velocidad (inercia)
        self.wolf_spawn_angle: float = 0.0           # sector del perímetro por el que entró la manada (rad, RNG)
        self.drones: np.ndarray | None = None
        self.battery: np.ndarray | None = None          # (n_drones,) fracción [0,1]
        self.drone_state: np.ndarray | None = None      # (n_drones,) ACTIVE/RETURNING/CHARGING/READY
        self.battery_activity: np.ndarray | None = None # (n_drones,) HOOK persecución (bandera #7): multiplica el drenaje
        self.drone_stranded: np.ndarray | None = None   # (n_drones,) HOOK "dron tirado" (sin travel-time no se activa)
        self._wolf_attacking: bool = False              # ¿la manada flanquea de verdad este paso? (instrumentación)
        self.pack_prey: int = -1                        # índice de la presa COMÚN fijada (-1 = ninguna)
        self.pack_prey_kind: str | None = None          # "adult" | "calf" | None (a qué array indexa pack_prey)
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
        self.capture_info: dict | None = None           # procedencia de la ÚLTIMA captura (flanqueo)
        self.captures: list = []                         # todas las capturas del episodio (multi-muerte)
        self.guard_violations: list = []                # log de la guardia de teletransporte
        # --- Escolta / terminal del episodio ---
        self.phase: str = "VIGILANCIA"                  # VIGILANCIA -> ESCOLTA (no vuelve atrás)
        self.cow_alive: np.ndarray | None = None        # (n_cows,) viva (no cazada)
        self.cow_safe: np.ndarray | None = None         # (n_cows,) refugiada en el establo (no cazable)
        self.calf_alive: np.ndarray | None = None       # (n_calves,) vivo
        self.calf_safe: np.ndarray | None = None        # (n_calves,) refugiado
        self.n_depredadas: int = 0                       # reses cazadas en el episodio (cuenta; más = peor)
        self.terminal_step: int | None = None           # paso en que se resolvió el episodio
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
        # La más LENTA tiende a quedarse en el borde -> emerge como presa (sin terneros).
        self.cow_speeds = self.cow_speed * self.rng.uniform(
            1.0 - self.cow_speed_jitter, 1.0 + self.cow_speed_jitter, size=self.n_cows
        )

        # Terneros (0/1/2, RNG sembrado: no aparecen/desaparecen a mitad). Cada uno con una adulta
        # DEFENSORA fija (su "madre"), asignada en el spawn; el ternero nace pegado a ella.
        self.n_calves = int(self.rng.choice(3, p=self.calf_count_probs))
        if self.n_calves > 0:
            self.calf_defender = self.rng.choice(self.n_cows, size=self.n_calves, replace=False)
            # Nace AL LADO de la defensora: a calf_personal_space en una dirección aleatoria (no encima).
            ang = self.rng.uniform(0.0, 2 * np.pi, size=self.n_calves)
            offset = self.calf_personal_space * np.column_stack([np.cos(ang), np.sin(ang)])
            self.calves = self.cows[self.calf_defender] + offset
        else:
            self.calf_defender = np.zeros(0, dtype=int)
            self.calves = np.zeros((0, 2))
        self.calf_vel = np.zeros((self.n_calves, 2))
        self._calf_graze_dir = self.rng.uniform(0.0, 2 * np.pi, size=self.n_calves)
        self.adult_calf = np.full(self.n_cows, -1, dtype=int)
        self.adult_calf[self.calf_defender] = np.arange(self.n_calves)

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

        # Lobos: nº aleatorio por episodio; TODOS salen AGRUPADOS de un mismo sector del perímetro
        # (sector sorteado por episodio) -> la manada llega junta y de una dirección (y se aleatoriza
        # la dirección de ataque entre episodios, bandera #4).
        self.n_wolves = int(self.rng.integers(self.wolves_min, self.wolves_max + 1))
        self.wolves = self._spawn_wolves_sector(self.n_wolves)
        self.wolf_vel = np.zeros((self.n_wolves, 2))

        # Batería a plena carga al reset (NO se aleatoriza en episodio: solo importa cuando los
        # drones actúan). HOOK: stagger=True (battery_check) reparte fases para operación continua.
        self._init_battery(stagger=False)

        self._wolf_attacking = False
        self.pack_prey = -1
        self.pack_prey_kind = None
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
        self.captures = []
        self.guard_violations = []

        # Escolta / terminal: máquina de fases + vivas/refugiadas (gancho de refugio).
        self.phase = "VIGILANCIA"
        self.cow_alive = np.ones(self.n_cows, dtype=bool)
        self.cow_safe = np.zeros(self.n_cows, dtype=bool)
        self.calf_alive = np.ones(self.n_calves, dtype=bool)
        self.calf_safe = np.zeros(self.n_calves, dtype=bool)
        self.n_depredadas = 0
        self.terminal_step = None

        # Presa COMÚN fijada en t=0 (no se espera a que un lobo se acerque): la manada se dirige a
        # ella desde el primer paso. Mantiene el commitment todo el episodio (sin re-fijación).
        self._commit_initial_prey()

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
        self._update_calves()               #         terneros pegados a su defensora
        self._update_wolves()               #         lobo direccional + flanqueo + inercia
        self._enforce_face_cones()          #         la vaca planta cara: empuja al lobo frontal a r_face_safe
        # Clamp #5 tiene la ÚLTIMA palabra: el empuje del cono (vacas que pastan cerca del borde) puede
        # meter un lobo en el establo -> se le vuelve a expulsar (invariante "ningún lobo dentro").
        self._push_outside_circle(self.wolves, self.safe_zone)
        self._push_outside_circle(self.wolves, self.central_station)
        self._step_battery()                # fase 3: batería/relevos (independiente de vacas/lobo)
        self.step_count += 1
        self._update_phase()                # VIGILANCIA -> ESCOLTA (informativa; seam para el guiado)
        self._instrument_flanking()         # mide el flanqueo sobre la presa (ANTES de aplicar muertes)
        prey_killed = self._process_predation()  # aplica muertes (regla SIN cambios) y cuenta n_depredadas
        self._update_instrumentation()      # guardia de teletransporte

        # Enlace de #3: en el PRIMER paso con quórum de flanqueadores, ¿disparó la muerte de la presa?
        if (self.flank_first_quorum is not None and self.flank_first_quorum["killed"] is None
                and self.flank_first_quorum["step"] == self.step_count):
            self.flank_first_quorum["killed"] = prey_killed

        terminated, truncated = self._check_terminal()
        reward = self._compute_reward(terminated, truncated)
        info = self._terminal_info(terminated or truncated)
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
            if not self.cow_alive[i] or self.cow_safe[i]:
                continue   # res fuera de juego (cazada/refugiada): no encara
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

        # 4b) Anclaje de las DEFENSORAS a su ternero: MUELLE a longitud natural = espacio personal,
        #     así la madre se queda JUNTO a la cría (a ~calf_personal_space, ni encima ni lejos; solo
        #     encara, sin interponerse). Las demás adultas pastan libres.
        anchor = np.zeros_like(cows)
        if self.n_calves > 0:
            d = self.calf_defender
            to_calf = self.calves - cows[d]
            dd = np.linalg.norm(to_calf, axis=1, keepdims=True)
            anchor[d] = self.k_defender_anchor * (dd - self.calf_personal_space) * to_calf / np.maximum(dd, 1e-9)

        # 5) Suma de fuerzas -> velocidad deseada usando su MAGNITUD como rapidez (NO se normaliza a
        #    tope: antes se normalizaba y el rebaño pastaba SIEMPRE a cow_speed, ignorando wander_calm).
        #    Así wander_calm fija la rapidez de pastoreo (casi quietas), mientras separación/valla/ancla
        #    siguen reaccionando fuerte cuando hace falta (se capa a cow_speed). INERCIA para firmeza.
        total = separation + wander + fence + anchor
        speed = np.linalg.norm(total, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.cow_speeds[:, None] / np.maximum(speed, 1e-9))
        desired_vel = total * scale
        self.cow_vel += self.cow_inertia * (desired_vel - self.cow_vel)
        self.cows = cows + self.cow_vel * self.dt

        # Reses ya resueltas (CAZADAS o REFUGIADAS de pasos previos) no se mueven: congeladas en su
        # sitio. La refugiada se queda DENTRO del establo. 'cows' = posición al inicio del paso.
        frozen = (~self.cow_alive) | self.cow_safe
        if frozen.any():
            self.cows[frozen] = cows[frozen]
            self.cow_vel[frozen] = 0.0
        self._clip_to_parcel(self.cows)

        # Gancho (a) REFUGIO: marca a salvo las vivas que han entrado al establo (umbral con histéresis
        # de borde) ANTES de expulsar a las que pastan -> una res que entra se queda (no se la expulsa).
        d_safe = np.linalg.norm(self.cows - self.safe_zone[:2], axis=1)
        self.cow_safe |= self.cow_alive & ~self.cow_safe & (d_safe <= self.safe_zone[2] - self.refuge_margin)

        # Contención DURA (parcela + zonas prohibidas) SOLO para las CAZABLES (a una refugiada NO se la
        # expulsa del establo). La zona de pasto la contiene la valla BLANDA, no un clamp.
        active = self.cow_alive & ~self.cow_safe
        if active.any():
            sub = self.cows[active]
            self._push_outside_circle(sub, self.safe_zone)
            self._push_outside_circle(sub, self.central_station)
            self.cows[active] = sub

    def _update_calves(self) -> None:
        """Ternero: se coloca AL LADO de su DEFENSORA (a ~calf_personal_space, no encima) + deambular
        leve, con INERCIA. NO encara, NO huye (indefenso; su protección es la defensora).

        La cohesión es un MUELLE a longitud natural = espacio personal (con el anclaje recíproco de la
        madre): el ternero se asienta a un lado (no superpuesto) y la sigue si ésta se aleja. Misma
        rapidez de pastoreo en calma (wander_calm) y mismo capado de magnitud que las adultas."""
        if self.n_calves == 0:
            return
        to_def = self.cows[self.calf_defender] - self.calves          # hacia la madre (ya movida este paso)
        dist = np.linalg.norm(to_def, axis=1, keepdims=True)
        # MUELLE a longitud natural = espacio personal: tira hacia la madre si está lejos, la separa
        # si está encima -> el ternero se asienta a ~calf_personal_space (AL LADO, no superpuesto).
        cohesion = self.k_calf_cohesion * (dist - self.calf_personal_space) * to_def / np.maximum(dist, 1e-9)
        self._calf_graze_dir = self._calf_graze_dir + self.rng.normal(0.0, self.wander_drift, size=self.n_calves)
        wander = self.wander_calm * np.column_stack([np.cos(self._calf_graze_dir),
                                                     np.sin(self._calf_graze_dir)])
        total = cohesion + wander
        speed = np.linalg.norm(total, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.cow_speed / np.maximum(speed, 1e-9))
        prev = self.calves
        self.calf_vel += self.cow_inertia * (total * scale - self.calf_vel)
        self.calves = self.calves + self.calf_vel * self.dt
        frozen = (~self.calf_alive) | self.calf_safe   # cazados/refugiados: congelados (no se expulsan del establo)
        if frozen.any():
            self.calves[frozen] = prev[frozen]
            self.calf_vel[frozen] = 0.0
        self._clip_to_parcel(self.calves)
        # Gancho (a) REFUGIO para terneros (igual que adultas).
        d_safe = np.linalg.norm(self.calves - self.safe_zone[:2], axis=1)
        self.calf_safe |= self.calf_alive & ~self.calf_safe & (d_safe <= self.safe_zone[2] - self.refuge_margin)
        active = self.calf_alive & ~self.calf_safe
        if active.any():
            sub = self.calves[active]
            self._push_outside_circle(sub, self.safe_zone)
            self._push_outside_circle(sub, self.central_station)
            self.calves[active] = sub

    def _update_wolves(self) -> None:
        """Lobo DIRECCIONAL con PRESA COMÚN de la manada (corazón del flanqueo).

        La manada comparte UNA presa, FIJADA EN t=0 (_commit_initial_prey en reset) y mantenida todo
        el episodio. Sin presa común no hay confluencia -> N duelos 1-contra-1, no pincer.
          - Fijación: en el reset, si hay caza (ternero, o >= n_min_adult lobos), se elige la presa
            (_select_prey) y TODA la manada va a por ESA desde el primer paso.
          - Se suelta SOLO si deja de ser cazable (_prey_lost_reason): se REFUGIA o MUERE -> la manada
            RE-SELECCIONA (única re-fijación). Ya NO se abandona por distancia (empieza lejos del perímetro).
          - Sin presa (lobo solo sin ternero): standoff AMPLIO a la vaca más cercana (no se compromete).
        Reparto de roles EMERGENTE: repulsión entre lobos alrededor de la presa única -> uno de frente
        (ella lo encara), los demás a los flancos/grupa. Si el rebaño se interpone, el lobo lo BORDEA
        (componente tangencial) en vez de atravesarlo. Velocidad con INERCIA.
        """
        if self.n_wolves == 0:
            self.pack_prey = -1
            self._wolf_attacking = False
            return

        d_wc = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)  # (nw, nc)

        # La presa viene fijada de t=0. Se SUELTA solo si deja de ser cazable: se REFUGIA (gancho b)
        # o muere. En ambos casos la manada RE-SELECCIONA (única re-fijación permitida); el contador
        # n_refix sube SOLO al refugiarse (la muerte fuerza la re-selección, no es oscilación).
        reason = self._prey_lost_reason()
        if reason is not None:
            self.pack_prey = -1; self.pack_prey_kind = None
            if reason == "refuge":
                self.n_refix += 1
            self._try_commit_prey()

        if self.pack_prey < 0:
            # Rondar sin comprometerse: standoff amplio a la vaca más cercana de cada lobo.
            nearest = self.cows[d_wc.argmin(axis=1)]
            rel = self.wolves - nearest
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            desired = -rhat * (dist - self.r_standoff)
            self._wolf_attacking = False
        else:
            # El cono que estorba es el de la presa adulta o el de la DEFENSORA del ternero; el lobo
            # CIERRA hacia la presa (ternero o adulta). Para una adulta, cono y presa coinciden.
            prey_pos = self._prey_pos()
            cone_pos, f = self._prey_cone()
            rel = self.wolves - cone_pos                 # ángulo respecto al cono (defensora/adulta)
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            cosphi = rhat @ f
            at_flank = cosphi < np.cos(self.cone_half_angle + self.cone_band)   # fuera del cono (banda muerta)
            close_in = prey_pos - self.wolves            # hacia la PRESA (cerrar a matar)
            cross = f[0] * rhat[:, 1] - f[1] * rhat[:, 0]    # signo de phi -> circular hacia el flanco
            tang = np.where((cross >= 0.0)[:, None],
                            np.column_stack([-rhat[:, 1], rhat[:, 0]]),
                            np.column_stack([rhat[:, 1], -rhat[:, 0]]))
            radial_hold = -rhat * (dist - self.r_face_safe)
            circle = tang + radial_hold
            desired = np.where(at_flank[:, None], close_in, circle)
            self._wolf_attacking = bool(np.any(at_flank & (dist.ravel() <= self.r_face_safe)))

        # --- RODEAR el rebaño (no atravesarlo): si las NO-presa se interponen entre el lobo y la
        #     presa, añade una componente TANGENCIAL (perpendicular a lobo->presa) hacia el lado
        #     OPUESTO al cúmulo -> el lobo ARQUEA alrededor del rebaño hasta el costado de la presa,
        #     en vez de beelinear y atascarse contra las vacas que lo encaran. Tangencial (no solo
        #     repulsión radial, que lo dejaría parado de frente) y comprometido con un lado (sign de s).
        if self.pack_prey >= 0:
            prey_pos = self._prey_pos()
            mask = self.cow_alive & ~self.cow_safe           # solo las CAZABLES son obstáculo (las muertas/refugiadas no)
            if self.pack_prey_kind == "adult":
                mask[self.pack_prey] = False                 # la presa adulta no es obstáculo de sí misma
            herd = self.cows[mask]
            if herd.shape[0] >= 2:
                C = herd.mean(axis=0)                                          # centroide del cúmulo
                R_herd = float(np.linalg.norm(herd - C, axis=1).mean()) + self.wolf_skirt_margin
                to_prey = prey_pos[None, :] - self.wolves
                L = np.linalg.norm(to_prey, axis=1, keepdims=True)
                u = to_prey / np.maximum(L, 1e-9)
                perp = np.column_stack([-u[:, 1], u[:, 0]])
                to_C = C[None, :] - self.wolves
                proj = np.sum(to_C * u, axis=1)                               # avance hasta la proyección de C
                s = np.sum(to_C * perp, axis=1)                               # offset perpendicular de C (con signo)
                between = (proj > 0.0) & (proj < L.ravel())                   # C está ENTRE el lobo y la presa
                gate = between * np.clip(1.0 - np.abs(s) / max(R_herd, 1e-9), 0.0, 1.0)  # cruza el cúmulo
                side = np.where(s >= 0.0, -1.0, 1.0)                          # rodea por el lado OPUESTO a C (commit)
                skirt = self.wolf_skirt_gain * (gate * L.ravel())[:, None] * (side[:, None] * perp)
                desired = desired + skirt

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

    def _commit_initial_prey(self) -> None:
        """Fija la presa COMÚN de la manada en t=0 (no espera a que un lobo cruce r_notice). Delega en
        _try_commit_prey; una vez fijada se mantiene (la suelta solo el refugio/la muerte de la presa)."""
        self.pack_prey = -1
        self.pack_prey_kind = None
        self._try_commit_prey()

    def _try_commit_prey(self) -> None:
        """Si no hay presa y hay caza, fija una entre las CAZABLES (viva y no refugiada):
          - Con ternero cazable -> ternero (objetivo blando, con cualquier nº de lobos).
          - Sin ternero y >= n_min_adult lobos -> la adulta cazable más expuesta.
          - Lobo solo sin ternero -> sin presa (standoff amplio: no se compromete).
        NO toca n_refix (la contabilidad de re-fijación la lleva quien llama, solo en refugio)."""
        if self.pack_prey >= 0 or self.n_wolves == 0:
            return
        hunt = bool((self.calf_alive & ~self.calf_safe).any()) or (self.n_wolves >= self.n_min_adult)
        if not hunt:
            return
        kind, cand = self._select_prey()
        if cand >= 0:
            self.pack_prey, self.pack_prey_kind = cand, kind
            self._ever_committed = True

    def _select_prey(self) -> tuple[str | None, int]:
        """Presa COMÚN de la manada -> (tipo, índice), solo entre las CAZABLES (viva y no refugiada).
          - Si hay TERNERO cazable: la presa es un ternero (override duro, con cualquier nº de lobos);
            con varios, el más accesible (más cercano al centroide de los lobos).
          - Si NO: la adulta cazable más EXPUESTA = la más LEJOS del centroide del REBAÑO vivo (la del
            borde/descolgada; reengancha con la heterogeneidad). NO la más céntrica (esa va protegida)."""
        cazable_calf = self.calf_alive & ~self.calf_safe
        if cazable_calf.any():
            wolves_centroid = self.wolves.mean(axis=0)
            d = np.linalg.norm(self.calves - wolves_centroid, axis=1)
            d[~cazable_calf] = np.inf
            return ("calf", int(np.argmin(d)))            # el ternero cazable más accesible
        cazable = (self.cow_alive & ~self.cow_safe) & ~self._in_forbidden(self.cows)
        if not cazable.any():
            return (None, -1)
        herd_centroid = self.cows[self.cow_alive & ~self.cow_safe].mean(axis=0)
        d = np.linalg.norm(self.cows - herd_centroid, axis=1)
        d[~cazable] = -np.inf
        return ("adult", int(np.argmax(d)))               # la adulta cazable más expuesta (borde)

    def _prey_pos(self) -> np.ndarray | None:
        """Posición de la presa fijada (ternero o adulta), o None."""
        if self.pack_prey < 0:
            return None
        return self.calves[self.pack_prey] if self.pack_prey_kind == "calf" else self.cows[self.pack_prey]

    def _prey_cone(self) -> tuple[np.ndarray, np.ndarray]:
        """Posición y mirada (unitaria) del cono que DEFIENDE a la presa: el de la defensora si es
        ternero, el de la propia adulta si es adulta."""
        d = int(self.calf_defender[self.pack_prey]) if self.pack_prey_kind == "calf" else int(self.pack_prey)
        head = self.cow_heading[d]
        return self.cows[d], np.array([np.cos(head), np.sin(head)])

    def _prey_lost_reason(self) -> str | None:
        """Por qué la presa fijada deja de ser cazable: 'dead' / 'refuge' / None. Es la ÚNICA
        condición de re-fijación (la presa se mantiene si no muere ni se refugia; sin abandono por
        distancia, que reintroduciría el bucle de oscilación)."""
        if self.pack_prey < 0:
            return None
        if self.pack_prey_kind == "calf":
            if not self.calf_alive[self.pack_prey]:
                return "dead"
            if self.calf_safe[self.pack_prey]:
                return "refuge"
        else:
            if not self.cow_alive[self.pack_prey]:
                return "dead"
            if self.cow_safe[self.pack_prey]:
                return "refuge"
        return None

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
            if not self.cow_alive[i] or self.cow_safe[i]:
                continue   # res fuera de juego: su cono ya no estorba al lobo
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
    # Máquina de fases + depredación + terminal (el refugio va en _update_cows/_update_calves)
    # ------------------------------------------------------------------ #
    def _update_phase(self) -> None:
        """VIGILANCIA -> ESCOLTA por DETECCIÓN: la PRIMERA vez que algún dron EN VUELO (ACTIVE) tiene
        un lobo a distancia horizontal (2D) <= r_detect. Los drones aparcados en la central
        (CHARGING/READY) no vigilan; RETURNING se deja fuera por simplicidad (retorno transitorio).
        No vuelve a VIGILANCIA. Informativa (seam para el guiado del paso siguiente; todavía NO cambia
        la dinámica de las vacas)."""
        if self.phase == "ESCOLTA" or self.n_wolves == 0:
            return
        flying = self.drones[self.drone_state == ACTIVE]   # solo los ACTIVE detectan (en tierra no se vigila)
        if flying.shape[0] == 0:
            return
        d = np.linalg.norm(flying[:, None, :] - self.wolves[None, :, :], axis=2)  # (n_vuelo, n_lobo)
        if float(d.min()) <= self.r_detect:
            self.phase = "ESCOLTA"

    def _process_predation(self) -> bool:
        """Aplica la muerte por FLANQUEO (regla SIN cambios) a las reses CAZABLES y las marca cazadas
        (multi-muerte: NO termina el episodio). Cuenta n_depredadas y registra cada captura. Devuelve
        si la PRESA fijada murió este paso (para enlazar el quórum de #3)."""
        if self.n_wolves == 0:
            return False
        cos_cone = np.cos(self.cone_half_angle)
        prey_killed = False

        # Terneros cazables: >= 1 flanqueador del cono de su DEFENSORA (si la madre sigue en juego;
        # si murió, el ternero queda indefenso = cualquier lobo dentro de capture_radius lo caza).
        for j in range(self.n_calves):
            if not (self.calf_alive[j] and not self.calf_safe[j]):
                continue
            d = int(self.calf_defender[j])
            dist_calf = np.linalg.norm(self.wolves - self.calves[j], axis=1)
            if self.cow_alive[d] and not self.cow_safe[d]:
                fdef = np.array([np.cos(self.cow_heading[d]), np.sin(self.cow_heading[d])])
                rel_def = self.wolves - self.cows[d]
                cos_def = (rel_def / np.maximum(np.linalg.norm(rel_def, axis=1)[:, None], 1e-9)) @ fdef
                flank = (dist_calf <= self.capture_radius) & (cos_def < cos_cone)
            else:
                flank = dist_calf <= self.capture_radius
            if flank.sum() >= 1:
                self.calf_alive[j] = False
                self.n_depredadas += 1
                self._add_capture(self._make_capture_calf(j, np.where(flank)[0], float(dist_calf.min())))
                if self.pack_prey_kind == "calf" and self.pack_prey == j:
                    prey_killed = True

        # Adultas cazables: >= n_min_adult flanqueadores a la vez (fuera del cono). Con 1 lobo no muere.
        cazable = self.cow_alive & ~self.cow_safe
        if cazable.any():
            f = self._heading_units()                                  # (nc, 2)
            rel = self.wolves[None, :, :] - self.cows[:, None, :]      # (nc, nw, 2)
            dist = np.linalg.norm(rel, axis=2)                         # (nc, nw)
            rhat = rel / np.maximum(dist[:, :, None], 1e-9)
            cosphi = np.einsum('ij,ikj->ik', f, rhat)                 # (nc, nw)
            flankers = (dist <= self.capture_radius) & (cosphi < cos_cone)
            count = flankers.sum(axis=1)
            count[~cazable] = 0                                        # las no cazables no mueren
            for ci in np.where(count >= self.n_min_adult)[0]:
                self.cow_alive[ci] = False
                self.n_depredadas += 1
                self._add_capture(self._make_capture_adult(int(ci), dist, flankers, int(count[ci])))
                if self.pack_prey_kind == "adult" and self.pack_prey == ci:
                    prey_killed = True
        return prey_killed

    def _check_terminal(self) -> tuple[bool, bool]:
        """Terminal del episodio de escolta (3 estados). El episodio se RESUELVE cuando no queda
        ninguna res cazable (todas a salvo o cazadas), o por tiempo.
          - ÉXITO        = todas las reses vivas a salvo, ninguna cazada y ningún lobo dentro del establo.
          - DEPREDACIÓN  = se resuelve / agota el tiempo con >= 1 res cazada (cuanta más, peor).
          - TIMEOUT      = se agota max_episode_steps sin éxito y sin cazadas."""
        in_play = int((self.cow_alive & ~self.cow_safe).sum() + (self.calf_alive & ~self.calf_safe).sum())
        wolf_in_establo = bool(self.n_wolves > 0 and self._in_safe_zone(self.wolves).any())

        if in_play == 0:                                  # todas las reses resueltas (a salvo o cazadas)
            self.status = "success" if (self.n_depredadas == 0 and not wolf_in_establo) else "predation"
            self.terminal_step = self.step_count
            return True, False
        if self.step_count >= self.max_episode_steps:     # se acaba el tiempo
            self.status = "predation" if self.n_depredadas >= 1 else "timeout"
            self.terminal_step = self.step_count
            return False, True
        return False, False

    def _terminal_info(self, terminal: bool) -> dict:
        """Resumen que devuelve step(): estado + fase + contadores (n_safe, n_depredadas, n_fuera)."""
        n_safe = int(self.cow_safe.sum() + self.calf_safe.sum())
        n_fuera = int((self.cow_alive & ~self.cow_safe).sum() + (self.calf_alive & ~self.calf_safe).sum())
        return {
            "status": self.status, "phase": self.phase,
            "n_safe": n_safe, "n_depredadas": int(self.n_depredadas), "n_fuera": n_fuera,
            "terminal_step": self.terminal_step if terminal else None,
        }

    def _add_capture(self, cap: dict) -> None:
        self.captures.append(cap)
        self.capture_info = cap          # capture_info = última captura (compat con la instrumentación)

    def _make_capture_adult(self, ci: int, dist: np.ndarray, flankers: np.ndarray, n_flankers: int) -> dict:
        """Procedencia de una captura de ADULTA por flanqueo."""
        fl = np.where(flankers[ci])[0]
        return {
            "step": self.step_count, "kind": "adult", "prey_idx": int(ci),
            "n_flankers": int(n_flankers), "flankers": fl.tolist(),
            "is_pack_prey": bool(self.pack_prey_kind == "adult" and ci == self.pack_prey),
            "is_weakest": bool(ci == int(np.argmin(self.cow_speeds))),
            "min_wolf_dist": float(dist[ci].min()),
        }

    def _make_capture_calf(self, j: int, flankers: np.ndarray, min_dist: float) -> dict:
        """Procedencia de una captura de TERNERO (su defensora + flanqueadores)."""
        return {
            "step": self.step_count, "kind": "calf", "prey_idx": int(j),
            "defender_idx": int(self.calf_defender[j]),
            "n_flankers": int(len(flankers)), "flankers": [int(x) for x in flankers],
            "is_pack_prey": bool(self.pack_prey_kind == "calf" and self.pack_prey == j),
            "min_wolf_dist": float(min_dist),
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
        # Flanqueador VÁLIDO = dentro de capture_radius de la PRESA y fuera del cono (de la defensora
        # si es ternero, de la propia adulta si no). Quórum = 1 para ternero, n_min_adult para adulta.
        prey_pos = self._prey_pos()
        cone_pos, f = self._prey_cone()
        dist = np.linalg.norm(self.wolves - prey_pos, axis=1)
        rel_cone = self.wolves - cone_pos
        cosphi = (rel_cone / np.maximum(np.linalg.norm(rel_cone, axis=1)[:, None], 1e-9)) @ f
        close = dist <= self.capture_radius
        out_cone = cosphi < np.cos(self.cone_half_angle)
        n_close = int(close.sum())
        n_flank = int((close & out_cone).sum())          # flanqueadores válidos (= regla de muerte)
        self._prey_close_count, self._prey_flanker_count = n_close, n_flank
        quorum_n = 1 if self.pack_prey_kind == "calf" else self.n_min_adult

        # Coordinación: nº de presas CAZABLES distintas atacadas a la vez (lobo a <= r_face_safe).
        parts = [self.cows[self.cow_alive & ~self.cow_safe]]
        if self.n_calves > 0:
            parts.append(self.calves[self.calf_alive & ~self.calf_safe])
        targets = np.vstack(parts)
        if targets.shape[0]:
            d_all = np.linalg.norm(targets[:, None, :] - self.wolves[None, :, :], axis=2)
            n_targets = int((d_all.min(axis=1) <= self.r_face_safe).sum())
            self.max_simul_targets = max(self.max_simul_targets, n_targets)
            self._simul_sum += n_targets
            self._simul_steps += 1

        # Primer instante de quórum: la muerte DEBERÍA dispararse aquí (se rellena 'killed' tras terminal).
        if n_flank >= quorum_n and self.flank_first_quorum is None:
            self.flank_first_quorum = {"step": self.step_count, "flankers": n_flank, "killed": None}

        # Desglose de 'toques' (algún lobo dentro de capture_radius) que NO son quórum.
        if n_close >= 1:
            n_front = int((close & ~out_cone).sum())     # tocó por el FRENTE (dentro del cono)
            if n_flank >= quorum_n:
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

    def _spawn_wolves_sector(self, n: int) -> np.ndarray:
        """Spawnea los n lobos AGRUPADOS en un mismo sector del perímetro (no cada uno en un punto
        aleatorio distinto): la manada llega junta y de una dirección. El sector se sortea por
        episodio (RNG sembrado) -> de paso aleatoriza la dirección de ataque (bandera #4).

        Ancla = rayo desde el centro del campo en un ángulo aleatorio, proyectado al borde de la
        parcela; los lobos se reparten en un cúmulo gaussiano (wolf_spawn_dispersion) alrededor."""
        center = np.array([self.W / 2.0, self.H / 2.0])
        self.wolf_spawn_angle = float(self.rng.uniform(0.0, 2 * np.pi))
        d = np.array([np.cos(self.wolf_spawn_angle), np.sin(self.wolf_spawn_angle)])
        # Escala del rayo hasta tocar el borde de la parcela (el menor de los dos cruces x/y).
        t = min((self.W / 2.0) / max(abs(d[0]), 1e-9), (self.H / 2.0) / max(abs(d[1]), 1e-9))
        anchor = center + d * t
        pts = anchor + self.rng.normal(0.0, self.wolf_spawn_dispersion, size=(n, 2))
        self._clip_to_parcel(pts)
        return pts

    def _random_perimeter_points(self, n: int) -> np.ndarray:
        """n puntos aleatorios sobre el perímetro de la parcela [0,W]x[0,H]. (Conservado como utilidad;
        el spawn de lobos usa ahora _spawn_wolves_sector, agrupado por sector.)"""
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
        Incluye mirada de las vacas, terneros y la presa fijada (el render solo LEE)."""
        prey_pos = self._prey_pos()
        if prey_pos is not None:
            cone_pos, fvec = self._prey_cone()
            prey_pos = prey_pos.copy()
            cone_pos = cone_pos.copy()
            cone_head = float(np.arctan2(fvec[1], fvec[0]))
        else:
            cone_pos = cone_head = None
        return {
            "step": self.step_count,
            "t": self.step_count * self.dt,
            "cows": self.cows.copy(),
            "cow_heading": self.cow_heading.copy(),
            "cow_safe": self.cow_safe.copy(),
            "cow_alive": self.cow_alive.copy(),
            "calves": self.calves.copy(),
            "calf_defender": self.calf_defender.copy(),
            "calf_safe": self.calf_safe.copy(),
            "calf_alive": self.calf_alive.copy(),
            "wolves": self.wolves.copy(),
            "drones": self.drones.copy(),
            "prey_pos": prey_pos,                # posición de la presa fijada (realce), o None
            "prey_cone_pos": cone_pos,           # centro del cono que la defiende (para colorear lobos)
            "prey_cone_head": cone_head,
            "prey_is_calf": bool(self.pack_prey_kind == "calf"),
            "phase": self.phase,                 # VIGILANCIA / ESCOLTA
            "n_safe": int(self.cow_safe.sum() + self.calf_safe.sum()),
            "n_depredadas": int(self.n_depredadas),
            "n_fuera": int((self.cow_alive & ~self.cow_safe).sum() + (self.calf_alive & ~self.calf_safe).sum()),
            "status": self.status,
        }
