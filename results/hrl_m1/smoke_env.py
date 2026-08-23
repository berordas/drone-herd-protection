import sys, time; sys.path.insert(0, "/workspace")
import numpy as np
from hrl.manager_env import ManagerEnv
env = ManagerEnv(seed=0)
obs, info = env.reset()
print("reset", obs.shape, info, flush=True)
t0 = time.time(); n = 0
rng = np.random.default_rng(0)
for ep in range(3):
    if ep: obs, info = env.reset()
    done = False
    while not done:
        a = int(rng.integers(4))
        obs, r, term, trunc, info = env.step(a)
        n += 1; done = term or trunc
        print(f"  dec {info['decision_idx']} {info['option']:<10s} ticks={info['ticks']:>5d} ev={info['event']:<17s} r={r:.0f}", ("| EP sev %s pen %s status %s" % (info.get("ep_sev"), info.get("penetrado_ticks"), info.get("status"))) if done else "", flush=True)
print("macro-pasos", n, "en", round(time.time()-t0,1), "s", flush=True)
