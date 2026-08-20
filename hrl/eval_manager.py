"""hrl/eval_manager.py — METRO del MANAGER (Etapa 1): baselines sin entrenar + checkpoints del
manager, 100 semillas EMPAREJADAS (EVAL_SEEDS del arnés: 0-99 × {lobos, mixto}; los mismos
episodios para todas las políticas) × defensas congeladas {Reactive v3.5, run02-eval, run09}.

Políticas (decide(obs, info_reset, env) -> acción Discrete(4)):
  B_masa   : MASA siempre (acción 0). En hrl_check [6]: ≡ MASA-forzado de E0.1 bit a bit.
  B_spawn  : cebo SII el spawn es agrupado (two_front) — CEBO_keep (membresías = las del spawn:
             señuelo = índice mín = el singleton del spawn en G); si no, MASA. Se decide UNA vez
             (primera decisión) y se mantiene (re-decisiones = la misma).
  B_oracle : regla DESTILADA de E0 (v3.5): CEBO_keep si G ∧ n>=3 · CEBO(Δ90) si S ∧ n>=3 · MASA
             si n<=2. Decidida en t=0 y mantenida.
  manager  : checkpoint SB3 (predict determinista) — decide en CADA frontera de opción.
Métricas: sev media ± IC bootstrap 10k (RNG propio del análisis), Δsev emparejado vs B_masa y vs
B_oracle con IC, P(a | G/S, n) (heatmap), decisiones/episodio, eventos, ticks PENETRADO (contador
pasivo), el GAP DE TRANSFERENCIA Δsev(Reactive→run09) por política (adenda 4 §1) y (K-bis) los
contadores de caza por episodio: re-arranques de opción, re-targets (regla: protegida), bloqueados
por cooldown y re-fijaciones por muerte/refugio/otro.
Artefactos: /data/hrl_m1/eval/<politica>_<oponente>.json + tabla.md. Uso:
    python3 hrl/eval_manager.py --policy oracle|masa|spawn|manager:<ckpt.zip> --opponent reactive|run02|run09 [--procs N]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hrl.manager_env import ManagerEnv, OPTION_NAMES     # noqa: E402
from hrl.manager_obs import N_OPTIONS                    # noqa: E402

OUT = pathlib.Path("/data/hrl_m1/eval")
SEEDS = [(s, k) for k in ("lobos", "mixto") for s in range(100)]
_MODEL = {}


def policy_fn(spec: str):
    if spec == "masa":
        return lambda obs, info, first: 0
    if spec == "spawn":
        return lambda obs, info, first: (1 if info["two_front"] else 0)
    if spec == "oracle":
        def f(obs, info, first):
            n = info["n_wolves"]
            if n <= 2:
                return 0
            return 1 if info["two_front"] else 2
        return f
    if spec.startswith("manager:"):
        path = spec.split(":", 1)[1]

        def f(obs, info, first):
            if path not in _MODEL:
                from stable_baselines3 import PPO
                _MODEL[path] = PPO.load(path, device="cpu")
            a, _ = _MODEL[path].predict(obs, deterministic=True)
            return int(a)
        return f
    raise ValueError(spec)


def run_one(job):
    seed, kind, spec, opponent = job
    env = ManagerEnv(kinds=(kind,), seed=0, opponent=opponent)
    obs, info = env.reset_to(seed, kind)
    pol = policy_fn(spec)
    first, done = True, False
    acts = []
    while not done:
        a = int(pol(obs, info, first)); first = False
        acts.append(a)
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    return {"seed": seed, "kind": kind, "sev": int(info["ep_sev"]), "n_wolves": info["n_wolves"],
            "two_front": info["two_front"], "status": info["status"], "decisions": info["ep_decisions"],
            "penetrado_ticks": info["penetrado_ticks"], "actions": acts,
            "events": [d["event"] for d in info["ep_log"]], "log": info["ep_log"],
            "hunt": info.get("hunt", {}), "jugada": info.get("jugada")}


def boot_ci(vals, n_boot=10_000, seed=20_260_819):
    v = np.asarray(vals, dtype=float)
    if v.size == 0:
        return [None, None, None]
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, v.size, size=(n_boot, v.size))].mean(axis=1)
    return [float(v.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def _censura(recs):
    cebo = [r for r in recs if r["n_wolves"] >= 3 and any(a != 0 for a in r["actions"])]
    jug = [r["jugada"] for r in cebo if r.get("jugada")]
    if not jug:
        return {"n_eps_cebo_n3": len(cebo), "jugada_completa_frac": None}
    shows = [j["t_show"] for j in jug if j["t_show"] is not None]
    return {"n_eps_cebo_n3": len(cebo),
            "jugada_completa_frac": round(float(np.mean([j["completa"] for j in jug])), 3),
            "con_show_frac": round(float(np.mean([j["t_show"] is not None for j in jug])), 3),
            "con_staged_frac": round(float(np.mean([j["t_staged"] is not None for j in jug])), 3),
            "con_strike_frac": round(float(np.mean([j.get("t_strike") is not None for j in jug])), 3),
            "t_show_mediana": (float(np.median(shows)) if shows else None)}


def summarize(recs):
    by_key = defaultdict(Counter)
    for r in recs:
        a0 = r["actions"][0]
        st = "G" if r["two_front"] else "S"
        by_key[st][a0] += 1; by_key[f"{st}_n{r['n_wolves']}"][a0] += 1; by_key[f"n{r['n_wolves']}"][a0] += 1

    def dist(c):
        tot = sum(c.values())
        return {OPTION_NAMES[a]: round(c[a] / tot, 3) for a in range(N_OPTIONS)} if tot else None
    g3 = [r for r in recs if r["two_front"] and r["n_wolves"] >= 3]
    ev = Counter(e for r in recs for e in r["events"])
    return {"n": len(recs), "sev": boot_ci([r["sev"] for r in recs]),
            "sev_lobos": boot_ci([r["sev"] for r in recs if r["kind"] == "lobos"]),
            "sev_mixto": boot_ci([r["sev"] for r in recs if r["kind"] == "mixto"]),
            "sev_G": boot_ci([r["sev"] for r in recs if r["two_front"]]),
            "sev_S": boot_ci([r["sev"] for r in recs if not r["two_front"]]),
            "P_cebo_G_n3": (float(np.mean([r["actions"][0] != 0 for r in g3])) if g3 else None),
            "P_a_first": {k: dist(v) for k, v in sorted(by_key.items())},
            "decisiones_media": float(np.mean([r["decisions"] for r in recs])),
            "penetrado_ticks_media": float(np.mean([r["penetrado_ticks"] for r in recs])),
            "caza_por_ep": {k: float(np.mean([r.get("hunt", {}).get(k, 0) for r in recs]))
                            for k in ("option_starts", "retargets", "retargets_blocked",
                                      "refix_muerte", "refix_refugio", "refix_otro")},
            # MÉTRICA DE CENSURA (adjudicación VERIF-0): episodios "con cebo jugable" = alguna
            # acción CEBO y n>=3 (el fallback de quórum absorbe n<=2). Jugada COMPLETA = show y
            # asalto SUELTO. sev 0 sin jugar != sev 0 jugando y fallando.
            "censura": _censura(recs),
            "eventos": dict(ev), "success": sum(1 for r in recs if r["status"] == "success")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--opponent", default="reactive", choices=["reactive", "run02", "run09"])
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    label = args.label or (args.policy.replace("manager:", "manager_").replace("/", "_").replace(".zip", ""))
    jobs = [(s, k, args.policy, args.opponent) for s, k in SEEDS]
    with mp.Pool(args.procs) as pool:
        recs = pool.map(run_one, jobs, chunksize=1)
    res = {"policy": args.policy, "opponent": args.opponent,
           "fecha": datetime.now().isoformat(timespec="seconds"),
           "resumen": summarize(recs), "episodes": recs}
    path = OUT / f"{label}__{args.opponent}.json"
    path.write_text(json.dumps(res, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res["resumen"].items() if k != "P_a_first"}, ensure_ascii=False, indent=1))
    print("P(a|G):", res["resumen"]["P_a_first"].get("G"), "P(a|S):", res["resumen"]["P_a_first"].get("S"))
    print("guardado ->", path)


if __name__ == "__main__":
    main()
