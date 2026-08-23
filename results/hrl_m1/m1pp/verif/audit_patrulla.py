"""Encargo 1c/1d — pasada retroactiva SOLO-LECTURA del auditor de patrulla sobre los corpus:
  reactiva   Reactive-estática 100/tipo (= metro v3.6 y brazo estática del A/B; mismas semillas)
  orbita     el brazo ÓRBITA del A/B (contraste; patrol_omega=0.02)
  sanity     sanity E0.1 v3.6 (50 semillas G/n>=3 × {CEBO_keep, MASA}, capa K) + 1d: sobrecoste
             del rodeo del señuelo — t(inicio→posición de merodeo) REAL vs t teórico en línea
             recta a 4 m/s (dist(spawn→posición alcanzada) / 0.4 ticks)
  floor      suelo residual (δ≡0) estática · run02e/run09e con modelo (OMP_NUM_THREADS=1)
Salida: /data/hrl_m1/m1pp/audit_patrulla_<modo>.json. Determinista (mismas semillas)."""
import os
os.environ["OMP_NUM_THREADS"] = "1"
import json
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world, KINDS
from coordinators import ReactiveCoordinator
from world import ACTIVE
from hrl.behavior_checks import PatrolCoverageTracker
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

_M = {}


def make_coord(w, modo):
    if modo == "orbita":
        return ReactiveCoordinator(w, patrol_omega=0.02)
    if modo in ("reactiva", "sanity"):
        return ReactiveCoordinator(w)
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    path = {"floor": None, "run02e": "/data/drones/run02_v34/model.zip",
            "run09e": "/data/drones/run09_v35/model.zip"}[modo]
    model = None
    if path:
        if path not in _M:
            import torch
            torch.set_num_threads(1)
            from stable_baselines3 import PPO
            _M[path] = PPO.load(path, device="cpu")
        model = _M[path]
    return ResidualDroneCoordinator(w, model=model)


def run_plain(job):
    modo, seed, kind = job
    w = build_world(seed, kind)
    coord = make_coord(w, modo)
    w.reset()
    tr = PatrolCoverageTracker(w)
    while True:
        tr.on_boundary()
        _o, _r, t, trc, _i = w.step(coord.act(w.get_observation()))
        if t or trc:
            break
    rec = tr.finalize()
    rec.update({"seed": seed, "kind": kind, "sev": int(w.n_depredadas), "steps": int(w.step_count)})
    rec.pop("entradas", None)
    return rec


def run_sanity(job):
    _modo, seed, arm = job
    opt = ("MASA", {}) if arm == "MASA" else ("CEBO", {"membership": "keep", "hold": 50.0})
    layer = WolfOptionLayer(option=opt)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    tr = PatrolCoverageTracker(w)
    decoy_p0 = w.wolves[0].copy() if arm != "MASA" and w.n_wolves > 0 else None
    hold_edge = float(w.decoy_hold_dist) + 20.0            # borde de la zona de merodeo (130+banda)
    t_mer, pos_mer = None, None
    while True:
        tr.on_boundary()
        if decoy_p0 is not None and t_mer is None:
            act = w.drones[w.drone_state == ACTIVE]
            if act.shape[0] > 0:
                d = float(np.linalg.norm(act - w.wolves[0], axis=1).min())
                if d <= hold_edge:
                    t_mer, pos_mer = int(w.step_count), w.wolves[0].copy()
        _o, _r, t, trc, _i = w.step(coord.act(w.get_observation()))
        if t or trc:
            break
    rec = tr.finalize()
    rec.pop("entradas", None)
    rec.update({"seed": seed, "kind": "lobos", "arm": arm, "sev": int(w.n_depredadas),
                "steps": int(w.step_count)})
    if decoy_p0 is not None:
        if t_mer is not None:
            dist = float(np.linalg.norm(pos_mer - decoy_p0))
            t_teo = dist / (w.wolf_speed * w.dt)
            rec["decoy"] = {"t_merodeo": t_mer, "dist_recta": round(dist, 1),
                            "t_teorico": round(t_teo, 1), "sobrecoste": round(t_mer - t_teo, 1)}
        else:
            rec["decoy"] = {"t_merodeo": None}
    return rec


def seeds_G(count):
    out, s = [], 0
    while len(out) < count and s < 4000:
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 2 and w.n_wolves >= 3:
            out.append(s)
        s += 1
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    modo = sys.argv[1]
    if modo == "sanity":
        ss = seeds_G(50)
        jobs = [("sanity", s, arm) for arm in ("CEBO_keep", "MASA") for s in ss]
        fn = run_sanity
    else:
        jobs = [(modo, s, k) for k in KINDS for s in range(100)]
        fn = run_plain
    ctx = mp.get_context("spawn" if modo in ("run02e", "run09e") else "fork")
    with ctx.Pool(20) as pool:
        recs = pool.map(fn, jobs, chunksize=2)

    def agg(rs):
        tp = sum(r["ticks_patrulla"] for r in rs)
        return {"n_eps": len(rs), "ticks_patrulla": tp,
                "frac_aviso": (sum(r["ticks_aviso"] for r in rs) / tp if tp else None),
                "frac_violacion": (sum(r["ticks_violacion"] for r in rs) / tp if tp else None),
                "D_max": max((r["D_max"] for r in rs), default=None),
                "R_media": (float(np.mean([r["R_media"] for r in rs if r["R_media"] is not None]))
                            if any(r["R_media"] is not None for r in rs) else None),
                "R_max": max((r["R_max"] for r in rs), default=None),
                "R_zonas_frac": {z: sum(r["R_zonas"][z] for r in rs) / tp if tp else None
                                 for z in ("lt71", "z71_142", "gt142")},
                "eps_con_violacion": sum(1 for r in rs if r["ticks_violacion"] > 0),
                "entradas_no_detectadas": sum(r["entradas_no_detectadas"] for r in rs),
                "end_por_arco_violacion": sum(r["entradas_no_detectadas_por_arco_violacion"] for r in rs),
                "end_por_arco_aviso": sum(r["entradas_no_detectadas_por_arco_aviso"] for r in rs)}

    out = {"modo": modo, "total": agg(recs)}
    if modo == "sanity":
        for arm in ("CEBO_keep", "MASA"):
            out[arm] = agg([r for r in recs if r["arm"] == arm])
        dec = [r["decoy"] for r in recs if r.get("decoy") and r["decoy"].get("t_merodeo") is not None]
        if dec:
            sob = [d["sobrecoste"] for d in dec]
            out["decoy_1d"] = {"n": len(dec), "no_alcanzado": sum(1 for r in recs if r.get("decoy")
                                                                  and r["decoy"].get("t_merodeo") is None),
                               "t_merodeo_medio": float(np.mean([d["t_merodeo"] for d in dec])),
                               "t_teorico_medio": float(np.mean([d["t_teorico"] for d in dec])),
                               "sobrecoste_medio": float(np.mean(sob)),
                               "sobrecoste_p50": float(np.percentile(sob, 50)),
                               "sobrecoste_p90": float(np.percentile(sob, 90)),
                               "sobrecoste_max": float(np.max(sob))}
    else:
        for k in KINDS:
            out[k] = agg([r for r in recs if r["kind"] == k])
    out["episodes"] = recs
    json.dump(out, open(f"/data/hrl_m1/m1pp/audit_patrulla_{modo}.json", "w"),
              indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "episodes"}, indent=1,
                     ensure_ascii=False)[:2400])
