"""visionado_d2.py — GIFs del STOP-D2 (pregunta única del dueño: ¿se ve el REPARTO — la barrera
aguanta y un guardia cubre el otro frente — y el manager decidiendo CUÁNDO?). Episodios con
atacante manager lobo (los más duros) y cebo 2f, elegidos de las evals: (1) reparto_entero — 2º
clúster percibido → 3-1 → guardia gana la carrera → vuelta a 4-0; (2) peor_dronemgr; (3)
decision_4_0 — episodio de 1 frente mantenido en 4-0 (sin guardias ociosos). Timelines con
decisiones y eventos (CLUSTER_CHANGE/STALL)."""
import json, pathlib, sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world, CONFIG_V2
from world import World
from hrl.manager_drone import LearnedAllocatorCoordinator, EVD_NAMES, PARTITION_NAMES
from render import render_episode

CK = sys.argv[1] if len(sys.argv) > 1 else "/data/hrl_d2/D2/model.zip"
OUT = pathlib.Path("/data/hrl_d2/visionado"); (OUT / "gifs").mkdir(parents=True, exist_ok=True)
(OUT / "timelines").mkdir(exist_ok=True)
cebo = json.load(open("/data/hrl_d2/e04_dronemgr__cebo2f.json"))["episodes"]
nat = json.load(open("/data/hrl_d2/e04_dronemgr__natural.json"))["episodes"]


def pick(eps, cond, key):
    c = [e for e in eps if cond(e)]
    return sorted(c, key=key)[0] if c else None


chosen = [
    ("reparto_entero", pick(cebo, lambda e: e["carrera"]["gana_guardia"] and e["cambios"] >= 2 and e["sev"] <= 1,
                            key=lambda e: e["cambios"])),
    ("peor_dronemgr", pick(cebo, lambda e: True, key=lambda e: -e["sev"])),
    ("decision_4_0", pick(nat, lambda e: (not e["two_front"]) and e["cambios"] == 0 and (e.get("stalls_def") or 0) == 0,
                          key=lambda e: e["sev"])),
]
for tag, e in chosen:
    if e is None:
        print("sin candidato:", tag); continue
    w = build_world(e["seed"], e["kind"]) if e["kind"] in ("lobos", "mixto", "corzos") else World(seed=e["seed"], **CONFIG_V2)
    coord = LearnedAllocatorCoordinator(w, CK)
    w.reset()
    hist, lines, last_part = [], [f"{tag} | seed={e['seed']} {e['kind']} sev_eval={e['sev']} cambios={e['cambios']} carrera={e['carrera']}"], None
    while True:
        wp = coord.act(w.get_observation())
        if coord.particion != last_part:
            lines.append(f"t={int(w.step_count):>6d}  PARTICION {coord.particion} (evento previo {EVD_NAMES[coord.core.last_event]})")
            last_part = coord.particion
        _o, _r, t, tr, _i = w.step(wp)
        hist.append({**w.snapshot(), "battery": w.battery.copy(),
                     "confirmed_mask": (coord.inner._confirmed.copy() if coord.inner._confirmed is not None else None)})
        if t or tr:
            break
    assert int(w.n_depredadas) == e["sev"], f"replay no determinista {tag}: {w.n_depredadas} vs {e['sev']}"
    frames = hist[::max(1, len(hist) // 800)]
    name = f"{tag}_seed{e['seed']}_{e['kind']}_sev{e['sev']}"
    render_episode(w, frames, save_path=str(OUT / "gifs" / f"{name}.gif"))
    (OUT / "timelines" / f"{name}.txt").write_text("\n".join(lines) + "\n")
    print(tag, name)
print("VISIONADO_D2_OK")
