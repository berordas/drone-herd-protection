"""v32_gifs.py — GIFs VERSIONADOS de v3.2 (requisito permanente; /data/gifs/v3.2/).
Uno por SÍNTOMA arreglado (el criterio de aceptación es el GIF, no el test):
  nº1: barrera COMPACTA sin huecos — lobos intentando cruzar la línea y siendo espantados/amurallados
       (elegido por máx. eventos de disuasión en episodios de 1 frente).
  nº2: barrera que AVANZA — la formación va claramente hacia los lobos, acotada al anillo de 50 m
       del centroide de collares (elegido por máx. fracción de pasos con persecución real).
  nº3: cebo con TIMING correcto — ESCOLTA salta con el asalto a <=150 m de su presa (elegido entre
       los episodios de 2 frentes que cumplen la vara, con muertes del asalto si las hay).
Además: v32_frame_emojis.png (frame real con EMOJI_SCALE=0.20, arreglo 4).
El "antes" de cada síntoma es el GIF correspondiente de /data/gifs/v3.1/."""
import sys, os
sys.path.insert(0, "/workspace")
import numpy as np
from PIL import Image
from world import ACTIVE
from baseline import build_world
from coordinators import ReactiveCoordinator, DummyCoordinator
from render import render_episode

OUT = "/data/gifs/v3.2"
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


# --- selección: recorre episodios de 1 y 2 frentes midiendo los síntomas ---
best1 = best2 = best3 = None            # (seed, score, extra)
s1_score = s2_score = -1.0
s3_score = (-1, -1.0)
for s in range(120):
    w = build_world(s, "lobos")
    c = ReactiveCoordinator(w); w.reset()
    two = len(w.wolf_group_sizes) == 2
    n1 = int(w.wolf_group_sizes[0]) if two else w.n_wolves
    deter_steps = 0
    pursuit = 0
    esc_steps = 0
    d_esc = None
    prev = w.drones.copy()
    while True:
        _o, _r, t, tr, _i = w.step(c.act(w.get_observation()))
        if w._wolf_scared.any() or w._wolf_walled.any():
            deter_steps += 1
        if w.phase == "ESCOLTA":
            esc_steps += 1
            conf = c._confirmed
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            if conf is not None and conf.any() and free.any():
                wc = w.wolves[conf]
                d0 = np.linalg.norm(prev[free][:, None, :] - wc[None, :, :], axis=2)
                d1 = np.linalg.norm(w.drones[free][:, None, :] - wc[None, :, :], axis=2)
                if ((d0 - d1) / w.dt > 1.0).any():
                    pursuit += 1
            if two and d_esc is None:
                p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                      else w.cows[w.cow_alive].mean(axis=0))
                d_esc = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
        prev = w.drones.copy()
        if t or tr:
            break
    if not two and w.n_wolves >= 3:
        if deter_steps > s1_score:
            s1_score, best1 = deter_steps, (s, deter_steps, int(w.n_depredadas))
        frac = pursuit / max(esc_steps, 1)
        if esc_steps > 400 and frac > s2_score:
            s2_score, best2 = frac, (s, round(100 * frac), int(w.n_depredadas))
    if two and d_esc is not None and d_esc <= 150.0 and w.wolf_decoy_released:
        kills_s2 = sum(1 for cap in w.captures if cap["flankers"] and min(cap["flankers"]) >= n1)
        score = (kills_s2, -d_esc)
        if score > s3_score:
            s3_score, best3 = score, (s, f"{n1}+{w.n_wolves - n1}", round(d_esc), kills_s2)

print("nº1 (sin huecos, máx disuasión):", best1)
print("nº2 (avanza, máx persecución):", best2)
print("nº3 (timing <=150):", best3)

jobs = [
    (best1[0], f"n1_sin_huecos_paredes_que_tocan_sev{best1[2]}"),
    (best2[0], f"n2_barrera_que_avanza_persecucion{best2[1]}pct"),
    (best3[0], f"n3_timing_escolta_con_asalto_a_{best3[2]}m_{best3[1].replace('+', 'mas')}"),
]
seen = set()
for seed, tag in jobs:
    w, hist = episode_hist(seed, ReactiveCoordinator)
    play = window(hist)
    out = f"{OUT}/v32_seed{seed}_{tag}.gif"
    print(f"  seed={seed} {tag}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
    seen.add(out)

# frame real para el arreglo 4 (emojis 0.20): frame central del GIF nº1
src = f"{OUT}/v32_seed{best1[0]}_n1_sin_huecos_paredes_que_tocan_sev{best1[2]}.gif"
im = Image.open(src)
im.seek(im.n_frames // 2)
im.convert("RGB").save(f"{OUT}/v32_frame_emojis.png")
print("frame de emojis ->", f"{OUT}/v32_frame_emojis.png")
print("GIFS_V32_LISTOS")
