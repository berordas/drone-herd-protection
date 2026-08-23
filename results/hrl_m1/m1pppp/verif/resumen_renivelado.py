import json, glob
import numpy as np
B = '/data/hrl_m1'

print("== CELDAS S LIMPIAS (v3.7) ==")
c = json.load(open(f'{B}/m1pppp/celdas_s_v37.json'))
for k, v in c["celdas"].items():
    print(f" {k}: sev {v['sev']} completa {v['jugada_completa_frac']} show {v['con_show_frac']} "
          f"strike {v['con_strike_frac']} stalls {v['stalls_total']} staged {v['staged_causas']} "
          f"align {v['align_causas']} err_show {v['err_show_deg']}")
for k in ("delta_d90_masa", "delta_d180_masa", "delta_d180_d90"):
    print(f" {k}: {c[k]}")

print("== SANITY E0.1 ==")
s = json.load(open(f'{B}/m1pppp/sanity_capa_v37.json'))
print(f" keep {s['sev_keep']} masa {s['sev_masa']} delta {s['delta_keep_menos_masa']} "
      f"(ref v3.6 {s['ref_v36']}) censura_keep {s['censura_keep']}")

print("== METRO v3.7 ==")
for f in sorted(glob.glob(f'{B}/m1pppp/metro/*.json')):
    d = json.load(open(f))
    name = f.split('/')[-1]
    if "by_kind" in d:
        row = {k: round(v["severity_mean"], 3) for k, v in d["by_kind"].items()}
        jug = {k: v.get("jugada_completa_frac") for k, v in d["by_kind"].items()
               if v.get("jugada_completa_frac") is not None}
        print(f" {name}: {row} jugada2f {jug}")
    else:
        print(f" {name}: sev2f {round(d['severidad_media_2grupos'],3)} knc {round(d['frac_killer_no_confirmado'],3)} "
              f"ancla_cebo {round(d['frac_ancla_cebo'],3)} n2f {d['n_episodios_2grupos']}")

print("== LISTONES B_* (v3.7) ==")
res = {}
for pol in ("masa", "spawn", "oracle"):
    for opp in ("reactive", "run02"):
        d = json.load(open(f'{B}/eval/{pol}_v37__{opp}.json'))
        r = d["resumen"]
        res[(pol, opp)] = d["episodes"]
        print(f" {pol} vs {opp}: sev {[round(x,3) if x is not None else x for x in r['sev']]} "
              f"censura {r.get('censura')} aborts/ep {round(r.get('aborts_por_ep',0),2)} "
              f"stalls {r.get('stalls_total')}")
rng = np.random.default_rng(20260821)
def ci(d):
    b = d[rng.integers(0, d.size, size=(10000, d.size))].mean(axis=1)
    return [round(float(d.mean()),3), round(float(np.percentile(b,2.5)),3), round(float(np.percentile(b,97.5)),3)]
for opp in ("reactive", "run02"):
    o = {(e["seed"], e["kind"]): e["sev"] for e in res[("oracle", opp)]}
    sp = {(e["seed"], e["kind"]): e["sev"] for e in res[("spawn", opp)]}
    d = np.array([o[k] - sp[k] for k in o], float)
    print(f" Delta(oracle-spawn) vs {opp}: {ci(d)}")
o_r = {(e["seed"], e["kind"]): e["sev"] for e in res[("oracle", "reactive")]}
o_2 = {(e["seed"], e["kind"]): e["sev"] for e in res[("oracle", "run02")]}
d = np.array([o_2[k] - o_r[k] for k in o_r], float)
print(f" gap transferencia oracle (run02-reactive): {ci(d)}")
print("RESUMEN_OK")
