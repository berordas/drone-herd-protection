"""tabla_d2.py — TABLA del STOP-D2: dronemgr vs listones E0.4 (mismas semillas => deltas
EMPAREJADOS con IC bootstrap) + compuertas del PREREGISTRO_D2."""
import json
import numpy as np
B = "/data/hrl_d2"
rng = np.random.default_rng(20260823)
DEFS = ("dummy", "reactive", "proporcional", "run09", "dronemgr")
ATKS = ("natural", "cebo2f", "manager")


def load(d, a):
    r = json.load(open(f"{B}/e04_{d}__{a}.json"))
    return r, {(e["seed"], e["kind"]): e for e in r["episodes"]}


def ci(d):
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    return (float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def fmt(t):
    return f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"


out = ["# TABLA D2 (100 semillas emparejadas por celda; IC bootstrap 10k)", "",
       "| defensa \\ atacante | natural | cebo 2f | manager lobo | PENETRADO (nat/cebo/mgr) | cambios/ep | stalls |",
       "|---|---|---|---|---|---|---|"]
R = {}
for d in DEFS:
    cells, pens, camb, st = [], [], [], []
    for a in ATKS:
        try:
            r, e = load(d, a)
        except FileNotFoundError:
            cells.append("—"); pens.append("—"); continue
        R[(d, a)] = (r, e)
        cells.append(f"{r['sev']:.2f}")
        pens.append(f"{r['penetrado_medio']:.0f}")
        if r.get("cambios_particion_media") is not None:
            camb.append(r["cambios_particion_media"])
        st.append(sum((x.get("stalls_def") or 0) for x in r["episodes"]))
    out.append(f"| {d} | {cells[0]} | {cells[1]} | {cells[2]} | {'/'.join(pens)} | "
               f"{(np.mean(camb) if camb else '—')} | {sum(st) if st else '—'} |")
out.append("")
for a in ATKS:
    if ("dronemgr", a) not in R:
        continue
    _, em = R[("dronemgr", a)]
    for ref in ("reactive", "proporcional"):
        _, er = R[(ref, a)]
        d = np.array([em[k]["sev"] - er[k]["sev"] for k in er if k in em], float)
        out.append(f"Δ(dronemgr − {ref}) vs {a}: {fmt(ci(d))}")
    r, _ = R[("dronemgr", a)]
    c = r["carrera"]
    out.append(f"  dronemgr vs {a}: KNC {r['knc_frac']} · jugada atacante {r['jugada_completa_frac']} · "
               f"gana_guardia {c['gana_guardia_frac']} (n {c['n_carreras']}) · latencia {c['latencia_media']} · "
               f"reasignaciones {c['reasignaciones_media']}")
open(f"{B}/TABLA_D2.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
print("TABLA_D2_OK")
