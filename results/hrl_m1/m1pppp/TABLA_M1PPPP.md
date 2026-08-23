# TABLA M1'''' (100 semillas emparejadas; IC bootstrap 10k; sev SIEMPRE sin coste)

| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_oracle | jugada completa | aborts/ep | stalls |
|---|---|---|---|---|---|---|---|
| B_masa | 0.56 | 0.60 | 0.52 | -1.10 [-1.41, -0.81] | None | 0.00 | 0 |
| B_spawn | 0.95 | 0.90 | 0.88 | -0.71 [-0.96, -0.47] | 1.0 | 0.00 | 0 |
| B_oracle | 1.66 | 1.64 | 1.69 | — | 1.0 | 0.28 | 9 |
| manager 60k | 1.73 | — | — | 0.07 [-0.01, 0.15] | 1.0 | 0.29 | 9 |
| manager final | 1.76 | 1.75 | 1.76 | 0.10 [0.03, 0.19] | 1.0 | 0.28 | 9 |

Δ(manager − B_spawn) vs reactive: 0.81 [0.56, 1.09]
Δ(manager − B_oracle) vs reactive: 0.10 [0.03, 0.19]
gap run02−reactive: manager -0.01 [-0.24, 0.20] · oráculo -0.02 [-0.23, 0.19]
gap run09−reactive: manager -0.01 [-0.14, 0.14] · oráculo 0.03 [-0.12, 0.17]

Manager censura: {"n_eps_cebo_n3": 134, "jugada_completa_frac": 1.0, "con_show_frac": 1.0, "con_staged_frac": 1.0, "con_strike_frac": 0.597, "t_show_mediana": 558.5}
P(a|G) 1ª: {'MASA': 0.0, 'CEBO_keep': 0.931, 'CEBO_d90': 0.069, 'CEBO_d180': 0.0}
P(a|S) 1ª: {'MASA': 0.0, 'CEBO_keep': 0.0, 'CEBO_d90': 1.0, 'CEBO_d180': 0.0}
P(cebo|G,n≥3): 1.0 · eventos: {'FIN_EPISODIO': 200, 'MUERTE': 285, 'K_MAX': 152, 'ABORT_BAIT_FAILED': 56}
caza/ep: {'option_starts': 2.415, 'retargets': 0.065, 'retargets_blocked': 0.0, 'refix_muerte': 1.545, 'refix_refugio': 0.81, 'refix_otro': 0.03}
