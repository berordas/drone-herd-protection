"""obs.py — Constructor de la OBSERVACIÓN de los lobos: la ÚNICA FUENTE DE VERDAD del layout.

Lo consumen el env de entrenamiento (`rl/wolf_env.py: WolfPackEnv`) y el controlador de
EVALUACIÓN (`rl/policy_wolf_controller.py: PolicyWolfController`). Si cada uno construyera
su obs, una divergencia silenciosa haría que el evaluador midiera OTRA política — por eso
vive aquí y solo aquí (equivalencia verificada bit a bit en rl_env_check test 7).

=======================  LAYOUT DE LA OBSERVACIÓN (la referencia)  =======================
Vector float32 de tamaño FIJO OBS_SIZE=122, con padding y máscaras. SIN corzos, SIN batería,
SIN presa fijada. Marco RELATIVO al centro del establo (`safe_zone[:2]`); posiciones
normalizadas por (W/2, H/2); velocidades por la velocidad máxima de su especie (pueden
rebasar ±1 levemente: p.ej. la vaca con jitter llega a 1+cow_speed_jitter).

  [  0: 30)  5 slots de LOBO  × 6: [pos_x, pos_y, vel_x, vel_y, scared, present]
             (slot i en [6i, 6i+6); padding a CERO con present=0 para i >= n_wolves;
              scared = world._wolf_scared[i], huyendo de un dron que embiste)
  [ 30: 66)  6 slots de VACA  × 6: [pos_x, pos_y, vel_x, vel_y, alive, safe]
             (slot i en [30+6i, 30+6i+6); los cadáveres conservan pos con alive=0)
  [ 66: 80)  2 slots de TERNERO × 7: [pos_x, pos_y, vel_x, vel_y, alive, safe, present]
             (slot i en [66+7i, 66+7i+7); padding a CERO con present=0 para i >= n_calves)
  [ 80:120)  8 slots de DRON  × 5: [pos_x, pos_y, vel_x, vel_y, is_active]
             (slot i en [80+5i, 80+5i+5); is_active = drone_state == ACTIVE, el único
              estado que asusta; INCOMING/RETURNING/CHARGING/READY/STRANDED -> 0)
  [120:122)  GLOBAL: [reses_vivas_no_safe / n_cows, step_count / max_episode_steps]
             (reses = vacas + terneros en juego; con terneros puede superar 1: hasta 8/6)

Se construye leyendo ATRIBUTOS del World directamente (`get_observation()` es parcial y no
vale). El INSTANTE de muestreo importa: el env la construye en la FRONTERA del step (estado
al terminar el paso de física anterior); el controlador de evaluación debe muestrear en el
MISMO instante (ver `SyncedReactiveCoordinator`) o mediría estados desplazados medio paso.
"""

from __future__ import annotations

import numpy as np

from world import ACTIVE, DRONE_MAX_SPEED

# --------------------------- layout de la observación --------------------------- #
N_WOLF_SLOTS, WOLF_FEAT = 5, 6      # = wolves_max de CONFIG_V2
N_COW_SLOTS, COW_FEAT = 6, 6        # = n_cows
N_CALF_SLOTS, CALF_FEAT = 2, 7      # = máx de calf_count_probs
N_DRONE_SLOTS, DRONE_FEAT = 8, 5    # = n_active + n_reserve
GLOBAL_FEAT = 2

OFF_WOLF = 0
OFF_COW = OFF_WOLF + N_WOLF_SLOTS * WOLF_FEAT       # 30
OFF_CALF = OFF_COW + N_COW_SLOTS * COW_FEAT         # 66
OFF_DRONE = OFF_CALF + N_CALF_SLOTS * CALF_FEAT     # 80
OFF_GLOBAL = OFF_DRONE + N_DRONE_SLOTS * DRONE_FEAT # 120
OBS_SIZE = OFF_GLOBAL + GLOBAL_FEAT                 # 122


def build_obs(world) -> np.ndarray:
    """Vector (OBS_SIZE,) float32 con el layout de arriba, leído del World directo."""
    w = world
    center = w.safe_zone[:2]
    scale = np.array([w.W / 2.0, w.H / 2.0])

    wolf = np.zeros((N_WOLF_SLOTS, WOLF_FEAT), dtype=np.float32)
    nw = w.n_wolves
    if nw > 0:
        wolf[:nw, 0:2] = (w.wolves - center) / scale
        wolf[:nw, 2:4] = w.wolf_vel / w.wolf_speed
        wolf[:nw, 4] = w._wolf_scared.astype(np.float32)
        wolf[:nw, 5] = 1.0

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
    drone[:, 0:2] = (w.drones - center) / scale
    drone[:, 2:4] = w.drone_vel / DRONE_MAX_SPEED
    drone[:, 4] = (w.drone_state == ACTIVE).astype(np.float32)

    in_play = float((w.cow_alive & ~w.cow_safe).sum() + (w.calf_alive & ~w.calf_safe).sum())
    glob = np.array([in_play / w.n_cows, w.step_count / w.max_episode_steps], dtype=np.float32)

    return np.concatenate([wolf.ravel(), cow.ravel(), calf.ravel(), drone.ravel(), glob])
