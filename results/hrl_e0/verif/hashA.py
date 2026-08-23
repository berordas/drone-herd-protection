"""hashA.py — Hash bit a bit del mundo scriptado (verificación del Commit A, refactor
conducta-preservante de wolf_controllers.py). Corre episodios COMPLETOS con el controlador
scriptado por defecto + ReactiveCoordinator (CONFIG_V2, tipos lobos y mixto) y acumula un
SHA256 por episodio sobre TODO el estado por tick. Se corre ANTES y DESPUÉS del refactor;
los digests deben ser IDÉNTICOS (24 semillas x 2 tipos = 48 episodios; incluye episodios
de 2 subgrupos = el camino del cebo).

Uso: python3 hashA.py <etiqueta>   ->  /data/hrl_e0/verif/hashA_<etiqueta>.json
"""
import hashlib
import json
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world              # noqa: E402
from coordinators import ReactiveCoordinator  # noqa: E402

SEEDS = range(50)
KINDS = ("lobos", "mixto")


def state_blob(w) -> bytes:
    parts = [
        w.wolves.tobytes(), w.wolf_vel.tobytes(), w.cows.tobytes(), w.cow_heading.tobytes(),
        w.drones.tobytes(), w.drone_vel.tobytes(), w.drone_waypoint.tobytes(),
        w.cow_alive.tobytes(), w.cow_safe.tobytes(),
        w.calf_alive.tobytes(), w.calf_safe.tobytes(), w.calves.tobytes(),
        w.battery.tobytes(), w.drone_state.tobytes(),
        np.int64([w.step_count, w.n_depredadas, w.pack_prey, w.pack_prey2,
                  int(w.wolf_decoy_released), w.n_refix]).tobytes(),
        w.phase.encode(),
        (w.pack_prey_kind or "-").encode(), (w.pack_prey2_kind or "-").encode(),
    ]
    if w.n_corzos > 0:
        parts += [w.corzos.tobytes(), w.corzo_dismissed.tobytes()]
    return b"".join(parts)


def episode_hash(seed: int, kind: str) -> dict:
    w = build_world(seed, kind)
    coord = ReactiveCoordinator(w)
    w.reset()
    h = hashlib.sha256()
    h.update(state_blob(w))
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        h.update(state_blob(w))
        if term or trunc:
            break
    return {"seed": seed, "kind": kind, "grupos": [int(x) for x in w.wolf_group_sizes],
            "sev": int(w.n_depredadas), "steps": int(w.step_count), "sha": h.hexdigest()}


def main():
    label = sys.argv[1]
    out = []
    for kind in KINDS:
        for s in SEEDS:
            r = episode_hash(s, kind)
            out.append(r)
    dos = sum(1 for r in out if len(r["grupos"]) == 2)
    print(f"[{label}] episodios: {len(out)} (2 subgrupos: {dos})")
    path = f"/data/hrl_e0/verif/hashA_{label}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print("HASHA_OK ->", path)


if __name__ == "__main__":
    main()
