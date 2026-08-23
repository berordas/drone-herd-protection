"""Forense seed 77 mixto (firma del dueño): en cada una de las 4 entradas NO detectadas,
¿estaba el anillo a M=3 por una INVESTIGACIÓN DE CORZO? Registra por entrada: M del anillo,
quién investigaba y si su contacto era corzo (verdad-terreno del stub _contact_bodies),
fase, D_max del anillo en ese tick, y n de corzos descartados hasta entonces."""
import sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from world import ACTIVE
from hrl.behavior_checks import PatrolCoverageTracker

w = build_world(77, "mixto")
c = ReactiveCoordinator(w)
w.reset()
tr = PatrolCoverageTracker(w)
print("n_wolves", w.n_wolves, "n_corzos", w.n_corzos, "grupos", w.wolf_group_sizes,
      "n_calves", w.n_calves)
out = []
while True:
    n_ent = len(tr.entradas)
    tr.on_boundary()
    # estado del anillo ESTE tick (el mismo instante que audita el tracker)
    act = w.drone_state == ACTIVE
    ring = act & ~w.drone_investigating
    inv = np.where(w.drone_investigating & act)[0]
    inv_info = []
    for i in inv:
        pos, is_wolf, gid = w._contact_bodies()
        j = int(np.argmin(np.linalg.norm(pos - w.drones[i], axis=1)))
        inv_info.append({"dron": int(i), "contacto_lobo": bool(is_wolf[j]),
                         "d_contacto": round(float(np.linalg.norm(pos[j] - w.drones[i])), 1)})
    snapshot = {"t": int(w.step_count), "fase": w.phase, "M_anillo": int(ring.sum()),
                "n_activos": int(act.sum()), "investigando": inv_info,
                "corzos_descartados": int(w.corzo_dismissed.sum())}
    for e in tr.entradas[n_ent:]:
        out.append({**e, **snapshot})
    _o, _r, t, trc, _i = w.step(c.act(w.get_observation()))
    if t or trc:
        break
rec = tr.finalize()
print("sev", w.n_depredadas, "status", w.status)
for o in out:
    print(o)
import json
json.dump({"entradas_detalle": out, "auditor": {k: rec[k] for k in
           ("ticks_patrulla", "ticks_aviso", "ticks_violacion", "D_max", "R_media", "R_max")}},
          open("/data/hrl_m1/m1pp/forense_s77.json", "w"), indent=1, ensure_ascii=False)
