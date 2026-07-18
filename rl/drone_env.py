"""drone_env.py — Env de EQUIPO del MARL de drones (agente = PUESTO) + desapilador VecEnv.

DOS capas, y la elección de API documentada aquí:
- `DroneTeamEnv` (gym.Env "CONJUNTO"): UN mundo por env; obs = las 4 obs por puesto apiladas
  ((N_SEATS·AGENT_OBS_SIZE,)) y acción = las 4 δ apiladas ((N_SEATS·2,)). Ser un gym.Env normal
  permite reutilizar `SubprocVecEnv(fork)` TAL CUAL (paralelismo por procesos, como los lobos).
- `TeamUnstackVecEnv` (VecEnvWrapper): convierte M envs conjuntos en 4·M STREAMS por-agente
  (obs (AGENT_OBS_SIZE,), acción (2,)) — el PPO de SB3 ve 4M "envs" y entrena UNA política
  COMPARTIDA con la obs local de cada puesto = MAPPO con parameter sharing (el crítico
  centralizado va dentro de la política: SplitMlpExtractor en rl/train_drones.py enruta la
  mitad local a π y la global a V). Sin PettingZoo: no añade nada aquí (la API multi-agente se
  reduce a este desapilado) y el contenedor queda SIN dependencias nuevas.

RECOMPENSA (dos componentes, SIEMPRE registradas por separado — vigilancia anti-proxy):
- GLOBAL (compartida): −1 × Δ(n_depredadas) en el tramo — la métrica que importa, la severidad
  con signo. Idéntica para los 4 puestos.
- LOCAL (por puesto): +local_coef por cada (lobo, paso) EXPULSADO cuyo causante es el dron del
  puesto — atribución DETERMINISTA recomputada del estado expuesto, con la regla del mundo
  (el lobo huye del dron ACTIVE acercándose MÁS CERCANO; world._apply_deterrence): ingredientes
  `_wolf_scared`, `drones`, `drone_vel`, `drone_state`, `wolves` + DETER_RADIUS /
  SCARE_APPROACH_MIN. Se recomputa en la frontera POSTERIOR al paso (el lobo ya huyó medio
  paso): misma regla, medio paso después — determinista y sin tocar el mundo.
- `info` por paso: `r_global`, `r_local` (N_SEATS,), `agent_rewards` (N_SEATS,) = global +
  local_coef·local. Al terminal: `ep_severity` (= n_depredadas del episodio) y `ep_deter`
  (Σ eventos de disuasión atribuidos). LA VARA FINAL ES LA SEVERIDAD DEL ARNÉS (drone_eval),
  nunca la recompensa.

EPISODIOS: los TRES tipos (lobos / mixto / corzos) ~1/3 — en solo-corzos la severidad es 0 pero
se aprende a NO dispersarse/malgastar (patrulla; el reflejo de investigación roba drones).
Semilla FRESCA por reset de una secuencia propia (como wolf_env: `World.reset(None)` repite).
Adversario: ScriptedWolfController v2.6 (el default del World — no se inyecta nada).
El frame-skip (5) y la δ mantenida entre fronteras van por `ResidualDroneCoordinator` en modo
entrenamiento (set_delta + act cada paso de física) — MISMO camino de código que la evaluación.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from stable_baselines3.common.vec_env.base_vec_env import VecEnvWrapper

from world import ACTIVE, DETER_RADIUS, SCARE_APPROACH_MIN, World
from baseline import CONFIG_V2

from rl.drone_obs import AGENT_OBS_SIZE, N_SEATS
from rl.residual_drone_coordinator import ResidualDroneCoordinator

TEAM_KINDS = ("lobos", "mixto", "corzos")   # los TRES (a diferencia de los lobos: aquí corzos enseña a no malgastar)
LOCAL_COEF_DEFAULT = 0.01                   # peso del bono local de disuasión (afinable; queda en config.json)


def deter_credit(world, seats: np.ndarray) -> np.ndarray:
    """(N_SEATS,) nº de lobos EXPULSADOS este paso atribuidos al dron de cada puesto.
    Regla del mundo (world._apply_deterrence): el lobo asustado huye del dron ACTIVE
    ACERCÁNDOSE (aproximación > SCARE_APPROACH_MIN, distancia <= DETER_RADIUS) MÁS CERCANO.
    Recomputado del estado expuesto en la frontera posterior al paso (solo lectura)."""
    w = world
    out = np.zeros(N_SEATS)
    if w.n_wolves == 0 or not w._wolf_scared.any():
        return out
    act_idx = np.where(w.drone_state == ACTIVE)[0]
    if act_idx.size == 0:
        return out
    rel = w.wolves[:, None, :] - w.drones[act_idx][None, :, :]          # (nw,na,2) dron->lobo
    dd = np.linalg.norm(rel, axis=2)
    units = rel / np.maximum(dd[:, :, None], 1e-9)
    approach = np.sum(w.drone_vel[act_idx][None, :, :] * units, axis=2)
    approaching = (dd <= DETER_RADIUS) & (approach > SCARE_APPROACH_MIN)
    seat_of = {int(d): k for k, d in enumerate(seats) if d >= 0}
    for j in np.where(w._wolf_scared)[0]:
        cand = approaching[j]
        if not cand.any():
            continue                                   # medio paso después ya no se le acerca nadie: sin crédito
        d = int(act_idx[np.argmin(np.where(cand, dd[j], np.inf))])
        k = seat_of.get(d)
        if k is not None:
            out[k] += 1.0
    return out


class DroneTeamEnv(gym.Env):
    """Env CONJUNTO del equipo de drones (un mundo; 4 puestos). Ver cabecera del módulo."""

    metadata = {"render_modes": []}

    def __init__(self, kinds: tuple[str, ...] = TEAM_KINDS, frame_skip: int = 5,
                 seed: int | None = None, config: dict | None = None,
                 residual_scale: float | None = None, local_coef: float = LOCAL_COEF_DEFAULT):
        super().__init__()
        kinds = tuple(kinds)
        if not kinds or any(k not in TEAM_KINDS for k in kinds):
            raise ValueError("kinds debe ser un subconjunto no vacío de %r; recibido %r"
                             % (TEAM_KINDS, kinds))
        self._kinds = kinds
        self._frame_skip = int(frame_skip)
        self._config = dict(CONFIG_V2 if config is None else config)
        self._residual_scale = residual_scale
        self._local_coef = float(local_coef)
        self._seed_rng = np.random.default_rng(seed)   # secuencia PROPIA de semillas de episodio
        self._world: World | None = None
        self._ctrl: ResidualDroneCoordinator | None = None
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(N_SEATS * 2,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf,
                                                shape=(N_SEATS * AGENT_OBS_SIZE,), dtype=np.float32)

    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        world_seed = int(self._seed_rng.integers(0, 2**31 - 1))   # SIEMPRE semilla fresca
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]
        self._world = World(seed=world_seed, episode_kind=kind, **self._config)
        self._ctrl = ResidualDroneCoordinator(self._world, model=None,
                                              frame_skip=self._frame_skip,
                                              residual_scale=self._residual_scale)
        self._world.reset()
        self._ep_deter = 0.0
        info = {"episode_kind": kind, "world_seed": world_seed,
                "n_wolves": int(self._world.n_wolves)}
        return self._joint_obs(), info

    def step(self, action):
        w = self._world
        a = np.clip(np.asarray(action, dtype=np.float32).reshape(N_SEATS, 2), -1.0, 1.0)
        self._ctrl.set_delta(a * self._ctrl.residual_scale)   # δ en metros; mantenida en el tramo
        deaths0 = w.n_depredadas
        deter = np.zeros(N_SEATS)
        terminated = truncated = False
        for _ in range(self._frame_skip):
            wp = self._ctrl.act(w.get_observation())
            _o, _r, terminated, truncated, _i = w.step(wp)
            deter += deter_credit(w, self._ctrl.seats())
            if terminated or truncated:
                break
        r_global = -float(w.n_depredadas - deaths0)           # −1 por res matada (compartida)
        agent_rewards = r_global + self._local_coef * deter
        self._ep_deter += float(deter.sum())
        info = {"r_global": r_global, "r_local": deter.copy(),
                "agent_rewards": agent_rewards.astype(np.float64)}
        if terminated or truncated:
            info["ep_severity"] = int(w.n_depredadas)         # LA métrica (la del arnés)
            info["ep_deter"] = self._ep_deter
        return self._joint_obs(), float(agent_rewards.mean()), terminated, truncated, info

    # ------------------------------------------------------------------ #
    def _joint_obs(self) -> np.ndarray:
        return self._ctrl.agent_obs(self._world).ravel()


class TeamUnstackVecEnv(VecEnvWrapper):
    """M envs CONJUNTOS -> 4·M streams POR-AGENTE para el PPO de SB3 (MAPPO con parameter
    sharing): obs (AGENT_OBS_SIZE,), acción (2,), recompensa la de SU puesto
    (info['agent_rewards']); done compartido por los 4 streams de un mundo."""

    def __init__(self, venv):
        obs_space = gym.spaces.Box(-np.inf, np.inf, shape=(AGENT_OBS_SIZE,), dtype=np.float32)
        act_space = gym.spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        super().__init__(venv, observation_space=obs_space, action_space=act_space)
        self.n_teams = venv.num_envs
        self.num_envs = venv.num_envs * N_SEATS

    def reset(self):
        obs = self.venv.reset()                                    # (M, 4·D)
        return obs.reshape(self.n_teams * N_SEATS, AGENT_OBS_SIZE)

    def step_async(self, actions):
        self.venv.step_async(np.asarray(actions).reshape(self.n_teams, N_SEATS * 2))

    def step_wait(self):
        obs, _rews, dones, infos = self.venv.step_wait()
        obs = obs.reshape(self.num_envs, AGENT_OBS_SIZE)
        rewards = np.zeros(self.num_envs, dtype=np.float64)
        out_dones = np.repeat(dones, N_SEATS)
        out_infos = []
        for m, info in enumerate(infos):
            ar = info.get("agent_rewards")
            term_obs = info.get("terminal_observation")
            for k in range(N_SEATS):
                s = dict(info)
                s.pop("agent_rewards", None)
                if ar is not None:
                    rewards[m * N_SEATS + k] = float(ar[k])
                if term_obs is not None:                           # obs terminal del stream k
                    s["terminal_observation"] = np.asarray(term_obs).reshape(
                        N_SEATS, AGENT_OBS_SIZE)[k]
                out_infos.append(s)
        return obs, rewards, out_dones, out_infos
