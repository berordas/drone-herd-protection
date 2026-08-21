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
para CEBO* y SOLO PRE-SHOW (Commit S2, adjudicación VERIF-0: post-show la condición se mantenía
cierta de continuo y el ABORT era un falso terminal en bucle — metrónomo de 50 ticks):
ABORT_BAIT_FAILED := no wolf_decoy_released ∧ ESCOLTA latcheada ∧ >= 3 de 4 ACTIVE dentro de
±60° del rumbo del ASALTO (cono ESPEJO al del señuelo; observable: posiciones de
drones/lobos/reses; PROHIBIDO leer _anchor/_confirmed del coordinador en lógica de decisión).

RECOMPENSA = Δmuertes durante la opción (el tramo entero), sin shaping. γ=1.0 (episódico; esquiva
el descuento SMDP de τ variable). Episodio del manager = episodio del mundo (2-6 decisiones
típicas). Entrenamiento: tipo 'lobos' (como wolf_env); eval también mixto. Cada reset() toma
semilla FRESCA de la secuencia del env (mismo seed del env => misma secuencia; determinista).

CONTADOR PASIVO de PENETRADO (hallazgo B, sin arreglo): ticks en que el coordinador está en la
rama PENETRADO (estado `_pose_last_step` de la barrera: rama CLEAN si == step; se lee SOLO para
el contador, nunca para decidir) — va en info al terminal.

AUDITOR DE PATRULLA (adenda post-visionado seed 84, Encargo 1e; pasivo): PatrolCoverageTracker
por episodio (fase != ESCOLTA): pares adyacentes del anillo con AVISO D>100 / VIOLACIÓN D>2·r_detect,
radio del anillo y entradas de lobo no detectadas — resumen en info["patrulla"] al terminal.

CONTADORES DE CAZA (K-bis, instrumentación; solo se reportan en info["hunt"] al terminal): re-arranques
de opción (OPTION_START de la capa), re-targets por la regla de caza (Commit K: causa "protegida"),
re-targets bloqueados por cooldown, y re-fijaciones de presa NO debidas a la regla, por causa de la
presa anterior (muerte / refugio / otro). Se leen de los contadores de la capa y del estado
pack_prey/pack_prey2 tick a tick; los eventos de la capa NO se consumen aquí (pop_events queda para
el auditor/visionado).
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from baseline import CONFIG_V2
from coordinators import ReactiveCoordinator
from world import ACTIVE, World

from hrl.manager_obs import (EV_ABORT, EV_FIN, EV_HERD_SAFE, EV_INICIO, EV_KMAX, EV_MUERTE,
                             MANAGER_OBS_SIZE, N_OPTIONS, build_manager_obs, herd_points)
from hrl.behavior_checks import PatrolCoverageTracker
from hrl.options_wolf import WolfOptionLayer

OPPONENTS = ("reactive", "run02", "run09", "mix") # defensas congeladas; 'mix' (adenda 4 §4, RUN-M3) = uniforme por episodio {reactive, run09}
RUN02_MODEL = "/data/drones/run02_v34/model.zip"
RUN09_MODEL = "/data/drones/run09_v35/model.zip"
_MODEL_CACHE: dict = {}

K_MAX = 4500                       # ticks: techo de revisión de una opción (p90 inicio->commit G/keep ≈ 4518)
ABORT_CONE_DEG = 60.0              # ±° del rumbo del ASALTO (cono espejo)
ABORT_MIN_ACTIVE = 3               # >= 3 de 4 ACTIVE en el cono del asalto, con ESCOLTA latcheada
ABORT_GRACE_TICKS = 50             # ticks de gracia al arrancar una opción CEBO antes de evaluar el aborto
                                   # (sin gracia, una re-decisión CEBO con la condición aún cierta termina
                                   # en 1 tick y produce macro-pasos vacíos en cadena — medido en el smoke)
DELIB_COST = 0.05                  # Commit Q (plan M1'''', dueño): COSTE DE DELIBERACIÓN pre-registrado
                                   # — una decisión tomada tras INTERRUPCIÓN (ABORT) que CAMBIA de opción
                                   # (con acciones discretas, "re-arrancar con parámetros nuevos" = otra
                                   # acción) resta esto a la recompensa del tramo nuevo. Decisiones tras
                                   # terminal NATURAL (MUERTE/HERD_SAFE/techo/FIN) = GRATIS; re-elegir la
                                   # MISMA opción tras ABORT = GRATIS (la capa no re-arranca). Motivo:
                                   # degeneración de opciones (cf. option-critic) — el manager conserva
                                   # TODA la libertad; molinillear se paga, no se prohíbe. FALLBACK ÚNICO
                                   # pre-registrado en PREREGISTRO_v3 (escrito ANTES de entrenar): 0.1 si
                                   # en la ligera de 40k los ABORTs/ep siguen > 10. Los baselines no
                                   # interrumpen => pagan 0 (escalera justa). La SEV de todas las tablas
                                   # es SIEMPRE sin coste (n_depredadas); el coste solo da forma al
                                   # RETORNO de entrenamiento (telemetría: aborts / delib_pagado).
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
                 config: dict | None = None, opponent: str = "reactive",
                 g_oversample: float | None = None, obs_ablate_progress: bool = False,
                 delib_cost: float = DELIB_COST):
        """`opponent`: 'reactive' (v3.5 congelado; el de RUN-M1) | 'run02' | 'run09'
        (ResidualDroneCoordinator con el modelo congelado; solo EVALUACIÓN/tabla-escalera) |
        'mix' (adenda 4 §4, RUN-M3: uniforme por episodio entre reactive y run09).
        ADENDA 4 (default OFF = RUN-M1 intacto): `g_oversample` (§2, contingencia de currículo,
        SOLO entrenamiento, jamás auto-activada): fracción de episodios FORZADA a spawn de 2
        grupos por RECHAZO del spawn real (la maquinaria de dieta de wolf_env: stream propio
        seed+11_000_003; nada sintético; None = natural; set_g_oversample(None) la apaga en
        caliente). `obs_ablate_progress` (§3, RUN-M4): obs[19:21] = 0 (sin los dos rasgos de
        progreso del cebo)."""
        super().__init__()
        if opponent not in OPPONENTS:
            raise ValueError(f"opponent {opponent!r} no está en {OPPONENTS}")
        self._opponent = opponent
        self._g_over = g_oversample
        self._g_rng = np.random.default_rng((seed or 0) + 11_000_003)   # mismo patrón que la dieta run08
        self._ablate = bool(obs_ablate_progress)
        self._delib_cost = float(delib_cost)             # Commit Q (0.0 = apagado)
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
        self._last_action: int | None = None             # Commit Q: para detectar el CAMBIO tras ABORT
        self._n_aborts = 0
        self._delib_paid = 0.0
        self._info_reset: dict = {}
        self.on_tick = None                       # gancho de SOLO LECTURA (render/visionado): f(world, coord, layer) tras cada step
        self.on_boundary = None                   # gancho de SOLO LECTURA (auditoría): f(world, coord, layer) ANTES de coord.act()

    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        world_seed = int(self._seed_rng.integers(0, 2**31 - 1))
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]
        if self._g_over is not None:
            # CONTINGENCIA DE CURRÍCULO (adenda 4 §2): oversampling de episodios G por RECHAZO del
            # spawn real (re-sortea la semilla hasta que el spawn natural da 2 grupos / 1 grupo).
            want_two = bool(self._g_rng.random() < self._g_over)
            for _ in range(80):
                probe = World(seed=world_seed, episode_kind=kind, **self._config)
                if (len(probe.wolf_group_sizes) == 2) == want_two:
                    break
                world_seed = int(self._seed_rng.integers(0, 2**31 - 1))
        return self._reset_world(world_seed, kind)

    def set_g_oversample(self, frac):
        """Contingencia de currículo: cambia (o apaga con None) el oversampling de G en caliente."""
        self._g_over = frac

    def reset_to(self, world_seed: int, kind: str):
        """Episodio CONCRETO (evaluación emparejada / baselines): misma semilla, mismo mundo."""
        return self._reset_world(int(world_seed), kind)

    def _reset_world(self, world_seed: int, kind: str):
        self._mgr = _ManagerDriven()
        self._layer = WolfOptionLayer(manager=self._mgr, frame_skip=self._frame_skip)
        self._world = World(seed=world_seed, episode_kind=kind, wolf_controller=self._layer,
                            **self._config)
        self._coord = self._make_coord(self._world)
        self._last_event = EV_INICIO
        self._decision_idx = 0
        self._log = []
        self._penetrado_ticks = 0
        self._last_action = None
        self._n_aborts = 0
        self._delib_paid = 0.0
        self._hunt = {"option_starts": 0, "retargets": 0, "retargets_blocked": 0,
                      "refix_muerte": 0, "refix_refugio": 0, "refix_otro": 0}
        self._patrol = PatrolCoverageTracker(self._world)
        self._ctx = {"option": None, "last_event": EV_INICIO, "decision_idx": 0,
                     "decoy_idx": None, "active_c_prev": None}
        w = self._world
        self._info_reset = {"episode_kind": kind, "world_seed": world_seed,
                            "n_wolves": int(w.n_wolves), "n_calves": int(w.n_calves),
                            "two_front": bool(len(w.wolf_group_sizes) == 2),
                            "grupos_spawn": [int(x) for x in w.wolf_group_sizes]}
        return self._obs(), dict(self._info_reset)

    def _obs(self):
        o = build_manager_obs(self._world, self._ctx)
        if self._ablate:
            o[19:21] = 0.0                            # RUN-M4: sin rasgos de progreso del cebo
        return o

    def _make_coord(self, w):
        opp = self._opponent
        if opp == "mix":
            opp = ("reactive", "run09")[int(self._seed_rng.integers(2))]
        if opp == "reactive":
            return ReactiveCoordinator(w)
        from rl.residual_drone_coordinator import ResidualDroneCoordinator
        path = RUN02_MODEL if opp == "run02" else RUN09_MODEL
        if path not in _MODEL_CACHE:
            from stable_baselines3 import PPO
            _MODEL_CACHE[path] = PPO.load(path, device="cpu")
        return ResidualDroneCoordinator(w, model=_MODEL_CACHE[path])

    # ------------------------------------------------------------------ #
    def _active_centroid(self):
        act = self._world.drones[self._world.drone_state == ACTIVE]
        return act.mean(axis=0) if act.shape[0] else None

    def _prey_state(self):
        w = self._world
        return (w.pack_prey_kind, int(w.pack_prey), w.pack_prey2_kind, int(w.pack_prey2))

    @staticmethod
    def _lost_cause(w, kind, idx) -> str:
        """Causa de una re-fijación NO debida a la regla, por el estado de la presa anterior."""
        if idx < 0 or kind is None:
            return "refix_otro"
        alive = w.calf_alive[idx] if kind == "calf" else w.cow_alive[idx]
        safe = w.calf_safe[idx] if kind == "calf" else w.cow_safe[idx]
        if not alive:
            return "refix_muerte"
        if safe:
            return "refix_refugio"
        return "refix_otro"

    def _update_hunt(self, before, rt_before) -> None:
        """Cuenta las re-fijaciones de presa de ESTE tick (pack_prey y pack_prey2: de una presa válida
        a OTRA válida) no explicadas por la regla de caza (cuyo contador propio ya las recoge)."""
        w = self._world
        after = self._prey_state()
        by_rule = self._layer.n_retargets - rt_before
        for k0, i0, k1, i1 in ((before[0], before[1], after[0], after[1]),
                               (before[2], before[3], after[2], after[3])):
            if i0 >= 0 and i1 >= 0 and (k0, i0) != (k1, i1):
                if by_rule > 0:
                    by_rule -= 1
                else:
                    self._hunt[self._lost_cause(w, k0, i0)] += 1

    def _bait_failed(self) -> bool:
        """ABORT_BAIT_FAILED (observable): ESCOLTA latcheada y >= ABORT_MIN_ACTIVE ACTIVE dentro de
        ±ABORT_CONE_DEG del rumbo del ASALTO (desde el centroide del rebaño). Solo se CONSULTA
        pre-show (Commit S2): el llamador lo gatea con not wolf_decoy_released."""
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
        # Commit Q: ¿decisión tras INTERRUPCIÓN (ABORT) que cambia de opción? => coste.
        delib = bool(self._last_event == EV_ABORT and self._last_action is not None
                     and a != self._last_action)
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
            prey_before = self._prey_state()
            rt_before = layer.n_retargets
            layer.refresh(w)                         # frontera: la capa aplica la opción vigente
            self._patrol.on_boundary()               # auditor de patrulla (Encargo 1e; pasivo)
            if self.on_boundary is not None:
                self.on_boundary(w, coord, layer)    # observador (EpisodeAudit.on_boundary); no toca nada
            wp = coord.act(w.get_observation())
            react = getattr(coord, "inner", coord)   # Reactive o la barrera interior del residual
            if getattr(react, "_pose_last_step", -10) != int(w.step_count) and w.phase == "ESCOLTA" \
                    and getattr(react, "_anchor", None) is not None:
                self._penetrado_ticks += 1           # contador PASIVO (no decide nada)
            _o, _r, terminated, truncated, _i = w.step(wp)
            ticks += 1
            self._update_hunt(prey_before, rt_before)   # contadores de caza (K-bis; solo reporte)
            if self.on_tick is not None:
                self.on_tick(w, coord, layer)        # observador (snapshots); no toca la dinámica
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
            if a != 0 and ticks >= ABORT_GRACE_TICKS and not w.wolf_decoy_released \
                    and self._bait_failed():
                # Commit S2 (adjudicación VERIF-0): el ABORT solo es evaluable ANTES del show —
                # un cebo que ya mostró y soltó el asalto no ha "fallado"; post-show la condición
                # era cierta de CONTINUO y el ABORT degeneraba en metrónomo de 50 ticks (verif0:
                # s67/s86/s98 con d2≈1-6 m). Post-release los terminales de CEBO son MUERTE /
                # HERD_SAFE / techo / FIN.
                event = EV_ABORT
                break
        reward = float(w.n_depredadas - deaths0) - (self._delib_cost if delib else 0.0)
        if delib:
            self._delib_paid += self._delib_cost
        if event == EV_ABORT:
            self._n_aborts += 1
        self._last_action = a
        self._decision_idx += 1
        self._last_event = event
        self._log.append({"decision": self._decision_idx, "action": a, "option": OPTION_NAMES[a],
                          "t0": t0, "ticks": ticks, "event": EVENT_NAMES[event], "reward": reward,
                          "delib": delib,
                          "n_wolves": int(w.n_wolves), "two_front": self._info_reset["two_front"]})
        self._ctx = {"option": a, "last_event": event, "decision_idx": self._decision_idx,
                     "decoy_idx": (layer.decoy_indices() if a != 0 else None),
                     "active_c_prev": active_c0}
        obs = self._obs()
        info = {"event": EVENT_NAMES[event], "ticks": ticks, "option": OPTION_NAMES[a],
                "decision_idx": self._decision_idx, **self._info_reset}
        if terminated or truncated:
            info["ep_sev"] = int(w.n_depredadas)     # SIEMPRE sin coste (la sev de las tablas)
            info["aborts"] = int(self._n_aborts)
            info["delib_pagado"] = round(float(self._delib_paid), 4)
            info["ep_decisions"] = self._decision_idx
            info["ep_log"] = list(self._log)
            info["penetrado_ticks"] = int(self._penetrado_ticks)
            info["status"] = w.status
            self._hunt["option_starts"] = int(layer.n_option_starts)
            self._hunt["retargets"] = int(layer.n_retargets)
            self._hunt["retargets_blocked"] = int(layer.n_retarget_blocked)
            info["hunt"] = dict(self._hunt)
            # MÉTRICA DE CENSURA (adjudicación VERIF-0): hitos de la jugada del episodio.
            info["jugada"] = {"t_staged": layer.t_staged, "t_show": layer.t_show,
                              "t_suelta": layer.t_suelta, "t_strike": layer.t_strike,
                              "completa": bool(layer.t_show is not None
                                               and layer.t_suelta is not None)}
            pat = self._patrol.finalize()
            info["patrulla"] = {k: pat[k] for k in
                                ("ticks_patrulla", "ticks_aviso", "ticks_violacion", "D_max",
                                 "R_media", "R_max", "entradas_no_detectadas",
                                 "entradas_no_detectadas_por_arco_violacion")}
        return obs, reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    @property
    def world(self):
        return self._world

    @property
    def episode_log(self):
        return list(self._log)
