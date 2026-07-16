"""eval_wolves.py — Evalúa una política de LOBOS entrenada con el ARNÉS DE SIEMPRE.

Apples-to-apples con el metro canónico v2.4.1: `baseline.evaluate` con las MISMAS semillas
(EVAL_SEEDS, range(100)), la MISMA CONFIG_V2 y la MISMA barrera reactiva congelada,
cambiando SOLO el cerebro de los lobos (scriptado → política SB3). La referencia a batir
por los lobos aprendidos son los SCRIPTADOS: severidad 2.77 (solo-lobos) / 2.80 (mixto)
contra esa barrera (leída de baseline_v2_reactive.json — más muertes = mejores lobos).

Uso (dentro del contenedor):
    python rl/eval_wolves.py --model /data/wolves/run01/checkpoints/ppo_wolves_500000_steps.zip
    python rl/eval_wolves.py --model /data/wolves/smoke/model.zip --n-seeds 10   # smoke rápido

El JSON de resultados va a /data (NUNCA al repo): default junto al modelo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Repo importable ejecutándolo como script suelto (en el contenedor ya hay PYTHONPATH=/workspace).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from baseline import EVAL_SEEDS, KIND_LABEL, TERMINALS, evaluate
from rl.policy_wolf_controller import PolicyWolfController, SyncedReactiveCoordinator
from rl.wolf_env import VALID_KINDS


def _scripted_reference(path: str = "baseline_v2_reactive.json") -> dict:
    """Severidad de los lobos SCRIPTADOS contra la misma barrera (el metro v2.4.1)."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return {k: d["by_kind"][k]["severity_mean"] for k in d["by_kind"]}
    except FileNotFoundError:
        return {}


def main() -> None:
    p = argparse.ArgumentParser(description="Evalúa lobos APRENDIDOS vs la barrera reactiva (arnés v2.4.1).")
    p.add_argument("--model", default=None, help="model.zip / checkpoint .zip de SB3 (en /data); opcional con --floor")
    p.add_argument("--kinds", type=str, default="lobos,mixto", help="tipos (coma; nunca 'corzos')")
    p.add_argument("--n-seeds", type=int, default=len(EVAL_SEEDS),
                   help="nº de semillas (default %d = la muestra oficial; menos = smoke)" % len(EVAL_SEEDS))
    p.add_argument("--out", type=str, default=None,
                   help="JSON de salida (default: junto al modelo, eval_<nombre>.json — en /data)")
    p.add_argument("--residual", action="store_true",
                   help="ResidualWolfController (RPL, run04): δ del modelo SOBRE el scriptado vivo")
    p.add_argument("--residual-scale", type=float, default=None, help="escala de δ (def. wolf_speed; = la del run)")
    p.add_argument("--floor", action="store_true",
                   help="SUELO del residual: δ≡0 (scriptado puro por el camino residual, sin modelo) — "
                        "verifica el cableado: debe reproducir ≈ 2.77/2.80")
    args = p.parse_args()
    if args.floor:
        args.residual = True
    if not args.floor and not args.model:
        p.error("--model es obligatorio (salvo --floor)")

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    if any(k not in VALID_KINDS for k in kinds):
        p.error("--kinds debe ser subconjunto de %r (nunca 'corzos')" % (VALID_KINDS,))
    seeds = tuple(range(args.n_seeds)) if args.n_seeds != len(EVAL_SEEDS) else EVAL_SEEDS

    model_path = Path(args.model) if args.model else None
    if args.out:
        out = Path(args.out)
    elif model_path is not None:
        out = model_path.parent / f"eval_{model_path.stem}.json"
    else:
        out = Path("/data/wolves/eval_floor_residual.json")
    if str(out.resolve()).startswith("/workspace") or str(out.resolve()).startswith(str(_ROOT)):
        print("⚠️  --out apunta DENTRO del repo; los artefactos de evaluación van a /data.", file=sys.stderr)

    modo = "residual (δ del modelo sobre el scriptado)" if args.residual else "política pura"
    if args.floor:
        modo = "SUELO residual (δ≡0 = scriptado por el camino residual)"
    print("=== eval_wolves: política SB3 vs barrera reactiva (arnés v2.4.1, mismas semillas) ===")
    print(f"  modelo = {model_path if model_path else '(ninguno: δ≡0)'}  |  modo = {modo}")
    print(f"  kinds = {kinds}  |  semillas = {len(seeds)} (range({len(seeds)}))  |  out = {out}")

    model = None
    if model_path is not None:
        from stable_baselines3 import PPO   # import perezoso (torch tarda)
        model = PPO.load(str(model_path), device="cpu")   # UNA carga; compartido entre episodios

    if args.residual:
        from rl.residual_wolf_controller import ResidualWolfController
        factory = lambda: ResidualWolfController(model=model, residual_scale=args.residual_scale)  # noqa: E731
    else:
        factory = lambda: PolicyWolfController(model=model)  # noqa: E731

    res = evaluate(coordinator_factory=lambda w: SyncedReactiveCoordinator(w),
                   wolf_controller_factory=factory,
                   seeds=seeds, kinds=kinds)

    ref = _scripted_reference()
    print("  %-12s %10s %14s %8s %8s   %s" % ("tipo", "scriptados", "APRENDIDOS", "Δsev", "n_safe", "terminales (aprendidos)"))
    for kind in kinds:
        r = res["by_kind"][kind]; t = r["terminals"]
        sref = ref.get(kind)
        sref_s = ("%10.2f" % sref) if sref is not None else "         ?"
        delta_s = ("%+8.2f" % (r["severity_mean"] - sref)) if sref is not None else "       ?"
        print("  %-12s %s %8.2f±%-4.2f %s %8.2f   success=%d predation=%d timeout=%d"
              % (KIND_LABEL[kind], sref_s, r["severity_mean"], r["severity_std"], delta_s,
                 r["n_safe_mean"], t["success"], t["predation"], t["timeout"]))
    print("  (severidad = muertes/episodio: MÁS alta = mejores lobos; los scriptados son la nota a batir)")

    payload = {
        "model": str(model_path) if model_path else "FLOOR (residual δ≡0 = scriptado)",
        "modo": modo,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "harness": "baseline.evaluate (v2.4.1, metro DGX)",
        "coordinator": "ReactiveCoordinator (congelado, via SyncedReactiveCoordinator)",
        "kinds": list(kinds), "n_seeds": len(seeds),
        "scripted_reference": ref,
        "by_kind": res["by_kind"], "aggregate": res["aggregate"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
