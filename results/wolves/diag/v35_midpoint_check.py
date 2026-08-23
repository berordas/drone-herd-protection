"""v35_midpoint_check.py — COMPROBACIÓN NUMÉRICA pedida por el usuario (v3.5): en el punto medio
entre dos drones contiguos, con paredes SOLAPADAS, la resultante de los dos vectores de pared tiene
componente NETA hacia AFUERA (no nula); con paredes TANGENTES (s=2R) es EXACTAMENTE nula.

Descompone los dos vectores radiales del modelo real (dron->lobo, peso fall=1-d/R, ganancia
STATIC_DETER_GAIN·wolf_speed) en el punto (0, y) del corredor (drones en (±s/2, 0)):
  - componente A LO LARGO de la línea: se CANCELA por simetría (se muestra numéricamente);
  - componente PERPENDICULAR hacia afuera: se SUMA (2·(y/d)·fall) — el frenado.
Y muestra el paso completo del modelo (deslizamiento + empuje) = v_wall, con la intención
perpendicular de caza (0, -w): el frenado neto solo vence a la intención con solape grande
(la física real de World._apply_deterrence se usa para validar cada fila).

Uso: python3 v35_midpoint_check.py <spacing> [spacing2 ...]
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, CHARGING, STATIC_DETER_RADIUS as R, STATIC_DETER_GAIN as G
from baseline import build_world

CX, CY = 250.0, 250.0


def setup(spacing: float, k: int):
    """Mundo real con k drones ACTIVE quietos en línea centrada en (CX, CY) (igual que el scan)."""
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
    return w

spacings = [float(a) for a in sys.argv[1:]] or [20.0, 18.0, 7.0]
for s in spacings:
    w = setup(s, 2)
    wsp = w.wolf_speed
    print("=" * 96)
    lens_top = float(np.sqrt(max(R * R - (s / 2) ** 2, 0.0)))
    print(f"s={s:.1f} m (solape {2 * R - s:.1f} m). Punto medio (0, y); drones en (±{s / 2:.1f}, 0). "
          f"Zona de DOBLE pared: y <= {lens_top:.2f} m")
    print(f"{'y':>5} {'d':>6} | {'push_L':>16} {'push_R':>16} | {'Σ_along':>8} {'Σ_out':>7} | "
          f"{'empuje_y m/s':>12} | {'v_wall (modelo real)':>22} | walled")
    for y in (0.01, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
        p = np.array([0.0, y])
        dl = np.array([-s / 2, 0.0])
        dr = np.array([s / 2, 0.0])
        vl, vr = p - dl, p - dr                       # dron -> lobo
        d = float(np.linalg.norm(vl))                 # misma distancia a ambos (punto medio)
        ul, ur = vl / d, vr / d
        fall = max(0.0, 1.0 - d / R)
        pl, pr = ul * fall, ur * fall                 # los DOS vectores de pared del modelo
        along = pl[0] + pr[0]                         # a lo largo de la línea -> debe ser 0
        out = pl[1] + pr[1]                           # perpendicular hacia afuera -> 2*(y/d)*fall
        push_y = G * wsp * out                        # m/s de frenado que añade el modelo
        # validación con la física real: v_wall = _apply_deterrence(intención (0,-w)) en ese punto
        w.wolves[0] = (CX + 0.0, CY + y)
        v_t = np.zeros_like(w.wolves)
        v_t[0] = (0.0, -wsp)
        v_out = w._apply_deterrence(v_t)
        walled = bool(w._wolf_walled[0])
        print(f"{y:5.2f} {d:6.2f} | ({pl[0]:+6.3f},{pl[1]:+6.3f}) ({pr[0]:+6.3f},{pr[1]:+6.3f}) | "
              f"{along:+8.5f} {out:+7.4f} | {push_y:+12.3f} | ({v_out[0, 0]:+7.3f},{v_out[0, 1]:+7.3f}) m/s | "
              f"{'SÍ' if walled else 'no'}")
    print("  -> Σ_along = 0 SIEMPRE (cancelación por simetría). Con s<2R, Σ_out > 0 para todo y>0 "
          "(frenado hacia afuera NETO); con s=2R el lobo solo queda walled en y=0, donde Σ_out=0.")
