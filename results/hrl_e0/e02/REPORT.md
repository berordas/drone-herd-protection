# E0.2 — Latencias → K (adenda §6)

**Regla pre-registrada:** terminación-por-evento = diseño PRINCIPAL de la Etapa 1 (p75 de t(inicio->commit) = 4126 > 2000); K = techo de revisión

p75 t(inicio→LURE_COMMIT) en celdas del manager: {'G_keep_reactive': 2316.0, 'S_d90_reactive': 4126.25} · celdas sin commit: []

K propuesto: None · frac. episodios lobos con ≥5 decisiones: None

ROC LURE_COMMIT — mejor Youden: {'min_drones': 4, 'gate_m': 70.0, 'cone_deg': 60.0, 'tpr': 1.0, 'fpr': 0.305, 'youden': 0.695, 'n': 446}

| celda | inicio→staged p50/p75/p90 (n) | staged→show | show→confirm | inicio→commit p50/p75/p90 (n) | release→muerte p50/p90 (n) |
|---|---|---|---|---|---|
| G_keep_reactive | 494/1506/3541 (346) | 0/0/0 (346) | 418/712/893 (335) | 1160/2316/4537 (226) | 804/1446 (338) |
| G_keep_run02 | 450/1351/3361 (343) | 0/0/0 (343) | 434/723/991 (328) | 1071/2330/4143 (217) | 859/1483 (337) |
| G_d180_reactive | 5104/12290/19483 (46) | 0/0/0 (46) | -468/326/387 (38) | 3474/6395/13780 (41) | 129/608 (39) |
| S_d90_reactive | 1652/4529/9175 (77) | 0/0/0 (77) | 382/532/608 (71) | 2798/4126/8690 (32) | 933/1568 (73) |
| S_d180_reactive | 7536/11356/17599 (46) | 0/0/0 (46) | 254/418/646 (36) | 4036/9195/16543 (23) | 391/814 (39) |

| celda | T_safe (ESCOLTA→a salvo) p50/p75/p90 (n) | margen release p25/p50/p75 · P(<0) |
|---|---|---|
| G_keep_reactive | 1146/1399/1666 (304) | 1114/1461/1874 · 0% (n=346) |
| G_keep_run02 | 1095/1399/1784 (306) | 1074/1393/1962 · 0% (n=343) |
| G_d180_reactive | 1166/1341/1543 (62) | 198/490/989 · 0% (n=46) |
| S_d90_reactive | 1157/1383/1583 (79) | 818/1392/1779 · 0% (n=77) |
| S_d180_reactive | 1094/1320/1439 (61) | 164/677/1225 · 0% (n=46) |

## ROC completa (cono 60°)

| min_drones | puerta m | TPR | FPR | Youden |
|---|---|---|---|---|
| 2 | 40 | 1.0 | 0.921 | 0.079 |
| 2 | 50 | 1.0 | 0.843 | 0.157 |
| 2 | 60 | 1.0 | 0.664 | 0.336 |
| 2 | 70 | 1.0 | 0.415 | 0.585 |
| 3 | 40 | 1.0 | 0.657 | 0.343 |
| 3 | 50 | 1.0 | 0.491 | 0.509 |
| 3 | 60 | 1.0 | 0.399 | 0.601 |
| 3 | 70 | 1.0 | 0.314 | 0.686 |
| 4 | 40 | 1.0 | 0.509 | 0.491 |
| 4 | 50 | 1.0 | 0.425 | 0.575 |
| 4 | 60 | 1.0 | 0.368 | 0.632 |
| 4 | 70 | 1.0 | 0.305 | 0.695 |
