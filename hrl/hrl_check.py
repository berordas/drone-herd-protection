"""hrl/hrl_check.py — Verificación de la capa de opciones del jerárquico (Etapa 0).

ENTRA EN LA VERJA desde el Commit C (8º check, junto a los 7 de siempre). Corre DENTRO del
contenedor: `python3 hrl/hrl_check.py`. Asserts al estilo de los demás checks.

  0) UNIDADES de events/behavior_checks (Commit B): geometría de seg_cross · detector
     LURE_COMMIT dirigido (stub geométrico: 3/4 drones en el cono del señuelo + puerta del
     asalto abierta => ON; un dron en la puerta => OFF) · la aserción CRITICAL "ORDEN DEL
     CEBO" salta con un SHOW_START sin latch · clustering de amenazas dirigido (contactos ∪
     confirmados, disjuntos; primario = clúster del ancla; secundario correcto).
  1) MASA vía capa vs ScriptedWolfController (hash SHA256 del estado íntegro por tick,
     episodios COMPLETOS, 12 semillas lobos+mixto de 1 GRUPO de spawn — el camino en que el
     script ES la caza de masa; con 2 grupos MASA difiere POR DISEÑO). Desde el Commit K la
     capa lleva la REGLA DE CAZA OPORTUNISTA (re-target con presa protegida), así que el
     "≡ bit a bit" SOLO vale mientras la regla no dispara: se exige hash IGUAL si no hubo
     RETARGET y hash DISTINTO si lo hubo (la regla hace algo). [K4] lo cierra con drones LEJOS.
  2) CEBO membership="spawn" vs script de dos sectores: misma lógica (igual sii sin RETARGET;
     5 semillas de 2 grupos). El impuesto de interfaz del camino spawn es CERO por construcción
     mientras la regla no dispara (referencia de E0.A(ii)).
  P) AUDITOR DE PATRULLA (adenda post-visionado seed 84, Encargo 1): geometría dirigida sobre un
     World real — anillo de 4 a R=150 (D≈212 > 2·r_detect) => VIOLACIÓN y un lobo que entra por
     el arco ancho sin detectar queda registrado (entrada_no_detectada + cruzo_arco_violacion);
     anillo a R=60 (D≈85 <= 100) => OK; el investigador queda FUERA del anillo auditado; en
     ESCOLTA no se audita (ticks_patrulla no avanza).
  K) REGLA DE CAZA OPORTUNISTA (Commit K; decisión de diseño del dueño): K1 presa viva y
     DESPROTEGIDA (drones lejos) => nunca cambia, ni tras >= 10 re-arranques de opción
     (keep/MASA/Δ90/Δ180 rotando) — persiste también a través de MASA. K2 protegida sostenida
     + alternativa >= 30 m más libre => cambia UNA vez (tras >= GUARD_HOLD), y la siguiente
     respeta el cooldown (RETARGET_BLOCKED entre medias). K3 protegida SIN alternativa mejor
     => no cambia. K4 MASA-forzado con 0 drones cerca (drones LEJOS) ≡ script BIT A BIT y la
     regla no dispara.
  3) ASERCIONES del protocolo sobre 5 episodios CEBO (membership manager, Δ=180°, n>=3):
     sin CRITICAL (orden del cebo, procedencia completa), sin violaciones de contrato
     (pack_prey/pack_prey2 válidos, máscara de comando respetada), OPTION_START presente.
     + DETERMINISMO de eventos: misma seed => misma línea temporal (bit a bit del JSON).
  3b) ADENDA tras STOP-1: CEBO_keep (membership='keep', estrato G) arranca sin CRITICAL ni
     violaciones (señuelo = índice mín, sin gate de rumbo) + el clasificador de ESCOLTA
     PREMATURA etiqueta un caso construido (asalto confirmado primero).
  5) Etapa 1 — manager_obs: builder sobre estado sintético con valores conocidos (Commit G).
  6) Etapa 1 — ManagerEnv (Commit H): determinismo · B_masa ≡ MASA-forzado bit a bit (10 eps) ·
     contratos (un paso = una opción hasta evento; K_MAX; ABORT solo CEBO*).
  4) AllocatorCoordinator con partición 4-0 ≡ ReactiveCoordinator BIT A BIT (5 semillas
     lobos+mixto, episodios completos — incluye relevos de batería e investigaciones).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from baseline import build_world                                   # noqa: E402
from coordinators import ReactiveCoordinator                       # noqa: E402
from world import ACTIVE                                           # noqa: E402
from rl.policy_wolf_controller import SyncedReactiveCoordinator    # noqa: E402

from hrl.behavior_checks import EpisodeAudit, seg_cross            # noqa: E402
from hrl.events import EventTracker                                # noqa: E402
from hrl.options_drone import AllocatorCoordinator, analyze_threats  # noqa: E402
from hrl.options_wolf import DECOY_V2_WAIT_BAND, WolfOptionLayer                       # noqa: E402


# ---------------------------------------------------------------------- #
def _blob(w) -> bytes:
    """Estado íntegro por tick (el mismo criterio que la verificación del Commit A)."""
    parts = [
        w.wolves.tobytes(), w.wolf_vel.tobytes(), w.cows.tobytes(), w.cow_heading.tobytes(),
        w.drones.tobytes(), w.drone_vel.tobytes(), w.drone_waypoint.tobytes(),
        w.cow_alive.tobytes(), w.cow_safe.tobytes(),
        w.calf_alive.tobytes(), w.calf_safe.tobytes(), w.calves.tobytes(),
        w.battery.tobytes(), w.drone_state.tobytes(),
        np.int64([w.step_count, w.n_depredadas, w.pack_prey, w.pack_prey2,
                  int(w.wolf_decoy_released), w.n_refix]).tobytes(),
        w.phase.encode(), (w.pack_prey_kind or "-").encode(),
        (w.pack_prey2_kind or "-").encode(),
    ]
    if w.n_corzos > 0:
        parts += [w.corzos.tobytes(), w.corzo_dismissed.tobytes()]
    return b"".join(parts)


def _run_hashed(seed: int, kind: str, wolf_layer=None, coord_factory=None) -> str:
    w = build_world(seed, kind, wolf_controller=wolf_layer)
    coord = coord_factory(w) if coord_factory is not None else ReactiveCoordinator(w)
    w.reset()
    h = hashlib.sha256()
    h.update(_blob(w))
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        h.update(_blob(w))
        if term or trunc:
            break
    return h.hexdigest()


def _seeds_by_groups(kind: str, n_groups: int, count: int, min_wolves: int = 0) -> list[int]:
    """Primeras `count` semillas cuyo spawn real tiene `n_groups` grupos (probe barato)."""
    out, seed = [], 0
    while len(out) < count:
        w = build_world(seed, kind)
        w.reset()
        if len(w.wolf_group_sizes) == n_groups and w.n_wolves >= min_wolves:
            out.append(seed)
        seed += 1
        if seed > 400:
            raise AssertionError(f"no hay {count} semillas de {n_groups} grupos en {kind}")
    return out


# ---------------------------------------------------------------------- #
class _Stub:
    pass


def _stub_reactive(confirmed=None, anchor=None):
    r = _Stub()
    r.barrier_standoff = 17.32
    r._confirmed = confirmed
    r._anchor = anchor
    return r


def _stub_world(drones, wolves, confirmed_mask=None):
    w = _Stub()
    w.n_wolves = len(wolves)
    w.wolves = np.asarray(wolves, dtype=float)
    w.cows = np.array([[250.0, 250.0]])
    w.cow_alive = np.array([True])
    w.cow_safe = np.array([False])
    w.n_calves = 0
    w.calf_alive = np.zeros(0, dtype=bool)
    w.calf_safe = np.zeros(0, dtype=bool)
    w.calves = np.zeros((0, 2))
    w.drones = np.asarray(drones, dtype=float)
    w.drone_state = np.full(len(drones), ACTIVE)
    w.step_count = 0
    w.phase = "ESCOLTA"
    w.wolf_decoy_released = False
    w.captures = []
    w.wolf_group_sizes = [w.n_wolves]
    w.n_depredadas = 0
    w.r_detect = 100.0
    w.W = w.H = 500.0
    w._contact_bodies = lambda: (w.wolves, np.ones(w.n_wolves, dtype=bool),
                                 np.arange(w.n_wolves))
    return w


def test_0_unidades():
    # 0a — seg_cross: cruce franco / colineal-fuera / paralelas.
    p = lambda *xy: np.array(xy, dtype=float)   # noqa: E731
    assert seg_cross(p(0, 0), p(2, 2), p(0, 2), p(2, 0)), "seg_cross: no vio el cruce"
    assert not seg_cross(p(0, 0), p(1, 0), p(0, 2), p(2, 2)), "seg_cross: falso cruce"
    assert not seg_cross(p(0, 0), p(1, 1), p(2, 0), p(3, 1)), "seg_cross: paralelas cruzan"

    # 0b — LURE_COMMIT dirigido: cebo al ESTE (rumbo 0°), asalto al OESTE (180°).
    east = [[330.0, 250.0], [319.3, 290.0], [319.3, 210.0]]        # 3 en el cono (0°, ±30°)
    north = [250.0, 330.0]                                          # fuera del cono, lejos de la puerta
    w = _stub_world(east + [north], [[330.0, 250.0], [170.0, 250.0]])
    tr = EventTracker(w, _stub_reactive(), decoy_indices=lambda: np.array([0]),
                      assault_indices=lambda: np.array([1]))
    on, data = tr._lure_state()
    assert on and data["drones_cono"] >= 3, f"LURE debía estar ON: {data}"
    w2 = _stub_world(east + [[200.0, 250.0]], [[330.0, 250.0], [170.0, 250.0]])
    tr2 = EventTracker(w2, _stub_reactive(), decoy_indices=lambda: np.array([0]),
                       assault_indices=lambda: np.array([1]))
    on2, data2 = tr2._lure_state()
    assert not on2 and data2["puerta_libre_m"] < 60.0, \
        f"LURE debía estar OFF con un dron en la puerta: {data2}"

    # 0c — la aserción CRITICAL "ORDEN DEL CEBO" salta con SHOW_START sin latch.
    wr = build_world(0, "lobos")
    coord = ReactiveCoordinator(wr)
    wr.reset()
    audit = EpisodeAudit(wr, coord)
    audit.on_boundary()
    audit.tracker.emit(10, "SHOW_START")
    rec = audit.finalize()
    assert any("ORDEN DEL CEBO" in c for c in rec["critical"]), \
        "SHOW_START sin STAGED no disparó la aserción CRITICAL"

    # 0d — clustering de amenazas: contactos ∪ confirmados (disjuntos), primario = ancla.
    ws = _stub_world([[300.0, 250.0], [260.0, 260.0]],
                     [[350.0, 250.0], [340.0, 270.0], [250.0, 350.0]])
    react = _stub_reactive(confirmed=np.array([True, False, False]), anchor=0)
    info = analyze_threats(ws, react)
    assert info["pts"].shape[0] == 3, f"amenazas: {info['pts'].shape[0]} != 3"
    assert int(info["is_confirmed"].sum()) == 1, "el confirmado debe salir de contactos"
    assert len(info["clusters"]) == 2, f"clusters: {len(info['clusters'])} != 2"
    prim = info["clusters"][info["primario"]]
    assert np.any(info["wolf_idx"][prim] == 0), "el primario no contiene al ancla"
    sec = info["clusters"][info["secundario"]]
    assert len(sec) == 1 and int(info["wolf_idx"][sec[0]]) == 2, "secundario incorrecto"
    try:
        AllocatorCoordinator(wr, particion=(3, 2))
        raise AssertionError("partición 3+2 != 4 no lanzó ValueError")
    except ValueError:
        pass
    print("  [0] unidades events/behavior_checks/clustering: OK")


class _FarCoordinator:
    """Drones LEJOS (test de la regla de caza): comanda a TODOS los drones a la esquina más
    alejada del rebaño y de la manada en t=0 (0 drones cerca de ninguna presa => la regla de
    caza nunca dispara). Sincroniza la capa de opciones como SyncedReactiveCoordinator."""

    def __init__(self, world):
        self.world = world
        self._corner = None

    def act(self, observation=None):
        w = self.world
        if hasattr(w.wolf_controller, "refresh"):
            w.wolf_controller.refresh(w)
        if self._corner is None:
            herd_c = w.cows.mean(axis=0)
            wolf_c = w.wolves.mean(axis=0) if w.n_wolves else herd_c
            corners = np.array([[5.0, 5.0], [w.W - 5.0, 5.0], [5.0, w.H - 5.0], [w.W - 5.0, w.H - 5.0]])
            score = np.minimum(np.linalg.norm(corners - herd_c, axis=1),
                               np.linalg.norm(corners - wolf_c, axis=1))
            self._corner = corners[int(np.argmax(score))]
        return np.tile(self._corner, (w.n_drones, 1))


def _run_hashed_events(seed, kind, wolf_layer, coord_factory):
    """Como _run_hashed pero con la capa: devuelve (hash, eventos de la capa)."""
    w = build_world(seed, kind, wolf_controller=wolf_layer)
    coord = coord_factory(w)
    w.reset()
    h = hashlib.sha256()
    h.update(_blob(w))
    evs = []
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        h.update(_blob(w))
        evs += wolf_layer.pop_events()
        if term or trunc:
            break
    return h.hexdigest(), evs


def test_1_masa_bit_a_bit():
    n = n_rt = 0
    for kind in ("lobos", "mixto"):
        for s in _seeds_by_groups(kind, 1, 6):
            ha = _run_hashed(s, kind)
            hb, evs = _run_hashed_events(s, kind, WolfOptionLayer(option=("MASA", {})),
                                         lambda w: SyncedReactiveCoordinator(w))
            rt = sum(e["ev"] == "RETARGET" for e in evs)
            if rt == 0:
                assert ha == hb, f"MASA vía capa != scriptado sin RETARGET (seed {s} {kind})"
            else:
                assert ha != hb, f"RETARGET sin efecto en el estado (seed {s} {kind})"
                n_rt += 1
            n += 1
    print(f"  [1] MASA vía capa ≡ scriptado BIT A BIT salvo regla de caza: {n} episodios de 1 grupo "
          f"OK ({n_rt} con RETARGET, distintos como debe)")


def test_2_cebo_spawn_bit_a_bit():
    n = n_rt = 0
    for kind, count in (("lobos", 3), ("mixto", 2)):
        for s in _seeds_by_groups(kind, 2, count):
            ha = _run_hashed(s, kind)
            hb, evs = _run_hashed_events(s, kind, WolfOptionLayer(option=("CEBO", {"membership": "spawn"})),
                                         lambda w: SyncedReactiveCoordinator(w))
            rt = sum(e["ev"] == "RETARGET" for e in evs)
            if rt == 0:
                assert ha == hb, f"CEBO/spawn vía capa != script 2 sectores sin RETARGET (seed {s} {kind})"
            else:
                assert ha != hb, f"RETARGET sin efecto en el estado (seed {s} {kind})"
                n_rt += 1
            n += 1
    print(f"  [2] CEBO membership=spawn ≡ script BIT A BIT salvo regla de caza: {n} episodios de 2 grupos "
          f"OK ({n_rt} con RETARGET)")


def _s1_episode(seed):
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs = []
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if term or trunc:
            break
    show = [e for e in evs if e["ev"] == "SHOW_START"]
    align = [e for e in evs if e["ev"] == "ALIGN_END"]
    return {"seed": seed, "sev": int(w.n_depredadas), "show_t": (show[0]["t"] if show else None),
            "err_deg": (show[0]["err_rumbo_deg"] if show else None),
            "align": (align[0]["causa"] if align else None), "ticks": int(w.step_count),
            "staged_causa": (show[0].get("staged_causa") if show else None),
            "stalls": int(layer.n_stalls)}


def test_S1_gate_mejor_esfuerzo():
    """Commit S1 (adjudicación VERIF-0 del dueño): los 9 seeds de INTERBLOQUEO de verif0
    (B_oracle en S: CEBO Δ90 fijo vs Reactive-estática — 9/20 episodios ESTACIONADOS sin show,
    máx 23.570 ticks, sev 0) llegan TODOS a show — el gate de rumbo ya no bloquea: la fase de
    alineación termina por tolerancia/sin-progreso/techo y después manda el guion v3.3 (staged
    por PROXIMIDAD => show, el camino sano de B_spawn). Reporta sev por episodio (la severidad
    con la jugada JUGADA — la tabla de la adjudicación). [2] cubre que B_spawn sigue bit a bit."""
    import multiprocessing as mp
    seeds = [3, 5, 9, 14, 18, 24, 35, 36, 55]
    with mp.get_context("fork").Pool(len(seeds)) as pool:
        rows = pool.map(_s1_episode, seeds, chunksize=1)
    for r in rows:
        assert r["show_t"] is not None, f"S1: seed {r['seed']} SIGUE sin show (interbloqueo)"
        assert r["align"] is not None, f"S1: seed {r['seed']} sin ALIGN_END"
        print(f"    seed {r['seed']:>2d}: show t={r['show_t']:>5d} (align={r['align']:<12s} "
              f"err={r['err_deg']}° staged={r['staged_causa']} stalls={r['stalls']}) "
              f"sev={r['sev']} ticks={r['ticks']}")
    print(f"  [S1] gate mejor-esfuerzo: 9/9 seeds de interbloqueo con show (antes 0/9); "
          f"sev={[r['sev'] for r in rows]}")


def test_S2_abort_solo_preshow():
    """Commit S2 (adjudicación VERIF-0 del dueño): ABORT_BAIT_FAILED solo es evaluable ANTES de
    wolf_decoy_released — un cebo que ya mostró y soltó el asalto no ha "fallado" (post-show la
    condición se mantenía cierta de CONTINUO y el ABORT degeneraba en metrónomo de 50 ticks:
    verif0 s67/s86/s98 con d2≈1-6 m). Dirigido: con la condición del ABORT FORZADA a cierta,
    pre-show aborta a los ~ABORT_GRACE_TICKS; con el show ya latcheado NO aborta (techo)."""
    from hrl.manager_env import ManagerEnv, ABORT_GRACE_TICKS
    s = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    env = ManagerEnv(kinds=("lobos",), seed=0, k_max=250)
    env.reset_to(s, "lobos")
    env._bait_failed = lambda: True                     # condición del ABORT SIEMPRE cierta
    _o, _r, _t, _tr, i1 = env.step(2)                   # CEBO d90 pre-show: aborta en la gracia
    assert i1["event"] == "ABORT_BAIT_FAILED" and i1["ticks"] == ABORT_GRACE_TICKS, i1
    env2 = ManagerEnv(kinds=("lobos",), seed=0, k_max=250)
    env2.reset_to(s, "lobos")
    env2._bait_failed = lambda: True
    env2._world.wolf_decoy_released = True              # show YA disparado (latch monótono)
    _o, _r, _t, _tr, i2 = env2.step(2)
    assert i2["event"] != "ABORT_BAIT_FAILED", i2
    print(f"  [S2] ABORT solo PRE-show: pre aborta a {i1['ticks']} ticks; post-show no aborta "
          f"(termina {i2['event']} a {i2['ticks']} ticks)")


def test_S3_censura():
    """MÉTRICA DE CENSURA (adjudicación VERIF-0 del dueño; estándar en todas las tablas): hitos
    de la jugada (t_staged/t_show/t_suelta) en la capa + info['jugada'] del ManagerEnv, con orden
    temporal coherente y completa := show ∧ suelta — sev 0 sin jugar != sev 0 jugando y fallando."""
    from hrl.manager_env import ManagerEnv
    s = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    env = ManagerEnv(kinds=("lobos",), seed=0)
    obs, info = env.reset_to(s, "lobos")
    done = False
    while not done:
        obs, r, term, trunc, info = env.step(2)              # CEBO d90 fijo (brazo de celda)
        done = term or trunc
    j = info["jugada"]
    assert set(j) == {"t_staged", "t_show", "t_suelta", "t_strike", "completa"}, j
    if j["t_show"] is not None and j["t_staged"] is not None:
        assert j["t_staged"] <= j["t_show"], j
    if j["t_suelta"] is not None:
        assert j["t_show"] is not None and j["t_show"] <= j["t_suelta"], j
    if j["t_strike"] is not None:
        assert j["t_suelta"] is not None and j["t_suelta"] <= j["t_strike"], j
    assert j["completa"] == (j["t_show"] is not None and j["t_suelta"] is not None), j
    print(f"  [S3] censura (hitos de jugada): {j} (CEBO d90 fijo, seed {s}, "
          f"sev {info['ep_sev']})")


def test_QC_coste_deliberacion():
    """Commit Q (plan M1'''' del dueño): COSTE DE DELIBERACIÓN — una decisión tomada tras
    INTERRUPCIÓN (ABORT) que CAMBIA de opción paga DELIB_COST; re-elegir la misma opción tras
    ABORT o cambiar tras terminal NATURAL (K_MAX) es gratis. Los baselines re-eligen la misma
    accion => pagan 0 (escalera justa). Dirigido con la condición del ABORT forzada (pre-show).
    La sev (n_depredadas) queda SIEMPRE sin coste."""
    from hrl.manager_env import ManagerEnv, DELIB_COST
    s = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    env = ManagerEnv(kinds=("lobos",), seed=0, k_max=200)
    env.reset_to(s, "lobos")
    env._bait_failed = lambda: True
    _o, r1, _t, _tr, i1 = env.step(2)                    # 1ª decisión: sin previo => sin coste
    assert i1["event"] == "ABORT_BAIT_FAILED" and abs(r1 - round(r1)) < 1e-9, (r1, i1)
    _o, r2, _t, _tr, i2 = env.step(2)                    # MISMA opción tras ABORT: gratis
    assert i2["event"] == "ABORT_BAIT_FAILED" and abs(r2 - round(r2)) < 1e-9, (r2, i2)
    _o, r3, _t, _tr, i3 = env.step(3)                    # CAMBIO tras ABORT: paga DELIB_COST
    assert abs((r3 - round(r3)) + DELIB_COST) < 1e-9, r3
    env2 = ManagerEnv(kinds=("lobos",), seed=0, fixed_k=60)
    env2.reset_to(s, "lobos")
    _o, q1, _t, _tr, j1 = env2.step(2)
    assert j1["event"] == "K_MAX", j1
    _o, q2, _t, _tr, j2 = env2.step(3)                   # cambio tras terminal NATURAL: gratis
    assert abs(q2 - round(q2)) < 1e-9, q2
    print(f"  [QC] coste de deliberación {DELIB_COST}: cambio tras ABORT paga; misma opción tras "
          f"ABORT y cambio tras K_MAX gratis")


def test_QB_tripwire_show():
    """Q-bis (plan M1''''; DEGRADADO a TRIPWIRE tras S1): asalto STAGED 400 ticks acumulados sin
    show => show FORZADO + evento STALL (cierre de GUION, no de decisión). Dirigido: la fase de
    alineación se bloquea artificialmente (parche de instancia) para que el gate jamás termine;
    el tripwire debe disparar a los 400 ticks staged y la jugada continuar por el flanco
    SHOW_START de siempre."""
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
    layer._align_update = lambda w, s2: None             # la alineación JAMÁS termina (dirigido)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs = []
    for _ in range(8000):
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if w.wolf_decoy_released or t or tr:
            break
    stall = [e for e in evs if e["ev"] == "STALL"]
    show = [e for e in evs if e["ev"] == "SHOW_START"]
    assert stall and show, (stall, show, int(w.step_count))
    assert layer.n_stalls == 1 and stall[0]["t"] >= 400, (layer.n_stalls, stall)
    assert not stall[0]["align_done"], stall
    print(f"  [QB] tripwire del show: STALL a t={stall[0]['t']} (400 staged, alineación "
          f"bloqueada) y show forzado a t={show[0]['t']}")


def test_S3_staged_meseta():
    """Commit S3 (firma del hallazgo MESETA; 2ª aplicación de la plantilla S1): la cláusula de
    A-TIRO del staged pasa a MEJOR-ESFUERZO — asalto ESTACIONADO en el anillo con d_prey en
    meseta (mejora < STAGED_PLATEAU_M en STAGED_PLATEAU_TICKS) => staged por readiness
    posicional (causa "meseta") => show por el guion. Seed 14 (el del interbloqueo por meseta)
    muestra SIN tripwire; un seed sano (9) conserva su mecanismo a_tiro. La composición
    a_tiro/meseta va en las celdas (SHOW_START.staged_causa)."""
    import multiprocessing as mp
    with mp.get_context("fork").Pool(2) as pool:
        r14, r9 = pool.map(_s1_episode, [14, 9], chunksize=1)
    assert r14["show_t"] is not None, "S3: seed 14 sigue sin show (meseta no cerrada)"
    assert r14["staged_causa"] == "meseta", r14
    assert r14["stalls"] == 0, ("S3: el rescate debe ser del guion (meseta), no del tripwire", r14)
    assert r9["show_t"] is not None and r9["staged_causa"] == "a_tiro", r9
    print(f"  [S3b] staged mejor-esfuerzo: seed 14 muestra por MESETA (t={r14['show_t']}, "
          f"stalls 0); seed 9 conserva a_tiro (t={r9['show_t']})")


def test_V2_senuelo_directo():
    """SEÑUELO v2 (Encargo 2, opción A del dueño): aproximación RECTA al centroide con ESPERA en
    el borde de merodeo — sin bordeo perimetral. Dirigido (CEBO d180 en S, pre-show): el señuelo
    se ACERCA (>60 m o hasta el borde), NO orbita (barrido angular < 45°; decoy_prowl orbitaba
    por diseño) y jamás baja del anillo de expulsión pre-show. spawn ≡ script queda en [2]."""
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 180.0, "hold": 50.0}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    def herd_c():
        return w.cows[w.cow_alive].mean(axis=0)
    d0 = float(np.linalg.norm(w.wolves[0] - herd_c()))
    angs, dmins, dcs = [], [], []
    for _ in range(4000):
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if w.wolf_decoy_released or t or tr:
            break
        v = w.wolves[0] - herd_c()
        angs.append(float(np.arctan2(v[1], v[0])))
        dcs.append(float(np.linalg.norm(v)))
        act = w.drones[w.drone_state == ACTIVE]
        if act.shape[0]:
            dmins.append(float(np.linalg.norm(act - w.wolves[0], axis=1).min()))
    assert len(angs) > 50, "ventana pre-show demasiado corta"
    barrido = float(np.rad2deg(np.abs(np.unwrap(np.asarray(angs)) - angs[0]).max()))
    acercamiento = d0 - min(dcs)
    borde = bool(dmins) and min(dmins) <= w.decoy_hold_dist + DECOY_V2_WAIT_BAND + 5.0
    assert acercamiento > 60.0 or borde, (acercamiento, min(dmins) if dmins else None)
    assert barrido < 45.0, f"el señuelo v2 no debe bordear: barrido {barrido:.0f}°"
    # Los PICOS transitorios bajo el hold con drones EN MOVIMIENTO (flyby de un relevo, barrera
    # que avanza) son física — el mismo caso del blindaje v3.1; el anillo de huida los resuelve.
    # Cota laxa: jamás una penetración PROFUNDA (cerca de la expulsión a <=20).
    assert not dmins or min(dmins) > 60.0, \
        f"penetración profunda pre-show: dmin {min(dmins):.1f}"

    # Unidades de la POLÍTICA del señuelo v2 (estado sintético, dron QUIETO): lejos => carga
    # RECTA al centroide; en la banda de espera => desired 0 EXACTO; dentro del hold => huida
    # radial pura del dron.
    class _WS:
        pass
    ws = _WS()
    ws.decoy_hold_dist = 130.0
    ws.cows = np.array([[300.0, 300.0]])
    ws.cow_alive = np.array([True])
    ws.W = ws.H = 600.0
    ws.drones = np.array([[250.0, 300.0]])
    ws.drone_state = np.array([0])                       # ACTIVE
    lay2 = WolfOptionLayer(option=("CEBO", {}))
    sel = np.array([0])
    des = np.zeros((1, 2))
    ws.wolves = np.array([[20.0, 300.0]])                # dmin=230: carga recta (+x)
    lay2._decoy_direct(ws, sel, des)
    assert des[0, 0] > 0.9 and abs(des[0, 1]) < 1e-9, des
    ws.wolves = np.array([[115.0, 300.0]])               # dmin=135 en [130,140): ESPERA (0 exacto)
    des = np.zeros((1, 2)); lay2._decoy_direct(ws, sel, des)
    assert np.allclose(des, 0.0), des
    ws.wolves = np.array([[130.0, 300.0]])               # dmin=120 < 130: HUIDA radial (-x)
    des = np.zeros((1, 2)); lay2._decoy_direct(ws, sel, des)
    assert des[0, 0] < -0.9 and abs(des[0, 1]) < 1e-9, des
    print(f"  [V2] señuelo directo: se acercó {acercamiento:.0f} m (d0 {d0:.0f}), barrido "
          f"{barrido:.0f}° (<45), dmin {min(dmins) if dmins else None:.1f} (picos por drones en "
          f"movimiento tolerados) — unidades carga/espera/huida OK")


class _RotatingManager:
    """Re-arranca la opción cada `period` ticks rotando la secuencia (todas distintas entre sí =>
    cada cambio es un re-arranque real de la capa)."""

    def __init__(self, sequence, period):
        self.sequence, self.period = sequence, int(period)

    def decide(self, world, layer):
        return self.sequence[(int(world.step_count) // self.period) % len(self.sequence)]


def _prey_ok(w, kind, idx):
    if idx < 0:
        return False
    return bool(w.calf_alive[idx] and not w.calf_safe[idx]) if kind == "calf" \
        else bool(w.cow_alive[idx] and not w.cow_safe[idx])


def test_K1_persistencia_sin_proteccion():
    """K1: presa del asalto viva y DESPROTEGIDA (drones lejos) => nunca cambia, ni tras >= 10
    re-arranques de opción (keep -> MASA -> Δ90 -> MASA -> Δ180 -> ...): la capa la RECUERDA y la
    RESTAURA en cada arranque de CEBO (también a través de MASA, que por contrato pone pack_prey2=-1)."""
    seq = [("CEBO", {"membership": "keep", "hold": 50.0}), ("MASA", {}),
           ("CEBO", {"delta_deg": 90.0, "hold": 50.0}), ("MASA", {}),
           ("CEBO", {"delta_deg": 180.0, "hold": 50.0})]
    n_eps = n_starts_alive = 0
    for s in _seeds_by_groups("lobos", 1, 3, min_wolves=3):
        layer = WolfOptionLayer(manager=_RotatingManager(seq, 30))
        w = build_world(s, "lobos", wolf_controller=layer)
        coord = _FarCoordinator(w)
        w.reset()
        remembered = None; starts = 0; changes_bad = []
        while True:
            _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
            for e in layer.pop_events():
                assert e["ev"] != "RETARGET", "RETARGET con drones lejos"
                if e["ev"] == "OPTION_START" and e["option"] == "CEBO":
                    starts += 1
                    cur = (w.pack_prey2_kind, int(w.pack_prey2))
                    if remembered is not None and _prey_ok(w, *remembered) \
                            and remembered != (w.pack_prey_kind, int(w.pack_prey)):
                        if cur != remembered:
                            changes_bad.append((int(w.step_count), remembered, cur))
                        n_starts_alive += 1
                    if cur[1] >= 0:
                        remembered = cur
            if w.step_count > 900 or term or trunc:
                break
        assert not changes_bad, f"la presa del asalto cambió en re-arranque sin perderse (seed {s}): {changes_bad}"
        assert starts >= 10, f"pocos re-arranques ({starts}) en seed {s}"
        n_eps += 1
    assert n_starts_alive >= 10, f"pocos re-arranques con presa viva: {n_starts_alive}"
    print(f"  [K1] presa del asalto PERSISTE sin protección: {n_eps} episodios, "
          f"{n_starts_alive} re-arranques con presa viva sin cambio OK")


class _GuardCoordinator:
    """Dron 0 PEGADO a la presa del paquete (pack_prey) cada tick; el resto lejos."""

    def __init__(self, world, corner):
        self.world, self.corner = world, np.asarray(corner, float)

    def act(self, observation=None):
        w = self.world
        if hasattr(w.wolf_controller, "refresh"):
            w.wolf_controller.refresh(w)
        wp = np.tile(self.corner, (w.n_drones, 1))
        if w.pack_prey >= 0:
            wp[0] = w._prey_pos_of(int(w.pack_prey), w.pack_prey_kind)
        return wp


def _guard_world(seed):
    """Escenario dirigido sobre un mundo real (lobos, 1 grupo, sin terneros, n>=2): la presa del
    paquete en su sitio; las demás adultas reubicadas a ~80-100 m al ESTE (más libres con el
    guardián encima de la presa); ESCOLTA latcheada (sin reflejo de investigación: el dron 0 no
    abandona la presa); baterías llenas (sin relevos en la ventana del test); drones 1-3 lejos."""
    layer = WolfOptionLayer(option=("MASA", {}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    w.reset()
    w.battery[:] = 1.0
    w.phase = "ESCOLTA"
    p0 = w.cows[int(w.pack_prey)].copy()
    k = 0
    for i in range(w.n_cows):
        if i == int(w.pack_prey):
            continue
        w.cows[i] = p0 + np.array([80.0 + 5.0 * k, 12.0 * (k % 3) - 12.0])
        k += 1
    w.drones[0] = p0.copy(); w.drone_waypoint[0] = p0.copy(); w.drone_vel[0] = 0.0
    w.drone_state[0] = ACTIVE
    return w, layer


def _find_guard_seed():
    for s in range(200):
        w = build_world(s, "lobos"); w.reset()
        if len(w.wolf_group_sizes) == 1 and w.n_calves == 0 and w.n_wolves >= 2 \
                and w.pack_prey_kind == "adult" and w.pack_prey >= 0:
            return s
    raise AssertionError("sin semilla para el escenario del guardián")


def test_K2_retarget_protegida_y_cooldown():
    """K2: presa PROTEGIDA de forma sostenida (dron 0 encima) + alternativa >= RETARGET_MARGIN más
    libre => re-target UNA vez (no antes de GUARD_HOLD ticks de protección), y con el guardián
    siguiendo a la nueva presa, el siguiente re-target respeta RETARGET_COOLDOWN (y entre medias
    se registra RETARGET_BLOCKED por cooldown)."""
    from hrl.options_wolf import GUARD_HOLD, RETARGET_COOLDOWN
    s = _find_guard_seed()
    w, layer = _guard_world(s)
    coord = _GuardCoordinator(w, (w.W - 5.0, 5.0))
    evs = []
    prey0 = (w.pack_prey_kind, int(w.pack_prey))
    t = 0
    while t < 600:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        t += 1
        if term or trunc:
            break
    rts = [e for e in evs if e["ev"] == "RETARGET"]
    bls = [e for e in evs if e["ev"] == "RETARGET_BLOCKED"]
    assert len(rts) >= 1, f"la regla no re-apuntó con presa protegida (seed {s}): {evs[:5]}"
    r0 = rts[0]
    assert r0["t"] >= GUARD_HOLD and r0["causa"] == "protegida" and r0["quien"] == "paquete", r0
    assert tuple(r0["de"]) == prey0 and r0["d_cand"] >= r0["d_cur"] + 30.0, r0
    assert r0["guard_ticks"] >= GUARD_HOLD, r0
    # primer re-target: UNO solo en su ventana de cooldown
    in_window = [e for e in rts if r0["t"] < e["t"] < r0["t"] + RETARGET_COOLDOWN]
    assert not in_window, f"re-target dentro del cooldown: {in_window}"
    if len(rts) >= 2:
        assert rts[1]["t"] - r0["t"] >= RETARGET_COOLDOWN, (rts[0], rts[1])
    assert any(r0["t"] < b["t"] < r0["t"] + RETARGET_COOLDOWN for b in bls), \
        f"sin RETARGET_BLOCKED por cooldown con el guardián sobre la nueva presa: {bls}"
    assert layer.n_retargets == len(rts)
    print(f"  [K2] re-target con presa protegida: 1º a t={r0['t']} (guard {r0['guard_ticks']} ticks, "
          f"{r0['d_cur']}->{r0['d_cand']} m), {len(rts)} en 600 ticks, cooldown respetado, "
          f"{len(bls)} BLOCKED: OK")


def test_K3_protegida_sin_alternativa():
    """K3: presa protegida pero SIN alternativa >= RETARGET_MARGIN más libre (todas las reses
    juntas, el guardián encima del grupo) => no cambia nunca."""
    s = _find_guard_seed()
    layer = WolfOptionLayer(option=("MASA", {}))
    w = build_world(s, "lobos", wolf_controller=layer)
    w.reset()
    w.battery[:] = 1.0
    w.phase = "ESCOLTA"
    p0 = w.cows[int(w.pack_prey)].copy()
    for i in range(w.n_cows):            # todas a <= 10 m de la presa: ninguna 30 m más libre
        w.cows[i] = p0 + np.array([6.0 * ((i % 3) - 1), 6.0 * ((i // 3) - 0.5)])
    w.drones[0] = p0.copy(); w.drone_waypoint[0] = p0.copy(); w.drone_vel[0] = 0.0
    w.drone_state[0] = ACTIVE
    coord = _GuardCoordinator(w, (w.W - 5.0, 5.0))
    prey0 = (w.pack_prey_kind, int(w.pack_prey))
    evs = []; protected_ticks = 0
    for t in range(400):
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if np.linalg.norm(w.drones[0] - w.cows[prey0[1]]) <= 25.0:
            protected_ticks += 1
        if term or trunc or not _prey_ok(w, *prey0):
            break
    assert protected_ticks >= 100, f"el escenario no protegió a la presa ({protected_ticks} ticks)"
    assert not [e for e in evs if e["ev"] == "RETARGET"], "re-target sin alternativa mejor"
    assert (w.pack_prey_kind, int(w.pack_prey)) == prey0 or not _prey_ok(w, *prey0)
    print(f"  [K3] protegida ({protected_ticks} ticks) sin alternativa mejor: sin re-target OK")


def test_K4_masa_drones_lejos_bit_a_bit():
    """K4: MASA-forzado con 0 drones cerca (drones LEJOS) ≡ ScriptedWolfController BIT A BIT y la
    regla no dispara (el ≡ de siempre, en el único régimen en que sigue aplicando)."""
    n = 0
    for kind in ("lobos", "mixto"):
        for s in _seeds_by_groups(kind, 1, 3):
            ha = _run_hashed(s, kind, coord_factory=lambda w: _FarCoordinator(w))
            hb, evs = _run_hashed_events(s, kind, WolfOptionLayer(option=("MASA", {})),
                                         lambda w: _FarCoordinator(w))
            assert not [e for e in evs if e["ev"] == "RETARGET"], f"RETARGET con drones lejos (seed {s})"
            assert ha == hb, f"MASA vía capa != scriptado con drones lejos (seed {s} {kind})"
            n += 1
    print(f"  [K4] MASA con drones LEJOS ≡ scriptado BIT A BIT (regla sin disparar): {n} episodios OK")


def _run_cebo_audit(seed: int) -> dict:
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 180.0}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    audit = EpisodeAudit(w, coord, wolf_controller=layer, meta={"seed": seed},
                         decoy_indices=layer.decoy_indices,
                         assault_indices=layer.assault_indices, option_name="CEBO")
    while True:
        audit.on_boundary()
        wp_before = w.drone_waypoint.copy()
        wp = coord.act(w.get_observation())
        audit.check_command(wp_before, wp)
        _o, _r, term, trunc, _i = w.step(wp)
        audit.after_step()
        if term or trunc:
            break
    return audit.finalize()


def test_3_aserciones_y_determinismo():
    seeds = _seeds_by_groups("lobos", 1, 3, min_wolves=3) + \
        _seeds_by_groups("lobos", 2, 2, min_wolves=3)
    recs = []
    for s in seeds:
        rec = _run_cebo_audit(s)
        assert not rec["critical"], f"CRITICAL en seed {s}: {rec['critical']}"
        assert not rec["violations"], f"contrato violado en seed {s}: {rec['violations']}"
        assert any(e["ev"] == "OPTION_START" for e in rec["events"]), "sin OPTION_START"
        t_staged = next((e["t"] for e in rec["events"] if e["ev"] == "STAGED"), None)
        t_show = next((e["t"] for e in rec["events"] if e["ev"] == "SHOW_START"), None)
        if t_show is not None:
            assert t_staged is not None and t_show >= t_staged, "orden del cebo"
        recs.append(rec)
    # Determinismo de la línea temporal: misma seed => mismos eventos, bit a bit.
    again = _run_cebo_audit(seeds[0])
    assert json.dumps(recs[0]["events"], sort_keys=True) == \
        json.dumps(again["events"], sort_keys=True), "eventos NO deterministas"
    print(f"  [3] aserciones del protocolo en {len(seeds)} episodios CEBO + "
          f"determinismo de eventos: OK")


def test_3b_cebo_keep_y_prematura():
    """Adenda tras STOP-1: CEBO_keep (membership='keep') en el estrato G — señuelo = índice
    mín (el singleton del spawn), asalto en su rumbo actual: sin gate de rumbo, arranca sin
    CRITICAL ni violaciones y la presa 2 se fija con la membresía del manager. Además el
    clasificador de ESCOLTA prematura etiqueta correctamente un caso construido (ESCOLTA
    antes del show con un lobo del asalto confirmado primero)."""
    seeds = _seeds_by_groups("lobos", 2, 2, min_wolves=3)
    for s in seeds:
        layer = WolfOptionLayer(option=("CEBO", {"membership": "keep"}))
        w = build_world(s, "lobos", wolf_controller=layer)
        coord = SyncedReactiveCoordinator(w)
        w.reset()
        audit = EpisodeAudit(w, coord, wolf_controller=layer, meta={"seed": s},
                             decoy_indices=layer.decoy_indices,
                             assault_indices=layer.assault_indices, option_name="CEBO_keep")
        while True:
            audit.on_boundary()
            wp = coord.act(w.get_observation())
            _o, _r, term, trunc, _i = w.step(wp)
            audit.after_step()
            if w.step_count == 3:
                assert layer.decoy_indices().tolist() == [0], "keep: señuelo debe ser el índice 0"
                assert layer._theta_asa is None, "keep: no debe haber objetivo de rumbo"
                assert layer._bearing_ok(w, layer.assault_indices()), "keep: gate de rumbo activo"
            if term or trunc:
                break
        rec = audit.finalize()
        assert not rec["critical"] and not rec["violations"], (rec["critical"], rec["violations"])
    # Clasificador de ESCOLTA prematura (caso construido sobre el estado real del mundo).
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 180.0}))
    w = build_world(seeds[0], "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    audit = EpisodeAudit(w, coord, wolf_controller=layer, meta={"seed": seeds[0]},
                         decoy_indices=layer.decoy_indices,
                         assault_indices=layer.assault_indices, option_name="CEBO")
    layer.refresh(w)
    audit.on_boundary()
    conf = np.zeros(w.n_wolves, dtype=bool)
    conf[1] = True                                        # un lobo del ASALTO confirmado
    coord.inner._confirmed = conf
    coord.inner._conf_step = int(w.step_count)
    w.phase = "ESCOLTA"                                   # ESCOLTA antes del show
    audit.on_boundary()
    assert audit.premature is not None, "no clasificó la ESCOLTA prematura"
    assert audit.premature["quien"] == "asalto" and audit.premature["primer_confirmado"] == 1, \
        audit.premature
    assert any(e["ev"] == "ESCOLTA_PREMATURA" for e in audit.tracker.events)
    print(f"  [3b] CEBO_keep sin CRITICAL en {len(seeds)} episodios G + clasificador de "
          f"ESCOLTA prematura: OK")


def test_5_manager_obs():
    """Etapa 1 (Commit G): builder de la OBS del manager sobre un estado SINTÉTICO con valores
    conocidos — layout 35, manada (n, clústeres, separación, menor, dist), rebaño/reloj, puertas
    por octante, rasgos del cebo (cono del señuelo + progreso), contexto one-hot."""
    from hrl.manager_obs import (MANAGER_OBS_SIZE, EV_MUERTE, build_manager_obs, wolf_clusters,
                                 gate_distances)
    w = build_world(0, "lobos"); w.reset()
    # Estado sintético: rebaño = 1 vaca en (250,250); 3 lobos: 2 al ESTE (0°) a 100 m, 1 al OESTE
    # (180°) a 200 m; 4 ACTIVE: 3 al este a 60 m (en el cono del señuelo = lobo 2 al oeste? no: el
    # señuelo será el lobo 2 (oeste) -> 0 ACTIVE en su cono), 1 al norte.
    w.cows[:] = np.array([250.0, 250.0]); w.cow_alive[:] = False; w.cow_alive[0] = True; w.cow_safe[:] = False
    w.calf_alive[:] = False
    w.wolves = np.array([[350.0, 250.0], [352.0, 262.0], [50.0, 250.0]])[: w.n_wolves] if w.n_wolves >= 3 \
        else np.array([[350.0, 250.0], [352.0, 262.0], [50.0, 250.0]])
    w.n_wolves = 3
    w.wolf_vel = np.zeros((3, 2))
    w.drone_state[:] = 3                           # READY (aparcados)
    w.drones[:] = 1e4
    for i, p_ in enumerate([[310.0, 250.0], [310.0, 262.0], [310.0, 238.0], [250.0, 310.0]]):
        w.drone_state[i] = ACTIVE; w.drones[i] = p_
    w.phase = "ESCOLTA"; w.n_depredadas = 2
    herd_c = np.array([250.0, 250.0])
    cl, _ang = wolf_clusters(w, herd_c)
    assert len(cl) == 2 and sorted(len(c) for c in cl) == [1, 2], f"clusters: {[len(c) for c in cl]}"
    ctx = {"option": 1, "last_event": EV_MUERTE, "decision_idx": 3,
           "decoy_idx": np.array([2]), "active_c_prev": np.array([270.0, 265.0])}
    o = build_manager_obs(w, ctx)
    assert o.shape == (MANAGER_OBS_SIZE,) and o.dtype == np.float32
    assert abs(o[0] - 3 / 5) < 1e-6, "n/5"
    assert abs(o[1] - 1.0) < 1e-6, "2 clusters -> 1.0"
    # centroide del clúster este = (351, 256) -> rumbo 3.4°; oeste 180° -> separación 176.6°/180
    assert abs(o[2] - (180.0 - np.degrees(np.arctan2(6.0, 101.0))) / 180.0) < 1e-3, \
        f"separación angular /π, got {o[2]}"
    assert abs(o[3] - 1 / 3) < 1e-6, "menor/n = 1/3"
    assert abs(o[4] - ((100 + np.hypot(102, 12) + 200) / 3) / 250.0) < 1e-3, "dist media /250"
    assert abs(o[5] - 1 / 6) < 1e-6 and o[6] == 0.0 and o[8] == 1.0 and abs(o[9] - 2 / 6) < 1e-6
    # puertas: octante 0 (este): puerta en (250+0+17.32, 250) -> ACTIVE más cercano (310,250) a 42.68
    g = gate_distances(w, w.cows[:1], herd_c)
    assert abs(g[0] - 42.68 / 250.0) < 1e-2, f"puerta este {g[0]*250:.1f}"
    # octante 4 (oeste): puerta (232.68,250): ACTIVE más cercano (250,310) a sqrt(17.32²+60²)=62.45
    assert abs(g[4] - np.hypot(17.32, 60.0) / 250.0) < 1e-2, f"puerta oeste {g[4]*250:.1f}"
    # rasgos del cebo: señuelo = lobo 2 (oeste, 180°); ACTIVEs a 0° (3) y 90° (1) -> ninguno en ±60°
    assert o[19] == 0.0, f"frac cono señuelo {o[19]}"
    # progreso: centroide ACTIVE actual (295, 265) − prev (270,265) = (25,0) proyectado sobre u=(-1,0) = -25 -> -0.25
    assert abs(o[20] - (-0.25)) < 1e-6, f"progreso {o[20]}"
    assert o[21 + 1] == 1.0 and o[21:25].sum() == 1.0, "one-hot opción"
    assert o[25 + EV_MUERTE] == 1.0 and o[25:31].sum() == 1.0, "one-hot evento"
    assert abs(o[31] - 3 / 8) < 1e-6
    # señuelo al este -> 3 de 4 ACTIVE en el cono
    ctx2 = dict(ctx, decoy_idx=np.array([0]), active_c_prev=None)
    o2 = build_manager_obs(w, ctx2)
    assert abs(o2[19] - 0.75) < 1e-6 and o2[20] == 0.0, f"cono este {o2[19]} prog {o2[20]}"
    print("  [5] manager_obs: layout 35 + manada/rebaño/puertas/cebo/contexto con valores conocidos OK")


def test_6_manager_env():
    """Etapa 1 (Commit H): ManagerEnv — (a) DETERMINISMO: mismo seed del env y misma secuencia
    de acciones => misma secuencia de (obs, reward, eventos) bit a bit; (b) B_masa vía
    ManagerEnv (acción 0 siempre, reset_to(seed, kind)) ≡ MASA-forzado de E0.1 (WolfOptionLayer
    MASA + ReactiveCoordinator en el arnés) BIT A BIT en 10 semillas (hash del estado íntegro al
    final + severidad + steps); (c) contratos: un paso = una opción hasta evento; cada MUERTE
    termina la opción; K_MAX acota; ABORT sólo con CEBO*."""
    from hrl.manager_env import ManagerEnv, EVENT_NAMES, K_MAX
    # (a) determinismo
    def rollout(seed):
        env = ManagerEnv(seed=seed)
        obs, info = env.reset()
        out = [obs.tobytes(), json.dumps(info, sort_keys=True)]
        rng = np.random.default_rng(seed + 7)
        for _ in range(2):
            done = False
            while not done:
                a = int(rng.integers(4))
                obs, r, term, trunc, info = env.step(a)
                out.append((obs.tobytes(), r, info["event"], info["ticks"]))
                done = term or trunc
            if not done:
                break
            obs, info = env.reset()
        return out
    assert rollout(3) == rollout(3), "ManagerEnv NO determinista con el mismo seed"
    # (b) B_masa ≡ MASA-forzado de E0.1 (10 semillas lobos)
    n = 0
    for s_ in range(10):
        env = ManagerEnv(seed=0)
        obs, info = env.reset_to(s_, "lobos")
        done = False; ev_seen = []
        while not done:
            obs, r, term, trunc, info = env.step(0)
            ev_seen.append(info["event"]); done = term or trunc
        h_env = hashlib.sha256(_blob(env.world)).hexdigest()
        # referencia: MASA-forzado de E0.1 por el arnés (misma semilla/tipo) -> ESTADO FINAL íntegro
        w_ref = build_world(s_, "lobos", wolf_controller=WolfOptionLayer(option=("MASA", {})))
        c_ref = SyncedReactiveCoordinator(w_ref); w_ref.reset()
        while True:
            _o, _r, t_, tr_, _i = w_ref.step(c_ref.act(w_ref.get_observation()))
            if t_ or tr_:
                break
        assert hashlib.sha256(_blob(w_ref)).hexdigest() == h_env, f"B_masa != MASA-forzado (seed {s_})"
        assert "ABORT_BAIT_FAILED" not in ev_seen, "ABORT con MASA (solo CEBO* puede abortar)"
        n += 1
    # (c) contratos con CEBO_keep en un episodio: ticks por opción <= K_MAX; cada tramo termina en
    # un evento nombrado; la re-decisión tras MUERTE existe.
    env = ManagerEnv(seed=1)
    obs, info = env.reset_to(_seeds_by_groups("lobos", 2, 1, min_wolves=3)[0], "lobos")
    done = False; evs = []
    while not done:
        obs, r, term, trunc, info = env.step(1)
        assert info["ticks"] <= K_MAX and info["event"] in EVENT_NAMES
        assert obs.shape == (35,) and np.all(np.isfinite(obs))
        evs.append(info["event"]); done = term or trunc
    assert evs[-1] == "FIN_EPISODIO"
    print(f"  [6] ManagerEnv: determinismo OK · B_masa ≡ MASA-forzado BIT A BIT ({n} eps) · contratos "
          f"(eventos {sorted(set(evs))}) OK")


def test_Q_fallback_quorum():
    """Fallback de quórum (mini-E0.3, plan M1''): CEBO con n_wolves <= n_min_adult (asalto < 2)
    cae a MASA con OPTION_FALLBACK 'CEBO/quorum' y el episodio queda BIT A BIT igual que
    MASA-forzado (misma semilla). Con n >= 3 no dispara."""
    import re
    from baseline import CONFIG_V2
    from world import World

    def build_n(seed, n):
        cfg = dict(CONFIG_V2)
        cfg["wolves_min"] = cfg["wolves_max"] = n
        return cfg

    n_ok = 0
    for n in (1, 2):
        for seed in (0, 3):
            cfg = build_n(seed, n)
            layer = WolfOptionLayer(option=("CEBO", {"membership": "keep", "hold": 50.0}))
            wa = World(seed=seed, episode_kind="lobos", wolf_controller=layer, **cfg)
            ca = SyncedReactiveCoordinator(wa); wa.reset()
            ha = hashlib.sha256(); ha.update(_blob(wa))
            evs = []
            while True:
                _o, _r, t, tr, _i = wa.step(ca.act(wa.get_observation()))
                ha.update(_blob(wa)); evs += layer.pop_events()
                if t or tr:
                    break
            fb = [e for e in evs if e["ev"] == "OPTION_FALLBACK"]
            assert fb and fb[0]["de"].startswith("CEBO/quorum"), f"sin fallback de quórum (n={n} seed {seed}): {evs[:3]}"
            layer_m = WolfOptionLayer(option=("MASA", {}))
            wb = World(seed=seed, episode_kind="lobos", wolf_controller=layer_m, **cfg)
            cb = SyncedReactiveCoordinator(wb); wb.reset()
            hb = hashlib.sha256(); hb.update(_blob(wb))
            while True:
                _o, _r, t, tr, _i = wb.step(cb.act(wb.get_observation()))
                hb.update(_blob(wb))
                if t or tr:
                    break
            assert ha.hexdigest() == hb.hexdigest(), f"CEBO/quorum-fallback != MASA (n={n} seed {seed})"
            n_ok += 1
    # con n>=3 NO dispara
    layer3 = WolfOptionLayer(option=("CEBO", {"membership": "keep", "hold": 50.0}))
    w3 = World(seed=_seeds_by_groups("lobos", 1, 1, min_wolves=3)[0], episode_kind="lobos",
               wolf_controller=layer3, **CONFIG_V2)
    c3 = SyncedReactiveCoordinator(w3); w3.reset()
    for _ in range(20):
        w3.step(c3.act(w3.get_observation()))
    assert not [e for e in layer3.pop_events() if e["ev"] == "OPTION_FALLBACK"], "fallback con n>=3"
    print(f"  [Q] fallback de quórum CEBO->MASA: {n_ok} episodios n<=2 BIT A BIT ≡ MASA + n>=3 sin disparar")


def test_P_auditor_patrulla():
    from hrl.behavior_checks import PatrolCoverageTracker
    w = build_world(0, "lobos")
    w.reset()
    w.phase = "VIGILANCIA"
    w.battery[:] = 1.0
    herd_c = w.cows[w.cow_alive].mean(axis=0)
    act = np.where(w.drone_state == ACTIVE)[0][:4]

    def ring(R):
        for k, i in enumerate(act):
            ang = np.pi / 4 + k * np.pi / 2
            w.drones[i] = herd_c + R * np.array([np.cos(ang), np.sin(ang)])

    # (1) anillo R=150 -> D ≈ 1.41·150 ≈ 212 > 200 => VIOLACIÓN; lobo entrando por el arco 0-90°
    tr = PatrolCoverageTracker(w)
    ring(150.0)
    w.wolves[:] = herd_c + np.array([400.0, 400.0])          # lejos: sin detectar
    d0 = np.linalg.norm(w.drones[act] - herd_c, axis=1)
    path = np.linspace(1.0, 0.0, 12)                         # entra en diagonal por el arco ancho (45°+45°=90°? no: bisectriz 90°)
    for frac in path:
        w.wolves[0] = herd_c + (30.0 + frac * 200.0) * np.array([np.cos(np.pi / 2), np.sin(np.pi / 2)])
        w.step_count += 1
        tr.on_boundary()
    rec1 = tr.finalize()
    assert rec1["ticks_violacion"] == len(path), rec1
    assert rec1["D_max"] > 2 * w.r_detect, rec1
    assert rec1["entradas_no_detectadas"] == 1 and rec1["entradas_no_detectadas_por_arco_violacion"] == 1, rec1
    # (2) anillo R=60 -> D ≈ 85 <= 100 => OK (ni aviso ni violación)
    tr2 = PatrolCoverageTracker(w)
    ring(60.0)
    w.wolves[:] = herd_c + np.array([400.0, 400.0])
    w.step_count += 1
    tr2.on_boundary()
    rec2 = tr2.finalize()
    assert rec2["ticks_aviso"] == 0 and rec2["ticks_violacion"] == 0 and rec2["D_max"] < 100.0, rec2
    # (3) el INVESTIGADOR queda fuera del anillo: 3 en anillo cerrado + 1 investigando LEJOS no
    # abre aviso (con 4 y el 4º lejos sí lo abriría)
    tr3 = PatrolCoverageTracker(w)
    for k, i in enumerate(act[:3]):
        ang = np.pi / 4 + k * 2 * np.pi / 3
        w.drones[i] = herd_c + 55.0 * np.array([np.cos(ang), np.sin(ang)])
    w.drones[act[3]] = herd_c + np.array([250.0, 0.0])
    w.drone_investigating[act[3]] = True
    w.step_count += 1
    tr3.on_boundary()
    w.drone_investigating[act[3]] = False
    rec3 = tr3.finalize()
    assert rec3["ticks_aviso"] == 0 and rec3["ticks_violacion"] == 0, rec3
    # (4) en ESCOLTA no se audita
    tr4 = PatrolCoverageTracker(w)
    w.phase = "ESCOLTA"
    w.step_count += 1
    tr4.on_boundary()
    rec4 = tr4.finalize()
    assert rec4["ticks_patrulla"] == 0, rec4
    w.phase = "VIGILANCIA"
    print("  [P] auditor de patrulla: VIOLACIÓN a R=150 (D=%.0f) + entrada no detectada por el arco"
          " · OK a R=60 · investigador excluido · ESCOLTA fuera de ámbito" % rec1["D_max"])


def test_4_allocator_4_0():
    n = 0
    for kind, count in (("lobos", 3), ("mixto", 2)):
        seed = 0
        for s in range(seed, seed + count):
            ha = _run_hashed(s, kind)
            hb = _run_hashed(s, kind,
                             coord_factory=lambda w: AllocatorCoordinator(w, (4, 0)))
            assert ha == hb, f"Allocator 4-0 != ReactiveCoordinator (seed {s} {kind})"
            n += 1
    print(f"  [4] AllocatorCoordinator 4-0 ≡ ReactiveCoordinator BIT A BIT: {n} episodios OK")


def test_D2a_guardia_sonido():
    """Commit D2a (adenda D2-Fase-1; SOLO docs/tests): el GUARDIA-QUE-PERSIGUE sigue siendo la
    conducta correcta con el sonido SIEMPRE-ACTIVO (v3.5+) — perseguir lleva la burbuja de 20 m
    hasta el lobo del 2º frente (un guardia quieto solo cubre la suya). Dirigido en G real:
    AllocatorCoordinator(3,1): (i) el waypoint del guardia es la POSICIÓN VIVA de una amenaza del
    clúster SECUNDARIO (unidad de conducta); (ii) en dinámica, el guardia llega a <= DETER del
    lobo objetivo (la burbuja ALCANZA) y el frente mantiene su línea de 3 sin comandar al
    guardia. Si esta conducta dejara de ser la correcta => PARAR y avisar (orden del dueño)."""
    from hrl.options_drone import AllocatorCoordinator, analyze_threats
    from world import DETER_RADIUS
    seed = _seeds_by_groups("lobos", 2, 1, min_wolves=3)[0]
    w = build_world(seed, "lobos")
    coord = AllocatorCoordinator(w, particion=(3, 1))
    w.reset()
    d_min_obj = 1e9
    unidad_ok = False
    for t in range(6000):
        wp = coord.act(w.get_observation())
        seats = coord._seats.seats()
        guard = int(seats[3]) if seats[3] >= 0 else -1
        if guard >= 0:
            info = analyze_threats(w, coord.inner)
            if info["secundario"] is not None and (w.drone_state[guard] == ACTIVE) \
                    and not w.drone_investigating[guard]:
                pts = info["clusters"][info["secundario"]]
                d_wp = np.linalg.norm(info["pts"][pts] - wp[guard], axis=1).min()
                if d_wp < 1e-6:
                    unidad_ok = True                     # waypoint = amenaza VIVA del 2º clúster
                    wolves_sec = info["wolf_idx"][pts]
                    wolves_sec = wolves_sec[wolves_sec >= 0]
                    if wolves_sec.size:
                        d_min_obj = min(d_min_obj, float(np.linalg.norm(
                            w.wolves[wolves_sec] - w.drones[guard], axis=1).min()))
        _o, _r, term, trunc, _i = w.step(wp)
        if term or trunc:
            break
    assert unidad_ok, "el guardia no persiguió una amenaza VIVA del clúster secundario"
    assert d_min_obj <= DETER_RADIUS + 2.0, \
        f"la burbuja del guardia no alcanzó al 2º frente (d_min {d_min_obj:.1f})"
    print(f"  [D2a] guardia-que-persigue bajo sonido siempre-activo: waypoint = amenaza viva y "
          f"burbuja alcanzada (d_min {d_min_obj:.1f} <= {DETER_RADIUS + 2:.0f}); conducta REVALIDADA")


def _h_managerenv(seed, kind, ckpt):
    from hrl.manager_env import ManagerEnv
    from hrl.eval_manager import policy_fn
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    h = hashlib.sha256()
    env.on_tick = lambda w, c, l: h.update(_blob(w))
    obs, info = env.reset_to(seed, kind)
    pol = policy_fn("manager:" + ckpt)
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    return h.hexdigest(), int(env.world.n_depredadas)


def _h_frozen(seed, kind, ckpt):
    from hrl.manager_drone import FrozenWolfManager
    fm = FrozenWolfManager(ckpt)
    layer = WolfOptionLayer(manager=fm, frame_skip=5)
    w = build_world(seed, kind, wolf_controller=layer)
    coord = ReactiveCoordinator(w)
    w.reset()
    h = hashlib.sha256()
    while True:
        layer.refresh(w)
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        fm.on_tick(w, layer)
        h.update(_blob(w))
        if t or tr:
            break
    return h.hexdigest(), int(w.n_depredadas)


def test_D2_frozen_wolf_manager():
    """D2-Fase-2 [D2-1]: el manager lobo CONGELADO reproducido dentro de otro arnés
    (FrozenWolfManager: misma lógica de eventos que ManagerEnv + argmax) es BIT A BIT el
    ManagerEnv — el atacante de train/eval de D2 es exactamente el resultado principal."""
    from hrl.manager_drone import WOLF_MANAGER_CKPT
    import os
    if not os.path.exists(WOLF_MANAGER_CKPT):
        print("  [D2-1] SALTADO: sin ckpt del manager lobo en este entorno"); return
    for seed, kind in ((21, "lobos"), (2, "mixto")):
        a = _h_managerenv(seed, kind, WOLF_MANAGER_CKPT)
        b = _h_frozen(seed, kind, WOLF_MANAGER_CKPT)
        assert a == b, f"D2-1: frozen != ManagerEnv (seed {seed} {kind}): {a[1]} vs {b[1]}"
    print("  [D2-1] FrozenWolfManager ≡ ManagerEnv BIT A BIT: 2 episodios OK")


def test_D2_env_4_0_y_determinismo():
    """[D2-2] DroneManagerEnv con partición 4-0 fija y atacante natural ≡ ReactiveCoordinator
    en bucle plano BIT A BIT (el env no perturba el mundo; AllocatorCoordinator 4-0 ≡ Reactive
    por [4]); [D2-3] reset_to determinista; coste de deliberación DIRIGIDO (decisión tras
    CLUSTER_CHANGE que cambia de partición paga DELIB_COST_D2; mantener es gratis)."""
    from hrl.manager_drone import (DroneManagerEnv, DELIB_COST_D2, EVD_CLUSTER, EVD_NAMES,
                                   DroneDecisionCore)
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    ha = _run_hashed(seed, "lobos")
    env = DroneManagerEnv(seed=0)
    h = hashlib.sha256()
    env.on_tick = lambda w, c, l: h.update(_blob(w))
    obs, info = env.reset_to(seed, "lobos", "natural")
    h.update(_blob(env.world))
    done = False
    while not done:
        obs, r, term, trunc, info = env.step(0)
        done = term or trunc
    assert h.hexdigest() == ha, "D2-2: env 4-0 != Reactive bit a bit"
    h2 = hashlib.sha256()
    env.on_tick = lambda w, c, l: h2.update(_blob(w))
    obs, info = env.reset_to(seed, "lobos", "natural")
    h2.update(_blob(env.world))
    done = False
    while not done:
        obs, r, term, trunc, info = env.step(0)
        done = term or trunc
    assert h2.hexdigest() == ha, "D2-3: reset_to no determinista"
    # coste DIRIGIDO: forzar un CLUSTER_CHANGE parcheando el conteo de clústeres del núcleo
    env3 = DroneManagerEnv(seed=0, k_max=300)
    env3.reset_to(seed, "lobos", "natural")
    flip = {"n": 0}
    orig = env3._core.n_clusters
    env3._core.n_clusters = lambda: orig() + (flip["n"] % 2)          # alterna => CLUSTER_CHANGE
    _o, r1, _t, _tr, i1 = env3.step(0)
    assert i1["event"] == "CLUSTER_CHANGE", i1
    flip["n"] += 1
    _o, r2, _t, _tr, i2 = env3.step(0)                     # misma partición tras interrupción: gratis
    assert abs(r2 - round(r2)) < 1e-9, r2
    flip["n"] += 1
    _o, r3, _t, _tr, i3 = env3.step(1)                     # cambio tras interrupción: paga
    assert abs((r3 - round(r3)) + DELIB_COST_D2) < 1e-9, (r3, i2, i3)
    print(f"  [D2-2/3] env 4-0 ≡ Reactive bit a bit · determinista · coste {DELIB_COST_D2} "
          f"pagado solo al cambiar tras CLUSTER_CHANGE")


def test_D2_tripwire_guardia():
    """[D2-4] TRIPWIRE D2 (espejo de Q-bis): guardias asignados >= 400 ticks SIN 2º clúster
    percibido => vuelta FORZADA a 4-0 + evento STALL. Dirigido: partición 3-1 en un mundo donde
    los lobos aún no se perciben (inicio de episodio, lejos)."""
    from hrl.manager_drone import DroneManagerEnv, GUARD_STALL_TICKS
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    env = DroneManagerEnv(seed=0)
    env.reset_to(seed, "lobos", "natural")
    _o, r, _t, _tr, info = env.step(0)                      # 4-0 hasta que el conteo se asiente
    assert info["event"] == "CLUSTER_CHANGE", info          # 0 -> 1 clúster percibido (legítimo)
    stall = None
    for _ in range(4):                                      # 3-1 con UN solo clúster (sin 2º)
        _o, r, _t, _tr, info = env.step(1)
        if info["event"] == "STALL":
            stall = info
            break
        assert info["event"] == "CLUSTER_CHANGE", info      # cualquier otro terminal = escenario inválido
    assert stall is not None and stall["ticks"] == GUARD_STALL_TICKS, stall
    assert env._coord.particion == (4, 0), env._coord.particion
    print(f"  [D2-4] tripwire de guardia: STALL a los {GUARD_STALL_TICKS} ticks sin 2º clúster y "
          f"4-0 forzado")


if __name__ == "__main__":
    test_0_unidades()
    test_1_masa_bit_a_bit()
    test_2_cebo_spawn_bit_a_bit()
    test_S1_gate_mejor_esfuerzo()
    test_S2_abort_solo_preshow()
    test_S3_censura()
    test_QC_coste_deliberacion()
    test_QB_tripwire_show()
    test_S3_staged_meseta()
    test_K1_persistencia_sin_proteccion()
    test_K2_retarget_protegida_y_cooldown()
    test_K3_protegida_sin_alternativa()
    test_K4_masa_drones_lejos_bit_a_bit()
    test_P_auditor_patrulla()
    test_Q_fallback_quorum()
    test_3_aserciones_y_determinismo()
    test_3b_cebo_keep_y_prematura()
    test_4_allocator_4_0()
    test_D2a_guardia_sonido()
    test_D2_frozen_wolf_manager()
    test_D2_env_4_0_y_determinismo()
    test_D2_tripwire_guardia()
    test_5_manager_obs()
    test_6_manager_env()
    print("hrl_check: TODO OK.")
