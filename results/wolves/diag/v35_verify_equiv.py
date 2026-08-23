"""v35_verify_equiv.py — comprueba que ReactiveCoordinator(w, drone_spacing=S) es equivalente a
cambiar el default: todos los atributos geometricos derivados coinciden y los waypoints son identicos."""
import sys
import numpy as np

sys.path.insert(0, "/workspace")
import coordinators
from coordinators import ReactiveCoordinator
from world import World, STATIC_DETER_RADIUS, DETER_RADIUS

S = 6.0
w1 = World(seed=3, corzos_max=3, episode_kind="lobos"); w1.reset()
c1 = ReactiveCoordinator(w1, drone_spacing=S)


class Patched(ReactiveCoordinator):
    def __init__(self, world, **kw):
        kw.setdefault("drone_spacing", S)
        super().__init__(world, **kw)


coordinators.ReactiveCoordinator = Patched
w2 = World(seed=3, corzos_max=3, episode_kind="lobos"); w2.reset()
c2 = Patched(w2)

print("drone_spacing:", c1.drone_spacing, c2.drone_spacing)
print("barrier_standoff:", c1.barrier_standoff, c2.barrier_standoff,
      "| formula:", float(np.sqrt(DETER_RADIUS ** 2 - (S / 2) ** 2)))
attrs = [a for a in vars(c1) if not a.startswith("_")]
diff = [a for a in attrs if repr(vars(c1)[a]) != repr(vars(c2)[a])]
print("atributos publicos distintos:", diff)

# corre 400 pasos en paralelo y compara waypoints paso a paso
mx = 0.0
for t in range(400):
    a1 = c1.act(w1.get_observation())
    a2 = c2.act(w2.get_observation())
    mx = max(mx, float(np.abs(a1 - a2).max()))
    w1.step(a1); w2.step(a2)
print("max |wp_kwarg - wp_default| en 400 pasos:", mx)
assert mx == 0.0
print("EQUIVALENCIA OK")
