"""
coordinators.py — Políticas de coordinación de los drones.

El coordinador recibe una observación (y, los clásicos, el estado del mundo) y devuelve
WAYPOINTS para los drones (array (n_drones, 2), estilo step()). El mundo solo aplica los
de los drones LIBRES (no-investigando); el reflejo de investigación manda sobre el dron
que investiga y la batería sobre los relevos. Es el hueco intercambiable: Dummy (referencia)
→ ReactiveCoordinator (clásico, regla fija) → MAPPO (aprendido) después.

Solo se compara el COORDINADOR; la física del mundo está congelada (v2, tag v2-baseline).
"""

from __future__ import annotations
import numpy as np

from world import ACTIVE, DETER_RADIUS, STATIC_DETER_RADIUS


class DummyCoordinator:
    """Ignora la observación y NO comanda nada (devuelve None) -> los drones MANTIENEN su waypoint, que
    es su posición de partida, así que se quedan efectivamente quietos. El movimiento de drones es una
    capacidad del mundo (command_waypoint); este coordinador simplemente no la usa. Es la BASELINE v2."""

    def __init__(self, n_drones: int):
        self.n_drones = n_drones

    def act(self, observation: dict | None) -> None:
        return None


class ReactiveCoordinator:
    """Coordinador CLÁSICO (regla FIJA, no aprende): la referencia que el MARL deberá batir.

    Forma una BARRERA DE APANTALLADO entre la manada de lobos y las vacas más cercanas a ella, para
    que la DISUASIÓN del mundo (automática: cada dron ACTIVE frena/aparta a los lobos a <= DETER_RADIUS)
    detenga a los lobos ANTES de que alcancen al rebaño. Es COORDINADO (reparte el frente, no cada uno a
    por un lobo) y REACTIVO (recalcula cada paso). Defiende al rebaño EN CONJUNTO -> NO usa la presa fijada
    del paquete; solo ve posiciones de lobos y de vacas vivas no-a-salvo (incluidos terneros).

    - ESCOLTA (>=1 lobo confirmado): barrera perpendicular al eje rebaño->manada, repartida y a un
      `barrier_standoff` por delante de las vacas más amenazadas. Caso PENETRADO (la manada ya está entre
      las vacas): degrada con gracia a cubrir a los lobos MÁS CERCANOS a las vacas (los ya enganchados).
    - Sin amenaza confirmada (VIGILANCIA/SOSPECHA, solo-corzos): PATRULLA en órbita alrededor del rebaño.

    PERCEPCIÓN HONESTA (v2.8): la barrera reacciona SOLO a lobos CONFIRMADOS de equipo con memoria —
    fin de la percepción-oráculo. Lineage: hasta v2.5 la barrera usaba el centroide de TODOS los lobos
    (omnisciencia de POSICIÓN); v2.6 la restringió a los DETECTADOS (<= r_detect=100 de un ACTIVE),
    pero eso seguía siendo trampa con el marco DRI del mundo: a r_detect solo se sabe "hay un CONTACTO"
    (bulto sin clasificar — podría ser un corzo); el TIPO solo se conoce a r_confirm=40 (oráculo,
    stand-in de YOLO). v2.6 reaccionaba a bultos a 100 m sabiendo por verdad-terreno que eran lobos ->
    no dejaba frente ciego. Regla EXACTA v2.8:
      * CONFIRMADO = lobo que ALGUNA VEZ ha estado a <= r_confirm de algún dron EN VUELO (ACTIVE) —
        el nivel IDENTIFICAR del marco DRI, el mismo r_confirm del oráculo del mundo. Confirmación de
        EQUIPO (compartida por la flota) con MEMORIA: dura el resto del episodio (tracking), aunque el
        lobo luego se aleje. Un contacto NUNCA confirmado NO existe para la barrera (aunque esté a
        <= r_detect y el mundo conozca su posición real). Modelado como oráculo determinista; la fase
        de percepción lo sustituirá por YOLO+tracking con esta MISMA interfaz de decisión.
      * El EJE de la barrera se ancla al lobo ANCLA = el PRIMER lobo confirmado (memoria del COORDINADOR:
        paso de primera confirmación por lobo; desempate por índice menor), con HISTÉRESIS (con la
        memoria latcheada un confirmado ya no "se pierde": el ancla es estable todo el episodio).
      * PENETRADO y la cobertura lobo-a-lobo operan SOLO sobre los lobos confirmados. Las FÓRMULAS no
        cambian: mismas ranuras/spacing, mismo reparto, misma patrulla; solo cambia A QUÉ lobos mira.
      * En ESCOLTA SIN ningún lobo confirmado: PATRULLA hasta que se confirme alguno. (La máquina de
        fases del mundo NO cambia: ESCOLTA ya disparaba por CONFIRMACIÓN del oráculo a r_confirm —
        world._update_phase — y los contactos sin confirmar solo mantienen SOSPECHA/investigación.)
    Consecuencia buscada: con dos frentes (spawn grouped v2.5), el frente que nadie ha CONFIRMADO tiene
    vía libre aunque esté detectado como contacto — el frente ciego que hace el cebo físicamente posible.

    BARRERA SIN HUECOS (v3.2, arreglo 1): separación entre drones = 2·STATIC_DETER_RADIUS = 20 m ->
    las PAREDES BLANDAS estáticas (radio 10, v2.7) de drones ADYACENTES SE TOCAN: un lobo NO puede
    cruzar la línea sin entrar en el radio de pared de algún dron (con el spacing previo 1.6·DETER=32
    quedaban franjas de 12 m sin pared: diagnóstico v3.2 = ~4.6 cruces de línea/ep y 75.4% de
    encuentros cercanos SILENCIOSOS — lobo a <=DETER de un ACTIVE sin susto ni pared). La línea queda
    ESTRECHA (~60 m con 4 drones): se ACEPTA que se pueda RODEAR por los FLANCOS — limitación honesta
    de esta baseline ingenua; el flanqueo lateral es (junto al 2º frente) el agujero que el MARL de
    drones deberá aprender a cubrir.

    STANDOFF DERIVADO (v2.8, recalculado con el spacing v3.2): la distancia MÍNIMA de la línea al
    borde delantero del rebaño garantiza que el punto PEOR (a mitad LATERAL entre dos drones
    adyacentes, sobre la línea de vacas frontales) queda a <= DETER_RADIUS del dron más cercano:
    standoff = sqrt(DETER_RADIUS² − (spacing/2)²) = sqrt(20² − 10²) ≈ 17.3 m.

    BARRERA QUE AVANZA DE VERDAD (v3.2, arreglo 2 — regla del usuario): una vez formada, la barrera
    AVANZA hacia el lobo que ANCLA, PERO su CENTRO nunca se aleja más de MAX_ADVANCE_FROM_HERD del
    CENTROIDE de las vacas (posiciones de COLLAR — conocidas siempre):
      aim = clip(d_ancla + STATIC_DETER_RADIUS, suelo, max_advance_from_herd), medido DESDE el
      centroide del rebaño por el eje rebaño->ancla; suelo = borde delantero del rebaño en ese eje
      + standoff (la línea SIEMPRE por delante de las vacas). El sobre-apuntado +10 (el radio de la
      pared blanda: el anillo donde un lobo aparca junto a un dron quieto sin ser espantado) hace que
      la formación CIERRE con velocidad de aproximación -> expulsa, no escolta.
    Diagnóstico v3.2 de por qué v3.1 NO avanzaba pese a su test: la línea v3.1 anclaba en front_c
    (~el centroide, medido a 0.8 m de él) con adv = clip(L+10, 12, 36.7) -> el centro vivía SIEMPRE a
    <=37 m del centroide y solo "perseguía" si el ancla estaba a L<27 m (la banda del test 12); con
    los lobos rondando a 40-100 m la línea esperaba clavada (17.9% de pasos de ESCOLTA la formación
    entera iba a <1 m/s = incapaz de expulsar; 6.6% de pasos saturada en el tope). v3.2 persigue al
    ancla en TODO el anillo de 50 m: MAX_ADVANCE_FROM_HERD = 50 (afinable) = radio del rebaño (~20)
    + ~30 de salida — sale a espantar ADELANTADO sin exponer la retaguardia (a 15 vs 4 m/s vuelve a
    tiempo). Sustituye al tope v2.9-v3.1 advance_max = sqrt(r_confirm²−(s/2)²) medido desde front_c
    (~39 del centroide): el anillo de 50 llega ~11 m más lejos — a costa de que un lobo que entre por
    la ESPALDA de la línea ya no quede confirmable por ella (en ESCOLTA el mundo no lanza nuevas
    investigaciones): agujero DELIBERADO, coherente con el 2º frente libre.
    DOS FRENTES confirmados: la barrera ENTERA va al frente que ANCLA (el 1º confirmado / el cebo); el
    2º frente queda LIBRE. Es una defensa DELIBERADAMENTE explotable — la línea única no se parte ni
    intenta cubrir ambos: la baseline ingenua cuyo agujero el MARL de drones deberá aprender a no
    tener (test dirigido: mover el 2º frente confirmado no cambia NI UN waypoint en modo CLEAN).

    Solo comanda a los drones LIBRES (ACTIVE y no-investigando): NO toca el reflejo de investigación (el
    investigador). v3.0 (pieza 5): el dron que ANUNCIÓ relevo sigue siendo comandable (ya no se clava
    esperando; el INCOMING lo persigue). NO toca la física (world.py congelado); construye un array de
    waypoints y deja que la disuasión del mundo haga el trabajo. Parámetros afinables."""

    def __init__(self, world, *, barrier_standoff: float | None = None, drone_spacing: float | None = None,
                 front_cows: int | None = None, engage_standoff: float | None = None,
                 max_advance_from_herd: float = 50.0,
                 patrol_radius: float | None = None, patrol_omega: float = 0.02):
        self.world = world
        self.n_drones = world.n_drones
        # Parámetros ETIQUETADOS / afinables (m; rad/paso). v3.2 (arreglo 1 — BARRERA SIN HUECOS):
        # spacing = 2·STATIC_DETER_RADIUS = 20 m -> las paredes blandas (radio 10) de drones adyacentes
        # SE TOCAN: cruzar la línea siempre mete al lobo en el radio de pared de algún dron (antes
        # 1.6·DETER=32: franjas de 12 m sin pared -> ~4.6 cruces/ep medidos). La línea estrecha se
        # RODEA por los flancos — limitación aceptada (documentada en el docstring).
        self.drone_spacing = drone_spacing if drone_spacing is not None else 2.0 * STATIC_DETER_RADIUS      # separación entre drones del frente (paredes blandas ADYACENTES se tocan)
        # v2.8: standoff DERIVADO de la geometría de disuasión (ver docstring): el punto peor de la línea
        # de vacas frontales (a mitad lateral entre dos drones) queda a <= DETER_RADIUS del más cercano.
        # sqrt(R² − (s/2)²) = sqrt(20² − 10²) ≈ 17.3 m con el spacing v3.2 (=20).
        self.barrier_standoff = barrier_standoff if barrier_standoff is not None else \
            float(np.sqrt(max(DETER_RADIUS ** 2 - (self.drone_spacing / 2.0) ** 2, 0.0)))                   # distancia MÍNIMA de la línea al borde delantero del rebaño
        # v3.2 (arreglo 2 — regla del usuario): la barrera PERSIGUE al ancla, pero su CENTRO no se aleja
        # más de esto del CENTROIDE de las vacas (collares). 50 = radio del rebaño (~20) + ~30 de salida:
        # espanta adelantado sin exponer la retaguardia (15 vs 4 m/s: vuelve a tiempo). Sustituye al tope
        # advance_max v2.9-v3.1 (sqrt(r_confirm²−(s/2)²) desde front_c ≈ 39 del centroide; ver docstring).
        self.max_advance_from_herd = float(max_advance_from_herd)
        self.front_cows = front_cows                                                                        # (sin uso desde v3.2: el eje ancla en el CENTROIDE de collares; se conserva por compat de firma)
        self.engage_standoff = engage_standoff if engage_standoff is not None else 2.0 * world.r_face_safe  # penetrado: dron entre la vaca y el lobo enganchado
        self.patrol_radius = patrol_radius                                                                 # órbita de patrulla (None -> adaptativo al tamaño del rebaño)
        self.patrol_omega = patrol_omega                                                                   # giro de la órbita (patrulla en movimiento)
        # Estado de la PATRULLA: ancla la FASE de la formación a la posición angular ACTUAL de los drones
        # -> desde el paso 0 cada dron va a su ranura MÁS CERCANA (no cruza el centro). Se re-ancla si cambia
        # el nº de drones libres o si la patrulla se reanuda tras una interrupción (ESCOLTA).
        self._patrol_base: float | None = None
        self._patrol_k: int | None = None
        self._patrol_step0: int = 0
        self._patrol_last_step: int = -10
        # Estado de PERCEPCIÓN (v2.8): máscara de lobos CONFIRMADOS (latch de equipo con memoria) +
        # memoria de primera confirmación por lobo + lobo ANCLA vigente. Vive en el COORDINADOR (el
        # mundo no cambia); se reinicia solo ante un episodio nuevo (step_count retrocede o cambia
        # n_wolves). -1 = lobo nunca confirmado.
        self._confirmed: np.ndarray | None = None
        self._conf_step: int = -1
        self._first_seen: np.ndarray | None = None
        self._anchor: int | None = None
        self._last_step: int = -1

    # ------------------------------------------------------------------ #
    def act(self, observation: dict | None = None) -> np.ndarray:
        """Devuelve waypoints (n_drones, 2). Por defecto cada dron MANTIENE su waypoint (reservas en la
        central, investigador, relevos); solo se reescribe el de los drones ACTIVE LIBRES."""
        w = self.world
        wp = w.drone_waypoint.copy()
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
        idx = np.where(free)[0]
        if idx.size == 0:
            return wp
        herd = self._live_herd()                                  # rebaño = vacas + terneros vivos y NO a salvo
        conf = self._confirmed_wolves()                           # v2.8: el coordinador solo VE lo CONFIRMADO
        anchor = self._update_anchor(conf)                        # lobo ANCLA (primer confirmado, histéresis)
        if w.phase == "ESCOLTA" and anchor is not None and herd.shape[0] > 0:
            seen = np.asarray(w.wolves, dtype=float)[conf]        # SOLO los lobos confirmados
            tgt = self._barrier(idx, seen, np.asarray(w.wolves[anchor], dtype=float), herd)
        else:
            tgt = self._patrol(idx, herd if herd.shape[0] > 0 else np.asarray(w.cows, dtype=float))
        wp[idx] = np.clip(tgt, [0.0, 0.0], [w.W, w.H])            # dentro del campo (el vuelo clipa igualmente)
        return wp

    # ------------------------------------------------------------------ #
    def _live_herd(self) -> np.ndarray:
        """Posiciones del rebaño a PROTEGER: vacas + terneros VIVOS y NO a salvo (el coordinador defiende
        al conjunto; NO usa la presa fijada). Vacío si no queda nada que proteger."""
        w = self.world
        parts = []
        m = w.cow_alive & ~w.cow_safe
        if m.any():
            parts.append(w.cows[m])
        if w.n_calves > 0:
            mc = w.calf_alive & ~w.calf_safe
            if mc.any():
                parts.append(w.calves[mc])
        return np.vstack(parts) if parts else np.zeros((0, 2))

    def _confirmed_wolves(self) -> np.ndarray:
        """Máscara (n_wolves,) de lobos CONFIRMADOS (v2.8, percepción HONESTA): un lobo queda CONFIRMADO
        en cuanto está a <= r_confirm de algún dron EN VUELO (ACTIVE) — el nivel IDENTIFICAR del marco
        DRI, el MISMO r_confirm del oráculo del mundo (_update_phase) — y la confirmación es de EQUIPO
        con MEMORIA (latch |=): se recuerda el resto del episodio aunque el lobo se aleje (tracking;
        sin drones en vuelo tampoco se olvida — es conocimiento de flota, no línea de vista). Un lobo
        NUNCA confirmado NO existe para la barrera aunque esté a <= r_detect (eso es solo un CONTACTO
        sin clasificar — el reflejo de investigación del MUNDO ya se ocupa de él). Se reinicia ante un
        episodio nuevo (step_count retrocede o cambia n_wolves). SOLO-LECTURA sobre el mundo."""
        w = self.world
        step = int(w.step_count)
        if self._confirmed is None or self._confirmed.shape[0] != w.n_wolves or step < self._conf_step:
            self._confirmed = np.zeros(w.n_wolves, dtype=bool)
        self._conf_step = step
        if w.n_wolves == 0:
            return self._confirmed
        flying = w.drones[w.drone_state == ACTIVE]
        if flying.shape[0] > 0:
            d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
            self._confirmed |= (d <= w.r_confirm).any(axis=1)
        return self._confirmed

    def _update_anchor(self, det: np.ndarray) -> int | None:
        """Lobo ANCLA de la barrera = el PRIMER lobo confirmado (v2.8; antes detectado), con HISTÉRESIS:
        mientras siga en la máscara se mantiene; al perderse, pasa al de primera confirmación más ANTIGUA
        (desempate: índice menor — determinista; con la memoria latcheada de v2.8 un confirmado ya no se
        pierde -> el ancla es estable todo el episodio). Devuelve None si no hay ninguno confirmado.
        La memoria (paso de primera confirmación) se acumula cada act() en TODAS las fases y se
        reinicia ante un episodio nuevo."""
        w = self.world
        step = int(w.step_count)
        if self._first_seen is None or self._first_seen.shape[0] != w.n_wolves or step < self._last_step:
            self._first_seen = np.full(w.n_wolves, -1, dtype=int)
            self._anchor = None
        self._last_step = step
        if det.shape[0] == 0 or not det.any():
            self._anchor = None
            return None
        news = det & (self._first_seen < 0)
        self._first_seen[news] = step
        if self._anchor is not None and det[self._anchor]:
            return self._anchor                                   # histéresis: sigue detectado -> se mantiene
        seen = np.where(det)[0]
        self._anchor = int(seen[np.argmin(self._first_seen[seen])])   # más antiguo; argmin = 1ª ocurrencia (índice menor)
        return self._anchor

    def _barrier(self, idx: np.ndarray, wolves: np.ndarray, anchor_pos: np.ndarray, herd: np.ndarray) -> np.ndarray:
        """Barrera de apantallado sobre los lobos CONFIRMADOS (v2.8). CLEAN (v3.2): frente perpendicular
        al eje centroide-de-collares -> ancla, que PERSIGUE al ancla acotado al anillo de
        max_advance_from_herd (regla del usuario). PENETRADO (el ancla ya está entre las vacas): cubre
        a los lobos confirmados más cercanos a ellas (sin cambios)."""
        k = idx.size
        pack_c = anchor_pos
        herd_c = herd.mean(axis=0)
        herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
        if float(np.linalg.norm(pack_c - herd_c)) <= herd_r:          # el paquete YA está dentro del rebaño
            return self._cover_engaged(idx, wolves, herd)

        # CLEAN (v3.2, arreglo 2 — regla del usuario): la FORMACIÓN ENTERA (línea perpendicular al
        # eje rebaño->ancla) PERSIGUE al ancla por ese eje, acotada al anillo de max_advance_from_herd
        # alrededor del CENTROIDE de las vacas (collares): empuja hacia la amenaza mientras
        # dist(centro_barrera, centroide) <= max_advance; si llegar al lobo excede eso, se queda en el
        # borde del anillo. El sobre-apuntado +STATIC_DETER_RADIUS (=10, el radio de la pared blanda:
        # el anillo donde un lobo aparca junto a un dron quieto sin ser espantado) garantiza que la
        # formación CIERRA con velocidad de aproximación -> EXPULSA mientras avanza (apuntar AL lobo
        # dejaría escolta lateral con aproximación ~0, jamás expulsa). Suelo: borde DELANTERO del
        # rebaño en el eje + standoff (la línea siempre POR DELANTE de las vacas; garantía v2.8).
        # [v3.1 anclaba en front_c≈centroide con adv<=36.7: el centro vivía pegado al rebaño y solo
        #  perseguía con el ancla a <27 m — el diagnóstico v3.2 la midió QUIETA (<1 m/s el 17.9% de
        #  ESCOLTA) con 75.4% de encuentros silenciosos. front_cows queda sin uso en CLEAN.]
        # DOS FRENTES confirmados: la barrera ENTERA va al frente que ANCLA (el 1º confirmado); el 2º
        # queda LIBRE — defensa DELIBERADAMENTE explotable (la línea única no se parte): es el agujero
        # que el MARL de drones deberá aprender a no tener.
        u = pack_c - herd_c
        d_anchor = float(np.linalg.norm(u))
        u = u / max(d_anchor, 1e-9)                                    # del centroide HACIA el ancla
        proj_front = float(((herd - herd_c) @ u).max())                # borde delantero del rebaño en el eje
        floor = proj_front + self.barrier_standoff
        aim = min(d_anchor + STATIC_DETER_RADIUS, self.max_advance_from_herd)
        aim = max(aim, floor)                                          # nunca detrás del frente de vacas
        center = herd_c + u * aim                                      # centro de la formación (persigue, acotado)
        perp = np.array([-u[1], u[0]])                                # eje del frente (perpendicular al eje de amenaza)
        offs = (np.arange(k) - (k - 1) / 2.0) * self.drone_spacing    # ranuras repartidas y centradas
        slots = center[None, :] + offs[:, None] * perp[None, :]
        return self._assign(idx, slots, perp)

    def _cover_engaged(self, idx: np.ndarray, wolves: np.ndarray, herd: np.ndarray) -> np.ndarray:
        """PENETRADO: para cada dron, un lobo de los MÁS enganchados (más cerca de una vaca); lo cubre
        situándose entre su vaca más cercana y él (a engage_standoff de la vaca, hacia el lobo)."""
        k = idx.size
        d = np.linalg.norm(wolves[:, None, :] - herd[None, :, :], axis=2)   # (nw, nh)
        near_cow = d.argmin(axis=1)
        order = np.argsort(d.min(axis=1))                                   # lobos más enganchados primero
        slots = np.zeros((k, 2))
        for s in range(k):
            wj = int(order[s % order.size])
            cow = herd[near_cow[wj]]
            v = wolves[wj] - cow
            v = v / max(float(np.linalg.norm(v)), 1e-9)
            slots[s] = cow + v * self.engage_standoff
        return self._assign(idx, slots, None)

    def _patrol(self, idx: np.ndarray, herd: np.ndarray) -> np.ndarray:
        """Sin amenaza confirmada: órbita lenta y REPARTIDA alrededor del centroide del rebaño. Cada dron va
        a SU ranura equiespaciada (i -> 2πi/k) y la FASE de la formación se ANCLA (media circular) a la
        posición angular actual de los drones -> desde el paso 0 cada dron va a su ranura MÁS CERCANA (no
        cruza el centro), y luego la formación gira RÍGIDA con patrol_omega (sin reasignaciones que crucen).
        [Bug corregido: al anclar la fase a 0, los drones —que nacen en las ESQUINAS del rebaño, ~225°+90°i—
        se enviaban a la ranura i·2π/k, ~135° OPUESTA, así que TODOS cruzaban el centro antes de recolocarse.]"""
        k = idx.size
        c = herd.mean(axis=0)
        r = self.patrol_radius
        if r is None:
            spread = float(np.linalg.norm(herd - c, axis=1).max()) if herd.shape[0] > 1 else 0.0
            r = spread + self.world.r_notice + DETER_RADIUS               # justo fuera del rebaño, listos para reaccionar
        step = self.world.step_count
        grid = 2 * np.pi * np.arange(k) / max(k, 1)                        # ranura equiespaciada por dron (por índice)
        # (Re)ancla la fase: primera patrulla, cambia el nº de libres, o se reanuda tras un hueco (ESCOLTA).
        if self._patrol_base is None or self._patrol_k != k or step - self._patrol_last_step > 1:
            d = self.world.drones[idx] - c
            theta = np.arctan2(d[:, 1], d[:, 0])                          # ángulo actual de cada dron libre
            resid = theta - grid                                         # desfase de cada dron respecto a su ranura
            self._patrol_base = float(np.arctan2(np.sin(resid).mean(), np.cos(resid).mean()))  # media circular -> ancla
            self._patrol_k = k
            self._patrol_step0 = step
        self._patrol_last_step = step
        ang = self._patrol_base + self.patrol_omega * (step - self._patrol_step0) + grid
        return c[None, :] + r * np.column_stack([np.cos(ang), np.sin(ang)])

    def _assign(self, idx: np.ndarray, slots: np.ndarray, axis: np.ndarray | None) -> np.ndarray:
        """Empareja drones libres con ranuras minimizando cruces (coordinado): ordena ambos por su
        proyección en `axis` (o por x si axis=None) y empareja en orden. Determinista. Devuelve los
        targets en el ORDEN de idx (target[j] = ranura del j-ésimo dron libre)."""
        drones = self.world.drones[idx]
        kd = drones @ axis if axis is not None else drones[:, 0]
        ks = slots @ axis if axis is not None else slots[:, 0]
        di = np.argsort(kd, kind="stable")
        si = np.argsort(ks, kind="stable")
        out = np.zeros_like(slots)
        out[di] = slots[si]
        return out
