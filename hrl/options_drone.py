"""hrl/options_drone.py — Capa de OPCIONES del bando DRON: reparto de puestos (Etapa 0).

`AllocatorCoordinator(world, particion)` reparte los 4 ASIENTOS de barrera (los `seats()`
del ResidualDroneCoordinator — heredados literalmente, con su edge-case de asientos vacíos)
entre:

  FRENTE   un ReactiveCoordinator RESTRINGIDO AL SUBCONJUNTO por subclase
           (`SubsetReactiveCoordinator` — coordinators.py NO se toca, mismo patrón que
           NonRigidBarrier): la MISMA línea rígida v3.4 con k ranuras (la barrera ya es
           paramétrica en k: offsets centrados (i−(k−1)/2)·spacing, gobernador incluido).
           Con partición 4-0 y todos los asientos, BIT A BIT ReactiveCoordinator
           (hrl_check 4).
  GUARDIA  persecución ACTIVA del lobo más cercano del clúster objetivo — REVALIDADA bajo
           v3.5+/v3.7.1 (Commit D2a): con la REGLA DEL SONIDO la expulsión ya NO exige
           aproximación (SCARE_APPROACH_MIN deprecated desde v3.5; un dron QUIETO expulsa a
           <= DETER_RADIUS=20), pero un guardia quieto solo cubre SU burbuja de 20 m — el
           waypoint sigue siendo LA POSICIÓN VIVA de la amenaza porque PERSEGUIR lleva la
           burbuja HASTA el lobo del 2º frente y lo intercepta ANTES del rebaño (a 15 vs
           4 m/s el alcance está garantizado): la CONDUCTA se mantiene, la justificación
           cambia (test [D2a] de hrl_check). Sin 2º clúster: cubrir el OCTANTE MÁS ABIERTO
           (el de rumbo más lejano de toda amenaza percibida y del resto de drones), a
           radio de patrulla.

PERCEPCIÓN HONESTA del reparto: los clústeres se forman con amenazas =
CONTACTOS ∪ CONFIRMADOS — el bando dron NO ve verdad-terreno. Contacto = cuerpo NO
descartado (lobo O corzo/jabalí: el tipo es desconocido a distancia) a <= r_detect de un
ACTIVE (el criterio DRI del mundo, recomputado en solo-lectura); confirmado = el latch de
equipo v2.8 del FRENTE (una sola fuente de verdad, con memoria). Un lobo confirmado sale
del grupo de contactos (grupos disjuntos, mismo convenio que la obs de run02). Clústeres =
amenazas separadas > CLUSTER_SEP_DEG (60°) de rumbo respecto al centroide del rebaño;
clúster PRIMARIO = el que contiene al ancla de la barrera (sin ancla: el más poblado);
clúster OBJETIVO de la guardia = el secundario más poblado (desempates deterministas).

REGLA PROPORCIONAL scripted (el manager clásico de E0.4):
`ProportionalAllocatorCoordinator` fija guardias = clip(nº amenazas del clúster secundario,
0, 2) re-muestreado cada `frame_skip=5` pasos (la frontera de los envs — lección
SyncedReactiveCoordinator). Los asientos de guardia son los ÚLTIMOS de la lista de seats()
(determinista; los relevos cambian el dron, no el puesto).

SIN RNG; solo lecturas del mundo + los waypoints devueltos (contrato de coordinador). La
máscara comandable es la del mundo (ACTIVE & ~investigating): un asiento STRANDED o
investigando NO se comanda (behavior_checks.check_command_mask lo vigila en los
experimentos)."""

from __future__ import annotations

import numpy as np

from coordinators import ReactiveCoordinator
from world import ACTIVE, DETER_RADIUS

from rl.drone_obs import N_SEATS
from rl.residual_drone_coordinator import ResidualDroneCoordinator

CLUSTER_SEP_DEG = 60.0    # ° de rumbo (desde el centroide del rebaño) que separan clústeres
GUARD_MAX = 2             # tope de guardias de la regla proporcional: clip(n_sec, 0, 2)


class _Seats(ResidualDroneCoordinator):
    """SOLO los asientos: hereda `seats()` LITERAL (ACTIVE∪STRANDED por índice, -1 = vacío,
    cap N_SEATS) sin construir la barrera interior ni el resto del residual."""

    def __init__(self, world):
        self.world = world


class SubsetReactiveCoordinator(ReactiveCoordinator):
    """ReactiveCoordinator restringido a un SUBCONJUNTO de drones (subclase; coordinators.py
    intacto). `set_allowed(mask)` fija a quién puede comandar; act() es la copia literal del
    original con `& allowed` en la free-mask (con allowed todo-True la máscara es idéntica
    -> BIT A BIT el ReactiveCoordinator, verificado en hrl_check 4). La CONFIRMACIÓN de
    equipo sigue siendo de FLOTA (usa TODOS los ACTIVE — conocimiento compartido), solo se
    restringe a quién se comanda; la línea rígida y su gobernador ya son paramétricos en k
    (offsets centrados, r_max=(k−1)/2·spacing)."""

    def __init__(self, world, **kw):
        super().__init__(world, **kw)
        self._allowed = np.ones(world.n_drones, dtype=bool)

    def set_allowed(self, mask: np.ndarray) -> None:
        self._allowed = np.asarray(mask, dtype=bool)

    def act(self, observation: dict | None = None) -> np.ndarray:
        w = self.world
        wp = w.drone_waypoint.copy()
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating) & self._allowed
        idx = np.where(free)[0]
        if idx.size == 0:
            if self._allowed.all():
                return wp        # sin restricción: retorno temprano BIT A BIT el original
            # Con restricción activa (hay guardias), mantiene vivo el estado de percepción
            # aunque no comande a nadie (el latch es de FLOTA; los guardias dependen de él
            # vía analyze_threats). [El original no lo actualiza en este caso — por eso el
            # camino sin restricción replica su retorno temprano exacto.]
            self._confirmed_wolves()
            self._update_anchor(self._confirmed)
            return wp
        herd = self._live_herd()
        conf = self._confirmed_wolves()
        anchor = self._update_anchor(conf)
        if w.phase == "ESCOLTA" and anchor is not None and herd.shape[0] > 0:
            seen = np.asarray(w.wolves, dtype=float)[conf]
            tgt = self._barrier(idx, seen, np.asarray(w.wolves[anchor], dtype=float), herd)
        else:
            tgt = self._patrol(idx, herd if herd.shape[0] > 0 else np.asarray(w.cows, dtype=float))
        wp[idx] = np.clip(tgt, [0.0, 0.0], [w.W, w.H])
        return wp


# ---------------------------------------------------------------------- #
def analyze_threats(world, reactive) -> dict:
    """Amenazas PERCIBIDAS y sus clústeres por rumbo (solo-lectura; reutilizable por la
    regla proporcional, los eventos y las métricas de E0.4). Devuelve dict con:
      pts (M,2) posiciones · is_confirmed (M,) · wolf_idx (M,) índice de lobo o -1 (corzo)
      clusters: lista de arrays de índices en pts (rumbos a <= CLUSTER_SEP_DEG de hueco)
      primario / secundario: índices en clusters (o None) · herd_c
    Contacto = cuerpo no descartado a <= r_detect de un ACTIVE (tipo DESCONOCIDO: los
    corzos cuentan — límite epistémico honesto del bando dron); confirmado = latch de
    equipo (sale de contactos: disjuntos)."""
    w = world
    conf = getattr(reactive, "_confirmed", None)
    act = w.drones[w.drone_state == ACTIVE]
    pts, is_conf, wolf_idx = [], [], []
    if act.shape[0] > 0:
        pos, _is_wolf, gid = w._contact_bodies()
        if pos.shape[0] > 0:
            d = np.linalg.norm(pos[:, None, :] - act[None, :, :], axis=2).min(axis=1)
            for k in np.where(d <= w.r_detect)[0]:
                g = int(gid[k])
                if g < w.n_wolves and conf is not None and conf[g]:
                    continue                        # confirmado: va en su grupo (disjuntos)
                pts.append(pos[k]); is_conf.append(False)
                wolf_idx.append(g if g < w.n_wolves else -1)
    if conf is not None and conf.any():
        for g in np.where(conf)[0]:
            pts.append(w.wolves[g]); is_conf.append(True); wolf_idx.append(int(g))
    m = w.cow_alive & ~w.cow_safe
    herd_c = w.cows[m].mean(axis=0) if m.any() else np.array([w.W / 2.0, w.H / 2.0])
    out = {"pts": np.asarray(pts, dtype=float).reshape(-1, 2),
           "is_confirmed": np.asarray(is_conf, dtype=bool),
           "wolf_idx": np.asarray(wolf_idx, dtype=int),
           "clusters": [], "primario": None, "secundario": None, "herd_c": herd_c}
    n = out["pts"].shape[0]
    if n == 0:
        return out
    rel = out["pts"] - herd_c
    ang = np.arctan2(rel[:, 1], rel[:, 0])
    order = np.argsort(ang, kind="stable")
    a = ang[order]
    gaps = np.diff(np.concatenate([a, a[:1] + 2 * np.pi]))     # huecos circulares
    cuts = np.where(gaps > np.deg2rad(CLUSTER_SEP_DEG))[0]
    if cuts.size == 0:
        clusters = [order]                                     # un solo clúster (círculo entero)
    else:
        clusters = []
        start = int(cuts[-1]) + 1                              # el primer clúster arranca tras el último corte
        seq = np.concatenate([order[start:], order[:start]])
        sizes = np.diff(np.concatenate([[0], cuts + 1]))       # tamaños en el orden angular
        pos0 = 0
        for s in sizes:
            clusters.append(seq[pos0:pos0 + int(s)])
            pos0 += int(s)
    out["clusters"] = clusters
    # PRIMARIO: el clúster del ancla; sin ancla, el más poblado (desempate: menor rumbo).
    anchor = getattr(reactive, "_anchor", None)
    prim = None
    if anchor is not None:
        for ci, cl in enumerate(clusters):
            if np.any(out["wolf_idx"][cl] == int(anchor)):
                prim = ci
                break
    if prim is None:
        prim = max(range(len(clusters)),
                   key=lambda ci: (len(clusters[ci]), -float(ang[clusters[ci]].min())))
    out["primario"] = prim
    rest = [ci for ci in range(len(clusters)) if ci != prim]
    if rest:
        out["secundario"] = max(rest, key=lambda ci: (len(clusters[ci]),
                                                      -float(ang[clusters[ci]].min())))
    return out


class AllocatorCoordinator:
    """FRENTE + GUARDIA sobre los asientos de barrera. `particion` = (n_frente, n_guardia)
    con n_frente + n_guardia == N_SEATS(4); los asientos de GUARDIA son los ÚLTIMOS. El
    manager (o E0.5) puede cambiarla con `set_particion` — surte efecto en el siguiente
    act(). Interfaz de coordinador clásica: act(obs) -> waypoints (n_drones, 2); expone
    `.inner` (el SubsetReactive del frente: latch/ancla de flota) para eventos y
    diagnósticos."""

    def __init__(self, world, particion: tuple[int, int] = (N_SEATS, 0)):
        self.world = world
        self.inner = SubsetReactiveCoordinator(world)
        self._seats = _Seats(world)
        self.set_particion(particion)

    def set_particion(self, particion: tuple[int, int]) -> None:
        nf, ng = int(particion[0]), int(particion[1])
        if nf < 0 or ng < 0 or nf + ng != N_SEATS:
            raise ValueError(f"particion inválida {particion}: nf+ng debe ser {N_SEATS}")
        self.particion = (nf, ng)

    # ------------------------------------------------------------------ #
    def act(self, observation: dict | None = None) -> np.ndarray:
        w = self.world
        seats = self._seats.seats()
        ng = self.particion[1]
        guard = [int(d) for d in seats[N_SEATS - ng:] if d >= 0] if ng > 0 else []
        allowed = np.ones(w.n_drones, dtype=bool)
        allowed[guard] = False                          # el frente no comanda a los guardias
        self.inner.set_allowed(allowed)
        wp = self.inner.act(observation)                # frente (+ mantiene latch de flota)
        if guard:
            free = (w.drone_state == ACTIVE) & (~w.drone_investigating)
            info = analyze_threats(w, self.inner)
            taken: list[np.ndarray] = []
            for d in guard:
                if not free[d]:
                    continue                            # STRANDED/investigador: no se comanda
                tgt = self._guard_target(w, d, info, taken)
                taken.append(tgt)
                wp[d] = np.clip(tgt, [0.0, 0.0], [w.W, w.H])
        return wp

    # ------------------------------------------------------------------ #
    def _guard_target(self, w, d: int, info: dict, taken: list[np.ndarray]) -> np.ndarray:
        """Objetivo del guardia `d`: la amenaza MÁS CERCANA (a él) del clúster SECUNDARIO,
        evitando repetir objetivo entre guardias si hay alternativas (reparto determinista
        por orden de asiento); sin 2º clúster, el octante más abierto."""
        sec = info["secundario"]
        if sec is not None:
            cl = info["clusters"][sec]
            pts = info["pts"][cl]
            order = np.argsort(np.linalg.norm(pts - w.drones[d], axis=1), kind="stable")
            for k in order:                             # la más cercana aún no asignada
                cand = pts[int(k)]
                if not any(np.array_equal(cand, t) for t in taken):
                    return cand
            return pts[int(order[0])]                   # más guardias que amenazas: se comparte
        return self._open_octant_point(w, info)

    def _open_octant_point(self, w, info: dict) -> np.ndarray:
        """Sin clúster secundario: cubrir el OCTANTE MÁS ABIERTO — el centro de octante
        (8 rumbos fijos cada 45°) con rumbo MÁS LEJANO de toda amenaza percibida y de los
        demás drones ACTIVE (desempate: menor índice de octante). Radio = el de patrulla
        (spread + r_notice + DETER_RADIUS: listo para reaccionar)."""
        herd_c = info["herd_c"]
        bearings = []
        if info["pts"].shape[0] > 0:
            rel = info["pts"] - herd_c
            bearings.extend(np.arctan2(rel[:, 1], rel[:, 0]).tolist())
        act = w.drones[w.drone_state == ACTIVE]
        if act.shape[0] > 0:
            rel = act - herd_c
            bearings.extend(np.arctan2(rel[:, 1], rel[:, 0]).tolist())
        centers = np.deg2rad(np.arange(8) * 45.0)
        if bearings:
            b = np.asarray(bearings)
            score = np.array([np.min(np.abs((b - c + np.pi) % (2 * np.pi) - np.pi))
                              for c in centers])
            oct_i = int(np.argmax(score))               # argmax = 1ª ocurrencia (det.)
        else:
            oct_i = 0
        m = w.cow_alive & ~w.cow_safe
        herd = w.cows[m] if m.any() else w.cows
        spread = (float(np.linalg.norm(herd - herd_c, axis=1).max())
                  if herd.shape[0] > 1 else 0.0)
        r = spread + w.r_notice + DETER_RADIUS
        c = centers[oct_i]
        return herd_c + r * np.array([np.cos(c), np.sin(c)])


class ProportionalAllocatorCoordinator(AllocatorCoordinator):
    """REGLA PROPORCIONAL scripted (E0.4): guardias = clip(nº amenazas del clúster
    secundario, 0, GUARD_MAX), re-muestreada cada `frame_skip` pasos (la frontera de los
    envs). Entre fronteras la partición se MANTIENE (sin parpadeo)."""

    def __init__(self, world, frame_skip: int = 5):
        super().__init__(world, particion=(N_SEATS, 0))
        self.frame_skip = int(frame_skip)
        self._countdown = 0
        self._last_step = -1

    def act(self, observation: dict | None = None) -> np.ndarray:
        w = self.world
        step = int(w.step_count)
        if step < self._last_step:
            self._countdown = 0                          # episodio nuevo
            self.set_particion((N_SEATS, 0))
        self._last_step = step
        if self._countdown <= 0:
            self._countdown = self.frame_skip
            info = analyze_threats(w, self.inner)
            n_sec = (len(info["clusters"][info["secundario"]])
                     if info["secundario"] is not None else 0)
            ng = int(np.clip(n_sec, 0, GUARD_MAX))
            self.set_particion((N_SEATS - ng, ng))
        self._countdown -= 1
        return super().act(observation)
