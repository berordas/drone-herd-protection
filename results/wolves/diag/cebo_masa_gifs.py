"""cebo_masa_gifs.py — SOLO LECTURA (desechable): 4-6 GIFs ilustrativos del diagnóstico de
reparto de masa, etiquetados por reparto (cebo n1 + asalto n2) y desenlace del cebo.
Elige de cebo_masa_diag.json: por cada reparto canónico, el episodio más informativo
(prioriza: cundió el cebo > asalto que llega sin matar > el primero)."""
import sys, json
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode

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


d = json.load(open("/data/wolves/diag/cebo_masa_diag.json"))
rows = d["episodios"]


# Representantes elegidos A MANO tras el cruce (cubren los 4 repartos + los 2 casos que matizan):
PICKS = [
    (100, "cunde_ancla_cebo"),           # 1+4: el cebo de 1 ANCLA la barrera y el asalto mata 5 en serie
    (91, "cunde_ancla_asalto"),          # 1+4: el ancla cae EN el asalto... y la masa bate a la línea igual
    (88, "cunde_ambos_cuorum"),          # 2+3: cebo de 2 ancla (y puede matar) + asalto de 3 con cuórum; sev 5
    (284, "cunde_asalto_justo"),         # 3+2: asalto de 2 = cuórum justo; cunde con lo mínimo
    (42, "fracasa_ventana_desperdiciada"),  # 4+1: ventana libre 70% que el asalto de 1 no puede usar (sin cuórum por regla)
    (336, "excepcion_cebo_gordo_rompe"), # 4+1: sev 5 — el CEBO de 4 rompe la línea él solo (la masa gana esté donde esté)
]
by_seed = {r["seed"]: r for r in rows}
picks = [by_seed[s] for s, _ in PICKS]
tags = dict(PICKS)

for r in picks:
    seed, rep = r["seed"], r["reparto"]
    tag = tags[seed]
    w, hist = episode_hist(seed)
    assert int(w.n_depredadas) == r["sev"], f"seed {seed}: sev {w.n_depredadas} != {r['sev']} (no reproducido)"
    out = f"/data/wolves/diag/cebo_masa_seed{seed}_cebo{rep.split('+')[0]}_asalto{rep.split('+')[1]}_{tag}.gif"
    play = window(hist)
    print(f"  seed={seed} reparto={rep} sev={r['sev']} {tag} frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
print("GIFS_LISTOS")
