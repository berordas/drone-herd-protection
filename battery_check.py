"""
battery_check.py — Verificación macro de la batería y el RELEVO REALISTA (hand-off, SIN teletransporte).

Operación continua: con batería ~10 min y episodios de defensa más cortos, dentro de un episodio no
se completa un ciclo de relevo. Por eso aquí se dirige el subsistema en aislado durante varios ciclos:
cada paso = dinámica de vuelo (`_apply_drone_actions(None)`: los relevos VUELAN de verdad, los ACTIVE
y las reservas quietas) + `_step_battery()` (batería + dispatch/hand-off/retorno/strand), SIN tocar
vacas/lobo (quedan quietos) y sin RNG en el step -> reproducible bit a bit.

Relevo REALISTA: al bajar del umbral, el ACTIVE se CLAVA en su puesto (sigue cubriendo) y la central
despacha al READY más cargado, que VUELA al puesto; al llegar encima -> hand-off (el relevo pasa a
ACTIVE, el bajo a RETURNING -> CHARGING). Cobertura CONTINUA (nadie se va antes de que llegue el relevo).
Bajo estrés (drenaje alto sostenido) las reservas pueden no dar abasto -> STRANDED (fallo esperado).

Esperado con 8 drones (4 puestos): régimen ~4 ACTIVE / ~2 CHARGING / ~2 READY (+ tránsito ocasional
INCOMING/RETURNING), relevos escalonados, 4 puestos SIEMPRE cubiertos a carga normal, sin teletransporte.
"""

from collections import Counter
import numpy as np
from world import (World, ACTIVE, RETURNING, CHARGING, READY, INCOMING, STRANDED,
                   DRONE_STATE_NAMES, DRONE_MAX_SPEED)

STEPS = 20000    # >= varios ciclos de batería para ver el régimen permanente
NSTATES = 6


def run(seed: int = 0, steps: int = STEPS, stress: float = 1.0):
    """Dirige batería + vuelo en aislado. stress>1 fuerza el drenaje de los ACTIVE (simula 'volar a tope'
    sin parar) para provocar el fallo de reservas (STRANDED)."""
    w = World(seed=seed)
    w._init_battery(stagger=True)  # arranque escalonado (RNG sembrado del World)

    occ = np.zeros((steps, NSTATES), dtype=int)
    handoffs = np.zeros(steps, dtype=int)
    min_active, stranded_max, max_jump = w.n_active, 0, 0.0
    prev = w.drones.copy()
    for t in range(steps):
        w._apply_drone_actions(None)                      # dinámica de vuelo: los relevos VUELAN
        if stress != 1.0:
            w.battery_activity[w.drone_state == ACTIVE] = stress   # ACTIVE 'a tope' -> drena stress x
        before = w.drone_state.copy()
        w._step_battery()                                 # batería + dispatch/hand-off/retorno/strand
        handoffs[t] = int(np.sum((before == INCOMING) & (w.drone_state == ACTIVE)))
        occ[t] = np.bincount(w.drone_state, minlength=NSTATES)
        max_jump = max(max_jump, float(np.linalg.norm(w.drones - prev, axis=1).max()))
        prev = w.drones.copy()
        min_active = min(min_active, int(occ[t, ACTIVE]))
        stranded_max = max(stranded_max, int(occ[t, STRANDED]))
    return w, occ, handoffs, min_active, stranded_max, max_jump


def main():
    w, occ, handoffs, min_active, stranded_max, max_jump = run(seed=0)
    half = len(occ) // 2
    avg = occ[half:].mean(axis=0)

    print("=== Ocupación media (régimen permanente, 2ª mitad de %d pasos) ===" % len(occ))
    for s in (ACTIVE, CHARGING, READY, INCOMING, RETURNING, STRANDED):
        print("  %-9s %.2f" % (DRONE_STATE_NAMES[s], avg[s]))

    total = int(handoffs.sum())
    print("\n=== Relevos (hand-off REALISTA, sin teletransporte) ===")
    print("  hand-offs=%d en %d pasos (~1 cada %d pasos = %.0f s)"
          % (total, len(occ), len(occ) // max(total, 1), (len(occ) // max(total, 1)) * w.dt))
    print("  pasos con >1 hand-off simultáneo: %d  (escalonado si ~0)" % int(np.sum(handoffs > 1)))

    lim = DRONE_MAX_SPEED * w.dt
    print("\n=== Sin teletransporte ===")
    print("  salto máx de posición/paso = %.3f m (tope físico DRONE_MAX_SPEED*dt = %.3f) -> continuo: %s"
          % (max_jump, lim, max_jump <= lim * 1.01))

    print("\n=== Invariantes (carga normal = hover) ===")
    cubierto = min_active == w.n_active
    print("  puestos ACTIVE SIEMPRE = %d:  %s (min observado=%d)  <- cobertura continua" % (w.n_active, cubierto, min_active))
    print("  total de drones conservado (=%d):  %s" % (w.n_drones, bool((occ.sum(axis=1) == w.n_drones).all())))
    print("  drones STRANDED: máx=%d  (0 esperado a carga hover: las reservas dan abasto)" % stranded_max)

    # Estrés: drenaje sostenido alto -> las reservas no dan abasto -> STRANDED (fallo esperado, no bug).
    _, _, _, min_active_s, stranded_s, _ = run(seed=0, stress=2.5)
    print("\n=== Estrés (drenaje 2.5x sostenido: moverse a tope sin parar) ===")
    print("  drones STRANDED: máx=%d  (>0 = reservas no dan abasto -> FALLO ESPERADO que el coordinador debe evitar)" % stranded_s)
    print("  min ACTIVE = %d  (<4 = hueco de cobertura mientras hay un dron tirado)" % min_active_s)

    # Reproducibilidad: misma seed -> mismo escalonado, misma secuencia de relevos/posiciones.
    _, occ2, handoffs2, _, _, _ = run(seed=0)
    repro = np.array_equal(occ, occ2) and np.array_equal(handoffs, handoffs2)
    print("\n=== Reproducibilidad (misma seed) ===")
    print("  ocupación idéntica:", np.array_equal(occ, occ2), "| hand-offs idénticos:", np.array_equal(handoffs, handoffs2))

    # Verja (verde = sin regresión del subsistema).
    assert max_jump <= lim * 1.01, "FALLO: TELETRANSPORTE (un dron saltó más que su tope físico por paso)"
    assert cubierto, "FALLO: hueco de cobertura a carga hover (algún puesto se quedó sin ACTIVE)"
    assert stranded_max == 0, "FALLO: STRANDED inesperado a carga hover (las reservas deberían dar abasto)"
    assert avg[ACTIVE] >= w.n_active - 1e-9, "FALLO: ACTIVE medio < n_active"
    assert stranded_s >= 1, "FALLO: el estrés no produjo STRANDED (el mecanismo de fallo no se verifica)"
    assert repro, "FALLO: no reproducible"
    print("\nbattery_check: TODO OK.")


if __name__ == "__main__":
    main()
