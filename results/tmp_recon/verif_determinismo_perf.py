"""Script EFIMERO de reconocimiento (no se commitea): determinismo + rendimiento."""
import hashlib, sys, time
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator

def run_traj(seed, kind):
    w = build_world(seed, kind); w.reset()
    c = ReactiveCoordinator(w)
    h = hashlib.sha256(); sums = 0.0; n = 0
    while True:
        a = c.act(w.get_observation())
        _o, _r, term, trunc, _i = w.step(a)
        state = np.concatenate([w.wolves.ravel(), w.drones.ravel(), w.cows.ravel(),
                                w.cow_vel.ravel(), np.array([float(w.n_depredadas)])])
        h.update(state.tobytes()); sums += float(np.abs(state).sum()); n += 1
        if term or trunc: break
    return h.hexdigest(), sums, n, w.status, int(w.n_depredadas)

print("== DETERMINISMO (misma semilla, 2 corridas independientes, hash SHA256 de todas las posiciones por tick) ==")
for seed, kind in ((0, "lobos"), (7, "mixto"), (3, "corzos")):
    a = run_traj(seed, kind); b = run_traj(seed, kind)
    print(f"  seed={seed} kind={kind}: hash_igual={a[0]==b[0]} suma_igual={a[1]==b[1]} "
          f"ticks={a[2]} status={a[3]} sev={a[4]}")

print("== RENDIMIENTO (headless, 1 hilo) ==")
t0 = time.time(); total = 0; eps = 0
for seed in range(6):
    w = build_world(seed, "lobos"); w.reset()
    c = ReactiveCoordinator(w)
    while True:
        _o, _r, term, trunc, _i = w.step(c.act(w.get_observation()))
        total += 1
        if term or trunc: eps += 1; break
el = time.time() - t0
print(f"  {total} ticks en {el:.1f} s -> {total/el:.0f} ticks/s | {eps} episodios "
      f"({total/eps:.0f} ticks/ep medio) -> ~{3600*eps/el:.0f} episodios/hora (1 proceso)")
t0 = time.time(); w = build_world(0, "lobos"); w.reset(); n = 0
while n < 2000:
    _ = w.step(None); n += 1
print(f"  mundo SIN coordinador (Dummy None): {n/(time.time()-t0):.0f} ticks/s")
