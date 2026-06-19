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

    world = World(seed=seed)
    coordinator = DummyCoordinator(world.n_drones)

    history, metrics = run_episode(world, coordinator)

    print("Métricas del episodio:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    render_episode(world, history)


if __name__ == "__main__":
    main()
