"""
rl_env_check.py — Verificación del ANDAMIAJE RL de lobos (rl/: controlador + env Gymnasium).

El andamiaje conecta la política aprendida con el mundo CONGELADO (v2.4) sin tocarlo. Aquí se
comprueba (asserts, estilo de los demás checks; corre con `python rl_env_check.py`):
  1) FORMAS Y MÁSCARAS: obs con el layout documentado (wolf_env.py); slots de padding a CERO
     con present/alive correctos (episodios con n_wolves<5 y sin terneros).
  2) DETERMINISMO: dos envs con la misma semilla -> mismas secuencias de kinds/episodios,
     misma obs inicial y misma trayectoria con las mismas acciones.
  3) CAP DE VELOCIDAD (la física prometida, en la FRONTERA del controlador): acción desbocada
     -> ni la intención ni la velocidad efectiva del lobo superan wolf_speed.
  4) REGLA DE PRESA (ternero primero): pack_prey_kind=="calf" mientras haya ternero cazable;
     solo adultas -> "adult"; nada -> -1/None y coasting.
  5) CANAL DE RECOMPENSA (el más importante): una política de mano que caza produce >=1 muerte
     y el env devuelve EXACTAMENTE +1 por muerte (obs->acción->mundo->recompensa conectado).
  6) EL MUNDO SCRIPTADO NO CAMBIÓ: spot-check contra baseline_v2.json (como wolf_controller_check)
     + make_wolf_controller('learned') SIGUE lanzando NotImplementedError + la extensión del
     arnés (build_world/evaluate) es retrocompatible.
"""

import json

import numpy as np

from world import World
from coordinators import DummyCoordinator
from wolf_controllers import ScriptedWolfController, make_wolf_controller
from baseline import CONFIG_V2, build_world, run_episode_metrics
from rl.rl_wolf_controller import RLWolfController
from rl.wolf_env import (CALF_FEAT, N_CALF_SLOTS, N_WOLF_SLOTS, OBS_SIZE, OFF_CALF, OFF_COW,
                         OFF_DRONE, OFF_GLOBAL, OFF_WOLF, WOLF_FEAT, WolfPackEnv)


def _reset_hasta(env, cond, max_resets=40):
    """Resetea hasta un episodio que cumpla cond(info) (la secuencia del env es determinista)."""
    for _ in range(max_resets):
        obs, info = env.reset()
        if cond(info):
            return obs, info
    raise AssertionError("no apareció un episodio con la condición pedida en %d resets" % max_resets)


def test_formas_y_mascaras():
    print("=== 1) FORMAS Y MÁSCARAS: layout documentado + padding a cero con present/alive ===")
    assert (OFF_WOLF, OFF_COW, OFF_CALF, OFF_DRONE, OFF_GLOBAL, OBS_SIZE) == (0, 30, 66, 80, 120, 122), \
        "el layout no cuadra con la referencia documentada en wolf_env.py"
    env = WolfPackEnv(seed=0)
    obs, info = env.reset()
    assert obs.shape == (OBS_SIZE,) and obs.dtype == np.float32, "obs debe ser float32 (122,)"
    assert env.action_space.shape == (N_WOLF_SLOTS * 2,)
    assert np.isfinite(obs).all(), "obs con NaN/inf"

    # Episodio con MENOS de 5 lobos: slots sobrantes TODO a cero (present=0); reales con present=1.
    obs, info = _reset_hasta(env, lambda i: 0 < i["n_wolves"] < N_WOLF_SLOTS)
    nw = info["n_wolves"]
    for i in range(nw):
        assert obs[OFF_WOLF + WOLF_FEAT * i + 5] == 1.0, "lobo real sin present=1"
    assert not obs[OFF_WOLF + WOLF_FEAT * nw: OFF_COW].any(), "slots de lobo de padding no están a cero"

    # Episodio SIN terneros: los 2 slots de ternero enteros a cero. Con terneros: present/alive=1.
    obs0, _ = _reset_hasta(env, lambda i: i["n_calves"] == 0)
    assert not obs0[OFF_CALF:OFF_DRONE].any(), "slots de ternero no están a cero sin terneros"
    obs1, info1 = _reset_hasta(env, lambda i: i["n_calves"] >= 1)
    for i in range(info1["n_calves"]):
        base = OFF_CALF + CALF_FEAT * i
        assert obs1[base + 4] == 1.0 and obs1[base + 6] == 1.0, "ternero real sin alive/present=1"

    # Globales al reset: todas las reses en juego ((6+terneros)/6) y reloj a 0.
    assert abs(obs1[OFF_GLOBAL] - (6 + info1["n_calves"]) / 6.0) < 1e-6, "global reses en juego mal"
    assert obs1[OFF_GLOBAL + 1] == 0.0, "global reloj debe ser 0 al reset"
    print("  layout (122) OK | padding lobos (nw=%d) a cero | terneros 0/%d con máscaras | globales OK"
          % (nw, info1["n_calves"]))
    print("  OK\n")


def test_determinismo():
    print("=== 2) DETERMINISMO: misma semilla del env => misma secuencia de episodios y trayectoria ===")
    e1, e2 = WolfPackEnv(seed=123), WolfPackEnv(seed=123)
    kinds = []
    for _ in range(3):
        o1, i1 = e1.reset(); o2, i2 = e2.reset()
        assert i1["episode_kind"] == i2["episode_kind"] and i1["world_seed"] == i2["world_seed"], \
            "la secuencia de episodios difiere con la misma semilla"
        assert np.array_equal(o1, o2), "obs inicial difiere con la misma semilla"
        kinds.append(i1["episode_kind"])
    # Misma trayectoria con las mismas acciones (mundo determinista + coordinador determinista).
    acts = np.random.default_rng(7).uniform(-1.0, 1.0, size=(30, N_WOLF_SLOTS * 2)).astype(np.float32)
    for a in acts:
        o1, r1, t1, tr1, _ = e1.step(a); o2, r2, t2, tr2, _ = e2.step(a)
        assert np.array_equal(o1, o2) and r1 == r2 and t1 == t2 and tr1 == tr2, "trayectorias divergen"
        if t1 or tr1:
            break
    # Y semillas distintas -> secuencias distintas (que no sea un env congelado).
    e3 = WolfPackEnv(seed=124)
    _, i3 = e3.reset()
    _, i1b = WolfPackEnv(seed=123).reset()
    assert i3["world_seed"] != i1b["world_seed"], "semillas distintas dan el mismo primer episodio"
    print("  3 resets idénticos (kinds=%s) | 30 pasos idénticos | seed distinta -> episodio distinto" % kinds)
    print("  OK\n")


def test_cap_velocidad():
    print("=== 3) CAP DE VELOCIDAD en la frontera: acción desbocada nunca supera wolf_speed ===")
    # (a) DIRECTO: el controlador recorta la NORMA de la intención (mucho más que el cap).
    ctrl = RLWolfController(N_WOLF_SLOTS)
    w = World(seed=3, episode_kind="lobos", wolf_controller=ctrl, **CONFIG_V2)
    ctrl.set_action(np.full((N_WOLF_SLOTS, 2), 100.0))
    v, coasting = ctrl.decide(w)
    assert v.shape == (w.n_wolves, 2) and not coasting
    assert (np.linalg.norm(v, axis=1) <= w.wolf_speed + 1e-9).all(), "la intención supera el cap"
    # (b) INTEGRADO: acción saturada (±1 en todo -> norma √2·wolf_speed SIN cap) durante 50
    #     decisiones; la velocidad EFECTIVA del lobo (wolf_vel, tras susto+inercia) nunca lo supera.
    env = WolfPackEnv(kinds=("lobos",), seed=5)
    env.reset()
    a = np.ones(N_WOLF_SLOTS * 2, dtype=np.float32)
    vmax = 0.0
    for _ in range(50):
        _, _, term, trunc, _ = env.step(a)
        if env._world.n_wolves > 0:
            vmax = max(vmax, float(np.linalg.norm(env._world.wolf_vel, axis=1).max()))
        if term or trunc:
            break
    assert vmax <= env._world.wolf_speed + 1e-6, "wolf_vel superó wolf_speed: el cap no llegó al mundo"
    print("  intención recortada por norma (|v|<=%.1f) | efectiva máx=%.3f <= wolf_speed=%.1f"
          % (w.wolf_speed, vmax, env._world.wolf_speed))
    print("  OK\n")


def test_regla_presa():
    print("=== 4) REGLA DE PRESA (ternero primero) + coasting determinista ===")
    # Un episodio de lobos CON ternero (World directo, semilla buscada determinista).
    ctrl = RLWolfController(N_WOLF_SLOTS)
    w = None
    for s in range(40):
        cand = World(seed=s, episode_kind="lobos", wolf_controller=ctrl, **CONFIG_V2)
        if cand.n_calves >= 1:
            w = cand
            break
    assert w is not None, "no apareció episodio de lobos con ternero en 40 semillas"
    ctrl.set_action(np.zeros((N_WOLF_SLOTS, 2)))

    # Con ternero cazable: presa = el ternero vivo no-a-salvo MÁS CERCANO al centroide del paquete.
    ctrl.decide(w)
    assert w.pack_prey_kind == "calf", "con ternero cazable la presa debe ser 'calf'"
    centroid = w.wolves.mean(axis=0)
    d = np.linalg.norm(w.calves - centroid, axis=1)
    assert w.pack_prey == int(np.argmin(d)), "no es el ternero más cercano al centroide del paquete"

    # Sin terneros cazables: pasa a la vaca viva no-a-salvo más cercana (índice en cows).
    w.calf_alive[:] = False
    ctrl.decide(w)
    assert w.pack_prey_kind == "adult", "sin terneros la presa debe ser 'adult'"
    d = np.linalg.norm(w.cows - centroid, axis=1)
    assert w.pack_prey == int(np.argmin(d)), "no es la vaca más cercana al centroide del paquete"

    # Vaca refugiada deja de ser presa (viva pero a salvo): la regla salta a la siguiente.
    w.cow_safe[w.pack_prey] = True
    prev = w.pack_prey
    ctrl.decide(w)
    assert w.pack_prey != prev, "una res refugiada no puede seguir siendo la presa"

    # Nada cazable: -1/None y COASTING (v=0), regla determinista (no lo decide la red).
    w.cow_alive[:] = False
    v, coasting = ctrl.decide(w)
    assert w.pack_prey == -1 and w.pack_prey_kind is None, "sin reses cazables debe quedar -1/None"
    assert coasting and not v.any(), "sin objetivos debe coastear con v=0"
    print("  calf más cercano OK -> adult más cercana OK -> refugiada se suelta OK -> agotado: -1/None + coasting")
    print("  OK\n")


def _accion_caza(env):
    """Política de MANO: cada lobo a tope hacia la res viva no-a-salvo más cercana (unitario)."""
    w = env._world
    a = np.zeros((N_WOLF_SLOTS, 2), dtype=np.float32)
    parts = []
    m = w.cow_alive & ~w.cow_safe
    if m.any():
        parts.append(w.cows[m])
    if w.n_calves > 0:
        mc = w.calf_alive & ~w.calf_safe
        if mc.any():
            parts.append(w.calves[mc])
    if not parts:
        return a.ravel()
    T = np.vstack(parts)
    for i in range(w.n_wolves):
        v = T[int(np.argmin(np.linalg.norm(T - w.wolves[i], axis=1)))] - w.wolves[i]
        n = float(np.linalg.norm(v))
        if n > 1e-9:
            a[i] = v / n
    return a.ravel()


def test_canal_recompensa():
    print("=== 5) CANAL DE RECOMPENSA: obs->acción->mundo->recompensa conectado (+1 exacto por muerte) ===")
    total_kills = 0
    resumen = []
    for s in range(6):
        env = WolfPackEnv(kinds=("lobos",), seed=s)
        env.reset()
        max_steps = env._world.max_episode_steps // env._frame_skip + 2
        ep_reward, steps, fin = 0.0, 0, False
        for _ in range(max_steps):
            _, r, term, trunc, _ = env.step(_accion_caza(env))
            assert r >= 0.0 and abs(r - round(r)) < 1e-9, "la recompensa debe ser entera >= 0 (+1 por muerte)"
            ep_reward += r
            steps += 1
            if term or trunc:
                fin = True
                break
        assert fin, "el episodio no terminó (seed=%d)" % s
        assert ep_reward == env._world.n_depredadas, \
            "recompensa acumulada %.0f != n_depredadas %d (canal roto)" % (ep_reward, env._world.n_depredadas)
        total_kills += int(ep_reward)
        resumen.append("seed %d: %d muertes en %d pasos de env" % (s, int(ep_reward), steps))
    print("  " + " | ".join(resumen))
    assert total_kills >= 1, "la política de caza de mano no mató NADA en 6 semillas: canal sospechoso"
    print("  total=%d muertes; recompensa == n_depredadas episodio a episodio (canal REAL)" % total_kills)
    print("  OK\n")


def test_mundo_scriptado_intacto():
    print("=== 6) EL MUNDO SCRIPTADO NO CAMBIÓ: spot-check vs baseline_v2.json + arnés retrocompatible ===")
    # El hueco 'learned' de la factoría SIGUE cerrado (el RL inyecta wolf_controller= directo).
    try:
        make_wolf_controller("learned")
        raise AssertionError("make_wolf_controller('learned') debería seguir lanzando NotImplementedError")
    except NotImplementedError:
        pass
    # Extensión retrocompatible: sin controlador -> scriptado; con controlador -> la instancia inyectada.
    w = build_world(0, "lobos")
    assert isinstance(w.wolf_controller, ScriptedWolfController), "build_world sin controlador ya no es scriptado"
    ctrl = RLWolfController(N_WOLF_SLOTS)
    w2 = build_world(0, "lobos", wolf_controller=ctrl)
    assert w2.wolf_controller is ctrl, "build_world no respeta la inyección de wolf_controller"
    # Spot-check: el andamiaje no puede haber movido la física (severidades IDÉNTICAS a v2.4).
    with open("baseline_v2.json", encoding="utf-8") as f:
        ref = json.load(f)
    assert ref["frozen_tag"] == "v2.4.1-baseline"   # metro DGX (reproducible solo dentro del contenedor)
    checked = 0
    for kind in ("lobos", "corzos", "mixto"):
        eps = ref["by_kind"][kind]["episodes"]
        for seed in (0, 1, 7):
            wk = build_world(seed, kind)
            m = run_episode_metrics(wk, DummyCoordinator(wk.n_drones))
            assert m["n_depredadas"] == eps[seed]["n_depredadas"], \
                "FALLO: %s seed=%d severidad %d != v2.4.1 %d (el andamiaje movió la física)" \
                % (kind, seed, m["n_depredadas"], eps[seed]["n_depredadas"])
            checked += 1
    print("  'learned' sigue NotImplementedError | build_world retrocompatible + inyección | "
          "%d episodios (3 tipos × 3 semillas) idénticos a v2.4.1" % checked)
    print("  OK\n")


if __name__ == "__main__":
    test_formas_y_mascaras()
    test_determinismo()
    test_cap_velocidad()
    test_regla_presa()
    test_canal_recompensa()
    test_mundo_scriptado_intacto()
    print("rl_env_check: TODO OK.")
