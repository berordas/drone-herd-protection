"""
provenance_check.py — ¿Las capturas son remates LEGÍTIMOS o artefactos?

Corre el mundo (comportamiento NUEVO, params por defecto) sobre las semillas de
baseline.py con la guardia de teletransporte activada, y resume la procedencia de
cada captura: aislamiento sostenido de la presa, si el lobo iba en persecución, y
si hubo salto de la presa o sobrepaso del lobo (teletransporte). NO recalibra nada.
"""

import numpy as np
from collections import Counter
from world import World
from coordinators import DummyCoordinator
from main import run_episode
from baseline import BASELINE_SEEDS


def main():
    out = Counter()
    captures, guard = [], []
    w0 = World()  # solo para leer parámetros derivados
    for s in BASELINE_SEEDS:
        w = World(seed=s, teleport_guard=True)
        _, m = run_episode(w, DummyCoordinator(w.n_drones))
        out[m["outcome"]] += 1
        if w.capture_info is not None:
            captures.append(w.capture_info)
        guard.extend(w.guard_violations)

    n = len(BASELINE_SEEDS)
    pred = out["predation"]
    print("=== Tasa NUEVA sobre %d semillas de baseline (sin recalibrar) ===" % n)
    print("  outcomes:", dict(out))
    print("  predation = %d/%d = %.1f%%" % (pred, n, 100 * pred / n))
    print("  umbral de pounce = 0.25*cow_spread = %.2f m   (cow_spread=%.1f, r_separation=%.1f)"
          % (w0.wolf_pounce_isolation, w0.cow_spread, w0.r_separation))
    print("  r_alarm=%.1f  r_calm=%.1f  K(sostenido)=%d pasos  motion_tol=%.1f"
          % (w0.r_alarm, w0.r_calm, w0.iso_sustain_steps, w0.motion_tol))

    if captures:
        iso = np.array([c["isolation"] for c in captures])
        clean = [c for c in captures if c["clean"]]
        flagged = [c for c in captures if not c["clean"]]
        print("\n=== Procedencia de %d capturas ===" % len(captures))
        print("  aislamiento de la presa al capturar: media=%.2f min=%.2f max=%.2f (umbral=%.2f)"
              % (iso.mean(), iso.min(), iso.max(), w0.wolf_pounce_isolation))
        print("  LIMPIAS (aislam. sostenido >=%d pasos + en persecución + sin salto/sobrepaso): %d/%d"
              % (w0.iso_sustain_steps, len(clean), len(captures)))
        print("  MARCADAS: %d" % len(flagged))
        print("  motivos: sin_aislam_sostenido=%d  no_persecución=%d  salto_presa=%d  sobrepaso_lobo=%d"
              % (sum(not c["iso_sustained"] for c in captures),
                 sum(not c["wolf_pouncing"] for c in captures),
                 sum(c["prey_jump_flag"] for c in captures),
                 sum(c["wolf_overshoot_flag"] for c in captures)))
        for c in flagged:
            print("    [marcada] paso=%d presa=%d aislam=%.2f racha=%d sostenido=%s pers=%s "
                  "salto=%.3f(%s) sobrepaso=%.3f(%s)"
                  % (c["step"], c["prey_idx"], c["isolation"], c["iso_streak"], c["iso_sustained"],
                     c["wolf_pouncing"], c["prey_jump"], c["prey_jump_flag"],
                     c["wolf_overshoot"], c["wolf_overshoot_flag"]))

    print("\n=== Guardia de teletransporte (sobre %d episodios) ===" % n)
    print("  violaciones totales: %d" % len(guard))
    for g in guard[:20]:
        print("    %-4s idx=%d paso=%d disp=%.3f > max=%.3f" % (g["entity"], g["idx"], g["step"], g["disp"], g["max"]))


if __name__ == "__main__":
    main()
