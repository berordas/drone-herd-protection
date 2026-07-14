"""policy_wolf_controller.py — Controlador AUTÓNOMO para EVALUAR una política SB3 entrenada.

`PolicyWolfController` es un `WolfController` que lleva el modelo dentro: en cada DECISIÓN
(cada `frame_skip=5` pasos de física, igual que en entrenamiento) construye la obs con el
builder COMPARTIDO (`rl/obs.py`), llama a `model.predict(obs, deterministic=True)`,
desnormaliza ×`wolf_speed` y delega en `RLWolfController` (herencia, sin duplicar código)
el CAP por norma, la regla de presa ternero-primero y el coasting determinista.

==============  EL INSTANTE DE MUESTREO (por qué existe SyncedReactiveCoordinator)  ==============
En entrenamiento, el env construye la obs en la FRONTERA del step (estado al completarse el
paso de física anterior: nada se ha movido aún). Pero `decide(world)` se llama DENTRO de
`world.step()`, en `_update_wolves` — cuando drones/vacas YA se movieron dt este paso. Si el
controlador muestreara ahí, vería estados desplazados medio paso respecto a los del
entrenamiento → mediría OTRA política (y la equivalencia bit a bit sería imposible).

Solución: el REFRESCO de la acción se hace en la frontera, enganchado al coordinador.
`SyncedReactiveCoordinator` envuelve al `ReactiveCoordinator` congelado y, en cada `act()`
(que el bucle de evaluación llama justo ANTES de `world.step()`, una vez por paso de física
— el mismo instante en que el env construye su obs), llama a `controller.refresh(world)`:
cada `frame_skip` pasos reconstruye obs → predict → `set_action`; entre medias la acción se
MANTIENE. `decide()` solo APLICA la acción vigente. Equivalencia con el env verificada BIT
A BIT en rl_env_check test 7 (mismas semillas y modelo ⇒ misma trayectoria).

Uso (evaluación con el arnés de siempre — ver rl/eval_wolves.py):
    model = PPO.load("/data/wolves/<run>/model.zip", device="cpu")
    evaluate(coordinator_factory=lambda w: SyncedReactiveCoordinator(w),
             wolf_controller_factory=lambda: PolicyWolfController(model=model), ...)

NO toca la factoría `make_wolf_controller` ('learned' sigue en NotImplementedError; el
cableado a `--lobos learned` vendrá cuando haya un modelo bendecido).
"""

from __future__ import annotations

import numpy as np

from coordinators import ReactiveCoordinator

from rl.obs import N_WOLF_SLOTS, build_obs
from rl.rl_wolf_controller import RLWolfController


class PolicyWolfController(RLWolfController):
    """Cerebro de lobos que consulta una política SB3 entrenada (para EVALUACIÓN).

    `model`: instancia SB3 ya cargada (compartible entre episodios: el estado por episodio
    es solo el contador y la acción vigente) — o `model_path` para cargarla aquí (PPO)."""

    def __init__(self, model=None, model_path: str | None = None, frame_skip: int = 5,
                 deterministic: bool = True, device: str = "cpu"):
        super().__init__(N_WOLF_SLOTS)
        if model is None:
            if model_path is None:
                raise ValueError("PolicyWolfController: pasa `model` (SB3 cargado) o `model_path`")
            from stable_baselines3 import PPO   # import perezoso (torch tarda)
            model = PPO.load(model_path, device=device)
        self.model = model
        self.frame_skip = int(frame_skip)
        self.deterministic = deterministic
        self._countdown = 0          # pasos de física hasta la próxima decisión
        self._refreshed = False      # ¿se ha muestreado alguna vez? (guardia anti-mal-uso)

    # ------------------------------------------------------------------ #
    def refresh(self, world) -> None:
        """Llamar UNA vez por paso de física, EN LA FRONTERA (antes de world.step) — lo hace
        SyncedReactiveCoordinator.act(). Cada frame_skip pasos: obs compartida → predict →
        set_action (desnormalizada ×wolf_speed); entre medias la acción se MANTIENE."""
        if self._countdown <= 0:
            obs = build_obs(world)
            action, _ = self.model.predict(obs, deterministic=self.deterministic)
            a = np.clip(np.asarray(action, dtype=np.float32).reshape(N_WOLF_SLOTS, 2), -1.0, 1.0)
            self.set_action(a * world.wolf_speed)   # el CAP por norma lo aplica decide() (heredado)
            self._countdown = self.frame_skip
            self._refreshed = True
        self._countdown -= 1

    def decide(self, world):
        if not self._refreshed:
            raise RuntimeError(
                "PolicyWolfController sin refrescar: la acción se muestrea en la FRONTERA del "
                "step (no dentro de la física). Usa SyncedReactiveCoordinator (o llama a "
                "refresh(world) antes de cada world.step)."
            )
        return super().decide(world)   # cap por norma + pack_prey ternero-primero + coasting


class SyncedReactiveCoordinator:
    """ReactiveCoordinator congelado + SINCRONIZACIÓN del controlador de lobos: en cada act()
    (frontera del paso de física) refresca la política de lobos ANTES de devolver los
    waypoints de la barrera. Requiere que el World lleve un controlador con `refresh`."""

    def __init__(self, world):
        if not hasattr(world.wolf_controller, "refresh"):
            raise TypeError("SyncedReactiveCoordinator: el wolf_controller del World no tiene "
                            "refresh() (esperaba un PolicyWolfController)")
        self.world = world
        self.inner = ReactiveCoordinator(world)

    def act(self, observation=None):
        self.world.wolf_controller.refresh(self.world)
        return self.inner.act(observation)
