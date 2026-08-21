"""
battery_check.py — Verificación macro de la batería y el RELEVO REALISTA (hand-off, SIN teletransporte).

Operación continua: con batería ~10 min y episodios de defensa más cortos, dentro de un episodio no
se completa un ciclo de relevo. Por eso aquí se dirige el subsistema en aislado durante varios ciclos:
cada paso = dinámica de vuelo (`_apply_drone_actions(None)`: los relevos VUELAN de verdad, los ACTIVE
y las reservas quietas) + `_step_battery()` (batería + dispatch/hand-off/retorno/strand), SIN tocar
vacas/lobo (quedan quietos) y sin RNG en el step -> reproducible bit a bit.

RELEVO DE CENTINELA (v3.7, Commit R — decisión de diseño del dueño; RE-GOLD consciente: INVIERTE la
pieza 5 de v3.0 "sin parálisis", cuyo test era su inverso exacto): al bajar del umbral el ACTIVE
ANUNCIA y SE CLAVA en su puesto (waypoint congelado; el mundo le RECHAZA comandos; sigue ACTIVE y
disuade QUIETO — v3.5: el sonido no exige movimiento); la central despacha al READY más cargado, que
vuela DIRECTO a las coordenadas del puesto; al estar encima (<= relay_handoff_tol) -> hand-off (el
relevo pasa a ACTIVE EN el puesto, el saliente a RETURNING -> CHARGING). PROHIBIDA la recolocación
de otros ACTIVE por causa del relevo (cada puesto es un sitio fijo). En este arnés SIN coordinador
(actions=None) el régimen 4/2/2 y el escalonado se verifican igual que siempre; el protocolo
centinela tiene tests dirigidos propios (clavado + pila completa con mundo GEMELO + STRANDED).
Bajo estrés (drenaje alto sostenido) las reservas pueden no dar abasto -> STRANDED (fallo esperado;
v3.0: el tirado se CONGELA donde esté — sin batería no se vuela).

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
    test_relevo_centinela()
    test_relevo_centinela_stack()
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


def test_relevo_centinela():
    """v3.7 (Commit R): el ACTIVE que ANUNCIA se CLAVA en su puesto — waypoint congelado en su
    posición, el mundo RECHAZA comandos (el coordinador lo intenta cada paso), no se mueve hasta
    el traspaso; el INCOMING vuela DIRECTO al puesto fijo y el hand-off ocurre a <=
    relay_handoff_tol; el saliente parte a cargar SOLO tras el traspaso; cobertura continua
    (min ACTIVE = n_active) y sin teletransporte. [RE-GOLD consciente: sustituye a
    test_relevo_sin_paralisis (v3.0, pieza 5) — su inverso exacto, por decisión del dueño.]"""
    print("\n=== Relevo de CENTINELA (v3.7, Commit R): clavado + vuelo directo al puesto + hand-off ===")
    w = World(seed=3)
    w._init_battery(stagger=False)               # 4 ACTIVE a tope, reservas READY
    na = w.n_active
    w.battery[na:] = 1.0                         # reservas llenas -> despacho inmediato
    w.battery[0] = w.announce_threshold - 0.01   # el dron 0 anuncia en el primer paso de batería

    target = w.drones[0] + np.array([120.0, 0.0])
    post = None                                  # el puesto se captura en el FLANCO del anuncio
    prev = w.drones.copy()
    handoff_step, max_jump, min_active = None, 0.0, na
    max_drift, incoming_j = 0.0, None
    for t in range(4000):
        wp = w.drone_waypoint.copy(); wp[0] = target     # el coordinador INTENTA moverlo cada paso
        w._apply_drone_actions(wp)
        w._step_battery()
        max_jump = max(max_jump, float(np.linalg.norm(w.drones - prev, axis=1).max()))
        prev = w.drones.copy()
        min_active = min(min_active, int((w.drone_state == ACTIVE).sum()))
        if w.drone_relief_hold[0] and w.drone_state[0] == ACTIVE:
            if post is None:
                post = w.drone_waypoint[0].copy()    # el puesto clavado (posición al anunciar)
            assert np.allclose(w.drone_waypoint[0], post), \
                "FALLO: el mundo ACEPTÓ un comando al clavado (v3.7 lo prohíbe)"
            max_drift = max(max_drift, float(np.linalg.norm(w.drones[0] - post)))
            inc = np.where(w.drone_state == INCOMING)[0]
            if inc.size:
                incoming_j = int(inc[0])
                assert np.allclose(w.drone_waypoint[incoming_j], w.drones[0]), \
                    "FALLO: el INCOMING no vuela al puesto"
        if handoff_step is None and w.drone_state[0] == RETURNING:
            handoff_step = t
            assert incoming_j is not None and w.drone_state[incoming_j] == ACTIVE
            d_fresh = float(np.linalg.norm(w.drones[incoming_j] - post))
            assert d_fresh <= w.relay_handoff_tol + 1.0, \
                f"FALLO: el fresco no está EN el puesto ({d_fresh:.2f} m)"
            break
    lim = DRONE_MAX_SPEED * w.dt
    assert handoff_step is not None, "FALLO: el hand-off al puesto fijo no llegó"
    print("  clavado: deriva máx %.2f m (<1 esperado: estaba parado) | hand-off en paso %s | "
          "fresco a %.2f m del puesto | min ACTIVE=%d | salto máx=%.3f (tope %.3f)"
          % (max_drift, handoff_step, d_fresh, min_active, max_jump, lim))
    assert max_drift < 1.0, "FALLO: el clavado se movió antes del traspaso"
    assert min_active == na, "FALLO: hueco de cobertura durante el relevo centinela"
    assert max_jump <= lim * 1.01, "FALLO: teletransporte durante el hand-off"

    # STRANDED SOLO si el fresco no llega a tiempo: (a) con reservas VACÍAS -> STRANDED y se
    # congela; (b) el bucle de arriba (reservas listas) jamás vio STRANDED.
    w2 = World(seed=4)
    w2._init_battery(stagger=False)
    w2.drone_state[w2.n_active:] = CHARGING      # reservas VACÍAS cargando -> sin relevo a tiempo
    w2.battery[w2.n_active:] = 0.0
    w2.battery[1] = w2.announce_threshold - 0.01
    far = w2.drones[1] + np.array([200.0, 0.0])
    for _ in range(3000):
        wp2 = w2.drone_waypoint.copy(); wp2[1] = far
        w2._apply_drone_actions(wp2)
        w2._step_battery()
        if w2.drone_state[1] == STRANDED:
            break
    assert w2.drone_state[1] == STRANDED, "FALLO: no llegó a STRANDED sin reservas"
    pos_strand = w2.drones[1].copy()
    for _ in range(50):
        wp2 = w2.drone_waypoint.copy(); wp2[1] = far
        w2._apply_drone_actions(wp2)
        w2._step_battery()
    drift = float(np.linalg.norm(w2.drones[1] - pos_strand))
    print("  STRANDED solo sin fresco a tiempo: congelado, deriva=%.2f m (<2 esperado)" % drift)
    assert drift < 2.0, "FALLO: un STRANDED (batería 0) sigue volando"
    print("  OK")


def test_relevo_centinela_stack():
    """v3.7, pila COMPLETA (ReactiveCoordinator estática v3.6, episodio solo-corzos ya
    tranquilo): 'ningún otro ACTIVE cambia de waypoint por causa del relevo' — contra un mundo
    GEMELO sin relevo forzado, los waypoints y posiciones de los DEMÁS ACTIVE son BIT A BIT
    idénticos durante anuncio -> hand-off, y el fresco acaba EN el puesto. El anuncio se fuerza
    en RÉGIMEN (centinelas APARCADOS en sus ranuras): es el dominio del protocolo. [Salvedad
    documentada: un anuncio EN TRÁNSITO (p.ej. volviendo de ESCOLTA a patrulla) congela al bajo
    fuera de su ranura y el order-matching puede re-emparejar UNA vez a los demás en ese
    instante — inherente a _assign, no un movimiento comandado por el relevo.]"""
    print("\n=== Relevo centinela en pila completa (gemelo bit a bit; cero recolocaciones) ===")
    from baseline import build_world
    from coordinators import ReactiveCoordinator

    def make(seed):
        w = build_world(seed, "corzos")
        c = ReactiveCoordinator(w)
        w.reset()
        return w, c

    wa = wb = ca = cb = t0 = None
    for cand in (1, 2, 3, 5, 8, 13):                     # 1ª semilla con ventana tranquila
        wa, ca = make(cand)
        wb, cb = make(cand)
        t0 = None
        for t in range(6000):
            wa.step(ca.act(wa.get_observation()))
            wb.step(cb.act(wb.get_observation()))
            if wa.n_corzos > 0 and bool(wa.corzo_dismissed.all()) and \
                    not wa.drone_investigating.any():
                t0 = t
                break
        if t0 is not None:
            print("  semilla %d: corzos descartados en t=%d (ventana tranquila)" % (cand, t0))
            break
    assert t0 is not None, "FALLO precondición: ninguna semilla llegó a ventana tranquila"
    # RÉGIMEN: centinelas aparcados en sus ranuras (50 ticks seguidos con todos a < 0.5 m)
    quiet = 0
    for _ in range(8000):
        wa.step(ca.act(wa.get_observation()))
        wb.step(cb.act(wb.get_observation()))
        act = np.where((wa.drone_state == ACTIVE) & ~wa.drone_investigating)[0]
        err = float(np.linalg.norm(wa.drones[act] - wa.drone_waypoint[act], axis=1).max()) \
            if act.size else 1e9
        quiet = quiet + 1 if err < 0.5 else 0
        if quiet >= 50:
            break
    assert quiet >= 50, "FALLO precondición: la patrulla no llegó a régimen (aparcados)"
    res = np.where((wa.drone_state == CHARGING) | (wa.drone_state == READY))[0]
    assert res.size > 0, "sin reservas"
    wa.battery[res] = 1.0; wb.battery[res] = 1.0         # mismas reservas LLENAS en ambos gemelos
    wa.step(ca.act(wa.get_observation()))                # un paso: las cargadas pasan a READY
    wb.step(cb.act(wb.get_observation()))
    assert (wa.drone_state[res] == READY).any(), "las reservas no pasaron a READY"
    low = int(np.where(wa.drone_state == ACTIVE)[0][0])
    wa.battery[low] = wa.announce_threshold - 0.01       # SOLO el gemelo A fuerza el anuncio
    post = None                                          # se captura en el flanco del anuncio
    others = [i for i in np.where(wa.drone_state == ACTIVE)[0] if i != low]
    handoff = False
    for t in range(2500):
        wa.step(ca.act(wa.get_observation()))
        wb.step(cb.act(wb.get_observation()))
        assert not wa.drone_investigating.any() and not wb.drone_investigating.any(), \
            "precondición rota: investigación durante la ventana"
        assert np.array_equal(wa.drone_waypoint[others], wb.drone_waypoint[others]), \
            "FALLO: un ACTIVE ajeno cambió de waypoint por causa del relevo"
        assert np.array_equal(wa.drones[others], wb.drones[others]), \
            "FALLO: un ACTIVE ajeno se movió distinto por causa del relevo"
        if wa.drone_relief_hold[low]:
            if post is None:
                post = wa.drone_waypoint[low].copy()     # el puesto clavado (al anunciar)
            assert np.allclose(wa.drone_waypoint[low], post, atol=1e-9), \
                "FALLO: el clavado cambió de waypoint"
        if post is not None and not handoff and wa.drone_state[low] == RETURNING:
            handoff = True
            fresh = [j for j in np.where(wa.drone_state == ACTIVE)[0] if j not in others]
            assert len(fresh) == 1
            d = float(np.linalg.norm(wa.drones[fresh[0]] - post))
            assert d <= wa.relay_handoff_tol + 1.0, f"fresco a {d:.2f} m del puesto"
            print("  hand-off en t=+%d; fresco (dron %d) a %.2f m del puesto; %d ACTIVE ajenos "
                  "bit a bit idénticos al gemelo" % (t, fresh[0], d, len(others)))
        if handoff and wa.drone_state[low] == CHARGING:
            break
    assert handoff, "FALLO: no hubo hand-off en la ventana"
    print("  OK")


if __name__ == "__main__":
    main()
