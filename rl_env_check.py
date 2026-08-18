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
  7) EQUIVALENCIA ENV ↔ CONTROLADOR DE EVALUACIÓN (obs de un solo origen, rl/obs.py): con el
     MISMO modelo (PPO sembrado sin entrenar, hermético) y la MISMA semilla de mundo, la
     trayectoria del env (WolfPackEnv + predict por fuera) y la del evaluador
     (PolicyWolfController + SyncedReactiveCoordinator, refresco en la FRONTERA del step)
     son BIT A BIT idénticas — si divergieran, eval_wolves mediría OTRA política.
  8) SHAPING POR POTENCIAL (plan B, r_shape = γ·Φ(s′) − Φ(s)): TELESCOPIA (la suma descontada
     del término == γ^T·Φ(s_T) − Φ(s_0), acotada — no cultivable); SIGNO (acercarse a la presa
     acumula r_shape > 0 al principio; alejarse, < 0); KILLS INTACTOS (con shaping ON,
     r_kills acumulado == Δn_depredadas EXACTO, como el test 5); y OFF ≡ run01 (con
     shaping=False —el default— la dinámica es bit a bit la misma y la recompensa es
     EXACTAMENTE la rala).
  9) RESIDUAL (RPL, run04 — rl/residual_wolf_controller.py): con δ≡0 la trayectoria de un
     episodio COMPLETO es BIT A BIT la del scriptado puro (incluida `pack_prey`: la del
     SCRIPT con su histéresis, NO la regla del contrato RL); con δ desbocado la velocidad
     final queda capada a wolf_speed; en coasting δ NO se aplica (pass-through); la obs
     residual es (132) con la pista del script a 0 en la primera frontera y viva después.
 10) DRONES (infra MARL, rl/drone_obs|drone_env|residual_drone_coordinator) — ADAPTADO a run02
     SIN bajar el listón (mismas igualdades EXACTAS; cambia el objetivo de la equivalencia, no
     la exigencia — decisión de diseño del usuario, run02: residual SIN rigidez + obs con
     contactos y confirmados):
     (a) build_drone_local_obs: layout/máscaras/ego correctos; un lobo NI-contacto-NI-confirmado
         NO viaja en la obs local (slot a cero); la mitad global == rl.obs.build_obs exacta;
     (b) SUELO: con δ≡0 (model=None, sin set_delta) ResidualDroneCoordinator ≡ NonRigidBarrier
         (la barrera v3.4 SIN el gobernador — el suelo DE ESTA VARIANTE) BIT A BIT en un
         episodio completo (waypoints, drones y muertes idénticos); y la NonRigidBarrier solo
         difiere de la ReactiveCoordinator v3.4 en la pose (mismo eje/las mismas ranuras cuando
         la pose rígida ya ha convergido no se asserta — es la deformación transitoria);
     (c) MÁSCARA (load-bearing): un δ enorme NO desvía a un RETURNING (fuera de los asientos)
         ni al investigador (mask), y SÍ mueve a los comandables;
     (d) CANAL DE RECOMPENSA: r_global acumulada == −n_depredadas EXACTO; agent_rewards =
         r_global + local_coef·r_local por puesto; ep_severity/ep_deter al terminal; y la
         atribución de disuasión (deter_credit) da crédito al dron que EMBISTE (dirigido);
     (e) CONTACTOS vs CONFIRMADOS (run02, cambio de diseño 2 — dirigido): un lobo a 60 m de un
         ACTIVE (contacto sin clasificar) viaja en el grupo de CONTACTOS y NO en confirmados;
         al cruzar r_confirm=40 pasa a CONFIRMADOS (sale de contactos: grupos disjuntos) y SE
         RECUERDA (memoria de equipo) aunque vuelva a alejarse a >r_detect.
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
    assert ref["frozen_tag"] == "v3.5-sonido"   # regla del sonido (v3.5); metro DGX (reproducible solo dentro del contenedor)
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


def test_equivalencia_env_controlador():
    print("=== 7) EQUIVALENCIA ENV ↔ CONTROLADOR DE EVALUACIÓN: misma política ⇒ misma trayectoria (bit a bit) ===")
    from stable_baselines3 import PPO
    from rl.policy_wolf_controller import PolicyWolfController, SyncedReactiveCoordinator

    # Modelo HERMÉTICO: PPO sembrado SIN entrenar (determinista con predict(deterministic=True));
    # no depende de ningún model.zip en /data. El env del modelo es aparte (solo fija los espacios).
    model = PPO("MlpPolicy", WolfPackEnv(kinds=("lobos",), seed=999), seed=0, device="cpu")

    # LADO ENV (como en entrenamiento): predict fuera, obs del env, frame-skip interno.
    env = WolfPackEnv(kinds=("lobos",), seed=17)
    obs, info = env.reset()
    traj_env, fin = [], False
    # cap DERIVADO del horizonte real del mundo (v3.0: terreno 500 -> max_episode_steps 23570 =
    # ~4714 pasos de env con frame-skip 5; el cap fijo 3500 se quedaba corto) + margen.
    cap = env._world.max_episode_steps // 5 + 100
    for _ in range(cap):
        action, _ = model.predict(obs, deterministic=True)
        obs, _r, term, trunc, _ = env.step(action)
        w = env._world
        traj_env.append((w.wolves.copy(), w.cows.copy(), int(w.n_depredadas), int(w.step_count)))
        if term or trunc:
            fin = True
            break
    assert fin, "el episodio del env no terminó (cap = horizonte del mundo + margen)"
    status_env = env._world.status

    # LADO EVALUADOR: mismo mundo (world_seed del env), PolicyWolfController + coordinador
    # SINCRONIZADO (refresca la política en la FRONTERA, antes de cada world.step — el mismo
    # instante en que el env construye su obs). Muestreamos en las MISMAS fronteras (cada 5
    # pasos de física y al terminal).
    ctrl = PolicyWolfController(model=model)
    w = World(seed=info["world_seed"], episode_kind=info["episode_kind"],
              wolf_controller=ctrl, **CONFIG_V2)
    coord = SyncedReactiveCoordinator(w)
    traj_ctl, k = [], 0
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        k += 1
        if k % 5 == 0 or term or trunc:
            traj_ctl.append((w.wolves.copy(), w.cows.copy(), int(w.n_depredadas), int(w.step_count)))
        if term or trunc:
            break
        # cap DERIVADO (v3.0: terreno 500 -> max_episode_steps 23570 > el fijo 20000 de antes)
        assert k < w.max_episode_steps + 500, "el episodio del evaluador no termina (desincronizado)"

    assert len(traj_env) == len(traj_ctl), \
        "nº de fronteras distinto: env=%d vs controlador=%d" % (len(traj_env), len(traj_ctl))
    for j, (a, b) in enumerate(zip(traj_env, traj_ctl)):
        assert (np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
                and a[2] == b[2] and a[3] == b[3]), \
            "trayectorias divergen en la frontera %d (paso de física %d)" % (j, b[3])
    assert status_env == w.status and env._world.n_depredadas == w.n_depredadas
    print("  %d fronteras idénticas (lobos+vacas+muertes+reloj, bit a bit) | terminal %s con %d muertes en ambos"
          % (len(traj_env), w.status, w.n_depredadas))
    print("  OK\n")


def _presa_designada(w):
    """Posición de la presa que usa Φ (la MISMA regla ternero-primero del controlador,
    aplicada con guardar/restaurar — igual que WolfPackEnv._phi)."""
    saved = (w.pack_prey, w.pack_prey_kind)
    RLWolfController._write_prey(w)
    idx, kind = w.pack_prey, w.pack_prey_kind
    w.pack_prey, w.pack_prey_kind = saved
    if idx < 0:
        return None
    return (w.calves[idx] if kind == "calf" else w.cows[idx]).copy()


def test_shaping_potencial():
    print("=== 8) SHAPING POR POTENCIAL: telescopia + signo + kills intactos + off ≡ run01 ===")
    BETA, GAMMA = 1.0, 0.999

    # (a) TELESCOPIA + (c) KILLS INTACTOS — política de caza (episodios con muertes, como test 5):
    #     Σ_t γ^t·r_shape_t == γ^T·Φ(s_T) − Φ(s_0) (propiedad de Ng et al.: el término no es
    #     cultivable — acotado por 2β sea cual sea T) y r_kills acumulado == n_depredadas EXACTO.
    total_kills, resumen = 0, []
    for s in range(3):
        env = WolfPackEnv(kinds=("lobos",), seed=s, shaping=True,
                          shaping_beta=BETA, shaping_gamma=GAMMA)
        env.reset()
        phi0 = env._phi_prev                              # Φ(s_0), recién calculado en reset
        max_steps = env._world.max_episode_steps // env._frame_skip + 2
        disc, g, T, kills, fin, info = 0.0, 1.0, 0, 0.0, False, {}
        for _ in range(max_steps):
            _, r, term, trunc, info = env.step(_accion_caza(env))
            assert abs(r - (info["r_kills"] + info["r_shape"])) < 1e-12, "reward != r_kills + r_shape"
            disc += g * info["r_shape"]
            g *= GAMMA
            T += 1
            kills += info["r_kills"]
            if term or trunc:
                fin = True
                break
        assert fin, "el episodio no terminó (seed=%d)" % s
        esperado = GAMMA ** T * env._phi_prev - phi0      # env._phi_prev == Φ(s_T)
        assert abs(disc - esperado) < 1e-9, \
            "telescopia rota (seed=%d): Σγ^t·r_shape=%.12f != γ^T·Φ_T−Φ_0=%.12f" % (s, disc, esperado)
        assert abs(disc) <= 2.0 * BETA + 1e-9, "la suma descontada del shaping no está acotada por 2β"
        assert kills == env._world.n_depredadas and kills == info["ep_kills"], \
            "r_kills acumulado %.0f != n_depredadas %d (el shaping tocó el canal de kills)" \
            % (kills, env._world.n_depredadas)
        total_kills += int(kills)
        resumen.append("seed %d: T=%d, Σγ^t·r_shape=%.4f, %d muertes" % (s, T, disc, int(kills)))
    assert total_kills >= 1, "la política de caza no mató nada en 3 semillas con shaping ON"
    print("  " + " | ".join(resumen))

    # (b) SIGNO: empujar los lobos HACIA la presa designada acumula r_shape > 0 en los primeros
    #     pasos; alejarlos, < 0 (mismo episodio, misma semilla; pocos pasos: antes del susto).
    def _suma_shape(hacia: bool, n_pasos: int = 4) -> float:
        env = WolfPackEnv(kinds=("lobos",), seed=11, shaping=True,
                          shaping_beta=BETA, shaping_gamma=GAMMA)
        env.reset()
        s_total = 0.0
        for _ in range(n_pasos):
            w = env._world
            prey = _presa_designada(w)
            assert prey is not None, "el episodio de signo arrancó sin presa cazable"
            a = np.zeros((N_WOLF_SLOTS, 2), dtype=np.float32)
            for i in range(w.n_wolves):
                v = prey - w.wolves[i]
                nv = float(np.linalg.norm(v))
                if nv > 1e-9:
                    a[i] = (v / nv) if hacia else (-v / nv)
            _, _r, term, trunc, info = env.step(a.ravel())
            s_total += info["r_shape"]
            assert not (term or trunc), "el episodio de signo terminó demasiado pronto"
        return s_total
    s_hacia, s_lejos = _suma_shape(True), _suma_shape(False)
    assert s_hacia > 0.0, "acercarse a la presa debería acumular r_shape > 0 (%.6f)" % s_hacia
    assert s_lejos < 0.0, "alejarse de la presa debería acumular r_shape < 0 (%.6f)" % s_lejos
    print("  signo: hacia la presa Σr_shape=%.5f > 0 | lejos Σr_shape=%.5f < 0" % (s_hacia, s_lejos))

    # (d) OFF ≡ run01: con shaping=False (el DEFAULT del constructor) la dinámica es bit a bit
    #     la del env de run01 y la recompensa es EXACTAMENTE la rala (r_kills); el flag ON no
    #     toca la física (obs idénticas paso a paso entre ambos).
    e_on = WolfPackEnv(kinds=("lobos",), seed=23, shaping=True,
                       shaping_beta=BETA, shaping_gamma=GAMMA)
    e_off = WolfPackEnv(kinds=("lobos",), seed=23)            # defaults = el env de run01
    o_on, i_on = e_on.reset()
    o_off, i_off = e_off.reset()
    assert i_on["world_seed"] == i_off["world_seed"] and np.array_equal(o_on, o_off)
    rng = np.random.default_rng(5)
    pasos = 0
    while True:
        a = rng.uniform(-1.0, 1.0, N_WOLF_SLOTS * 2).astype(np.float32)
        o1, r1, t1, tr1, i1 = e_on.step(a)
        o2, r2, t2, tr2, i2 = e_off.step(a)
        assert np.array_equal(o1, o2), "el shaping tocó la DINÁMICA (obs divergen en el paso %d)" % pasos
        assert r2 == i1["r_kills"], "con off la recompensa debe ser EXACTAMENTE la rala (run01)"
        assert i2["r_shape"] == 0.0 and abs(r1 - (r2 + i1["r_shape"])) < 1e-12
        assert (t1, tr1) == (t2, tr2), "terminales divergen entre on/off"
        pasos += 1
        if t1 or tr1:
            break
    print("  off ≡ run01: %d pasos con obs bit a bit idénticas on/off, reward_off == r_kills_on" % pasos)
    print("  OK\n")


def test_residual():
    print("=== 9) RESIDUAL (RPL): δ=0 ⇒ scriptado BIT A BIT · cap con δ desbocado · presa del script · coasting ===")
    from coordinators import ReactiveCoordinator
    from rl.residual_wolf_controller import RESIDUAL_OBS_SIZE, ResidualWolfController

    # (a) δ≡0 (model=None) ⇒ episodio COMPLETO bit a bit igual al scriptado puro contra la
    #     barrera — incluida pack_prey: la del SCRIPT (su fijación/histéresis), NO el contrato RL.
    def _traj(ctrl):
        w = World(seed=21, episode_kind="lobos", wolf_controller=ctrl, **CONFIG_V2)
        coord = ReactiveCoordinator(w)
        traj = []
        while True:
            _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
            traj.append((w.wolves.copy(), w.cows.copy(), int(w.n_depredadas),
                         int(w.pack_prey), w.pack_prey_kind, int(w.step_count)))
            if term or trunc:
                break
        return traj, w
    tj_s, w_s = _traj(ScriptedWolfController())
    tj_r, w_r = _traj(ResidualWolfController())          # sin modelo ⇒ δ≡0 (el SUELO)
    assert len(tj_s) == len(tj_r), "longitudes distintas: el camino residual con δ=0 no es el scriptado"
    for j, (a, b) in enumerate(zip(tj_s, tj_r)):
        assert (np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]) and a[2:] == b[2:]), \
            "δ=0 diverge del scriptado en el paso %d (¿clip/presa/sincronía?)" % b[5]
    assert w_s.status == w_r.status and w_s.n_depredadas == w_r.n_depredadas
    print("  δ=0 ≡ scriptado: %d pasos bit a bit (lobos+vacas+muertes+presa) | terminal %s con %d muertes"
          % (len(tj_s), w_r.status, w_r.n_depredadas))

    # (b) δ DESBOCADO ⇒ ni la intención ni la velocidad efectiva superan wolf_speed.
    ctrl = ResidualWolfController()
    w = World(seed=5, episode_kind="lobos", wolf_controller=ctrl, **CONFIG_V2)
    coord = ReactiveCoordinator(w)
    ctrl.set_delta(np.full((5, 2), 1e3))
    v, coasting = ctrl.decide(w)
    assert not coasting and (np.linalg.norm(v, axis=1) <= w.wolf_speed + 1e-9).all(), \
        "la intención residual supera wolf_speed"
    vmax = 0.0
    for _ in range(30):
        ctrl.set_delta(np.full((5, 2), 1e3))
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        vmax = max(vmax, float(np.linalg.norm(w.wolf_vel, axis=1).max()))
        if term or trunc:
            break
    assert vmax <= w.wolf_speed + 1e-6, "wolf_vel superó wolf_speed con δ desbocado"
    print("  δ desbocado: |v_final| <= %.1f (intención) y |wolf_vel| máx = %.3f <= %.1f (efectiva)"
          % (w.wolf_speed, vmax, w.wolf_speed))

    # (c) COASTING: δ no se aplica (pass-through del script — la red no impide el desenganche).
    ctrl = ResidualWolfController()
    w = World(seed=3, episode_kind="lobos", wolf_controller=ctrl, **CONFIG_V2)
    w.cow_alive[:] = False
    if w.n_calves > 0:
        w.calf_alive[:] = False
    ctrl.set_delta(np.full((5, 2), 100.0))
    v, coasting = ctrl.decide(w)
    assert coasting and not v.any(), "en coasting δ no debe aplicarse (pass-through del script)"

    # (d) OBS RESIDUAL del env: (132,); pista a 0 en la PRIMERA frontera (el script no habló) y
    #     viva después (último v_target normalizado, |·| <= 1 por componente).
    env = WolfPackEnv(kinds=("lobos",), seed=7, residual=True)
    obs, _info = env.reset()
    assert obs.shape == (RESIDUAL_OBS_SIZE,) and obs.dtype == np.float32
    assert not obs[OBS_SIZE:].any(), "la pista debe ser 0 en la primera frontera"
    obs2, _r, term, trunc, _i = env.step(np.zeros(10, dtype=np.float32))
    assert not (term or trunc)
    assert obs2[OBS_SIZE:].any() and (np.abs(obs2[OBS_SIZE:]) <= 1.0 + 1e-6).all(), \
        "la pista del script debe estar viva y normalizada tras el primer step"
    print("  coasting pass-through OK | obs residual (132): pista 0 en t=0, viva y acotada después")
    print("  OK\n")


def test_drones():
    print("=== 10) DRONES (infra MARL, run02): obs contactos+confirmados · SUELO δ=0 ≡ SIN-RIGIDEZ "
          "bit a bit · máscara · recompensa ===")
    from baseline import build_world
    from world import ACTIVE, RETURNING, World
    from rl.drone_obs import (AGENT_OBS_SIZE, LOCAL_SIZE, N_SEATS, OFF_CONF, OFF_COW, OFF_DRONE,
                              OFF_EGO, OFF_LGLOBAL, OFF_WOLF, build_drone_agent_obs,
                              build_drone_local_obs)
    from rl.drone_env import DroneTeamEnv, deter_credit
    from rl.obs import build_obs
    from rl.residual_drone_coordinator import NonRigidBarrier, ResidualDroneCoordinator

    # (a) LAYOUT + percepción: contacto viaja en SU grupo; lobo fuera de radio y sin confirmar
    #     NO viaja en ninguno; ego/global correctos.
    for s in range(1, 15):                                        # primer seed con >=3 lobos (determinista)
        w = build_world(s, "lobos"); w.reset()
        if w.n_wolves >= 3:
            break
    d0 = int(np.where(w.drone_state == ACTIVE)[0][0])
    w.wolves[0] = w.drones[d0] + np.array([60.0, 0.0])            # CONTACTO (60 <= r_detect, > r_confirm)
    far = np.array([3.0, 3.0]) if np.linalg.norm(w.drones - [3, 3], axis=1).min() > w.r_detect + 5 \
        else np.array([297.0, 297.0])
    for j in range(1, w.n_wolves):
        w.wolves[j] = far + np.array([float(j), 0.0])             # NI contacto NI confirmado (lejos)
    base_wp = np.array([150.0, 150.0])
    lo = build_drone_local_obs(w, d0, base_wp)                    # confirmed=None (nada confirmado)
    center, scale = w.safe_zone[:2], np.array([w.W / 2, w.H / 2])
    assert lo.shape == (LOCAL_SIZE,) and lo.dtype == np.float32
    assert np.allclose(lo[OFF_EGO:OFF_EGO + 2], (w.drones[d0] - center) / scale), "ego pos mal"
    assert lo[OFF_EGO + 4] == 1.0 and lo[OFF_EGO + 5] == 1.0, "ego is_active/commandable mal"
    assert np.allclose(lo[OFF_EGO + 6:OFF_EGO + 8], (base_wp - center) / scale), "pista base_wp mal"
    s0 = lo[OFF_WOLF:OFF_WOLF + 6]
    assert s0[5] == 1.0 and np.allclose(s0[0:2], (w.wolves[0] - center) / scale), "contacto ausente"
    assert not lo[OFF_CONF:OFF_COW].any(), "confirmados debería estar VACÍO (confirmed=None)"
    for j in range(1, w.n_wolves):
        assert not lo[OFF_WOLF + 6 * j:OFF_WOLF + 6 * (j + 1)].any(), \
            "FALLO: un lobo fuera de radio viaja en la obs local (omnisciencia)"
    ag = build_drone_agent_obs(w, d0, base_wp)
    assert ag.shape == (AGENT_OBS_SIZE,) and np.array_equal(ag[:LOCAL_SIZE], lo)
    assert np.array_equal(ag[LOCAL_SIZE:], build_obs(w)), "la mitad global no es build_obs exacta"
    print("  (a) layout OK (%d): ego+pista, contacto presente, confirmados vacío, %d lejanos a cero, "
          "global == build_obs" % (LOCAL_SIZE, w.n_wolves - 1))

    # (b) SUELO run02: δ≡0 ⇒ bit a bit la barrera SIN RIGIDEZ (el suelo DE ESTA VARIANTE),
    #     episodio COMPLETO (mundos gemelos). Mismo listón de igualdad exacta que siempre.
    wA = build_world(5, "mixto"); wA.reset(); cA = NonRigidBarrier(wA)
    wB = build_world(5, "mixto"); wB.reset(); cB = ResidualDroneCoordinator(wB, model=None)
    steps = 0
    while True:
        a = cA.act(wA.get_observation()); b = cB.act(wB.get_observation())
        assert np.array_equal(a, b), "FALLO suelo: waypoints difieren en el paso %d" % steps
        _, _, tA, uA, _ = wA.step(a)
        _, _, tB, uB, _ = wB.step(b)
        assert np.array_equal(wA.drones, wB.drones) and (tA, uA) == (tB, uB)
        steps += 1
        if tA or uA:
            break
    assert wA.n_depredadas == wB.n_depredadas and wA.status == wB.status
    print("  (b) SUELO δ=0 ≡ barrera SIN RIGIDEZ BIT A BIT: %d pasos, status=%s, muertes=%d idénticos"
          % (steps, wB.status, wB.n_depredadas))

    # (c) MÁSCARA load-bearing: δ enorme NO toca RETURNING/investigador; SÍ mueve comandables.
    w = build_world(2, "lobos"); w.reset()
    ctrl = ResidualDroneCoordinator(w, model=None)
    w.drone_state[1] = RETURNING                                   # fuera de estación (fuera de asientos)
    w.drone_investigating[2] = True                                # ACTIVE pero el reflejo manda
    base = ctrl.act(None).copy()                                   # sin δ: barrera pura
    ctrl.set_delta(np.full((N_SEATS, 2), 500.0))
    wp = ctrl.act(None)
    assert np.array_equal(wp[1], base[1]), "FALLO máscara: δ desvió a un RETURNING (rompe la carga)"
    assert np.array_equal(wp[2], base[2]), "FALLO máscara: δ desvió al investigador (reflejo manda)"
    moved = [d for d in (0, 3) if not np.array_equal(wp[d], base[d])]
    assert moved, "FALLO: δ no movió a ningún dron comandable"
    assert (wp >= 0).all() and (wp[:, 0] <= w.W).all() and (wp[:, 1] <= w.H).all(), "δ fuera del campo"
    print("  (c) máscara OK: RETURNING e investigador intactos; comandables movidos %s (clip al campo)" % moved)

    # (d) CANAL DE RECOMPENSA: global == −Δmuertes exacto; componentes por separado; terminal.
    env = DroneTeamEnv(kinds=("lobos",), seed=3)
    obs, info = env.reset()
    assert obs.shape == (N_SEATS * AGENT_OBS_SIZE,)
    zero = np.zeros(N_SEATS * 2, dtype=np.float32)
    tot_global = 0.0; tot_local = np.zeros(N_SEATS)
    while True:
        obs, r, term, trunc, info = env.step(zero)
        tot_global += info["r_global"]; tot_local += info["r_local"]
        ar = info["agent_rewards"]
        assert ar.shape == (N_SEATS,)
        assert np.allclose(ar, info["r_global"] + env._local_coef * info["r_local"]), \
            "agent_rewards != global + local_coef·local"
        if term or trunc:
            break
    wenv = env._world
    assert tot_global == -float(wenv.n_depredadas), "FALLO: Σ r_global != -n_depredadas"
    assert info["ep_severity"] == int(wenv.n_depredadas) and info["ep_deter"] == float(tot_local.sum())
    print("  (d) canal OK: Σ r_global = %.0f == -muertes(%d) | ep_deter=%.0f (por separado, anti-proxy)"
          % (tot_global, wenv.n_depredadas, info["ep_deter"]))

    # (d2) atribución DIRIGIDA: un dron que EMBISTE a un lobo a tiro cobra el crédito de SU puesto.
    w = World(seed=0, wolves_min=1, wolves_max=1); w.reset()
    d0 = int(np.where(w.drone_state == ACTIVE)[0][0])
    w.wolves[0] = w.drones[d0] + np.array([10.0, 0.0]); w.wolf_vel[0] = 0.0
    w.drone_vel[d0] = np.array([15.0, 0.0])                        # embistiendo (aprox. 15 >> 1)
    w.step(None)
    assert w._wolf_scared[0], "el montaje no asustó al lobo"
    ctrl = ResidualDroneCoordinator(w, model=None)
    credit = deter_credit(w, ctrl.seats())
    seat = int(np.where(ctrl.seats() == d0)[0][0])
    assert credit[seat] >= 1.0 and credit.sum() == credit[seat], \
        "FALLO: el crédito de disuasión no fue al puesto del dron que embiste"
    print("  (d2) atribución dirigida OK: lobo expulsado -> crédito al puesto %d (dron %d)" % (seat, d0))

    # (e) CONTACTOS vs CONFIRMADOS (run02, cambio 2 — dirigido): 60 m = contacto y NO confirmado;
    #     cruzar 40 m => confirmado (sale de contactos, grupos disjuntos) y SE RECUERDA al alejarse.
    #     Se ejercita el camino REAL: el latch es el de la barrera interior del coordinador
    #     residual (equipo con memoria v2.8), leído por agent_obs — no un mock.
    w = build_world(2, "lobos"); w.reset()
    ctrl = ResidualDroneCoordinator(w, model=None)
    d0 = int(np.where((w.drone_state == ACTIVE) & ~w.drone_investigating)[0][0])
    w.drones[d0] = np.array([100.0, 100.0])                        # geometría controlada, lejos de la flota
    for dj in np.where(w.drone_state == ACTIVE)[0]:
        if dj != d0:
            w.drones[dj] = np.array([460.0, 460.0])                # el resto de ACTIVE, fuera de todos los radios
    far = np.array([3.0, 3.0])
    for j in range(1, w.n_wolves):
        w.wolves[j] = far + np.array([float(j), 0.0])              # lejos de d0 (>100) y de la flota
    w.wolves[0] = w.drones[d0] + np.array([60.0, 0.0])            # fase 1: CONTACTO sin clasificar
    ctrl.act(w.get_observation())                                  # el latch de la barrera se refresca
    seat0 = int(np.where(ctrl.seats() == d0)[0][0]) if (ctrl.seats() == d0).any() else 0
    lo = ctrl.agent_obs(w)[seat0][:LOCAL_SIZE]
    c0, k0 = lo[OFF_WOLF:OFF_WOLF + 6], lo[OFF_CONF:OFF_CONF + 6]
    assert c0[5] == 1.0, "FALLO (e): lobo a 60 m no aparece como CONTACTO"
    assert k0[5] == 0.0, "FALLO (e): lobo a 60 m (sin cruzar 40) aparece como CONFIRMADO"
    w.wolves[0] = w.drones[d0] + np.array([35.0, 0.0])            # fase 2: cruza r_confirm=40
    ctrl.act(w.get_observation())
    lo = ctrl.agent_obs(w)[seat0][:LOCAL_SIZE]
    c1, k1 = lo[OFF_WOLF:OFF_WOLF + 6], lo[OFF_CONF:OFF_CONF + 6]
    assert k1[5] == 1.0, "FALLO (e): lobo a 35 m no pasó a CONFIRMADOS"
    assert c1[5] == 0.0, "FALLO (e): el confirmado sigue en CONTACTOS (los grupos deben ser disjuntos)"
    w.wolves[0] = w.drones[d0] + np.array([w.r_detect + 60.0, 0.0])   # fase 3: se aleja a >r_detect
    ctrl.act(w.get_observation())
    lo = ctrl.agent_obs(w)[seat0][:LOCAL_SIZE]
    c2, k2 = lo[OFF_WOLF:OFF_WOLF + 6], lo[OFF_CONF:OFF_CONF + 6]
    assert k2[5] == 1.0, "FALLO (e): la confirmación NO se recuerda al alejarse (el latch es memoria)"
    assert c2[5] == 0.0, "FALLO (e): un lobo fuera de r_detect aparece como contacto"
    n_cont = lo[OFF_LGLOBAL + 2] * 5
    n_conf = lo[OFF_LGLOBAL + 3] * 5
    assert abs(n_conf - 1.0) < 1e-6 and abs(n_cont - 0.0) < 1e-6, "contadores local-global mal"
    print("  (e) contactos/confirmados OK: 60 m = contacto puro -> 35 m = confirmado (disjunto) -> "
          "alejado >r_detect = recordado (memoria de equipo); contadores %d/%d" % (n_cont, n_conf))
    print("  OK\n")


if __name__ == "__main__":
    test_formas_y_mascaras()
    test_determinismo()
    test_cap_velocidad()
    test_regla_presa()
    test_canal_recompensa()
    test_mundo_scriptado_intacto()
    test_equivalencia_env_controlador()
    test_shaping_potencial()
    test_residual()
    test_drones()
    print("rl_env_check: TODO OK.")
