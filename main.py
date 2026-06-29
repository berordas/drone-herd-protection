"""
main.py — Bucle de un episodio.

Orquesta World + Coordinator, registra métricas y al final anima el episodio.
El World no sabe nada del render: aquí grabamos un historial de snapshots durante
el bucle y se lo pasamos a render_episode para reproducirlo.

Bucle: reset -> [observar -> coordinar -> aplicar+step -> terminal] -> métricas.

Uso:
    python main.py                          # seed aleatoria; tipo de episodio sorteado (~1/3 solo-lobos / solo-corzos / mixto)
    python main.py 42                       # seed fija -> episodio reproducible
    python main.py --escenario solo-corzos  # FUERZA el tipo (solo-lobos / solo-corzos / mixto); ver corzos a voluntad
    python main.py 42 --escenario mixto     # seed fija + tipo forzado
"""

from __future__ import annotations
import argparse
import numpy as np

from world import World
from coordinators import DummyCoordinator
from render import render_episode

# CLI --escenario -> episode_kind del World (3c). El mundo de la baseline v2 lleva corzos activos
# (corzos_max>0) y sortea el tipo por episodio; --escenario lo fuerza para ver corzos sin depender del azar.
ESCENARIOS = {"solo-lobos": "lobos", "solo-corzos": "corzos", "mixto": "mixto"}
CORZOS_MAX = 3   # 1-3 corzos en los episodios que los tienen (mismo mundo v2 que mide la baseline por tipo)


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
        "episodio": world.episode_kind,
        "phase_final": world.phase,
        "n_wolves": world.n_wolves,
        "n_corzos": world.n_corzos,
        "n_corzos_descartados": int(world.corzo_dismissed.sum()),
        "n_safe": int(world.cow_safe.sum() + world.calf_safe.sum()),
        "n_depredadas": world.n_depredadas,
        "n_fuera": int((world.cow_alive & ~world.cow_safe).sum() + (world.calf_alive & ~world.calf_safe).sum()),
        "steps": world.step_count,
        "sim_time_s": round(world.step_count * world.dt, 2),
        "total_reward": round(total_reward, 3),
    }
    return history, metrics


def main():
    parser = argparse.ArgumentParser(description="Un episodio de la escolta (drones / lobos / vacas / corzos).")
    parser.add_argument("seed", nargs="?", type=int, default=None, help="seed (omítela para una aleatoria)")
    parser.add_argument("--escenario", choices=list(ESCENARIOS), default=None,
                        help="fuerza el tipo de episodio (si se omite, se sortea ~1/3 cada uno)")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else int(np.random.randint(0, 10000))
    episode_kind = ESCENARIOS.get(args.escenario)   # None -> sorteo sembrado

    world = World(seed=seed, teleport_guard=True, corzos_max=CORZOS_MAX, episode_kind=episode_kind)
    coordinator = DummyCoordinator(world.n_drones)

    forzado = f"  (forzado: --escenario {args.escenario})" if args.escenario else "  (sorteado)"
    print(f"seed = {seed}  (reproduce con: python main.py {seed}"
          + (f" --escenario {args.escenario}" if args.escenario else "") + ")")
    print(f"episodio = {world.episode_kind}{forzado}  |  lobos = {world.n_wolves}  corzos = {world.n_corzos}")

    history, metrics = run_episode(world, coordinator)

    print("Métricas del episodio:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Manada (presa común): coordinación + instrumentación del flanqueo (#3) + retoque por exposición.
    mean_simul = world._simul_sum / max(world._simul_steps, 1)
    print(f"Manada (presa común): terneros={world.n_calves}")
    # Espaciado del rebaño (#1) + spawn de lobos por sector (#2), leídos del estado en t=0.
    cows0, wolves0 = history[0]["cows"], history[0]["wolves"]
    Dnn = np.linalg.norm(cows0[:, None, :] - cows0[None, :, :], axis=2)
    np.fill_diagonal(Dnn, np.inf)
    print(f"  rebaño al pastar: vecino más cercano medio={Dnn.min(axis=1).mean():.1f} m (repartido)")
    if world.n_wolves > 0:
        disp0 = float(np.linalg.norm(wolves0 - wolves0.mean(axis=0), axis=1).mean()) if world.n_wolves > 1 else 0.0
        print(f"  lobos: entran agrupados por el sector {np.degrees(world.wolf_spawn_angle):.0f}° "
              f"(dispersión del cúmulo={disp0:.1f} m)")
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

    # Animaciones muy largas (p. ej. solo-corzos hace TIMEOUT a max_episode_steps -> miles de frames) ->
    # submuestrea el historial para que el render sea manejable. NO cambia la simulación; solo cuántos
    # snapshots se reproducen (el render solo LEE).
    MAX_FRAMES = 600
    if len(history) > MAX_FRAMES:
        stride = len(history) // MAX_FRAMES + 1
        history = history[::stride] + [history[-1]]
        print(f"  (animación submuestreada: {len(history)} frames, 1 de cada {stride})")

    render_episode(world, history)


if __name__ == "__main__":
    main()
