"""v35_corridor_fine.py — afinado del umbral de sellado del corredor (física real) y CLASIFICACIÓN
del modo de fallo: cruce POR SEGMENTO (entre drones contiguos) vs rodeo POR EL EXTREMO de la línea.
Complementa v35_corridor_scan.py. k=4 (la barrera real), pose quieta (peor caso v3.4)."""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, CHARGING, STATIC_DETER_RADIUS
from baseline import build_world

R = STATIC_DETER_RADIUS
CX, CY = 250.0, 250.0


def setup(spacing: float, k: int):
    w = build_world(0, "lobos")
    w.reset()
    w.drone_state[:] = CHARGING
    w.drone_vel[:] = 0.0
    w.drones[:] = np.array([450.0, 450.0])
    offs = (np.arange(k) - (k - 1) / 2.0) * spacing
    for i, o in enumerate(offs):
        w.drones[i] = (CX + o, CY)
        w.drone_state[i] = ACTIVE
    w.wolves[:] = np.array([440.0, 440.0])
    w.wolf_vel[:] = 0.0
    return w, offs


def run(w, offs, start, prey, T=6000):
    w.wolves[0] = np.asarray(start, dtype=float)
    w.wolf_vel[0] = 0.0
    min_y, prev = start[1], np.asarray(start, dtype=float).copy()
    half = abs(offs[0])
    for _ in range(T):
        v_t = np.zeros_like(w.wolves)
        d = np.asarray(prey) - w.wolves[0]
        v_t[0] = w.wolf_speed * d / max(float(np.linalg.norm(d)), 1e-9)
        v_t = w._apply_deterrence(v_t)
        w.wolf_vel += w.wolf_inertia * (v_t - w.wolf_vel)
        w.wolves = w.wolves + w.wolf_vel * w.dt
        p = w.wolves[0]
        min_y = min(min_y, float(p[1]))
        if prev[1] >= CY > p[1]:                                  # cruza la RECTA y=CY este paso
            lam = (prev[1] - CY) / max(prev[1] - p[1], 1e-12)
            x_at = float(prev[0] + lam * (p[0] - prev[0])) - CX
            mode = "SEGMENTO" if -half - 1e-9 <= x_at <= half + 1e-9 else "EXTREMO"
            return mode, x_at, min_y
        prev = p.copy()
    return "no-cruza", float("nan"), min_y


print("k=4 drones, pose QUIETA. presa 30 m detras del centro. clasificacion del cruce de la RECTA de la linea:")
print("  SEGMENTO = dentro del tramo ocupado por drones (la gotera) | EXTREMO = rodeo por el flanco (agujero aceptado)")
attacks = [("centro", 0.0, 25.0), ("off+1", 1.0, 25.0), ("off-2", -2.0, 25.0), ("off+4", 4.0, 25.0),
           ("off-8", -8.0, 25.0), ("diag_x15", 15.0, 15.0), ("diag_x25", 25.0, 12.0), ("diag_x40", 40.0, 20.0)]
for spacing in (8.0, 7.5, 7.2, 7.0, 6.5, 6.0):
    w0, offs = setup(spacing, 4)
    res = []
    for name, x0, y0 in attacks:
        w, offs = setup(spacing, 4)
        mode, x_at, min_y = run(w, offs, (CX + x0, CY + y0), (CX, CY - 30.0))
        if mode == "no-cruza":
            res.append("%s: aguanta (min_y %+.1f)" % (name, min_y - CY))
        else:
            res.append("%s: %s x=%+.1f" % (name, mode, x_at))
    print("  s=%.1f (solape %.1f, linea %.0f m):" % (spacing, 2 * R - spacing, 3 * spacing))
    for r in res:
        print("      " + r)
