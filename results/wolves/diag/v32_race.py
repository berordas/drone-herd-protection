"""v32_race.py — anatomía de la CARRERA del timing en episodios 2-frentes (v3.2 en curso).

Para cada episodio: paso de 1ª detección del asalto (algún lobo s2 <= r_detect de un ACTIVE),
paso de lanzamiento de investigación, paso de release (y si fue por gate-dark o por regla base),
paso de ESCOLTA, y d_prey del asalto en cada hito. Decompone la banda de fallo 151-200.
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE
from coordinators import ReactiveCoordinator
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
        coord = ReactiveCoordinator(w)
        det_step = inv_step = rel_step = -1
        d_at_det = d_at_rel = None
        prev_inv_any = False
        while True:
            prev_inv = w.drone_investigating.copy()
            a = coord.act(w.get_observation())
            _, _, term, trunc, _ = w.step(a)
            p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                  else w.cows[w.cow_alive].mean(axis=0))
            d_prey = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
            act_dr = w.drones[w.drone_state == ACTIVE]
            if det_step < 0 and act_dr.shape[0] > 0:
                dmin = float(np.linalg.norm(w.wolves[n1:][:, None, :] - act_dr[None, :, :], axis=2).min())
                if dmin <= w.r_detect:
                    det_step = int(w.step_count); d_at_det = d_prey
            if inv_step < 0 and w.drone_investigating.any() and not prev_inv_any:
                inv_step = int(w.step_count)
            prev_inv_any = bool(w.drone_investigating.any())
            if rel_step < 0 and w.wolf_decoy_released:
                rel_step = int(w.step_count); d_at_rel = d_prey
            if w.phase == "ESCOLTA":
                who = "?"
                for i in np.where(prev_inv)[0]:
                    dw = np.linalg.norm(w.wolves - w.drones[i], axis=1)
                    jw = int(np.argmin(dw))
                    if dw[jw] <= w.r_confirm + 2.0:
                        who = "cebo" if jw < n1 else "asalto"
                rows.append(dict(kind=kind, seed=s, who=who, d_esc=d_prey, esc=int(w.step_count),
                                 det=det_step, d_det=d_at_det, inv=inv_step,
                                 rel=rel_step, d_rel=d_at_rel))
                break
            if term or trunc:
                break

d = np.array([r["d_esc"] for r in rows])
print(f"n={len(rows)}  <=150: {int((d<=150).sum())}  mediana {np.median(d):.0f}")
print("\n-- BANDA DE FALLO 150-220 (la fixable) --")
for r in sorted([r for r in rows if 150 < r["d_esc"] <= 220], key=lambda r: r["d_esc"]):
    print(f"  {r['kind']}/s{r['seed']}: d_esc={r['d_esc']:.0f} who={r['who']} | det@{r['det']}"
          f"(d={r['d_det'] if r['d_det'] is None else round(r['d_det'])}) inv@{r['inv']}"
          f" rel@{r['rel']}(d={r['d_rel'] if r['d_rel'] is None else round(r['d_rel'])}) esc@{r['esc']}")
print("\n-- PASAN (muestra 8) --")
for r in sorted([r for r in rows if r["d_esc"] <= 150], key=lambda r: -r["d_esc"])[:8]:
    print(f"  {r['kind']}/s{r['seed']}: d_esc={r['d_esc']:.0f} who={r['who']} | det@{r['det']}"
          f"(d={r['d_det'] if r['d_det'] is None else round(r['d_det'])}) inv@{r['inv']}"
          f" rel@{r['rel']}(d={r['d_rel'] if r['d_rel'] is None else round(r['d_rel'])}) esc@{r['esc']}")
