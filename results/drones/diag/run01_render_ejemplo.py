"""run01_render_ejemplo.py — GIFs GEMELOS de un episodio ilustrativo (barrera vs politica MARL).

Elige, de comportamiento_run01.json, el episodio de 2 subgrupos con mayor contraste
(sev suelo - sev politica), lo re-corre con el model.zip FINAL (verificando que el contraste
se mantiene; si no, prueba el siguiente candidato) y guarda los dos GIFs con la ventana
relevante de main.py. Usar y tirar; artefactos a /data/drones/run01/.
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world                                    # noqa: E402
from render import render_episode                                   # noqa: E402
from rl.residual_drone_coordinator import ResidualDroneCoordinator  # noqa: E402

MODEL = "/data/drones/run01/model.zip"        # el FINAL (20M): 2.35/0/2.34, el artefacto estrella
MAX_FRAMES, TAIL = 800, 50                    # = ventana relevante de main.py


def episode(seed, kind, model, keep_history=False):
    w = build_world(seed, kind)
    coord = ResidualDroneCoordinator(w, model=model)
    w.reset()
    hist = [{**w.snapshot(), "battery": w.battery.copy()}] if keep_history else None
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        if keep_history:
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


def main():
    from stable_baselines3 import PPO
    model = PPO.load(MODEL, device="cpu")

    d = json.load(open("/data/drones/run01/comportamiento_run01.json"))
    s = {(e["seed"], e["kind"]): e for e in d["suelo"]["episodes"]}
    p = {(e["seed"], e["kind"]): e for e in d["politica"]["episodes"]}
    cand = sorted(((s[k]["n_depredadas"] - p[k]["n_depredadas"], k) for k in s if k in p), reverse=True)
    print("candidatos (contraste con el ckpt del diagnostico):", cand[:6])

    for contraste, (seed, kind) in cand[:8]:
        w_pol, _ = episode(seed, kind, model)                 # re-verificar con el model.zip FINAL
        sev_suelo = s[(seed, kind)]["n_depredadas"]
        print(f"  seed={seed} kind={kind}: suelo={sev_suelo} politica(final)={w_pol.n_depredadas}")
        if sev_suelo - w_pol.n_depredadas >= max(2, contraste - 1):
            break
    else:
        contraste, (seed, kind) = cand[0]
        print("  (ninguno mantuvo el contraste con el final; uso el primero del diagnostico)")

    for label, mdl in (("barrera", None), ("marl", model)):
        w, hist = episode(seed, kind, mdl, keep_history=True)
        play = window(hist)
        out = f"/data/drones/run01/ejemplo_seed{seed}_{kind}_{label}.gif"
        print(f"  {label}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
              f"frames={len(play)} -> {out}", flush=True)
        render_episode(w, play, save_path=out)
    print("LISTO")


if __name__ == "__main__":
    main()
