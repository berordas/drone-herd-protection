"""metro_v37.py — RE-NIVELADO del paquete M1-4p (fisica v3.7 relevo centinela; capa S1/S2+tripwire+senuelo v2 NO afecta al metro: los lobos scriptados no pasan por la capa). Piezas nuevas: dummy, reactive.
100 semillas/tipo, artefactos en /data/hrl_m1/m1pppp/metro/. Piezas:
  floor        suelo residual de drones (NonRigidBarrier δ≡0, patrulla estática default)
  run02        run02 (entrenado v3.4/órbita) evaluado en v3.6-estática — mismatch documentado
  run09e       run09 (entrenado v3.5/órbita) evaluado en v3.6-estática (config oficial)
  run09o       run09 evaluado con SU config de entrenamiento (patrol_omega=0.02, órbita)
  run02o       run02 evaluado con órbita (su config de entrenamiento)
  cebo         suelo del cebo scriptado 2 frentes (KNC / ancla-cebo / sev-2f) con Reactive-estática
[Dummy NO se re-mide: no usa ReactiveCoordinator (drones quietos) => baseline_v2.json v3.5 vigente.]
Los lobos scriptados NO pasan por la capa (regla K solo aplica a quien juega por la capa)."""
import json, sys, pathlib
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world, evaluate
from coordinators import ReactiveCoordinator

OUT = pathlib.Path("/data/hrl_m1/m1pppp/metro"); OUT.mkdir(parents=True, exist_ok=True)

def _residual(model_path, omega=None):
    from stable_baselines3 import PPO
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    model = PPO.load(model_path, device="cpu") if model_path else None
    def factory(w):
        c = ResidualDroneCoordinator(w, model=model)
        if omega is not None:
            c.inner.patrol_omega = omega
        return c
    return factory

def piece(name):
    if name == "dummy":
        from coordinators import DummyCoordinator
        res = evaluate()                                  # DummyCoordinator es el default de evaluate
        res["nota"] = "Dummy re-medido bajo v3.7 (esperado: identico a v3.5 — el relevo centinela no cambia nada sin comandos)"
        out = "dummy_v37.json"
    elif name == "reactive":
        res = evaluate(coordinator_factory=lambda w: ReactiveCoordinator(w))
        res["nota"] = "Reactive-estatica (v3.6 config oficial) bajo fisica v3.7 relevo centinela"
        out = "reactive_estatica_v37.json"
    elif name == "floor":
        res = evaluate(coordinator_factory=_residual(None)); out = "floor_residual_v37.json"
    elif name == "run02":
        res = evaluate(coordinator_factory=_residual("/data/drones/run02_v34/model.zip"))
        res["nota"] = "run02 (v3.4, órbita) evaluado en v3.6-estática (mismatch de patrulla documentado)"
        out = "run02_en_v37_estatica.json"
    elif name == "run02o":
        res = evaluate(coordinator_factory=_residual("/data/drones/run02_v34/model.zip", omega=0.02))
        res["nota"] = "run02 con SU patrulla de entrenamiento (órbita 0.02)"
        out = "run02_en_v37_orbita.json"
    elif name == "run09e":
        res = evaluate(coordinator_factory=_residual("/data/drones/run09_v35/model.zip"))
        res["nota"] = "run09 (v3.5, órbita) evaluado en v3.6-estática (config oficial; mismatch documentado)"
        out = "run09_en_v37_estatica.json"
    elif name == "run09o":
        res = evaluate(coordinator_factory=_residual("/data/drones/run09_v35/model.zip", omega=0.02))
        res["nota"] = "run09 con SU patrulla de entrenamiento (órbita 0.02)"
        out = "run09_en_v37_orbita.json"
    elif name == "cebo":
        from hrl.behavior_checks import EpisodeAudit
        eps = []
        for kind in ("lobos", "mixto"):
            for s in range(100):
                w = build_world(s, kind); coord = ReactiveCoordinator(w); w.reset()
                if len(w.wolf_group_sizes) != 2:
                    continue
                audit = EpisodeAudit(w, coord, meta={"seed": s, "kind": kind})
                while True:
                    audit.on_boundary()
                    _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
                    audit.after_step()
                    if term or trunc:
                        break
                rec = audit.finalize()
                eps.append({"seed": s, "kind": kind, "sizes": rec["grupos_spawn"], "sev": rec["sev"],
                            "primer_ancla": rec["primer_ancla"], "gotera": rec["gotera_cruces"],
                            "relevos": rec["relevos"],
                            "deaths": [{"knc": not d["killer_confirmado"], "grupo": d["grupo_killer"]}
                                       for d in rec["deaths"]]})
        ds = [d for e in eps for d in e["deaths"]]
        anc = [e for e in eps if e["primer_ancla"] is not None]
        res = {"n_episodios_2grupos": len(eps), "n_muertes": len(ds),
               "severidad_media_2grupos": float(np.mean([e["sev"] for e in eps])),
               "frac_killer_no_confirmado": (float(np.mean([d["knc"] for d in ds])) if ds else None),
               "frac_ancla_cebo": (float(np.mean([e["primer_ancla"] < e["sizes"][0] for e in anc])) if anc else None),
               "gotera_por_ep": float(np.mean([e["gotera"] for e in eps])), "episodes": eps}
        out = "cebo_floor_v37.json"
    else:
        raise SystemExit(f"pieza desconocida: {name}")
    (OUT / out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    if name == "cebo":
        print("CEBO", {k: v for k, v in res.items() if k != "episodes"})
    else:
        print(name.upper(), {k: round(v["severity_mean"], 3) for k, v in res["by_kind"].items()})

if __name__ == "__main__":
    piece(sys.argv[1])
