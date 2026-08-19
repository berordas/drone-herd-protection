"""hrl/manager_env.py — ManagerEnv: semi-MDP del MANAGER de lobos sobre las OPCIONES congeladas.

Un paso del env = UNA opción ejecutada hasta su evento TERMINAL (terminación-por-evento, elegida
por la regla pre-registrada de E0.2: p75 t(inicio->commit) > 2000 ticks; NO hay K fijo salvo el
techo K_MAX). Construido SOBRE la maquinaria de wolf_env (misma frontera de muestreo — riesgo #8:
la capa se refresca UNA vez por tick ANTES de coord.act(), el mismo instante en que los envs
construyen su obs; frame_skip=5 intacto POR DEBAJO en la capa, que re-consulta su opción fija
cada 5 ticks y la mantiene). Oponente: ReactiveCoordinator congelado (v3.5) por dentro.

ACCIÓN Discrete(4): 0 = MASA · 1 = CEBO_keep (membresías del manager, asalto en su rumbo actual;
en spawn de 1 grupo el rumbo "actual" del resto es el del paquete => la geometría que resulta es
la de CEBO(Δ90): el señuelo merodea lateral y el asalto se queda en su lado — documentado, sin
masking: aprender a evitar las malas es resultado) · 2 = CEBO(Δ=90°) · 3 = CEBO(Δ=180°). Las
opciones son las de hrl/options_wolf.WolfOptionLayer (hold=50 de serie).

EVENTOS TERMINALES de toda opción: cada MUERTE de res · HERD_SAFE (todas las reses resueltas) ·
FIN de episodio (terminated/truncated del mundo) · techo K_MAX=4500 ticks en la opción. Además,
para CEBO*: ABORT_BAIT_FAILED := ESCOLTA latcheada ∧ >= 3 de 4 ACTIVE dentro de ±60° del rumbo
del ASALTO (cono ESPEJO al del señuelo; observable: posiciones de drones/lobos/reses; PROHIBIDO
leer _anchor/_confirmed del coordinador en lógica de decisión).

RECOMPENSA = Δmuertes durante la opción (el tramo entero), sin shaping. γ=1.0 (episódico; esquiva
el descuento SMDP de τ variable). Episodio del manager = episodio del mundo (2-6 decisiones
típicas). Entrenamiento: tipo 'lobos' (como wolf_env); eval también mixto. Cada reset() toma
semilla FRESCA de la secuencia del env (mismo seed del env => misma secuencia; determinista).

CONTADOR PASIVO de PENETRADO (hallazgo B, sin arreglo): ticks en que el coordinador está en la
rama PENETRADO (estado `_pose_last_step` de la barrera: rama CLEAN si == step; se lee SOLO para
el contador, nunca para decidir) — va en info al terminal.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from baseline import CONFIG_V2
from coordinators import ReactiveCoordinator
from world import ACTIVE, World

from hrl.manager_obs import (EV_ABORT, EV_FIN, EV_HERD_SAFE, EV_INICIO, EV_KMAX, EV_MUERTE,
                             MANAGER_OBS_SIZE, N_OPTIONS, build_manager_obs, herd_points)
from hrl.options_wolf import WolfOptionLayer

K_MAX = 4500                       # ticks: techo de revisión de una opción (p90 inicio->commit G/keep ≈ 4518)
ABORT_CONE_DEG = 60.0              # ±° del rumbo del ASALTO (cono espejo)
ABORT_MIN_ACTIVE = 3               # >= 3 de 4 ACTIVE en el cono del asalto, con ESCOLTA latcheada
ABORT_GRACE_TICKS = 50             # ticks de gracia al arrancar una opción CEBO antes de evaluar el aborto
                                   # (sin gracia, una re-decisión CEBO con la condición aún cierta termina
                                   # en 1 tick y produce macro-pasos vacíos en cadena — medido en el smoke)
OPTION_SPECS = (                   # acción -> (nombre, params) de WolfOptionLayer
    ("MASA", {}),
    ("CEBO", {"membership": "keep", "hold": 50.0}),
    ("CEBO", {"delta_deg": 90.0, "hold": 50.0}),
    ("CEBO", {"delta_deg": 180.0, "hold": 50.0}),
)
OPTION_NAMES = ("MASA", "CEBO_keep", "CEBO_d90", "CEBO_d180")
EVENT_NAMES = ("INICIO", "MUERTE", "HERD_SAFE", "K_MAX", "ABORT_BAIT_FAILED", "FIN_EPISODIO")


class _ManagerDriven:
    """Manager interno de la capa: devuelve la opción que el env le ha fijado (la capa lo
    consulta cada frame_skip fronteras y sólo re-arranca la opción si cambia)."""

    def __init__(self):
        self.current = None

    def decide(self, world, layer):
        return self.current


class ManagerEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, kinds: tuple[str, ...] = ("lobos",), seed: int | None = None,
                 frame_skip: int = 5, k_max: int = K_MAX, fixed_k: int | None = None,
                 config: dict | None = None):
        super().__init__()
        self._kinds = tuple(kinds)
        self._frame_skip = int(frame_skip)
        self._k_max = int(k_max)
        self._fixed_k = None if fixed_k is None else int(fixed_k)   # RUN-M2: interrupción a K fijo
        self._config = dict(CONFIG_V2 if config is None else config)
        self._seed_rng = np.random.default_rng(seed)
        self.observation_space = gym.spaces.Box(-1.0, 1.0, (MANAGER_OBS_SIZE,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(N_OPTIONS)
        self._world: World | None = None
        self._coord: ReactiveCoordinator | None = None
        self._layer: WolfOptionLayer | None = None
        self._mgr = _ManagerDriven()
        self._ctx: dict = {}
        self._last_event = EV_INICIO
        self._decision_idx = 0
        self._log: list[dict] = []
        self._penetrado_ticks = 0
        self._info_reset: dict = {}

    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        world_seed = int(self._seed_rng.integers(0, 2**31 - 1))
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]
        return self._reset_world(world_seed, kind)

    def reset_to(self, world_seed: int, kind: str):
        """Episodio CONCRETO (evaluación emparejada / baselines): misma semilla, mismo mundo."""
        return self._reset_world(int(world_seed), kind)

    def _reset_world(self, world_seed: int, kind: str):
        self._mgr = _ManagerDriven()
        self._layer = WolfOptionLayer(manager=self._mgr, frame_skip=self._frame_skip)
        self._world = World(seed=world_seed, episode_kind=kind, wolf_controller=self._layer,
                            **self._config)
        self._coord = ReactiveCoordinator(self._world)
        self._last_event = EV_INICIO
        self._decision_idx = 0
        self._log = []
        self._penetrado_ticks = 0
        self._ctx = {"option": None, "last_event": EV_INICIO, "decision_idx": 0,
                     "decoy_idx": None, "active_c_prev": None}
        w = self._world
        self._info_reset = {"episode_kind": kind, "world_seed": world_seed,
                            "n_wolves": int(w.n_wolves), "n_calves": int(w.n_calves),
                            "two_front": bool(len(w.wolf_group_sizes) == 2),
                            "grupos_spawn": [int(x) for x in w.wolf_group_sizes]}
        return build_manager_obs(w, self._ctx), dict(self._info_reset)

    # ------------------------------------------------------------------ #
    def _active_centroid(self):
        act = self._world.drones[self._world.drone_state == ACTIVE]
        return act.mean(axis=0) if act.shape[0] else None

    def _bait_failed(self) -> bool:
        """ABORT_BAIT_FAILED (observable): ESCOLTA latcheada y >= ABORT_MIN_ACTIVE ACTIVE dentro de
        ±ABORT_CONE_DEG del rumbo del ASALTO (desde el centroide del rebaño)."""
        w = self._world
        if w.phase != "ESCOLTA":
            return False
        asa = self._layer.assault_indices()
        if asa.size == 0:
            return False
        act = w.drones[w.drone_state == ACTIVE]
        if act.shape[0] == 0:
            return False
        herd = herd_points(w)
        if herd.shape[0] == 0:
            return False
        herd_c = herd.mean(axis=0)
        v = w.wolves[asa].mean(axis=0) - herd_c
        if np.linalg.norm(v) < 1e-9:
            return False
        ang_a = np.arctan2(v[1], v[0])
        rel = act - herd_c
        ang = np.arctan2(rel[:, 1], rel[:, 0])
        diff = np.abs((ang - ang_a + np.pi) % (2 * np.pi) - np.pi)
        return int((diff <= np.deg2rad(ABORT_CONE_DEG)).sum()) >= ABORT_MIN_ACTIVE

    def step(self, action):
        a = int(action)
        assert 0 <= a < N_OPTIONS, a
        w, coord, layer = self._world, self._coord, self._layer
        name, params = OPTION_SPECS[a]
        self._mgr.current = (name, dict(params))
        t0 = int(w.step_count)
        deaths0 = int(w.n_depredadas)
        active_c0 = self._active_centroid()
        event = None
        terminated = truncated = False
        ticks = 0
        # La opción arranca en la PRIMERA frontera (refresh con countdown 0 al cambiar)... la capa
        # re-consulta cada frame_skip; forzamos la decisión inmediata para que el tramo empiece ya.
        layer._countdown = 0
        while True:
            layer.refresh(w)                         # frontera: la capa aplica la opción vigente
            wp = coord.act(w.get_observation())
            if getattr(coord, "_pose_last_step", -10) != int(w.step_count) and w.phase == "ESCOLTA" \
                    and getattr(coord, "_anchor", None) is not None:
                self._penetrado_ticks += 1           # contador PASIVO (no decide nada)
            _o, _r, terminated, truncated, _i = w.step(wp)
            ticks += 1
            if terminated or truncated:
                event = EV_FIN
                break
            if int(w.n_depredadas) > deaths0:
                # cualquier MUERTE durante el tramo termina la opción (re-decisión tras cada muerte)
                event = EV_MUERTE
                break
            in_play = int((w.cow_alive & ~w.cow_safe).sum() + (w.calf_alive & ~w.calf_safe).sum())
            if in_play == 0:
                event = EV_HERD_SAFE
                break
            if self._fixed_k is not None and ticks >= self._fixed_k:
                event = EV_KMAX
                break
            if ticks >= self._k_max:
                event = EV_KMAX
                break
            if a != 0 and ticks >= ABORT_GRACE_TICKS and self._bait_failed():
                event = EV_ABORT
                break
        reward = float(w.n_depredadas - deaths0)
        self._decision_idx += 1
        self._last_event = event
        self._log.append({"decision": self._decision_idx, "action": a, "option": OPTION_NAMES[a],
                          "t0": t0, "ticks": ticks, "event": EVENT_NAMES[event], "reward": reward,
                          "n_wolves": int(w.n_wolves), "two_front": self._info_reset["two_front"]})
        self._ctx = {"option": a, "last_event": event, "decision_idx": self._decision_idx,
                     "decoy_idx": (layer.decoy_indices() if a != 0 else None),
                     "active_c_prev": active_c0}
        obs = build_manager_obs(w, self._ctx)
        info = {"event": EVENT_NAMES[event], "ticks": ticks, "option": OPTION_NAMES[a],
                "decision_idx": self._decision_idx, **self._info_reset}
        if terminated or truncated:
            info["ep_sev"] = int(w.n_depredadas)
            info["ep_decisions"] = self._decision_idx
            info["ep_log"] = list(self._log)
            info["penetrado_ticks"] = int(self._penetrado_ticks)
            info["status"] = w.status
        return obs, reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    @property
    def world(self):
        return self._world

    @property
    def episode_log(self):
        return list(self._log)
