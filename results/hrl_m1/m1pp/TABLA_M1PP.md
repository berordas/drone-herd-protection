# TABLA-ESCALERA STOP-M1'' (100 semillas emparejadas × defensas; capa K, v3.6)

| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_masa | Δ vs B_spawn | Δ vs B_oracle | gap run02 | gap run09 |
|---|---|---|---|---|---|---|---|---|
| masa_v36 | 0.57 | 0.62 | 0.53 | — | -0.41 [-0.64, -0.20] | -0.43 [-0.69, -0.18] | +0.05 [-0.06, +0.15] | -0.04 [-0.14, +0.05] |
| spawn_v36 | 0.98 | 0.85 | 0.87 | +0.41 [+0.20, +0.65] | — | -0.01 [-0.14, +0.10] | -0.14 [-0.34, +0.06] | -0.12 [-0.26, +0.03] |
| oracle_v36 | 1.00 | 0.91 | 0.99 | +0.43 [+0.19, +0.69] | +0.01 [-0.10, +0.14] | — | -0.09 [-0.29, +0.10] | -0.01 [-0.16, +0.14] |
| manager_M1pp_60k | 1.58 | — | — | +1.01 [+0.70, +1.34] | +0.59 [+0.33, +0.88] | +0.58 [+0.30, +0.86] | — | — |
| manager_M1pp_final | 2.26 | 2.20 | 2.17 | +1.69 [+1.32, +2.06] | +1.27 [+0.93, +1.62] | +1.26 [+0.93, +1.60] | -0.06 [-0.32, +0.19] | -0.10 [-0.27, +0.08] |

## P(1ª acción | estrato) y caza/ep — vs Reactive

### masa_v36
P(a|G) {'MASA': 1.0, 'CEBO_keep': 0.0, 'CEBO_d90': 0.0, 'CEBO_d180': 0.0} · P(a|S) {'MASA': 1.0, 'CEBO_keep': 0.0, 'CEBO_d90': 0.0, 'CEBO_d180': 0.0} · P(cebo|G,n≥3) 0.0 · dec/ep 2.2 · PENETRADO 28
caza/ep: option_starts 1.00 · retargets 0.27 · retargets_blocked 0.01 · refix_muerte 0.34 · refix_refugio 0.60 · refix_otro 0.00

### spawn_v36
P(a|G) {'MASA': 0.0, 'CEBO_keep': 1.0, 'CEBO_d90': 0.0, 'CEBO_d180': 0.0} · P(a|S) {'MASA': 1.0, 'CEBO_keep': 0.0, 'CEBO_d90': 0.0, 'CEBO_d180': 0.0} · P(cebo|G,n≥3) 1.0 · dec/ep 31.5 · PENETRADO 27
caza/ep: option_starts 1.00 · retargets 0.13 · retargets_blocked 0.00 · refix_muerte 0.88 · refix_refugio 0.68 · refix_otro 0.00

### oracle_v36
P(a|G) {'MASA': 0.0, 'CEBO_keep': 1.0, 'CEBO_d90': 0.0, 'CEBO_d180': 0.0} · P(a|S) {'MASA': 0.465, 'CEBO_keep': 0.0, 'CEBO_d90': 0.535, 'CEBO_d180': 0.0} · P(cebo|G,n≥3) 1.0 · dec/ep 44.2 · PENETRADO 8
caza/ep: option_starts 1.00 · retargets 0.04 · retargets_blocked 0.00 · refix_muerte 0.93 · refix_refugio 0.68 · refix_otro 0.00

### manager_M1pp_60k
P(a|G) {'MASA': 0.0, 'CEBO_keep': 0.828, 'CEBO_d90': 0.0, 'CEBO_d180': 0.172} · P(a|S) {'MASA': 0.0, 'CEBO_keep': 0.0, 'CEBO_d90': 0.0, 'CEBO_d180': 1.0} · P(cebo|G,n≥3) 1.0 · dec/ep 43.0 · PENETRADO 8
caza/ep: option_starts 4.49 · retargets 0.04 · retargets_blocked 0.00 · refix_muerte 1.53 · refix_refugio 0.54 · refix_otro 0.08

### manager_M1pp_final
P(a|G) {'MASA': 0.0, 'CEBO_keep': 0.483, 'CEBO_d90': 0.0, 'CEBO_d180': 0.517} · P(a|S) {'MASA': 0.0, 'CEBO_keep': 0.0, 'CEBO_d90': 0.0, 'CEBO_d180': 1.0} · P(cebo|G,n≥3) 1.0 · dec/ep 49.1 · PENETRADO 8
caza/ep: option_starts 4.47 · retargets 0.07 · retargets_blocked 0.00 · refix_muerte 2.01 · refix_refugio 0.62 · refix_otro 0.02

