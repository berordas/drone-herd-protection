"""drone_obs.py — Observación POR PUESTO del MARL de drones: la ÚNICA fuente de verdad del layout.

La consumen el env de entrenamiento (`rl/drone_env.py: DroneTeamEnv`) y el controlador de
evaluación (`rl/residual_drone_coordinator.py`) — mismo principio de origen único que rl/obs.py
para los lobos (una divergencia silenciosa haría que el evaluador midiera OTRA política).

AGENTE = PUESTO de barrera (asiento k = 0..3), no el dron físico: el asiento k lo ocupa el
k-ésimo dron EN ESTACIÓN (estado ACTIVE o STRANDED, por orden de índice) — el puesto persiste
aunque el dron que lo ocupa se vaya a cargar (el relevo entra al mismo asiento). El mapeo vive
en `ResidualDroneCoordinator.seats()`.

PERCEPCIÓN: el actor solo VE lobos DETECTADOS (criterio DRI del mundo, COMPARTIDO entre
puestos: lobo a <= r_detect de un dron EN VUELO/ACTIVE — el mismo de la barrera v2.6 y del
disparador; `detected_mask()` lo recomputa en solo-lectura). SIN batería, SIN corzos (su efecto
llega vía is_active/investigating de los compañeros). El CRÍTICO centralizado (CTDE) sí ve el
estado PRIVILEGIADO completo: reutiliza `rl.obs.build_obs` (122; lobos por verdad-terreno,
incluidos los NO detectados).

=================  LAYOUT LOCAL por puesto (LOCAL_SIZE = 131, float32)  =================
Marco RELATIVO al centro del establo; posiciones /(W/2, H/2); velocidades /v_max de su especie
(patrón de rl/obs.py: tamaño fijo, slots + padding a cero + flags present).

  [  0:  8) EGO del dron del puesto: [pos_x, pos_y, vel_x, vel_y, is_active, commandable,
            base_wp_x, base_wp_y]
            (commandable = ACTIVE & ~investigating & ~relief_hold — si 0, la δ de este puesto
             NO se aplica este tramo; base_wp = waypoint que la BARRERA propone para este dron
             en el último paso de física — la pista de la intención de la base (la histéresis
             del ancla v2.6 y la fase de patrulla son estado oculto; lección del plan C);
             0 en la primera frontera del episodio.)
  [  8: 38) 5 slots de LOBO DETECTADO × 6: [pos_x, pos_y, vel_x, vel_y, scared, present]
            (slot i = lobo i, ALINEADO POR ÍNDICE; present=1 SOLO si el lobo i existe Y está
             DETECTADO; no detectado o inexistente → todo 0. La verdad-terreno NO viaja aquí.)
  [ 38: 74) 6 slots de VACA × 6: [pos_x, pos_y, vel_x, vel_y, alive, safe]
  [ 74: 88) 2 slots de TERNERO × 7: [pos_x, pos_y, vel_x, vel_y, alive, safe, present]
  [ 88:128) 8 slots de DRON × 5: [pos_x, pos_y, vel_x, vel_y, is_active]
            (roster completo, incluido el propio dron — el ego va aparte y duplica; simple y
             mantiene los slots alineados con el índice de dron)
  [128:131) LOCAL-GLOBAL: [reses_en_juego / n_cows, step / max_episode_steps, n_detectados / 5]

===============  OBS COMPUESTA por agente (AGENT_OBS_SIZE = 253, CTDE)  ===============
  [   0:131) LOCAL del puesto (arriba)          → la ve el ACTOR (π, descentralizado)
  [ 131:253) GLOBAL privilegiada = rl.obs.build_obs(world) (122) → la ve el CRÍTICO (V)
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
N_WOLF_SLOTS, WOLF_FEAT = 5, 6       # = wolves_max
N_COW_SLOTS, COW_FEAT = 6, 6         # = n_cows
N_CALF_SLOTS, CALF_FEAT = 2, 7
N_DRONE_SLOTS, DRONE_FEAT = 8, 5     # = n_active + n_reserve
LOCAL_GLOBAL_FEAT = 3

OFF_EGO = 0
OFF_WOLF = OFF_EGO + EGO_FEAT                        # 8
OFF_COW = OFF_WOLF + N_WOLF_SLOTS * WOLF_FEAT        # 38
OFF_CALF = OFF_COW + N_COW_SLOTS * COW_FEAT          # 74
OFF_DRONE = OFF_CALF + N_CALF_SLOTS * CALF_FEAT      # 88
OFF_LGLOBAL = OFF_DRONE + N_DRONE_SLOTS * DRONE_FEAT # 128
LOCAL_SIZE = OFF_LGLOBAL + LOCAL_GLOBAL_FEAT         # 131

AGENT_OBS_SIZE = LOCAL_SIZE + GLOBAL_SIZE            # 253 = 131 + 122


def detected_mask(world) -> np.ndarray:
    """(n_wolves,) bool: lobo DETECTADO ⟺ a <= r_detect de un dron EN VUELO (ACTIVE).
    El MISMO criterio DRI del disparador del mundo y de la barrera v2.6
    (ReactiveCoordinator._detected), recomputado en SOLO-LECTURA — compartido entre puestos."""
    w = world
    if w.n_wolves == 0:
        return np.zeros(0, dtype=bool)
    flying = w.drones[w.drone_state == ACTIVE]
    if flying.shape[0] == 0:
        return np.zeros(w.n_wolves, dtype=bool)
    d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
    return (d <= w.r_detect).any(axis=1)


def build_drone_local_obs(world, i: int, base_wp=None) -> np.ndarray:
    """Vector LOCAL (LOCAL_SIZE,) float32 del puesto cuyo dron es `i` (índice de dron).
    `base_wp` = waypoint (x, y) que la barrera propone para el dron i (None → ceros, primera
    frontera). Se construye leyendo ATRIBUTOS del World directamente."""
    w = world
    center = w.safe_zone[:2]
    scale = np.array([w.W / 2.0, w.H / 2.0])

    ego = np.zeros(EGO_FEAT, dtype=np.float32)
    ego[0:2] = (w.drones[i] - center) / scale
    ego[2:4] = w.drone_vel[i] / DRONE_MAX_SPEED
    ego[4] = 1.0 if w.drone_state[i] == ACTIVE else 0.0
    ego[5] = 1.0 if (w.drone_state[i] == ACTIVE and not w.drone_investigating[i]
                     and not w.drone_relief_hold[i]) else 0.0
    if base_wp is not None:
        ego[6:8] = (np.asarray(base_wp, dtype=float) - center) / scale

    det = detected_mask(w)
    wolf = np.zeros((N_WOLF_SLOTS, WOLF_FEAT), dtype=np.float32)
    nw = w.n_wolves
    if nw > 0 and det.any():
        vis = np.zeros(N_WOLF_SLOTS, dtype=bool)
        vis[:nw] = det[:N_WOLF_SLOTS]
        wolf[vis, 0:2] = (w.wolves[det[:N_WOLF_SLOTS]] - center) / scale
        wolf[vis, 2:4] = w.wolf_vel[det[:N_WOLF_SLOTS]] / w.wolf_speed
        wolf[vis, 4] = w._wolf_scared[det[:N_WOLF_SLOTS]].astype(np.float32)
        wolf[vis, 5] = 1.0

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
                        float(det.sum()) / N_WOLF_SLOTS], dtype=np.float32)

    return np.concatenate([ego, wolf.ravel(), cow.ravel(), calf.ravel(), drone.ravel(), lglobal])


def build_drone_agent_obs(world, i: int, base_wp=None) -> np.ndarray:
    """Obs COMPUESTA (AGENT_OBS_SIZE,) del puesto con dron `i`: [LOCAL_i ‖ GLOBAL privilegiada].
    La parte global (rl.obs.build_obs, 122) es idéntica para todos los puestos — el crítico
    centralizado (CTDE) ve el estado completo; el actor solo la mitad local."""
    return np.concatenate([build_drone_local_obs(world, i, base_wp), build_obs(world)])
