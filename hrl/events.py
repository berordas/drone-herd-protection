"""hrl/events.py — Detectores de EVENTOS de la Etapa 0 del jerárquico (HRL).

SOLO LECTURA sobre (World, coordinador de drones): ningún detector escribe estado del mundo
ni consume RNG (regla 4 de la misión E0). El muestreo va en la FRONTERA del paso de física —
el mismo instante en que los envs construyen su obs (lección SyncedReactiveCoordinator,
riesgo #8 del reconocimiento): el arnés llama a `on_boundary()` UNA vez por tick ANTES de
`world.step()` y a `finalize()` al terminal. Las muertes se leen del registro de capturas
del propio mundo (`world.captures`, con índices de flanqueadores y step exacto).

El estado interno de la BARRERA se lee SOLO para análisis (ancla `_anchor`, latch de equipo
`_confirmed`), exactamente como hacen los diagnósticos de /data (run08_ancla_diag,
cebo_diag) — el bando LOBO nunca recibe estos datos como observación.

Eventos (edge-triggered; deterministas — misma seed => misma línea temporal, hrl_check):
  STAGED          latch `wolf_decoy_released` False->True (el asalto quedó estacionado; lo
                  escribe decoy_timing/la capa — aquí solo se LEE el flanco).
  SHOW_START      el CEBO recibe la orden de MOSTRARSE. Lo emite la CAPA (WolfOptionLayer,
                  vía pop_events); con el scriptado puro se infiere = tick de STAGED (por
                  construcción el script deja de merodear el mismo tick del latch). La
                  aserción CRITICAL "orden del cebo" (behavior_checks) exige
                  tick(SHOW_START) >= tick(STAGED).
  CONFIRM_DECOY   primer tick con algún lobo del sector-cebo dentro del latch de confirmación
                  de equipo (`reactive._confirmed`).
  ANCHOR_FLIP     cambio del lobo ANCLA (`reactive._anchor`), incluido None->i (primer
                  ancla: `from` None — el dato de la métrica ancla-cebo).
  LURE_COMMIT     definición OBSERVACIONAL del "la defensa ha picado" (umbrales nombrados
                  abajo, marcados CALIBRAR-E0.2; se ajustarán por ROC contra «el asalto mató
                  sin ser expulsado»): [>= LURE_COMMIT_MIN_DRONES drones ACTIVE con rumbo
                  (visto desde el centroide del rebaño) a <= ±LURE_COMMIT_CONE_DEG del rumbo
                  del SEÑUELO] Y [dist del ACTIVE más cercano al PUNTO-PUERTA del rumbo de
                  asalto >= LURE_COMMIT_GATE_CLEAR_M]. Punto-puerta = borde del rebaño sobre
                  el rumbo de asalto + standoff de barrera (sqrt(DETER²−(s/2)²) ≈ 17.3, leído
                  de `reactive.barrier_standoff` — la MISMA fórmula v2.8/v3.2). Se emite el
                  flanco OFF->ON con ambos términos en data (y OFF con LURE_COMMIT_END).
  ESCOLTA_LATCH   fase -> "ESCOLTA" (latcheada por el mundo).
  HERD_SAFE       in_play == 0 (todas las reses resueltas: a salvo o muertas), con el
                  desglose n_safe/n_muertas en data (el reloj de escolta usa este tick).
  DEATH           una entrada por captura del mundo (step exacto, presa, flanqueadores);
                  la PROCEDENCIA completa la añade behavior_checks.EpisodeAudit.
  STRIKE_RESOLVED al finalize: primera muerte TRAS el release (outcome="kill", con la
                  latencia release->muerte) o terminal sin muerte post-release
                  (outcome="none") — la t(release->1ª muerte) de E0.2.
  OPTION_* / TIMEOUT_OPCION / SHOW_START los emite la capa de opciones por su cola
                  `pop_events()` (cada uno trae su tick); el tracker los integra tal cual.
"""

from __future__ import annotations

import numpy as np

from world import ACTIVE

# Umbrales del detector LURE_COMMIT — CALIBRAR-E0.2 (se ajustarán por ROC contra
# "el asalto mató sin ser expulsado"; hasta entonces, los valores del prompt de la misión).
LURE_COMMIT_CONE_DEG = 60.0     # ± grados alrededor del rumbo del señuelo (drones "mirando al cebo")
LURE_COMMIT_GATE_CLEAR_M = 60.0  # m: puerta del asalto "abierta" (ACTIVE más cercano al punto-puerta)
LURE_COMMIT_MIN_DRONES = 3      # nº mínimo de ACTIVE dentro del cono del señuelo


def reactive_of(coord):
    """La instancia ReactiveCoordinator-like con `_anchor`/`_confirmed`/`barrier_standoff`:
    el propio coordinador o su `.inner` (SyncedReactiveCoordinator, ResidualDroneCoordinator,
    AllocatorCoordinator). Duck-typing deliberado (mismo patrón que los diagnósticos)."""
    return coord.inner if hasattr(coord, "inner") else coord


def spawn_groups(world) -> tuple[np.ndarray, np.ndarray]:
    """Membresías POR SPAWN (v2.5): (cebo, asalto) = (grupo 1, grupo 2) si hay 2 subgrupos;
    con 1 grupo devuelve (vacío, vacío) — sin roles de spawn."""
    if len(world.wolf_group_sizes) != 2:
        z = np.zeros(0, dtype=int)
        return z, z
    n1 = int(world.wolf_group_sizes[0])
    return np.arange(0, n1), np.arange(n1, world.n_wolves)


class EventTracker:
    """Acumula la línea temporal de eventos de UN episodio. Uso (arnés run_e0):
        tracker = EventTracker(world, coordinator, wolf_controller=capa_o_None)
        loop:  tracker.on_boundary()  ->  coord.act()  ->  world.step()
        al terminal: tracker.finalize()
    `decoy_indices`/`assault_indices`: callables sin args -> índices de lobo por rol; con la
    capa se cablean a sus membresías (manager); por defecto, los grupos de SPAWN. SOLO lee."""

    def __init__(self, world, coordinator, wolf_controller=None,
                 decoy_indices=None, assault_indices=None):
        self.world = world
        self.reactive = reactive_of(coordinator)
        self.wolf_controller = wolf_controller
        s1, s2 = spawn_groups(world)
        self.decoy_indices = decoy_indices if decoy_indices is not None else (lambda: s1)
        self.assault_indices = assault_indices if assault_indices is not None else (lambda: s2)
        self.events: list[dict] = []
        self._prev_released = bool(world.wolf_decoy_released)
        self._prev_phase = world.phase
        self._prev_anchor: int | None = None
        self._prev_lure = False
        self._confirm_decoy_done = False
        self._herd_safe_done = False
        self._captures_seen = 0
        self._release_tick: int | None = None
        self._finalized = False

    # ------------------------------------------------------------------ #
    def emit(self, tick: int, ev: str, **data) -> None:
        self.events.append({"t": int(tick), "ev": ev, **data})

    def _drain_layer(self) -> None:
        """Integra los eventos de la capa de opciones (SHOW_START, OPTION_*, TIMEOUT_OPCION,
        ...): cada uno trae su tick propio."""
        wc = self.wolf_controller
        if wc is not None and hasattr(wc, "pop_events"):
            for e in wc.pop_events():
                self.events.append(dict(e))

    # ------------------------------------------------------------------ #
    def on_boundary(self) -> None:
        """UNA llamada por tick, en la FRONTERA (antes de world.step) — el instante de la
        obs de los envs. Todos los detectores comparan con el estado de la frontera previa."""
        w = self.world
        t = int(w.step_count)
        self._drain_layer()

        # STAGED (flanco del latch; el latch lo escriben decoy_timing / la capa).
        released = bool(w.wolf_decoy_released)
        if released and not self._prev_released:
            self.emit(t, "STAGED")
            self._release_tick = t
        self._prev_released = released

        # ESCOLTA_LATCH.
        if w.phase == "ESCOLTA" and self._prev_phase != "ESCOLTA":
            self.emit(t, "ESCOLTA_LATCH")
        self._prev_phase = w.phase

        # CONFIRM_DECOY (primer lobo del sector-cebo en el latch de equipo).
        conf = getattr(self.reactive, "_confirmed", None)
        if not self._confirm_decoy_done and conf is not None:
            dec = np.asarray(self.decoy_indices(), dtype=int)
            if dec.size and bool(conf[dec].any()):
                self.emit(t, "CONFIRM_DECOY",
                          wolf=int(dec[np.argmax(conf[dec])]))
                self._confirm_decoy_done = True

        # ANCHOR_FLIP (incluido None->i: primer ancla).
        anchor = getattr(self.reactive, "_anchor", None)
        if anchor != self._prev_anchor and anchor is not None:
            self.emit(t, "ANCHOR_FLIP", frm=self._prev_anchor, to=int(anchor))
        self._prev_anchor = anchor

        # LURE_COMMIT (flancos ON/OFF de la definición observacional).
        lure, data = self._lure_state()
        if lure and not self._prev_lure:
            self.emit(t, "LURE_COMMIT", **data)
        elif self._prev_lure and not lure:
            self.emit(t, "LURE_COMMIT_END")
        self._prev_lure = lure

        # DEATH: capturas nuevas desde la última frontera (el tick exacto va en la captura).
        self._drain_captures()

        # HERD_SAFE (todas las reses resueltas; el desglose distingue éxito de matanza).
        if not self._herd_safe_done:
            in_play = int((w.cow_alive & ~w.cow_safe).sum() + (w.calf_alive & ~w.calf_safe).sum())
            if in_play == 0:
                n_safe = int(w.cow_safe.sum() + w.calf_safe.sum())
                self.emit(t, "HERD_SAFE", n_safe=n_safe, n_muertas=int(w.n_depredadas))
                self._herd_safe_done = True

    def _drain_captures(self) -> None:
        caps = self.world.captures
        while self._captures_seen < len(caps):
            c = caps[self._captures_seen]
            self.emit(c["step"], "DEATH", kind=c["kind"], prey=int(c["prey_idx"]),
                      flankers=list(c["flankers"]))
            self._captures_seen += 1

    # ------------------------------------------------------------------ #
    def _lure_state(self) -> tuple[bool, dict]:
        """(¿LURE_COMMIT activo?, data). Observacional puro: posiciones de drones/lobos/reses.
        Rumbos vistos DESDE el centroide del rebaño; el punto-puerta usa el standoff derivado
        de la barrera (misma fórmula v2.8). Falso si falta cualquier pieza (sin ACTIVE, sin
        rebaño vivo, sin roles)."""
        w = self.world
        act = w.drones[w.drone_state == ACTIVE]
        dec = np.asarray(self.decoy_indices(), dtype=int)
        asa = np.asarray(self.assault_indices(), dtype=int)
        if act.shape[0] == 0 or dec.size == 0 or asa.size == 0:
            return False, {}
        parts = []
        m = w.cow_alive & ~w.cow_safe
        if m.any():
            parts.append(w.cows[m])
        if w.n_calves > 0:
            mc = w.calf_alive & ~w.calf_safe
            if mc.any():
                parts.append(w.calves[mc])
        if not parts:
            return False, {}
        herd = np.vstack(parts)
        herd_c = herd.mean(axis=0)

        # (a) drones "mirando al cebo": rumbo angular del dron ~ rumbo del señuelo.
        dec_c = w.wolves[dec].mean(axis=0)
        v_dec = dec_c - herd_c
        if float(np.linalg.norm(v_dec)) < 1e-9:
            return False, {}
        ang_dec = np.arctan2(v_dec[1], v_dec[0])
        v_dr = act - herd_c
        ang_dr = np.arctan2(v_dr[:, 1], v_dr[:, 0])
        diff = np.abs((ang_dr - ang_dec + np.pi) % (2 * np.pi) - np.pi)
        n_in_cone = int((diff <= np.deg2rad(LURE_COMMIT_CONE_DEG)).sum())

        # (b) puerta del asalto abierta: nadie cerca del punto-puerta de su rumbo.
        asa_c = w.wolves[asa].mean(axis=0)
        v_asa = asa_c - herd_c
        na = float(np.linalg.norm(v_asa))
        if na < 1e-9:
            return False, {}
        u = v_asa / na
        proj_front = float(((herd - herd_c) @ u).max())
        standoff = float(getattr(self.reactive, "barrier_standoff", 17.32))
        gate = herd_c + u * (proj_front + standoff)
        gate_clear = float(np.linalg.norm(act - gate, axis=1).min())

        on = (n_in_cone >= LURE_COMMIT_MIN_DRONES) and (gate_clear >= LURE_COMMIT_GATE_CLEAR_M)
        return on, {"drones_cono": n_in_cone, "puerta_libre_m": round(gate_clear, 1)}

    # ------------------------------------------------------------------ #
    def finalize(self) -> list[dict]:
        """Cierra la línea temporal en el terminal: drena capa y capturas pendientes, emite
        HERD_SAFE si se resolvió en el último paso y STRIKE_RESOLVED (E0.2: t(release->1ª
        muerte))."""
        if self._finalized:
            return self.events
        self._finalized = True
        w = self.world
        self.on_boundary()      # última frontera: drena capturas/flancos del paso final
        t_end = int(w.step_count)
        if self._release_tick is not None:
            post = [e for e in self.events
                    if e["ev"] == "DEATH" and e["t"] >= self._release_tick]
            if post:
                t0 = min(e["t"] for e in post)
                self.emit(t0, "STRIKE_RESOLVED", outcome="kill",
                          latencia=t0 - self._release_tick)
            else:
                self.emit(t_end, "STRIKE_RESOLVED", outcome="none",
                          latencia=t_end - self._release_tick)
        self.events.sort(key=lambda e: e["t"])
        return self.events


def format_timeline(events: list[dict], header: str = "") -> str:
    """Sidecar timeline.txt del lote de visionado: una línea por evento, con tick."""
    lines = [header] if header else []
    for e in events:
        data = " ".join(f"{k}={v}" for k, v in e.items() if k not in ("t", "ev"))
        lines.append(f"t={e['t']:>6d}  {e['ev']:<16s} {data}".rstrip())
    return "\n".join(lines) + "\n"
