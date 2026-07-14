"""wolf_env.py — Envoltorio Gymnasium SINGLE-AGENT del paquete de lobos (WolfPackEnv).

Un cerebro ÚNICO mueve a TODOS los lobos contra la BARRERA REACTIVA congelada (v2.4): cada
episodio construye un `World` con `wolf_controller=RLWolfController(...)` inyectado y el
`ReactiveCoordinator` moviendo los drones POR DENTRO (el env llama al coordinador y pasa sus
waypoints a `world.step`, exactamente como hace `baseline.run_episode_metrics`). PettingZoo
queda para la fase de drones.

Decisiones (documentadas también en DISEÑO.md):
- **Acción**: `Box(-1, 1, (10,))` = velocidad deseada por SLOT de lobo (5 slots × 2), decidida
  cada `frame_skip=5` pasos de física (0.5 s) y MANTENIDA entre decisiones. Se desnormaliza
  ×`wolf_speed` y el CAP por norma vive en el controlador (frontera). Slots de lobos
  inexistentes (n_wolves < 5) se ignoran.
- **Recompensa RALA**: +1 por res matada (Δ `world.n_depredadas` acumulado en los pasos del
  frame-skip), compartida por el paquete. Sin castigo por tiempo ni por vacas a salvo.
- **terminated/truncated**: los del mundo (success/predation ↔ resolución; timeout ↔ tiempo).
- **Episodios**: kinds ~uniforme entre `kinds` (def. lobos/mixto ~50/50). NUNCA 'corzos'
  (sin lobos no hay nada que aprender). Cada `reset()` toma semilla NUEVA de una secuencia
  propia del env (recuerda: `World.reset(seed=None)` REPITE el mismo episodio; aquí SIEMPRE
  semilla fresca). Mismo seed del env ⇒ misma secuencia de episodios (determinista,
  verificado en rl_env_check).

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

La obs se construye leyendo ATRIBUTOS del World directamente (get_observation() es parcial
y no vale). Constantes exportadas para los checks: OBS_SIZE, N_*_SLOTS, *_FEAT, OFF_*.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from coordinators import ReactiveCoordinator
from world import ACTIVE, DRONE_MAX_SPEED, World
from baseline import CONFIG_V2

from rl.rl_wolf_controller import RLWolfController

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

VALID_KINDS = ("lobos", "mixto")    # NUNCA 'corzos' (sin lobos no hay nada que aprender)


class WolfPackEnv(gym.Env):
    """Paquete de lobos (cerebro único) contra la barrera reactiva congelada. Ver módulo."""

    metadata = {"render_modes": []}

    def __init__(self, kinds: tuple[str, ...] = ("lobos", "mixto"), frame_skip: int = 5,
                 seed: int | None = None, config: dict | None = None):
        super().__init__()
        kinds = tuple(kinds)
        if not kinds or any(k not in VALID_KINDS for k in kinds):
            raise ValueError("kinds debe ser un subconjunto no vacío de %r (nunca 'corzos'); recibido %r"
                             % (VALID_KINDS, kinds))
        if frame_skip < 1:
            raise ValueError("frame_skip >= 1")
        self._kinds = kinds
        self._frame_skip = int(frame_skip)
        self._config = dict(CONFIG_V2 if config is None else config)
        # Secuencia PROPIA de semillas de episodio (independiente de self.np_random de gym).
        self._seed_rng = np.random.default_rng(seed)
        self._controller = RLWolfController(N_WOLF_SLOTS)
        self._world: World | None = None
        self._coordinator: ReactiveCoordinator | None = None

        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(N_WOLF_SLOTS * 2,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(OBS_SIZE,), dtype=np.float32)

    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:                      # re-sembrar la secuencia de episodios (API gym)
            self._seed_rng = np.random.default_rng(seed)
        world_seed = int(self._seed_rng.integers(0, 2**31 - 1))   # SIEMPRE semilla fresca
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]

        self._controller.reset()
        self._world = World(seed=world_seed, episode_kind=kind,
                            wolf_controller=self._controller, **self._config)
        self._coordinator = ReactiveCoordinator(self._world)
        info = {"episode_kind": kind, "world_seed": world_seed,
                "n_wolves": int(self._world.n_wolves), "n_calves": int(self._world.n_calves)}
        return self._obs(), info

    def step(self, action):
        w = self._world
        a = np.clip(np.asarray(action, dtype=np.float32).reshape(N_WOLF_SLOTS, 2), -1.0, 1.0)
        self._controller.set_action(a * w.wolf_speed)   # desnormaliza; el cap por norma, en el controlador

        deaths0 = w.n_depredadas
        terminated = truncated = False
        info: dict = {}
        for _ in range(self._frame_skip):               # la acción se mantiene entre decisiones
            waypoints = self._coordinator.act(w.get_observation())   # la barrera se recoloca cada paso
            _obs, _r, terminated, truncated, info = w.step(waypoints)
            if terminated or truncated:
                break
        reward = float(w.n_depredadas - deaths0)        # RALA: +1 por res matada en el tramo
        return self._obs(), reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    def _obs(self) -> np.ndarray:
        """Construye el vector (ver layout en el docstring del módulo) leyendo el World directo."""
        w = self._world
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
