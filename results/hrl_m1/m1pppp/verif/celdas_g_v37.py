"""celdas_g_v37.py — CELDAS G (firma STOP-replica): CEBO_keep vs CEBO(d180), estrato G n>=3,
100 semillas EMPAREJADAS, Reactive-estatica, mundo v3.7 PINEADO (ejecutar desde
/workspace/wt_v37_replica). Pregunta: ¿es plano el paisaje G entre keep y d180?"""
import json, sys
import numpy as np
sys.path.insert(0, "/workspace/wt_v37_replica")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

ARMS = {"KEEP": ("CEBO", {"membership": "keep", "hold": 50.0}),
        "D180": ("CEBO", {"delta_deg": 180.0, "hold": 50.0}),
        "D90": ("CEBO", {"delta_deg": 90.0, "hold": 50.0})}


def run(job):
    seed, arm = job
    layer = WolfOptionLayer(option=ARMS[arm])
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs = []
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if t or tr:
            break
    show = [e for e in evs if e["ev"] == "SHOW_START"]
    return {"seed": seed, "arm": arm, "sev": int(w.n_depredadas), "n": int(w.n_wolves),
            "completa": bool(layer.t_show is not None and layer.t_suelta is not None),
            "stalls": int(layer.n_stalls),
            "staged_causa": (show[0].get("staged_causa") if show else None)}


def seeds_G(count):
    out, s = [], 0
    while len(out) < count and s < 8000:
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
    ss = seeds_G(100)
    jobs = [(s, a) for a in ARMS for s in ss]
    with mp.Pool(24) as pool:
        recs = pool.map(run, jobs, chunksize=2)
    by = {a: np.array([r["sev"] for r in recs if r["arm"] == a], float) for a in ARMS}
    rng = np.random.default_rng(20260823)

    def ci(d):
        b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
        return [round(float(d.mean()), 3), round(float(np.percentile(b, 2.5)), 3),
                round(float(np.percentile(b, 97.5)), 3)]

    res = {"config": "v3.7 pineado (wt_v37_replica); G n>=3; 100 pares; Reactive-estatica",
           "sev": {a: ci(by[a]) for a in ARMS},
           "delta_d180_menos_keep": ci(by["D180"] - by["KEEP"]),
           "delta_d90_menos_keep": ci(by["D90"] - by["KEEP"]),
           "censura": {a: {"completa": round(float(np.mean([r["completa"] for r in recs if r["arm"] == a])), 3),
                           "stalls": int(sum(r["stalls"] for r in recs if r["arm"] == a))} for a in ARMS},
           "episodes": recs}
    json.dump(res, open("/data/hrl_m1/m1pppp/celdas_g_v37.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "episodes"}, indent=1, ensure_ascii=False))
    print("CELDAS_G_OK")
