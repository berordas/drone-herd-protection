"""
provenance_check.py — Procedencia de capturas + BARRIDO de pounce_margin (remate RELATIVO).

El remate ya no usa un umbral absoluto: la presa cuenta como descolgada cuando su
aislamiento (dist a su vaca más próxima) supera por pounce_margin a la MEDIANA del
aislamiento del RESTO del rebaño AHORA. Aquí se barre el margen sobre las semillas de
baseline y se reporta tasa, % de capturas limpias, standoff-vs-remate del lobo y las
distribuciones de aislamiento Y de outlier (pasto / huddle / rezagada). NO se apunta a
una tasa: con drones quietos el huddle defiende -> tasa baja esperada.
"""

import numpy as np
from collections import Counter
from world import World
from coordinators import DummyCoordinator
from main import run_episode
from baseline import BASELINE_SEEDS

MARGINS = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def run_instrumented(seed, **kw):
    """Un episodio con records por paso: remate/standoff, alarma, aislamientos y outliers."""
    w = World(seed=seed, teleport_guard=True, **kw)
    c = DummyCoordinator(w.n_drones)
    rec = {"pounce_steps": 0, "wolf_steps": 0,
           "calm_iso": [], "alarm_iso": [], "alarm_maxiso": [],
           "calm_outlier": [], "alarm_maxoutlier": [], "timeline": []}
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        if w.n_wolves > 0:
            rec["wolf_steps"] += 1
            rec["pounce_steps"] += int(w._wolf_pounce)
        iso, out = w._cow_isolation, w._cow_outlier
        if w.herd_alarmed:
            rec["alarm_iso"].extend(iso.tolist())
            rec["alarm_maxiso"].append(float(iso.max()))
            rec["alarm_maxoutlier"].append(float(out.max()))
        else:
            rec["calm_iso"].extend(iso.tolist())
            rec["calm_outlier"].extend(out.tolist())
        rec["timeline"].append((bool(w.herd_alarmed), bool(w._wolf_pounce)))
        if term or trunc:
            break
    return w, info, rec


def sweep():
    print("=== BARRIDO de pounce_margin (remate relativo: aislamiento - mediana del resto) ===")
    print("  elige el margen MÁS BAJO cuyas capturas sean ~todas limpias (limpieza + margen, NO tasa)\n")
    print("  %-9s %-13s %-12s" % ("margin", "predation", "limpias"))
    for mg in MARGINS:
        out, captures = Counter(), []
        for s in BASELINE_SEEDS:
            w = World(seed=s, pounce_margin=mg, teleport_guard=True)
            _, m = run_episode(w, DummyCoordinator(w.n_drones))
            out[m["outcome"]] += 1
            if w.capture_info is not None:
                captures.append(w.capture_info)
        n, pred = len(BASELINE_SEEDS), out["predation"]
        clean = sum(c["clean"] for c in captures)
        cl = 100.0 * clean / len(captures) if captures else float("nan")
        print("  %-9.1f %3d/%d = %3.0f%%   %3d/%-3d = %3.0f%%"
              % (mg, pred, n, 100 * pred / n, clean, len(captures), cl))


def report():
    """Detalle con el margen por DEFECTO (el elegido) del World."""
    w0 = World()
    print("\n=== Margen por defecto: %.1f  (remate si el outlier de la presa >= margen) ===" % w0.pounce_margin)
    out, captures, guard = Counter(), [], []
    pounce_steps = wolf_steps = 0
    calm_iso, alarm_iso, alarm_maxiso = [], [], []
    calm_outlier, alarm_maxoutlier = [], []
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
        calm_outlier += rec["calm_outlier"]
        alarm_maxoutlier += rec["alarm_maxoutlier"]
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
    print("  aislamiento nn (media / p90 / max)  [el pasto ya NO debe salir más disperso que la rezagada]:")
    print("    pastando (calma)       : %.1f / %.1f / %.1f" % stats(calm_iso))
    print("    en huddle (alarmado)   : %.1f / %.1f / %.1f" % stats(alarm_iso))
    print("    rezagada (max alarmado): %.1f / %.1f / %.1f" % stats(alarm_maxiso))
    print("  OUTLIER relativo (media / p90 / max)  [margen=%.1f -> separa pasto de rezagada]:" % w0.pounce_margin)
    print("    pastando (todas, calma): %.1f / %.1f / %.1f" % stats(calm_outlier))
    print("    rezagada (max alarmado): %.1f / %.1f / %.1f" % stats(alarm_maxoutlier))

    flagged = [c for c in captures if not c["clean"]]
    print("  capturas MARCADAS: %d" % len(flagged))
    for c in flagged[:10]:
        print("    paso=%d presa=%d aislam=%.2f outlier=%.2f racha=%d sostenido=%s pers=%s salto=%.3f(%s) sobrepaso=%.3f(%s)"
              % (c["step"], c["prey_idx"], c["isolation"], c["outlier"], c["iso_streak"], c["iso_sustained"],
                 c["wolf_pouncing"], c["prey_jump"], c["prey_jump_flag"], c["wolf_overshoot"], c["wolf_overshoot_flag"]))

    if sample_timeline:
        seq = "".join("P" if p else ("A" if a else ".") for (a, p) in sample_timeline)
        print("  timeline del lobo (seed %d)  '.'=standoff/calma  'A'=standoff/alarma  'P'=remate:" % BASELINE_SEEDS[0])
        print("   ", seq[:220] + ("..." if len(seq) > 220 else ""))


if __name__ == "__main__":
    sweep()
    report()
