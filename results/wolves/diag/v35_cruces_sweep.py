"""v35_cruces_sweep.py — la MÉTRICA DEL USUARIO (cruces de segmento entre drones contiguos) en las
MISMAS 28 eps que v3.4 (seeds 0-13 × lobos/mixto), con el CONTADOR EXACTO de v34_cruces_anatomia.py,
parametrizada por espaciado de la barrera: ReactiveCoordinator(w, drone_spacing=S) (el standoff se
deriva solo, misma fórmula). Uso: python3 v35_cruces_sweep.py <spacing> -> JSON por stdout."""
import json
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, STATIC_DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import build_world

SPACING = float(sys.argv[1])


def seg_cross_t(p1, p2, a, b):
    d1, d2 = p2 - p1, b - a
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
    s = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
    if 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0:
        return t, s
    return None


crosses, flanks = [], []
sev = []
for kind in ("lobos", "mixto"):
    for seed in range(14):
        w = build_world(seed, kind)
        w.reset()
        c = ReactiveCoordinator(w, drone_spacing=SPACING)
        prev_wolves = w.wolves.copy()
        formed, prev_ids = False, None
        while True:
            a = c.act(w.get_observation())
            clean = (c._pose_last_step == w.step_count)
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx = np.where(free)[0]
            wp = a[idx].copy()
            _o, _r, term, trunc, info = w.step(a)
            cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
            free2 = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx2 = np.where(free2)[0]
            same = idx.size == idx2.size and np.array_equal(idx, idx2)
            if clean and same and idx.size >= 2:
                ids_now = tuple(idx.tolist())
                if prev_ids != ids_now:
                    formed = False
                if float(np.linalg.norm(w.drones[idx] - wp, axis=1).max()) <= 2.0:
                    formed = True
                prev_ids = ids_now
            else:
                formed, prev_ids = False, None
            if w.phase == "ESCOLTA" and idx.size >= 2 and cows_ns.shape[0] > 0:
                herd = c._live_herd()
                in_pen = True
                if c._anchor is not None and herd.shape[0] > 0:
                    hc = herd.mean(axis=0)
                    hr = float(np.linalg.norm(herd - hc, axis=1).max()) if herd.shape[0] > 1 else 0.0
                    in_pen = float(np.linalg.norm(w.wolves[c._anchor] - hc)) <= hr
                pts = w.drones[idx]
                cc = pts - pts.mean(axis=0)
                _u2, _s2, vt = np.linalg.svd(cc)
                order = np.argsort(pts @ vt[0])
                pts_o = pts[order]
                hc_now = cows_ns.mean(axis=0)
                axis, normal = vt[0], vt[1]
                lo, hi = float(pts_o[0] @ axis), float(pts_o[-1] @ axis)
                for j in range(w.n_wolves):
                    p1, p2 = prev_wolves[j], w.wolves[j]
                    inward = np.linalg.norm(p2 - hc_now) < np.linalg.norm(p1 - hc_now)
                    hit = False
                    for kk in range(idx.size - 1):
                        r = seg_cross_t(p1, p2, pts_o[kk], pts_o[kk + 1])
                        if r is None:
                            continue
                        hit = True
                        _t, s = r
                        gap = float(np.linalg.norm(pts_o[kk] - pts_o[kk + 1]))
                        sfrac = min(s, 1.0 - s)
                        crosses.append(dict(
                            kind=kind, seed=seed, seg=kk, nseg=int(idx.size - 1),
                            extremo=bool(kk == 0 or kk == idx.size - 2), gap=gap,
                            d_borde=sfrac * gap, sfrac=sfrac, inward=bool(inward),
                            pen=bool(in_pen), formed=bool(formed),
                            walled=bool(w._wolf_walled[j]), scared=bool(w._wolf_scared[j])))
                    if not hit:
                        s1 = float((p1 - pts_o[0]) @ normal)
                        s2n = float((p2 - pts_o[0]) @ normal)
                        if s1 * s2n < 0:
                            lam = s1 / (s1 - s2n)
                            px = p1 + lam * (p2 - p1)
                            ax = float(px @ axis)
                            if ax < lo - 1e-9 or ax > hi + 1e-9:
                                flanks.append(dict(kind=kind, seed=seed, inward=bool(inward),
                                                   pen=bool(in_pen)))
            prev_wolves = w.wolves.copy()
            if term or trunc:
                sev.append(float(info.get("severity", np.nan)) if isinstance(info, dict) else np.nan)
                break

inw = [x for x in crosses if x["inward"] and not x["pen"]]
fl = [f for f in flanks if f["inward"] and not f["pen"]]
out = dict(
    spacing=SPACING,
    overlap=2 * STATIC_DETER_RADIUS - SPACING,
    total_crosses=len(crosses),
    inward_clean=len(inw),
    inward_clean_per_ep=len(inw) / 28.0,
    walled=sum(x["walled"] for x in inw),
    scared=sum(x["scared"] for x in inw),
    formed=sum(1 for x in inw if x["formed"]),
    interior=sum(1 for x in inw if not x["extremo"]),
    flank_rodeos_inward_clean=len(fl),
    sfrac_median=float(np.median([x["sfrac"] for x in inw])) if inw else None,
    gap_median=float(np.median([x["gap"] for x in inw])) if inw else None,
)
print(json.dumps(out))
