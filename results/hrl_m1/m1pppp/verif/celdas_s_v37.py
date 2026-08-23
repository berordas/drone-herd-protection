"""Celdas S LIMPIAS (v3.7 + capa S1/S2 + tripwire + senuelo v2) — el paisaje S real por primera
vez (las celdas v3.6 estaban contaminadas: 9/20 interbloqueos). Brazos FORZADOS MASA / CEBO(d90)
/ CEBO(d180) (membership manager, hold 50), estrato S, n>=3, 100 semillas EMPAREJADAS, vs
Reactive-estatica. Con CENSURA (hitos + tasa jugada completa), distribucion de Δ CONSEGUIDO
(SHOW_START err_rumbo_deg), causas de fin de alineacion y STALLs (tripwire ~0 esperado)."""
import json, sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

ARMS = {"MASA": ("MASA", {}),
        "D90": ("CEBO", {"delta_deg": 90.0, "hold": 50.0}),
        "D180": ("CEBO", {"delta_deg": 180.0, "hold": 50.0})}
OUT = "/data/hrl_m1/m1pppp/celdas_s_v37.json"


def run(job):
    seed, arm = job
    layer = WolfOptionLayer(option=ARMS[arm])
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs = []
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if t or tr:
            break
    show = [e for e in evs if e["ev"] == "SHOW_START"]
    align = [e for e in evs if e["ev"] == "ALIGN_END"]
    return {"seed": seed, "arm": arm, "sev": int(w.n_depredadas), "n": int(w.n_wolves),
            "t_staged": layer.t_staged, "t_show": layer.t_show, "t_suelta": layer.t_suelta,
            "t_strike": layer.t_strike,
            "completa": bool(layer.t_show is not None and layer.t_suelta is not None),
            "stalls": int(layer.n_stalls),
            "err_show_deg": (show[0].get("err_rumbo_deg") if show else None),
            "staged_causa": (show[0].get("staged_causa") if show else None),
            "align_causa": (align[0]["causa"] if align else None),
            "align_err_deg": (align[0]["err_deg"] if align else None)}


def seeds_S(count):
    out, s = [], 0
    while len(out) < count and s < 8000:
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 1 and w.n_wolves >= 3:
            out.append(s)
        s += 1
    if len(out) < count:
        raise RuntimeError(f"solo {len(out)}")
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    ss = seeds_S(100)
    jobs = [(s, a) for a in ARMS for s in ss]
    with mp.Pool(24) as pool:
        recs = pool.map(run, jobs, chunksize=2)
    by = {a: [r for r in recs if r["arm"] == a] for a in ARMS}
    sev = {a: np.array([r["sev"] for r in by[a]], float) for a in ARMS}
    rng = np.random.default_rng(20260821)

    def ci(d):
        b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
        return [round(float(d.mean()), 3), round(float(np.percentile(b, 2.5)), 3),
                round(float(np.percentile(b, 97.5)), 3)]

    def cens(a):
        rs = by[a]
        errs = [r["err_show_deg"] for r in rs if r["err_show_deg"] is not None]
        return {"sev": ci(sev[a]),
                "jugada_completa_frac": round(float(np.mean([r["completa"] for r in rs])), 3),
                "con_show_frac": round(float(np.mean([r["t_show"] is not None for r in rs])), 3),
                "con_strike_frac": round(float(np.mean([r["t_strike"] is not None for r in rs])), 3),
                "stalls_total": int(sum(r["stalls"] for r in rs)),
                "align_causas": {c: sum(1 for r in rs if r["align_causa"] == c)
                                 for c in ("tolerancia", "sin_progreso", "t_max", None)},
                "staged_causas": {c: sum(1 for r in rs if r["staged_causa"] == c)
                                  for c in ("a_tiro", "meseta", None)},
                "err_show_deg": ({"mediana": round(float(np.median(errs)), 1),
                                  "p90": round(float(np.percentile(errs, 90)), 1)} if errs else None)}

    res = {"config": "v3.7 + capa S1/S2 + tripwire + senuelo v2; Reactive-estatica; S n>=3; 100 pares",
           "celdas": {a: cens(a) for a in ARMS},
           "delta_d90_masa": ci(sev["D90"] - sev["MASA"]),
           "delta_d180_masa": ci(sev["D180"] - sev["MASA"]),
           "delta_d180_d90": ci(sev["D180"] - sev["D90"]),
           "episodes": recs}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "episodes"}, indent=1, ensure_ascii=False))
    print("CELDAS_V37_OK")
