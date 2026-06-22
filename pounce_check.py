"""
pounce_check.py — Remate RELATIVO + regresión anti-colapso del pasto.

Dos comprobaciones del paso "pounce relativo + cohesión de pasto suelta":
  1) test de OUTLIER INYECTADO (unitario, determinista): el criterio relativo dispara
     sobre una rezagada clara y NO sobre un rebaño uniforme (standoff). Valida la lógica
     aunque las capturas naturales sean pocas (el huddle defiende).
  2) regresión ANTI-COLAPSO: pasto solo (sin lobo); el spread del rebaño se estabiliza en
     un valor MODERADO -> ni -> 0 (el bug original de cohesión 0.4) ni -> radio del área
     (la sobre-corrección de cohesión 0). Barre k_cohesion_calm para elegir el equilibrio.

Conduce métodos del World directamente (sin step()) para aislar cada dinámica.
"""

import numpy as np
from world import World


def _ring(n, center, radius):
    """n puntos equiespaciados en un anillo -> vecina más próxima ~igual para todas."""
    ang = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([center[0] + radius * np.cos(ang),
                            center[1] + radius * np.sin(ang)])


def test_injected_outlier():
    print("=== Test de outlier inyectado (criterio de remate relativo) ===")
    center = np.array([50.0, 50.0])

    # Rebaño UNIFORME: 6 vacas en un anillo (vecina más próxima ~igual -> outlier ~0 -> standoff).
    w = World(seed=0, wolves_min=1, wolves_max=1)
    w.cows = _ring(w.n_cows, center, 5.0)
    w.wolves = np.array([[50.0, 30.0]])
    nn, outlier = w._herd_isolation()
    w._update_wolves()
    print("  uniforme : nn medio=%.2f  outlier max=%.2f  margen=%.2f  -> pounce=%s (esperado False)"
          % (nn.mean(), outlier.max(), w.pounce_margin, w._wolf_pounce))
    assert not w._wolf_pounce, "FALLO: remató sobre un rebaño uniforme (debería ser standoff)"

    # Rebaño con REZAGADA: una vaca claramente descolgada -> presa Y outlier -> remate (persecución).
    w = World(seed=0, wolves_min=1, wolves_max=1)
    cows = _ring(w.n_cows, center, 5.0)
    cows[0] = np.array([50.0, 85.0])            # descolgada muy lejos del grupo
    w.cows = cows
    w.wolves = np.array([[50.0, 30.0]])
    wolf_before = w.wolves.copy()
    nn, outlier = w._herd_isolation()
    prey_idx = int(np.argmax(np.linalg.norm(w.cows - w.cows.mean(axis=0), axis=1)))
    w._update_wolves()
    disp = w.wolves[0] - wolf_before[0]
    toward = float(disp @ (cows[0] - wolf_before[0]))   # proyección del avance sobre la dir. a la presa
    print("  rezagada : presa=%d  su outlier=%.2f  margen=%.2f  -> pounce=%s (esperado True)"
          % (prey_idx, outlier[prey_idx], w.pounce_margin, w._wolf_pounce))
    print("  el lobo avanza HACIA la rezagada: proy=%.3f (esperado > 0)" % toward)
    assert prey_idx == 0, "la rezagada debería ser la presa (la más expuesta)"
    assert w._wolf_pounce, "FALLO: NO remató sobre una rezagada clara"
    assert toward > 0, "FALLO: el lobo no persigue a la rezagada en el remate"
    print("  OK\n")


def grazing_spread(k, seed=0, steps=2000, warmup=1500):
    """Pasto SOLO (sin lobo): conduce _update_cows() y mide spread (dist media al centroide)
    y vecina-más-próxima en régimen permanente (media tras warmup). Sin step() -> sin lobo
    ni terminal; aísla la dinámica de pastoreo."""
    w = World(seed=seed, wolves_min=0, wolves_max=0, k_cohesion_calm=k)
    spreads, nns = [], []
    for t in range(steps):
        w._update_cows()
        if t >= warmup:
            c = w.cows
            spreads.append(float(np.linalg.norm(c - c.mean(axis=0), axis=1).mean()))
            d = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2)
            np.fill_diagonal(d, np.inf)
            nns.append(float(d.min(axis=1).mean()))
    return float(np.mean(spreads)), float(np.mean(nns))


def test_grazing_equilibrium():
    print("=== Regresión anti-colapso del pasto (spread de equilibrio, sin lobo) ===")
    w0 = World()
    print("  cow_spread(radio del área)=%.1f  r_separation=%.1f  k_cohesion_calm(def)=%.2f"
          % (w0.cow_spread, w0.r_separation, w0.k_cohesion_calm))
    print("  %-18s %-18s %-14s" % ("k_cohesion_calm", "spread(centroide)", "vecina próxima"))
    for k in [0.0, 0.15, 0.30, 0.50, 0.80]:
        sp, nn = grazing_spread(k)
        mark = "  <- default" if abs(k - w0.k_cohesion_calm) < 1e-9 else ""
        print("  %-18.2f %-18.2f %-14.2f%s" % (k, sp, nn, mark))
    sp, nn = grazing_spread(w0.k_cohesion_calm)
    # Banda moderada: ni colapso (-> 0) ni llenar el área (spread de un disco lleno = (2/3)*radio).
    lo, hi = 1.5, (2.0 / 3.0) * w0.cow_spread
    print("  equilibrio (default): spread=%.2f  nn=%.2f   banda moderada [%.1f, %.1f]" % (sp, nn, lo, hi))
    assert lo < sp < hi, "FALLO: el pasto no se estabiliza en un grupo suelto (colapsa o llena el área)"
    print("  OK\n")


if __name__ == "__main__":
    test_injected_outlier()
    test_grazing_equilibrium()
