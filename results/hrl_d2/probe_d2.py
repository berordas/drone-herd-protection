"""probe_d2.py — smoke de hrl/manager_drone.py: (1) FrozenWolfManager ≡ ManagerEnv bit a bit
(hash del mundo por tick, 2 episodios); (2) DroneManagerEnv determinista + episodio corto con
atacante manager y natural."""
import hashlib, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from hrl.hrl_check import _blob
from hrl.manager_env import ManagerEnv
from hrl.eval_manager import policy_fn
from hrl.manager_drone import FrozenWolfManager, DroneManagerEnv, WOLF_MANAGER_CKPT
from hrl.options_wolf import WolfOptionLayer

def h_managerenv(seed, kind):
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    h = hashlib.sha256()
    env.on_tick = lambda w, c, l: h.update(_blob(w))
    obs, info = env.reset_to(seed, kind)
    pol = policy_fn("manager:" + WOLF_MANAGER_CKPT)
    first, done, n = True, False, 0
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a); n += 1
        done = term or trunc
    return h.hexdigest(), int(env.world.n_depredadas), n

def h_frozen(seed, kind):
    fm = FrozenWolfManager(WOLF_MANAGER_CKPT)
    layer = WolfOptionLayer(manager=fm, frame_skip=5)
    w = build_world(seed, kind, wolf_controller=layer)
    coord = ReactiveCoordinator(w)
    w.reset()
    h = hashlib.sha256()
    while True:
        layer.refresh(w)
        wp = coord.act(w.get_observation())
        _o, _r, t, tr, _i = w.step(wp)
        fm.on_tick(w, layer)
        h.update(_blob(w))
        if t or tr:
            break
    return h.hexdigest(), int(w.n_depredadas), fm.n_decisions

for seed, kind in ((21, "lobos"), (77, "lobos")):
    t0 = time.time()
    a = h_managerenv(seed, kind); b = h_frozen(seed, kind)
    print(f"seed {seed} {kind}: ManagerEnv sev={a[1]} dec={a[2]} | Frozen sev={b[1]} dec={b[2]} | "
          f"hash igual={a[0] == b[0]} ({time.time()-t0:.0f}s)")

env = DroneManagerEnv(seed=0)
for atk in ("natural", "manager"):
    res = []
    for rep in range(2):
        obs, info = env.reset_to(3, "lobos", atk)
        assert obs.shape == (44,)
        h = hashlib.sha256(); done = False; k = 0
        env.on_tick = lambda w, c, l: h.update(_blob(w))
        while not done:
            obs, r, term, trunc, info = env.step(k % 3); k += 1
            done = term or trunc
        res.append((h.hexdigest(), info["ep_sev"], info["ep_decisions"], info["interrupciones"],
                    info["stalls"], info["cambios"], info["delib_pagado"]))
    print(atk, "det:", res[0][0] == res[1][0], "sev/dec/interr/stalls/cambios/delib:", res[0][1:])
print("PROBE_D2_OK")
