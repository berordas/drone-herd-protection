"""paso0_suelo_v27.py — ¿el SUELO residual (scriptado δ=0) está SANO contra la pared v2.7,
o los lobos se atascan (zombis) hasta el timeout? Solo lectura; throwaway en /data.

En episodios grouped de 2 SUBGRUPOS (v2.7, barrera Reactiva, ResidualWolfController δ=0),
mide por episodio: status, pasos, muertes, RAPIDEZ MEDIA de los lobos (¿se mueven o están
congelados?), rapidez en el ÚLTIMO 25% (¿zombis al final?), fracción de lobo-pasos AMURALLADOS
(_wolf_walled), y la MÍNIMA distancia paquete->presa alcanzada (¿llegan a atacar?).
Sano = se mueven / rodean / atacan (kills o timeouts CON movimiento). Zombi = congelados
contra la pared, severidad artificialmente 0 por timeouts sin intento.
"""
import sys; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from world import ACTIVE
from rl.residual_wolf_controller import ResidualWolfController
from rl.policy_wolf_controller import SyncedReactiveCoordinator

KINDS = ("lobos", "mixto")
N_SEEDS = 40

def prey_pos(w):
    pp = w._prey_pos()
    return pp

def run(seed, kind):
    ctrl = ResidualWolfController(model=None)   # δ=0 = scriptado puro
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    speeds = []; walled_steps = 0; wolf_steps = 0; mind = np.inf
    while True:
        _o,_r,term,trunc,_i = w.step(coord.act(w.get_observation()))
        sp = np.linalg.norm(w.wolf_vel, axis=1)
        speeds.append(float(sp.mean()))
        walled_steps += int(w._wolf_walled.sum()); wolf_steps += int(w.n_wolves)
        pp = prey_pos(w)
        if pp is not None:
            mind = min(mind, float(np.linalg.norm(w.wolves - pp, axis=1).min()))
        if term or trunc: break
    sp = np.array(speeds); tail = sp[int(0.75*len(sp)):]
    return dict(status=w.status, steps=int(w.step_count), dead=int(w.n_depredadas),
                v_mean=float(sp.mean()), v_tail=float(tail.mean()),
                walled_frac=(walled_steps/max(wolf_steps,1)),
                mind_prey=(None if mind==np.inf else round(mind,1)),
                sizes=[int(x) for x in w.wolf_group_sizes])

eps = []
for kind in KINDS:
    for s in range(N_SEEDS):
        r = run(s, kind)
        if r: eps.append(r)

from collections import Counter
st = Counter(e["status"] for e in eps)
m = lambda k: float(np.mean([e[k] for e in eps]))
print("=== PASO 0: suelo residual (scriptado δ=0) vs pared v2.7 — episodios de 2 subgrupos ===")
print(f"  n episodios 2 grupos = {len(eps)} (de {N_SEEDS}×{len(KINDS)})")
print(f"  status: {dict(st)}")
print(f"  severidad media = {m('dead'):.2f}  | pasos medios = {m('steps'):.0f}")
print(f"  RAPIDEZ media lobos = {m('v_mean'):.2f} m/s  | en el ULTIMO 25% = {m('v_tail'):.2f} m/s  (cap wolf_speed=4)")
print(f"  fraccion lobo-pasos AMURALLADOS = {100*m('walled_frac'):.1f}%")
print(f"  MIN dist paquete->presa alcanzada (media) = {m('mind_prey'):.1f} m  (capture_radius=3, r_face_safe=6)")
# Veredicto heuristico
zombie = (m('v_tail') < 0.6 and st.get('timeout',0) > 0.7*len(eps) and m('dead') < 0.5)
print(f"  VEREDICTO heuristico: {'⚠️ POSIBLE ZOMBI (congelados, timeouts sin intento)' if zombie else '✅ SANO (los lobos se mueven / atacan / rodean)'}")
