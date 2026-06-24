"""
drone_check.py — Verificación de la DINÁMICA DE VUELO del dron y el coste de batería por moverse.

Mecánica AISLADA (paso 3a): el dron es holonómico (cuadricóptero, se mueve en cualquier dirección),
persigue un waypoint con rapidez/aceleración máximas y se PARA en el destino; moverse drena más
batería que flotar (flag #7, "pursuit cost"). NO cambia aún ningún comportamiento de detección/escolta
(el disparador es el paso 3b). El DummyCoordinator no comanda nada -> los drones se quedan quietos.

  1) Punto a punto: A->B acelera, cruza, frena y se PARA en B (sin overshoot sostenido).
  2) Respeta topes: rapidez pico <= DRONE_MAX_SPEED, aceleración por paso <= DRONE_MAX_ACCEL.
  3) Coste de moverse: un dron que reposiciona drena MÁS que uno que flota (flote = suelo).
  4) Reproducibilidad: misma semilla -> misma trayectoria.
  5) Sin regresiones: face_check 12/12, battery_check 4/2/2, escort_check 8/8 verdes.
  + Ojeo: animación de un dron volando A->B.
"""

import matplotlib
matplotlib.use("Agg")
import subprocess
import sys
import numpy as np
from world import World, ACTIVE, DRONE_MAX_SPEED, DRONE_MAX_ACCEL
from coordinators import DummyCoordinator


def _fly(seed, A, B, n=400, record=False):
    """Comanda al dron 0 volar de A a B y registra su cinemática. Devuelve (pos, speed, accel, world)."""
    w = World(seed=seed, wolves_min=0, wolves_max=0)
    c = DummyCoordinator(w.n_drones)
    w.drones[0] = np.asarray(A, dtype=float)
    w.drone_vel[0] = 0.0
    w.command_waypoint(0, B)
    pos, spd, acc = [w.drones[0].copy()], [0.0], [0.0]
    prev_v = w.drone_vel[0].copy()
    hist = [w.snapshot()] if record else None
    for _ in range(n):
        w.step(c.act(None))
        if record:
            hist.append(w.snapshot())
        v = w.drone_vel[0].copy()
        pos.append(w.drones[0].copy())
        spd.append(float(np.linalg.norm(v)))
        acc.append(float(np.linalg.norm(v - prev_v) / w.dt))
        prev_v = v
        if float(np.linalg.norm(w.drones[0] - B)) < 0.3 and spd[-1] < 0.1:
            break
    return np.array(pos), np.array(spd), np.array(acc), w, hist


# ---------------------------------------------------------------------------- #
def test_point_to_point():
    print("=== 1) Punto a punto: A->B acelera, cruza, frena y se PARA en B ===")
    A, B = np.array([20.0, 20.0]), np.array([200.0, 200.0])
    pos, spd, acc, w, _ = _fly(0, A, B)
    d_final = float(np.linalg.norm(pos[-1] - B))
    # Overshoot a lo largo del eje A->B: ¿se pasó del destino?
    dirAB = (B - A) / np.linalg.norm(B - A)
    s = (pos - A) @ dirAB
    overshoot = max(0.0, float(s.max() - np.linalg.norm(B - A)))
    print("  parado en %d pasos | dist final a B=%.3f m | velocidad final=%.3f m/s | overshoot=%.3f m"
          % (len(pos) - 1, d_final, spd[-1], overshoot))
    assert d_final < 0.5, "FALLO: no llegó a B"
    assert spd[-1] < 0.1, "FALLO: no se detuvo en B"
    assert overshoot < 1.0, "FALLO: overshoot sostenido (se pasó del destino)"
    print("  OK\n")


def test_caps():
    print("=== 2) Respeta los topes físicos (SI) ===")
    _pos, spd, acc, _w, _ = _fly(0, np.array([10.0, 10.0]), np.array([260.0, 260.0]))
    print("  rapidez pico=%.4f m/s (cap %.1f) | aceleración pico=%.4f m/s² (cap %.1f)"
          % (spd.max(), DRONE_MAX_SPEED, acc.max(), DRONE_MAX_ACCEL))
    assert spd.max() <= DRONE_MAX_SPEED * (1 + 1e-6), "FALLO: supera DRONE_MAX_SPEED"
    assert acc.max() <= DRONE_MAX_ACCEL * (1 + 1e-6), "FALLO: supera DRONE_MAX_ACCEL"
    print("  OK\n")


def test_move_cost():
    print("=== 3) Coste de moverse: reposicionar drena MÁS que flotar (flate = suelo) ===")
    w = World(seed=0, wolves_min=0, wolves_max=0)
    c = DummyCoordinator(w.n_drones)
    w.drone_state[0] = ACTIVE
    w.drone_state[1] = ACTIVE
    w.battery[0] = w.battery[1] = 1.0
    w.drones[0] = np.array([150.0, 150.0])
    w.drones[1] = np.array([40.0, 40.0])
    w.command_waypoint(0, w.drones[0].copy())          # dron 0 FLOTA (waypoint = su posición)
    corners = [np.array([40.0, 40.0]), np.array([260.0, 260.0])]
    tgt = 1
    w.command_waypoint(1, corners[tgt])                # dron 1 se REPOSICIONA sin parar (ping-pong)
    N = 300
    for _ in range(N):
        if float(np.linalg.norm(w.drones[1] - corners[tgt])) < 25.0:
            tgt = 1 - tgt
            w.command_waypoint(1, corners[tgt])
        w.step(c.act(None))
    floor = w.drain_rate_active * w.dt                 # drenaje por paso flotando (suelo)
    drained_hover = 1.0 - w.battery[0]
    drained_move = 1.0 - w.battery[1]
    print("  en %d pasos: flota drena=%.4f (=%d*suelo) | reposiciona drena=%.4f (%.1fx) | suelo/paso=%.2e"
          % (N, drained_hover, round(drained_hover / floor), drained_move, drained_move / drained_hover, floor))
    assert drained_move > drained_hover * 1.3, "FALLO: moverse no drena más que flotar"
    assert abs(drained_hover - N * floor) < 1e-6, "FALLO: flotar no es exactamente el suelo de consumo"
    print("  OK\n")


def test_reproducible():
    print("=== 4) Reproducibilidad (misma semilla -> misma trayectoria) ===")
    p1, *_ = _fly(7, np.array([30.0, 30.0]), np.array([180.0, 90.0]))
    p2, *_ = _fly(7, np.array([30.0, 30.0]), np.array([180.0, 90.0]))
    same = p1.shape == p2.shape and np.allclose(p1, p2)
    print("  trayectorias idénticas:", same)
    assert same, "FALLO: no reproducible"
    print("  OK\n")


def test_no_regressions():
    print("=== 5) Sin regresiones (face_check + battery_check + escort_check) ===")
    for script in ("face_check.py", "battery_check.py", "escort_check.py"):
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        ok = r.returncode == 0
        print("  %-16s -> %s" % (script, "VERDE" if ok else "ROJO (exit %d)" % r.returncode))
        assert ok, "FALLO: %s no pasó\n%s" % (script, (r.stdout + r.stderr)[-800:])
    print("  OK\n")


def save_animation():
    print("=== Ojeo: un dron volando A->B ===")
    _pos, _spd, _acc, w, hist = _fly(0, np.array([30.0, 30.0]), np.array([260.0, 250.0]), record=True)
    from render import render_episode
    render_episode(w, hist, save_path="drone_flight.gif")
    print("  drone_flight.gif: %d frames\n" % len(hist))


if __name__ == "__main__":
    test_point_to_point()
    test_caps()
    test_move_cost()
    test_reproducible()
    test_no_regressions()
    save_animation()
    print("drone_check: TODO OK.")
