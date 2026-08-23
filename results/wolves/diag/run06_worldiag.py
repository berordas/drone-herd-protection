"""run06_worldiag.py — DIAGNÓSTICO SOLO LECTURA: ¿por qué no emerge el cebo? (mundo vs RL)

Corre episodios grouped de 2 subgrupos con DOS controladores sobre las MISMAS semillas:
(a) scriptado (δ=0 vía ResidualWolfController(model=None)) y (b) el mejor ckpt de run06 (4M).
Instrumenta por paso EN SOLO LECTURA (no toca el mundo) las 4 hipótesis A/B/C/D + el reparto
de la disuasión por frente. Nada se escribe en el repo. JSON + prints a /data.
"""
import sys, json; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from world import ACTIVE, STATIC_DETER_RADIUS, DETER_RADIUS
from rl.residual_wolf_controller import ResidualWolfController
from rl.policy_wolf_controller import SyncedReactiveCoordinator

BEST_4M = "/data/wolves/run06_curric/checkpoints/ppo_wolves_3999936_steps.zip"
N_SCAN = 34                      # semillas a barrer para juntar ~12-15 episodios de 2 subgrupos
KIND = "lobos"
FRONT_SEP = 60.0                 # m: umbral de "2 frentes reales" (= WOLF_GROUP_MIN_ANGLE_SEP en distancia)
GRID = 50                        # resolución del muestreo de cobertura del campo


def detected_mask(w):
    flying = w.drones[w.drone_state == ACTIVE]
    if flying.shape[0] == 0 or w.n_wolves == 0:
        return np.zeros(w.n_wolves, bool)
    d = np.linalg.norm(np.asarray(w.wolves, float)[:, None, :] - flying[None, :, :], axis=2)
    return (d <= w.r_detect).any(axis=1)


def nearest_active_dist(w):
    act = w.drones[w.drone_state == ACTIVE]
    if act.shape[0] == 0:
        return np.full(w.n_wolves, np.inf)
    d = np.linalg.norm(np.asarray(w.wolves, float)[:, None, :] - act[None, :, :], axis=2)
    return d.min(axis=1)


def field_coverage(w):
    """% del campo dentro de r_detect de algún dron ACTIVE (grid GRID×GRID)."""
    act = w.drones[w.drone_state == ACTIVE]
    if act.shape[0] == 0:
        return 0.0
    xs = np.linspace(0, w.W, GRID); ys = np.linspace(0, w.H, GRID)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    d = np.linalg.norm(pts[:, None, :] - act[None, :, :], axis=2)
    return float((d.min(axis=1) <= w.r_detect).mean())


def run(seed, model):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, KIND, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n = w.n_wolves; n1 = int(w.wolf_group_sizes[0])
    g1 = np.arange(0, n1); g2 = np.arange(n1, n)
    herd0 = w.cows.mean(0)
    d_spawn = [float(np.linalg.norm(w.wolves[g].mean(0) - herd0)) for g in (g1, g2)]

    scared = np.zeros(n); walled = np.zeros(n); ndist = np.zeros(n); det_steps = np.zeros(n)
    seps = []; two_front_steps = 0; escolta_steps = 0; cov = []
    g_undet_run = 0; g_undet_runs = []           # rachas del 2º frente (el menos anclado) sin ver
    arrival = {1: None, 2: None}                  # paso en que el centroide del grupo llega al rebaño
    arrival_safe = {1: None, 2: None}
    arrival_mass = {1: None, 2: None}             # lobos del grupo dentro de r_notice al llegar
    kills_by_group = {1: 0, 2: 0}
    prev_cow = w.cow_alive.copy(); prev_calf = w.calf_alive.copy() if w.n_calves > 0 else None
    steps = 0
    while True:
        det = detected_mask(w)
        wolves = np.asarray(w.wolves, float)
        c1, c2 = wolves[g1].mean(0), wolves[g2].mean(0)
        sep = float(np.linalg.norm(c1 - c2)); seps.append(sep)
        nd = nearest_active_dist(w)
        escolta = (w.phase == "ESCOLTA")
        if escolta:
            escolta_steps += 1
            if sep > FRONT_SEP: two_front_steps += 1
            cov.append(field_coverage(w))
            det_g = {1: bool(det[g1].any()), 2: bool(det[g2].any())}
            anchor = coord.inner._anchor
            ag = None if anchor is None else (1 if anchor < n1 else 2)
            other = 2 if ag == 1 else 1               # el frente NO anclado (candidato a "no visto")
            if ag is not None and not det_g[other]:
                g_undet_run += 1
            else:
                if g_undet_run > 0: g_undet_runs.append(g_undet_run)
                g_undet_run = 0
        # acumular por lobo
        scared += w._wolf_scared.astype(float)
        walled += w._wolf_walled.astype(float)
        ndist += np.where(np.isinf(nd), 0.0, nd)
        det_steps += det.astype(float)
        # llegada de cada subgrupo al rebaño (centroide a <= cow_spread+r_notice del rebaño VIVO)
        alive_cows = w.cows[w.cow_alive] if w.cow_alive.any() else w.cows
        herd = alive_cows.mean(0)
        reach = w.cow_spread + w.r_notice
        for gi, g in ((1, g1), (2, g2)):
            if arrival[gi] is None and np.linalg.norm(wolves[g].mean(0) - herd) <= reach:
                arrival[gi] = steps
                arrival_safe[gi] = float(w.cow_safe.mean())
                arrival_mass[gi] = int((np.linalg.norm(wolves[g][:, None, :] - alive_cows[None, :, :], axis=2).min(1) <= w.r_notice).sum())

        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        steps += 1
        # muertes de este paso -> grupo del lobo más cercano
        died = []
        for i in np.where(prev_cow & ~w.cow_alive)[0]: died.append(w.cows[i])
        prev_cow = w.cow_alive.copy()
        if prev_calf is not None:
            for i in np.where(prev_calf & ~w.calf_alive)[0]: died.append(w.calves[i])
            prev_calf = w.calf_alive.copy()
        for pos in died:
            k = int(np.linalg.norm(np.asarray(w.wolves, float) - pos, axis=1).argmin())
            kills_by_group[1 if k < n1 else 2] += 1
        if term or trunc: break
    if g_undet_run > 0: g_undet_runs.append(g_undet_run)

    per_wolf = [{"grupo": 1 if i < n1 else 2, "scared": int(scared[i]), "walled": int(walled[i]),
                 "dist_media_dron": round(ndist[i]/max(steps,1), 1),
                 "frac_detectado": round(det_steps[i]/max(steps,1), 2)} for i in range(n)]
    return {
        "seed": seed, "n_wolves": n, "sizes": [n1, n-n1], "status": w.status, "steps": steps,
        "n_depredadas": int(w.n_depredadas), "dist_spawn_rebano": [round(x) for x in d_spawn],
        "sep_media": round(float(np.mean(seps)), 1), "sep_min": round(float(np.min(seps)), 1),
        "sep_t0": round(seps[0], 1), "frac_2frentes_escolta": round(two_front_steps/max(escolta_steps,1), 2),
        "fusion_step": next((k for k in range(len(seps)) if seps[k] < FRONT_SEP), None),
        "cobertura_campo_media": round(float(np.mean(cov)), 3) if cov else None,
        "frac_2ofrente_no_visto": round((sum(g_undet_runs))/max(escolta_steps,1), 2),
        "rachas_no_visto_max": max(g_undet_runs) if g_undet_runs else 0,
        "rachas_no_visto_media": round(float(np.mean(g_undet_runs)), 0) if g_undet_runs else 0,
        "arrival": arrival, "arrival_safe": arrival_safe, "arrival_mass": arrival_mass,
        "kills_by_group": kills_by_group, "per_wolf": per_wolf,
    }


def main():
    from stable_baselines3 import PPO
    model4m = PPO.load(BEST_4M, device="cpu")
    out = {"scripted": [], "best4m": []}
    for seed in range(N_SCAN):
        rs = run(seed, None)
        if rs is None: continue
        rb = run(seed, model4m)
        out["scripted"].append(rs)
        if rb is not None: out["best4m"].append(rb)
        if len(out["scripted"]) >= 14: break
    json.dump(out, open("/data/wolves/diag/run06_worldiag.json", "w"), indent=2, default=str)

    def agg(eps, key, sub=None):
        vals = [(e[key] if sub is None else e[key][sub]) for e in eps if (e[key] if sub is None else e[key][sub]) is not None]
        return float(np.mean(vals)) if vals else None

    for name, eps in (("SCRIPTED (δ=0)", out["scripted"]), ("BEST 4M", out["best4m"])):
        print(f"\n===== {name}  ({len(eps)} episodios de 2 subgrupos) =====")
        print("  severidad media: %.2f | pasos medios: %.0f" % (agg(eps,"n_depredadas"), agg(eps,"steps")))
        print("  A LLEGADA: dist spawn 2 grupos (media): %s m | 2º grupo llega en paso %s (%.0f s); %% vacas a salvo al llegar: %s"
              % ([round(np.mean([e["dist_spawn_rebano"][0] for e in eps])), round(np.mean([e["dist_spawn_rebano"][1] for e in eps]))],
                 round(agg(eps,"arrival",2) or 0), (agg(eps,"arrival",2) or 0)*0.1,
                 round(100*(agg(eps,"arrival_safe",2) or 0))))
        print("  B FUSIÓN: sep media %.0f m (min %.0f, t0 %.0f) | %% pasos 2 frentes reales (>%dm): %.0f%% | fusión de media en paso %s"
              % (agg(eps,"sep_media"), agg(eps,"sep_min"), agg(eps,"sep_t0"), FRONT_SEP,
                 100*agg(eps,"frac_2frentes_escolta"), round(agg(eps,"fusion_step") or 0)))
        print("  C DETECCIÓN: cobertura del campo (r_detect) media %.0f%% | %% pasos ESCOLTA con 2º frente NO visto: %.0f%% | racha no-visto máx %d pasos (%.0f s), media %.0f"
              % (100*(agg(eps,"cobertura_campo_media") or 0), 100*agg(eps,"frac_2ofrente_no_visto"),
                 max(e["rachas_no_visto_max"] for e in eps), max(e["rachas_no_visto_max"] for e in eps)*0.1,
                 agg(eps,"rachas_no_visto_media") or 0))
        mass2 = [e["arrival_mass"][2] for e in eps if e["arrival_mass"][2] is not None]
        print("  D QUÓRUM: masa del 2º grupo al llegar (lobos a <=r_notice): media %.1f (min %d, máx %d); quórum>=2: %.0f%% de las llegadas | reparto de masa (sizes): %s"
              % (np.mean(mass2) if mass2 else 0, min(mass2) if mass2 else 0, max(mass2) if mass2 else 0,
                 100*np.mean([m>=2 for m in mass2]) if mass2 else 0, [e["sizes"] for e in eps]))
        # reparto de disuasión por frente
        sc_g = {1:0,2:0}; wl_g = {1:0,2:0}; det_g = {1:[],2:[]}
        for e in eps:
            for pw in e["per_wolf"]:
                sc_g[pw["grupo"]] += pw["scared"]; wl_g[pw["grupo"]] += pw["walled"]; det_g[pw["grupo"]].append(pw["frac_detectado"])
        print("  DISUASIÓN por frente (grupo1=anclado-primario / grupo2): scared g1=%d g2=%d | walled g1=%d g2=%d | frac_detectado medio g1=%.2f g2=%.2f"
              % (sc_g[1], sc_g[2], wl_g[1], wl_g[2], np.mean(det_g[1]) if det_g[1] else 0, np.mean(det_g[2]) if det_g[2] else 0))
        print("  kills por grupo:", {k: sum(e["kills_by_group"][str(k)] if str(k) in e["kills_by_group"] else e["kills_by_group"][k] for e in eps) for k in (1,2)})
    print("\n  JSON -> /data/wolves/diag/run06_worldiag.json")


if __name__ == "__main__":
    main()
