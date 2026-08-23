"""tabla_d2_r1.py — TABLA de la RÉPLICA D2 (seed 1) + barra de error CONJUNTA (RUN-D2 ∪ réplica):
deltas EMPAREJADOS por semilla contra los listones de E0.4, IC bootstrap 10k. Predicciones del
PREREGISTRO RÉPLICA D2 adjudicadas aquí (no se persiguen)."""
import json
import numpy as np
B = "/data/hrl_d2"
rng = np.random.default_rng(20260824)
ATKS = ("natural", "cebo2f", "manager")
RUNS = (("dronemgr", "RUN-D2 (seed 0)"), ("dronemgr_r1", "réplica (seed 1)"))


def load(d, a):
    r = json.load(open(f"{B}/e04_{d}__{a}.json"))
    return r, {(e["seed"], e["kind"]): e for e in r["episodes"]}


def ci(d):
    d = np.asarray(d, float)
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    return (float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


out = ["# TABLA RÉPLICA D2 (seed 1) — 100 semillas emparejadas por celda; IC bootstrap 10k", "",
       "| defensa \\ atacante | natural | cebo 2f | manager lobo | PENETRADO (nat/cebo/mgr) | cambios/ep | stalls |",
       "|---|---|---|---|---|---|---|"]
R = {}
for d in ("reactive", "proporcional", "dronemgr", "dronemgr_r1"):
    cells, pens, camb, st = [], [], [], []
    for a in ATKS:
        r, e = load(d, a)
        R[(d, a)] = (r, e)
        cells.append(f"{r['sev']:.2f}"); pens.append(f"{r['penetrado_medio']:.0f}")
        if r.get("cambios_particion_media") is not None:
            camb.append(r["cambios_particion_media"])
        st.append(sum((x.get("stalls_def") or 0) for x in r["episodes"]))
    out.append(f"| {d} | {cells[0]} | {cells[1]} | {cells[2]} | {'/'.join(pens)} | "
               f"{(round(float(np.mean(camb)), 2) if camb else '—')} | {sum(st)} |")
out.append("")
res = {}
for a in ATKS:
    for ref in ("reactive", "proporcional"):
        _, er = R[(ref, a)]
        ds = {}
        for d, lab in RUNS:
            _, em = R[(d, a)]
            ds[d] = np.array([em[k]["sev"] - er[k]["sev"] for k in er if k in em], float)
            out.append(f"Δ({lab} − {ref}) vs {a}: {fmt(ci(ds[d]))}")
        both = np.concatenate([ds["dronemgr"], ds["dronemgr_r1"]])
        t = ci(both); res[f"{a}|{ref}"] = t
        out.append(f"Δ(AMBOS aprendices − {ref}) vs {a} (200 pares, 2 seeds; SOLO barra de error): {fmt(t)}")
    r, _ = R[("dronemgr_r1", a)]
    c = r["carrera"]
    out.append(f"  réplica vs {a}: KNC {r['knc_frac']} · jugada atacante {r['jugada_completa_frac']} · "
               f"gana_guardia {c['gana_guardia_frac']} (n {c['n_carreras']}) · latencia {c['latencia_media']} · "
               f"reasignaciones {c['reasignaciones_media']} · PENETRADO 2f {r.get('penetrado_2f_medio', 'n/d')}")
    out.append("")
# Predicciones del pre-registro de la réplica
s = json.load(open(f"{B}/D2_r1/summary.json"))["eval_final"]
p1 = s["P_guardia_2clusters"] >= 0.90 and s["P_a_2clusters"].get("3-1", 0) <= 0.10
p2 = res["cebo2f|proporcional"][0] > 0
out += ["## Predicciones del PREREGISTRO RÉPLICA D2",
        f"1. Estructura se reproduce (P(guardia|2cl) ≥ 0.90 y P(3-1|2cl) ≤ 0.10): P(guardia|2cl)={s['P_guardia_2clusters']} "
        f"P(a|2cl)={s['P_a_2clusters']} P(a|1cl)={s['P_a_1cluster']} ⇒ {'CUMPLIDA' if p1 else 'FALLA'}",
        f"2. Δ(réplica − proporcional) vs cebo-2f positivo y solapa con [+0.01, +0.37]: ver arriba; conjunto {fmt(res['cebo2f|proporcional'])} ⇒ {'CUMPLIDA' if p2 else 'FALLA'} (solape: adjudicar a mano con el IC de la réplica)",
        "3. Δ vs Reactive con IC excluyendo 0 en las 3 celdas: " + ", ".join(f"{a} {fmt(res[f'{a}|reactive'])}" for a in ATKS),
        "4. PENETRADO ≥ proporcional en natural y cebo-2f: " + ", ".join(
            f"{a} {R[('dronemgr_r1', a)][0]['penetrado_medio']:.0f} vs {R[('proporcional', a)][0]['penetrado_medio']:.0f}" for a in ATKS),
        f"ligera final réplica: sev {s['sev_media']} stalls {s['stalls_total']} cambios/ep {s['cambios_por_ep']} pen {s['penetrado_medio']}"]
open(f"{B}/TABLA_D2_R1.md", "w").write("\n".join(out) + "\n")
print("\n".join(out)); print("TABLA_D2_R1_OK")
