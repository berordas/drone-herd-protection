"""ATRIBUCIÓN de la desviación de la sanity de capa (Δ=+1.16 vs ref v3.5 +0.85, umbral 0.3).
Mismas 50 semillas G/n>=3 de sanity_capaK.py, tres configuraciones:
  A) capa pre-K (worktree ded2123) + patrulla ÓRBITA (0.02)  = réplica v3.5 exacta sobre ESTAS semillas
  B) capa K (HEAD) + patrulla ÓRBITA (0.02)                  = aísla el efecto de la regla K
  C) capa K (HEAD) + patrulla ESTÁTICA (0.0)                 = ya medida (sanity_capaK.json, Δ=+1.16)
Si A ~ 1.16 => la ref +0.85 no era comparable en estas 50 semillas (muestreo) -> desviación NO real.
Si A ~ 0.85 y B ~ 1.16 => el efecto es de la regla K. Si A ~ B ~ 0.85 => es la patrulla estática.
Uso: python3 atrib_sanity.py A|B  (A corre con sys.path al worktree pre-K)."""
import sys, json
import numpy as np

MODE = sys.argv[1]                      # A = pre-K+órbita · B = K+órbita · C = K+estática
ROOT = "/workspace/wt_preK" if MODE == "A" else "/workspace"
OMEGA = 0.0 if MODE == "C" else 0.02
sys.path.insert(0, ROOT)

from baseline import build_world                                   # noqa: E402
from coordinators import ReactiveCoordinator                       # noqa: E402
from hrl.options_wolf import WolfOptionLayer                       # noqa: E402


class SyncedOrbit:
    """SyncedReactiveCoordinator con patrol_omega explícito (órbita 0.02 en ambos modos)."""

    def __init__(self, world):
        self.world = world
        self.inner = ReactiveCoordinator(world, patrol_omega=OMEGA)

    def act(self, observation=None):
        self.world.wolf_controller.refresh(self.world)
        return self.inner.act(observation)


def run(seed, opt):
    layer = WolfOptionLayer(option=opt)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedOrbit(w)
    w.reset()
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if t or tr:
            break
    return int(w.n_depredadas)


def seeds_G(count):
    out, s = [], 0
    while len(out) < count and s < 4000:
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 2 and w.n_wolves >= 3:
            out.append(s)
        s += 1
    return out


if __name__ == "__main__":
    import multiprocessing as mp
    ss = seeds_G(50)
    jobs = [(s, ("CEBO", {"membership": "keep", "hold": 50.0})) for s in ss] + \
           [(s, ("MASA", {})) for s in ss]
    with mp.Pool(24) as pool:
        sev = pool.starmap(run, jobs, chunksize=2)
    cebo, masa = np.array(sev[:50], float), np.array(sev[50:], float)
    d = cebo - masa
    rng = np.random.default_rng(20260819)
    boots = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    out = {"modo": MODE, "root": ROOT, "omega": OMEGA, "n_pares": 50, "seeds": ss,
           "sev_cebo": float(cebo.mean()), "sev_masa": float(masa.mean()),
           "cebo_por_seed": cebo.tolist(), "masa_por_seed": masa.tolist(),
           "delta": [float(d.mean()), float(np.percentile(boots, 2.5)),
                     float(np.percentile(boots, 97.5))]}
    json.dump(out, open(f"/data/hrl_m1/m1pp/atrib_sanity_{MODE}.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
