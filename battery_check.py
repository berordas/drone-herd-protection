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

    # Estrés: drenaje sostenido alto -> las reservas no dan abasto -> STRANDED (fallo esperado, no bug). v2.4: con
    # la carga 1.5x MÁS RÁPIDA (charge_full≈160 s vs 300 s), el estrés 2.5x ya NO agota las reservas (dan abasto);
    # se sube a 5.0x (drenaje/carga > 1 -> depleción neta) para seguir verificando el mecanismo de STRANDED.
    STRESS = 5.0
    _, _, _, min_active_s, stranded_s, _ = run(seed=0, stress=STRESS)
    print("\n=== Estrés (drenaje %.1fx sostenido: moverse a tope sin parar; carga v2.4 más rápida) ===" % STRESS)
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

    test_reset_baterias()
    test_charge_ratio()
    print("\nbattery_check: TODO OK.")


def test_reset_baterias():
    """v2.4: arranque de EPISODIO con baterías aleatorias + reserva ESPEJO (substream separado)."""
    print("\n=== Arranque de EPISODIO (v2.4): baterías aleatorias [0.25,1] + reserva espejo (substream) ===")
    w = World(seed=7, corzos_max=3, episode_kind="mixto")   # reset ya corrido en el constructor
    na, nr = w.n_active, w.n_reserve
    act, res = w.battery[:na], w.battery[na:na + nr]
    print("  activos EN VUELO: %s (todos en [%.2f,1]) | reservas EN CARGA (espejo 1-pareja): %s"
          % (np.round(act, 3), w.battery_init_min, np.round(res, 3)))
    assert (act >= w.battery_init_min - 1e-9).all() and (act <= 1.0 + 1e-9).all(), "FALLO: activos fuera de [init_min,1]"
    assert np.allclose(res, 1.0 - act[:nr]), "FALLO: la reserva NO es el espejo exacto (1 - pareja)"
    assert (w.drone_state[:na] == ACTIVE).all() and (w.drone_state[na:] == CHARGING).all(), "FALLO: estados de arranque"
    assert (w.battery[:na] > w.announce_threshold).all(), "FALLO: algún activo arranca bajo el umbral (dispararía relevo en t=0)"
    # Reproducible + SUBSTREAM separado (cambiar battery_init_min NO perturba los spawns).
    w2 = World(seed=7, corzos_max=3, episode_kind="mixto")
    assert np.allclose(w.battery, w2.battery), "FALLO: baterías no reproducibles"
    a = World(seed=5, corzos_max=3, episode_kind="mixto", battery_init_min=0.25)
    b = World(seed=5, corzos_max=3, episode_kind="mixto", battery_init_min=0.90)
    same_spawn = (a.n_wolves == b.n_wolves and np.allclose(a.wolves, b.wolves)
                  and np.allclose(a.cows, b.cows) and np.allclose(a.corzos, b.corzos))
    diff_bat = not np.allclose(a.battery[:a.n_active], b.battery[:b.n_active])
    print("  reproducible=OK | substream: distinto init_min -> spawns idénticos=%s, baterías distintas=%s" % (same_spawn, diff_bat))
    assert same_spawn and diff_bat, "FALLO: el substream de batería perturba los spawns (o no cambia las baterías)"
    print("  OK")


def test_charge_ratio():
    """v2.4: cargar recupera ≈ CHARGE_TO_FLIGHT_RATIO x lo que el vuelo PLENO gasta por segundo."""
    from world import CHARGE_TO_FLIGHT_RATIO, DRONE_MOVE_DRAIN
    print("\n=== Ratio de carga (v2.4): carga = %.1fx el gasto de vuelo PLENO ===" % CHARGE_TO_FLIGHT_RATIO)
    w = World(seed=0)
    flight_full = w.drain_rate_active * (1.0 + DRONE_MOVE_DRAIN)   # gasto a vuelo pleno (fracción/s)
    # Medida empírica: UN dron CHARGING de 0 a lleno; cuenta el tiempo -> tasa de recuperación (el resto READY,
    # sin ACTIVE -> el paso de batería solo carga; sin dispatch/relevos que interfieran).
    w.drone_state[:] = READY
    w.drone_state[0] = CHARGING; w.battery[:] = 1.0; w.battery[0] = 0.0
    steps = 0
    while w.battery[0] < 1.0 - 1e-9 and steps < 100000:
        w._step_battery(); steps += 1
    charge_rate_meas = 1.0 / (steps * w.dt)                        # fracción/s recuperada
    ratio_meas = charge_rate_meas / flight_full
    print("  gasto vuelo pleno=%.5f/s | carga medida=%.5f/s | ratio=%.3f (esperado %.2f) | carga completa=%.0f s (~160)"
          % (flight_full, charge_rate_meas, ratio_meas, CHARGE_TO_FLIGHT_RATIO, steps * w.dt))
    assert abs(ratio_meas - CHARGE_TO_FLIGHT_RATIO) < 0.02, "FALLO: la carga no recupera 1.5x el vuelo pleno"
    assert abs(steps * w.dt - 160.0) < 1.0, "FALLO: el tiempo de carga completa no es ~160 s"
    print("  OK")


if __name__ == "__main__":
    main()
