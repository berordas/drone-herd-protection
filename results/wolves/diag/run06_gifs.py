"""run06_gifs.py — GIFs ilustrativos del diagnóstico (SOLO LECTURA, locales en /data).
Elige de run06_worldiag.json 2 semillas con episodios de 2 subgrupos bien separados y
renderiza gemelos (scriptado δ=0 vs mejor ckpt 4M) con la ventana relevante de main.py.
"""
import sys, json; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from render import render_episode
from rl.residual_wolf_controller import ResidualWolfController
from rl.policy_wolf_controller import SyncedReactiveCoordinator

BEST_4M = "/data/wolves/run06_curric/checkpoints/ppo_wolves_3999936_steps.zip"
MAX_FRAMES, TAIL = 800, 50

def episode(seed, kind, model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w); w.reset()
    hist = [{**w.snapshot(), "battery": w.battery.copy()}]
    while True:
        _o,_r,term,trunc,_i = w.step(coord.act(w.get_observation()))
        hist.append({**w.snapshot(), "battery": w.battery.copy()})
        if term or trunc: break
    return w, hist

def window(history):
    def key(s):
        return (s["phase"], s["n_depredadas"], s["n_safe"], int(np.sum(s.get("corzo_dismissed", []))))
    last = max((k for k in range(1, len(history)) if key(history[k]) != key(history[k-1])), default=0)
    end = min(len(history), last + TAIL + 1)
    win = history[:end]
    stride = max(1, len(win)//MAX_FRAMES)
    return win[::stride]

d = json.load(open("/data/wolves/diag/run06_worldiag.json"))
eps = sorted(d["scripted"], key=lambda e: -e["sep_media"])   # los de frentes más separados = más ilustrativos
seeds = [e["seed"] for e in eps[:2]]
print("semillas elegidas (mayor separación de frentes):", seeds)

from stable_baselines3 import PPO
m4 = PPO.load(BEST_4M, device="cpu")
for seed in seeds:
    for label, mdl in (("scripted", None), ("best4M", m4)):
        w, hist = episode(seed, "lobos", mdl)
        play = window(hist)
        out = f"/data/wolves/diag/worldiag_seed{seed}_{label}.gif"
        print(f"  seed={seed} {label}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} frames={len(play)} -> {out}", flush=True)
        render_episode(w, play, save_path=out)
print("GIFS_LISTOS")
