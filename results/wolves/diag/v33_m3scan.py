"""v33_m3scan.py — M3 a fondo: ¿quién ancla? ¿por qué el asalto no aguanta el hold?"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE
from coordinators import ReactiveCoordinator
from wolf_controllers import ASSAULT_CHASED_APPROACH
from baseline import build_world

rows = []
for kind in ("lobos", "mixto"):
    for s in range(300):
        if len(rows) >= 40 and kind == "mixto":
            break
        w = build_world(s, kind)
        w.reset()
        if len(w.wolf_group_sizes) != 2:
            continue
        n1 = int(w.wolf_group_sizes[0])
        s1 = np.arange(0, n1); s2 = np.arange(n1, w.n_wolves)
        coord = ReactiveCoordinator(w)
        rel_step = -1
        chased_steps = 0
        pre_steps = 0
        det_step = -1
        while True:
            a = coord.act(w.get_observation())
            _, _, term, trunc, _ = w.step(a)
            if w.phase != "ESCOLTA":
                pre_steps += 1
                act_m = w.drone_state == ACTIVE
                act = w.drones[act_m]
                if act.shape[0] > 0:
                    vel = w.drone_vel[act_m]
                    c = w.wolves[s2].mean(axis=0)
                    rel = c[None, :] - act
                    dd = np.linalg.norm(rel, axis=1)
                    closing = (rel * vel).sum(axis=1) / np.maximum(dd, 1e-9)
                    if ((closing > ASSAULT_CHASED_APPROACH) & (dd <= 250.0)).any():
                        chased_steps += 1
                    if det_step < 0 and float(np.linalg.norm(
                            w.wolves[s2][:, None, :] - act[None, :, :], axis=2).min()) <= w.r_detect:
                        det_step = int(w.step_count)
            if rel_step < 0 and w.wolf_decoy_released:
                rel_step = int(w.step_count)
            if w.phase == "ESCOLTA":
                p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                      else w.cows[w.cow_alive].mean(axis=0))
                d_prey = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
                esc_at = int(w.step_count)
                # el ancla del coordinador se fija en su SIGUIENTE act(): asentar unos pasos
                for _ in range(30):
                    if coord._anchor is not None:
                        break
                    w.step(coord.act(w.get_observation()))
                anc = coord._anchor
                rows.append(dict(seed=s, kind=kind, esc=esc_at,
                                 ancla=("cebo" if anc is not None and anc < n1 else
                                        ("asalto" if anc is not None else "none")),
                                 d_prey=d_prey, rel=rel_step,
                                 chased_frac=chased_steps / max(pre_steps, 1),
                                 det_s2=det_step))
                break
            if term or trunc:
                break

from collections import Counter
anc = Counter(r["ancla"] for r in rows)
d = np.array([r["d_prey"] for r in rows])
print(f"n={len(rows)} | ANCLA: {dict(anc)} | d_prey: mediana {np.median(d):.0f} <=150 {100*(d<=150).mean():.0f}%")
print(f"chased_frac (pre-ESCOLTA, señal de caza sobre s2): media {np.mean([r['chased_frac'] for r in rows]):.2f}")
print("peores (ancla=asalto o d>150):")
for r in [r for r in rows if r["ancla"] == "asalto" or r["d_prey"] > 150][:15]:
    print(f"  {r['kind']}/s{r['seed']}: ancla={r['ancla']} d_prey={r['d_prey']:.0f} esc@{r['esc']} "
          f"rel@{r['rel']} det_s2@{r['det_s2']} chased_frac={r['chased_frac']:.2f}")
print("mejores (muestra):")
for r in [r for r in rows if r["ancla"] == "cebo" and r["d_prey"] <= 150][:8]:
    print(f"  {r['kind']}/s{r['seed']}: d_prey={r['d_prey']:.0f} esc@{r['esc']} rel@{r['rel']} "
          f"det_s2@{r['det_s2']} chased_frac={r['chased_frac']:.2f}")
