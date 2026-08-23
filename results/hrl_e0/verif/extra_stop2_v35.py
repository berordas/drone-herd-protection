import json, numpy as np
d = json.load(open('/data/hrl_e0/v35/e01/results.json'))
r = d["resumen"]
g = r["G_keep_h50_reactive"]; grid = g["grid"]; vc, vm = g["valle"]["cebo"], g["valle"]["masa"]
cross = next((t for t, a, b in zip(grid, vc, vm) if a > b), None)
print("valle G/keep: cebo>masa desde tick", cross, "| a 500:", vc[2], vm[2], "| 1000:", vc[4], vm[4], "| 2000:", vc[8], vm[8], "| 4000:", vc[16], vm[16], "| final:", vc[-1], vm[-1])
s = r["S_d90_h50_reactive"]; vc, vm = s["valle"]["cebo"], s["valle"]["masa"]
print("valle S/d90: 1000:", vc[4], vm[4], "| 2000:", vc[8], vm[8], "| 4000:", vc[16], vm[16], "| 8000:", vc[32], vm[32], "| final:", vc[-1], vm[-1])
eps = d["episodes"]
print("episodios e01:", len(eps), "| CRITICAL:", sum(1 for e in eps if e["critical"]), "| violaciones:", sum(1 for e in eps if e["violations"]))
keep = [e for e in eps if e["arm"]=="cebo_keep_h50_reactive"]; masa = {(e["seed"],e["kind"]):e for e in eps if e["arm"]=="masa_reactive" and len(e["grupos_spawn"])==2}
for kind in ("lobos","mixto"):
    dd = [e["sev"]-masa[(e["seed"],e["kind"])]["sev"] for e in keep if e["kind"]==kind]
    print(kind, "delta media", round(float(np.mean(dd)),3), "n", len(dd))
anc = [e for e in keep if e["primer_ancla"] is not None]
print("ancla=senuelo(idx0) en G/keep:", round(float(np.mean([e["primer_ancla"]==0 for e in anc])),3), "n", len(anc))
steps = [e["steps"] for e in keep if e["kind"]=="lobos"]
print("steps G/keep lobos p50/p75:", np.percentile(steps,50), np.percentile(steps,75))
