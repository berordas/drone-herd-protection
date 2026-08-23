"""v35_residual_anatomia.py — ANATOMÍA de los cruces RESIDUALES con paredes muy solapadas:
si el caso estático está sellado (testbed: s<=7.5 aguanta con pose QUIETA), ¿POR QUÉ siguen
cruzando en episodios reales? Hipótesis: la línea que AVANZA (sobre-apuntado d_ancla+10, hasta
~3.1 m/s con el gobernador) ATROPELLA a lobos estancados en el corredor — el empuje saliente
neto de la pared (<=~0.7 m/s) no puede ganar a la velocidad de avance de la pose.
Por cruce registra: |Δc| y |Δφ| de la pose EN ese paso, |v| real del lobo, aproximación del
dron más cercano hacia el lobo (>1 = la línea se le echa encima), ángulo de la velocidad del
lobo respecto a la normal de la línea, y si el dron aproximaba por debajo del gate de expulsión.
Uso: python3 v35_residual_anatomia.py <spacing>"""
import json
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, SCARE_APPROACH_MIN
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


rows = []
for kind in ("lobos", "mixto"):
    for seed in range(14):
        w = build_world(seed, kind)
        w.reset()
        c = ReactiveCoordinator(w, drone_spacing=SPACING)
        prev_wolves = w.wolves.copy()
        prev_pose = None
        walled_streak = np.zeros(w.n_wolves, dtype=int)
        while True:
            a = c.act(w.get_observation())
            clean = (c._pose_last_step == w.step_count)
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx = np.where(free)[0]
            _o, _r, term, trunc, _i = w.step(a)
            walled_streak = np.where(w._wolf_walled, walled_streak + 1, 0)
            cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
            d_pose = dphi = None
            if clean and c._pose_c is not None:
                if prev_pose is not None:
                    pc, pu = prev_pose
                    d_pose = float(np.linalg.norm(c._pose_c - pc))
                    cr = pu[0] * c._pose_u[1] - pu[1] * c._pose_u[0]
                    dphi = abs(float(np.arctan2(cr, float(pu @ c._pose_u))))
                prev_pose = (c._pose_c.copy(), c._pose_u.copy())
            else:
                prev_pose = None
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
                vels_o = w.drone_vel[idx][order]
                hc_now = cows_ns.mean(axis=0)
                normal = vt[1]
                for j in range(w.n_wolves):
                    p1, p2 = prev_wolves[j], w.wolves[j]
                    inward = np.linalg.norm(p2 - hc_now) < np.linalg.norm(p1 - hc_now)
                    for kk in range(idx.size - 1):
                        r = seg_cross_t(p1, p2, pts_o[kk], pts_o[kk + 1])
                        if r is None or not inward or in_pen:
                            continue
                        dw = np.linalg.norm(pts_o - p2, axis=1)
                        jn = int(np.argmin(dw))
                        u_dl = (p2 - pts_o[jn]) / max(float(dw[jn]), 1e-9)
                        appr = float(vels_o[jn] @ u_dl)             # >0 = el dron se echa ENCIMA
                        vw = w.wolf_vel[j]
                        vn = float(np.linalg.norm(vw))
                        cosang = abs(float(vw @ normal)) / max(vn, 1e-9)
                        rows.append(dict(
                            kind=kind, seed=seed, step=int(w.step_count),
                            d_pose=d_pose, dphi_deg=(np.degrees(dphi) if dphi is not None else None),
                            v_lobo=vn, cos_normal=cosang, d_dron=float(dw[jn]),
                            approach=appr, gate_expulsion=bool(appr > SCARE_APPROACH_MIN),
                            walled=bool(w._wolf_walled[j]), scared=bool(w._wolf_scared[j]),
                            streak_walled=int(walled_streak[j])))
            prev_wolves = w.wolves.copy()
            if term or trunc:
                break

print(f"s={SPACING}: {len(rows)} cruces hacia dentro (CLEAN)")
if rows:
    dp = np.array([r["d_pose"] for r in rows if r["d_pose"] is not None])
    print(f"  pose |Δc| en el paso del cruce (m): mediana {np.median(dp):.3f}  p90 "
          f"{np.percentile(dp, 90):.3f}  (equivale a {np.median(dp) / 0.1:.1f} m/s; quieta <0.1)"
          if dp.size else "  (sin pose)")
    dq = np.array([r["dphi_deg"] for r in rows if r["dphi_deg"] is not None])
    if dq.size:
        print(f"  pose |Δφ| (grados/paso): mediana {np.median(dq):.3f}  p90 {np.percentile(dq, 90):.3f}")
    vl = np.array([r["v_lobo"] for r in rows])
    ap = np.array([r["approach"] for r in rows])
    cn = np.array([r["cos_normal"] for r in rows])
    st = np.array([r["streak_walled"] for r in rows])
    print(f"  |v| del lobo al cruzar: mediana {np.median(vl):.2f} m/s  p10 {np.percentile(vl, 10):.2f} "
          f"(caza plena=4; lento = lo llevan por delante)")
    print(f"  aproximación del dron más cercano: mediana {np.median(ap):+.2f} m/s  "
          f"cruces con dron echándosele encima (>1, gate expulsión): {int((ap > 1).sum())}/{len(rows)} | "
          f"con aproximación >0: {int((ap > 0).sum())}/{len(rows)}")
    print(f"  |cos| v_lobo·normal: mediana {np.median(cn):.2f} (1=perpendicular a la línea, 0=rasante)")
    print(f"  pasos seguidos walled antes de cruzar: mediana {np.median(st):.0f}  p90 {np.percentile(st, 90):.0f}")
    print(f"  scared al cruzar: {sum(r['scared'] for r in rows)} | walled: {sum(r['walled'] for r in rows)}")
with open(f"v35_residual_s{SPACING}.json", "w") as f:
    json.dump(rows, f)
