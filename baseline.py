"""
baseline.py — Arnés de EVALUACIÓN de la v2 CONGELADA (DummyCoordinator + física v2).

================================  v2 CONGELADA  ================================
A partir del tag git `v2-baseline` el MUNDO (la física) NO cambia: es la referencia
fija que los coordinadores deberán BATIR. Este fichero NO es el mundo —es el banco
de medida del mundo—: fija la config de evaluación (`CONFIG_V2`, corzos ON con los
3 tipos de episodio), corre el `DummyCoordinator` (drones quietos = SIN intervención)
sobre un set FIJO de semillas, N por tipo, y reporta las métricas POR TIPO.

⚠️ Esto es FIJAR Y MEDIR, no tunear. La baseline es la que salga. NO se cambia la
   física para "mejorar" estos números; se baja la severidad con el COORDINADOR
   (posicionar drones), que es lo que se compara —y se evalúa con ESTE mismo arnés
   cambiando SOLO el coordinador (Dummy -> el nuevo), sobre las MISMAS semillas y
   config: apples-to-apples.

Métrica PRINCIPAL = SEVERIDAD = muertes (reses depredadas) por episodio. Más:
reparto de terminales (success / predation / timeout) y n_safe medio. Números
CONGELADOS (N=100/tipo, DummyCoordinator, semillas range(100)):
  solo-lobos  4.45 ± 2.15 (máx 8) · n_safe 2.39 · success 4 / predation 88 / timeout 8
  solo-corzos 0.00 ± 0.00 (máx 0) · n_safe 0.00 · timeout 100        (SIN amenaza)
  mixto       4.41 ± 2.18 (máx 8) · n_safe 2.43 · success 4 / predation 88 / timeout 8
  AGREGADO    2.95 ± 2.74 (máx 8) · n_safe 1.61 · success 8 / predation 176 / timeout 116
mixto ≈ solo-lobos (los corzos solo consumen ciclos de investigación; el agregado
mezclado es poco informativo: la comparación se hace POR TIPO).

Resultados guardados en baseline_v2.json (rico, por episodio) y baseline_v2.csv
(tabla). `python baseline.py` re-mide y comprueba que no ha derivado.

La batería/carga es infraestructura ortogonal (gobierna qué drones están disponibles,
no la dinámica vaca/lobo). El guiado/collares y la disuasión son infraestructura del
MUNDO (iguales para todos los coordinadores). Solo se compara el coordinador de drones.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter

import numpy as np

from world import World
from coordinators import DummyCoordinator

# =============================== CONFIG_V2 (CONGELADA) ===============================
# Config del MUNDO v2 con CORZOS ACTIVOS (los 3 tipos de episodio). Es el mundo al que se
# enfrentan los coordinadores. Los valores EXPLÍCITOS espejan los defaults de World en el
# momento del congelado, para no depender de futuros cambios en esos defaults; el arnés
# verifica (cross-check de fidelidad, abajo) que este bloque == "defaults + corzos ON" bit
# a bit. Los parámetros con default DERIVADO (None -> fórmula) se dejan al constructor y se
# documentan aquí con su valor RESUELTO a 300×300 m:
#   safe_radius=36.0 (0.12·min)  station_radius=15.0  station_gap=3.0  cow_spawn=(75,225)
#   cow_spread=40.0  r_separation=22.0  cow_spawn_min_sep=10.0  r_notice=20.0  r_face_safe=6.0
#   capture_radius=3.0  r_standoff=12.0  wolf_repulsion_radius=12.0  wolf_skirt_margin=6.0
#   wolf_spawn_dispersion=5.0  calf_personal_space=1.5  refuge_margin=3.6
#   max_episode_steps=14142 (=int(4·√(300²+300²)/1.2/0.1))  charge_capacity=4 (=n_reserve)
# Las CONSTANTES FÍSICAS de módulo (escala biológica absoluta HERD_*, dron DRONE_*,
# disuasión DETER_*, bordeo de zona WOLF_ZONE_SKIRT_*, evitación COW_AVOID_*/W_*, corzos
# CORZO_*) viven en la cabecera de world.py y quedan congeladas por el tag (no son params
# del constructor; no se pueden fijar desde aquí). NO TOCAR ninguno de estos sin re-medir.
CONFIG_V2 = dict(
    # --- equipo y rebaño ---
    n_active_drones=4, n_reserve_drones=4, n_cows=6,
    wolves_min=1, wolves_max=5,
    # --- CORZOS ON (3c): 3 tipos de episodio ~1/3 (solo-lobos / solo-corzos / mixto) ---
    corzos_min=1, corzos_max=3, corzo_speed=4.0,
    corzo_episode_probs=(1 / 3, 1 / 3, 1 / 3),
    # --- campo y layout ---
    parcel_size=(300.0, 300.0), station_dir=(0.0, 1.0),
    dt=0.1, max_steps=600,
    # --- vaca adulta (pastar disperso + dar la cara + inercia) ---
    cow_speed=1.2, cow_speed_jitter=0.4, k_separation=3.0,
    wander_calm=0.2, wander_drift=0.12, k_fence=1.5,
    cone_half_angle=np.pi / 4, face_cooldown=1.0, turn_rate=2.0, cow_inertia=0.25,
    # --- terneros + defensoras (madre no abandona al ternero) ---
    calf_count_probs=(1 / 3, 1 / 3, 1 / 3), calf_speed=0.8,
    k_calf_cohesion=1.0, k_defender_anchor=0.6,
    # --- lobo direccional (cono + flanqueo + envolvente + bordeo) ---
    wolf_speed=4.0, wolf_repulsion_strength=1.0, wolf_skirt_gain=1.5,
    wolf_envelop_gain=3.0, n_min_adult=2, cone_band=0.12, wolf_inertia=0.35,
    # --- escolta / terminal (máquina de fases + guiado al refugio + disuasión) ---
    r_detect=100.0, r_confirm=40.0, episode_time_factor=4.0, escort_enabled=True,
    # --- batería / cola de carga ---
    battery_capacity=600.0, charge_full=300.0, announce_threshold=0.20,
    # --- guardia de teletransporte: solo LOGUEA (no afecta la dinámica) ---
    teleport_guard=False, motion_tol=1.5,
)

# Set FIJO de semillas (mismas para cada tipo, forzando el tipo -> muestra sólida y comparable).
N_PER_KIND = 100
EVAL_SEEDS = tuple(range(N_PER_KIND))
KINDS = ("lobos", "corzos", "mixto")
KIND_LABEL = {"lobos": "solo-lobos", "corzos": "solo-corzos", "mixto": "mixto"}
TERMINALS = ("success", "predation", "timeout")
FROZEN_TAG = "v2-baseline"   # tag git del commit congelado (la física no cambia a partir de él)

# Referencia CONGELADA de severidad (media de muertes/ep) por tipo, para detectar DERIVA.
# Se rellena tras la primera medición; en re-corridas debe coincidir (mundo reproducible).
REFERENCE_SEVERITY = {
    "lobos": 4.45,   # solo-lobos (amenaza pura) ≈ v2 honesta; succ 4 / pred 88 / timeout 8; n_safe 2.39
    "corzos": 0.00,  # solo-corzos = SIN amenaza (100/100 timeout; el rebaño pasta, n_safe 0)
    "mixto": 4.41,   # ≈ solo-lobos (los corzos solo consumen ciclos de investigación)
}

# Tolerancia de deriva (la media es exacta y reproducible bit a bit; margen mínimo por si
# se reordena alguna operación NumPy sin cambiar la física).
DRIFT_TOL = 0.005


def build_world(seed: int, kind: str) -> World:
    """World v2 (CONFIG_V2) con el tipo de episodio FORZADO (muestra por tipo)."""
    return World(seed=seed, episode_kind=kind, **CONFIG_V2)


def run_episode_metrics(world: World, coordinator) -> dict:
    """Corre un episodio hasta terminal (mismo bucle que main.run_episode, SIN historial)
    y devuelve sus métricas. El coordinador es lo único que cambia entre evaluaciones."""
    world.reset()
    while True:
        actions = coordinator.act(world.get_observation())
        _obs, _reward, terminated, truncated, info = world.step(actions)
        if terminated or truncated:
            break
    return {
        "status": world.status,
        "episodio": world.episode_kind,
        "n_wolves": int(world.n_wolves),
        "n_corzos": int(world.n_corzos),
        "n_corzos_descartados": int(world.corzo_dismissed.sum()),
        "n_depredadas": int(world.n_depredadas),                 # SEVERIDAD del episodio
        "n_safe": int(world.cow_safe.sum() + world.calf_safe.sum()),
        "steps": int(world.step_count),
    }


def evaluate(coordinator_factory=lambda w: DummyCoordinator(w.n_drones),
             seeds=EVAL_SEEDS, kinds=KINDS) -> dict:
    """Evalúa un coordinador sobre el mundo v2: para CADA tipo, corre todas las semillas y
    agrega severidad (media±desv), reparto de terminales y n_safe medio. Reutilízalo para
    comparar un coordinador nuevo: pasa su factory; misma config, mismas semillas."""
    by_kind = {}
    all_deaths, all_safe, all_terms = [], [], Counter()
    for kind in kinds:
        deaths, safe, terms, episodes = [], [], Counter(), []
        for s in seeds:
            w = build_world(s, kind)
            m = run_episode_metrics(w, coordinator_factory(w))
            deaths.append(m["n_depredadas"]); safe.append(m["n_safe"]); terms[m["status"]] += 1
            episodes.append(m)
        deaths_a = np.asarray(deaths, dtype=float)
        by_kind[kind] = {
            "label": KIND_LABEL[kind], "n": len(seeds),
            "severity_mean": float(deaths_a.mean()),
            "severity_std": float(deaths_a.std()),
            "severity_max": int(deaths_a.max()),
            "n_safe_mean": float(np.mean(safe)),
            "terminals": {t: int(terms.get(t, 0)) for t in TERMINALS},
            "episodes": episodes,
        }
        all_deaths.extend(deaths); all_safe.extend(safe); all_terms.update(terms)
    agg_deaths = np.asarray(all_deaths, dtype=float)
    aggregate = {
        "n": len(all_deaths),
        "severity_mean": float(agg_deaths.mean()),
        "severity_std": float(agg_deaths.std()),
        "severity_max": int(agg_deaths.max()),
        "n_safe_mean": float(np.mean(all_safe)),
        "terminals": {t: int(all_terms.get(t, 0)) for t in TERMINALS},
    }
    return {"by_kind": by_kind, "aggregate": aggregate}


def _verify_fidelity(seeds=(0, 1, 2, 3, 4)) -> bool:
    """Cross-check: CONFIG_V2 debe ser BIT A BIT == 'defaults de World + corzos ON'. Si algún
    valor explícito de CONFIG_V2 se desviara del default, el mundo medido no sería la v2."""
    ok = True
    for kind in KINDS:
        for s in seeds:
            a = build_world(s, kind)                                      # CONFIG_V2 explícito
            b = World(seed=s, episode_kind=kind, corzos_min=1, corzos_max=3)  # defaults + corzos
            a.reset(); b.reset()
            same = (a.n_wolves == b.n_wolves and a.n_corzos == b.n_corzos
                    and a.n_calves == b.n_calves
                    and np.allclose(a.cows, b.cows) and np.allclose(a.wolves, b.wolves)
                    and np.allclose(a.corzos, b.corzos)
                    and a.max_episode_steps == b.max_episode_steps
                    and a.safe_radius == b.safe_radius and a.r_notice == b.r_notice
                    and a.r_face_safe == b.r_face_safe and a.capture_radius == b.capture_radius)
            ok = ok and same
    return ok


def _write_artifacts(results: dict, path_json="baseline_v2.json", path_csv="baseline_v2.csv") -> None:
    """Guarda los resultados como referencia fija: JSON (rico, por episodio) + CSV (tabla)."""
    payload = {
        "frozen_tag": FROZEN_TAG,
        "coordinator": "DummyCoordinator",
        "n_per_kind": N_PER_KIND,
        "seeds": list(EVAL_SEEDS),
        "kinds": list(KINDS),
        "config_v2": {k: (list(v) if isinstance(v, tuple) else v) for k, v in CONFIG_V2.items()},
        "by_kind": {k: {kk: vv for kk, vv in d.items()} for k, d in results["by_kind"].items()},
        "aggregate": results["aggregate"],
    }
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(path_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tipo", "n", "severidad_media", "severidad_desv", "severidad_max",
                    "n_safe_media", "success", "predation", "timeout"])
        for kind in KINDS:
            d = results["by_kind"][kind]; t = d["terminals"]
            w.writerow([d["label"], d["n"], "%.4f" % d["severity_mean"], "%.4f" % d["severity_std"],
                        d["severity_max"], "%.4f" % d["n_safe_mean"],
                        t["success"], t["predation"], t["timeout"]])
        a = results["aggregate"]; t = a["terminals"]
        w.writerow(["AGREGADO", a["n"], "%.4f" % a["severity_mean"], "%.4f" % a["severity_std"],
                    a["severity_max"], "%.4f" % a["n_safe_mean"],
                    t["success"], t["predation"], t["timeout"]])


def _print_table(results: dict) -> None:
    print("  %-12s %4s  %18s  %9s  %s" % ("tipo", "n", "SEVERIDAD (media±desv)", "n_safe", "terminales"))
    for kind in KINDS:
        d = results["by_kind"][kind]; t = d["terminals"]
        print("  %-12s %4d  %8.2f ± %-6.2f (máx %d)  %7.2f  success=%d predation=%d timeout=%d"
              % (d["label"], d["n"], d["severity_mean"], d["severity_std"], d["severity_max"],
                 d["n_safe_mean"], t["success"], t["predation"], t["timeout"]))
    a = results["aggregate"]; t = a["terminals"]
    print("  %-12s %4d  %8.2f ± %-6.2f (máx %d)  %7.2f  success=%d predation=%d timeout=%d"
          % ("AGREGADO", a["n"], a["severity_mean"], a["severity_std"], a["severity_max"],
             a["n_safe_mean"], t["success"], t["predation"], t["timeout"]))


if __name__ == "__main__":
    print("=== baseline v2 (CONGELADA, tag %s): DummyCoordinator sobre %d semillas × %d tipos ==="
          % (FROZEN_TAG, N_PER_KIND, len(KINDS)))

    fidelity = _verify_fidelity()
    print("  fidelidad CONFIG_V2 == defaults+corzos (bit a bit): %s" % ("OK" if fidelity else "FALLO"))
    assert fidelity, "FALLO: CONFIG_V2 se ha desviado de la v2 (defaults + corzos ON)"

    results = evaluate()
    _print_table(results)
    _write_artifacts(results)
    print("  guardado -> baseline_v2.json (por episodio) + baseline_v2.csv (tabla)")

    # Self-check de deriva: la severidad por tipo debe coincidir con la referencia congelada.
    print("  deriva vs referencia congelada:")
    drift_ok = True
    for kind in KINDS:
        meas = results["by_kind"][kind]["severity_mean"]
        ref = REFERENCE_SEVERITY[kind]
        d = abs(meas - ref)
        status = "OK" if d <= DRIFT_TOL else "DERIVA %.3f" % d
        drift_ok = drift_ok and d <= DRIFT_TOL
        print("    %-12s medido=%.2f  referencia=%.2f  -> %s" % (KIND_LABEL[kind], meas, ref, status))
    print("  %s" % ("baseline v2 estable (sin deriva)" if drift_ok else "¡DERIVA! el mundo se ha movido"))
