"""techo_mean_label.py — TECHO de la etiqueta 'mean' (diagnóstico A′, no es código del repo).

Oráculo = clon PERFECTO de la etiqueta media: en cada frontera de decisión clona (deepcopy) el
par (mundo, coordinador), rueda la copia frame_skip pasos con el EXPERTO de las demos (scriptado
+ presa del contrato, como collect_demos v3) para leer sus v_target, y ejecuta su MEDIA mantenida
en el mundo REAL a través de un RLWolfController (cap por norma + presa del contrato + coasting =
exactamente la semántica de servicio del clon). Lo que saque esto es lo MÁXIMO que un BC sobre la
etiqueta 'mean' puede dar. 10 semillas deterministas de 'lobos' (las de la eval ligera).
"""
import copy
import numpy as np

from baseline import build_world
from coordinators import ReactiveCoordinator
from wolf_controllers import ScriptedWolfController, WolfController
from rl.rl_wolf_controller import RLWolfController
from rl.obs import N_WOLF_SLOTS

FS = 5


class RecScripted(WolfController):
    """Experto de las demos v3: scriptado + presa del contrato, guardando su v_target."""

    def __init__(self):
        self.inner = ScriptedWolfController()
        self.last_v = None

    def decide(self, world):
        v, c = self.inner.decide(world)
        self.last_v = np.asarray(v, dtype=np.float64).copy()
        RLWolfController._write_prey(world)
        return v, c


def mean_label(w, coord):
    """Etiqueta 'mean' calculada EN VIVO: media de los v_target del experto en la ventana
    que empieza en el estado actual (rollout sobre una copia profunda)."""
    w2, coord2 = copy.deepcopy((w, coord))
    rec = RecScripted()
    w2.wolf_controller = rec
    vs = []
    for _ in range(FS):
        _o, _r, t, tr, _i = w2.step(coord2.act(w2.get_observation()))
        v = np.zeros((N_WOLF_SLOTS, 2))
        v[: w2.n_wolves] = rec.last_v[: w2.n_wolves] / w2.wolf_speed
        vs.append(v)
        if t or tr:
            break
    return np.mean(vs, axis=0)


def run_episode(seed, kind="lobos"):
    hold = RLWolfController(N_WOLF_SLOTS)          # la semántica de servicio del clon
    w = build_world(seed, kind, wolf_controller=hold)
    w.reset()
    coord = ReactiveCoordinator(w)
    k = 0
    while True:
        if k % FS == 0:
            hold.set_action(mean_label(w, coord) * w.wolf_speed)
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        k += 1
        if term or trunc:
            break
    return int(w.n_depredadas), w.status


if __name__ == "__main__":
    deaths = []
    for s in range(10):
        d, st = run_episode(s)
        deaths.append(d)
        print("  seed %d: %d muertes (%s)" % (s, d, st), flush=True)
    print("TECHO held-mean-label (10 semillas lobos): %s | media = %.2f"
          % (deaths, float(np.mean(deaths))))
