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
from wolf_controllers import WolfController, ScriptedWolfController, make_wolf_controller

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


def test_spotcheck_baseline():
    print("=== 4) SPOT-CHECK vs baseline v2.7 CONGELADA (baseline_v2.json, metro DGX): severidades IDÉNTICAS (no re-medir) ===")
    with open("baseline_v2.json", encoding="utf-8") as f:
        ref = json.load(f)
    # v2.7 = susto de DOS RADIOS (pared blanda estática); RE-MEDIDA en el contenedor canónico de la DGX (metro
    # oficial). Este spot-check solo es reproducible DENTRO de ese entorno (fuera puede salir rojo: deriva FP).
    assert ref["frozen_tag"] == "v2.7-baseline", "baseline_v2.json no es v2.7 (susto de dos radios: dron quieto repele a corta)"
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


if __name__ == "__main__":
    test_interfaz()
    test_frontera_politica_fisica()
    test_susto_innegociable()
    test_spotcheck_baseline()
    print("wolf_controller_check: TODO OK.")
