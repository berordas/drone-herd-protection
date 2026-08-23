"""v34_rigidez.py — MÉTRICAS DE RIGIDEZ de la línea v3.4 (métricas del usuario) + coste del cierre.

Sobre las MISMAS 14 semillas x 2 tipos que v33_parte0 (el ANTES con cierres, v34_antes_cierres.txt):
  RIGIDEZ (solo rama CLEAN de la barrera):
    - error de ESTACIÓN: dist dron -> su waypoint rígido, por paso. Máx y p95, separando el
      TRANSITORIO de formación/incorporación (vuelo de llegada, físicamente inevitable: la pose
      espera QUIETA) del estado FORMADA (err_max<=2 m alcanzado y sin cambio del conjunto de
      drones libres) — la rigidez se afirma sobre la línea FORMADA en movimiento.
    - ESPACIADO real entre drones contiguos (proyección sobre el frente de la pose): distribución
      vs el nominal (spacing=20).
    - COLINEALIDAD: residuo rms del ajuste de los drones libres a una recta (SVD), por paso.
    - velocidad de la POSE (informativa: el gobernador del más rezagado en acción).
  M2 (coste de ELIMINAR el cierre local): cruces geométricos de segmentos entre drones contiguos
      (mismo contador que v33_parte0) — comparar con el ANTES.
  M1 (no romper lo validado): % de pasos en que dist(centro formación -> vaca no-a-salvo más
      próxima) CRECE mientras los lobos se acercan + series por episodio.
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE
from coordinators import ReactiveCoordinator
from baseline import build_world

FORMED_ERR = 2.0      # m: umbral de "línea FORMADA" (≈ err de equilibrio del gobernador ~1.2 m + margen)


def seg_cross(p1, p2, a, b):
    d1 = p2 - p1
    d2 = b - a
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return False
    t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
    s = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
    return 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0


def run(seeds, kinds):
    err_all, err_formed = [], []          # error de estación por dron-paso
    errmax_formed = []                    # err MÁX del paso (el rezagado) en formada
    gaps_formed = []                      # espaciados contiguos en formada
    colin_all, colin_formed = [], []      # residuo rms de recta
    pose_speed = []                       # |Δpose_c|/dt
    n_clean = n_formed = n_pen = 0
    m1_grow_raw, m1_grow_win, m1_series = [], [], []
    crosses = []
    for kind in kinds:
        for s in seeds:
            w = build_world(s, kind)
            w.reset()
            coord = ReactiveCoordinator(w)
            two = len(w.wolf_group_sizes) == 2
            n1 = int(w.wolf_group_sizes[0]) if two else w.n_wolves
            prev_wolves = w.wolves.copy()
            prev_pose = None
            prev_ids = None
            formed = False
            d_series, approach = [], []
            while True:
                a = coord.act(w.get_observation())
                clean = (coord._pose_last_step == w.step_count)   # la rama CLEAN corrió este paso
                free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
                idx = np.where(free)[0]
                wp = a[idx].copy()
                _, _, term, trunc, _ = w.step(a)
                free2 = (w.drone_state == ACTIVE) & (~w.drone_investigating)
                idx2 = np.where(free2)[0]
                same_set = idx.size == idx2.size and np.array_equal(idx, idx2)
                cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
                if clean and same_set and idx.size >= 2:
                    n_clean += 1
                    pts = w.drones[idx]
                    errs = np.linalg.norm(pts - wp, axis=1)
                    emax = float(errs.max())
                    # estado FORMADA: err_max<=umbral alcanzado; se pierde si cambia el conjunto
                    ids_now = tuple(idx.tolist())
                    if prev_ids != ids_now:
                        formed = False
                    if emax <= FORMED_ERR:
                        formed = True
                    prev_ids = ids_now
                    err_all.extend(errs.tolist())
                    c = pts - pts.mean(axis=0)
                    _u_, sv, vt = np.linalg.svd(c, full_matrices=False)
                    resid = float(np.sqrt((sv[1] ** 2) / idx.size)) if idx.size > 1 else 0.0
                    colin_all.append(resid)
                    if formed:
                        n_formed += 1
                        err_formed.extend(errs.tolist())
                        errmax_formed.append(emax)
                        colin_formed.append(resid)
                        pu = coord._pose_u
                        perp = np.array([-pu[1], pu[0]])
                        proj = np.sort(pts @ perp)
                        gaps_formed.extend(np.diff(proj).tolist())
                        if prev_pose is not None:
                            pose_speed.append(float(np.linalg.norm(coord._pose_c - prev_pose)) / w.dt)
                    prev_pose = coord._pose_c.copy() if coord._pose_c is not None else None
                else:
                    prev_pose = None
                    formed = False
                    prev_ids = None
                # ---- M1 + M2 (mismo criterio que v33_parte0: pasos de ESCOLTA con >=2 libres) ----
                if w.phase == "ESCOLTA" and idx.size >= 2 and cows_ns.shape[0] > 0:
                    center = w.drones[idx].mean(axis=0)
                    d = float(np.linalg.norm(cows_ns - center, axis=1).min())
                    dw = float(np.linalg.norm(w.wolves[:, None, :] - cows_ns[None, :, :], axis=2).min())
                    d_series.append(d)
                    approach.append(dw)
                    herd = coord._live_herd()
                    in_pen = True
                    if coord._anchor is not None and herd.shape[0] > 0:
                        hc = herd.mean(axis=0)
                        hr = float(np.linalg.norm(herd - hc, axis=1).max()) if herd.shape[0] > 1 else 0.0
                        in_pen = float(np.linalg.norm(w.wolves[coord._anchor] - hc)) <= hr
                    if in_pen:
                        n_pen += 1
                    pts = w.drones[idx]
                    cc = pts - pts.mean(axis=0)
                    _u2, _s2, vt = np.linalg.svd(cc)
                    order = np.argsort(pts @ vt[0])
                    pts_o = pts[order]
                    hc_now = cows_ns.mean(axis=0)
                    for j in range(w.n_wolves):
                        for kk in range(idx.size - 1):
                            if seg_cross(prev_wolves[j], w.wolves[j], pts_o[kk], pts_o[kk + 1]):
                                gap = float(np.linalg.norm(pts_o[kk] - pts_o[kk + 1]))
                                inward = (np.linalg.norm(w.wolves[j] - hc_now)
                                          < np.linalg.norm(prev_wolves[j] - hc_now))
                                crosses.append(dict(
                                    kind=kind, seed=s, gap=gap, inward=bool(inward), pen=in_pen,
                                    walled=bool(w._wolf_walled[j]), scared=bool(w._wolf_scared[j]),
                                    sector=("cebo" if j < n1 else "asalto") if two else "unico"))
                prev_wolves = w.wolves.copy()
                if term or trunc:
                    break
            if len(d_series) > 40:
                ds = np.array(d_series)
                ap = np.array(approach)
                raw = np.diff(ds) > 0
                app_mask = np.diff(ap) < 0
                m1_grow_raw.append(float(raw[app_mask].mean()) if app_mask.any() else np.nan)
                win = 30
                mw = [ds[i:i + win].mean() for i in range(0, len(ds) - win, win)]
                m1_grow_win.append(float(np.mean(np.diff(mw) > 0)) if len(mw) > 2 else np.nan)
                m1_series.append((kind, s, float(ds[:50].mean()), float(ds.mean()),
                                  float(ds.max()), float(ds[-50:].mean())))

    ea, ef = np.array(err_all), np.array(err_formed)
    emf = np.array(errmax_formed) if errmax_formed else np.array([0.0])
    gf = np.array(gaps_formed) if gaps_formed else np.array([0.0])
    ca = np.array(colin_all) if colin_all else np.array([0.0])
    cf = np.array(colin_formed) if colin_formed else np.array([0.0])
    ps = np.array(pose_speed) if pose_speed else np.array([0.0])
    print("=== RIGIDEZ (rama CLEAN) ===")
    print(f"  pasos CLEAN {n_clean} | FORMADA (err_max<={FORMED_ERR} alcanzado, mismo conjunto) "
          f"{n_formed} ({100 * n_formed / max(n_clean, 1):.0f}%) | pasos PENETRADO {n_pen}")
    print(f"  error de ESTACIÓN por dron-paso — TODO CLEAN (incluye vuelo de llegada): "
          f"p50 {np.percentile(ea, 50):.2f}  p95 {np.percentile(ea, 95):.1f}  máx {ea.max():.1f}")
    print(f"                                  — FORMADA: p50 {np.percentile(ef, 50):.2f}  "
          f"p95 {np.percentile(ef, 95):.2f}  máx {ef.max():.2f}")
    print(f"  err_MÁX del paso (el rezagado) en FORMADA: p50 {np.percentile(emf, 50):.2f}  "
          f"p95 {np.percentile(emf, 95):.2f}  máx {emf.max():.2f}")
    print(f"  ESPACIADO contiguo en FORMADA (nominal {20.0}): mín {gf.min():.1f}  p5 "
          f"{np.percentile(gf, 5):.1f}  p50 {np.percentile(gf, 50):.1f}  p95 {np.percentile(gf, 95):.1f}  máx {gf.max():.1f}")
    print(f"  COLINEALIDAD (residuo rms de recta): TODO CLEAN p95 {np.percentile(ca, 95):.2f} máx {ca.max():.1f}"
          f" | FORMADA p95 {np.percentile(cf, 95):.2f} máx {cf.max():.2f}")
    print(f"  velocidad de la POSE en FORMADA: p50 {np.percentile(ps, 50):.2f}  p95 "
          f"{np.percentile(ps, 95):.2f}  máx {ps.max():.2f} m/s (equilibrio analítico ~3.1)")
    print("\n=== M2: cruces de segmento (COSTE de eliminar el cierre; ANTES=v3.3 con cierres: "
          "56 total, 33 hacia-dentro-línea-en-pie) ===")
    print(f"  TOTAL: {len(crosses)} en {len(list(seeds)) * len(kinds)} episodios | "
          f"HACIA DENTRO: {sum(c['inward'] for c in crosses)} | línea en pie (CLEAN): "
          f"{sum(1 for c in crosses if not c['pen'])} (hacia dentro "
          f"{sum(1 for c in crosses if not c['pen'] and c['inward'])})")
    from collections import Counter
    print(f"  por sector: {dict(Counter(c['sector'] for c in crosses))}")
    print(f"  estado del lobo: walled={sum(c['walled'] for c in crosses)} "
          f"scared={sum(c['scared'] for c in crosses)} "
          f"libre={sum(1 for c in crosses if not c['walled'] and not c['scared'])}")
    gaps = np.array([c["gap"] for c in crosses]) if crosses else np.array([0.0])
    print(f"  hueco cruzado: mediana {np.median(gaps):.1f}  p90 {np.percentile(gaps, 90):.1f}  máx {gaps.max():.1f}")
    print("\n=== M1 (validada en v3.3 — no debe romperse) ===")
    print(f"  % pasos que CRECE (lobos acercándose): {100 * np.nanmean(m1_grow_raw):.1f}% | "
          f"ventanas 3 s: {100 * np.nanmean(m1_grow_win):.1f}%")
    for kind, s, a0, am, amx, af in m1_series[:14]:
        print(f"    {kind}/s{s}: {a0:.1f} -> {am:.1f} -> máx {amx:.1f} -> {af:.1f}")


if __name__ == "__main__":
    run(seeds=range(14), kinds=("lobos", "mixto"))
