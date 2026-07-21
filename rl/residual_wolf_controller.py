"""residual_wolf_controller.py — Política RESIDUAL sobre el scriptado (RPL, run04).

Cambio de enfoque (decisión del usuario, respaldado por Silver et al. 2018 — Residual Policy
Learning, ver BIBLIOGRAFIA.md): ya NO intentamos que la red aprenda la caza (ni imitando —
plan C, clon ≈0 — ni explorando — run01/run02): el SCRIPTADO VIVE DENTRO del controlador,
INTACTO, y la red aprende solo una CORRECCIÓN aditiva δ encima. El suelo de rendimiento es el
script completo (~2.77/2.80 contra la barrera); todo lo que suba es adaptación anti-dron
descubierta por RL.

Diseño:
- **El script vive dentro**: una instancia REAL de `ScriptedWolfController`. En cada
  `decide(world)` (cada paso de física) se llama `script.decide(world)` con TODA su lógica
  intacta: SU fijación de presa (escribe `pack_prey` como siempre — aquí NO hay presa del
  contrato RL), su histéresis, su coasting, su envolvente. El script RECALCULA cada paso.
- **La corrección**: `v_final = clip_norma(v_script + δ, wolf_speed)`. δ (por lobo, 2D, m/s)
  la decide la red cada `frame_skip=5` pasos de física — la MISMA sincronía de fronteras que
  el env / PolicyWolfController (en evaluación, `SyncedReactiveCoordinator` llama a
  `refresh(world)` en la frontera; en entrenamiento, el env fija δ con `set_delta`) — y se
  MANTIENE entre decisiones. Con δ≡0 hay PASS-THROUGH EXACTO (sin suma ni clip) → el
  controlador es BIT A BIT el scriptado puro (rl_env_check test 9). [El clip con δ≡0 NO era
  un no-op numérico: si la normalización del script deja la norma 1 ulp sobre wolf_speed,
  recortarla introduce una diferencia ~1e-16 que el caos amplifica — destapado por v2.8.]
- **En coasting δ NO se aplica** (pass-through del script, como el susto): sin res cazable el
  paquete coastea a parada; la red no puede impedirlo (paralelo al susto, que es física).
- **Entrada de la red (obs residual, 132)**: la obs de 122 (`build_obs`, rl/obs.py INTACTO) +
  la acción del script normalizada (÷wolf_speed, 10 dims, slots ausentes a 0). Razón: la
  HISTÉRESIS del script es estado oculto que no viaja en la obs (la lección del plan C) —
  darle a la red lo que el script QUIERE hacer es la pista mínima para corregirlo con
  sentido. La pista es el último v_target emitido por el script (el del paso de física
  anterior a la frontera — lo más fresco disponible SIN llamar a decide() fuera de turno,
  que duplicaría sus efectos laterales de fijación); en la primera frontera del episodio
  (el script aún no ha hablado) la pista es 0. La concatenación vive AQUÍ y en el modo
  residual del env — el layout de 122 no cambia.
- **Escala de la corrección**: `residual_scale` (def. `wolf_speed` — autoridad plena, estilo
  RPL): δ = acción_red ∈ [-1,1]^10 × residual_scale. DEBE coincidir entre entrenamiento y
  evaluación (queda en config.json del run).

Modo EVALUACIÓN (autónomo, análogo a PolicyWolfController): pasa `model=`/`model_path=` y usa
`SyncedReactiveCoordinator` — `refresh()` consulta la política en las fronteras. Con
`model=None`, δ≡0 SIEMPRE: es el controlador del SUELO (scriptado puro por el camino
residual; sirve para verificar el cableado con el arnés).
"""

from __future__ import annotations

import numpy as np

from wolf_controllers import ScriptedWolfController, WolfController

from rl.obs import N_WOLF_SLOTS, OBS_SIZE, build_obs

RESIDUAL_OBS_SIZE = OBS_SIZE + N_WOLF_SLOTS * 2   # 122 + 10 = 132 (obs + pista del script)


class ResidualWolfController(WolfController):
    """Scriptado + corrección aditiva δ de una red (RPL). Ver cabecera del módulo."""

    def __init__(self, n_slots: int = N_WOLF_SLOTS, model=None, model_path: str | None = None,
                 frame_skip: int = 5, deterministic: bool = True, device: str = "cpu",
                 residual_scale: float | None = None):
        if model is None and model_path is not None:
            from stable_baselines3 import PPO   # import perezoso (torch tarda)
            model = PPO.load(model_path, device=device)
        self.n_slots = n_slots
        self.script = ScriptedWolfController()      # EL script, vivo y entero
        self.model = model                          # None => δ≡0 (controlador del SUELO)
        self.frame_skip = int(frame_skip)
        self.deterministic = deterministic
        self.residual_scale = residual_scale        # None => wolf_speed del mundo (autoridad plena)
        self.delta = np.zeros((n_slots, 2))         # corrección vigente (m/s), mantenida entre fronteras
        self.last_script_v: np.ndarray | None = None  # último v_target del script (m/s, lobos reales)
        self._countdown = 0

    def reset(self) -> None:
        self.delta[:] = 0.0
        self.last_script_v = None
        self._countdown = 0

    # ------------------------------------------------------------------ #
    def set_delta(self, delta: np.ndarray) -> None:
        """Fija la corrección (m/s, (n_slots,2)). La fija el env en cada frontera (modo
        entrenamiento) y se MANTIENE los frame_skip pasos de física siguientes."""
        self.delta = np.asarray(delta, dtype=float).reshape(self.n_slots, 2).copy()

    def residual_obs(self, world) -> np.ndarray:
        """Obs residual (132, float32) = build_obs(world) + pista del script normalizada.
        Construir SOLO en la frontera (mismo instante que la obs del env — test 7/9)."""
        hint = np.zeros((self.n_slots, 2), dtype=np.float32)
        if self.last_script_v is not None:
            n = min(world.n_wolves, self.n_slots)
            hint[:n] = np.clip(self.last_script_v[:n] / world.wolf_speed, -1.0, 1.0)
        return np.concatenate([build_obs(world), hint.ravel()])

    def refresh(self, world) -> None:
        """Modo EVALUACIÓN: llamar UNA vez por paso de física EN LA FRONTERA (lo hace
        SyncedReactiveCoordinator.act(), la misma maquinaria que PolicyWolfController).
        Cada frame_skip pasos: obs residual → predict → δ; entre medias δ se mantiene.
        Con model=None, δ queda 0 (suelo = scriptado puro por el camino residual)."""
        if self._countdown <= 0:
            if self.model is not None:
                obs = self.residual_obs(world)
                action, _ = self.model.predict(obs, deterministic=self.deterministic)
                a = np.clip(np.asarray(action, dtype=np.float32).reshape(self.n_slots, 2), -1.0, 1.0)
                scale = self.residual_scale if self.residual_scale is not None else world.wolf_speed
                self.set_delta(a * scale)
            self._countdown = self.frame_skip
        self._countdown -= 1

    # ------------------------------------------------------------------ #
    def decide(self, world) -> tuple[np.ndarray, bool]:
        v_script, coasting = self.script.decide(world)   # el script ENTERO: presa/histéresis/envolvente
        self.last_script_v = np.asarray(v_script, dtype=float).copy()
        if coasting:
            return v_script, True                        # pass-through: δ no toca el coasting
        delta = self.delta[: world.n_wolves]
        if not delta.any():
            # δ≡0 ⇒ PASS-THROUGH EXACTO (el SUELO ≡ scriptado BIT A BIT, rl_env_check test 9).
            # El clip de abajo NO es un no-op numérico cuando la normalización del propio script
            # deja la norma 1 ulp por encima de wolf_speed (p.ej. 4.000000000000001): el mundo
            # integra la salida del scriptado SIN recorte, así que recortarla aquí rompía la
            # equivalencia (divergencia float amplificada por el caos — destapado por v2.8).
            return v_script, False
        v = v_script + delta
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        v = v * np.minimum(1.0, world.wolf_speed / np.maximum(norm, 1e-9))
        return v, False
