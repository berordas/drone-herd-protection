import json, numpy as np
from collections import Counter
E = "/data/hrl_m1/eval/"
def load(n): return {(e["seed"],e["kind"]): e for e in json.load(open(E+n+".json"))["episodes"]}
m, o, ma, sp = load("manager_M1_final__reactive"), load("oracle__reactive"), load("masa__reactive"), load("spawn__reactive")
keys = sorted(m)
def boot(d):
    d=np.asarray(d,float); rng=np.random.default_rng(0); b=d[rng.integers(0,d.size,(10000,d.size))].mean(1); return round(d.mean(),3), round(np.percentile(b,2.5),3), round(np.percentile(b,97.5),3), d.size
for lab, sel in [("G n>=3", lambda e: e["two_front"] and e["n_wolves"]>=3), ("S n>=3", lambda e: (not e["two_front"]) and e["n_wolves"]>=3), ("n<=2", lambda e: e["n_wolves"]<=2), ("n=3", lambda e: e["n_wolves"]==3), ("n=4", lambda e: e["n_wolves"]==4), ("n=5", lambda e: e["n_wolves"]==5)]:
    ks=[k for k in keys if sel(m[k])]
    print(f"{lab:8s} mgr {boot([m[k]['sev'] for k in ks])[0]:.2f} oracle {boot([o[k]['sev'] for k in ks])[0]:.2f} masa {boot([ma[k]['sev'] for k in ks])[0]:.2f} spawn {boot([sp[k]['sev'] for k in ks])[0]:.2f} | Δ(mgr-oracle) {boot([m[k]['sev']-o[k]['sev'] for k in ks])} | Δ(mgr-masa) {boot([m[k]['sev']-ma[k]['sev'] for k in ks])[:3]}")
seqS = Counter(tuple(m[k]["actions"][:6]) for k in keys if not m[k]["two_front"])
print("secuencias S (6 primeras acciones):", seqS.most_common(4))
print("eventos S mgr:", Counter(e for k in keys if not m[k]["two_front"] for e in m[k]["events"]))
print("eventos S oracle:", Counter(e for k in keys if not o[k]["two_front"] for e in o[k]["events"]))
for n in (1,2):
    ks=[k for k in keys if m[k]["n_wolves"]==n]; print(f" n={n}: mgr {np.mean([m[k]['sev'] for k in ks]):.2f} oracle {np.mean([o[k]['sev'] for k in ks]):.2f} n={len(ks)}")
# ¿De dónde sale la ganancia en S? status y duración
for lab, d in (("mgr", m), ("oracle", o)):
    ks=[k for k in keys if not d[k]["two_front"] and d[k]["n_wolves"]>=3]
    print(lab, "S n>=3: success", sum(1 for k in ks if d[k]["status"]=="success"), "pred", sum(1 for k in ks if d[k]["status"]=="predation"), "timeout", sum(1 for k in ks if d[k]["status"]=="timeout"), "dec", np.mean([d[k]["decisions"] for k in ks]).round(1), "pen", np.mean([d[k]["penetrado_ticks"] for k in ks]).round(1))
