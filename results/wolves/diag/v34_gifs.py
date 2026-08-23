"""v34_gifs.py — GIFs de v3.4 (LÍNEA RÍGIDA). Los que el usuario juzgará:
  nº1: la barrera avanzando como LÍNEA RÍGIDA hacia el cebo/ancla, sin deformarse
       (episodio con mayor avance real de la métrica M1; preferencia: ancla = cebo).
  nº2: episodio de 2 FRENTES con el cebo funcionando (ancla=cebo, asalto <=150 al saltar
       ESCOLTA, muertes del asalto) y la línea rígida — candidato al GIF nº3 de la narrativa.
"""
import sys, os
sys.path.insert(0, "/workspace")
import numpy as np
from world import ACTIVE
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode

OUT = "/data/gifs/v3.4"
os.makedirs(OUT, exist_ok=True)
MAX_FRAMES, TAIL = 800, 50


def episode_hist(seed):
    w = build_world(seed, "lobos")
    coord = ReactiveCoordinator(w)
    w.reset()
    hist = [{**w.snapshot(), "battery": w.battery.copy()}]
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        hist.append({**w.snapshot(), "battery": w.battery.copy()})
        if term or trunc:
            break
    return w, hist


def window(history):
    def key(s):
        return (s["phase"], s["n_depredadas"], s["n_safe"], int(np.sum(s.get("corzo_dismissed", []))))
    last = max((k for k in range(1, len(history)) if key(history[k]) != key(history[k - 1])), default=0)
    end = min(len(history), last + TAIL + 1)
    win = history[:end]
    stride = max(1, len(win) // MAX_FRAMES)
    return win[::stride]


def scan(seed):
    """Corre el episodio (sin render) y devuelve los indicadores de selección."""
    w = build_world(seed, "lobos")
    c = ReactiveCoordinator(w)
    w.reset()
    two = len(w.wolf_group_sizes) == 2
    n1 = int(w.wolf_group_sizes[0]) if two else w.n_wolves
    d0 = dN = None
    n_m1 = 0
    formed = 0
    clean = 0
    d_esc = None
    while True:
        a = c.act(w.get_observation())
        is_clean = (c._pose_last_step == w.step_count)
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        idx = np.where(free)[0]
        wp = a[idx].copy()
        _o, _r, term, trunc, _i = w.step(a)
        if d_esc is None and w.phase == "ESCOLTA" and two:
            p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                  else w.cows[w.cow_alive].mean(axis=0))
            d_esc = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
        cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
        if w.phase == "ESCOLTA" and idx.size >= 2 and cows_ns.shape[0] > 0:
            d = float(np.linalg.norm(cows_ns - w.drones[idx].mean(axis=0), axis=1).min())
            if d0 is None:
                d0 = d
            dN = d
            n_m1 += 1
        if is_clean and idx.size >= 2:
            clean += 1
            if float(np.linalg.norm(w.drones[idx] - wp, axis=1).max()) <= 2.0:
                formed += 1
        if term or trunc:
            break
    anc = c._anchor
    kills2 = sum(1 for cap in w.captures if cap["flankers"] and min(cap["flankers"]) >= n1) if two else 0
    return dict(seed=seed, two=two, n1=n1, d0=d0, dN=dN, n_m1=n_m1, formed=formed, clean=clean,
                anc_cebo=(two and anc is not None and anc < n1), d_esc=d_esc, kills2=kills2,
                sev=int(w.n_depredadas), grupos=f"{n1}+{w.n_wolves - n1}" if two else f"{w.n_wolves}")


rows = [scan(s) for s in range(120)]
# nº1: mayor avance real (dN - d0) con línea mayormente FORMADA; preferencia ancla=cebo
cand = [r for r in rows if r["d0"] is not None and r["n_m1"] > 400 and r["clean"] > 0
        and r["formed"] / r["clean"] > 0.5]
pref = [r for r in cand if r["anc_cebo"]] or cand
n1_row = max(pref, key=lambda r: r["dN"] - r["d0"])
print("nº1 (línea rígida que avanza):", {k: n1_row[k] for k in
      ("seed", "grupos", "d0", "dN", "formed", "clean", "anc_cebo", "sev")})

# nº2: 2 frentes, ancla=cebo, asalto <=150 al saltar ESCOLTA, muertes del asalto
cand2 = [r for r in rows if r["two"] and r["anc_cebo"] and r["d_esc"] is not None
         and r["d_esc"] <= 150.0 and r["kills2"] >= 1 and r["seed"] != n1_row["seed"]]
if not cand2:
    for s in range(120, 300):
        r = scan(s)
        if (r["two"] and r["anc_cebo"] and r["d_esc"] is not None and r["d_esc"] <= 150.0
                and r["kills2"] >= 2):
            cand2 = [r]
            break
n2_row = max(cand2, key=lambda r: (r["kills2"], -(r["d_esc"] or 1e9)))
print("nº2 (cebo + 2 frentes + línea rígida):", {k: n2_row[k] for k in
      ("seed", "grupos", "d_esc", "kills2", "anc_cebo", "sev")})

jobs = [
    (n1_row["seed"], f"n1_linea_rigida_avanza_{round(n1_row['d0'])}a{round(n1_row['dN'])}m"),
    (n2_row["seed"], f"n2_cebo_ancla_2frentes_asalto_a_{round(n2_row['d_esc'])}m_"
                     f"{n2_row['grupos'].replace('+', 'mas')}_linea_rigida"),
]
for seed, tag in jobs:
    w, hist = episode_hist(seed)
    play = window(hist)
    out = f"{OUT}/v34_seed{seed}_{tag}.gif"
    print(f"  seed={seed}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
print("GIFS_V34_LISTOS")
