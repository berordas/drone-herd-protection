"""hrl/train_drone_manager.py — RUN-D2: entrena el MANAGER DEL BANDO DRON (DroneManagerEnv) con
la receta ESPEJO del manager lobo (HYPER de train_manager; PREREGISTRO_D2 congelado).

Artefactos en /data/hrl_d2/<run>/: config.json, train.log, eval_ligera.jsonl, checkpoints/,
model.zip, summary.json (RUN_DONE). Ligera: 40 semillas fijas × atacante {natural, manager},
política determinista (argmax) + P(a) estocástica: sev, P(a | 1 clúster), P(a | 2º clúster)
(1ª decisión tras percibir un 2º clúster), interrupciones-con-cambio/ep (el gate del fallback
0.1 a 40k), STALLs, coste pagado, PENETRADO, reasignaciones.

Uso: python3 -m hrl.train_drone_manager --run D2 --total 120000 --n-envs 24 --seed 0"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, "/workspace")
from hrl.manager_drone import (DroneManagerEnv, EVD_CLUSTER, N_ACTIONS, PARTITION_NAMES,  # noqa: E402
                               build_drone_obs)
from hrl.train_manager import HYPER, NET_ARCH                                            # noqa: E402

EVAL_SEEDS = tuple((s, "lobos", "natural") for s in range(10)) + tuple((s, "mixto", "natural") for s in range(10)) \
    + tuple((s, "lobos", "manager") for s in range(10)) + tuple((s, "mixto", "manager") for s in range(10))
_EVAL_MODEL: dict = {}


def make_env(seed, delib_cost=None):
    def _f():
        kw = {} if delib_cost is None else {"delib_cost": float(delib_cost)}
        return DroneManagerEnv(seed=seed, **kw)
    return _f


def _light_eval_one(job):
    ckpt, s, kind, atk = job
    if ckpt not in _EVAL_MODEL:
        from stable_baselines3 import PPO
        _EVAL_MODEL[ckpt] = PPO.load(ckpt, device="cpu")
    model = _EVAL_MODEL[ckpt]
    env = DroneManagerEnv(seed=12345)
    obs, info = env.reset_to(s, kind, atk)
    done = False
    acts, probs, ents, a_1c, a_2c = [], [], [], [], []
    while not done:
        obs_t, _ = model.policy.obs_to_tensor(obs)
        dist = model.policy.get_distribution(obs_t)
        probs.append(dist.distribution.probs.detach().cpu().numpy()[0].tolist())
        ents.append(float(dist.entropy().item()))
        n_cl = int(round(float(obs[0]) * 3))
        a, _ = model.predict(obs, deterministic=True)
        a = int(a)
        (a_2c if n_cl >= 2 else a_1c).append(a)
        acts.append(a)
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    return {"s": s, "kind": kind, "atk": atk, "sev": info["ep_sev"], "dec": info["ep_decisions"],
            "interr": info["interrupciones"], "cambios": info["cambios"], "stalls": info["stalls"],
            "delib": info["delib_pagado"], "pen": info["penetrado_ticks"], "acts": acts,
            "a_1c": a_1c, "a_2c": a_2c, "probs": probs, "ents": ents,
            "jug": (info.get("jugada_atacante") or {}).get("completa")}


def light_eval(model, procs: int = 20) -> dict:
    import multiprocessing as mp
    import tempfile
    from collections import Counter
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    model.save(tmp)
    jobs = [(tmp, s, k, a) for s, k, a in EVAL_SEEDS]
    with mp.get_context("fork").Pool(min(procs, len(jobs))) as pool:
        res = pool.map(_light_eval_one, jobs, chunksize=1)

    def dist(c):
        tot = sum(c.values())
        return {PARTITION_NAMES[a]: round(c[a] / tot, 3) for a in range(N_ACTIONS)} if tot else None
    c1, c2 = Counter(), Counter()
    for r in res:
        c1.update(r["a_1c"]); c2.update(r["a_2c"])
    by_atk = {atk: float(np.mean([r["sev"] for r in res if r["atk"] == atk])) for atk in ("natural", "manager")}
    jug = [r["jug"] for r in res if r["jug"] is not None]
    return {"sev_media": float(np.mean([r["sev"] for r in res])), "sev_por_atacante": by_atk,
            "P_a_1cluster": dist(c1), "P_a_2clusters": dist(c2),
            "P_guardia_2clusters": (round(1.0 - c2[0] / max(sum(c2.values()), 1), 3) if c2 else None),
            "interrupciones_por_ep": float(np.mean([r["interr"] for r in res])),
            "cambios_por_ep": float(np.mean([r["cambios"] for r in res])),
            "stalls_total": int(sum(r["stalls"] for r in res)),
            "delib_por_ep": float(np.mean([r["delib"] for r in res])),
            "penetrado_medio": float(np.mean([r["pen"] for r in res])),
            "decisiones_media": float(np.mean([r["dec"] for r in res])),
            "entropia_media": float(np.mean([e for r in res for e in r["ents"]])) if any(r["ents"] for r in res) else None,
            "jugada_completa_atacante": (float(np.mean(jug)) if jug else None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="D2")
    ap.add_argument("--total", type=int, default=120_000)
    ap.add_argument("--n-envs", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--eval-every", type=int, default=10_000)
    ap.add_argument("--ckpt-every", type=int, default=5_000)
    ap.add_argument("--delib-cost", type=float, default=None,
                    help="PREREGISTRO_D2: None = 0.05; 0.1 = fallback único (ligera 40k, interr-con-cambio/ep > 10)")
    ap.add_argument("--smoke", action="store_true", help="n_steps*n_envs macro-pasos, 8 envs, eval al final")
    args = ap.parse_args()
    if args.smoke:
        args.total = HYPER["n_steps"] * args.n_envs
        args.eval_every, args.ckpt_every = args.total, args.total
        args.run = args.run + "_smoke"
    out = pathlib.Path("/data/hrl_d2") / args.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(exist_ok=True)

    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv
    torch.set_num_threads(1)

    venv = SubprocVecEnv([make_env(args.seed * 1000 + i, args.delib_cost) for i in range(args.n_envs)],
                         start_method="fork")

    def ent_sched(progress_remaining):
        return HYPER["ent_coef_end"] + (HYPER["ent_coef_start"] - HYPER["ent_coef_end"]) * progress_remaining

    model = PPO("MlpPolicy", venv, n_steps=HYPER["n_steps"], batch_size=HYPER["batch_size"],
                gamma=HYPER["gamma"], gae_lambda=HYPER["gae_lambda"],
                learning_rate=HYPER["learning_rate"], clip_range=HYPER["clip_range"],
                n_epochs=HYPER["n_epochs"], ent_coef=HYPER["ent_coef_start"],
                policy_kwargs=dict(net_arch=NET_ARCH), seed=args.seed, device="cpu", verbose=0,
                tensorboard_log=str(out / "tb"))
    config = {"args": vars(args), "hyper": HYPER, "net_arch": NET_ARCH, "eval_seeds": EVAL_SEEDS,
              "fecha": datetime.now().isoformat(timespec="seconds"), "particiones": PARTITION_NAMES,
              "mundo": "v3.7.1-plazas-estacion", "atacantes_train": ["natural", "manager(M1pppp congelado)"]}
    (out / "config.json").write_text(json.dumps(config, indent=1, ensure_ascii=False))
    log = open(out / "train.log", "a", encoding="utf-8")
    log.write(f"[{datetime.now().isoformat(timespec='seconds')}] RUN {args.run}: {vars(args)}\n"); log.flush()

    class CB(BaseCallback):
        def __init__(self):
            super().__init__(); self.t0 = time.time(); self.next_eval = args.eval_every
            self.next_ckpt = args.ckpt_every; self.ep_sev = []; self.ep_dec = []; self.ep_int = []
            self.acts = np.zeros(N_ACTIONS); self.events = {}

        def _on_step(self):
            for info in self.locals.get("infos", []):
                if "ep_sev" in info:
                    self.ep_sev.append(info["ep_sev"]); self.ep_dec.append(info["ep_decisions"])
                    self.ep_int.append(info["interrupciones"])
                if "event" in info:
                    self.events[info["event"]] = self.events.get(info["event"], 0) + 1
            for a in np.asarray(self.locals.get("actions", [])).ravel():
                self.acts[int(a)] += 1
            self.model.ent_coef = float(ent_sched(1.0 - self.num_timesteps / max(args.total, 1)))
            t = self.num_timesteps
            if t >= self.next_ckpt:
                self.next_ckpt += args.ckpt_every
                self.model.save(str(out / "checkpoints" / f"dronemgr_{t}"))
            if t >= self.next_eval:
                self.next_eval += args.eval_every
                fps = t / max(time.time() - self.t0, 1e-9)
                eta = (args.total - t) / max(fps, 1e-9) / 3600
                tot = max(self.acts.sum(), 1)
                line = (f"[{datetime.now().isoformat(timespec='seconds')}] pasos={t:>8,} fps={fps:.1f} ETA={eta:.1f}h  "
                        f"buffer: ep_sev={np.mean(self.ep_sev[-200:]) if self.ep_sev else float('nan'):.2f} "
                        f"dec/ep={np.mean(self.ep_dec[-200:]) if self.ep_dec else float('nan'):.1f} "
                        f"interr/ep={np.mean(self.ep_int[-200:]) if self.ep_int else float('nan'):.1f} "
                        f"P(a)={np.round(self.acts / tot, 3).tolist()} ent={self.model.ent_coef:.4f} eventos={self.events}")
                print(line, flush=True); log.write(line + "\n"); log.flush()
                ev = light_eval(self.model)
                ev.update({"pasos": int(t), "fecha": datetime.now().isoformat(timespec="seconds")})
                with open(out / "eval_ligera.jsonl", "a") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                l2 = (f"  EVAL_LIGERA pasos={t:,} sev={ev['sev_media']:.2f} por_atacante={ev['sev_por_atacante']} "
                      f"P(a|1cl)={ev['P_a_1cluster']} P(a|2cl)={ev['P_a_2clusters']} "
                      f"P(guardia|2cl)={ev['P_guardia_2clusters']} interr/ep={ev['interrupciones_por_ep']:.2f} "
                      f"cambios/ep={ev['cambios_por_ep']:.2f} stalls={ev['stalls_total']} delib/ep={ev['delib_por_ep']:.3f} "
                      f"pen={ev['penetrado_medio']:.0f} H={ev['entropia_media']}")
                print(l2, flush=True); log.write(l2 + "\n"); log.flush()
            return True

    cb = CB()
    t0 = time.time()
    model.learn(total_timesteps=args.total, callback=cb)
    model.save(str(out / "model"))
    ev = light_eval(model)
    ev.update({"pasos": int(model.num_timesteps), "final": True})
    with open(out / "eval_ligera.jsonl", "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    summary = {"macro_pasos": int(model.num_timesteps), "segundos": round(time.time() - t0, 1),
               "fps": round(model.num_timesteps / max(time.time() - t0, 1e-9), 2),
               "nan": bool(any(np.isnan(p.detach().numpy()).any() for p in model.policy.parameters())),
               "eval_final": ev}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print("RUN_DONE", json.dumps(summary, ensure_ascii=False)[:600])
    log.write(f"RUN_DONE {json.dumps(summary, ensure_ascii=False)}\n"); log.close()


if __name__ == "__main__":
    main()
