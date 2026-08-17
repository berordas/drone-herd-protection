"""hrl/hrl_check.py — Verificación de la capa de opciones del jerárquico (Etapa 0).

Commit B: TESTS UNITARIOS de hrl/events.py y hrl/behavior_checks.py. [El check se AMPLÍA en
los commits C/D con las equivalencias bit a bit de la capa (MASA/CEBO/Allocator) y ENTRA EN
LA VERJA como 8º check desde el Commit C.] Corre DENTRO del contenedor:
`python3 hrl/hrl_check.py`. Asserts al estilo de los demás checks.

  0) UNIDADES: geometría de seg_cross · detector LURE_COMMIT dirigido (stub geométrico:
     3/4 drones en el cono del señuelo + puerta del asalto abierta => ON; un dron en la
     puerta => OFF) · la aserción CRITICAL "ORDEN DEL CEBO" salta con un SHOW_START sin
     latch.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from baseline import build_world                                   # noqa: E402
from coordinators import ReactiveCoordinator                       # noqa: E402
from world import ACTIVE                                           # noqa: E402

from hrl.behavior_checks import EpisodeAudit, seg_cross            # noqa: E402
from hrl.events import EventTracker                                # noqa: E402


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


if __name__ == "__main__":
    test_0_unidades()
    print("hrl_check: TODO OK.")
