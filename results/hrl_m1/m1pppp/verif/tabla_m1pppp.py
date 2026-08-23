"""tabla_m1pppp.py — TABLA del STOP-M1'''' contra los labels *_v37 (deltas EMPAREJADOS + censura
+ aborts/stalls). Escribe /data/hrl_m1/m1pppp/TABLA_M1PPPP.md."""
import json
import numpy as np

E = "/data/hrl_m1/eval"
rng = np.random.default_rng(20260821)


def load(label, opp):
    d = json.load(open(f"{E}/{label}__{opp}.json"))
    return d["resumen"], {(e["seed"], e["kind"]): e for e in d["episodes"]}


def ci(d):
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    return (float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def fmt(t):
    return f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


POLS = [("B_masa", "masa_v37"), ("B_spawn", "spawn_v37"), ("B_oracle", "oracle_v37"),
        ("manager 60k", "manager_M1pppp_60k"), ("manager final", "manager_M1pppp_final")]
rows, eps = {}, {}
for name, lab in POLS:
    for opp in ("reactive", "run02", "run09"):
        try:
            r, e = load(lab, opp)
            rows[(name, opp)] = r
            eps[(name, opp)] = e
        except FileNotFoundError:
            pass

orc = eps[("B_oracle", "reactive")]
spw = eps[("B_spawn", "reactive")]
out = ["# TABLA M1'''' (100 semillas emparejadas; IC bootstrap 10k; sev SIEMPRE sin coste)", "",
       "| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_oracle | jugada completa | aborts/ep | stalls |",
       "|---|---|---|---|---|---|---|---|"]
for name, lab in POLS:
    cells = []
    for opp in ("reactive", "run02", "run09"):
        r = rows.get((name, opp))
        cells.append(f"{r['sev'][0]:.2f}" if r else "—")
    e = eps.get((name, "reactive"))
    if e and name != "B_oracle":
        d = np.array([e[k]["sev"] - orc[k]["sev"] for k in orc if k in e], float)
        dvo = fmt(ci(d))
    else:
        dvo = "—"
    r0 = rows.get((name, "reactive"), {})
    cen = r0.get("censura") or {}
    out.append(f"| {name} | {cells[0]} | {cells[1]} | {cells[2]} | {dvo} | "
               f"{cen.get('jugada_completa_frac', '—')} | {r0.get('aborts_por_ep', 0):.2f} | "
               f"{r0.get('stalls_total', '—')} |")
mgr = eps.get(("manager final", "reactive"))
if mgr:
    d_sp = np.array([mgr[k]["sev"] - spw[k]["sev"] for k in spw if k in mgr], float)
    d_or = np.array([mgr[k]["sev"] - orc[k]["sev"] for k in orc if k in mgr], float)
    out += ["", f"Δ(manager − B_spawn) vs reactive: {fmt(ci(d_sp))}",
            f"Δ(manager − B_oracle) vs reactive: {fmt(ci(d_or))}"]
    for opp in ("run02", "run09"):
        m2 = eps.get(("manager final", opp))
        o2 = eps.get(("B_oracle", opp))
        if m2 and o2:
            gm = np.array([m2[k]["sev"] - mgr[k]["sev"] for k in mgr if k in m2], float)
            go = np.array([o2[k]["sev"] - orc[k]["sev"] for k in orc if k in o2], float)
            out.append(f"gap {opp}−reactive: manager {fmt(ci(gm))} · oráculo {fmt(ci(go))}")
    rmgr = rows[("manager final", "reactive")]
    out += ["", f"Manager censura: {json.dumps(rmgr.get('censura'), ensure_ascii=False)}",
            f"P(a|G) 1ª: {rmgr['P_a_first'].get('G')}", f"P(a|S) 1ª: {rmgr['P_a_first'].get('S')}",
            f"P(cebo|G,n≥3): {rmgr.get('P_cebo_G_n3')} · eventos: {rmgr.get('eventos')}",
            f"caza/ep: {rmgr.get('caza_por_ep')}"]
open("/data/hrl_m1/m1pppp/TABLA_M1PPPP.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
print("TABLA_OK")
