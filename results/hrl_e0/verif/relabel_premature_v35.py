"""relabel_premature.py — Re-etiqueta el campo `premature` de los episodios de e01 con el
clasificador CORREGIDO (diferido al latch + spawn excluido del borde) SIN re-correr el
experimento: los episodios son deterministas (misma seed/kind/brazo => misma trayectoria),
así que se re-simulan SOLO los que tenían ESCOLTA prematura (el resto no cambia: el flag
solo se activa si ESCOLTA salta antes del show, y eso lo decide el mundo, no el
clasificador). Verifica de paso que sev/steps coinciden con el registro original (guardia
de determinismo) y regenera results.json + REPORT.md."""
import json
import multiprocessing as mp
import pathlib
import sys

sys.path.insert(0, "/workspace")
from hrl import run_e0  # noqa: E402

BASE = pathlib.Path("/data/hrl_e0/v35/e01")


def job_of(r):
    # Reconstruye el job desde el registro (nombre del brazo -> spec).
    name = r["arm"]
    drone = "run02" if name.endswith("_run02") else "reactive"
    if name.startswith("masa"):
        arm = dict(run_e0.ARM_MASA, drone=drone, name=name)
    elif name.startswith("cebo_keep"):
        arm = run_e0._arm_cebo(50.0, drone, membership="keep")
    else:                                     # cebo_d{delta}_h{hold}_{drone}
        parts = name.split("_")
        delta = float(parts[1][1:]); hold = float(parts[2][1:])
        arm = run_e0._arm_cebo(hold, drone, delta=delta)
    assert arm["name"] == name, (arm["name"], name)
    return {"seed": r["seed"], "kind": r["kind"], "arm": arm}


def rerun(r):
    rec = run_e0.run_episode(job_of(r))
    assert rec["sev"] == r["sev"] and rec["steps"] == r["steps"], \
        f"NO determinista: {r['arm']} {r['seed']} {r['kind']}"
    return rec["premature"], [e for e in rec["events"] if e["ev"] == "ESCOLTA_PREMATURA"]


def main():
    data = json.load(open(BASE / "results.json"))
    eps = data["episodes"]
    idx = [i for i, r in enumerate(eps) if r.get("premature")]
    print("prematuras a re-etiquetar:", len(idx))
    with mp.Pool(32) as pool:
        out = pool.map(rerun, [eps[i] for i in idx], chunksize=1)
    for i, (prem, evs) in zip(idx, out):
        eps[i]["premature"] = prem
        eps[i]["events"] = [e for e in eps[i]["events"] if e["ev"] != "ESCOLTA_PREMATURA"] + evs
        eps[i]["events"].sort(key=lambda e: e["t"])
    # Recalcular las tasas de cada celda con _tasas (solo cambian las frecuencias prematuras).
    res = data["resumen"]
    by_arm = {}
    for r in eps:
        by_arm.setdefault(r["arm"], []).append(r)
    for key, cell in res.items():
        if not isinstance(cell, dict) or "tasas" not in cell:
            continue
        # nombre de brazo CEBO de la celda: {estrato}_{cfg}_{drone} -> cebo_...
        est, *mid, drone = key.split("_")
        cfg = "_".join(mid)
        cebo_name = ("cebo_keep_h50_" + drone) if cfg == "keep_h50" else f"cebo_{cfg}_{drone}"
        masa_name = f"masa_{drone}"
        ng = 2 if est == "G" else 1              # estrato = geometría de spawn (inequívoco)
        cebo = [r for r in by_arm.get(cebo_name, []) if len(r["grupos_spawn"]) == ng]
        assert len(cebo) == cell["dist"]["cebo"]["n"], (key, len(cebo), cell["dist"]["cebo"]["n"])
        masa = [r for r in by_arm.get(masa_name, []) if (r["seed"], r["kind"]) in
                {(c["seed"], c["kind"]) for c in cebo}]
        cell["tasas"] = {"cebo": run_e0._tasas(cebo), "masa": run_e0._tasas(masa)}
    data["resumen"] = res
    (BASE / "results.json").write_text(json.dumps(data, ensure_ascii=False))
    print("RELABEL_OK")


if __name__ == "__main__":
    main()
