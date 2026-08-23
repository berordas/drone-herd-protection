"""GIF de evidencia del Encargo 1c: seed 77 mixto, Reactive-estática — el único episodio del
corpus con entradas de lobo NO detectadas hasta <100 del rebaño (4, por arcos en AVISO; sev 8).
Timeline sidecar con los flancos del auditor (detecciones, entradas, ventanas de aviso)."""
import sys

import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode
from world import ACTIVE
from hrl.behavior_checks import PatrolCoverageTracker


def snap(w, conf):
    s = {**w.snapshot(), "battery": w.battery.copy()}
    if conf is not None:
        s["confirmed_mask"] = conf.copy()
    return s


if __name__ == "__main__":
    w = build_world(77, "mixto")
    c = ReactiveCoordinator(w)
    w.reset()
    tr = PatrolCoverageTracker(w)
    hist, lines = [snap(w, c._confirmed)], []
    det_prev = tr._detected.copy()
    prev_phase, prev_dep = w.phase, 0
    while True:
        tr.on_boundary()
        for i in np.where(tr._detected & ~det_prev)[0]:
            lines.append(f"t={w.step_count} DETECTADO lobo {i}")
        det_prev = tr._detected.copy()
        n_ent = len(tr.entradas)
        _o, _r, t, trc, _i = w.step(c.act(w.get_observation()))
        hist.append(snap(w, c._confirmed))
        for e in tr.entradas[n_ent:]:
            lines.append(f"t={e['t']} ENTRADA lobo {e['lobo']} detectado={e['detectado']} "
                         f"arco_aviso={e['cruzo_arco_aviso']} arco_violacion={e['cruzo_arco_violacion']}")
        if w.phase != prev_phase:
            lines.append(f"t={w.step_count} FASE {prev_phase}->{w.phase}")
            prev_phase = w.phase
        if int(w.n_depredadas) > prev_dep:
            prev_dep = int(w.n_depredadas)
            lines.append(f"t={w.step_count} MUERTE (total {prev_dep})")
        if t or trc:
            break
    rec = tr.finalize()
    path = "/data/hrl_m1/m1pp/gifs/audit_entradas_s77_mixto_estatica.gif"
    stride = max(1, len(hist) // 2500)
    render_episode(w, hist[::stride], save_path=path)
    lines.append(f"-- auditor: {[(k, rec[k]) for k in ('ticks_patrulla', 'ticks_aviso', 'ticks_violacion', 'D_max', 'R_media')]}")
    lines.append(f"ventanas_top: {rec['ventanas_top'][:5]}")
    open(path.replace(".gif", "_timeline.txt"), "w").write(
        "\n".join(lines) + f"\nsev={w.n_depredadas} status={w.status} stride={stride}\n")
    print(path, "sev", w.n_depredadas, w.status, len(hist), "ticks, stride", stride,
          "| entradas no detectadas:", rec["entradas_no_detectadas"])
