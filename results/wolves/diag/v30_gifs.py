"""v30_gifs.py — GIFs VERSIONADOS de v3.0 (requisito permanente; se guardan en /data/gifs/v3.0/).
1) 2 frentes con el CEBO PERFECTO ejecutándose (cebo espera -> asalto llega -> barrera atiende ->
   asalto mata libre) — candidato al GIF nº2 de la narrativa (lobos usando el cebo).
2) 1 frente scriptado (sin cebo) — candidato al GIF nº1 (lobos sin cebo).
Se guardan AUNQUE el cebo no rinda (no descartar). Elige el episodio de 2 frentes del JSON del
medidor decoy (mayor ancla_cebo, luego kills_s2)."""
import sys, json, os
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode

OUT = "/data/gifs/v3.0"
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


d = json.load(open("/data/wolves/diag/v30_decoy_size.json"))
import baseline
decoy = baseline.CONFIG_V2["wolf_decoy_size"]
rows = d[f"decoy_{decoy}"]["episodios"]
best2 = sorted(rows, key=lambda r: (-r["ancla_cebo"], -r["kills_s2"], -r["ventana"]))[0]
print("episodio 2 frentes elegido:", {k: best2[k] for k in ("seed", "reparto", "sev", "ancla_cebo", "ventana", "kills_s2")})

seed1 = None
for s in range(100):
    w = build_world(s, "lobos"); w.reset()
    if len(w.wolf_group_sizes) == 1 and w.n_wolves >= 3:
        seed1 = s
        break
print("episodio 1 frente elegido: seed", seed1)

for seed, tag in ((best2["seed"], f"cebo_perfecto_2frentes_{best2['reparto'].replace('+', 'mas')}"),
                  (seed1, "sin_cebo_1frente")):
    w, hist = episode_hist(seed)
    play = window(hist)
    out = f"{OUT}/v30_seed{seed}_{tag}.gif"
    print(f"  seed={seed} {tag}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
          f"frames={len(play)} -> {out}", flush=True)
    render_episode(w, play, save_path=out)
print("GIFS_V30_LISTOS")
