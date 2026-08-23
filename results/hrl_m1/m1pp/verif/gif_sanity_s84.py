"""GIFs de escalado de la sanity (re-nivelado paso 1): seed 84, CEBO_keep forzado, G/n>=3 —
el par más divergente: v3.5 (pre-K + órbita, sev 0) vs v3.6 (capa K + estática, sev 6).
Timeline sidecar con eventos de la capa + fase + relevos."""
import sys
import numpy as np

MODE = sys.argv[1]                      # v35 = preK+órbita · v36 = K+estática
ROOT = "/workspace/wt_preK" if MODE == "v35" else "/workspace"
OMEGA = 0.02 if MODE == "v35" else 0.0
sys.path.insert(0, ROOT)

from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode
from hrl.options_wolf import WolfOptionLayer

SEED = 84

def snap(w, conf):
    s = {**w.snapshot(), "battery": w.battery.copy()}
    if conf is not None:
        s["confirmed_mask"] = conf.copy()
    return s

if __name__ == "__main__":
    layer = WolfOptionLayer(option=("CEBO", {"membership": "keep", "hold": 50.0}))
    w = build_world(SEED, "lobos", wolf_controller=layer)
    inner = ReactiveCoordinator(w, patrol_omega=OMEGA)
    w.reset()
    hist, lines = [snap(w, getattr(inner, "_confirmed", None))], []
    prev_phase, prev_dep = w.phase, 0
    while True:
        layer.refresh(w)
        _o, _r, t, tr, _i = w.step(inner.act(w.get_observation()))
        hist.append(snap(w, getattr(inner, "_confirmed", None)))
        for e in layer.pop_events():
            lines.append(f"t={e['t']} {e['ev']} " + " ".join(f"{k}={v}" for k, v in e.items() if k not in ("t", "ev")))
        if w.phase != prev_phase:
            lines.append(f"t={w.step_count} FASE {prev_phase}->{w.phase}")
            prev_phase = w.phase
        if int(w.n_depredadas) > prev_dep:
            prev_dep = int(w.n_depredadas)
            lines.append(f"t={w.step_count} MUERTE (total {prev_dep})")
        if t or tr:
            break
    path = f"/data/hrl_m1/m1pp/gifs/sanity_s84_{MODE}.gif"
    stride = max(1, len(hist) // 2500)
    render_episode(w, hist[::stride], save_path=path)
    open(path.replace(".gif", "_timeline.txt"), "w").write(
        "\n".join(lines) + f"\nsev={w.n_depredadas} status={w.status} stride={stride} frames={len(hist)}\n")
    print(path, "sev", w.n_depredadas, w.status, len(hist), "ticks, stride", stride)
