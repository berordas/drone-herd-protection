"""v33_steal.py — ¿CÓMO se roba el asalto el ancla? Momento exacto de la 1ª confirmación de equipo."""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE
from coordinators import ReactiveCoordinator
from baseline import build_world

rows = []
for kind in ("lobos",):
    for s in range(300):
        w = build_world(s, kind)
        w.reset()
        if len(w.wolf_group_sizes) != 2:
            continue
        n1 = int(w.wolf_group_sizes[0])
        coord = ReactiveCoordinator(w)
        prev_conf = np.zeros(w.n_wolves, dtype=bool)
        first = None
        rel_step = -1
        while True:
            a = coord.act(w.get_observation())
            conf = coord._confirmed.copy() if coord._confirmed is not None else prev_conf
            new = conf & ~prev_conf
            if first is None and new.any():
                j = int(np.where(new)[0][0])
                act_m = w.drone_state == ACTIVE
                act = w.drones[act_m]
                dmin = float(np.linalg.norm(act - w.wolves[j], axis=1).min()) if act.shape[0] else 1e9
                inv_on = bool(w.drone_investigating.any())
                d_inv = 1e9
                if inv_on:
                    i = int(np.where(w.drone_investigating)[0][0])
                    d_inv = float(np.linalg.norm(w.drones[i] - w.wolves[j]))
                first = dict(seed=s, wolf=j, sector="cebo" if j < n1 else "asalto",
                             step=int(w.step_count), dmin=dmin, inv_on=inv_on, d_inv=d_inv,
                             rel=rel_step, phase=w.phase)
            prev_conf = conf
            _, _, term, trunc, _ = w.step(a)
            if rel_step < 0 and w.wolf_decoy_released:
                rel_step = int(w.step_count)
            if w.phase == "ESCOLTA" and first is not None:
                break
            if term or trunc:
                break
        if first is not None:
            rows.append(first)
        if len(rows) >= 40:
            break

from collections import Counter
print(f"n={len(rows)} | 1ª confirmación de equipo por sector: {dict(Counter(r['sector'] for r in rows))}")
bad = [r for r in rows if r["sector"] == "asalto"]
print(f"\nROBOS ({len(bad)}): quién/cuándo/cómo")
for r in bad:
    print(f"  s{r['seed']}: lobo {r['wolf']} paso {r['step']} fase={r['phase']} dmin={r['dmin']:.0f} "
          f"investigando={r['inv_on']} d_investigador={r['d_inv']:.0f} rel@{r['rel']}")
