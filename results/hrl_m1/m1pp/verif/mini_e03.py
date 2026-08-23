"""MINI-E0.3 (plan M1prima2): verificación de n BAJOS antes de fijar la distribución de train.
- n=2 forzado (wolves_min=wolves_max=2): 60 pares CON ternero y 60 SIN, brazos MASA-forzado y
  CEBO_keep-forzado (capa K), vs Reactive-ESTÁTICA (v3.6) Y vs Dummy.
- n=1 forzado: 30 episodios (MASA; con 1 lobo el CEBO no tiene asalto) vs Dummy.
Criterio pre-registrado: severidad <0.05 en TODOS los brazos => n<=2 excluido del train con
evidencia. Si aparece caza => reportar y PARAR (decisión del dueño)."""
import sys, json
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import CONFIG_V2
from coordinators import DummyCoordinator, ReactiveCoordinator
from world import World
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

def build(seed, n_wolves):
    cfg = dict(CONFIG_V2); cfg["wolves_min"] = n_wolves; cfg["wolves_max"] = n_wolves
    return cfg

def run(seed, n_wolves, arm, defensa):
    cfg = build(seed, n_wolves)
    opt = ("MASA", {}) if arm == "MASA" else ("CEBO", {"membership": "keep", "hold": 50.0})
    layer = WolfOptionLayer(option=opt)
    w = World(seed=seed, episode_kind="lobos", wolf_controller=layer, **cfg)
    if defensa == "dummy":
        coord = DummyCoordinator(w.n_drones)
        w.reset()
        # el Dummy no refresca la capa: bucle manual con refresh en la frontera
        while True:
            layer.refresh(w)
            _o,_r,t,tr,_i = w.step(coord.act(w.get_observation()))
            if t or tr: break
    else:
        coord = SyncedReactiveCoordinator(w)
        w.reset()
        while True:
            _o,_r,t,tr,_i = w.step(coord.act(w.get_observation()))
            if t or tr: break
    return {"seed": seed, "sev": int(w.n_depredadas), "n_calves": int(w.n_calves),
            "status": w.status, "retargets": layer.n_retargets}

def seeds_by_calf(n_wolves, want_calf, count):
    out, s = [], 0
    while len(out) < count and s < 6000:
        cfg = build(s, n_wolves)
        w = World(seed=s, episode_kind="lobos", **cfg); w.reset()
        if (w.n_calves > 0) == want_calf:
            out.append(s)
        s += 1
    if len(out) < count:
        raise RuntimeError(f"solo {len(out)}/{count} semillas (ternero={want_calf})")
    return out

if __name__ == "__main__":
    import multiprocessing as mp
    res = {}
    jobs, keys = [], []
    for calf in (True, False):
        ss = seeds_by_calf(2, calf, 60)
        for defensa in ("reactive_estatica", "dummy"):
            for arm in ("MASA", "CEBO_keep"):
                for s in ss:
                    jobs.append((s, 2, arm, defensa))
                    keys.append(f"n2_{'ternero' if calf else 'sin_ternero'}_{defensa}_{arm}")
    ss1 = [s for s in range(500)][:0] or None
    # n=1: 30 episodios vs Dummy (MASA)
    s1 = []
    s = 0
    while len(s1) < 30:
        s1.append(s); s += 1
    for s_ in s1:
        jobs.append((s_, 1, "MASA", "dummy")); keys.append("n1_dummy_MASA")
    with mp.Pool(24) as pool:
        recs = pool.starmap(run, jobs, chunksize=4)
    agg = {}
    for k, r in zip(keys, recs):
        agg.setdefault(k, []).append(r)
    out = {}
    for k, rs in agg.items():
        sev = [r["sev"] for r in rs]
        out[k] = {"n": len(rs), "sev_media": float(np.mean(sev)), "sev_max": int(max(sev)),
                  "P_sev_pos": float(np.mean([s_ > 0 for s_ in sev])),
                  "retargets_ep": float(np.mean([r["retargets"] for r in rs]))}
    caza = {k: v for k, v in out.items() if v["sev_media"] >= 0.05}
    out["_veredicto"] = ("CAZA DETECTADA en: " + ", ".join(sorted(caza)) + " -> PARAR (decisión del dueño)"
                         if caza else "severidad <0.05 en TODOS los brazos -> n<=2 excluido del train")
    json.dump(out, open("/data/hrl_m1/m1pp/mini_e03.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
