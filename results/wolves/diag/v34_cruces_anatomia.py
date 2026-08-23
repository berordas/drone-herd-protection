"""v34_cruces_anatomia.py — DIAGNÓSTICO 2 (solo lectura): ¿DÓNDE y CUÁNDO cruzan los lobos la
línea rígida v3.4? Mismas 28 eps (seeds 0-13 × lobos/mixto) y mismo contador que v34_rigidez.

Por cruce de segmento entre drones contiguos se registra:
  - posición del SEGMENTO en la línea: extremo (primero/último de los k-1) vs interior;
  - PUNTO de cruce dentro del hueco: dist al dron más cercano (d_borde) y fracción s∈[0,0.5]
    (0.5 = centro exacto del corredor);
  - anchura REAL del hueco y si supera 2·STATIC_DETER_RADIUS (corredor abierto) o no (paredes
    tangentes/solapadas);
  - estado de la POSE en ese paso (rama CLEAN): |Δc| y |Δφ| (quieta vs moviéndose/rotando),
    y si la línea estaba FORMADA (err_max<=2 alcanzado, mismo conjunto);
  - estado del lobo (walled/scared/libre) y rama (CLEAN/PENETRADO).
Aparte se cuentan los RODEOS POR LOS EXTREMOS (no son cruces de segmento): lobo que cruza la
RECTA de la línea hacia dentro con el punto de corte FUERA del tramo ocupado por los drones.
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, STATIC_DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import build_world


def seg_cross_t(p1, p2, a, b):
    """Devuelve (t, s) del cruce p1->p2 con a->b, o None."""
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
for kind in ("lobos", "mixto"):
    for seed in range(14):
        w = build_world(seed, kind)
        w.reset()
        c = ReactiveCoordinator(w)
        prev_wolves = w.wolves.copy()
        prev_pose_c = prev_pose_u = None
        formed, prev_ids = False, None
        while True:
            a = c.act(w.get_observation())
            clean = (c._pose_last_step == w.step_count)
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx = np.where(free)[0]
            wp = a[idx].copy()
            _o, _r, term, trunc, _i = w.step(a)
            cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
            # pose de este paso (tras act)
            d_pose = dphi = None
            if clean and c._pose_c is not None:
                if prev_pose_c is not None:
                    d_pose = float(np.linalg.norm(c._pose_c - prev_pose_c))
                    cr = prev_pose_u[0] * c._pose_u[1] - prev_pose_u[1] * c._pose_u[0]
                    dphi = abs(float(np.arctan2(cr, float(prev_pose_u @ c._pose_u))))
                prev_pose_c, prev_pose_u = c._pose_c.copy(), c._pose_u.copy()
            else:
                prev_pose_c = prev_pose_u = None
            # estado FORMADA (mismo criterio que v34_rigidez, con el conjunto de ANTES del step)
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
                            kind=kind, seed=seed, seg=kk, nseg=idx.size - 1,
                            extremo=(kk == 0 or kk == idx.size - 2), gap=gap,
                            d_borde=sfrac * gap, sfrac=sfrac, inward=bool(inward),
                            pen=in_pen, formed=formed, d_pose=d_pose, dphi=dphi,
                            walled=bool(w._wolf_walled[j]), scared=bool(w._wolf_scared[j])))
                    # rodeo por el EXTREMO: cruza la RECTA (lado del normal cambia) fuera del tramo
                    if not hit:
                        s1 = float((p1 - pts_o[0]) @ normal)
                        s2n = float((p2 - pts_o[0]) @ normal)
                        if s1 * s2n < 0:
                            lam = s1 / (s1 - s2n)
                            px = p1 + lam * (p2 - p1)
                            ax = float(px @ axis)
                            if ax < lo - 1e-9 or ax > hi + 1e-9:
                                flanks.append(dict(kind=kind, seed=seed, inward=bool(inward), pen=in_pen,
                                                   d_ext=float(min(abs(ax - lo), abs(ax - hi)))))
            prev_wolves = w.wolves.copy()
            if term or trunc:
                break

print(f"CONSTANTES: STATIC_DETER_RADIUS={STATIC_DETER_RADIUS} | spacing nominal=2·STATIC="
      f"{2 * STATIC_DETER_RADIUS} -> paredes TANGENTES a spacing exacto (solape 0, corredor 0)")
inw = [c for c in crosses if c["inward"] and not c["pen"]]
print(f"\nCRUCES de segmento: total {len(crosses)} | HACIA DENTRO con línea en pie (CLEAN): {len(inw)}")
ne = sum(1 for c in inw if c["extremo"])
print(f"  segmento: EXTREMO {ne} vs INTERIOR {len(inw) - ne} "
      f"(con k=4 hay 2 extremos y 1 interior -> esperado al azar ~2:1)")
db = np.array([c["d_borde"] for c in inw])
sf = np.array([c["sfrac"] for c in inw])
print(f"  punto de cruce, dist al dron más cercano: p25 {np.percentile(db, 25):.1f}  mediana "
      f"{np.median(db):.1f}  p75 {np.percentile(db, 75):.1f} m | fracción del hueco (0.5=centro): "
      f"mediana {np.median(sf):.2f}  p25 {np.percentile(sf, 25):.2f}")
g = np.array([c["gap"] for c in inw])
print(f"  hueco real: mediana {np.median(g):.1f}  p90 {np.percentile(g, 90):.1f}  máx {g.max():.1f} | "
      f"con hueco > 2·STATIC (corredor abierto): {int((g > 2 * STATIC_DETER_RADIUS + 1e-9).sum())}/{len(inw)}")
nf = sum(1 for c in inw if c["formed"])
print(f"  estado de la línea: FORMADA {nf} vs ensamblaje/incorporación {len(inw) - nf}")
dp = np.array([c["d_pose"] for c in inw if c["d_pose"] is not None])
dq = np.array([c["dphi"] for c in inw if c["dphi"] is not None])
if dp.size:
    quiet = int(((dp < 0.1) & (dq < 0.005)).sum())
    print(f"  pose en el paso del cruce (n={dp.size} con pose): QUIETA (<0.1 m y <0.3°) {quiet} | "
          f"|Δc| mediana {np.median(dp):.2f} m  p90 {np.percentile(dp, 90):.2f} | "
          f"|Δφ| mediana {np.degrees(np.median(dq)):.2f}°  p90 {np.degrees(np.percentile(dq, 90)):.2f}°")
print(f"  lobo al cruzar: walled {sum(c['walled'] for c in inw)} · scared {sum(c['scared'] for c in inw)} "
      f"· libre {sum(1 for c in inw if not c['walled'] and not c['scared'])}")
fl = [f for f in flanks if f["inward"] and not f["pen"]]
d_ext = np.array([f["d_ext"] for f in fl]) if fl else np.array([0.0])
print(f"\nRODEOS por los EXTREMOS (cruzan la RECTA fuera del tramo de drones, hacia dentro, línea en "
      f"pie): {len(fl)} | dist al dron extremo: mediana {np.median(d_ext):.1f}  p90 {np.percentile(d_ext, 90):.1f} m")
print(f"(comparar: {len(inw)} cruces de segmento vs {len(fl)} rodeos)")
