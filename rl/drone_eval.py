"""drone_eval.py — Evalúa un COORDINADOR DE DRONES aprendido con el ARNÉS DE SIEMPRE.

La MISMA vara que Dummy/Reactive (apples-to-apples): `baseline.evaluate` con las MISMAS 100
semillas, la MISMA CONFIG_V2 y los lobos SCRIPTADOS por defecto (v3.4: cebo con roles
invertidos), cambiando SOLO el coordinador:
`coordinator_factory=lambda w: ResidualDroneCoordinator(w, model=modelo)`.
Referencias leídas de los artefactos VIGENTES del repo: Dummy (baseline_v2.json, v3.4
3.82/0/3.84) y Reactive (baseline_v2_reactive.json, v3.4 2.68/0/2.77 = la NOTA A BATIR).
SEVERIDAD: MENOS = MEJOR (signo contrario a eval_wolves).

run02: el residual envuelve la barrera SIN RIGIDEZ (NonRigidBarrier, cambio de diseño 1) ⇒
--floor (δ≡0) mide EL SUELO DE ESTA VARIANTE, que NO tiene por qué reproducir la Reactive
rígida 2.68/0/2.77 (la rigidez afectaba al comportamiento): ese número re-medido es el
suelo/termómetro del run (guardias de train_drones). Con --floor-ref <json> las evaluaciones
de modelos imprimen también Δ respecto a ese suelo re-medido.

Uso (dentro del contenedor):
    python rl/drone_eval.py --floor
    python rl/drone_eval.py --model /data/drones/run01/checkpoints/mappo_drones_4000000_steps.zip
El JSON va a /data (NUNCA al repo).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from baseline import EVAL_SEEDS, KINDS, KIND_LABEL, evaluate
from rl.residual_drone_coordinator import ResidualDroneCoordinator


def _reference(path: str, name: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return {k: d["by_kind"][k]["severity_mean"] for k in d["by_kind"]}
    except FileNotFoundError:
        print(f"⚠️  {path} no encontrado ({name} sin referencia)", file=sys.stderr)
        return {}


def main() -> None:
    p = argparse.ArgumentParser(description="Evalúa el coordinador de drones (arnés canónico, metro DGX).")
    p.add_argument("--model", default=None, help="model.zip / checkpoint .zip SB3 (en /data); opcional con --floor")
    p.add_argument("--floor", action="store_true",
                   help="SUELO run02: δ≡0 = barrera SIN rigidez por el camino residual (se RE-MIDE; no es la rígida)")
    p.add_argument("--floor-ref", type=str, default=None,
                   help="JSON del suelo re-medido (eval --floor previa) para imprimir Δsuelo real")
    p.add_argument("--residual-scale", type=float, default=None, help="escala de δ (def. DETER_RADIUS; = la del run)")
    p.add_argument("--n-seeds", type=int, default=len(EVAL_SEEDS))
    p.add_argument("--out", type=str, default=None, help="JSON de salida (def.: junto al modelo / /data/drones)")
    args = p.parse_args()
    if not args.floor and not args.model:
        p.error("--model es obligatorio (salvo --floor)")

    seeds = tuple(range(args.n_seeds)) if args.n_seeds != len(EVAL_SEEDS) else EVAL_SEEDS
    model_path = Path(args.model) if args.model else None
    if args.out:
        out = Path(args.out)
    elif model_path is not None:
        out = model_path.parent / f"eval_{model_path.stem}.json"
    else:
        out = Path("/data/drones/eval_floor_drones.json")

    model = None
    if model_path is not None:
        from stable_baselines3 import PPO
        model = PPO.load(str(model_path), device="cpu")

    modo = "SUELO run02 (δ≡0 = barrera v3.4 SIN RIGIDEZ por el camino residual)" if model is None \
        else "residual (δ del modelo sobre la barrera sin rigidez)"
    print("=== drone_eval run02: coordinador de drones vs lobos scriptados v3.4 (arnés canónico) ===")
    print(f"  modelo = {model_path if model_path else '(ninguno: δ≡0)'}  |  modo = {modo}")
    print(f"  semillas = {len(seeds)}  |  out = {out}")

    res = evaluate(coordinator_factory=lambda w: ResidualDroneCoordinator(
                       w, model=model, residual_scale=args.residual_scale),
                   seeds=seeds)                                      # lobos scriptados (default)

    dummy = _reference("baseline_v2.json", "Dummy")
    reactive = _reference("baseline_v2_reactive.json", "Reactive")
    floor_ref = _reference(args.floor_ref, "suelo re-medido") if args.floor_ref else {}
    print("  %-12s %8s %9s %8s %11s %9s %8s %8s   %s"
          % ("tipo", "Dummy", "Reactive", "suelo", "APRENDIDO", "Δreactive", "Δsuelo", "n_safe",
             "terminales (aprendido)"))
    for kind in KINDS:
        r = res["by_kind"][kind]; t = r["terminals"]
        d_s = ("%8.2f" % dummy[kind]) if kind in dummy else "       ?"
        re_s = ("%9.2f" % reactive[kind]) if kind in reactive else "        ?"
        fl_s = ("%8.2f" % floor_ref[kind]) if kind in floor_ref else "       -"
        d_re = ("%+9.2f" % (r["severity_mean"] - reactive[kind])) if kind in reactive else "        ?"
        d_fl = ("%+8.2f" % (r["severity_mean"] - floor_ref[kind])) if kind in floor_ref else "       -"
        print("  %-12s %s %s %s %6.2f±%-4.2f %s %s %8.2f   success=%d predation=%d timeout=%d"
              % (KIND_LABEL[kind], d_s, re_s, fl_s, r["severity_mean"], r["severity_std"], d_re,
                 d_fl, r["n_safe_mean"], t["success"], t["predation"], t["timeout"]))
    print("  (severidad = muertes/episodio: MENOS = mejor; NOTA A BATIR = Reactive v3.4 2.68/0/2.77; "
          "'suelo' = δ≡0 SIN rigidez re-medido)")

    payload = {
        "model": str(model_path) if model_path else "FLOOR run02 (δ≡0 = barrera v3.4 SIN rigidez)",
        "modo": modo,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "harness": "baseline.evaluate (metro DGX; lobos scriptados default; referencias = artefactos vigentes)",
        "n_seeds": len(seeds),
        "dummy_reference": dummy, "reactive_reference": reactive,
        "floor_reference": floor_ref or None,
        "by_kind": res["by_kind"], "aggregate": res["aggregate"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
