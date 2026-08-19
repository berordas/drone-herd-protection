"""hrl/behavior_checks.py — ASERCIONES AUTOMÁTICAS + PROCEDENCIA de cada muerte (Etapa 0).

Motivación (protocolo §2 de la misión E0 — dos bugs históricos que los tests NO detectaron y
solo se vieron en simulaciones: lobos colándose por el punto medio entre drones donde las
fuerzas se cancelan, y cebo disparado prematuramente con el asalto lejos): en TODOS los
episodios de TODOS los experimentos se evalúa
  A) ORDEN DEL CEBO (CRITICAL): en todo episodio con opción CEBO, tick(show del señuelo) >=
     tick(latch wolf_decoy_released). Violación => parar el experimento, renderizar TODOS los
     episodios violadores, informar (lo hace run_e0 leyendo `critical` del registro).
  B) PROCEDENCIA DE CADA MUERTE: matadores (flanqueadores del registro del mundo + el lobo
     MÁS CERCANO, el contador de cebo_diag/run08 para comparar apples-to-apples), confirmado
     o no ANTE LA BARRERA en la frontera anterior al paso de la muerte (KNC), cruce del
     corredor central (detector portado de /data/drones/diag/run02_comportamiento.py, aquí
     como funciones reutilizables), octante de aproximación respecto al ancla vigente y ticks
     desde el último ANCHOR_FLIP.
  C) RELOJ DE ESCOLTA: tick(latch ESCOLTA), tick(rebaño a salvo), y en episodios CEBO la
     ventana restante en el release.
  C') ESCOLTA PREMATURA (adenda E0 §5, episodios CEBO): si ESCOLTA salta ANTES del show,
     etiqueta (a) quién fue confirmado primero (señuelo / miembro del asalto, índice), (b) si
     el investigador iba hacia un DISTRACTOR (corzo) al cruzarse con el tránsito oscuro,
     (c) pinzamiento de borde (mín. distancia del asalto al borde de parcela < 25 m en los
     200 ticks previos). Evento ESCOLTA_PREMATURA en la línea temporal + campo `premature`.
  D) COHERENCIA DE CONTRATOS: pack_prey/pack_prey2 válidos tras las escrituras de la capa;
     ninguna opción comanda drones no comandables (check_command_mask, lo llama el arnés con
     los waypoints ANTES/DESPUÉS de coord.act()).

SOLO LECTURA sobre el mundo; sin RNG. El muestreo sigue la convención de cebo_diag: el estado
"en el tick de la muerte" es el de la FRONTERA anterior al paso en que cae la res.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from world import ACTIVE, INCOMING, STRANDED

from hrl.events import EventTracker, spawn_groups

PREMATURE_EDGE_WINDOW = 200   # ticks previos a ESCOLTA que mira el clasificador (adenda §5c)
PREMATURE_EDGE_M = 25.0       # m: "pinzamiento de borde" del asalto (mín. dist al borde < 25)
PREMATURE_SPAWN_SKIP = 200    # ticks iniciales excluidos del historial de borde (spawn en el perímetro)
GOTERA_GAP = 24.0   # m: pares de drones contiguos a hueco <= 1.2*spacing = pared-corredor real
                    # (MISMO umbral que run02_comportamiento.py -> métricas comparables)


def seg_cross(p1, p2, a, b) -> bool:
    """¿El segmento p1->p2 (trayecto del lobo en un paso) cruza el segmento a->b (pared entre
    dos drones contiguos)? Portado TAL CUAL de run02_comportamiento.py (detector de la gotera
    central, la métrica del usuario de v3.4/v3.5)."""
    d1, d2 = p2 - p1, b - a
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return False
    t = ((a[0] - p1[0]) * d2[1] - (a[1] - p1[1]) * d2[0]) / den
    s = ((a[0] - p1[0]) * d1[1] - (a[1] - p1[1]) * d1[0]) / den
    return 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0


class CorridorTracker:
    """Cruces del corredor central POR LOBO (port del bloque (3) de run02_comportamiento.py):
    tras cada paso, para cada lobo que se ACERCA al rebaño, ¿su trayecto cruzó el segmento
    entre dos drones LIBRES contiguos (orden por proyección en el eje principal, SVD)?
    `gotera` = pares a hueco <= GOTERA_GAP (pared-corredor real); `cruces` = cualquier par.
    Llamar `after_step(prev_wolves)` DESPUÉS de world.step con las posiciones previas."""

    def __init__(self, world):
        self.world = world
        n = world.n_wolves
        self.gotera = np.zeros(n, dtype=int)        # cruces por la gotera, por lobo
        self.cruces = np.zeros(n, dtype=int)        # cruces por cualquier par contiguo
        self.last_cross_tick = np.full(n, -1, dtype=int)

    def after_step(self, prev_wolves: np.ndarray) -> None:
        w = self.world
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        idx = np.where(free)[0]
        cows_ns = w.cows[w.cow_alive & ~w.cow_safe]
        if idx.size < 2 or cows_ns.shape[0] == 0 or w.n_wolves == 0:
            return
        pts = w.drones[idx]
        cc = pts - pts.mean(axis=0)
        _u, _s, vt = np.linalg.svd(cc)
        pts_o = pts[np.argsort(pts @ vt[0])]
        hc = cows_ns.mean(axis=0)
        for j in range(w.n_wolves):
            p1, p2 = prev_wolves[j], w.wolves[j]
            if not (np.linalg.norm(p2 - hc) < np.linalg.norm(p1 - hc)):
                continue                             # solo trayectos HACIA el rebaño
            for kk in range(idx.size - 1):
                if seg_cross(p1, p2, pts_o[kk], pts_o[kk + 1]):
                    self.cruces[j] += 1
                    self.last_cross_tick[j] = int(w.step_count)
                    if np.linalg.norm(pts_o[kk] - pts_o[kk + 1]) <= GOTERA_GAP:
                        self.gotera[j] += 1


def check_prey_contract(w) -> list[str]:
    """Validez de pack_prey/pack_prey2 (contrato compartido con el pin de la vaca): índice en
    rango para su `kind`, kind coherente, y -1 <=> kind None. Devuelve mensajes de violación."""
    out = []
    for name, idx, kind in (("pack_prey", w.pack_prey, w.pack_prey_kind),
                            ("pack_prey2", w.pack_prey2, w.pack_prey2_kind)):
        if idx < 0:
            if kind is not None:
                out.append(f"{name}={idx} con kind={kind!r} (debe ser None)")
            continue
        if kind == "adult":
            if not (0 <= idx < w.n_cows):
                out.append(f"{name}={idx} fuera de rango adult (n_cows={w.n_cows})")
        elif kind == "calf":
            if not (0 <= idx < w.n_calves):
                out.append(f"{name}={idx} fuera de rango calf (n_calves={w.n_calves})")
        else:
            out.append(f"{name}={idx} con kind inválido {kind!r}")
    return out


def check_command_mask(w, wp_before: np.ndarray, wp_cmd) -> list[str]:
    """¿El coordinador tocó el waypoint de un dron NO comandable? Comandables = ACTIVE y no
    investigando (la free-mask del mundo; v3.0: el anunciado de relevo SIGUE comandable).
    `wp_before` = w.drone_waypoint ANTES de coord.act(); `wp_cmd` = lo devuelto (None = nadie
    comanda, válido)."""
    if wp_cmd is None:
        return []
    free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
    bad = ~free & np.any(np.asarray(wp_cmd) != wp_before, axis=1)
    return [f"waypoint de dron NO comandable {i} modificado (estado={int(w.drone_state[i])})"
            for i in np.where(bad)[0]]


class EpisodeAudit:
    """Auditoría COMPLETA de un episodio: EventTracker + corredor + procedencia de muertes +
    reloj de escolta + aserciones. Uso (arnés run_e0):

        audit = EpisodeAudit(world, coord, wolf_controller=capa, meta={"seed": s, ...})
        loop:
            audit.on_boundary()
            wp_before = world.drone_waypoint.copy()
            wp = coord.act(world.get_observation())
            audit.check_command(wp_before, wp)          # contrato D (barato)
            world.step(wp); audit.after_step()
        rec = audit.finalize()   # dict con events/deaths/clock/violations/critical
    """

    def __init__(self, world, coordinator, wolf_controller=None, meta: dict | None = None,
                 decoy_indices=None, assault_indices=None, option_name: str | None = None):
        self.world = world
        self.tracker = EventTracker(world, coordinator, wolf_controller=wolf_controller,
                                    decoy_indices=decoy_indices, assault_indices=assault_indices)
        self.corridor = CorridorTracker(world)
        self.meta = dict(meta or {})
        self.option_name = option_name
        self.deaths: list[dict] = []
        self.violations: list[str] = []
        self._contract_seen: set[str] = set()
        # Instantáneas de la FRONTERA (convención cebo_diag: la muerte se atribuye con el
        # estado anterior al paso en que cae).
        self._snap_conf: np.ndarray | None = None
        self._snap_anchor: int | None = None
        self._snap_wolves: np.ndarray | None = None
        self._snap_cows: np.ndarray | None = None
        self._snap_calves: np.ndarray | None = None
        self._snap_herd_c: np.ndarray | None = None
        self._last_flip_tick: int | None = None
        self._captures_seen = 0
        # Clasificador de ESCOLTA PREMATURA (adenda E0 §5): historial por frontera de
        # (a) investigador y su contacto, (b) distancia mínima del asalto al borde de parcela
        # (ventana de PREMATURE_EDGE_WINDOW ticks), evaluado al saltar ESCOLTA antes del show.
        self._prev_conf_any = False
        self._inv_hist: deque = deque(maxlen=PREMATURE_EDGE_WINDOW)   # (tick, inv_idx, contacto_es_corzo)
        self._edge_hist: deque = deque(maxlen=PREMATURE_EDGE_WINDOW)  # dist mín asalto→borde
        self.premature: dict | None = None
        self._premature_pending: int | None = None
        self._escolta_seen = False
        # v3.6 (Commit L): métricas de RELEVO (solo lectura; flancos por frontera — cadencia 1 tick
        # en los arneses de E0/M1, que llaman on_boundary cada paso de física).
        self._relay_hold_since: dict[int, int] = {}
        self._relay_esperas: list[int] = []
        self._relay_por_fase = {"ESCOLTA": 0, "patrulla": 0}
        self._relay_stranded: set[int] = set()
        self._relay_prev_state: np.ndarray | None = None
        self._relay_prev_hold: np.ndarray | None = None

    # ------------------------------------------------------------------ #
    def on_boundary(self) -> None:
        w = self.world
        self.tracker.on_boundary()
        self._track_relays()
        for e in self.tracker.events:
            if e["ev"] == "ANCHOR_FLIP":
                self._last_flip_tick = e["t"]
        self._track_premature()
        conf = getattr(self.tracker.reactive, "_confirmed", None)
        self._snap_conf = None if conf is None else conf.copy()
        self._snap_anchor = getattr(self.tracker.reactive, "_anchor", None)
        self._snap_wolves = w.wolves.copy()
        self._snap_cows = w.cows.copy()
        self._snap_calves = w.calves.copy() if w.n_calves > 0 else None
        m = w.cow_alive & ~w.cow_safe
        self._snap_herd_c = w.cows[m].mean(axis=0) if m.any() else None
        for msg in check_prey_contract(w):
            if msg not in self._contract_seen:            # dedup: una vez por episodio
                self._contract_seen.add(msg)
                self.violations.append(f"contrato@t={int(w.step_count)}: {msg}")

    def _track_relays(self) -> None:
        """v3.6: flancos de relevo (anuncio drone_relief_hold OFF->ON; hand-off INCOMING->ACTIVE
        con el bajo liberado ese tick). Solo lectura."""
        w = self.world
        st, hold = w.drone_state, w.drone_relief_hold
        if self._relay_prev_state is not None:
            for i in np.where(hold & ~self._relay_prev_hold)[0]:
                self._relay_hold_since[int(i)] = int(w.step_count)
            if bool(((self._relay_prev_state == INCOMING) & (st == ACTIVE)).any()):
                for j in np.where(self._relay_prev_hold & ~hold)[0]:
                    if int(j) in self._relay_hold_since:
                        self._relay_esperas.append(int(w.step_count) - self._relay_hold_since.pop(int(j)))
                        self._relay_por_fase["ESCOLTA" if w.phase == "ESCOLTA" else "patrulla"] += 1
            self._relay_stranded |= set(int(x) for x in np.where(st == STRANDED)[0])
        self._relay_prev_state = st.copy()
        self._relay_prev_hold = hold.copy()

    def _track_premature(self) -> None:
        """Historial para el clasificador de ESCOLTA PREMATURA + la clasificación en el
        flanco de ESCOLTA (si el show aún no ha ocurrido). SOLO LECTURA."""
        w = self.world
        t = int(w.step_count)
        # (a)/(b): quién investiga y si su contacto es un distractor (el reflejo persigue el
        # CUERPO más cercano; se compara drone_contact con las posiciones de corzos vivos).
        inv = np.where(w.drone_investigating)[0]
        if inv.size:
            i = int(inv[0])
            c = w.drone_contact[i]
            es_corzo = False
            if w.n_corzos > 0 and np.all(np.isfinite(c)):
                keep = ~w.corzo_dismissed
                if keep.any():
                    es_corzo = bool(np.linalg.norm(w.corzos[keep] - c, axis=1).min() < 1e-6)
            self._inv_hist.append((t, i, es_corzo))
        # (c): pinzamiento de borde del ASALTO. Los lobos NACEN en el perímetro (spawn a
        # ≤ ~5 m del borde): los primeros PREMATURE_SPAWN_SKIP ticks se excluyen para que el
        # spawn no cuente como pinzamiento (medido: sin esto, borde_min=0.0 en el 100% de
        # las prematuras tempranas — artefacto del spawn, no una maniobra pinzada).
        asa = np.asarray(self.tracker.assault_indices(), dtype=int)
        if asa.size and t >= PREMATURE_SPAWN_SKIP:
            p = w.wolves[asa]
            d_edge = float(np.min(np.concatenate([p[:, 0], w.W - p[:, 0], p[:, 1], w.H - p[:, 1]])))
            self._edge_hist.append(d_edge)
        # Flanco de ESCOLTA antes del show => clasificar. La confirmación de EQUIPO de la
        # barrera (`_confirmed`) se actualiza DENTRO de coord.act(), es decir, UN tick
        # después de que el mundo latchee ESCOLTA en su step: la clasificación de "quién fue
        # confirmado primero" se DIFIERE a la primera frontera con algún confirmado (a más
        # tardar 2 fronteras después del flanco; si no lo hay, queda 'desconocido').
        if w.phase == "ESCOLTA" and not self._escolta_seen:
            self._escolta_seen = True
            t_show = next((e["t"] for e in self.tracker.events if e["ev"] == "SHOW_START"), None)
            staged = bool(w.wolf_decoy_released)
            if not staged and t_show is None and self.option_name and "CEBO" in self.option_name:
                self._premature_pending = t
        if self._premature_pending is not None and self.premature is None:
            conf = getattr(self.tracker.reactive, "_confirmed", None)
            has_conf = conf is not None and bool(conf.any())
            if has_conf or t - self._premature_pending >= 2:
                dec = np.asarray(self.tracker.decoy_indices(), dtype=int)
                first = None
                quien = "desconocido"
                if has_conf:
                    first = int(np.where(conf)[0][0])          # menor índice confirmado
                    quien = "señuelo" if (dec.size and first in set(dec.tolist())) else "asalto"
                elif dec.size == 0:
                    quien = "sin_roles"
                hacia_corzo = any(es for (_t, _i, es) in self._inv_hist)
                inv_last = self._inv_hist[-1][1] if self._inv_hist else None
                edge_min = float(min(self._edge_hist)) if self._edge_hist else None
                self.premature = {
                    "t": int(self._premature_pending), "primer_confirmado": first, "quien": quien,
                    "investigador": inv_last, "investigador_hacia_corzo": bool(hacia_corzo),
                    "asalto_borde_min_m": edge_min,
                    "pinzamiento_borde": (edge_min is not None and edge_min < PREMATURE_EDGE_M),
                }
                self.tracker.emit(int(self._premature_pending), "ESCOLTA_PREMATURA",
                                  **self.premature)

    def check_command(self, wp_before: np.ndarray, wp_cmd) -> None:
        for msg in check_command_mask(self.world, wp_before, wp_cmd):
            if msg not in self._contract_seen:
                self._contract_seen.add(msg)
                self.violations.append(f"comando@t={int(self.world.step_count)}: {msg}")

    def after_step(self) -> None:
        if self._snap_wolves is not None:
            self.corridor.after_step(self._snap_wolves)
        self._attribute_new_deaths()

    # ------------------------------------------------------------------ #
    def _attribute_new_deaths(self) -> None:
        """Procedencia de cada captura nueva, con las instantáneas de la frontera previa."""
        w = self.world
        caps = w.captures
        s1, _s2 = spawn_groups(w)
        while self._captures_seen < len(caps):
            c = caps[self._captures_seen]
            self._captures_seen += 1
            prey_pos = (self._snap_cows[c["prey_idx"]] if c["kind"] == "adult"
                        else self._snap_calves[c["prey_idx"]])
            d = np.linalg.norm(self._snap_wolves - prey_pos, axis=1)
            nearest = int(np.argmin(d))                   # el contador de cebo_diag (run08)
            conf = self._snap_conf
            flk = [int(x) for x in c["flankers"]]
            octant = None
            rel_deg = None
            if self._snap_anchor is not None and self._snap_herd_c is not None:
                va = self._snap_wolves[self._snap_anchor] - self._snap_herd_c
                vk = self._snap_wolves[nearest] - self._snap_herd_c
                if np.linalg.norm(va) > 1e-9 and np.linalg.norm(vk) > 1e-9:
                    rel = np.arctan2(vk[1], vk[0]) - np.arctan2(va[1], va[0])
                    rel_deg = float(np.degrees((rel + np.pi) % (2 * np.pi) - np.pi))
                    octant = int(round(rel_deg / 45.0)) % 8   # 0 = lado del ancla, 4 = opuesto
            self.deaths.append({
                "t": int(c["step"]), "kind": c["kind"], "prey": int(c["prey_idx"]),
                "flankers": flk,
                "flankers_confirmado": ([bool(conf[k]) for k in flk] if conf is not None
                                        else None),
                "killer_nearest": nearest,
                "killer_confirmado": (bool(conf[nearest]) if conf is not None else False),
                "grupo_killer": (1 if (s1.size and nearest < s1.size) else 2) if s1.size else None,
                "grupo_ancla": ((1 if (s1.size and self._snap_anchor < s1.size) else 2)
                                if (s1.size and self._snap_anchor is not None) else None),
                "cruzo_gotera": bool(self.corridor.gotera[nearest] > 0),
                "cruzo_corredor": bool(self.corridor.cruces[nearest] > 0),
                "octante_vs_ancla": octant, "rel_ancla_deg": rel_deg,
                "ticks_desde_flip": (int(c["step"]) - self._last_flip_tick
                                     if self._last_flip_tick is not None else None),
                "is_pack_prey": bool(c.get("is_pack_prey", False)),
                "is_pack_prey2": bool(c.get("is_pack_prey2", False)),
            })

    # ------------------------------------------------------------------ #
    def finalize(self) -> dict:
        w = self.world
        events = self.tracker.finalize()
        self._attribute_new_deaths()                      # capturas del último paso

        def first_tick(ev):
            return next((e["t"] for e in events if e["ev"] == ev), None)

        t_staged = first_tick("STAGED")
        t_show = first_tick("SHOW_START")
        t_escolta = first_tick("ESCOLTA_LATCH")
        t_safe = first_tick("HERD_SAFE")
        t_end = int(w.step_count)

        critical = []
        # A) ORDEN DEL CEBO (CRITICAL): show comandado sin latch, o antes del latch.
        if t_show is not None and (t_staged is None or t_show < t_staged):
            critical.append(f"ORDEN DEL CEBO: show@t={t_show} antes del latch "
                            f"(STAGED@{t_staged}) — CRITICAL")
        # B) completitud de la procedencia.
        if len(self.deaths) != int(w.n_depredadas):
            critical.append(f"PROCEDENCIA: {len(self.deaths)} muertes atribuidas != "
                            f"n_depredadas={int(w.n_depredadas)}")

        first_flip = next((e for e in events if e["ev"] == "ANCHOR_FLIP" and e["frm"] is None),
                          None)
        clock = {
            "t_staged": t_staged, "t_show": t_show, "t_escolta": t_escolta,
            "t_safe": t_safe, "t_end": t_end,
            "t_safe_desde_escolta": (t_safe - t_escolta
                                     if t_safe is not None and t_escolta is not None else None),
            "ventana_release": ((t_safe if t_safe is not None else t_end) - t_staged
                                if t_staged is not None else None),
            "t_confirm_decoy": first_tick("CONFIRM_DECOY"),
            "t_lure_commit": first_tick("LURE_COMMIT"),
            "t_primer_ancla": (first_flip["t"] if first_flip else None),
        }
        return {
            **self.meta,
            "option": self.option_name, "status": w.status,
            "sev": int(w.n_depredadas),
            "n_safe": int(w.cow_safe.sum() + w.calf_safe.sum()),
            "n_calves": int(w.n_calves),
            "steps": t_end, "grupos_spawn": [int(x) for x in w.wolf_group_sizes],
            "primer_ancla": (int(first_flip["to"]) if first_flip else None),
            "clock": clock, "events": events, "deaths": self.deaths,
            "premature": self.premature,
            "gotera_cruces": int(self.corridor.gotera.sum()),
            "corredor_cruces": int(self.corridor.cruces.sum()),
            "relevos": {"n": len(self._relay_esperas),
                        "escolta": self._relay_por_fase["ESCOLTA"],
                        "patrulla": self._relay_por_fase["patrulla"],
                        "espera_media": (float(np.mean(self._relay_esperas))
                                         if self._relay_esperas else None),
                        "espera_max": (int(max(self._relay_esperas))
                                       if self._relay_esperas else None),
                        "stranded": len(self._relay_stranded)},
            "violations": self.violations, "critical": critical,
        }
