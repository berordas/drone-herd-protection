"""canal_fases.py — Análisis adicional del STOP-M1'' (orden del dueño; SOLO LECTURA, no toca el run):
clasificador de FASE POR MUERTE en las evals del STOP. En el tick de cada muerte, fase de la
defensa: PATRULLA / VENTANA DE INVESTIGACIÓN (algún ACTIVE investigando, pre-ESCOLTA) /
ESCOLTA-BARRERA. Etiquetas: CANAL B = muerte en patrulla/investigación ANTES de ESCOLTA (el
mecanismo del seed 77) · CANAL A = muerte con escolta activa. Tabla por política con % de
muertes por fase y KNC por fase + reparto A/B. Determinista (reset_to, mismas 100×2 semillas del
metro).

ADENDA (dueño, 2026-08-20): métrica DESPERTAR TARDÍO — por episodio, en el tick del latch de
ESCOLTA: d_min(lobo→rebaño) y nº de lobos ya a <100 NO detectados previamente (auditor de
patrulla). DESPERTAR TARDÍO := latch con >=1 entrada no detectada previa (mecanismo seed 77).
Tabla por política: episodios afectados, muertes en ellos, lag (t_latch − t_1ª_entrada_no_det).

Uso: python3 canal_fases.py <politica> <oponente> <out.json>
    politica ∈ masa | spawn | oracle | manager:<ckpt.zip>"""
import json
import multiprocessing as mp
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE
from hrl.behavior_checks import EpisodeAudit, PatrolCoverageTracker
from hrl.eval_manager import policy_fn
from hrl.manager_env import ManagerEnv

POLICY = sys.argv[1]
OPP = sys.argv[2]
OUT = sys.argv[3]


def run(job):
    s, kind = job
    env = ManagerEnv(kinds=(kind,), seed=0, opponent=OPP)
    obs, info = env.reset_to(s, kind)
    w, layer = env.world, env._layer
    audit = EpisodeAudit(w, env._coord, wolf_controller=layer, meta={"seed": s, "kind": kind},
                         decoy_indices=layer.decoy_indices, assault_indices=layer.assault_indices,
                         option_name=POLICY)
    patrol = PatrolCoverageTracker(w)            # entradas de lobo no detectadas (pre-ESCOLTA)
    estado = {"t_esc": None, "inv": [], "d_min_latch": None}

    def on_b(w_, c_, l_):
        audit.on_boundary()
        patrol.on_boundary()
        t = int(w_.step_count)
        if estado["t_esc"] is None:
            if w_.phase == "ESCOLTA":
                estado["t_esc"] = t
                herd = PatrolCoverageTracker._herd_pts(w_)
                if w_.n_wolves > 0 and herd.shape[0] > 0:
                    estado["d_min_latch"] = round(float(np.linalg.norm(
                        w_.wolves[:, None, :] - herd[None, :, :], axis=2).min()), 1)
            elif bool((w_.drone_investigating & (w_.drone_state == ACTIVE)).any()):
                estado["inv"].append(t)

    env.on_boundary = on_b
    env.on_tick = lambda w_, c_, l_: audit.after_step()
    pol = policy_fn(POLICY)
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first))
        first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    rec = audit.finalize()
    inv = set(estado["inv"])
    t_esc = estado["t_esc"]
    deaths = []
    for d in rec["deaths"]:
        t = int(d["t"])
        if t_esc is not None and t >= t_esc:
            fase = "ESCOLTA-BARRERA"
        elif (t in inv) or (t - 1 in inv):
            fase = "VENTANA_INVESTIGACION"
        else:
            fase = "PATRULLA"
        deaths.append({"t": t, "fase": fase,
                       "canal": ("A" if fase == "ESCOLTA-BARRERA" else "B"),
                       "knc": not d["killer_confirmado"]})
    # DESPERTAR TARDÍO (adenda): entradas no detectadas previas al latch (el auditor solo
    # registra en patrulla => todas son pre-latch por construcción).
    no_det = [e for e in patrol.entradas if not e["detectado"]]
    tardio = (t_esc is not None and len(no_det) >= 1)
    return {"seed": s, "kind": kind, "sev": rec["sev"], "t_escolta": t_esc,
            "critical": rec["critical"], "violations": rec["violations"],
            "gotera": rec["gotera_cruces"], "knc_total": sum(1 for d in rec["deaths"] if not d["killer_confirmado"]),
            "d_min_latch": estado["d_min_latch"],
            "entradas_no_detectadas": len(no_det),
            "despertar_tardio": tardio,
            "lag_despertar": (t_esc - min(e["t"] for e in no_det) if tardio else None),
            "deaths": deaths, "canal_B": sum(1 for d in deaths if d["canal"] == "B")}


if __name__ == "__main__":
    jobs = [(s, k) for k in ("lobos", "mixto") for s in range(100)]
    ctx = mp.get_context("spawn" if (OPP != "reactive" or POLICY.startswith("manager")) else "fork")
    with ctx.Pool(20) as pool:
        recs = pool.map(run, jobs, chunksize=2)
    all_d = [d for r in recs for d in r["deaths"]]
    fases = ("PATRULLA", "VENTANA_INVESTIGACION", "ESCOLTA-BARRERA")
    por_fase = {}
    for f in fases:
        ds = [d for d in all_d if d["fase"] == f]
        por_fase[f] = {"n": len(ds), "frac": (len(ds) / len(all_d) if all_d else None),
                       "knc_frac": (float(np.mean([d["knc"] for d in ds])) if ds else None)}
    nB = sum(1 for d in all_d if d["canal"] == "B")
    tardios = [r for r in recs if r["despertar_tardio"]]
    res = {"policy": POLICY, "opponent": OPP, "n_eps": len(recs), "n_deaths": len(all_d),
           "auditoria": {"critical": sum(1 for r in recs if r["critical"]),
                          "violations": sum(1 for r in recs if r["violations"]),
                          "gotera_total": sum(r["gotera"] for r in recs),
                          "knc_frac": (sum(r["knc_total"] for r in recs) / len(all_d) if all_d else None)},
           "por_fase": por_fase,
           "canal_A": len(all_d) - nB, "canal_B": nB,
           "frac_canal_B": (nB / len(all_d) if all_d else None),
           "despertar_tardio": {
               "episodios": len(tardios),
               "muertes_en_ellos": sum(r["sev"] for r in tardios),
               "muertes_totales": sum(r["sev"] for r in recs),
               "lag_medio": (float(np.mean([r["lag_despertar"] for r in tardios])) if tardios else None),
               "lag_max": (max(r["lag_despertar"] for r in tardios) if tardios else None),
               "d_min_latch_medio_tardios": (float(np.mean([r["d_min_latch"] for r in tardios
                                                            if r["d_min_latch"] is not None]))
                                             if tardios else None),
               "d_min_latch_medio_resto": (float(np.mean([r["d_min_latch"] for r in recs
                                                          if not r["despertar_tardio"]
                                                          and r["d_min_latch"] is not None]))
                                           if any(not r["despertar_tardio"] and r["d_min_latch"] is not None
                                                  for r in recs) else None),
               "casos": [(r["seed"], r["kind"], r["entradas_no_detectadas"], r["lag_despertar"],
                          r["sev"]) for r in sorted(tardios, key=lambda x: -x["sev"])[:10]]},
           "eps_con_canal_B": sorted([(r["seed"], r["kind"], r["canal_B"], r["sev"])
                                      for r in recs if r["canal_B"] > 0],
                                     key=lambda x: -x[2])[:12],
           "episodes": recs}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "episodes"}, indent=1,
                     ensure_ascii=False))
