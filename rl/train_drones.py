"""train_drones.py — Entrenamiento MAPPO/CTDE del MARL de drones (residual sobre la barrera).

MAPPO SOBRE EL SB3 PINNEADO (sin dependencias nuevas): PPO con
- ACTOR COMPARTIDO DESCENTRALIZADO: una sola red π; cada PUESTO de barrera es un "stream" del
  VecEnv (TeamUnstackVecEnv: M mundos → 4·M streams) y π solo ve la mitad LOCAL de la obs.
- CRÍTICO CENTRALIZADO: V ve la mitad GLOBAL privilegiada (rl.obs.build_obs — verdad-terreno,
  CTDE). El enrutado lo hace `SplitMlpExtractor` dentro de la política (π ← obs[:LOCAL_SIZE],
  V ← obs[LOCAL_SIZE:]); en ejecución solo se usa π ⇒ ejecución 100% descentralizada.
Es el algoritmo MAPPO (Yu et al. 2022) implementado con la mecánica de SB3 (parameter sharing).

RESIDUAL (RPL, la receta de run04/run05): acción = δ ∈ [-1,1]² × residual_scale (def.
DETER_RADIUS=20 m) SUMADA al waypoint que propone la barrera; init δ≡0 EXACTO (última capa a
cero, verificado por assert) + log_std −2; DOS FASES (fase 1 solo-crítico con π congelada —
las evals ligeras deben CLAVARSE en el SUELO 2.80 (ligera 5 lobos+5 mixto) / 2.74/2.82
(arnés) —, fase 2 PPO). Con δ≡0 el coordinador ES la barrera (rl_env_check test 10).

MÉTRICA: SEVERIDAD (muertes/episodio) — MENOS = MEJOR (¡signo contrario a los lobos!). El
éxito es BAJAR de 2.74/2.82 (barrera v2.6) en el arnés de 100 semillas (rl/drone_eval.py).
La recompensa (global −1/muerte + local de disuasión) es el VEHÍCULO, no la vara: el log
registra ep_sev y ep_deter POR SEPARADO (vigilancia anti-proxy).

CONTABILIDAD DE PASOS: num_timesteps de SB3 cuenta pasos de STREAM (= pasos-agente); con 4
puestos, pasos de mundo ≈ total_steps / 4 (y cada paso de mundo son frame_skip=5 de física).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch as th
from torch import nn

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

import sys
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rl.drone_env import DroneTeamEnv, TeamUnstackVecEnv, TEAM_KINDS, LOCAL_COEF_DEFAULT
from rl.drone_obs import AGENT_OBS_SIZE, LOCAL_SIZE, N_SEATS
from rl.residual_drone_coordinator import DRONE_RESIDUAL_SCALE_DEFAULT, ResidualDroneCoordinator
from rl.train_wolves import HYPER, NET_ARCH, RESIDUAL_LOG_STD_INIT   # mismos hiperparámetros base

ABORT_NOTE_DRONES = (
    "PACTO run01 (guardias INVERTIDAS — MENOS severidad = MEJOR, ¡signo contrario a los lobos!): "
    "el SUELO es la barrera v2.6 (2.74/0/2.82 en el arnés; eval ligera 10 eps 5 lobos+5 mixto "
    "con δ=0 = 2.80 EXACTO, detalle [3,0,3,4,4 | 4,0,3,2,5]). FASE 1 (solo-crítico, δ medio 0): "
    "las ligeras deben CLAVARSE en ese suelo. GUARDIA DE EROSIÓN: ligera SOSTENIDA por encima "
    "de ~2.9 en fase 2 durante ≥1,5M pasos-agente → PARAR y reportar (la red estropea la "
    "barrera; palancas —bajar lr / alargar fase 1— = decisión del usuario). GUARDIA ANTI-PROXY "
    "(el riesgo asumido con la recompensa local): si ep_deter SUBE pero ep_sev NO baja (o "
    "empeora) de forma sostenida ≥2M pasos-agente → PARAR y avisar (la política cultiva el "
    "proxy: perseguir lobos rompiendo la barrera; mitigación —quitar la componente local y "
    "seguir con recompensa global pura— = decisión del usuario); cada eval ligera imprime el "
    "buffer (ep_sev, ep_deter) para esta vigilancia. SIN aborto por estancamiento: el suelo es "
    "útil (δ≈0 = la barrera); no bajar de 2.74/2.82 NO es fracaso catastrófico. ÉXITO = bajar "
    "la severidad de forma CLARA y SOSTENIDA; la vara final es el arnés de 100 semillas "
    "(rl/drone_eval.py), no la recompensa.")


# ------------------------------------------------------------------ #
# MAPPO sobre SB3: extractor que ENRUTA la obs compuesta [local ‖ global]
# ------------------------------------------------------------------ #
class SplitMlpExtractor(nn.Module):
    """π ve obs[..., :LOCAL_SIZE] (la obs LOCAL del puesto); V ve obs[..., LOCAL_SIZE:] (la
    GLOBAL privilegiada). Sustituye al MlpExtractor de SB3 (misma interfaz: forward /
    forward_actor / forward_critic + latent_dim_pi/vf)."""

    def __init__(self, local_dim: int, global_dim: int, net_arch, activation_fn):
        super().__init__()
        self.local_dim = local_dim

        def mlp(in_dim):
            layers, last = [], in_dim
            for h in net_arch:
                layers += [nn.Linear(last, h), activation_fn()]
                last = h
            return nn.Sequential(*layers), last

        self.policy_net, self.latent_dim_pi = mlp(local_dim)
        self.value_net, self.latent_dim_vf = mlp(global_dim)

    def forward(self, features):
        return self.forward_actor(features), self.forward_critic(features)

    def forward_actor(self, features):
        return self.policy_net(features[..., : self.local_dim])

    def forward_critic(self, features):
        return self.value_net(features[..., self.local_dim:])


class MAPPOPolicy(ActorCriticPolicy):
    """ActorCriticPolicy de SB3 con el extractor partido (crítico centralizado, CTDE)."""

    def _build_mlp_extractor(self) -> None:
        assert self.features_dim == AGENT_OBS_SIZE, \
            "MAPPOPolicy espera la obs compuesta [local ‖ global] (%d)" % AGENT_OBS_SIZE
        self.mlp_extractor = SplitMlpExtractor(LOCAL_SIZE, AGENT_OBS_SIZE - LOCAL_SIZE,
                                               NET_ARCH, self.activation_fn).to(self.device)


# ------------------------------------------------------------------ #
def make_env(seed: int, kinds, frame_skip: int, residual_scale, local_coef: float):
    def _thunk():
        return DroneTeamEnv(kinds=kinds, frame_skip=frame_skip, seed=seed,
                            residual_scale=residual_scale, local_coef=local_coef)
    return _thunk


class TrainLog(BaseCallback):
    """train.log legible (calca del de lobos, semántica de drones): ep_rew (recompensa del
    stream) + ep_sev / ep_deter (las componentes por separado, anti-proxy) + ep_len."""

    def __init__(self, path: Path, run_desc: str, abort_note: str, every_steps: int = 25_000):
        super().__init__()
        self.path, self.run_desc, self.abort_note = Path(path), run_desc, abort_note
        self.every = every_steps
        self._t0 = None
        self._last = 0
        self._rew, self._sev, self._det, self._len = [], [], [], []

    def _on_training_start(self) -> None:
        if self._t0 is not None:
            return                      # segunda learn() (fase 2): sin cabecera repetida
        self._t0 = time.time()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] ARRANQUE  {self.run_desc}\n")
            f.write(self.abort_note + "\n")
            f.write("columnas: timestamp | pasos(agente) | fps | ep_rew_mean (últ. 100 streams) | "
                    "ep_sev_mean (MENOS=mejor) | ep_deter_mean | ep_len_mean\n")

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", ()):
            ep = info.get("episode")
            if ep is not None:
                self._rew.append(float(ep["r"])); self._len.append(int(ep["l"]))
                if "ep_severity" in info:
                    self._sev.append(float(info["ep_severity"]))
                    self._det.append(float(info["ep_deter"]))
        if self.num_timesteps - self._last >= self.every:
            self._last = self.num_timesteps
            fps = self.num_timesteps / max(time.time() - self._t0, 1e-9)
            r = np.mean(self._rew[-100:]) if self._rew else float("nan")
            s = np.mean(self._sev[-100:]) if self._sev else float("nan")
            d = np.mean(self._det[-100:]) if self._det else float("nan")
            ln = np.mean(self._len[-100:]) if self._len else float("nan")
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat(timespec='seconds')}] pasos={self.num_timesteps:>11,}  "
                        f"fps={fps:>7.1f}  ep_rew_mean={r:>7.3f}  ep_sev_mean={s:>6.3f}  "
                        f"ep_deter_mean={d:>8.1f}  ep_len_mean={ln:>7.1f}\n")
        return True


class LightEval(BaseCallback):
    """Eval ligera DETERMINISTA cada eval_every pasos(agente): 10 semillas FIJAS de lobos+mixto
    (5+5, arnés real build_world + run_episode_metrics) con el coordinador residual sirviendo el
    modelo EN TRAINING. Reporta SEVERIDAD (menos = mejor; suelo δ=0 = 2.80 EXACTO, detalle
    [3,0,3,4,4 | 4,0,3,2,5]) y el buffer (ep_sev, ep_deter) del TrainLog en cada línea — la
    vigilancia ANTI-PROXY del pacto se lee eval a eval."""

    EVAL_SPECS = tuple((s, "lobos") for s in range(5)) + tuple((s, "mixto") for s in range(5))

    def __init__(self, path: Path, eval_every: int, residual_scale, train_log: "TrainLog | None" = None):
        super().__init__()
        self.path = Path(path)
        self.every = int(eval_every)
        self.residual_scale = residual_scale
        self.train_log = train_log
        self._next = self.every

    def _on_step(self) -> bool:
        if self.every <= 0 or self.num_timesteps < self._next:
            return True
        self._next += self.every
        from baseline import build_world, run_episode_metrics
        t0 = time.time()
        sev = []
        for s, kind in self.EVAL_SPECS:
            w = build_world(s, kind)
            coord = ResidualDroneCoordinator(w, model=self.model,
                                             residual_scale=self.residual_scale)
            sev.append(run_episode_metrics(w, coord)["n_depredadas"])
        lob, mix = sev[:5], sev[5:]
        buf = ""
        if self.train_log is not None and self.train_log._sev:
            buf = (f"  buffer: ep_sev={np.mean(self.train_log._sev[-100:]):.2f} "
                   f"ep_deter={np.mean(self.train_log._det[-100:]):.1f}")
        line = (f"[{datetime.now().isoformat(timespec='seconds')}] EVAL_LIGERA pasos={self.num_timesteps:>11,}  "
                f"severidad_media={np.mean(sev):.2f}  (lobos {np.mean(lob):.2f} | mixto {np.mean(mix):.2f}; "
                f"n=10 determinista; MENOS=mejor; suelo=2.80; detalle={sev}; "
                f"{time.time() - t0:.0f}s){buf}")
        print("  " + line)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True


# ------------------------------------------------------------------ #
def main() -> None:
    p = argparse.ArgumentParser(description="MAPPO/CTDE residual de drones (SB3 pinneado, sin deps nuevas)")
    p.add_argument("--total-steps", type=int, default=1_000_000,
                   help="pasos de STREAM (pasos-agente; mundo ≈ /4)")
    p.add_argument("--n-envs", type=int, default=8, help="nº de MUNDOS en paralelo (streams = 4×)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", type=str, default=None, help="def. /data/drones/<timestamp> (¡fuera del repo!)")
    p.add_argument("--kinds", type=str, default="lobos,mixto,corzos", help="tipos (coma; los 3 por defecto)")
    p.add_argument("--device", type=str, default="cpu")
    p.add_argument("--frame-skip", type=int, default=5)
    p.add_argument("--eval-every", type=int, default=250_000, help="eval ligera cada N pasos-agente; 0=off")
    p.add_argument("--lr", type=float, default=None, help="override del learning rate")
    p.add_argument("--residual-scale", type=float, default=None,
                   help="autoridad de δ en metros (def. DETER_RADIUS=20)")
    p.add_argument("--local-coef", type=float, default=LOCAL_COEF_DEFAULT,
                   help="peso del bono local de disuasión (anti-proxy: vigilar ep_sev vs ep_deter)")
    p.add_argument("--phase1-steps", type=int, default=1_000_000,
                   help="pasos-agente de FASE 1 (solo crítico, π congelada); 0 = sin fase 1")
    p.add_argument("--smoke", action="store_true", help="preset humo: 60k pasos-agente, 3 mundos")
    args = p.parse_args()

    if args.smoke:
        args.total_steps = 60_000
        args.n_envs = 3
        if args.phase1_steps >= args.total_steps:
            args.phase1_steps = 20_000

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    if any(k not in TEAM_KINDS for k in kinds):
        p.error("--kinds debe ser subconjunto de %r" % (TEAM_KINDS,))

    outdir = Path(args.outdir) if args.outdir else Path("/data/drones") / datetime.now().strftime("%Y%m%d-%H%M%S")
    hyper = dict(HYPER)
    if args.lr is not None:
        hyper["learning_rate"] = args.lr
    scale = args.residual_scale if args.residual_scale is not None else DRONE_RESIDUAL_SCALE_DEFAULT

    print("=== train_drones (MAPPO/CTDE residual sobre la barrera v2.6; SB3 pinneado) ===")
    print(f"  mundos = {args.n_envs} (SubprocVecEnv fork) -> streams = {args.n_envs * N_SEATS}  |  device = {args.device}")
    print(f"  kinds = {kinds}  |  frame_skip = {args.frame_skip}  |  total_steps(agente) = {args.total_steps:,}")
    print(f"  residual_scale = {scale} m  |  local_coef = {args.local_coef}  |  outdir = {outdir}")

    outdir.mkdir(parents=True, exist_ok=True)
    probe = outdir / ".write_test"
    probe.write_text("ok"); probe.unlink()

    config = {
        "args": vars(args) | {"kinds": list(kinds), "outdir": str(outdir)},
        "hyper": hyper, "net_arch": NET_ARCH, "algo": "PPO(MAPPOPolicy) = MAPPO parameter-sharing",
        "mappo": {"actor": "compartido, DESCENTRALIZADO (obs local %d)" % LOCAL_SIZE,
                  "critic": "CENTRALIZADO (obs global privilegiada %d = rl.obs.build_obs, CTDE)"
                            % (AGENT_OBS_SIZE - LOCAL_SIZE),
                  "agente": "PUESTO de barrera (k-ésimo dron EN ESTACIÓN); N_SEATS=%d" % N_SEATS},
        "reward": {"global": "-1 por res matada (compartida) — LA métrica con signo",
                   "local": "+local_coef por (lobo,paso) expulsado atribuido al dron del puesto "
                            "(regla del mundo recomputada; determinista)",
                   "local_coef": args.local_coef,
                   "anti_proxy": "ep_sev y ep_deter POR SEPARADO en el log; la vara = severidad del arnés"},
        "residual": {"scale_m": scale, "phase1_steps": args.phase1_steps,
                     "log_std_init": RESIDUAL_LOG_STD_INIT,
                     "nota": "δ sobre el waypoint de la barrera v2.6 (viva dentro); máscara "
                             "ACTIVE&~investigating&~relief_hold; δ≡0 = barrera pura (suelo 2.74/2.82)"},
        "abort": ABORT_NOTE_DRONES,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    (outdir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False))

    venv = SubprocVecEnv([make_env(args.seed + i, kinds, args.frame_skip, scale, args.local_coef)
                          for i in range(args.n_envs)], start_method="fork")
    venv = TeamUnstackVecEnv(venv)
    venv = VecMonitor(venv)

    model = PPO(MAPPOPolicy, venv, verbose=1, seed=args.seed, device=args.device,
                tensorboard_log=str(outdir / "tb"), **hyper)

    # INIT RESIDUAL (RPL + RRC): media de δ ≡ 0 EXACTO + σ pequeña. Verificación obligatoria.
    model.policy.action_net.weight.data.zero_()
    model.policy.action_net.bias.data.zero_()
    model.policy.log_std.data.fill_(RESIDUAL_LOG_STD_INIT)
    probe = th.as_tensor(np.random.default_rng(0).normal(
        size=(5, AGENT_OBS_SIZE)).astype(np.float32))
    with th.no_grad():
        mu = model.policy.get_distribution(probe).distribution.mean
    assert (mu == 0.0).all(), "init residual roto: la media de δ no es 0 exacto"
    print(f"  RESIDUAL: init verificado — media de δ = 0 EXACTO (5 obs aleatorias); "
          f"log_std = {RESIDUAL_LOG_STD_INIT} (σ≈{np.exp(RESIDUAL_LOG_STD_INIT):.2f})")

    run_desc = (f"total_steps(agente)={args.total_steps:,} mundos={args.n_envs} seed={args.seed} "
                f"device={args.device} kinds={kinds} frame_skip={args.frame_skip} "
                f"MAPPO residual scale={scale} local_coef={args.local_coef} lr={hyper['learning_rate']} "
                f"fase1={args.phase1_steps:,} outdir={outdir}")
    train_log = TrainLog(outdir / "train.log", run_desc, ABORT_NOTE_DRONES)
    light_eval = LightEval(outdir / "train.log", args.eval_every, scale, train_log=train_log)
    checkpoints = CheckpointCallback(save_freq=max(500_000 // venv.num_envs, 1),
                                     save_path=str(outdir / "checkpoints"), name_prefix="mappo_drones")
    callbacks = [train_log, light_eval, checkpoints]

    t0 = time.time()
    try:
        if args.phase1_steps > 0:
            # FASE 1 — SOLO CRÍTICO (truco RRC): π y log_std congelados (δ medio = 0, solo ruido
            # σ≈0.14); el crítico centralizado aprende cuánto vale la BARRERA antes de mover nada.
            pi_params = (list(model.policy.mlp_extractor.policy_net.parameters())
                         + list(model.policy.action_net.parameters()) + [model.policy.log_std])
            for p_ in pi_params:
                p_.requires_grad_(False)
            fase1 = min(args.phase1_steps, args.total_steps)
            print(f"  FASE 1 (solo crítico): política CONGELADA durante {fase1:,} pasos-agente")
            model.learn(total_timesteps=fase1, callback=callbacks)
            for p_ in pi_params:
                p_.requires_grad_(True)
            marca = (f"[{datetime.now().isoformat(timespec='seconds')}] === FASE 2 (PPO normal): "
                     f"política DESCONGELADA en el paso {model.num_timesteps:,} ===")
            print("  " + marca)
            with open(outdir / "train.log", "a", encoding="utf-8") as f:
                f.write(marca + "\n")
            restante = args.total_steps - model.num_timesteps
            if restante > 0:
                model.learn(total_timesteps=restante, callback=callbacks, reset_num_timesteps=False)
        else:
            model.learn(total_timesteps=args.total_steps, callback=callbacks)
    finally:
        venv.close()                                   # sin workers colgados (buen vecino)
    elapsed = time.time() - t0

    model.save(str(outdir / "model.zip"))
    summary = {
        "total_steps_agente": int(model.num_timesteps),
        "elapsed_s": round(elapsed, 1),
        "fps_agente": round(model.num_timesteps / max(elapsed, 1e-9), 1),
        "ep_sev_mean_final": (float(np.mean(train_log._sev[-100:])) if train_log._sev else None),
        "ep_deter_mean_final": (float(np.mean(train_log._det[-100:])) if train_log._det else None),
        "episodios_stream": len(train_log._rew),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("=== resumen ===")
    print(f"  {summary['total_steps_agente']:,} pasos-agente en {summary['elapsed_s']:.0f} s "
          f"-> {summary['fps_agente']:.0f} fps(agente)")
    print(f"  ep_sev_mean(últ.100)={summary['ep_sev_mean_final']}  ep_deter_mean={summary['ep_deter_mean_final']}")
    print(f"  artefactos -> {outdir} (model.zip, checkpoints/, tb/, config.json, summary.json)")


if __name__ == "__main__":
    main()
