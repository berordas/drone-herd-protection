import sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator
from wolf_controllers import assault_staged
from world import ACTIVE

layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
w = build_world(14, "lobos", wolf_controller=layer)
coord = SyncedReactiveCoordinator(w)
w.reset()
evs, staged_ticks, ring_ok_t, dp_hist = [], 0, 0, []
while True:
    _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
    evs += layer.pop_events()
    if not w.wolf_decoy_released and w.pack_prey2 >= 0 and layer._s2.size > 0:
        s2 = layer._s2
        p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
        act = w.drones[w.drone_state == ACTIVE]
        dmin = float(np.linalg.norm(w.wolves[s2][:, None, :] - act[None, :, :], axis=2).min()) if act.shape[0] else 0.0
        dp = float(np.linalg.norm(w.wolves[s2].mean(axis=0) - p2))
        ring = dmin <= w.r_detect + 50.0 + 20.0
        ring_ok_t += ring
        staged_ticks += bool(assault_staged(w, s2, p2, stage_hold=50.0))
        if int(w.step_count) % 400 == 0:
            dp_hist.append((int(w.step_count), round(dp, 1), round(dmin, 1), w.phase,
                            bool(layer._align_done)))
    if t or tr:
        break
print("eventos:", [(e["ev"], e["t"], e.get("causa", e.get("err_rumbo_deg"))) for e in evs
                   if e["ev"] in ("ALIGN_END", "SHOW_START", "STALL", "OPTION_FALLBACK", "RETARGET")])
print("fin t=%d sev=%d status=%s show=%s staged_hito=%s stalls=%d" %
      (w.step_count, w.n_depredadas, w.status, layer.t_show, layer.t_staged, layer.n_stalls))
print("ticks con anillo-ok=%d, con staged-completo=%d (trigger d_prey<=%.0f)" %
      (ring_ok_t, staged_ticks, w.assault_trigger_dist + 60.0))
print("muestras (t, d_prey, dmin_drones, fase, align_done):")
for x in dp_hist[:14]:
    print("  ", x)
