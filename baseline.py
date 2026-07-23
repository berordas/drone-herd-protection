"""
baseline.py — Arnés de EVALUACIÓN de la v2 CONGELADA (DummyCoordinator + física v2).

================================  v2.4 CONGELADA  ================================
A partir del tag git `v2.4-baseline` el MUNDO (la física) NO cambia: es la referencia
fija que los coordinadores deberán BATIR. (v2 → v2.1 = RELEVO de flota REALISTA; v2.1 →
v2.2 = el JABALÍ como 2ª distracción, substream RNG separado; v2.2 → v2.3 = SUSTO FUERTE
—campo de fuerza estático—; v2.3 → v2.4 = SUSTO POR MOVIMIENTO: el lobo se HABITÚA a
disuasores estáticos, solo un dron que SE ECHA ENCIMA —aproximación > umbral— lo expulsa;
un dron QUIETO es solo un obstáculo. Los drones CLAVADOS del Dummy dejan de disuadir → la
severidad Dummy RE-MEDIDA SUBE de 2.36/2.24 a 4.41/4.34 —≈ v2.2, la disuasión estática
se evapora—. Además: baterías iniciales ALEATORIAS + reserva espejo, y carga 1.5× el vuelo
pleno —charge_full≈160 s—.) Este fichero NO es el mundo —es el banco de medida—: fija la
config de evaluación (`CONFIG_V2`, corzos ON con los 3 tipos de episodio), corre el
`DummyCoordinator` (drones quietos) sobre un set FIJO de semillas, N por tipo, y reporta
las métricas POR TIPO.

⚠️ Esto es FIJAR Y MEDIR, no tunear. La baseline es la que salga. NO se cambia la
   física para "mejorar" estos números; se baja la severidad con el COORDINADOR
   (posicionar drones), que es lo que se compara —y se evalúa con ESTE mismo arnés
   cambiando SOLO el coordinador (Dummy -> el nuevo), sobre las MISMAS semillas y
   config: apples-to-apples.

Métrica PRINCIPAL = SEVERIDAD = muertes (reses depredadas) por episodio. Más:
reparto de terminales (success / predation / timeout) y n_safe medio.

⚠️ METRO CANÓNICO (v2.4.1): estos números se miden DENTRO del contenedor del proyecto
en la DGX (docker/) — decisión 2026-07-14. La FÍSICA no cambió respecto a v2.4 (mismos
spawns, mismo RNG, mismas reglas); lo que cambió es el ENTORNO de medida: la referencia
anterior se midió en el portátil y la deriva FP entre plataformas (última ULP de
libm/hardware, amplificada por el caos) mueve ~0.1 la media. Los spot-checks contra los
artefactos pueden salir ROJOS fuera del contenedor (portátil) — ESPERADO.

Números CONGELADOS v2.4.1 (N=100/tipo, DummyCoordinator, semillas range(100), DGX):
  solo-lobos  4.54 ± 2.21 (máx 8) · n_safe 2.25 · success 4 / predation 88 / timeout 8
  solo-corzos 0.00 ± 0.00 (máx 0) · n_safe 0.00 · timeout 100        (SIN amenaza)
  mixto       4.46 ± 2.27 (máx 8) · n_safe 2.38 · success 5 / predation 86 / timeout 9
  AGREGADO    3.00 ± 2.80 (máx 8) · n_safe 1.54 · success 9 / predation 174 / timeout 117
mixto ≈ solo-lobos (los corzos solo consumen ciclos de investigación; el agregado
mezclado es poco informativo: la comparación se hace POR TIPO).
(Lineage portátil v2.4: 4.41 / 0.00 / 4.34 — mismo mundo, otro metro.)

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
# verifica (cross-check de fidelidad, abajo) que este bloque == "defaults + corzos ON +
# extras v3.0 DOCUMENTADOS" bit a bit.
#
# v3.0 — TERRENO 500×500 (pieza 1 del CEBO PERFECTO; SOLO en CONFIG_V2: los DEFAULTS de World
# siguen en 300×300 -> face/battery/escort/drone/reactive checks y su física quedan BIT A BIT):
#   · parcel_size 300->500: los radios FÍSICOS (r_detect=100, r_confirm=40, DETER 20/10,
#     velocidades) son ABSOLUTOS y NO cambian — su efecto RELATIVO sí (más campo = margen real
#     de aproximación), que es lo buscado.
#   · cow_spawn EXPLÍCITO (150,350) (antes el derivado 0.25W,0.75H=(125,375)): COLCHÓN >=100 m
#     del área de pasto a TODOS los bordes (150−spread 40=110) — un lobo naciente en el borde
#     queda a >r_detect de toda vaca (no nace ya confirmable; margen de aproximación).
#   · el spawn de lobos NO se toca: ya nace en el PERÍMETRO (ancla proyectada al borde) — a 500
#     eso queda a >=110 m del rebaño por el colchón anterior.
#   · LAYOUT que escala con min(W,H) POR DISEÑO (re-escala coherente, sin tocar código):
#     safe_radius=60.0 (0.12·min)  station_radius=25.0  station_gap=5.0  refuge_margin=6.0
#   · max_episode_steps DERIVADO escala solo: int(4·√(500²+500²)/1.2/0.1)=23570 (antes 14142)
#     — el refugio sigue alcanzable con la misma holgura relativa (factor 4.0 intacto).
# Valores RESUELTOS que NO cambian (escala biológica ABSOLUTA): cow_spread=40.0
#   r_separation=22.0  cow_spawn_min_sep=10.0  r_notice=20.0  r_face_safe=6.0  capture_radius=3.0
#   r_standoff=12.0  wolf_repulsion_radius=12.0  wolf_skirt_margin=6.0  wolf_spawn_dispersion=5.0
#   calf_personal_space=1.5  charge_capacity=4 (=n_reserve)  charge_full≈160 (DERIVADO v2.4)
# Las CONSTANTES FÍSICAS de módulo (escala biológica absoluta HERD_*, dron DRONE_*,
# disuasión DETER_*, bordeo de zona WOLF_ZONE_SKIRT_*, evitación COW_AVOID_*/W_*, corzos
# CORZO_*) viven en la cabecera de world.py y quedan congeladas por el tag (no son params
# del constructor; no se pueden fijar desde aquí). NO TOCAR ninguno de estos sin re-medir.
CONFIG_V2 = dict(
    # --- equipo y rebaño ---
    n_active_drones=4, n_reserve_drones=4, n_cows=6,
    wolves_min=1, wolves_max=5,
    # --- DISTRACCIÓN ON (3c): 3 tipos de episodio ~1/3 (solo-lobos / solo-distracción / mixto);
    #     la distracción es corzo o JABALÍ ~50/50 (mismo comportamiento; substream RNG separado) ---
    corzos_min=1, corzos_max=3, corzo_speed=4.0,
    corzo_episode_probs=(1 / 3, 1 / 3, 1 / 3), distraction_species_prob=0.5,
    # --- campo y layout (v3.0: TERRENO 500 + colchón del rebaño; ver bloque de cabecera) ---
    parcel_size=(500.0, 500.0), cow_spawn=(150.0, 350.0), station_dir=(0.0, 1.0),
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
    # --- v2.5 (Nivel A): SPAWN EN SUBGRUPOS (1-2 grupos desiguales en sectores distintos; substream
    #     RNG propio -> vacas/drones/corzos bit a bit vs clustered). El default de World sigue siendo
    #     "clustered" (checks bit a bit); la v2.5 MIDE con "grouped". ---
    wolf_spawn_mode="grouped",
    # --- v3.0 (CEBO PERFECTO, piezas 2+3): reparto de masa FIJO (sector-CEBO = wolf_decoy_size lobos,
    #     capado a n-2 -> el ASALTO conserva quórum >= 2; fin del k~unif del diagnóstico 2026-07-22) y
    #     TIMING PROGRAMADO del cebo (merodea a >decoy_hold_dist del ACTIVE más cercano hasta que el
    #     asalto está a <=assault_trigger_dist de su presa; entonces se lanza). Cebo DISEÑADO, NO
    #     emergente (etapa 1/2). decoy_size elegido MIDIENDO 1 vs 2 (¿ancla el cebo de 1?). ---
    wolf_decoy_size=1,
    # --- escolta / terminal (máquina de fases + guiado al refugio + disuasión) ---
    r_detect=100.0, r_confirm=40.0, episode_time_factor=4.0, escort_enabled=True,
    # --- batería / cola de carga + RELEVO REALISTA (hand-off, sin teletransporte) ---
    #     v2.4: la CARGA se DERIVA (CHARGE_TO_FLIGHT_RATIO=1.5 -> charge_full≈160 s; charge_full es DEPRECATED, no se
    #     pasa); baterías iniciales ALEATORIAS [battery_init_min=0.25, 1] + reserva espejo (substream RNG separado).
    battery_capacity=600.0, battery_init_min=0.25, announce_threshold=0.20, relay_handoff_tol=2.0,
    # --- guardia de teletransporte: solo LOGUEA (no afecta la dinámica) ---
    teleport_guard=False, motion_tol=1.5,
)

# Set FIJO de semillas (mismas para cada tipo, forzando el tipo -> muestra sólida y comparable).
N_PER_KIND = 100
EVAL_SEEDS = tuple(range(N_PER_KIND))
KINDS = ("lobos", "corzos", "mixto")
KIND_LABEL = {"lobos": "solo-lobos", "corzos": "solo-corzos", "mixto": "mixto"}
TERMINALS = ("success", "predation", "timeout")
FROZEN_TAG = "v3.4-baseline"   # tag git del commit congelado: LÍNEA RÍGIDA + ROLES INVERTIDOS DEL CEBO.
                               # v3.3 (aceptada por el usuario EN GIF, congelada aquí): 1) TRINQUETE del avance —
                               # el aim de la barrera es MONÓTONO hacia fuera (la línea sale hacia los lobos y SE
                               # QUEDA fuera; métrica del usuario: dist centro->vaca más próxima CRECE mientras los
                               # lobos se acercan — 58% por ventanas, series 13->50-60 sostenidas); 2) INVERSIÓN DE
                               # ROLES del cebo (wolf_controllers.py) — el CEBO se deja confirmar PRIMERO (se muestra
                               # + ALA ROTA arrastrando al investigador) y el ASALTO espera OSCURO por anillos
                               # (STAGE r_detect+50 -> CREEP r_detect+25 -> DEEP r_confirm+25) hasta que la barrera
                               # está comprometida: ancla = sector-cebo en ~60% de episodios de 2 frentes (techo
                               # medido ~73%: el 27% restante el asalto NACE a 108-130 m de un dron y es cazado por
                               # el barrido — geometría de spawn, irreducible del lado del lobo) con el asalto a
                               # <=150 de su presa al saltar ESCOLTA en 42-45% (frontera ancla<->profundidad ~1:1
                               # medida en 8 configuraciones; vías refutadas documentadas en wolf_controllers.py).
                               # v3.4 (regla del usuario: si un dron avanza, avanzan TODOS): la barrera es una LÍNEA
                               # RÍGIDA — UNA pose (centro C + eje u) con offsets FIJOS y GOBERNADOR DEL MÁS REZAGADO
                               # (paso_pose = max(0, DRONE_MAX_SPEED·dt − err_max); la formación avanza al ritmo del
                               # más rezagado y espera QUIETA mientras se forma). Rigidez MEDIDA (28 eps): error de
                               # estación FORMADA p95 1.66 / máx 4.71 m; espaciado p5-p95 19.7-20.3 (nominal 20);
                               # colinealidad p95 0.20 m. El CIERRE LOCAL v3.3 queda ELIMINADO (deformaba la línea
                               # por definición); su coste MEDIDO: cruces de segmento 56 -> 149/28 eps (hacia dentro
                               # con la línea en pie 33 -> 92) y PENETRADO 4159 -> 13593 pasos — agujeros DELIBERADOS
                               # de la baseline rígida (junto a flancos + espalda del anillo + 2º frente lastrado por
                               # la inversión). Defaults de World en 300 intactos (face_check bit a bit). METRO DGX.
                               # Nota a batir del MARL -> Reactive v3.4 (la línea rígida con el cebo invertido).

# Referencia CONGELADA de severidad (media de muertes/ep) por tipo, para detectar DERIVA.
# Se rellena tras la primera medición; en re-corridas debe coincidir (mundo reproducible POR ENTORNO).
# v3.4 (METRO DGX): LÍNEA RÍGIDA + ROLES INVERTIDOS DEL CEBO (ver FROZEN_TAG). Al Dummy lo mueve poco
# el lado lobo (+0.05/+0.10 vs v3.2: el asalto que espera oscuro apenas cambia contra drones clavados);
# el que cambia es el Reactive (1.91/1.96 -> 2.68/2.77, +0.77/+0.81): el cebo INVERTIDO ancla la línea
# única en ~60% de los 2 frentes (el asalto entra por el frente libre) y la línea rígida sin cierres
# paga sus corredores — POR FIN el multi-frente scriptado rinde contra la defensa. Es medida, no
# objetivo. Contraste v3.2: Dummy 3.77/0/3.74 · Reactive 1.91/0/1.96. v3.1: 3.74/0/3.69 · 2.18/0/2.21.
# v3.0: 3.85/0/3.69 · 1.00/0/1.14 (artefacto del perseguidor). v2.9: 3.98/0/3.88 · 2.46/0/2.44.
REFERENCE_SEVERITY = {
    "lobos": 3.82,   # solo-lobos (amenaza pura); succ 9 / pred 83 / timeout 8; n_safe 2.75
    "corzos": 0.00,  # solo-corzos = SIN amenaza (100/100 timeout; el rebaño pasta, n_safe 0)
    "mixto": 3.84,   # ≈ solo-lobos (los corzos solo consumen ciclos de investigación); succ 6/pred 85/to 9; n_safe 2.74
}

# Tolerancia de deriva (la media es exacta y reproducible bit a bit; margen mínimo por si
# se reordena alguna operación NumPy sin cambiar la física).
DRIFT_TOL = 0.005


def build_world(seed: int, kind: str, wolf_controller=None) -> World:
    """World v2 (CONFIG_V2) con el tipo de episodio FORZADO (muestra por tipo).
    `wolf_controller` (fase RL, opcional): instancia WolfController inyectada al World
    (lobos aprendidos); con None (default) TODO queda exactamente como estaba (scriptado
    v2.4 — pasar None es el default del propio World)."""
    return World(seed=seed, episode_kind=kind, wolf_controller=wolf_controller, **CONFIG_V2)


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
             seeds=EVAL_SEEDS, kinds=KINDS, wolf_controller_factory=None) -> dict:
    """Evalúa un coordinador sobre el mundo v2: para CADA tipo, corre todas las semillas y
    agrega severidad (media±desv), reparto de terminales y n_safe medio. Reutilízalo para
    comparar un coordinador nuevo: pasa su factory; misma config, mismas semillas.
    `wolf_controller_factory` (fase RL, opcional): callable SIN argumentos que devuelve una
    instancia WolfController FRESCA por episodio (lobos aprendidos con el MISMO arnés y
    semillas: apples-to-apples también para el adversario). Con None (default), scriptado
    v2.4 — bit a bit lo de siempre."""
    by_kind = {}
    all_deaths, all_safe, all_terms = [], [], Counter()
    for kind in kinds:
        deaths, safe, terms, episodes = [], [], Counter(), []
        for s in seeds:
            wc = wolf_controller_factory() if wolf_controller_factory is not None else None
            w = build_world(s, kind, wolf_controller=wc)
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
    """Cross-check: CONFIG_V2 debe ser BIT A BIT == 'defaults de World + corzos ON + los extras
    DOCUMENTADOS de la versión congelada'. Extras v3.0 (los ÚNICOS sobre defaults; todo lo demás
    espeja defaults): wolf_spawn_mode=grouped (v2.5) + TERRENO 500 con colchón (parcel_size,
    cow_spawn — pieza 1) + CEBO PERFECTO (wolf_decoy_size — piezas 2+3). El default de World se
    queda en 300/clustered/None para los checks (face_check bit a bit). Si algún OTRO valor
    explícito se desviara, el mundo medido no sería el congelado."""
    ok = True
    for kind in KINDS:
        for s in seeds:
            a = build_world(s, kind)                                      # CONFIG_V2 explícito
            b = World(seed=s, episode_kind=kind, corzos_min=1, corzos_max=3,
                      wolf_spawn_mode="grouped",                          # defaults + corzos + grouped
                      parcel_size=(500.0, 500.0), cow_spawn=(150.0, 350.0),   # + terreno v3.0
                      wolf_decoy_size=CONFIG_V2["wolf_decoy_size"])           # + cebo v3.0
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
