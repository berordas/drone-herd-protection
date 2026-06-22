"""
battery_check.py — Verificación macro del subsistema de batería y cola de carga.

Es de OPERACIÓN CONTINUA: con batería ~10 min y episodios de defensa mucho más
cortos, dentro de un episodio no se completa un ciclo de relevo. Por eso aquí se
dirige SOLO World._step_battery() durante varios ciclos de batería (sin tocar
vacas/lobo, que quedan quietos) y se registra la ocupación.

Esperado con 8 drones (4 puestos activos): ~4 activos / ~2 cargando / ~2 listos,
relevos escalonados (no simultáneos), siempre 4 puestos cubiertos.
"""

from collections import Counter
import numpy as np
from world import World, ACTIVE, RETURNING, CHARGING, READY, DRONE_STATE_NAMES

STEPS = 20000  # >= 6000; varios ciclos de batería para ver el régimen permanente


def run(seed: int = 0, steps: int = STEPS):
    w = World(seed=seed)
    w._init_battery(stagger=True)  # arranque escalonado (RNG sembrado del World)

    occ = np.zeros((steps, 4), dtype=int)
    relays = np.zeros(steps, dtype=int)
    min_active = w.n_active
    for t in range(steps):
        before = w.drone_state.copy()
        w._step_battery()
        relays[t] = int(np.sum((before != ACTIVE) & (w.drone_state == ACTIVE)))
        occ[t] = np.bincount(w.drone_state, minlength=4)
        min_active = min(min_active, int(occ[t, ACTIVE]))
    return w, occ, relays, min_active


def main():
    w, occ, relays, min_active = run(seed=0)
    half = len(occ) // 2
    avg = occ[half:].mean(axis=0)

    print("=== Ocupación media (régimen permanente, segunda mitad de %d pasos) ===" % len(occ))
    for s in (ACTIVE, CHARGING, READY, RETURNING):
        print("  %-9s %.2f" % (DRONE_STATE_NAMES[s], avg[s]))

    total = int(relays.sum())
    multi = int(np.sum(relays > 1))
    print("\n=== Relevos ===")
    print("  totales=%d en %d pasos (~1 cada %d pasos = %.0f s)"
          % (total, len(occ), len(occ) // max(total, 1), (len(occ) // max(total, 1)) * w.dt))
    print("  pasos con >1 relevo simultáneo: %d  (escalonado si ~0)" % multi)

    print("\n=== Invariantes ===")
    cubierto = (occ[:, ACTIVE] == w.n_active).all()
    print("  puestos activos SIEMPRE = %d:  %s (min observado=%d)" % (w.n_active, cubierto, min_active))
    print("  total de drones conservado (=%d):  %s" % (w.n_drones, bool((occ.sum(axis=1) == w.n_drones).all())))

    # Reproducibilidad: misma seed -> mismo escalonado y misma secuencia de relevos.
    _, occ2, relays2, _ = run(seed=0)
    print("\n=== Reproducibilidad (misma seed) ===")
    print("  ocupación idéntica:", np.array_equal(occ, occ2), "| relevos idénticos:", np.array_equal(relays, relays2))


if __name__ == "__main__":
    main()
