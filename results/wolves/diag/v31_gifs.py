"""v31_gifs.py — GIFs VERSIONADOS de v3.1 (requisito permanente; /data/gifs/v3.1/).
  nº3: cebo con barrera EN CONJUNTO (2 frentes: el cebo espera y dispara, la formación ENTERA va al
       ancla, el asalto entra libre) — candidato al GIF nº3 de la narrativa.
  nº2: barrera clásica vs lobos SIN cebo (episodio de 1 grupo) — candidato al GIF nº2.
  nº1: Dummy PASIVO vs lobos (drones sin hacer nada) — candidato al GIF nº1.
Se guardan aunque el cebo no rinda."""
import sys, os
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator, DummyCoordinator
from render import render_episode

OUT = "/data/gifs/v3.1"
os.makedirs(OUT, exist_ok=True)
MAX_FRAMES, TAIL = 800, 50


def episode_hist(seed, coord_cls):
    w = build_world(seed, "lobos")
    coord = coord_cls(w) if coord_cls is ReactiveCoordinator else coord_cls(w.n_drones)
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


# nº3: 2 frentes con cebo ejecutando (release disparado y muertes del asalto si las hay)
best2, best_score = None, (-1, -1)
for s in range(120):
    w = build_world(s, "lobos")
    c = ReactiveCoordinator(w); w.reset()
    if len(w.wolf_group_sizes) != 2:
        continue
    n1 = int(w.wolf_group_sizes[0])
    while True:
        _o, _r, t, tr, _i = w.step(c.act(w.get_observation()))
        if t or tr:
            break
    kills_s2 = sum(1 for cap in w.captures if cap["flankers"] and min(cap["flankers"]) >= n1)
    score = (kills_s2, int(w.n_depredadas))
    if w.wolf_decoy_released and score > best_score:
        best2, best_score = (s, f"{n1}+{w.n_wolves - n1}", int(w.n_depredadas), kills_s2), score
    if best_score >= (2, 2):
        break
print("nº3 elegido (2 frentes):", best2)

seed1 = None
for s in range(120):
    w = build_world(s, "lobos")
    w.reset()
    if len(w.wolf_group_sizes) == 1 and w.n_wolves >= 3:
        seed1 = s
        break
print("nº2 elegido (1 frente):", seed1)

jobs = [
    (best2[0], ReactiveCoordinator, f"n3_cebo_conjunto_2frentes_{best2[1].replace('+', 'mas')}"),
    (seed1, ReactiveCoordinator, "n2_barrera_clasica_1frente"),
    (seed1, DummyCoordinator, "n1_dummy_pasivo"),
]
for seed, cls, tag in jobs:
    w, hist = episode_hist(seed, cls)
    play = window(hist)
    out = f"{OUT}/v31_seed{seed}_{tag}.gif"
    print(f"  seed={seed} {tag}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
print("GIFS_V31_LISTOS")
