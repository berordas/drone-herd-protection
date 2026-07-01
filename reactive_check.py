"""
reactive_check.py — Verificación del ReactiveCoordinator (barrera de apantallado, regla FIJA).

Comprueba el COMPORTAMIENTO del primer coordinador de verdad (NO la física, congelada v2):
  1) BARRERA: en ESCOLTA los drones libres se sitúan ENTRE la manada y el rebaño, REPARTIDOS
     (no amontonados, no cada uno a por un lobo).
  2) REACTIVO: la barrera se reposiciona al moverse la manada.
  3) SIN PRESA FIJADA: la heurística NO usa pack_prey (defiende al rebaño en conjunto).
  4) PENETRADO: con la manada entre las vacas, cubre a los lobos más cercanos a ellas (no barrera externa inútil).
  5) PATRULLA: sin amenaza confirmada (solo-corzos), orbitan alrededor del rebaño.
  6) SEVERIDAD (muestra pequeña): Reactive <= Dummy en solo-lobos/mixto; solo-corzos sigue 0.
  7) REPRODUCIBILIDAD.
Guarda dos renders: barrera en acción (solo-lobos/mixto) y patrulla (solo-corzos).

El mundo NO se toca (world.py congelado); solo se añade y verifica el coordinador. La baseline Dummy
sigue idéntica (mismo arnés baseline.py). face_check y la regresión siguen verdes.
"""

from __future__ import annotations
import sys
import subprocess

import numpy as np

from world import World, ACTIVE
from coordinators import ReactiveCoordinator, DummyCoordinator
from render import render_episode


# ---------------------------------------------------------------------------- #
def _free(w) -> np.ndarray:
    return (w.drone_state == ACTIVE) & (~w.drone_investigating)


def _herd(w) -> np.ndarray:
    m = w.cow_alive & ~w.cow_safe
    parts = [w.cows[m]] if m.any() else []
    if w.n_calves > 0:
        mc = w.calf_alive & ~w.calf_safe
        if mc.any():
            parts.append(w.calves[mc])
    return np.vstack(parts) if parts else np.zeros((0, 2))


def _advance_to_escolta(w, c, cap=4000) -> bool:
    while w.phase != "ESCOLTA":
        w.step(c.act(w.get_observation()))
        if w.step_count >= cap or (w.cow_alive & ~w.cow_safe).sum() == 0:
            return False
    return True


# ---------------------------------------------------------------------------- #
def test_barrera():
    print("=== 1) BARRERA de apantallado: drones ENTRE manada y rebaño, REPARTIDOS ===")
    w = World(seed=1, corzos_max=3, episode_kind="lobos"); w.reset()
    c = ReactiveCoordinator(w)
    assert _advance_to_escolta(w, c), "no llegó a ESCOLTA"
    for _ in range(120):                                  # deja VOLAR a los drones a la barrera (hasta ~150 m)
        w.step(c.act(w.get_observation()))
    free = _free(w); herd = _herd(w)
    dr = w.drones[free]; pc = w.wolves.mean(0); hc = herd.mean(0)
    u = pc - hc; L = float(np.linalg.norm(u)); u = u / max(L, 1e-9)
    proj = ((dr - hc) @ u) / max(L, 1e-9)                 # 0 = en el rebaño, 1 = en el paquete
    perp = np.array([-u[1], u[0]]); lat = (dr - hc) @ perp
    sep = np.linalg.norm(dr[:, None, :] - dr[None, :, :], axis=2); np.fill_diagonal(sep, np.inf)
    print("  %d drones libres | proj eje rebaño->paquete media=%.2f (0<..<1 = en medio) | ancho del frente=%.0f m | sep mín=%.1f m"
          % (free.sum(), proj.mean(), lat.max() - lat.min(), sep.min()))
    assert free.sum() >= 2, "hacen falta >=2 drones libres para una barrera"
    assert proj.mean() > 0.05 and (proj > -0.15).all() and proj.mean() < 0.9, \
        "los drones no están en el lado de la amenaza (entre rebaño y paquete)"
    assert lat.max() - lat.min() > c.drone_spacing, "no REPARTEN el frente (amontonados)"
    assert sep.min() > 0.5 * c.drone_spacing, "drones amontonados (o cada uno a por un lobo)"
    print("  OK\n")


def test_reactivo():
    print("=== 2) REACTIVO: la barrera se reposiciona al moverse la manada ===")
    w = World(seed=1, corzos_max=3, episode_kind="lobos"); w.reset()
    c = ReactiveCoordinator(w)
    assert _advance_to_escolta(w, c)
    idx = np.where(_free(w))[0]
    center1 = c.act(w.get_observation())[idx].mean(0)
    w.wolves[:, 0] += 50.0                                 # mueve el paquete +X (solo el estado; sin step)
    center2 = c.act(w.get_observation())[idx].mean(0)
    print("  centro de la barrera: %s -> %s (paquete movido +50 en X)" % (np.round(center1, 1), np.round(center2, 1)))
    assert center2[0] > center1[0] + 5.0, "la barrera NO siguió al paquete (no reactiva)"
    print("  OK\n")


def test_sin_presa_fijada():
    print("=== 3) DEFIENDE A TODAS: la heurística NO usa la presa fijada (pack_prey) ===")
    w = World(seed=1, corzos_max=3, episode_kind="lobos"); w.reset()
    c = ReactiveCoordinator(w)
    assert _advance_to_escolta(w, c)
    a1 = c.act(w.get_observation()).copy()
    alive = np.where(w.cow_alive & ~w.cow_safe)[0]
    w.pack_prey = int(alive[-1]); w.pack_prey_kind = "adult"   # cambia la presa fijada del paquete
    a2 = c.act(w.get_observation())
    print("  waypoints idénticos tras cambiar pack_prey: %s (no depende de la presa fijada)" % np.allclose(a1, a2))
    assert np.allclose(a1, a2), "FALLO: el coordinador depende de la presa fijada"
    print("  OK\n")


def test_penetrado():
    print("=== 4) PENETRADO: manada entre las vacas -> cubre a los lobos más cercanos a ellas ===")
    w = World(seed=3, corzos_max=3, episode_kind="lobos"); w.reset()
    c = ReactiveCoordinator(w)
    assert _advance_to_escolta(w, c)
    for _ in range(40):
        w.step(c.act(w.get_observation()))
    herd = _herd(w); hc = herd.mean(0)
    herd_r = float(np.linalg.norm(herd - hc, axis=1).max()) if herd.shape[0] > 1 else 0.0
    w.wolves[:] = hc + np.random.default_rng(0).normal(0.0, 3.0, size=w.wolves.shape)   # manada DENTRO del rebaño
    idx = np.where(_free(w))[0]
    tgt = c.act(w.get_observation())[idx]
    d_hc = np.linalg.norm(tgt - hc, axis=1)
    print("  %d drones | dist target->centroide del rebaño: máx=%.1f m (radio rebaño=%.1f, engage=%.1f) -> cubren DENTRO, no barrera externa"
          % (idx.size, d_hc.max(), herd_r, c.engage_standoff))
    assert d_hc.max() <= herd_r + c.engage_standoff + 5.0, "FALLO: en penetrado sigue con barrera externa (no cubre a las vacas)"
    print("  OK\n")


def test_patrulla():
    print("=== 5) PATRULLA sin amenaza (solo-corzos): órbita alrededor del rebaño ===")
    w = World(seed=7, corzos_max=3, episode_kind="corzos"); w.reset()
    c = ReactiveCoordinator(w)
    for _ in range(300):
        w.step(c.act(w.get_observation()))
    ang1 = _ring_angles(w)
    for _ in range(30):
        w.step(c.act(w.get_observation()))
    ang2 = _ring_angles(w)
    idx = np.where(_free(w))[0]; herd = _herd(w); hc = herd.mean(0)
    rad = np.linalg.norm(w.drones[idx] - hc, axis=1)
    rot = float(np.abs(((ang2 - ang1 + 180) % 360) - 180).mean())
    print("  fase=%s | %d drones | radio medio=%.0f m (cv=%.2f, anillo) | giro medio en 30 pasos=%.1f° (orbita)"
          % (w.phase, idx.size, rad.mean(), rad.std() / max(rad.mean(), 1e-9), rot))
    assert w.phase in ("VIGILANCIA", "SOSPECHA"), "en solo-corzos no debe haber ESCOLTA"
    assert rad.std() / max(rad.mean(), 1e-9) < 0.35, "no es un anillo (radios dispares)"
    assert rot > 1.0, "la patrulla no orbita (no rota)"
    print("  OK\n")


def _ring_angles(w) -> np.ndarray:
    idx = np.where(_free(w))[0]; herd = _herd(w); hc = herd.mean(0)
    d = w.drones[idx] - hc
    return np.degrees(np.arctan2(d[:, 1], d[:, 0]))


def test_severidad_muestra():
    print("=== 6) SEVERIDAD (muestra n=15): Reactive vs Dummy (mismas semillas/CONFIG_V2) ===")
    from baseline import build_world, run_episode_metrics
    def sev(kind, n, factory):
        d = [run_episode_metrics(build_world(s, kind), factory(build_world(s, kind)))["n_depredadas"] for s in range(n)]
        return float(np.mean(d)), int(np.max(d))
    for kind in ("lobos", "mixto"):
        md, _ = sev(kind, 15, lambda w: DummyCoordinator(w.n_drones))
        mr, xr = sev(kind, 15, lambda w: ReactiveCoordinator(w))
        print("  %-6s  Dummy=%.2f  Reactive=%.2f (máx %d)  -> %+.2f" % (kind, md, mr, xr, mr - md))
        assert mr <= md + 1e-9, "FALLO: Reactive EMPEORA la severidad en %s (muestra)" % kind
    mc, _ = sev("corzos", 3, lambda w: ReactiveCoordinator(w))
    print("  corzos  Reactive=%.2f (esperado 0: sin amenaza)" % mc)
    assert mc == 0.0, "FALLO: solo-corzos debería ser 0"
    print("  OK\n")


def test_reproducible():
    print("=== 7) Reproducibilidad (misma seed -> mismo resultado con Reactive) ===")
    def fp(seed):
        w = World(seed=seed, corzos_max=3, episode_kind="mixto"); w.reset()
        c = ReactiveCoordinator(w)
        while True:
            _, _, term, trunc, info = w.step(c.act(w.get_observation()))
            if term or trunc:
                break
        return (info["status"], int(w.n_depredadas), tuple(w.cow_safe.tolist()), np.round(w.drones, 3).tobytes())
    a, b = fp(5), fp(5)
    print("  fingerprint idéntico:", a == b, "| status=%s n_depredadas=%d" % (a[0], a[1]))
    assert a == b, "FALLO: no reproducible"
    print("  OK\n")


def test_no_regresiones():
    print("=== 8) Sin regresiones (world.py intacto): face_check + battery_check ===")
    for script in ("face_check.py", "battery_check.py"):
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        ok = r.returncode == 0
        print("  %-16s -> %s" % (script, "VERDE" if ok else "ROJO (exit %d)" % r.returncode))
        assert ok, "FALLO: %s no pasó\n%s" % (script, (r.stdout + r.stderr)[-800:])
    print("  OK\n")


# ---------------------------------------------------------------------------- #
def _collect(kind, seed, maxsteps, tail=50, max_frames=800):
    """Corre un episodio con Reactive y devuelve (world, ventana de snapshots a ritmo natural)."""
    w = World(seed=seed, corzos_max=3, episode_kind=kind); w.reset()
    c = ReactiveCoordinator(w)
    hist = [w.snapshot()]
    for _ in range(maxsteps):
        _, _, term, trunc, _ = w.step(c.act(w.get_observation()))
        hist.append(w.snapshot())
        if term or trunc:
            break

    def key(s):
        return (s["phase"], s["n_depredadas"], s["n_safe"], int(np.sum(s.get("corzo_dismissed", []))))
    last = max((k for k in range(1, len(hist)) if key(hist[k]) != key(hist[k - 1])), default=0)
    end = min(len(hist), last + tail + 1)
    window = hist[:end]
    stride = max(1, len(window) // max_frames)
    return w, window[::stride]


def save_renders():
    print("=== Ojeo: BARRERA en acción (solo-lobos) y PATRULLA (solo-corzos) ===")
    # (1) Barrera: busca una seed solo-lobos DEMOSTRATIVA -> ESCOLTA + el episodio RESUELVE (no 'running')
    #     con la barrera visible y algún rescate (a salvo >= 2) para verla frenar a los lobos.
    CAP = 3000
    best = None
    for s in range(30):
        w = World(seed=s, corzos_max=3, episode_kind="lobos"); w.reset()
        c = ReactiveCoordinator(w); esc = None; done = False
        for t in range(CAP):
            _, _, term, trunc, _ = w.step(c.act(w.get_observation()))
            if esc is None and w.phase == "ESCOLTA":
                esc = t
            if term or trunc:
                done = True; break
        saved = int(w.cow_safe.sum() + w.calf_safe.sum())
        if esc is not None and done and saved >= 2:
            score = (t, w.n_depredadas)              # el más corto y con menos muertes = demostrativo y ágil
            if best is None or score < best[1]:
                best = (s, score, esc)
    seed_b = best[0] if best else 1
    w, play = _collect("lobos", seed_b, CAP)
    render_episode(w, play, save_path="reactive_barrera.gif")
    print("  reactive_barrera.gif: seed=%d, %d frames | status=%s cazadas=%d a salvo=%d (barrera de drones)"
          % (seed_b, len(play), w.status, w.n_depredadas, int(w.cow_safe.sum() + w.calf_safe.sum())))

    # (2) Patrulla: solo-corzos, drones orbitando mientras un dron investiga y descarta.
    w, play = _collect("corzos", 7, 1600)
    render_episode(w, play, save_path="reactive_patrulla.gif")
    print("  reactive_patrulla.gif: %d frames | fase=%s corzos descartados=%d/%d (patrulla en órbita)"
          % (len(play), w.phase, int(w.corzo_dismissed.sum()), w.n_corzos))


if __name__ == "__main__":
    test_barrera()
    test_reactivo()
    test_sin_presa_fijada()
    test_penetrado()
    test_patrulla()
    test_severidad_muestra()
    test_reproducible()
    test_no_regresiones()
    save_renders()
    print("reactive_check: TODO OK.")
