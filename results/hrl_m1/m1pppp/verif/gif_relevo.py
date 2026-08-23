"""gif_relevo.py — GIF de referencia del RELEVO DE CENTINELA v3.7 (episodio corzos, patrulla en
régimen): el bajo ANUNCIA y se CLAVA, el fresco vuela DIRECTO al puesto, traspaso, el saliente
vuelve a cargar — y NINGÚN otro ACTIVE se mueve."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode
from world import ACTIVE, CHARGING, READY, RETURNING

w = build_world(1, "corzos")
coord = ReactiveCoordinator(w)
w.reset()
for _ in range(700):
    w.step(coord.act(w.get_observation()))
res = np.where((w.drone_state == CHARGING) | (w.drone_state == READY))[0]
w.battery[res] = 1.0
w.step(coord.act(w.get_observation()))
low = int(np.where(w.drone_state == ACTIVE)[0][0])
w.battery[low] = w.announce_threshold - 0.01
hist = []
end = None
for t in range(2500):
    w.step(coord.act(w.get_observation()))
    hist.append({**w.snapshot(), "battery": w.battery.copy(), "confirmed_mask": None})
    if end is None and w.drone_state[low] == CHARGING:
        end = t + 60
    if end is not None and t >= end:
        break
frames = hist[::max(1, len(hist) // 500)]
out = pathlib.Path("/data/hrl_m1/m1pppp/visionado/gifs/relevo_centinela_corzos_s1.gif")
render_episode(w, frames, save_path=str(out))
print("RELEVO_GIF_OK", out, "frames", len(frames))
