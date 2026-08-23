"""v25_spawn_diag.py — Diagnóstico del spawn en subgrupos (v2.5, Nivel A). No es código del repo.

Verifica: (1) DETERMINISMO (misma seed => misma formación); (2) SUBSTREAM (grouped vs clustered:
vacas/drones/corzos/terneros BIT A BIT idénticos; con 1 grupo, también los lobos);
(3) GEOMETRÍA (2 grupos: sectores separados >= 60°, ancla del 2º en el borde como el 1º,
cúmulo apretado); (4) DISTRIBUCIÓN (frecuencia 1 vs 2 grupos y repartos, sembrado).
"""
import numpy as np

from baseline import CONFIG_V2, build_world
from world import WOLF_GROUP_MIN_ANGLE_SEP, World

CFG_CLUSTERED = dict(CONFIG_V2, wolf_spawn_mode="clustered")

# (1) DETERMINISMO
for s in (0, 3, 7, 11):
    a = build_world(s, "lobos"); a.reset()
    b = build_world(s, "lobos"); b.reset()
    assert a.wolf_group_sizes == b.wolf_group_sizes and a.wolf_spawn_angles == b.wolf_spawn_angles
    assert np.array_equal(a.wolves, b.wolves)
print("(1) determinismo: misma seed => misma formación (4 semillas) OK")

# (2) SUBSTREAM: grouped vs clustered -> todo lo demás bit a bit
n_wolves_eq = 0
for s in range(20):
    for kind in ("lobos", "mixto", "corzos"):
        g = World(seed=s, episode_kind=kind, **CONFIG_V2); g.reset()
        c = World(seed=s, episode_kind=kind, **CFG_CLUSTERED); c.reset()
        assert np.array_equal(g.cows, c.cows), "vacas divergen (s=%d %s)" % (s, kind)
        assert np.array_equal(g.drones, c.drones), "drones divergen (s=%d %s)" % (s, kind)
        assert np.array_equal(g.corzos, c.corzos), "corzos divergen (s=%d %s)" % (s, kind)
        assert g.n_calves == c.n_calves and (g.n_calves == 0 or np.array_equal(g.calves, c.calves))
        assert np.array_equal(g.battery, c.battery), "baterías divergen"
        if len(g.wolf_group_sizes) == 1 and g.n_wolves > 0:
            assert np.array_equal(g.wolves, c.wolves), "1 grupo debería ser ≡ clustered (s=%d)" % s
            n_wolves_eq += 1
print("(2) substream: 20 semillas x 3 tipos -> vacas/drones/corzos/terneros/baterías BIT A BIT;"
      " %d episodios con 1 grupo ≡ clustered en posiciones de lobos" % n_wolves_eq)

# (3) GEOMETRÍA de los episodios con 2 grupos
checked = 0
for s in range(200):
    w = build_world(s, "lobos"); w.reset()
    if len(w.wolf_group_sizes) != 2:
        continue
    n1, k = w.wolf_group_sizes
    a1, a2 = w.wolf_spawn_angles
    dang = abs((a2 - a1 + np.pi) % (2 * np.pi) - np.pi)
    assert dang >= WOLF_GROUP_MIN_ANGLE_SEP - 1e-9, "sectores demasiado juntos (s=%d: %.1f°)" % (s, np.degrees(dang))
    # ancla del 2º grupo: proyección al borde por angle2 (misma regla que el 1er grupo)
    center = np.array([w.W / 2, w.H / 2])
    d = np.array([np.cos(a2), np.sin(a2)])
    t = min((w.W / 2) / max(abs(d[0]), 1e-9), (w.H / 2) / max(abs(d[1]), 1e-9))
    anchor2 = center + d * t
    g2 = w.wolves[n1:]
    dist = np.linalg.norm(g2 - anchor2, axis=1)
    assert dist.max() < 6 * w.wolf_spawn_dispersion, "el 2º grupo no está en su ancla del borde (s=%d)" % s
    # cúmulos apretados y separados entre sí
    g1 = w.wolves[:n1]
    assert np.linalg.norm(g1.mean(axis=0) - g2.mean(axis=0)) > 50, "subgrupos demasiado cerca (s=%d)" % s
    checked += 1
print("(3) geometría: %d episodios con 2 grupos verificados (sep>=60°, ancla en el borde, cúmulos separados)" % checked)

# (4) DISTRIBUCIÓN (200 semillas de 'lobos')
from collections import Counter
splits, n_groups_count = Counter(), Counter()
elegibles = 0
for s in range(200):
    w = build_world(s, "lobos"); w.reset()
    n_groups_count[len(w.wolf_group_sizes)] += 1
    if w.n_wolves > 2:
        elegibles += 1
    if len(w.wolf_group_sizes) == 2:
        splits[tuple(w.wolf_group_sizes)] += 1
print("(4) distribución (200 semillas lobos): grupos=%s | elegibles n>2: %d | repartos=%s"
      % (dict(n_groups_count), elegibles, dict(splits)))
print("v25_spawn_diag: TODO OK")
