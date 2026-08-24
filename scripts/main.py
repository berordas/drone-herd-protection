"""
main.py — Bucle de un episodio.

Orquesta World + Coordinator, registra métricas y al final anima el episodio.
El World no sabe nada del render: aquí grabamos un historial de snapshots durante
el bucle y se lo pasamos a render_episode para reproducirlo.

Bucle: reset -> [observar -> coordinar -> aplicar+step -> terminal] -> métricas.

Uso:
    python main.py                                        # seed aleatoria; tipo sorteado; coordinador dummy (drones quietos)
    python main.py 42                                     # seed fija -> episodio reproducible
    python main.py --escenario solo-corzos                # FUERZA el tipo (solo-lobos / solo-corzos / mixto)
    python main.py --coordinador reactive                 # barrera de apantallado + patrulla (drones que se MUEVEN)
    python main.py --coordinador reactive --escenario solo-lobos   # barrera en acción, emojis + barra de batería
    python main.py --lobos scripted                       # cerebro de los lobos (default; 'learned' pendiente RL)
"""

from __future__ import annotations
import sys as _sys, pathlib as _pl  # layout: raíz (rl/, hrl/) y sim/ (núcleo) importables sin instalar el paquete
_ROOT = _pl.Path(__file__).resolve().parents[1]; _sys.path[:0] = [str(_ROOT), str(_ROOT / "sim")]
import argparse
import numpy as np

from world import World
from coordinators import DummyCoordinator, ReactiveCoordinator
from render import render_episode

# El render dibuja una barra de batería sobre cada dron -> el history necesita la batería por frame.
# La añadimos aquí (main solo LEE el estado; no toca la física ni snapshot()).
def _snap(world: World) -> dict:
    return {**world.snapshot(), "battery": world.battery.copy()}

# CLI --escenario -> episode_kind del World (3c). El mundo de la baseline v2 lleva corzos activos
# (corzos_max>0) y sortea el tipo por episodio; --escenario lo fuerza para ver corzos sin depender del azar.
ESCENARIOS = {"solo-lobos": "lobos", "solo-corzos": "corzos", "mixto": "mixto"}
CORZOS_MAX = 3   # 1-3 corzos en los episodios que los tienen (mismo mundo v2 que mide la baseline por tipo)


def run_episode(world: World, coordinator):
    world.reset()
    history = [_snap(world)]
    total_reward = 0.0

    while True:
        obs = world.get_observation()                                   # observar
        actions = coordinator.act(obs)                                  # coordinar
        obs, reward, terminated, truncated, info = world.step(actions)  # aplicar + step
        history.append(_snap(world))
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
    parser.add_argument("--coordinador", choices=["dummy", "reactive"], default="dummy",
                        help="dummy = drones quietos (baseline); reactive = barrera de apantallado + patrulla")
    parser.add_argument("--lobos", choices=["scripted", "learned"], default="scripted",
                        help="cerebro de los LOBOS: scripted = comportamiento v2.4 (default); learned = pendiente RL")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else int(np.random.randint(0, 10000))
    episode_kind = ESCENARIOS.get(args.escenario)   # None -> sorteo sembrado

    world = World(seed=seed, teleport_guard=True, corzos_max=CORZOS_MAX, episode_kind=episode_kind,
                  wolf_policy=args.lobos, wolf_spawn_mode="grouped")   # v2.5: subgrupos (= CONFIG_V2)
    coordinator = ReactiveCoordinator(world) if args.coordinador == "reactive" else DummyCoordinator(world.n_drones)

    forzado = f"  (forzado: --escenario {args.escenario})" if args.escenario else "  (sorteado)"
    repro = f"python main.py {seed} --coordinador {args.coordinador}" + (f" --escenario {args.escenario}" if args.escenario else "")
    esp = "corzos" if world.distraction_species == "corzo" else "jabalíes"
    dist = f"{world.n_corzos} {esp}" if world.n_corzos else "0"
    print(f"seed = {seed}  (reproduce con: {repro})")
    print(f"coordinador = {args.coordinador}  |  lobos({args.lobos}) = {world.n_wolves}  |  episodio = {world.episode_kind}{forzado}  |  distracción = {dist}")

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

    # Reproducción a RITMO NATURAL (el render solo LEE; la simulación NO cambia). Episodios muy largos
    # (solo-corzos hace TIMEOUT a max_episode_steps cuando, tras la investigación inicial, ya no pasa nada) se
    # verían ACELERADOS si comprimiéramos miles de frames. En vez de eso renderizamos solo la VENTANA RELEVANTE
    # (hasta poco después del ÚLTIMO evento: cambio de fase / muerte / refugio / descarte de corzo) con stride
    # pequeño -> movimiento suave y observable. Para episodios normales (cortos) = el episodio entero.
    def _key(s):
        return (s["phase"], s["n_depredadas"], s["n_safe"], int(np.sum(s.get("corzo_dismissed", []))))
    last_event = max((k for k in range(1, len(history)) if _key(history[k]) != _key(history[k - 1])), default=0)
    TAIL, MAX_FRAMES = 50, 800                      # ~5 s de cola tras el último evento; tope de frames
    end = min(len(history), last_event + TAIL + 1)
    window = history[:end]
    stride = max(1, len(window) // MAX_FRAMES)      # stride pequeño -> ritmo natural (no saltos bruscos)
    play = window[::stride]
    if end < len(history) or stride > 1:
        print(f"  (render: ventana relevante de {end} pasos a 1 de cada {stride} -> {len(play)} frames, ritmo natural)")

    render_episode(world, play)


if __name__ == "__main__":
    main()
