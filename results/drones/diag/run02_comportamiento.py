"""run02_comportamiento.py — ¿QUÉ aprendió la política run02 para bajar la severidad?

Mismo espíritu que run01_comportamiento.py (episodios GEMELOS suelo vs política, solo spawns de
2 SUBGRUPOS, semillas 0-99 × lobos/mixto), con las métricas de run01 (comparables) y UNA nueva:

  (1) REPARTO ENTRE FRENTES: fracción de pasos-2-frentes con AMBOS frentes atendidos (>=1
      ACTIVE a <= ATENCION del centroide) + dist al frente PEOR atendido. run01: 6.2% -> 6.5%
      (NO aprendió a repartirse; la rigidez y la falta de contactos eran sospechosas — run02
      quita ambas).
  (2) MOVERSE PARA DISUADIR: rapidez media ACTIVE en ESCOLTA + sustos/(paso de escolta).
      run01: 3.76->4.39 m/s (+17%) y 1.19->1.50 (+26%) — el Δ de run01 fue esto.
  (3) GOTERA CENTRAL (nueva, la métrica del usuario de v3.4/v3.5): cruces de segmento entre
      drones CONTIGUOS (orden por proyección en el eje principal de los libres) HACIA DENTRO,
      contando SOLO pares a hueco <= GOTERA_GAP (pares que forman pared-corredor; con la línea
      del suelo eso es el corredor de 20 m; con la política, cualquier pareja cercana). ¿La
      política los evita moviéndose (cerrar el corredor) o los sigue regalando?

Uso (dentro del contenedor):
    python3 run02_comportamiento.py <checkpoint.zip|FLOOR> [etiqueta]
Corre la campaña UNA vez (suelo se corre pasando FLOOR) y guarda JSON por etiqueta en
/data/drones/run02_v34/comportamiento_<etiqueta>.json (se comparan después).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE, STATIC_DETER_RADIUS                  # noqa: E402
from baseline import build_world                               # noqa: E402
from rl.residual_drone_coordinator import ResidualDroneCoordinator  # noqa: E402

SEP_DOS_FRENTES = 60.0   # m (= run01, comparable)
ATENCION = 40.0          # m (= run01, comparable)
GOTERA_GAP = 24.0        # m: pares de drones a hueco <= 1.2*spacing (pared-corredor real)
SEEDS = range(100)
KINDS = ("lobos", "mixto")


def seg_cross(p1, p2, a, b):
    d1, d2 = p2 - p1, b - a
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return False
    t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
    s = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
    return 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0


def run_episode(seed: int, kind: str, model):
    w = build_world(seed, kind)
    coord = ResidualDroneCoordinator(w, model=model)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n1 = int(w.wolf_group_sizes[0])
    g1, g2 = np.arange(0, n1), np.arange(n1, w.n_wolves)

    pasos_escolta = pasos_2f = pasos_2f_ambos = 0
    dist_peor, vel_active = [], []
    sustos = 0
    gotera = 0                    # cruces hacia dentro por pares a hueco <= GOTERA_GAP
    cruces_todos = 0              # cruces hacia dentro por CUALQUIER par contiguo (contexto)
    prev_pos = w.drones.copy()
    prev_active = (w.drone_state == ACTIVE)
    prev_wolves = w.wolves.copy()

    while True:
        en_escolta = (w.phase == "ESCOLTA")
        if en_escolta:
            pasos_escolta += 1
            wolves = np.asarray(w.wolves, dtype=float)
            c1, c2 = wolves[g1].mean(axis=0), wolves[g2].mean(axis=0)
            if np.linalg.norm(c1 - c2) > SEP_DOS_FRENTES:
                pasos_2f += 1
                act_pos = w.drones[w.drone_state == ACTIVE]
                if act_pos.shape[0] > 0:
                    d1 = np.linalg.norm(act_pos - c1, axis=1).min()
                    d2 = np.linalg.norm(act_pos - c2, axis=1).min()
                    if d1 <= ATENCION and d2 <= ATENCION:
                        pasos_2f_ambos += 1
                    dist_peor.append(max(d1, d2))
                else:
                    dist_peor.append(float("nan"))

        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))

        if en_escolta:
            both = prev_active & (w.drone_state == ACTIVE)
            if both.any():
                v = np.linalg.norm(w.drones[both] - prev_pos[both], axis=1) / w.dt
                vel_active.extend(v.tolist())
            sustos += int(w._wolf_scared.sum())
            # (3) GOTERA: cruces de segmento entre drones libres contiguos, hacia dentro.
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            idx = np.where(free)[0]
            cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
            if idx.size >= 2 and cows_ns.shape[0] > 0:
                pts = w.drones[idx]
                cc = pts - pts.mean(axis=0)
                _u2, _s2, vt = np.linalg.svd(cc)
                pts_o = pts[np.argsort(pts @ vt[0])]
                hc = cows_ns.mean(axis=0)
                for j in range(w.n_wolves):
                    p1, p2 = prev_wolves[j], w.wolves[j]
                    if not (np.linalg.norm(p2 - hc) < np.linalg.norm(p1 - hc)):
                        continue
                    for kk in range(idx.size - 1):
                        if seg_cross(p1, p2, pts_o[kk], pts_o[kk + 1]):
                            cruces_todos += 1
                            if np.linalg.norm(pts_o[kk] - pts_o[kk + 1]) <= GOTERA_GAP:
                                gotera += 1
        prev_pos = w.drones.copy()
        prev_active = (w.drone_state == ACTIVE)
        prev_wolves = w.wolves.copy()
        if term or trunc:
            break

    return {
        "seed": seed, "kind": kind, "sizes": [int(x) for x in w.wolf_group_sizes],
        "n_depredadas": int(w.n_depredadas), "status": w.status, "steps": int(w.step_count),
        "pasos_escolta": pasos_escolta, "pasos_2f": pasos_2f, "pasos_2f_ambos": pasos_2f_ambos,
        "dist_peor_media": (float(np.nanmean(dist_peor)) if dist_peor else None),
        "vel_active_media": (float(np.mean(vel_active)) if vel_active else None),
        "sustos_por_paso_escolta": (sustos / pasos_escolta if pasos_escolta else 0.0),
        "gotera_cruces": gotera, "cruces_todos": cruces_todos,
    }


def main():
    arg = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else ("suelo" if arg == "FLOOR" else Path(arg).stem)
    model = None
    if arg != "FLOOR":
        from stable_baselines3 import PPO
        model = PPO.load(arg, device="cpu")
    print(f"=== comportamiento run02 [{label}]: 2 subgrupos, semillas 0-99 x {KINDS} ===")
    eps = []
    for kind in KINDS:
        for s in SEEDS:
            r = run_episode(s, kind, model)
            if r is not None:
                eps.append(r)
    m = lambda key: float(np.mean([e[key] for e in eps if e[key] is not None]))  # noqa: E731
    resumen = {
        "n_episodios_2grupos": len(eps),
        "severidad_media_2grupos": round(m("n_depredadas"), 3),
        "frac_pasos_2f": round(float(np.mean([e["pasos_2f"] / max(e["pasos_escolta"], 1) for e in eps])), 3),
        "frac_ambos_frentes_atendidos": round(float(np.mean(
            [e["pasos_2f_ambos"] / e["pasos_2f"] for e in eps if e["pasos_2f"] > 0])), 3),
        "dist_frente_peor_atendido_m": round(m("dist_peor_media"), 1),
        "vel_drones_active_ms": round(m("vel_active_media"), 2),
        "sustos_por_paso_escolta": round(m("sustos_por_paso_escolta"), 3),
        "gotera_cruces_por_ep": round(m("gotera_cruces"), 2),
        "cruces_todos_por_ep": round(m("cruces_todos"), 2),
    }
    for k, v in resumen.items():
        print(f"  {k}: {v}")
    out = Path(f"/data/drones/run02_v34/comportamiento_{label}.json")
    out.write_text(json.dumps({
        "model": arg, "fecha": datetime.now().isoformat(timespec="seconds"),
        "params": {"sep_dos_frentes_m": SEP_DOS_FRENTES, "atencion_m": ATENCION,
                   "gotera_gap_m": GOTERA_GAP, "kinds": list(KINDS), "n_seeds": len(list(SEEDS)),
                   "static_deter_radius": STATIC_DETER_RADIUS},
        "resumen": resumen, "episodes": eps,
    }, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
