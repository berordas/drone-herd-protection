"""verif_s2_replays.py — Verificacion de los Commits S1+S2 (orden del dueno): replays de
s67/s86 lobos (manager M1pp) — los ABORTs POST-show deben colapsar de 268/143 a ~0 (S2:
ABORT solo evaluable pre-release); los pre-show legitimos se conservan (ahora acotados por
la fase de alineacion S1). Tambien s63 mixto (el del ABORT pre-show staged) y s35 lobos
(cadena 470). NOTA: con S1 activo la trayectoria cambia respecto a M1'' (el show llega antes);
los numeros son del ckpt M1pp REJUGADO sobre la capa nueva — verificacion de mecanismo, no eval."""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

sys.path.insert(0, "/workspace")
from hrl.eval_manager import policy_fn
from hrl.manager_env import ManagerEnv

CKPT = "/data/hrl_m1/M1pp/model.zip"
PRE = {(67, "lobos"): 268, (86, "lobos"): 143, (63, "mixto"): 1, (35, "lobos"): 470}
OUT = "/data/hrl_m1/m1pppp/verif/verif_s2.json"

rows = []
for (seed, kind), pre_aborts in PRE.items():
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    obs, info = env.reset_to(seed, kind)
    w, layer = env.world, env._layer
    pol = policy_fn("manager:" + CKPT)
    aborts_pre = aborts_post = 0
    t_show = None
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
        for ev in layer.pop_events():
            if ev["ev"] == "SHOW_START" and t_show is None:
                t_show = int(ev["t"])
        if info["event"] == "ABORT_BAIT_FAILED":
            if w.wolf_decoy_released:
                aborts_post += 1
            else:
                aborts_pre += 1
    rows.append({"seed": seed, "kind": kind, "aborts_M1pp": pre_aborts,
                 "aborts_pre_show": aborts_pre, "aborts_post_show": aborts_post,
                 "t_show": t_show, "sev": int(w.n_depredadas),
                 "decisiones": info["ep_decisions"]})
    print(rows[-1], flush=True)
ok = all(r["aborts_post_show"] == 0 for r in rows)
json.dump({"rows": rows, "post_show_cero": ok}, open(OUT, "w"), indent=1, ensure_ascii=False)
print("ABORTS POST-SHOW = 0 EN TODOS:", ok)
print("VERIF_S2_OK")
