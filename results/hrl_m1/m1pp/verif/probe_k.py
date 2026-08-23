"""Sonda Commit K: ¿cuántas veces dispara la regla con Reactive v3.5? + ¿bit a bit con drones LEJOS?"""
import sys, hashlib, numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from rl.policy_wolf_controller import SyncedReactiveCoordinator
from hrl.options_wolf import WolfOptionLayer
from hrl.hrl_check import _blob, _seeds_by_groups

def run(seed, kind, opt, coord_cls):
    layer = WolfOptionLayer(option=opt)
    w = build_world(seed, kind, wolf_controller=layer); coord = coord_cls(w); w.reset()
    evs = []
    while True:
        _o,_r,t,tr,_i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if t or tr: break
    return w, evs

for opt in [("MASA",{}), ("CEBO",{"membership":"keep","hold":50.0}), ("CEBO",{"delta_deg":90.0,"hold":50.0})]:
    tot = dict(rt=0, bl=0, sev=0, n=0)
    for kind in ("lobos","mixto"):
        for s in range(12):
            w, evs = run(s, kind, opt, SyncedReactiveCoordinator)
            rt = [e for e in evs if e["ev"]=="RETARGET"]; bl=[e for e in evs if e["ev"]=="RETARGET_BLOCKED"]
            tot["rt"]+=len(rt); tot["bl"]+=len(bl); tot["sev"]+=w.n_depredadas; tot["n"]+=1
            if rt: print(" ", opt[0], opt[1].get("membership",opt[1].get("delta_deg","")), kind, s, "n=",w.n_wolves, "sev",w.n_depredadas, [(e["t"],e["quien"],e["de"],e["a"],e["d_cur"],e["d_cand"]) for e in rt][:4], "blocked",len(bl))
    print(opt, tot)
