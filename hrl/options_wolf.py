"""hrl/options_wolf.py — Capa de OPCIONES del bando LOBO (Etapa 0 del jerárquico).

`WolfOptionLayer` implementa el protocolo del cerebro enchufable
(`WolfController.decide(world) -> (v_deseada, coasting)`) y expone DOS opciones scripted
congeladas que un MANAGER de alto nivel elige en la frontera del env (cada `frame_skip=5`
pasos — la misma frontera en que muestrean los envs, lección SyncedReactiveCoordinator):

  MASA          delega BIT A BIT en la heurística scriptada de paquete único sobre
                `pack_prey` (`ScriptedWolfController._decide_single`): todo el paquete caza
                la presa común, SIN roles — la opción "no cebar". Al ARRANCAR la opción se
                escribe `pack_prey2 = -1` (contrato del pin: una vaca solo encara si es
                presa; sin sector 2 no hay 2ª presa) — la única escritura extra.
                [hrl_check verifica MASA ≡ ScriptedWolfController bit a bit en episodios de
                1 grupo de spawn, donde el script toma exactamente ese camino; con 2 grupos
                MASA difiere del script POR DISEÑO: es la decisión del manager de fusionar.]

  CEBO(Δ, hold) la máquina de dos sectores v3.3/v3.4 con MEMBRESÍAS DICTADAS (no por spawn):
                señuelo = lobo vivo de índice más bajo; asalto = resto. Rumbo señuelo =
                rumbo actual del paquete al centroide del rebaño (el lado que ya ocupa);
                rumbo asalto = señuelo + Δ. Reutiliza las FASES del script extraídas en el
                Commit A (merodeo `decoy_prowl` > decoy_hold_dist; anillos oscuros
                STAGE/CREEP/DEEP con `hold` parametrizable — default 50 => STAGE
                r_detect+50=150; latch staged->show; `group_hunted`; ala rota
                `decoy_broken_wing`; cola `pack_common_tail`). Presa del asalto: RÉPLICA de
                la regla del mundo (`world._freest_prey_for_sector2`, world.py:1391 —
                ternero-primero, máx. distancia al ACTIVE más cercano, quórum local,
                anti-convergencia), leída AL INICIAR la opción y re-evaluada solo al perder
                la presa (mismo contrato); escribe pack_prey/pack_prey2/wolf_decoy_released
                respetando los contratos (riesgos #3/#6 del reconocimiento, incluido el
                reset por retroceso de step_count).
                `membership="spawn"` (E0.A.ii): membresías = los grupos de SPAWN y timing
                por `decoy_timing` con defaults => camino BIT A BIT el del script (mide el
                impuesto de interfaz puro). Requiere 2 grupos reales; si no los hay cae a
                MASA y lo deja registrado (OPTION_FALLBACK).
                `membership="keep"` = CEBO_keep (adenda E0 §2, estrato G): membresías del
                manager (señuelo = índice vivo más bajo = el singleton del spawn en G;
                asalto = resto) pero rumbo del asalto = su rumbo ACTUAL (sin Δ) =>
                reposicionamiento ≈ 0 — el cebo como decisión pura cuando la geometría de
                dos frentes ya existe. Timing = escalera del manager (creep=min(25,hold)).

REGLA DE CAZA OPORTUNISTA (Commit K, Etapa 1 — decisión de diseño del dueño: "cambiar de presa
cuando la actual está protegida es caza REALISTA"; lo ilegítimo en RUN-M1 era el MECANISMO: el
re-apuntado lo disparaba el churn de re-arranques de opción, solo el manager tenía la capacidad y
con ese exploit no aprendió criterio). Desde K:
  - La presa del CAZADOR PERSISTE por defecto: MASA => `pack_prey` (todo el paquete); CEBO* =>
    `pack_prey2` (el asalto), que la capa RECUERDA (`_asa_prey`) y RESTAURA en cada arranque o
    re-arranque de opción si sigue cazable (el churn de opciones ya NO re-apunta: botón cerrado;
    solo el PRIMER arranque del episodio la lee fresca con la regla de siempre).
  - RE-TARGET permitido sii: la presa actual está PROTEGIDA (algún dron ACTIVE a <=
    THREAT_GUARD_DIST m de ella, sostenido >= GUARD_HOLD ticks, medido cada frontera) Y la
    alternativa de la regla de siempre (`freest_prey_for`: res en juego más libre, ternero-
    primero, quórum local) tiene su ACTIVE más cercano >= RETARGET_MARGIN m MÁS LEJOS que el de
    la actual. Cooldown por paquete RETARGET_COOLDOWN ticks (anti-metrónomo). La suelta por
    muerte/refugio sigue siendo la maquinaria de siempre del mundo/script (no pasa por aquí).
  - La regla vive en la CAPA y aplica a TODO el que juegue por ella (MASA, CEBO*, B_masa,
    B_spawn, B_oracle y el manager). world.py y wolf_controllers.py NO se tocan (física e
    historia congeladas). FALLBACK de quórum (mini-E0.3): CEBO con asalto < n_min_adult cae a
    MASA (OPTION_FALLBACK "CEBO/quorum") — espeja el cap del mundo (asalto siempre >= 2). CONSECUENCIA DOCUMENTADA: el "≡ script bit a bit" de MASA y de
    CEBO/spawn SOLO se mantiene mientras la regla no dispara (sin drones cerca de la presa);
    con drones cerca es un comportamiento NUEVO y deliberado (hrl_check [1]/[2] lo miden con
    drones lejos; [K] mide la regla). Eventos: RETARGET (causa="protegida", de/a, distancias)
    y RETARGET_BLOCKED (causa="cooldown", una vez por ventana). Constantes marcadas CALIBRAR
    si el visionado lo pide.

Decisiones de CAPA documentadas (no tocan wolf_controllers.py):
  - Escalera con hold != 50: CREEP nunca más laxo que el STAGE (creep = min(25, hold)); el
    DEEP (r_confirm+25=65) queda como está (siempre por debajo de los STAGE de E0.1:
    150/105/90). Es la variante de escenificación de E0.1, no un cambio del script.
  - Reposicionamiento del asalto (solo membership="manager"): mientras su rumbo real (visto
    desde el centroide) difiera del objetivo Δ en > ASSAULT_BEARING_TOL_DEG, el punto de
    presión de `assault_stage` es un punto LEJANO sobre el rumbo objetivo — el empuje del
    hold lo hace DESLIZAR por fuera del sobre oscuro hasta ese lado (la maniobra del
    script, con otro objetivo) MIENTRAS dura la fase de ALINEACIÓN (Commit S1, adjudicación
    VERIF-0: mejor-esfuerzo con salidas por tolerancia/sin-progreso/techo — el gate duro ±25°
    interbloqueaba el show en S: 9/20 episodios de B_oracle sin jugar, ambas patrullas).
  - Latch `wolf_decoy_released` MONÓTONO por episodio (contrato del World): una re-entrada
    en CEBO tras el show NO lo resetea (el cebo re-entra ya "mostrado"); E0.5 mide ese
    coste de conmutación.

RNG: la capa NO consume ningún stream del mundo (regla 4) — todo es lectura + escrituras de
contrato deterministas. Eventos propios (SHOW_START, OPTION_START, OPTION_FALLBACK,
TIMEOUT_OPCION del manager) salen por `pop_events()` con tick de FRONTERA (los emitidos
dentro de decide llevan step_count+1: el paso en que surten efecto — comparable con los
flancos que el EventTracker detecta en la frontera)."""

from __future__ import annotations

import numpy as np

from world import ACTIVE
from wolf_controllers import (ASSAULT_DARK_HOLD, ScriptedWolfController, WolfController,
                              assault_stage, assault_staged, decoy_broken_wing, decoy_prowl,
                              decoy_timing, group_hunted, manage_pack_preys,
                              pack_common_tail, sector_desired)

ASSAULT_BEARING_TOL_DEG = 25.0   # ± grados: "rumbo de asalto alcanzado" (gate del show en
                                 # membership=manager; afinable, se revisará con E0.2)
REPOSITION_EXTRA_M = 60.0        # m sobre el anillo STAGE: radio del punto de presión del
                                 # reposicionamiento (solo fija la DIRECCIÓN de la carga; la
                                 # profundidad la gobierna el hold, como en el script)

# --- Regla de caza oportunista (Commit K; decisión de diseño del dueño: caza oportunista
# realista). CALIBRAR si el visionado lo pide. ---
THREAT_GUARD_DIST = 25.0         # m: presa "PROTEGIDA" = algún dron ACTIVE a <= esta distancia de ella
GUARD_HOLD = 50                  # ticks: protección SOSTENIDA (medida cada frontera, 5 ticks) antes de
                                 # poder re-apuntar
RETARGET_MARGIN = 30.0           # m: la alternativa debe tener su ACTIVE más cercano >= este margen MÁS
                                 # LEJOS que el de la presa actual
RETARGET_COOLDOWN = 250          # ticks entre dos re-targets del MISMO paquete (anti-metrónomo)

# --- Fase de ALINEACIÓN del asalto (Commit S1; adjudicación VERIF-0 del dueño: el gate de rumbo
# pasa de BLOQUEO a MEJOR-ESFUERZO). VERIF-0 midió el gate duro en INTERBLOQUEO: B_oracle en S
# solo 8/20 shows, 9/20 episodios ESTACIONADOS sin show >= 400 ticks (máx 23.570 = el episodio
# entero, sev 0, 100% de los ticks con bearing_ok=False), con AMBAS patrullas (estática 9/9 y
# órbita v3.5 9/9) — el mismo modo de fallo que el script eliminó en v3.3 (docstring de
# assault_staged), reintroducido por la capa al materializar Δ. Desde S1: el tránsito sigue
# dirigiéndose a θ_asa (Δ conserva su significado de rumbo PRETENDIDO), pero la fase de
# alineación TERMINA por CUALQUIERA de
#   (a) error <= ASSAULT_BEARING_TOL_DEG (la tolerancia pasa de requisito a PREFERENCIA),
#   (b) SIN PROGRESO angular (mejora < ALIGN_NO_PROGRESS_DEG en ALIGN_NO_PROGRESS_TICKS ticks),
#   (c) techo T_ALIGN_MAX ticks desde el arranque de la opción;
# al terminar mandan las condiciones v3.3 del guion (staged por PROXIMIDAD => show), como en el
# camino de B_spawn (sano en VERIF-0: 9/10 shows, espera máx 1 tick). El error angular CONSEGUIDO
# se registra en ALIGN_END y en SHOW_START (las celdas S pasan a ser "Δ pretendido" con
# distribución de Δ conseguido). Constantes CALIBRAR si el visionado lo pide. ---
ALIGN_NO_PROGRESS_DEG = 2.0      # °: mejora mínima del error para contar como PROGRESO
ALIGN_NO_PROGRESS_TICKS = 300    # ticks sin progreso => fin de la fase de alineación (causa b)
ALIGN_T_MAX = 2500               # ticks: techo absoluto de la fase de alineación (causa c)

SHOW_STALL_TICKS = 400           # Q-bis (plan M1'''' del dueño; DEGRADADO a TRIPWIRE tras S1): asalto
                                 # STAGED este nº de ticks ACUMULADOS sin show => show FORZADO + evento
                                 # STALL. Cierre de GUION, no de decisión (la opción ejecuta el cebo
                                 # entero; decidir es del manager, ejecutar es de la opción). Tras S1
                                 # debe disparar ~0: n_stalls es métrica de SALUD y su disparo en eval
                                 # = DECISIÓN HUMANA PENDIENTE (pre-registrado en PREREGISTRO_v3).


def freest_prey_for(w, sel: np.ndarray) -> tuple[str | None, int]:
    """RÉPLICA CONDUCTA-FIEL de `World._freest_prey_for_sector2` (world.py:1391, mundo
    CONGELADO — no se puede parametrizar allí) con la membresía `sel` del MANAGER en lugar
    del sector de spawn: la res CAZABLE MÁS LIBRE (máx. distancia al dron ACTIVE más
    cercano), ternero-primero, quórum local (adulta solo si sel >= n_min_adult),
    anti-convergencia (excluye la presa del sector 1 si hay alternativa del mismo tipo);
    sin ACTIVE cae a la más cercana al centroide de `sel`. SOLO LECTURA."""
    if sel.size == 0:
        return (None, -1)
    act = w.drones[w.drone_state == ACTIVE]
    cazable_calf = w.calf_alive & ~w.calf_safe
    if cazable_calf.any():
        cand = cazable_calf.copy()
        if w.pack_prey_kind == "calf" and w.pack_prey >= 0 and cand.sum() > 1:
            cand[w.pack_prey] = False
        if act.shape[0] > 0:
            d = np.linalg.norm(w.calves[:, None, :] - act[None, :, :], axis=2).min(axis=1)
            d[~cand] = -np.inf
            return ("calf", int(np.argmax(d)))
        d = np.linalg.norm(w.calves - w.wolves[sel].mean(axis=0), axis=1)
        d[~cand] = np.inf
        return ("calf", int(np.argmin(d)))
    if sel.size >= w.n_min_adult:
        cazable = (w.cow_alive & ~w.cow_safe) & ~w._in_forbidden(w.cows)
        if cazable.any():
            cand = cazable.copy()
            if w.pack_prey_kind == "adult" and w.pack_prey >= 0 and cand.sum() > 1:
                cand[w.pack_prey] = False
            if act.shape[0] > 0:
                d = np.linalg.norm(w.cows[:, None, :] - act[None, :, :], axis=2).min(axis=1)
                d[~cand] = -np.inf
                return ("adult", int(np.argmax(d)))
            d = np.linalg.norm(w.cows - w.wolves[sel].mean(axis=0), axis=1)
            d[~cand] = np.inf
            return ("adult", int(np.argmin(d)))
    return (None, -1)


class WolfOptionLayer(WolfController):
    """Capa de opciones del lobo. `option` = opción FIJA ("MASA", {}) | ("CEBO", {...}) o
    `manager` con `decide(world, layer) -> (nombre, params) | None`, consultado cada
    `frame_skip` fronteras (None = mantener). Requiere `refresh(world)` UNA vez por paso de
    física EN LA FRONTERA (SyncedReactiveCoordinator ya lo hace). Params de CEBO:
    `delta_deg` (default 180), `hold` (offset sobre r_detect, default ASSAULT_DARK_HOLD=50),
    `membership` ("manager" default | "spawn" | "keep")."""

    def __init__(self, option: tuple[str, dict] | None = None, manager=None,
                 frame_skip: int = 5):
        if (option is None) == (manager is None):
            raise ValueError("WolfOptionLayer: pasa exactamente uno de option= o manager=")
        self.fixed_option = option
        self.manager = manager
        self.frame_skip = int(frame_skip)
        self.script = ScriptedWolfController()     # EL script, vivo (para MASA y utilidades)
        self._events: list[dict] = []
        self._last_step = -1
        self._countdown = 0
        self._opt_name: str | None = None
        self._opt_params: dict = {}
        self._opt_requested: tuple[str, dict] | None = None   # lo PEDIDO (≠ vigente si hubo fallback)
        self._mode = "manager"
        self._hold = float(ASSAULT_DARK_HOLD)
        self._delta = np.pi
        self._theta_asa: float | None = None
        self._s1 = np.zeros(0, dtype=int)
        self._s2 = np.zeros(0, dtype=int)
        # Fase de alineación (Commit S1): solo los brazos CEBO con rumbo pretendido (θ_asa) la
        # tienen; _align_done latchea POR ARRANQUE de opción (mejor-esfuerzo, no bloqueo).
        self._align_done = True
        self._align_best: float | None = None
        self._align_mark = 0
        self._align_t0 = 0
        # Regla de caza (Commit K): memoria de la presa del asalto + estado de la regla.
        self._asa_prey: tuple[str, int] | None = None   # (kind, idx) del asalto, PERSISTE entre opciones
        self._guard_prey: tuple[str, int] | None = None # presa cuya protección se está midiendo
        self._guard_since: int | None = None            # tick de la 1ª frontera protegida consecutiva
        self._last_retarget: int | None = None          # tick del último re-target por la regla
        self._blocked_logged = False                    # RETARGET_BLOCKED emitido en esta ventana
        self.n_retargets = 0                            # contadores del episodio (K-bis los lee)
        self.n_retarget_blocked = 0
        self.n_option_starts = 0
        # MÉTRICA DE CENSURA (adjudicación VERIF-0 del dueño): hitos de la JUGADA por episodio
        # (sev 0 sin jugar != sev 0 jugando y fallando). t_staged = 1er tick con el asalto
        # ESTACIONADO pre-show · t_show = latch del show · t_suelta (RELEASE) = 1er tick
        # post-show con el asalto SUELTO de los anillos oscuros (assault_hold None: ESCOLTA
        # latcheada o group_hunted — va a por su presa) · t_strike = 1er tick post-show con el
        # asalto A TIRO (flag attacking de sector_desired: flanco y <= r_face_safe). Jugada
        # COMPLETA := show + suelta (el strike es DESENLACE — la defensa puede negarlo
        # legítimamente; la censura mide el MECANISMO).
        self.t_staged: int | None = None
        self.t_show: int | None = None
        self.t_suelta: int | None = None
        self.t_strike: int | None = None
        self._staged_noshow = 0                          # Q-bis: ticks staged acumulados sin show
        self.n_stalls = 0                                # Q-bis: disparos del tripwire (salud)

    # ------------------------------------------------------------------ #
    # Eventos propios (los integra hrl/events.EventTracker vía pop_events).
    def push_event(self, ev: str, tick: int, **data) -> None:
        self._events.append({"t": int(tick), "ev": ev, **data})

    def pop_events(self) -> list[dict]:
        out, self._events = self._events, []
        return out

    # Membresías vigentes (para EventTracker/diagnósticos).
    def decoy_indices(self) -> np.ndarray:
        return self._s1

    def assault_indices(self) -> np.ndarray:
        return self._s2

    @property
    def option(self) -> tuple[str | None, dict]:
        return self._opt_name, dict(self._opt_params)

    # ------------------------------------------------------------------ #
    def refresh(self, world) -> None:
        """UNA llamada por paso de física, EN LA FRONTERA (antes de world.step). Detecta el
        episodio nuevo (retroceso de step_count — riesgo #6), y consulta al manager cada
        frame_skip fronteras (la frontera de los envs)."""
        step = int(world.step_count)
        if step < self._last_step or self._opt_name is None:
            self._countdown = 0                          # episodio nuevo: decisión inmediata
            self._opt_name = None
            self._opt_requested = None
            self._asa_prey = None                        # la memoria de presa es POR EPISODIO
            self._guard_prey = None
            self._guard_since = None
            self._last_retarget = None
            self._blocked_logged = False
            self.n_retargets = self.n_retarget_blocked = self.n_option_starts = 0
            self.t_staged = self.t_show = self.t_suelta = self.t_strike = None   # censura
            self._staged_noshow = 0
            self.n_stalls = 0
        self._last_step = step
        if self._countdown <= 0:
            self._countdown = self.frame_skip
            want = (self.fixed_option if self.manager is None
                    else self.manager.decide(world, self))
            if want is not None:
                name, params = want[0], dict(want[1] or {})
                # Se compara contra lo SOLICITADO (no lo vigente): si CEBO/spawn cayó a MASA
                # por fallback, re-pedir lo mismo NO re-arranca la opción cada frontera.
                if (name, params) != self._opt_requested:
                    self._start_option(world, name, params)
            # Regla de caza oportunista (Commit K): cada frontera de env (frame_skip ticks).
            self._hunt_rule(world)
            if self._opt_name == "CEBO" and world.pack_prey2 >= 0:
                self._asa_prey = (world.pack_prey2_kind, int(world.pack_prey2))   # memoria del asalto
        self._countdown -= 1

    # ------------------------------------------------------------------ #
    @staticmethod
    def _cazable(w, kind: str | None, idx: int, n_hunters: int) -> bool:
        """¿Sigue siendo presa legal para `n_hunters` lobos? (viva, no refugiada; adulta solo con
        quórum y fuera de zona prohibida) — el mismo criterio de cazable de freest_prey_for."""
        if idx < 0 or kind is None:
            return False
        if kind == "calf":
            return bool(w.calf_alive[idx] and not w.calf_safe[idx])
        return bool(n_hunters >= w.n_min_adult and w.cow_alive[idx] and not w.cow_safe[idx]
                    and not w._in_forbidden(w.cows[idx][None, :])[0])

    @staticmethod
    def _d_guard(w, kind: str | None, idx: int, act: np.ndarray) -> float:
        """Distancia de la presa (kind, idx) al dron ACTIVE más cercano (inf si no hay ACTIVE)."""
        if act.shape[0] == 0:
            return float("inf")
        p = w._prey_pos_of(idx, kind)
        return float(np.linalg.norm(act - p[None, :], axis=1).min())

    def _hunter(self, w) -> tuple[np.ndarray, str, str | None, int]:
        """Quién caza y a qué presa gobierna la regla: MASA => todo el paquete sobre pack_prey;
        CEBO* => el asalto (s2) sobre pack_prey2."""
        if self._opt_name == "MASA":
            return np.arange(w.n_wolves), "paquete", w.pack_prey_kind, int(w.pack_prey)
        return self._s2, "asalto", w.pack_prey2_kind, int(w.pack_prey2)

    def _hunt_rule(self, w) -> None:
        """REGLA DE CAZA OPORTUNISTA (Commit K). Evaluada en la frontera: si la presa del cazador
        está PROTEGIDA de forma sostenida y la regla de siempre ofrece una alternativa
        RETARGET_MARGIN m más libre, re-fija (una vez; cooldown por paquete). SOLO LECTURA salvo la
        escritura de contrato pack_prey/pack_prey2 (el mismo patrón que manage_pack_preys)."""
        if self._opt_name is None:
            return
        sel, who, cur_kind, cur_idx = self._hunter(w)
        step = int(w.step_count)
        if cur_idx < 0 or sel.size == 0:
            self._guard_prey, self._guard_since = None, None
            return
        if self._guard_prey != (cur_kind, cur_idx):     # presa nueva (muerte/refugio/opción): reloj a 0
            self._guard_prey, self._guard_since = (cur_kind, cur_idx), None
            self._blocked_logged = False
        act = w.drones[w.drone_state == ACTIVE]
        d_cur = self._d_guard(w, cur_kind, cur_idx, act)
        if d_cur > THREAT_GUARD_DIST:
            self._guard_since = None                     # no protegida: el reloj se reinicia
            self._blocked_logged = False
            return
        if self._guard_since is None:
            self._guard_since = step
        if step - self._guard_since < GUARD_HOLD:
            return
        kind, idx = freest_prey_for(w, sel)              # la regla de siempre (ternero-primero, quórum)
        if idx < 0 or (kind, idx) == (cur_kind, cur_idx):
            return
        d_cand = self._d_guard(w, kind, idx, act)
        if d_cand < d_cur + RETARGET_MARGIN:
            return
        if self._last_retarget is not None and step - self._last_retarget < RETARGET_COOLDOWN:
            if not self._blocked_logged:
                self.push_event("RETARGET_BLOCKED", tick=step, causa="cooldown", quien=who,
                                de=[cur_kind, cur_idx], a=[kind, idx],
                                restante=int(RETARGET_COOLDOWN - (step - self._last_retarget)))
                self._blocked_logged = True
                self.n_retarget_blocked += 1
            return
        guard_ticks = int(step - self._guard_since)
        if who == "paquete":
            w.pack_prey, w.pack_prey_kind = idx, kind
        else:
            w.pack_prey2, w.pack_prey2_kind = idx, kind
            self._asa_prey = (kind, idx)
        w._ever_committed = True
        self._last_retarget = step
        self._guard_prey, self._guard_since = (kind, idx), None
        self._blocked_logged = False
        self.n_retargets += 1
        self.push_event("RETARGET", tick=step, causa="protegida", quien=who, option=self._opt_name,
                        de=[cur_kind, cur_idx], a=[kind, idx], d_cur=round(d_cur, 2),
                        d_cand=round(d_cand, 2), guard_ticks=guard_ticks)

    def _start_option(self, w, name: str, params: dict) -> None:
        if name not in ("MASA", "CEBO"):
            raise ValueError(f"opción desconocida: {name!r} (usa 'MASA' | 'CEBO')")
        self._opt_requested = (name, dict(params))       # lo pedido, ANTES de cualquier fallback
        if name == "CEBO" and params.get("membership", "manager") == "spawn" \
                and len(w.wolf_group_sizes) != 2:
            # E0.A.ii pide spawn real de 2 grupos; sin él no hay roles de spawn que imitar.
            self.push_event("OPTION_FALLBACK", tick=int(w.step_count),
                            de="CEBO/spawn", a="MASA")
            name, params = "MASA", {}
        if name == "CEBO":
            # FALLBACK de quórum (mini-E0.3, plan M1''): si el ASALTO quedaría con < n_min_adult
            # lobos, el cebo no tiene brazo que golpee (espeja el cap del mundo: wolf_decoy_size se
            # capa a n-2 para que el asalto conserve quórum >= 2) -> cae a MASA y queda registrado.
            memb = params.get("membership", "manager")
            n_asalto = (int(w.wolf_group_sizes[1]) if memb == "spawn" and len(w.wolf_group_sizes) == 2
                        else w.n_wolves - 1)
            if n_asalto < w.n_min_adult:
                self.push_event("OPTION_FALLBACK", tick=int(w.step_count),
                                de=f"CEBO/quorum(n={w.n_wolves})", a="MASA")
                name, params = "MASA", {}
        self._opt_name, self._opt_params = name, dict(params)
        self._align_done = True                          # (Commit S1) default: sin fase de alineación
        self._staged_noshow = 0                          # (Q-bis) el reloj del tripwire es POR JUGADA
        self.n_option_starts += 1
        self.push_event("OPTION_START", tick=int(w.step_count), option=name, **params)
        if name == "MASA":
            self._s1 = np.zeros(0, dtype=int)
            self._s2 = np.zeros(0, dtype=int)
            if w.pack_prey2 >= 0:                        # fusionar el paquete: sin 2ª presa
                w.pack_prey2 = -1
                w.pack_prey2_kind = None
            return
        # CEBO(Δ, hold): membresías + rumbos + presa del asalto, leídos AL INICIAR la opción.
        self._mode = params.get("membership", "manager")
        self._hold = float(params.get("hold", ASSAULT_DARK_HOLD))
        self._delta = np.deg2rad(float(params.get("delta_deg", 180.0)))
        if self._mode == "spawn":
            n1 = int(w.wolf_group_sizes[0])
            self._s1 = np.arange(0, n1)
            self._s2 = np.arange(n1, w.n_wolves)
            self._theta_asa = None                       # sin reposicionamiento: rumbo = spawn
        else:
            self._s1 = np.array([0], dtype=int) if w.n_wolves > 0 else np.zeros(0, dtype=int)
            self._s2 = np.arange(1, w.n_wolves)
            herd_c = self._herd_c(w)
            if self._mode == "keep":
                # CEBO_keep (adenda E0 §2): rumbo del asalto = rumbo ACTUAL del centroide del
                # resto (NO señuelo+Δ) -> reposicionamiento ≈ 0: mide el cebo como DECISIÓN
                # pura cuando la geometría de dos frentes ya existe (estrato G). Sin objetivo
                # de rumbo no hay gate de rumbo (_bearing_ok es True) ni punto de presión.
                self._theta_asa = None
            else:
                v = w.wolves.mean(axis=0) - herd_c       # rumbo actual del paquete (lado que ocupa)
                theta_dec = float(np.arctan2(v[1], v[0])) if np.linalg.norm(v) > 1e-9 else 0.0
                self._theta_asa = theta_dec + self._delta
                # Fase de alineación (Commit S1): se RE-ABRE en cada arranque con rumbo pretendido
                # (un re-arranque re-fija θ_asa => el reloj de mejor-esfuerzo parte de 0).
                self._align_done = False
                self._align_best = None
                self._align_mark = self._align_t0 = int(w.step_count)
            # Presa del asalto (Commit K): PERSISTE — si la capa recuerda una presa del asalto
            # de este episodio y sigue cazable (y no es la presa del señuelo: anti-convergencia),
            # se RESTAURA; solo el PRIMER arranque (o una presa perdida) la lee fresca con la
            # regla de siempre y la MEMBRESÍA del manager (sobrescribe la del spawn si el mundo
            # fijó pack_prey2 en t=0 con sus sectores: aquí mandan las membresías).
            prev = self._asa_prey
            if prev is not None and self._cazable(w, prev[0], prev[1], self._s2.size) \
                    and prev != (w.pack_prey_kind, int(w.pack_prey)):
                kind, idx = prev
            else:
                kind, idx = freest_prey_for(w, self._s2)
            w.pack_prey2, w.pack_prey2_kind = (idx, kind) if idx >= 0 else (-1, None)
            if idx >= 0:
                w._ever_committed = True
                self._asa_prey = (kind, idx)

    # ------------------------------------------------------------------ #
    def decide(self, world) -> tuple[np.ndarray, bool]:
        if self._opt_name is None:
            raise RuntimeError("WolfOptionLayer sin refresh(): la opción se decide en la "
                               "FRONTERA (usa SyncedReactiveCoordinator o llama a refresh "
                               "antes de cada world.step)")
        if self._opt_name == "MASA":
            return self.script._decide_single(world)
        return self._decide_cebo(world)

    # ------------------------------------------------------------------ #
    def _herd_c(self, w) -> np.ndarray:
        """Centro del rebaño para rumbos: vacas VIVAS (mismo criterio que decoy_prowl)."""
        return (w.cows[w.cow_alive].mean(axis=0) if w.cow_alive.any()
                else np.array([w.W / 2.0, w.H / 2.0]))

    def _bearing_err(self, w, s2: np.ndarray) -> float:
        """|error| (rad) entre el rumbo REAL del asalto (centroide, visto desde el rebaño) y el
        rumbo PRETENDIDO θ_asa. 0.0 si no hay rumbo pretendido (keep/spawn) o sin asalto."""
        if self._theta_asa is None or s2.size == 0:
            return 0.0
        v = w.wolves[s2].mean(axis=0) - self._herd_c(w)
        if np.linalg.norm(v) < 1e-9:
            return 0.0
        err = np.arctan2(v[1], v[0]) - self._theta_asa
        return abs(float((err + np.pi) % (2 * np.pi) - np.pi))

    def _bearing_ok(self, w, s2: np.ndarray) -> bool:
        return self._bearing_err(w, s2) <= np.deg2rad(ASSAULT_BEARING_TOL_DEG)

    def _align_update(self, w, s2: np.ndarray) -> None:
        """Commit S1: avance de la fase de ALINEACIÓN (mejor-esfuerzo), una llamada por tick.
        Termina por (a) tolerancia alcanzada (preferencia), (b) SIN PROGRESO (mejora <
        ALIGN_NO_PROGRESS_DEG en ALIGN_NO_PROGRESS_TICKS) o (c) techo ALIGN_T_MAX; latchea
        _align_done por arranque de opción y emite ALIGN_END con causa y error conseguido."""
        if self._align_done:
            return
        step = int(w.step_count)
        err = self._bearing_err(w, s2)
        if self._align_best is None or err < self._align_best - np.deg2rad(ALIGN_NO_PROGRESS_DEG):
            self._align_best = err                       # progreso real: el reloj (b) se re-arma
            self._align_mark = step
        if err <= np.deg2rad(ASSAULT_BEARING_TOL_DEG):
            causa = "tolerancia"
        elif step - self._align_mark >= ALIGN_NO_PROGRESS_TICKS:
            causa = "sin_progreso"
        elif step - self._align_t0 >= ALIGN_T_MAX:
            causa = "t_max"
        else:
            return
        self._align_done = True
        self.push_event("ALIGN_END", tick=step, causa=causa, err_deg=round(float(np.rad2deg(err)), 1),
                        ticks=int(step - self._align_t0))

    def _reposition_point(self, w) -> np.ndarray:
        """Punto de presión LEJANO sobre el rumbo objetivo del asalto: la carga apunta a él y
        el empuje del hold (assault_stage) convierte esa presión en DESLIZAMIENTO por fuera
        del sobre oscuro hasta el lado Δ — la misma maniobra del script con otro objetivo."""
        u = np.array([np.cos(self._theta_asa), np.sin(self._theta_asa)])
        return self._herd_c(w) + u * (w.r_detect + self._hold + REPOSITION_EXTRA_M)

    def _manage_preys(self, w) -> None:
        """Presa 1 SIEMPRE por la maquinaria del mundo. Presa 2: en spawn, también
        (manage_pack_preys second=True ≡ script); en manager, ciclo de vida por RÉPLICA con
        la membresía del asalto (mismo contrato: suelta por muerte/refugio + n_refix por
        refugio + re-fijación de la MÁS LIBRE en ese instante)."""
        if self._mode == "spawn":
            manage_pack_preys(w, second=True)
            return
        manage_pack_preys(w)
        reason2 = w._prey2_lost_reason()
        if reason2 is not None:
            w.pack_prey2 = -1
            w.pack_prey2_kind = None
            if reason2 == "refuge":
                w.n_refix += 1
        if w.pack_prey2 < 0 and self._s2.size > 0:
            kind, idx = freest_prey_for(w, self._s2)
            if idx >= 0:
                w.pack_prey2, w.pack_prey2_kind = idx, kind
                w._ever_committed = True

    def _timing_manager(self, w, s1: np.ndarray, s2: np.ndarray) -> tuple[bool, float | None]:
        """Espejo de wolf_controllers.decoy_timing (Commit A) para membership=manager: misma
        escalera STAGE/CREEP/DEEP y mismo fallback group_hunted, con DOS diferencias de capa
        (documentadas en cabecera): el gate del show exige además que la fase de ALINEACIÓN haya
        TERMINADO (Commit S1: mejor-esfuerzo — tolerancia, sin-progreso o techo; ya NO bloqueo
        duro ±25°) y CREEP = min(25, hold) — la escalera nunca más laxa que el STAGE."""
        prowling = False
        hold_r = None
        if w.pack_prey2 >= 0 and s2.size > 0 and s1.size > 0:
            p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
            if not w.wolf_decoy_released:
                # Commit S1: el show ya NO exige cerrar ±25° — exige que la fase de alineación
                # haya TERMINADO (por tolerancia, sin-progreso o techo); después manda el guion
                # v3.3: staged por PROXIMIDAD => show.
                if assault_staged(w, s2, p2, stage_hold=self._hold) and self._align_done:
                    w.wolf_decoy_released = True
                else:
                    prowling = True
            if w.phase != "ESCOLTA" and not group_hunted(w, s2):
                if not w.wolf_decoy_released:
                    hold_r = w.r_detect + self._hold
                else:
                    decoy_c = w.wolves[s1].mean(axis=0)
                    act = w.drones[w.drone_state == ACTIVE]
                    d_decoy = (float(np.linalg.norm(act - decoy_c, axis=1).min())
                               if act.shape[0] else 1e9)
                    hold_r = (w.r_detect + min(25.0, self._hold)) \
                        if d_decoy > w.r_detect + 10.0 else (w.r_confirm + 25.0)
        elif not w.wolf_decoy_released:
            w.wolf_decoy_released = True                 # sin asalto/presa: nada que acompasar
        return prowling, hold_r

    def _decide_cebo(self, w) -> tuple[np.ndarray, bool]:
        d_wc = np.linalg.norm(w.cows[None, :, :] - w.wolves[:, None, :], axis=2)  # (nw, nc)
        self._manage_preys(w)
        if w._targets_exhausted():
            w._wolf_attacking = False
            return np.zeros((w.n_wolves, 2)), True
        s1, s2 = self._s1, self._s2
        desired = np.zeros((w.n_wolves, 2))

        released_before = bool(w.wolf_decoy_released)
        # Censura (hito staged) + TRIPWIRE del show (Q-bis): asalto ESTACIONADO pre-show.
        if not w.wolf_decoy_released and w.pack_prey2 >= 0 and s1.size > 0 and s2.size > 0 \
                and assault_staged(w, s2, w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind),
                                   stage_hold=self._hold):
            if self.t_staged is None:
                self.t_staged = int(w.step_count)
            self._staged_noshow += 1
            if self._staged_noshow >= SHOW_STALL_TICKS:
                w.wolf_decoy_released = True             # TRIPWIRE: show forzado
                self.n_stalls += 1
                self._staged_noshow = 0
                self.push_event("STALL", tick=int(w.step_count) + 1,
                                ticks_staged=SHOW_STALL_TICKS, mode=self._mode,
                                align_done=self._align_done)
        if self._mode == "spawn":
            decoy_prowling, assault_hold = decoy_timing(
                w, s1, s2, stage_hold=self._hold, creep_hold=min(25.0, self._hold))
        else:
            self._align_update(w, s2)                    # Commit S1: fase de alineación (por tick)
            decoy_prowling, assault_hold = self._timing_manager(w, s1, s2)
        if w.wolf_decoy_released and not released_before:
            # El show surte efecto EN ESTE paso -> tick step_count+1 (frontera siguiente,
            # comparable con el flanco STAGED que ve el EventTracker). Aserción A del
            # protocolo: SHOW_START nunca antes del latch. Commit S1: registra el ERROR ANGULAR
            # CONSEGUIDO (θ logrado vs pretendido) — las celdas S pasan a ser "Δ pretendido" con
            # distribución de Δ conseguido.
            if self.t_show is None:
                self.t_show = int(w.step_count) + 1          # hito de censura (tick de efecto)
            self.push_event("SHOW_START", tick=int(w.step_count) + 1, mode=self._mode,
                            err_rumbo_deg=(None if self._theta_asa is None else
                                           round(float(np.rad2deg(self._bearing_err(w, s2))), 1)),
                            delta_pretendida_deg=(None if self._theta_asa is None else
                                                  round(float(np.rad2deg(self._delta)), 0)))

        atk1 = atk2 = False
        if decoy_prowling:
            decoy_prowl(w, s1, desired)
        else:
            atk1 = sector_desired(w, s1, w.pack_prey, w.pack_prey_kind, d_wc, desired)
            if (w.wolf_decoy_size is not None and w.wolf_decoy_released and w.phase != "ESCOLTA"
                    and s1.size > 0 and s2.size > 0):
                if decoy_broken_wing(w, s1, desired):
                    atk1 = False
        if assault_hold is not None:
            aim = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
            # Commit S1: el tránsito se dirige a θ_asa MIENTRAS dura la fase de alineación (Δ
            # conserva su significado de rumbo PRETENDIDO); al terminar (tolerancia, sin-progreso
            # o techo) la presión vuelve a la presa — condiciones v3.3 del guion.
            if self._theta_asa is not None and not self._align_done:
                aim = self._reposition_point(w)
            assault_stage(w, s2, aim, desired, hold=assault_hold)
        elif s2.size > 0:
            if w.wolf_decoy_released and self.t_suelta is None:
                self.t_suelta = int(w.step_count)            # censura: asalto SUELTO (release)
            atk2 = sector_desired(w, s2, w.pack_prey2, w.pack_prey2_kind, d_wc, desired)
        w._wolf_attacking = bool(atk1 or atk2)
        if atk2 and w.wolf_decoy_released and self.t_strike is None:
            self.t_strike = int(w.step_count)                # censura: asalto A TIRO (strike)

        return pack_common_tail(w, desired, d_wc), False
