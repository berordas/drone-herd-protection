"""v35_gifs.py — GIFs de EVIDENCIA v3.5 (paredes solapadas; NO es un congelado — el espaciado se
pasa por CLI y no toca el repo). Modos:
  cross <spacing>: episodio real donde un lobo CRUZA el corredor central pese al solape
                   (ventana alrededor del cruce) — refuta en GIF que ese solape selle.
  hold <spacing>:  episodio real con la PRESIÓN sostenida más larga en un segmento interior
                   SIN cruce en todo el episodio (el frenado hacia afuera funcionando).
  flank <spacing>: episodio con rodeo por los EXTREMOS (el precio de la línea estrecha).
Uso: python3 v35_gifs.py <cross|hold|flank> <spacing>
"""
import sys, os
sys.path.insert(0, "/workspace")
import numpy as np
from world import ACTIVE
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode

MODE, SPACING = sys.argv[1], float(sys.argv[2])
OUT = "/data/gifs/v3.5"
os.makedirs(OUT, exist_ok=True)
MAX_FRAMES, TAIL = 800, 50


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


def scan(seed, kind="lobos"):
    """Episodio real con espaciado SPACING: cruces hacia-dentro CLEAN (paso, lobo), rodeos por
    extremos (paso), presiones sostenidas en corredor interior (lobo, t0, t1, dmin)."""
    w = build_world(seed, kind)
    w.reset()
    c = ReactiveCoordinator(w, drone_spacing=SPACING)
    prev_wolves = w.wolves.copy()
    crosses, flanks, runs = [], [], {}
    open_run = {}
    while True:
        a = c.act(w.get_observation())
        clean = (c._pose_last_step == w.step_count)
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        idx = np.where(free)[0]
        _o, _r, term, trunc, _i = w.step(a)
        cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
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
                    if seg_cross_t(p1, p2, pts_o[kk], pts_o[kk + 1]) is not None:
                        hit = True
                        if inward and not in_pen:
                            crosses.append((int(w.step_count), j))
                if not hit and inward and not in_pen:
                    s1 = float((p1 - pts_o[0]) @ normal)
                    s2n = float((p2 - pts_o[0]) @ normal)
                    if s1 * s2n < 0:
                        lam = s1 / (s1 - s2n)
                        px = p1 + lam * (p2 - p1)
                        ax = float(px @ axis)
                        if ax < lo - 1e-9 or ax > hi + 1e-9:
                            flanks.append((int(w.step_count), j))
                # presión sostenida en tramo interior (para 'hold')
                if clean and idx.size >= 3:
                    p = w.wolves[j]
                    d_line = abs(float((p - pts_o[0]) @ normal))
                    ax = float(p @ axis)
                    lo_i, hi_i = float(pts_o[1] @ axis), float(pts_o[-2] @ axis)
                    inside = min(lo_i, hi_i) - 1.0 <= ax <= max(lo_i, hi_i) + 1.0
                    if w._wolf_walled[j] and d_line <= 12.0 and inside:
                        t0, dmin = open_run.get(j, (int(w.step_count), d_line))
                        open_run[j] = (t0, min(dmin, d_line))
                    elif j in open_run:
                        t0, dmin = open_run.pop(j)
                        runs.setdefault(j, []).append((t0, int(w.step_count), dmin))
        prev_wolves = w.wolves.copy()
        if term or trunc:
            break
    for j in list(open_run):
        t0, dmin = open_run.pop(j)
        runs.setdefault(j, []).append((t0, int(w.step_count), dmin))
    best = (0, None)
    for j, rs in runs.items():
        for t0, t1, dmin in rs:
            if t1 - t0 > best[0]:
                best = (t1 - t0, (j, t0, t1, dmin))
    return dict(seed=seed, crosses=crosses, flanks=flanks, best=best,
                sev=int(w.n_depredadas), steps=int(w.step_count))


def render_window(seed, tag, t_from, t_to, kind="lobos"):
    w = build_world(seed, kind)
    coord = ReactiveCoordinator(w, drone_spacing=SPACING)
    w.reset()
    hist = [{**w.snapshot(), "battery": w.battery.copy()}]
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        hist.append({**w.snapshot(), "battery": w.battery.copy()})
        if term or trunc:
            break
    lo = max(0, t_from - 100)
    hi = min(len(hist), t_to + TAIL)
    win = hist[lo:hi]
    stride = max(1, len(win) // MAX_FRAMES)
    play = win[::stride]
    out = f"{OUT}/v35_seed{seed}_{tag}.gif"
    print(f"  seed={seed}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"ventana=[{lo},{hi}) frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)


if __name__ == "__main__":
    rows = [scan(s) for s in range(28)]
    stag = ("s%.1f" % SPACING).replace(".0", "").replace(".", "p")
    if MODE == "cross":
        cand = [r for r in rows if r["crosses"]]
        assert cand, "ningún cruce con ese espaciado en seeds 0-27"
        r = max(cand, key=lambda r: len(r["crosses"]))
        t_cr, j = r["crosses"][0]
        print("cross:", dict(seed=r["seed"], lobo=j, paso=t_cr, cruces_ep=len(r["crosses"]), sev=r["sev"]))
        render_window(r["seed"], f"n1_solape_{stag}_lobo_cruza_el_corredor_igual", t_cr, t_cr + 40)
    elif MODE == "hold":
        cand = [r for r in rows if not r["crosses"] and r["best"][1] is not None and r["best"][0] >= 80]
        assert cand, "ninguna presión sostenida sin cruce en seeds 0-27"
        r = max(cand, key=lambda r: r["best"][0])
        j, t0, t1, dmin = r["best"][1]
        print("hold:", dict(seed=r["seed"], lobo=j, pasos=(t0, t1), dur=t1 - t0,
                            dmin=round(dmin, 1), sev=r["sev"]))
        render_window(r["seed"], f"n2_solape_{stag}_presion_corredor_{t1 - t0}pasos_no_cruza", t0, t1)
    elif MODE == "flank":
        cand = [r for r in rows if r["flanks"]]
        assert cand, "ningún rodeo por extremos en seeds 0-27"
        r = max(cand, key=lambda r: len(r["flanks"]))
        t_fl, j = r["flanks"][0]
        print("flank:", dict(seed=r["seed"], lobo=j, paso=t_fl, rodeos_ep=len(r["flanks"]), sev=r["sev"]))
        render_window(r["seed"], f"n3_solape_{stag}_rodeo_por_el_flanco_linea_estrecha", t_fl, t_fl + 60)
    print("GIF_V35_OK")
