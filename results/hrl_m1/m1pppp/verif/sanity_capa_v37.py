"""Sanity E0.1 (paquete v3.7): celda G n>=3 CEBO_keep vs MASA, 50 pares, Reactive-estatica.
Referencia RE-FIJADA v3.6: Δ = +1.16 [+0.42, +1.90]. El paquete CAMBIA cosas A PROPOSITO
(senuelo v2 en keep, relevo centinela en la defensa): se mide, se reporta el movimiento y la
referencia se RE-FIJA en PREREGISTRO_v3 (escalar solo si conducta rara/inversion de signo)."""
import json, sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator


def run(job):
    seed, opt = job
    layer = WolfOptionLayer(option=opt)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if t or tr:
            break
    return {"sev": int(w.n_depredadas),
            "completa": bool(layer.t_show is not None and layer.t_suelta is not None),
            "t_show": layer.t_show, "stalls": int(layer.n_stalls), "status": w.status}


def seeds_G(count):
    out, s = [], 0
    while len(out) < count and s < 4000:
        w = build_world(s, "lobos")
        w.reset()
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
        recs = pool.map(run, jobs, chunksize=2)
    cebo, masa = recs[:50], recs[50:]
    d = np.array([c["sev"] - m["sev"] for c, m in zip(cebo, masa)], float)
    rng = np.random.default_rng(20260821)
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    out = {"n_pares": 50,
           "sev_keep": float(np.mean([r["sev"] for r in cebo])),
           "sev_masa": float(np.mean([r["sev"] for r in masa])),
           "delta_keep_menos_masa": [round(float(d.mean()), 3), round(float(np.percentile(b, 2.5)), 3),
                                     round(float(np.percentile(b, 97.5)), 3)],
           "ref_v36": [1.16, 0.42, 1.90],
           "censura_keep": {"jugada_completa_frac": float(np.mean([r["completa"] for r in cebo])),
                            "stalls_total": int(sum(r["stalls"] for r in cebo))}}
    json.dump(out, open("/data/hrl_m1/m1pppp/sanity_capa_v37.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    print("SANITY_V37_OK")
