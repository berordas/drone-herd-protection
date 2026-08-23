"""v33_parte0.py — DIAGNÓSTICO de los 3 fallos persistentes con LAS MÉTRICAS DEL USUARIO (v3.2 HEAD).

M1 (avance): dist(centro de la formación de drones LIBRES -> vaca no-a-salvo MÁS PRÓXIMA al centro),
    por paso en ESCOLTA. Si la barrera avanza, CRECE mientras los lobos se aproximan. Se reporta la
    serie (resumen), % de pasos que crece (bruto y por ventanas de 3 s) y los correlatos que señalan
    la causa (aim/floor/d_ancla/penetrado/retroceso del centroide del rebaño).
M2 (cuelan): cruces GEOMÉTRICOS del segmento entre cada par de drones LIBRES contiguos (ordenados a
    lo largo de la línea) por el desplazamiento de un lobo entre pasos consecutivos. Contexto de cada
    cruce: anchura del hueco, estado del lobo (walled/scared), rama (CLEAN/PENETRADO), quién era.
M3 (roles): en episodios de 2 frentes, ¿qué SECTOR ancla la barrera (1º confirmado)? + dist del
    asalto a su presa al saltar ESCOLTA (la métrica de v3.2).
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import build_world


def seg_cross(p1, p2, a, b):
    """¿El segmento p1->p2 (lobo entre pasos) cruza el segmento a->b (par de drones)?"""
    d1 = p2 - p1
    d2 = b - a
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return False
    t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
    s = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
    return 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0


def run(seeds, kinds):
    m1_grow_raw, m1_grow_win, m1_series = [], [], []
    m1_ctx = dict(esc=0, pen=0, line=0)
    crosses = []
    m3 = []
    for kind in kinds:
        for s in seeds:
            w = build_world(s, kind)
            w.reset()
            coord = ReactiveCoordinator(w)
            two = len(w.wolf_group_sizes) == 2
            n1 = int(w.wolf_group_sizes[0]) if two else w.n_wolves
            prev_wolves = w.wolves.copy()
            d_series = []          # métrica 1 por paso
            approach = []          # ¿los lobos se acercaban a las vacas este paso?
            esc_done = False
            while True:
                a = coord.act(w.get_observation())
                _, _, term, trunc, _ = w.step(a)
                free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
                idx = np.where(free)[0]
                cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
                if w.phase == "ESCOLTA" and idx.size >= 2 and cows_ns.shape[0] > 0:
                    m1_ctx["esc"] += 1
                    center = w.drones[idx].mean(axis=0)
                    d = float(np.linalg.norm(cows_ns - center, axis=1).min())
                    # ¿aproximación de lobos? (dist mín lobo->vaca no-a-salvo cayendo)
                    dw = float(np.linalg.norm(w.wolves[:, None, :] - cows_ns[None, :, :], axis=2).min())
                    d_series.append(d); approach.append(dw)
                    # rama
                    herd = coord._live_herd()
                    in_pen = True
                    if coord._anchor is not None and herd.shape[0] > 0:
                        hc = herd.mean(axis=0)
                        hr = float(np.linalg.norm(herd - hc, axis=1).max()) if herd.shape[0] > 1 else 0.0
                        if float(np.linalg.norm(w.wolves[coord._anchor] - hc)) <= hr:
                            m1_ctx["pen"] += 1
                        else:
                            m1_ctx["line"] += 1
                            in_pen = False
                    # M2: cruces de segmentos entre drones contiguos
                    pts = w.drones[idx]
                    c = pts - pts.mean(axis=0)
                    if idx.size >= 2:
                        _u2, _s2, vt = np.linalg.svd(c)
                        order = np.argsort(pts @ vt[0])
                        pts_o = pts[order]
                        hc_now = cows_ns.mean(axis=0)
                        for j in range(w.n_wolves):
                            for k in range(idx.size - 1):
                                if seg_cross(prev_wolves[j], w.wolves[j], pts_o[k], pts_o[k + 1]):
                                    gap = float(np.linalg.norm(pts_o[k] - pts_o[k + 1]))
                                    inward = (np.linalg.norm(w.wolves[j] - hc_now)
                                              < np.linalg.norm(prev_wolves[j] - hc_now))
                                    crosses.append(dict(
                                        kind=kind, seed=s, step=int(w.step_count), gap=gap,
                                        inward=bool(inward), pen=in_pen,
                                        walled=bool(w._wolf_walled[j]), scared=bool(w._wolf_scared[j]),
                                        sector=("cebo" if j < n1 else "asalto") if two else "unico"))
                if two and not esc_done and w.phase == "ESCOLTA":
                    esc_done = True
                    p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                          else w.cows[w.cow_alive].mean(axis=0))
                    d_prey = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
                    anc = coord._anchor
                    m3.append(dict(seed=s, kind=kind,
                                   ancla=("cebo" if anc is not None and anc < n1 else "asalto"),
                                   d_prey=d_prey))
                prev_wolves = w.wolves.copy()
                if term or trunc:
                    break
            if len(d_series) > 40:
                ds = np.array(d_series)
                ap = np.array(approach)
                raw = np.diff(ds) > 0
                app_mask = np.diff(ap) < 0            # pasos en que los lobos SE ACERCAN
                m1_grow_raw.append(float(raw[app_mask].mean()) if app_mask.any() else np.nan)
                win = 30
                mw = [ds[i:i + win].mean() for i in range(0, len(ds) - win, win)]
                m1_grow_win.append(float(np.mean(np.diff(mw) > 0)) if len(mw) > 2 else np.nan)
                m1_series.append((kind, s, float(ds[:50].mean()), float(ds.mean()),
                                  float(ds.max()), float(ds[-50:].mean())))
    print("=== M1: dist(centro formación -> vaca no-a-salvo más próxima) ===")
    print(f"  pasos ESCOLTA {m1_ctx['esc']} | rama línea {m1_ctx['line']} | PENETRADO {m1_ctx['pen']}")
    print(f"  %% pasos que CRECE (bruto, solo mientras lobos se acercan): "
          f"{100 * np.nanmean(m1_grow_raw):.1f}%  | por ventanas de 3 s: {100 * np.nanmean(m1_grow_win):.1f}%")
    print("  episodio: d(inicio50) -> d(media) -> d(máx) -> d(final50):")
    for kind, s, a0, am, amx, af in m1_series[:14]:
        print(f"    {kind}/s{s}: {a0:.1f} -> {am:.1f} -> máx {amx:.1f} -> {af:.1f}")
    print("\n=== M2: cruces de segmento entre drones contiguos ===")
    print(f"  TOTAL cruces: {len(crosses)} en {len(seeds) * len(kinds)} episodios | "
          f"HACIA DENTRO: {sum(c['inward'] for c in crosses)} | con la LÍNEA en pie (rama CLEAN): "
          f"{sum(1 for c in crosses if not c['pen'])} (hacia dentro {sum(1 for c in crosses if not c['pen'] and c['inward'])})")
    from collections import Counter
    print(f"  por sector: {dict(Counter(c['sector'] for c in crosses))}")
    print(f"  estado del lobo al cruzar: walled={sum(c['walled'] for c in crosses)} "
          f"scared={sum(c['scared'] for c in crosses)} libre={sum(1 for c in crosses if not c['walled'] and not c['scared'])}")
    gaps = np.array([c["gap"] for c in crosses]) if crosses else np.array([0.0])
    print(f"  anchura del hueco cruzado: mediana {np.median(gaps):.1f} m  p90 {np.percentile(gaps, 90):.1f}  máx {gaps.max():.1f}")
    print("\n=== M3: ¿qué sector ANCLA la barrera? (2 frentes) ===")
    anc = Counter(r["ancla"] for r in m3)
    d3 = np.array([r["d_prey"] for r in m3]) if m3 else np.array([0.0])
    print(f"  n={len(m3)} | ancla: {dict(anc)}  (el DISEÑO pide cebo ~100%)")
    print(f"  d(asalto->presa) al saltar ESCOLTA: mediana {np.median(d3):.0f}  <=150: {100 * (d3 <= 150).mean():.0f}%")


if __name__ == "__main__":
    run(seeds=range(14), kinds=("lobos", "mixto"))
