"""
escort_check.py — Verificación del TERMINAL del episodio de escolta + la máquina de fases.

Construye el "juez" ANTES de añadir el guiado al refugio (bandera #13: "verificar el terminal antes
de construir comportamientos encima"). Cubre los tres terminales y sus contadores, la máquina de fases
VIGILANCIA->ESCOLTA, y los DOS ganchos: (a) res en el establo = a salvo y NO cazable; (b) si la presa
fijada se refugia, la manada RE-SELECCIONA (única re-fijación permitida). Drones quietos (DummyCoordinator).

  0) Disparador en DOS etapas: detección (r_detect)->SOSPECHA + 1 dron investigando (+ mensaje al
     coordinador); confirmación (r_confirm)->ESCOLTA + dron liberado; aparcados no cuentan.
  0b) El dron INVESTIGA (se mueve al contacto) y confirma; PRECEDENCIA reflejo>coordinador; buy-time.
  1) ÉXITO forzado
  1b) ÉXITO ORGÁNICO: el GUIADO al refugio (paso 2) conduce el rebaño al establo en ESCOLTA -> ÉXITO sin forzar.
  1c) 'Dar la cara' INTACTO en la fuga (la atracción al refugio es solo traslación; terneros anclados).
  2) DEPREDACIÓN forzada (multi-muerte; cuanta más, peor -> cuenta)
  3) TIMEOUT forzado
  4) Refugio = soltar presa (re-fijación SOLO al refugiarse; 0 en otro caso)
  5) Exclusión del lobo (nunca dentro del establo)
  6) Reproducibilidad (mismo estado terminal + contadores)
  7) Sin regresiones (face_check.py + battery_check.py siguen verdes)
  8) Timing de las dos etapas: paso de SOSPECHA y paso de ESCOLTA (el hueco = tiempo de investigación).
  9) Tasa de la escolta (Dummy + guiado) candidata a v2: MEDIDA (tasa + severidad), no objetivo.
  + Ojeo: animación por terminal + arco detección->ESCOLTA + BUCLE COMPLETO (detectar->fuga->terminal).
"""

import matplotlib
matplotlib.use("Agg")   # sin ventana: guardamos las animaciones a disco
import subprocess
import sys
import numpy as np
from world import World, ACTIVE, CHARGING, READY
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
    print("=== 1b) ÉXITO ORGÁNICO: el rebaño HUYE al establo en ESCOLTA y se resuelve solo ===")
    # Sin forzar NINGÚN estado (solo config + correr): un lobo SOLO (no puede tumbar adultas) dispara la
    # escolta; el guiado conduce el rebaño al establo; TODAS se refugian -> ÉXITO antes del timeout.
    w = World(seed=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    reached_escolta = False
    info = {"status": w.status}
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        reached_escolta |= (w.phase == "ESCOLTA")
        if term or trunc:
            break
    print("  status=%s  n_safe=%d/%d  cazadas=%d  ESCOLTA alcanzada=%s  terminal=%s (max=%d)"
          % (info["status"], info["n_safe"], w.n_cows, info["n_depredadas"], reached_escolta,
             info["terminal_step"], w.max_episode_steps))
    assert reached_escolta, "FALLO: no se llegó a ESCOLTA (el guiado no se activó)"
    assert info["status"] == "success", "FALLO: no hubo ÉXITO orgánico"
    assert info["n_safe"] == w.n_cows and info["n_depredadas"] == 0
    assert info["terminal_step"] is not None and info["terminal_step"] < w.max_episode_steps, \
        "FALLO: se resolvió por TIMEOUT, no por refugio (no es ÉXITO orgánico)"
    print("  OK\n")


def test_dar_la_cara_en_fuga():
    print("=== 1c) 'Dar la cara' INTACTO en la fuga (la atracción al refugio es SOLO traslación) ===")
    # Una res en ESCOLTA, bajo atracción al refugio, con un lobo acercándose por un FLANCO: debe PIVOTAR
    # a encararlo (cono activo) MIENTRAS se traslada al establo. El morro lo gobierna 'dar la cara'; el
    # refugio solo mueve el cuerpo (retroceso con los cuernos por delante, no desbandada).
    w = World(seed=5, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    c = DummyCoordinator(w.n_drones)
    w.phase = "ESCOLTA"
    w.cow_speeds[0] = w.cow_speed
    c0 = w.safe_zone[:2] + np.array([100.0, 0.0])     # 100 m al ESTE del establo
    w.cows[0] = c0
    w.cow_heading[0] = np.pi                           # mira al OESTE (al establo), NO al lobo
    w.cow_vel[0] = 0.0
    w.wolves[0] = c0 + np.array([0.0, 12.0])           # lobo al NORTE, dentro de r_notice
    w.wolf_vel[0] = 0.0
    ang_wolf = np.arctan2(12.0, 0.0)
    err = lambda: abs(((ang_wolf - w.cow_heading[0] + np.pi) % (2 * np.pi)) - np.pi)
    e0, d0 = err(), float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    for _ in range(20):
        w.step(c.act(None))
    e1, d1 = err(), float(np.linalg.norm(w.cows[0] - w.safe_zone[:2]))
    print("  encara: err angular al lobo %.2f->%.2f rad (baja) | traslada: dist al establo %.1f->%.1f m (baja)"
          % (e0, e1, d0, d1))
    assert e1 < e0 - 0.3, "FALLO: la vaca no pivotó a encarar al lobo en la fuga ('dar la cara' roto)"
    assert d1 < d0 - 1.0, "FALLO: la vaca no se trasladó al refugio en ESCOLTA"
    # Terneros: la pareja MIGRA JUNTA (ternero anclado a su defensora durante la fuga).
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


def test_depredacion():
    print("=== 2) DEPREDACIÓN forzada (la manada caza; cuenta de cazadas) ===")
    w = World(seed=1, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=500)
    c = DummyCoordinator(w.n_drones)
    # Escenario: una adulta EXPUESTA con la manada encima; el resto del rebaño lejos.
    w.cows[0] = np.array([75.0, 50.0])
    w.cows[1:] = np.array([15.0, 85.0]) + w.rng.uniform(-2, 2, size=(w.n_cows - 1, 2))
    w.cow_vel[:] = 0.0
    w.wolves[:] = np.array([[85.0, 50.0], [75.0, 40.0], [65.0, 50.0]])
    w.wolf_vel[:] = 0.0
    w._commit_initial_prey()
    info = {"status": w.status}
    for _ in range(500):
        _, _, term, trunc, info = w.step(c.act(None))
        if term or trunc:
            break
    print("  status=%s  n_depredadas=%d  n_safe=%d  capturas=%d  paso=%s"
          % (info["status"], info["n_depredadas"], info["n_safe"], len(w.captures), info["terminal_step"]))
    assert info["n_depredadas"] >= 1, "FALLO: no hubo ninguna depredación"
    assert info["status"] == "predation", "FALLO: el estado no es DEPREDACIÓN (fracaso parcial)"
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
    print("=== 9) Tasa de la escolta (Dummy + guiado) — candidata a v2 (MEDIDA, NO objetivo) ===")
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
        return out, float(np.mean(deaths))
    n_g, n_u = 40, 15
    g_out, g_deaths = sweep(True, n_g)
    u_out, u_deaths = sweep(False, n_u)
    print("  CON guiado (n=%d): %s | depredación=%.0f%% | éxitos=%d | muertes/episodio=%.2f"
          % (n_g, dict(g_out), 100 * g_out["predation"] / n_g, g_out["success"], g_deaths))
    print("  SIN guiado (n=%d): %s | depredación=%.0f%% | muertes/episodio=%.2f"
          % (n_u, dict(u_out), 100 * u_out["predation"] / n_u, u_deaths))
    print("  -> el guiado NO hunde la TASA (la manada a 4 m/s alcanza a la presa antes del establo; el")
    print("     apantallado de los drones es post-v2) pero ~HALVES la SEVERIDAD y hace el ÉXITO orgánico.")
    assert g_out["success"] >= 1, "FALLO: con guiado no se alcanza ÉXITO orgánico en ninguna seed"
    assert g_deaths < u_deaths, "FALLO: el guiado no reduce la severidad (muertes/episodio)"
    print("  OK\n")


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
    print("=== Ojeo: BUCLE COMPLETO detectar->investigar->confirmar->ESCOLTA->FUGA al establo->terminal ===")
    w = World(seed=seed)
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    susp = esc = None
    step = 0
    while True:
        _, _, term, trunc, _ = w.step(c.act(None)); step += 1
        if susp is None and w.phase == "SOSPECHA": susp = w.step_count
        if esc is None and w.phase == "ESCOLTA": esc = w.step_count
        if step % 2 == 0 or term or trunc:        # submuestreo x2 -> gif manejable
            hist.append(w.snapshot())
        if term or trunc:
            break
    render_episode(w, hist, save_path="escort_bucle_completo.gif")
    print("  escort_bucle_completo.gif: seed=%d, %d frames | SOSPECHA=%s ESCOLTA=%s -> %s (a salvo %d, cazadas %d)\n"
          % (seed, len(hist), susp, esc, w.status, int(w.cow_safe.sum() + w.calf_safe.sum()), w.n_depredadas))


def _save_episode(w, cap, path):
    c = DummyCoordinator(w.n_drones)
    hist = [w.snapshot()]
    for _ in range(cap):
        _, _, term, trunc, _ = w.step(c.act(None))
        hist.append(w.snapshot())
        if term or trunc:
            break
    render_episode(w, hist, save_path=path)
    print("  %-26s %d frames -> estado=%s, cazadas=%d, a salvo=%d"
          % (path, len(hist), w.status, w.n_depredadas, int(w.cow_safe.sum() + w.calf_safe.sum())))


def save_animations():
    print("=== Ojeo: una animación corta por terminal ===")
    # ÉXITO: rebaño dentro del establo, lobo merodeando fuera.
    w = World(seed=5, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    w.cows[:] = w.safe_zone[:2] + w.rng.uniform(-6.0, 6.0, size=(w.n_cows, 2))
    w.wolves[:] = w.safe_zone[:2] + np.array([70.0, 0.0])     # lobo fuera del establo, en el campo
    _save_episode(w, 25, "escort_exito.gif")
    # DEPREDACIÓN: escenario construido (manada encima de una adulta expuesta) -> flanqueo -> muerte.
    # Rebaño PEQUEÑO (n_cows=2) y lejos del establo para que se resuelva en pocos pasos (banner visible).
    w = World(seed=1, n_cows=2, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=300)
    cd = w.safe_zone[:2] + np.array([-60.0, -80.0])
    w.cows[0] = cd
    w.cows[1] = cd + np.array([-30.0, 20.0])
    w.wolves[:] = np.array([cd + [12.0, 0.0], cd + [0.0, -12.0], cd + [-12.0, 0.0]])
    w.cow_vel[:] = 0.0
    w.wolf_vel[:] = 0.0
    w._commit_initial_prey()
    _save_episode(w, 250, "escort_depredacion.gif")
    # TIMEOUT: lobo solo (no mata), límite de tiempo bajo.
    w = World(seed=2, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, max_episode_steps=60)
    _save_episode(w, 60, "escort_timeout.gif")
    print()


if __name__ == "__main__":
    test_trigger_dos_etapas()
    test_investigar_confirmar()
    test_exito()
    test_exito_organico()
    test_dar_la_cara_en_fuga()
    test_depredacion()
    test_timeout()
    test_refugio_suelta_presa()
    test_wolf_exclusion()
    test_reproducible()
    test_no_regressions()
    far_seed = test_timing_deteccion()
    test_tasa_escolta()
    save_animations()
    save_detection_animation(far_seed)
    save_loop_animation()
    print("escort_check: TODO OK.")
