"""
provenance_check.py — Procedencia de capturas + BARRIDO del umbral de remate.

El umbral se re-ancla a wolf_pounce_isolation = pounce_factor * r_separation. Aquí se
barre el factor sobre las semillas de baseline para encontrar la ventana LIMPIA (que
las capturas sean todas de una rezagada real, sin coger vacas pastando ni del borde
del huddle). Se reporta tasa, % de capturas limpias, standoff-vs-remate del lobo y la
distribución de aislamiento (pasto / huddle / rezagada). NO se apunta a una tasa.
"""

import numpy as np
from collections import Counter
from world import World
from coordinators import DummyCoordinator
from main import run_episode
from baseline import BASELINE_SEEDS

FACTORS = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]


def run_instrumented(seed, **kw):
    """Un episodio con records por paso: remate/standoff, alarma, aislamientos."""
    w = World(seed=seed, teleport_guard=True, **kw)
    c = DummyCoordinator(w.n_drones)
    rec = {"pounce_steps": 0, "wolf_steps": 0,
           "calm_iso": [], "alarm_iso": [], "alarm_maxiso": [], "timeline": []}
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        if w.n_wolves > 0:
            rec["wolf_steps"] += 1
            rec["pounce_steps"] += int(w._wolf_pounce)
        iso = w._cow_isolation
        if w.herd_alarmed:
            rec["alarm_iso"].extend(iso.tolist())
            rec["alarm_maxiso"].append(float(iso.max()))
        else:
            rec["calm_iso"].extend(iso.tolist())
        rec["timeline"].append((bool(w.herd_alarmed), bool(w._wolf_pounce)))
        if term or trunc:
            break
    return w, info, rec


def sweep():
    r_sep = World().r_separation
    print("=== BARRIDO del umbral de remate (umbral = factor * r_separation) ===")
    print("  r_separation (pasto) = %.2f m  -> el umbral DEBE quedar por encima del pasto\n" % r_sep)
    print("  %-7s %-10s %-13s %-12s" % ("factor", "umbral(m)", "predation", "limpias"))
    for f in FACTORS:
        out, captures, rejected = Counter(), [], False
        for s in BASELINE_SEEDS:
            try:
                w = World(seed=s, pounce_factor=f, teleport_guard=True)
            except AssertionError:
                rejected = True
                break
            _, m = run_episode(w, DummyCoordinator(w.n_drones))
            out[m["outcome"]] += 1
            if w.capture_info is not None:
                captures.append(w.capture_info)
        if rejected:
            print("  %-7.2f %-10.2f RECHAZADO por asersión (umbral <= pasto)" % (f, f * r_sep))
            continue
        n, pred = len(BASELINE_SEEDS), out["predation"]
        clean = sum(c["clean"] for c in captures)
        cl = 100.0 * clean / len(captures) if captures else float("nan")
        print("  %-7.2f %-10.2f %3d/%d = %3.0f%%   %3d/%-3d = %3.0f%%"
              % (f, f * r_sep, pred, n, 100 * pred / n, clean, len(captures), cl))


def report():
    """Detalle con el factor por DEFECTO (el elegido) del World."""
    w0 = World()
    print("\n=== Factor por defecto: %.2f  ->  umbral %.2f m  (r_separation=%.2f) ==="
          % (w0.pounce_factor, w0.wolf_pounce_isolation, w0.r_separation))
    out, captures, guard = Counter(), [], []
    pounce_steps = wolf_steps = 0
    calm_iso, alarm_iso, alarm_maxiso = [], [], []
    sample_timeline = None
    for s in BASELINE_SEEDS:
        w, info, rec = run_instrumented(s)
        out[info["status"]] += 1
        if w.capture_info is not None:
            captures.append(w.capture_info)
        guard.extend(w.guard_violations)
        pounce_steps += rec["pounce_steps"]
        wolf_steps += rec["wolf_steps"]
        calm_iso += rec["calm_iso"]
        alarm_iso += rec["alarm_iso"]
        alarm_maxiso += rec["alarm_maxiso"]
        if s == BASELINE_SEEDS[0]:
            sample_timeline = rec["timeline"]

    n, pred = len(BASELINE_SEEDS), out["predation"]
    clean = sum(c["clean"] for c in captures)
    print("  tasa: predation %d/%d = %.0f%%  | timeout %d" % (pred, n, 100 * pred / n, out["timeout"]))
    print("  capturas LIMPIAS: %d/%d = %.0f%%" % (clean, len(captures), 100 * clean / max(len(captures), 1)))
    print("  lobo: STANDOFF %.0f%% / REMATE %.0f%% de los pasos  (debe dominar el standoff)"
          % (100 * (wolf_steps - pounce_steps) / max(wolf_steps, 1), 100 * pounce_steps / max(wolf_steps, 1)))
    print("  guardia de teletransporte: %d violaciones" % len(guard))

    def stats(a):
        a = np.array(a)
        return (a.mean(), np.percentile(a, 90), a.max()) if a.size else (float("nan"),) * 3
    print("  aislamiento (media / p90 / max), umbral=%.1f:" % w0.wolf_pounce_isolation)
    print("    pastando (calma)      : %.1f / %.1f / %.1f" % stats(calm_iso))
    print("    en huddle (alarmado)  : %.1f / %.1f / %.1f" % stats(alarm_iso))
    print("    rezagada (max alarmado): %.1f / %.1f / %.1f" % stats(alarm_maxiso))

    flagged = [c for c in captures if not c["clean"]]
    print("  capturas MARCADAS: %d" % len(flagged))
    for c in flagged[:10]:
        print("    paso=%d presa=%d aislam=%.2f racha=%d sostenido=%s pers=%s salto=%.3f(%s) sobrepaso=%.3f(%s)"
              % (c["step"], c["prey_idx"], c["isolation"], c["iso_streak"], c["iso_sustained"],
                 c["wolf_pouncing"], c["prey_jump"], c["prey_jump_flag"], c["wolf_overshoot"], c["wolf_overshoot_flag"]))

    if sample_timeline:
        seq = "".join("P" if p else ("A" if a else ".") for (a, p) in sample_timeline)
        print("  timeline del lobo (seed %d)  '.'=standoff/calma  'A'=standoff/alarma  'P'=remate:" % BASELINE_SEEDS[0])
        print("   ", seq[:220] + ("..." if len(seq) > 220 else ""))


if __name__ == "__main__":
    sweep()
    report()
