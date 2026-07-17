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
# RELEVO REALISTA (con hand-off, sin teletransporte): la reserva vuela al puesto (INCOMING), el bajo
# lo cubre hasta que llega y hace hand-off, luego vuelve a cargar (RETURNING). STRANDED = bajo a ~0 antes
# de que llegue el relevo (se queda en el puesto, sin disuadir, hasta el hand-off). Ciclo:
# READY -> INCOMING -> ACTIVE -> RETURNING -> CHARGING -> READY  (STRANDED = fallo de ACTIVE bajo estrés).
ACTIVE, RETURNING, CHARGING, READY, INCOMING, STRANDED = 0, 1, 2, 3, 4, 5
DRONE_STATE_NAMES = {ACTIVE: "ACTIVE", RETURNING: "RETURNING", CHARGING: "CHARGING", READY: "READY",
                     INCOMING: "INCOMING", STRANDED: "STRANDED"}

# --- HUELLA DEL REBAÑO AL PASTAR (escala biológica ABSOLUTA, en metros; NO depende del campo) ---
# Par fácil de afinar por render: con un campo de 300 m el rebaño debe verse DISPERSO ("dar la cara,
# no apiñamiento"), no apelotonado. HERD_SPREAD = radio de la zona de pasto (valla blanda);
# HERD_SEPARATION = espacio personal entre vacas (~0.55 * HERD_SPREAD).
HERD_SPREAD = 40.0        # m (cow_spread)
HERD_SEPARATION = 22.0    # m (r_separation)

# --- DINÁMICA DE VUELO DEL DRON (constantes FÍSICAS absolutas en SI; cuadricóptero HOLONÓMICO: se
# mueve en cualquier dirección, sin restricción de morro). Pareja afinable rapidez/aceleración de
# crucero-aproximación de un dron de vigilancia. ---
DRONE_MAX_SPEED = 15.0    # m/s (~54 km/h)
DRONE_MAX_ACCEL = 4.0     # m/s^2
# Coste de batería por MOVERSE (flag #7, "pursuit cost"): el drenaje en ACTIVE = base de flote
# multiplicada por (1 + DRONE_MOVE_DRAIN * v/vmax). Flotar = SUELO de consumo; reposicionarse a tope
# gasta (1+DRONE_MOVE_DRAIN)x -> perseguir/sobre-comprometer drones tiene coste táctico real. Afinable.
DRONE_MOVE_DRAIN = 1.5

# --- SUSTO POR MOVIMIENTO (scare, v2.4; sustituye al susto "campo de fuerza" de v2.3): respuesta del LOBO a un
# dron ACTIVE cercano según SI EL DRON SE LE ECHA ENCIMA (no solo la distancia). Los depredadores se HABITÚAN a
# disuasores ESTÁTICOS; lo que asusta es algo lanzándose hacia ti. Es CÓMO responde el mundo al dron
# (infraestructura), NO el coordinador (dónde está el dron lo deciden el reflejo/Dummy/coordinador). Para cada
# lobo se mira la VELOCIDAD DE APROXIMACIÓN de cada dron ACTIVE a tiro (<= SCARE_RADIUS) = componente de la
# velocidad del dron hacia el lobo:
#   · Dron ACERCÁNDOSE (aproximación > SCARE_APPROACH_MIN): EXPULSIÓN PLENA (mecanismo v2.3) -> el lobo HUYE
#     RADIAL alejándose, módulo CRECIENTE al acercarse el dron, acotado [SCARE_SPEED_MIN, wolf_speed]; la huida
#     SUSTITUYE a la caza y NO mata mientras huye (marcado _wolf_scared). Si varios drones se acercan, manda el
#     acercándose MÁS CERCANO (desempate determinista por índice). SIN excepción a corta.
#   · Dron ESTÁTICO o alejándose: miedo REDUCIDO, NO cero -> el lobo SIGUE cazando (no abandona su intención),
#     pero EVITA incrustarse en el dron parado: repulsión SUAVE de esquiva dentro de SCARE_STATIC_RADIUS (un poste,
#     no una amenaza; renormalizada a la rapidez de caza -> solo REDIRIGE, no la anula). NO marca _wolf_scared (mata).
# Efecto de diseño: el Dummy (drones clavados = postes) pierde casi toda su disuasión; defender bien pasa a exigir
# MOVERSE con intención (lo que el futuro MARL deberá aprender). Expulsado != rendido: al frenar/alejarse el dron
# el lobo retoma la caza (sin cooldown). Solo ACTIVE asustan; gateado por escort_enabled (combate puro NO aplica ->
# face_check bit a bit). Afinable por render; MEDIDA, no objetivo (no tunear SCARE_* para perseguir cifras).
DETER_RADIUS = 20.0        # m: radio de SUSTO (= SCARE_RADIUS; nombre conservado porque render/coordinators lo
                           #    importan). El lobo es AUDAZ -> solo reacciona de CERCA. EJE DE SENSIBILIDAD CLAVE.
SCARE_APPROACH_MIN = 1.0   # m/s: velocidad de aproximación del dron a partir de la cual EXPULSA (por debajo = poste). TUNE
SCARE_SPEED_MIN = 0.8      # m/s: módulo MÍNIMO de la huida al expulsar (nunca v~0 -> sin "cuadro congelado" lobo-vaca-dron).
SCARE_STATIC_RADIUS = 6.0  # m: radio de ESQUIVA de un dron estático/alejándose (obstáculo; el lobo lo rodea y SIGUE cazando). TUNE
SCARE_STATIC_GAIN = 1.0    # peso de la esquiva suave del obstáculo (se suma al rumbo de caza y se renormaliza; no acelera). TUNE

# --- RATIO CARGA:VUELO (v2.4): cargar recupera CHARGE_TO_FLIGHT_RATIO veces lo que el vuelo PLENO gasta. El
# drenaje a vuelo pleno (ACTIVE moviéndose a tope) = drain_rate_active·(1+DRONE_MOVE_DRAIN); la carga se DERIVA
# de ahí -> charge_rate = ratio·drenaje_pleno, y el tiempo de carga completa = 1/charge_rate. Con battery_capacity
# =600 s y DRONE_MOVE_DRAIN=1.5: drenaje pleno = 2.5/600/s, carga = 3.75/600/s -> ~160 s a full (recupera 1.5x lo
# que gasta volando a tope). Reemplaza el charge_full FIJO (300 s) de v2.3 -> el param charge_full pasa a DEPRECATED.
CHARGE_TO_FLIGHT_RATIO = 1.5

# --- EVITACIÓN de lobos al HUIR (ESCOLTA): una vaca NO-fijada que huye al establo RODEA a los lobos en vez
# de atravesar la pelea (una vaca real da un rodeo). El rumbo objetivo MEZCLA "hacia el establo" (DOMINA el
# neto -> sigue progresando) + "alejándose de los lobos cercanos" (con falloff lineal). Con el movimiento
# NO-HOLONÓMICO (avanza siempre de frente a cow_speed, gira a turn_rate) la mezcla produce un rodeo (arquea
# alrededor del lobo). SOLO el modo HUIR; la PRESA fijada (y su defensora si es ternero) sigue en ENCARAR
# (parada, de cara) -> no esquiva. No toca combate/pastoreo (escort_enabled=False). Afinables. ---
COW_AVOID_RADIUS = 30.0   # m: radio en que una vaca que huye percibe/evita a un lobo (~1.5*r_notice). TUNE
W_REFUGIO = 1.0           # peso del rumbo HACIA el establo (domina el neto: sigue llegando). TUNE
W_EVITAR = 1.3            # peso de la EVITACIÓN de lobos (rodeo; falloff lineal con la distancia). TUNE

# --- BORDEO de las ZONAS PROHIBIDAS (refugio/central) por el LOBO: un lobo que persigue HACIA una zona (su
# presa se refugió, o su objetivo está al otro lado) se quedaba CLAVADO en el borde: la persecución apunta
# DENTRO y el clamp (_push_outside_circle) lo frena de frente -> fuerza neta ~0 (mismo ATASCO RADIAL que con
# el dron). Cerca de la frontera, una componente TANGENCIAL hace que el lobo ARQUEE alrededor de la zona (por
# FUERA: no entra, el clamp sigue) para alcanzar objetivos al otro lado, en vez de empujar de frente. Análogo
# al bordeo del dron y del rebaño. Gateado por escort_enabled (en combate la presa no se refugia -> NO aplica
# -> face_check bit a bit). Afinables por render. ---
WOLF_ZONE_SKIRT_BAND = 20.0   # m: banda FUERA de la frontera donde actúa el bordeo (reacciona cerca del borde). TUNE
WOLF_ZONE_SKIRT_GAIN = 3.0    # peso del bordeo tangencial (relativo al impulso de caza); domina cerca del borde. TUNE

# --- SPAWN EN SUBGRUPOS (v2.5, Nivel A): con wolf_spawn_mode="grouped" la manada puede nacer PARTIDA en
# subgrupos de tamaño DESIGUAL en sectores DISTINTOS del perímetro (misma distancia de spawn: el borde), en vez
# de apilada en uno solo. Hipótesis a medir: multi-frente -> un subgrupo hace de CEBO mientras otro mata por
# otro lado -> la barrera única del Reactive deja de bastar. El sorteo (nº de grupos, reparto, sector del 2º
# grupo) va ÍNTEGRO en un substream RNG separado (_wolf_group_rng, seed+3_000_003) -> NO consume del stream
# principal -> spawns de vacas/drones/corzos bit a bit; con 1 grupo las posiciones son EXACTAMENTE las del modo
# "clustered" (el sorteo solo decide si se PARTE el cúmulo ya spawneado). "clustered" (default) = v2.4.1 bit a
# bit. El modo lo fija CONFIG_V2 (v2.5 mide con "grouped"). ---
WOLF_GROUP_MIN_ANGLE_SEP = np.pi / 3   # rad: separación angular MÍNIMA entre sectores de subgrupos (>=60°). TUNE

# --- CORZOS (cuerpos NO-amenaza, 3c): cuerpos de fondo que el coordinador deberá aprender a NO investigar a
# fondo (discriminar amenaza). DEAMBULAN (wander lento) y HUYEN de lobos y drones ACTIVE cercanos (repulsión con
# falloff); NO cazan, NO van al rebaño, NO atacan; las vacas NO los encaran (no son amenaza -> no disparan
# r_notice). Detectables como CONTACTOS (r_detect) -> disparan el reflejo de investigación IGUAL que un lobo; el
# TIPO se revela por ORÁCULO a r_confirm (stand-in determinista de YOLO): lobo -> ESCOLTA, corzo -> el dron se
# desengancha (DESCARTA, NO escolta). OFF por defecto (corzos_max=0 -> mundo actual bit a bit, cero draws RNG);
# se activan con corzos_max>0 -> 3 tipos de episodio (~1/3 solo-lobos / solo-corzos / mixto). Afinables. ---
CORZO_FLEE_RADIUS = 30.0  # m: radio en que el corzo percibe/HUYE de un lobo o un dron ACTIVE (esquivo). TUNE
CORZO_FLEE_GAIN = 3.0     # peso de la huida (repulsión) frente al deambular (domina cuando hay amenaza cerca). TUNE
# Los corzos forman GRUPOS pequeños: spawnean AGRUPADOS (un centroide + dispersión pequeña) DENTRO de la banda
# de detección del rebaño (entre un radio interior —fuera del rebaño— y r_detect, para que disparen SOSPECHA la
# mayoría de las veces) y se mantienen juntos con una cohesión SUAVE al centroide del grupo (+ separación para no
# apilarse). Spawn sembrado; banda derivada (cow_spread/r_notice/r_detect), sin números mágicos. Afinables.
CORZO_GROUP_DISPERSION = 6.0  # m: cúmulo de spawn del grupo de corzos (salen JUNTOS, no esparcidos). TUNE
CORZO_COHESION = 0.05        # cohesión suave hacia el centroide del grupo (se mantienen juntos al deambular). TUNE
CORZO_SEPARATION = 4.0       # m: separación entre corzos (no se apilan; juntos pero "sin pegarse"). TUNE


class World:
    def __init__(
        self,
        n_active_drones: int = 4,
        n_reserve_drones: int = 4,
        n_cows: int = 6,
        wolves_min: int = 1,            # nº de lobos sorteado en reset() ...
        wolves_max: int = 5,            # ... entre [wolves_min, wolves_max]
        # --- Corzos (3c, cuerpos NO-amenaza): OFF por defecto (corzos_max=0 -> mundo actual bit a bit). Con
        #     corzos_max>0 se activan 3 tipos de episodio (~1/3 cada uno). Ver constantes CORZO_* en cabecera. ---
        corzos_min: int = 1,            # nº de corzos sorteado entre [corzos_min, corzos_max] cuando el episodio los tiene
        corzos_max: int = 0,            # 0 = SIN corzos (y sin sorteo de tipo de episodio) -> mundo actual intacto
        corzo_speed: float = 4.0,       # m/s del corzo (esquivo, escapa); etiquetado/afinable. TUNE
        corzo_episode_probs: tuple[float, float, float] = (1/3, 1/3, 1/3),  # P(solo-lobos / solo-corzos / mixto) si corzos_max>0
        distraction_species_prob: float = 0.5,  # P(la distracción sea CORZO); 1-p = JABALÍ. La MISMA prob de que haya distracción;
                                                 #   solo cambia la especie (corzo/jabalí, mismo comportamiento). Substream RNG SEPARADO -> no perturba spawns.
        episode_kind: str | None = None,  # fuerza el tipo ('lobos'/'corzos'/'mixto') en vez de sortear (tests deterministas)
        parcel_size: tuple[float, float] = (300.0, 300.0),   # ~9 ha (parcela realista); r_detect=100 m -> 1/3 del campo
        safe_radius: float | None = None,     # establo (centro del campo)
        station_radius: float | None = None,  # estación central de carga
        station_gap: float | None = None,     # separación establo<->estación
        station_dir: tuple[float, float] = (0.0, 1.0),  # dirección estación respecto al establo
        cow_spawn: tuple[float, float] | None = None,   # punto de aparición del rebaño (esquina)
        cow_spread: float | None = None,      # radio del área de pasto
        dt: float = 0.1,
        max_steps: int = 600,
        drone_speed: float = 6.0,     # DEPRECATED: la dinámica de vuelo usa DRONE_MAX_SPEED/ACCEL; se ACEPTA pero NO se usa
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
        calf_speed: float = 0.8,           # m/s: rapidez de huida del ternero (< cow_speed: la cría es más lenta).
                                           #   En ESCOLTA la madre NO la adelanta (huye a este ritmo). TUNE
        k_calf_cohesion: float = 1.0,      # cohesión ternero->defensora (se pega a la madre). TUNE
        k_defender_anchor: float = 0.6,    # cohesión defensora->su ternero (se queda con la cría). TUNE
        calf_personal_space: float | None = None,  # m: separación ternero<->defensora (AL LADO, no encima; default 0.5*capture_radius). TUNE
        # --- Lobo (reutilizado, ahora DIRECCIONAL): cono frontal + flanqueo + nº mínimo ---
        wolf_speed: float = 4.0,                       # m/s del lobo
        wolf_repulsion_radius: float | None = None,    # reparto angular de la manada (pincer; default 2*r_face_safe)
        wolf_repulsion_strength: float = 1.0,          # peso de la repulsión entre lobos
        wolf_spawn_dispersion: float | None = None,    # m: dispersión del cúmulo de spawn (salen JUNTOS de un sector; default 0.05*min). TUNE
        wolf_spawn_mode: str = "clustered",            # "clustered" (v2.4.1, un solo cúmulo) | "grouped" (v2.5: 1-2 subgrupos desiguales en sectores distintos; substream propio). El default se queda en clustered (checks bit a bit); CONFIG_V2 pide grouped.
        wolf_skirt_gain: float = 1.5,                  # ganancia de la componente TANGENCIAL para BORDEAR el rebaño (no atravesarlo). TUNE
        wolf_skirt_margin: float | None = None,        # m: holgura sobre la extensión del rebaño-obstáculo (default = r_face_safe). TUNE
        wolf_envelop_gain: float = 3.0,                # ATAQUE ENVOLVENTE: reparte los rumbos del paquete en ángulos equiespaciados alrededor de la presa (N→2π/N) -> no se apiñan en el cono. TUNE
        n_min_adult: int = 2,              # nº mínimo de lobos para tumbar a una adulta. TUNE
        r_standoff: float | None = None,   # m: standoff AMPLIO del lobo solo (default 2*r_face_safe). TUNE
        prey_abandon_dist: float | None = None,  # DEPRECATED: abandono por distancia. La presa se fija en t=0 y solo se suelta si se refugia; se ACEPTA pero NO se usa.
        cone_band: float = 0.12,           # rad: banda muerta del cono (anti entra-sale-entra). TUNE
        wolf_inertia: float = 0.35,        # suavizado de velocidad del lobo. TUNE
        capture_radius: float | None = None,  # m, a qué distancia (un flanqueador) puede tumbar (default 0.03*min)
        teleport_guard: bool = False,      # log si una entidad se desplaza > su máx por paso * motion_tol
        motion_tol: float = 1.5,           # tolerancia de desplazamiento por paso (guardia)
        # --- Escolta / terminal del episodio (máquina de fases VIGILANCIA->ESCOLTA + refugio) ---
        r_detect: float = 100.0,                 # m: DETECCIÓN ("hay algo") de un dron en vuelo -> SOSPECHA. TUNE
        r_confirm: float = 40.0,                 # m: CONFIRMACIÓN ("es un lobo") tras acercarse -> ESCOLTA. TUNE
        episode_time_factor: float = 4.0,        # holgura del límite de tiempo (~k * diag / cow_speed). TUNE
        max_episode_steps: int | None = None,    # límite de pasos (default DERIVADO de geometría/cow_speed; ver __init__)
        refuge_margin: float | None = None,      # m: histéresis de borde del establo para contar "refugiada" (default 0.1*safe_radius). TUNE
        escort_enabled: bool = True,             # subsistema de escolta (máquina de fases + guiado al refugio). False = adversario PURO (face_check: combate sin escolta)
        # --- DEPRECATED: modelo anterior (apiñamiento + Muro-pounce). Se ACEPTAN para no romper
        #     baseline.py v1 (los pasa explícitos) pero se IGNORAN en la dinámica nueva. ---
        k_cohesion_calm: float = 0.0, k_cohesion_panic: float = 0.0, wander_panic: float = 0.0,
        r_alarm: float | None = None, r_calm: float | None = None, r_fear: float | None = None,
        d_safe: float | None = None, wolf_speed_near: float | None = None,
        wolf_engage_band: float | None = None, iso_sustain_steps: int = 0,
        pounce_margin: float = 0.0, pounce_factor: float = 0.0, wolf_pounce_isolation: float | None = None,
        # --- Batería y cola de carga (operación continua; ver battery_check.py) ---
        battery_capacity: float = 600.0,   # s de vuelo a plena carga (batería ~10 min)
        charge_full: float = 300.0,        # DEPRECATED (v2.4): la carga se DERIVA de CHARGE_TO_FLIGHT_RATIO (~160 s); se ACEPTA pero NO se usa
        battery_init_min: float = 0.25,    # v2.4: batería inicial aleatoria de los ACTIVE en [battery_init_min, 1] (> announce_threshold -> sin relevos en t=0). TUNE
        announce_threshold: float = 0.20,  # fracción de batería a la que se pide relevo. TUNE
        charge_capacity: int | None = None,  # puestos de carga en paralelo (default = nº de reserva)
        relay_handoff_tol: float = 2.0,    # m: el relevo debe estar ESTO cerca del bajo para el hand-off (sin teletransporte). TUNE
        # --- Cerebro ENCHUFABLE de los lobos (política de movimiento; ver wolf_controllers.py). El default
        #     'scripted' es el comportamiento v2.4 BIT A BIT. El mundo consume el controlador en _update_wolves;
        #     'learned' quedará para la fase RL (lobos que burlan la barrera). Análogo al coordinador de drones. ---
        wolf_policy: str = "scripted",     # 'scripted' (default) | 'learned' (pendiente RL)
        wolf_controller=None,              # inyección directa de una instancia WolfController (precede a wolf_policy; para el RL)
        seed: int | None = None,
    ):
        # --- configuración (inmutable durante el episodio) ---
        self.n_active = n_active_drones
        self.n_reserve = n_reserve_drones
        self.n_drones = n_active_drones + n_reserve_drones
        self.n_cows = n_cows
        self.wolves_min = wolves_min
        self.wolves_max = wolves_max
        # Corzos (3c): OFF si corzos_max=0 (mundo actual). Las probs de tipo de episodio se normalizan.
        self.corzos_min = corzos_min
        self.corzos_max = corzos_max
        self.corzo_speed = corzo_speed
        self.corzo_episode_probs = np.asarray(corzo_episode_probs, dtype=float)
        self.corzo_episode_probs = self.corzo_episode_probs / self.corzo_episode_probs.sum()
        self.distraction_species_prob = float(distraction_species_prob)   # P(corzo); 1-p = jabalí
        self._episode_kind_forced = episode_kind
        self.episode_kind = "lobos"      # se fija en reset() (sorteo o forzado); default sin corzos
        self.distraction_species = "corzo"  # 'corzo' / 'jabali': especie de la distracción este episodio (se fija en reset)
        self.W, self.H = parcel_size
        m = min(self.W, self.H)  # escala de LAYOUT (establo/central/spawn/perímetro derivan de m y SÍ escalan)

        # ESCALA BIOLÓGICA = ABSOLUTA (en metros, NO escala con el campo). Si dependiera de m, agrandar
        # el campo desparramaría el rebaño y el cúmulo de spawn, y agrandaría el alcance del lobo. Estos
        # valores son los que tenía el modelo a min(W,H)=100 (calibrado allí) y se FIJAN: extensión del
        # rebaño (cow_spread, r_separation), cúmulo de spawn de lobos (wolf_spawn_dispersion), y radios
        # de COMBATE/percepción del animal (r_notice, r_face_safe, capture_radius) -> el lobo es un lobo
        # a cualquier tamaño de parcela.

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
        self.cow_spread = cow_spread if cow_spread is not None else HERD_SPREAD  # m ABSOLUTOS: zona de pasto (no escala)

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
        self.r_separation = r_separation if r_separation is not None else HERD_SEPARATION  # m ABSOLUTOS (~0.55*cow_spread)
        self.wander_calm = wander_calm
        self.wander_drift = wander_drift
        self.k_fence = k_fence
        # Confrontación: encara al lobo dentro de r_notice; lo mantiene a r_face_safe si cae en
        # el cono frontal (±cone_half_angle); gira a turn_rate; tras encarar, face_cooldown antes
        # de cambiar de objetivo (la ventana que la manada explota por el flanco).
        self.r_notice = r_notice if r_notice is not None else 20.0     # m ABSOLUTOS: percepción del animal (no escala)
        self.cone_half_angle = cone_half_angle
        self.r_face_safe = r_face_safe if r_face_safe is not None else 6.0   # m ABSOLUTOS: standoff frontal (no escala)
        self.face_cooldown = face_cooldown
        self.turn_rate = turn_rate
        self.cow_inertia = cow_inertia

        # --- Terneros + defensoras ---
        self.calf_count_probs = np.asarray(calf_count_probs, dtype=float)
        self.calf_count_probs = self.calf_count_probs / self.calf_count_probs.sum()  # normaliza
        self.calf_speed = calf_speed
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
        self.wolf_spawn_dispersion = wolf_spawn_dispersion if wolf_spawn_dispersion is not None else 5.0  # m ABSOLUTOS (cúmulo apretado)
        if wolf_spawn_mode not in ("clustered", "grouped"):
            raise ValueError("wolf_spawn_mode debe ser 'clustered' o 'grouped'; recibido %r" % (wolf_spawn_mode,))
        self.wolf_spawn_mode = wolf_spawn_mode         # v2.5: "grouped" = subgrupos (ver _split_wolves_groups)
        self.wolf_skirt_gain = wolf_skirt_gain
        self.wolf_envelop_gain = wolf_envelop_gain
        self.wolf_skirt_margin = wolf_skirt_margin if wolf_skirt_margin is not None else self.r_face_safe

        # capture_radius = a qué distancia un FLANQUEADOR puede tumbar (no mata de pasada: hace
        # falta n_min_adult flanqueadores a la vez fuera del cono). ABSOLUTO (alcance de mordida, no escala).
        self.capture_radius = capture_radius if capture_radius is not None else 3.0   # m ABSOLUTOS
        # El ternero se coloca AL LADO de la defensora (no superpuesto): se pega a un anillo a esta
        # distancia, no a su posición exacta. Atado a la geometría (media capture_radius ~1.5 m).
        self.calf_personal_space = (
            calf_personal_space if calf_personal_space is not None else 0.5 * self.capture_radius
        )
        self.teleport_guard = teleport_guard
        self.motion_tol = motion_tol

        # --- Escolta / terminal del episodio ---
        # Disparador en DOS etapas (DETECCIÓN -> acercarse -> CONFIRMACIÓN): un dron EN VUELO (ACTIVE)
        # DETECTA "hay algo" a <= r_detect (VIGILANCIA->SOSPECHA), investiga acercándose, y CONFIRMA
        # "es un lobo" a <= r_confirm (SOSPECHA->ESCOLTA). Distancia horizontal 2D.
        #   r_detect=100 m: criterio DRI de Johnson a nivel DETECTAR (~8-13 px sobre un lobo de ~1,2 m),
        #   GSD ~1,2 cm/px a ~52 m AGL, patrulla ~40-50 m, margen oblicuo/movimiento -> ~80-120 m.
        #   r_confirm=40 m: nivel IDENTIFICAR-especie (~100-300 px/animal); a ~1,2 cm/px un lobo de ~1,2 m
        #   da ~130 px a 40 m. La confirmación es GEOMÉTRICA y determinista (no hay clasificador: como en
        #   el mundo solo hay lobos, siempre confirma "sí"); la percepción imperfecta es la fase YOLO.
        # Ambos son placeholders limpios hasta YOLO. Horizontal porque la z aún es conceptual (flag #2).
        self.r_detect = r_detect
        self.r_confirm = r_confirm
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
        # Subsistema de escolta: máquina de fases (VIGILANCIA->SOSPECHA->ESCOLTA) + GUIADO al refugio
        # (collares que conducen el rebaño al establo en ESCOLTA). Es INFRAESTRUCTURA del mundo, igual
        # para todos los coordinadores (no es el coordinador). escort_enabled=False lo apaga por completo
        # (la fase se queda en VIGILANCIA -> el guiado nunca dispara): el mundo es el adversario PURO
        # (face_check prueba ahí el COMBATE, invariante de fase). main/escort_check lo dejan en True.
        self.escort_enabled = escort_enabled

        # Batería: tasas DERIVADAS (sin números mágicos). La batería es una fracción [0,1]; drena 1->0 en
        # battery_capacity s a flote. CARGA DERIVADA DEL RATIO (v2.4): recupera CHARGE_TO_FLIGHT_RATIO veces
        # el drenaje a VUELO PLENO (drain_rate_active·(1+DRONE_MOVE_DRAIN)) -> tiempo de carga completa =
        # 1/charge_rate (~160 s a los defaults). El param charge_full queda DEPRECATED (ignorado).
        self.battery_capacity = battery_capacity
        self.drain_rate_active = 1.0 / battery_capacity   # fracción por segundo (patrulla/flote)
        flight_full_drain = self.drain_rate_active * (1.0 + DRONE_MOVE_DRAIN)   # drenaje a vuelo pleno
        self.charge_rate = CHARGE_TO_FLIGHT_RATIO * flight_full_drain           # carga = 1.5x el vuelo pleno
        self.charge_full = 1.0 / self.charge_rate         # tiempo de carga completa RESUELTO (~160 s)
        self.battery_init_min = battery_init_min          # batería inicial aleatoria de los ACTIVE en [este, 1]
        self.announce_threshold = announce_threshold
        self.charge_capacity = (
            charge_capacity if charge_capacity is not None else self.n_drones - self.n_active
        )
        # RELEVO REALISTA: el tiempo de vuelo del relevo ya NO es un hook fijo -> EMERGE de la dinámica de
        # vuelo (DRONE_MAX_SPEED y la distancia central<->puesto). Solo queda como param la tolerancia de
        # hand-off ("estar encima" del bajo para relevarlo).
        self.relay_handoff_tol = relay_handoff_tol

        # Cerebro ENCHUFABLE de los lobos: instancia inyectada, o construida por política (default scripted =
        # v2.4 bit a bit). Import PEREZOSO (wolf_controllers importa `world` para las constantes de bordeo de
        # zona -> se evita el ciclo importándolo aquí, ya cargado el módulo). No consume RNG (bit a bit).
        if wolf_controller is not None:
            self.wolf_controller = wolf_controller
        else:
            from wolf_controllers import make_wolf_controller
            self.wolf_controller = make_wolf_controller(wolf_policy)
        self.wolf_policy = wolf_policy

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
        # Corzos (3c, cuerpos NO-amenaza): deambulan + huyen de lobos/drones; descartados por el oráculo a r_confirm.
        self.n_corzos: int = 0                       # nº de corzos este episodio (0 si no los hay, RNG)
        self.corzos: np.ndarray | None = None        # (n_corzos,2) posición
        self.corzo_vel: np.ndarray | None = None     # (n_corzos,2) velocidad (inercia)
        self._corzo_graze_dir: np.ndarray | None = None  # (n_corzos,) deambular leve
        self.corzo_dismissed: np.ndarray | None = None   # (n_corzos,) bool: ya confirmado NO-amenaza -> no se reinvestiga
        self._distraction_rng = None                     # substream RNG SEPARADO para el tipo de distracción (corzo/jabalí): NO perturba spawns
        self._battery_rng = None                         # substream RNG SEPARADO (v2.4) para las baterías iniciales: NO perturba spawns (face_check bit a bit) de lobo/vaca
        self.drones: np.ndarray | None = None
        self.drone_vel: np.ndarray | None = None        # (n_drones,2) velocidad (dinámica de vuelo, flag #1 para drones)
        self.drone_waypoint: np.ndarray | None = None   # (n_drones,2) destino comandado (command_waypoint); hold = posición
        self.drone_investigating: np.ndarray | None = None  # (n_drones,) ¿en estado INVESTIGANDO? (reflejo manda sobre él)
        self.drone_contact: np.ndarray | None = None    # (n_drones,2) posición del contacto que investiga (NaN si no)
        self.drone_home: np.ndarray | None = None       # (n_drones,2) waypoint/puesto previo a investigar (vuelve ahí si descarta un corzo)
        self.investigations: list = []                  # mensaje al coordinador: investigaciones activas {id, contacto, estado}
        self.battery: np.ndarray | None = None          # (n_drones,) fracción [0,1]
        self.drone_state: np.ndarray | None = None      # (n_drones,) ACTIVE/RETURNING/CHARGING/READY
        self.battery_activity: np.ndarray | None = None # (n_drones,) HOOK persecución (bandera #7): multiplica el drenaje
        self.drone_stranded: np.ndarray | None = None   # (n_drones,) "dron tirado": ACTIVE que llega a ~0 esperando relevo
        self.drone_relief_hold: np.ndarray | None = None # (n_drones,) ACTIVE que se clava en su puesto esperando/recibiendo relevo (el coordinador NO lo comanda)
        self.relief_target: np.ndarray | None = None     # (n_drones,) para un INCOMING: índice del dron bajo que va a relevar (-1 si no)
        self._wolf_attacking: bool = False              # ¿la manada flanquea de verdad este paso? (instrumentación)
        self.pack_prey: int = -1                        # índice de la presa COMÚN fijada (-1 = ninguna)
        self.pack_prey_kind: str | None = None          # "adult" | "calf" | None (a qué array indexa pack_prey)
        self._ever_committed: bool = False              # ¿se fijó ya alguna presa este episodio?
        self.n_refix: int = 0                           # re-fijaciones de presa (tras matar/refugiarse la presa)
        self.max_simul_targets: int = 0                 # máx nº de vacas atacadas a la vez (coordinación; ~1 ideal)
        self._simul_sum: int = 0                        # acumulador para la media de vacas atacadas a la vez
        self._simul_steps: int = 0
        self.flank_first_quorum: dict | None = None     # primer quórum de flanqueadores {step, flankers, killed}
        self.touch_breakdown: dict | None = None        # desglose de 'toques' que NO matan (diagnóstico de #3)
        self._prey_close_count: int = 0                 # lobos dentro de capture_radius de la presa (este paso)
        self._prey_flanker_count: int = 0               # de ésos, flanqueadores válidos (fuera del cono)
        self._wolf_scared: np.ndarray | None = None     # (nw,) lobos que HUYEN de un dron que EMBISTE (susto por movimiento; no matan)
        self._drone_scaring: np.ndarray | None = None   # (nd,) drones ACTIVE que se acercan a algún lobo a tiro (para el 🔊 del render)
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
        # Substream INDEPENDIENTE (seed desplazado) para el tipo de distracción (corzo/jabalí): sortear la especie
        # NO consume del stream principal -> los spawns de lobos/vacas/corzos quedan bit a bit iguales (baseline comparable).
        self._distraction_rng = np.random.default_rng(None if self._seed is None else self._seed + 1_000_003)
        # Substream INDEPENDIENTE (v2.4) para las baterías iniciales aleatorias: NO consume del stream principal ->
        # los spawns quedan bit a bit iguales (face_check 12/12). Offset distinto del de distracción.
        self._battery_rng = np.random.default_rng(None if self._seed is None else self._seed + 2_000_003)
        # Substream INDEPENDIENTE (v2.5) para el sorteo de SUBGRUPOS de lobos (nº de grupos, reparto, sector del
        # 2º grupo): NO consume del stream principal -> vacas/drones/corzos bit a bit iguales que en "clustered"
        # (y con 1 grupo, también los lobos). Offset propio, distinto de los otros dos.
        self._wolf_group_rng = np.random.default_rng(None if self._seed is None else self._seed + 3_000_003)

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

        # Drones de reserva: en ROMBO (4 vértices) dentro de la central. Determinista (no consume RNG ->
        # spawns bit a bit); solo cambia la POSICIÓN de partida de las reservas (lo recoge la re-medición v2.3).
        scx, scy, sr = self.central_station
        half = 0.7 * sr  # radio del rombo (margen para no salirse de la región central)
        ang = np.pi / 2 - 2 * np.pi * np.arange(self.n_reserve) / max(self.n_reserve, 1)  # arriba, sentido horario
        reserve = np.column_stack([scx + half * np.cos(ang), scy + half * np.sin(ang)])
        self.drones = np.vstack([active, reserve])  # filas [0:n_active] activos, resto reserva
        self.drone_vel = np.zeros((self.n_drones, 2))      # parados al inicio
        self.drone_waypoint = self.drones.copy()           # destino = posición actual (mantener/hold)
        self.drone_home = self.drones.copy()               # puesto al que vuelve tras descartar un corzo
        self.drone_investigating = np.zeros(self.n_drones, dtype=bool)
        self.drone_contact = np.full((self.n_drones, 2), np.nan)
        self.investigations = []

        # Tipo de episodio (3c): solo-lobos / solo-corzos / mixto. SOLO si los corzos están activos
        # (corzos_max>0) y en escenario de escolta; si no, "lobos" SIN sortear (cero draws RNG -> mundo actual
        # bit a bit). Se hace ANTES del sorteo del nº de lobos para poder anularlos en "corzos".
        self._roll_episode_kind()

        # Lobos: nº aleatorio por episodio; TODOS salen AGRUPADOS de un mismo sector del perímetro
        # (sector sorteado por episodio) -> la manada llega junta y de una dirección (y se aleatoriza
        # la dirección de ataque entre episodios, bandera #4). En "solo-corzos" no hay lobos (el sorteo del
        # nº se mantiene para no desalinear el RNG en los mundos con corzos; se descarta).
        n_wolves_roll = int(self.rng.integers(self.wolves_min, self.wolves_max + 1))
        self.n_wolves = 0 if self.episode_kind == "corzos" else n_wolves_roll
        self.wolves = self._spawn_wolves_sector(self.n_wolves)
        # Instrumentación del spawn (render/diagnóstico): tamaños y sectores de los subgrupos.
        self.wolf_group_sizes = [self.n_wolves] if self.n_wolves > 0 else []
        self.wolf_spawn_angles = [self.wolf_spawn_angle] if self.n_wolves > 0 else []
        if self.wolf_spawn_mode == "grouped":
            self.wolves = self._split_wolves_groups(self.wolves)   # v2.5: subgrupos (substream propio)
        self.wolf_vel = np.zeros((self.n_wolves, 2))
        self._wolf_scared = np.zeros(self.n_wolves, dtype=bool)   # (nw,) lobos que HUYEN de un dron este paso (susto por movimiento)
        self._drone_scaring = np.zeros(self.n_drones, dtype=bool) # (nd,) drones que 'ladran' (se acercan a un lobo a tiro) este paso

        # Corzos (3c): en "solo-corzos"/"mixto", nº aleatorio fuera de zonas y del rebaño. En "lobos" (incl.
        # corzos OFF) NO se toca el RNG -> mundo actual bit a bit.
        if self.episode_kind == "lobos":
            self.n_corzos = 0
            self.corzos = np.zeros((0, 2)); self.corzo_vel = np.zeros((0, 2))
            self._corzo_graze_dir = np.zeros(0); self.corzo_dismissed = np.zeros(0, dtype=bool)
            self.distraction_species = "corzo"      # sin distracción (no se usa)
        else:
            self.n_corzos = int(self.rng.integers(self.corzos_min, self.corzos_max + 1))
            self.corzos = self._spawn_corzos(self.n_corzos)
            self.n_corzos = self.corzos.shape[0]                 # por si el rechazo no llenó (guard)
            self.corzo_vel = np.zeros((self.n_corzos, 2))
            self._corzo_graze_dir = self.rng.uniform(0.0, 2 * np.pi, size=self.n_corzos)
            self.corzo_dismissed = np.zeros(self.n_corzos, dtype=bool)
            # Especie de la distracción (grupo entero): corzo o jabalí ~50/50 (mismo comportamiento). Del SUBSTREAM
            # separado -> no perturba el spawn. Un tipo MÁS para el oráculo; el dron descarta igual (no es lobo).
            self.distraction_species = "corzo" if self._distraction_rng.random() < self.distraction_species_prob else "jabali"

        # Batería al reset (v2.4): los n_active EN VUELO arrancan con batería ALEATORIA en [battery_init_min, 1]
        # (una flota real está a mitad de ciclo, no a tope); cada reserva EN CARGA es el ESPEJO de su pareja
        # (1 - bat_activo). Del SUBSTREAM separado -> spawns bit a bit. HOOK: _init_battery(stagger=...) sigue para
        # battery_check (régimen permanente en aislado).
        self._init_battery_episode()

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
            "phase": self.phase,
            # Mensaje del reflejo: investigaciones activas {drone_id, contact_pos, state}. El coordinador
            # podrá leerlo (cimiento de lo que observará); el DummyCoordinator lo ignora.
            "investigations": self._build_investigations(),
        }

    def _build_investigations(self) -> list:
        """Mensaje legible por el coordinador: una entrada por dron INVESTIGANDO {drone_id, contact_pos
        (lobo más cercano), state}. Se arma fresco -> correcto ya en el paso de detección."""
        msg = []
        for i in np.where(self.drone_investigating)[0]:
            if self.n_wolves > 0:
                cpos = self.wolves[int(np.argmin(np.linalg.norm(self.wolves - self.drones[i], axis=1)))].copy()
            else:
                cpos = self.drone_contact[i].copy()
            msg.append({"drone_id": int(i), "contact_pos": cpos, "state": "investigando"})
        self.investigations = msg
        return [dict(d) for d in msg]

    # ------------------------------------------------------------------ #
    # Step: una transición de la dinámica (firma estilo gym/PettingZoo)
    # ------------------------------------------------------------------ #
    def step(self, actions):
        """
        Avanza dt. `actions`: array (n_drones, 2) = WAYPOINT (x,y) por dron (destino); cada dron lo
        persigue con su dinámica de vuelo. Si es None, los drones mantienen su waypoint (el coordinador
        también puede comandar uno a uno con command_waypoint). Devuelve la 5-tupla estilo gym:
            (obs, reward, terminated, truncated, info)
        """
        self._prev_cows = self.cows.copy()   # para la guardia de teletransporte
        self._prev_wolves = self.wolves.copy()
        self._apply_drone_actions(actions)  # fase 1: control
        self._update_cows()                 # fase 2: pastar + encarar + inercia
        self._update_calves()               #         terneros pegados a su defensora
        self._update_wolves()               #         lobo direccional + flanqueo + inercia
        self._enforce_face_cones()          #         la vaca planta cara: empuja al lobo frontal a r_face_safe
        self._update_corzos()               #         corzos (3c): deambulan + huyen de lobos/drones (no-op si no hay)
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
    def command_waypoint(self, i: int, xy) -> None:
        """Interfaz limpia para el coordinador: ordena a UN dron volar a un waypoint (x,y). El dron lo
        persigue con su dinámica de vuelo (acelera, cruza, frena y se para). Persistente hasta otro
        comando. (El DummyCoordinator no comanda nada -> los drones MANTIENEN su waypoint = quietos.)"""
        self.drone_waypoint[i] = np.asarray(xy, dtype=float)

    def _apply_drone_actions(self, actions) -> None:
        """Control + dinámica de vuelo de los drones. PRECEDENCIA: el REFLEJO de investigación manda
        sobre el dron INVESTIGANDO (su waypoint = el contacto); el COORDINADOR comanda al resto. Luego
        vuelo HOLONÓMICO hacia el waypoint: velocidad deseada = ir a por él pudiendo FRENAR a tiempo
        (v_freno = sqrt(2*a*dist)), capada a DRONE_MAX_SPEED; se acelera a <= DRONE_MAX_ACCEL por paso ->
        acelera, cruza, frena y se para (sin overshoot sostenido). `actions` (waypoints n_drones,2) solo
        afecta a los drones NO investigando; None = mantener. Fija battery_activity por el esfuerzo (#7)."""
        if actions is not None:
            wp = np.asarray(actions, dtype=float).reshape(self.n_drones, 2)
            # PRECEDENCIA: el coordinador NO toca al INVESTIGADOR (reflejo) ni al dron CLAVADO esperando/recibiendo
            # relevo (drone_relief_hold: mantiene su puesto para el hand-off). El resto sí.
            free = ~self.drone_investigating & ~self.drone_relief_hold
            self.drone_waypoint[free] = wp[free]
        self._update_investigation_waypoint()             # reflejo: el investigador persigue su contacto

        to_wp = self.drone_waypoint - self.drones
        dist = np.linalg.norm(to_wp, axis=1, keepdims=True)
        direction = np.where(dist > 1e-9, to_wp / np.maximum(dist, 1e-9), 0.0)
        # Rapidez desde la que aún se frena a tiempo con DRONE_MAX_ACCEL -> garantiza parada sin overshoot.
        v_brake = np.sqrt(2.0 * DRONE_MAX_ACCEL * dist)
        desired_speed = np.minimum(DRONE_MAX_SPEED, v_brake)
        desired_vel = direction * desired_speed
        # Aceleración acotada por paso (DRONE_MAX_ACCEL): no salta de velocidad.
        dv = desired_vel - self.drone_vel
        dvn = np.linalg.norm(dv, axis=1, keepdims=True)
        dv *= np.minimum(1.0, (DRONE_MAX_ACCEL * self.dt) / np.maximum(dvn, 1e-9))
        self.drone_vel = self.drone_vel + dv
        self.drones = self.drones + self.drone_vel * self.dt
        self._clip_to_parcel(self.drones)

        # Coste de batería por moverse (flag #7): flote = suelo; crece con la rapidez (v/vmax).
        effort = np.minimum(np.linalg.norm(self.drone_vel, axis=1) / DRONE_MAX_SPEED, 1.0)
        self.battery_activity = 1.0 + DRONE_MOVE_DRAIN * effort

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
        self.drone_stranded = np.zeros(n, dtype=bool)   # ACTIVE tirado (batería a ~0 esperando relevo)
        self.drone_relief_hold = np.zeros(n, dtype=bool)  # ACTIVE clavado en su puesto esperando/recibiendo relevo
        self.relief_target = np.full(n, -1, dtype=int)  # INCOMING -> índice del bajo que releva (-1 si no)
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

    def _init_battery_episode(self) -> None:
        """Arranque de EPISODIO (v2.4): una flota real está a mitad de ciclo, no a tope. Los n_active EN VUELO
        con batería ALEATORIA uniforme en [battery_init_min, 1] (por encima de announce_threshold -> no dispara
        relevos en el paso 0); cada reserva EN CARGA es el ESPEJO de su pareja (reserva i <-> activo i:
        bat = 1 - bat_activo_i). Así el que vuela LLENO tiene pareja VACÍA (recién relevado) y el que vuela BAJO
        tiene pareja casi LISTA (a punto de salir; su mirror es el más cargado -> primero en llegar a READY para
        relevarlo). RNG del SUBSTREAM separado (_battery_rng) -> NO consume del stream principal -> spawns bit a
        bit (face_check 12/12). Ninguna reserva arranca READY (mirror <= 1-0.25 = 0.75 < 1) -> despega cuando carga."""
        n, na, nr = self.n_drones, self.n_active, self.n_reserve
        self.battery = np.ones(n)
        self.drone_state = np.full(n, READY, dtype=int)
        self.drone_state[:na] = ACTIVE
        self.battery_activity = np.ones(n)               # HOOK persecución (1.0 = patrulla)
        self.drone_stranded = np.zeros(n, dtype=bool)
        self.drone_relief_hold = np.zeros(n, dtype=bool)
        self.relief_target = np.full(n, -1, dtype=int)
        # Activos en vuelo: batería aleatoria (substream) por encima del umbral de relevo.
        self.battery[:na] = self._battery_rng.uniform(self.battery_init_min, 1.0, size=na)
        # Reservas EN CARGA, ESPEJO EXACTO de su pareja activa (reserva i <-> activo i).
        self.drone_state[na:] = CHARGING
        for i in range(nr):
            self.battery[na + i] = 1.0 - self.battery[i % na]
        np.clip(self.battery, 0.0, 1.0, out=self.battery)

    def _step_battery(self) -> None:
        """Avanza la batería y resuelve el RELEVO REALISTA (con hand-off, SIN teletransporte). Independiente
        de vacas/lobo y NO usa el RNG (determinista -> no perturba el stream; baseline intacto). El MOVIMIENTO
        de los drones lo hace la dinámica de vuelo (_apply_drone_actions); aquí solo se fijan waypoints/estados.

        Relevo: cuando un ACTIVE baja de announce_threshold se CLAVA en su puesto (sigue cubriendo/disuadiendo,
        el coordinador ya no lo comanda) y la central DESPACHA al READY más cargado, que VUELA hasta el puesto
        (INCOMING). Al llegar ENCIMA (<= relay_handoff_tol) -> HAND-OFF: el relevo pasa a ACTIVE y el bajo a
        RETURNING (vuela a la central; al entrar -> CHARGING). Sin reserva lista, el bajo sigue drenando; si
        llega a ~0 antes del relevo -> STRANDED (en el puesto, SIN disuadir —ya no es ACTIVE—, hasta el hand-off).
        Cobertura CONTINUA (el bajo no se va hasta que llega el relevo), salvo el hueco del caso STRANDED."""
        st, bat = self.drone_state, self.battery
        cc, cr = self.central_station[:2], self.central_station[2]

        # 1) Drenaje de los que VUELAN/cubren: ACTIVE (incl. el que espera relevo, sigue cubriendo), INCOMING
        #    (reserva en tránsito al puesto) y RETURNING (saliente de vuelta). battery_activity (#7) multiplica.
        flying = (st == ACTIVE) | (st == INCOMING) | (st == RETURNING)
        bat[flying] -= self.drain_rate_active * self.battery_activity[flying] * self.dt

        # 2) Carga en paralelo hasta charge_capacity (si sobran, cargan los más vacíos).
        charging = np.where(st == CHARGING)[0]
        if charging.size:
            slots = (charging if charging.size <= self.charge_capacity
                     else charging[np.argsort(bat[charging])][:self.charge_capacity])
            bat[slots] += self.charge_rate * self.dt
        np.clip(bat, 0.0, 1.0, out=bat)

        # 3) Cargado a tope -> READY (ni drena ni carga, espera a que un puesto pida relevo).
        st[(st == CHARGING) & (bat >= 1.0 - 1e-9)] = READY

        # 4) HAND-OFF: cada relevo INCOMING que ya está ENCIMA de su bajo (<= relay_handoff_tol) toma el puesto
        #    (-> ACTIVE) y libera al bajo (-> RETURNING, a la central). Mientras vuela, el waypoint SIGUE al bajo
        #    (que está clavado -> punto fijo). Nada salta de posición (sin teletransporte).
        for j in np.where(st == INCOMING)[0]:
            i = int(self.relief_target[j])
            self.drone_waypoint[j] = self.drones[i].copy()
            if float(np.linalg.norm(self.drones[j] - self.drones[i])) <= self.relay_handoff_tol:
                st[j] = ACTIVE                                  # el relevo cubre el puesto
                st[i] = RETURNING                              # el bajo (o el tirado) se retira a cargar
                self.drone_waypoint[i] = cc.copy()             # vuela a la central
                self.relief_target[j] = -1
                self.drone_relief_hold[i] = False
                self.drone_stranded[i] = False

        # 5) RETURNING que entra en la central -> CHARGING (aparca donde entra; empieza a cargar).
        for i in np.where(st == RETURNING)[0]:
            if float(np.linalg.norm(self.drones[i] - cc)) <= cr:
                st[i] = CHARGING
                self.drone_waypoint[i] = self.drones[i].copy()
                self.drone_vel[i] = 0.0

        # 6) ACTIVE que baja del umbral -> se CLAVA en su puesto (cobertura continua) y deja de obedecer al
        #    coordinador (drone_relief_hold). Excluye al investigador: el reflejo tiene precedencia.
        newly = np.where((st == ACTIVE) & (bat <= self.announce_threshold)
                         & ~self.drone_relief_hold & ~self.drone_investigating)[0]
        for i in newly:
            self.drone_relief_hold[i] = True
            self.drone_waypoint[i] = self.drones[i].copy()
            self.drone_vel[i] = 0.0

        # 7) DESPACHO: por cada puesto esperando relevo (ACTIVE clavado o STRANDED) SIN relevo en camino, sale
        #    el READY MÁS cargado (siempre ~lleno) a volar al puesto. Sin READY, el bajo sigue (drenará/strand).
        for i in np.where(((st == ACTIVE) & self.drone_relief_hold) | (st == STRANDED))[0]:
            if bool((self.relief_target == i).any()):
                continue                                       # ya tiene un relevo en camino
            ready = np.where(st == READY)[0]
            if ready.size == 0:
                continue                                       # sin reserva lista: reintenta cuando haya READY
            j = int(ready[np.argmax(bat[ready])])
            st[j] = INCOMING
            self.relief_target[j] = int(i)
            self.drone_waypoint[j] = self.drones[i].copy()     # despega hacia el puesto

        # 8) STRANDED: un ACTIVE clavado que se queda a ~0 antes del relevo -> tirado (deja de ser ACTIVE ->
        #    ya NO disuade/detecta; se queda en el puesto, congelado, hasta que el relevo haga hand-off).
        stuck = (st == ACTIVE) & self.drone_relief_hold & (bat <= 1e-9)
        st[stuck] = STRANDED
        self.drone_stranded[stuck] = True

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

    def _update_cow_headings(self, face_mask: np.ndarray | None = None) -> None:
        """Actualiza a quién encara cada vaca (heading) con enfriamiento.

        Encara al lobo más amenazante (el más cercano que se ACERCA) dentro de r_notice, girando
        a turn_rate. Una vez comprometida con un lobo, no cambia de objetivo hasta que pase
        face_cooldown -> mientras está fijada en uno, el flanco queda abierto a los demás.

        face_mask: si se da, SOLO esas vacas reorientan al lobo (las demás no tocan su heading). En
        pastoreo/combate todas dan la cara (mask=None); en ESCOLTA solo la PRESA fijada (y su defensora)
        encara -> las no-fijadas siguen huyendo aunque tengan lobos en r_notice.
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
            if face_mask is not None and not face_mask[i]:
                continue   # ESCOLTA: solo la presa/defensora encara; las demás no reorientan al lobo
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
        """Vaca adulta. DOS regímenes de movimiento:

        - PASTOREO / COMBATE (VIGILANCIA/SOSPECHA, o sin escolta): HOLONÓMICO e intacto (face_check corre
          aquí). Pasta DISPERSA y planta cara: separación + deambular (paseo angular lento) + valla blanda
          + anclaje de defensoras; SIN apiñamiento ni huida. El cono se impone sobre el lobo en
          _enforce_face_cones. La rapidez (magnitud de la suma de fuerzas) la fija wander_calm (casi quieta).

        - ESCOLTA (paso 2, guiado): NO-HOLONÓMICO. La vaca corre HACIA DONDE MIRA; huir y dar la cara son
          EXCLUYENTES. ENCARAR (lobo dentro de r_notice) -> gira a encararlo y se PARA (vulnerable al
          pin-and-flank). HUIR (sin lobo cerca) -> gira el heading al establo y avanza DE FRENTE a cow_speed.
          La velocidad es SIEMPRE a lo largo de cow_heading (nunca lateral) -> el flanco queda expuesto.
        """
        cows = self.cows

        if self.escort_enabled and self.phase == "ESCOLTA":
            # --- NO-HOLONÓMICO (solo ESCOLTA) ---
            active = self.cow_alive & ~self.cow_safe
            # Solo la PRESA fijada por el paquete (o su DEFENSORA si la presa es un ternero) puede ENCARAR
            # (pararse + dar la cara): el paquete está comprometido con UNA presa, no con las demás. Las
            # no-fijadas siguen HUYENDO aunque tengan lobos en r_notice.
            pinnable = np.zeros(self.n_cows, dtype=bool)
            if self.pack_prey >= 0:
                idx = int(self.pack_prey) if self.pack_prey_kind == "adult" else int(self.calf_defender[self.pack_prey])
                pinnable[idx] = True
            # ENCARAR: la presa/defensora reorienta al lobo (cono/face_cooldown igual); las demás NO.
            self._update_cow_headings(face_mask=pinnable)
            if self.n_wolves > 0:
                d_cw = np.linalg.norm(self.wolves[None, :, :] - cows[:, None, :], axis=2)   # (nc, nw)
                wolf_near = (d_cw <= self.r_notice).any(axis=1)
            else:
                wolf_near = np.zeros(self.n_cows, dtype=bool)
            encarar = active & pinnable & wolf_near   # presa/defensora con un lobo cerca -> para + encara
            huir = active & ~encarar                  # todas las demás (y la presa sin lobo cerca) -> huir
            # HUIR: rumbo objetivo = HACIA el establo (W_REFUGIO, domina) + ALEJÁNDOSE de los lobos cercanos
            # (W_EVITAR, con falloff) -> la vaca RODEA a los lobos en su camino en vez de atravesarlos. Las que
            # ENCARAN ya tienen el heading girado al lobo por _update_cow_headings (no se tocan aquí).
            to_ref = self.safe_zone[:2] - cows
            ref_dir = to_ref / np.maximum(np.linalg.norm(to_ref, axis=1, keepdims=True), 1e-9)
            avoid = np.zeros_like(cows)
            if self.n_wolves > 0:
                rel = cows[:, None, :] - self.wolves[None, :, :]            # (nc, nw, 2): lobo -> vaca (alejarse)
                dwolf = np.linalg.norm(rel, axis=2)                         # (nc, nw)
                fall = np.clip(1.0 - dwolf / COW_AVOID_RADIUS, 0.0, 1.0)    # falloff lineal: 1 a quemarropa, 0 en el borde
                units = rel / np.maximum(dwolf[:, :, None], 1e-9)
                avoid = (units * fall[:, :, None]).sum(axis=1)             # (nc, 2): suma de todos los lobos a tiro
            target = W_REFUGIO * ref_dir + W_EVITAR * avoid                 # el establo domina; la evitación es LOCAL
            tnorm = np.linalg.norm(target, axis=1)
            ref_ang = np.where(tnorm > 1e-9, np.arctan2(target[:, 1], target[:, 0]),
                               np.arctan2(to_ref[:, 1], to_ref[:, 0]))      # fallback: al establo si se anula
            self.cow_heading[huir] = self._rotate_toward(self.cow_heading[huir], ref_ang[huir], self.turn_rate * self.dt)
            # Velocidad NO-HOLONÓMICA: a lo largo del heading; avanza a cow_speed solo si HUYE (si ENCARA, 0).
            head = np.column_stack([np.cos(self.cow_heading), np.sin(self.cow_heading)])
            adv = np.where(huir, self.cow_speeds, 0.0)
            # La MADRE no abandona al ternero: una DEFENSORA que HUYE no lo ADELANTA -> su avance se limita a la
            # rapidez del ternero (la más lenta de la pareja, calf_speed < cow_speed) -> huyen JUNTAS a ese ritmo.
            # Solo mientras el ternero siga en juego (vivo y no a salvo); si ya entró o murió, la madre huye a su
            # ritmo. (Si ENCARA, adv ya es 0 -> el min no la afecta: la presa/defensora fijada sigue PARADA.)
            if self.n_calves > 0:
                pair = self.calf_alive & ~self.calf_safe
                d = self.calf_defender[pair]
                adv[d] = np.minimum(adv[d], self.calf_speed)
            self.cow_vel = head * adv[:, None]
            self.cows = cows + self.cow_vel * self.dt
        else:
            # --- HOLONÓMICO (pastoreo/combate, INTACTO) ---
            # 1) A quién encara cada vaca (todas dan la cara). 2) Separación (no se solapan).
            self._update_cow_headings()
            delta = cows[:, None, :] - cows[None, :, :]                    # (n,n,2): i - j
            dd = np.linalg.norm(delta, axis=2)
            close = (dd < self.r_separation) & (dd > 1e-9)
            push = np.where(
                close[:, :, None],
                delta / np.maximum(dd[:, :, None], 1e-9) * (1.0 - dd[:, :, None] / self.r_separation),
                0.0,
            )
            separation = self.k_separation * push.sum(axis=1)             # (n,2)

            # 3) Deambular como PASEO ANGULAR LENTO del rumbo de pasto (firme, sin temblor).
            self._cow_graze_dir = self._cow_graze_dir + self.rng.normal(0.0, self.wander_drift, size=self.n_cows)
            wander = self.wander_calm * np.column_stack([np.cos(self._cow_graze_dir),
                                                         np.sin(self._cow_graze_dir)])

            # 4) Valla blanda ("correa"): retorno hacia la zona de pasto SOLO si salen de ella.
            off = cows - self.cow_spawn
            dist_f = np.linalg.norm(off, axis=1, keepdims=True)
            excess = np.maximum(dist_f - self.cow_spread, 0.0)
            fence = -self.k_fence * off / np.maximum(dist_f, 1e-9) * excess

            # 4b) Anclaje de las DEFENSORAS a su ternero: MUELLE a longitud natural = espacio personal.
            anchor = np.zeros_like(cows)
            if self.n_calves > 0:
                d = self.calf_defender
                to_calf = self.calves - cows[d]
                ddc = np.linalg.norm(to_calf, axis=1, keepdims=True)
                anchor[d] = self.k_defender_anchor * (ddc - self.calf_personal_space) * to_calf / np.maximum(ddc, 1e-9)

            # 5) Suma de fuerzas -> velocidad deseada usando su MAGNITUD como rapidez (wander_calm fija la
            #    rapidez de pastoreo, casi quieta; se capa a cow_speeds). INERCIA para firmeza.
            total = separation + wander + fence + anchor
            speed = np.linalg.norm(total, axis=1, keepdims=True)
            scale = np.minimum(1.0, self.cow_speeds[:, None] / np.maximum(speed, 1e-9))
            self.cow_vel += self.cow_inertia * (total * scale - self.cow_vel)
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
            # En ESCOLTA el guiado las conduce HACIA el establo: NO las expulses (entrarían y rebotarían
            # en el borde sin cruzar el margen para marcarse a salvo). Entran, cruzan el margen y se marcan
            # a salvo (arriba). Fuera de ESCOLTA, contención normal. La central de carga SIEMPRE las repele.
            if not (self.escort_enabled and self.phase == "ESCOLTA"):
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
        escort = self.escort_enabled and self.phase == "ESCOLTA"
        # Objetivo de cohesión = la DEFENSORA (el ternero se ancla a su lado). En ESCOLTA, si la defensora
        # YA está a salvo (parada dentro del establo), el ternero apunta al CENTRO del establo para ENTRAR
        # ÉL MISMO (Bug 2): si no, se quedaría a rest-length FUERA del umbral y nunca se marcaría a salvo.
        # La madre a-salvo sigue siendo el ancla que lo trajo hasta aquí; ahora cruza el umbral y entra.
        target = self.cows[self.calf_defender].copy()                 # madre (ya movida este paso)
        if escort:
            target[self.cow_safe[self.calf_defender]] = self.safe_zone[:2]
        to_def = target - self.calves
        dist = np.linalg.norm(to_def, axis=1, keepdims=True)
        # MUELLE a longitud natural = espacio personal: tira hacia el objetivo si está lejos, separa si está
        # encima -> el ternero se asienta a ~calf_personal_space (AL LADO de la madre; o entra al establo).
        cohesion = self.k_calf_cohesion * (dist - self.calf_personal_space) * to_def / np.maximum(dist, 1e-9)
        self._calf_graze_dir = self._calf_graze_dir + self.rng.normal(0.0, self.wander_drift, size=self.n_calves)
        wander = self.wander_calm * np.column_stack([np.cos(self._calf_graze_dir),
                                                     np.sin(self._calf_graze_dir)])
        # En ESCOLTA el ternero MIGRA siguiendo a su defensora (cohesión): la pareja va junta al establo;
        # se suprime su wander de pastoreo. Más lento de reacción -> queda algo más expuesto (no se toca).
        if escort:
            wander = np.zeros_like(wander)
        total = cohesion + wander
        speed = np.linalg.norm(total, axis=1, keepdims=True)
        # En ESCOLTA el ternero HUYE a su rapidez propia (calf_speed < cow_speed: la cría es más lenta); en
        # pastoreo/combate sigue capado a cow_speed (INTACTO). La madre va capada a calf_speed -> la pareja
        # migra junta al ritmo del ternero, que la sigue sin rezagarse.
        cap = self.calf_speed if escort else self.cow_speed
        scale = np.minimum(1.0, cap / np.maximum(speed, 1e-9))
        prev = self.calves
        self.calf_vel += self.cow_inertia * (total * scale - self.calf_vel)
        self.calves = self.calves + self.calf_vel * self.dt
        frozen = (~self.calf_alive) | self.calf_safe   # cazados/refugiados: congelados (no se expulsan del establo)
        if frozen.any():
            self.calves[frozen] = prev[frozen]
            self.calf_vel[frozen] = 0.0
        self._clip_to_parcel(self.calves)
        # Gancho (a) REFUGIO para terneros: a salvo SOLO cuando el PROPIO ternero está dentro (Bug 2:
        # calf_safe <=> ternero dentro, NO cuando lo está su madre). Hasta entonces sigue migrando (arriba
        # apunta al centro si la madre ya está dentro) -> entra él mismo y SE marca a salvo.
        d_safe = np.linalg.norm(self.calves - self.safe_zone[:2], axis=1)
        self.calf_safe |= self.calf_alive & ~self.calf_safe & (d_safe <= self.safe_zone[2] - self.refuge_margin)
        active = self.calf_alive & ~self.calf_safe
        if active.any():
            sub = self.calves[active]
            if not escort:                       # en ESCOLTA no lo expulses del establo (igual que las adultas)
                self._push_outside_circle(sub, self.safe_zone)
            self._push_outside_circle(sub, self.central_station)
            self.calves[active] = sub

    def _update_wolves(self) -> None:
        """Orquestador POLÍTICA -> FÍSICA de los lobos. La TÁCTICA (a dónde quiere ir cada lobo: fijación de
        presa común, standoff, cono/flanqueo, rodeo, envolvente, repulsión, bordeo de zonas, coasting al
        agotar) la decide el CONTROLADOR enchufable (`self.wolf_controller`, scriptado por defecto = v2.4 bit
        a bit; ver wolf_controllers.py). El controlador devuelve la VELOCIDAD deseada por lobo (la intención)
        y fija/re-fija la presa común (estado del World, contrato compartido: la LEE el 'pin' de la vaca).

        La FÍSICA la impone AQUÍ el mundo (innegociable para cualquier controlador, aprendido incluido):
          - el SUSTO por movimiento (`_apply_deterrence`): si un dron EMBISTE, la huida SUSTITUYE a la
            intención (un lobo huyendo no mata ni flanquea); un dron estático es un obstáculo (esquiva suave);
          - la INERCIA (suavizado) + la integración del movimiento + los clamps de zona (`_push_outside_circle`).
        El CAP wolf_speed es física; el scriptado ya emite a tope por construcción, así que el mundo NO recorta
        su salida (cap implícito, bit a bit); recortará la salida de un controlador APRENDIDO (fase RL).

        Coasting (objetivos AGOTADOS): el controlador devuelve v=0 y coasting=True -> el mundo desacelera
        (inercia sobre v=0) y OMITE el susto ese paso (no hay velocidad de caza que sobrescribir), igual que v2.4.
        """
        if self.n_wolves == 0:
            self.pack_prey = -1
            self._wolf_attacking = False
            return

        # POLÍTICA: el controlador decide la velocidad deseada por lobo (y fija/re-fija la presa común).
        v_target, coasting = self.wolf_controller.decide(self)

        # FÍSICA: el SUSTO se impone SOBRE la intención (salvo en coast, que no tiene velocidad de caza que
        # sobrescribir -> se omite, exactamente como v2.4). Marca _wolf_scared (lo lee _process_predation) y
        # _drone_scaring (🔊 del render). Gateado internamente por escort_enabled (combate puro -> face_check bit a bit).
        if not coasting:
            v_target = self._apply_deterrence(v_target)

        # FÍSICA: INERCIA (suavizado, sin saltos) + integración + clamps de zona.
        self.wolf_vel += self.wolf_inertia * (v_target - self.wolf_vel)
        self.wolves = self.wolves + self.wolf_vel * self.dt
        self._clip_to_parcel(self.wolves)
        self._push_outside_circle(self.wolves, self.safe_zone)
        self._push_outside_circle(self.wolves, self.central_station)

    def _apply_deterrence(self, v_target: np.ndarray) -> np.ndarray:
        """SUSTO POR MOVIMIENTO (scare, v2.4): el miedo del lobo depende de si el dron SE LE ECHA ENCIMA, no solo
        de la distancia (los depredadores se habitúan a disuasores estáticos). Para cada lobo y cada dron ACTIVE
        a <= DETER_RADIUS se calcula la VELOCIDAD DE APROXIMACIÓN del dron (componente de su velocidad hacia el
        lobo):
          · Dron ACERCÁNDOSE (aprox. > SCARE_APPROACH_MIN): EXPULSIÓN PLENA (mecanismo v2.3) -> el lobo HUYE
            RADIAL alejándose del dron acercándose MÁS CERCANO (manda el más amenazante; desempate por índice),
            módulo clip(wolf_speed·(1-d/R), SCARE_SPEED_MIN, wolf_speed). La huida SUSTITUYE a la caza; el lobo
            queda marcado _wolf_scared -> NO mata mientras huye (ver _process_predation). SIN excepción a corta.
          · Dron ESTÁTICO/alejándose a <= SCARE_STATIC_RADIUS: ESQUIVA SUAVE -> el lobo SIGUE cazando (v_target
            manda) pero añade una repulsión radial del poste, renormalizada a la RAPIDEZ DE CAZA (solo redirige,
            no acelera ni frena). NO marca _wolf_scared -> PUEDE matar con un dron parado al lado (obstáculo, no
            amenaza).
        Marca self._drone_scaring = drones ACTIVE que se acercan a algún lobo a tiro (señal del 🔊 del render).
        Solo en escolta (escort_enabled): en combate puro devuelve v_target SIN tocar y deja _wolf_scared/
        _drone_scaring en todo False -> face_check bit a bit. Solo drones ACTIVE asustan (INCOMING/RETURNING/
        STRANDED no)."""
        self._wolf_scared = np.zeros(self.n_wolves, dtype=bool)       # reset cada paso (por defecto nadie huye)
        self._drone_scaring = np.zeros(self.n_drones, dtype=bool)     # drones que 'ladran' (se acercan a un lobo a tiro)
        if not self.escort_enabled or self.n_wolves == 0:
            return v_target
        act_idx = np.where(self.drone_state == ACTIVE)[0]
        if act_idx.size == 0:
            return v_target
        act = self.drones[act_idx]                                   # (na,2)
        act_vel = self.drone_vel[act_idx]                            # (na,2)
        rel = self.wolves[:, None, :] - act[None, :, :]              # (nw,na,2): dron -> lobo (huye alejándose)
        dd = np.linalg.norm(rel, axis=2)                             # (nw,na)
        units = rel / np.maximum(dd[:, :, None], 1e-9)              # unitario dron->lobo
        within = dd <= DETER_RADIUS                                  # (nw,na): dron a tiro
        # Velocidad de aproximación de cada dron hacia cada lobo (componente de v_dron sobre dron->lobo).
        approach = np.sum(act_vel[None, :, :] * units, axis=2)       # (nw,na) >0 = el dron se ECHA ENCIMA
        approaching = within & (approach > SCARE_APPROACH_MIN)       # (nw,na): a tiro Y acercándose de verdad
        # 🔊: un dron 'ladra' si se acerca a ALGÚN lobo a tiro (señal para el render; independiente de a quién expulsa).
        self._drone_scaring[act_idx] = approaching.any(axis=0)

        v_out = v_target.copy()

        # --- EXPULSIÓN: cada lobo con >=1 dron acercándose HUYE del dron acercándose MÁS CERCANO (el más amenazante) ---
        expelled = approaching.any(axis=1)                          # (nw,)
        if expelled.any():
            dd_appr = np.where(approaching, dd, np.inf)             # distancia SOLO de los que se acercan
            j = np.argmin(dd_appr, axis=1)                         # (nw,) dron acercándose más cercano (manda; empate -> menor índice)
            wi = np.arange(self.n_wolves)
            flee_dir = units[wi, j]                                # (nw,2) radial, alejándose del dron que embiste
            fall = np.clip(1.0 - dd[wi, j] / DETER_RADIUS, 0.0, 1.0)
            speed = np.clip(self.wolf_speed * fall, SCARE_SPEED_MIN, self.wolf_speed)   # nunca supera el cap
            v_flee = flee_dir * speed[:, None]
            v_out = np.where(expelled[:, None], v_flee, v_out)
            self._wolf_scared = expelled                           # los expulsados NO cazan/matan este paso

        # --- ESQUIVA SUAVE del poste: dron estático/alejándose a <= SCARE_STATIC_RADIUS y lobo NO expulsado ->
        #     el lobo SIGUE cazando (rapidez de caza intacta) pero RODEA el obstáculo (repulsión radial suave). ---
        obstacle = within & ~approaching & (dd <= SCARE_STATIC_RADIUS) & ~expelled[:, None]   # (nw,na)
        rows = obstacle.any(axis=1)
        if rows.any():
            fall_s = np.clip(1.0 - dd / SCARE_STATIC_RADIUS, 0.0, 1.0) * obstacle             # (nw,na)
            push = (units * fall_s[:, :, None]).sum(axis=1)        # (nw,2) alejándose de los postes
            vn = np.linalg.norm(v_out, axis=1, keepdims=True)      # rapidez de caza original (se PRESERVA)
            biased = v_out + SCARE_STATIC_GAIN * self.wolf_speed * push
            bn = np.linalg.norm(biased, axis=1, keepdims=True)
            steer = np.where(bn > 1e-9, biased / np.maximum(bn, 1e-9) * vn, v_out)   # solo REDIRIGE (misma rapidez)
            v_out = np.where(rows[:, None], steer, v_out)
        return v_out

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
        """FIJACIÓN INICIAL (t=0): si no hay presa y hay caza, fija una entre las CAZABLES (viva y no
        refugiada) con _select_prey:
          - Con ternero cazable -> ternero (objetivo blando, con cualquier nº de lobos).
          - Sin ternero y >= n_min_adult lobos -> la adulta cazable más expuesta.
          - Lobo solo sin ternero -> sin presa (standoff amplio: no se compromete).
        Las RE-FIJACIONES (tras matar/refugiarse) NO pasan por aquí: van por _recommit_nearest_prey (la
        más cercana). NO toca n_refix (la contabilidad la lleva quien llama)."""
        if self.pack_prey >= 0 or self.n_wolves == 0:
            return
        hunt = bool((self.calf_alive & ~self.calf_safe).any()) or (self.n_wolves >= self.n_min_adult)
        if not hunt:
            return
        kind, cand = self._select_prey()
        if cand >= 0:
            self.pack_prey, self.pack_prey_kind = cand, kind
            self._ever_committed = True

    def _targets_exhausted(self) -> bool:
        """¿No queda ninguna res viva y no-a-salvo? (todas muertas o refugiadas) -> el paquete ya no tiene
        a quién cazar y se desengancha (coastea a parada). Distinto de 'no se compromete' (lobo solo con
        adultas vivas): ahí sí hay objetivos, solo que no los puede tumbar (standoff)."""
        return not (bool((self.cow_alive & ~self.cow_safe).any())
                    or bool((self.calf_alive & ~self.calf_safe).any()))

    def _recommit_nearest_prey(self) -> None:
        """RE-FIJACIÓN (matanza excedente, tras matar o refugiarse la presa): la nueva presa común es la res
        viva y no-a-salvo MÁS CERCANA al centroide del paquete (va a por la siguiente). Respeta la
        capacidad de caza (a una adulta solo si >= n_min_adult lobos; a un ternero, con cualquier nº) -> un
        lobo solo no se compromete a una adulta que no puede tumbar. Si no queda objetivo cazable, deja
        pack_prey=-1 (lo recoge _targets_exhausted/standoff). NO toca n_refix (lo lleva quien llama)."""
        if self.pack_prey >= 0 or self.n_wolves == 0:
            return
        centroid = self.wolves.mean(axis=0)
        best_d, kind, idx = np.inf, None, -1
        if self.n_wolves >= self.n_min_adult:                  # adultas: solo si el paquete puede tumbarlas
            cazable = (self.cow_alive & ~self.cow_safe) & ~self._in_forbidden(self.cows)
            if cazable.any():
                d = np.linalg.norm(self.cows - centroid, axis=1)
                d[~cazable] = np.inf
                i = int(np.argmin(d))
                if d[i] < best_d:
                    best_d, kind, idx = float(d[i]), "adult", i
        cazable_calf = self.calf_alive & ~self.calf_safe       # terneros: cazables con cualquier nº de lobos
        if cazable_calf.any():
            d = np.linalg.norm(self.calves - centroid, axis=1)
            d[~cazable_calf] = np.inf
            j = int(np.argmin(d))
            if d[j] < best_d:
                best_d, kind, idx = float(d[j]), "calf", j
        if idx >= 0:
            self.pack_prey, self.pack_prey_kind = idx, kind
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

    def _envelop_slots(self, prey_pos: np.ndarray, eng: np.ndarray) -> np.ndarray:
        """ATAQUE ENVOLVENTE: asigna a cada lobo de `eng` un ángulo objetivo EQUIESPACIADO alrededor de la
        presa (paso 2π/N). Ordena por ángulo actual y reparte los slots en ese orden (sin cruces), anclando
        el conjunto al ángulo MEDIO actual (mínima rotación; ancla circular). Devuelve (len(eng),) ángulos."""
        rel = self.wolves[eng] - prey_pos
        ang = np.arctan2(rel[:, 1], rel[:, 0])
        ranks = np.empty(eng.size, dtype=int)
        ranks[np.argsort(ang)] = np.arange(eng.size)        # rango angular de cada lobo (0..N-1)
        step = 2.0 * np.pi / eng.size
        offsets = ang - step * ranks                        # ángulo de cada lobo menos su slot ideal
        theta0 = np.arctan2(np.sin(offsets).mean(), np.cos(offsets).mean())   # ancla (media circular)
        return theta0 + step * ranks

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
    def _update_investigation_waypoint(self) -> None:
        """REFLEJO de investigación (infraestructura, NO decisión del coordinador): cada dron en estado
        INVESTIGANDO persigue su CONTACTO = el CUERPO (lobo o corzo) más cercano (la manada es un cúmulo ~5 m,
        se lee como UN contacto; el TIPO se ignora hasta confirmar). Actualiza su waypoint y su contacto cada
        paso (el MENSAJE al coordinador se arma fresco en get_observation). Sin corzos = el lobo más cercano."""
        self.drone_contact[:] = np.nan
        pos, _, _ = self._contact_bodies()
        if self.drone_investigating.any() and pos.shape[0] > 0:
            for i in np.where(self.drone_investigating)[0]:
                j = int(np.argmin(np.linalg.norm(pos - self.drones[i], axis=1)))
                self.drone_contact[i] = pos[j]
                self.drone_waypoint[i] = pos[j]    # lo persigue (command_waypoint del reflejo)

    def _pick_investigator(self, free: np.ndarray, pos: np.ndarray) -> int:
        """REFLEJO (infraestructura, igual en todos los coordinadores): elige QUÉ dron va a investigar un
        contacto. Va el dron ACTIVE LIBRE (no investigando ya otro contacto) MÁS CERCANO al contacto (el
        CUERPO más cercano —lobo o corzo—, cúmulo ~5 m) entre los que lo DETECTAN (<= r_detect) -> llega antes.
        Si el más cercano está ocupado, va el siguiente más cercano libre (los ocupados no están en `free`).
        Desempate DETERMINISTA por menor índice (sin aleatoriedad). Devuelve el índice o -1 si nadie libre
        detecta. `free` = máscara (n_drones,) de elegibles; `pos` (M,2) = cuerpos detectables (_contact_bodies)."""
        cand = np.where(free)[0]
        if cand.size == 0 or pos.shape[0] == 0:
            return -1
        d = np.array([float(np.linalg.norm(pos - self.drones[i], axis=1).min()) for i in cand])
        d = np.where(d <= self.r_detect, d, np.inf)   # solo los que DETECTAN; el resto descartado
        if not np.isfinite(d).any():
            return -1
        return int(cand[int(np.argmin(d))])           # más cercano; argmin -> primer mínimo -> menor índice

    def _update_phase(self) -> None:
        """Disparador en DOS etapas (reflejo). VIGILANCIA -> SOSPECHA -> ESCOLTA, sin retorno; informativa
        (todavía NO cambia la dinámica de las vacas). Solo los drones EN VUELO (ACTIVE) detectan/confirman
        (los aparcados CHARGING/READY no vigilan; RETURNING fuera por simplicidad).
          - DETECCIÓN: cuando un CUERPO (lobo o corzo) entra a <= r_detect, investiga el dron ACTIVE libre MÁS
            CERCANO al contacto (_pick_investigator; el más cercano llega antes) -> SOSPECHA y ese dron pasa a
            INVESTIGANDO (el reflejo lo lanza hacia el contacto). Si se queda sin investigador, re-detecta.
          - CONFIRMACIÓN (ORÁCULO a r_confirm, stand-in de YOLO): cuando el dron llega a <= r_confirm de su
            contacto se revela el TIPO (verdad-terreno): LOBO -> amenaza -> ESCOLTA y el dron se LIBERA;
            CORZO -> NO-amenaza -> el dron se DESENGANCHA (descarta el corzo: no se reinvestiga) y se libera,
            SIN disparar ESCOLTA. En solo-corzos nunca se confirma un lobo -> ESCOLTA jamás se activa."""
        if not self.escort_enabled:
            return   # adversario PURO (face_check): sin máquina de fases -> la fase se queda en VIGILANCIA
        if self.phase == "ESCOLTA":
            return   # ESCOLTA latcheada: una vez confirmado un lobo no se vuelve atrás
        pos, is_wolf, gid = self._contact_bodies()
        active = self.drone_state == ACTIVE
        # Detección: si nadie investiga y hay un contacto a <= r_detect, lanza al dron libre MÁS CERCANO. El
        # tipo (lobo/corzo) es DESCONOCIDO de lejos -> el dron vuela igual hacia el contacto (waypoint en
        # _update_investigation_waypoint) y solo se revela a r_confirm. Guarda su PUESTO para volver si descarta.
        if not self.drone_investigating.any() and pos.shape[0] > 0:
            # Elegible = ACTIVE libre y DISPONIBLE: excluye al que está clavado esperando/recibiendo relevo
            # (batería baja, no debe abandonar su puesto). No cambia el comportamiento del reflejo, solo el pool.
            i = self._pick_investigator(active & ~self.drone_investigating & ~self.drone_relief_hold, pos)
            if i >= 0:
                self.drone_investigating[i] = True
                self.drone_home[i] = self.drone_waypoint[i].copy()   # puesto previo (vuelve aquí si era un corzo)
                j = int(np.argmin(np.linalg.norm(pos - self.drones[i], axis=1)))
                self.drone_contact[i] = pos[j]           # contacto = cuerpo más cercano (tipo desconocido aún)
        # Confirmación (ORÁCULO a r_confirm, NO antes): el investigador a <= r_confirm de su contacto revela el
        # tipo. LOBO -> ESCOLTA (no vuelve). CORZO -> DESCARTA (no se reinvestiga) y el dron VUELVE A SU PUESTO.
        escolta = False
        if self.drone_investigating.any() and pos.shape[0] > 0:
            for i in np.where(self.drone_investigating & active)[0]:
                d = np.linalg.norm(pos - self.drones[i], axis=1)
                j = int(np.argmin(d))
                if float(d[j]) <= self.r_confirm:
                    self.drone_investigating[i] = False  # se libera al coordinador en AMBOS casos
                    if bool(is_wolf[j]):
                        escolta = True                   # LOBO confirmado -> amenaza
                    else:
                        self.corzo_dismissed[int(gid[j]) - self.n_wolves] = True  # CORZO -> descarta
                        self.drone_waypoint[i] = self.drone_home[i]               #          y vuelve a su puesto
                    break
        # Fase: ESCOLTA (latch, lobo) > SOSPECHA (alguien investiga) > VIGILANCIA. NO se queda pillada en
        # SOSPECHA: si tras descartar no queda nadie investigando (ni se re-detecta), vuelve a VIGILANCIA.
        if escolta:
            self.phase = "ESCOLTA"
        else:
            self.phase = "SOSPECHA" if self.drone_investigating.any() else "VIGILANCIA"

    def _process_predation(self) -> bool:
        """Aplica la muerte por FLANQUEO (regla SIN cambios: cono / n_min_adult / capture_radius) a las
        reses CAZABLES y las marca cazadas. MATANZA EXCEDENTE (multi-muerte: NO termina el episodio): cae
        toda res flanqueada este paso; tras una caza el paquete RE-FIJA la más cercana (_update_wolves) y
        sigue hasta agotar objetivos. Cuenta n_depredadas y registra cada captura. Devuelve si murió la
        PRESA fijada este paso (para enlazar el quórum de #3)."""
        if self.n_wolves == 0:
            return False
        cos_cone = np.cos(self.cone_half_angle)
        prey_killed = False

        # Terneros cazables: >= 1 flanqueador del cono de su DEFENSORA (si la madre sigue en juego; si murió,
        # el ternero queda indefenso = cualquier lobo dentro de capture_radius lo caza).
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
            flank = flank & ~self._wolf_scared           # SUSTO: un lobo que HUYE de un dron no mata (v2.3)
            if flank.sum() >= 1:
                self.calf_alive[j] = False
                self.n_depredadas += 1
                self._add_capture(self._make_capture_calf(j, np.where(flank)[0], float(dist_calf.min())))
                if self.pack_prey_kind == "calf" and self.pack_prey == j:
                    prey_killed = True

        # Adultas cazables: >= n_min_adult flanqueadores a la vez (fuera del cono). Con 1 lobo no muere.
        # Caen TODAS las que tengan quórum este paso (multi-muerte); el episodio no termina por ello.
        cazable = self.cow_alive & ~self.cow_safe
        if cazable.any():
            f = self._heading_units()                                  # (nc, 2)
            rel = self.wolves[None, :, :] - self.cows[:, None, :]      # (nc, nw, 2)
            dist = np.linalg.norm(rel, axis=2)                         # (nc, nw)
            rhat = rel / np.maximum(dist[:, :, None], 1e-9)
            cosphi = np.einsum('ij,ikj->ik', f, rhat)                 # (nc, nw)
            flankers = (dist <= self.capture_radius) & (cosphi < cos_cone) & ~self._wolf_scared[None, :]  # SUSTO: el que HUYE no cuenta (v2.3)
            count = flankers.sum(axis=1)
            count[~cazable] = 0                                        # las no cazables no mueren
            for ci in np.where(count >= self.n_min_adult)[0]:
                ci = int(ci)
                self.cow_alive[ci] = False
                self.n_depredadas += 1
                self._add_capture(self._make_capture_adult(ci, dist, flankers, int(count[ci])))
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

    def _split_wolves_groups(self, pts: np.ndarray) -> np.ndarray:
        """v2.5 (Nivel A) — SPAWN EN SUBGRUPOS: parte (o no) el cúmulo ya spawneado en 1-2 subgrupos
        de tamaño DESIGUAL en sectores DISTINTOS. Sorteo ÍNTEGRO en el substream `_wolf_group_rng`
        (el stream principal NO se toca -> vacas/drones/corzos bit a bit iguales que "clustered").

        Distribución (sembrada, documentada):
        - nº de grupos: n<=2 lobos -> SIEMPRE 1 grupo; n>2 -> 1 ó 2 al 50/50. (Gancho a 3 grupos:
          ampliar este sorteo; por ahora 1-2 basta para el patrón cebo/matador.)
        - con 1 grupo NO se toca nada: las posiciones son EXACTAMENTE las de "clustered" (bit a bit).
        - con 2 grupos: tamaño del 2º grupo k ~ uniforme{1..n-1} (reparto desigual permitido; k=1 =
          CEBO posible); lo forman los k ÚLTIMOS índices (reparto por índice, determinista). El 2º
          sector se sortea a >= WOLF_GROUP_MIN_ANGLE_SEP del primero (uniforme en el arco restante) y
          su ancla se proyecta al borde de la parcela EXACTAMENTE como en _spawn_wolves_sector (misma
          distancia de spawn: cambia el eje de llegada, no cuándo llegan); mismo cúmulo gaussiano
          (wolf_spawn_dispersion) dentro del subgrupo."""
        n = len(pts)
        if n <= 2:
            return pts                                   # 1 (o 0) grupo: sin sorteo, sin cambios
        if int(self._wolf_group_rng.integers(0, 2)) == 0:
            return pts                                   # sorteó 1 grupo: posiciones clustered intactas
        k = int(self._wolf_group_rng.integers(1, n))     # tamaño del 2º grupo (1..n-1, desigual permitido)
        angle2 = (self.wolf_spawn_angle
                  + float(self._wolf_group_rng.uniform(WOLF_GROUP_MIN_ANGLE_SEP,
                                                       2 * np.pi - WOLF_GROUP_MIN_ANGLE_SEP)))
        center = np.array([self.W / 2.0, self.H / 2.0])
        d = np.array([np.cos(angle2), np.sin(angle2)])
        t = min((self.W / 2.0) / max(abs(d[0]), 1e-9), (self.H / 2.0) / max(abs(d[1]), 1e-9))
        anchor2 = center + d * t                         # misma regla de distancia que el 1er grupo (borde)
        pts = pts.copy()
        pts[n - k:] = anchor2 + self._wolf_group_rng.normal(0.0, self.wolf_spawn_dispersion, size=(k, 2))
        self._clip_to_parcel(pts[n - k:])
        self.wolf_group_sizes = [n - k, k]
        self.wolf_spawn_angles = [self.wolf_spawn_angle, float(angle2 % (2 * np.pi))]
        return pts

    def _roll_episode_kind(self) -> None:
        """Fija self.episode_kind para el episodio (3c). SOLO sortea si los corzos están activos
        (corzos_max>0) y en escenario de escolta; si no, 'lobos' SIN tocar el RNG -> mundo actual bit a bit
        (combate puro NO tiene corzos -> face_check intacto). Si se pasó episode_kind explícito, se respeta."""
        if not (self.escort_enabled and self.corzos_max > 0):
            self.episode_kind = "lobos"
            return
        if self._episode_kind_forced is not None:
            self.episode_kind = self._episode_kind_forced
            return
        self.episode_kind = str(self.rng.choice(("lobos", "corzos", "mixto"), p=self.corzo_episode_probs))

    def _spawn_corzos(self, n: int) -> np.ndarray:
        """n corzos AGRUPADOS (un GRUPO pequeño): un centroide en la BANDA de detección del rebaño
        [cow_spread+r_notice, r_detect] (fuera del rebaño pero a <= r_detect -> dispara SOSPECHA la mayoría de
        las veces), en el campo y FUERA de las zonas; los n corzos alrededor con dispersión pequeña
        (CORZO_GROUP_DISPERSION). Rechazo sembrado (reproducible). Si el guard se agota devuelve < n."""
        if n <= 0:
            return np.zeros((0, 2))
        inner = self.cow_spread + self.r_notice    # fuera del rebaño (no encima)
        outer = self.r_detect                       # dentro de r_detect -> dispara SOSPECHA
        # 1) centroide del GRUPO en la banda [inner, outer] del rebaño, en el campo y fuera de zonas.
        center = self.cow_spawn.copy()
        for _ in range(200):
            ang = float(self.rng.uniform(0.0, 2 * np.pi))
            rad = float(self.rng.uniform(inner, outer))
            cand = self.cow_spawn + rad * np.array([np.cos(ang), np.sin(ang)])
            if (0.0 <= cand[0] <= self.W and 0.0 <= cand[1] <= self.H
                    and not bool(self._in_forbidden(cand[None, :])[0])):
                center = cand
                break
        # 2) los n corzos alrededor del centroide (cúmulo pequeño), en el campo y fuera de zonas.
        pts = np.empty((n, 2)); k = 0; guard = 0
        while k < n and guard < 2000:
            guard += 1
            p = center + self.rng.normal(0.0, CORZO_GROUP_DISPERSION, size=2)
            if (0.0 <= p[0] <= self.W and 0.0 <= p[1] <= self.H
                    and not bool(self._in_forbidden(p[None, :])[0])):
                pts[k] = p; k += 1
        return pts[:k]

    def _contact_bodies(self):
        """Cuerpos DETECTABLES por los drones (lobo o corzo) NO descartados, para el reflejo de investigación.
        Devuelve (pos (M,2), is_wolf (M,) bool, gid (M,) int). is_wolf = verdad-terreno para el ORÁCULO a
        r_confirm; gid = id estable (lobo j -> j ; corzo c -> n_wolves+c) para descartar el corzo exacto.
        SIN corzos (n_corzos=0) devuelve EXACTAMENTE self.wolves -> el reflejo se reduce al actual (bit a bit)."""
        if self.n_corzos == 0:
            return self.wolves, np.ones(self.n_wolves, dtype=bool), np.arange(self.n_wolves)
        keep = ~self.corzo_dismissed
        pos = np.vstack([self.wolves, self.corzos[keep]]) if self.n_wolves else self.corzos[keep]
        is_wolf = np.concatenate([np.ones(self.n_wolves, dtype=bool), np.zeros(int(keep.sum()), dtype=bool)])
        gid = np.concatenate([np.arange(self.n_wolves), self.n_wolves + np.where(keep)[0]])
        return pos, is_wolf, gid

    def _update_corzos(self) -> None:
        """Corzo (cuerpo NO-amenaza): DEAMBULA (paseo angular lento, como las vacas al pastar) + HUYE
        (repulsión con falloff) de lobos y drones ACTIVE dentro de CORZO_FLEE_RADIUS. NO caza, NO va al
        rebaño, NO ataca. Holonómico con inercia, capado a corzo_speed. Se mantiene FUERA de las zonas."""
        if self.n_corzos == 0:
            return
        self._corzo_graze_dir = self._corzo_graze_dir + self.rng.normal(0.0, self.wander_drift, size=self.n_corzos)
        wander = self.wander_calm * np.column_stack([np.cos(self._corzo_graze_dir), np.sin(self._corzo_graze_dir)])
        flee = np.zeros((self.n_corzos, 2))
        threats = []
        if self.n_wolves > 0:
            threats.append(self.wolves)
        act = self.drones[self.drone_state == ACTIVE]
        if act.shape[0] > 0:
            threats.append(act)
        for src in threats:                                  # repulsión desde lobos y drones a tiro
            rel = self.corzos[:, None, :] - src[None, :, :]  # (nc, ns, 2): amenaza -> corzo (alejarse)
            d = np.linalg.norm(rel, axis=2)
            fall = np.clip(1.0 - d / CORZO_FLEE_RADIUS, 0.0, 1.0)
            units = rel / np.maximum(d[:, :, None], 1e-9)
            flee = flee + (units * fall[:, :, None]).sum(axis=1)
        # Grupo: cohesión SUAVE al centroide del grupo + separación para no apilarse (juntos "sin pegarse").
        group = np.zeros((self.n_corzos, 2))
        if self.n_corzos >= 2:
            C = self.corzos.mean(axis=0)
            group = group + CORZO_COHESION * (C - self.corzos)
            delta = self.corzos[:, None, :] - self.corzos[None, :, :]     # (nc, nc, 2): j -> i (separar)
            dd = np.linalg.norm(delta, axis=2)
            close = (dd < CORZO_SEPARATION) & (dd > 1e-9)
            group = group + np.where(close[:, :, None], delta / np.maximum(dd[:, :, None], 1e-9)
                                     * (1.0 - dd[:, :, None] / CORZO_SEPARATION), 0.0).sum(axis=1)
        total = wander + CORZO_FLEE_GAIN * flee + group
        speed = np.linalg.norm(total, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.corzo_speed / np.maximum(speed, 1e-9))
        self.corzo_vel = self.corzo_vel + self.cow_inertia * (total * scale - self.corzo_vel)
        self.corzos = self.corzos + self.corzo_vel * self.dt
        self._clip_to_parcel(self.corzos)
        self._push_outside_circle(self.corzos, self.safe_zone)      # no entra al establo/central (animal salvaje)
        self._push_outside_circle(self.corzos, self.central_station)

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
            "corzos": self.corzos.copy(),                 # corzos (3c, cuerpos no-amenaza)
            "corzo_dismissed": self.corzo_dismissed.copy(),  # ya confirmados NO-amenaza (descartados)
            "episode_kind": self.episode_kind,            # 'lobos' / 'corzos' / 'mixto'
            "distraction_species": self.distraction_species,  # 'corzo' / 'jabali': especie de la distracción (para el render)
            "drones": self.drones.copy(),
            "drone_state": self.drone_state.copy(),       # para dibujar el radio de disuasión de los ACTIVE
            "drone_scaring": (self._drone_scaring.copy() if self._drone_scaring is not None
                              else np.zeros(self.n_drones, dtype=bool)),   # 🔊: dron que EMBISTE a un lobo a tiro (susto por movimiento)
            "drone_investigating": self.drone_investigating.copy(),
            "drone_contact": self.drone_contact.copy(),
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
