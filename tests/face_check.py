"""
face_check.py — Verificación del modelo "DAR LA CARA" + presa común + TERNEROS/defensoras.

  1) LOBO SOLO vs ADULTA (sin terneros) -> no puede tumbarla (regla de nº mínimo).
  2) MANADA vs ADULTA (escenario) -> flanquean -> muere; confirma instrumentación de #3.
  3) MOVIMIENTO FIRME -> tembleque bajo (vacas, lobos y terneros).
  4) RETOQUE -> sin terneros, la presa adulta es del BORDE (lejos del centroide del rebaño).
  5) TERNEROS -> la manada va al ternero (muere con 1 flanqueador); lobo solo vs ternero disputado
     (se reporta, NO se tunea); con 2 terneros la manada se compromete con UNO.
  6) COORDINACIÓN (sin terneros) -> confluyen en UNA presa, re-fijaciones ~0.
  7) TASA sin drones range(100) (terneros por defecto) + split ternero/adulta + toques.
  8) REPRODUCIBILIDAD (incluido nº de terneros y defensoras).
"""
import sys as _sys, pathlib as _pl  # layout: raíz (rl/, hrl/) y sim/ (núcleo) importables sin instalar el paquete
_ROOT = _pl.Path(__file__).resolve().parents[1]; _sys.path[:0] = [str(_ROOT), str(_ROOT / "sim")]

import numpy as np
from world import World
from coordinators import DummyCoordinator

NO_CALVES = (1.0, 0.0, 0.0)     # forzar 0 terneros
ONE_CALF = (0.0, 1.0, 0.0)      # forzar 1 ternero
TWO_CALVES = (0.0, 0.0, 1.0)    # forzar 2 terneros


def run_ep(seed, record=False, **kw):
    """Un episodio con drones quietos. Devuelve (world, outcome, pasos_ataque, pasos_lobo,
    (cow_vels, wolf_vels, calf_vels)) — velocidades por paso solo si record=True.

    Cap de pasos corto por defecto: estos tests verifican la DINÁMICA (cono/flanqueo/firmeza), no el
    timeout largo de la escolta. La depredación ya NO termina el episodio (multi-muerte): las muertes
    se detectan por w.captures / w.capture_info, no por 'terminated'.

    Campo CALIBRADO 100x100: el modelo de COMBATE es invariante de escala (radios biológicos absolutos),
    así que se prueba en el campo donde se calibró —donde el cap de 600 basta para que el lobo
    enganche—. El campo de PRODUCCIÓN (300x300, default del World) se verifica aparte: la FIJACIÓN de la
    escala biológica en los tests 9/10 (a 300) y el timing de detección + tasa de episodio completo en
    escort_check. (A 300 con cap 600 la tasa cae por artefacto: el lobo aún se acerca; episodio completo ~87%.)"""
    kw.setdefault("parcel_size", (100.0, 100.0))
    kw.setdefault("max_episode_steps", 600)
    kw.setdefault("escort_enabled", False)   # COMBATE puro: sin escolta -> la fase no dispara y el guiado al refugio NO se filtra (las vacas pastan)
    w = World(seed=seed, **kw)
    c = DummyCoordinator(w.n_drones)
    attack_steps = wolf_steps = 0
    cow_v, wolf_v, calf_v = [], [], []
    while True:
        _, _, term, trunc, info = w.step(c.act(None))
        if w.n_wolves > 0:
            wolf_steps += 1
            attack_steps += int(w._wolf_attacking)
        if record:
            cow_v.append(w.cow_vel.copy())
            wolf_v.append(w.wolf_vel.copy())
            if w.n_calves > 0:
                calf_v.append(w.calf_vel.copy())
        if term or trunc:
            break
    return w, info["status"], attack_steps, wolf_steps, (cow_v, wolf_v, calf_v)


def _mean_turn(vels):
    """Giro medio / p95 por paso (rad) de una secuencia de velocidades (T, N, 2). Bajo = firme."""
    V = np.array(vels)
    sp = np.linalg.norm(V, axis=2)
    moving = (sp[:-1] > 1e-3) & (sp[1:] > 1e-3)
    cos = np.clip(np.sum(V[:-1] * V[1:], axis=2) / np.maximum(sp[:-1] * sp[1:], 1e-9), -1.0, 1.0)
    ang = np.arccos(cos)
    if not moving.any():
        return 0.0, 0.0
    return float(ang[moving].mean()), float(np.percentile(ang[moving], 95))


# ---------------------------------------------------------------------------- #
def test_lone_wolf_no_kill():
    print("=== 1) Lobo SOLO vs ADULTA (sin terneros): no puede tumbarla ===")
    preds = 0
    for s in range(30):
        w, status, *_ = run_ep(s, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES, teleport_guard=True)
        preds += int(status == "predation")
    print("  depredaciones con 1 lobo (30 seeds): %d  (esperado 0)" % preds)
    assert preds == 0, "FALLO: un lobo solo tumbó a una adulta"
    print("  OK\n")


def test_pack_flank_kill():
    print("=== 2) MANADA vs ADULTA (escenario): flanquean -> muere; #3 quórum->muerte ===")
    w = World(seed=1, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, teleport_guard=True,
              escort_enabled=False)
    c = DummyCoordinator(w.n_drones)
    w.cow_speeds[:] = w.cow_speed
    w.cow_speeds[0] = 0.5 * w.cow_speed
    w.cows[0] = np.array([75.0, 50.0])   # aislada y EXPUESTA, pero fuera del establo (no refugiada)
    w.cows[1:] = np.array([15.0, 85.0]) + w.rng.uniform(-2, 2, size=(w.n_cows - 1, 2))
    w.cow_heading[0] = 0.0
    w.cow_vel[:] = 0.0
    w.wolves[:] = np.array([[85.0, 50.0], [75.0, 40.0], [65.0, 50.0]])
    w.wolf_vel[:] = 0.0
    w._commit_initial_prey()   # presa fijada en t=0: re-fijar tras recolocar el escenario (la presa
    assert w.pack_prey == 0    # más expuesta es la cow[0] aislada)
    killed = None
    for _ in range(400):
        w.step(c.act(None))
        if w.capture_info is not None:   # primera captura (la muerte ya NO termina el episodio)
            killed = w.capture_info["step"]
            break
    assert killed is not None, "FALLO: la manada no tumbó a la adulta en el escenario construido"
    ci, q = w.capture_info, w.flank_first_quorum
    print("  MUERTE paso %d: adulta=%d (presa fijada=%s) con %d flanqueadores (>= %d)"
          % (killed, ci["prey_idx"], ci["is_pack_prey"], ci["n_flankers"], w.n_min_adult))
    print("  #3: primer quórum paso %s -> muerte=%s" % (q["step"] if q else None, q["killed"] if q else None))
    assert ci["is_pack_prey"] and ci["n_flankers"] >= w.n_min_adult
    assert q is not None and q["killed"], "FALLO(#3): quórum sin muerte"
    print("  OK\n")


def test_firm_motion():
    print("=== 3) Movimiento firme (giro por paso, rad) ===")
    _w, _s, _a, _ws, (gcow_v, _wv, _cv) = run_ep(2, record=True, wolves_min=0, wolves_max=0, calf_count_probs=NO_CALVES)
    gm, _ = _mean_turn(gcow_v)
    calm_disp = float(np.linalg.norm(np.array(gcow_v), axis=2).mean()) * _w.dt   # desplazamiento medio/paso (m)
    print("  vacas pastando (sin lobo): giro medio=%.3f | desplazamiento/paso=%.3f m "
          "(a tope sería %.3f m -> más quietas)" % (gm, calm_disp, _w.cow_speed * _w.dt))
    assert calm_disp < 0.5 * _w.cow_speed * _w.dt, "FALLO: las vacas pastan demasiado rápido (poco quietas)"
    _w, _s, _a, _ws, (cow_v, wolf_v, calf_v) = run_ep(2, record=True, wolves_min=3, wolves_max=3, calf_count_probs=TWO_CALVES)
    cm, _ = _mean_turn(cow_v)
    wm, _ = _mean_turn(wolf_v)
    km, _ = _mean_turn(calf_v) if calf_v else (0.0, 0.0)
    print("  con manada+terneros: vacas=%.3f lobos=%.3f terneros=%.3f  (vibración daría ~pi/2)" % (cm, wm, km))
    assert gm < 0.35 and wm < 0.5 and km < 0.5, "FALLO: movimiento con tembleque"
    print("  OK\n")


def test_retoque_exposure():
    print("=== 4) Retoque: la presa ADULTA es del BORDE (lejos del centroide), no céntrica ===")
    dps, dms = [], []
    for s in range(30):
        w = World(seed=s, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES, escort_enabled=False)
        c = DummyCoordinator(w.n_drones)
        rec = None
        while True:
            _, _, term, trunc, _ = w.step(c.act(None))
            if w.pack_prey >= 0 and w.pack_prey_kind == "adult":
                centroid = w.cows.mean(axis=0)
                rec = (float(np.linalg.norm(w.cows[w.pack_prey] - centroid)),
                       float(np.linalg.norm(w.cows - centroid, axis=1).mean()))
                break    # solo necesitamos la exposición al FIJAR (paso ~0); no agotamos el episodio
            if term or trunc:
                break
        if rec:
            dps.append(rec[0]); dms.append(rec[1])
    print("  al FIJAR la presa: dist presa->centroide=%.1f m  vs media del rebaño=%.1f m (n=%d)"
          % (np.mean(dps), np.mean(dms), len(dps)))
    assert np.mean(dps) > np.mean(dms), "FALLO: la presa no es la más expuesta (debería estar más lejos que la media)"
    print("  OK\n")


def test_calves():
    print("=== 5) Terneros: la manada va al ternero (muere con 1 flanqueador) ===")
    # #1: el ternero se coloca AL LADO de la defensora (no encima): distancia media ternero-defensora.
    w = World(seed=3, wolves_min=0, wolves_max=0, calf_count_probs=ONE_CALF)
    cc = DummyCoordinator(w.n_drones)
    dists = []
    for _ in range(200):
        _, _, term, trunc, _ = w.step(cc.act(None))
        dists.append(float(np.linalg.norm(w.calves[0] - w.cows[w.calf_defender[0]])))
        if term or trunc:
            break
    print("  dist media ternero<->defensora=%.2f m (espacio personal=%.2f m; al lado, no encima)"
          % (np.mean(dists), w.calf_personal_space))
    assert 0.3 * w.calf_personal_space < np.mean(dists) < 3.0 * w.calf_personal_space, \
        "FALLO: el ternero no se coloca al lado de la defensora"
    calf_deaths = 0
    for s in range(40):
        w, status, *_ = run_ep(s, wolves_min=3, wolves_max=3, calf_count_probs=ONE_CALF)
        calf_deaths += int(any(c["kind"] == "calf" for c in w.captures))   # ¿murió EL ternero alguna vez?
    print("  ternero + manada (1 ternero, 3 lobos, 40 seeds): %d muertes de ternero" % calf_deaths)
    assert calf_deaths > 20, "FALLO: la manada no caza al ternero de forma fiable"
    # Lobo solo vs ternero: DISPUTADO (reportar, NO tunear).
    lone = 0
    for s in range(50):
        w, *_ = run_ep(s, wolves_min=1, wolves_max=1, calf_count_probs=ONE_CALF)
        lone += int(any(c["kind"] == "calf" for c in w.captures))
    print("  lobo SOLO vs ternero (50 seeds): %d%% muertes de ternero  (disputado; NO se tunea aquí)" % (100 * lone // 50))
    # 2 terneros: la manada se compromete con UNO (re-fijaciones bajas).
    refix = [run_ep(s, wolves_min=4, wolves_max=4, calf_count_probs=TWO_CALVES)[0].n_refix for s in range(10)]
    print("  2 terneros: re-fijaciones media=%.1f máx=%d  (commitment con uno)" % (np.mean(refix), max(refix)))
    print("  OK\n")


def test_coordination():
    print("=== 6) Coordinación sin terneros: confluyen en UNA presa (commitment) ===")
    # #2: la presa se fija en t=0 (antes de cualquier paso) -> la manada va a por ella desde el inicio.
    w0 = World(seed=0, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES)
    assert w0.step_count == 0 and w0.pack_prey >= 0, "FALLO: la presa no se fija en t=0"
    print("  presa fijada en t=0: pack_prey=%d kind=%s (paso=%d, esperado 0)"
          % (w0.pack_prey, w0.pack_prey_kind, w0.step_count))
    wl = World(seed=0, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    assert wl.pack_prey < 0, "FALLO: lobo solo sin ternero no debe comprometerse en t=0"
    print("  lobo solo sin ternero en t=0: pack_prey=%d (sin presa = standoff amplio)" % wl.pack_prey)
    means, refixes = [], []
    for s in range(20):
        w, *_ = run_ep(s, wolves_min=3, wolves_max=3, calf_count_probs=NO_CALVES)
        if w._simul_steps:
            means.append(w._simul_sum / w._simul_steps)
            refixes.append(w.n_refix)
    print("  vacas atacadas a la vez: media=%.2f  | re-fijaciones: media=%.2f máx=%d"
          % (np.mean(means), np.mean(refixes), max(refixes)))
    assert np.mean(means) < 1.4, "FALLO: la manada no confluye"
    print("  OK\n")


def test_rate():
    print("=== 7) Tasa sin drones range(100) (terneros por defecto 1/3 c/u) ===")
    from collections import Counter
    out, kind = Counter(), Counter()
    for s in range(100):
        w, status, *_ = run_ep(s)               # cap 600 pasos; depredación = episodio con >=1 res cazada
        out[status] += 1
        for c in w.captures:                    # MATANZA EXCEDENTE (multi-muerte): cuenta TODAS las capturas
            kind[c["kind"]] += 1
    print("  outcomes:", dict(out))
    print("  depredación (>=1 res cazada) = %d/100 episodios  (no es objetivo; se mide)" % out["predation"])
    print("  capturas totales: ternero=%d adulta=%d  (multi-muerte -> pueden ser > nº de depredaciones)"
          % (kind["calf"], kind["adult"]))


def test_grazing_spread():
    print("=== 9) Espaciado del rebaño al pastar (#1: más repartidas) ===")
    def settle(**kw):
        w = World(seed=2, wolves_min=0, wolves_max=0, calf_count_probs=NO_CALVES, **kw)
        c = DummyCoordinator(w.n_drones)
        for _ in range(150):
            w.step(c.act(None))
        D = np.linalg.norm(w.cows[:, None, :] - w.cows[None, :, :], axis=2)
        np.fill_diagonal(D, np.inf)
        return float(D.min(axis=1).mean()), w
    nn_old, _ = settle(cow_spread=20.0, r_separation=11.0)  # huella anterior (campo 300 apelotonado)
    nn, w = settle()                                        # huella nueva (defaults dispersos)
    print("  dist media al vecino más cercano=%.1f m (huella anterior %.1f m) | r_separation=%.1f m cow_spread=%.1f m"
          % (nn, nn_old, w.r_separation, w.cow_spread))
    assert nn > nn_old, "FALLO: el rebaño no quedó más repartido"
    assert nn > 15.0, "FALLO: el espaciado no subió a ~20 m con la huella nueva"
    print("  OK\n")


def test_wolf_spawn_sector():
    print("=== 10) Lobos salen JUNTOS de un sector (#2) ===")
    angles, disp = [], []
    for s in range(8):
        w = World(seed=s, wolves_min=4, wolves_max=4, calf_count_probs=NO_CALVES)
        angles.append(float(np.degrees(w.wolf_spawn_angle)))
        ctr = w.wolves.mean(axis=0)
        disp.append(float(np.linalg.norm(w.wolves - ctr, axis=1).mean()))
    wd = World(seed=0).wolf_spawn_dispersion
    print("  dispersión media del cúmulo=%.1f m (wolf_spawn_dispersion=%.1f m; pequeña = juntos)"
          % (np.mean(disp), wd))
    print("  sector por seed (grados):", [round(a) for a in angles], "-> varía entre episodios")
    assert np.mean(disp) < 0.25 * min(World(seed=0).W, World(seed=0).H), "FALLO: los lobos no salen agrupados"
    assert np.std(angles) > 5.0, "FALLO: el sector de spawn no varía entre episodios"
    print("  OK\n")


def test_skirt_around_herd():
    print("=== 11) El lobo RODEA el rebaño (no lo atraviesa) (#3, prueba clave) ===")
    def run_skirt(skirt_gain):
        w = World(seed=4, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES,
                  wolf_skirt_gain=skirt_gain, escort_enabled=False)
        c = DummyCoordinator(w.n_drones)
        w.cow_speeds[:] = 0.02 * w.cow_speed                          # rebaño casi congelado (aísla el camino del lobo)
        w.cows[0] = np.array([90.0, 25.0])                           # PRESA al otro lado del rebaño
        w.cows[1:] = np.column_stack([np.full(w.n_cows - 1, 50.0),
                                      np.linspace(19.0, 31.0, w.n_cows - 1)])  # MURO de vacas en medio
        w.cow_vel[:] = 0.0
        w.cow_heading[:] = np.pi                                      # de cara al lobo (viene por -x)
        w.wolves[0] = np.array([10.0, 25.0])                         # lobo al otro lado
        w.wolf_vel[:] = 0.0
        w.pack_prey, w.pack_prey_kind, w._ever_committed = 0, "adult", True
        min_d = np.inf
        for _ in range(300):
            w.step(c.act(None))
            if w.pack_prey != 0:                                     # re-fijar (no debe soltarla, pero por si acaso)
                w.pack_prey, w.pack_prey_kind = 0, "adult"
            min_d = min(min_d, float(np.linalg.norm(w.wolves[0] - w.cows[0])))
        return min_d, w.r_face_safe
    d_off, _ = run_skirt(0.0)        # SIN rodeo: beelinea y se atasca contra el muro
    d_on, rf = run_skirt(1.5)        # CON rodeo: bordea hasta el costado de la presa
    print("  dist MÍN lobo->presa con el rebaño en medio: SIN rodeo=%.1f m | CON rodeo=%.1f m" % (d_off, d_on))
    assert d_on < d_off, "FALLO: el rodeo no acerca el lobo a la presa"
    assert d_on < 2.0 * rf, "FALLO: el lobo no alcanza el costado de la presa (%.1f m)" % d_on
    print("  OK\n")


def test_reproducible():
    print("\n=== 12) Reproducibilidad (misma seed, incluido nº de terneros y defensoras) ===")
    w1, *_ = run_ep(7)
    w2, *_ = run_ep(7)
    same = (np.array_equal(w1.cows, w2.cows) and np.array_equal(w1.wolves, w2.wolves)
            and w1.n_calves == w2.n_calves and np.array_equal(w1.calf_defender, w2.calf_defender)
            and np.array_equal(w1.calves, w2.calves) and w1.status == w2.status)
    print("  estado final idéntico:", same, "| n_calves:", w1.n_calves)
    assert same, "FALLO: no reproducible"
    print("  OK")


if __name__ == "__main__":
    test_lone_wolf_no_kill()
    test_pack_flank_kill()
    test_firm_motion()
    test_retoque_exposure()
    test_calves()
    test_coordination()
    test_rate()
    test_grazing_spread()
    test_wolf_spawn_sector()
    test_skirt_around_herd()
    test_reproducible()
