"""hrl/manager_obs.py — OBSERVACIÓN del MANAGER de lobos (Etapa 1, semi-MDP sobre opciones).

Verdad-terreno LEGÍTIMA del bando lobo (los lobos son omniscientes en este mundo: posiciones de
drones, reses y compañeros; ver docs/INFORME_RECONOCIMIENTO.md §C). PROHIBIDO leer el estado
interno del coordinador (`_anchor`, `_confirmed`) en lógica de decisión: todo lo que aquí entra
es geometría observable. Layout FIJO (MANAGER_OBS_SIZE=35, float32), normalizado a ~[0,1]:

  [0:5]   MANADA: n/5 · nº clústeres/2 (clústeres de lobos separados >60° de rumbo respecto al
          centroide del rebaño) · separación angular entre los dos clústeres mayores /π (0 si 1)
          · tamaño del clúster MENOR /n (0 si 1) · dist. media de los lobos al rebaño /250.
  [5:11]  REBAÑO/RELOJ: reses en juego (vacas+terneros vivos no a salvo) /6 · terneros vivos /2 ·
          dist. centroide del rebaño → zona segura /250 · ESCOLTA latcheada (0/1) · muertes /6 ·
          reloj del episodio (step/max_episode_steps).
  [11:19] DEFENSA — distancia de PUERTA por OCTANTE (8, /250): para cada rumbo de octante
          (0°,45°,…,315° desde el centroide del rebaño) la distancia del ACTIVE más cercano al
          punto-puerta = borde del rebaño sobre ese rumbo + standoff (17.3 m). Sin ACTIVE: 1.0.
  [19:21] DEFENSA — fracción de ACTIVEs en el cono ±60° del rumbo del SEÑUELO (0 si no hay cebo
          vigente) · desplazamiento del centroide de ACTIVEs proyectado sobre el rumbo del señuelo
          en el último tramo /100 (rasgo de PROGRESO del cebo; 0 si no hay cebo o sin tramo).
  [21:25] CONTEXTO — opción vigente one-hot(4) [MASA, CEBO_keep, CEBO90, CEBO180] (todo 0 en la
          primera decisión).
  [25:31] CONTEXTO — último evento terminal one-hot(6) [INICIO, MUERTE, HERD_SAFE, K_MAX,
          ABORT_BAIT_FAILED, FIN_EPISODIO].
  [31:32] CONTEXTO — nº de decisión /8.
  [32:35] reservadas (0) — redondeo a 35 para no romper el layout si se añade un rasgo.

`build_manager_obs(world, ctx)`: `ctx` = dict con `option` (int|None), `last_event` (int),
`decision_idx` (int), `decoy_idx` (array|None), `active_c_prev` (array|None = centroide de
ACTIVEs al inicio del tramo anterior). Sin RNG, solo lectura."""

from __future__ import annotations

import numpy as np

from world import ACTIVE

MANAGER_OBS_SIZE = 35
N_OPTIONS = 4                      # MASA · CEBO_keep · CEBO(Δ90) · CEBO(Δ180)
N_EVENTS = 6                       # INICIO · MUERTE · HERD_SAFE · K_MAX · ABORT_BAIT_FAILED · FIN_EPISODIO
EV_INICIO, EV_MUERTE, EV_HERD_SAFE, EV_KMAX, EV_ABORT, EV_FIN = range(N_EVENTS)
CLUSTER_SEP_DEG = 60.0
BAIT_CONE_DEG = 60.0
GATE_STANDOFF_M = 17.32            # sqrt(DETER² − (spacing/2)²) = la misma fórmula v2.8 de la barrera
D_NORM = 250.0
PROGRESS_NORM = 100.0
OCTANT_ANGLES = np.deg2rad(np.arange(8) * 45.0)


def herd_points(w) -> np.ndarray:
    parts = []
    m = w.cow_alive & ~w.cow_safe
    if m.any():
        parts.append(w.cows[m])
    if w.n_calves > 0:
        mc = w.calf_alive & ~w.calf_safe
        if mc.any():
            parts.append(w.calves[mc])
    return np.vstack(parts) if parts else np.zeros((0, 2))


def wolf_clusters(w, herd_c: np.ndarray):
    """Clústeres de LOBOS por rumbo (hueco angular > CLUSTER_SEP_DEG respecto al centroide del
    rebaño). Devuelve lista de arrays de índices de lobo (orden angular), ángulos por lobo."""
    if w.n_wolves == 0:
        return [], np.zeros(0)
    rel = w.wolves - herd_c
    ang = np.arctan2(rel[:, 1], rel[:, 0])
    order = np.argsort(ang, kind="stable")
    a = ang[order]
    gaps = np.diff(np.concatenate([a, a[:1] + 2 * np.pi]))
    cuts = np.where(gaps > np.deg2rad(CLUSTER_SEP_DEG))[0]
    if cuts.size == 0:
        return [order], ang
    start = int(cuts[-1]) + 1
    seq = np.concatenate([order[start:], order[:start]])
    sizes = np.diff(np.concatenate([[0], cuts + 1]))
    out, pos = [], 0
    for s_ in sizes:
        out.append(seq[pos:pos + int(s_)]); pos += int(s_)
    return out, ang


def gate_distances(w, herd: np.ndarray, herd_c: np.ndarray) -> np.ndarray:
    """(8,) distancia del ACTIVE más cercano al punto-puerta de cada octante, /D_NORM (1.0 si
    no hay ACTIVE; clip a 1)."""
    act = w.drones[w.drone_state == ACTIVE]
    out = np.ones(8, dtype=np.float32)
    if act.shape[0] == 0 or herd.shape[0] == 0:
        return out
    for k, th in enumerate(OCTANT_ANGLES):
        u = np.array([np.cos(th), np.sin(th)])
        proj_front = float(((herd - herd_c) @ u).max())
        gate = herd_c + u * (proj_front + GATE_STANDOFF_M)
        out[k] = min(1.0, float(np.linalg.norm(act - gate, axis=1).min()) / D_NORM)
    return out


def bait_features(w, herd_c: np.ndarray, decoy_idx, active_c_prev):
    """(frac ACTIVEs en cono ±60° del rumbo del señuelo, progreso del centroide de ACTIVEs sobre
    ese rumbo /100). (0,0) si no hay cebo vigente."""
    if decoy_idx is None:
        return 0.0, 0.0
    dec = np.asarray(decoy_idx, dtype=int)
    if dec.size == 0 or w.n_wolves == 0:
        return 0.0, 0.0
    act = w.drones[w.drone_state == ACTIVE]
    if act.shape[0] == 0:
        return 0.0, 0.0
    v = w.wolves[dec].mean(axis=0) - herd_c
    nv = float(np.linalg.norm(v))
    if nv < 1e-9:
        return 0.0, 0.0
    u = v / nv
    ang_dec = np.arctan2(u[1], u[0])
    rel = act - herd_c
    ang = np.arctan2(rel[:, 1], rel[:, 0])
    diff = np.abs((ang - ang_dec + np.pi) % (2 * np.pi) - np.pi)
    frac = float((diff <= np.deg2rad(BAIT_CONE_DEG)).mean())
    prog = 0.0
    if active_c_prev is not None:
        prog = float(np.clip(((act.mean(axis=0) - np.asarray(active_c_prev)) @ u) / PROGRESS_NORM,
                             -1.0, 1.0))
    return frac, prog


def build_manager_obs(w, ctx: dict) -> np.ndarray:
    o = np.zeros(MANAGER_OBS_SIZE, dtype=np.float32)
    herd = herd_points(w)
    herd_c = herd.mean(axis=0) if herd.shape[0] else np.array([w.W / 2.0, w.H / 2.0])
    n = int(w.n_wolves)
    # MANADA
    o[0] = n / 5.0
    if n > 0:
        cl, ang = wolf_clusters(w, herd_c)
        o[1] = min(len(cl), 2) / 2.0
        if len(cl) >= 2:
            two = sorted(cl, key=len, reverse=True)[:2]
            c0 = np.arctan2(*(w.wolves[two[0]].mean(axis=0) - herd_c)[::-1])
            c1 = np.arctan2(*(w.wolves[two[1]].mean(axis=0) - herd_c)[::-1])
            sep = abs((c0 - c1 + np.pi) % (2 * np.pi) - np.pi)
            o[2] = sep / np.pi
            o[3] = min(len(c) for c in cl) / n
        o[4] = min(1.0, float(np.linalg.norm(w.wolves - herd_c, axis=1).mean()) / D_NORM)
    # REBAÑO / RELOJ
    o[5] = herd.shape[0] / 6.0
    o[6] = (int(w.calf_alive.sum()) / 2.0) if w.n_calves > 0 else 0.0
    o[7] = min(1.0, float(np.linalg.norm(herd_c - w.safe_zone[:2])) / D_NORM)
    o[8] = 1.0 if w.phase == "ESCOLTA" else 0.0
    o[9] = min(1.0, w.n_depredadas / 6.0)
    o[10] = min(1.0, w.step_count / max(float(w.max_episode_steps), 1.0))
    # DEFENSA
    o[11:19] = gate_distances(w, herd, herd_c)
    frac, prog = bait_features(w, herd_c, ctx.get("decoy_idx"), ctx.get("active_c_prev"))
    o[19], o[20] = frac, prog
    # CONTEXTO
    opt = ctx.get("option")
    if opt is not None and 0 <= int(opt) < N_OPTIONS:
        o[21 + int(opt)] = 1.0
    ev = int(ctx.get("last_event", EV_INICIO))
    if 0 <= ev < N_EVENTS:
        o[25 + ev] = 1.0
    o[31] = min(1.0, int(ctx.get("decision_idx", 0)) / 8.0)
    return o
