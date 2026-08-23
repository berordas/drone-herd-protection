"""GIFs del A/B (Commit L): peor hand-off en ÓRBITA (corzos seed 50, espera_max 777, 8 STRANDED)
y su GEMELO en ESTÁTICA. El episodio es un timeout de ~23.570 ticks -> se renderiza una VENTANA
alrededor del PEOR relevo (espera máxima), con stride 3, y el timeline sidecar cubre TODO el
episodio."""
import sys
import numpy as np
sys.path.insert(0, "/workspace")
from baseline import build_world
from coordinators import ReactiveCoordinator
from render import render_episode
from world import ACTIVE, INCOMING, STRANDED

MARGIN, STRIDE = 300, 3

def snap(w):
    return {**w.snapshot(), "battery": w.battery.copy()}

def run(seed, kind, omega, path):
    w = build_world(seed, kind)
    c = ReactiveCoordinator(w, patrol_omega=omega)
    w.reset()
    hist = [snap(w)]
    hold_since, lines, spans = {}, [], []
    prev_st = w.drone_state.copy(); prev_hold = w.drone_relief_hold.copy()
    while True:
        _o, _r, t, tr, _i = w.step(c.act(w.get_observation()))
        hist.append(snap(w))
        st, hold = w.drone_state, w.drone_relief_hold
        for i in np.where(hold & ~prev_hold)[0]:
            hold_since[int(i)] = int(w.step_count)
            lines.append(f"t={w.step_count} ANUNCIO dron {i} (bat {w.battery[i]:.2f})")
        if bool(((prev_st == INCOMING) & (st == ACTIVE)).any()):
            for j in np.where(prev_hold & ~hold)[0]:
                if int(j) in hold_since:
                    t0 = hold_since.pop(int(j))
                    espera = int(w.step_count) - t0
                    spans.append((espera, t0, int(w.step_count)))
                    lines.append(f"t={w.step_count} HAND-OFF dron {j} (espera {espera} ticks, fase {w.phase})")
        for i in np.where((st == STRANDED) & (prev_st != STRANDED))[0]:
            lines.append(f"t={w.step_count} STRANDED dron {i}")
        prev_st = st.copy(); prev_hold = hold.copy()
        if t or tr:
            break
    espera, ta, tb = max(spans) if spans else (0, 0, min(len(hist) - 1, 2000))
    lo, hi = max(0, ta - MARGIN), min(len(hist) - 1, tb + MARGIN)
    render_episode(w, hist[lo:hi:STRIDE], save_path=path)
    open(path.replace(".gif", "_timeline.txt"), "w").write(
        "\n".join(lines) + f"\nsev={w.n_depredadas} status={w.status} "
        f"ventana_gif=[{lo},{hi}] stride={STRIDE} peor_espera={espera}\n")
    print(path, "sev", w.n_depredadas, w.status, f"ventana [{lo},{hi}] de {len(hist)},",
          len(lines), "eventos de relevo, peor espera", espera)

if __name__ == "__main__":
    run(50, "corzos", 0.02, "/data/hrl_m1/m1pp/gifs/ab_peor_handoff_ORBITA_corzos_s50.gif")
    run(50, "corzos", 0.0, "/data/hrl_m1/m1pp/gifs/ab_gemelo_ESTATICA_corzos_s50.gif")
