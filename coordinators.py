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

from world import ACTIVE, DETER_RADIUS


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

    PERCEPCIÓN REALISTA (v2.6): el coordinador solo VE los lobos DETECTADOS — hasta v2.5 la barrera se
    orientaba al centroide de TODOS los lobos (omnisciencia: conocía lobos que ningún dron había visto).
    Regla EXACTA:
      * DETECTADO = lobo a <= r_detect de algún dron EN VUELO (ACTIVE) — el MISMO criterio DRI del
        disparador del mundo (_update_phase/_pick_investigator: "solo los ACTIVE detectan/confirman",
        mismo r_detect); recomputado aquí en SOLO-LECTURA cada paso (el mundo no cambia, sin radio nuevo).
      * El EJE de la barrera se ancla al lobo ANCLA = el PRIMER lobo detectado (memoria del COORDINADOR:
        paso de primera detección por lobo; desempate por índice menor), con HISTÉRESIS: se mantiene sobre
        él mientras siga detectado; si deja de serlo (sale de detección), pasa al siguiente detectado más
        antiguo. (El "primer detectado" ≈ el que disparó la ESCOLTA.)
      * PENETRADO y la cobertura lobo-a-lobo operan SOLO sobre los lobos detectados (sin esto el frente
        no visto seguiría atrayendo drones por la puerta de atrás). Las FÓRMULAS no cambian: mismo
        standoff, mismas ranuras/spacing, mismo reparto, misma patrulla; solo cambia A QUÉ lobos mira.
      * En ESCOLTA SIN ningún lobo detectado: PATRULLA (como sin amenaza) hasta re-detectar.
    Consecuencia buscada: con dos frentes (spawn grouped v2.5), si los drones solo han visto uno, el otro
    entra SIN SER VISTO — el cebo pasa a ser físicamente real, no un artefacto de la media global.

    Solo comanda a los drones LIBRES (ACTIVE y no-investigando): NO toca el reflejo de investigación (el
    investigador) ni los relevos de batería (deja su waypoint actual). NO toca la física (world.py congelado);
    construye un array de waypoints y deja que la disuasión del mundo haga el trabajo. Parámetros afinables."""

    def __init__(self, world, *, barrier_standoff: float | None = None, drone_spacing: float | None = None,
                 front_cows: int | None = None, engage_standoff: float | None = None,
                 patrol_radius: float | None = None, patrol_omega: float = 0.02):
        self.world = world
        self.n_drones = world.n_drones
        # Parámetros ETIQUETADOS / afinables (m; rad/paso). Defaults atados a la escala de disuasión del
        # mundo (DETER_RADIUS=20) -> el frente "teja" con solape de campos de disuasión (spacing < 2*R).
        self.barrier_standoff = barrier_standoff if barrier_standoff is not None else DETER_RADIUS          # barrera por delante de la vaca más amenazada, HACIA el paquete
        self.drone_spacing = drone_spacing if drone_spacing is not None else 1.6 * DETER_RADIUS             # separación entre drones del frente (< 2*DETER_RADIUS => solapan)
        self.front_cows = front_cows                                                                        # nº de vacas "del frente" para anclar la barrera (None -> tantas como drones, mín 2)
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
        # Estado de PERCEPCIÓN (v2.6): memoria de primera detección por lobo + lobo ANCLA vigente.
        # Vive en el COORDINADOR (el mundo no cambia); se reinicia solo ante un episodio nuevo
        # (step_count retrocede o cambia n_wolves). -1 = lobo nunca visto.
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
        det = self._detected()                                    # v2.6: el coordinador solo VE lo detectado
        anchor = self._update_anchor(det)                         # lobo ANCLA (primer detectado, histéresis)
        if w.phase == "ESCOLTA" and anchor is not None and herd.shape[0] > 0:
            seen = np.asarray(w.wolves, dtype=float)[det]         # SOLO los lobos detectados
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

    def _detected(self) -> np.ndarray:
        """Máscara (n_wolves,) de lobos DETECTADOS (v2.6): a <= r_detect de algún dron EN VUELO (ACTIVE).
        Calca el criterio DRI del disparador del mundo (_update_phase: 'solo los ACTIVE detectan',
        _pick_investigator: d <= r_detect); SOLO-LECTURA sobre estado que el mundo ya calcula."""
        w = self.world
        if w.n_wolves == 0:
            return np.zeros(0, dtype=bool)
        flying = w.drones[w.drone_state == ACTIVE]
        if flying.shape[0] == 0:
            return np.zeros(w.n_wolves, dtype=bool)
        d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
        return (d <= w.r_detect).any(axis=1)

    def _update_anchor(self, det: np.ndarray) -> int | None:
        """Lobo ANCLA de la barrera (v2.6) = el PRIMER lobo detectado, con HISTÉRESIS: mientras siga
        detectado se mantiene; al perderse, pasa al detectado con primera detección más ANTIGUA
        (desempate: índice menor — determinista). Devuelve None si no hay ninguno detectado.
        La memoria (paso de primera detección) se acumula cada act() en TODAS las fases (los drones ya
        ven en VIGILANCIA/SOSPECHA) y se reinicia ante un episodio nuevo."""
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
        """Barrera de apantallado sobre los lobos DETECTADOS (v2.6). CLEAN: frente perpendicular entre el
        lobo ANCLA y las vacas más cercanas a él. PENETRADO (el ancla ya está entre las vacas): cubre a
        los lobos detectados más cercanos a ellas. Fórmulas idénticas a v2.5; solo cambió el QUÉ mira
        (`wolves` = subconjunto detectado, `pack_c` = posición del ancla en vez de la media global)."""
        k = idx.size
        pack_c = anchor_pos
        herd_c = herd.mean(axis=0)
        herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
        if float(np.linalg.norm(pack_c - herd_c)) <= herd_r:          # el paquete YA está dentro del rebaño
            return self._cover_engaged(idx, wolves, herd)

        # CLEAN: ancla en el centroide de las vacas MÁS CERCANAS al paquete (el frente amenazado).
        nfront = self.front_cows if self.front_cows is not None else max(2, k)
        order = np.argsort(np.linalg.norm(herd - pack_c, axis=1))
        front_c = herd[order[:nfront]].mean(axis=0)
        u = pack_c - front_c
        u = u / max(float(np.linalg.norm(u)), 1e-9)                    # de las vacas HACIA el paquete
        center = front_c + u * self.barrier_standoff                  # punto de barrera (standoff por delante)
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
