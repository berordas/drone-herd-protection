"""
wolf_controller_check.py — Verificación del REFACTOR del controlador de lobos (scriptado | aprendido).

Refactor PURO: el comportamiento con el ScriptedWolfController es BIT A BIT idéntico a v2.4. Aquí se
comprueba:
  1) INTERFAZ: decide(world) -> (v_target (n_wolves,2), coasting bool); make_wolf_controller; inyección.
  2) FRONTERA POLÍTICA/FÍSICA: el controlador NO integra ni asusta (solo devuelve la intención); el mundo
     impone susto + inercia + integración. El controlador SÍ fija la presa común (estado del World).
  3) SUSTO INNEGOCIABLE: si un dron EMBISTE, el mundo IMPONE la huida SOBRE la intención del controlador
     (aunque la intención diga "sigue a la presa"); un lobo huyendo no mata.
  4) SPOT-CHECK vs baseline v2.4.1 CONGELADA (baseline_v2.json, METRO DGX: medida dentro del contenedor
     del proyecto — fuera puede salir rojo por deriva FP entre plataformas): mismas semillas ->
     severidades IDÉNTICAS (no se re-mide; solo se confirma que nada movió la baseline).

El fingerprint de equivalencia (SHA del estado en episodios completos, git stash HEAD vs refactor) es la
prueba REINA; esto son comprobaciones dirigidas complementarias. face_check/battery/escort/drone/reactive
siguen verdes SIN adaptar (el comportamiento no cambió).
"""

import json
import numpy as np

from world import World, ACTIVE, READY
from coordinators import DummyCoordinator
from wolf_controllers import (WolfController, ScriptedWolfController, make_wolf_controller,
                              ASSAULT_DARK_HOLD, ASSAULT_DARK_BAND, DECOY_SHOW_LEAD)

NO_CALVES = (1.0, 0.0, 0.0)


def test_interfaz():
    print("=== 1) INTERFAZ: decide -> (v_target, coasting) · make_wolf_controller · inyección ===")
    w = World(seed=0)
    assert isinstance(w.wolf_controller, ScriptedWolfController), "el default no es ScriptedWolfController"
    assert w.wolf_policy == "scripted"
    out = w.wolf_controller.decide(w)
    assert isinstance(out, tuple) and len(out) == 2, "decide debe devolver (v_target, coasting)"
    v_target, coasting = out
    assert v_target.shape == (w.n_wolves, 2), "v_target debe ser (n_wolves, 2)"
    assert isinstance(bool(coasting), bool)
    # La intención del scriptado va a rapidez de caza (~wolf_speed) o 0 (coast) -> nunca supera el cap.
    speeds = np.linalg.norm(v_target, axis=1)
    assert (speeds <= w.wolf_speed + 1e-9).all(), "la intención del scriptado supera el cap wolf_speed"
    # make_wolf_controller + inyección directa.
    assert isinstance(make_wolf_controller("scripted"), ScriptedWolfController)
    inj = ScriptedWolfController()
    w2 = World(seed=0, wolf_controller=inj)
    assert w2.wolf_controller is inj, "no se respetó la inyección de instancia"
    try:
        make_wolf_controller("learned"); raise AssertionError("learned debería lanzar NotImplementedError")
    except NotImplementedError:
        pass
    print("  decide OK | v_target (%d,2), |v|<=%.1f | make_wolf_controller('scripted') OK | inyección OK | 'learned' NotImplementedError" % (w.n_wolves, w.wolf_speed))
    print("  OK\n")


def test_frontera_politica_fisica():
    print("=== 2) FRONTERA: el controlador NO integra/asusta (solo intención); fija la presa común (estado del World) ===")
    # decide NO mueve a los lobos ni cambia su velocidad (eso es física del mundo): solo lee y devuelve intención.
    w = World(seed=3, corzos_max=3, episode_kind="lobos")
    for _ in range(20):                      # deja que la manada se comprometa
        w.step(DummyCoordinator(w.n_drones).act(None))
    wolves0 = w.wolves.copy(); vel0 = w.wolf_vel.copy()
    prey0 = w.pack_prey
    v_target, coasting = w.wolf_controller.decide(w)
    assert np.array_equal(w.wolves, wolves0), "FALLO: decide MOVIÓ a los lobos (debería ser física del mundo)"
    assert np.array_equal(w.wolf_vel, vel0), "FALLO: decide cambió la velocidad (integración = física del mundo)"
    # El controlador SÍ escribe la presa común (contrato compartido con la física de la vaca): fijada.
    assert w.pack_prey >= 0 and w.pack_prey == prey0, "FALLO: la presa común no está fijada (o cambió sin causa)"
    print("  decide no mueve/integra a los lobos (%d) | escribe la presa común (pack_prey=%d) leída por el pin de la vaca" % (w.n_wolves, w.pack_prey))
    print("  OK\n")


def _one_active_drone(w, pos, vel=(0.0, 0.0)):
    w.drone_state[:] = READY; w.drones[:] = np.array([1e4, 1e4]); w.drone_vel[:] = 0.0
    w.drone_state[0] = ACTIVE; w.drones[0] = np.asarray(pos, float); w.drone_vel[0] = np.asarray(vel, float)
    w.drone_waypoint[0] = w.drones[0].copy()


def test_susto_innegociable():
    print("=== 3) SUSTO INNEGOCIABLE: la embestida SOBRESCRIBE la intención del controlador (un lobo huyendo no mata) ===")
    c = DummyCoordinator(World(seed=0).n_drones)
    P = np.array([80.0, 80.0])
    w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    w.cows[0] = P.copy(); w.cow_vel[0] = 0.0; w.cow_speeds[0] = 0.0
    w.phase = "ESCOLTA"; w.pack_prey, w.pack_prey_kind = 0, "adult"
    w.wolves[0] = P + np.array([12.0, 0.0]); w.wolf_vel[0] = 0.0     # lobo al ESTE de la presa (la presa está al oeste)
    # (a) DIRECTO: la INTENCIÓN del controlador apunta HACIA la presa (al OESTE, -x); un dron EMBISTE desde el
    #     NORTE (velocidad hacia el sur) -> el mundo (_apply_deterrence) IMPONE la huida al SUR (-y), sobrescribiendo
    #     la intención de caza. Direcciones distintas -> se ve que el mundo MANDA sobre el controlador.
    _one_active_drone(w, P + np.array([12.0, 12.0]), vel=(0.0, -15.0))   # dron embistiendo desde el norte, dentro del radio
    v_int, coasting = w.wolf_controller.decide(w)                       # intención de caza (hacia la presa)
    to_prey = (P - w.wolves[0]); to_prey /= np.linalg.norm(to_prey)     # ~oeste
    assert not coasting and float(v_int[0] @ to_prey) > 0.5 * w.wolf_speed, "la intención no apunta a la presa"
    v_imposed = w._apply_deterrence(v_int.copy())                      # el MUNDO impone el susto sobre la intención
    assert w._wolf_scared[0], "FALLO: el mundo no marcó al lobo asustado (embestida dentro del radio)"
    assert not np.allclose(v_imposed[0], v_int[0]), "FALLO: el mundo NO sobrescribió la intención (susto negociable)"
    assert float(v_imposed[0, 1]) < -0.5, "FALLO: la huida no se aleja del dron (norte) -> el susto no se impuso"
    print("  intención=caza al OESTE (%s) | susto impuesto=huida al SUR (%s) | asustado=%s (el mundo MANDA sobre el controlador)"
          % (np.round(v_int[0], 2), np.round(v_imposed[0], 2), bool(w._wolf_scared[0])))
    # (b) INTEGRADO: con el dron atravesando por encima varias veces, el lobo queda asustado y NO mata.
    w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
    w.cows[0] = P.copy(); w.cow_vel[0] = 0.0; w.cow_speeds[0] = 0.0
    w.phase = "ESCOLTA"; w.pack_prey, w.pack_prey_kind = 0, "adult"
    w.wolves[0] = P + np.array([3.0, 0.0]); w.wolf_vel[0] = 0.0        # lobo PEGADO a la presa (mataría sin dron)
    _one_active_drone(w, P + np.array([3.0, 25.0]), vel=(0.0, -15.0))
    scared_any = False
    for _ in range(25):
        w.pack_prey, w.pack_prey_kind = 0, "adult"; w.cows[0] = P.copy(); w.cow_vel[0] = 0.0
        w.command_waypoint(0, P + np.array([3.0, -40.0]))            # el dron atraviesa de norte a sur sobre el lobo
        w.step(c.act(None))
        scared_any = scared_any or bool(w._wolf_scared.any())
    print("  integrado: dron atravesando -> asustado alguna vez=%s | cazada=%d (un lobo huyendo NO mata ni flanquea)"
          % (scared_any, w.n_depredadas))
    assert scared_any and w.n_depredadas == 0, "FALLO: la embestida no impuso la huida / hubo caza"
    print("  OK\n")


def test_presa_por_sector():
    """v2.9 (CEBO DISEÑADO, dirigido B): en episodios grouped de 2 subgrupos, el 2º sector fija la
    presa MÁS LIBRE (máx. distancia al dron ACTIVE más cercano; ternero-primero; excluye la presa
    del 1º si hay alternativa del mismo tipo; capacidad del sector para adultas) y el 1º mantiene
    la común de SIEMPRE. Con 1 solo grupo, pack_prey2 = -1 (contrato v2.8 intacto)."""
    print("=== PRESA POR SECTOR (v2.9): el 2º sector fija la MÁS LIBRE; el 1º la común de siempre ===")
    from baseline import build_world
    from world import ACTIVE
    vistos_2g = vistos_1g = verificados = 0
    for s in range(40):
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) != 2:
            vistos_1g += 1
            assert w.pack_prey2 == -1, "FALLO: pack_prey2 fijada con 1 solo grupo"
            continue
        vistos_2g += 1
        s2 = w._sector2()
        act = w.drones[w.drone_state == ACTIVE]
        if w.pack_prey2 < 0:
            # solo legítimo si el sector no puede cazar nada (sin terneros y sector < n_min_adult)
            assert not (w.calf_alive & ~w.calf_safe).any() and s2.size < w.n_min_adult, \
                "FALLO: pack_prey2 sin fijar habiendo objetivo cazable para el sector"
            continue
        # recomputa la regla y compara con lo fijado en t=0
        kind, idx = w.pack_prey2_kind, w.pack_prey2
        if kind == "calf":
            cand = (w.calf_alive & ~w.calf_safe).copy()
            if w.pack_prey_kind == "calf" and w.pack_prey >= 0 and cand.sum() > 1:
                cand[w.pack_prey] = False
            d = np.linalg.norm(w.calves[:, None, :] - act[None, :, :], axis=2).min(axis=1)
            d[~cand] = -np.inf
            assert idx == int(np.argmax(d)), "FALLO: prey2 no es el ternero MÁS LIBRE"
        else:
            cand = ((w.cow_alive & ~w.cow_safe) & ~w._in_forbidden(w.cows)).copy()
            if w.pack_prey_kind == "adult" and w.pack_prey >= 0 and cand.sum() > 1:
                cand[w.pack_prey] = False
            d = np.linalg.norm(w.cows[:, None, :] - act[None, :, :], axis=2).min(axis=1)
            d[~cand] = -np.inf
            assert idx == int(np.argmax(d)), "FALLO: prey2 no es la adulta MÁS LIBRE"
            assert s2.size >= w.n_min_adult, "FALLO: sector sin quórum fijó una adulta"
        verificados += 1
        if verificados >= 6:
            break
    print("  %d episodios de 2 grupos (verificados %d contra la regla) | %d de 1 grupo con pack_prey2=-1"
          % (vistos_2g, verificados, vistos_1g))
    assert verificados >= 3, "muestra insuficiente de episodios de 2 grupos"
    print("  OK\n")


def test_spotcheck_baseline():
    print("=== 4) SPOT-CHECK vs baseline v2.7 CONGELADA (baseline_v2.json, metro DGX): severidades IDÉNTICAS (no re-medir) ===")
    with open("baseline_v2.json", encoding="utf-8") as f:
        ref = json.load(f)
    # v2.7 = susto de DOS RADIOS (pared blanda estática); RE-MEDIDA en el contenedor canónico de la DGX (metro
    # oficial). Este spot-check solo es reproducible DENTRO de ese entorno (fuera puede salir rojo: deriva FP).
    assert ref["frozen_tag"] == "v3.4-baseline", "baseline_v2.json no es v3.4 (línea rígida + roles invertidos del cebo)"
    from baseline import build_world, run_episode_metrics
    checked = 0
    for kind in ("lobos", "corzos", "mixto"):
        eps = ref["by_kind"][kind]["episodes"]
        for seed in (0, 1, 2, 3, 7):                    # spot-check de 5 semillas por tipo
            w = build_world(seed, kind)
            m = run_episode_metrics(w, DummyCoordinator(w.n_drones))
            exp = eps[seed]["n_depredadas"]
            assert m["n_depredadas"] == exp, ("FALLO: %s seed=%d severidad %d != v2.4.1 %d (algo movió la baseline)"
                                              % (kind, seed, m["n_depredadas"], exp))
            checked += 1
    print("  %d episodios (3 tipos × 5 semillas): n_depredadas IDÉNTICO a v2.4.1 (nada movió la baseline)" % checked)
    print("  OK\n")


def test_timing_cebo():
    """v3.0 (pieza 3, dirigido): el sector-CEBO ESPERA merodeando (a >~decoy_hold_dist del ACTIVE
    más cercano, SIN congelarse) y se LANZA cuando el centroide del ASALTO cruza
    assault_trigger_dist de su presa (wolf_decoy_released False->True); tras el disparo el cebo
    CIERRA hacia el rebaño. Con DummyCoordinator (drones quietos) -> determinista y sin barrera."""
    print("=== TIMING DEL CEBO (v3.0): merodea sin congelarse -> disparo con el asalto a tiro -> carga ===")
    from baseline import build_world
    from world import ACTIVE
    hechos = 0
    for s in range(60):
        w = build_world(s, "lobos")
        coord = DummyCoordinator(w.n_drones)
        w.reset()
        if len(w.wolf_group_sizes) != 2 or w.pack_prey2 < 0 or w.wolf_decoy_released:
            continue
        n1 = int(w.wolf_group_sizes[0])
        s2 = np.arange(n1, w.n_wolves)
        herd_c0 = w.cows[w.cow_alive].mean(axis=0)
        release_step, d2_pre_release, dmin2_pre_release = None, None, None
        min_hold_settled = np.inf
        min_show = np.inf                             # v3.3: dmin cebo->ACTIVE TRAS el disparo (se muestra)
        path_len = 0.0
        prev_decoy = w.wolves[:n1].copy()
        for t in range(w.max_episode_steps):
            p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0 else None
            d2 = float(np.linalg.norm(w.wolves[s2].mean(axis=0) - p2)) if p2 is not None else None
            act_pre = w.drones[w.drone_state == ACTIVE]
            dmin2 = (float(np.linalg.norm(w.wolves[s2][:, None, :] - act_pre[None, :, :], axis=2).min())
                     if act_pre.shape[0] > 0 else np.inf)
            was = w.wolf_decoy_released
            w.step(coord.act(w.get_observation()))
            act = w.drones[w.drone_state == ACTIVE]
            if not was:
                path_len += float(np.linalg.norm(w.wolves[:n1] - prev_decoy, axis=1).sum())
                if t > 80 and act.shape[0] > 0:      # tras asentarse el merodeo
                    dmin = float(np.linalg.norm(w.wolves[:n1][:, None, :] - act[None, :, :], axis=2).min())
                    min_hold_settled = min(min_hold_settled, dmin)
            elif act.shape[0] > 0:
                min_show = min(min_show, float(np.linalg.norm(
                    w.wolves[:n1][:, None, :] - act[None, :, :], axis=2).min()))
            prev_decoy = w.wolves[:n1].copy()
            if w.wolf_decoy_released and release_step is None:
                release_step, d2_pre_release, dmin2_pre_release = t, d2, dmin2
            # ventana de show: con el DUMMY los drones están CLAVADOS (nadie barre) y el cebo puede
            # arrancar a ~300 m -> a 4 m/s tarda cientos de pasos en dejarse ver; se observa hasta
            # que ENTRA en r_detect, salta ESCOLTA o acaba el episodio (tope 2000 de seguridad).
            if release_step is not None and (t >= release_step + 2000 or min_show <= w.r_detect
                                             or w.phase == "ESCOLTA"):
                break
            if w.status != "running":
                break
        if release_step is None or release_step < 10:
            continue                                  # busca un episodio con ESPERA real
        print("  seed=%d: espera %d pasos (merodeo: camino=%.0f m, dist mín al ACTIVE=%.0f) | disparo con el "
              "asalto ESTACIONADO (dmin al ACTIVE %.0f <= sobre %.0f) y a %.0f m de su presa (<= %.0f = "
              "trigger+LEAD) | cebo SE MUESTRA tras el disparo: dmin %.0f (<= r_detect %.0f)"
              % (s, release_step, path_len, min_hold_settled, dmin2_pre_release or -1,
                 w.r_detect + ASSAULT_DARK_HOLD + ASSAULT_DARK_BAND, d2_pre_release or -1,
                 w.assault_trigger_dist + DECOY_SHOW_LEAD, min_show, w.r_detect))
        assert path_len > 20.0, "FALLO: el cebo esperó CONGELADO (merodeo sin movimiento)"
        assert min_hold_settled > w.decoy_hold_dist - 25.0, \
            "FALLO: el cebo invadió el radio de espera (no se mantiene fuera del alcance)"
        # v3.3 (ROLES INVERTIDOS): el disparo ya no es "asalto cruzando 150" (v3.0) sino el GATE de
        # estacionamiento de _assault_staged — asalto PEGADO al sobre oscuro Y a <= trigger +
        # DECOY_SHOW_LEAD de su presa (el cebo se muestra con ADELANTO: lo que el asalto avanza en
        # CREEP durante el show ≈ 60 m). Tras el disparo el cebo SE DEJA VER (entra en r_detect de
        # un ACTIVE — la inversión: el cebo busca ser el PRIMER confirmado y anclar la barrera).
        assert d2_pre_release is not None and \
            d2_pre_release <= w.assault_trigger_dist + DECOY_SHOW_LEAD + 10.0, \
            "FALLO: el disparo no respeta el gate de distancia (trigger + DECOY_SHOW_LEAD)"
        assert dmin2_pre_release is not None and \
            dmin2_pre_release <= w.r_detect + ASSAULT_DARK_HOLD + ASSAULT_DARK_BAND + 10.0, \
            "FALLO: el disparo con el asalto sin ESTACIONAR (lejos del sobre oscuro)"
        assert min_show <= w.r_detect, "FALLO: tras el disparo el cebo no se MUESTRA (no entra en r_detect)"
        hechos += 1
        if hechos >= 2:
            break
    assert hechos >= 1, "FALLO: ningún episodio con espera+disparo verificable en 60 semillas"
    print("  OK\n")


if __name__ == "__main__":
    test_interfaz()
    test_frontera_politica_fisica()
    test_susto_innegociable()
    test_presa_por_sector()
    test_timing_cebo()
    test_spotcheck_baseline()
    print("wolf_controller_check: TODO OK.")
