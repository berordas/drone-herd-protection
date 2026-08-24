"""
reactive_eval.py — Evalúa el ReactiveCoordinator con el MISMO arnés que la baseline v2.

Apples-to-apples: reutiliza baseline.evaluate (mismas semillas EVAL_SEEDS, misma CONFIG_V2,
mismos 3 tipos) cambiando SOLO el coordinador (Dummy -> Reactive). Reporta la severidad POR
TIPO y la compara con la baseline Dummy CONGELADA (leída de baseline_v2.json). Guarda
baseline_v2_reactive.json (por episodio) + baseline_v2_reactive.csv (tabla comparada).

La física está congelada (v2, tag v2-baseline); baseline.py no se toca (su evaluate ya es
genérico). Severidad = MEDIDA, no objetivo: se espera que baje en solo-lobos/mixto; solo-corzos
sigue 0 (sin amenaza) y ahí lo que importa es la eficiencia (movimiento/batería de la patrulla).
"""

from __future__ import annotations
import sys as _sys, pathlib as _pl  # layout: raíz (rl/, hrl/) y sim/ (núcleo) importables sin instalar el paquete
_ROOT = _pl.Path(__file__).resolve().parents[1]; _sys.path[:0] = [str(_ROOT), str(_ROOT / "sim")]
import csv
import json

from baseline import evaluate, EVAL_SEEDS, KINDS, KIND_LABEL, TERMINALS, N_PER_KIND
from coordinators import ReactiveCoordinator


def _load_dummy_reference(path=str(_ROOT / "tests/fixtures/baseline_v2.json")) -> dict:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {k: d["by_kind"][k] for k in KINDS} | {"aggregate": d["aggregate"]}


def main():
    print("=== ReactiveCoordinator vs baseline Dummy CONGELADA (N=%d/tipo, mismas semillas/CONFIG_V2) ===" % N_PER_KIND)
    ref = _load_dummy_reference()
    res = evaluate(lambda w: ReactiveCoordinator(w))

    print("  %-12s %10s %10s %8s   %8s   %s" % ("tipo", "Dummy", "Reactive", "Δsev", "n_safe", "terminales (Reactive)"))
    for kind in KINDS:
        r = res["by_kind"][kind]; t = r["terminals"]
        d_sev = ref[kind]["severity_mean"]; r_sev = r["severity_mean"]
        print("  %-12s %10.2f %6.2f±%-4.2f %+8.2f   %8.2f   success=%d predation=%d timeout=%d"
              % (r["label"], d_sev, r_sev, r["severity_std"], r_sev - d_sev, r["n_safe_mean"],
                 t["success"], t["predation"], t["timeout"]))
    ra = res["aggregate"]; da = ref["aggregate"]
    print("  %-12s %10.2f %6.2f±%-4.2f %+8.2f   %8.2f"
          % ("AGREGADO", da["severity_mean"], ra["severity_mean"], ra["severity_std"],
             ra["severity_mean"] - da["severity_mean"], ra["n_safe_mean"]))

    _write(res, ref)
    print("  guardado -> baseline_v2_reactive.json (por episodio) + baseline_v2_reactive.csv (tabla comparada)")


def _write(res: dict, ref: dict, path_json=str(_ROOT / "tests/fixtures/baseline_v2_reactive.json"), path_csv=str(_ROOT / "tests/fixtures/baseline_v2_reactive.csv")) -> None:
    payload = {
        "coordinator": "ReactiveCoordinator",
        "compared_to": "DummyCoordinator (baseline_v2, tag v2-baseline)",
        "n_per_kind": N_PER_KIND, "seeds": list(EVAL_SEEDS), "kinds": list(KINDS),
        "by_kind": res["by_kind"], "aggregate": res["aggregate"],
        "dummy_reference": {k: {"severity_mean": ref[k]["severity_mean"],
                                "n_safe_mean": ref[k]["n_safe_mean"],
                                "terminals": ref[k]["terminals"]} for k in KINDS},
    }
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(path_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tipo", "n", "dummy_sev", "reactive_sev", "reactive_desv", "delta_sev",
                    "reactive_max", "dummy_n_safe", "reactive_n_safe", "success", "predation", "timeout"])
        for kind in KINDS:
            r = res["by_kind"][kind]; t = r["terminals"]
            w.writerow([r["label"], r["n"], "%.4f" % ref[kind]["severity_mean"],
                        "%.4f" % r["severity_mean"], "%.4f" % r["severity_std"],
                        "%+.4f" % (r["severity_mean"] - ref[kind]["severity_mean"]), r["severity_max"],
                        "%.4f" % ref[kind]["n_safe_mean"], "%.4f" % r["n_safe_mean"],
                        t["success"], t["predation"], t["timeout"]])


if __name__ == "__main__":
    main()
