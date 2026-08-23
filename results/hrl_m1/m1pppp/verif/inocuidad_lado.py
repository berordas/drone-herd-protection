"""inocuidad_lado.py <repo_root> <out.json> — 50 episodios de MEZCLA NATURAL (sin forzar tipo)
vs Reactive-estatica, sev por semilla. Se ejecuta una vez por lado (v3.7 pineado / v3.7.1)."""
import json, sys
sys.path.insert(0, sys.argv[1])
import multiprocessing as mp
from baseline import CONFIG_V2
from coordinators import ReactiveCoordinator
from world import World


def run(seed):
    w = World(seed=seed, **CONFIG_V2)          # tipo NATURAL (sorteo del propio mundo)
    coord = ReactiveCoordinator(w)
    w.reset()
    while True:
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if t or tr:
            break
    return {"seed": seed, "kind": w.episode_kind, "sev": int(w.n_depredadas)}


if __name__ == "__main__":
    with mp.get_context("fork").Pool(16) as pool:
        rows = pool.map(run, list(range(50)), chunksize=2)
    json.dump(rows, open(sys.argv[2], "w"))
    print("LADO_OK", sys.argv[1])
