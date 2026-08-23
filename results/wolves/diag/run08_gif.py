"""run08_gif.py — GIF de run08: episodio de 2 frentes con la política aprendida, ¿ceba o no?
GEMELOS del seed 76 lobos (cebo 1 + asalto 3): suelo δ≡0 = el cebo scriptado v3.4 en pleno
funcionamiento (6 muertas, todas killer-NO-confirmado) vs política best2.5M (5/5 — lo conserva
degradado, no genera cebo propio). Versionado en /data/gifs/run08_dieta50/."""
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world                                   # noqa: E402
from render import render_episode                                  # noqa: E402
from rl.policy_wolf_controller import SyncedReactiveCoordinator    # noqa: E402
from rl.residual_wolf_controller import ResidualWolfController     # noqa: E402

OUT = "/data/gifs/run08_dieta50"
MAX_FRAMES, TAIL = 800, 50
SEED, KIND = 76, "lobos"
BEST = "/data/wolves/run08_dieta50/checkpoints/ppo_wolves_2500000_steps.zip"


def episode(model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(SEED, KIND, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w)
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
    win = history[:min(len(history), last + TAIL + 1)]
    stride = max(1, len(win) // MAX_FRAMES)
    return win[::stride]


def main():
    from stable_baselines3 import PPO
    os.makedirs(OUT, exist_ok=True)
    model = PPO.load(BEST, device="cpu")
    for label, mdl in (("n1_suelo_cebo_scriptado_pleno", None), ("n2_politica_best2p5M_conserva_degradado", model)):
        w, hist = episode(mdl)
        play = window(hist)
        out = f"{OUT}/run08_seed{SEED}_{KIND}_1mas3_{label}_sev{w.n_depredadas}.gif"
        print(f"  {label}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
              f"frames={len(play)} -> {out}", flush=True)
        render_episode(w, play, save_path=out)
    print("GIF_RUN08_OK")


if __name__ == "__main__":
    main()
