"""forense_e01.py — FORENSE (solo lectura, replay determinista) de los GIFs 1 y 2 de e01
(seed 398 mixto: G/CEBO_keep vs MASA, ambos vs Reactive). Reconstruye por tick el estado
del coordinador (ancla, pose C/φ, PENETRADO, asignación dron→ranura, investigador, INCOMING)
y de la percepción (detectados/confirmados por lobo), y detecta:
  A) cadena de detección/confirmación: quién fue detectado/confirmado primero, ticks;
  B) APILAMIENTO: pares de drones ACTIVE a < STACK_M entre sí, con la explicación
     mecánica (rama del coordinador, ranuras asignadas, investigación, hand-off);
  C) CRUCES del corredor (seg_cross entre drones libres contiguos, hacia el rebaño) con la
     mecánica en el tick del cruce: dist al dron más cercano, approach de ese dron,
     |empuje de pared|, scared/walled del mundo.
Salida: JSON por episodio (/data/hrl_e0/forense/*.json) + resumen en stdout."""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, "/workspace")
sys.path.insert(0, "/data/hrl_e0/verif")
from world import (ACTIVE, INCOMING, DETER_RADIUS, STATIC_DETER_RADIUS,  # noqa: E402
                   SCARE_APPROACH_MIN, STATIC_DETER_GAIN)
from hrl import run_e0                                              # noqa: E402
from hrl.behavior_checks import seg_cross                           # noqa: E402
from hrl.events import reactive_of                                  # noqa: E402
from relabel_premature import job_of                                # noqa: E402

OUT = pathlib.Path("/data/hrl_e0/forense")
STACK_M = 3.0          # "apilados": dos ACTIVE a < 3 m (menor que relay_handoff_tol=2? no: 2 m es
                       # el hand-off legítimo; 3 m captura hand-off + apilamientos reales; se
                       # distinguen por la etiqueta 'handoff' abajo)


def replay(seed, kind, arm_name):
    rec_stub = {"arm": arm_name, "seed": seed, "kind": kind}
    job = job_of(rec_stub)
    wolf = run_e0.make_wolf(job["arm"].get("wolf"))
    w = run_e0.make_world(seed, kind, wolf_controller=wolf)
    coord = run_e0.make_drone(job["arm"]["drone"])(w)
    react = reactive_of(coord)
    w.reset()
    ticks = []
    first_det = {}          # lobo -> tick primera detección (<= r_detect de un ACTIVE)
    first_conf = {}         # lobo -> tick primera confirmación (latch de la barrera)
    stacks = []
    crosses = []
    prev_wolves = w.wolves.copy()
    prev_phase = w.phase
    while True:
        if wolf is not None:
            wolf.refresh(w)
        t = int(w.step_count)
        # ---- percepción en la frontera
        act_mask = w.drone_state == ACTIVE
        act = w.drones[act_mask]
        if act.shape[0]:
            dd = np.linalg.norm(w.wolves[:, None, :] - act[None, :, :], axis=2)
            det = (dd <= w.r_detect).any(axis=1)
            for j in np.where(det)[0]:
                first_det.setdefault(int(j), t)
        conf = getattr(react, "_confirmed", None)
        if conf is not None:
            for j in np.where(conf)[0]:
                first_conf.setdefault(int(j), t)
        wp_before = w.drone_waypoint.copy()
        wp = coord.act(w.get_observation())
        # ---- estado del coordinador tras act()
        anchor = getattr(react, "_anchor", None)
        pose_c = getattr(react, "_pose_c", None)
        pose_u = getattr(react, "_pose_u", None)
        pose_step = getattr(react, "_pose_last_step", -10)
        clean = pose_c is not None and pose_step == t     # rama CLEAN este tick
        free = act_mask & ~w.drone_investigating
        # PENETRADO = ESCOLTA con ancla y herd pero SIN pose fresca (la rama _cover_engaged)
        herd_ok = bool((w.cow_alive & ~w.cow_safe).any() or (w.calf_alive & ~w.calf_safe).any())
        penetrado = (w.phase == "ESCOLTA" and anchor is not None and herd_ok and not clean
                     and free.any())
        inv = np.where(w.drone_investigating)[0].tolist()
        inc = np.where(w.drone_state == INCOMING)[0].tolist()
        # ---- apilamiento entre ACTIVE (y ACTIVE-INCOMING)
        idx_on = np.where(act_mask | (w.drone_state == INCOMING))[0]
        for a_i in range(idx_on.size):
            for b_i in range(a_i + 1, idx_on.size):
                a, b = int(idx_on[a_i]), int(idx_on[b_i])
                d = float(np.linalg.norm(w.drones[a] - w.drones[b]))
                if d < STACK_M:
                    handoff = (w.drone_state[a] == INCOMING or w.drone_state[b] == INCOMING or
                               (a in inc) or (b in inc))
                    same_wp = float(np.linalg.norm(wp[a] - wp[b])) if wp is not None else None
                    stacks.append({"t": t, "a": a, "b": b, "dist": round(d, 2),
                                   "estados": [int(w.drone_state[a]), int(w.drone_state[b])],
                                   "handoff": bool(handoff), "penetrado": bool(penetrado),
                                   "clean": bool(clean), "inv": inv,
                                   "wp_dist": (None if same_wp is None else round(same_wp, 2)),
                                   "wp_a": (None if wp is None else np.round(wp[a], 1).tolist()),
                                   "wp_b": (None if wp is None else np.round(wp[b], 1).tolist()),
                                   "phase": w.phase})
        # ---- step
        _o, _r, term, trunc, _i = w.step(wp)
        # ---- cruces del corredor tras el paso, con la mecánica del susto en ese paso
        idx_free = np.where((w.drone_state == ACTIVE) & ~w.drone_investigating)[0]
        cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
        if idx_free.size >= 2 and cows_ns.shape[0]:
            pts = w.drones[idx_free]
            _u, _s, vt = np.linalg.svd(pts - pts.mean(axis=0))
            order = np.argsort(pts @ vt[0])
            pts_o = pts[order]
            hc = cows_ns.mean(axis=0)
            act2 = w.drones[w.drone_state == ACTIVE]
            act2_vel = w.drone_vel[w.drone_state == ACTIVE]
            for j in range(w.n_wolves):
                p1, p2 = prev_wolves[j], w.wolves[j]
                if not (np.linalg.norm(p2 - hc) < np.linalg.norm(p1 - hc)):
                    continue
                for kk in range(idx_free.size - 1):
                    if seg_cross(p1, p2, pts_o[kk], pts_o[kk + 1]):
                        gap = float(np.linalg.norm(pts_o[kk] - pts_o[kk + 1]))
                        # mecánica en el tick: dist al ACTIVE más cercano, approach, pared
                        rel = p2[None, :] - act2
                        dist = np.linalg.norm(rel, axis=1)
                        jn = int(np.argmin(dist))
                        units = rel / np.maximum(dist[:, None], 1e-9)
                        approach = float(np.sum(act2_vel * units, axis=1)[jn])
                        walled_by = dist <= STATIC_DETER_RADIUS
                        fall = np.clip(1.0 - dist / STATIC_DETER_RADIUS, 0.0, 1.0) * walled_by
                        push = (units * fall[:, None]).sum(axis=0)
                        # punto medio del par: distancia del lobo al segmento
                        a, b = pts_o[kk], pts_o[kk + 1]
                        ab = b - a
                        tt = float(np.clip(((p2 - a) @ ab) / max(ab @ ab, 1e-9), 0, 1))
                        d_seg = float(np.linalg.norm(p2 - (a + tt * ab)))
                        crosses.append({
                            "t": int(w.step_count), "lobo": j, "gap_par": round(gap, 1),
                            "d_dron_mas_cercano": round(float(dist[jn]), 2),
                            "approach_ese_dron": round(approach, 2),
                            "expulsion_activa": bool(dist[jn] <= DETER_RADIUS and
                                                     approach > SCARE_APPROACH_MIN),
                            "pared_activa": bool(walled_by.any()),
                            "pared_push_norma": round(float(np.linalg.norm(push)) *
                                                      STATIC_DETER_GAIN * w.wolf_speed, 3),
                            "frac_sobre_segmento": round(tt, 2), "d_al_segmento": round(d_seg, 2),
                            "scared_mundo": bool(w._wolf_scared[j]),
                            "walled_mundo": bool(w._wolf_walled[j]),
                        })
        ticks.append({"t": t, "phase": w.phase, "anchor": (None if anchor is None else int(anchor)),
                      "clean": bool(clean), "penetrado": bool(penetrado),
                      "pose_c": (None if pose_c is None else np.round(pose_c, 1).tolist()),
                      "inv": inv, "inc": inc,
                      "n_conf": (0 if conf is None else int(conf.sum()))})
        prev_wolves = w.wolves.copy()
        if term or trunc:
            break
    return {"seed": seed, "kind": kind, "arm": arm_name, "sev": int(w.n_depredadas),
            "steps": int(w.step_count), "grupos": [int(x) for x in w.wolf_group_sizes],
            "n_wolves": int(w.n_wolves),
            "first_det": first_det, "first_conf": first_conf,
            "captures": [{"t": c["step"], "kind": c["kind"], "prey": c["prey_idx"],
                          "flankers": c["flankers"]} for c in w.captures],
            "stacks": stacks, "crosses": crosses, "ticks": ticks}


def summarize(r):
    print(f"=== {r['arm']} seed={r['seed']} {r['kind']} sev={r['sev']} steps={r['steps']} "
          f"grupos={r['grupos']} n_wolves={r['n_wolves']}")
    fd = sorted(r["first_det"].items(), key=lambda kv: kv[1])
    fc = sorted(r["first_conf"].items(), key=lambda kv: kv[1])
    print("  A) primera DETECCIÓN por lobo (lobo:tick):", fd)
    print("     primera CONFIRMACIÓN por lobo:", fc)
    n1 = r["grupos"][0] if len(r["grupos"]) == 2 else None
    if n1 is not None and fc:
        print(f"     señuelo = lobo 0 (grupo 1 = índices <{n1}); primer confirmado = lobo {fc[0][0]} "
              f"({'SEÑUELO' if fc[0][0] < n1 else 'ASALTO'}) en t={fc[0][1]}")
    st = r["stacks"]
    print(f"  B) pares ACTIVE a <{STACK_M} m: {len(st)} ticks-par; hand-off: "
          f"{sum(1 for s in st if s['handoff'])}; PENETRADO: {sum(1 for s in st if s['penetrado'])}; "
          f"CLEAN: {sum(1 for s in st if s['clean'])}; con investigación: "
          f"{sum(1 for s in st if s['inv'])}")
    non_h = [s for s in st if not s["handoff"]]
    if non_h:
        # tramos contiguos
        tr = []
        cur = [non_h[0]]
        for s in non_h[1:]:
            if s["t"] - cur[-1]["t"] <= 1 and (s["a"], s["b"]) == (cur[-1]["a"], cur[-1]["b"]):
                cur.append(s)
            else:
                tr.append(cur); cur = [s]
        tr.append(cur)
        for seg in tr[:12]:
            s0, s1 = seg[0], seg[-1]
            print(f"     apilamiento drones {s0['a']}-{s0['b']} t={s0['t']}..{s1['t']} "
                  f"({len(seg)} ticks) dist_min={min(x['dist'] for x in seg):.2f} "
                  f"penetrado={any(x['penetrado'] for x in seg)} clean={any(x['clean'] for x in seg)} "
                  f"inv={s0['inv']} wp_dist={s0['wp_dist']} phase={s0['phase']} "
                  f"wp_a={s0['wp_a']} wp_b={s0['wp_b']}")
    cr = r["crosses"]
    print(f"  C) cruces de corredor hacia el rebaño: {len(cr)}; con expulsión activa: "
          f"{sum(1 for c in cr if c['expulsion_activa'])}; con pared activa: "
          f"{sum(1 for c in cr if c['pared_activa'])}; scared: {sum(1 for c in cr if c['scared_mundo'])}")
    for c in cr[:15]:
        print("    ", c)
    pen = sum(1 for tk in r["ticks"] if tk["penetrado"])
    cl = sum(1 for tk in r["ticks"] if tk["clean"])
    print(f"  ticks PENETRADO={pen} CLEAN={cl} de {len(r['ticks'])}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seed, kind = 398, "mixto"
    for arm in ("cebo_keep_h50_reactive", "masa_reactive"):
        r = replay(seed, kind, arm)
        summarize(r)
        (OUT / f"forense_seed{seed}_{kind}_{arm}.json").write_text(
            json.dumps(r, ensure_ascii=False))
    print("FORENSE_OK")


if __name__ == "__main__":
    main()
