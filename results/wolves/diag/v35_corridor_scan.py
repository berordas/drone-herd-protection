"""v35_corridor_scan.py — TESTBED (solo lectura de física): ¿qué espaciado SELLA el corredor central
por pura geometría (solape de paredes), sin tocar radio ni modelo de fuerza?

Usa la física REAL del mundo (World._apply_deterrence + inercia + integración, las MISMAS líneas de
_update_wolves) sobre un escenario sintético: una línea de k drones ACTIVE QUIETOS (pose quieta = el
peor caso diagnosticado en v3.4: 54/92 cruces con pose quieta, sin expulsión por movimiento) y un lobo
cuya INTENCIÓN es caza a tope hacia una presa fija detrás de la línea (lo que emite el controlador en
persecución). Se integra la dinámica real y se mide si CRUZA la línea.

Parte A — perfil de fuerza en el CORREDOR CENTRAL (comprobación numérica de la explicación v3.5):
  en el punto medio entre dos drones, con solape, la resultante de las dos paredes tiene componente
  NETA hacia AFUERA (la componente a lo largo de la línea se cancela por simetría; la perpendicular
  se SUMA). Con paredes tangentes (spacing=2R) el lobo solo queda 'walled' sobre la propia línea,
  donde esa componente es 0 -> nada lo frena. Se imprime el perfil v_wall(y) exacto del modelo.

Parte B — barrido de espaciados × ofertas de ataque (centro exacto, desplazado, en diagonal),
  k=2 y k=4: ¿cruza? ¿a qué distancia se estanca?
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, CHARGING, DETER_RADIUS, STATIC_DETER_RADIUS, STATIC_DETER_GAIN
from baseline import build_world

R = STATIC_DETER_RADIUS
CX, CY = 250.0, 250.0          # centro del escenario. OJO (hallazgo de la verificación adversaria): coincide con el
                               # centro del ESTABLO (safe_zone r=60); es equivalente a campo abierto SOLO porque run()
                               # integra sin _clip_to_parcel/_push_outside_circle (fidelidad bit a bit verificada en
                               # (150,150) por v35_verify_fidelity.py). No usar este punto con _update_wolves completo.


def setup(spacing: float, k: int):
    """Mundo real con una línea de k drones ACTIVE quietos centrada en (CX, CY) sobre el eje x."""
    w = build_world(0, "lobos")
    w.reset()
    assert w.escort_enabled
    # línea de k drones; el resto de la flota, lejos y sin estado ACTIVE (no disuade)
    w.drone_state[:] = CHARGING
    w.drone_vel[:] = 0.0
    w.drones[:] = np.array([450.0, 450.0])
    offs = (np.arange(k) - (k - 1) / 2.0) * spacing
    for i, o in enumerate(offs):
        w.drones[i] = (CX + o, CY)
        w.drone_state[i] = ACTIVE
    # un solo lobo activo; el resto del paquete, lejos (sin tocar n_wolves)
    w.wolves[:] = np.array([440.0, 440.0])
    w.wolf_vel[:] = 0.0
    return w


def run(w, start, prey, T=4000):
    """Integra la física real: intención = caza a tope hacia prey; pared/susto del mundo; inercia."""
    w.wolves[0] = np.asarray(start, dtype=float)
    w.wolf_vel[0] = 0.0
    min_y = start[1]
    for _ in range(T):
        v_t = np.zeros_like(w.wolves)
        d = np.asarray(prey) - w.wolves[0]
        v_t[0] = w.wolf_speed * d / max(float(np.linalg.norm(d)), 1e-9)
        v_t = w._apply_deterrence(v_t)                       # la física REAL (misma llamada que _update_wolves)
        w.wolf_vel += w.wolf_inertia * (v_t - w.wolf_vel)
        w.wolves = w.wolves + w.wolf_vel * w.dt
        min_y = min(min_y, float(w.wolves[0, 1]))
        if w.wolves[0, 1] < CY - 3.0:                        # claramente al otro lado de la línea
            return True, min_y
    return False, min_y


# ---------------- Parte A: perfil exacto del modelo en el corredor central ----------------
print("=" * 100)
print("A) PERFIL DE v_wall EN EL CORREDOR CENTRAL (física real, lobo en (0, y) sobre el punto medio,")
print("   intención (0,-w) = caza perpendicular hacia la presa; drones en (±s/2, 0) quietos)")
print("   R=STATIC_DETER_RADIUS=%.0f  GAIN=%.1f  w=wolf_speed  |  v_y>0 = FRENADO NETO HACIA AFUERA" % (R, STATIC_DETER_GAIN))
for spacing in (20.0, 18.0, 16.0, 14.0, 12.0, 10.0, 8.0, 6.0):
    w = setup(spacing, 2)
    ys = np.arange(0.5, 10.01, 0.5)
    rows = []
    for y in ys:
        w.wolves[0] = (CX, CY + y)
        v_t = np.zeros_like(w.wolves)
        v_t[0] = (0.0, -w.wolf_speed)
        v_out = w._apply_deterrence(v_t)
        walled = bool(w._wolf_walled[0])
        rows.append((y, v_out[0, 0], v_out[0, 1], walled))
    lens_top = np.sqrt(max(R ** 2 - (spacing / 2.0) ** 2, 0.0))
    inside = [r for r in rows if r[3]]
    vy_in = np.array([r[2] for r in inside]) if inside else np.array([])
    tag = ""
    if vy_in.size:
        tag = " | v_y en zona walled: min %+.2f  max %+.2f  (>0 en %d/%d puntos)" % (
            vy_in.min(), vy_in.max(), int((vy_in > 0).sum()), vy_in.size)
    print("  s=%4.1f (solape %4.1f m, lente hasta y=%.2f): walled desde y=%.1f%s" % (
        spacing, 2 * R - spacing, lens_top,
        max([r[0] for r in inside], default=0.0), tag))
    if spacing in (20.0, 18.0, 12.0, 8.0):
        for y, vx, vy, wl in rows:
            if wl or y <= max(lens_top + 2.0, 3.0):
                print("      y=%4.1f  v_wall=(%+.2f, %+.2f) m/s  %s" % (y, vx, vy, "WALLED" if wl else ""))

# ---------------- Parte B: barrido dinámico — ¿cruza? ----------------
print("\n" + "=" * 100)
print("B) BARRIDO: lobo real integrado (T=400 s) — 'CRUZA' = pasa 3 m al otro lado de la línea")
print("   ataques: centro exacto / desplazado ±2, ±5 / diagonal 30°; k=2 y k=4 (presa tras el centro)")
attacks = [("centro", 0.0, 0.0), ("off+2", 2.0, 0.0), ("off-5", -5.0, 0.0),
           ("diag30", 15.0, -0.0)]
for k in (2, 4):
    print("  k=%d drones:" % k)
    for spacing in (20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0):
        res = []
        for name, x0, _ in attacks:
            w = setup(spacing, k)
            y0 = 25.0 if name != "diag30" else 15.0
            start = (CX + x0, CY + y0)
            prey = (CX, CY - 30.0)
            crossed, min_y = run(w, start, prey)
            res.append("%s:%s(min_y%+5.1f)" % (name, "CRUZA" if crossed else "no   ", min_y - CY))
        print("    s=%4.1f (solape %4.1f): %s" % (spacing, 2 * R - spacing, " | ".join(res)))
