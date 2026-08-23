# TABLA RÉPLICA D2 (seed 1) — 100 semillas emparejadas por celda; IC bootstrap 10k

| defensa \ atacante | natural | cebo 2f | manager lobo | PENETRADO (nat/cebo/mgr) | cambios/ep | stalls |
|---|---|---|---|---|---|---|
| reactive | 0.74 | 2.61 | 1.76 | 25/6/20 | — | 0 |
| proporcional | 0.25 | 0.85 | 0.61 | 32/434/72 | — | 0 |
| dronemgr | 0.21 | 1.03 | 0.67 | 42/529/146 | 1.2 | 189 |
| dronemgr_r1 | 0.21 | 1.06 | 0.76 | 92/514/108 | 1.55 | 147 |

Δ(RUN-D2 (seed 0) − reactive) vs natural: -0.53 [-0.85, -0.25]
Δ(réplica (seed 1) − reactive) vs natural: -0.53 [-0.86, -0.22]
Δ(AMBOS aprendices − reactive) vs natural (200 pares, 2 seeds; SOLO barra de error): -0.53 [-0.76, -0.32]
Δ(RUN-D2 (seed 0) − proporcional) vs natural: -0.04 [-0.13, +0.04]
Δ(réplica (seed 1) − proporcional) vs natural: -0.04 [-0.12, +0.03]
Δ(AMBOS aprendices − proporcional) vs natural (200 pares, 2 seeds; SOLO barra de error): -0.04 [-0.10, +0.01]
  réplica vs natural: KNC 0.0 · jugada atacante 0.22 · gana_guardia 0.815 (n 27) · latencia 35.5 · reasignaciones 2.71 · PENETRADO 2f n/d

Δ(RUN-D2 (seed 0) − reactive) vs cebo2f: -1.58 [-2.03, -1.14]
Δ(réplica (seed 1) − reactive) vs cebo2f: -1.55 [-1.98, -1.13]
Δ(AMBOS aprendices − reactive) vs cebo2f (200 pares, 2 seeds; SOLO barra de error): -1.56 [-1.88, -1.26]
Δ(RUN-D2 (seed 0) − proporcional) vs cebo2f: +0.18 [+0.00, +0.38]
Δ(réplica (seed 1) − proporcional) vs cebo2f: +0.21 [+0.03, +0.40]
Δ(AMBOS aprendices − proporcional) vs cebo2f (200 pares, 2 seeds; SOLO barra de error): +0.20 [+0.07, +0.33]
  réplica vs cebo2f: KNC 0.0 · jugada atacante 1.0 · gana_guardia 0.857 (n 91) · latencia 18.3 · reasignaciones 2.34 · PENETRADO 2f n/d

Δ(RUN-D2 (seed 0) − reactive) vs manager: -1.09 [-1.35, -0.84]
Δ(réplica (seed 1) − reactive) vs manager: -1.01 [-1.26, -0.77]
Δ(AMBOS aprendices − reactive) vs manager (200 pares, 2 seeds; SOLO barra de error): -1.05 [-1.23, -0.88]
Δ(RUN-D2 (seed 0) − proporcional) vs manager: +0.06 [-0.04, +0.17]
Δ(réplica (seed 1) − proporcional) vs manager: +0.14 [+0.02, +0.28]
Δ(AMBOS aprendices − proporcional) vs manager (200 pares, 2 seeds; SOLO barra de error): +0.10 [+0.02, +0.19]
  réplica vs manager: KNC None · jugada atacante 0.67 · gana_guardia 0.776 (n 107) · latencia 104.1 · reasignaciones 1.0 · PENETRADO 2f n/d

## Predicciones del PREREGISTRO RÉPLICA D2
1. Estructura se reproduce (P(guardia|2cl) ≥ 0.90 y P(3-1|2cl) ≤ 0.10): P(guardia|2cl)=0.943 P(a|2cl)={'4-0': 0.057, '3-1': 0.019, '2-2': 0.925} P(a|1cl)={'4-0': 0.897, '3-1': 0.0, '2-2': 0.103} ⇒ CUMPLIDA
2. Δ(réplica − proporcional) vs cebo-2f positivo y solapa con [+0.01, +0.37]: ver arriba; conjunto +0.20 [+0.07, +0.33] ⇒ CUMPLIDA (solape: adjudicar a mano con el IC de la réplica)
3. Δ vs Reactive con IC excluyendo 0 en las 3 celdas: natural -0.53 [-0.76, -0.32], cebo2f -1.56 [-1.88, -1.26], manager -1.05 [-1.23, -0.88]
4. PENETRADO ≥ proporcional en natural y cebo-2f: natural 92 vs 32, cebo2f 514 vs 434, manager 108 vs 72
ligera final réplica: sev 0.175 stalls 2 cambios/ep 0.4 pen 19.425
