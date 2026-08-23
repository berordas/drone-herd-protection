"""visionado_m2.py — GIF del STOP-M2: una jugada CORTADA por K=1000 (el mecanismo de la
ablacion) en un episodio G con la conducta nueva (D180 en G). Timeline con cortes K_MAX."""
import json, pathlib, sys
import numpy as np
sys.path.insert(0, "/workspace")
from hrl.manager_env import ManagerEnv, OPTION_NAMES
from hrl.eval_manager import policy_fn
from render import render_episode

OUT = pathlib.Path("/data/hrl_m1/m1pppp/visionado")
mgr = json.load(open("/data/hrl_m1/eval/manager_M2_final__reactive.json"))["episodes"]
cand = sorted([e for e in mgr if e["two_front"] and e["sev"] >= 1
               and "K_MAX" in e["events"] and e["jugada"]["t_suelta"] is not None],
              key=lambda e: -e["events"].count("K_MAX"))
e = cand[0]
env = ManagerEnv(kinds=(e["kind"],), seed=0, opponent="reactive", fixed_k=1000)
hist = []
env.on_tick = lambda w, c, l: hist.append({**w.snapshot(), "battery": w.battery.copy(),
                                           "confirmed_mask": (None if getattr(c, "_confirmed", None) is None
                                                              else c._confirmed.copy())})
obs, info = env.reset_to(e["seed"], e["kind"])
w = env.world
pol = policy_fn("manager:/data/hrl_m1/M2/model.zip")
lines = [f"STOP-M2 jugada cortada | seed={e['seed']} {e['kind']} n={e['n_wolves']} G={e['two_front']} "
         f"sev={e['sev']} jugada={e['jugada']} K=1000 FIJO"]
first, done = True, False
while not done:
    a = int(pol(obs, info, first)); first = False
    t0 = int(w.step_count)
    obs, r, term, trunc, info = env.step(a)
    lines.append(f"t={t0:>6d}  DECISION #{info['decision_idx']:<3d} {OPTION_NAMES[a]:<10s} "
                 f"-> {info['event']:<17s} ticks={info['ticks']:>5d}")
    done = term or trunc
assert int(w.n_depredadas) == e["sev"], "replay no determinista"
for ev in env._layer.pop_events():
    if ev["ev"] in ("SHOW_START", "ALIGN_END", "STALL", "OPTION_FALLBACK", "RETARGET"):
        lines.append(f"t={ev['t']:>6d}  capa {ev['ev']} " +
                     " ".join(f"{k}={v}" for k, v in ev.items() if k not in ("t", "ev")))
frames = hist[::max(1, len(hist) // 800)]
name = f"m2_jugada_cortada_seed{e['seed']}_{e['kind']}_sev{e['sev']}"
render_episode(w, frames, save_path=str(OUT / "gifs" / f"{name}.gif"))
(OUT / "timelines" / f"{name}.txt").write_text("\n".join(lines) + "\n")
print("M2_GIF_OK", name)
