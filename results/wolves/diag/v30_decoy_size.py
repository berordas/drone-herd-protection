"""v30_decoy_size.py — SOLO EVAL (desechable): ¿basta un CEBO de 1 para anclar la barrera v3.0,
o hace falta 2? Instrumenta episodios grouped-2 (CONFIG_V2 v3.0: terreno 500 + reparto fijo +
timing) vs ReactiveCoordinator con wolf_decoy_size=1 y =2, y mide por episodio:
  - ancla: fracción de pasos de ESCOLTA con el ancla en el sector-CEBO (1º)
  - quién confirma primero (cebo/asalto) y paso del disparo (wolf_decoy_released)
  - ventana del asalto (pasos de ESCOLTA con cebo confirmado y asalto SIN confirmar)
  - severidad, muertes del asalto (todos los flanqueadores del 2º sector), muertes de prey2
Elige el default de CONFIG_V2 con datos. JSON -> /data/wolves/diag/v30_decoy_size.json
"""
import sys, json
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import CONFIG_V2
from world import World, ACTIVE
from coordinators import ReactiveCoordinator


def run_ep(seed, decoy):
    cfg = {**CONFIG_V2, "wolf_decoy_size": decoy}
    w = World(seed=seed, episode_kind="lobos", **cfg)
    coord = ReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n, n1 = int(w.n_wolves), int(w.wolf_group_sizes[0])
    esc = anchor_s1 = anchor_s2 = s2_free = 0
    conf1_s1 = conf1_s2 = release = None
    while True:
        wp = coord.act(w.get_observation())
        conf = coord._confirmed.copy() if coord._confirmed is not None else np.zeros(n, bool)
        anchor = coord._anchor
        _o, _r, term, trunc, _i = w.step(wp)
        if conf[:n1].any() and conf1_s1 is None:
            conf1_s1 = int(w.step_count)
        if conf[n1:].any() and conf1_s2 is None:
            conf1_s2 = int(w.step_count)
        if release is None and w.wolf_decoy_released:
            release = int(w.step_count)
        if w.phase == "ESCOLTA":
            esc += 1
            if anchor is not None:
                if anchor < n1:
                    anchor_s1 += 1
                else:
                    anchor_s2 += 1
            if conf[:n1].any() and not conf[n1:].any():
                s2_free += 1
        if term or trunc:
            break
    kills_s2 = sum(1 for c in w.captures if c["flankers"] and min(c["flankers"]) >= n1)
    kills_p2 = sum(1 for c in w.captures if c.get("is_pack_prey2"))
    return {
        "seed": seed, "n": n, "reparto": f"{n1}+{n - n1}", "sev": int(w.n_depredadas),
        "status": w.status, "steps": int(w.step_count), "esc": esc,
        "ancla_cebo": round(anchor_s1 / max(anchor_s1 + anchor_s2, 1), 3),
        "conf1_cebo": conf1_s1, "conf1_asalto": conf1_s2, "release": release,
        "ventana": round(s2_free / max(esc, 1), 3),
        "kills_s2": kills_s2, "kills_prey2": kills_p2,
    }


out = {}
for decoy in (1, 2):
    rows = []
    for s in range(200):
        r = run_ep(s, decoy)
        if r is not None:
            rows.append(r)
            print(f"  d={decoy} seed={s:3d} {r['reparto']} sev={r['sev']} ancla_cebo={r['ancla_cebo']:.2f} "
                  f"ventana={r['ventana']:.2f} conf1(c/a)={r['conf1_cebo']}/{r['conf1_asalto']} "
                  f"rel={r['release']} kills_s2={r['kills_s2']}", flush=True)
        if len(rows) >= 25:
            break
    sev = [r["sev"] for r in rows]
    resumen = {
        "n_eps": len(rows),
        "sev_media": round(float(np.mean(sev)), 2), "sev_std": round(float(np.std(sev)), 2),
        "ancla_cebo_media": round(float(np.mean([r["ancla_cebo"] for r in rows])), 3),
        "eps_ancla_cebo_mayoria": sum(1 for r in rows if r["ancla_cebo"] > 0.5),
        "cebo_confirma_primero": sum(1 for r in rows if (r["conf1_cebo"] or 9e9) < (r["conf1_asalto"] or 9e9)),
        "ventana_media": round(float(np.mean([r["ventana"] for r in rows])), 3),
        "kills_s2_media": round(float(np.mean([r["kills_s2"] for r in rows])), 2),
        "cunde": sum(1 for r in rows if r["kills_s2"] > 0),
    }
    out[f"decoy_{decoy}"] = {"resumen": resumen, "episodios": rows}
    print(f"== decoy={decoy}: {resumen}", flush=True)

json.dump(out, open("/data/wolves/diag/v30_decoy_size.json", "w"), indent=1)
print("JSON -> /data/wolves/diag/v30_decoy_size.json")
print("DECOY_LISTO")
