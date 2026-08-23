"""ablacion_v29.py — SOLO EVAL (desechable): aislar el CEBO DISEÑADO del AVANCE de la barrera.
Esquina 'cebo SIN avance': ReactiveCoordinator v2.9 con advance_max forzado al mínimo (= la línea
fija de v2.8, adv siempre clip -> barrier_standoff) contra los lobos v2.9 (2 sectores, 2 presas).
Comparable DIRECTO con el Reactive v2.8 (2.56/0/2.26, lobos sin cebo, misma barrera):
la diferencia = el efecto PURO del cebo diseñado. [La esquina 'avance sin cebo' no es medible sin
tocar el mundo: el cebo vive en el scriptado v2.9.]
"""
import sys, json; sys.path.insert(0, "/workspace")
from baseline import evaluate, KINDS
from coordinators import ReactiveCoordinator


def barrera_v28(w):
    c = ReactiveCoordinator(w)
    c.advance_max = c.barrier_standoff      # clip(_, 12, 12) = 12 SIEMPRE = la línea fija de v2.8
    return c


res = evaluate(barrera_v28)
out = {k: {"sev": res["by_kind"][k]["severity_mean"], "std": res["by_kind"][k]["severity_std"]}
       for k in KINDS}
print("cebo SIN avance (barrera v2.8 fija vs lobos v2.9):",
      {k: round(out[k]["sev"], 2) for k in KINDS})
json.dump(out, open("/data/wolves/diag/ablacion_v29.json", "w"), indent=2)
print("JSON -> /data/wolves/diag/ablacion_v29.json")
