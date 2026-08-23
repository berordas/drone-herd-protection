"""verif0_orbita.py — Diagnostico opcional de la adjudicacion VERIF-0 (dueno): tasa de
interbloqueo de los 9 seeds de verif0 (oracle S, CEBO d90) bajo patrulla ORBITA v3.5
(patrol_omega=0.02) con la capa PRE-S1 — ¿la patrulla estatica agravo el interbloqueo?
SOLO LECTURA; debe ejecutarse ANTES de aplicar el Commit S1."""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp
import numpy as np

sys.path.insert(0, "/workspace")
from coordinators import ReactiveCoordinator
from wolf_controllers import assault_staged
from hrl.eval_manager import policy_fn
from hrl.manager_env import ManagerEnv

SEEDS = [3, 5, 9, 14, 18, 24, 35, 36, 55]
OUT = "/data/hrl_m1/m1pppp/verif/verif0_orbita.json"

# Parche de capa de EVALUACION: el coordinador de la defensa con la orbita historica v3.5.
ManagerEnv._make_coord = lambda self, w: ReactiveCoordinator(w, patrol_omega=0.02)


def staged_now(w, layer):
    if layer._opt_name != "CEBO" or w.wolf_decoy_released or w.pack_prey2 < 0:
        return None
    if layer._s1.size == 0 or layer._s2.size == 0:
        return None
    p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
    return bool(assault_staged(w, layer._s2, p2, stage_hold=layer._hold))


def run(seed):
    env = ManagerEnv(kinds=("lobos",), seed=0, opponent="reactive")
    obs, info = env.reset_to(seed, "lobos")
    w, layer = env.world, env._layer
    est = {"noshow": 0, "max": 0, "shows": []}

    def tick(w_, c_, l_):
        if staged_now(w_, l_):
            est["noshow"] += 1
            est["max"] = max(est["max"], est["noshow"])

    env.on_tick = tick
    pol = policy_fn("oracle")
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
        for ev in layer.pop_events():
            if ev["ev"] == "SHOW_START":
                est["shows"].append(int(ev["t"])); est["noshow"] = 0
    return {"seed": seed, "sev": int(w.n_depredadas), "staged_noshow_max": est["max"],
            "n_shows": len(est["shows"]), "t_show1": est["shows"][0] if est["shows"] else None}


if __name__ == "__main__":
    with mp.get_context("fork").Pool(9) as pool:
        rows = pool.map(run, SEEDS, chunksize=1)
    stalls = sum(1 for r in rows if r["staged_noshow_max"] >= 400)
    res = {"patrulla": "orbita v3.5 (omega=0.02)", "capa": "PRE-S1", "rows": rows,
           "stalls_400": stalls, "nota": "comparar con 9/9 en estatica (verif0.json)"}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    print("ORBITA_OK")
