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

La OBSERVACIÓN (layout, normalizaciones e instante de muestreo) vive en `rl/obs.py` —
la ÚNICA fuente de verdad, compartida con el controlador de evaluación
(`rl/policy_wolf_controller.py`); equivalencia verificada en rl_env_check test 7. Este
módulo re-exporta las constantes del layout por compatibilidad.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from coordinators import ReactiveCoordinator
from world import World
from baseline import CONFIG_V2

from rl.rl_wolf_controller import RLWolfController
from rl.obs import (build_obs,  # noqa: F401 — re-export: el layout vive en rl/obs.py
                    CALF_FEAT, COW_FEAT, DRONE_FEAT, GLOBAL_FEAT, N_CALF_SLOTS, N_COW_SLOTS,
                    N_DRONE_SLOTS, N_WOLF_SLOTS, OBS_SIZE, OFF_CALF, OFF_COW, OFF_DRONE,
                    OFF_GLOBAL, OFF_WOLF, WOLF_FEAT)

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
        """Delegado al builder COMPARTIDO (rl/obs.py) — única fuente de verdad del layout."""
        return build_obs(self._world)
