# E0.2 — Latencias → K (adenda §6)

**Regla pre-registrada:** terminación-por-evento = diseño PRINCIPAL de la Etapa 1 (p75 de t(inicio->commit) = 4345 > 2000); K = techo de revisión

p75 t(inicio→LURE_COMMIT) en celdas del manager: {'G_keep_reactive': 2299.0, 'S_d90_reactive': 4345.0} · celdas sin commit: []

K propuesto: None · frac. episodios lobos con ≥5 decisiones: None

ROC LURE_COMMIT — mejor Youden: {'min_drones': 4, 'gate_m': 60.0, 'cone_deg': 60.0, 'tpr': 1.0, 'fpr': 0.272, 'youden': 0.728, 'n': 475}

| celda | inicio→staged p50/p75/p90 (n) | staged→show | show→confirm | inicio→commit p50/p75/p90 (n) | release→muerte p50/p90 (n) |
|---|---|---|---|---|---|
| G_keep_reactive | 498/1496/3471 (375) | 0/0/0 (375) | 346/660/887 (343) | 1073/2299/4518 (225) | 626/1238 (236) |
| G_keep_run02 | 454/1289/3253 (372) | 0/0/0 (372) | 414/723/955 (348) | 952/2293/3939 (221) | 686/1586 (253) |
| G_d180_reactive | 4701/7444/19589 (29) | 0/0/0 (29) | -790/158/217 (27) | 3474/7290/13740 (33) | 87/1035 (17) |
| S_d90_reactive | 1657/4575/8146 (60) | 0/0/0 (60) | 354/540/602 (59) | 2313/4345/8376 (15) | 838/1125 (12) |
| S_d180_reactive | 7911/9858/16562 (23) | 0/0/0 (23) | 253/320/373 (17) | 6850/11546/17137 (11) | 599/1171 (8) |

| celda | T_safe (ESCOLTA→a salvo) p50/p75/p90 (n) | margen release p25/p50/p75 · P(<0) |
|---|---|---|
| G_keep_reactive | 988/1244/1525 (228) | 1113/1620/23138 · 0% (n=375) |
| G_keep_run02 | 1011/1230/1571 (229) | 1134/1644/23135 · 0% (n=372) |
| G_d180_reactive | 1347/1511/1608 (69) | 169/665/1110 · 0% (n=29) |
| S_d90_reactive | 1261/1456/1549 (73) | 1262/1684/3473 · 0% (n=60) |
| S_d180_reactive | 1267/1486/1560 (59) | 699/1070/10227 · 0% (n=23) |

## ROC completa (cono 60°)

| min_drones | puerta m | TPR | FPR | Youden |
|---|---|---|---|---|
| 2 | 40 | 1.0 | 0.837 | 0.163 |
| 2 | 50 | 1.0 | 0.779 | 0.221 |
| 2 | 60 | 1.0 | 0.589 | 0.411 |
| 2 | 70 | 0.993 | 0.381 | 0.612 |
| 3 | 40 | 1.0 | 0.432 | 0.568 |
| 3 | 50 | 1.0 | 0.323 | 0.677 |
| 3 | 60 | 1.0 | 0.293 | 0.707 |
| 3 | 70 | 0.993 | 0.272 | 0.721 |
| 4 | 40 | 1.0 | 0.308 | 0.692 |
| 4 | 50 | 1.0 | 0.275 | 0.725 |
| 4 | 60 | 1.0 | 0.272 | 0.728 |
| 4 | 70 | 0.993 | 0.269 | 0.724 |
