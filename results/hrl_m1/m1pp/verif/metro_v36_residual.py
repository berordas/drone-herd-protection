"""Piezas RESIDUALES del metro v3.6 con POOL (20 procs, OMP_NUM_THREADS=1): run02/run09 ×
{estática oficial, órbita de entrenamiento}. Misma vara que evaluate() (mismas semillas 0-99,
CONFIG_V2, lobos scriptados), agregado equivalente."""
import os
os.environ["OMP_NUM_THREADS"] = "1"
import json, pathlib, sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world, run_episode_metrics, KINDS

OUT = pathlib.Path("/data/hrl_m1/m1pp/metro")
PIEZAS = {
    "run02":  ("/data/drones/run02_v34/model.zip", None,  "run02_en_v36_estatica.json",
               "run02 (v3.4, órbita) evaluado en v3.6-estática (mismatch de patrulla documentado)"),
    "run02o": ("/data/drones/run02_v34/model.zip", 0.02,  "run02_en_v36_orbita.json",
               "run02 con SU patrulla de entrenamiento (órbita 0.02)"),
    "run09e": ("/data/drones/run09_v35/model.zip", None,  "run09_en_v36_estatica.json",
               "run09 (v3.5, órbita) evaluado en v3.6-estática (config oficial; mismatch documentado)"),
    "run09o": ("/data/drones/run09_v35/model.zip", 0.02,  "run09_en_v36_orbita.json",
               "run09 con SU patrulla de entrenamiento (órbita 0.02)"),
}
_M = {}

def one(job):
    import torch
    torch.set_num_threads(1)
    path, omega, seed, kind = job
    if path not in _M:
        from stable_baselines3 import PPO
        _M[path] = PPO.load(path, device="cpu")
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    w = build_world(seed, kind)
    c = ResidualDroneCoordinator(w, model=_M[path])
    if omega is not None:
        c.inner.patrol_omega = omega
    m = run_episode_metrics(w, c)
    return {"kind": kind, "seed": seed, **m}

if __name__ == "__main__":
    import multiprocessing as mp
    name = sys.argv[1]
    path, omega, outfile, nota = PIEZAS[name]
    jobs = [(path, omega, s, k) for k in KINDS for s in range(100)]
    with mp.get_context("spawn").Pool(20) as pool:
        recs = pool.map(one, jobs, chunksize=2)
    by_kind = {}
    for k in KINDS:
        rs = [r for r in recs if r["kind"] == k]
        sev = np.array([r["n_depredadas"] for r in rs], float)
        from collections import Counter
        terms = Counter(r["status"] for r in rs)
        esp = [r["espera_handoff_media"] for r in rs if r["espera_handoff_media"] is not None]
        by_kind[k] = {"label": k, "severity_mean": float(sev.mean()), "severity_std": float(sev.std()),
                      "n_safe_mean": float(np.mean([r["n_safe"] for r in rs])),
                      "terminals": dict(terms),
                      "relevos_ep": float(np.mean([r["relevos"] for r in rs])),
                      "espera_handoff_media": (float(np.mean(esp)) if esp else None),
                      "stranded_ep": float(np.mean([r["stranded"] for r in rs])),
                      "episodes": rs}
    res = {"nota": nota, "by_kind": by_kind,
           "aggregate": {"severity_mean": float(np.mean([r["n_depredadas"] for r in recs])),
                          "n_safe_mean": float(np.mean([r["n_safe"] for r in recs]))}}
    (OUT / outfile).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(name.upper(), {k: round(v["severity_mean"], 3) for k, v in by_kind.items()},
          "| relevos/esp/stranded:", {k: (round(v["relevos_ep"], 1), None if v["espera_handoff_media"] is None else round(v["espera_handoff_media"]), round(v["stranded_ep"], 2)) for k, v in by_kind.items()})
