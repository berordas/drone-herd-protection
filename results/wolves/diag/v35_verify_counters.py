"""v35_verify_counters.py — VERIFICACIÓN independiente del contador de v35_cruces_sweep.py.

Ejecuta las MISMAS 28 eps (seeds 0-13 x lobos/mixto) con ReactiveCoordinator(w, drone_spacing=S)
y corre EN PARALELO dos contadores:
  A) el contador EXACTO de v34/v35 (intersección del desplazamiento del lobo p1->p2 con el
     segmento de drones POSTERIOR al step);
  B) un detector por CAMBIO DE LADO EN MARCO MÓVIL: lado del lobo respecto a la recta de la
     línea ANTES del step (frame pre) vs DESPUÉS del step (frame post), con normal orientada
     hacia fuera del rebaño en ambos frames. Detecta atropellos (la línea avanza y deja al lobo
     dentro sin que el camino del lobo corte el segmento post-step).
Además mide la COBERTURA: cambios de lado ocurridos en pasos en los que el contador A no evalúa
(phase!=ESCOLTA, idx.size<2, cows_ns==0, set de drones cambia), y el desplazamiento de los
drones por paso (cota del túnel).
Uso: python3 v35_verify_counters.py <spacing>
"""
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


def line_frame(pts, hc):
    """centro, normal (orientada FUERA del rebaño), eje y proyecciones [lo,hi] del tramo."""
    c0 = pts.mean(axis=0)
    cc = pts - c0
    _u, _s, vt = np.linalg.svd(cc)
    axis, normal = vt[0], vt[1]
    if float(normal @ (c0 - hc)) < 0:
        normal = -normal
    pr = pts @ axis
    return c0, normal, axis, float(pr.min()), float(pr.max())


nA = 0            # contador exacto v35 (inward & ~pen)
nA_total = 0      # sin filtros
nB_strict = 0     # cambio de lado, ambos extremos dentro del tramo (inward & ~pen)
nB_loose = 0      # cambio de lado, algún extremo dentro del tramo (inward & ~pen)
nB_only = 0       # eventos B (strict) SIN evento A para ese lobo en ese paso
nB_skipped = 0    # cambios de lado (strict, inward) en pasos donde A NO evalúa
steps_eval = 0
steps_skip_line = 0   # pasos con >=2 drones libres pero A no evalúa
drone_disp = []
for kind in ("lobos", "mixto"):
    for seed in range(14):
        w = build_world(seed, kind)
        w.reset()
        c = ReactiveCoordinator(w, drone_spacing=SPACING)
        prev_wolves = w.wolves.copy()
        while True:
            a = c.act(w.get_observation())
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx = np.where(free)[0]
            pre_drones = w.drones.copy()
            pre_cows = w.cows[w.cow_alive & ~w.cow_safe]
            _o, _r, term, trunc, _i = w.step(a)
            cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
            evaluates = (w.phase == "ESCOLTA" and idx.size >= 2 and cows_ns.shape[0] > 0)
            have_line = idx.size >= 2 and cows_ns.shape[0] > 0 and pre_cows.shape[0] > 0
            if have_line:
                hc_now = cows_ns.mean(axis=0)
                hc_pre = pre_cows.mean(axis=0)
                c_pre, n_pre, ax_pre, lo_pre, hi_pre = line_frame(pre_drones[idx], hc_pre)
                c_post, n_post, ax_post, lo_post, hi_post = line_frame(w.drones[idx], hc_now)
                drone_disp.append(float(np.linalg.norm(w.drones[idx] - pre_drones[idx], axis=1).max()))
                # pen (idéntico a v35)
                herd = c._live_herd()
                in_pen = True
                if c._anchor is not None and herd.shape[0] > 0:
                    hcm = herd.mean(axis=0)
                    hr = float(np.linalg.norm(herd - hcm, axis=1).max()) if herd.shape[0] > 1 else 0.0
                    in_pen = float(np.linalg.norm(w.wolves[c._anchor] - hcm)) <= hr
                pts = w.drones[idx]
                cc2 = pts - pts.mean(axis=0)
                _u2, _s2, vt = np.linalg.svd(cc2)
                order = np.argsort(pts @ vt[0])
                pts_o = pts[order]
                for j in range(w.n_wolves):
                    p1, p2 = prev_wolves[j], w.wolves[j]
                    inward = np.linalg.norm(p2 - hc_now) < np.linalg.norm(p1 - hc_now)
                    # A: contador exacto v35
                    hitA = False
                    if evaluates:
                        for kk in range(idx.size - 1):
                            r = seg_cross_t(p1, p2, pts_o[kk], pts_o[kk + 1])
                            if r is None:
                                continue
                            hitA = True
                            nA_total += 1
                            if inward and not in_pen:
                                nA += 1
                    # B: cambio de lado en marco móvil
                    s1 = float((p1 - c_pre) @ n_pre)
                    s2 = float((p2 - c_post) @ n_post)
                    a1 = float(p1 @ ax_pre)
                    a2 = float(p2 @ ax_post)
                    in1 = lo_pre - 1e-9 <= a1 <= hi_pre + 1e-9
                    in2 = lo_post - 1e-9 <= a2 <= hi_post + 1e-9
                    if s1 > 0 >= s2:  # de fuera a dentro (normal apunta fuera)
                        if inward and not in_pen:
                            if in1 and in2:
                                nB_strict += 1
                                if not evaluates:
                                    nB_skipped += 1
                                elif not hitA:
                                    nB_only += 1
                            if in1 or in2:
                                nB_loose += 1
            if evaluates:
                steps_eval += 1
            elif have_line:
                steps_skip_line += 1
            prev_wolves = w.wolves.copy()
            if term or trunc:
                break

dd = np.array(drone_disp) if drone_disp else np.array([0.0])
out = dict(
    spacing=SPACING,
    A_inward_clean=nA,
    A_total=nA_total,
    B_strict_inward_clean=nB_strict,
    B_loose_inward_clean=nB_loose,
    B_strict_sin_A=nB_only,
    B_en_pasos_no_evaluados=nB_skipped,
    steps_eval=steps_eval,
    steps_con_linea_no_eval=steps_skip_line,
    drone_disp_por_paso_mediana=float(np.median(dd)),
    drone_disp_por_paso_p95=float(np.percentile(dd, 95)),
    drone_disp_por_paso_max=float(dd.max()),
)
print(json.dumps(out))
