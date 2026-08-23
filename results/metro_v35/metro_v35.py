"""metro_v35.py — RE-METRO del mundo v3.5 (regla del sonido), 100 semillas/tipo, artefactos *_v35 en
/data/metro_v35/. Piezas: (1) suelo residual de drones (NonRigidBarrier δ≡0) · (2) run02 RE-EVALUADO
("política v3.4 evaluada en mundo v3.5"; NO re-entrenado) · (3) suelo del cebo scriptado (cebo_diag
--floor equivalente: subconjunto de 2 frentes, KNC/ancla-cebo/sev-2f, mismas semillas: el spawn NO
cambia) · (4) cruces de corredor por episodio (Reactive) — esperado ~0. Dummy y Reactive los mide
baseline.py / reactive_eval.py (artefactos del repo). Uso: python3 metro_v35.py <pieza> con
pieza ∈ {floor, run02, cebo, cruces}."""
import json, sys, pathlib
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world, evaluate, EVAL_SEEDS, KINDS      # noqa
from coordinators import ReactiveCoordinator                        # noqa
from world import ACTIVE                                            # noqa

OUT = pathlib.Path("/data/metro_v35")


def piece_floor():
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    res = evaluate(coordinator_factory=lambda w: ResidualDroneCoordinator(w, model=None))
    (OUT / "floor_residual_drones_v35.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("FLOOR", {k: round(v["severity_mean"], 3) for k, v in res["by_kind"].items()})


def piece_run02():
    from stable_baselines3 import PPO
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    model = PPO.load("/data/drones/run02_v34/model.zip", device="cpu")
    res = evaluate(coordinator_factory=lambda w: ResidualDroneCoordinator(w, model=model))
    res["nota"] = "política run02 (entrenada en v3.4) EVALUADA en el mundo v3.5 — NO re-entrenada"
    (OUT / "run02_v34_en_v35.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("RUN02@v35", {k: round(v["severity_mean"], 3) for k, v in res["by_kind"].items()})


def piece_cebo():
    """Suelo del cebo scriptado v3.5 (mismo contador que run08/cebo_diag: episodios de 2 subgrupos,
    killer = lobo más cercano en la frontera previa, confirmado = latch de la barrera)."""
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
                        "deaths": [{"knc": not d["killer_confirmado"], "grupo": d["grupo_killer"]}
                                   for d in rec["deaths"]]})
    ds = [d for e in eps for d in e["deaths"]]
    anc = [e for e in eps if e["primer_ancla"] is not None]
    res = {"n_episodios_2grupos": len(eps), "n_muertes": len(ds),
           "severidad_media_2grupos": float(np.mean([e["sev"] for e in eps])),
           "frac_killer_no_confirmado": (float(np.mean([d["knc"] for d in ds])) if ds else None),
           "frac_ancla_cebo": (float(np.mean([e["primer_ancla"] < e["sizes"][0] for e in anc])) if anc else None),
           "gotera_por_ep": float(np.mean([e["gotera"] for e in eps])), "episodes": eps}
    (OUT / "cebo_floor_v35.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("CEBO", {k: v for k, v in res.items() if k != "episodes"})


def piece_cruces():
    """Cruces de corredor por episodio con Reactive (100 semillas lobos+mixto) — v3.4 medía 30-55% de
    muertes tras gotera; esperado ~0 con la regla del sonido."""
    from hrl.behavior_checks import EpisodeAudit
    out = []
    for kind in ("lobos", "mixto"):
        for s in range(100):
            w = build_world(s, kind); coord = ReactiveCoordinator(w); w.reset()
            audit = EpisodeAudit(w, coord, meta={"seed": s, "kind": kind})
            while True:
                audit.on_boundary()
                _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
                audit.after_step()
                if term or trunc:
                    break
            rec = audit.finalize()
            out.append({"seed": s, "kind": kind, "sev": rec["sev"], "gotera": rec["gotera_cruces"],
                        "corredor": rec["corredor_cruces"],
                        "muertes_tras_gotera": sum(1 for d in rec["deaths"] if d["cruzo_gotera"])})
    res = {"n": len(out), "gotera_por_ep": float(np.mean([o["gotera"] for o in out])),
           "corredor_por_ep": float(np.mean([o["corredor"] for o in out])),
           "frac_muertes_tras_gotera": (sum(o["muertes_tras_gotera"] for o in out) /
                                        max(sum(o["sev"] for o in out), 1)),
           "sev_media": float(np.mean([o["sev"] for o in out])), "episodes": out}
    (OUT / "cruces_reactive_v35.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("CRUCES", {k: v for k, v in res.items() if k != "episodes"})


if __name__ == "__main__":
    {"floor": piece_floor, "run02": piece_run02, "cebo": piece_cebo, "cruces": piece_cruces}[sys.argv[1]]()
