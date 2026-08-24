"""sim/ — núcleo del simulador: world.py (física congelada, v3.7.1), wolf_controllers.py, coordinators.py,
render.py y baseline.py. Se importan como módulos de nivel superior (`from world import World`): con `pip install -e .`
(pyproject.toml), con PYTHONPATH=/workspace:/workspace/sim (docker/) o vía el shim de los scripts y tests."""
import sys as _sys, pathlib as _pl
_HERE = str(_pl.Path(__file__).resolve().parent)
if _HERE not in _sys.path: _sys.path.insert(0, _HERE)
