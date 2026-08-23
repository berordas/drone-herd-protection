"""visionado_m1pp.py — Lote de visionado del STOP-M1'' (PREREGISTRO_v2 + adendas):
  gemelo_seed21           seed 21 lobos con la capa K (el caso del mecanismo de M1) — ¿los giros
                          coinciden ahora con "presa protegida" en el timeline?
  retarget_masa_puro      episodio de B_masa con RETARGET de la regla de caza (causa protegida)
  redecision_tras_muerte  manager: re-decisión tras la primera MUERTE
  primer_cebo_G           manager: primer episodio con cebo elegido en G
  peor_manager            manager: episodio de mayor severidad
  molinillo_S             manager: episodio S de alta severidad con re-decisiones Δ90 en cadena
                          (el candidato a mecanismo nuevo: re-apuntado ANGULAR por re-arranque)
  despertar_tardio_mgr    manager seed 8 mixto (3 entradas no detectadas, lag 4) — pareja del
                          GIF del seed 77 ("muertes canal B = 0; despertar tardío")
Replay determinista (reset_to + argmax) con snapshots on_tick; sidecar timeline con decisiones,
eventos de capa (RETARGET/FALLBACK), muertes y relevos."""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from hrl.manager_env import ManagerEnv, OPTION_NAMES
from hrl.eval_manager import policy_fn
from render import render_episode

CKPT = "/data/hrl_m1/M1pp/model.zip"
OUT = pathlib.Path("/data/hrl_m1/m1pp/visionado")
(OUT / "gifs").mkdir(parents=True, exist_ok=True)
(OUT / "timelines").mkdir(parents=True, exist_ok=True)

mgr = json.load(open("/data/hrl_m1/eval/manager_M1pp_final__reactive.json"))["episodes"]
masa = json.load(open("/data/hrl_m1/eval/masa_v36__reactive.json"))["episodes"]
orc = {(e["seed"], e["kind"]): e for e in
       json.load(open("/data/hrl_m1/eval/oracle_v36__reactive.json"))["episodes"]}


def pick(eps, cond, key=None, rev=False):
    c = [e for e in eps if cond(e)]
    if not c:
        return None
    return sorted(c, key=key, reverse=rev)[0] if key else c[0]


chosen = []


def add(tag, policy, e):
    if e is not None and all(x[2] is not e for x in chosen):
        chosen.append((tag, policy, e))


add("gemelo_seed21", "manager", next((e for e in mgr if e["seed"] == 21 and e["kind"] == "lobos"), None))
add("retarget_masa_puro", "masa",
    pick(masa, lambda e: e.get("hunt", {}).get("retargets", 0) >= 1,
         key=lambda e: -e["hunt"]["retargets"]))
add("redecision_tras_muerte", "manager",
    pick(mgr, lambda e: "MUERTE" in e["events"][:-1] and len(set(e["actions"])) >= 2))
add("primer_cebo_G", "manager", pick(mgr, lambda e: e["two_front"] and e["actions"][0] != 0))
add("peor_manager", "manager", pick(mgr, lambda e: True, key=lambda e: e["sev"], rev=True))
add("molinillo_S", "manager",
    pick(mgr, lambda e: (not e["two_front"]) and e["sev"] >= 3 and e["actions"].count(2) + e["actions"].count(3) >= 5,
         key=lambda e: -e["sev"]))
add("despertar_tardio_mgr", "manager", next((e for e in mgr if e["seed"] == 8 and e["kind"] == "mixto"), None))

_M = {}
out = []
for tag, pol_name, e in chosen:
    env = ManagerEnv(kinds=(e["kind"],), seed=0, opponent="reactive")
    hist = []

    def snap(w, coord, layer):
        cm = getattr(coord, "_confirmed", None)
        hist.append({**w.snapshot(), "battery": w.battery.copy(),
                     "confirmed_mask": (None if cm is None else cm.copy())})

    env.on_tick = snap
    obs, info = env.reset_to(e["seed"], e["kind"])
    w = env.world
    snap(w, env._coord, env._layer)
    pol = policy_fn("manager:" + CKPT if pol_name == "manager" else pol_name)
    lines = [f"{tag} | seed={e['seed']} {e['kind']} n={e['n_wolves']} G={e['two_front']} "
             f"sev_eval={e['sev']} | oracle sev={orc.get((e['seed'], e['kind']), {}).get('sev')}"]
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first))
        first = False
        t0 = int(w.step_count)
        obs, r, term, trunc, info = env.step(a)
        lines.append(f"t={t0:>6d}  DECISION #{info['decision_idx']:<3d} {OPTION_NAMES[a]:<10s} "
                     f"-> {info['event']:<17s} ticks={info['ticks']:>5d} r={r:.0f}")
        done = term or trunc
    assert int(w.n_depredadas) == e["sev"], f"replay no determinista ({tag}): {w.n_depredadas} != {e['sev']}"
    for ev in env._layer.pop_events():
        if ev["ev"] in ("RETARGET", "RETARGET_BLOCKED", "OPTION_FALLBACK", "SHOW_START"):
            lines.append(f"t={ev['t']:>6d}  capa {ev['ev']} " +
                         " ".join(f"{k}={v}" for k, v in ev.items() if k not in ("t", "ev")))

    def key(s_):
        return (s_["phase"], s_["n_depredadas"], s_["n_safe"])

    last = max((k for k in range(1, len(hist)) if key(hist[k]) != key(hist[k - 1])), default=0)
    win = hist[:min(len(hist), last + 50 + 1)]
    frames = win[::max(1, len(win) // 800)]
    name = f"{tag}_seed{e['seed']}_{e['kind']}_sev{e['sev']}"
    gif = OUT / "gifs" / f"{name}.gif"
    render_episode(w, frames, save_path=str(gif))
    (OUT / "timelines" / f"{name}.txt").write_text("\n".join(lines) + "\n")
    print(tag, gif, flush=True)
    out.append({"tag": tag, "gif": str(gif), "sev": e["sev"], "seed": e["seed"], "kind": e["kind"]})
(OUT / "visionado.json").write_text(json.dumps(out, indent=1))
print("VISIONADO_OK", len(out))
