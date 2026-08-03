"""drone_obs.py — Observación POR PUESTO del MARL de drones: la ÚNICA fuente de verdad del layout.

La consumen el env de entrenamiento (`rl/drone_env.py: DroneTeamEnv`) y el controlador de
evaluación (`rl/residual_drone_coordinator.py`) — mismo principio de origen único que rl/obs.py
para los lobos (una divergencia silenciosa haría que el evaluador midiera OTRA política).

AGENTE = PUESTO de barrera (asiento k = 0..3), no el dron físico: el asiento k lo ocupa el
k-ésimo dron EN ESTACIÓN (estado ACTIVE o STRANDED, por orden de índice) — el puesto persiste
aunque el dron que lo ocupa se vaya a cargar (el relevo entra al mismo asiento). El mapeo vive
en `ResidualDroneCoordinator.seats()`.

PERCEPCIÓN (run02, CAMBIO DE DISEÑO 2 — decisión del usuario): los lobos viajan en DOS grupos
ETIQUETADOS por separado, con padding+present cada uno:
  · CONTACTOS ("hay algo"): cuerpo AHORA a <= r_detect=100 de algún dron EN VUELO (ACTIVE) y
    NUNCA confirmado — el nivel DETECTAR del marco DRI, un bulto sin clasificar (instantáneo,
    `detected_mask`, sin memoria: si sale del radio, desaparece del grupo).
  · CONFIRMADOS ("es un lobo"): lobo ALGUNA VEZ a <= r_confirm=40 de un dron ACTIVE, con
    MEMORIA de equipo el resto del episodio (tracking) — el MISMO latch v2.8 de la barrera
    (`ReactiveCoordinator._confirmed`, UNA fuente de verdad, pasada por el coordinador residual);
    su posición/velocidad viajan siempre (confirmar = mantener el track, convenio v2.8).
    Al confirmarse, el lobo SALE del grupo de contactos (grupos disjuntos: la etiqueta es el dato).
POR QUÉ (documentado para la memoria): la barrera clásica solo reacciona a CONFIRMADOS — es la
baseline tonta a batir. Darle al MARL también los CONTACTOS le permite ANTICIPARSE a un frente
antes de que la barrera reaccione (p.ej. desplazarse hacia un bulto que aún no está clasificado)
— asimetría de información a FAVOR del aprendido, y realista: un sensor ve movimiento mucho
antes de clasificarlo (YOLO en la fase de percepción). SIN batería, SIN corzos... con un matiz:
los corzos NO viajan en la obs (no hay slots de corzo), pero un corzo dentro de r_detect es un
CONTACTO real del mundo — aquí solo viajan LOBOS (los arrays de lobos); el efecto de los corzos
llega vía is_active/investigating de los compañeros (el reflejo roba drones), como en run01.
El CRÍTICO centralizado (CTDE) sí ve el estado PRIVILEGIADO completo: reutiliza
`rl.obs.build_obs` (122; lobos por verdad-terreno, incluidos los NO detectados).

=================  LAYOUT LOCAL por puesto (LOCAL_SIZE = 162, float32)  =================
Marco RELATIVO al centro del establo; posiciones /(W/2, H/2); velocidades /v_max de su especie
(patrón de rl/obs.py: tamaño fijo, slots + padding a cero + flags present).

  [  0:  8) EGO del dron del puesto: [pos_x, pos_y, vel_x, vel_y, is_active, commandable,
            base_wp_x, base_wp_y]
            (commandable = ACTIVE & ~investigating — v3.0: el anunciado sigue comandable; si 0,
             la δ de este puesto NO se aplica este tramo; base_wp = waypoint que la BARRERA SIN
             RIGIDEZ propone para este dron en el último paso de física; 0 en la 1ª frontera.)
  [  8: 38) 5 slots de CONTACTO × 6: [pos_x, pos_y, vel_x, vel_y, scared, present]
            (slot i = lobo i, ALINEADO POR ÍNDICE; present=1 SOLO si el lobo i existe, está
             AHORA a <= r_detect de un ACTIVE y NUNCA fue confirmado. La verdad-terreno de los
             no-detectados NO viaja.)
  [ 38: 68) 5 slots de CONFIRMADO × 6: [pos_x, pos_y, vel_x, vel_y, scared, present]
            (slot i = lobo i; present=1 si ALGUNA VEZ confirmado — memoria de equipo; posición
             SIEMPRE mientras dure el episodio: tracking v2.8.)
  [ 68:104) 6 slots de VACA × 6: [pos_x, pos_y, vel_x, vel_y, alive, safe]
  [104:118) 2 slots de TERNERO × 7: [pos_x, pos_y, vel_x, vel_y, alive, safe, present]
  [118:158) 8 slots de DRON × 5: [pos_x, pos_y, vel_x, vel_y, is_active]
            (roster completo, incluido el propio dron — el ego va aparte y duplica; simple y
             mantiene los slots alineados con el índice de dron)
  [158:162) LOCAL-GLOBAL: [reses_en_juego / n_cows, step / max_episode_steps,
                           n_contactos / 5, n_confirmados / 5]

===============  OBS COMPUESTA por agente (AGENT_OBS_SIZE = 284, CTDE)  ===============
  [   0:162) LOCAL del puesto (arriba)          → la ve el ACTOR (π, descentralizado)
  [ 162:284) GLOBAL privilegiada = rl.obs.build_obs(world) (122) → la ve el CRÍTICO (V)
El extractor del policy (rl/train_drones.py: SplitMlpExtractor) enruta cada mitad a su red.
"""

from __future__ import annotations

import numpy as np

from world import ACTIVE, DRONE_MAX_SPEED

from rl.obs import OBS_SIZE as GLOBAL_SIZE
from rl.obs import build_obs

# --------------------------- layout local --------------------------- #
N_SEATS = 4                          # puestos de barrera (= n_active_drones de CONFIG_V2)
EGO_FEAT = 8
N_WOLF_SLOTS, WOLF_FEAT = 5, 6       # = wolves_max (por grupo: contactos y confirmados)
N_COW_SLOTS, COW_FEAT = 6, 6         # = n_cows
N_CALF_SLOTS, CALF_FEAT = 2, 7
N_DRONE_SLOTS, DRONE_FEAT = 8, 5     # = n_active + n_reserve
LOCAL_GLOBAL_FEAT = 4                # run02: contadores de contactos Y confirmados

OFF_EGO = 0
OFF_WOLF = OFF_EGO + EGO_FEAT                        # 8   (grupo CONTACTOS)
OFF_CONF = OFF_WOLF + N_WOLF_SLOTS * WOLF_FEAT       # 38  (grupo CONFIRMADOS, run02)
OFF_COW = OFF_CONF + N_WOLF_SLOTS * WOLF_FEAT        # 68
OFF_CALF = OFF_COW + N_COW_SLOTS * COW_FEAT          # 104
OFF_DRONE = OFF_CALF + N_CALF_SLOTS * CALF_FEAT      # 118
OFF_LGLOBAL = OFF_DRONE + N_DRONE_SLOTS * DRONE_FEAT # 158
LOCAL_SIZE = OFF_LGLOBAL + LOCAL_GLOBAL_FEAT         # 162

AGENT_OBS_SIZE = LOCAL_SIZE + GLOBAL_SIZE            # 284 = 162 + 122


def detected_mask(world) -> np.ndarray:
    """(n_wolves,) bool: lobo DETECTADO ⟺ a <= r_detect de un dron EN VUELO (ACTIVE).
    El MISMO criterio DRI del disparador del mundo, recomputado en SOLO-LECTURA — compartido
    entre puestos. Instantáneo y SIN memoria (el nivel DETECTAR: un contacto que se aleja se
    pierde; la memoria es solo de los CONFIRMADOS, latch v2.8 de la barrera)."""
    w = world
    if w.n_wolves == 0:
        return np.zeros(0, dtype=bool)
    flying = w.drones[w.drone_state == ACTIVE]
    if flying.shape[0] == 0:
        return np.zeros(w.n_wolves, dtype=bool)
    d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
    return (d <= w.r_detect).any(axis=1)


def _wolf_group(world, mask: np.ndarray, center, scale) -> np.ndarray:
    """(N_WOLF_SLOTS, WOLF_FEAT) slots de lobo para una máscara (alineados por índice)."""
    w = world
    out = np.zeros((N_WOLF_SLOTS, WOLF_FEAT), dtype=np.float32)
    if w.n_wolves == 0 or not mask.any():
        return out
    m = np.zeros(N_WOLF_SLOTS, dtype=bool)
    m[:w.n_wolves] = mask[:N_WOLF_SLOTS]
    sel = mask[:N_WOLF_SLOTS]
    out[m, 0:2] = (w.wolves[sel] - center) / scale
    out[m, 2:4] = w.wolf_vel[sel] / w.wolf_speed
    out[m, 4] = w._wolf_scared[sel].astype(np.float32)
    out[m, 5] = 1.0
    return out


def build_drone_local_obs(world, i: int, base_wp=None, confirmed=None) -> np.ndarray:
    """Vector LOCAL (LOCAL_SIZE,) float32 del puesto cuyo dron es `i` (índice de dron).
    `base_wp` = waypoint (x, y) que la barrera propone para el dron i (None → ceros, primera
    frontera). `confirmed` = máscara (n_wolves,) del latch de equipo v2.8 (la pasa el
    coordinador residual desde su barrera interior; None → nada confirmado aún, p.ej. la
    primera frontera del episodio). Se construye leyendo ATRIBUTOS del World directamente."""
    w = world
    center = w.safe_zone[:2]
    scale = np.array([w.W / 2.0, w.H / 2.0])

    ego = np.zeros(EGO_FEAT, dtype=np.float32)
    ego[0:2] = (w.drones[i] - center) / scale
    ego[2:4] = w.drone_vel[i] / DRONE_MAX_SPEED
    ego[4] = 1.0 if w.drone_state[i] == ACTIVE else 0.0
    ego[5] = 1.0 if (w.drone_state[i] == ACTIVE and not w.drone_investigating[i]) else 0.0  # v3.0: el anunciado sigue comandable
    if base_wp is not None:
        ego[6:8] = (np.asarray(base_wp, dtype=float) - center) / scale

    conf = (np.asarray(confirmed, dtype=bool) if confirmed is not None
            else np.zeros(w.n_wolves, dtype=bool))
    det = detected_mask(w)
    contact = det & ~conf                        # bulto sin clasificar (grupos DISJUNTOS)
    wolf_c = _wolf_group(w, contact, center, scale)
    wolf_k = _wolf_group(w, conf, center, scale)

    cow = np.zeros((N_COW_SLOTS, COW_FEAT), dtype=np.float32)
    cow[:, 0:2] = (w.cows - center) / scale
    cow[:, 2:4] = w.cow_vel / w.cow_speed
    cow[:, 4] = w.cow_alive.astype(np.float32)
    cow[:, 5] = w.cow_safe.astype(np.float32)

    calf = np.zeros((N_CALF_SLOTS, CALF_FEAT), dtype=np.float32)
    nc = w.n_calves
    if nc > 0:
        calf[:nc, 0:2] = (w.calves - center) / scale
        calf[:nc, 2:4] = w.calf_vel / w.calf_speed
        calf[:nc, 4] = w.calf_alive.astype(np.float32)
        calf[:nc, 5] = w.calf_safe.astype(np.float32)
        calf[:nc, 6] = 1.0

    drone = np.zeros((N_DRONE_SLOTS, DRONE_FEAT), dtype=np.float32)
    nd = min(w.n_drones, N_DRONE_SLOTS)
    drone[:nd, 0:2] = (w.drones[:nd] - center) / scale
    drone[:nd, 2:4] = w.drone_vel[:nd] / DRONE_MAX_SPEED
    drone[:nd, 4] = (w.drone_state[:nd] == ACTIVE).astype(np.float32)

    en_juego = float((w.cow_alive & ~w.cow_safe).sum())
    if w.n_calves > 0:
        en_juego += float((w.calf_alive & ~w.calf_safe).sum())
    lglobal = np.array([en_juego / w.n_cows, w.step_count / w.max_episode_steps,
                        float(contact.sum()) / N_WOLF_SLOTS,
                        float(conf.sum()) / N_WOLF_SLOTS], dtype=np.float32)

    return np.concatenate([ego, wolf_c.ravel(), wolf_k.ravel(), cow.ravel(), calf.ravel(),
                           drone.ravel(), lglobal])


def build_drone_agent_obs(world, i: int, base_wp=None, confirmed=None) -> np.ndarray:
    """Obs COMPUESTA (AGENT_OBS_SIZE,) del puesto con dron `i`: [LOCAL_i ‖ GLOBAL privilegiada].
    La parte global (rl.obs.build_obs, 122) es idéntica para todos los puestos — el crítico
    centralizado (CTDE) ve el estado completo; el actor solo la mitad local."""
    return np.concatenate([build_drone_local_obs(world, i, base_wp, confirmed), build_obs(world)])
