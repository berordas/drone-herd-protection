"""rl_wolf_controller.py — Controlador de lobos APRENDIBLE (el hueco 'learned' hecho carne).

Implementa la interfaz `WolfController.decide(world) -> (v_target, coasting)` (contrato en la
cabecera de wolf_controllers.py) para una política que decide DESDE FUERA (el env de RL): el
env fija la última acción comandada con `set_action(...)` y `decide` la devuelve tal cual,
ya recortada. El mundo (world.py, CONGELADO v2.4) le aplica después el susto + la inercia +
la integración, exactamente igual que al scriptado.

Decisiones de diseño de este paso (documentadas también en DISEÑO.md):

- **CAP de velocidad EN LA FRONTERA (aquí, no en el mundo).** El contrato decía "el mundo
  recortará la salida de un controlador APRENDIDO"; world.py está congelado y NO se toca, así
  que el recorte prometido vive en la frontera del controlador: `decide` recorta la NORMA de
  la velocidad de cada lobo a `world.wolf_speed` ANTES de devolverla -> el mundo nunca ve una
  intención por encima del cap (equivalente a recortarla nada más entrar). Revisable cuando
  se descongele el mundo. Verificado en rl_env_check (test del cap).

- **pack_prey por REGLA FIJA (no lo decide la red).** Como el scriptado, `decide` escribe la
  presa común en el World (contrato compartido: la LEE el 'pin' de la vaca, la instrumentación
  y el render). Regla: el TERNERO vivo no-a-salvo más cercano al centroide del paquete; si no
  hay, la VACA viva no-a-salvo más cercana; si no queda nada, -1/None. Índices según la
  convención existente (índice en `cows` si kind=="adult", en `calves` si "calf").
  (Sin el gating n_min_adult/zonas del scriptado: la política aprendida decide sola si ataca;
  el pin solo necesita saber a quién encarar.)

- **coasting DETERMINISTA (no lo decide la red).** True SOLO si no queda res viva no-a-salvo
  (mismo criterio que el scriptado: `world._targets_exhausted()`); en ese caso devuelve v=0 y
  el mundo desacelera y omite el susto, como en v2.4.
"""

from __future__ import annotations

import numpy as np

from wolf_controllers import WolfController


class RLWolfController(WolfController):
    """Cerebro de lobos comandado desde fuera (el env de RL). `set_action` fija la velocidad
    deseada por SLOT (m/s, hasta n_slots lobos); `decide` recorta por norma a wolf_speed,
    escribe la presa común (regla fija) y devuelve la intención de los n_wolves reales."""

    def __init__(self, n_slots: int = 5):
        self.n_slots = n_slots                      # = wolves_max de CONFIG_V2 (slots de acción)
        self.v_cmd = np.zeros((n_slots, 2))         # última acción comandada (m/s por slot)

    def reset(self) -> None:
        """Acción a cero (se llama en cada reset del env; los lobos arrancan sin intención)."""
        self.v_cmd[:] = 0.0

    def set_action(self, v_cmd: np.ndarray) -> None:
        """Fija la velocidad deseada por slot (m/s, shape (n_slots, 2)). La fija el env en cada
        step y se MANTIENE entre decisiones (frame-skip): el mundo llama a decide() cada paso
        de física y recibe esta misma intención hasta el siguiente set_action."""
        v = np.asarray(v_cmd, dtype=float).reshape(self.n_slots, 2)
        self.v_cmd = v.copy()

    # ------------------------------------------------------------------ #
    def decide(self, world) -> tuple[np.ndarray, bool]:
        self._write_prey(world)                     # efecto lateral, como el scriptado (el pin la lee)

        if world._targets_exhausted():              # nada vivo y no-a-salvo -> desengancha y frena
            return np.zeros((world.n_wolves, 2)), True

        # CAP en la frontera: recorta la NORMA de cada velocidad a wolf_speed (la física del
        # contrato; el mundo congelado no recorta, así que no puede llegarle nada por encima).
        v = self.v_cmd[: world.n_wolves].copy()
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        v *= np.minimum(1.0, world.wolf_speed / np.maximum(norm, 1e-9))
        return v, False

    # ------------------------------------------------------------------ #
    @staticmethod
    def _write_prey(world) -> None:
        """Regla FIJA de presa común (ternero primero): escribe world.pack_prey/pack_prey_kind.
        Ternero vivo no-a-salvo más cercano al centroide del paquete; si no hay, vaca viva
        no-a-salvo más cercana; si no queda res cazable (o no hay lobos), -1/None."""
        w = world
        if w.n_wolves == 0:
            w.pack_prey, w.pack_prey_kind = -1, None
            return
        centroid = w.wolves.mean(axis=0)

        if w.n_calves > 0:
            calf_ok = w.calf_alive & ~w.calf_safe
            if calf_ok.any():
                d = np.linalg.norm(w.calves - centroid, axis=1)
                d[~calf_ok] = np.inf
                w.pack_prey, w.pack_prey_kind = int(np.argmin(d)), "calf"
                return

        cow_ok = w.cow_alive & ~w.cow_safe
        if cow_ok.any():
            d = np.linalg.norm(w.cows - centroid, axis=1)
            d[~cow_ok] = np.inf
            w.pack_prey, w.pack_prey_kind = int(np.argmin(d)), "adult"
            return

        w.pack_prey, w.pack_prey_kind = -1, None
