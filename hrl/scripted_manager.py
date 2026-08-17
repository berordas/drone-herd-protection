"""hrl/scripted_manager.py — Managers CONSTANTES/FORZADOS y el conmutador de E0.5.

En la Etapa 0 NO hay manager aprendido: estos managers scripted fuerzan opciones para
CALIBRAR el mundo (E0.1-E0.4) y miden el COSTE DE CONMUTACIÓN con cambios forzados de
período fijo (E0.5). Protocolo del lado lobo (WolfOptionLayer): `decide(world, layer) ->
(nombre, params) | None`, consultado por la capa cada frame_skip=5 pasos (la frontera de
los envs); None = mantener. Lado dron: subclases de AllocatorCoordinator que fijan la
partición por reloj. Todo determinista, SIN RNG."""

from __future__ import annotations

from hrl.options_drone import AllocatorCoordinator


class ForcedWolfManager:
    """Opción constante todo el episodio (los brazos CEBO-forzado / MASA-forzado de E0.1,
    E0.3, E0.4)."""

    def __init__(self, option: tuple[str, dict]):
        self.option = (option[0], dict(option[1] or {}))

    def decide(self, world, layer):
        return self.option


class SwitchingWolfManager:
    """E0.5 (lado lobo): conmuta la secuencia de opciones cada `period` ticks (múltiplo de
    frame_skip=5 — la capa muestrea en la frontera de los envs). Emite TIMEOUT_OPCION en
    cada conmutación (el fin de la macro-decisión anterior). El latch wolf_decoy_released
    es MONÓTONO: un CEBO re-entrado tras el show re-entra ya "mostrado" (coste medido por
    el propio experimento)."""

    def __init__(self, sequence: list[tuple[str, dict]], period: int):
        self.sequence = [(n, dict(p or {})) for n, p in sequence]
        self.period = int(period)
        self._last_i: int | None = None
        self._last_step = -1

    def decide(self, world, layer):
        step = int(world.step_count)
        if step < self._last_step:
            self._last_i = None                      # episodio nuevo
        self._last_step = step
        i = (step // self.period) % len(self.sequence)
        if self._last_i is not None and i != self._last_i:
            layer.push_event("TIMEOUT_OPCION", tick=step,
                             de=self.sequence[self._last_i][0], a=self.sequence[i][0])
        self._last_i = i
        return self.sequence[i]


class SwitchingAllocator(AllocatorCoordinator):
    """E0.5 (lado dron): partición forzada por reloj — alterna `partitions` cada `period`
    ticks. La línea del frente conserva su pose entre conmutaciones (el estado vive en el
    SubsetReactive interior); lo que cambia es QUIÉN la ocupa y cuántos guardias hay."""

    def __init__(self, world, partitions=((4, 0), (3, 1), (2, 2)), period: int = 1000):
        super().__init__(world, particion=tuple(partitions[0]))
        self.partitions = [tuple(p) for p in partitions]
        self.period = int(period)

    def act(self, observation=None):
        i = (int(self.world.step_count) // self.period) % len(self.partitions)
        self.set_particion(self.partitions[i])
        return super().act(observation)
