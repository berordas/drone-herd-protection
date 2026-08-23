"""v35_verify_fidelity.py — RED TEAM del testbed v3.5.
(1) fidelidad: testbed run() vs _update_wolves REAL (controlador stub) bit a bit, en campo
    abierto y en (250,250) (== centro del ESTABLO safe_zone: ¿importan los clamps omitidos?);
(2) matematica y->0 en el punto medio (¿v_wall -> (0,-w) para cualquier s?);
(3) k=4: nº de drones a <=R del punto medio segun s (¿suma el 3º/4º poste?);
(4) mecanismos omitidos: linea AVANZANDO y linea con JITTER lateral (expulsion radio 20,
    gate approach>SCARE_APPROACH_MIN=1) a s=18: ¿sella el corredor sin colapsar el frente?
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
import world as W
from world import ACTIVE, CHARGING
from baseline import build_world

R = W.STATIC_DETER_RADIUS
G = W.STATIC_DETER_GAIN


def setup(spacing, k, cx, cy):
    w = build_world(0, "lobos")
    w.reset()
    w.drone_state[:] = CHARGING
    w.drone_vel[:] = 0.0
    w.drones[:] = np.array([450.0, 450.0])
    offs = (np.arange(k) - (k - 1) / 2.0) * spacing
    for i, o in enumerate(offs):
        w.drones[i] = (cx + o, cy)
        w.drone_state[i] = ACTIVE
    w.wolves[:] = np.array([440.0, 440.0])
    w.wolf_vel[:] = 0.0
    return w


class StubCtrl:
    """Controlador que emite caza a tope del lobo 0 hacia prey (lo que asume el testbed)."""
    def __init__(self, prey):
        self.prey = np.asarray(prey, dtype=float)

    def decide(self, w):
        v = np.zeros_like(w.wolves)
        d = self.prey - w.wolves[0]
        v[0] = w.wolf_speed * d / max(float(np.linalg.norm(d)), 1e-9)
        return v, False


def run_testbed(w, start, prey, T, cy):
    """La integracion EXACTA de v35_corridor_scan.run()."""
    w.wolves[0] = np.asarray(start, dtype=float)
    w.wolf_vel[0] = 0.0
    traj = [w.wolves[0].copy()]
    for _ in range(T):
        v_t = np.zeros_like(w.wolves)
        d = np.asarray(prey) - w.wolves[0]
        v_t[0] = w.wolf_speed * d / max(float(np.linalg.norm(d)), 1e-9)
        v_t = w._apply_deterrence(v_t)
        w.wolf_vel += w.wolf_inertia * (v_t - w.wolf_vel)
        w.wolves = w.wolves + w.wolf_vel * w.dt
        traj.append(w.wolves[0].copy())
    return np.array(traj)


def run_real(w, start, prey, T):
    """El camino REAL: _update_wolves completo (deter+inercia+integracion+clamps)."""
    w.wolves[0] = np.asarray(start, dtype=float)
    w.wolf_vel[0] = 0.0
    w.wolf_controller = StubCtrl(prey)
    traj = [w.wolves[0].copy()]
    for _ in range(T):
        w._update_wolves()
        traj.append(w.wolves[0].copy())
    return np.array(traj)


print("=" * 100)
print("(1) FIDELIDAD testbed vs _update_wolves real (mismo escenario, T=1500 pasos, s=7.5, off+2)")
for cx, cy, tag in ((150.0, 150.0, "CAMPO ABIERTO (150,150), lejos de establo/central/bordes"),
                    (250.0, 250.0, "(250,250) == CENTRO DEL ESTABLO safe_zone r=60 (el del testbed)")):
    for s, x0 in ((7.5, 2.0), (18.0, 0.0), (12.0, -5.0)):
        wa = setup(s, 4, cx, cy)
        wb = setup(s, 4, cx, cy)
        start = (cx + x0, cy + 25.0)
        prey = (cx, cy - 30.0)
        ta = run_testbed(wa, start, prey, 1500, cy)
        tb = run_real(wb, start, prey, 1500)
        dmax = float(np.abs(ta - tb).max())
        cross_a = bool((ta[:, 1] < cy - 3.0).any())
        cross_b = bool((tb[:, 1] < cy - 3.0).any())
        miny_a = float(ta[:, 1].min() - cy)
        miny_b = float(tb[:, 1].min() - cy)
        print(f"  {tag}: s={s:4.1f} off={x0:+.0f}  max|diff|={dmax:.3e}  "
              f"cruza testbed={cross_a} real={cross_b}  min_y {miny_a:+.2f}/{miny_b:+.2f}")

print()
print("=" * 100)
print("(2) MATEMATICA y->0 en el punto medio exacto (x=0): v_wall del codigo real, intencion (0,-w)")
w = setup(18.0, 2, 150.0, 150.0)
wsp = w.wolf_speed
for s in (18.0, 14.0, 12.0, 8.0, 6.0, 5.0, 4.0, 2.0):
    w2 = setup(s, 2, 150.0, 150.0)
    row = []
    for y in (1.0, 0.1, 0.01, 0.001):
        w2.wolves[0] = (150.0, 150.0 + y)
        v_t = np.zeros_like(w2.wolves)
        v_t[0] = (0.0, -wsp)
        v_o = w2._apply_deterrence(v_t)
        row.append((y, float(v_o[0, 0]), float(v_o[0, 1]), bool(w2._wolf_walled[0])))
    txt = "  ".join(f"y={y:g}:({vx:+.3f},{vy:+.3f}){'W' if wl else ' '}" for y, vx, vy, wl in row)
    print(f"  s={s:4.1f}: {txt}   (limite teorico v_wall->(0,{-wsp:.0f}))")
print(f"  derivada analitica: slide quita w*y/d -> 0; push_y = G*w*2*(y/d)*fall -> 0. Ambos O(y).")

print()
print("=" * 100)
print("(3) k=4: nº de drones-pared a <= R=10 del punto medio (0, y) del hueco central")
for s in (20.0, 18.0, 14.0, 12.0, 10.0, 8.0, 7.0, 6.7, 6.5, 6.0, 5.0, 4.0):
    offs = (np.arange(4) - 1.5) * s          # posiciones x de los 4 drones; hueco central en x=0
    for y in (0.0, 2.0):
        dd = np.sqrt((offs) ** 2 + y ** 2)
        n_in = int((dd <= R).sum())
        if y == 0.0:
            n0 = n_in
        else:
            n2 = n_in
    d3 = 1.5 * s
    print(f"  s={s:5.1f}: dist 3er dron al punto medio = 1.5*s = {d3:5.2f} m -> "
          f"drones a <=10 m: y=0: {n0}, y=2: {n2}  ({'>2 SOLO si s<=6.67' if d3 > R else '3-4 POSTES SUMAN'})")

print()
print("=" * 100)
print("(4) MECANISMOS OMITIDOS por el testbed estatico (expulsion radio 20, gate approach>1 m/s)")
print("    escenario campo abierto (150,150), k=4, lobo atacando el punto medio; drones CON velocidad")


def run_moving(s, k, mode, amp=3.0, period=6.0, T=4000):
    """Drones se mueven de verdad (posicion integrada); fisica real del lobo; se mide cruce."""
    cx, cy = 150.0, 150.0
    w = setup(s, k, cx, cy)
    base = w.drones[:k].copy()
    start = np.array([cx, cy + 25.0])
    prey = np.array([cx, cy - 30.0])
    w.wolves[0] = start
    w.wolf_vel[0] = 0.0
    min_y = start[1]
    n_expel = n_wall = 0
    t = 0.0
    for step in range(T):
        t = step * w.dt
        if mode == "jitter_x":          # vaivén lateral en fase alterna (rotacion de pose / reencaje)
            ph = np.sin(2 * np.pi * t / period)
            vx = amp * (2 * np.pi / period) * np.cos(2 * np.pi * t / period)
            for i in range(k):
                sgn = 1.0 if i % 2 == 0 else -1.0
                w.drones[i, 0] = base[i, 0] + sgn * amp * ph
                w.drone_vel[i] = (sgn * vx, 0.0)
        elif mode == "advance_hold":    # la linea avanza hacia el lobo 2 m/s y RETROCEDE (patrulla +-4 m)
            ph = np.sin(2 * np.pi * t / period)
            vy = amp * (2 * np.pi / period) * np.cos(2 * np.pi * t / period)
            for i in range(k):
                w.drones[i, 1] = base[i, 1] + amp * ph
                w.drone_vel[i] = (0.0, vy)
        v_t = np.zeros_like(w.wolves)
        d = prey - w.wolves[0]
        v_t[0] = w.wolf_speed * d / max(float(np.linalg.norm(d)), 1e-9)
        v_t = w._apply_deterrence(v_t)
        n_expel += int(w._wolf_scared[0])
        n_wall += int(w._wolf_walled[0])
        w.wolf_vel += w.wolf_inertia * (v_t - w.wolf_vel)
        w.wolves = w.wolves + w.wolf_vel * w.dt
        min_y = min(min_y, float(w.wolves[0, 1]))
        if w.wolves[0, 1] < cy - 3.0:
            return True, min_y - cy, n_expel, n_wall, step
    return False, min_y - cy, n_expel, n_wall, T


for s in (20.0, 18.0, 14.0, 12.0):
    for mode, amp, per in (("jitter_x", 3.0, 6.0), ("jitter_x", 1.5, 6.0), ("advance_hold", 4.0, 8.0)):
        crossed, min_y, ne, nw_, steps = run_moving(s, 4, mode, amp, per)
        vmax = amp * 2 * np.pi / per
        print(f"  s={s:4.1f} {mode:12s} amp={amp:.1f}m per={per:.0f}s (v_max={vmax:.2f} m/s): "
          f"{'CRUZA @' + str(steps) if crossed else 'NO cruza (400 s)'}  min_y={min_y:+6.2f}  "
          f"pasos expulsado={ne} walled={nw_}")
print()
print("    control (drones quietos, mismos ataques):")
for s in (20.0, 18.0, 14.0, 12.0):
    cx, cy = 150.0, 150.0
    w = setup(s, 4, cx, cy)
    traj = run_testbed(w, (cx, cy + 25.0), (cx, cy - 30.0), 4000, cy)
    crossed = bool((traj[:, 1] < cy - 3.0).any())
    print(f"  s={s:4.1f} estatico: {'CRUZA' if crossed else 'NO cruza'}  min_y={float(traj[:,1].min()-cy):+6.2f}")
