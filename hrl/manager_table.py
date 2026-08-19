"""hrl/manager_table.py — TABLA-ESCALERA del STOP-M1 desde los JSON de eval_manager: políticas ×
defensas, IC emparejados (Δ vs B_masa y vs B_oracle, bootstrap 10k sobre diferencias por
episodio), gap de transferencia Δsev(Reactive→run09) por política, heatmap P(a | G/S, n).
Uso: python3 hrl/manager_table.py  -> /data/hrl_m1/eval/TABLA.md"""
from __future__ import annotations

import json
import pathlib

import numpy as np

OUT = pathlib.Path("/data/hrl_m1/eval")


def boot_ci(vals, n_boot=10_000, seed=20_260_819):
    v = np.asarray(vals, dtype=float)
    if v.size == 0:
        return None
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, v.size, size=(n_boot, v.size))].mean(axis=1)
    return float(v.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def fmt(ci):
    return "—" if ci is None else f"{ci[0]:+.2f} [{ci[1]:+.2f}, {ci[2]:+.2f}]"


def main():
    files = sorted(OUT.glob("*__*.json"))
    data = {}
    for f in files:
        d = json.load(open(f))
        label, opp = f.stem.rsplit("__", 1)
        data[(label, opp)] = d
    labels = sorted({l for l, _ in data})
    opps = [o for o in ("reactive", "run02", "run09") if any(o == op for _, op in data)]
    L = ["# TABLA-ESCALERA del manager (100 semillas emparejadas × defensas)", "",
         "| política | " + " | ".join(f"sev vs {o} [IC]" for o in opps) + " | Δ vs B_masa (Reactive) | Δ vs B_oracle (Reactive) | gap Reactive→run09 |",
         "|---|" + "---|" * (len(opps) + 3)]
    by_ep = {}
    for (l, o), d in data.items():
        by_ep[(l, o)] = {(e["seed"], e["kind"]): e["sev"] for e in d["episodes"]}
    for l in labels:
        cells = []
        for o in opps:
            d = data.get((l, o))
            cells.append("—" if d is None else f"{d['resumen']['sev'][0]:.2f} [{d['resumen']['sev'][1]:.2f}, {d['resumen']['sev'][2]:.2f}]")

        def delta(ref):
            a, b = by_ep.get((l, "reactive")), by_ep.get((ref, "reactive"))
            if not a or not b:
                return None
            keys = sorted(set(a) & set(b))
            return boot_ci([a[k] - b[k] for k in keys])
        a, b = by_ep.get((l, "reactive")), by_ep.get((l, "run09"))
        gap = None
        if a and b:
            keys = sorted(set(a) & set(b))
            gap = boot_ci([b[k] - a[k] for k in keys])
        L.append(f"| {l} | " + " | ".join(cells) + f" | {fmt(delta('masa'))} | {fmt(delta('oracle'))} | {fmt(gap)} |")
    L += ["", "## Heatmap P(primera acción | estrato, n) — vs Reactive", ""]
    for l in labels:
        d = data.get((l, "reactive"))
        if not d:
            continue
        L.append(f"### {l}")
        L.append("| clave | " + " | ".join(["MASA", "CEBO_keep", "CEBO_d90", "CEBO_d180"]) + " |")
        L.append("|---|---|---|---|---|")
        for k, v in d["resumen"]["P_a_first"].items():
            if v:
                L.append(f"| {k} | " + " | ".join(f"{v[n]:.2f}" for n in ["MASA", "CEBO_keep", "CEBO_d90", "CEBO_d180"]) + " |")
        L.append(f"P(cebo | G, n≥3) = {d['resumen']['P_cebo_G_n3']} · decisiones/ep {d['resumen']['decisiones_media']:.2f} · "
                 f"PENETRADO ticks/ep {d['resumen']['penetrado_ticks_media']:.0f} · eventos {d['resumen']['eventos']}")
        cz = d["resumen"].get("caza_por_ep")
        if cz:
            L.append("caza/ep (K-bis): " + " · ".join(f"{k} {v:.2f}" for k, v in cz.items()))
        L.append("")
    (OUT / "TABLA.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
