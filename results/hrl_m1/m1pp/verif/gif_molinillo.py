"""GIF dedicado del MOLINILLO: seed 63 mixto (S, n=4, sev 8; Δ90×6 + MASA×4 + Δ180×2 + keep) —
el candidato a mecanismo de M1'': re-apuntado ANGULAR del asalto en cada re-arranque de CEBO."""
import json
import pathlib
import sys

sys.path.insert(0, "/workspace")
from hrl.manager_env import ManagerEnv, OPTION_NAMES
from hrl.eval_manager import policy_fn
from render import render_episode

OUT = pathlib.Path("/data/hrl_m1/m1pp/visionado")
env = ManagerEnv(kinds=("mixto",), seed=0, opponent="reactive")
hist = []


def snap(w, coord, layer):
    cm = getattr(coord, "_confirmed", None)
    hist.append({**w.snapshot(), "battery": w.battery.copy(),
                 "confirmed_mask": (None if cm is None else cm.copy())})


env.on_tick = snap
obs, info = env.reset_to(63, "mixto")
w = env.world
snap(w, env._coord, env._layer)
pol = policy_fn("manager:/data/hrl_m1/M1pp/model.zip")
lines = [f"molinillo_S | seed=63 mixto n={info['n_wolves']} G={info['two_front']}"]
first, done = True, False
while not done:
    a = int(pol(obs, info, first))
    first = False
    t0 = int(w.step_count)
    obs, r, term, trunc, info = env.step(a)
    lines.append(f"t={t0:>6d}  DECISION #{info['decision_idx']:<3d} {OPTION_NAMES[a]:<10s} "
                 f"-> {info['event']:<17s} ticks={info['ticks']:>5d} r={r:.0f}")
    done = term or trunc
assert int(w.n_depredadas) == 8, w.n_depredadas
for ev in env._layer.pop_events():
    if ev["ev"] in ("RETARGET", "RETARGET_BLOCKED", "OPTION_FALLBACK", "SHOW_START"):
        lines.append(f"t={ev['t']:>6d}  capa {ev['ev']} " +
                     " ".join(f"{k}={v}" for k, v in ev.items() if k not in ("t", "ev")))


def key(s_):
    return (s_["phase"], s_["n_depredadas"], s_["n_safe"])


last = max((k for k in range(1, len(hist)) if key(hist[k]) != key(hist[k - 1])), default=0)
win = hist[:min(len(hist), last + 50 + 1)]
frames = win[::max(1, len(win) // 800)]
gif = OUT / "gifs" / "molinillo_S_seed63_mixto_sev8.gif"
render_episode(w, frames, save_path=str(gif))
(OUT / "timelines" / "molinillo_S_seed63_mixto_sev8.txt").write_text("\n".join(lines) + "\n")
print("OK", gif)
