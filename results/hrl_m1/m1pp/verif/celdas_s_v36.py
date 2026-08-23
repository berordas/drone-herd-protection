"""Celdas S bajo v3.6 (ADENDA DE ADJUDICACIÓN del PREREGISTRO_v2 — el disparo se activó:
Pstoch(Δ180|S)=0.948 con H(a|S)<0.9 en el checkpoint final). Brazos FORZADOS MASA / CEBO(Δ90) /
CEBO(Δ180) (membership manager, hold 50 — las celdas de E0.1), estrato S (1 grupo de spawn),
n>=3, 100 semillas EMPAREJADAS, vs Reactive-estática. Se mide ANTES de adjudicar la cláusula."""
import json
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

ARMS = {"MASA": ("MASA", {}),
        "D90": ("CEBO", {"delta_deg": 90.0, "hold": 50.0}),
        "D180": ("CEBO", {"delta_deg": 180.0, "hold": 50.0})}


def run(job):
    seed, arm = job
    layer = WolfOptionLayer(option=ARMS[arm])
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if t or tr:
            break
    return {"seed": seed, "arm": arm, "sev": int(w.n_depredadas), "n": int(w.n_wolves)}


def seeds_S(count):
    out, s = [], 0
    while len(out) < count and s < 8000:
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 1 and w.n_wolves >= 3:
            out.append(s)
        s += 1
    if len(out) < count:
        raise RuntimeError(f"solo {len(out)}")
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    ss = seeds_S(100)
    jobs = [(s, a) for a in ARMS for s in ss]
    with mp.Pool(20) as pool:
        recs = pool.map(run, jobs, chunksize=2)
    by = {a: np.array([r["sev"] for r in recs if r["arm"] == a], float) for a in ARMS}
    rng = np.random.default_rng(20260820)

    def ci(d):
        b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
        return [round(float(d.mean()), 3), round(float(np.percentile(b, 2.5)), 3),
                round(float(np.percentile(b, 97.5)), 3)]

    d90 = by["D90"] - by["MASA"]
    d180 = by["D180"] - by["MASA"]
    diff = by["D180"] - by["D90"]
    out = {"n_pares": 100, "seeds": ss,
           "sev": {a: float(by[a].mean()) for a in ARMS},
           "delta_D90_menos_MASA": ci(d90),
           "delta_D180_menos_MASA": ci(d180),
           "delta_D180_menos_D90": ci(diff),
           "veredicto": ("D180 >= D90: la cláusula se evalúa contra el paisaje v3.6 MEDIDO "
                          "(el manager tenía razón; B_oracle juega Δ90 en S)"
                          if diff.mean() >= 0 else
                          "D180 < D90: la cláusula FALLA, con evidencia")}
    json.dump(out, open("/data/hrl_m1/m1pp/celdas_s_v36.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "seeds"}, indent=1, ensure_ascii=False))
