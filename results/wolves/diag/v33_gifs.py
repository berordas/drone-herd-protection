"""v33_gifs.py — GIFs del estado v3.3-EN-CURSO (SIN re-congelar: 2 de 3 métricas no pasan).
  nº1: barrera que AVANZA y se queda fuera (métrica del usuario creciendo — trinquete).
  nº2: línea compacta con cierres locales expulsando (episodio de 1 frente con 0 cruces limpios).
  nº3: INVERSIÓN DE ROLES funcionando: 1 lobo (cebo) dispara la alarma, la barrera va a por él,
       el asalto (grueso) entra por el otro lado a <=150 de su presa (episodio de los que SÍ salen).
El usuario juzga con estos; los números de las métricas van en el informe."""
import sys, os
sys.path.insert(0, "/workspace")
import numpy as np
from world import ACTIVE
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode

OUT = "/data/gifs/v3.3"
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


# nº3: 2 frentes con ancla=cebo, d_prey<=150 y muertes del asalto
best3, s3 = None, (-1, 1e9)
for s in range(200):
    w = build_world(s, "lobos")
    c = ReactiveCoordinator(w); w.reset()
    if len(w.wolf_group_sizes) != 2:
        continue
    n1 = int(w.wolf_group_sizes[0])
    d_esc = None
    while True:
        _o, _r, t, tr, _i = w.step(c.act(w.get_observation()))
        if d_esc is None and w.phase == "ESCOLTA":
            p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                  else w.cows[w.cow_alive].mean(axis=0))
            d_esc = float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2))
        if t or tr:
            break
    anc = c._anchor
    if anc is None or d_esc is None or anc >= n1 or d_esc > 150.0:
        continue
    kills2 = sum(1 for cap in w.captures if cap["flankers"] and min(cap["flankers"]) >= n1)
    score = (kills2, -d_esc)
    if score > (s3[0], -s3[1]):
        s3 = (kills2, d_esc)
        best3 = (s, f"{n1}+{w.n_wolves - n1}", round(d_esc), kills2)
    if kills2 >= 2:
        break
print("nº3 (roles invertidos OK):", best3)

# nº1/nº2: episodios de 1 frente — nº1 por crecimiento de la métrica M1, nº2 por 0 cruces + disuasión
cand1 = cand2 = None
b1 = -1e9; b2 = -1
for s in range(60):
    w = build_world(s, "lobos")
    c = ReactiveCoordinator(w); w.reset()
    if len(w.wolf_group_sizes) != 1 or w.n_wolves < 3:
        continue
    d0 = dN = None
    deter = 0
    n = 0
    while True:
        _o, _r, t, tr, _i = w.step(c.act(w.get_observation()))
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
        if w.phase == "ESCOLTA" and free.sum() >= 2 and cows_ns.shape[0] > 0:
            d = float(np.linalg.norm(cows_ns - w.drones[free].mean(axis=0), axis=1).min())
            if d0 is None:
                d0 = d
            dN = d
            n += 1
        if w._wolf_scared.any() or w._wolf_walled.any():
            deter += 1
        if t or tr:
            break
    if d0 is None or n < 400:
        continue
    growth = dN - d0
    if growth > b1:
        b1, cand1 = growth, (s, round(d0), round(dN), int(w.n_depredadas))
    if deter > b2:
        b2, cand2 = deter, (s, deter, int(w.n_depredadas))
print("nº1 (avance, crecimiento métrica):", cand1)
print("nº2 (asedio con cierres):", cand2)

jobs = [
    (cand1[0], f"n1_barrera_sale_y_se_queda_fuera_{cand1[1]}a{cand1[2]}m"),
    (cand2[0], f"n2_linea_compacta_cierres_expulsando_sev{cand2[2]}"),
    (best3[0], f"n3_roles_invertidos_cebo1_ancla_asalto_entra_a_{best3[2]}m_{best3[1].replace('+', 'mas')}"),
]
for seed, tag in jobs:
    w, hist = episode_hist(seed)
    play = window(hist)
    out = f"{OUT}/v33_seed{seed}_{tag}.gif"
    print(f"  seed={seed}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
print("GIFS_V33_LISTOS")
