"""v32_verify.py — MÉTRICAS DESPUÉS de los arreglos v3.2 (mismas varas que v32_parte0.py).

A (arreglos 1+2): huecos + avance.
  - encuentros SILENCIOSOS (lobo <=DETER de un ACTIVE sin susto/pared) — antes 75.4%;
  - CRUCES de la línea sin contacto RECIENTE (<=1 s) de disuasión — antes ~4.6 cruces/ep;
  - formación a <1 m/s en ESCOLTA (incapaz de expulsar) — antes 17.9%;
  - centro de la barrera <= MAX_ADVANCE_FROM_HERD del centroide de vacas (regla del usuario);
  - PERSECUCIÓN: fracción de pasos CLEAN con algún dron cerrando sobre un lobo confirmado a >1 m/s.

B (arreglo 3): al saltar ESCOLTA, dist del ASALTO a su presa (vara <=150) — antes 58%.
"""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, DETER_RADIUS, STATIC_DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import build_world

RECENT = 10  # pasos (1 s) de ventana de "contacto reciente" para clasificar un cruce


def clean_line(w, coord):
    """Geometría CLEAN v3.2: (herd_c, u, aim, semiancho) o None."""
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
    u = pack_c - herd_c
    d_anchor = float(np.linalg.norm(u))
    u = u / max(d_anchor, 1e-9)
    proj_front = float(((herd - herd_c) @ u).max())
    aim = min(d_anchor + STATIC_DETER_RADIUS, coord.max_advance_from_herd)
    aim = max(aim, proj_front + coord.barrier_standoff)
    half = (k - 1) / 2.0 * coord.drone_spacing + coord.drone_spacing / 2.0
    return herd_c, u, aim, half, idx


def diag_A(seeds, kinds):
    print("=== VERIFY A (v3.2): huecos + avance ===")
    tot = dict(esc_steps=0, slow10=0, clean_steps=0, cross_clean=0, cross_touch=0,
               silent=0, close=0, pursuit=0, center_over=0, deaths=0, eps=0)
    center_d = []
    for kind in kinds:
        for s in seeds:
            w = build_world(s, kind)
            w.reset()
            coord = ReactiveCoordinator(w)
            prev_drones = w.drones.copy()
            prev_proj = None
            recent_contact = np.zeros(w.n_wolves, dtype=int)   # pasos desde el último contacto (grande = lejos)
            recent_contact[:] = 10**6
            while True:
                a = coord.act(w.get_observation())
                _, _, term, trunc, _ = w.step(a)
                act_dr = w.drones[w.drone_state == ACTIVE]
                if act_dr.shape[0] > 0 and w.n_wolves > 0:
                    dmin = np.linalg.norm(w.wolves[:, None, :] - act_dr[None, :, :], axis=2).min(axis=1)
                    close = dmin <= DETER_RADIUS
                    touched = close | w._wolf_scared | w._wolf_walled
                    recent_contact = np.where(touched, 0, recent_contact + 1)
                    silent = close & ~w._wolf_scared & ~w._wolf_walled
                    tot["close"] += int(close.sum()); tot["silent"] += int(silent.sum())
                line = clean_line(w, coord)
                if w.phase == "ESCOLTA":
                    free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
                    if free.any():
                        sp = np.linalg.norm(w.drones[free] - prev_drones[free], axis=1) / w.dt
                        tot["esc_steps"] += 1
                        if sp.mean() < 1.0: tot["slow10"] += 1
                        # PERSECUCIÓN: ¿algún dron libre CIERRA sobre un lobo confirmado a >1 m/s?
                        conf = coord._confirmed
                        if conf is not None and conf.any():
                            wc = w.wolves[conf]
                            d0 = np.linalg.norm(prev_drones[free][:, None, :] - wc[None, :, :], axis=2)
                            d1 = np.linalg.norm(w.drones[free][:, None, :] - wc[None, :, :], axis=2)
                            if ((d0 - d1) / w.dt > 1.0).any():
                                tot["pursuit"] += 1
                if line is not None:
                    herd_c, u, aim, half, idx = line
                    tot["clean_steps"] += 1
                    cd = float(np.linalg.norm(w.drones[idx].mean(axis=0) - herd_c))
                    center_d.append(cd)
                    if cd > coord.max_advance_from_herd + coord.drone_spacing:  # holgura: drones EN VUELO hacia la ranura
                        tot["center_over"] += 1
                    proj = (w.wolves - herd_c) @ u
                    lat = np.abs((w.wolves - herd_c) @ np.array([-u[1], u[0]]))
                    if prev_proj is not None:
                        crossed = (prev_proj >= aim) & (proj < aim) & (lat <= half)
                        for jw in np.where(crossed)[0]:
                            if recent_contact[jw] <= RECENT: tot["cross_touch"] += 1
                            else: tot["cross_clean"] += 1
                    prev_proj = proj
                else:
                    prev_proj = None
                prev_drones = w.drones.copy()
                if term or trunc:
                    break
            tot["deaths"] += int(w.n_depredadas); tot["eps"] += 1
    print(f"  episodios: {tot['eps']}  muertes: {tot['deaths']}")
    print(f"  encuentros SILENCIOSOS: {100.0*tot['silent']/max(tot['close'],1):.1f}% de {tot['close']} (antes 75.4%)")
    print(f"  CRUCES: LIMPIOS (sin contacto reciente <=1s) = {tot['cross_clean']}  | con contacto = {tot['cross_touch']} (antes 111 cruces tot.)")
    print(f"  formación <1 m/s en ESCOLTA: {100.0*tot['slow10']/max(tot['esc_steps'],1):.1f}% (antes 17.9%)")
    print(f"  PERSECUCIÓN (algún dron cierra >1 m/s sobre confirmado): {100.0*tot['pursuit']/max(tot['esc_steps'],1):.1f}% de pasos ESCOLTA")
    print(f"  centro de barrera: media {np.mean(center_d):.1f} m del centroide, máx {np.max(center_d):.1f}"
          f"  | pasos con centro > max_advance+spacing: {tot['center_over']} de {tot['clean_steps']}")


def diag_B(max_seeds=300, want=40):
    print("\n=== VERIFY B (v3.2): timing (vara <=150 al saltar ESCOLTA; antes 58%) ===")
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
            while True:
                prev_inv = w.drone_investigating.copy()
                a = coord.act(w.get_observation())
                _, _, term, trunc, _ = w.step(a)
                if released_step < 0 and w.wolf_decoy_released:
                    released_step = int(w.step_count)
                if w.phase == "ESCOLTA":
                    assault = w.wolves[n1:]
                    ac = assault.mean(axis=0)
                    p2 = (w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind) if w.pack_prey2 >= 0
                          else w.cows[w.cow_alive].mean(axis=0))
                    who = "?"
                    for i in np.where(prev_inv)[0]:
                        dw = np.linalg.norm(w.wolves - w.drones[i], axis=1)
                        jw = int(np.argmin(dw))
                        if dw[jw] <= w.r_confirm + 2.0:
                            who = "cebo" if jw < n1 else "asalto"
                    rows.append(dict(kind=kind, seed=s, who=who, released=released_step >= 0,
                                     d_prey=float(np.linalg.norm(ac - p2)), step=int(w.step_count)))
                    break
                if term or trunc:
                    break
    d_prey = np.array([r["d_prey"] for r in rows])
    ok = d_prey <= 150.0
    from collections import Counter
    print(f"  episodios 2-frentes con ESCOLTA: {len(rows)}")
    print(f"  dist ASALTO->presa al saltar ESCOLTA: media {d_prey.mean():.0f}  mediana {np.median(d_prey):.0f}"
          f"  rango [{d_prey.min():.0f}, {d_prey.max():.0f}]")
    print(f"  <=150 m: {int(ok.sum())}/{len(rows)} = {100.0*ok.mean():.0f}%  (antes 45/78 = 58%)")
    print(f"  confirmado 1º: {dict(Counter(r['who'] for r in rows))}  | released ya: {sum(r['released'] for r in rows)}/{len(rows)}")
    for r in sorted(rows, key=lambda r: -r["d_prey"])[:8]:
        print(f"    {r['kind']}/s{r['seed']}: d_prey={r['d_prey']:.0f} who={r['who']} released={r['released']} esc_step={r['step']}")


if __name__ == "__main__":
    import sys as _s
    which = _s.argv[1] if len(_s.argv) > 1 else "AB"
    if "A" in which:
        diag_A(seeds=range(12), kinds=("lobos", "mixto"))
    if "B" in which:
        diag_B()
