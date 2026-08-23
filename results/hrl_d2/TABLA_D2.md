# TABLA D2 (100 semillas emparejadas por celda; IC bootstrap 10k)

| defensa \ atacante | natural | cebo 2f | manager lobo | PENETRADO (nat/cebo/mgr) | cambios/ep | stalls |
|---|---|---|---|---|---|---|
| dummy | 1.13 | 3.11 | 2.75 | 0/0/0 | — | 0 |
| reactive | 0.74 | 2.61 | 1.76 | 25/6/20 | — | 0 |
| proporcional | 0.25 | 0.85 | 0.61 | 32/434/72 | — | 0 |
| run09 | 0.69 | 2.53 | 1.77 | 0/27/10 | — | 0 |
| dronemgr | 0.21 | 1.03 | 0.67 | 42/529/146 | 1.2033333333333334 | 189 |

Δ(dronemgr − reactive) vs natural: -0.53 [-0.85, -0.25]
Δ(dronemgr − proporcional) vs natural: -0.04 [-0.13, +0.05]
  dronemgr vs natural: KNC 0.0 · jugada atacante 0.22 · gana_guardia 0.885 (n 26) · latencia 9.6 · reasignaciones 2.4
Δ(dronemgr − reactive) vs cebo2f: -1.58 [-2.03, -1.14]
Δ(dronemgr − proporcional) vs cebo2f: +0.18 [+0.01, +0.37]
  dronemgr vs cebo2f: KNC 0.0 · jugada atacante 1.0 · gana_guardia 0.868 (n 91) · latencia 9.6 · reasignaciones 1.23
Δ(dronemgr − reactive) vs manager: -1.09 [-1.35, -0.85]
Δ(dronemgr − proporcional) vs manager: +0.06 [-0.04, +0.17]
  dronemgr vs manager: KNC None · jugada atacante 0.67 · gana_guardia 0.84 (n 106) · latencia 12.1 · reasignaciones 0.67
