"""v35_verify_gate.py — corre los tests de reactive_check.py con el DEFAULT de drone_spacing
parcheado a S (sin tocar el repo: monkeypatch de coordinators.ReactiveCoordinator antes de importar
reactive_check). Salta save_renders (escribiria gifs) y test_no_regresiones (independiente del
spacing; ademas escribe renders del repo). Uso: python3 v35_verify_gate.py <spacing> [--fast]
--fast: salta test_severidad_muestra y test_cebo_disenado (los lentos)."""
import json
import sys
import traceback

sys.path.insert(0, "/workspace")
S = float(sys.argv[1])
FAST = "--fast" in sys.argv

import coordinators

_Base = coordinators.ReactiveCoordinator


class Patched(_Base):
    def __init__(self, world, **kw):
        kw.setdefault("drone_spacing", S)
        super().__init__(world, **kw)


coordinators.ReactiveCoordinator = Patched

import os
os.chdir("/workspace")  # solo por si algun test usa rutas relativas de LECTURA; no llamamos save_renders
import reactive_check as rc

names = ["test_barrera", "test_reactivo", "test_sin_presa_fijada", "test_penetrado",
         "test_percepcion", "test_standoff", "test_avance", "test_patrulla",
         "test_arranque", "test_reproducible"]
if not FAST:
    names += ["test_severidad_muestra", "test_cebo_disenado"]

results = {}
for n in names:
    try:
        getattr(rc, n)()
        results[n] = "PASS"
    except AssertionError as e:
        results[n] = "FAIL: %s" % e
    except Exception as e:
        results[n] = "ERROR: %s: %s" % (type(e).__name__, e)
        traceback.print_exc()

print("\n===== RESUMEN spacing=%s =====" % S)
for n in names:
    print("  %-24s %s" % (n, results[n]))
print(json.dumps({"spacing": S, "results": results}))
