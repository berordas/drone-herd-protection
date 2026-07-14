"""train_wolves.py — Entrenador PPO del paquete de lobos (SB3) contra la barrera reactiva.

PPO("MlpPolicy") de Stable-Baselines3 sobre WolfPackEnv (cerebro único, recompensa RALA
+1/muerte), con SubprocVecEnv (n envs en paralelo) + VecMonitor. TODOS los artefactos
(checkpoints, TensorBoard, model.zip, config.json, summary.json) van al outdir — que debe
vivir en /data (= ~/rl_data del host, FUERA del repo; persiste aunque el contenedor muera).

Uso (dentro del contenedor, ver docker/):
    python rl/train_wolves.py --smoke --outdir /data/wolves/smoke     # humo: ~60k pasos, 4 envs, CPU
    python rl/train_wolves.py --total-steps 2000000 --n-envs 8        # entrenamiento de verdad (futuro)

Device: por defecto CPU — la red es un MLP diminuto y en la DGX compartida CPU es lo cortés
(y suele ser igual de rápido: el cuello es la simulación, no la red).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# El repo (padre de rl/) importable como scripts sueltos Y en los workers de SubprocVecEnv
# (forkserver/spawn heredan PYTHONPATH, no sys.path). En el contenedor ya viene PYTHONPATH=/workspace.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ["PYTHONPATH"] = str(_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from rl.wolf_env import VALID_KINDS, WolfPackEnv

# Hiperparámetros por defecto (razonables, NO afinados; quedan anotados en config.json).
HYPER = dict(
    n_steps=2048,            # rollout por env (episodios largos: hasta ~2830 pasos de env)
    batch_size=512,
    gamma=0.999,             # horizonte LARGO (~1000 decisiones ≈ 500 s sim: la recompensa rala llega tarde)
    gae_lambda=0.95,
    learning_rate=3e-4,
    ent_coef=0.01,           # algo de exploración (recompensa RALA)
    clip_range=0.2,
    n_epochs=10,
)
NET_ARCH = [128, 128]

# Criterio de ABORTO pactado (se escribe en train.log al arrancar): si a ~2M de pasos
# ep_rew_mean sigue en 0.00 (ninguna muerte espontánea), PARAR el run y reportar; el plan B
# (shaping basado en potencial) NO se implementa sin decisión del usuario.
ABORT_NOTE = ("CRITERIO DE ABORTO (pactado): si a ~2.000.000 de pasos ep_rew_mean sigue en 0.00 "
              "(ninguna muerte espontánea), parar el run y reportar. El shaping por potencial es "
              "plan B y lo decide el usuario — NO implementarlo por cuenta propia.")


def make_env(seed: int, kinds: tuple[str, ...], frame_skip: int):
    """Thunk picklable para SubprocVecEnv (cada worker importa rl.wolf_env vía PYTHONPATH)."""
    def _thunk():
        return WolfPackEnv(kinds=kinds, frame_skip=frame_skip, seed=seed)
    return _thunk


class EpisodeLog(BaseCallback):
    """Recoge (timestep, recompensa, longitud) de cada episodio terminado (vía VecMonitor)."""

    def __init__(self):
        super().__init__()
        self.episodes: list[dict] = []

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", ()):
            ep = info.get("episode")
            if ep is not None:
                self.episodes.append({"t": int(self.num_timesteps),
                                      "r": float(ep["r"]), "l": int(ep["l"])})
        return True


class TrainLog(BaseCallback):
    """Log periódico LEGIBLE a outdir/train.log (lo que se consulta con `tail -f`): una línea
    por rollout con timestamp, pasos, fps y medias móviles de recompensa/longitud (últimos
    100 episodios, vía VecMonitor). La cabecera documenta el criterio de aborto pactado."""

    def __init__(self, logpath: Path, run_config: str):
        super().__init__()
        self.logpath = logpath
        self.run_config = run_config
        self._t0 = None

    def _write(self, line: str) -> None:
        with open(self.logpath, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _on_training_start(self) -> None:
        self._t0 = time.time()
        self._write("=" * 100)
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] ARRANQUE  {self.run_config}")
        self._write(ABORT_NOTE)
        self._write("columnas: timestamp | pasos | fps | ep_rew_mean (últimos 100 eps) | ep_len_mean")

    def _on_rollout_end(self) -> None:
        buf = self.model.ep_info_buffer
        rew = float(np.mean([e["r"] for e in buf])) if buf else float("nan")
        length = float(np.mean([e["l"] for e in buf])) if buf else float("nan")
        fps = self.num_timesteps / max(time.time() - self._t0, 1e-9)
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] pasos={self.num_timesteps:>10,}  "
                    f"fps={fps:7.1f}  ep_rew_mean={rew:6.3f}  ep_len_mean={length:8.1f}")

    def _on_step(self) -> bool:
        return True

    def _on_training_end(self) -> None:
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] FIN  pasos={self.num_timesteps:,}")


class LightEval(BaseCallback):
    """Eval periódica LIGERA (cada eval_every pasos): 10 episodios DETERMINISTAS en semillas
    fijas de 'lobos' con la política actual contra la barrera (mismo mecanismo que el
    evaluador: PolicyWolfController + SyncedReactiveCoordinator) → media de muertes al
    train.log. La eval COMPLETA (100 semillas) es solo con rl/eval_wolves.py, manual."""

    EVAL_SEEDS_LIGHT = tuple(range(10))

    def __init__(self, logpath: Path, eval_every: int = 250_000):
        super().__init__()
        self.logpath = logpath
        self.eval_every = int(eval_every)
        self._next_at = self.eval_every

    def _on_step(self) -> bool:
        if self.eval_every <= 0 or self.num_timesteps < self._next_at:
            return True
        self._next_at += self.eval_every
        from baseline import build_world
        from rl.policy_wolf_controller import PolicyWolfController, SyncedReactiveCoordinator
        t0 = time.time()
        deaths = []
        for s in self.EVAL_SEEDS_LIGHT:
            ctrl = PolicyWolfController(model=self.model)
            w = build_world(s, "lobos", wolf_controller=ctrl)
            w.reset()
            coord = SyncedReactiveCoordinator(w)
            while True:
                _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
                if term or trunc:
                    break
            deaths.append(w.n_depredadas)
        line = (f"[{datetime.now().isoformat(timespec='seconds')}] EVAL_LIGERA pasos={self.num_timesteps:>10,}  "
                f"muertes_media={np.mean(deaths):.2f}  (n=10 semillas lobos, determinista; "
                f"detalle={deaths}; {time.time() - t0:.0f}s)")
        with open(self.logpath, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True


def _reward_por_tramos(episodes: list[dict], n_tramos: int = 4) -> list[dict]:
    """Media/máx de recompensa por tramos consecutivos de episodios (progresión del smoke)."""
    if not episodes:
        return []
    rs = np.array([e["r"] for e in episodes], dtype=float)
    tramos = []
    for chunk in np.array_split(rs, min(n_tramos, len(rs))):
        tramos.append({"n_episodios": int(chunk.size),
                       "reward_media": float(chunk.mean()), "reward_max": float(chunk.max())})
    return tramos


def main() -> None:
    p = argparse.ArgumentParser(description="Entrena PPO (paquete de lobos) contra la barrera reactiva.")
    p.add_argument("--total-steps", type=int, default=1_000_000, help="pasos totales de env (suma de todos los envs)")
    p.add_argument("--n-envs", type=int, default=8, help="envs en paralelo (SubprocVecEnv)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", type=str, default=None, help="def. /data/wolves/<timestamp> (¡fuera del repo!)")
    p.add_argument("--kinds", type=str, default="lobos,mixto", help="tipos de episodio (coma; nunca 'corzos')")
    p.add_argument("--device", type=str, default="cpu", help="cpu (def., lo cortés en la DGX compartida) | cuda")
    p.add_argument("--frame-skip", type=int, default=5, help="pasos de física por decisión (0.5 s)")
    p.add_argument("--smoke", action="store_true", help="preset humo: 60k pasos, 4 envs (demuestra que gira)")
    p.add_argument("--resume", type=str, default=None, help="checkpoint .zip del que RETOMAR (PPO.load, sin resetear el contador)")
    p.add_argument("--eval-every", type=int, default=250_000, help="eval ligera (10 eps deterministas) cada N pasos; 0 = off")
    args = p.parse_args()

    if args.smoke:
        args.total_steps = 60_000
        args.n_envs = 4

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    if any(k not in VALID_KINDS for k in kinds):
        p.error("--kinds debe ser subconjunto de %r (nunca 'corzos')" % (VALID_KINDS,))

    outdir = Path(args.outdir) if args.outdir else Path("/data/wolves") / datetime.now().strftime("%Y%m%d-%H%M%S")

    print("=== train_wolves (PPO, cerebro único del paquete, recompensa RALA +1/muerte) ===")
    print(f"  envs = {args.n_envs} (SubprocVecEnv)  |  device = {args.device}  |  seed = {args.seed}")
    print(f"  kinds = {kinds}  |  frame_skip = {args.frame_skip}  |  total_steps = {args.total_steps:,}")
    print(f"  outdir = {outdir}")

    # outdir escribible ANTES de entrenar (que no se pierda una noche de run por un typo).
    outdir.mkdir(parents=True, exist_ok=True)
    probe = outdir / ".write_test"
    probe.write_text("ok"); probe.unlink()

    config = {
        "args": vars(args) | {"kinds": list(kinds), "outdir": str(outdir)},
        "hyper": HYPER, "net_arch": NET_ARCH, "algo": "PPO(MlpPolicy)",
        "reward": "+1 por res matada (rala, compartida); sin castigo por tiempo ni por a-salvo",
        "abort": ABORT_NOTE,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    (outdir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False))

    # start_method="fork" (Linux): los workers HEREDAN el estado del padre. El default de SB3
    # (forkserver) arranca un proceso limpio que re-importa el stack y moría en la imagen del
    # lab importando cv2 (opencv del lockfile) sin libGL (arreglado también en docker/Dockerfile).
    venv = SubprocVecEnv([make_env(args.seed + i, kinds, args.frame_skip) for i in range(args.n_envs)],
                         start_method="fork")
    venv = VecMonitor(venv)

    if args.resume:
        # Retomar de checkpoint: mismos hiperparámetros embebidos en el .zip; el contador de
        # pasos NO se resetea (learn(reset_num_timesteps=False)) -> checkpoints/log continúan.
        model = PPO.load(args.resume, env=venv, device=args.device,
                         tensorboard_log=str(outdir / "tb"))
        print(f"  RESUME desde {args.resume} (pasos ya entrenados: {model.num_timesteps:,})")
    else:
        model = PPO("MlpPolicy", venv, verbose=1, seed=args.seed, device=args.device,
                    tensorboard_log=str(outdir / "tb"),
                    policy_kwargs=dict(net_arch=NET_ARCH), **HYPER)

    run_desc = (f"total_steps={args.total_steps:,} n_envs={args.n_envs} seed={args.seed} "
                f"device={args.device} kinds={kinds} frame_skip={args.frame_skip} "
                f"resume={args.resume or '-'} outdir={outdir}")
    ep_log = EpisodeLog()
    train_log = TrainLog(outdir / "train.log", run_desc)
    light_eval = LightEval(outdir / "train.log", eval_every=args.eval_every)
    checkpoints = CheckpointCallback(save_freq=max(500_000 // args.n_envs, 1),   # ~cada 500k pasos totales
                                     save_path=str(outdir / "checkpoints"), name_prefix="ppo_wolves")

    t0 = time.time()
    try:
        model.learn(total_timesteps=args.total_steps, callback=[ep_log, train_log, light_eval, checkpoints],
                    reset_num_timesteps=not args.resume)
    finally:
        venv.close()                                   # sin workers colgados (buen vecino)
    elapsed = time.time() - t0

    model.save(str(outdir / "model.zip"))

    rs = np.array([e["r"] for e in ep_log.episodes], dtype=float)
    assert rs.size == 0 or np.isfinite(rs).all(), "recompensas no finitas (NaN/inf) — pipeline roto"
    summary = {
        "total_steps": int(model.num_timesteps),
        "elapsed_s": round(elapsed, 1),
        "fps": round(model.num_timesteps / max(elapsed, 1e-9), 1),
        "episodios": len(ep_log.episodes),
        "reward_media": float(rs.mean()) if rs.size else None,
        "reward_max": float(rs.max()) if rs.size else None,
        "reward_por_tramos": _reward_por_tramos(ep_log.episodes),
        "longitud_media_ep": float(np.mean([e["l"] for e in ep_log.episodes])) if ep_log.episodes else None,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("=== resumen ===")
    print(f"  {summary['total_steps']:,} pasos en {summary['elapsed_s']:.0f} s -> {summary['fps']:.0f} fps")
    print(f"  episodios = {summary['episodios']}  |  reward media = {summary['reward_media']}  |  max = {summary['reward_max']}")
    for i, tr in enumerate(summary["reward_por_tramos"]):
        print(f"    tramo {i + 1}: n={tr['n_episodios']}  media={tr['reward_media']:.2f}  max={tr['reward_max']:.0f}")
    print(f"  artefactos -> {outdir} (model.zip, checkpoints/, tb/, config.json, summary.json)")


if __name__ == "__main__":
    main()
