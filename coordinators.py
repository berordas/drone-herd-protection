"""
coordinators.py — Políticas de coordinación de los drones.

El coordinador recibe una observación y devuelve acciones para los drones.
Es el hueco donde luego enchufaremos MAPPO. De momento, solo el tonto.
"""

from __future__ import annotations
import numpy as np


class DummyCoordinator:
    """Ignora la observación y NO comanda nada (devuelve None) -> los drones MANTIENEN su waypoint, que
    es su posición de partida, así que se quedan efectivamente quietos. El movimiento de drones es una
    capacidad del mundo (command_waypoint); este coordinador simplemente no la usa."""

    def __init__(self, n_drones: int):
        self.n_drones = n_drones

    def act(self, observation: dict | None) -> None:
        return None
