"""hrl/hrl_check.py — Verificación de la capa de opciones del jerárquico (Etapa 0).

ENTRA EN LA VERJA desde el Commit C (8º check, junto a los 7 de siempre). Corre DENTRO del
contenedor: `python3 hrl/hrl_check.py`. Asserts al estilo de los demás checks.

  0) UNIDADES de events/behavior_checks (Commit B): geometría de seg_cross · detector
     LURE_COMMIT dirigido (stub geométrico: 3/4 drones en el cono del señuelo + puerta del
     asalto abierta => ON; un dron en la puerta => OFF) · la aserción CRITICAL "ORDEN DEL
     CEBO" salta con un SHOW_START sin latch.
  1) MASA vía capa ≡ ScriptedWolfController BIT A BIT (hash SHA256 del estado íntegro por
     tick, episodios COMPLETOS): 12 semillas lobos+mixto de 1 GRUPO de spawn — el camino en
     que el script ES la caza de masa. [Con 2 grupos MASA difiere del script POR DISEÑO:
     es la decisión del manager de fusionar el paquete — no se compara ahí.]
  2) CEBO membership="spawn" ≡ script de dos sectores BIT A BIT (5 semillas de 2 grupos,
     lobos y mixto): el impuesto de interfaz del camino spawn es CERO por construcción —
     la referencia dura de E0.A(ii).
  3) ASERCIONES del protocolo sobre 5 episodios CEBO (membership manager, Δ=180°, n>=3):
     sin CRITICAL (orden del cebo, procedencia completa), sin violaciones de contrato
     (pack_prey/pack_prey2 válidos, máscara de comando respetada), OPTION_START presente.
     + DETERMINISMO de eventos: misma seed => misma línea temporal (bit a bit del JSON).
  [4) Allocator 4-0 ≡ Reactive bit a bit + clustering dirigido: llegan con el Commit D.]
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
from hrl.options_wolf import WolfOptionLayer                       # noqa: E402


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

    print("  [0] unidades events/behavior_checks: OK")


def test_1_masa_bit_a_bit():
    n = 0
    for kind in ("lobos", "mixto"):
        for s in _seeds_by_groups(kind, 1, 6):
            ha = _run_hashed(s, kind)
            hb = _run_hashed(s, kind, wolf_layer=WolfOptionLayer(option=("MASA", {})),
                             coord_factory=lambda w: SyncedReactiveCoordinator(w))
            assert ha == hb, f"MASA vía capa != scriptado (seed {s} {kind})"
            n += 1
    print(f"  [1] MASA vía capa ≡ scriptado BIT A BIT: {n} episodios de 1 grupo OK")


def test_2_cebo_spawn_bit_a_bit():
    n = 0
    for kind, count in (("lobos", 3), ("mixto", 2)):
        for s in _seeds_by_groups(kind, 2, count):
            ha = _run_hashed(s, kind)
            hb = _run_hashed(s, kind,
                             wolf_layer=WolfOptionLayer(option=("CEBO", {"membership": "spawn"})),
                             coord_factory=lambda w: SyncedReactiveCoordinator(w))
            assert ha == hb, f"CEBO/spawn vía capa != script 2 sectores (seed {s} {kind})"
            n += 1
    print(f"  [2] CEBO membership=spawn ≡ script BIT A BIT: {n} episodios de 2 grupos OK")


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


if __name__ == "__main__":
    test_0_unidades()
    test_1_masa_bit_a_bit()
    test_2_cebo_spawn_bit_a_bit()
    test_3_aserciones_y_determinismo()
    print("hrl_check: TODO OK.")
