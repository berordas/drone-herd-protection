import json, sys
import numpy as np
a = json.load(open("/data/hrl_m1/m1pppp/inocuidad_v37.json"))
b = json.load(open("/data/hrl_m1/m1pppp/inocuidad_v371.json"))
assert [r["seed"] for r in a] == [r["seed"] for r in b]
kinds_igual = all(x["kind"] == y["kind"] for x, y in zip(a, b))
d = np.array([y["sev"] - x["sev"] for x, y in zip(a, b)], float)
rng = np.random.default_rng(20260822)
boot = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
res = {"n_pares": 50, "kinds_identicos": kinds_igual,
       "sev_v37": float(np.mean([x["sev"] for x in a])),
       "sev_v371": float(np.mean([y["sev"] for y in b])),
       "delta_v371_menos_v37": [round(float(d.mean()), 4),
                                round(float(np.percentile(boot, 2.5)), 3),
                                round(float(np.percentile(boot, 97.5)), 3)],
       "pares_distintos": int((d != 0).sum()),
       "umbral_parada": 0.10}
res["VEREDICTO"] = ("INOCUA (v3.7.1 oficial)" if abs(res["delta_v371_menos_v37"][0]) <= 0.10
                    else "|dsev| > 0.10 - PARAR Y AVISAR")
json.dump(res, open("/data/hrl_m1/m1pppp/inocuidad_v371.resumen.json", "w"), indent=1)
print(json.dumps(res, indent=1, ensure_ascii=False))
