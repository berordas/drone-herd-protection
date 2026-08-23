"""cebo_masa_diag.py — SOLO LECTURA (desechable): ¿el cebo no rinde por el REPARTO DE MASA aleatorio?

Hipótesis del usuario: el reparto cebo/asalto es aleatorio (v2.5: k~unif{1..n-1}) → a menudo el
CEBO (1er sector, presa común) sale GRANDE y el ASALTO (2º sector, presa libre) PEQUEÑO (4+1) y
llega sin quórum. Un cebo debería ser POCOS lobos (ideal 1) y el asalto el grueso.

Mide por episodio (scriptado v2.9 vs ReactiveCoordinator, mismo bucle que el arnés):
  - reparto (n1=cebo, n2=asalto), severidad, muertes del asalto (is_pack_prey2 / flanqueadores s2)
  - llegada del asalto (min dist de cada lobo s2 a prey2; paso de 1ª llegada a <=6 y <=3)
  - quórum del asalto (máx nº simultáneo de lobos s2 a <=capture_radius de prey2, sin susto/pared)
  - anclaje: ¿el ancla de la barrera es del sector 1?; ventana del asalto (s2 sin confirmar);
    orientación de la línea (bearing centro-línea vs centroide s1 vs s2 desde el rebaño)
  - libertad de prey2: dist al ACTIVE más cercano AL FIJAR vs al LLEGAR (¿deja de ser libre?)
Cruce final: reparto × ¿cundió el cebo?  +  ¿basta cebo de 1 para anclar?
Nada del repo se toca; JSON a /data/wolves/diag/cebo_masa_diag.json; GIFs en pasada aparte.
"""
import sys, json
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator
from world import ACTIVE

R_CONTACT = 6.0    # r_face_safe: "llega al contacto" (anillo de standoff de la caza)
R_ATTACK = 3.0     # capture_radius: "a distancia de ataque"


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def scan_seeds(n_scan=400):
    """Catálogo barato: reset sin pasos, reparto (n1, n2) de los episodios grouped de 2 subgrupos."""
    cat = []
    for s in range(n_scan):
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 2:
            cat.append({"seed": s, "n1": int(w.wolf_group_sizes[0]), "n2": int(w.wolf_group_sizes[1]),
                        "n": int(w.n_wolves), "n_calves": int(w.calf_alive.sum())})
    return cat


def run_instrumented(seed):
    w = build_world(seed, "lobos")
    coord = ReactiveCoordinator(w)
    w.reset()
    n = int(w.n_wolves)
    n1, n2 = (int(x) for x in w.wolf_group_sizes)
    s2 = np.arange(n1, n)

    esc = 0                       # pasos en ESCOLTA
    anchor_s1 = anchor_s2 = 0     # sector del ancla (pasos con ancla)
    s2_free_steps = 0             # ventana del asalto: >=1 de s1 confirmado y NINGUNO de s2
    err_line_s1, err_line_s2 = [], []   # |bearing(centro línea) - bearing(centroide sector)| desde el rebaño
    d_drone_s2 = []               # dist mínima de un dron ACTIVE al centroide del asalto
    s2_scared_frac = []           # fracción de lobos s2 asustados/amurallados por paso
    dmin_s2 = np.full(n2, np.inf)  # min dist de cada lobo s2 a prey2 (a lo largo del episodio)
    arrive6 = arrive3 = None      # paso de 1ª llegada del asalto a <=6 / <=3 de prey2
    quorum_max = 0                # máx lobos s2 simultáneos a <=3 de prey2 sin susto/pared
    commits = []                  # por cada fijación de prey2: paso, kind, idx, libertad (dist al ACTIVE + cercano)
    free_at_arrive = None         # libertad de prey2 en el paso de 1ª llegada (<=6)
    prev_prey2 = -1
    conf_first_s1 = conf_first_s2 = None   # paso de 1ª confirmación de cada sector

    while True:
        wp = coord.act(w.get_observation())
        conf = coord._confirmed.copy() if coord._confirmed is not None else np.zeros(n, bool)
        anchor = coord._anchor
        _o, _r, term, trunc, _i = w.step(wp)

        if conf[:n1].any() and conf_first_s1 is None:
            conf_first_s1 = int(w.step_count)
        if n2 > 0 and conf[n1:].any() and conf_first_s2 is None:
            conf_first_s2 = int(w.step_count)

        if w.phase == "ESCOLTA":
            esc += 1
            if anchor is not None:
                if anchor < n1:
                    anchor_s1 += 1
                else:
                    anchor_s2 += 1
            if conf[:n1].any() and not conf[n1:].any():
                s2_free_steps += 1

            # orientación de la línea (waypoints recién emitidos a los ACTIVE libres)
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            herd_pts = [w.cows[w.cow_alive & ~w.cow_safe]]
            if w.n_calves > 0:
                herd_pts.append(w.calves[w.calf_alive & ~w.calf_safe])
            herd_pts = np.vstack([p for p in herd_pts if p.shape[0] > 0]) if any(
                p.shape[0] > 0 for p in herd_pts) else None
            if free.any() and herd_pts is not None and anchor is not None:
                hc = herd_pts.mean(axis=0)
                lc = wp[free].mean(axis=0)
                b_line = np.arctan2(*(lc - hc)[::-1])
                b_s1 = np.arctan2(*(w.wolves[:n1].mean(axis=0) - hc)[::-1])
                err_line_s1.append(abs(wrap(b_line - b_s1)))
                if n2 > 0:
                    b_s2 = np.arctan2(*(w.wolves[n1:].mean(axis=0) - hc)[::-1])
                    err_line_s2.append(abs(wrap(b_line - b_s2)))

            act_dr = w.drones[w.drone_state == ACTIVE]
            if n2 > 0 and act_dr.shape[0] > 0:
                d_drone_s2.append(float(np.linalg.norm(
                    act_dr - w.wolves[n1:].mean(axis=0), axis=1).min()))
            if n2 > 0:
                s2_scared_frac.append(float(
                    (w._wolf_scared[n1:] | w._wolf_walled[n1:]).mean()))

        # presa del asalto: fijaciones + llegada + quórum + libertad
        p2, k2 = int(w.pack_prey2), w.pack_prey2_kind
        act_dr = w.drones[w.drone_state == ACTIVE]
        if p2 >= 0:
            pos2 = w.calves[p2] if k2 == "calf" else w.cows[p2]
            if p2 != prev_prey2:
                libertad = float(np.linalg.norm(act_dr - pos2, axis=1).min()) if act_dr.shape[0] else None
                commits.append({"step": int(w.step_count), "kind": k2, "idx": p2, "libertad_fijar": libertad})
            d2 = np.linalg.norm(w.wolves[n1:] - pos2, axis=1)
            dmin_s2 = np.minimum(dmin_s2, d2)
            if arrive6 is None and (d2 <= R_CONTACT).any():
                arrive6 = int(w.step_count)
                free_at_arrive = float(np.linalg.norm(act_dr - pos2, axis=1).min()) if act_dr.shape[0] else None
            if arrive3 is None and (d2 <= R_ATTACK).any():
                arrive3 = int(w.step_count)
            q = int(((d2 <= R_ATTACK) & ~w._wolf_scared[n1:] & ~w._wolf_walled[n1:]).sum())
            quorum_max = max(quorum_max, q)
        prev_prey2 = p2

        if term or trunc:
            break

    # clasificación de muertes por sector de los flanqueadores
    kills_prey2 = sum(1 for c in w.captures if c.get("is_pack_prey2"))
    kills_s2 = sum(1 for c in w.captures if c["flankers"] and min(c["flankers"]) >= n1)
    kills_s1 = sum(1 for c in w.captures if c["flankers"] and max(c["flankers"]) < n1)
    kills_mix = int(w.n_depredadas) - kills_s2 - kills_s1

    return {
        "seed": seed, "n": n, "n1": n1, "n2": n2, "reparto": f"{n1}+{n2}",
        "n_calves": int(w.calf_alive.sum() + (~w.calf_alive).sum()) if w.n_calves else 0,
        "sev": int(w.n_depredadas), "status": w.status, "steps": int(w.step_count), "esc_steps": esc,
        "kills_prey2": kills_prey2, "kills_s2": kills_s2, "kills_s1": kills_s1, "kills_mix": kills_mix,
        "cundio": bool(kills_prey2 > 0 or kills_s2 > 0),
        "anchor_s1_frac": round(anchor_s1 / max(anchor_s1 + anchor_s2, 1), 3),
        "s2_free_frac_esc": round(s2_free_steps / max(esc, 1), 3),
        "conf_first_s1": conf_first_s1, "conf_first_s2": conf_first_s2,
        "err_line_s1_deg": round(float(np.degrees(np.mean(err_line_s1))), 1) if err_line_s1 else None,
        "err_line_s2_deg": round(float(np.degrees(np.mean(err_line_s2))), 1) if err_line_s2 else None,
        "d_drone_s2_min": round(min(d_drone_s2), 1) if d_drone_s2 else None,
        "s2_scared_frac": round(float(np.mean(s2_scared_frac)), 3) if s2_scared_frac else None,
        "prey2_commits": commits,
        "dmin_s2": [round(float(x), 1) for x in dmin_s2],
        "n_llegan6": int((dmin_s2 <= R_CONTACT).sum()), "n_llegan3": int((dmin_s2 <= R_ATTACK).sum()),
        "paso_llegada6": arrive6, "paso_llegada3": arrive3,
        "quorum_max": quorum_max, "libertad_al_llegar": free_at_arrive,
        "captures": [{k: c[k] for k in ("step", "kind", "prey_idx", "flankers", "is_pack_prey", "is_pack_prey2")}
                     for c in w.captures],
    }


if __name__ == "__main__":
    cat = scan_seeds(400)
    from collections import Counter, defaultdict
    print(f"catalogo: {len(cat)} episodios grouped-2 en 400 semillas 'lobos'")
    print("repartos:", dict(Counter(f"{c['n1']}+{c['n2']}" for c in cat)))

    # selección: prioriza n=5 (los 4 repartos canónicos), completa con n=4/3; ~5 por clase de asalto
    by_rep = defaultdict(list)
    for c in cat:
        by_rep[(c["n1"], c["n2"])].append(c["seed"])
    chosen = []
    for rep in [(1, 4), (2, 3), (3, 2), (4, 1)]:          # n=5: TODAS las semillas del catálogo
        chosen += [(s, rep) for s in by_rep.get(rep, [])[:10]]
    for rep in [(1, 3), (3, 1), (1, 2), (2, 1), (2, 2)]:  # n=4 y n=3 (cobertura)
        chosen += [(s, rep) for s in by_rep.get(rep, [])[:1]]
    print(f"seleccionados {len(chosen)} episodios:", [(s, f"{a}+{b}") for s, (a, b) in chosen])

    rows = []
    for s, rep in chosen:
        r = run_instrumented(s)
        rows.append(r)
        print(f"  seed={s:3d} {r['reparto']}  sev={r['sev']} status={r['status']:9s} "
              f"kills_prey2={r['kills_prey2']} kills_s2={r['kills_s2']} "
              f"llegan6={r['n_llegan6']}/{r['n2']} quorum_max={r['quorum_max']} "
              f"ancla_s1={r['anchor_s1_frac']} ventana_s2libre={r['s2_free_frac_esc']}", flush=True)

    json.dump({"catalogo": cat, "episodios": rows}, open("/data/wolves/diag/cebo_masa_diag.json", "w"), indent=1)
    print("JSON -> /data/wolves/diag/cebo_masa_diag.json")
    print("DIAG_LISTO")
