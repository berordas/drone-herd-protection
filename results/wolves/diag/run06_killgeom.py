"""run06_killgeom.py — SOLO LECTURA: geometría en el MOMENTO de cada muerte.
¿Las muertes son 'visto pero NO disuadido' (r_detect=100 >> DETER_RADIUS=20 -> la zona de matanza
siempre se ve pero un dron no llega a disuadir) o 'no visto' (cebo real)? Y ¿un dron ACTIVE estaba
a tiro de disuasión (<=DETER_RADIUS) del matador? Amplía a lobos+mixto para más episodios de 2 grupos.
"""
import sys; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from world import ACTIVE, DETER_RADIUS, STATIC_DETER_RADIUS
from rl.residual_wolf_controller import ResidualWolfController
from rl.policy_wolf_controller import SyncedReactiveCoordinator

BEST_4M = "/data/wolves/run06_curric/checkpoints/ppo_wolves_3999936_steps.zip"

def run(seed, kind, model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w); w.reset()
    if len(w.wolf_group_sizes) != 2: return None
    kills = []
    prev_cow = w.cow_alive.copy(); prev_calf = w.calf_alive.copy() if w.n_calves>0 else None
    while True:
        # estado PRE-paso
        act = w.drones[w.drone_state == ACTIVE]
        wolves_pre = np.asarray(w.wolves, float)
        _o,_r,term,trunc,_i = w.step(coord.act(w.get_observation()))
        died = []
        for i in np.where(prev_cow & ~w.cow_alive)[0]: died.append(w.cows[i])
        prev_cow = w.cow_alive.copy()
        if prev_calf is not None:
            for i in np.where(prev_calf & ~w.calf_alive)[0]: died.append(w.calves[i])
            prev_calf = w.calf_alive.copy()
        if died and act.shape[0] > 0:
            wolves_now = np.asarray(w.wolves, float)
            for pos in died:
                ki = int(np.linalg.norm(wolves_now - pos, axis=1).argmin())
                dmin = float(np.linalg.norm(act - wolves_now[ki], axis=1).min())   # dron ACTIVE más cercano al matador
                # distancia del dron más cercano a la PRESA (la res que cae)
                dprey = float(np.linalg.norm(act - pos, axis=1).min())
                kills.append({"d_killer_dron": dmin, "d_presa_dron": dprey,
                              "visto": dmin <= w.r_detect, "disuadible": dmin <= DETER_RADIUS,
                              "pared": dmin <= STATIC_DETER_RADIUS})
        if term or trunc: break
    return kills

def main():
    from stable_baselines3 import PPO
    m4 = PPO.load(BEST_4M, device="cpu")
    for name, model in (("SCRIPTED", None), ("BEST 4M", m4)):
        allk = []; neps = 0
        for kind in ("lobos","mixto"):
            for s in range(60):
                r = run(s, kind, model)
                if r is None: continue
                neps += 1; allk.extend(r)
                if neps >= 24: break
        if not allk:
            print(name, "sin muertes"); continue
        dk = np.array([k["d_killer_dron"] for k in allk])
        dp = np.array([k["d_presa_dron"] for k in allk])
        print(f"\n===== {name}: {len(allk)} muertes en {neps} episodios de 2 subgrupos =====")
        print(f"  dist MATADOR -> dron ACTIVE más cercano: media {dk.mean():.0f} m (min {dk.min():.0f}, máx {dk.max():.0f}, mediana {np.median(dk):.0f})")
        print(f"  dist PRESA (res que cae) -> dron más cercano: media {dp.mean():.0f} m")
        print(f"  %% muertes VISTAS (matador <= r_detect=100): {100*np.mean([k['visto'] for k in allk]):.0f}%")
        print(f"  %% muertes con un dron A TIRO DE DISUASIÓN del matador (<= DETER_RADIUS=20): {100*np.mean([k['disuadible'] for k in allk]):.0f}%")
        print(f"  %% muertes con el matador dentro de la PARED (<= {STATIC_DETER_RADIUS:.0f}): {100*np.mean([k['pared'] for k in allk]):.0f}%")
        print(f"  -> lectura: si VISTAS~100%% pero A-TIRO-DE-DISUASIÓN bajo => 'visto pero NO disuadido' (r_detect 100 >> DETER 20); el cebo 'no visto' es imposible: la zona de matanza siempre se ve")

if __name__ == "__main__":
    main()
