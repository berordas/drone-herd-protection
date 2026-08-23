"""v25_cebo_diag.py — DIAGNÓSTICO de SOLO LECTURA (no toca el repo): ¿engaña el cebo a la barrera reactiva?

Pregunta: con spawn "grouped" (v2.5) y 2 subgrupos separados, ¿la barrera del ReactiveCoordinator
se PARTE para cubrir ambos frentes, sigue al centroide (desviable por un cebo), o se ancla a las vacas?

Fase A: escanea las 100 semillas del arnés (kind="lobos", CONFIG_V2 grouped) y lista los episodios
        con 2 subgrupos (tamaños, separación angular).
Fase B: corre N episodios ilustrativos con ReactiveCoordinator + ScriptedWolfController e instrumenta
        por paso (sin modificar nada; replica en local la geometría de coordinators._barrier):
        - reparto de drones libres por frente (asignación al centroide de grupo más cercano)
        - cobertura de disuasión por grupo (lobos con un dron libre a <= DETER_RADIUS)
        - rama de la barrera (CLEAN vs PENETRADO) y desalineación del eje respecto a cada frente
        - muertes atribuidas al grupo del lobo más cercano a la res muerta
        - severidad del MISMO seed con spawn clustered (contraste)
Salida: informe por texto. Script desechable (/data/wolves/diag/), nada se escribe en el repo.
"""
from __future__ import annotations

import sys
import numpy as np

sys.path.insert(0, "/workspace")

from world import World, ACTIVE, DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import CONFIG_V2

SEP_FRONTS = 60.0     # m: separación entre centroides de grupo para considerar "2 frentes" vivos
N_EPISODES = 5        # episodios ilustrativos


def build(seed, mode):
    cfg = dict(CONFIG_V2)
    cfg["wolf_spawn_mode"] = mode
    return World(seed=seed, episode_kind="lobos", **cfg)


def ang_deg(a):
    return np.degrees((a + np.pi) % (2 * np.pi) - np.pi)


# ---------------------------------------------------------------- Fase A: escaneo
print("=== FASE A: escaneo de las 100 semillas del arnés (kind=lobos, grouped) ===")
two_group = []
for s in range(100):
    w = build(s, "grouped")
    w.reset()
    if len(w.wolf_group_sizes) == 2:
        sep = abs(ang_deg(w.wolf_spawn_angles[1] - w.wolf_spawn_angles[0]))
        two_group.append((s, w.n_wolves, tuple(w.wolf_group_sizes), sep))
print("  episodios con 2 grupos: %d/100" % len(two_group))
for s, nw, sizes, sep in two_group:
    print("    seed %3d  n_wolves=%d  grupos=%s  sep=%5.1f°" % (s, nw, str(sizes), sep))

# Selección ilustrativa: prioriza cebo (grupo de 1) con mucha separación + variedad de repartos.
two_group.sort(key=lambda t: (-(1 in t[2]), -t[3]))
picked, seen_kinds = [], set()
for s, nw, sizes, sep in two_group:
    kind = (min(sizes), max(sizes))
    if kind in seen_kinds and len(picked) >= 3:
        continue
    picked.append((s, nw, sizes, sep))
    seen_kinds.add(kind)
    if len(picked) == N_EPISODES:
        break
print("  seleccionados: %s" % ", ".join("seed %d %s sep %.0f°" % (s, str(sz), sep) for s, _, sz, sep in picked))


# ---------------------------------------------------------------- Fase B: instrumentación
def live_herd(w):
    parts = []
    m = w.cow_alive & ~w.cow_safe
    if m.any():
        parts.append(w.cows[m])
    if w.n_calves > 0:
        mc = w.calf_alive & ~w.calf_safe
        if mc.any():
            parts.append(w.calves[mc])
    return np.vstack(parts) if parts else np.zeros((0, 2))


def run_instrumented(seed):
    w = build(seed, "grouped")
    coord = ReactiveCoordinator(w)
    w.reset()
    n1, _k2 = w.wolf_group_sizes
    g1 = np.arange(0, n1)                      # grupo 1 = primeros n-k índices
    g2 = np.arange(n1, w.n_wolves)             # grupo 2 = últimos k (v2.5 _split_wolves_groups)
    sizes = tuple(w.wolf_group_sizes)
    sep0 = abs(ang_deg(w.wolf_spawn_angles[1] - w.wolf_spawn_angles[0]))

    # acumuladores mientras hay 2 frentes separados (> SEP_FRONTS)
    stats = dict(steps_escolta=0, steps_2fronts=0, steps_pen=0,
                 assign1=0.0, assign2=0.0, cover1=0.0, cover2=0.0,
                 axis_err1=[], axis_err2=[], merge_step=None)
    kills = []                                 # (step, tipo, grupo_killer, d_dron_libre_mas_cercano, asignados_a_su_grupo)
    prev_cow_alive = w.cow_alive.copy()
    prev_calf_alive = w.calf_alive.copy() if w.n_calves > 0 else None

    while True:
        # ---- estado en la FRONTERA (antes de actuar), solo lectura ----
        wolves = np.asarray(w.wolves, dtype=float)
        c1, c2 = wolves[g1].mean(axis=0), wolves[g2].mean(axis=0)
        d_fronts = float(np.linalg.norm(c1 - c2))
        if stats["merge_step"] is None and d_fronts < 40.0 and w.step_count > 0:
            stats["merge_step"] = w.step_count
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        fidx = np.where(free)[0]
        herd = live_herd(w)

        two_fronts = d_fronts > SEP_FRONTS
        in_escolta = (w.phase == "ESCOLTA" and herd.shape[0] > 0)
        if in_escolta:
            stats["steps_escolta"] += 1
        assigned1 = assigned2 = 0
        if fidx.size > 0:
            dr = w.drones[fidx]
            dd1 = np.linalg.norm(dr - c1, axis=1)
            dd2 = np.linalg.norm(dr - c2, axis=1)
            assigned1 = int((dd1 <= dd2).sum())
            assigned2 = int((dd1 > dd2).sum())
        if in_escolta and two_fronts:
            stats["steps_2fronts"] += 1
            stats["assign1"] += assigned1
            stats["assign2"] += assigned2
            if fidx.size > 0:
                dw = np.linalg.norm(wolves[:, None, :] - w.drones[fidx][None, :, :], axis=2)
                covered = (dw <= DETER_RADIUS).any(axis=1)
                stats["cover1"] += covered[g1].mean()
                stats["cover2"] += covered[g2].mean()
            # réplica local de _barrier: ¿rama y eje?
            pack_c = wolves.mean(axis=0)
            herd_c = herd.mean(axis=0)
            herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
            if float(np.linalg.norm(pack_c - herd_c)) <= herd_r:
                stats["steps_pen"] += 1
            else:
                k = max(fidx.size, 1)
                nfront = max(2, k)
                order = np.argsort(np.linalg.norm(herd - pack_c, axis=1))
                front_c = herd[order[:nfront]].mean(axis=0)
                u = pack_c - front_c
                au = np.arctan2(u[1], u[0])
                a1 = np.arctan2(*(c1 - front_c)[::-1])
                a2 = np.arctan2(*(c2 - front_c)[::-1])
                stats["axis_err1"].append(abs(ang_deg(a1 - au)))
                stats["axis_err2"].append(abs(ang_deg(a2 - au)))

        # ---- actuar y avanzar ----
        actions = coord.act(w.get_observation())
        _o, _r, term, trunc, _i = w.step(actions)

        # ---- muertes de este paso, atribuidas al grupo del lobo más cercano ----
        died = []
        new_cow = w.cow_alive
        for i in np.where(prev_cow_alive & ~new_cow)[0]:
            died.append(("vaca", w.cows[i]))
        prev_cow_alive = new_cow.copy()
        if prev_calf_alive is not None:
            new_calf = w.calf_alive
            for i in np.where(prev_calf_alive & ~new_calf)[0]:
                died.append(("ternero", w.calves[i]))
            prev_calf_alive = new_calf.copy()
        for tipo, pos in died:
            wolves_now = np.asarray(w.wolves, dtype=float)
            killer = int(np.linalg.norm(wolves_now - pos, axis=1).argmin())
            kg = 1 if killer < n1 else 2
            d_drone = float(np.linalg.norm(w.drones[fidx] - wolves_now[killer], axis=1).min()) if fidx.size else np.inf
            kills.append((w.step_count, tipo, kg, d_drone, assigned1 if kg == 1 else assigned2, d_fronts))
        if term or trunc:
            break

    return dict(seed=seed, sizes=sizes, sep0=sep0, status=w.status, steps=int(w.step_count),
                n_depredadas=int(w.n_depredadas), n_safe=int(w.cow_safe.sum() + w.calf_safe.sum()),
                stats=stats, kills=kills)


def run_plain(seed, mode):
    w = build(seed, mode)
    coord = ReactiveCoordinator(w)
    w.reset()
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        if term or trunc:
            break
    return int(w.n_depredadas), w.status


print()
print("=== FASE B: episodios instrumentados (ReactiveCoordinator, grouped) ===")
for s, nw, sizes, sep in picked:
    r = run_instrumented(s)
    st = r["stats"]
    n2f = max(st["steps_2fronts"], 1)
    kc, kstat = run_plain(s, "clustered")
    print()
    print("--- seed %d · grupos %s · sep spawn %.0f° · %s en %d pasos · sev=%d (clustered mismo seed: %d, %s) · n_safe=%d"
          % (s, str(r["sizes"]), r["sep0"], r["status"], r["steps"], r["n_depredadas"], kc, kstat, r["n_safe"]))
    print("    ESCOLTA %d pasos · con 2 FRENTES separados (>%.0f m): %d pasos · fusión de grupos (<40 m): %s"
          % (st["steps_escolta"], SEP_FRONTS, st["steps_2fronts"],
             ("paso %d" % st["merge_step"]) if st["merge_step"] is not None else "nunca"))
    if st["steps_2fronts"] > 0:
        print("    reparto medio de drones libres (asignados al frente más cercano): G1=%.2f  G2=%.2f  (de ~4)"
              % (st["assign1"] / n2f, st["assign2"] / n2f))
        print("    cobertura de disuasión media (frac. lobos del grupo con dron libre a <=%.0f m): G1=%.2f  G2=%.2f"
              % (DETER_RADIUS, st["cover1"] / n2f, st["cover2"] / n2f))
        print("    rama PENETRADO en %d/%d pasos de 2-frentes (%.0f%%)"
              % (st["steps_pen"], st["steps_2fronts"], 100.0 * st["steps_pen"] / n2f))
        if st["axis_err1"]:
            print("    rama CLEAN: desalineación del EJE de la barrera vs cada frente: |eje-G1|=%.0f°  |eje-G2|=%.0f° (medias)"
              % (float(np.mean(st["axis_err1"])), float(np.mean(st["axis_err2"]))))
    if r["kills"]:
        for step, tipo, kg, dd, asg, dfr in r["kills"]:
            print("    MUERTE paso %5d: %s por G%d · dron libre más cercano al killer: %5.1f m · drones asignados a su frente: %d · sep frentes: %5.1f m"
                  % (step, tipo, kg, dd, asg, dfr))
    else:
        print("    sin muertes")

print()
print("=== fin del diagnóstico (solo lectura) ===")
