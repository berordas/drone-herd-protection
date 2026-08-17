"""hrl/run_e0.py — CLI de los EXPERIMENTOS de la Etapa 0 (jerárquico).

Uso (dentro del contenedor, CPU):
    python3 hrl/run_e0.py --exp e0a|e01|e02|e03|e04|e05 [--procs N] [--pairs N] [--gifs]

Montado SOBRE el arnés de evaluación existente (mismo World/CONFIG_V2, mismas semillas por
tipo) y muestreando en la MISMA frontera que los envs (lección SyncedReactiveCoordinator):
el bucle refresca la capa de lobos UNA vez por tick ANTES de coord.act() — nunca se usa
SyncedReactiveCoordinator aquí (refrescaría por segunda vez). TODOS los episodios de TODOS
los experimentos corren con EpisodeAudit (aserciones del protocolo §2: orden del cebo
CRITICAL, procedencia de cada muerte, reloj de escolta, contratos). Artefactos:
/data/hrl_e0/<exp>/{config.json, results.json, REPORT.md, gifs/, timelines/}.

Experimentos (semillas EMPAREJADAS entre brazos: mismo seed+kind, distinta política):
  e0a  Impuesto de interfaz. (i) cubierto por hrl_check (bit a bit). (ii) CEBO vía capa en
       modo membresías=spawn sobre las MISMAS 58 parejas (seed,kind) de 2 frentes de
       cebo_floor_v34.json — tolerancias: sev 3.50±0.15 · KNC 26.6%±3 · ancla-cebo
       65.5%±5. (iii) CEBO vía capa (manager: cebo=índice mín, Δ=180°) desde spawns
       ARBITRARIOS n>=3 — sin referencia numérica: lote de visionado + aserciones.
  e01  Margen Δ del cebo: CEBO(Δ=180°) vs MASA, n>=3, oponentes Reactive y run02;
       piloto 50 pares -> n = ceil((1.96·σ̂/(Δ̂/3))²) acotado [200,400]; variante de
       escenificación hold ∈ {50, 5, -10} (anillos 150/105/90).
  e02  Latencias -> K: distribuciones de t(inicio->staged/show/confirm/flip/commit),
       t(release->1ª muerte), T_safe y ventana del release sobre los episodios CEBO de
       e01 + grabación por-frontera de los canales del detector LURE_COMMIT para el ajuste
       ROC de sus umbrales. Propuesta K = p75-p90 de t(inicio->commit), múltiplo de 5.
  e03  Frontera de quórum: wolves_min=wolves_max=n, n ∈ {2,3,4,5}, CEBO vs MASA, ambos
       oponentes; n=2 partido por presencia de ternero.
  e04  Espejo dron: Dummy / Reactive / PROPORCIONAL / run02 contra (a) lobos CEBO-forzado
       n>=3 y (b) mezcla scriptada v3.4; carrera de redespliegue por episodio.
  e05  Coste de conmutación: lobos CEBO<->MASA y drones 4-0<->3-1<->2-2 forzados cada
       K ∈ {250,500,1000,2000} vs control sin conmutar; Δsev + hueco de cobertura +
       interacción con relevos.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pathlib
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from baseline import CONFIG_V2                                     # noqa: E402
from coordinators import DummyCoordinator, ReactiveCoordinator     # noqa: E402
from world import ACTIVE, DETER_RADIUS, World                      # noqa: E402

from hrl.behavior_checks import EpisodeAudit                       # noqa: E402
from hrl.events import format_timeline                             # noqa: E402
from hrl.options_drone import (AllocatorCoordinator, ProportionalAllocatorCoordinator,  # noqa: E402
                               analyze_threats)
from hrl.options_wolf import WolfOptionLayer                       # noqa: E402
from hrl.scripted_manager import SwitchingAllocator, SwitchingWolfManager  # noqa: E402

OUT_BASE = "/data/hrl_e0"
RUN02_MODEL = "/data/drones/run02_v34/model.zip"
CEBO_FLOOR_JSON = "/data/wolves/run08_dieta50/cebo_floor_v34.json"
REF_E0A = {"sev": 3.50, "sev_tol": 0.15, "knc": 0.266, "knc_tol": 0.03,
           "ancla": 0.655, "ancla_tol": 0.05}
GATE_OPEN_M = 60.0            # e05: "puerta abierta" = punto-puerta de un clúster a >= 60 m
_RUN02 = None                 # caché del modelo run02 POR PROCESO (fork)


# ====================================================================== #
# Fábricas
# ====================================================================== #
def make_world(seed: int, kind: str, wolf_controller=None, overrides: dict | None = None):
    cfg = dict(CONFIG_V2)
    if overrides:
        cfg.update(overrides)
    return World(seed=seed, episode_kind=kind, wolf_controller=wolf_controller, **cfg)


def make_wolf(spec):
    """None = scriptado puro. ("opt", (nombre, params)) = opción fija.
    ("switch", {sequence, period}) = conmutador E0.5."""
    if spec is None:
        return None
    tag = spec[0]
    if tag == "opt":
        return WolfOptionLayer(option=(spec[1][0], dict(spec[1][1])))
    if tag == "switch":
        seq = [(n, dict(p)) for n, p in spec[1]["sequence"]]
        return WolfOptionLayer(manager=SwitchingWolfManager(seq, spec[1]["period"]))
    raise ValueError(f"wolf spec desconocida: {spec!r}")


def make_drone(spec):
    name = spec if isinstance(spec, str) else spec[0]
    if name == "reactive":
        return ReactiveCoordinator
    if name == "dummy":
        return lambda w: DummyCoordinator(w.n_drones)
    if name == "proporcional":
        return ProporcionalFactory
    if name == "particion":
        nf, ng = spec[1]
        return lambda w: AllocatorCoordinator(w, (int(nf), int(ng)))
    if name == "switch_alloc":
        period = spec[1]
        return lambda w: SwitchingAllocator(w, period=int(period))
    if name == "run02":
        return Run02Factory
    raise ValueError(f"drone spec desconocida: {spec!r}")


def ProporcionalFactory(w):
    return ProportionalAllocatorCoordinator(w)


def Run02Factory(w):
    global _RUN02
    if _RUN02 is None:
        from stable_baselines3 import PPO
        _RUN02 = PPO.load(RUN02_MODEL, device="cpu")
    from rl.residual_drone_coordinator import ResidualDroneCoordinator
    return ResidualDroneCoordinator(w, model=_RUN02)


# ====================================================================== #
# Sondas por-tick (opcionales, por experimento; nombradas para que el job sea picklable)
# ====================================================================== #
def _probe_carrera(w, coord, wolf, st):
    """e04: CARRERA DE REDESPLIEGUE — t(un guardia a <= DETER del clúster secundario) vs
    t(asalto a <= assault_trigger_dist de su presa)."""
    inner = getattr(coord, "inner", None)
    if st.get("t_guard") is None and isinstance(coord, AllocatorCoordinator):
        seats = coord._seats.seats()
        ng = coord.particion[1]
        guard = [int(d) for d in seats[len(seats) - ng:] if d >= 0] if ng > 0 else []
        if guard and inner is not None:
            info = analyze_threats(w, inner)
            if info["secundario"] is not None:
                pts = info["pts"][info["clusters"][info["secundario"]]]
                d = np.linalg.norm(w.drones[guard][:, None, :] - pts[None, :, :], axis=2)
                if float(d.min()) <= DETER_RADIUS:
                    st["t_guard"] = int(w.step_count)
    if st.get("t_asalto") is None:
        if wolf is not None and wolf.assault_indices().size > 0 and w.pack_prey2 >= 0:
            s2 = wolf.assault_indices()
        elif len(w.wolf_group_sizes) == 2 and w.pack_prey2 >= 0:
            s2 = np.arange(int(w.wolf_group_sizes[0]), w.n_wolves)
        else:
            return
        p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
        if p2 is not None and \
                float(np.linalg.norm(w.wolves[s2].mean(axis=0) - p2)) <= w.assault_trigger_dist:
            st["t_asalto"] = int(w.step_count)


def _probe_puerta(w, coord, wolf, st):
    """e05: HUECO DE COBERTURA — por tick, la peor 'puerta' entre clústeres de amenaza:
    dist del ACTIVE más cercano al punto-puerta (borde del rebaño + standoff en el rumbo
    del clúster). Acumula ticks con puerta >= GATE_OPEN_M e integral (m·s) del exceso."""
    from hrl.events import reactive_of
    inner = reactive_of(coord)
    if not hasattr(inner, "barrier_standoff"):
        return
    act = w.drones[w.drone_state == ACTIVE]
    if act.shape[0] == 0:
        return
    info = analyze_threats(w, inner)
    if not info["clusters"]:
        return
    m = w.cow_alive & ~w.cow_safe
    if not m.any():
        return
    herd = w.cows[m]
    herd_c = info["herd_c"]
    worst = 0.0
    for cl in info["clusters"]:
        c = info["pts"][cl].mean(axis=0) - herd_c
        n = float(np.linalg.norm(c))
        if n < 1e-9:
            continue
        u = c / n
        gate = herd_c + u * (float(((herd - herd_c) @ u).max()) + inner.barrier_standoff)
        worst = max(worst, float(np.linalg.norm(act - gate, axis=1).min()))
    if worst >= GATE_OPEN_M:
        st["puerta_ticks"] = st.get("puerta_ticks", 0) + 1
        st["puerta_integral"] = st.get("puerta_integral", 0.0) + (worst - GATE_OPEN_M) * w.dt


def _probe_lure_rec(w, coord, wolf, st):
    """e02: graba por FRONTERA (cada 5 ticks) los canales del detector LURE_COMMIT para el
    ajuste ROC offline: diffs angulares |dron−señuelo| ordenados (hasta 5, rad) + distancia
    del ACTIVE más cercano al punto-puerta del rumbo REAL del asalto."""
    if int(w.step_count) % 5 != 0:
        return
    rows = st.setdefault("lure_rows", [])
    act = w.drones[w.drone_state == ACTIVE]
    dec = wolf.decoy_indices() if wolf is not None else np.zeros(0, dtype=int)
    asa = wolf.assault_indices() if wolf is not None else np.zeros(0, dtype=int)
    m = w.cow_alive & ~w.cow_safe
    if act.shape[0] == 0 or dec.size == 0 or asa.size == 0 or not m.any():
        return
    herd = w.cows[m]
    herd_c = herd.mean(axis=0)
    v_dec = w.wolves[dec].mean(axis=0) - herd_c
    v_asa = w.wolves[asa].mean(axis=0) - herd_c
    if min(np.linalg.norm(v_dec), np.linalg.norm(v_asa)) < 1e-9:
        return
    ang_dec = np.arctan2(v_dec[1], v_dec[0])
    ang_dr = np.arctan2((act - herd_c)[:, 1], (act - herd_c)[:, 0])
    diffs = np.sort(np.abs((ang_dr - ang_dec + np.pi) % (2 * np.pi) - np.pi))[:5]
    u = v_asa / np.linalg.norm(v_asa)
    gate = herd_c + u * (float(((herd - herd_c) @ u).max()) + 17.32)
    gate_clear = float(np.linalg.norm(act - gate, axis=1).min())
    rows.append([int(w.step_count)] + [round(float(x), 4) for x in diffs] +
                [-1.0] * (5 - diffs.size) + [round(gate_clear, 2)])


_PROBES = {"carrera": _probe_carrera, "puerta": _probe_puerta, "lure_rec": _probe_lure_rec}


# ====================================================================== #
# Bucle de episodio + pool
# ====================================================================== #
def trim_events(events: list[dict]) -> list[dict]:
    """Los flancos LURE pueden oscilar: en results.json se guardan el PRIMER LURE_COMMIT y
    el recuento de oscilaciones (la serie completa se regenera determinista al renderizar)."""
    out, lure_seen, toggles = [], False, 0
    for e in events:
        if e["ev"] in ("LURE_COMMIT", "LURE_COMMIT_END"):
            toggles += 1
            if e["ev"] == "LURE_COMMIT" and not lure_seen:
                lure_seen = True
                out.append(e)
            continue
        out.append(e)
    if toggles:
        out.append({"t": out[-1]["t"] if out else 0, "ev": "LURE_TOGGLES", "n": toggles})
    return out


def run_episode(job: dict) -> dict:
    seed, kind = int(job["seed"]), job["kind"]
    arm = job["arm"]
    wolf = make_wolf(arm.get("wolf"))
    w = make_world(seed, kind, wolf_controller=wolf, overrides=job.get("overrides"))
    coord = make_drone(arm["drone"])(w)
    w.reset()
    audit = EpisodeAudit(
        w, coord, wolf_controller=wolf,
        meta={"seed": seed, "kind": kind, "arm": arm["name"]},
        decoy_indices=(wolf.decoy_indices if wolf is not None else None),
        assault_indices=(wolf.assault_indices if wolf is not None else None),
        option_name=arm.get("option_name"))
    probe = _PROBES.get(job.get("probe", ""), None)
    st: dict = {}
    while True:
        if wolf is not None:
            wolf.refresh(w)
        audit.on_boundary()
        if probe is not None:
            probe(w, coord, wolf, st)
        wp_before = w.drone_waypoint.copy()
        wp = coord.act(w.get_observation())
        audit.check_command(wp_before, wp)
        _o, _r, term, trunc, _i = w.step(wp)
        audit.after_step()
        if term or trunc:
            break
    rec = audit.finalize()
    rec["events"] = trim_events(rec["events"])
    rec["probe"] = {k: v for k, v in st.items() if k != "lure_rows"}
    if "lure_rows" in st:
        rec["lure_rows"] = st["lure_rows"]
    return rec


def run_jobs(jobs: list[dict], procs: int) -> list[dict]:
    if procs <= 1:
        return [run_episode(j) for j in jobs]
    with mp.Pool(processes=procs) as pool:
        return pool.map(run_episode, jobs, chunksize=1)


# ====================================================================== #
# Estadística
# ====================================================================== #
def boot_ci(vals, n_boot: int = 10_000, seed: int = 20_260_817):
    """(media, IC95 bajo, IC95 alto) por bootstrap (RNG PROPIO del análisis — no toca
    ningún stream del mundo)."""
    v = np.asarray([x for x in vals if x is not None], dtype=float)
    if v.size == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, v.size, size=(n_boot, v.size))].mean(axis=1)
    return float(v.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def frac_ci(mask_list, **kw):
    return boot_ci([1.0 if b else 0.0 for b in mask_list], **kw)


def knc_of(records: list[dict]):
    """Fracción killer-NO-confirmado sobre TODAS las muertes (contador de cebo_diag/run08:
    killer = lobo más cercano, confirmación = latch de la barrera en la frontera previa)."""
    flags = [not d["killer_confirmado"] for r in records for d in r["deaths"]]
    return frac_ci(flags) if flags else (None, None, None)


def seeds_with(kind: str, want, count: int, overrides: dict | None = None,
               start: int = 0, hard_cap: int = 600) -> list[int]:
    """Primeras `count` semillas cuyo spawn cumple `want(world)` (probe con reset, barato)."""
    out, seed = [], start
    while len(out) < count and seed < start + hard_cap:
        w = make_world(seed, kind, overrides=overrides)
        w.reset()
        if want(w):
            out.append(seed)
        seed += 1
    if len(out) < count:
        raise RuntimeError(f"solo {len(out)}/{count} semillas válidas en {kind}")
    return out


# ====================================================================== #
# GIFs + timelines (lote de visionado)
# ====================================================================== #
def render_gif(job: dict, tag: str, outdir: pathlib.Path, max_frames: int = 800,
               tail: int = 50) -> dict:
    """Re-corre el episodio (determinista) grabando snapshots y renderiza la VENTANA
    relevante (mismo criterio que los GIFs de run08); sidecar timeline.txt con la línea
    temporal de eventos + muertes con procedencia."""
    from render import render_episode
    seed, kind = int(job["seed"]), job["kind"]
    wolf = make_wolf(job["arm"].get("wolf"))
    w = make_world(seed, kind, wolf_controller=wolf, overrides=job.get("overrides"))
    coord = make_drone(job["arm"]["drone"])(w)
    w.reset()
    audit = EpisodeAudit(w, coord, wolf_controller=wolf,
                         meta={"seed": seed, "kind": kind, "arm": job["arm"]["name"]},
                         decoy_indices=(wolf.decoy_indices if wolf is not None else None),
                         assault_indices=(wolf.assault_indices if wolf is not None else None),
                         option_name=job["arm"].get("option_name"))
    hist = [{**w.snapshot(), "battery": w.battery.copy()}]
    while True:
        if wolf is not None:
            wolf.refresh(w)
        audit.on_boundary()
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        audit.after_step()
        hist.append({**w.snapshot(), "battery": w.battery.copy()})
        if term or trunc:
            break
    rec = audit.finalize()

    def key(s):
        return (s["phase"], s["n_depredadas"], s["n_safe"],
                int(np.sum(s.get("corzo_dismissed", []))))
    last = max((k for k in range(1, len(hist)) if key(hist[k]) != key(hist[k - 1])),
               default=0)
    win = hist[:min(len(hist), last + tail + 1)]
    frames = win[::max(1, len(win) // max_frames)]
    (outdir / "gifs").mkdir(parents=True, exist_ok=True)
    (outdir / "timelines").mkdir(parents=True, exist_ok=True)
    name = f"{tag}_seed{seed}_{kind}_sev{w.n_depredadas}"
    gif = outdir / "gifs" / f"{name}.gif"
    render_episode(w, frames, save_path=str(gif))
    head = (f"{name} | arm={job['arm']['name']} status={w.status} sev={w.n_depredadas} "
            f"steps={w.step_count} grupos={rec['grupos_spawn']} | muertes con procedencia "
            f"al final")
    body = format_timeline(rec["events"], header=head)
    body += "".join(
        f"t={d['t']:>6d}  MUERTE {d['kind']}#{d['prey']} flankers={d['flankers']} "
        f"conf={d['flankers_confirmado']} nearest={d['killer_nearest']}"
        f"(conf={d['killer_confirmado']}) grupo={d['grupo_killer']} "
        f"octante={d['octante_vs_ancla']} gotera={d['cruzo_gotera']} "
        f"dflip={d['ticks_desde_flip']}\n" for d in rec["deaths"])
    (outdir / "timelines" / f"{name}.txt").write_text(body)
    return {"gif": str(gif), "sev": int(w.n_depredadas), "tag": tag}


def pick_visionado(records: list[dict], jobs_by_key: dict, max_gifs: int = 12) -> list[tuple]:
    """Criterio §2B (adaptado a un solo brazo): 1º episodio con LURE_COMMIT · 2 medianos ·
    extremos de severidad · TODOS los violadores de aserciones · 1 con release+muertes."""
    chosen: list[tuple[str, dict]] = []

    def add(tag, rec):
        k = (rec["seed"], rec["kind"])
        if k in jobs_by_key and all(c[1] is not rec for c in chosen) and len(chosen) < max_gifs:
            chosen.append((tag, rec))
    for r in records:
        if r["critical"] or r["violations"]:
            add("violacion", r)
    lure = [r for r in records if r["clock"]["t_lure_commit"] is not None]
    if lure:
        add("primer_lure", min(lure, key=lambda r: (r["seed"], r["kind"])))
    sevs = sorted(records, key=lambda r: (r["sev"], r["seed"]))
    if sevs:
        add("sev_max", sevs[-1])
        add("sev_min", sevs[0])
        med = len(sevs) // 2
        add("mediano_a", sevs[med])
        add("mediano_b", sevs[max(0, med - 1)])
    strike = [r for r in records
              if any(e["ev"] == "STRIKE_RESOLVED" and e.get("outcome") == "kill"
                     for e in r["events"])]
    if strike:
        add("release_con_muerte", max(strike, key=lambda r: r["sev"]))
    dosf = [r for r in records if len(r["grupos_spawn"]) == 2]
    if dosf:
        add("spawn_2grupos_manager", dosf[0])
    return chosen


# ====================================================================== #
# E0.A — impuesto de interfaz
# ====================================================================== #
def exp_e0a(args):
    outdir = pathlib.Path(OUT_BASE) / "e0a"
    outdir.mkdir(parents=True, exist_ok=True)
    ref = json.load(open(CEBO_FLOOR_JSON))
    ref_by = {(e["seed"], e["kind"]): e for e in ref["episodes"]}

    # (ii) CEBO vía capa, membresías = spawn, sobre las MISMAS 58 parejas de 2 frentes.
    arm_ii = {"name": "cebo_capa_spawn", "wolf": ("opt", ("CEBO", {"membership": "spawn"})),
              "drone": "reactive", "option_name": "CEBO"}
    jobs_ii = [{"seed": s, "kind": k, "arm": arm_ii} for (s, k) in sorted(ref_by)]
    recs_ii = run_jobs(jobs_ii, args.procs)

    sev_m, sev_lo, sev_hi = boot_ci([r["sev"] for r in recs_ii])
    knc_m, knc_lo, knc_hi = knc_of(recs_ii)
    con_ancla = [r for r in recs_ii if r["primer_ancla"] is not None]
    ancla_m, ancla_lo, ancla_hi = frac_ci(
        [r["primer_ancla"] < r["grupos_spawn"][0] for r in con_ancla])
    exact = sum(1 for r in recs_ii if r["sev"] == ref_by[(r["seed"], r["kind"])]["n_depredadas"])
    tol_ok = {
        "sev": abs(sev_m - REF_E0A["sev"]) <= REF_E0A["sev_tol"],
        "knc": abs(knc_m - REF_E0A["knc"]) <= REF_E0A["knc_tol"],
        "ancla": abs(ancla_m - REF_E0A["ancla"]) <= REF_E0A["ancla_tol"],
    }

    # (iii) CEBO manager (Δ=180°, hold default) desde spawns arbitrarios n>=3.
    arm_iii = {"name": "cebo_capa_manager", "wolf": ("opt", ("CEBO", {"delta_deg": 180.0})),
               "drone": "reactive", "option_name": "CEBO"}
    seeds3 = seeds_with("lobos", lambda w: w.n_wolves >= 3, 30)
    seeds3m = seeds_with("mixto", lambda w: w.n_wolves >= 3, 10)
    jobs_iii = ([{"seed": s, "kind": "lobos", "arm": arm_iii} for s in seeds3] +
                [{"seed": s, "kind": "mixto", "arm": arm_iii} for s in seeds3m])
    recs_iii = run_jobs(jobs_iii, args.procs)

    crit = [r for r in recs_ii + recs_iii if r["critical"]]
    viol = [r for r in recs_ii + recs_iii if r["violations"]]
    s3_m, s3_lo, s3_hi = boot_ci([r["sev"] for r in recs_iii])
    staged = sum(1 for r in recs_iii if r["clock"]["t_staged"] is not None)
    lure = sum(1 for r in recs_iii if r["clock"]["t_lure_commit"] is not None)
    kills_post = sum(1 for r in recs_iii
                     if any(e["ev"] == "STRIKE_RESOLVED" and e.get("outcome") == "kill"
                            for e in r["events"]))

    resumen = {
        "ii": {"n": len(recs_ii), "sev": [sev_m, sev_lo, sev_hi],
               "sev_exacta_vs_floor": f"{exact}/{len(recs_ii)}",
               "knc": [knc_m, knc_lo, knc_hi], "n_con_ancla": len(con_ancla),
               "ancla_cebo": [ancla_m, ancla_lo, ancla_hi],
               "referencias": REF_E0A, "tolerancias_ok": tol_ok},
        "iii": {"n": len(recs_iii), "sev": [s3_m, s3_lo, s3_hi],
                "eps_staged": staged, "eps_lure_commit": lure,
                "eps_muerte_post_release": kills_post,
                "knc": list(knc_of(recs_iii))},
        "criticals": len(crit), "violaciones": len(viol),
    }
    config = {"fecha": datetime.now().isoformat(timespec="seconds"),
              "arms": {"ii": arm_ii, "iii": arm_iii},
              "pares_ii": sorted(ref_by), "seeds_iii": {"lobos": seeds3, "mixto": seeds3m},
              "referencia": CEBO_FLOOR_JSON, "procs": args.procs}
    _dump(outdir, config, recs_ii + recs_iii, resumen)

    # Lote de visionado: violadores (TODOS) + criterio §2B sobre (iii) (+1 par de (ii)).
    gifs = []
    if args.gifs:
        jobs_by_key = {(j["seed"], j["kind"]): j for j in jobs_iii}
        chosen = pick_visionado(recs_iii, jobs_by_key)
        for r in crit:
            key = (r["seed"], r["kind"])
            src = jobs_by_key.get(key) or {"seed": r["seed"], "kind": r["kind"], "arm": arm_ii}
            gifs.append(render_gif(src, "CRITICAL", outdir))
        for tag, r in chosen:
            gifs.append(render_gif(jobs_by_key[(r["seed"], r["kind"])], tag, outdir))
        pair0 = sorted(ref_by)[0]
        gifs.append(render_gif({"seed": pair0[0], "kind": pair0[1], "arm": arm_ii},
                               "ii_spawn", outdir))
    _report_e0a(outdir, resumen, gifs)
    print(json.dumps(resumen, indent=1, ensure_ascii=False))
    return resumen


def _report_e0a(outdir, resumen, gifs):
    ii, iii = resumen["ii"], resumen["iii"]
    ok = ii["tolerancias_ok"]
    lines = [
        "# E0.A — Impuesto de interfaz de la capa de opciones", "",
        f"(i) Bit a bit: cubierto por hrl_check (MASA ≡ script en 1 grupo; CEBO/spawn ≡ "
        f"script en 2 grupos; Allocator 4-0 ≡ Reactive).", "",
        f"(ii) CEBO vía capa (membresías=spawn) sobre las {ii['n']} parejas de 2 frentes "
        f"de run08:", "",
        "| métrica | capa | referencia scriptado | tolerancia | ¿dentro? |",
        "|---|---|---|---|---|",
        f"| severidad 2f | {ii['sev'][0]:.2f} [{ii['sev'][1]:.2f}, {ii['sev'][2]:.2f}] | "
        f"{REF_E0A['sev']:.2f} | ±{REF_E0A['sev_tol']} | {'SÍ' if ok['sev'] else 'NO'} |",
        f"| KNC | {ii['knc'][0]:.1%} | {REF_E0A['knc']:.1%} | ±3 pt | "
        f"{'SÍ' if ok['knc'] else 'NO'} |",
        f"| ancla=cebo | {ii['ancla_cebo'][0]:.1%} (n={ii['n_con_ancla']}) | "
        f"{REF_E0A['ancla']:.1%} | ±5 pt | {'SÍ' if ok['ancla'] else 'NO'} |",
        "",
        f"Severidad por episodio EXACTA a la del suelo scriptado: {ii['sev_exacta_vs_floor']}.",
        "",
        f"(iii) CEBO manager (Δ=180°) desde spawns arbitrarios n>=3 ({iii['n']} eps): "
        f"sev {iii['sev'][0]:.2f} [{iii['sev'][1]:.2f}, {iii['sev'][2]:.2f}] · staged "
        f"{iii['eps_staged']}/{iii['n']} · LURE_COMMIT {iii['eps_lure_commit']}/{iii['n']} · "
        f"muerte post-release {iii['eps_muerte_post_release']}/{iii['n']} · KNC "
        f"{(iii['knc'][0] or 0):.1%}.",
        "",
        f"Aserciones: CRITICAL={resumen['criticals']} · violaciones de contrato="
        f"{resumen['violaciones']}.",
        "",
        "## Lote de visionado",
    ] + [f"- [{g['tag']}] sev={g['sev']} — {g['gif']}" for g in gifs]
    (outdir / "REPORT.md").write_text("\n".join(lines) + "\n")


# ====================================================================== #
# E0.1 — margen Δ (CEBO vs MASA) · E0.2 — latencias/K · E0.3 — quórum ·
# E0.4 — espejo dron · E0.5 — conmutación
# ====================================================================== #
ARM_MASA = {"name": "masa", "wolf": ("opt", ("MASA", {})), "drone": "reactive",
            "option_name": "MASA"}


def _arm_cebo(hold: float, drone="reactive"):
    return {"name": f"cebo_h{int(hold)}_{drone if isinstance(drone, str) else drone[0]}",
            "wolf": ("opt", ("CEBO", {"delta_deg": 180.0, "hold": float(hold)})),
            "drone": drone, "option_name": "CEBO"}


def exp_e01(args):
    outdir = pathlib.Path(OUT_BASE) / "e01"
    outdir.mkdir(parents=True, exist_ok=True)
    pool_l = [("lobos", s) for s in seeds_with("lobos", lambda w: w.n_wolves >= 3, 200)]
    pool_m = [("mixto", s) for s in seeds_with("mixto", lambda w: w.n_wolves >= 3, 200)]

    def run_arm(pairs, arm, probe=None):
        return run_jobs([{"seed": s, "kind": k, "arm": arm,
                          **({"probe": probe} if probe else {})} for k, s in pairs],
                        args.procs)

    # PILOTO (Reactive, hold 50, 25+25 pares) -> σ̂ de la diferencia -> n de pares.
    pilot = pool_l[:25] + pool_m[:25]
    cebo_p = run_arm(pilot, _arm_cebo(50.0, "reactive"))
    masa_p = run_arm(pilot, dict(ARM_MASA, name="masa_reactive"))
    by_p = {(r["seed"], r["kind"]): r for r in masa_p}
    diffs_p = [r["sev"] - by_p[(r["seed"], r["kind"])]["sev"] for r in cebo_p]
    d_hat = float(np.mean(diffs_p))
    sigma = float(np.std(diffs_p, ddof=1))
    n_pairs = 400 if abs(d_hat) < 1e-6 else int(np.ceil((1.96 * sigma / (abs(d_hat) / 3)) ** 2))
    n_pairs = int(np.clip(n_pairs, 200, 400))
    if args.pairs:
        n_pairs = args.pairs
    pairs = pool_l[:n_pairs // 2] + pool_m[:n_pairs - n_pairs // 2]

    results = {"piloto": {"n": len(pilot), "delta_hat": d_hat, "sigma": sigma,
                          "n_pares": n_pairs}}
    all_recs = []
    grid = list(range(0, 24_000, 250))
    for drone in ("reactive", "run02"):
        # UN solo brazo MASA por oponente (no depende del hold); CEBO por cada hold.
        masa = run_arm(pairs, dict(ARM_MASA, drone=drone, name=f"masa_{drone}"))
        all_recs += masa
        by = {(r["seed"], r["kind"]): r for r in masa}
        for hold in (50.0, 5.0, -10.0):
            cebo = run_arm(pairs, _arm_cebo(hold, drone),
                           probe=("lure_rec" if hold == 50.0 else None))
            all_recs += cebo
            cell = {}
            for nlab, sel in [("todos", lambda r: True)] + \
                    [(f"n{k}", lambda r, k=k: sum(r["grupos_spawn"]) == k) for k in (3, 4, 5)]:
                dsel = [r["sev"] - by[(r["seed"], r["kind"])]["sev"]
                        for r in cebo if sel(r)]
                if dsel:
                    cell[nlab] = list(boot_ci(dsel)) + [len(dsel)]
            prov = {}
            for lab, rs in (("cebo", cebo), ("masa", masa)):
                ds = [d for r in rs for d in r["deaths"]]
                prov[lab] = {
                    "n_muertes": len(ds),
                    "knc": (float(np.mean([not d["killer_confirmado"] for d in ds]))
                            if ds else None),
                    "gotera": (float(np.mean([d["cruzo_gotera"] for d in ds])) if ds else None),
                    "octantes": (np.bincount([d["octante_vs_ancla"] for d in ds
                                              if d["octante_vs_ancla"] is not None],
                                             minlength=8).tolist() if ds else None),
                }
            valle = {}
            for lab, rs in (("cebo", cebo), ("masa", masa)):
                cum = np.zeros(len(grid))
                for r in rs:
                    ts = sorted(d["t"] for d in r["deaths"])
                    cum += [sum(1 for t in ts if t <= g) for g in grid]
                valle[lab] = (cum / max(len(rs), 1)).round(3).tolist()
            results[f"{drone}_h{int(hold)}"] = {"delta": cell, "procedencia": prov,
                                                "valle": valle, "grid": grid}
    _dump(outdir, {"fecha": datetime.now().isoformat(timespec="seconds"),
                   "n_pares": n_pairs, "holds": [50, 5, -10],
                   "oponentes": ["reactive", "run02"], "procs": args.procs},
          all_recs, results)
    print(json.dumps(results["piloto"], indent=1))
    print("e01: resultados en", outdir)
    return results


def exp_e02(args):
    """Latencias -> K. Analiza los episodios CEBO de e01 (results.json) y ajusta por ROC
    los umbrales de LURE_COMMIT con los canales grabados (lure_rows)."""
    outdir = pathlib.Path(OUT_BASE) / "e02"
    outdir.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path(OUT_BASE) / "e01" / "results.json"
    data = json.load(open(src))
    cebo = [r for r in data["episodes"] if r["option"] == "CEBO"]

    def dist(key_a, key_b=None):
        vals = []
        for r in cebo:
            a = r["clock"][key_a]
            b = 0 if key_b is None else r["clock"][key_b]
            if a is not None and b is not None:
                vals.append(a - b)
        if not vals:
            return None
        v = np.asarray(vals)
        return {"n": len(vals), "p25": float(np.percentile(v, 25)),
                "p50": float(np.percentile(v, 50)), "p75": float(np.percentile(v, 75)),
                "p90": float(np.percentile(v, 90))}

    lat = {
        "inicio_staged": dist("t_staged"),
        "staged_show": dist("t_show", "t_staged"),
        "show_confirm": dist("t_confirm_decoy", "t_show"),
        "inicio_flip": dist("t_primer_ancla"),
        "inicio_commit": dist("t_lure_commit"),
        "escolta_safe": dist("t_safe", "t_escolta"),
    }
    rel_kill = [e.get("latencia") for r in cebo for e in r["events"]
                if e["ev"] == "STRIKE_RESOLVED" and e.get("outcome") == "kill"]
    lat["release_muerte"] = (None if not rel_kill else
                             {"n": len(rel_kill),
                              "p50": float(np.percentile(rel_kill, 50)),
                              "p90": float(np.percentile(rel_kill, 90))})
    ventana = [r["clock"]["ventana_release"] for r in cebo
               if r["clock"]["ventana_release"] is not None]

    # ROC de LURE_COMMIT: etiqueta = "el asalto mató sin ser expulsado" (muerte post-release
    # de un lobo != señuelo); predictor = commit alcanzado bajo el umbral candidato.
    roc = []
    for cone in (40.0, 50.0, 60.0, 70.0, 80.0):
        for gate in (40.0, 50.0, 60.0, 70.0, 80.0):
            for mind in (2, 3):
                tp = fp = fn = tn = 0
                for r in cebo:
                    rows = r.get("lure_rows") or []
                    hit = any(sum(1 for x in row[1:6] if 0 <= x <= np.deg2rad(cone)) >= mind
                              and row[6] >= gate for row in rows)
                    label = any(e["ev"] == "STRIKE_RESOLVED" and e.get("outcome") == "kill"
                                for e in r["events"]) and \
                        any(d["t"] >= (r["clock"]["t_staged"] or 1 << 30) and
                            d["killer_nearest"] != 0 for d in r["deaths"])
                    tp += hit and label; fp += hit and not label
                    fn += (not hit) and label; tn += (not hit) and not label
                tpr = tp / max(tp + fn, 1)
                fpr = fp / max(fp + tn, 1)
                roc.append({"cone": cone, "gate": gate, "min_drones": mind,
                            "tpr": round(tpr, 3), "fpr": round(fpr, 3),
                            "youden": round(tpr - fpr, 3)})
    best = max(roc, key=lambda r: r["youden"])

    commit = lat["inicio_commit"]
    k_prop = None
    if commit is not None:
        k_prop = int(round(np.mean([commit["p75"], commit["p90"]]) / 5.0) * 5)
    ep_len = [r["steps"] for r in cebo if r["kind"] == "lobos"]
    sanity = (None if k_prop is None or not ep_len else
              float(np.mean([l / k_prop >= 5 for l in ep_len])))
    resumen = {"latencias": lat, "ventana_release_p50":
               (float(np.percentile(ventana, 50)) if ventana else None),
               "roc_mejor": best, "roc": roc, "K_propuesto": k_prop,
               "frac_eps_con_5_decisiones": sanity,
               "recomendacion": ("K por reloj" if (sanity or 0) >= 0.7 else
                                 "terminación-por-evento como diseño principal")}
    (outdir / "results.json").write_text(json.dumps(resumen, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in resumen.items() if k != "roc"}, indent=1,
                     ensure_ascii=False))
    return resumen


def exp_e03(args):
    outdir = pathlib.Path(OUT_BASE) / "e03"
    outdir.mkdir(parents=True, exist_ok=True)
    results, all_recs = {}, []
    n_pairs = args.pairs or 100
    for n in (2, 3, 4, 5):
        ov = {"wolves_min": n, "wolves_max": n}
        pairs = [("lobos", s) for s in range(n_pairs)]
        for drone in ("reactive", "run02"):
            arm_c = _arm_cebo(50.0, drone)
            arm_m = dict(ARM_MASA, drone=drone, name=f"masa_{drone}")
            jobs = []
            for kind, s in pairs:
                jobs.append({"seed": s, "kind": kind, "arm": arm_c, "overrides": ov})
                jobs.append({"seed": s, "kind": kind, "arm": arm_m, "overrides": ov})
            recs = run_jobs(jobs, args.procs)
            all_recs += recs
            cebo = {(r["seed"]): r for r in recs if r["option"] == "CEBO"}
            masa = {(r["seed"]): r for r in recs if r["option"] == "MASA"}
            cell = {}
            splits = [("todos", lambda r: True)]
            if n == 2:
                splits += [("con_ternero", lambda r: r.get("n_calves", 0) > 0),
                           ("sin_ternero", lambda r: r.get("n_calves", 0) == 0)]
            for lab, sel in splits:
                d = [cebo[s]["sev"] - masa[s]["sev"] for s in cebo
                     if s in masa and sel(cebo[s])]
                cell[lab] = (list(boot_ci(d)) + [len(d)]) if d else None
            results[f"n{n}_{drone}"] = cell
    _dump(outdir, {"fecha": datetime.now().isoformat(timespec="seconds"),
                   "n_pares": n_pairs, "ns": [2, 3, 4, 5], "procs": args.procs},
          all_recs, results)
    print(json.dumps(results, indent=1, ensure_ascii=False))
    return results


def exp_e04(args):
    outdir = pathlib.Path(OUT_BASE) / "e04"
    outdir.mkdir(parents=True, exist_ok=True)
    defenses = [("dummy", "dummy"), ("reactive", "reactive"),
                ("proporcional", "proporcional"), ("run02", "run02")]
    n_seeds = args.pairs or 100
    seeds3 = seeds_with("lobos", lambda w: w.n_wolves >= 3, n_seeds)
    results, all_recs = {}, []
    for wlab, wspec, kindseeds in (
            ("cebo_forzado", ("opt", ("CEBO", {"delta_deg": 180.0})),
             [("lobos", s) for s in seeds3]),
            ("scriptado_v34", None,
             [("lobos", s) for s in range(n_seeds)] + [("mixto", s) for s in range(n_seeds)])):
        for dlab, dspec in defenses:
            arm = {"name": f"{dlab}_vs_{wlab}", "wolf": wspec, "drone": dspec,
                   "option_name": ("CEBO" if wspec else None)}
            jobs = [{"seed": s, "kind": k, "arm": arm, "probe": "carrera"}
                    for k, s in kindseeds]
            recs = run_jobs(jobs, args.procs)
            all_recs += recs
            dosf = [r for r in recs if len(r["grupos_spawn"]) == 2]
            carrera = [(r["probe"].get("t_guard"), r["probe"].get("t_asalto"))
                       for r in recs if r["probe"].get("t_asalto") is not None]
            gana_guardia = [g is not None and g <= a for g, a in carrera]
            results[f"{dlab}_vs_{wlab}"] = {
                "sev": list(boot_ci([r["sev"] for r in recs])),
                "sev_2f": list(boot_ci([r["sev"] for r in dosf])) + [len(dosf)],
                "knc": list(knc_of(recs)),
                "gotera_por_ep": list(boot_ci([r["gotera_cruces"] for r in recs])),
                "carrera_n": len(carrera),
                "carrera_gana_guardia": (float(np.mean(gana_guardia)) if carrera else None),
            }
    _dump(outdir, {"fecha": datetime.now().isoformat(timespec="seconds"),
                   "defensas": [d[0] for d in defenses], "n_seeds": n_seeds,
                   "procs": args.procs}, all_recs, results)
    print(json.dumps(results, indent=1, ensure_ascii=False))
    return results


def exp_e05(args):
    outdir = pathlib.Path(OUT_BASE) / "e05"
    outdir.mkdir(parents=True, exist_ok=True)
    n_pairs = args.pairs or 50
    seeds3 = seeds_with("lobos", lambda w: w.n_wolves >= 3, n_pairs)
    results, all_recs = {}, []
    # Lado LOBO: CEBO<->MASA cada K vs CEBO fijo (control).
    control = {"name": "wolf_control", "wolf": ("opt", ("CEBO", {"delta_deg": 180.0})),
               "drone": "reactive", "option_name": "CEBO"}
    recs_ctrl = run_jobs([{"seed": s, "kind": "lobos", "arm": control, "probe": "puerta"}
                          for s in seeds3], args.procs)
    all_recs += recs_ctrl
    ctrl_by = {r["seed"]: r for r in recs_ctrl}
    for K in (250, 500, 1000, 2000):
        arm = {"name": f"wolf_switch_K{K}",
               "wolf": ("switch", {"sequence": [("CEBO", {"delta_deg": 180.0}), ("MASA", {})],
                                   "period": K}),
               "drone": "reactive", "option_name": "SWITCH"}
        recs = run_jobs([{"seed": s, "kind": "lobos", "arm": arm, "probe": "puerta"}
                         for s in seeds3], args.procs)
        all_recs += recs
        d = [r["sev"] - ctrl_by[r["seed"]]["sev"] for r in recs]
        results[f"lobo_K{K}"] = {"delta_sev": list(boot_ci(d)),
                                 "conmutaciones_medias": float(np.mean(
                                     [sum(1 for e in r["events"]
                                          if e["ev"] == "TIMEOUT_OPCION") for r in recs]))}
    # Lado DRON: partición conmutada cada K vs (4,0) fija, contra scriptado v3.4.
    dctrl = {"name": "dron_control", "wolf": None, "drone": ("particion", (4, 0))}
    recs_dc = run_jobs([{"seed": s, "kind": "lobos", "arm": dctrl, "probe": "puerta"}
                        for s in range(n_pairs)], args.procs)
    all_recs += recs_dc
    dctrl_by = {r["seed"]: r for r in recs_dc}
    for K in (250, 500, 1000, 2000):
        arm = {"name": f"dron_switch_K{K}", "wolf": None, "drone": ("switch_alloc", K)}
        recs = run_jobs([{"seed": s, "kind": "lobos", "arm": arm, "probe": "puerta"}
                         for s in range(n_pairs)], args.procs)
        all_recs += recs
        d = [r["sev"] - dctrl_by[r["seed"]]["sev"] for r in recs]
        results[f"dron_K{K}"] = {
            "delta_sev": list(boot_ci(d)),
            "puerta_ticks": list(boot_ci([r["probe"].get("puerta_ticks", 0) for r in recs])),
            "puerta_integral": list(boot_ci([r["probe"].get("puerta_integral", 0.0)
                                             for r in recs])),
        }
    results["dron_control_puerta_ticks"] = list(
        boot_ci([r["probe"].get("puerta_ticks", 0) for r in recs_dc]))
    _dump(outdir, {"fecha": datetime.now().isoformat(timespec="seconds"),
                   "Ks": [250, 500, 1000, 2000], "n_pares": n_pairs,
                   "procs": args.procs}, all_recs, results)
    print(json.dumps(results, indent=1, ensure_ascii=False))
    return results


# ====================================================================== #
def _dump(outdir: pathlib.Path, config: dict, episodes: list[dict], resumen: dict) -> None:
    (outdir / "config.json").write_text(json.dumps(config, indent=1, ensure_ascii=False))
    slim = []
    for r in episodes:
        r = dict(r)
        r.pop("lure_rows", None)
        slim.append(r)
    (outdir / "results.json").write_text(json.dumps(
        {"config": config, "resumen": resumen, "episodes": slim}, ensure_ascii=False))
    rows = [r.get("lure_rows") for r in episodes]
    if any(rows):
        np.savez_compressed(outdir / "lure_rows.npz",
                            **{f"ep{i}": np.asarray(r, dtype=np.float32)
                               for i, r in enumerate(rows) if r})


def main():
    ap = argparse.ArgumentParser(description="Experimentos Etapa 0 (jerárquico)")
    ap.add_argument("--exp", required=True,
                    choices=["e0a", "e01", "e02", "e03", "e04", "e05"])
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--pairs", type=int, default=None,
                    help="override del nº de pares/semillas (smokes)")
    ap.add_argument("--gifs", action="store_true", help="renderiza el lote de visionado")
    args = ap.parse_args()
    os.makedirs(OUT_BASE, exist_ok=True)
    {"e0a": exp_e0a, "e01": exp_e01, "e02": exp_e02,
     "e03": exp_e03, "e04": exp_e04, "e05": exp_e05}[args.exp](args)


if __name__ == "__main__":
    main()
