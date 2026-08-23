"""run01_comportamiento.py — ¿QUÉ aprendió la política MARL para bajar la severidad?

Espíritu de cebo_diag, invertido al bando de los drones: episodios GEMELOS (mismas semillas,
CONFIG_V2 grouped, lobos scriptados) con la BARRERA (δ≡0, suelo) y con la POLÍTICA (mejor
checkpoint), SOLO en los episodios cuyo spawn salió con 2 SUBGRUPOS (wolf_group_sizes == 2).
Dos hipótesis del Δ, cada una con su métrica de comportamiento:

  (1) REPARTO ENTRE FRENTES (lo que la barrera de UNA línea no hace): mientras los frentes
      siguen SIENDO dos (separación de centroides > SEP_DOS_FRENTES, en ESCOLTA), ¿qué fracción
      de pasos tiene CADA frente >= 1 dron ACTIVE a <= ATENCION m de su centroide? + distancia
      del dron más cercano al frente PEOR atendido (la barrera debería dejarlo lejos).
  (2) MOVERSE PARA DISUADIR (vencer la habituación v2.4): rapidez media de los drones ACTIVE
      en ESCOLTA (m/s; solo el dron que EMBISTE expulsa) + presión de susto = fracción de
      (lobo,paso) huyendo (_wolf_scared, el flag del propio mundo) por paso de ESCOLTA.

Solo lectura del estado por paso (no toca física ni artefactos). Uso y salida: dentro del
contenedor; JSON a /data/drones/run01/comportamiento_run01.json. Script de diagnóstico
(usar y tirar), vive en /data.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace")
from world import ACTIVE                                   # noqa: E402
from baseline import build_world                           # noqa: E402
from rl.residual_drone_coordinator import ResidualDroneCoordinator  # noqa: E402

BEST_CKPT = "/data/drones/run01/checkpoints/mappo_drones_18998784_steps.zip"
SEP_DOS_FRENTES = 60.0   # m: los centroides siguen siendo DOS frentes (pre-fusión)
ATENCION = 40.0          # m: un dron "atiende" un frente si esta a <= 2*DETER_RADIUS del centroide
SEEDS = range(100)
KINDS = ("lobos", "mixto")


def run_episode(seed: int, kind: str, model):
    """Un episodio instrumentado (mismo bucle que baseline.run_episode_metrics).
    None si el spawn no salio con 2 subgrupos."""
    w = build_world(seed, kind)
    coord = ResidualDroneCoordinator(w, model=model)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n1 = int(w.wolf_group_sizes[0])
    g1, g2 = np.arange(0, n1), np.arange(n1, w.n_wolves)

    pasos_escolta = 0
    pasos_2f = 0                 # pasos de ESCOLTA con dos frentes reales (sep > umbral)
    pasos_2f_ambos = 0           # ... y AMBOS frentes atendidos (>=1 ACTIVE a <= ATENCION)
    dist_peor = []               # dist del dron ACTIVE mas cercano al frente PEOR atendido
    vel_active = []              # rapidez de cada dron ACTIVE por paso de ESCOLTA (m/s)
    sustos = 0                   # (lobo,paso) huyendo en ESCOLTA
    prev_pos = w.drones.copy()
    prev_active = (w.drone_state == ACTIVE)

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
            both = prev_active & (w.drone_state == ACTIVE)   # ACTIVE en ambos extremos del paso
            if both.any():
                v = np.linalg.norm(w.drones[both] - prev_pos[both], axis=1) / w.dt
                vel_active.extend(v.tolist())
            sustos += int(w._wolf_scared.sum())
        prev_pos = w.drones.copy()
        prev_active = (w.drone_state == ACTIVE)
        if term or trunc:
            break

    return {
        "seed": seed, "kind": kind, "sizes": [int(x) for x in w.wolf_group_sizes],
        "n_depredadas": int(w.n_depredadas), "status": w.status, "steps": int(w.step_count),
        "pasos_escolta": pasos_escolta, "pasos_2f": pasos_2f, "pasos_2f_ambos": pasos_2f_ambos,
        "dist_peor_media": (float(np.nanmean(dist_peor)) if dist_peor else None),
        "vel_active_media": (float(np.mean(vel_active)) if vel_active else None),
        "sustos_por_paso_escolta": (sustos / pasos_escolta if pasos_escolta else 0.0),
    }


def campaign(model, label):
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
    }
    print(f"--- {label} ---")
    for k, v in resumen.items():
        print(f"  {k}: {v}")
    return resumen, eps


def main():
    from stable_baselines3 import PPO
    model = PPO.load(BEST_CKPT, device="cpu")
    print("=== comportamiento run01: barrera (suelo) vs politica (mejor ckpt 18,998,784) ===")
    print(f"  episodios de 2 subgrupos, kinds={KINDS}, semillas 0-99; "
          f"dos-frentes = sep>{SEP_DOS_FRENTES} m; atencion = {ATENCION} m")
    suelo, eps_s = campaign(None, "BARRERA (suelo, δ≡0)")
    poli, eps_p = campaign(model, "POLITICA (mejor ckpt)")
    out = Path("/data/drones/run01/comportamiento_run01.json")
    out.write_text(json.dumps({
        "best_ckpt": BEST_CKPT, "fecha": datetime.now().isoformat(timespec="seconds"),
        "params": {"sep_dos_frentes_m": SEP_DOS_FRENTES, "atencion_m": ATENCION,
                   "kinds": list(KINDS), "n_seeds": len(list(SEEDS))},
        "suelo": {"resumen": suelo, "episodes": eps_s},
        "politica": {"resumen": poli, "episodes": eps_p},
    }, ensure_ascii=False, indent=2))
    print(f"  guardado -> {out}")


if __name__ == "__main__":
    main()
