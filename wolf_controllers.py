"""
wolf_controllers.py — Cerebro ENCHUFABLE de los lobos (política de movimiento).

Análogo al coordinador de drones (Dummy / Reactive / futuro MARL): separa la POLÍTICA del lobo
(la TÁCTICA: a dónde quiere ir cada lobo) de la FÍSICA del mundo (que la IMPONE). El controlador
SCRIPTADO es el default y es BIT A BIT idéntico a v2.4 (mismas trayectorias, mismas muertes). Esto
prepara la fase RL —lobos APRENDIDOS que burlan la barrera reactiva— sin tocar el comportamiento.

================================  FRONTERA POLÍTICA / FÍSICA  ================================
(Este es el CONTRATO del RL: el controlador DECIDE, el mundo IMPONE.)

POLÍTICA — va al controlador (un cerebro aprendido podrá sustituirlo):
  · fijación / re-fijación de la presa común (matanza excedente) y coasting al agotar objetivos;
  · la táctica de movimiento: standoff del lobo solo, cierre por el cono / flanqueo, rodeo del
    rebaño-obstáculo, ataque ENVOLVENTE (reparto angular), repulsión entre lobos, bordeo de las
    zonas prohibidas (arquear alrededor del establo/central).
  Salida: la INTENCIÓN de movimiento = VELOCIDAD deseada por lobo (n_wolves, 2). Será la acción del RL.

FÍSICA — se queda en el mundo (innegociable para CUALQUIER controlador, aprendido incluido):
  · el CAP de velocidad del lobo (wolf_speed=4.0) y la integración (inercia) del movimiento;
  · el SUSTO por movimiento (v2.4, `_apply_deterrence`): si un dron ACTIVE EMBISTE, el mundo IMPONE
    la huida SOBRE la intención del controlador (la huida sustituye a la caza; un lobo huyendo NO mata
    ni flanquea). El miedo NO es opcional —un lobo aprendido no puede desaprenderlo—;
  · la EVITACIÓN SUAVE del dron estático (obstáculo, dentro del mismo `_apply_deterrence`);
  · las reglas de captura/muerte (`_process_predation`): radio de captura, DAR-LA-CARA (una vaca que
    encara no es capturable de frente / r_face_safe), muerte de la res, estado de cadáveres;
  · la PERCEPCIÓN disponible (qué ve el lobo), la dinámica de vacas/terneros/corzos y la
    detección/confirmación de drones; los clamps de zona (`_push_outside_circle`).

ESTADO COMPARTIDO (decisión de diseño, 2026-07): la PRESA COMÚN (`pack_prey`, `pack_prey_kind`,
`n_refix`, `_ever_committed`, `_wolf_attacking`) VIVE en el World, no en el controlador, porque la
LEEN partes que NO son del lobo: la física de la vaca (el 'PIN' —una vaca solo se planta y encara
si es la presa fijada—), la instrumentación de depredación (`is_pack_prey`) y el render (realce de
la presa + coloreo del cono). El controlador la ESCRIBE (contrato compartido). Cuando llegue el
controlador APRENDIDO —que quizá no fije una presa explícita— tendrá que emitir TAMBIÉN una señal de
'presa objetivo' para que el pin siga funcionando; eso se decide en la fase RL.

============================================  CONTRATO  =====================================
  decide(world) -> (v_target: np.ndarray (n_wolves, 2), coasting: bool)
    v_target : VELOCIDAD deseada por lobo (la intención). El mundo la trata como intención y le
               aplica el susto + la inercia + la integración. El CAP wolf_speed es FÍSICA; el
               scriptado ya emite a tope por construcción (`dir·wolf_speed`), así que el mundo NO
               recorta la salida del scriptado (cap IMPLÍCITO) para mantener el bit a bit; recortará
               la salida de un controlador APRENDIDO (se añade con él y se re-verifica en la fase RL).
    coasting : True SOLO si no queda objetivo cazable (todas muertas o a salvo) y el paquete se
               DESENGANCHA y FRENA (coast a parada). En ese caso el mundo OMITE el susto ese paso
               (no hay velocidad de caza que sobrescribir), EXACTAMENTE como en v2.4. En cualquier
               otro caso False -> el mundo aplica el susto sobre v_target.
"""

from __future__ import annotations
import numpy as np

import world as _wm   # solo para las constantes de módulo del bordeo de zona (valor VIVO; import perezoso -> sin ciclo)


class WolfController:
    """Interfaz base del cerebro de los lobos. Implementa `decide(world) -> (v_target, coasting)`
    (ver el contrato en la cabecera del módulo). El mundo la consume en `_update_wolves`."""

    def decide(self, world) -> tuple[np.ndarray, bool]:
        raise NotImplementedError


class ScriptedWolfController(WolfController):
    """Comportamiento SCRIPTADO de v2.4, movido DETRÁS de la interfaz sin cambiar ni un número
    (bit a bit). Es el controlador por DEFECTO. Corazón del flanqueo: PRESA COMÚN de la manada
    (fijada en t=0 en `reset`, mantenida hasta que deja de ser cazable; MATANZA EXCEDENTE = re-fija
    la más cercana tras matar/refugiarse). Reparto de roles EMERGENTE (repulsión + envolvente ->
    unos de frente, otros a los flancos). Fija/re-fija la presa común y `_wolf_attacking` (estado del
    World) como EFECTO LATERAL; devuelve la velocidad de caza por lobo. NO integra ni aplica el susto
    (eso es física del mundo)."""

    def decide(self, world) -> tuple[np.ndarray, bool]:
        # v2.9 (CEBO DISEÑADO, etapa 1/2 — diseñado, NO emergente): con 2 SUBGRUPOS de spawn cada
        # sector caza SU presa — el 1º la común de SIEMPRE (hace de cebo: dispara/ancla la barrera),
        # el 2º la MÁS LIBRE (máx. distancia al dron ACTIVE más cercano; rompe la convergencia a
        # presa común que anulaba el multi-frente). Con 1 solo grupo (clustered, o sorteo de 1 en
        # grouped) -> el camino v2.8 ÍNTEGRO E INTACTO (bit a bit; face_check 12/12).
        if len(world.wolf_group_sizes) == 2:
            return self._decide_two_sectors(world)
        return self._decide_single(world)

    def _decide_single(self, world) -> tuple[np.ndarray, bool]:
        """Camino de UN solo grupo: el comportamiento v2.4→v2.8 SIN TOCAR (bit a bit)."""
        w = world

        d_wc = np.linalg.norm(w.cows[None, :, :] - w.wolves[:, None, :], axis=2)  # (nw, nc)

        # La presa viene fijada de t=0. Se SUELTA solo si deja de ser cazable (_prey_lost_reason): MUERE o
        # se REFUGIA. En AMBOS casos (matanza excedente) la manada RE-FIJA la res viva no-a-salvo MÁS CERCANA
        # (_recommit_nearest_prey) y sigue cazando -> varias muertes hasta agotar objetivos. n_refix cuenta
        # SOLO las re-fijaciones por REFUGIO (indicador de oscilación); la muerte re-fija pero no es oscilación.
        reason = w._prey_lost_reason()
        if reason is not None:
            w.pack_prey = -1; w.pack_prey_kind = None
            if reason == "refuge":
                w.n_refix += 1
            w._recommit_nearest_prey()   # va a por la siguiente más cercana (tras matar o refugiarse)

        if w._targets_exhausted():
            # Objetivos AGOTADOS (todas las reses muertas o a salvo): el paquete se DESENGANCHA y FRENA. No
            # vuelve al standoff+repulsión, que con la manada agrupada lo haría ORBITAR (tembleque); coastea
            # a parada -> movimiento FIRME (esto mantiene face_check test 3 sano). El mundo integra (v=0 ->
            # desacelera) y OMITE el susto (coasting=True), igual que en v2.4.
            w._wolf_attacking = False
            return np.zeros((w.n_wolves, 2)), True

        if w.pack_prey < 0:
            # Rondar sin comprometerse: standoff amplio a la vaca más cercana de cada lobo.
            nearest = w.cows[d_wc.argmin(axis=1)]
            rel = w.wolves - nearest
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            desired = -rhat * (dist - w.r_standoff)
            w._wolf_attacking = False
        else:
            # El cono que estorba es el de la presa adulta o el de la DEFENSORA del ternero; el lobo
            # CIERRA hacia la presa (ternero o adulta). Para una adulta, cono y presa coinciden.
            prey_pos = w._prey_pos()
            cone_pos, f = w._prey_cone()
            rel = w.wolves - cone_pos                 # ángulo respecto al cono (defensora/adulta)
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            cosphi = rhat @ f
            at_flank = cosphi < np.cos(w.cone_half_angle + w.cone_band)   # fuera del cono (banda muerta)
            close_in = prey_pos - w.wolves            # hacia la PRESA (cerrar a matar)
            cross = f[0] * rhat[:, 1] - f[1] * rhat[:, 0]    # signo de phi -> circular hacia el flanco
            tang = np.where((cross >= 0.0)[:, None],
                            np.column_stack([-rhat[:, 1], rhat[:, 0]]),
                            np.column_stack([rhat[:, 1], -rhat[:, 0]]))
            radial_hold = -rhat * (dist - w.r_face_safe)
            circle = tang + radial_hold
            desired = np.where(at_flank[:, None], close_in, circle)
            w._wolf_attacking = bool(np.any(at_flank & (dist.ravel() <= w.r_face_safe)))

        # --- RODEAR el rebaño (no atravesarlo): si las NO-presa se interponen entre el lobo y la
        #     presa, añade una componente TANGENCIAL (perpendicular a lobo->presa) hacia el lado
        #     OPUESTO al cúmulo -> el lobo ARQUEA alrededor del rebaño hasta el costado de la presa,
        #     en vez de beelinear y atascarse contra las vacas que lo encaran. Tangencial (no solo
        #     repulsión radial, que lo dejaría parado de frente) y comprometido con un lado (sign de s).
        if w.pack_prey >= 0:
            prey_pos = w._prey_pos()
            mask = w.cow_alive & ~w.cow_safe           # solo las CAZABLES son obstáculo (las muertas/refugiadas no)
            if w.pack_prey_kind == "adult":
                mask[w.pack_prey] = False                 # la presa adulta no es obstáculo de sí misma
            herd = w.cows[mask]
            if herd.shape[0] >= 2:
                C = herd.mean(axis=0)                                          # centroide del cúmulo
                R_herd = float(np.linalg.norm(herd - C, axis=1).mean()) + w.wolf_skirt_margin
                to_prey = prey_pos[None, :] - w.wolves
                L = np.linalg.norm(to_prey, axis=1, keepdims=True)
                u = to_prey / np.maximum(L, 1e-9)
                perp = np.column_stack([-u[:, 1], u[:, 0]])
                to_C = C[None, :] - w.wolves
                proj = np.sum(to_C * u, axis=1)                               # avance hasta la proyección de C
                s = np.sum(to_C * perp, axis=1)                               # offset perpendicular de C (con signo)
                between = (proj > 0.0) & (proj < L.ravel())                   # C está ENTRE el lobo y la presa
                gate = between * np.clip(1.0 - np.abs(s) / max(R_herd, 1e-9), 0.0, 1.0)  # cruza el cúmulo
                side = np.where(s >= 0.0, -1.0, 1.0)                          # rodea por el lado OPUESTO a C (commit)
                skirt = w.wolf_skirt_gain * (gate * L.ravel())[:, None] * (side[:, None] * perp)
                desired = desired + skirt

        # --- ATAQUE ENVOLVENTE: reparte los rumbos del paquete en ángulos EQUIESPACIADOS alrededor de la
        #     presa fijada (N lobos -> 2π/N; 4 → ~N/E/S/O, 3 → ~120°), anclado al ángulo medio actual (mínima
        #     rotación). Empuje TANGENCIAL hacia el slot asignado -> los lobos comprometidos se separan a
        #     costados opuestos y SALEN del cono frontal a flancos LIMPIOS. Sin esto, contra una presa CLAVADA
        #     (parada) se apiñan en el cono y "dar la cara" los mantiene a TODOS a raya (a r_face_safe) -> la
        #     presa era invulnerable. La rapidez del slot la fija wolf_envelop_gain. Solo con presa fijada. ---
        if w.pack_prey >= 0 and w.wolf_envelop_gain > 0.0:
            prey_pos = w._prey_pos()
            d_prey = np.linalg.norm(w.wolves - prey_pos, axis=1)
            eng = np.where(d_prey <= w.r_notice)[0]           # lobos comprometidos (cerca de la presa)
            if eng.size >= 2:
                slot = w._envelop_slots(prey_pos, eng)        # ángulo objetivo equiespaciado por lobo
                rel = w.wolves[eng] - prey_pos
                cur = np.arctan2(rel[:, 1], rel[:, 0])
                ang_err = ((slot - cur + np.pi) % (2 * np.pi)) - np.pi   # error angular con signo -> a qué lado rotar
                rhat = rel / np.maximum(d_prey[eng][:, None], 1e-9)
                tang = np.column_stack([-rhat[:, 1], rhat[:, 0]])        # tangente CCW alrededor de la presa
                desired[eng] = desired[eng] + w.wolf_envelop_gain * ang_err[:, None] * tang

        # Repulsión entre lobos cerca del rebaño -> reparto angular alrededor de la presa (pincer).
        engaged_w = d_wc.min(axis=1) <= w.r_notice
        dd_w = w.wolves[:, None, :] - w.wolves[None, :, :]
        ddn = np.linalg.norm(dd_w, axis=2)
        near = (ddn < w.wolf_repulsion_radius) & engaged_w[None, :]
        np.fill_diagonal(near, False)
        rep_units = dd_w / np.maximum(ddn[:, :, None], 1e-9)
        repulsion = (rep_units * near[:, :, None]).sum(axis=1) * engaged_w[:, None] * w.wolf_repulsion_strength
        desired = desired + repulsion

        # --- BORDEAR las ZONAS PROHIBIDAS (refugio/central): un lobo que persigue HACIA una zona se clavaba en
        #     su borde (el clamp lo frena de frente -> atasco radial). Cerca de la frontera añade una TANGENCIAL
        #     -> el lobo ARQUEA por FUERA de la zona hasta el objetivo del otro lado (NO entra: el clamp sigue).
        #     Análogo al bordeo del dron y del rebaño. Se suma a `desired` (antes de normalizar) -> solo redirige,
        #     no acelera. Gateado por escort_enabled (en combate la presa no se refugia -> face_check bit a bit).
        if w.escort_enabled:
            dnorm = np.linalg.norm(desired, axis=1, keepdims=True)
            vd = desired / np.maximum(dnorm, 1e-9)               # dirección de caza por lobo
            for circle in (w.safe_zone, w.central_station):
                C, rz = circle[:2], circle[2]
                to_zone = C - w.wolves                           # lobo -> centro de la zona
                d = np.linalg.norm(to_zone, axis=1)
                band = rz + _wm.WOLF_ZONE_SKIRT_BAND
                near_z = (d < band) & (d > 1e-9)
                if not near_z.any():
                    continue
                u = to_zone / np.maximum(d[:, None], 1e-9)       # hacia el centro de la zona
                block = np.clip(np.sum(vd * u, axis=1), 0.0, 1.0)            # 1 = la caza apunta de frente a la zona
                fall = np.clip((band - d) / _wm.WOLF_ZONE_SKIRT_BAND, 0.0, 1.0) * near_z  # 1 en el borde, 0 a `band`
                perp = np.column_stack([-u[:, 1], u[:, 0]])
                side = np.where(np.sum(perp * vd, axis=1) >= 0.0, 1.0, -1.0)  # lado que conserva el avance (det.)
                tang = perp * side[:, None]                                   # tangente unitaria que rodea la zona
                desired = desired + _wm.WOLF_ZONE_SKIRT_GAIN * (fall * block * dnorm.ravel())[:, None] * tang

        # Dirección deseada -> velocidad objetivo a rapidez plena (el "impulso de caza" hacia la presa/standoff).
        # (El CAP wolf_speed es física; aquí el scriptado ya emite a tope por construcción -> el mundo NO recorta.)
        dn = np.linalg.norm(desired, axis=1, keepdims=True)
        desired_dir = np.where(dn > 1e-9, desired / np.maximum(dn, 1e-9), 0.0)
        v_target = desired_dir * w.wolf_speed
        return v_target, False

    # ------------------------------------------------------------------ #
    # v2.9 — CEBO DISEÑADO (etapa 1/2): dos sectores, dos presas.
    # ------------------------------------------------------------------ #
    def _decide_two_sectors(self, world) -> tuple[np.ndarray, bool]:
        """Camino de DOS subgrupos de spawn (v2.9): la MISMA táctica por-sector que el camino único
        (standoff / cono-flanqueo / rodeo / envolvente — vía _sector_desired), con la presa de CADA
        sector: sector 1 = pack_prey (maquinaria clásica: fijación t=0, recommit más-cercana), sector
        2 = pack_prey2 (la MÁS LIBRE; recommit re-evalúa la más libre). Repulsión entre lobos y bordeo
        de zonas siguen siendo GLOBALES (idénticos al camino único). n_refix cuenta las re-fijaciones
        por refugio de AMBOS sectores (mismo significado: oscilación por refugio)."""
        w = world

        d_wc = np.linalg.norm(w.cows[None, :, :] - w.wolves[:, None, :], axis=2)  # (nw, nc)

        # Gestión de presa POR SECTOR (misma semántica de suelta/re-fijación que el camino único).
        reason = w._prey_lost_reason()
        if reason is not None:
            w.pack_prey = -1; w.pack_prey_kind = None
            if reason == "refuge":
                w.n_refix += 1
            w._recommit_nearest_prey()
        reason2 = w._prey2_lost_reason()
        if reason2 is not None:
            w.pack_prey2 = -1; w.pack_prey2_kind = None
            if reason2 == "refuge":
                w.n_refix += 1
            w._try_commit_prey2()          # re-fija la MÁS LIBRE en ese instante (matanza excedente)

        if w._targets_exhausted():
            w._wolf_attacking = False
            return np.zeros((w.n_wolves, 2)), True

        n1 = int(w.wolf_group_sizes[0])
        s1 = np.arange(0, n1)
        s2 = np.arange(n1, w.n_wolves)
        desired = np.zeros((w.n_wolves, 2))

        # --- v3.0 (CEBO PERFECTO, pieza 3): TIMING PROGRAMADO del cebo (scripted, NO emergente) ---
        # Solo en modo cebo (wolf_decoy_size fijado). El sector-CEBO (1º) ESPERA merodeando —fuera del
        # alcance de confirmación, SIN congelarse— hasta que el ASALTO (2º) está a <= assault_trigger_dist
        # de su presa; ENTONCES se lanza (se deja confirmar y dispara/ancla la barrera) -> ambos frentes
        # llegan acompasados. El latch vive en el World (wolf_decoy_released, patrón pack_prey: el
        # controlador lo escribe, el reset del World lo reinicia; visible para instrumentación/render).
        decoy_waiting = False
        if w.wolf_decoy_size is not None and not w.wolf_decoy_released:
            if w.pack_prey2 >= 0 and s2.size > 0:
                p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
                if float(np.linalg.norm(w.wolves[s2].mean(axis=0) - p2)) <= w.assault_trigger_dist:
                    w.wolf_decoy_released = True          # DISPARO: el cebo avanza desde este paso
                else:
                    decoy_waiting = True
            else:
                w.wolf_decoy_released = True              # sin presa del asalto: nada que acompasar

        if decoy_waiting:
            atk1 = False
            self._decoy_prowl(w, s1, desired)
        else:
            atk1 = self._sector_desired(w, s1, w.pack_prey, w.pack_prey_kind, d_wc, desired)
        atk2 = self._sector_desired(w, s2, w.pack_prey2, w.pack_prey2_kind, d_wc, desired)
        w._wolf_attacking = bool(atk1 or atk2)

        # Repulsión entre lobos cerca del rebaño (GLOBAL, idéntica al camino único).
        engaged_w = d_wc.min(axis=1) <= w.r_notice
        dd_w = w.wolves[:, None, :] - w.wolves[None, :, :]
        ddn = np.linalg.norm(dd_w, axis=2)
        near = (ddn < w.wolf_repulsion_radius) & engaged_w[None, :]
        np.fill_diagonal(near, False)
        rep_units = dd_w / np.maximum(ddn[:, :, None], 1e-9)
        repulsion = (rep_units * near[:, :, None]).sum(axis=1) * engaged_w[:, None] * w.wolf_repulsion_strength
        desired = desired + repulsion

        # BORDEAR las ZONAS PROHIBIDAS (GLOBAL, idéntico al camino único).
        if w.escort_enabled:
            dnorm = np.linalg.norm(desired, axis=1, keepdims=True)
            vd = desired / np.maximum(dnorm, 1e-9)
            for circle in (w.safe_zone, w.central_station):
                C, rz = circle[:2], circle[2]
                to_zone = C - w.wolves
                d = np.linalg.norm(to_zone, axis=1)
                band = rz + _wm.WOLF_ZONE_SKIRT_BAND
                near_z = (d < band) & (d > 1e-9)
                if not near_z.any():
                    continue
                u = to_zone / np.maximum(d[:, None], 1e-9)
                block = np.clip(np.sum(vd * u, axis=1), 0.0, 1.0)
                fall = np.clip((band - d) / _wm.WOLF_ZONE_SKIRT_BAND, 0.0, 1.0) * near_z
                perp = np.column_stack([-u[:, 1], u[:, 0]])
                side = np.where(np.sum(perp * vd, axis=1) >= 0.0, 1.0, -1.0)
                tang = perp * side[:, None]
                desired = desired + _wm.WOLF_ZONE_SKIRT_GAIN * (fall * block * dnorm.ravel())[:, None] * tang

        dn = np.linalg.norm(desired, axis=1, keepdims=True)
        desired_dir = np.where(dn > 1e-9, desired / np.maximum(dn, 1e-9), 0.0)
        v_target = desired_dir * w.wolf_speed
        return v_target, False

    def _decoy_prowl(self, w, sel: np.ndarray, desired: np.ndarray) -> None:
        """v3.0/v3.1 (pieza 3): MERODEO del sector-CEBO mientras espera el disparo — acecho LATERAL
        creíble, NO congelado y SIN acercarse: componente TANGENCIAL alrededor del rebaño (lado
        determinista por lobo) + evasión del dron ACTIVE más cercano. Determinista, SIN RNG.

        v3.1 (diagnóstico 0b): en v3.0 el cebo BAJABA de r_detect mientras "esperaba" (nace a ~114-135
        del dron más cercano y el empuje mixto tardaba) -> se convertía en EL contacto, el INVESTIGADOR
        lo cazaba (15 vs 4 m/s, hasta 0.3-2 m) y lo confirmaba con el asalto aún a 238-440 m de su
        presa (5/15 episodios). Blindaje en dos anillos:
          - dmin < decoy_hold_dist (=130, r_detect + 30 de buffer de evasión): HUIDA RADIAL PURA a
            velocidad plena (nada de acecho: salir del alcance es lo único que importa);
          - hold <= dmin < hold + DECOY_HOLD_BAND: mezcla acecho + empuje creciente (frontera suave).
        La normalización global de _decide_two_sectors lo lleva a wolf_speed."""
        DECOY_HOLD_BAND = 20.0                        # m: banda de holgura del merodeo (empuja antes de invadir)
        wolves = w.wolves[sel]
        herd_c = w.cows[w.cow_alive].mean(axis=0) if w.cow_alive.any() else np.array([w.W / 2.0, w.H / 2.0])
        rel = wolves - herd_c
        rn = np.linalg.norm(rel, axis=1, keepdims=True)
        rhat = rel / np.maximum(rn, 1e-9)
        side = np.where((sel % 2 == 0)[:, None], 1.0, -1.0)          # lado determinista (sin RNG)
        tang = side * np.column_stack([-rhat[:, 1], rhat[:, 0]])     # acecho lateral (orbita el rebaño)
        des = tang.copy()
        act = w.drones[w.drone_state == _wm.ACTIVE]
        if act.shape[0] > 0:
            d = np.linalg.norm(wolves[:, None, :] - act[None, :, :], axis=2)   # (k, nd)
            j = d.argmin(axis=1)
            dmin = d[np.arange(sel.size), j]
            away = wolves - act[j]
            away = away / np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-9)
            push = np.clip((w.decoy_hold_dist + DECOY_HOLD_BAND - dmin) / DECOY_HOLD_BAND, 0.0, 1.0)
            des = des + 2.0 * push[:, None] * away    # banda exterior: el alejarse domina al acecho
            inside = dmin < w.decoy_hold_dist         # anillo interior: HUIDA PURA (v3.1)
            des = np.where(inside[:, None], away, des)
        desired[sel] = des

    def _sector_desired(self, w, sel: np.ndarray, prey_idx: int, prey_kind: str | None,
                        d_wc: np.ndarray, desired: np.ndarray) -> bool:
        """Rellena desired[sel] con la táctica del camino único aplicada al SECTOR contra SU presa:
        sin presa -> rondar en standoff; con presa -> cono/flanqueo + rodeo del rebaño + envolvente
        (slots equiespaciados ENTRE LOS LOBOS DEL SECTOR — cada sector envuelve a su presa).
        Devuelve el flag 'attacking' del sector. Mismas fórmulas que _decide_single, indexadas."""
        if sel.size == 0:
            return False
        wolves = w.wolves[sel]
        if prey_idx < 0:
            nearest = w.cows[d_wc[sel].argmin(axis=1)]
            rel = wolves - nearest
            dist = np.linalg.norm(rel, axis=1, keepdims=True)
            rhat = rel / np.maximum(dist, 1e-9)
            desired[sel] = -rhat * (dist - w.r_standoff)
            return False

        prey_pos = w._prey_pos_of(prey_idx, prey_kind)
        cone_pos, f = w._prey_cone_of(prey_idx, prey_kind)
        rel = wolves - cone_pos
        dist = np.linalg.norm(rel, axis=1, keepdims=True)
        rhat = rel / np.maximum(dist, 1e-9)
        cosphi = rhat @ f
        at_flank = cosphi < np.cos(w.cone_half_angle + w.cone_band)
        close_in = prey_pos - wolves
        cross = f[0] * rhat[:, 1] - f[1] * rhat[:, 0]
        tang = np.where((cross >= 0.0)[:, None],
                        np.column_stack([-rhat[:, 1], rhat[:, 0]]),
                        np.column_stack([rhat[:, 1], -rhat[:, 0]]))
        radial_hold = -rhat * (dist - w.r_face_safe)
        circle = tang + radial_hold
        des = np.where(at_flank[:, None], close_in, circle)
        attacking = bool(np.any(at_flank & (dist.ravel() <= w.r_face_safe)))

        # RODEAR el rebaño (misma fórmula; la presa adulta PROPIA no es obstáculo de sí misma —
        # la del otro sector SÍ lo es para este sector, como cualquier otra res cazable).
        mask = w.cow_alive & ~w.cow_safe
        if prey_kind == "adult":
            mask[prey_idx] = False
        herd = w.cows[mask]
        if herd.shape[0] >= 2:
            C = herd.mean(axis=0)
            R_herd = float(np.linalg.norm(herd - C, axis=1).mean()) + w.wolf_skirt_margin
            to_prey = prey_pos[None, :] - wolves
            L = np.linalg.norm(to_prey, axis=1, keepdims=True)
            u = to_prey / np.maximum(L, 1e-9)
            perp = np.column_stack([-u[:, 1], u[:, 0]])
            to_C = C[None, :] - wolves
            proj = np.sum(to_C * u, axis=1)
            s = np.sum(to_C * perp, axis=1)
            between = (proj > 0.0) & (proj < L.ravel())
            gate = between * np.clip(1.0 - np.abs(s) / max(R_herd, 1e-9), 0.0, 1.0)
            side = np.where(s >= 0.0, -1.0, 1.0)
            skirt = w.wolf_skirt_gain * (gate * L.ravel())[:, None] * (side[:, None] * perp)
            des = des + skirt

        # ENVOLVENTE del SECTOR alrededor de SU presa (slots entre los comprometidos del sector).
        if w.wolf_envelop_gain > 0.0:
            d_prey = np.linalg.norm(wolves - prey_pos, axis=1)
            eng_local = np.where(d_prey <= w.r_notice)[0]
            if eng_local.size >= 2:
                eng = sel[eng_local]
                slot = w._envelop_slots(prey_pos, eng)
                rel_e = w.wolves[eng] - prey_pos
                cur = np.arctan2(rel_e[:, 1], rel_e[:, 0])
                ang_err = ((slot - cur + np.pi) % (2 * np.pi)) - np.pi
                rhat_e = rel_e / np.maximum(d_prey[eng_local][:, None], 1e-9)
                tang_e = np.column_stack([-rhat_e[:, 1], rhat_e[:, 0]])
                des[eng_local] = des[eng_local] + w.wolf_envelop_gain * ang_err[:, None] * tang_e

        desired[sel] = des
        return attacking


def make_wolf_controller(policy: str = "scripted") -> WolfController:
    """Selección análoga a `--coordinador` de los drones. 'scripted' = comportamiento v2.4 (default).
    'learned' = hueco para el controlador APRENDIDO por RL (pendiente; lanza NotImplementedError)."""
    if policy == "scripted":
        return ScriptedWolfController()
    if policy == "learned":
        raise NotImplementedError(
            "controlador de lobos APRENDIDO (RL): pendiente de la fase RL "
            "(entrenar lobos que burlen la barrera reactiva y congelarlos)."
        )
    raise ValueError("wolf_policy desconocido: %r (usa 'scripted' | 'learned')" % (policy,))
