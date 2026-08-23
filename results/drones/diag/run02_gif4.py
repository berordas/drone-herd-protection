"""run02_gif4.py — GIF nº4 de la narrativa: drones aprendidos DESBARATANDO el cebo.

GIFs GEMELOS (suelo δ≡0 vs política run02 FINAL) del episodio de 2 subgrupos con mayor
contraste (sev suelo − sev política), elegido del diagnóstico de comportamiento y RE-VERIFICADO
con el model.zip final (patrón de run01_render_ejemplo.py). Salida versionada en
/data/gifs/run02_v34/. Culminación de la secuencia: 1 lobos sin defensa → 2 barrera clásica →
3 cebo funcionando (v3.4) → 4 drones defendiendo el cebo (run02).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world                                    # noqa: E402
from render import render_episode                                   # noqa: E402
from rl.residual_drone_coordinator import ResidualDroneCoordinator  # noqa: E402

MODEL = "/data/drones/run02_v34/model.zip"    # el FINAL (20M): 2.40/0/2.27, el artefacto estrella
OUT = "/data/gifs/run02_v34"
MAX_FRAMES, TAIL = 800, 50


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
    os.makedirs(OUT, exist_ok=True)
    model = PPO.load(MODEL, device="cpu")

    src = "/data/drones/run02_v34/comportamiento_final20M.json"
    if not os.path.exists(src):
        src = "/data/drones/run02_v34/comportamiento_best18M.json"
    pol = json.load(open(src))
    su = json.load(open("/data/drones/run02_v34/comportamiento_suelo.json"))
    s = {(e["seed"], e["kind"]): e for e in su["episodes"]}
    p = {(e["seed"], e["kind"]): e for e in pol["episodes"]}
    cand = sorted(((s[k]["n_depredadas"] - p[k]["n_depredadas"], k) for k in s if k in p), reverse=True)
    print(f"candidatos ({src}):", cand[:6])

    for contraste, (seed, kind) in cand[:8]:
        w_pol, _ = episode(seed, kind, model)                 # re-verificar con el model.zip FINAL
        sev_suelo = s[(seed, kind)]["n_depredadas"]
        print(f"  seed={seed} kind={kind}: suelo={sev_suelo} politica(final)={w_pol.n_depredadas}")
        if sev_suelo - w_pol.n_depredadas >= max(2, contraste - 1):
            break
    else:
        contraste, (seed, kind) = cand[0]
        print("  (ninguno mantuvo el contraste con el final; uso el primero del diagnostico)")

    grupos = "mas".join(str(x) for x in s[(seed, kind)]["sizes"])
    for label, mdl in (("n4a_suelo_cebo_mata", None), ("n4b_marl_desbarata", model)):
        w, hist = episode(seed, kind, mdl, keep_history=True)
        play = window(hist)
        out = f"{OUT}/run02_seed{seed}_{kind}_{grupos}_{label}_sev{w.n_depredadas}.gif"
        print(f"  {label}: sev={w.n_depredadas} status={w.status} pasos={w.step_count} "
              f"frames={len(play)} -> {out}", flush=True)
        render_episode(w, play, save_path=out)
    print("GIF4_LISTO")


if __name__ == "__main__":
    main()
