"""residual_drone_coordinator.py — Coordinador de drones RESIDUAL sobre la barrera (MARL, fase drones).

El mismo patrón RPL que funcionó en la fase de lobos (rl/residual_wolf_controller.py), aplicado
al COORDINADOR: la BARRERA REACTIVA v2.6 VIVE DENTRO (una instancia real de ReactiveCoordinator,
intacta — percepción realista, ancla con histéresis, patrulla) y la red aprende solo una
CORRECCIÓN aditiva δ al waypoint de cada PUESTO. El suelo de rendimiento es la barrera completa
(2.74/0/2.82 contra el scriptado v2.6); todo lo que BAJE la severidad es coordinación descubierta.

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
from world import ACTIVE, DETER_RADIUS, STRANDED

from rl.drone_obs import AGENT_OBS_SIZE, N_SEATS, build_drone_agent_obs

DRONE_RESIDUAL_SCALE_DEFAULT = DETER_RADIUS   # m: autoridad de δ (afinable por flag; queda en config.json)


class ResidualDroneCoordinator:
    """Barrera reactiva + corrección aditiva δ por puesto (RPL). Ver cabecera del módulo."""

    def __init__(self, world, model=None, model_path: str | None = None, frame_skip: int = 5,
                 deterministic: bool = True, device: str = "cpu",
                 residual_scale: float | None = None):
        if model is None and model_path is not None:
            from stable_baselines3 import PPO   # import perezoso (torch tarda)
            model = PPO.load(model_path, device=device)
        self.world = world
        self.inner = ReactiveCoordinator(world)      # LA barrera v2.6, viva y entera
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
        frontera — mismo convenio que la pista del script en los lobos). Asiento vacío → fila 0."""
        out = np.zeros((N_SEATS, AGENT_OBS_SIZE), dtype=np.float32)
        st = self.seats()
        for k in range(N_SEATS):
            d = int(st[k])
            if d < 0:
                continue
            base_wp = self.last_base[d] if self.last_base is not None else None
            out[k] = build_drone_agent_obs(world, d, base_wp)
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
