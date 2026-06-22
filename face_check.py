"""
face_check.py — Verificación del modelo "DAR LA CARA" (vacas adultas + lobos).

Comprueba el pivote de amenaza (sin apiñamiento; confrontación direccional + flanqueo) y la
PRESA COMÚN de la manada (commitment):
  1) LOBO SOLO -> no puede tumbar a una adulta (regla de nº mínimo + la mantiene a raya).
  2) MANADA -> escenario construido: encara a uno, flanquean los demás, y al juntarse el quórum
     de flanqueadores válidos MUERE; confirma la instrumentación de #3 (quórum -> muerte).
  3) MOVIMIENTO FIRME -> métrica de tembleque (giro medio por paso) baja.
  4) COORDINACIÓN -> con manada, todos confluyen en UNA presa (~1 vaca atacada a la vez),
     pocas re-fijaciones (commitment).
  5) TASA sin drones sobre range(100) + standoff-vs-ataque + desglose de toques + quórum->muerte.
  6) REPRODUCIBILIDAD: misma seed -> misma secuencia.
"""

import numpy as np
from world import World
from coordinators import DummyCoordinator


def run_ep(seed, record=False, **kw):
    """Un episodio con drones quietos. Devuelve outcome, pasos de ataque/standoff, capture_info
    y (si record) las velocidades por paso de vacas y lobos (para la métrica de tembleque)."""
    w = World(seed=seed, **kw)
    c = DummyCoordinator(w.n_drones)
    attack_steps = wolf_steps = 0
    cow_v, wolf_v = [], []
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        if w.n_wolves > 0:
            wolf_steps += 1
            attack_steps += int(w._wolf_attacking)
        if record:
            cow_v.append(w.cow_vel.copy())
            wolf_v.append(w.wolf_vel.copy())
        if term or trunc:
            break
    return w, info["status"], attack_steps, wolf_steps, (cow_v, wolf_v)


# ---------------------------------------------------------------------------- #
def test_lone_wolf_no_kill():
    print("=== 1) Lobo SOLO: no puede tumbar a una adulta ===")
    preds, min_dists = 0, []
    for s in range(30):
        w, status, *_ = run_ep(s, wolves_min=1, wolves_max=1, teleport_guard=True)
        preds += int(status == "predation")
        prey = int(np.argmin(w.cow_speeds))
        min_dists.append(float(np.linalg.norm(w.wolves - w.cows[prey], axis=1).min()))
    print("  depredaciones con 1 lobo (30 seeds): %d  (esperado 0)" % preds)
    print("  dist lobo-presa al final: media=%.1f mín=%.1f  (r_face_safe=%.1f r_standoff=%.1f)"
          % (np.mean(min_dists), np.min(min_dists), w.r_face_safe, w.r_standoff))
    assert preds == 0, "FALLO: un lobo solo tumbó a una adulta"
    print("  OK\n")


def test_pack_flank_kill():
    print("=== 2) MANADA: encara a uno, flanquean los demás -> la débil muere ===")
    w = World(seed=1, wolves_min=3, wolves_max=3, teleport_guard=True)
    c = DummyCoordinator(w.n_drones)
    # Escenario construido: la presa (la más lenta) sola en el centro; el resto del rebaño lejos
    # (para que la manada se centre en ella). 3 lobos: uno al frente, dos a los flancos.
    w.cow_speeds[:] = w.cow_speed
    w.cow_speeds[0] = 0.5 * w.cow_speed            # la 0 es claramente la más débil
    w.cows[0] = np.array([50.0, 50.0])
    w.cows[1:] = np.array([15.0, 85.0]) + w.rng.uniform(-2, 2, size=(w.n_cows - 1, 2))
    w.cow_heading[0] = 0.0                          # mira a +x (al lobo del frente)
    w.cow_vel[:] = 0.0
    w.wolves[:] = np.array([[60.0, 50.0],          # frente (en el cono)
                            [50.0, 40.0],          # flanco
                            [40.0, 50.0]])         # grupa
    w.wolf_vel[:] = 0.0

    killed_step, n_flankers = None, 0
    for t in range(400):
        _, _, term, trunc, _ = w.step(c.act(None))
        if term and w.status == "predation":
            killed_step = w.step_count
            n_flankers = w.capture_info["n_flankers"]
            break
    if killed_step is not None:
        ci = w.capture_info
        q = w.flank_first_quorum
        print("  MUERTE en paso %d: presa=%d (presa fijada=%s) con %d flanqueadores (>= n_min_adult=%d)"
              % (killed_step, ci["prey_idx"], ci["is_pack_prey"], n_flankers, w.n_min_adult))
        print("  #3 instrumentación: primer quórum en paso %s -> muerte=%s"
              % (q["step"] if q else None, q["killed"] if q else None))
        assert ci["is_pack_prey"], "FALLO: la víctima no era la presa fijada de la manada"
        assert n_flankers >= w.n_min_adult, "FALLO: muerte sin suficientes flanqueadores"
        assert q is not None and q["killed"], "FALLO(#3): hubo quórum de flanqueadores pero NO disparó la muerte"
        print("  OK\n")
    else:
        print("  ATASCO: la manada NO consiguió flanquear (revisar parámetros del cono/flanco).\n")
        raise AssertionError("FALLO: la manada no tumbó a la adulta en el escenario construido")


def _mean_turn(vels):
    """Giro medio por paso (rad) de una secuencia de velocidades (T, N, 2). Tembleque bajo = firme."""
    V = np.array(vels)                             # (T, N, 2)
    sp = np.linalg.norm(V, axis=2)                 # (T, N)
    moving = (sp[:-1] > 1e-3) & (sp[1:] > 1e-3)
    dots = np.sum(V[:-1] * V[1:], axis=2)
    cos = np.clip(dots / np.maximum(sp[:-1] * sp[1:], 1e-9), -1.0, 1.0)
    ang = np.arccos(cos)                           # (T-1, N)
    return float(ang[moving].mean()), float(np.percentile(ang[moving], 95))


def test_firm_motion():
    print("=== 3) Movimiento firme (métrica de tembleque: giro por paso, rad) ===")
    # Pastoreo PURO (sin lobo): aísla la firmeza del deambular de la dinámica de acoso.
    wg, _s, _a, _ws, (gcow_v, _) = run_ep(2, record=True, wolves_min=0, wolves_max=0)
    gm, gp95 = _mean_turn(gcow_v)
    print("  vacas pastando (sin lobo): media=%.3f / p95=%.3f" % (gm, gp95))
    # Episodio con MANADA: vacas (incluye la presa acosada) + lobos.
    w, status, _a, _ws, (cow_v, wolf_v) = run_ep(2, record=True, wolves_min=3, wolves_max=3)
    cm, cp95 = _mean_turn(cow_v)
    wm, wp95 = _mean_turn(wolf_v)
    print("  vacas con manada (presa incluida): media=%.3f / p95=%.3f" % (cm, cp95))
    print("  lobos: media=%.3f / p95=%.3f" % (wm, wp95))
    print("  (firme si la media es pequeña, p. ej. << 0.3 rad ~ 17°/paso; la vibración daría ~pi/2)")
    assert gm < 0.35 and wm < 0.5, "FALLO: movimiento con tembleque (giro medio por paso alto)"
    print("  OK\n")


def test_coordination():
    print("=== 4) Coordinación: la manada confluye en UNA presa (commitment) ===")
    simul_means, simul_maxes, refixes = [], [], []
    for s in range(20):
        w, *_ = run_ep(s, wolves_min=3, wolves_max=3)
        if w._simul_steps:
            simul_means.append(w._simul_sum / w._simul_steps)
            simul_maxes.append(w.max_simul_targets)
            refixes.append(w.n_refix)
    print("  vacas atacadas a la vez (20 seeds, 3 lobos): media=%.2f máx=%d  (ideal ~1)"
          % (np.mean(simul_means), max(simul_maxes)))
    print("  re-fijaciones de presa por episodio: media=%.2f máx=%d  (commitment: debe ser bajo)"
          % (np.mean(refixes), max(refixes)))
    assert np.mean(simul_means) < 1.4, "FALLO: la manada NO confluye (ataca varias vacas a la vez)"
    print("  OK\n")


def test_rate_and_standoff():
    print("=== 5) Tasa sin drones (range(100)) + standoff/ataque + toques + quórum->muerte ===")
    from collections import Counter
    out = Counter()
    attack = wolf = 0
    flank_counts = []
    touch = Counter()
    quorum_eps = quorum_killed = 0
    for s in range(100):
        w, status, a, ws, _ = run_ep(s)
        out[status] += 1
        attack += a
        wolf += ws
        touch.update(w.touch_breakdown)
        if w.flank_first_quorum is not None:
            quorum_eps += 1
            quorum_killed += int(bool(w.flank_first_quorum["killed"]))
        if w.capture_info is not None:
            flank_counts.append(w.capture_info["n_flankers"])
    n = 100
    print("  outcomes:", dict(out))
    print("  depredación = %d/%d = %d%%  (no se persigue una tasa; el lobo completo llega en v2)"
          % (out["predation"], n, 100 * out["predation"] // n))
    print("  lobo: ATAQUE %d%% / STANDOFF %d%% de los pasos"
          % (100 * attack // max(wolf, 1), 100 * (wolf - attack) // max(wolf, 1)))
    print("  desglose de TOQUES (lobo en capture_radius):", dict(touch))
    print("  #3 quórum->muerte: %d/%d episodios con quórum acabaron en muerte en ese paso"
          % (quorum_killed, quorum_eps))
    if flank_counts:
        print("  flanqueadores por captura: media=%.1f máx=%d" % (np.mean(flank_counts), max(flank_counts)))


def test_reproducible():
    print("\n=== 6) Reproducibilidad (misma seed) ===")
    w1, *_ = run_ep(7)
    w2, *_ = run_ep(7)
    same = (np.array_equal(w1.cows, w2.cows) and np.array_equal(w1.wolves, w2.wolves)
            and w1.status == w2.status and w1.step_count == w2.step_count)
    print("  estado final idéntico:", same)
    assert same, "FALLO: no reproducible"
    print("  OK")


if __name__ == "__main__":
    test_lone_wolf_no_kill()
    test_pack_flank_kill()
    test_firm_motion()
    test_coordination()
    test_rate_and_standoff()
    test_reproducible()
