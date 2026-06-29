"""
escort_check.py — Verificación del TERMINAL del episodio de escolta + la máquina de fases.

Construye el "juez" ANTES de añadir el guiado al refugio (bandera #13: "verificar el terminal antes
de construir comportamientos encima"). Cubre los tres terminales y sus contadores, la máquina de fases
VIGILANCIA->ESCOLTA, y los DOS ganchos: (a) res en el establo = a salvo y NO cazable; (b) si la presa
fijada se refugia, la manada RE-SELECCIONA (única re-fijación permitida). Drones quietos (DummyCoordinator).

  0) Disparador en DOS etapas: detección (r_detect)->SOSPECHA + 1 dron investigando (+ mensaje al
     coordinador); confirmación (r_confirm)->ESCOLTA + dron liberado; aparcados no cuentan.
  0b) El dron INVESTIGA (se mueve al contacto) y confirma; PRECEDENCIA reflejo>coordinador; buy-time.
  0c) Investiga el dron ACTIVE LIBRE MÁS CERCANO al contacto (no aleatorio; ocupado->siguiente; determinista).
  1) ÉXITO forzado
  1b) ÉXITO ORGÁNICO (lobo-solo SIN terneros -> el rebaño escapa) + lobo-solo CON ternero -> TIMEOUT + Bug 2 (ternero entra tras su madre).
  1c) NO-HOLONÓMICO en ESCOLTA: HUIR / ENCARAR-PIN (SOLO la presa) / REANUDAR + Bug 1 (no-fijada huye con lobo cerca); terneros anclados.
  1d) DISUASIÓN del dron (radio CORTO + BORDEO): ESQUIVA+FRENA / PARCIAL (uno huye, otros aguantan) / APARTA AL QUE SE ACERCA (previene pines de lejos).
  1e) ADULTA CLAVADA matable: ataque ENVOLVENTE (rumbos repartidos ~N/E/S/O); con/sin dron (la disuasión retrasa, no invulnerabiliza).
  1f) Las vacas NO-fijadas RODEAN a los lobos al HUIR (no atraviesan) y siguen llegando; la presa fijada sigue ENCARANDO.
  1g) La MADRE no abandona al ternero al HUIR: avanza a calf_speed (la cría es más lenta), a su lado, llegan juntos; pareja más lenta; fijado->ENCARAR intacto.
  1h) El LOBO no se clava en la ZONA SEGURA: la BORDEA (tangencial en la frontera, no entra) y suelta a la presa refugiada al instante (re-fija fuera).
  1i) CORZOS (3c): cuerpo NO-amenaza (deambula+HUYE de lobos/drones, no caza); detectable como contacto; ORÁCULO a r_confirm (lobo->ESCOLTA, corzo->descarta); 3 tipos de episodio ~1/3.
  9b) SEVERIDAD por TIPO (corzos activos): solo-lobos ~v2 / solo-corzos = 0 / mixto ≈ solo-lobos (MEDIDA).
  2) DEPREDACIÓN forzada (multi-muerte; cuanta más, peor -> cuenta)
  3) TIMEOUT forzado
  4) Refugio = soltar presa (re-fijación SOLO al refugiarse; 0 en otro caso)
  5) Exclusión del lobo (nunca dentro del establo)
  6) Reproducibilidad (mismo estado terminal + contadores)
  7) Sin regresiones (face_check.py + battery_check.py siguen verdes)
  8) Timing de las dos etapas: paso de SOSPECHA y paso de ESCOLTA (el hueco = tiempo de investigación).
  9) Tasa de la escolta (Dummy + guiado + DISUASIÓN) candidata a v2: MEDIDA (tasa + severidad), no objetivo.
  + Ojeo: animación por terminal + DISUASIÓN (despeja un pin) + arco detección->ESCOLTA + BUCLE COMPLETO.
"""

import matplotlib
matplotlib.use("Agg")   # sin ventana: guardamos las animaciones a disco
import subprocess
import sys
import numpy as np
from world import World, ACTIVE, CHARGING, READY, DETER_RADIUS, DETER_REPULSION, DETER_SLOWDOWN
from coordinators import DummyCoordinator
from render import render_episode

NO_CALVES = (1.0, 0.0, 0.0)
ONE_CALF = (0.0, 1.0, 0.0)


def _run(w, cap=None):
    """Corre un episodio con drones quietos hasta el terminal. Devuelve el info del último step."""
    c = DummyCoordinator(w.n_drones)
    cap = cap if cap is not None else w.max_episode_steps
    info = {"status": w.status, "phase": w.phase, "n_safe": 0, "n_depredadas": 0, "n_fuera": 0,
            "terminal_step": None}
    for _ in range(cap + 1):
        _, _, term, trunc, info = w.step(c.act(None))
        if term or trunc:
            break
    return info


# ---------------------------------------------------------------------------- #
def test_trigger_dos_etapas():
    print("=== 0) Disparador en DOS etapas: detección->SOSPECHA, confirmación->ESCOLTA ===")
    corner = np.array([[0.0, 0.0], [0.0, 5.0], [5.0, 0.0], [5.0, 5.0]])   # 4 activos en una esquina

    def fresh():
        w = World(seed=0, wolves_min=1, wolves_max=1)
        w.phase = "VIGILANCIA"
        w.drone_state[:] = READY            # todos aparcados...
        w.drone_state[:4] = ACTIVE          # ...salvo 4 EN VUELO, en una esquina
        w.drones[:4] = corner
        w.drone_investigating[:] = False
        return w

    w0 = World(seed=0)
    rd, rc = w0.r_detect, w0.r_confirm
    # (1) lobo lejos de TODOS los activos -> sigue VIGILANCIA, nadie investiga.
    w = fresh(); w.drones[4:] = 1.0; w.wolves[:] = [[100.0, 100.0]]   # ~134 m del activo más cercano
    w._update_phase()
    assert w.phase == "VIGILANCIA" and not w.drone_investigating.any(), "FALLO: disparó fuera de r_detect"
    # (2) lobo a < r_detect pero > r_confirm de un activo -> SOSPECHA (NO ESCOLTA todavía), un dron investiga.
    w.wolves[:] = [[60.0, 60.0]]                                      # ~78 m del activo (5,5): <100, >40
    w._update_phase()
    assert w.phase == "SOSPECHA", "FALLO: detección no pasó a SOSPECHA"
    assert int(w.drone_investigating.sum()) == 1, "FALLO: no hay exactamente un dron INVESTIGANDO"
    inv = int(np.where(w.drone_investigating)[0][0])
    msg = w.get_observation()["investigations"]
    assert len(msg) == 1 and msg[0]["drone_id"] == inv and np.allclose(msg[0]["contact_pos"], [60.0, 60.0]), \
        "FALLO: mensaje al coordinador incorrecto (id/contacto)"
    # (3) acercar el contacto a <= r_confirm del investigador -> ESCOLTA y el dron se libera.
    w.wolves[:] = [w.drones[inv] + [0.0, rc - 5.0]]                   # a r_confirm-5 del investigador
    w._update_phase()
    assert w.phase == "ESCOLTA", "FALLO: confirmación no pasó a ESCOLTA"
    assert not w.drone_investigating.any(), "FALLO: el dron no se liberó tras confirmar"
    # (4) lobo pegado a un dron APARCADO (CHARGING) pero lejos de los activos -> NO dispara.
    w = fresh(); w.drone_state[4] = CHARGING; w.drones[4] = [100.0, 100.0]; w.wolves[:] = [[100.0, 100.0]]
    w._update_phase()
    assert w.phase == "VIGILANCIA", "FALLO: un dron aparcado disparó la detección"
    print("  r_detect=%.0f m -> SOSPECHA + 1 dron investigando (+ mensaje); r_confirm=%.0f m -> ESCOLTA + liberado;"
          " aparcado no dispara" % (rd, rc))
    print("  OK\n")


def test_investigar_confirmar():
    print("=== 0b) El dron INVESTIGA (se mueve al contacto) y la PRECEDENCIA reflejo/coordinador ===")
    w = World(seed=8)
    c = DummyCoordinator(w.n_drones)
    susp = esc = None
    inv = inv_pos0 = d_confirm_herd = None
    moved = 0.0
    for _ in range(2000):
        obs, _, term, trunc, info = w.step(c.act(None))
        if susp is None and info["phase"] == "SOSPECHA":
            susp = w.step_count
            inv = int(np.where(w.drone_investigating)[0][0])
            inv_pos0 = w.drones[inv].copy()
            # PRECEDENCIA: el coordinador intenta mover al investigador a otro sitio -> debe IGNORARSE.
            w.command_waypoint(inv, np.array([5.0, 5.0]))
        if susp is not None and esc is None and w.drone_investigating.any():
            moved = float(np.linalg.norm(w.drones[inv] - inv_pos0))
        if esc is None and info["phase"] == "ESCOLTA":
            esc = w.step_count
            # "buy time": distancia del contacto (lobo) al rebaño al CONFIRMAR.
            live = w.cow_alive & ~w.cow_safe
            d_confirm_herd = float(np.linalg.norm(w.wolves.mean(axis=0) - w.cows[live].mean(axis=0)))
            break
    assert susp is not None and esc is not None and esc > susp, "FALLO: no recorrió SOSPECHA->ESCOLTA"
    assert moved > 10.0, "FALLO: el dron investigador no se movió hacia el contacto (precedencia o reflejo roto)"
    print("  SOSPECHA paso %d -> ESCOLTA paso %d (investigación=%d pasos) | el dron voló %.1f m al contacto"
          % (susp, esc, esc - susp, moved))
    print("  precedencia OK (el comando del coordinador al investigador se ignoró: voló al lobo, no a (5,5))")
    print("  buy time: contacto a %.0f m del rebaño al confirmar (investigar activamente confirma lejos)"
          % d_confirm_herd)
    print("  OK\n")


def test_investigador_mas_cercano():
    print("=== 0c) Investiga el dron ACTIVE LIBRE MÁS CERCANO al contacto (no aleatorio; determinista) ===")
    # 4 drones ACTIVE en las cuatro esquinas de un cuadrado de 100 m; el resto aparcado (no vigila).
    pos = np.array([[0.0, 0.0], [100.0, 0.0], [0.0, 100.0], [100.0, 100.0]])

    def fresh():
        w = World(seed=0, wolves_min=1, wolves_max=1)
        w.phase = "VIGILANCIA"
        w.drone_state[:] = READY            # todos aparcados...
        w.drone_state[:4] = ACTIVE          # ...salvo 4 EN VUELO, en las esquinas
        w.drones[:4] = pos
        w.drones[4:] = 1.0
        w.drone_investigating[:] = False
        return w

    # (1) El MÁS CERCANO va: contacto cerca de cada esquina k, en la banda (r_confirm, r_detect) para que
    # se quede en SOSPECHA (un investigador asignado, sin confirmar aún). Los 4 lo DETECTAN; gana el más
    # cercano (= el que llega antes), no el de menor índice.
    inward = np.array([[35.0, 35.0], [-35.0, 35.0], [35.0, -35.0], [-35.0, -35.0]])  # ~49.5 m hacia el centro
    for k in range(4):
        w = fresh()
        w.wolves[:] = [pos[k] + inward[k]]
        w._update_phase()
        d_all = np.linalg.norm(pos - w.wolves[0], axis=1)
        n_detect = int((d_all <= w.r_detect).sum())
        assert w.phase == "SOSPECHA" and int(w.drone_investigating.sum()) == 1, \
            "FALLO: no quedó exactamente 1 investigador en SOSPECHA (esquina %d)" % k
        inv = int(np.where(w.drone_investigating)[0][0])
        assert inv == k, "FALLO: investigó el dron %d, no el más cercano (%d)" % (inv, k)
        assert np.isclose(d_all[inv], d_all.min()) and n_detect >= 2, \
            "FALLO: el investigador no está a distancia mínima o no había varios detectando"
    print("  el MÁS CERCANO investiga en las 4 posiciones (dist investigador->contacto = mínima; 4 detectan)")

    # (2) Ocupado -> siguiente más cercano LIBRE: con el más cercano ya investigando otro contacto, va el 2º.
    w = fresh()
    w.wolves[:] = [[70.0, 40.0]]                          # contacto que DETECTAN los 4 (todos < r_detect)
    order = list(np.argsort(np.linalg.norm(pos - w.wolves[0], axis=1)))   # ranking por cercanía
    nearest, second = int(order[0]), int(order[1])
    free = (w.drone_state == ACTIVE).copy()
    free[nearest] = False                                # el más cercano OCUPADO (investigando otro)
    pick = w._pick_investigator(free, w.wolves)
    assert pick == second, "FALLO: con el más cercano (%d) ocupado no eligió el 2º (%d), eligió %d" % (nearest, second, pick)
    print("  el más cercano (%d) ocupado -> va el siguiente más cercano libre (%d)" % (nearest, second))

    # (3) Determinista: misma escena -> mismo investigador; empate -> menor índice (sin aleatoriedad).
    a = fresh(); a.wolves[:] = [[50.0, 60.0]]; a._update_phase()
    b = fresh(); b.wolves[:] = [[50.0, 60.0]]; b._update_phase()
    assert np.array_equal(a.drone_investigating, b.drone_investigating), "FALLO: la elección no es determinista"
    w = fresh(); w.wolves[:] = [[50.0, 0.0]]              # equidistante de los drones 0 y 1 -> empate exacto
    tie = w._pick_investigator(w.drone_state == ACTIVE, w.wolves)
    assert tie == 0, "FALLO: el empate no se rompió por menor índice (eligió %d)" % tie
    print("  misma escena -> mismo dron; empate (drones 0 y 1) -> menor índice (0)")
    print("  OK\n")


def test_exito():
    print("=== 1) ÉXITO forzado (todas refugiadas, lobo lejos) ===")
    w = World(seed=5, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    w.cows[:] = w.safe_zone[:2] + w.rng.uniform(-2.0, 2.0, size=(w.n_cows, 2))  # dentro del establo
    w.wolves[:] = np.array([[2.0, 2.0]])                                        # lobo lejos
    info = _run(w, cap=20)
    print("  status=%s  n_safe=%d  n_depredadas=%d  n_fuera=%d  paso=%s"
          % (info["status"], info["n_safe"], info["n_depredadas"], info["n_fuera"], info["terminal_step"]))
    assert info["status"] == "success", "FALLO: no se alcanzó ÉXITO"
    assert info["n_safe"] == w.n_cows and info["n_depredadas"] == 0 and info["n_fuera"] == 0
    print("  OK\n")


def test_exito_organico():
    print("=== 1b) ÉXITO ORGÁNICO (rebaño escapa) + lobo-solo + Bug 2 (ternero entra tras su madre) ===")
    # ÉXITO orgánico: un lobo SOLO SIN terneros NO fija presa (no se compromete) -> NINGUNA vaca es
    # "pinnable" (Bug 1) -> todas HUYEN y se refugian -> ÉXITO sin forzar estados.
    w = World(seed=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    info = {"status": w.status}
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        if term or trunc:
            break
    print("  lobo-solo SIN terneros: status=%s  n_safe=%d/%d  cazadas=%d  (no fija presa -> todas huyen -> ÉXITO)"
          % (info["status"], info["n_safe"], w.n_cows, info["n_depredadas"]))
    assert info["status"] == "success" and info["n_safe"] == w.n_cows, "FALLO: el rebaño no escapó al lobo solo"
    # Lobo-solo CON ternero -> TIMEOUT: fija el ternero -> su DEFENSORA queda CLAVADA defendiéndolo (no
    # puede flanquear -> no muere; la pareja no llega). Es el resultado "sin ayuda" (la presa fijada clavada).
    w2 = World(seed=1, wolves_min=1, wolves_max=1, calf_count_probs=ONE_CALF)
    c2 = DummyCoordinator(w2.n_drones)
    info2 = {"status": w2.status}
    while True:
        _, _, term, trunc, info2 = w2.step(c2.act(None))
        if term or trunc:
            break
    print("  lobo-solo CON ternero: status=%s  n_safe=%d  cazadas=%d  (fija el ternero -> defensora clavada -> TIMEOUT)"
          % (info2["status"], info2["n_safe"], info2["n_depredadas"]))
    assert info2["status"] == "timeout" and info2["n_depredadas"] == 0, \
        "FALLO: lobo-solo+ternero debería dar TIMEOUT (defensora clavada, sin muerte)"
    # Bug 2: un ternero cuya MADRE ya está a salvo (dentro) sigue migrando hasta ENTRAR él, y se marca a
    # salvo SOLO cuando el ternero está dentro (no cuando lo está su madre).
    w3 = World(seed=4, wolves_min=0, wolves_max=0, calf_count_probs=ONE_CALF)
    c3 = DummyCoordinator(w3.n_drones)
    w3.phase = "ESCOLTA"
    dfn, ctr, thr = int(w3.calf_defender[0]), w3.safe_zone[:2], w3.safe_zone[2] - w3.refuge_margin
    w3.cows[dfn] = ctr + np.array([thr - 2.0, 0.0]); w3.cow_safe[dfn] = True; w3.cow_vel[dfn] = 0.0
    w3.calves[0] = ctr + np.array([thr + 1.5, 0.0]); w3.calf_vel[0] = 0.0   # ternero FUERA del umbral
    assert not w3.calf_safe[0], "el ternero no debería estar a salvo por estar su madre dentro"
    for _ in range(80):
        w3.step(c3.act(None))
        if w3.calf_safe[0]:
            break
    inside = float(np.linalg.norm(w3.calves[0] - ctr)) <= thr + 1e-6
    print("  Bug 2: madre a salvo dentro; el ternero entra -> calf_safe=%s, ternero dentro=%s" % (bool(w3.calf_safe[0]), inside))
    assert w3.calf_safe[0] and inside, "FALLO(Bug 2): el ternero no entró / no se marcó a salvo al entrar él mismo"
    print("  OK\n")


def test_no_holonomico():
    print("=== 1c) NO-HOLONÓMICO en ESCOLTA: HUIR / ENCARAR-PIN (solo la presa) / REANUDAR ===")
    # La vaca PRESA corre HACIA DONDE MIRA; huir y dar la cara son EXCLUYENTES. (cow0 = presa fijada -> es
    # la única "pinnable"; ver Bug 1 abajo para las no-fijadas.)
    w = World(seed=5, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"
    w.cow_speeds[0] = w.cow_speed
    w.pack_prey, w.pack_prey_kind = 0, "adult"             # la cow0 es la PRESA fijada -> puede ENCARAR (pin)
    w.cows[0] = w.safe_zone[:2] + np.array([120.0, 0.0])
    w.cow_heading[0] = 0.0                                  # mira AL ESTE (lejos del establo): debe girar
    w.wolves[0] = w.safe_zone[:2] + np.array([400.0, 400.0]); w.wolf_vel[0] = 0.0   # lobo MUY lejos
    # HUIR: avanza hacia el establo; la velocidad es SIEMPRE a lo largo del heading (no-holonómico).
    max_lat, d0 = 0.0, float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    for _ in range(60):
        p = w.cows[0].copy()
        w.step(c.act(None))
        v = w.cows[0] - p
        if np.linalg.norm(v) > 1e-6:
            h = np.array([np.cos(w.cow_heading[0]), np.sin(w.cow_heading[0])])
            max_lat = max(max_lat, abs(v[0] * h[1] - v[1] * h[0]) / np.linalg.norm(v))
    d1 = float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    print("  HUIR: dist al establo %.1f->%.1f m (baja) | máx lateral de v=%.4f (~0 = no-holonómico)" % (d0, d1, max_lat))
    assert d1 < d0 - 2.0, "FALLO: la vaca no huyó hacia el establo"
    assert max_lat < 1e-3, "FALLO: la velocidad NO es a lo largo del heading (sería holonómico)"
    # PIN: un lobo mantenido dentro de r_notice clava a la vaca (se para y lo encara).
    moved = 0.0
    for _ in range(40):
        p = w.cows[0].copy()
        w.wolves[0] = w.cows[0] + np.array([0.0, 12.0]); w.wolf_vel[0] = 0.0   # lobo pegado (<r_notice)
        w.step(c.act(None))
        moved += float(np.linalg.norm(w.cows[0] - p))
    head_err = abs(((np.arctan2(12.0, 0.0) - w.cow_heading[0] + np.pi) % (2 * np.pi)) - np.pi)
    print("  PIN: desplazamiento en 40 pasos=%.3f m (~0 = clavada) | err angular al lobo=%.2f rad (encara)" % (moved, head_err))
    assert moved < 0.5, "FALLO: el lobo no clavó a la vaca (sigue avanzando)"
    assert head_err < 0.3, "FALLO: la vaca no encara al lobo que la clava"
    # REANUDAR: al apartar el lobo (>r_notice), vuelve a huir.
    d2 = float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    w.wolves[0] = w.safe_zone[:2] + np.array([400.0, 400.0]); w.wolf_vel[0] = 0.0
    for _ in range(60):
        w.step(c.act(None))
    d3 = float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    print("  REANUDAR: dist al establo %.1f->%.1f m (baja de nuevo al apartar el lobo)" % (d2, d3))
    assert d3 < d2 - 2.0, "FALLO: la vaca no reanudó la huida tras apartar el lobo"
    # Bug 1: SOLO la presa fijada se para. Una vaca NO-FIJADA con un lobo dentro de r_notice SIGUE
    # huyendo (el paquete está comprometido con la presa, no con ella).
    wb = World(seed=2, n_cows=3, wolves_min=2, wolves_max=2, calf_count_probs=NO_CALVES)
    cb = DummyCoordinator(wb.n_drones)
    wb.phase = "ESCOLTA"
    wb.cow_speeds[:] = wb.cow_speed
    ctr = wb.safe_zone[:2]
    wb.cows[0] = ctr + np.array([80.0, 0.0])      # PRESA fijada
    wb.cows[1] = ctr + np.array([0.0, 100.0])     # NO-fijada, lejos del establo
    wb.cows[2] = ctr + np.array([0.0, -100.0])
    wb.pack_prey, wb.pack_prey_kind = 0, "adult"
    dn0 = float(np.linalg.norm(wb.cows[1] - ctr))
    p_prey = wb.cows[0].copy()
    for _ in range(20):
        wb.pack_prey, wb.pack_prey_kind = 0, "adult"                   # mantener la presa fijada
        wb.wolves[0] = wb.cows[0] + np.array([0.0, 10.0])              # lobo pegado a la PRESA
        wb.wolves[1] = wb.cows[1] + np.array([10.0, 0.0]); wb.wolf_vel[:] = 0.0   # lobo pegado a la NO-fijada
        wb.step(cb.act(None))
    moved_prey = float(np.linalg.norm(wb.cows[0] - p_prey))
    dn1 = float(np.linalg.norm(wb.cows[1] - ctr))
    print("  Bug 1: PRESA con lobo cerca se para (%.2f m) | NO-FIJADA con lobo cerca SIGUE huyendo (%.1f->%.1f m)"
          % (moved_prey, dn0, dn1))
    assert moved_prey < 0.5, "FALLO: la presa fijada no se clavó"
    assert dn1 < dn0 - 1.0, "FALLO(Bug 1): una vaca NO-fijada se paró por un lobo cercano (debería huir)"
    # Terneros: siguen ANCLADOS a su defensora durante la fuga (la pareja para/huye junta).
    w2 = World(seed=13, wolves_min=1, wolves_max=1, calf_count_probs=ONE_CALF)
    c2 = DummyCoordinator(w2.n_drones)
    w2.phase = "ESCOLTA"
    dists = []
    for _ in range(120):
        w2.step(c2.act(None))
        if w2.calf_alive[0] and not w2.calf_safe[0]:
            dists.append(float(np.linalg.norm(w2.calves[0] - w2.cows[w2.calf_defender[0]])))
    print("  ternero<->defensora en la fuga: media=%.2f m máx=%.2f m (espacio personal=%.2f m; sigue anclado)"
          % (np.mean(dists), np.max(dists), w2.calf_personal_space))
    assert np.mean(dists) < 3.0 * w2.calf_personal_space, "FALLO: el ternero se despegó de la defensora en la fuga"
    print("  OK\n")


def _one_active_drone(w, pos):
    """Deja UN solo dron ACTIVE en `pos`; los demás aparcados lejísimos (no disuaden). Aísla la disuasión."""
    w.drone_state[:] = READY
    w.drones[:] = np.array([1e4, 1e4])
    w.drone_state[0] = ACTIVE
    w.drones[0] = np.asarray(pos, dtype=float)
    w.drone_vel[:] = 0.0
    w.drone_waypoint[:] = w.drones


def test_disuasion():
    print("=== 1d) DISUASIÓN del dron: ESQUIVA + FRENA / PARCIAL (emergente) / DESPEJA EL PIN ===")
    # (a) ESQUIVA + FRENA: un lobo cruzando junto a un dron ACTIVE se desvía (trayectoria curva) y baja de
    #     rapidez (su rapidez máx se capa a wolf_speed*DETER_SLOWDOWN). Aislado: un dron quieto, un lobo pasando.
    def pass_by(with_drone):
        w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
        c = DummyCoordinator(w.n_drones)
        w.cows[0] = np.array([260.0, 150.0]); w.cow_vel[0] = 0.0; w.cow_speeds[0] = 0.0  # "objetivo" lejos al este
        w.wolves[0] = np.array([60.0, 150.0]); w.wolf_vel[0] = np.array([4.0, 0.0])      # lobo lanzado al este
        if with_drone:
            _one_active_drone(w, [140.0, 162.0])     # 12 m al norte del paso del lobo (<DETER_RADIUS)
        else:
            w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4])
        ys, sp = [], []
        for _ in range(80):
            w.pack_prey = -1; w.pack_prey_kind = None     # sin presa -> standoff recto al este (aísla la esquiva)
            w.step(c.act(None))
            ys.append(float(w.wolves[0, 1])); sp.append(float(np.linalg.norm(w.wolf_vel[0])))
            if w.wolves[0, 0] > 200:
                break
        return np.max(np.abs(np.array(ys) - 150.0)), min(sp)
    lat0, _ = pass_by(False)
    lat1, spmin1 = pass_by(True)
    print("  (a) ESQUIVA+FRENA: sin dron desvío lateral=%.2f m | con dron desvío=%.2f m, rapidez mín=%.2f m/s (cap %.1f)"
          % (lat0, lat1, spmin1, 4.0 * DETER_SLOWDOWN))
    assert lat1 > lat0 + 2.0, "FALLO: el lobo no esquivó al dron"
    assert spmin1 < 4.0 * DETER_SLOWDOWN + 0.5, "FALLO: el lobo no frenó dentro del radio"
    # (b) PARCIAL (emergente): una manada converge sobre UNA presa; un dron junto a UN lobo. Ese se desvía/
    #     aguanta lejos (disuadido); los otros empujan a través y cierran. Mismos params -> "uno huye, otros aguantan".
    #     La presa va FUERA del establo (si estuviera dentro se marcaría a salvo -> objetivos agotados -> coast).
    w = World(seed=0, n_cows=1, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    P = np.array([80.0, 80.0])               # presa lejos del establo (centro 150,150) -> sigue cazable
    w.cows[0] = P.copy(); w.cow_vel[0] = 0.0; w.cow_speeds[0] = 0.0
    w.wolves[:] = np.array([P + [-40, 0], P + [0, 40], P + [40, 0]], dtype=float)   # O/N/E a 40 m, separados
    w.wolf_vel[:] = 0.0
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    _one_active_drone(w, P + [-28.0, 0.0])   # 12 m al ESTE del lobo OESTE (lo empuja al oeste); >40 m de los otros 2
    d0 = np.linalg.norm(w.wolves - w.cows[0], axis=1).copy()
    for _ in range(40):
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        w.cow_vel[0] = 0.0; w.cows[0] = P.copy()
        w.step(c.act(None))
    d1 = np.linalg.norm(w.wolves - w.cows[0], axis=1)
    print("  (b) PARCIAL: lobo del dron dist a presa %.0f->%.0f m (disuadido) | los otros %.0f->%.0f y %.0f->%.0f (empujan)"
          % (d0[0], d1[0], d0[1], d1[1], d0[2], d1[2]))
    assert d1[0] > d1[1] + 5.0 and d1[0] > d1[2] + 5.0, "FALLO: el lobo del dron no quedó más lejos (no es parcial)"
    assert d1[1] < d0[1] and d1[2] < d0[2], "FALLO: los lobos sin dron no cerraron (deberían empujar a través)"
    # (c) DESPEJA/PREVIENE EL PIN — "aparta a los que se ACERCAN de lejos" (con el radio CORTO, R=20, el dron
    #     PASIVO ya no expulsa a un pinador comprometido a 12 m —se asienta a ~16 m, dentro de r_notice—; pero
    #     SÍ deflacta a un lobo que se ACERCA desde fuera de r_notice, impidiéndole cerrar el pin -> la vaca
    #     sigue huyendo. Expulsar un pin ya cerrado pasa a ser trabajo del COORDINADOR, post-v2; ver DISEÑO §9).
    def approach(with_drone):
        w = World(seed=5, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
        c = DummyCoordinator(w.n_drones)
        w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        ctr = w.safe_zone[:2]
        w.cows[0] = ctr + np.array([90.0, 0.0]); w.cow_heading[0] = np.pi   # vaca lejos, huyendo al oeste
        w.wolves[0] = w.cows[0] + np.array([28.0, 0.0]); w.wolf_vel[0] = 0.0  # lobo a 28 m: FUERA de r_notice=20
        if with_drone:                                                       # dron interpuesto, 8 m del lobo
            to_cow = (w.cows[0] - w.wolves[0]) / np.linalg.norm(w.cows[0] - w.wolves[0])
            _one_active_drone(w, w.wolves[0] + to_cow * 8.0)
        else:
            w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4])
        d0 = float(np.linalg.norm(w.cows[0] - ctr)); mind = np.inf; pinned = 0
        for _ in range(120):
            w.pack_prey, w.pack_prey_kind = 0, "adult"
            w.step(c.act(None))                                              # el lobo lo mueve la caza/disuasión
            dw = float(np.linalg.norm(w.wolves[0] - w.cows[0])); mind = min(mind, dw)
            pinned += int(dw <= w.r_notice)
        return mind, pinned, d0, float(np.linalg.norm(w.cows[0] - ctr))
    m0, p0, d0, d1_0 = approach(False)     # sin dron: el lobo cierra y CLAVA -> la vaca casi no progresa
    m1, p1, _, d1_1 = approach(True)       # con dron: el lobo NO cierra a r_notice -> la vaca sigue huyendo
    print("  (c) APARTA AL QUE SE ACERCA (R=%.0f): sin dron lobo cierra a %.0f m (pina %d pasos, vaca %.0f->%.0f) |"
          " con dron cierra a %.0f m (pina %d, vaca %.0f->%.0f)" % (DETER_RADIUS, m0, p0, d0, d1_0, m1, p1, d0, d1_1))
    assert m1 > w.r_notice and p1 == 0, "FALLO: el dron no impidió que el lobo cerrara el pin (no aparta al que se acerca)"
    assert d1_1 < d1_0 - 3.0, "FALLO: con el dron la vaca no progresó más (no se previno el pin)"
    print("  OK\n")


def test_rodeo():
    print("=== 1f) Las vacas NO-fijadas RODEAN a los lobos al HUIR (no atraviesan) y siguen llegando ===")
    import world as _w
    # (a) RODEA vs ATRAVIESA: vaca no-fijada huyendo con un lobo CONGELADO justo en medio.
    def flee(w_evitar):
        saved = _w.W_EVITAR; _w.W_EVITAR = w_evitar
        try:
            w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, max_episode_steps=2000)
            c = DummyCoordinator(w.n_drones)
            w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
            w.pack_prey, w.pack_prey_kind = -1, None        # SIN presa fijada -> la vaca HUYE (no-fijada)
            ctr = w.safe_zone[:2]
            w.cows[0] = ctr + np.array([100.0, 0.0]); w.cow_heading[0] = np.pi
            wolf = ctr + np.array([55.0, 0.0])               # lobo en medio (línea vaca-establo)
            mind = np.inf
            for _ in range(2000):
                w.pack_prey, w.pack_prey_kind = -1, None
                w.wolves[0] = wolf; w.wolf_vel[0] = 0.0       # lobo congelado en medio
                w.step(c.act(None))
                mind = min(mind, float(np.linalg.norm(w.cows[0] - wolf)))
                if w.cow_safe[0]:
                    break
            return mind, bool(w.cow_safe[0]), float(np.linalg.norm(w.cows[0] - ctr))
        finally:
            _w.W_EVITAR = saved
    m_off, _, _ = flee(0.0)
    m_on, safe_on, d_on = flee(_w.W_EVITAR)
    print("  SIN evitar (W_EVITAR=0): min dist al lobo=%.1f m (atraviesa) | CON evitar: %.1f m (BORDEA) | a salvo=%s"
          % (m_off, m_on, safe_on))
    assert m_on > m_off + 2.0, "FALLO: la evitación no aparta a la vaca del lobo (no rodea)"
    assert safe_on, "FALLO: la vaca rodea pero NO llega al establo (la evitación la atrapa)"
    # (b) PRESA FIJADA intacta: la presa fijada sigue PARÁNDOSE a encarar (no esquiva).
    w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
    ctr = w.safe_zone[:2]; w.cows[0] = ctr + np.array([90.0, 0.0]); w.cow_heading[0] = np.pi
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    moved = 0.0
    for _ in range(40):
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        w.wolves[0] = w.cows[0] + np.array([12.0, 0.0]); w.wolf_vel[0] = 0.0
        p = w.cows[0].copy(); w.step(c.act(None)); moved += float(np.linalg.norm(w.cows[0] - p))
    print("  presa FIJADA con lobo cerca: desplazamiento=%.3f m (~0 = clavada, NO esquiva; solo las no-fijadas rodean)" % moved)
    assert moved < 0.5, "FALLO: la presa fijada se movió (debería ENCARAR parada, no esquivar)"
    print("  OK\n")


def test_madre_no_abandona():
    print("=== 1g) La MADRE no abandona al ternero al HUIR: va a su ritmo (calf_speed), a su lado, llegan juntos ===")

    def pair_flee():
        """Madre + ternero huyendo al establo SIN lobos (HUIR puro; las demás ya a salvo). Métricas de la pareja."""
        w = World(seed=3, wolves_min=0, wolves_max=0, calf_count_probs=ONE_CALF, max_episode_steps=4000)
        c = DummyCoordinator(w.n_drones)
        w.phase = "ESCOLTA"
        dfn = int(w.calf_defender[0]); ctr = w.safe_zone[:2]
        others = [i for i in range(w.n_cows) if i != dfn]
        w.cows[others] = ctr; w.cow_safe[others] = True; w.cow_vel[others] = 0.0
        w.cows[dfn] = ctr + np.array([120.0, 0.0]); w.cow_heading[dfn] = np.pi
        w.calves[0] = w.cows[dfn] + np.array([0.0, -w.calf_personal_space])
        w.cow_speeds[dfn] = w.cow_speed                 # madre a rapidez de adulta: la cap debe bajarla a calf_speed
        maxgap, mommax, steps = 0.0, 0.0, None
        for k in range(4000):
            w.step(c.act(None))
            maxgap = max(maxgap, float(np.linalg.norm(w.cows[dfn] - w.calves[0])))
            mommax = max(mommax, float(np.linalg.norm(w.cow_vel[dfn])))
            if w.cow_safe[dfn] and w.calf_safe[0]:
                steps = k + 1; break
        return maxgap, mommax, steps, bool(w.cow_safe[dfn]), bool(w.calf_safe[0])

    def lone_adult():
        """Una adulta SOLA (sin ternero) desde la MISMA distancia -> pasos hasta refugiarse (más rápida)."""
        w = World(seed=3, wolves_min=0, wolves_max=0, calf_count_probs=NO_CALVES, max_episode_steps=4000)
        c = DummyCoordinator(w.n_drones)
        w.phase = "ESCOLTA"; ctr = w.safe_zone[:2]
        others = list(range(1, w.n_cows))
        w.cows[others] = ctr; w.cow_safe[others] = True; w.cow_vel[others] = 0.0
        w.cows[0] = ctr + np.array([120.0, 0.0]); w.cow_heading[0] = np.pi; w.cow_speeds[0] = w.cow_speed
        for k in range(4000):
            w.step(c.act(None))
            if w.cow_safe[0]:
                return k + 1
        return 4000

    w0 = World(seed=0, calf_count_probs=ONE_CALF)
    cs, ps = w0.calf_speed, w0.calf_personal_space
    maxgap, mommax, steps, msafe, csafe = pair_flee()
    solo = lone_adult()
    print("  NO la deja atrás: máx dist madre-ternero=%.2f m (esp. personal=%.2f) | rapidez máx madre=%.2f m/s (cap calf_speed=%.2f)"
          % (maxgap, ps, mommax, cs))
    print("  llegan JUNTOS: madre=%s ternero=%s en %d pasos | adulta SOLA en %d (la pareja es MÁS LENTA: ritmo del ternero)"
          % (msafe, csafe, steps, solo))
    assert maxgap < 3.0 * ps, "FALLO: la madre dejó atrás al ternero (gap grande)"
    assert mommax <= cs + 0.05, "FALLO: la madre va más rápido que el ternero (lo adelanta)"
    assert msafe and csafe, "FALLO: la pareja no se refugió junta"
    assert steps > solo, "FALLO: la pareja no es más lenta que una adulta sola"
    # Ternero FIJADO -> su defensora sigue en ENCARAR (parada): el cap de calf_speed no toca el pin (Bug 1 intacto).
    w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=ONE_CALF)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"; w.cow_speeds[:] = w.cow_speed
    dfn = int(w.calf_defender[0]); ctr = w.safe_zone[:2]
    w.cows[dfn] = ctr + np.array([90.0, 0.0]); w.cow_heading[dfn] = np.pi
    w.calves[0] = w.cows[dfn] + np.array([0.0, -w.calf_personal_space])
    w.pack_prey, w.pack_prey_kind = 0, "calf"
    moved = 0.0
    for _ in range(40):
        w.pack_prey, w.pack_prey_kind = 0, "calf"
        w.wolves[0] = w.cows[dfn] + np.array([12.0, 0.0]); w.wolf_vel[0] = 0.0
        p = w.cows[dfn].copy(); w.step(c.act(None)); moved += float(np.linalg.norm(w.cows[dfn] - p))
    print("  ternero FIJADO -> defensora con lobo cerca: desplazamiento=%.3f m (~0 = ENCARAR parada, Bug 1 intacto)" % moved)
    assert moved < 0.5, "FALLO: la defensora de un ternero FIJADO se movió (debería ENCARAR parada)"
    print("  OK\n")


def test_zona_bordeo():
    print("=== 1h) El LOBO no se clava en la ZONA SEGURA: la BORDEA (no entra) y suelta a la presa refugiada ===")
    from world import WOLF_ZONE_SKIRT_BAND as ZB
    w0 = World(seed=0)
    print("  zona segura: radio=%.1f m (=%.0f%% del lado de %.0f m, %.1f%% del área) | central radio=%.1f m"
          % (w0.safe_zone[2], 100*w0.safe_zone[2]/w0.W, w0.W,
             100*np.pi*w0.safe_zone[2]**2/(w0.W*w0.H), w0.central_station[2]))

    def chase_across(perp_off):
        """Lobo al ESTE de la zona; presa fijada al OESTE (al otro lado). perp_off=0 -> colineal exacto (saddle).
        ¿Bordea (min dist a la presa baja) y se queda FUERA, o se clava en el borde (min ~ inicial)?"""
        w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
        c = DummyCoordinator(w.n_drones)
        w.phase = "ESCOLTA"
        C, r = w.safe_zone[:2], w.safe_zone[2]
        prey = C + np.array([-r - 25.0, 0.0])
        w.cows[0] = prey.copy(); w.cow_vel[0] = 0.0; w.cow_speeds[0] = 0.0
        w.wolves[0] = C + np.array([r + 3.0, perp_off]); w.wolf_vel[0] = 0.0
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        d0 = float(np.linalg.norm(w.wolves[0] - prey)); mind = np.inf; entered = False
        for _ in range(400):
            w.cows[0] = prey.copy(); w.cow_vel[0] = 0.0
            w.pack_prey, w.pack_prey_kind = 0, "adult"
            w.step(c.act(None))
            mind = min(mind, float(np.linalg.norm(w.wolves[0] - prey)))
            entered = entered or (float(np.linalg.norm(w.wolves[0] - C)) < r)
        return d0, mind, entered

    for off, tag in [(0.0, "colineal exacto (saddle)"), (4.0, "ligero desfase")]:
        d0, mind, entered = chase_across(off)
        print("  desfase=%.0f m (%-24s): dist lobo-presa %.0f -> MIN %.1f m | entró en la zona=%s" % (off, tag, d0, mind, entered))
        assert mind < d0 - 30.0, "FALLO: el lobo no bordeó la zona (sigue clavado en el borde)"
        assert not entered, "FALLO: el lobo ENTRÓ en la zona segura (debe quedarse fuera)"
    # Suelta a la presa refugiada al INSTANTE: re-fija a la res viva FUERA (no persigue dentro de la zona).
    w = World(seed=0, n_cows=2, wolves_min=2, wolves_max=2, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"
    C, r = w.safe_zone[:2], w.safe_zone[2]
    w.cows[0] = C + np.array([r - w.refuge_margin - 1.0, 0.0])         # presa 0 ya dentro del margen -> a salvo
    w.cows[1] = C + np.array([0.0, r + 40.0]); w.cow_speeds[1] = 0.0   # otra res viva FUERA
    w.wolves[:] = np.array([C + [r + 4.0, 0.0], C + [r + 8.0, 2.0]]); w.wolf_vel[:] = 0.0
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    w.step(c.act(None))
    print("  presa 0 a salvo=%s | tras refugio re-fija a presa=%d (%s) = la res viva FUERA, no la refugiada"
          % (bool(w.cow_safe[0]), int(w.pack_prey), w.pack_prey_kind))
    assert w.cow_safe[0], "FALLO: la presa no se refugió"
    assert int(w.pack_prey) == 1, "FALLO: no soltó la presa refugiada / no re-fijó a la res de fuera al instante"
    print("  OK\n")


def test_corzos():
    print("=== 1i) CORZOS (3c): cuerpo NO-amenaza · deambula+HUYE · AGRUPADOS · el dron VUELA y descarta a r_confirm · 3 tipos ===")
    from collections import Counter
    from world import CORZO_GROUP_DISPERSION

    # (a) HUYE de un lobo y de un dron ACTIVE cercanos (esquivo); NO ataca al rebaño.
    w = World(seed=4, wolves_min=1, wolves_max=1, corzos_min=1, corzos_max=1, episode_kind="mixto", calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.corzos[0] = np.array([150.0, 70.0]); w.corzo_vel[0] = 0.0
    wolf = w.corzos[0] + np.array([7.0, 0.0])                 # lobo congelado pegado al corzo
    d0_w = float(np.linalg.norm(w.corzos[0] - wolf))
    for _ in range(30):
        w.wolves[0] = wolf; w.wolf_vel[0] = 0.0
        w.step(c.act(None))
    d1_w = float(np.linalg.norm(w.corzos[0] - wolf))
    w2 = World(seed=4, corzos_min=1, corzos_max=1, episode_kind="corzos", calf_count_probs=NO_CALVES)
    w2.corzos[0] = np.array([150.0, 70.0]); w2.corzo_vel[0] = 0.0
    _one_active_drone(w2, w2.corzos[0] + np.array([7.0, 0.0]))
    drone = w2.drones[0].copy(); d0_d = float(np.linalg.norm(w2.corzos[0] - drone))
    for _ in range(30):
        _one_active_drone(w2, drone); w2.step(c.act(None))
    d1_d = float(np.linalg.norm(w2.corzos[0] - drone))
    print("  (a) HUYE: dist a lobo %.1f->%.1f m | dist a dron %.1f->%.1f m (se aleja de ambos)" % (d0_w, d1_w, d0_d, d1_d))
    assert d1_w > d0_w + 5.0 and d1_d > d0_d + 5.0, "FALLO: el corzo no huye de lobo/dron"

    # (b) Solo-corzos: NO ataca al rebaño -> ESCOLTA jamás, severidad 0; el rebaño pasta (no huye).
    w = World(seed=7, corzos_min=2, corzos_max=3, episode_kind="corzos", max_episode_steps=400)
    c = DummyCoordinator(w.n_drones)
    phases = set(); cow0 = w.cows.copy()
    while True:
        _, _, term, trunc, info = w.step(c.act(None)); phases.add(w.phase)
        if term or trunc: break
    moved = float(np.linalg.norm(w.cows - cow0, axis=1).mean())
    print("  (b) SOLO-CORZOS: fases vistas=%s | cazadas=%d | a salvo=%d | desplaz. medio rebaño=%.1f m (pasta, no huye)"
          % (sorted(phases), info["n_depredadas"], info["n_safe"], moved))
    assert "ESCOLTA" not in phases, "FALLO: ESCOLTA se activó sin lobos (un corzo disparó la escolta)"
    assert info["n_depredadas"] == 0, "FALLO: hubo depredación en solo-corzos (severidad debe ser 0)"

    # (c) DETECCIÓN: un corzo a < r_detect de un dron ACTIVE dispara el reflejo (SOSPECHA + 1 investigando).
    w = World(seed=0, corzos_min=1, corzos_max=1, episode_kind="corzos")
    w.phase = "VIGILANCIA"; w.drone_state[:] = READY; w.drones[:] = 1e4
    w.drone_state[:4] = ACTIVE; w.drones[:4] = np.array([[0., 0.], [5., 0.], [0., 5.], [5., 5.]])
    w.drone_investigating[:] = False
    w.corzos[0] = np.array([60.0, 60.0])                      # ~85 m del activo (5,5): <r_detect, >r_confirm
    w._update_phase()
    assert w.phase == "SOSPECHA" and int(w.drone_investigating.sum()) == 1, "FALLO: un corzo no dispara la detección"
    assert np.allclose(w.drone_contact[np.where(w.drone_investigating)[0][0]], w.corzos[0]), "FALLO: el contacto no es el corzo"
    print("  (c) DETECCIÓN: el corzo dispara el reflejo (SOSPECHA + 1 dron investigando; contacto = el corzo)")

    # (d) TIPO SOLO A r_confirm: un corzo a r_detect pero >r_confirm NO se descarta de lejos (sigue SOSPECHA).
    assert w.phase == "SOSPECHA" and not bool(w.corzo_dismissed[0]), "FALLO: el corzo se descartó a r_detect (debe ser a r_confirm)"
    # ORÁCULO al llegar a r_confirm: CORZO -> descarta + dron VUELVE A SU PUESTO + fase -> VIGILANCIA (no pillada).
    inv = int(np.where(w.drone_investigating)[0][0])
    home = w.drone_home[inv].copy()
    w.corzos[0] = w.drones[inv] + np.array([0.0, w.r_confirm - 5.0])   # acerca el corzo a r_confirm del investigador
    w._update_phase()
    assert bool(w.corzo_dismissed[0]) and not w.drone_investigating.any(), "FALLO: el corzo no se descartó / el dron no se liberó"
    assert w.phase == "VIGILANCIA", "FALLO: tras descartar el corzo la fase no volvió a VIGILANCIA (se quedó pillada)"
    assert np.allclose(w.drone_waypoint[inv], home), "FALLO: el dron no volvió a su puesto tras descartar el corzo"
    wl = World(seed=0, wolves_min=1, wolves_max=1, corzos_max=0)       # un lobo: confirma -> ESCOLTA (no vuelve)
    wl.phase = "VIGILANCIA"; wl.drone_state[:] = READY; wl.drones[:] = 1e4
    wl.drone_state[0] = ACTIVE; wl.drones[0] = np.array([5.0, 5.0]); wl.drone_investigating[:] = False
    wl.wolves[:] = wl.drones[0] + np.array([0.0, wl.r_confirm - 5.0])
    wl._update_phase()
    assert wl.phase == "ESCOLTA", "FALLO: un LOBO confirmado no disparó ESCOLTA"
    print("  (d) ORÁCULO: tipo solo a r_confirm (no de lejos) | CORZO->descarta + vuelve al puesto + fase VIGILANCIA | LOBO->ESCOLTA")

    # (d2) END-TO-END (BUG arreglado): con un corzo en SOSPECHA, el investigador VUELA hacia él, llega a
    #      <=r_confirm, ahí lo identifica y descarta, vuelve a su puesto y la fase vuelve a VIGILANCIA.
    w = World(seed=11, corzos_min=1, corzos_max=1, episode_kind="corzos")
    c = DummyCoordinator(w.n_drones)
    homes = w.drone_home[:w.n_active].copy()
    min_to_corzo = np.inf; dismissed_step = None
    for step in range(600):
        w.step(c.act(None))
        # dist mínima de un dron ACTIVE a un corzo (el investigador se acerca a <=r_confirm para descartar).
        dmin = float(np.linalg.norm(w.drones[:w.n_active][:, None, :] - w.corzos[None, :, :], axis=2).min())
        min_to_corzo = min(min_to_corzo, dmin)
        if dismissed_step is None and w.corzo_dismissed.all():
            dismissed_step = step
        if dismissed_step is not None and step > dismissed_step + 200:
            break
    back = float(np.linalg.norm(w.drones[:w.n_active] - homes, axis=1).max())
    print("  (d2) END-TO-END: el dron se acercó a %.1f m del corzo (<=r_confirm=%.0f) antes de descartar; tras volver: dist al puesto=%.1f m | fase=%s"
          % (min_to_corzo, w.r_confirm, back, w.phase))
    assert min_to_corzo <= w.r_confirm + 1e-6, "FALLO: el dron descartó el corzo SIN acercarse a r_confirm (no fue a investigarlo)"
    assert back < 2.0 and w.phase == "VIGILANCIA", "FALLO: el dron no volvió a su puesto / la fase no volvió a VIGILANCIA"

    # (h) AGRUPADOS + DENTRO DE SOSPECHA: los corzos salen JUNTOS (spread pequeño) y el grupo cae dentro de
    #     r_detect de un dron la MAYORÍA de las veces (dispara SOSPECHA), fuera del rebaño.
    spreads = []; in_sospecha = 0; n = 120
    for s in range(n):
        ws = World(seed=s, corzos_min=2, corzos_max=3, episode_kind="corzos")
        if ws.n_corzos > 1:
            spreads.append(float(np.linalg.norm(ws.corzos - ws.corzos.mean(axis=0), axis=1).mean()))
        dmin = float(np.linalg.norm(ws.corzos[:, None, :] - ws.drones[:ws.n_active][None, :, :], axis=2).min())
        in_sospecha += int(dmin <= ws.r_detect)
    print("  (h) AGRUPADOS: spread medio del grupo=%.1f m (juntos) | DENTRO de r_detect (SOSPECHA): %d/%d (%.0f%%)"
          % (np.mean(spreads), in_sospecha, n, 100 * in_sospecha / n))
    assert np.mean(spreads) < 3.0 * CORZO_GROUP_DISPERSION, "FALLO: los corzos salen dispersos (no agrupados)"
    assert in_sospecha >= 0.7 * n, "FALLO: el grupo no cae dentro de SOSPECHA la mayoría de las veces"

    # (e) MIXTO: los lobos disparan ESCOLTA y la caza procede; los corzos se descartan (el reflejo investiga ambos).
    saw_escolta = saw_dismiss = False
    for s in range(12):
        w = World(seed=s, corzos_min=1, corzos_max=3, episode_kind="mixto", max_episode_steps=1500)
        c = DummyCoordinator(w.n_drones)
        while True:
            _, _, term, trunc, info = w.step(c.act(None))
            saw_escolta = saw_escolta or (w.phase == "ESCOLTA")
            saw_dismiss = saw_dismiss or bool(w.corzo_dismissed.any())
            if term or trunc: break
    print("  (e) MIXTO: alguna ESCOLTA disparada=%s | algún corzo descartado=%s" % (saw_escolta, saw_dismiss))
    assert saw_escolta and saw_dismiss, "FALLO: en mixto no se vio ESCOLTA (lobo) y/o descarte (corzo)"

    # (f) Reparto de episodios ~1/3 cada uno (sembrado) + reproducibilidad.
    cnt = Counter(World(seed=s, corzos_max=3).episode_kind for s in range(360))
    frac = {k: cnt[k] / 360 for k in ("lobos", "corzos", "mixto")}
    print("  (f) reparto 360 seeds: lobos=%.0f%% corzos=%.0f%% mixto=%.0f%% (~1/3 cada uno)"
          % (100*frac["lobos"], 100*frac["corzos"], 100*frac["mixto"]))
    for k, f in frac.items():
        assert 0.25 <= f <= 0.42, "FALLO: el tipo '%s' no es ~1/3 (%.2f)" % (k, f)
    a = World(seed=5, corzos_max=3); b = World(seed=5, corzos_max=3)
    assert a.episode_kind == b.episode_kind and a.n_corzos == b.n_corzos and np.allclose(a.corzos, b.corzos), \
        "FALLO: corzos no reproducibles (misma seed -> distinto)"
    print("  (g) reproducible: misma seed -> mismo tipo, nº y posiciones de corzos")
    print("  OK\n")


def _pin_scene(with_drone):
    """Adulta CLAVADA (ESCOLTA) FUERA del establo + 4 lobos a 10 m en N/E/S/O. Sin/con un dron a tiro."""
    w = World(seed=0, n_cows=1, wolves_min=4, wolves_max=4, calf_count_probs=NO_CALVES,
              escort_enabled=True, max_episode_steps=400)
    P = np.array([80.0, 80.0])
    w.cows[0] = P.copy(); w.cow_vel[0] = 0.0; w.cow_speeds[0] = w.cow_speed; w.cow_heading[0] = np.pi
    w.phase = "ESCOLTA"; w.pack_prey, w.pack_prey_kind = 0, "adult"
    w.wolves[:] = np.array([P + [0, 10], P + [10, 0], P + [0, -10], P + [-10, 0]], dtype=float)
    w.wolf_vel[:] = 0.0
    w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4])
    if with_drone:
        # Dron a tiro del NUEVO radio corto (DETER_RADIUS=20): a 14 m de la presa entra en el radio del lobo
        # ESTE (4 m) y de los N/S (~17 m) -> los frena/aparta y RETRASA la caza (con 40 m bastaba a 22 m).
        w.drone_state[0] = ACTIVE; w.drones[0] = P + [14.0, 0.0]; w.drone_vel[0] = 0.0
        w.drone_waypoint[0] = w.drones[0].copy()
    return w, P


def test_pin_envolvente():
    print("=== 1e) ADULTA CLAVADA matable en ESCOLTA (ataque ENVOLVENTE; con/sin dron) ===")
    # REGRESIÓN: antes 4 lobos rodeando una adulta clavada NO la mataban (se apiñaban en el cono frontal y
    # "dar la cara" los mantenía a TODOS a r_face_safe). El ataque ENVOLVENTE los reparte a flancos limpios.
    def kill_steps(with_drone):
        w, P = _pin_scene(with_drone)
        c = DummyCoordinator(w.n_drones)
        for k in range(400):
            w.pack_prey, w.pack_prey_kind = 0, "adult"     # mantener la presa fijada (aislar el flanqueo)
            w.step(c.act(None))
            if not w.cow_alive[0]:
                return k + 1
        return None
    k_sin = kill_steps(False)
    k_con = kill_steps(True)
    print("  SIN dron: la matan en %s pasos | CON dron a tiro: en %s pasos (la disuasión RETRASA, no impide)"
          % (k_sin, k_con))
    assert k_sin is not None, "FALLO: el paquete NO mata a una adulta clavada en ESCOLTA (regresión del pin)"
    assert k_con is not None, "FALLO: con un dron a tiro la adulta clavada es INVULNERABLE (disuasión absoluta)"
    assert k_con > k_sin, "FALLO: el dron no retrasa la caza (disuasión sin efecto)"
    # ENVOLVENTE: 4 lobos arrancando APIÑADOS en un costado se REPARTEN alrededor de la presa (no 2+2).
    w, P = _pin_scene(False)
    w.wolves[:] = P + np.array([[14, 3], [14, -3], [12, 6], [12, -6]], dtype=float)   # los 4 al ESTE (apiñados)
    w.wolf_vel[:] = 0.0
    c = DummyCoordinator(w.n_drones)
    def maxgap():
        a = np.sort(np.degrees(np.arctan2(w.wolves[:, 1] - P[1], w.wolves[:, 0] - P[0])))
        return float(max(np.diff(np.concatenate([a, [a[0] + 360]]))))
    gap0, best = maxgap(), maxgap()
    for _ in range(60):
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        w.step(c.act(None))
        if not w.cow_alive[0]:
            break
        best = min(best, maxgap())
    print("  ENVOLVENTE: máx hueco angular %0.f°->%0.f° (apiñados ~300°, repartido 4 lobos ~90°) | matada=%s"
          % (gap0, best, not w.cow_alive[0]))
    assert gap0 > 200 and (best < 160 or not w.cow_alive[0]), "FALLO: los lobos no se reparten (siguen apiñados)"
    print("  OK\n")


def test_depredacion():
    print("=== 2) DEPREDACIÓN forzada — MATANZA EXCEDENTE (la manada caza VARIAS; ya no hay tope de 1) ===")
    # Combate puro (escort_enabled=False: sin huida ni disuasión) con reses CONGELADAS (cow_speeds=0) y
    # alcanzables en línea: el paquete mata, RE-FIJA la más cercana y SIGUE -> mueren VARIAS. Antes (máx. 1
    # caza) se saciaba tras la primera; ahora la severidad vuelve a ser la métrica (cuántas cabezas se pierden).
    w = World(seed=1, n_cows=5, wolves_min=5, wolves_max=5, calf_count_probs=NO_CALVES,
              max_episode_steps=600, escort_enabled=False)
    c = DummyCoordinator(w.n_drones)
    ctr = np.array([150.0, 150.0])
    w.cows[:] = ctr + np.array([[-40, 0], [-20, 0], [0, 0], [20, 0], [40, 0]], dtype=float)
    w.cow_vel[:] = 0.0; w.cow_speeds[:] = 0.0
    ang = np.linspace(0, 2 * np.pi, w.n_wolves, endpoint=False)
    w.wolves[:] = w.cows[0] + 6.0 * np.column_stack([np.cos(ang), np.sin(ang)])
    w.wolf_vel[:] = 0.0
    w._commit_initial_prey()
    info = {"status": w.status}
    for _ in range(600):
        _, _, term, trunc, info = w.step(c.act(None))
        if term or trunc:
            break
    print("  status=%s  n_depredadas=%d (de %d)  capturas=%d  paso=%s"
          % (info["status"], info["n_depredadas"], w.n_cows, len(w.captures), info["terminal_step"]))
    assert info["n_depredadas"] >= 2, "FALLO: el paquete no cazó VARIAS (matanza excedente: sin tope de 1)"
    assert info["status"] == "predation", "FALLO: el estado no es DEPREDACIÓN (>=1 cazada)"
    print("  OK\n")


def test_timeout():
    print("=== 3) TIMEOUT forzado (lobo solo no mata; max_episode_steps bajo) ===")
    w = World(seed=2, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, max_episode_steps=40)
    info = _run(w)
    print("  status=%s  n_depredadas=%d  n_fuera=%d  paso=%s"
          % (info["status"], info["n_depredadas"], info["n_fuera"], info["terminal_step"]))
    assert info["status"] == "timeout", "FALLO: no se alcanzó TIMEOUT"
    assert info["n_depredadas"] == 0 and info["n_fuera"] >= 1
    print("  OK\n")


def test_refugio_suelta_presa():
    print("=== 4) Refugio = soltar presa (re-fijación SOLO al refugiarse) ===")
    w = World(seed=3, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=500)
    c = DummyCoordinator(w.n_drones)
    for _ in range(10):
        w.step(c.act(None))            # deja que la manada se comprometa y se acerque
    prey0, refix0 = w.pack_prey, w.n_refix
    assert prey0 >= 0, "FALLO: la manada no tiene presa fijada para la prueba"
    w.cows[prey0] = w.safe_zone[:2] + np.array([1.0, 0.0])   # FUERZA a la presa al establo
    w.step(c.act(None))
    print("  presa0=%d -> a salvo=%s | nueva presa=%d | re-fijaciones %d->%d"
          % (prey0, bool(w.cow_safe[prey0]), w.pack_prey, refix0, w.n_refix))
    assert w.cow_safe[prey0], "FALLO: la presa refugiada no se marcó a salvo"
    assert w.n_refix == refix0 + 1, "FALLO: la re-fijación por refugio no se contó (o se contó de más)"
    assert w.pack_prey != prey0, "FALLO: la manada no re-seleccionó tras el refugio"
    # Control: en un episodio normal (sin refugio) las re-fijaciones son 0.
    w2 = World(seed=4, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=300)
    _run(w2)
    print("  episodio normal (sin refugio): re-fijaciones=%d (esperado 0)" % w2.n_refix)
    assert w2.n_refix == 0, "FALLO: hubo re-fijaciones sin ningún refugio"
    print("  OK\n")


def test_wolf_exclusion():
    print("=== 5) Exclusión del lobo: nunca dentro del establo (clamp #5) ===")
    worst_margin = np.inf
    for s in range(12):
        w = World(seed=s, wolves_min=2, wolves_max=5, max_episode_steps=300)
        c = DummyCoordinator(w.n_drones)
        for _ in range(300):
            _, _, term, trunc, _ = w.step(c.act(None))
            assert not w._in_safe_zone(w.wolves).any(), \
                "FALLO: un lobo entró en el establo (seed %d, paso %d)" % (s, w.step_count)
            margin = float(np.linalg.norm(w.wolves - w.safe_zone[:2], axis=1).min() - w.safe_zone[2])
            worst_margin = min(worst_margin, margin)
            if term or trunc:
                break
    print("  12 episodios: ningún lobo dentro; margen mínimo lobo-borde del establo=%.2f m (>0)" % worst_margin)
    assert worst_margin > 0.0
    print("  OK\n")


def test_reproducible():
    print("=== 6) Reproducibilidad (mismo estado terminal + contadores) ===")
    def fingerprint(seed):
        w = World(seed=seed, max_episode_steps=300)
        info = _run(w)
        return (info["status"], info["n_safe"], info["n_depredadas"], info["n_fuera"],
                info["terminal_step"], tuple(w.cow_safe.tolist()), tuple(w.cow_alive.tolist()))
    a, b = fingerprint(7), fingerprint(7)
    print("  fingerprint idéntico:", a == b, "| status=%s n_depredadas=%d" % (a[0], a[2]))
    assert a == b, "FALLO: no reproducible"
    print("  OK\n")


def test_no_regressions():
    print("=== 7) Sin regresiones (face_check.py + battery_check.py) ===")
    for script in ("face_check.py", "battery_check.py"):
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        ok = r.returncode == 0
        print("  %-16s -> %s" % (script, "VERDE" if ok else "ROJO (exit %d)" % r.returncode))
        assert ok, "FALLO: %s no pasó\n%s" % (script, (r.stdout + r.stderr)[-800:])
    print("  OK\n")


def test_timing_deteccion():
    print("=== 8) Timing de las dos etapas: SOSPECHA (detección) y ESCOLTA (confirmación) ===")
    s_sosp, s_esc, gaps, best = [], [], [], (-1, None)
    for s in range(20):
        w = World(seed=s)
        c = DummyCoordinator(w.n_drones)
        susp = esc = None
        while True:
            _, _, term, trunc, info = w.step(c.act(None))
            if susp is None and info["phase"] in ("SOSPECHA", "ESCOLTA"):
                susp = w.step_count
            if esc is None and info["phase"] == "ESCOLTA":
                esc = w.step_count
            if term or trunc:
                break
        if susp is not None and esc is not None:
            s_sosp.append(susp); s_esc.append(esc); gaps.append(esc - susp)
            if 120 <= esc <= 380 and esc > best[0]:   # arco largo pero gif manejable
                best = (esc, s)
    s_sosp, s_esc, gaps = np.array(s_sosp), np.array(s_esc), np.array(gaps)
    print("  SOSPECHA (<=r_detect): mediana=%d  | ESCOLTA (tras confirmar a <=r_confirm): mediana=%d  (n=%d)"
          % (int(np.median(s_sosp)), int(np.median(s_esc)), len(s_esc)))
    print("  hueco investigación SOSPECHA->ESCOLTA: mediana=%d máx=%d pasos (el dron vuela al contacto)"
          % (int(np.median(gaps)), int(gaps.max())))
    assert np.median(s_sosp) > 20, "FALLO: la detección es casi inmediata (campo demasiado pequeño)"
    assert np.median(gaps) >= 1, "FALLO: no hay hueco SOSPECHA->ESCOLTA (no se investiga)"
    print("  OK\n")
    return best[1] if best[1] is not None else int(s_esc.argmax()) if len(s_esc) else 8


def test_tasa_escolta():
    print("=== 9) Candidata a v2 (Dummy + guiado + disuasión) — SEVERIDAD y tasa MEDIDAS (matanza excedente) ===")
    from collections import Counter
    def sweep(escort, n):
        out, deaths = Counter(), []
        for s in range(n):
            w = World(seed=s, escort_enabled=escort)
            c = DummyCoordinator(w.n_drones)
            while True:
                _, _, term, trunc, info = w.step(c.act(None))
                if term or trunc:
                    break
            out[info["status"]] += 1
            deaths.append(w.n_depredadas)
        return out, deaths
    n_g, n_u = 40, 15
    g_out, g_deaths = sweep(True, n_g)
    u_out, u_deaths = sweep(False, n_u)
    print("  ESCENARIO escolta (escort_enabled=True: guiado + no-holonómico + DISUASIÓN), Dummy n=%d: %s"
          % (n_g, dict(g_out)))
    print("    -> tasa (>=1 muerta)=%.0f%% | SEVERIDAD=%.2f muertes/ep (máx=%d) <- la métrica principal a batir"
          % (100 * g_out["predation"] / n_g, np.mean(g_deaths), max(g_deaths)))
    print("  ADVERSARIO PURO (escort_enabled=False: sin escolta ni drones), n=%d: %s | tasa=%.0f%% | SEVERIDAD=%.2f (máx=%d)"
          % (n_u, dict(u_out), 100 * u_out["predation"] / n_u, np.mean(u_deaths), max(u_deaths)))
    print("  -> BASELINE HONESTA (pin matable; NO-fijadas RODEAN; disuasión radio CORTO + bordeo; pareja lenta; lobos no se pillan en la zona):")
    print("     SEVERIDAD ~4.4 muertes/ep (subió desde ~2.33 al acortar el radio 40->20 y suavizar el frenazo —el dron")
    print("     reacciona solo de CERCA, el Dummy QUIETO cubre mucho menos—, y un poco más al dejar de pillarse los lobos")
    print("     en la zona segura —ya no pierden tiempo—). La disuasión PARCIAL aún baja la severidad frente al adv. puro (~6.3) pero")
    print("     POCO; el coordinador (posicionar drones CERCA) la bajará de verdad -> post-v2; ESTA es la referencia a batir.")
    assert max(g_deaths) >= 2 or max(u_deaths) >= 2, "FALLO: ningún episodio con >1 caza (la matanza excedente no ocurre)"
    assert g_out["success"] >= 1, "FALLO: debería haber ÉXITO orgánico en alguna seed"
    assert 100 * g_out["predation"] / n_g < 100 * u_out["predation"] / n_u, \
        "FALLO: la disuasión NO bajó la tasa respecto al adversario puro"
    print("  OK\n")


def test_severidad_por_tipo():
    print("=== 9b) SEVERIDAD por TIPO de episodio (corzos activos, Dummy) — MEDIDA, no objetivo ===")
    from collections import Counter
    def sweep(kind, n):
        out, deaths = Counter(), []
        for s in range(n):
            w = World(seed=s, corzos_max=3, episode_kind=kind)
            c = DummyCoordinator(w.n_drones)
            while True:
                _, _, term, trunc, info = w.step(c.act(None))
                if term or trunc:
                    break
            out[info["status"]] += 1; deaths.append(w.n_depredadas)
        return out, deaths
    n = 30
    for kind in ("lobos", "corzos", "mixto"):
        out, deaths = sweep(kind, n)
        print("  %-7s n=%d: %-44s | tasa=%3.0f%% | SEVERIDAD=%.2f (máx=%d)"
              % (kind, n, str(dict(out)), 100 * out["predation"] / n, np.mean(deaths), max(deaths)))
        if kind == "corzos":
            assert sum(deaths) == 0 and out["predation"] == 0, "FALLO: solo-corzos debería tener SEVERIDAD 0 (sin amenaza)"
    print("  -> solo-lobos ~ v2 (~4.4; idéntico a corzos OFF) | solo-corzos = 0 (sin amenaza) | mixto ≈ solo-lobos bajo")
    print("     Dummy (los corzos solo consumen ciclos de investigación; el agregado MEZCLADO es poco informativo).")
    print("  OK\n")


def save_corzos_animations():
    print("=== Ojeo: CORZOS — solo-corzos (drones investigan y DESCARTAN, rebaño pastando) y MIXTO (descarta corzo + escolta lobo) ===")
    # (1) SOLO-CORZOS: sin lobos -> ESCOLTA jamás; un dron VUELA al grupo, lo comprueba a r_confirm, lo DESCARTA
    #     (gris) y VUELVE a su puesto (fase -> VIGILANCIA); el rebaño pasta. Stride 1 -> ritmo natural (no acelerado).
    w = World(seed=7, corzos_min=3, corzos_max=3, episode_kind="corzos", max_episode_steps=4000)
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]; done = None
    for step in range(2000):
        _, _, term, trunc, _ = w.step(c.act(None))
        hist.append(w.snapshot())                    # stride 1: movimiento suave
        if done is None and w.corzo_dismissed.all():
            done = step
        if (done is not None and step > done + 80) or term or trunc:   # +80 pasos: que el dron VUELVA al puesto
            break
    render_episode(w, hist, save_path="escort_corzos_solo.gif")
    print("  escort_corzos_solo.gif: %d frames (ritmo natural) | fase=%s | corzos descartados=%d/%d | cazadas=%d (el dron vuela, descarta y VUELVE; rebaño pasta)"
          % (len(hist), w.phase, int(w.corzo_dismissed.sum()), w.n_corzos, w.n_depredadas))

    # (2) MIXTO: un dron descarta un corzo y la escolta procede sobre un lobo (ESCOLTA disparada).
    w = None
    for s in range(20):                       # busca una seed mixta que dispare ESCOLTA y descarte algún corzo
        cand = World(seed=s, corzos_min=2, corzos_max=3, episode_kind="mixto", max_episode_steps=900)
        cc = DummyCoordinator(cand.n_drones); seen_esc = seen_dis = False; h = [cand.snapshot()]
        for step in range(900):
            _, _, term, trunc, _ = cand.step(cc.act(None))
            seen_esc = seen_esc or cand.phase == "ESCOLTA"; seen_dis = seen_dis or bool(cand.corzo_dismissed.any())
            if step % 2 == 0 or term or trunc:       # stride 2 -> ritmo observable
                h.append(cand.snapshot())
            if term or trunc:
                break
        if seen_esc and seen_dis:
            w, hist = cand, h; break
    if w is None:
        w, hist = cand, h
    render_episode(w, hist, save_path="escort_corzos_mixto.gif")
    print("  escort_corzos_mixto.gif: %d frames | fase=%s | corzos descartados=%d/%d | cazadas=%d (descarta corzo + escolta lobo)\n"
          % (len(hist), w.phase, int(w.corzo_dismissed.sum()), w.n_corzos, w.n_depredadas))


def save_detection_animation(seed):
    print("=== Ojeo: arco DETECCIÓN -> INVESTIGACIÓN -> CONFIRMACIÓN -> ESCOLTA (sector lejano) ===")
    w = World(seed=seed)
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    susp = esc = None
    for _ in range(500):
        _, _, term, trunc, _ = w.step(c.act(None))
        hist.append(w.snapshot())
        if susp is None and w.phase == "SOSPECHA":
            susp = w.step_count
        if esc is None and w.phase == "ESCOLTA":
            esc = w.step_count
        if (esc is not None and w.step_count >= esc + 40) or term or trunc:
            break
    render_episode(w, hist, save_path="escort_vigilancia_deteccion.gif")
    print("  escort_vigilancia_deteccion.gif: seed=%d, %d frames | SOSPECHA paso %s -> ESCOLTA paso %s\n"
          % (seed, len(hist), susp, esc))


def save_loop_animation(seed=9):
    print("=== Ojeo: BUCLE COMPLETO detectar->confirmar->ESCOLTA->HUIR / FIJAR(pin) / pin-and-flank->1 caza ===")
    w = World(seed=seed)
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    susp = esc = None
    step = 0
    while True:
        _, _, term, trunc, _ = w.step(c.act(None)); step += 1
        if susp is None and w.phase == "SOSPECHA": susp = w.step_count
        if esc is None and w.phase == "ESCOLTA": esc = w.step_count
        if step % 3 == 0 or term or trunc:        # submuestreo x3 -> gif manejable hasta el terminal
            hist.append(w.snapshot())
        # Con Bug 1 arreglado las NO-FIJADAS llegan a salvo -> el episodio RESUELVE (no se arrastra al
        # timeout): corre hasta el terminal para ver el arco entero (pin-and-flank + rebaño/terneros a salvo);
        # tope de seguridad por si una seed se alarga.
        if term or trunc or step >= 1800:
            break
    render_episode(w, hist, save_path="escort_bucle_completo.gif")
    print("  escort_bucle_completo.gif: seed=%d, %d frames | SOSPECHA=%s ESCOLTA=%s -> %s (a salvo %d, cazadas %d)\n"
          % (seed, len(hist), susp, esc, w.status, int(w.cow_safe.sum() + w.calf_safe.sum()), w.n_depredadas))


def save_deterrence_animation():
    print("=== Ojeo: DISUASIÓN — un dron despeja un pin (el lobo se desvía + frena, la vaca reanuda la huida) ===")
    # Escolta, una vaca lejos del establo CLAVADA por un lobo. Un dron ACTIVO vuela a interponerse junto al
    # lobo (lado de la vaca): el lobo esquiva + frena (sale de r_notice) y la vaca reanuda la huida al establo.
    w = World(seed=5, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    ctr = w.safe_zone[:2]
    w.cows[0] = ctr + np.array([52.0, 0.0]); w.cow_heading[0] = np.pi    # cerca del establo -> el gif resuelve
    w.wolves[0] = w.cows[0] + np.array([12.0, 0.0]); w.wolf_vel[0] = 0.0
    # Un dron ACTIVE (el resto aparcado lejos); arranca en una esquina, lejos del lobo (aún NO disuade).
    w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4])
    w.drone_state[0] = ACTIVE; w.drones[0] = ctr + np.array([95.0, 60.0]); w.drone_vel[0] = 0.0
    w.drone_waypoint[0] = w.drones[0].copy()
    hist = [w.snapshot()]
    for step in range(400):
        # GUION DEL OJEO (no es un coordinador; solo SCRIPTea al dron para VER el mecanismo del mundo): tras
        # ver el PIN, el dron se interpone entre la vaca y el lobo (lado de la vaca) y lo va apartando -> la
        # disuasión despeja el pin de forma sostenida y la vaca se refugia. El POSICIONAMIENTO real lo hará
        # el coordinador (post-v2); aquí solo demostramos el efecto disuasorio del mundo.
        if step >= 18 and w.cow_alive[0] and not w.cow_safe[0]:
            gap = w.wolves[0] - w.cows[0]
            w.command_waypoint(0, w.cows[0] + gap * 0.35)     # interpuesto, del lado de la vaca
        w.pack_prey, w.pack_prey_kind = (0, "adult") if (w.cow_alive[0] and not w.cow_safe[0]) else (-1, None)
        _, _, term, trunc, _ = w.step(c.act(None))
        if step % 2 == 0 or term or trunc:       # submuestreo x2 -> gif manejable
            hist.append(w.snapshot())
        if term or trunc:
            break
    render_episode(w, hist, save_path="escort_disuasion.gif")
    print("  escort_disuasion.gif: %d frames | estado=%s | a salvo=%d (el dron despeja el pin -> la vaca REANUDA;"
          " con disuasión PARCIAL un solo dron no siempre la lleva del todo a salvo)\n"
          % (len(hist), w.status, int(w.cow_safe.sum())))


def save_bordeo_animation():
    print("=== Ojeo: BORDEO — el lobo IGNORA al dron de lejos y ARQUEA a su alrededor solo en corto (R=20) ===")
    # Un lobo COMPROMETIDO con una presa (adulta clavada en ESCOLTA) se acerca con un dron QUIETO interpuesto,
    # ligeramente descentrado. De lejos (>DETER_RADIUS) ni se inmuta; al entrar en el radio ARQUEA alrededor del
    # dron (componente tangencial) hacia la presa, a ritmo razonable (no se queda "super lento"). El dron quieto
    # es el Dummy (sin coordinador): RETRASA/desvía, no invulnerabiliza. render dibuja el anillo DETER_RADIUS.
    w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    ctr = w.safe_zone[:2]
    cow = ctr + np.array([78.0, 0.0])
    w.cows[0] = cow.copy(); w.cow_vel[0] = 0.0; w.cow_heading[0] = 0.0       # encara al lobo (al este)
    w.wolves[0] = cow + np.array([46.0, 5.0]); w.wolf_vel[0] = np.array([-3.0, 0.0])  # lejos, ligeramente al norte
    w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4])
    w.drone_state[0] = ACTIVE; w.drones[0] = cow + np.array([20.0, 0.0])     # QUIETO, entre lobo y presa
    w.drone_vel[0] = 0.0; w.drone_waypoint[0] = w.drones[0].copy()
    hist = [w.snapshot()]; lat0 = float(w.wolves[0, 1]); latmax = 0.0; reacted = None
    for step in range(260):
        w.cows[0] = cow.copy(); w.cow_vel[0] = 0.0                            # presa quieta (aísla el bordeo)
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        _, _, term, trunc, _ = w.step(c.act(None))
        d2d = float(np.linalg.norm(w.wolves[0] - w.drones[0]))
        if reacted is None and d2d < DETER_RADIUS:
            reacted = step
        if reacted is not None:
            latmax = max(latmax, abs(float(w.wolves[0, 1]) - lat0))
        if step % 2 == 0 or term or trunc:
            hist.append(w.snapshot())
        if term or trunc:
            break
    render_episode(w, hist, save_path="escort_bordeo.gif")
    print("  escort_bordeo.gif: %d frames | reacciona al entrar en R=%.0f (paso %s) y ARQUEA %.1f m alrededor del dron"
          " (de lejos lo ignora)\n" % (len(hist), DETER_RADIUS, reacted, latmax))


def save_madre_animation():
    print("=== Ojeo: MADRE+TERNERO — huyen JUNTOS al ritmo del ternero, la madre no lo deja atrás ===")
    # Madre + ternero huyendo al establo SIN lobos (HUIR puro); las demás vacas ya a salvo (aísla la pareja).
    # La madre va capada a calf_speed -> migran juntos a ese ritmo; el ternero la sigue sin rezagarse.
    w = World(seed=3, wolves_min=0, wolves_max=0, calf_count_probs=ONE_CALF, max_episode_steps=4000)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"
    dfn = int(w.calf_defender[0]); ctr = w.safe_zone[:2]
    others = [i for i in range(w.n_cows) if i != dfn]
    w.cows[others] = ctr; w.cow_safe[others] = True; w.cow_vel[others] = 0.0
    w.cows[dfn] = ctr + np.array([90.0, 0.0]); w.cow_heading[dfn] = np.pi
    w.calves[0] = w.cows[dfn] + np.array([0.0, -w.calf_personal_space]); w.cow_speeds[dfn] = w.cow_speed
    hist = [w.snapshot()]; maxgap = 0.0
    for step in range(4000):
        _, _, term, trunc, _ = w.step(c.act(None))
        maxgap = max(maxgap, float(np.linalg.norm(w.cows[dfn] - w.calves[0])))
        if step % 3 == 0 or term or trunc:
            hist.append(w.snapshot())
        if (w.cow_safe[dfn] and w.calf_safe[0]) or term or trunc:
            break
    render_episode(w, hist, save_path="escort_madre_ternero.gif")
    print("  escort_madre_ternero.gif: %d frames | a salvo madre=%s ternero=%s | máx dist madre-ternero=%.2f m"
          " (huyen juntos al ritmo del ternero)\n" % (len(hist), bool(w.cow_safe[dfn]), bool(w.calf_safe[0]), maxgap))


def save_zona_animation():
    print("=== Ojeo: ZONA SEGURA — el lobo BORDEA la zona (no se clava) tras refugiarse su presa ===")
    # Una presa a punto de refugiarse + otra res viva al OTRO LADO de la zona. Al refugiarse la presa, el
    # paquete re-fija a la de fuera; el lobo, en vez de clavarse en el borde, ARQUEA alrededor de la zona
    # (por fuera) para alcanzarla. Sin lobo->presa forzado: lo mueve la caza. render dibuja la zona segura.
    w = World(seed=0, n_cows=2, wolves_min=2, wolves_max=2, calf_count_probs=NO_CALVES, max_episode_steps=600)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"
    C, r = w.safe_zone[:2], w.safe_zone[2]
    w.cows[0] = C + np.array([r - w.refuge_margin - 1.0, 0.0])         # presa 0: se refugia en el primer paso
    w.cow_heading[0] = np.arctan2(C[1]-w.cows[0,1], C[0]-w.cows[0,0])
    w.cows[1] = C + np.array([-r - 30.0, 0.0]); w.cow_speeds[1] = 0.0  # res viva al OTRO LADO (oeste), quieta
    w.cow_heading[1] = 0.0
    w.wolves[:] = np.array([C + [r + 4.0, 0.0], C + [r + 7.0, 4.0]]); w.wolf_vel[:] = 0.0   # lobos al ESTE
    w.pack_prey, w.pack_prey_kind = 0, "adult"
    hist = [w.snapshot()]; entered = False; mind = np.inf
    for step in range(600):
        w.cows[1] = C + np.array([-r - 30.0, 0.0]); w.cow_vel[1] = 0.0   # mantener la res de fuera quieta (aísla el bordeo)
        _, _, term, trunc, _ = w.step(c.act(None))
        entered = entered or bool(w.n_wolves > 0 and (np.linalg.norm(w.wolves - C, axis=1) < r).any())
        if w.cow_alive[1] and not w.cow_safe[1]:
            mind = min(mind, float(np.linalg.norm(w.wolves - w.cows[1], axis=1).min()))
        if step % 2 == 0 or term or trunc:
            hist.append(w.snapshot())
        if (not w.cow_alive[1]) or term or trunc:
            break
    render_episode(w, hist, save_path="escort_zona_bordeo.gif")
    print("  escort_zona_bordeo.gif: %d frames | algún lobo entró en la zona=%s | min dist lobo-res(otro lado)=%.1f m"
          " (bordea la zona para alcanzarla)\n" % (len(hist), entered, mind))


def save_pin_animations():
    print("=== Ojeo: PIN — envolvente que MATA a una clavada, y un dron que RETRASA/REDUCE (no invulnerabiliza) ===")
    # (1) ENVOLVENTE: 4 lobos arrancando APIÑADOS en un costado de una adulta clavada -> se reparten
    #     (~N/E/S/O) y la flanquean -> CAZA. (Antes: apiñados en el cono, invulnerable.)
    w, P = _pin_scene(False)
    w.wolves[:] = P + np.array([[14, 3], [14, -3], [12, 6], [12, -6]], dtype=float)   # apiñados al ESTE
    w.wolf_vel[:] = 0.0
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    for _ in range(120):
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        _, _, term, trunc, _ = w.step(c.act(None))
        hist.append(w.snapshot())
        if not w.cow_alive[0] or term or trunc:
            break
    render_episode(w, hist, save_path="escort_pin_envolvente.gif")
    print("  escort_pin_envolvente.gif: %d frames | cazada=%s (4 lobos apiñados se reparten y flanquean)"
          % (len(hist), not w.cow_alive[0]))
    # (2) DRON RETRASA/REDUCE: MISMO arranque apiñado, pero un dron ACTIVO se interpone (GUION del ojeo, no un
    #     coordinador) entre la presa y el lobo más cercano -> aparta a los que se ACERCAN (>r_face_safe) y
    #     RETRASA la caza (más frames que sin dron); el flanqueador comprometido (<r_face_safe) acaba entrando
    #     -> PARCIAL, no invulnerable.
    w, P = _pin_scene(False)
    w.wolves[:] = P + np.array([[14, 3], [14, -3], [12, 6], [12, -6]], dtype=float)   # mismo arranque apiñado
    w.wolf_vel[:] = 0.0
    w.drone_state[0] = ACTIVE; w.drones[0] = P + [30.0, 30.0]; w.drone_vel[0] = 0.0; w.drone_waypoint[0] = w.drones[0].copy()
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    for _ in range(220):
        if w.cow_alive[0]:
            d = np.linalg.norm(w.wolves - w.cows[0], axis=1)
            jn = int(np.argmin(d))                                   # lobo más cercano
            gap = w.wolves[jn] - w.cows[0]
            w.command_waypoint(0, w.cows[0] + gap * 0.5)             # interpuesto del lado de ese lobo
        w.pack_prey, w.pack_prey_kind = 0, "adult"
        _, _, term, trunc, _ = w.step(c.act(None))
        hist.append(w.snapshot())
        if not w.cow_alive[0] or term or trunc:
            break
    render_episode(w, hist, save_path="escort_pin_con_dron.gif")
    print("  escort_pin_con_dron.gif:   %d frames | cazada=%s (el dron interpuesto la RETRASA; el comprometido entra -> parcial)\n"
          % (len(hist), not w.cow_alive[0]))


def save_rodeo_animation():
    print("=== Ojeo: RODEO — una vaca que huye BORDEA a un grupo de lobos de camino al establo ===")
    # Vaca NO-fijada huyendo desde lejos; un grupo de 3 lobos CONGELADO justo en su camino al establo.
    # Con la evitación, la vaca arquea su trayectoria para rodearlos y sigue hasta refugiarse.
    w = World(seed=0, n_cows=1, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=2000)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"; w.cow_speeds[0] = w.cow_speed
    ctr = w.safe_zone[:2]
    w.cows[0] = ctr + np.array([105.0, 0.0]); w.cow_heading[0] = np.pi
    grupo = ctr + np.array([[55.0, 0.0], [50.0, 8.0], [50.0, -8.0]])     # 3 lobos en medio
    hist = [w.snapshot()]
    for k in range(1200):
        w.pack_prey, w.pack_prey_kind = -1, None        # no-fijada -> HUIR (rodea)
        w.wolves[:] = grupo; w.wolf_vel[:] = 0.0          # grupo congelado en el camino
        _, _, term, trunc, _ = w.step(c.act(None))
        if k % 2 == 0 or w.cow_safe[0] or term or trunc:
            hist.append(w.snapshot())
        if w.cow_safe[0] or term or trunc:
            break
    render_episode(w, hist, save_path="escort_rodeo.gif")
    print("  escort_rodeo.gif: %d frames | a salvo=%s (la vaca BORDEA al grupo y llega al establo)\n"
          % (len(hist), bool(w.cow_safe[0])))


def _save_episode(w, cap, path, stride=1):
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    for k in range(cap):
        _, _, term, trunc, _ = w.step(c.act(None))
        if k % stride == 0 or term or trunc:     # submuestreo -> gif manejable en episodios largos
            hist.append(w.snapshot())
        if term or trunc:
            break
    render_episode(w, hist, save_path=path)
    print("  %-28s %d frames -> estado=%s, cazadas=%d, a salvo=%d"
          % (path, len(hist), w.status, w.n_depredadas, int(w.cow_safe.sum() + w.calf_safe.sum())))


def save_animations():
    print("=== Ojeo: una animación corta por terminal ===")
    # ÉXITO: rebaño dentro del establo, lobo merodeando fuera.
    w = World(seed=5, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    w.cows[:] = w.safe_zone[:2] + w.rng.uniform(-6.0, 6.0, size=(w.n_cows, 2))
    w.wolves[:] = w.safe_zone[:2] + np.array([70.0, 0.0])     # lobo fuera del establo, en el campo
    _save_episode(w, 25, "escort_exito.gif")
    # DEPREDACIÓN — MATANZA EXCEDENTE: cúmulo de 3 reses CONGELADAS (cow_speeds=0) y alcanzables, paquete
    # de 5 lobos encima. Mata, re-fija la más cercana y SIGUE -> caen las 3 (in_play=0) -> banner DEPREDACIÓN.
    w = World(seed=1, n_cows=3, wolves_min=5, wolves_max=5, calf_count_probs=NO_CALVES,
              max_episode_steps=400, escort_enabled=False)
    cd = w.safe_zone[:2] + np.array([-55.0, -70.0])
    w.cows[:] = cd + np.array([[-3.0, 0.0], [0.0, 0.0], [3.0, 0.0]])     # cúmulo apretado y quieto
    w.cow_vel[:] = 0.0; w.cow_speeds[:] = 0.0
    ang = np.linspace(0, 2 * np.pi, w.n_wolves, endpoint=False)
    w.wolves[:] = cd + 7.0 * np.column_stack([np.cos(ang), np.sin(ang)])
    w.wolf_vel[:] = 0.0
    w._commit_initial_prey()
    _save_episode(w, 400, "escort_matanza_excedente.gif", stride=2)
    # REBAÑO A SALVO ENTERO (orgánico): lobo SOLO sin terneros -> no fija presa -> todas HUYEN y se
    # refugian -> ÉXITO sin forzar nada (el rebaño entero llega al establo).
    w = World(seed=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    _save_episode(w, w.max_episode_steps, "escort_rebano_a_salvo.gif", stride=5)
    # TIMEOUT: lobo solo (no mata), límite de tiempo bajo.
    w = World(seed=2, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, max_episode_steps=60)
    _save_episode(w, 60, "escort_timeout.gif")
    print()


if __name__ == "__main__":
    test_trigger_dos_etapas()
    test_investigar_confirmar()
    test_investigador_mas_cercano()
    test_exito()
    test_exito_organico()
    test_no_holonomico()
    test_disuasion()
    test_pin_envolvente()
    test_rodeo()
    test_madre_no_abandona()
    test_zona_bordeo()
    test_corzos()
    test_depredacion()
    test_timeout()
    test_refugio_suelta_presa()
    test_wolf_exclusion()
    test_reproducible()
    test_no_regressions()
    far_seed = test_timing_deteccion()
    test_tasa_escolta()
    test_severidad_por_tipo()
    save_animations()
    save_corzos_animations()
    save_pin_animations()
    save_rodeo_animation()
    save_madre_animation()
    save_zona_animation()
    save_deterrence_animation()
    save_bordeo_animation()
    save_detection_animation(far_seed)
    save_loop_animation()
    print("escort_check: TODO OK.")
