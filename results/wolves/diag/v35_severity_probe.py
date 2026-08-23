"""v35_severity_probe.py — severidad del Reactive con espaciado alternativo, MISMO arnés que
reactive_eval.py (baseline.evaluate, mismas 100 semillas/tipo, CONFIG_V2, dentro del contenedor).
NO congela nada: es una SONDA para decidir (v3.5). Uso: python3 v35_severity_probe.py <spacing>"""
import json
import sys

sys.path.insert(0, "/workspace")
from baseline import evaluate, KINDS
from coordinators import ReactiveCoordinator

S = float(sys.argv[1])
res = evaluate(lambda w: ReactiveCoordinator(w, drone_spacing=S))
out = {"spacing": S}
for kind in KINDS:
    r = res["by_kind"][kind]
    out[kind] = {"sev": round(r["severity_mean"], 4), "std": round(r["severity_std"], 4),
                 "n_safe": round(r["n_safe_mean"], 4), "terminals": r["terminals"]}
out["aggregate"] = round(res["aggregate"]["severity_mean"], 4)
print(json.dumps(out))
