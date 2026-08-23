"""RE-NIVELADO paso 1 — sanity de capa K: celda E0.1 (estrato G, n>=3): CEBO_keep-forzado vs
MASA-forzado, 50 pares de semillas EMPAREJADAS, capa K, Reactive-ESTÁTICA (v3.6). Reporta el
Δ nuevo (la regla de caza beneficia a ambos brazos). Referencia v3.5 (órbita, capa sin regla):
Δ = +0.85 [+0.60, +1.09]. Si |Δ_nuevo − 0.85| > 0.3 o conducta rara => PARAR y escalar con GIFs."""
import sys, json
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

def run(seed, opt):
    layer = WolfOptionLayer(option=opt)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    while True:
        _o,_r,t,tr,_i = w.step(coord.act(w.get_observation()))
        if t or tr: break
    return {"sev": int(w.n_depredadas), "retargets": layer.n_retargets,
            "blocked": layer.n_retarget_blocked, "status": w.status}

def seeds_G(count):
    out, s = [], 0
    while len(out) < count and s < 4000:
        w = build_world(s, "lobos"); w.reset()
        if len(w.wolf_group_sizes) == 2 and w.n_wolves >= 3:
            out.append(s)
        s += 1
    if len(out) < count:
        raise RuntimeError(f"solo {len(out)}")
    return out

if __name__ == "__main__":
    import multiprocessing as mp
    ss = seeds_G(50)
    jobs = [(s, ("CEBO", {"membership": "keep", "hold": 50.0})) for s in ss] + \
           [(s, ("MASA", {})) for s in ss]
    with mp.Pool(24) as pool:
        recs = pool.starmap(run, jobs, chunksize=2)
    cebo, masa = recs[:50], recs[50:]
    d = np.array([c["sev"] - m["sev"] for c, m in zip(cebo, masa)], dtype=float)
    rng = np.random.default_rng(20260819)
    boots = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    out = {"n_pares": 50,
           "sev_cebo": float(np.mean([r["sev"] for r in cebo])),
           "sev_masa": float(np.mean([r["sev"] for r in masa])),
           "delta_keep_menos_masa": [float(d.mean()), float(np.percentile(boots, 2.5)),
                                      float(np.percentile(boots, 97.5))],
           "ref_v35": 0.85,
           "retargets_ep": {"cebo": float(np.mean([r["retargets"] for r in cebo])),
                             "masa": float(np.mean([r["retargets"] for r in masa]))},
           "blocked_ep": {"cebo": float(np.mean([r["blocked"] for r in cebo])),
                           "masa": float(np.mean([r["blocked"] for r in masa]))}}
    out["_veredicto"] = ("OK (|Δ−0.85| <= 0.3)" if abs(out["delta_keep_menos_masa"][0] - 0.85) <= 0.3
                          else "DESVIACIÓN > 0.3 -> PARAR y escalar con GIFs")
    json.dump(out, open("/data/hrl_m1/m1pp/sanity_capaK.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
