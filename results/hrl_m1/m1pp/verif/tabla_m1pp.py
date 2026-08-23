"""TABLA-ESCALERA del STOP-M1'' (etiquetas *_v36 + manager_M1pp_*): sev por oponente, Δ emparejado
vs B_masa/B_spawn/B_oracle (reactive), gaps de transferencia (run02−reactive, run09−reactive)."""
import json
import pathlib

import numpy as np

E = pathlib.Path("/data/hrl_m1/eval")
LABELS = ["masa_v36", "spawn_v36", "oracle_v36", "manager_M1pp_60k", "manager_M1pp_final"]
OPPS = ["reactive", "run02", "run09"]
rng = np.random.default_rng(20260820)


def load(l, o):
    p = E / f"{l}__{o}.json"
    if not p.exists():
        return None
    d = json.load(open(p))
    return {(e["seed"], e["kind"]): e["sev"] for e in d["episodes"]}, d["resumen"]


def ci(d):
    d = np.asarray(d, float)
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    return f"{d.mean():+.2f} [{np.percentile(b, 2.5):+.2f}, {np.percentile(b, 97.5):+.2f}]"


data = {(l, o): load(l, o) for l in LABELS for o in OPPS}
L = ["# TABLA-ESCALERA STOP-M1'' (100 semillas emparejadas × defensas; capa K, v3.6)", "",
     "| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_masa | Δ vs B_spawn | Δ vs B_oracle | gap run02 | gap run09 |",
     "|---|---|---|---|---|---|---|---|---|"]
for l in LABELS:
    row = [l]
    for o in OPPS:
        d = data[(l, o)]
        row.append("—" if d is None else f"{np.mean(list(d[0].values())):.2f}")
    re = data[(l, "reactive")]
    for ref in ("masa_v36", "spawn_v36", "oracle_v36"):
        rf = data[(ref, "reactive")]
        if re and rf and l != ref:
            ks = sorted(set(re[0]) & set(rf[0]))
            row.append(ci([re[0][k] - rf[0][k] for k in ks]))
        else:
            row.append("—")
    for o in ("run02", "run09"):
        d = data[(l, o)]
        if re and d:
            ks = sorted(set(re[0]) & set(d[0]))
            row.append(ci([d[0][k] - re[0][k] for k in ks]))
        else:
            row.append("—")
    L.append("| " + " | ".join(row) + " |")
L += ["", "## P(1ª acción | estrato) y caza/ep — vs Reactive", ""]
for l in LABELS:
    d = data[(l, "reactive")]
    if not d:
        continue
    r = d[1]
    L.append(f"### {l}")
    L.append(f"P(a|G) {r['P_a_first'].get('G')} · P(a|S) {r['P_a_first'].get('S')} · "
             f"P(cebo|G,n≥3) {r['P_cebo_G_n3']} · dec/ep {r['decisiones_media']:.1f} · "
             f"PENETRADO {r['penetrado_ticks_media']:.0f}")
    cz = r.get("caza_por_ep")
    if cz:
        L.append("caza/ep: " + " · ".join(f"{k} {v:.2f}" for k, v in cz.items()))
    L.append("")
pathlib.Path("/data/hrl_m1/m1pp/TABLA_M1PP.md").write_text("\n".join(L) + "\n")
print("\n".join(L[:14]))
