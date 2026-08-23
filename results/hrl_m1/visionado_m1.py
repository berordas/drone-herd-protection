"""visionado_m1.py — Lote de visionado del STOP-M1 desde la eval del manager vs Reactive (100
semillas): primer episodio con cebo elegido en G · un ABORT_BAIT_FAILED en acción · un S con Δ90 ·
un n=2 (¿MASA?) · una re-decisión tras la 1ª muerte · el peor episodio del manager · mejor y peor
Δ vs B_oracle. Re-simula determinista (mismo predict) grabando snapshots por tick con el gancho
on_tick del env; render nuevo; sidecar timeline con las DECISIONES del manager + eventos de capa.
Uso: python3 visionado_m1.py <ckpt.zip> <eval_json_manager_reactive> [outdir]"""
import json, pathlib, sys
sys.path.insert(0, "/workspace")
import numpy as np
from hrl.manager_env import ManagerEnv, OPTION_NAMES
from render import render_episode

CKPT, EVJ = sys.argv[1], sys.argv[2]
OUT = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "/data/hrl_m1/M1/visionado")
(OUT / "gifs").mkdir(parents=True, exist_ok=True); (OUT / "timelines").mkdir(parents=True, exist_ok=True)
from stable_baselines3 import PPO
model = PPO.load(CKPT, device="cpu")
eps = json.load(open(EVJ))["episodes"]
orc = {(e["seed"], e["kind"]): e for e in json.load(open("/data/hrl_m1/eval/oracle__reactive.json"))["episodes"]}

def pick(cond, key=None, rev=False):
    c = [e for e in eps if cond(e)]
    if not c:
        return None
    return sorted(c, key=key, reverse=rev)[0] if key else sorted(c, key=lambda e: (e["kind"], e["seed"]))[0]
chosen = []
def add(tag, e):
    if e is not None and all(x[1] is not e for x in chosen):
        chosen.append((tag, e))
add("primer_cebo_G", pick(lambda e: e["two_front"] and e["actions"][0] != 0))
add("abort_en_accion", pick(lambda e: "ABORT_BAIT_FAILED" in e["events"] and e["decisions"] <= 10, key=lambda e: e["decisions"]))
add("S_d90", pick(lambda e: (not e["two_front"]) and 2 in e["actions"][:3]))
add("n2", pick(lambda e: e["n_wolves"] == 2))
add("redecision_tras_1a_muerte", pick(lambda e: "MUERTE" in e["events"][:-1] and len(set(e["actions"])) >= 2))
add("peor_manager", pick(lambda e: True, key=lambda e: e["sev"], rev=True))
add("mejor_vs_oracle", pick(lambda e: (e["seed"], e["kind"]) in orc, key=lambda e: e["sev"] - orc[(e["seed"], e["kind"])]["sev"], rev=True))
add("peor_vs_oracle", pick(lambda e: (e["seed"], e["kind"]) in orc, key=lambda e: e["sev"] - orc[(e["seed"], e["kind"])]["sev"]))

out = []
for tag, e in chosen[:8]:
    env = ManagerEnv(kinds=(e["kind"],), seed=0, opponent="reactive")
    hist = []
    def snap(w, coord, layer):
        cm = getattr(coord, "_confirmed", None)
        hist.append({**w.snapshot(), "battery": w.battery.copy(), "confirmed_mask": (None if cm is None else cm.copy())})
    env.on_tick = snap
    obs, info = env.reset_to(e["seed"], e["kind"])
    w = env.world
    snap(w, env._coord, env._layer)
    lines = [f"{tag} | seed={e['seed']} {e['kind']} n={e['n_wolves']} G={e['two_front']} | manager={pathlib.Path(CKPT).stem} sev_eval={e['sev']} | oracle sev={orc.get((e['seed'], e['kind']), {}).get('sev')}"]
    done = False
    while not done:
        a, _ = model.predict(obs, deterministic=True); a = int(a)
        t0 = int(w.step_count)
        obs, r, term, trunc, info = env.step(a)
        lines.append(f"t={t0:>6d}  DECISION #{info['decision_idx']:<3d} {OPTION_NAMES[a]:<10s} -> {info['event']:<17s} ticks={info['ticks']:>5d} r={r:.0f}")
        done = term or trunc
    assert int(w.n_depredadas) == e["sev"], f"replay no determinista: {w.n_depredadas} != {e['sev']}"
    for ev in env._layer.pop_events():
        lines.append(f"t={ev['t']:>6d}  capa {ev['ev']} {ev}")
    # ventana relevante (mismo criterio que run_e0)
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
