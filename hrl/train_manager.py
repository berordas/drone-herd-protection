"""hrl/train_manager.py — RUN-M1: PPO sobre el ManagerEnv (manager de lobos, semi-MDP).

Receta (misión Etapa 1 §3): PPO SB3, MlpPolicy [64,64], lr 3e-4, γ=1.0 (episódico — esquiva el
descuento SMDP de τ variable), gae_λ=0.95, ent_coef 0.02 con anneal lineal → 0.005, clip 0.2,
n_steps=256 macro-pasos/env, batch 512, 10 epochs, 16-32 envs SubprocVecEnv(fork), oponente
Reactive v3.5. Presupuesto 120k macro-pasos (fps y ETA en el log). Checkpoints cada 5k ·
EVAL_LIGERA determinista cada 10k sobre 40 semillas FIJAS (20 lobos + 20 mixto, reset_to)
registrando sev media, P(a|G), P(a|S), P(a|n) — LA CURVA DE EMERGENCIA (eval_ligera.jsonl) es el
artefacto estrella. Contador pasivo de PENETRADO por política (solo se reporta).

Variantes pre-registradas (flags, default OFF = RUN-M1 intacto): --fixed-k 1000 (RUN-M2: opciones
interrumpidas a K fijo) · --ablate-progress (RUN-M4, adenda 4 §3: sin los dos rasgos de progreso) ·
--opponent mix (RUN-M3, adenda 4 §4) · --g-oversample 0.6 --g-oversample-steps 30000 (CONTINGENCIA
de currículo, adenda 4 §2: SOLO si en la ligera de 40k P(cebo|G,n>=3) < 0.3 — el entrenador
únicamente escribe un AVISO en train.log, JAMÁS se auto-activa; relanzar a mano; warmup con
oversampling de G al 60% y después distribución natural; queda en config.json).

Artefactos en /data/hrl_m1/<run>/: config.json, train.log, eval_ligera.jsonl, checkpoints/,
model.zip, summary.json. CPU; buen vecino (CUDA_VISIBLE_DEVICES="" desde fuera).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hrl.manager_env import ManagerEnv, OPTION_NAMES              # noqa: E402
from hrl.manager_obs import N_OPTIONS                             # noqa: E402

HYPER = dict(n_steps=256, batch_size=512, gamma=1.0, gae_lambda=0.95, learning_rate=3e-4,
             clip_range=0.2, n_epochs=10, ent_coef_start=0.02, ent_coef_end=0.005)
NET_ARCH = [64, 64]
EVAL_SEEDS = tuple((s, "lobos") for s in range(20)) + tuple((s, "mixto") for s in range(20))


def make_env(seed, opponent, fixed_k, ablate=False, g_over=None):
    def _f():
        return ManagerEnv(kinds=("lobos",), seed=seed, opponent=opponent, fixed_k=fixed_k,
                          obs_ablate_progress=ablate, g_oversample=g_over)
    return _f


_EVAL_MODEL = {}


def _light_eval_one(job):
    """Un episodio de la ligera en un proceso hijo (fork): carga el checkpoint una vez por proceso."""
    ckpt, s, kind, opponent, fixed_k, ablate = job
    if ckpt not in _EVAL_MODEL:
        from stable_baselines3 import PPO
        _EVAL_MODEL[ckpt] = PPO.load(ckpt, device="cpu")
    model = _EVAL_MODEL[ckpt]
    env = ManagerEnv(kinds=(kind,), seed=12345, opponent=opponent, fixed_k=fixed_k,
                     obs_ablate_progress=ablate)
    obs, info = env.reset_to(s, kind)
    stratum = "G" if info["two_front"] else "S"
    n = info["n_wolves"]
    done, first, a0, acts = False, True, None, []
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        a = int(a)
        if first:
            a0 = a; first = False
        acts.append(a)
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    return {"stratum": stratum, "n": n, "a0": a0, "acts": acts, "sev": info["ep_sev"],
            "dec": info["ep_decisions"], "pen": info["penetrado_ticks"], "kind": kind}


def light_eval(model, opponent: str, fixed_k, ablate: bool = False, procs: int = 20) -> dict:
    """40 semillas FIJAS (reset_to), política determinista, en un POOL de procesos (la ligera
    secuencial tardaba ~5 min y hundía los fps del smoke). Devuelve sev media, P(a|G), P(a|S),
    P(a|n), P(cebo|G,n>=3), ticks PENETRADO medios y nº de decisiones medio."""
    import multiprocessing as mp
    import tempfile
    from collections import Counter, defaultdict
    eval_opp = "reactive" if opponent == "mix" else opponent      # la ligera siempre vs Reactive
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    model.save(tmp)
    jobs = [(tmp, s, kind, eval_opp, fixed_k, ablate) for s, kind in EVAL_SEEDS]
    with mp.get_context("fork").Pool(min(procs, len(jobs))) as pool:
        res = pool.map(_light_eval_one, jobs, chunksize=1)
    sev = [r["sev"] for r in res]; dec = [r["dec"] for r in res]; pen = [r["pen"] for r in res]
    acts_by = defaultdict(Counter)      # clave -> Counter de acciones (primera decisión)
    all_by = defaultdict(Counter)       # clave -> Counter de acciones (todas las decisiones)
    cebo_g3 = [0, 0]
    for r in res:
        acts_by[r["stratum"]][r["a0"]] += 1; acts_by[f"n{r['n']}"][r["a0"]] += 1
        if r["stratum"] == "G" and r["n"] >= 3:
            cebo_g3[1] += 1; cebo_g3[0] += int(r["a0"] != 0)
        for a in r["acts"]:
            all_by[r["stratum"]][a] += 1

    def dist(c):
        tot = sum(c.values())
        return {OPTION_NAMES[a]: round(c[a] / tot, 3) for a in range(N_OPTIONS)} if tot else None
    return {"sev_media": float(np.mean(sev)), "sev_lobos": float(np.mean(sev[:20])),
            "sev_mixto": float(np.mean(sev[20:])),
            "P_cebo_G_n3": (cebo_g3[0] / cebo_g3[1] if cebo_g3[1] else None), "n_G_n3": cebo_g3[1],
            "P_a_G_first": dist(acts_by["G"]), "P_a_S_first": dist(acts_by["S"]),
            "P_a_n": {k: dist(v) for k, v in acts_by.items() if k.startswith("n")},
            "P_a_G_all": dist(all_by["G"]), "P_a_S_all": dist(all_by["S"]),
            "decisiones_media": float(np.mean(dec)), "penetrado_ticks_media": float(np.mean(pen))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="M1")
    ap.add_argument("--total", type=int, default=120_000, help="macro-pasos (env steps)")
    ap.add_argument("--n-envs", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--opponent", default="reactive", choices=["reactive", "run02", "run09", "mix"])
    ap.add_argument("--fixed-k", type=int, default=None, help="RUN-M2: interrumpir opciones a K ticks")
    ap.add_argument("--ablate-progress", action="store_true", help="RUN-M4 (adenda 4): sin rasgos de progreso")
    ap.add_argument("--g-oversample", type=float, default=None,
                    help="CONTINGENCIA (adenda 4): frac. episodios G en el warmup (jamás automática)")
    ap.add_argument("--g-oversample-steps", type=int, default=30_000)
    ap.add_argument("--eval-every", type=int, default=10_000)
    ap.add_argument("--ckpt-every", type=int, default=5_000)
    ap.add_argument("--smoke", action="store_true", help="1k macro-pasos, 8 envs, eval cada 500")
    args = ap.parse_args()
    if args.smoke:
        # 1 rollout con la config real (n_envs de la línea de comandos): mide fps/ETA reales
        args.total = HYPER["n_steps"] * args.n_envs
        args.eval_every, args.ckpt_every = args.total, args.total
        args.run = args.run + "_smoke"
    out = pathlib.Path("/data/hrl_m1") / args.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(exist_ok=True)

    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv
    torch.set_num_threads(1)

    g_over = args.g_oversample
    venv = SubprocVecEnv([make_env(args.seed * 1000 + i, args.opponent, args.fixed_k,
                                   args.ablate_progress, g_over) for i in range(args.n_envs)],
                         start_method="fork")

    def ent_sched(progress_remaining):   # 1 -> 0 a lo largo del run
        return HYPER["ent_coef_end"] + (HYPER["ent_coef_start"] - HYPER["ent_coef_end"]) * progress_remaining

    model = PPO("MlpPolicy", venv, n_steps=HYPER["n_steps"], batch_size=HYPER["batch_size"],
                gamma=HYPER["gamma"], gae_lambda=HYPER["gae_lambda"],
                learning_rate=HYPER["learning_rate"], clip_range=HYPER["clip_range"],
                n_epochs=HYPER["n_epochs"], ent_coef=HYPER["ent_coef_start"],
                policy_kwargs=dict(net_arch=NET_ARCH), seed=args.seed, device="cpu", verbose=0,
                tensorboard_log=str(out / "tb"))
    config = {"args": vars(args), "hyper": HYPER, "net_arch": NET_ARCH,
              "eval_seeds": EVAL_SEEDS, "fecha": datetime.now().isoformat(timespec="seconds"),
              "opciones": OPTION_NAMES, "curriculum_used": bool(g_over is not None),
              "adenda4": {"ablate_progress": args.ablate_progress, "g_oversample": g_over,
                          "g_oversample_steps": args.g_oversample_steps, "opponent": args.opponent}}
    (out / "config.json").write_text(json.dumps(config, indent=1, ensure_ascii=False))
    log = open(out / "train.log", "a", encoding="utf-8")
    log.write(f"[{datetime.now().isoformat(timespec='seconds')}] RUN {args.run}: {vars(args)}\n"); log.flush()

    class CB(BaseCallback):
        def __init__(self):
            super().__init__(); self.t0 = time.time(); self.next_eval = args.eval_every
            self.next_ckpt = args.ckpt_every; self.ep_sev = []; self.ep_dec = []; self.ep_pen = []
            self.acts = np.zeros(N_OPTIONS); self.events = {}; self.g_switched = False

        def _on_step(self):
            for info in self.locals.get("infos", []):
                if "ep_sev" in info:
                    self.ep_sev.append(info["ep_sev"]); self.ep_dec.append(info["ep_decisions"])
                    self.ep_pen.append(info["penetrado_ticks"])
                if "event" in info:
                    self.events[info["event"]] = self.events.get(info["event"], 0) + 1
            for a in np.asarray(self.locals.get("actions", [])).ravel():
                self.acts[int(a)] += 1
            # anneal de la entropía (lineal con el progreso)
            prog = 1.0 - self.num_timesteps / max(args.total, 1)
            self.model.ent_coef = float(ent_sched(prog))
            t = self.num_timesteps
            if g_over is not None and not self.g_switched and t >= args.g_oversample_steps:
                self.training_env.env_method("set_g_oversample", None); self.g_switched = True
                log.write(f"[{datetime.now().isoformat(timespec='seconds')}] CURRÍCULO: fin del warmup "
                          f"(oversampling G) en {t:,} macro-pasos -> distribución natural\n"); log.flush()
            if t >= self.next_ckpt:
                self.next_ckpt += args.ckpt_every
                self.model.save(str(out / "checkpoints" / f"manager_{t}"))
            if t >= self.next_eval:
                self.next_eval += args.eval_every
                fps = t / max(time.time() - self.t0, 1e-9)
                eta = (args.total - t) / max(fps, 1e-9) / 3600
                tot = max(self.acts.sum(), 1)
                line = (f"[{datetime.now().isoformat(timespec='seconds')}] pasos={t:>8,} fps={fps:.1f} "
                        f"ETA={eta:.1f}h  buffer: ep_sev={np.mean(self.ep_sev[-200:]) if self.ep_sev else float('nan'):.2f} "
                        f"dec/ep={np.mean(self.ep_dec[-200:]) if self.ep_dec else float('nan'):.1f} "
                        f"pen/ep={np.mean(self.ep_pen[-200:]) if self.ep_pen else float('nan'):.0f} "
                        f"P(a)={np.round(self.acts / tot, 3).tolist()} ent={self.model.ent_coef:.4f} "
                        f"eventos={self.events}")
                print(line, flush=True); log.write(line + "\n"); log.flush()
                ev = light_eval(self.model, args.opponent, args.fixed_k, args.ablate_progress)
                ev.update({"pasos": int(t), "fecha": datetime.now().isoformat(timespec="seconds")})
                with open(out / "eval_ligera.jsonl", "a") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                l2 = (f"  EVAL_LIGERA pasos={t:,} sev={ev['sev_media']:.2f} (lobos {ev['sev_lobos']:.2f} | mixto "
                      f"{ev['sev_mixto']:.2f}) P(cebo|G,n>=3)={ev['P_cebo_G_n3']} (n={ev['n_G_n3']}) "
                      f"P(a|G)={ev['P_a_G_first']} P(a|S)={ev['P_a_S_first']} dec/ep={ev['decisiones_media']:.1f} "
                      f"pen={ev['penetrado_ticks_media']:.0f}")
                print(l2, flush=True); log.write(l2 + "\n"); log.flush()
                if g_over is None and t >= 40_000 and ev["P_cebo_G_n3"] is not None and ev["P_cebo_G_n3"] < 0.3:
                    log.write("  AVISO CONTINGENCIA PRE-REGISTRADA (adenda 4 §2): P(cebo|G,n>=3) < 0.3 a >=40k "
                              "-> candidato a relanzar con --g-oversample 0.6 (decisión HUMANA; este run sigue)\n")
                    log.flush()
            return True

    cb = CB()
    t0 = time.time()
    model.learn(total_timesteps=args.total, callback=cb)
    model.save(str(out / "model"))
    ev = light_eval(model, args.opponent, args.fixed_k, args.ablate_progress)
    ev.update({"pasos": int(model.num_timesteps), "final": True})
    with open(out / "eval_ligera.jsonl", "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    summary = {"macro_pasos": int(model.num_timesteps), "segundos": round(time.time() - t0, 1),
               "fps": round(model.num_timesteps / max(time.time() - t0, 1e-9), 2),
               "nan": bool(any(np.isnan(p.detach().numpy()).any() for p in model.policy.parameters())),
               "eval_final": ev, "curriculum_used": bool(g_over is not None)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print("RUN_DONE", json.dumps(summary, ensure_ascii=False)[:600])
    log.write(f"RUN_DONE {json.dumps(summary, ensure_ascii=False)}\n"); log.close()


if __name__ == "__main__":
    main()
