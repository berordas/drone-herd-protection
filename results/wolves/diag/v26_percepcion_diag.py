"""v26_percepcion_diag.py — Verificación DIRIGIDA de la barrera con percepción realista (v2.6).

(1) SINTÉTICO (falsificador clave): en ESCOLTA, un lobo DETECTADO cerca del rebaño y el resto
    tele-transportado FUERA de r_detect de todo dron ACTIVE:
      a) mover el frente NO VISTO no cambia NI UN waypoint (antes sí: entraba en la media global);
      b) el eje de la barrera apunta al lobo ancla (no a la media global);
      c) sin NINGÚN lobo detectado -> patrulla; al re-detectar -> barrera de nuevo.
(2) SANITY un frente (clustered): la barrera sigue entre rebaño y paquete, repartida.
(3) EPISODIOS grouped reales (semillas de 2 frentes del reconocimiento): cobertura por frente y
    severidad con la nueva regla (observacional).
Solo lectura del mundo; el coordinador es el nuevo. Script desechable en /data/wolves/diag/.
"""
from __future__ import annotations

import sys
import numpy as np

sys.path.insert(0, "/workspace")

from world import World, ACTIVE, DETER_RADIUS
from coordinators import ReactiveCoordinator
from baseline import CONFIG_V2


def free_mask(w):
    return (w.drone_state == ACTIVE) & (~w.drone_investigating)


def herd_of(w):
    m = w.cow_alive & ~w.cow_safe
    parts = [w.cows[m]] if m.any() else []
    if w.n_calves > 0:
        mc = w.calf_alive & ~w.calf_safe
        if mc.any():
            parts.append(w.calves[mc])
    return np.vstack(parts) if parts else np.zeros((0, 2))


def detected_ext(w):
    """Criterio de detección recomputado EXTERNAMENTE (mismo que _update_phase: ACTIVE + r_detect)."""
    flying = w.drones[w.drone_state == ACTIVE]
    if flying.shape[0] == 0:
        return np.zeros(w.n_wolves, dtype=bool)
    d = np.linalg.norm(w.wolves[:, None, :] - flying[None, :, :], axis=2)
    return (d <= w.r_detect).any(axis=1)


def advance_to_escolta(w, c, cap=4000):
    while w.phase != "ESCOLTA":
        w.step(c.act(w.get_observation()))
        if w.step_count >= cap:
            return False
    return True


def ang(v):
    return np.degrees(np.arctan2(v[1], v[0]))


def wrap(a):
    return abs((a + 180.0) % 360.0 - 180.0)


# ---------------------------------------------------------------- (1) sintético
print("=== (1) SINTÉTICO: el frente NO VISTO no influye ===")
seed_ok = None
for s in range(1, 15):
    w = World(seed=s, corzos_max=3, episode_kind="lobos"); w.reset()
    if w.n_wolves >= 3:
        c = ReactiveCoordinator(w)
        if advance_to_escolta(w, c):
            seed_ok = s
            break
print("  seed sintético: %d (n_wolves=%d)" % (seed_ok, w.n_wolves))
for _ in range(60):
    w.step(c.act(w.get_observation()))

hc = herd_of(w).mean(axis=0)
anchor = c._anchor
others = [j for j in range(w.n_wolves) if j != anchor]
# candidatos FUERA de r_detect de todo dron ACTIVE (con holgura), rankeados por diferencia
# angular respecto al rumbo del ancla (este) -> la media global apuntaría lejos del ancla.
cand = np.array([[3.0, 3.0], [297.0, 3.0], [3.0, 297.0], [297.0, 297.0],
                 [150.0, 3.0], [150.0, 297.0], [3.0, 150.0], [297.0, 150.0]])
flying = w.drones[w.drone_state == ACTIVE]
clear = np.array([np.linalg.norm(flying - cc, axis=1).min() > w.r_detect + 15.0 for cc in cand])
cand = cand[clear]
bear = np.array([wrap(ang(cc - hc) - 0.0) for cc in cand])      # ancla al ESTE (0°)
order = np.argsort(-bear)
far, far2 = cand[order[0]], cand[order[1]]

w.wolves[anchor] = hc + np.array([45.0, 0.0])          # ancla VISIBLE al este del rebaño
w.wolves[others] = far + np.random.default_rng(0).normal(0, 3, size=(len(others), 2))
det = detected_ext(w)
assert det[anchor] and not det[others].any(), "el montaje no dejó al ancla como único detectado"
print("  detectados: ancla=%d sí, resto (%s) no — montaje OK" % (anchor, others))

idx = np.where(free_mask(w))[0]
W1 = c.act(w.get_observation()).copy()
w.wolves[others] = far2 + np.random.default_rng(1).normal(0, 3, size=(len(others), 2))   # mueve el frente NO visto
det2 = detected_ext(w)
assert not det2[others].any()
W2 = c.act(w.get_observation()).copy()
same = np.array_equal(W1, W2)
print("  (a) mover el frente NO visto -> waypoints IDÉNTICOS: %s" % same)
assert same, "FALLO: el frente no detectado influyó en la barrera"

center = W1[idx].mean(axis=0)
err_anchor = wrap(ang(center - hc) - ang(w.wolves[anchor] - hc))
gmean = w.wolves.mean(axis=0)
err_mean = wrap(ang(center - hc) - ang(gmean - hc))
print("  (b) eje de la barrera: |centro-vs-ANCLA|=%.1f°  |centro-vs-MEDIA global|=%.1f° (la media apunta a la esquina)"
      % (err_anchor, err_mean))
assert err_anchor < 25.0 and err_mean > err_anchor + 20.0, "FALLO: la barrera no está anclada al detectado"

w.wolves[anchor] = far2 + np.array([5.0, 0.0])          # también el ancla fuera de detección
det3 = detected_ext(w)
assert not det3.any()
W3 = c.act(w.get_observation())
rad = np.linalg.norm(W3[idx] - hc, axis=1)
print("  (c) sin NINGÚN detectado -> targets en anillo de patrulla: radios %s (cv=%.2f)"
      % (np.round(rad, 0), rad.std() / max(rad.mean(), 1e-9)))
assert rad.std() / max(rad.mean(), 1e-9) < 0.35, "FALLO: sin detectados no cayó a patrulla"
w.wolves[anchor] = hc + np.array([45.0, 0.0])           # re-detecta -> barrera de nuevo
W4 = c.act(w.get_observation())
center4 = W4[idx].mean(axis=0)
err4 = wrap(ang(center4 - hc) - ang(w.wolves[anchor] - hc))
print("      re-detectado -> barrera de nuevo hacia el ancla (err=%.1f°)" % err4)
assert err4 < 25.0
print("  OK")

# ---------------------------------------------------------------- (2) sanity un frente
print()
print("=== (2) SANITY un frente (clustered): barrera entre rebaño y paquete ===")
w = World(seed=1, corzos_max=3, episode_kind="lobos"); w.reset()
c = ReactiveCoordinator(w)
assert advance_to_escolta(w, c)
for _ in range(120):
    w.step(c.act(w.get_observation()))
free = free_mask(w); herd = herd_of(w)
dr = w.drones[free]; pc = w.wolves.mean(0); hc = herd.mean(0)
u = pc - hc; L = float(np.linalg.norm(u)); u = u / max(L, 1e-9)
proj = ((dr - hc) @ u) / max(L, 1e-9)
perp = np.array([-u[1], u[0]]); lat = (dr - hc) @ perp
print("  %d drones libres | proj eje rebaño->paquete media=%.2f | ancho del frente=%.0f m"
      % (free.sum(), proj.mean(), lat.max() - lat.min()))
assert proj.mean() > 0.05 and proj.mean() < 0.9 and (lat.max() - lat.min()) > c.drone_spacing
print("  OK (esencialmente como antes con un solo frente)")

# ---------------------------------------------------------------- (3) grouped reales
print()
print("=== (3) EPISODIOS grouped de 2 frentes (observacional, nueva regla) ===")
for s in (46, 77, 48, 12, 88):
    cfg = dict(CONFIG_V2)
    w = World(seed=s, episode_kind="lobos", **cfg)
    c = ReactiveCoordinator(w)
    w.reset()
    n1 = w.wolf_group_sizes[0]
    g1, g2 = np.arange(0, n1), np.arange(n1, w.n_wolves)
    cov1 = cov2 = det1 = det2_ = n2f = 0
    while True:
        wolves = np.asarray(w.wolves, dtype=float)
        c1m, c2m = wolves[g1].mean(0), wolves[g2].mean(0)
        if np.linalg.norm(c1m - c2m) > 60.0 and w.phase == "ESCOLTA":
            n2f += 1
            det = detected_ext(w)
            det1 += det[g1].mean(); det2_ += det[g2].mean()
            fidx = np.where(free_mask(w))[0]
            if fidx.size:
                dw = np.linalg.norm(wolves[:, None, :] - w.drones[fidx][None, :, :], axis=2)
                covered = (dw <= DETER_RADIUS).any(axis=1)
                cov1 += covered[g1].mean(); cov2 += covered[g2].mean()
        _o, _r, term, trunc, _i = w.step(c.act(w.get_observation()))
        if term or trunc:
            break
    n2f = max(n2f, 1)
    print("  seed %2d grupos %-6s -> sev=%d (%s, %d pasos) | 2-frentes: %d pasos | detectado medio G1=%.2f G2=%.2f | cobertura G1=%.2f G2=%.2f"
          % (s, str(tuple(w.wolf_group_sizes)), w.n_depredadas, w.status, w.step_count,
             n2f, det1 / n2f, det2_ / n2f, cov1 / n2f, cov2 / n2f))

print()
print("=== fin ===")
