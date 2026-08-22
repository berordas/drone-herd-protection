"""hrl/manager_drone.py — D2-FASE-2: MANAGER DEL BANDO DRON (semi-MDP por eventos sobre la capa
de reparto hrl/options_drone.AllocatorCoordinator) + MANAGER LOBO CONGELADO reproducido dentro
del arnés (el atacante de train/eval).

PREREGISTRO_D2 (congelado antes de este commit): receta ESPEJO del manager lobo que dio el
resultado principal de la Etapa 1.

  FrozenWolfManager      ckpt PPO del manager lobo (M1'''') reproducido DENTRO de otro arnés con
                         la MISMA lógica de eventos de ManagerEnv (MUERTE / HERD_SAFE / K_MAX /
                         ABORT pre-show con gracia 50) y decisión determinista (argmax).
                         Protocolo: on_tick(world, layer) tras cada world.step (detecta el evento
                         y fuerza la consulta: layer._countdown = 0) + decide(world, layer) como
                         manager de WolfOptionLayer. Equivalencia BIT A BIT con ManagerEnv
                         (hrl_check [D2-1]).
  DroneDecisionCore      la lógica del semi-MDP del dron (obs, eventos, tripwire, coste) reusable
                         por el env (train) y por el coordinador aprendido (eval).
  DroneManagerEnv        gym.Env: acción Discrete(3) {4-0, 3-1, 2-2}; un paso = una partición
                         hasta su evento terminal; recompensa = −Δmuertes − coste; atacante por
                         episodio {natural scriptado, manager lobo congelado}.
  LearnedAllocatorCoordinator  AllocatorCoordinator gobernado por un ckpt del manager dron:
                         interfaz de coordinador clásica (evals E0.4 sin tocar el arnés).

EVENTOS TERMINALES de toda partición: MUERTE · CAMBIO del nº de clústeres percibidos (la
INTERRUPCIÓN del bando dron; gracia 50 ticks tras arrancar la partición) · HERD_SAFE · techo
K_MAX=4500 · STALL (tripwire: guardias asignados >= 400 ticks SIN 2º clúster percibido => vuelta
FORZADA a 4-0, contador de salud) · FIN. COSTE DE DELIBERACIÓN (Q espejo): decisión tras una
INTERRUPCIÓN (CLUSTER_CHANGE o STALL) que CAMBIA de partición paga DELIB_COST=0.05; mantener o
decidir tras terminal natural es gratis. La sev de las tablas es SIEMPRE sin coste.

OBSERVACIÓN (DRONE_OBS_SIZE=44, percepción HONESTA del bando dron vía analyze_threats —
contactos ∪ confirmados, nunca verdad-terreno de los lobos; el latch/ancla del PROPIO frente es
conocimiento legítimo del equipo):
  [0:3]   clústeres percibidos: nº/3 · nº amenazas/6 · nº confirmados/6
  [3:8]   PRIMARIO: tamaño/5 · frac confirmados · rumbo (sin, cos) · dist al centroide/250
  [8:13]  SECUNDARIO: ídem (0 si no hay)
  [13:15] CIERRE: Δdist del primario y del secundario respecto al inicio del tramo anterior /50
  [15:23] OCTANTES: amenaza percibida por octante (8, 0/1)
  [23:27] DEFENSA: ACTIVE libres/4 · partición vigente one-hot(3) (todo 0 en la 1ª decisión)
  [27:29] ESCOLTA latcheada · ancla del frente presente
  [29:34] REBAÑO/RELOJ: en juego/6 · terneros vivos/2 · muertes/6 · reloj · a salvo/6
  [34:41] último evento one-hot(7) [INICIO, MUERTE, CLUSTER_CHANGE, HERD_SAFE, K_MAX, STALL, FIN]
  [41:42] nº de decisión/8 · [42:44] reservadas.
SIN RNG propio salvo el sorteo de atacante/tipo del episodio (stream del env)."""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from baseline import CONFIG_V2
from world import ACTIVE, World

from hrl.manager_env import (ABORT_CONE_DEG, ABORT_GRACE_TICKS, ABORT_MIN_ACTIVE, K_MAX,
                             OPTION_SPECS)
from hrl.manager_obs import (EV_ABORT, EV_FIN, EV_HERD_SAFE, EV_INICIO, EV_KMAX, EV_MUERTE,
                             build_manager_obs, herd_points)
from hrl.options_drone import AllocatorCoordinator, analyze_threats
from hrl.options_wolf import WolfOptionLayer
from rl.drone_obs import N_SEATS

WOLF_MANAGER_CKPT = "/data/hrl_m1/M1pppp/model.zip"    # el manager lobo CONGELADO (resultado principal)
_MODELS: dict = {}

PARTITIONS = ((4, 0), (3, 1), (2, 2))
PARTITION_NAMES = ("4-0", "3-1", "2-2")
N_ACTIONS = 3
DRONE_OBS_SIZE = 44
DELIB_COST_D2 = 0.05               # PREREGISTRO_D2: fallback único 0.1 (ligera 40k, interrupciones-con-cambio/ep > 10)
CLUSTER_GRACE_TICKS = 50           # gracia tras arrancar la partición antes de evaluar CLUSTER_CHANGE
GUARD_STALL_TICKS = 400            # tripwire: guardias >= 400 ticks sin 2º clúster => 4-0 forzado + STALL
N_EVD = 7
EVD_INICIO, EVD_MUERTE, EVD_CLUSTER, EVD_HERD_SAFE, EVD_KMAX, EVD_STALL, EVD_FIN = range(N_EVD)
EVD_NAMES = ("INICIO", "MUERTE", "CLUSTER_CHANGE", "HERD_SAFE", "K_MAX", "STALL", "FIN_EPISODIO")
ATTACKERS = ("natural", "manager")


def _load_model(path):
    if path not in _MODELS:
        from stable_baselines3 import PPO
        _MODELS[path] = PPO.load(path, device="cpu")
    return _MODELS[path]


# ====================================================================== #
class FrozenWolfManager:
    """Manager lobo CONGELADO dentro de otro arnés (ver cabecera). `model_path` ckpt PPO."""

    def __init__(self, model_path: str = WOLF_MANAGER_CKPT):
        self.model_path = model_path
        self.reset_state()

    def reset_state(self) -> None:
        self._ctx = {"option": None, "last_event": EV_INICIO, "decision_idx": 0,
                     "decoy_idx": None, "active_c_prev": None}
        self._seg_t0 = None
        self._deaths0 = 0
        self._active_c0 = None
        self._action = None
        self._current = None
        self._pending = True
        self._last_step = -1
        self.n_decisions = 0

    @staticmethod
    def _active_centroid(w):
        act = w.drones[w.drone_state == ACTIVE]
        return act.mean(axis=0) if act.shape[0] else None

    @staticmethod
    def _bait_failed(w, layer) -> bool:
        """Copia literal de ManagerEnv._bait_failed (observable; pre-show lo gatea el llamador)."""
        if w.phase != "ESCOLTA":
            return False
        asa = layer.assault_indices()
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

    def on_tick(self, w, layer) -> None:
        """Tras cada world.step: detecta el evento terminal del tramo (misma lógica y orden que
        ManagerEnv.step) y fuerza la consulta del manager en la frontera siguiente."""
        if self._seg_t0 is None or self._pending:
            return
        ticks = int(w.step_count) - self._seg_t0
        a = self._action
        event = None
        if int(w.n_depredadas) > self._deaths0:
            event = EV_MUERTE
        else:
            in_play = int((w.cow_alive & ~w.cow_safe).sum() + (w.calf_alive & ~w.calf_safe).sum())
            if in_play == 0:
                event = EV_HERD_SAFE
            elif ticks >= K_MAX:
                event = EV_KMAX
            elif a != 0 and ticks >= ABORT_GRACE_TICKS and not w.wolf_decoy_released \
                    and self._bait_failed(w, layer):
                event = EV_ABORT
        if event is None:
            return
        self._ctx = {"option": a, "last_event": event, "decision_idx": self.n_decisions,
                     "decoy_idx": (layer.decoy_indices() if a != 0 else None),
                     "active_c_prev": self._active_c0}
        self._pending = True
        layer._countdown = 0                             # consulta INMEDIATA en la frontera siguiente

    def decide(self, w, layer):
        step = int(w.step_count)
        if step < self._last_step:
            self.reset_state()
        self._last_step = step
        if not self._pending:
            return self._current                         # entre eventos: misma opción (sin re-arranque)
        obs = build_manager_obs(w, self._ctx)
        a, _ = _load_model(self.model_path).predict(obs, deterministic=True)
        a = int(a)
        self._action = a
        self._seg_t0 = step
        self._deaths0 = int(w.n_depredadas)
        self._active_c0 = self._active_centroid(w)
        self._pending = False
        self.n_decisions += 1
        name, params = OPTION_SPECS[a]
        self._current = (name, dict(params))
        return self._current


# ====================================================================== #
def build_drone_obs(w, coord: AllocatorCoordinator, ctx: dict) -> np.ndarray:
    o = np.zeros(DRONE_OBS_SIZE, dtype=np.float32)
    info = analyze_threats(w, coord.inner)
    herd = herd_points(w)
    herd_c = info["herd_c"]
    pts, is_conf, clusters = info["pts"], info["is_confirmed"], info["clusters"]
    o[0] = min(len(clusters), 3) / 3.0
    o[1] = min(pts.shape[0], 6) / 6.0
    o[2] = min(int(is_conf.sum()), 6) / 6.0
    dists = {}
    for slot, key in ((3, "primario"), (8, "secundario")):
        ci = info[key]
        if ci is None:
            continue
        cl = clusters[ci]
        p = pts[cl]
        c = p.mean(axis=0) - herd_c
        d = float(np.linalg.norm(c))
        ang = float(np.arctan2(c[1], c[0])) if d > 1e-9 else 0.0
        o[slot] = min(len(cl), 5) / 5.0
        o[slot + 1] = float(is_conf[cl].mean())
        o[slot + 2] = np.sin(ang)
        o[slot + 3] = np.cos(ang)
        o[slot + 4] = min(d, 250.0) / 250.0
        dists[key] = d
    prev = ctx.get("dist_prev") or {}
    for k, key in ((13, "primario"), (14, "secundario")):
        if key in dists and key in prev:
            o[k] = float(np.clip((prev[key] - dists[key]) / 50.0, -1.0, 1.0))
    if pts.shape[0]:
        rel = pts - herd_c
        ang = np.arctan2(rel[:, 1], rel[:, 0])
        octs = ((np.round(ang / (np.pi / 4)).astype(int)) % 8)
        for k in np.unique(octs):
            o[15 + int(k)] = 1.0
    free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
    o[23] = min(int(free.sum()), N_SEATS) / float(N_SEATS)
    if ctx.get("action") is not None:
        o[24 + int(ctx["action"])] = 1.0
    o[27] = 1.0 if w.phase == "ESCOLTA" else 0.0
    o[28] = 1.0 if getattr(coord.inner, "_anchor", None) is not None else 0.0
    o[29] = min(herd.shape[0], 6) / 6.0
    o[30] = (min(int((w.calf_alive & ~w.calf_safe).sum()), 2) / 2.0) if w.n_calves else 0.0
    o[31] = min(int(w.n_depredadas), 6) / 6.0
    o[32] = min(int(w.step_count) / float(max(w.max_episode_steps, 1)), 1.0)
    o[33] = min(int(w.cow_safe.sum() + (w.calf_safe.sum() if w.n_calves else 0)), 6) / 6.0
    o[34 + int(ctx.get("last_event", EVD_INICIO))] = 1.0
    o[41] = min(int(ctx.get("decision_idx", 0)), 8) / 8.0
    return o


class DroneDecisionCore:
    """El semi-MDP del dron, reusable: begin(a) al arrancar una partición; tick() tras cada
    world.step devuelve el evento terminal (o None). Mantiene el reloj del tripwire."""

    def __init__(self, world, coord: AllocatorCoordinator, k_max: int = K_MAX):
        self.w, self.coord, self.k_max = world, coord, int(k_max)
        self.action = None
        self.last_event = EVD_INICIO
        self.decision_idx = 0
        self.n_interrupciones = 0
        self.n_stalls = 0
        self.n_cambios = 0
        self.deaths0 = 0
        self.t0 = 0
        self.n_clusters0 = 0
        self.dist_prev = {}
        self._dist_seg0 = {}
        self._guard_noshow = 0

    def n_clusters(self) -> int:
        return len(analyze_threats(self.w, self.coord.inner)["clusters"])

    def _dists(self) -> dict:
        info = analyze_threats(self.w, self.coord.inner)
        out = {}
        for key in ("primario", "secundario"):
            ci = info[key]
            if ci is not None:
                c = info["pts"][info["clusters"][ci]].mean(axis=0) - info["herd_c"]
                out[key] = float(np.linalg.norm(c))
        return out

    def ctx(self) -> dict:
        return {"action": self.action, "last_event": self.last_event,
                "decision_idx": self.decision_idx, "dist_prev": self.dist_prev}

    def begin(self, a: int) -> None:
        if self.action is not None and a != self.action:
            self.n_cambios += 1
        self.action = int(a)
        self.coord.set_particion(PARTITIONS[a])
        self.t0 = int(self.w.step_count)
        self.deaths0 = int(self.w.n_depredadas)
        self.n_clusters0 = self.n_clusters()
        self.dist_prev = dict(self._dist_seg0)
        self._dist_seg0 = self._dists()
        self._guard_noshow = 0

    def tick(self):
        w = self.w
        ticks = int(w.step_count) - self.t0
        if int(w.n_depredadas) > self.deaths0:
            return EVD_MUERTE
        in_play = int((w.cow_alive & ~w.cow_safe).sum() + (w.calf_alive & ~w.calf_safe).sum())
        if in_play == 0:
            return EVD_HERD_SAFE
        if ticks >= self.k_max:
            return EVD_KMAX
        info = analyze_threats(w, self.coord.inner)
        if PARTITIONS[self.action][1] > 0:
            if info["secundario"] is None:
                self._guard_noshow += 1
                if self._guard_noshow >= GUARD_STALL_TICKS:
                    self.n_stalls += 1
                    self.coord.set_particion(PARTITIONS[0])   # TRIPWIRE: 4-0 forzado
                    self.action = 0                            # la partición VIGENTE pasa a ser 4-0:
                    return EVD_STALL                           # re-asignar guardias después = CAMBIO (paga)
            else:
                self._guard_noshow = 0
        if ticks >= CLUSTER_GRACE_TICKS and len(info["clusters"]) != self.n_clusters0:
            return EVD_CLUSTER
        return None

    def end(self, event: int) -> None:
        self.last_event = int(event)
        self.decision_idx += 1
        if event in (EVD_CLUSTER, EVD_STALL):
            self.n_interrupciones += 1


class DroneManagerEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, kinds=("lobos", "mixto"), seed=None, attackers=ATTACKERS, k_max=K_MAX,
                 delib_cost: float = DELIB_COST_D2, wolf_ckpt: str = WOLF_MANAGER_CKPT):
        super().__init__()
        self._kinds = tuple(kinds)
        self._attackers = tuple(attackers)
        self._k_max = int(k_max)
        self._delib = float(delib_cost)
        self._wolf_ckpt = wolf_ckpt
        self._seed_rng = np.random.default_rng(seed)
        self.observation_space = gym.spaces.Box(-1.0, 1.0, (DRONE_OBS_SIZE,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(N_ACTIONS)
        self._world = self._coord = self._core = self._frozen = self._layer = None
        self._last_action = None
        self._delib_paid = 0.0
        self._log = []
        self._penetrado = 0
        self._info_reset = {}
        self.on_tick = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        ws = int(self._seed_rng.integers(0, 2**31 - 1))
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]
        atk = self._attackers[int(self._seed_rng.integers(len(self._attackers)))]
        return self.reset_to(ws, kind, atk)

    def reset_to(self, world_seed: int, kind: str, attacker: str = "natural"):
        self._frozen = self._layer = None
        wc = None
        if attacker == "manager":
            self._frozen = FrozenWolfManager(self._wolf_ckpt)
            self._layer = WolfOptionLayer(manager=self._frozen, frame_skip=5)
            wc = self._layer
        self._world = World(seed=int(world_seed), episode_kind=kind, wolf_controller=wc, **CONFIG_V2)
        self._coord = AllocatorCoordinator(self._world, particion=PARTITIONS[0])
        self._core = DroneDecisionCore(self._world, self._coord, self._k_max)
        self._last_action = None
        self._delib_paid = 0.0
        self._log = []
        self._penetrado = 0
        w = self._world
        self._info_reset = {"episode_kind": kind, "world_seed": int(world_seed), "attacker": attacker,
                            "n_wolves": int(w.n_wolves), "two_front": bool(len(w.wolf_group_sizes) == 2)}
        return build_drone_obs(w, self._coord, self._core.ctx()), dict(self._info_reset)

    def step(self, action):
        a = int(action)
        assert 0 <= a < N_ACTIONS, a
        w, coord, core = self._world, self._coord, self._core
        interrupted = core.last_event in (EVD_CLUSTER, EVD_STALL)
        # Coste (Q espejo): tras una INTERRUPCIÓN, cambiar respecto a la partición VIGENTE paga
        # (tras STALL la vigente es el 4-0 forzado: re-pedir guardias de inmediato paga — sin esto
        # el tripwire degeneraba en metrónomo de 400 ticks, medido en el smoke: 25 interr/ep).
        delib = bool(interrupted and core.action is not None and a != core.action)
        core.begin(a)
        deaths0 = int(w.n_depredadas)
        t0 = int(w.step_count)
        event = None
        terminated = truncated = False
        ticks = 0
        while True:
            if self._layer is not None:
                self._layer.refresh(w)                   # frontera del manager lobo congelado
            wp = coord.act(w.get_observation())
            react = coord.inner
            if getattr(react, "_pose_last_step", -10) != int(w.step_count) and w.phase == "ESCOLTA" \
                    and getattr(react, "_anchor", None) is not None:
                self._penetrado += 1
            _o, _r, terminated, truncated, _i = w.step(wp)
            ticks += 1
            if self._frozen is not None:
                self._frozen.on_tick(w, self._layer)
            if self.on_tick is not None:
                self.on_tick(w, coord, self._layer)
            if terminated or truncated:
                event = EVD_FIN
                break
            event = core.tick()
            if event is not None:
                break
        reward = -float(w.n_depredadas - deaths0) - (self._delib if delib else 0.0)
        if delib:
            self._delib_paid += self._delib
        core.end(event)
        self._log.append({"decision": core.decision_idx, "action": a, "particion": PARTITION_NAMES[a],
                          "t0": t0, "ticks": ticks, "event": EVD_NAMES[event], "reward": reward,
                          "delib": delib})
        obs = build_drone_obs(w, coord, core.ctx())
        info = {"event": EVD_NAMES[event], "ticks": ticks, "particion": PARTITION_NAMES[a],
                "decision_idx": core.decision_idx, **self._info_reset}
        if terminated or truncated:
            info["ep_sev"] = int(w.n_depredadas)
            info["ep_decisions"] = core.decision_idx
            info["ep_log"] = list(self._log)
            info["interrupciones"] = int(core.n_interrupciones)
            info["cambios"] = int(core.n_cambios)
            info["stalls"] = int(core.n_stalls)
            info["delib_pagado"] = round(self._delib_paid, 4)
            info["penetrado_ticks"] = int(self._penetrado)
            info["status"] = w.status
            if self._layer is not None:
                info["jugada_atacante"] = {"t_show": self._layer.t_show, "t_suelta": self._layer.t_suelta,
                                           "completa": bool(self._layer.t_show is not None
                                                            and self._layer.t_suelta is not None)}
        return obs, reward, terminated, truncated, info

    @property
    def world(self):
        return self._world


# ====================================================================== #
class LearnedAllocatorCoordinator(AllocatorCoordinator):
    """AllocatorCoordinator gobernado por un ckpt del manager dron (EVAL): misma lógica de eventos
    que DroneManagerEnv — el evento del paso anterior se evalúa al principio de act() (estado
    post-step) y la decisión se aplica en esa misma frontera, como en el env."""

    def __init__(self, world, model_path: str, k_max: int = K_MAX):
        super().__init__(world, particion=PARTITIONS[0])
        self.model_path = model_path
        self.core = DroneDecisionCore(world, self, k_max)
        self._started = False
        self._last_step = -1
        self._pending = True

    def act(self, observation=None):
        w = self.world
        step = int(w.step_count)
        if step < self._last_step:
            self.core = DroneDecisionCore(w, self, self.core.k_max)
            self._pending = True
        self._last_step = step
        if not self._pending and self.core.action is not None and step > self.core.t0:
            ev = self.core.tick()
            if ev is not None:
                self.core.end(ev)
                self._pending = True
        if self._pending:
            obs = build_drone_obs(w, self, self.core.ctx())
            a, _ = _load_model(self.model_path).predict(obs, deterministic=True)
            self.core.begin(int(a))
            self._pending = False
        return super().act(observation)
