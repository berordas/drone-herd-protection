"""ablacion_barrera_v28.py — SOLO EVAL (sin re-congelar, sin tocar defaults ni artefactos):
desglosar los DOS efectos que v2.8 cambió a la vez, tabla 2x2 percepción × standoff.

Esquinas conocidas (arnés canónico, 100 semillas/tipo, metro DGX):
  - oráculo + standoff 20  = v2.7  = 2.30 / 0 / 2.42
  - honesta + standoff 12  = v2.8  = 2.56 / 0 / 2.26
Se miden aquí:
  - honesta + standoff 20  (tercera esquina — aísla cada efecto)
  - oráculo + standoff 12  (cuarta — cierra la 2x2 y testa aditividad; misma tanda)

'Oráculo' = la percepción v2.6/v2.7 (lobos DETECTADOS a <= r_detect de un ACTIVE, sin
confirmación ni memoria), recreada AQUÍ en una subclase desechable — el default v2.8 del
repo no se toca. 'Honesta' = el ReactiveCoordinator v2.8 tal cual.
"""
import sys, json; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import evaluate, KINDS
from coordinators import ReactiveCoordinator
from world import ACTIVE


class OracleReactive(ReactiveCoordinator):
    """Percepción-oráculo v2.6/v2.7 para la ablación: máscara = detectados a <= r_detect
    (instantánea, sin latch). _update_anchor conserva la histéresis de v2.6 tal cual."""
    def _confirmed_wolves(self):
        w = self.world
        if w.n_wolves == 0:
            return np.zeros(0, dtype=bool)
        flying = w.drones[w.drone_state == ACTIVE]
        if flying.shape[0] == 0:
            return np.zeros(w.n_wolves, dtype=bool)
        d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
        return (d <= w.r_detect).any(axis=1)


CORNERS = {
    "honesta+20": lambda w: ReactiveCoordinator(w, barrier_standoff=20.0),
    "oraculo+12": lambda w: OracleReactive(w),   # standoff = default derivado v2.8 (12)
}

out = {}
for name, fac in CORNERS.items():
    res = evaluate(fac)
    out[name] = {k: {"sev": res["by_kind"][k]["severity_mean"],
                     "std": res["by_kind"][k]["severity_std"],
                     "n": res["by_kind"][k]["n"]} for k in KINDS}
    print("%s: %s" % (name, {k: round(out[name][k]["sev"], 2) for k in KINDS}), flush=True)

json.dump(out, open("/data/wolves/diag/ablacion_barrera_v28.json", "w"), indent=2)
print("JSON -> /data/wolves/diag/ablacion_barrera_v28.json")
