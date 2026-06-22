"""
main.py — Bucle de un episodio.

Orquesta World + Coordinator, registra métricas y al final anima el episodio.
El World no sabe nada del render: aquí grabamos un historial de snapshots durante
el bucle y se lo pasamos a render_episode para reproducirlo.

Bucle: reset -> [observar -> coordinar -> aplicar+step -> terminal] -> métricas.

Uso:
    python main.py        # seed aleatoria (cada ejecución cambia, p. ej. el nº de lobos)
    python main.py 42     # seed fija -> episodio reproducible
"""

from __future__ import annotations
import sys
import numpy as np

from world import World
from coordinators import DummyCoordinator
from render import render_episode


def run_episode(world: World, coordinator: DummyCoordinator):
    world.reset()
    history = [world.snapshot()]
    total_reward = 0.0

    while True:
        obs = world.get_observation()                                   # observar
        actions = coordinator.act(obs)                                  # coordinar
        obs, reward, terminated, truncated, info = world.step(actions)  # aplicar + step
        history.append(world.snapshot())
        total_reward += reward
        if terminated or truncated:                                     # terminal
            break

    metrics = {
        "outcome": world.status,
        "n_wolves": world.n_wolves,
        "steps": world.step_count,
        "sim_time_s": round(world.step_count * world.dt, 2),
        "total_reward": round(total_reward, 3),
    }
    return history, metrics


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else int(np.random.randint(0, 10000))
    print(f"seed = {seed}  (reproduce con: python main.py {seed})")

    world = World(seed=seed, teleport_guard=True)
    coordinator = DummyCoordinator(world.n_drones)

    history, metrics = run_episode(world, coordinator)

    print("Métricas del episodio:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Manada (presa común): coordinación + instrumentación del flanqueo (#3) + retoque por exposición.
    mean_simul = world._simul_sum / max(world._simul_steps, 1)
    print(f"Manada (presa común): terneros={world.n_calves}")
    pp = world._prey_pos()
    if pp is not None and world.pack_prey_kind == "adult":
        centroid = world.cows.mean(axis=0)
        d_prey = float(np.linalg.norm(pp - centroid))
        d_mean = float(np.linalg.norm(world.cows - centroid, axis=1).mean())
        print(f"  presa adulta: dist al centroide del rebaño={d_prey:.1f} m vs media del rebaño={d_mean:.1f} m "
              f"(retoque: la presa debe estar MÁS lejos = del borde)")
    print(f"  presas atacadas a la vez: máx={world.max_simul_targets} media={mean_simul:.2f} | "
          f"re-fijaciones={world.n_refix}")
    q = world.flank_first_quorum
    if q is not None:
        print(f"  primer quórum de flanqueadores: paso={q['step']} flanqueadores={q['flankers']} -> muerte={q['killed']}")
    print(f"  desglose de toques (lobo en capture_radius): {world.touch_breakdown}")

    c = world.capture_info
    if c is not None:
        if c["kind"] == "calf":
            print(f"Captura de TERNERO {c['prey_idx']} (defensora={c['defender_idx']}, presa fijada={c['is_pack_prey']}) | "
                  f"flanqueadores={c['n_flankers']} (lobos {c['flankers']}) | lobo más cercano={c['min_wolf_dist']:.2f} m")
        else:
            print(f"Captura de ADULTA {c['prey_idx']} (presa fijada={c['is_pack_prey']}, la más lenta={c['is_weakest']}) | "
                  f"flanqueadores={c['n_flankers']} (lobos {c['flankers']}) | lobo más cercano={c['min_wolf_dist']:.2f} m")
    if world.guard_violations:
        print(f"Guardia de teletransporte: {len(world.guard_violations)} violaciones (detalle en face_check.py)")

    render_episode(world, history)


if __name__ == "__main__":
    main()
