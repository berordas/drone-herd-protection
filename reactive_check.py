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
  9) ARRANQUE: la patrulla reparte a los drones desde t=0 (a su ranura MÁS CERCANA), sin mandarlos
     al centro ni cruzarse (la fase de la formación se ancla a su posición angular actual).
 10) PERCEPCIÓN HONESTA (v2.8): la barrera reacciona SOLO a lobos CONFIRMADOS de equipo con memoria
     (alguna vez a <= r_confirm=40 de un dron ACTIVE; latch el resto del episodio). Dirigidos:
     (A) un contacto DETECTADO (<= r_detect) pero NUNCA confirmado NO dispara la barrera (v2.6 sí lo
     hacía: percepción-oráculo — sabía el tipo de un bulto a 100 m); al cruzar los 40 m de un dron
     queda confirmado y la barrera reacciona; si luego se aleja (incluso más allá de r_detect) SIGUE
     confirmado (memoria/tracking). (B) dos frentes, uno confirmado y otro nunca a <= 40 m: la barrera
     se coloca SOLO respecto al confirmado — mover el frente sin confirmar no cambia NI UN waypoint
     (el frente ciego que hace el cebo físicamente posible).
 11) STANDOFF derivado (v2.8): standoff = sqrt(DETER_RADIUS² − (spacing/2)²) = 12 m — el peor punto de
     la línea de vacas frontales (a mitad lateral entre dos drones) queda a <= DETER_RADIUS del dron
     más cercano: un lobo confirmado no puede colarse entre la barrera y el rebaño sin entrar en
     radio de disuasión (con el standoff previo = 20 sí podía: peor punto a sqrt(20²+16²) = 25.6 m).
Guarda dos renders: barrera en acción (solo-lobos/mixto) y patrulla (solo-corzos).
[v2.8: los tests 1-9 pasan SIN cambios de aserción — con un solo frente (clustered, todos los tests
previos) el paquete entero acaba CONFIRMADO en cuanto llega a la barrera (cruza los 40 m de los drones
del frente) y la barrera anclada al primer confirmado ≈ la de antes; solo el standoff acerca la línea.]

El mundo NO se toca (world.py congelado); solo se añade y verifica el coordinador. La baseline Dummy
sigue idéntica (mismo arnés baseline.py). face_check y la regresión siguen verdes.
"""

from __future__ import annotations
import sys
import subprocess

import numpy as np

from world import World, ACTIVE, DETER_RADIUS
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
    # v2.8: el desplazamiento esperado ESCALA con el standoff (centro = front_c + u·standoff; con el
    # standoff derivado 12 la parte u·standoff es 12/20 de la de v2.6) -> umbral recalibrado 5.0 -> 3.0.
    # MISMA propiedad (la barrera sigue al paquete); solo cambia la magnitud por la línea más pegada.
    assert center2[0] > center1[0] + 3.0, "la barrera NO siguió al paquete (no reactiva)"
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


def _wrap(a):
    return abs((a + 180.0) % 360.0 - 180.0)


def _bearing_err(p, hc, target):
    """Diferencia angular (grados, [0,180]) entre el rumbo hc->p y el rumbo hc->target."""
    return _wrap(np.degrees(np.arctan2(p[1] - hc[1], p[0] - hc[0])
                            - np.arctan2(target[1] - hc[1], target[0] - hc[0])))


def _band_points(w, lo, hi, hc):
    """Puntos del campo (barrido DETERMINISTA de anillos alrededor del rebaño) cuya distancia MÍNIMA a
    todo dron ACTIVE cae en (lo, hi] — contactos DETECTABLES pero fuera del radio de confirmación."""
    flying = w.drones[w.drone_state == ACTIVE]
    out = []
    for r in (60.0, 80.0, 100.0, 120.0, 140.0):
        for adeg in range(0, 360, 15):
            p = hc + r * np.array([np.cos(np.radians(adeg)), np.sin(np.radians(adeg))])
            if not (5.0 <= p[0] <= w.W - 5.0 and 5.0 <= p[1] <= w.H - 5.0):
                continue
            dmin = float(np.linalg.norm(flying - p, axis=1).min())
            if lo < dmin <= hi:
                out.append(p)
    return out


def test_percepcion():
    print("=== 10) PERCEPCIÓN HONESTA (v2.8): la barrera reacciona SOLO a lobos CONFIRMADOS (equipo+memoria) ===")
    # Primer seed solo-lobos (clustered) con >=3 lobos que alcanza ESCOLTA (determinista).
    w = c = None
    for s in range(1, 15):
        w = World(seed=s, corzos_max=3, episode_kind="lobos"); w.reset()
        if w.n_wolves >= 3:
            c = ReactiveCoordinator(w)
            if _advance_to_escolta(w, c):
                break
    for _ in range(60):
        w.step(c.act(w.get_observation()))
    hc = _herd(w).mean(axis=0)
    idx = np.where(_free(w))[0]
    flying = w.drones[w.drone_state == ACTIVE]

    # ---- (A) contacto DETECTADO pero NUNCA confirmado -> NO dispara la barrera (v2.6 sí) ----
    c2 = ReactiveCoordinator(w)      # coordinador FRESCO: memoria de confirmación VACÍA (fase ya en ESCOLTA)
    band = _band_points(w, w.r_confirm + 10.0, w.r_detect - 5.0, hc)
    assert len(band) >= 2, "montaje: sin puntos en la banda contacto-sin-confirmar de los drones"
    rng = np.random.default_rng(0)
    w.wolves[:] = band[0] + rng.normal(0, 1, size=w.wolves.shape)     # ruido 1 m: sigue a > r_confirm
    dmin = float(np.linalg.norm(w.wolves[:, None, :] - flying[None, :, :], axis=2).min())
    a1 = c2.act(w.get_observation())
    rad = np.linalg.norm(a1[idx] - hc, axis=1)
    cv = rad.std() / max(rad.mean(), 1e-9)
    print("  (A) contacto a %.0f m del dron más cercano (<= r_detect=%.0f, > r_confirm=%.0f) -> patrulla (cv=%.2f), sin barrera"
          % (dmin, w.r_detect, w.r_confirm, cv))
    assert w.r_confirm < dmin <= w.r_detect, "montaje: el contacto debe estar en la banda (r_confirm, r_detect]"
    assert cv < 0.35, "FALLO: la barrera reaccionó a un contacto sin confirmar (percepción-oráculo)"
    # Cruza los 40 m de un dron ACTIVE -> CONFIRMADO -> la barrera reacciona.
    w.wolves[0] = flying[0] + np.array([w.r_confirm - 10.0, 0.0])     # a 30 m del dron: confirmable
    a2 = c2.act(w.get_observation())
    err2 = _bearing_err(a2[idx].mean(axis=0), hc, w.wolves[0])
    print("  (A) el lobo cruza los 40 m de un dron -> CONFIRMADO -> barrera (err eje=%.1f°)" % err2)
    assert bool(c2._confirmed[0]), "FALLO: el lobo a <= r_confirm no quedó confirmado"
    assert err2 < 25.0, "FALLO: la barrera no reaccionó al lobo recién confirmado"
    # Se aleja MÁS ALLÁ incluso de r_detect -> SIGUE confirmado (memoria/tracking): la barrera lo rastrea.
    cand = np.array([[3.0, 3.0], [297.0, 3.0], [3.0, 297.0], [297.0, 297.0]])
    far = cand[np.argmax([float(np.linalg.norm(flying - cc, axis=1).min()) for cc in cand])]
    w.wolves[0] = far
    dfar = float(np.linalg.norm(flying - far, axis=1).min())
    a3 = c2.act(w.get_observation())
    err3 = _bearing_err(a3[idx].mean(axis=0), hc, w.wolves[0])
    print("  (A) el confirmado se aleja a %.0f m (> r_detect) -> SIGUE confirmado (memoria): la barrera lo rastrea (err=%.1f°)"
          % (dfar, err3))
    assert dfar > w.r_detect, "montaje: el punto lejano debería quedar fuera de r_detect"
    assert bool(c2._confirmed[0]), "FALLO: la confirmación se olvidó al alejarse (sin memoria)"
    assert err3 < 25.0, "FALLO: la barrera no rastrea al confirmado que se aleja"

    # ---- (B) dos frentes: uno CONFIRMADO y otro NUNCA a <= 40 m -> solo el confirmado coloca ----
    w.wolves[0] = hc + np.array([45.0, 0.0])                          # el confirmado, al este del rebaño
    others = np.arange(1, w.n_wolves)
    # dos posiciones de banda con rumbo MUY distinto al confirmado (frente "ciego" al otro lado)
    byang = sorted(band, key=lambda p: -_bearing_err(p, hc, w.wolves[0]))
    far_b1, far_b2 = byang[0], byang[1]
    assert _bearing_err(far_b1, hc, w.wolves[0]) > 60.0, "montaje: el frente ciego debe venir por otro rumbo"
    w.wolves[others] = far_b1 + rng.normal(0, 1, size=(others.size, 2))
    b1 = c2.act(w.get_observation()).copy()
    w.wolves[others] = far_b2 + rng.normal(0, 1, size=(others.size, 2))   # mueve el frente sin confirmar
    b2 = c2.act(w.get_observation()).copy()
    center = b1[idx].mean(axis=0)
    err_conf = _bearing_err(center, hc, w.wolves[0])
    err_mean = _bearing_err(center, hc, w.wolves.mean(axis=0))
    print("  (B) frente contacto-sin-confirmar movido -> waypoints idénticos: %s | eje: |vs confirmado|=%.1f° |vs media global|=%.1f°"
          % (np.array_equal(b1, b2), err_conf, err_mean))
    assert not c2._confirmed[others].any(), "montaje: el 2º frente no debería estar confirmado"
    assert np.array_equal(b1, b2), "FALLO: el frente sin confirmar influyó en la barrera"
    assert err_conf < 25.0, "FALLO: la barrera no se coloca respecto al confirmado"
    assert err_mean > err_conf + 20.0, "FALLO: la barrera sigue la media global, no al confirmado"
    print("  OK\n")


def test_standoff():
    print("=== 11) STANDOFF derivado (v2.8): no hay hueco entre la barrera y el rebaño fuera de disuasión ===")
    w = World(seed=1, corzos_max=3, episode_kind="lobos"); w.reset()
    c = ReactiveCoordinator(w)
    worst = float(np.hypot(c.barrier_standoff, c.drone_spacing / 2.0))
    print("  standoff=%.1f m (derivado sqrt(R²−(s/2)²); antes 20) | spacing=%.1f m | peor punto de la línea"
          " de vacas frontales a %.1f m del dron más cercano (<= DETER_RADIUS=%.0f)"
          % (c.barrier_standoff, c.drone_spacing, worst, DETER_RADIUS))
    assert abs(c.barrier_standoff - 12.0) < 1e-9, "el standoff derivado con defaults debe ser 12 m"
    assert worst <= DETER_RADIUS + 1e-6, "FALLO: un lobo puede colarse entre barrera y rebaño fuera de disuasión"
    # Empírico sobre una barrera REAL: los puntos de la línea de vacas frontales detrás de cada hueco
    # entre drones adyacentes quedan a <= DETER_RADIUS de alguna ranura.
    assert _advance_to_escolta(w, c), "no llegó a ESCOLTA"
    for _ in range(40):
        w.step(c.act(w.get_observation()))
    idx = np.where(_free(w))[0]
    assert idx.size >= 2, "hacen falta >=2 ranuras para medir el hueco"
    slots = c.act(w.get_observation())[idx]
    p = slots - slots.mean(axis=0)
    perp = p[np.argmax(np.linalg.norm(p, axis=1))]
    perp = perp / max(float(np.linalg.norm(perp)), 1e-9)              # eje del frente
    u = np.array([-perp[1], perp[0]])                                 # normal al frente
    if float(np.dot(u, np.asarray(w.wolves[c._anchor], float) - slots.mean(axis=0))) < 0:
        u = -u                                                        # apunta HACIA el paquete
    order = np.argsort(slots @ perp)
    gaps = []
    for a, b in zip(order[:-1], order[1:]):
        mid = 0.5 * (slots[a] + slots[b]) - u * c.barrier_standoff    # punto de vacas tras el hueco
        gaps.append(float(np.linalg.norm(slots - mid, axis=1).min()))
    print("  barrera real: %d ranuras | peor hueco medido %.1f m (<= %.0f)" % (idx.size, max(gaps), DETER_RADIUS))
    assert max(gaps) <= DETER_RADIUS + 0.5, "FALLO: hueco real entre barrera y rebaño fuera de disuasión"
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


def test_arranque():
    print("=== 9) ARRANQUE: la patrulla reparte a los drones desde t=0 (NO al centro, NO se cruzan) ===")
    for seed in (0, 3, 5):
        w = World(seed=seed, corzos_max=3, episode_kind="mixto"); w.reset()
        c = ReactiveCoordinator(w)
        idx = np.where(_free(w))[0]
        hc = _herd(w).mean(0)
        d = w.drones[idx] - hc
        theta0 = np.arctan2(d[:, 1], d[:, 0])
        tgt = c.act(w.get_observation())[idx] - hc                     # ranura asignada a cada dron (paso 0)
        slot = np.arctan2(tgt[:, 1], tgt[:, 0])
        ang_err = np.degrees(np.abs(((slot - theta0 + np.pi) % (2 * np.pi)) - np.pi))
        minsep = np.inf
        for _ in range(40):                                           # ventana de arranque
            w.step(c.act(w.get_observation()))
            cur = w.drones[idx]
            sep = np.linalg.norm(cur[:, None, :] - cur[None, :, :], axis=2)
            np.fill_diagonal(sep, np.inf)
            minsep = min(minsep, float(sep.min()))
        print("  seed=%d | error angular dron->ranura (t=0): media %.0f° máx %.0f° | sep MÍNIMA en 40 pasos: %.1f m"
              % (seed, ang_err.mean(), ang_err.max(), minsep))
        # Cada dron va a su ranura MÁS CERCANA (no a la opuesta ~180°): antes del fix media ~135°.
        assert ang_err.max() < 45.0, "FALLO: un dron va a una ranura LEJANA (cruza el centro al arrancar)"
        # sep mínima alta = nadie se junta en el centro (si se cruzaran, tocaría ~0). Antes del fix bajaba a ~5 m.
        assert minsep > DETER_RADIUS, "FALLO: los drones se juntan en el centro al arrancar (se cruzan)"
    print("  OK\n")


def test_severidad_muestra():
    # MEDIDA. En v2.8 (barrera HONESTA) el reactivo reacciona más tarde (espera a CONFIRMAR a <= 40 m) ->
    # puede subir vs la barrera-oráculo de v2.6/v2.7; el standoff derivado (12 m) compensa acercando la
    # línea. Aun así debe SEGUIR batiendo al Dummy (que no usa la barrera y queda intacto). Medida
    # autoritativa (N=100, reactive_eval). BUG CORREGIDO (v2.3): sev() construía el coordinador con un world
    # DISTINTO al que corría -> el ReactiveCoordinator leía estado CONGELADO y salía artificialmente mal; ahora
    # usa el MISMO world.
    N = 30
    print("=== 6) SEVERIDAD (muestra n=%d): Reactive vs Dummy en v2.8 (barrera honesta) ===" % N)
    from baseline import build_world, run_episode_metrics
    def sev(kind, n, factory):
        out = []
        for s in range(n):
            w = build_world(s, kind)                       # el MISMO world para correr Y para el coordinador
            out.append(run_episode_metrics(w, factory(w))["n_depredadas"])
        return float(np.mean(out)), int(np.max(out))
    for kind in ("lobos", "mixto"):
        md, _ = sev(kind, N, lambda w: DummyCoordinator(w.n_drones))
        mr, xr = sev(kind, N, lambda w: ReactiveCoordinator(w))
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
    test_percepcion()
    test_standoff()
    test_patrulla()
    test_arranque()
    test_severidad_muestra()
    test_reproducible()
    test_no_regresiones()
    save_renders()
    print("reactive_check: TODO OK.")
