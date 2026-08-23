"""Línea temporal de investigaciones del seed 77 mixto: flancos de drone_investigating con el
tipo de contacto (corzo/lobo), descartes de corzo y fases — para la anotación de la firma."""
import sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from world import ACTIVE

w = build_world(77, "mixto")
from coordinators import ReactiveCoordinator
c = ReactiveCoordinator(w)
w.reset()
prev_inv = w.drone_investigating.copy()
prev_dis = w.corzo_dismissed.copy()
prev_phase = w.phase
lines = []
while True:
    inv = w.drone_investigating
    for i in np.where(inv & ~prev_inv)[0]:
        pos, is_wolf, gid = w._contact_bodies()
        j = int(np.argmin(np.linalg.norm(pos - w.drones[i], axis=1)))
        lines.append(f"t={w.step_count} INVESTIGA dron {i} contacto={'LOBO' if is_wolf[j] else 'CORZO'} d={np.linalg.norm(pos[j]-w.drones[i]):.0f}")
    for i in np.where(prev_inv & ~inv)[0]:
        lines.append(f"t={w.step_count} FIN investigación dron {i}")
    for k in np.where(w.corzo_dismissed & ~prev_dis)[0]:
        lines.append(f"t={w.step_count} CORZO {k} descartado")
    if w.phase != prev_phase:
        lines.append(f"t={w.step_count} FASE {prev_phase}->{w.phase}")
        prev_phase = w.phase
    prev_inv = inv.copy(); prev_dis = w.corzo_dismissed.copy()
    _o, _r, t, trc, _i = w.step(c.act(w.get_observation()))
    if t or trc or w.step_count > 1400:
        break
print("\n".join(lines[:40]))
