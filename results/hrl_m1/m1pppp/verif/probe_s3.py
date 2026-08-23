import sys
sys.path.insert(0, '/workspace')
from baseline import build_world
from hrl.options_wolf import WolfOptionLayer
from rl.policy_wolf_controller import SyncedReactiveCoordinator

layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
w = build_world(3, "lobos", wolf_controller=layer)
coord = SyncedReactiveCoordinator(w)
w.reset()
prev_phase, esc_t = w.phase, None
prey2_hist = []
while True:
    _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
    if w.phase != prev_phase:
        print("t=%d: fase %s -> %s" % (w.step_count, prev_phase, w.phase))
        if w.phase == "ESCOLTA" and esc_t is None:
            esc_t = int(w.step_count)
        prev_phase = w.phase
    if int(w.step_count) % 200 == 0:
        prey2_hist.append((int(w.step_count), int(w.pack_prey2), w.phase,
                           bool(w.wolf_decoy_released)))
    if t or tr:
        break
print("muestras (t, prey2, fase, released):", prey2_hist)
print("fin t=%d sev=%d status=%s show=%s staged=%s suelta=%s esc_t=%s"
      % (w.step_count, w.n_depredadas, w.status, layer.t_show, layer.t_staged,
         layer.t_suelta, esc_t))
