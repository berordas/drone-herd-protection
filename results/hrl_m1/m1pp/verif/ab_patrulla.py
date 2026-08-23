"""A/B Commit L (patrulla estática): 100 semillas/tipo EMPAREJADAS, Reactive clásica con
patrol_omega=0.02 (órbita, la de siempre) vs 0.0 (estática, config oficial nueva).
Δseveridad + MÉTRICAS DE RELEVO (t anuncio->hand-off, STRANDED/ep, relevos en patrulla vs
en barrera). Sin compuerta (decisión de diseño del dueño); si |Δsev|>0.3 -> AVISO con GIF
comparado. Renderiza el episodio con PEOR hand-off en órbita y su gemelo en estática."""
import sys, json, numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world, EVAL_SEEDS, KINDS
from coordinators import ReactiveCoordinator
from world import ACTIVE, INCOMING, STRANDED

def run(seed, kind, omega):
    w = build_world(seed, kind)
    c = ReactiveCoordinator(w, patrol_omega=omega)
    w.reset()
    hold_since = {}          # dron -> tick del ANUNCIO vigente
    handoffs = []            # dicts: t, espera, fase
    stranded_seen = set()
    prev_state = w.drone_state.copy(); prev_hold = w.drone_relief_hold.copy()
    while True:
        _o,_r,term,trunc,_i = w.step(c.act(w.get_observation()))
        st, hold = w.drone_state, w.drone_relief_hold
        for i in np.where(hold & ~prev_hold)[0]:
            hold_since[int(i)] = int(w.step_count)          # flanco de ANUNCIO
        for i in np.where((prev_state == INCOMING) & (st == ACTIVE))[0]:
            j = None                                        # el bajo: dejo hold en este tick
            for k in np.where(prev_hold & ~hold)[0]:
                j = int(k)
            if j is not None and j in hold_since:
                handoffs.append({"t": int(w.step_count), "espera": int(w.step_count - hold_since.pop(j)),
                                 "fase": w.phase})
        stranded_seen |= set(np.where(st == STRANDED)[0].tolist())
        prev_state = st.copy(); prev_hold = hold.copy()
        if term or trunc: break
    esperas = [h["espera"] for h in handoffs]
    return {"seed": seed, "kind": kind, "sev": int(w.n_depredadas), "status": w.status,
            "handoffs": len(handoffs), "espera_media": float(np.mean(esperas)) if esperas else None,
            "espera_max": int(max(esperas)) if esperas else None,
            "stranded": len(stranded_seen),
            "relevos_escolta": sum(1 for h in handoffs if h["fase"] == "ESCOLTA"),
            "relevos_patrulla": sum(1 for h in handoffs if h["fase"] != "ESCOLTA")}

if __name__ == "__main__":
    import multiprocessing as mp
    jobs = [(s, k, om) for om in (0.02, 0.0) for k in KINDS for s in EVAL_SEEDS]
    with mp.Pool(24) as pool:
        recs = pool.starmap(run, jobs, chunksize=4)
    out = {"orbita": [r for r, j in zip(recs, jobs) if j[2] == 0.02],
           "estatica": [r for r, j in zip(recs, jobs) if j[2] == 0.0]}
    def agg(rs, kind=None):
        rs = [r for r in rs if kind is None or r["kind"] == kind]
        eh = [r["espera_media"] for r in rs if r["espera_media"] is not None]
        return {"n": len(rs), "sev": float(np.mean([r["sev"] for r in rs])),
                "handoffs_ep": float(np.mean([r["handoffs"] for r in rs])),
                "espera_media": float(np.mean(eh)) if eh else None,
                "espera_max": max((r["espera_max"] or 0) for r in rs),
                "stranded_ep": float(np.mean([r["stranded"] for r in rs])),
                "relevos_escolta_ep": float(np.mean([r["relevos_escolta"] for r in rs])),
                "relevos_patrulla_ep": float(np.mean([r["relevos_patrulla"] for r in rs]))}
    res = {"jobs": len(jobs)}
    for lbl in ("orbita", "estatica"):
        res[lbl] = {"total": agg(out[lbl]), **{k: agg(out[lbl], k) for k in KINDS}}
    # Δ emparejado (misma semilla+tipo)
    o = {(r["seed"], r["kind"]): r["sev"] for r in out["orbita"]}
    e = {(r["seed"], r["kind"]): r["sev"] for r in out["estatica"]}
    d = np.array([e[k] - o[k] for k in sorted(o)])
    rng = np.random.default_rng(20260819)
    boots = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    res["delta_sev_estatica_menos_orbita"] = [float(d.mean()), float(np.percentile(boots, 2.5)),
                                              float(np.percentile(boots, 97.5))]
    # peor hand-off en órbita + gemelo
    worst = max(out["orbita"], key=lambda r: (r["espera_max"] or -1))
    res["peor_handoff_orbita"] = worst
    res["gemelo_estatica"] = e.get((worst["seed"], worst["kind"]))
    json.dump(res, open("/data/hrl_m1/m1pp/ab_patrulla.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "jobs"}, indent=1, ensure_ascii=False)[:2000])
