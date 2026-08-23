"""visionado_m1pppp.py — Lote de visionado del STOP-M1'''' (firma 2). PREGUNTA ÚNICA del dueño:
¿se ve la jugada simple ENTERA — un lobo muestra, el resto entra por el otro lado — y el manager
decidiendo CUÁNDO?
  jugada_entera_S      S (Δ90) con hitos completos y strike — la jugada entera en S
  jugada_entera_G      G (keep) — la geometría de dos frentes jugada entera
  gemelo_seed21        el caso del mecanismo de M1, con la capa completa nueva
  peor_manager         episodio de mayor severidad
  stall_rescate_s68    uno de los 9 STALL listados (seed 68 lobos, sev 3): el tripwire rescata
                       la alineación lenta y la jugada se COMPLETA (decisión humana pendiente)
  retarget_masa        la regla de caza K en uso legítimo (B_masa)
Timelines con decisiones + ALIGN_END (causa, err) + SHOW_START (staged_causa, err) + STALL +
RETARGET + hitos de censura. Replay determinista (assert sev)."""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from hrl.manager_env import ManagerEnv, OPTION_NAMES
from hrl.eval_manager import policy_fn
from render import render_episode

CKPT = "/data/hrl_m1/M1pppp/model.zip"
OUT = pathlib.Path("/data/hrl_m1/m1pppp/visionado")
(OUT / "gifs").mkdir(parents=True, exist_ok=True)
(OUT / "timelines").mkdir(parents=True, exist_ok=True)

mgr = json.load(open("/data/hrl_m1/eval/manager_M1pppp_final__reactive.json"))["episodes"]
masa = json.load(open("/data/hrl_m1/eval/masa_v37__reactive.json"))["episodes"]
orc = {(e["seed"], e["kind"]): e for e in
       json.load(open("/data/hrl_m1/eval/oracle_v37__reactive.json"))["episodes"]}


def pick(eps, cond, key=None, rev=False):
    c = [e for e in eps if cond(e)]
    if not c:
        return None
    return sorted(c, key=key, reverse=rev)[0] if key else c[0]


chosen = []


def add(tag, policy, e):
    if e is not None and all(x[2] is not e for x in chosen):
        chosen.append((tag, policy, e))


add("jugada_entera_S", "manager",
    pick(mgr, lambda e: (not e["two_front"]) and 2 <= e["sev"] <= 4 and (e.get("stalls") or 0) == 0
         and e["jugada"]["t_strike"] is not None,
         key=lambda e: e["decisions"]))
add("jugada_entera_G", "manager",
    pick(mgr, lambda e: e["two_front"] and e["actions"][0] == 1 and e["jugada"]["t_suelta"] is not None,
         key=lambda e: -e["sev"]))
add("gemelo_seed21", "manager", next((e for e in mgr if e["seed"] == 21 and e["kind"] == "lobos"), None))
add("peor_manager", "manager", pick(mgr, lambda e: True, key=lambda e: e["sev"], rev=True))
add("stall_rescate_s68", "manager", next((e for e in mgr if e["seed"] == 68 and e["kind"] == "lobos"), None))
add("retarget_masa", "masa",
    pick(masa, lambda e: e.get("hunt", {}).get("retargets", 0) >= 1,
         key=lambda e: -e["hunt"]["retargets"]))

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
             f"sev_eval={e['sev']} jugada={e.get('jugada')} stalls={e.get('stalls')} | "
             f"oracle sev={orc.get((e['seed'], e['kind']), {}).get('sev')}"]
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first))
        first = False
        t0 = int(w.step_count)
        obs, r, term, trunc, info = env.step(a)
        lines.append(f"t={t0:>6d}  DECISION #{info['decision_idx']:<3d} {OPTION_NAMES[a]:<10s} "
                     f"-> {info['event']:<17s} ticks={info['ticks']:>5d} r={r:.2f}")
        done = term or trunc
    assert int(w.n_depredadas) == e["sev"], f"replay no determinista ({tag}): {w.n_depredadas} != {e['sev']}"
    for ev in env._layer.pop_events():
        if ev["ev"] in ("RETARGET", "RETARGET_BLOCKED", "OPTION_FALLBACK", "SHOW_START",
                        "ALIGN_END", "STALL"):
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
    (OUT / "timelines" / f"{name}.txt").write_text("\n".join(sorted(lines[1:], key=lambda l: int(l.split("=")[1].split()[0]))
                                                             and lines) + "\n")
    print(tag, gif, flush=True)
    out.append({"tag": tag, "gif": str(gif), "sev": e["sev"], "seed": e["seed"], "kind": e["kind"]})
(OUT / "visionado.json").write_text(json.dumps(out, indent=1))
print("VISIONADO_OK", len(out))
