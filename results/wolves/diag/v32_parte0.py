"""v32_parte0.py — DIAGNÓSTICOS Parte 0 de v3.2 (SOLO LECTURA, sobre v3.1 HEAD).

DIAG A (arreglos 1+2): ¿por qué la barrera se ve QUIETA y los lobos se cuelan?
  - fracción de pasos de ESCOLTA con los drones de barrera casi parados (< 0.3 y < 1.0 m/s
    = SCARE_APPROACH_MIN: un dron más lento que eso JAMÁS expulsa);
  - saturación del tope: fracción de pasos CLEAN con adv == advance_max (la línea clavada
    en el tope, sin perseguir al lobo que está más lejos);
  - CRUCES de la línea: lobo que pasa de proj>=adv a proj<adv dentro del ancho de la línea,
    clasificado por si ALGUNA VEZ estuvo a <= DETER_RADIUS de un ACTIVE (contacto) o no (LIMPIO);
  - encuentros SILENCIOSOS: pasos con un lobo a <= DETER_RADIUS de un ACTIVE sin susto ni pared
    (el "está al lado y no suena" del usuario).

DIAG B (arreglo 3): LA MÉTRICA CORRECTA del timing — en el instante EXACTO en que salta
  ESCOLTA, distancia del centroide del ASALTO a su presa (pack_prey2) y al rebaño; quién fue
  el confirmado (cebo o asalto) y si el disparo del cebo (released) ya había ocurrido.
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import build_world

SCARE_APPROACH_MIN = 1.0


def clean_line(w, coord):
    """Reconstruye la geometría CLEAN de la barrera v3.1 (front_c, u, adv, semiancho) o None."""
    free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
    idx = np.where(free)[0]
    if w.phase != "ESCOLTA" or coord._anchor is None or idx.size == 0:
        return None
    herd = coord._live_herd()
    if herd.shape[0] == 0:
        return None
    pack_c = np.asarray(w.wolves[coord._anchor], float)
    herd_c = herd.mean(axis=0)
    herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
    if float(np.linalg.norm(pack_c - herd_c)) <= herd_r:
        return None  # PENETRADO
    k = idx.size
    nfront = max(2, k)
    order = np.argsort(np.linalg.norm(herd - pack_c, axis=1))
    front_c = herd[order[:nfront]].mean(axis=0)
    u = pack_c - front_c
    L = float(np.linalg.norm(u))
    u = u / max(L, 1e-9)
    adv = float(np.clip(L + 10.0, coord.barrier_standoff, coord.advance_max))
    half = (k - 1) / 2.0 * coord.drone_spacing + coord.drone_spacing / 2.0
    return front_c, u, adv, half, L, herd_c, idx


def diag_A(seeds, kinds):
    print("=== DIAG A: barrera quieta + huecos (v3.1 tal cual) ===")
    tot = dict(esc_steps=0, slow03=0, slow10=0, clean_steps=0, sat=0,
               cross_clean=0, cross_touch=0, silent=0, close=0, deaths=0, eps=0)
    dists_fc = []
    for kind in kinds:
        for s in seeds:
            w = build_world(s, kind)
            w.reset()
            coord = ReactiveCoordinator(w)
            prev_drones = w.drones.copy()
            prev_proj = None       # proyección de cada lobo sobre u (paso previo, mismo frame no — se recalcula)
            ever_deter = np.zeros(w.n_wolves, dtype=bool)
            prev_line = None
            while True:
                a = coord.act(w.get_observation())
                _, _, term, trunc, _ = w.step(a)
                # contacto de disuasión (tras el step: flags del paso)
                act_dr = w.drones[w.drone_state == ACTIVE]
                if act_dr.shape[0] > 0 and w.n_wolves > 0:
                    dmin = np.linalg.norm(w.wolves[:, None, :] - act_dr[None, :, :], axis=2).min(axis=1)
                    close = dmin <= DETER_RADIUS
                    ever_deter |= close
                    silent = close & ~w._wolf_scared & ~w._wolf_walled
                    tot["close"] += int(close.sum()); tot["silent"] += int(silent.sum())
                line = clean_line(w, coord)
                if w.phase == "ESCOLTA":
                    free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
                    if free.any():
                        sp = np.linalg.norm(w.drones[free] - prev_drones[free], axis=1) / w.dt
                        tot["esc_steps"] += 1
                        if sp.mean() < 0.3: tot["slow03"] += 1
                        if sp.mean() < SCARE_APPROACH_MIN: tot["slow10"] += 1
                if line is not None:
                    front_c, u, adv, half, L, herd_c, idx = line
                    tot["clean_steps"] += 1
                    if adv >= coord.advance_max - 1e-9: tot["sat"] += 1
                    dists_fc.append(float(np.linalg.norm(front_c - herd_c)))
                    proj = (w.wolves - front_c) @ u
                    lat = np.abs((w.wolves - front_c) @ np.array([-u[1], u[0]]))
                    if prev_line is not None and prev_proj is not None:
                        crossed = (prev_proj >= adv) & (proj < adv) & (lat <= half)
                        for j in np.where(crossed)[0]:
                            if ever_deter[j]: tot["cross_touch"] += 1
                            else: tot["cross_clean"] += 1
                    prev_proj = proj
                else:
                    prev_proj = None
                prev_line = line
                prev_drones = w.drones.copy()
                if term or trunc:
                    break
            tot["deaths"] += int(w.n_depredadas); tot["eps"] += 1
    print(f"  episodios: {tot['eps']}  muertes: {tot['deaths']}")
    print(f"  pasos ESCOLTA: {tot['esc_steps']}  | drones de barrera con vel media < 0.3 m/s: "
          f"{100.0*tot['slow03']/max(tot['esc_steps'],1):.1f}%  | < 1.0 m/s (SCARE_APPROACH_MIN, jamás expulsan): "
          f"{100.0*tot['slow10']/max(tot['esc_steps'],1):.1f}%")
    print(f"  pasos CLEAN: {tot['clean_steps']}  | adv saturado en advance_max: "
          f"{100.0*tot['sat']/max(tot['clean_steps'],1):.1f}%  | dist(front_c, centroide vacas) media: "
          f"{np.mean(dists_fc) if dists_fc else float('nan'):.1f} m")
    print(f"  CRUCES de la línea: LIMPIOS (sin haber tocado radio de disuasión) = {tot['cross_clean']}"
          f"  | con contacto previo = {tot['cross_touch']}")
    print(f"  encuentros SILENCIOSOS (lobo a <=DETER de un ACTIVE sin susto/pared): "
          f"{100.0*tot['silent']/max(tot['close'],1):.1f}% de {tot['close']} pasos-lobo cercanos")


def diag_B(max_seeds=300, want=40):
    print("\n=== DIAG B: timing con LA MÉTRICA CORRECTA (dist del ASALTO al saltar ESCOLTA) ===")
    rows = []
    for kind in ("lobos", "mixto"):
        for s in range(max_seeds):
            if len(rows) >= want and kind == "mixto":
                break
            w = build_world(s, kind)
            w.reset()
            if len(w.wolf_group_sizes) != 2:
                continue
            n1 = int(w.wolf_group_sizes[0])
            coord = ReactiveCoordinator(w)
            released_step = -1
            birth_dmin = None
            act_dr = w.drones[w.drone_state == ACTIVE]
            if act_dr.shape[0] > 0:
                birth_dmin = float(np.linalg.norm(w.wolves[:n1][:, None, :] - act_dr[None, :, :], axis=2).min())
            while True:
                prev_inv = w.drone_investigating.copy()
                a = coord.act(w.get_observation())
                _, _, term, trunc, _ = w.step(a)
                if released_step < 0 and w.wolf_decoy_released:
                    released_step = int(w.step_count)
                if w.phase == "ESCOLTA":
                    assault = w.wolves[n1:]
                    ac = assault.mean(axis=0)
                    if w.pack_prey2 >= 0:
                        p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
                    else:
                        p2 = w.cows[w.cow_alive].mean(axis=0)
                    live = w.cows[w.cow_alive]
                    hc = live.mean(axis=0) if live.shape[0] else np.array([w.W/2, w.H/2])
                    # ¿quién fue confirmado? el cuerpo más cercano al dron que investigaba
                    who = "?"
                    for i in np.where(prev_inv)[0]:
                        dwolves = np.linalg.norm(w.wolves - w.drones[i], axis=1)
                        j = int(np.argmin(dwolves))
                        if dwolves[j] <= w.r_confirm + 2.0:
                            who = "cebo" if j < n1 else "asalto"
                    rows.append(dict(kind=kind, seed=s, nw=int(w.n_wolves), n1=n1,
                                     step=int(w.step_count), released=released_step >= 0,
                                     rel_step=released_step, who=who,
                                     d_prey=float(np.linalg.norm(ac - p2)),
                                     d_herd=float(np.linalg.norm(ac - hc)),
                                     birth_dmin=birth_dmin))
                    break
                if term or trunc:
                    break
    d_prey = np.array([r["d_prey"] for r in rows])
    ok = (d_prey <= 150.0)
    print(f"  episodios 2-frentes con ESCOLTA: {len(rows)}")
    print(f"  dist ASALTO->presa al saltar ESCOLTA: media {d_prey.mean():.0f}  mediana {np.median(d_prey):.0f}"
          f"  rango [{d_prey.min():.0f}, {d_prey.max():.0f}]")
    print(f"  <=150 m (VARA del usuario): {int(ok.sum())}/{len(rows)} = {100.0*ok.mean():.0f}%")
    from collections import Counter
    print(f"  confirmado 1º: {dict(Counter(r['who'] for r in rows))}")
    print(f"  released ya disparado al saltar ESCOLTA: {sum(r['released'] for r in rows)}/{len(rows)}")
    for r in sorted(rows, key=lambda r: -r["d_prey"])[:12]:
        print(f"    {r['kind']}/s{r['seed']}: d_prey={r['d_prey']:.0f} d_herd={r['d_herd']:.0f} "
              f"who={r['who']} released={r['released']} (rel_step={r['rel_step']}, esc_step={r['step']}) "
              f"n={r['nw']} cebo={r['n1']} birth_dmin={r['birth_dmin']:.0f}")


if __name__ == "__main__":
    diag_A(seeds=range(12), kinds=("lobos", "mixto"))
    diag_B()
