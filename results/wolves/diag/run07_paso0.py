"""run07_paso0.py — Paso 0 de run07: verificar el SUELO δ=0 sobre v2.8 (barrera honesta) ANTES de entrenar.
(a) Episodios grouped de 2 frentes con el residual δ=0: ¿los lobos rodean/atacan (sano) o se atascan
    (zombis)? severidad / % pasos amurallado / % pasos espantado / timeouts / rapidez media.
(b) Suelo de la EVAL LIGERA (el mismo camino que LightEval: 10 semillas fijas 'lobos', δ=0) ->
    calibra las guardias de run07 (no se reutiliza el 2.20 de v2.7).
"""
import sys; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from rl.policy_wolf_controller import SyncedReactiveCoordinator
from rl.residual_wolf_controller import ResidualWolfController

# (a) sanidad en 2 frentes (lobos+mixto hasta 12 episodios de 2 grupos)
print("=== (a) SUELO δ=0 sobre v2.8, episodios grouped de 2 subgrupos ===", flush=True)
sev, walled, scared, steps, timeouts, speeds, neps = [], 0, 0, 0, 0, [], 0
for kind in ("lobos", "mixto"):
    for s in range(40):
        ctrl = ResidualWolfController(model=None)
        w = build_world(s, kind, wolf_controller=ctrl)
        coord = SyncedReactiveCoordinator(w); w.reset()
        if len(w.wolf_group_sizes) != 2:
            continue
        neps += 1
        prev = w.wolves.copy()
        while True:
            _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
            walled += int(w._wolf_walled.sum()); scared += int(w._wolf_scared.sum())
            steps += w.n_wolves
            speeds.append(float(np.linalg.norm(w.wolves - prev, axis=1).mean() / w.dt))
            prev = w.wolves.copy()
            if term or trunc:
                break
        sev.append(int(w.n_depredadas)); timeouts += int(w.status == "timeout")
        if neps >= 12:
            break
    if neps >= 12:
        break
print("  %d episodios | severidad media %.2f | amurallado %.1f%% de lobo-pasos | espantado %.1f%% | "
      "timeouts %d/%d | rapidez media de lobo %.2f m/s"
      % (neps, np.mean(sev), 100 * walled / max(steps, 1), 100 * scared / max(steps, 1),
         timeouts, neps, np.mean(speeds)), flush=True)

# (b) suelo de la eval ligera (mismo camino que LightEval: 10 semillas 'lobos', δ=0 determinista)
print("=== (b) SUELO de la EVAL LIGERA sobre v2.8 (10 semillas fijas 'lobos', δ=0) ===", flush=True)
deaths = []
for s in range(10):
    ctrl = ResidualWolfController(model=None)
    w = build_world(s, "lobos", wolf_controller=ctrl)
    w.reset()
    coord = SyncedReactiveCoordinator(w)
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        if term or trunc:
            break
    deaths.append(int(w.n_depredadas))
print("  suelo ligera v2.8 = %.2f | detalle %s" % (float(np.mean(deaths)), deaths), flush=True)
print("PASO0_LISTO")
