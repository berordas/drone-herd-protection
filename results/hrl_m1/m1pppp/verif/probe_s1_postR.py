import sys, json
import numpy as np
sys.path.insert(0, "/workspace")
import multiprocessing as mp
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator
from world import ACTIVE, RETURNING, INCOMING

def run(seed):
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs, relevos, prev_inc = [], 0, 0
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        inc = int((w.drone_state == INCOMING).sum())
        if inc < prev_inc:
            relevos += 1
        prev_inc = inc
        if t or tr:
            break
    align = [e for e in evs if e["ev"] == "ALIGN_END"]
    stall = [e for e in evs if e["ev"] == "STALL"]
    return {"seed": seed, "sev": int(w.n_depredadas), "t_show": layer.t_show,
            "t_staged": layer.t_staged, "stalls": len(stall),
            "align": (align[0]["causa"] if align else None),
            "t_align": (align[0]["t"] if align else None),
            "relevos": relevos, "ticks": int(w.step_count), "status": w.status}

if __name__ == "__main__":
    seeds = [3, 5, 9, 14, 18, 24, 35, 36, 55]
    with mp.get_context("fork").Pool(9) as pool:
        rows = pool.map(run, seeds, chunksize=1)
    for r in rows:
        print(r)
    sin_show = [r["seed"] for r in rows if r["t_show"] is None]
    print("SIN SHOW (2º modo):", sin_show, "| con STALL:", [r["seed"] for r in rows if r["stalls"]])
