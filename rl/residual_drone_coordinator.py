"""residual_drone_coordinator.py — Coordinador de drones RESIDUAL sobre la barrera (MARL, fase drones).

El mismo patrón RPL que funcionó en la fase de lobos (rl/residual_wolf_controller.py), aplicado
al COORDINADOR. run02 (sobre el mundo terminado v3.4): dentro vive la barrera v3.4 SIN el
gobernador de cuerpo rígido (`NonRigidBarrier`, abajo — cambio de diseño 1; percepción honesta
v2.8, ancla con histéresis, trinquete v3.3, anillo de 50 y patrulla INTACTOS) y la red aprende
solo una CORRECCIÓN aditiva δ al waypoint de cada PUESTO, con autoridad PLENA por dron (sin
gobernador que congele la pose al sacar un dron de su ranura). El suelo de rendimiento es esa
barrera sin rigidez con δ≡0 — RE-MEDIDO con el arnés (no tiene por qué ser el 2.68/0/2.77 de la
rígida); todo lo que BAJE la severidad respecto a ese suelo es coordinación descubierta.

Diseño:
- **AGENTE = PUESTO (asiento k = 0..3), no el dron físico**: el asiento k lo ocupa el k-ésimo
  dron EN ESTACIÓN (ACTIVE o STRANDED, por orden de índice; `seats()`). Los relevos de batería
  cambian QUÉ dron ocupa el asiento (hand-off), pero el puesto persiste — la política es
  COMPARTIDA (una red, cada puesto la evalúa con SU obs local), así que el intercambio es benigno.
- **La corrección**: `wp_final[d] = clip_campo(wp_base[d] + δ_k)` SOLO para los drones
  COMANDABLES: `ACTIVE & ~investigating` (v3.0: el que anunció relevo sigue comandable) — LA MÁSCARA ES LOAD-BEARING: el mundo
  solo protege al investigador y al relevo (world._apply_drone_actions); un δ sobre un
  RETURNING/CHARGING lo desviaría y rompería el ciclo de carga. δ (metros, por puesto) la decide
  la red cada `frame_skip=5` pasos de física y se MANTIENE entre fronteras (countdown), la misma
  sincronía que toda la fase RL.
- **Escala de δ**: `residual_scale` (def. `DETER_RADIUS`=20 m): un radio de disuasión de
  autoridad mueve un puesto fuera del frente con intención sin tele-transportarlo; afinable por
  flag y registrado en config.json (DEBE coincidir entre entrenamiento y evaluación).
- **SUELO por construcción**: con `model=None` y sin `set_delta`, `act()` DELEGA en la barrera
  sin tocar un solo float (ni suma ni clip) → bit a bit ReactiveCoordinator (rl_env_check
  test 10b). Es el controlador del suelo (`drone_eval.py --floor`).
- **Modo EVALUACIÓN** (con `model=`/`model_path=`): este coordinador ES a quien llama el arnés
  cada paso (`act()`), así que se auto-sincroniza con su countdown — NO hace falta el
  SyncedReactiveCoordinator de los lobos (aquel existía porque la política de LOBOS necesitaba
  refresco externo en la frontera). En la frontera: obs por puesto (pista = waypoint base del
  último paso de física, `last_base` — el análogo exacto del last_script_v de los lobos; ceros
  en la primera frontera) → UN predict por lotes (4, AGENT_OBS_SIZE) → δ.
- **Modo ENTRENAMIENTO**: el env fija δ con `set_delta()` (ya en metros) y llama a `act()` cada
  paso de física — mismo camino de código que la evaluación (train ≡ serve).
"""

from __future__ import annotations

import numpy as np

from coordinators import ReactiveCoordinator
from world import ACTIVE, DETER_RADIUS, STATIC_DETER_RADIUS, STRANDED

from rl.drone_obs import AGENT_OBS_SIZE, N_SEATS, build_drone_agent_obs

DRONE_RESIDUAL_SCALE_DEFAULT = DETER_RADIUS   # m: autoridad de δ (afinable por flag; queda en config.json)


class NonRigidBarrier(ReactiveCoordinator):
    """Barrera v3.4 SIN el gobernador de cuerpo rígido — CAMBIO DE DISEÑO 1 de run02 (decisión
    del usuario). SOLO para el residual: `coordinators.py` (la barrera clásica congelada) NO se
    toca; esta subclase vive en rl/ y redefine únicamente la colocación de la pose en la rama
    CLEAN de `_barrier`.

    QUÉ QUITA: el lazo del gobernador v3.4 (paso_pose = max(0, DRONE_MAX_SPEED·dt − err_max) con
    la pose interpolada al ritmo del MÁS REZAGADO). Aquí la pose SALTA al objetivo cada paso:
    ranuras = c_des + off_i·perp(u), como v3.2/v3.3 pero sin cierres locales (waypoint SIEMPRE
    de ranura). El vuelo físico (DRONE_MAX_SPEED/ACCEL) sigue limitando a cada dron — lo que
    desaparece es el ACOPLE entre drones, no la física.

    POR QUÉ (documentado para la memoria): con el gobernador, la δ de la red LUCHA contra la
    base — si la red saca un dron de su ranura (repartirse a otro frente, cerrar la gotera
    central), su error de estación err_max crece y la POSE ENTERA SE CONGELA (paso_pose→0): mover
    UN dron paraliza el avance de TODOS. La rigidez era para que la barrera CLÁSICA no se
    deformara feo (v3.4); al MARL le estorba — necesita autoridad plena POR DRON para romper la
    formación. QUÉ CONSERVA (el suelo sigue siendo la barrera de verdad): percepción honesta
    v2.8 (solo confirmados, ancla con histéresis), TRINQUETE del avance v3.3 (aim monótono),
    suelo del standoff (línea siempre delante de las vacas), anillo de max_advance_from_herd=50,
    sobre-apuntado +STATIC_DETER_RADIUS, offsets fijos de ranura, PENETRADO y patrulla: INTACTOS
    (heredados). Con δ≡0 este es el SUELO de run02 — se RE-MIDE con el arnés (NO es el 2.68/2.77
    de la rígida; la rigidez afectaba al comportamiento) y ese número es el termómetro del run."""

    def _barrier(self, idx: np.ndarray, wolves: np.ndarray, anchor_pos: np.ndarray,
                 herd: np.ndarray) -> np.ndarray:
        k = idx.size
        pack_c = anchor_pos
        herd_c = herd.mean(axis=0)
        herd_r = float(np.linalg.norm(herd - herd_c, axis=1).max()) if herd.shape[0] > 1 else 0.0
        if float(np.linalg.norm(pack_c - herd_c)) <= herd_r:      # PENETRADO: igual que la v3.4
            return self._cover_engaged(idx, wolves, herd)
        # Rama CLEAN de v3.4 (eje al ancla + trinquete + suelo + anillo), SIN el gobernador.
        u = pack_c - herd_c
        d_anchor = float(np.linalg.norm(u))
        u = u / max(d_anchor, 1e-9)
        proj_front = float(((herd - herd_c) @ u).max())
        floor = proj_front + self.barrier_standoff
        self._aim_out = max(self._aim_out, min(d_anchor + STATIC_DETER_RADIUS,
                                               self.max_advance_from_herd))
        aim = max(self._aim_out, floor)
        c_des = herd_c + u * aim
        # Pose = el OBJETIVO, directamente (sin interpolar al más rezagado). Se escribe el estado
        # de pose para que la instrumentación externa (diagnósticos que detectan la rama CLEAN
        # por _pose_last_step) siga funcionando sobre esta variante.
        self._pose_c = c_des.copy()
        self._pose_u = u.copy()
        self._pose_last_step = int(self.world.step_count)
        perp = np.array([-u[1], u[0]])
        k_off = (np.arange(k) - (k - 1) / 2.0) * self.drone_spacing   # offsets FIJOS (v3.2)
        slots = c_des[None, :] + k_off[:, None] * perp[None, :]
        return self._assign(idx, slots, perp)


class ResidualDroneCoordinator:
    """Barrera SIN rigidez (NonRigidBarrier) + corrección aditiva δ por puesto (RPL). Ver
    cabecera del módulo; run02 = cambios de diseño 1 (sin gobernador) y 2 (obs con contactos y
    confirmados)."""

    def __init__(self, world, model=None, model_path: str | None = None, frame_skip: int = 5,
                 deterministic: bool = True, device: str = "cpu",
                 residual_scale: float | None = None):
        if model is None and model_path is not None:
            from stable_baselines3 import PPO   # import perezoso (torch tarda)
            model = PPO.load(model_path, device=device)
        self.world = world
        self.inner = NonRigidBarrier(world)          # la barrera v3.4 SIN rigidez (run02, cambio 1)
        self.model = model                           # None => δ≡0 (controlador del SUELO)
        self.frame_skip = int(frame_skip)
        self.deterministic = deterministic
        self.residual_scale = (residual_scale if residual_scale is not None
                               else DRONE_RESIDUAL_SCALE_DEFAULT)
        self.delta = np.zeros((N_SEATS, 2))          # corrección vigente (m), mantenida entre fronteras
        self._delta_active = False                   # False y model=None => delegación PURA (suelo bit a bit)
        self.last_base = None                        # waypoints base del último paso de física (pista de la obs)
        self._countdown = 0

    # ------------------------------------------------------------------ #
    def seats(self) -> np.ndarray:
        """(N_SEATS,) índice de DRON que ocupa cada puesto: los drones EN ESTACIÓN (ACTIVE o
        STRANDED), por orden de índice; -1 = asiento vacío. Normalmente son exactamente 4; en el
        hand-off de un relevo el índice del asiento cambia de dron (el puesto persiste)."""
        w = self.world
        on_station = np.where((w.drone_state == ACTIVE) | (w.drone_state == STRANDED))[0]
        out = np.full(N_SEATS, -1, dtype=int)
        n = min(N_SEATS, on_station.size)
        out[:n] = on_station[:n]
        return out

    def set_delta(self, delta: np.ndarray) -> None:
        """Fija δ (METROS, (N_SEATS,2)) — la llama el env en cada frontera (modo entrenamiento);
        se MANTIENE los frame_skip pasos siguientes."""
        self.delta = np.asarray(delta, dtype=float).reshape(N_SEATS, 2).copy()
        self._delta_active = True

    def agent_obs(self, world) -> np.ndarray:
        """(N_SEATS, AGENT_OBS_SIZE) float32: obs compuesta por puesto en la FRONTERA. La pista
        base_wp es el waypoint base del último paso de física (`last_base`; ceros en la primera
        frontera — mismo convenio que la pista del script en los lobos). Asiento vacío → fila 0.
        run02 (cambio 2): pasa la máscara de CONFIRMADOS de la barrera interior (equipo con
        memoria, UNA fuente de verdad — el mismo latch v2.8 que usa la base; None al arrancar el
        episodio = nada confirmado) para que la obs separe contactos y confirmados."""
        out = np.zeros((N_SEATS, AGENT_OBS_SIZE), dtype=np.float32)
        st = self.seats()
        conf = self.inner._confirmed                 # latch de equipo de la barrera (o None)
        for k in range(N_SEATS):
            d = int(st[k])
            if d < 0:
                continue
            base_wp = self.last_base[d] if self.last_base is not None else None
            out[k] = build_drone_agent_obs(world, d, base_wp, confirmed=conf)
        return out

    # ------------------------------------------------------------------ #
    def act(self, observation=None) -> np.ndarray:
        """Waypoints (n_drones,2) = barrera + δ enmascarada. Interfaz idéntica a la de los
        coordinadores clásicos (la llama el arnés/el env UNA vez por paso de física)."""
        w = self.world
        if self.model is not None:                    # modo evaluación: refresco en la frontera
            if self._countdown <= 0:
                obs = self.agent_obs(w)               # pista = base del paso ANTERIOR (train ≡ serve)
                action, _ = self.model.predict(obs, deterministic=self.deterministic)
                a = np.clip(np.asarray(action, dtype=np.float32).reshape(N_SEATS, 2), -1.0, 1.0)
                self.set_delta(a * self.residual_scale)
                self._countdown = self.frame_skip
            self._countdown -= 1
        base = self.inner.act(observation)
        self.last_base = base.copy()
        if not self._delta_active:
            return base                               # SUELO: delegación pura (bit a bit la barrera)
        # v3.0 (pieza 5): el dron que anunció relevo SIGUE comandable (el mundo ya no lo clava) ->
        # sale de la exclusión; la máscara queda ACTIVE & ~investigating (== free-mask del mundo).
        mask = ((w.drone_state == ACTIVE) & ~w.drone_investigating)
        st = self.seats()
        for k in range(N_SEATS):
            d = int(st[k])
            if d >= 0 and mask[d]:                    # LA MÁSCARA: solo drones comandables
                base[d] = np.clip(base[d] + self.delta[k], [0.0, 0.0], [w.W, w.H])
        return base
