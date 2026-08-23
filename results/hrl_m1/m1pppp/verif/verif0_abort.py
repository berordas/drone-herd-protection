"""verif0_abort.py — VERIFICACION 0 del plan M1'''' (SOLO LECTURA, ~30 min).
(a) Manager (seed 63 mixto + 5 S con mas ABORTs): en cada ABORT, estado del mundo:
    show ya disparado (latch), asalto STAGED, rumbo alcanzado, d(asalto->presa2), ticks del tramo.
    "Jugada a punto de completarse" := staged o released en el momento del ABORT.
(b) Brazos SIN manager (B_oracle en 20 S, B_spawn en 10 G): ticks acumulados en STAGED sin show
    antes del primer show; si algun episodio >= 400 -> EL GUION SE ATASCA SOLO => PARAR Y AVISAR.
"""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp
import numpy as np

sys.path.insert(0, "/workspace")
from wolf_controllers import assault_staged
from hrl.eval_manager import policy_fn
from hrl.manager_env import ManagerEnv

CKPT = "/data/hrl_m1/M1pp/model.zip"
OUT = "/data/hrl_m1/m1pppp/verif/verif0.json"

MGR_EPS = [(63, "mixto"), (35, "lobos"), (5, "mixto"), (67, "lobos"), (98, "lobos"), (86, "lobos")]


def staged_now(w, layer):
    if layer._opt_name != "CEBO" or w.wolf_decoy_released or w.pack_prey2 < 0:
        return None
    s1, s2 = layer._s1, layer._s2
    if s1.size == 0 or s2.size == 0:
        return None
    p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
    return bool(assault_staged(w, s2, p2, stage_hold=layer._hold))


def run_manager(seed, kind):
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    obs, info = env.reset_to(seed, kind)
    w, layer = env.world, env._layer
    pol = policy_fn("manager:" + CKPT)
    aborts, shows = [], []
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
        for ev in layer.pop_events():
            if ev["ev"] == "SHOW_START":
                shows.append(int(ev["t"]))
        if info["event"] == "ABORT_BAIT_FAILED":
            st = staged_now(w, layer)
            d2 = None
            if layer._opt_name == "CEBO" and w.pack_prey2 >= 0 and layer._s2.size > 0:
                p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
                d2 = round(float(np.linalg.norm(w.wolves[layer._s2].mean(axis=0) - p2)), 1)
            aborts.append({"t": int(w.step_count), "ticks_tramo": info["ticks"],
                           "released": bool(w.wolf_decoy_released),
                           "staged": st, "bearing_ok": (bool(layer._bearing_ok(w, layer._s2))
                                                        if layer._opt_name == "CEBO" else None),
                           "d_asalto_presa2": d2, "accion": info["option"]})
    n_ab = len(aborts)
    punto = sum(1 for x in aborts if x["released"] or x["staged"])
    return {"seed": seed, "kind": kind, "sev": int(w.n_depredadas), "n_aborts": n_ab,
            "n_shows": len(shows), "t_shows": shows[:5],
            "aborts_released": sum(1 for x in aborts if x["released"]),
            "aborts_staged_noshow": sum(1 for x in aborts if x["staged"]),
            "aborts_a_punto": punto, "frac_a_punto": round(punto / n_ab, 3) if n_ab else None,
            "d_asalto_presa2_mediana": (round(float(np.median([x["d_asalto_presa2"] for x in aborts
                                                               if x["d_asalto_presa2"] is not None])), 1)
                                        if any(x["d_asalto_presa2"] is not None for x in aborts) else None),
            "ticks_tramo_mediana": (float(np.median([x["ticks_tramo"] for x in aborts])) if aborts else None),
            "muestra_aborts": aborts[:6]}


def run_arm(job):
    policy, seed, kind = job
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    obs, info = env.reset_to(seed, kind)
    w, layer = env.world, env._layer
    est = {"noshow": 0, "max_noshow": 0, "shows": [], "bear_fail": 0}

    def tick(w_, c_, l_):
        st = staged_now(w_, l_)
        if st:
            est["noshow"] += 1
            est["max_noshow"] = max(est["max_noshow"], est["noshow"])
            if not l_._bearing_ok(w_, l_._s2):
                est["bear_fail"] += 1

    env.on_tick = tick
    pol = policy_fn(policy)
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
        for ev in layer.pop_events():
            if ev["ev"] == "SHOW_START":
                est["shows"].append(int(ev["t"]))
                est["noshow"] = 0                      # tras el show, el contador es de la SIGUIENTE espera
    return {"policy": policy, "seed": seed, "kind": kind, "sev": int(w.n_depredadas),
            "staged_noshow_max": est["max_noshow"], "bearing_fail_ticks": est["bear_fail"],
            "n_shows": len(est["shows"]), "t_show1": est["shows"][0] if est["shows"] else None}


if __name__ == "__main__":
    o = json.load(open("/data/hrl_m1/eval/oracle_v36__reactive.json"))["episodes"]
    oS = [(("oracle",) + (e["seed"], e["kind"])) for e in o if not e["two_front"] and e["n_wolves"] >= 3][:20]
    sp = json.load(open("/data/hrl_m1/eval/spawn_v36__reactive.json"))["episodes"]
    spG = [(("spawn",) + (e["seed"], e["kind"])) for e in sp if e["two_front"]][:10]
    with mp.get_context("fork").Pool(15) as pool:
        arms = pool.map(run_arm, oS + spG, chunksize=1)
    mgr = [run_manager(s, k) for s, k in MGR_EPS]
    stall = [a for a in arms if a["staged_noshow_max"] >= 400]
    res = {"manager": mgr,
           "arms_resumen": {"n": len(arms),
                            "staged_noshow_max_global": max(a["staged_noshow_max"] for a in arms),
                            "episodios_stall_400": len(stall),
                            "stalls": stall},
           "arms": arms,
           "VEREDICTO_GUION": ("SE ATASCA SOLO - PARAR" if stall else "el show se dispara con normalidad")}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    frac = [m["frac_a_punto"] for m in mgr if m["frac_a_punto"] is not None]
    print(json.dumps({"manager_frac_a_punto": frac,
                      "manager": [{k: m[k] for k in ("seed", "kind", "sev", "n_aborts", "n_shows",
                                                     "aborts_released", "aborts_staged_noshow", "frac_a_punto")}
                                  for m in mgr],
                      "arms": res["arms_resumen"] | {"stalls": len(stall)},
                      "VEREDICTO": res["VEREDICTO_GUION"]}, indent=1, ensure_ascii=False))
    print("VERIF0_OK")
