"""run07_gifs.py — GIFs gemelos del desenlace de run07 (SOLO LECTURA, locales en /data).
Elige de run07_cebo_final_20M.json 2 semillas 'lobos' de 2 subgrupos con la VENTANA EXPLOTABLE
más larga (fracción de pasos de ESCOLTA con un solo grupo CONFIRMADO) y renderiza el mismo
episodio con: scriptado δ=0 | mejor ckpt (7.5M) | FINAL (20M, erosionado).
"""
import sys, json; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from render import render_episode
from rl.residual_wolf_controller import ResidualWolfController
from rl.policy_wolf_controller import SyncedReactiveCoordinator

BEST = "/data/wolves/run07_curric_v28/checkpoints/ppo_wolves_7499880_steps.zip"
FINAL = "/data/wolves/run07_curric_v28/model.zip"
MAX_FRAMES, TAIL = 800, 50

def episode(seed, kind, model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w); w.reset()
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
    last = max((k for k in range(1, len(history)) if key(history[k]) != key(history[k-1])), default=0)
    end = min(len(history), last + TAIL + 1)
    win = history[:end]
    stride = max(1, len(win)//MAX_FRAMES)
    return win[::stride]

d = json.load(open("/data/wolves/run07_cebo_final_20M.json"))
eps = [e for e in d["episodes"] if e["kind"] == "lobos" and e["steps_escolta"] > 0]
eps.sort(key=lambda e: -(e["steps_un_grupo_confirmado"] / max(e["steps_escolta"], 1)))
seeds = [e["seed"] for e in eps[:2]]
print("semillas elegidas (mayor ventana un-solo-grupo-confirmado):",
      [(e["seed"], round(e["steps_un_grupo_confirmado"]/max(e["steps_escolta"],1), 2), e["sizes"]) for e in eps[:2]])

from stable_baselines3 import PPO
models = (("scripted", None), ("best7p5M", PPO.load(BEST, device="cpu")), ("final20M", PPO.load(FINAL, device="cpu")))
for seed in seeds:
    for label, mdl in models:
        w, hist = episode(seed, "lobos", mdl)
        play = window(hist)
        out = f"/data/wolves/diag/run07_seed{seed}_{label}.gif"
        print(f"  seed={seed} {label}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} frames={len(play)} -> {out}", flush=True)
        render_episode(w, play, save_path=out)
print("GIFS_LISTOS")
