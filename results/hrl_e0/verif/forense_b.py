"""forense_b.py — Hallazgo B: en el replay MASA seed 398 mixto, alrededor de t=880-910,
volcar por tick: fase, ancla, PENETRADO (rama _cover_engaged), nº de lobos confirmados y
sus posiciones, ranuras que _cover_engaged calcula (slots) y a qué dron van, distancia
lobo-vaca del par elegido, drones libres, hand-offs. Contrasta las hipótesis (a)-(d)."""
import sys
import numpy as np
sys.path.insert(0, "/workspace"); sys.path.insert(0, "/data/hrl_e0/verif")
from world import ACTIVE, INCOMING, RETURNING
from hrl import run_e0
from relabel_premature import job_of

seed, kind, arm = 398, "mixto", "masa_reactive"
job = job_of({"arm": arm, "seed": seed, "kind": kind})
wolf = run_e0.make_wolf(job["arm"].get("wolf"))
w = run_e0.make_world(seed, kind, wolf_controller=wolf)
coord = run_e0.make_drone(job["arm"]["drone"])(w)
w.reset()
T0, T1 = 860, 915
while True:
    if wolf is not None:
        wolf.refresh(w)
    t = int(w.step_count)
    wp = coord.act(w.get_observation())
    if T0 <= t <= T1 and t % 3 == 0:
        conf = coord._confirmed
        anchor = coord._anchor
        herd = coord._live_herd()
        free = (w.drone_state == ACTIVE) & ~w.drone_investigating
        idx = np.where(free)[0]
        seen = w.wolves[conf] if conf is not None else np.zeros((0, 2))
        herd_c = herd.mean(axis=0) if herd.shape[0] else None
        herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
        pen = (anchor is not None and herd_c is not None and
               float(np.linalg.norm(w.wolves[anchor] - herd_c)) <= herd_r)
        d = np.linalg.norm(seen[:, None, :] - herd[None, :, :], axis=2) if seen.shape[0] and herd.shape[0] else None
        # ranuras que devolvería _cover_engaged
        slots_txt = ""
        if pen and d is not None:
            near_cow = d.argmin(axis=1); order = np.argsort(d.min(axis=1))
            k = idx.size
            sl = []
            for s in range(k):
                wj = int(order[s % order.size]); cow = herd[near_cow[wj]]
                v = w.wolves[conf][wj] - cow; v = v / max(float(np.linalg.norm(v)), 1e-9)
                sl.append((wj, np.round(cow + v * coord.engage_standoff, 1).tolist()))
            slots_txt = f" slots(lobo→pos)={sl}"
        st = {i: int(w.drone_state[i]) for i in range(w.n_drones)}
        print(f"t={t} phase={w.phase} anchor={anchor} n_conf={0 if conf is None else int(conf.sum())} "
              f"herd_n={herd.shape[0]} herd_r={herd_r:.1f} d_anchor_c={float(np.linalg.norm(w.wolves[anchor]-herd_c)) if (anchor is not None and herd_c is not None) else None:.1f} "
              f"PENETRADO={pen} libres={idx.tolist()} states={st} inv={np.where(w.drone_investigating)[0].tolist()}"
              f"{slots_txt}")
        for i in idx:
            print(f"    dron {i} pos={np.round(w.drones[i],1).tolist()} wp={np.round(wp[i],1).tolist()}")
        if d is not None:
            print(f"    lobos conf pos={np.round(seen,1).tolist()} dmin_a_vaca={np.round(d.min(axis=1),1).tolist()}")
    _o, _r, term, trunc, _i = w.step(wp)
    if term or trunc or t > T1:
        break
