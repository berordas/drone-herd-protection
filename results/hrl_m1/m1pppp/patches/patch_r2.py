"""Commit R parte 2 — re-gold consciente de battery_check (test_relevo_sin_paralisis es el
INVERSO de v3.7 por decision de diseno del dueno) + tests nuevos del protocolo centinela."""
import re
p = 'battery_check.py'
s = open(p).read()

old = """Relevo REALISTA (v3.0, SIN PARÁLISIS): al bajar del umbral, el ACTIVE ANUNCIA (drone_relief_hold) pero
SIGUE comandable y cubriendo/moviéndose (antes se clavaba en su puesto = agujero en la defensa); la
central despacha al READY más cargado, que VUELA PERSIGUIENDO su posición viva; al estar encima ->
hand-off (el relevo pasa a ACTIVE, el bajo a RETURNING -> CHARGING). Cobertura CONTINUA (nadie se va
antes de que llegue el relevo). En este arnés SIN coordinador (actions=None) el anunciado conserva su
waypoint (su puesto) -> el régimen 4/2/2 y el escalonado se verifican igual que siempre; la pieza 5
(anunciado que SIGUE moviéndose bajo comando + hand-off a blanco móvil) tiene test dirigido propio."""
new = """RELEVO DE CENTINELA (v3.7, Commit R — decisión de diseño del dueño; RE-GOLD consciente: INVIERTE la
pieza 5 de v3.0 "sin parálisis", cuyo test era su inverso exacto): al bajar del umbral el ACTIVE
ANUNCIA y SE CLAVA en su puesto (waypoint congelado; el mundo le RECHAZA comandos; sigue ACTIVE y
disuade QUIETO — v3.5: el sonido no exige movimiento); la central despacha al READY más cargado, que
vuela DIRECTO a las coordenadas del puesto; al estar encima (<= relay_handoff_tol) -> hand-off (el
relevo pasa a ACTIVE EN el puesto, el saliente a RETURNING -> CHARGING). PROHIBIDA la recolocación
de otros ACTIVE por causa del relevo (cada puesto es un sitio fijo). En este arnés SIN coordinador
(actions=None) el régimen 4/2/2 y el escalonado se verifican igual que siempre; el protocolo
centinela tiene tests dirigidos propios (clavado + pila completa con mundo GEMELO + STRANDED)."""
assert old in s, "P1"; s = s.replace(old, new, 1)

i0 = s.index("def test_relevo_sin_paralisis():")
i1 = s.index('if __name__ == "__main__":')
nuevo = '''def test_relevo_centinela():
    """v3.7 (Commit R): el ACTIVE que ANUNCIA se CLAVA en su puesto — waypoint congelado en su
    posición, el mundo RECHAZA comandos (el coordinador lo intenta cada paso), no se mueve hasta
    el traspaso; el INCOMING vuela DIRECTO al puesto fijo y el hand-off ocurre a <=
    relay_handoff_tol; el saliente parte a cargar SOLO tras el traspaso; cobertura continua
    (min ACTIVE = n_active) y sin teletransporte. [RE-GOLD consciente: sustituye a
    test_relevo_sin_paralisis (v3.0, pieza 5) — su inverso exacto, por decisión del dueño.]"""
    print("\\n=== Relevo de CENTINELA (v3.7, Commit R): clavado + vuelo directo al puesto + hand-off ===")
    w = World(seed=3)
    w._init_battery(stagger=False)               # 4 ACTIVE a tope, reservas READY
    na = w.n_active
    w.battery[na:] = 1.0                         # reservas llenas -> despacho inmediato
    w.battery[0] = w.announce_threshold - 0.01   # el dron 0 anuncia en el primer paso de batería

    target = w.drones[0] + np.array([120.0, 0.0])
    post = w.drones[0].copy()                    # su puesto (está parado en él)
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
            assert np.allclose(w.drone_waypoint[0], post), \\
                "FALLO: el mundo ACEPTÓ un comando al clavado (v3.7 lo prohíbe)"
            max_drift = max(max_drift, float(np.linalg.norm(w.drones[0] - post)))
            inc = np.where(w.drone_state == INCOMING)[0]
            if inc.size:
                incoming_j = int(inc[0])
                assert np.allclose(w.drone_waypoint[incoming_j], w.drones[0]), \\
                    "FALLO: el INCOMING no vuela al puesto"
        if handoff_step is None and w.drone_state[0] == RETURNING:
            handoff_step = t
            assert incoming_j is not None and w.drone_state[incoming_j] == ACTIVE
            d_fresh = float(np.linalg.norm(w.drones[incoming_j] - post))
            assert d_fresh <= w.relay_handoff_tol + 1.0, \\
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
    idénticos durante anuncio -> hand-off, y el fresco acaba EN el puesto."""
    print("\\n=== Relevo centinela en pila completa (gemelo bit a bit; cero recolocaciones) ===")
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
            if wa.n_corzos > 0 and bool(wa.corzo_dismissed.all()) and \\
                    not wa.drone_investigating.any():
                t0 = t
                break
        if t0 is not None:
            print("  semilla %d: corzos descartados en t=%d (ventana tranquila)" % (cand, t0))
            break
    assert t0 is not None, "FALLO precondición: ninguna semilla llegó a ventana tranquila"
    low = int(np.where(wa.drone_state == ACTIVE)[0][0])
    ready = np.where(wa.drone_state == READY)[0]
    assert ready.size > 0
    wa.battery[ready] = 1.0; wb.battery[ready] = 1.0     # mismas reservas en ambos
    wa.battery[low] = wa.announce_threshold - 0.01       # SOLO el gemelo A fuerza el anuncio
    post = wa.drones[low].copy()
    others = [i for i in np.where(wa.drone_state == ACTIVE)[0] if i != low]
    handoff = False
    for t in range(2500):
        wa.step(ca.act(wa.get_observation()))
        wb.step(cb.act(wb.get_observation()))
        assert not wa.drone_investigating.any() and not wb.drone_investigating.any(), \\
            "precondición rota: investigación durante la ventana"
        assert np.array_equal(wa.drone_waypoint[others], wb.drone_waypoint[others]), \\
            "FALLO: un ACTIVE ajeno cambió de waypoint por causa del relevo"
        assert np.array_equal(wa.drones[others], wb.drones[others]), \\
            "FALLO: un ACTIVE ajeno se movió distinto por causa del relevo"
        if wa.drone_relief_hold[low]:
            assert np.allclose(wa.drone_waypoint[low], post, atol=1e-9), \\
                "FALLO: el clavado cambió de waypoint"
        if not handoff and wa.drone_state[low] == RETURNING:
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


'''
s = s[:i0] + nuevo + s[i1:]
s = s.replace("""    test_relevo_sin_paralisis()""",
              """    test_relevo_centinela()
    test_relevo_centinela_stack()""", 1)
assert "def test_relevo_sin_paralisis" not in s and "    test_relevo_sin_paralisis()" not in s, "P2"
open(p, 'w').write(s)
print("battery_check.py: R OK")
