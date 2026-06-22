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

    c = world.capture_info
    if c is not None:
        print("Procedencia de la captura:")
        print(f"  presa={c['prey_idx']} aislamiento={c['isolation']:.2f} outlier={c['outlier']:.2f} "
              f"(margen {c['pounce_margin']:.2f}) racha={c['iso_streak']} sostenido={c['iso_sustained']}")
        print(f"  lobo en persecución={c['wolf_pouncing']} | salto_presa={c['prey_jump']:.3f}({c['prey_jump_flag']}) "
              f"sobrepaso_lobo={c['wolf_overshoot']:.3f}({c['wolf_overshoot_flag']})  ->  LIMPIA={c['clean']}")
    if world.guard_violations:
        print(f"Guardia de teletransporte: {len(world.guard_violations)} violaciones (detalle en provenance_check.py)")

    render_episode(world, history)


if __name__ == "__main__":
    main()
