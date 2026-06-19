"""
coordinators.py — Políticas de coordinación de los drones.

El coordinador recibe una observación y devuelve acciones para los drones.
Es el hueco donde luego enchufaremos MAPPO. De momento, solo el tonto.
"""

from __future__ import annotations
import numpy as np


class DummyCoordinator:
    """Ignora la observación y manda 'todos quietos' (velocidad cero)."""

    def __init__(self, n_drones: int):
        self.n_drones = n_drones

    def act(self, observation: dict) -> np.ndarray:
        return np.zeros((self.n_drones, 2), dtype=float)
