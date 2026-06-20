"""
baseline.py — Mundo de referencia CONGELADO (adversario vaca + lobo).

Punto de congelación tras calibrar vacas (calma + miedo) y lobo (Muro + remate).
Define el ADVERSARIO FIJO contra el que se medirán TODOS los coordinadores (FSM y
MARL), para que la comparación sea justa: mismo set de parámetros + mismas semillas.

⚠️ NO cambiar estos valores una vez empiece la comparación FSM vs MARL. Si hay que
recalibrar la dinámica vaca/lobo, hacerlo aquí y RE-MEDIR ambas ramas.

La batería/carga es ortogonal (gobierna qué drones están disponibles, no la dinámica
vaca/lobo) y no mueve este baseline. busca-huecos / amago son adversarios POSTERIORES
de la escalera de robustez, no este baseline.

Baseline medido con DummyCoordinator (drones quietos = sin intervención), N=100 seeds:
    predation = 49/100 = 49.0%   (Wilson 95% IC: 39.4% .. 58.7%)
Es la referencia que los coordinadores deben MEJORAR (bajar la depredación).
Ejecuta `python baseline.py` para re-medir y comprobar que no ha derivado.
"""

from __future__ import annotations
from world import World

# Config congelada (defaults resueltos en el momento de la calibración, EXPLÍCITOS para
# no depender de futuros cambios en los defaults de World).
BASELINE_PARAMS = dict(
    n_active_drones=4, n_reserve_drones=4, n_cows=6,
    wolves_min=1, wolves_max=5,
    parcel_size=(100.0, 100.0),
    safe_radius=12.0, station_radius=5.0, station_gap=1.0, station_dir=(0.0, 1.0),
    cow_spawn=(25.0, 75.0), cow_spread=10.0,
    dt=0.1, max_steps=600, drone_speed=6.0, capture_radius=3.0,
    # vacas (calma + miedo)
    cow_speed=1.2, cow_speed_jitter=0.4,
    k_cohesion_calm=0.4, k_cohesion_panic=1.2,
    k_separation=3.0, r_separation=4.0,
    wander_calm=1.0, wander_panic=0.35, r_fear=25.0, k_fence=1.5,
    # lobo (Muro + remate)
    wolf_speed=4.0, wolf_speed_near=4.0, d_safe=6.0,
    wolf_repulsion_radius=12.0, wolf_repulsion_strength=1.0,
    wolf_engage_band=3.0, wolf_pounce_isolation=2.5,
)

# Semillas de evaluación congeladas. Reportar SIEMPRE las métricas sobre este conjunto.
BASELINE_SEEDS = tuple(range(100))

# Baseline congelado (sin drones) para detectar deriva.
BASELINE_PREDATION_RATE = 0.49  # 49/100; Wilson 95% IC ~ [0.394, 0.587]


def build_baseline_world(seed: int) -> World:
    """Devuelve el World del adversario congelado para una semilla dada."""
    return World(seed=seed, **BASELINE_PARAMS)


if __name__ == "__main__":
    import math
    from collections import Counter
    from coordinators import DummyCoordinator
    from main import run_episode

    out = Counter()
    for s in BASELINE_SEEDS:
        w = build_baseline_world(s)
        _, m = run_episode(w, DummyCoordinator(w.n_drones))
        out[m["outcome"]] += 1

    n = len(BASELINE_SEEDS)
    k = out["predation"]
    p = k / n
    z = 1.96
    den = 1.0 + z * z / n
    cen = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    print("outcomes:", dict(out))
    print("predation = %d/%d = %.1f%%  (Wilson 95%% IC: %.1f%%..%.1f%%)"
          % (k, n, 100 * p, 100 * (cen - half), 100 * (cen + half)))
    drift = abs(p - BASELINE_PREDATION_RATE)
    print("congelado = %.1f%%  ->  %s"
          % (100 * BASELINE_PREDATION_RATE,
             "OK (sin deriva)" if drift <= 0.001 else "DERIVA %.1f pp" % (100 * drift)))
