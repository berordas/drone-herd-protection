"""drone_eval.py — Evalúa un COORDINADOR DE DRONES aprendido con el ARNÉS DE SIEMPRE.

La MISMA vara que Dummy/Reactive (apples-to-apples): `baseline.evaluate` con las MISMAS 100
semillas, la MISMA CONFIG_V2 (v2.6 grouped) y los lobos SCRIPTADOS por defecto, cambiando SOLO
el coordinador: `coordinator_factory=lambda w: ResidualDroneCoordinator(w, model=modelo)`.
Referencias leídas de los artefactos VIGENTES del repo: Dummy (baseline_v2.json, 4.42/0/4.34)
y Reactive (baseline_v2_reactive.json, 2.74/0/2.82 = el SUELO del residual y la nota a batir).
SEVERIDAD: MENOS = MEJOR (signo contrario a eval_wolves).

--floor: modelo None ⇒ δ≡0 ⇒ el coordinador ES la barrera → debe reproducir 2.74/0/2.82
(verificación del cableado; si sale lejos, algo está mal — máscara/asientos/sincronía).

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
                   help="SUELO: δ≡0 (barrera pura por el camino residual) — debe dar ≈ 2.74/0/2.82")
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

    modo = "SUELO (δ≡0 = barrera v2.6 por el camino residual)" if model is None \
        else "residual (δ del modelo sobre la barrera)"
    print("=== drone_eval: coordinador de drones vs lobos scriptados v2.6 (arnés canónico) ===")
    print(f"  modelo = {model_path if model_path else '(ninguno: δ≡0)'}  |  modo = {modo}")
    print(f"  semillas = {len(seeds)}  |  out = {out}")

    res = evaluate(coordinator_factory=lambda w: ResidualDroneCoordinator(
                       w, model=model, residual_scale=args.residual_scale),
                   seeds=seeds)                                      # lobos scriptados (default)

    dummy = _reference("baseline_v2.json", "Dummy")
    reactive = _reference("baseline_v2_reactive.json", "Reactive")
    print("  %-12s %8s %9s %11s %8s %8s   %s"
          % ("tipo", "Dummy", "Reactive", "APRENDIDO", "Δsuelo", "n_safe", "terminales (aprendido)"))
    for kind in KINDS:
        r = res["by_kind"][kind]; t = r["terminals"]
        d_s = ("%8.2f" % dummy[kind]) if kind in dummy else "       ?"
        re_s = ("%9.2f" % reactive[kind]) if kind in reactive else "        ?"
        delta = ("%+8.2f" % (r["severity_mean"] - reactive[kind])) if kind in reactive else "       ?"
        print("  %-12s %s %s %6.2f±%-4.2f %s %8.2f   success=%d predation=%d timeout=%d"
              % (KIND_LABEL[kind], d_s, re_s, r["severity_mean"], r["severity_std"], delta,
                 r["n_safe_mean"], t["success"], t["predation"], t["timeout"]))
    print("  (severidad = muertes/episodio: MENOS = mejor; el suelo/nota a batir es la barrera 2.74/0/2.82)")

    payload = {
        "model": str(model_path) if model_path else "FLOOR (δ≡0 = barrera v2.6)",
        "modo": modo,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "harness": "baseline.evaluate (metro DGX; lobos scriptados default; referencias = artefactos vigentes)",
        "n_seeds": len(seeds),
        "dummy_reference": dummy, "reactive_reference": reactive,
        "by_kind": res["by_kind"], "aggregate": res["aggregate"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
