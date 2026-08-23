"""run08_ancla_diag.py — ¿el sector-CEBO es el que dispara/ancla la barrera? (métrica de
comportamiento de run08, complementa a cebo_diag).

Por episodio de 2 SUBGRUPOS (spawn real v3.4: grupo 1 = cebo de 1 lobo, grupo 2 = asalto n−1),
registra el grupo del PRIMER lobo ANCLA de la barrera (coordinator.inner._anchor la primera vez
que deja de ser None) y reporta el %% de episodios donde ancla = sector-cebo. Referencia v3.4
(diagnóstico de la etapa v3.3/v3.4, scriptado): ~60%% (techo ~73%% por spawns cazados al nacer).
Se mide aquí también el suelo δ≡0 para apples-to-apples con el MISMO contador.

Uso: python3 run08_ancla_diag.py <FLOOR|checkpoint.zip> [etiqueta]
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world                                   # noqa: E402
from rl.policy_wolf_controller import SyncedReactiveCoordinator    # noqa: E402
from rl.residual_wolf_controller import ResidualWolfController     # noqa: E402

SEEDS = range(100)
KINDS = ("lobos", "mixto")


def run_episode(seed, kind, model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n1 = int(w.wolf_group_sizes[0])
    first_anchor_g = None
    while True:
        wp = coord.act(w.get_observation())
        if first_anchor_g is None and coord.inner._anchor is not None:
            first_anchor_g = 1 if int(coord.inner._anchor) < n1 else 2
        _o, _r, term, trunc, _i = w.step(wp)
        if term or trunc:
            break
    return dict(seed=seed, kind=kind, sizes=[int(x) for x in w.wolf_group_sizes],
                n_depredadas=int(w.n_depredadas),
                first_anchor_group=first_anchor_g,          # None = nunca hubo ancla (sin ESCOLTA)
                ancla_es_cebo=(first_anchor_g == 1))


def main():
    arg = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else ("suelo" if arg == "FLOOR" else Path(arg).stem)
    model = None
    if arg != "FLOOR":
        from stable_baselines3 import PPO
        model = PPO.load(arg, device="cpu")
    eps = []
    for kind in KINDS:
        for s in SEEDS:
            r = run_episode(s, kind, model)
            if r is not None:
                eps.append(r)
    con_ancla = [e for e in eps if e["first_anchor_group"] is not None]
    frac = float(np.mean([e["ancla_es_cebo"] for e in con_ancla])) if con_ancla else 0.0
    print(f"[{label}] episodios 2 subgrupos: {len(eps)} | con ancla: {len(con_ancla)} | "
          f"ANCLA = SECTOR-CEBO: {100 * frac:.1f}%  (referencia scriptado v3.3/v3.4: ~60%)")
    out = Path(f"/data/wolves/run08_dieta50/ancla_{label}.json")
    out.write_text(json.dumps({"model": arg, "fecha": datetime.now().isoformat(timespec="seconds"),
                               "frac_ancla_cebo": round(frac, 4), "n": len(eps),
                               "episodes": eps}, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
