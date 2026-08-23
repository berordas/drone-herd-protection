import sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from world import ACTIVE, READY, CHARGING, INCOMING, RETURNING

def make(seed):
    w = build_world(seed, "corzos")
    c = ReactiveCoordinator(w)
    w.reset()
    return w, c

wa, ca = make(1)
wb, cb = make(1)
for t in range(6000):
    wa.step(ca.act(wa.get_observation()))
    wb.step(cb.act(wb.get_observation()))
    if wa.n_corzos > 0 and bool(wa.corzo_dismissed.all()) and not wa.drone_investigating.any():
        break
res = np.where((wa.drone_state == CHARGING) | (wa.drone_state == READY))[0]
wa.battery[res] = 1.0; wb.battery[res] = 1.0
wa.step(ca.act(wa.get_observation())); wb.step(cb.act(wb.get_observation()))
quiet = 0
for _ in range(8000):
    wa.step(ca.act(wa.get_observation())); wb.step(cb.act(wb.get_observation()))
    act = np.where((wa.drone_state == ACTIVE) & ~wa.drone_investigating)[0]
    err = float(np.linalg.norm(wa.drones[act] - wa.drone_waypoint[act], axis=1).max()) if act.size else 1e9
    quiet = quiet + 1 if err < 0.5 else 0
    if quiet >= 50:
        break
print("regimen en t=", wa.step_count, "estados:", wa.drone_state.tolist())
low = int(np.where(wa.drone_state == ACTIVE)[0][0])
wa.battery[low] = wa.announce_threshold - 0.01
others = [i for i in np.where(wa.drone_state == ACTIVE)[0] if i != low]
print("low:", low, "others:", others)
for t in range(2500):
    wa.step(ca.act(wa.get_observation())); wb.step(cb.act(wb.get_observation()))
    if not np.array_equal(wa.drone_waypoint[others], wb.drone_waypoint[others]):
        d = np.abs(wa.drone_waypoint[others] - wb.drone_waypoint[others]).max(axis=1)
        j = int(np.argmax(d))
        print(f"DIVERGE t=+{t} dron {others[j]}: A={wa.drone_waypoint[others[j]]} B={wb.drone_waypoint[others[j]]} |d|={d[j]:.4f}")
        print("  estados A:", wa.drone_state.tolist(), "hold A:", wa.drone_relief_hold.tolist())
        print("  estados B:", wb.drone_state.tolist(), "hold B:", wb.drone_relief_hold.tolist())
        print("  inv A:", wa.drone_investigating.tolist(), "inv B:", wb.drone_investigating.tolist())
        print("  pos A[others]:", wa.drones[others].round(2).tolist())
        print("  pos B[others]:", wb.drones[others].round(2).tolist())
        print("  low pos A:", wa.drones[low].round(2).tolist(), "B:", wb.drones[low].round(2).tolist())
        da = np.abs(wa.drones[others] - wb.drones[others]).max()
        print("  max dif posicion others:", round(float(da), 5))
        break
    if wa.drone_state[low] == CHARGING:
        print("relevo completo sin divergencia, t=+", t)
        break
else:
    print("sin divergencia ni fin en 2500")
