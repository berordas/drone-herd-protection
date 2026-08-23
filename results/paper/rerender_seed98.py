"""rerender_seed98.py — re-render de los 3 fotogramas de la jugada entera (seed 98, mixto, manager M1'''') con
cabecera/leyenda en ES y en EN. Replay DETERMINISTA con el código v3.7 EXACTO (worktree pineado 4bf5024, el
mismo con el que se renderizó el GIF); ningún entrenamiento ni eval nueva. Los textos se traducen sobre los
objetos Text de la figura de matplotlib (el renderer del repo NO se modifica)."""
import sys, re, json
sys.path.insert(0, "/workspace/wt_v37_replica")
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
from hrl.manager_env import ManagerEnv
from hrl.eval_manager import policy_fn
from render import render_episode
CKPT = "/data/hrl_m1/M1pppp/model.zip"; OUT = "/data/paper/figs_en"
e = [x for x in json.load(open("/data/hrl_m1/eval/manager_M1pppp_final__reactive.json"))["episodes"] if x["seed"] == 98 and x["kind"] == "mixto"][0]
env = ManagerEnv(kinds=("mixto",), seed=0, opponent="reactive"); hist = []
def snap(w, coord, layer):
    cm = getattr(coord, "_confirmed", None)
    hist.append({**w.snapshot(), "battery": w.battery.copy(), "confirmed_mask": (None if cm is None else cm.copy())})
env.on_tick = snap
obs, info = env.reset_to(98, "mixto"); w = env.world; snap(w, env._coord, env._layer)
pol = policy_fn("manager:" + CKPT); first, done = True, False; decs = []
while not done:
    a = int(pol(obs, info, first)); first = False; t0 = int(w.step_count)
    obs, r, term, trunc, info = env.step(a); decs.append((t0, a, info["event"], info["ticks"])); done = term or trunc
assert int(w.n_depredadas) == e["sev"] == 2, f"replay no determinista: {w.n_depredadas} != {e['sev']}"
lay = env._layer
hitos = {"t_staged": lay.t_staged, "t_show": lay.t_show, "t_suelta": lay.t_suelta, "t_strike": lay.t_strike, "ticks": len(hist), "decisiones": decs}
assert (lay.t_staged, lay.t_show, lay.t_suelta, lay.t_strike) == (901, 1231, 1419, 2375), hitos
print("replay OK:", {k: v for k, v in hitos.items() if k != "decisiones"}, decs)

TR = [(r"FASE: VIGILANCIA", "PHASE: SURVEILLANCE"), (r"FASE: ESCOLTA", "PHASE: ESCORT"), (r"FASE: ", "PHASE: "),
      (r"\bpaso=", "step="), (r"\blobos=", "wolves="), (r"presa=adulta", "prey=adult"), (r"presa=ternero", "prey=calf"),
      (r"episodio=mixto", "episode=mixed"), (r"episodio=corzos", "episode=roe deer"), (r"distracción=", "distraction="),
      (r"\bcorzos\b", "roe deer"), (r"jabalíes", "wild boar"), (r"a salvo=", "safe="), (r"cazadas=", "killed="), (r"fuera=", "outside="),
      (r"a salvo ", "safe "), (r"cazadas ", "killed "), (r"fuera ", "outside "),
      (r"zona segura \(establo\)", "safe zone (shelter)"), (r"estación central \(reserva\)", "charging station (reserve)"),
      (r"zona vacas \(bbox\)", "herd (bounding box)"), (r"cono de seguridad", "safety cone"), (r"^defensora$", "defender cow"),
      (r"radio disuasión", "expulsion radius"), (r"^investigando$", "investigating"), (r"terneros", "calves"),
      (r"cuadrado naranja = lobo detectado \(<= r_detect de un ACTIVE\)", "orange square = wolf detected (<= r_detect of an ACTIVE drone)"),
      (r"cuadrado rojo = lobo confirmado \(latch de la barrera\)", "red square = wolf confirmed (barrier latch)"),
      (r"ÉXITO", "SUCCESS"), (r"DEPREDACIÓN", "PREDATION")]
def tr(s):
    for a, b in TR: s = re.sub(a, b, s)
    return s
FR = [("show", 1230), ("suelta", 1419), ("strike", 2373)]     # mismos índices que la figura ES (frame = t//3 del GIF)
for lang in ("es", "en"):
    for name, idx in FR:
        anim = render_episode(w, [hist[idx]], save_path=None)
        fig = plt.gcf(); anim._init_draw(); anim._draw_frame(0)
        if lang == "en":
            for t in fig.findobj(Text):
                s = t.get_text()
                if s: t.set_text(tr(s))
        fig.savefig(f"{OUT}/_frame_{name}_{lang}.png", dpi=100); plt.close(fig)
json.dump({k: v for k, v in hitos.items()}, open(f"{OUT}/_rerender_seed98_hitos.json", "w"))
print("RERENDER_OK")
