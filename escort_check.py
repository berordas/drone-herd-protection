"""
escort_check.py — Verificación del TERMINAL del episodio de escolta + la máquina de fases.

Construye el "juez" ANTES de añadir el guiado al refugio (bandera #13: "verificar el terminal antes
de construir comportamientos encima"). Cubre los tres terminales y sus contadores, la máquina de fases
VIGILANCIA->ESCOLTA, y los DOS ganchos: (a) res en el establo = a salvo y NO cazable; (b) si la presa
fijada se refugia, la manada RE-SELECCIONA (única re-fijación permitida). Drones quietos (DummyCoordinator).

  0) Disparador VIGILANCIA->ESCOLTA por DETECCIÓN de un dron en vuelo (r_detect; aparcados no cuentan)
  1) ÉXITO forzado
  2) DEPREDACIÓN forzada (multi-muerte; cuanta más, peor -> cuenta)
  3) TIMEOUT forzado
  4) Refugio = soltar presa (re-fijación SOLO al refugiarse; 0 en otro caso)
  5) Exclusión del lobo (nunca dentro del establo)
  6) Reproducibilidad (mismo estado terminal + contadores)
  7) Sin regresiones (face_check.py + battery_check.py siguen verdes)
  + Ojeo: una animación corta por terminal (ÉXITO / DEPREDACIÓN / TIMEOUT).
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
def test_trigger_deteccion():
    print("=== 0) Disparador VIGILANCIA->ESCOLTA por DETECCIÓN de dron (r_detect) ===")
    corner = np.array([[0.0, 0.0], [0.0, 5.0], [5.0, 0.0], [5.0, 5.0]])   # 4 activos en una esquina

    def fresh():
        w = World(seed=0, wolves_min=1, wolves_max=1)
        w.phase = "VIGILANCIA"
        w.drone_state[:] = READY            # todos aparcados...
        w.drone_state[:4] = ACTIVE          # ...salvo 4 EN VUELO, en una esquina
        w.drones[:4] = corner
        return w

    rd = World(seed=0).r_detect
    # (1) lobo lejos de TODOS los drones activos -> sigue VIGILANCIA.
    w = fresh(); w.drones[4:] = 1.0; w.wolves[:] = [[100.0, 100.0]]   # ~134 m del activo más cercano
    w._update_phase()
    assert w.phase == "VIGILANCIA", "FALLO: disparó con el lobo fuera de r_detect"
    # (2) acercar el lobo a < r_detect de un dron activo -> ESCOLTA en ese paso.
    w.wolves[:] = [[60.0, 60.0]]                                      # ~78 m del activo (5,5) < 100
    w._update_phase()
    assert w.phase == "ESCOLTA", "FALLO: no disparó con un lobo dentro de r_detect de un dron activo"
    # (3) lobo PEGADO a un dron APARCADO (CHARGING) pero lejos de los activos -> NO dispara.
    w = fresh(); w.drone_state[4] = CHARGING; w.drones[4] = [100.0, 100.0]; w.wolves[:] = [[100.0, 100.0]]
    w._update_phase()
    assert w.phase == "VIGILANCIA", "FALLO: un dron aparcado (CHARGING/READY) disparó la detección"
    print("  r_detect=%.0f m | lejos->VIGILANCIA, cerca de ACTIVE->ESCOLTA, cerca de APARCADO->VIGILANCIA" % rd)
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
    w.wolves[:] = np.array([[6.0, 6.0]])
    _save_episode(w, 25, "escort_exito.gif")
    # DEPREDACIÓN: episodio natural con manada (multi-muerte).
    w = World(seed=1, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, max_episode_steps=250)
    _save_episode(w, 250, "escort_depredacion.gif")
    # TIMEOUT: lobo solo (no mata), límite de tiempo bajo.
    w = World(seed=2, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, max_episode_steps=60)
    _save_episode(w, 60, "escort_timeout.gif")
    print()


if __name__ == "__main__":
    test_trigger_deteccion()
    test_exito()
    test_depredacion()
    test_timeout()
    test_refugio_suelta_presa()
    test_wolf_exclusion()
    test_reproducible()
    test_no_regressions()
    save_animations()
    print("escort_check: TODO OK.")
