"""visionado_e01.py — Lote de visionado de E0.1/E0.2 (protocolo §2B + adenda §7): 8-12 GIFs
elegidos por criterio desde results.json, re-simulados deterministas con render_gif de
run_e0 (sidecar timeline.txt). Criterio: 2 pares de semillas con mayor |Δ| en cada signo
(G/CEBO_keep vs MASA vs Reactive: se renderiza el episodio CEBO_keep y su gemelo MASA del
par con mayor Δ+ y el par con mayor Δ−), primer LURE_COMMIT, 2 medianos, 2 ESCOLTA
prematura etiquetada, 1 sev>=5, y (si hay) violadores."""
import json
import pathlib
import sys

sys.path.insert(0, "/workspace")
from hrl import run_e0                                       # noqa: E402
sys.path.insert(0, "/data/hrl_e0/verif")
from relabel_premature_v35 import job_of                         # noqa: E402

BASE = pathlib.Path("/data/hrl_e0/v35/e01")
MAX = 12


def main():
    data = json.load(open(BASE / "results.json"))
    eps = data["episodes"]
    keep = [r for r in eps if r["arm"] == "cebo_keep_h50_reactive"]
    masa = {(r["seed"], r["kind"]): r for r in eps if r["arm"] == "masa_reactive"
            and len(r["grupos_spawn"]) == 2}
    pairs = [(r, masa[(r["seed"], r["kind"])]) for r in keep if (r["seed"], r["kind"]) in masa]
    pairs.sort(key=lambda p: p[0]["sev"] - p[1]["sev"])
    chosen = []                                              # (tag, rec)
    # 2 pares con mayor |Δ| en cada signo (4 pares = 8 GIFs) -> se limita a 1 par por signo
    # para dejar hueco al resto del criterio (12 GIFs máx: Pillow).
    for tag, (c, m) in (("dpos_max", pairs[-1]), ("dneg_max", pairs[0])):
        chosen += [(f"{tag}_cebo_keep", c), (f"{tag}_masa", m)]
    lure = [r for r in keep if r["clock"]["t_lure_commit"] is not None]
    if lure:
        chosen.append(("primer_lure", min(lure, key=lambda r: (r["kind"], r["seed"]))))
    med = sorted(keep, key=lambda r: (r["sev"], r["seed"]))
    chosen += [("mediano_a", med[len(med) // 2]), ("mediano_b", med[len(med) // 2 - 1])]
    prem = [r for r in eps if r.get("premature") and r["premature"]["quien"] != "desconocido"]
    prem.sort(key=lambda r: (r["premature"]["quien"], r["seed"]))
    seen_q = set()
    for r in prem:
        q = r["premature"]["quien"]
        if q not in seen_q:
            seen_q.add(q)
            chosen.append((f"escolta_prematura_{q}", r))
        if len(seen_q) >= 2:
            break
    sev5 = [r for r in keep if r["sev"] >= 5]
    if sev5:
        chosen.append(("sev5mas", max(sev5, key=lambda r: (r["sev"], -r["seed"]))))
    viol = [r for r in eps if r["critical"] or r["violations"]]
    for r in viol:
        chosen.append(("VIOLACION", r))
    chosen = chosen[:MAX]
    if len(sys.argv) > 1 and sys.argv[1] == "--only":      # Commit F: re-render de GIFs concretos
        want = [int(x) for x in sys.argv[2].split(",")]
        chosen = [chosen[i - 1] for i in want]
    out = []
    for tag, r in chosen:
        job = job_of(r)
        g = run_e0.render_gif(job, f"{tag}_{r['arm']}", BASE)
        print(tag, g["gif"], flush=True)
        out.append({"tag": tag, **g})
    if not (len(sys.argv) > 1 and sys.argv[1] == "--only"):
        (BASE / "visionado.json").write_text(json.dumps(out, indent=1))
    print("VISIONADO_OK", len(out))


if __name__ == "__main__":
    main()
