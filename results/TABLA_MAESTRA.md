# TABLA MAESTRA DEL PROYECTO — todos los runs y celdas, con sus artefactos (CIERRE TOTAL, KILL-DATE del dueño)

Convenciones: `/data` = `$HOME/rl_data` (host) · **sev** = muertes por episodio (media sobre 100
semillas por tipo; formato **lobos / corzos / mixto** o **lobos / mixto**; IC = bootstrap 95 % 10k sobre pares
emparejados por semilla) · **KNC** = fracción de muertes por el canal trasero (cebo) · **ancla** = fracción de
episodios con el clúster de cebo anclado · repo `$HOME/drone-herd-protection` (= `/workspace`),
`DISEÑO.md` = memoria viva (diario arriba). Esta tabla no añade mediciones: recopila lo ya adjudicado en cada
informe; cuando dos fuentes difieren por redondeo se cita el crudo en §7. Construida 2026-08-22 (réplica D2
completada; fila §5.3 rellenada al cerrar, 2026-08-23).

## 0. Versiones de física del mundo (tags de git)

| tag | commit | fecha | qué cambió | metro (Dummy · Reactive) |
|---|---|---|---|---|
| v2.4.1 … v3.2 | `0097e32` … `3bf39a5` | 07-14 … 07-23 | historia pre-v3.4 (subgrupos v2.5, percepción realista v2.6, dos radios v2.7, barrera honesta v2.8, …) | v2.4.1 4.54/2.77 · v2.6 2.74 · v2.8 2.56/0/2.26 · v3.2 1.91/0/1.96 |
| **v3.4-baseline** | `bfd78bf` | 07-24 | línea rígida + trinquete + roles invertidos del cebo; corredor central = gotera (luego reconocida como defecto) | 3.82/0/3.84 · **2.68/0/2.77** |
| (v3.5 solape, NO congelado) | repo en `bfd78bf` | 08-03 | medición de `drone_spacing` < 20: s=4 cierra los cruces pero colapsa el frente ⇒ el dueño mantuvo v3.4 | `/data/wolves/diag/v35_informe.md` |
| **v3.5-sonido** | `8aeaf89` (tag anotado `3e0c8a0`) | 08-19 | regla del sonido: expulsión a ≤ DETER_RADIUS=20 de cualquier ACTIVE sin requisito de aproximación; re-gold consciente | 1.90/0/2.02 · **0.88/0/0.76** |
| v3.6-patrol-estatica | `caeb683` (Commit L) | 08-20 | config, no física: `patrol_omega` 0.02→0 (STRANDED 2.95→0/ep) | Reactive-est 0.94/0/0.93 |
| **v3.7-relevo-centinela** | `a2b8166` (Commit R) | 08-21 | el ACTIVE bajo se clava, el READY vuela directo y HEREDA la ranura (cierra bandera 14: rotación espuria de ranuras desde v3.0) | 1.91/0/2.06 · 0.93/0/0.69 |
| **v3.7.1-plazas-estacion** | `3989ef8` (Commit T) | 08-22 | plazas fijas en la estación; inocuidad 50 pares Δsev = 0.000 (`/data/hrl_m1/m1pppp/inocuidad_v371.resumen.json`) | oficial para D2+ |

## 1. MARL de drones (`/data/drones/`) — PPO/CTDE residual sobre la barrera, 20 M pasos-agente

| run | fecha | física | seed | duración / fps | resultado (vs Reactive) | veredicto | artefactos |
|---|---|---|---|---|---|---|---|
| run01 | 07-18 | v2.6 | 0 | 5,5 h / 1010 | final 2.35/0/2.34 vs 2.74/0/2.82 (Δ −0.39/−0.48); rapidez +17 %, sustos +26 %, sin reparto | bate la barrera; **histórico** (invalidado por v2.7) | `/data/drones/run01/{model.zip, eval_model.json, comportamiento_run01.json, *.gif}` |
| **run02_v34** | 08-03/04 | v3.4 | 0 | 6 h 03 / 920 | final **2.40/0/2.27** vs 2.68/0/2.77 (Δ −0.28/−0.50); gotera 3.47→2.36/ep (−32 %); reparto 5.7→5.3 % (NO emerge); guardias 0/76 | **bate la barrera v3.4**; en v3.5 vale 1.09/0/0.78 | `/data/drones/run02_v34/{model.zip, eval_final_20M.json, eval_best_18M.json, eval_floor_drones.json, comportamiento_*.json}` · `/data/gifs/run02_v34/` |
| **run09_v35** | 08-19 | v3.5 | 0 | 7 h 57 / 701 | sin informe propio; como defensa: v3.6 órbita 0.79/0/0.78 · v3.7 estática 0.77/0/0.62 · E0.4 v3.7.1 **0.69 / 2.53 / 1.78** (natural / cebo-2f / manager lobo) | defensa de transferencia de M1''→M1'''' y listón en E0.4 | `/data/drones/run09_v35/{model.zip, summary.json}` · `/data/hrl_m1/m1pppp/metro/run09_en_v37_*.json` · `/data/hrl_d2/e04_run09__*.json` |

## 2. Lobos aprendidos pre-jerárquicos (`/data/wolves/`) — ¿emerge el CEBO (2 frentes) por PPO puro?

| run | fecha | física | pasos / duración / fps | resultado (lobos / mixto; scriptado = nota a batir) | veredicto | artefactos |
|---|---|---|---|---|---|---|
| run01 | 07-14 | v2.4.1 | abortado a 2,48 M / — / 1070 | recompensa rala 0.000 todo el run | ABORTADO | `/data/wolves/run01/` |
| run02 | 07-15 | v2.4.1 | 10 M / 3 h / 918 | **0.57 / 0.60** (vs 2.77/2.80) | meseta robusta | `/data/wolves/run02/{model.zip, eval_final_10M.json, eval_best_5.5M.json}` |
| BC (plan C) | 07-15 | v2.4.1 | 120 k pares | clon 0.2/10; techo de la etiqueta media 2.60 | cuna no válida por sí sola | `/data/wolves/demos/`, `diag/techo.log` |
| run03 | 07-15/16 | v2.4.1 | 10 M / 4,5 h / 613 | **0.65 / 0.72** (cuna +0.08/+0.12) | el flanqueo es el muro | `/data/wolves/run03/` |
| run04 | 07-16 | v2.4.1 | 10 M / 4,3 h / 648 | residual: mejor 1,5 M **2.82 / 2.81** (Δ +0.05/+0.01 sobre el suelo 2.78/2.81) | Δ ≈ 0 ⇒ cierre de la fase "lobos aprendidos" | `/data/wolves/run04/`, `run04_floor.json` |
| run05_nivelB | 07-17/18 | v2.6 | parado a 4,2 M (guardia) | 2.67/2.71 (Δ −0.07/−0.11); cebo_diag 0.0 % | cebo NO emerge (1ª) | `/data/wolves/run05_nivelB/checkpoints/`, `cebo_ppo_wolves_*.json` |
| run06_curric | 07-20/21 | v2.7 | 20 M / 8 h 49 / 630 | **1.90 / 1.88** (Δ −0.40/−0.54); cebo 0.0 % | cebo NO cruza el valle (2ª) | `/data/wolves/run06_curric/{model.zip, eval_*.json, cebo_*.json}` |
| run07_curric_v28 | 07-21/22 | v2.8 | 20 M / 9 h 53 / 562 | **1.93 / 1.87** (Δ −0.63/−0.39); KNC 0.0 % en todos los ckpts | cebo NO emerge (3ª); currículo agotado | `/data/wolves/run07_curric_v28/`, `diag/run07_*.gif` |
| **run08_dieta50** | 08-04/05 | v3.4 | 10 M / 5 h 53 / 472 | final **2.17 / 2.25** (Δ −0.51/−0.52); **KNC 26.6 → 21.0 → 13.0 %**, sev-2f 3.50→2.65, ancla 65.5→53.4 % | (3) ESTRUCTURAL: la dieta no arranca el cebo, PPO de equipo lo EROSIONA ⇒ jerárquico justificado | `/data/wolves/run08_dieta50/{model.zip, eval_*.json, cebo_*.json, ancla_*.json}` · `/data/gifs/run08_dieta50/` |

## 3. Etapa 0 — jerárquico (capa de opciones lobo) + v3.5 sonido (`/data/hrl_e0/`, `/data/metro_v35/`)

| celda | fecha | física | n | resultado | veredicto | artefactos |
|---|---|---|---|---|---|---|
| E0.A (STOP-1) | 08-17 | v3.4 + capa | 58 pares + 40 | 58/58 severidades idénticas (impuesto de interfaz 0); CEBO Δ180 desde spawn: 1.90 [1.40,2.42] | G0 PASA | `/data/hrl_e0/e0a/{REPORT.md, results.json, gifs/}` |
| E0.1 (STOP-2) | 08-17 | v3.4 | 2.184 eps; 346 pares | Δ(CEBO_keep − MASA \| G, n≥3) **+0.43 [+0.25,+0.62]**; S: Δ180 −1.12, Δ90 −0.44; KNC CEBO 25 % | G1 PASA (el valor vive en G) | `/data/hrl_e0/e01/{REPORT.md, results.json, gifs/}`, `STOP2_INFORME.md` |
| E0.2 | 08-18 | v3.4 | sobre E0.1 | p75 inicio→commit 2.316 (G) / 4.126 (S) > 2.000 ⇒ terminación-por-evento; ROC J=0.695 | regla pre-registrada dispara | `/data/hrl_e0/e02/REPORT.md` |
| Forense seed 398 (STOP-F1) | 08-18 | v3.4 | 2 eps | cruce con dron a 9.96 m y approach −0.57 < 1 ⇒ expulsión inactiva; apilamiento 246 ticks-par < 3 m | ⇒ orden del dueño: v3.5 sonido; apilamiento = decisión pendiente (future work) | `/data/hrl_e0/forense/{FORENSE.md, INDEX.md}` |
| Metro v3.5 | 08-18/19 | v3.5 | 100/tipo | Dummy 1.90/0/2.02 · **Reactive 0.88/0/0.76** · suelo 0.92/0/0.81 · run02 1.09/0/0.78 · cebo 2f 2.60 KNC 37.7 % | nueva nota a batir | `/data/metro_v35/` |
| E0.A v3.5 | 08-19 | v3.5 | 98 | 58/58 idénticas; sev 2.60; (iii) 0.47 | G0 PASA | `/data/hrl_e0/v35/e0a/` |
| **E0.1 v3.5 (STOP-2')** | 08-19 | v3.5 | 2.300 eps; 375 pares | **+0.85 [+0.60,+1.09]**; n3 +1.21 / n4 +0.85 / n5 +0.45; S: Δ90 **+0.32 [+0.04,+0.64]**; G/Δ180 −0.93; 4/4 predicciones | G1 PASA | `/data/hrl_e0/v35/e01/{REPORT.md, INDEX.md, gifs/}`, `STOP2prima_INFORME.md` |
| E0.2 v3.5 | 08-19 | v3.5 | — | p75 2.299 / 4.345; ROC J=0.728 | terminación-por-evento (K techo 4.500) | `/data/hrl_e0/v35/e02/` |
| E0.3 / E0.5 | — | — | — | NO corridos (E0.3 sustituido por mini-E0.3 en v3.6: Dummy 1.98, Reactive-est 0.15-0.18 con n=2) | congelados (future work) | `hrl/run_e0.py`, `/data/hrl_m1/m1pp/mini_e03.json` |

## 4. Etapa 1 — manager jerárquico del bando LOBO (`/data/hrl_m1/`)

### 4.1 Re-nivelados (100 semillas × {lobos, mixto} = 200 eps emparejados; vs Reactive / run02 / run09)

| versión | B_masa | B_spawn | **B_oracle** | celdas / sanity | fuente |
|---|---|---|---|---|---|
| v3.5 (órbita) | 0.585 / 0.685 | 0.82 / 0.935 | **0.885 [0.645,1.14] / 1.02** | — | `/data/hrl_m1/eval/{masa,spawn,oracle}__*.json`, `PREREGISTRO.md` |
| v3.6 (estática, capa K) | 0.57 / 0.62 / 0.53 | 0.99 / 0.85 / 0.87 | **1.00 [0.74,1.28] / 0.91 / 0.99** | celdas S CONTAMINADAS (gate ±25°): MASA 0.33 / Δ90 0.58 / Δ180 0.50; sanity +1.16 | `/data/hrl_m1/eval/*_v36__*.json`, `/data/hrl_m1/m1pp/{STOP_NIVELADO_INFORME.md, PREREGISTRO_v2.md, celdas_s_v36.json}` |
| **v3.7 (relevo; capa S1+S2+S3+CENSURA+Q+Q-bis+V2)** | 0.56 / 0.605 / 0.515 | 0.95 / 0.90 / 0.88 | **1.66 [1.355,1.97] / 1.64 / 1.69** | celdas S LIMPIAS: **MASA 0.30 · Δ90 1.71 · Δ180 1.42**; Δ(Δ180−Δ90) −0.29 [−0.76,+0.17]; sanity +1.16 [+0.38,+1.94]; tripwire Δ90 9 % / Δ180 25 % | `/data/hrl_m1/eval/*_v37__*.json`, `/data/hrl_m1/m1pppp/{celdas_s_v37.json, sanity_capa_v37.json, PREREGISTRO_v3.md, metro/}` |
| v3.7 pineado `4bf5024` — celdas G | — | — | — | **keep 2.76 · Δ180 2.84 · Δ90 2.51**; Δ(Δ180−keep) **+0.08 [−0.22,+0.38]** ⇒ paisaje G PLANO | `/data/hrl_m1/m1pppp/celdas_g_v37.json` |
| v3.7 → v3.7.1 inocuidad | — | — | — | 50 pares Δsev 0.000, 0 pares distintos | `/data/hrl_m1/m1pppp/inocuidad_v371.resumen.json` |

### 4.2 Runs del manager lobo (PPO [64,64], 24 envs, 122.880 macro-pasos, ligera 10k/40 semillas; eval 100 semillas × {lobos, mixto})

| run | fecha | física / capa | seed | duración / fps | resultado | veredicto / firma | artefactos |
|---|---|---|---|---|---|---|---|
| **M1** | 08-19 | v3.5 órbita, capa pre-K | 0 | 5 h 15 / 6.5 | **1.31 [1.02,1.62]** / 1.20; Δ vs B_oracle **+0.42 [+0.23,+0.63]**; P(keep)=1.0 en G y S; ABORT 99/ep; KNC 40.1 % | Estructura FALLA; +0.42 = exploit de interfaz (re-fijación de presa por churn) ⇒ Commit K | `/data/hrl_m1/M1/{model.zip, visionado/}`, `/data/hrl_m1/eval/manager_M1_*`, `STOP_M1_INFORME.md` |
| **M1'' (M1pp)** | 08-20 | v3.6 estática, capa K, wolves_min 3 | 0 | 5 h 25 / 6.3 | **2.26 / 2.20 / 2.17**; Δ vs B_oracle **+1.26 [+0.93,+1.60]**; P(Δ180\|S)=1.0; G keep 0.48/Δ180 0.52; ABORT 45/ep; dec/ep 49 | NO ADJUDICABLE (VERIF-0: gate ±25° interbloqueaba 9/20 del oráculo en S; molinillo de rumbo) | `/data/hrl_m1/M1pp/`, `/data/hrl_m1/eval/manager_M1pp_*`, `/data/hrl_m1/m1pp/{STOP_M1PP_INFORME.md, TABLA_M1PP.md, visionado/}` |
| VERIF-0 / MESETA | 08-20/21 | v3.6 | — | 20 eps oráculo-S | 9/20 interbloqueo; seed 14 meseta d_prey 222-233 m | PARAR ⇒ S1/S2/CENSURA/Q/Q-bis/S3/R/V2 | `/data/hrl_m1/m1pppp/{VERIF0_INFORME.md, HALLAZGO_MESETA_INFORME.md, verif/, patches/}` |
| **M1'''' (M1pppp) — RESULTADO PRINCIPAL** | 08-21 | v3.7, capa completa, coste 0.05 | 0 | 5 h 44 / 5.96 | **1.76 / 1.75 / 1.76**; **Δ vs B_oracle +0.10 [+0.03,+0.19]** (estrella); Δ vs B_spawn +0.81; **P(keep\|G)=0.931 · P(Δ90\|S)=1.000 · P(Δ180)=0**; jugada completa 1.00; ABORTs/ep 0.28; dec/ep 3.5; STALLs 9 (= los 9 del oráculo); KNC 36.3 %; canal B 0; despertar tardío 0 | **CUMPLE el criterio pre-registrado** (firma 2 del dueño, 08-21/22; commit `4bf5024`) | `/data/hrl_m1/M1pppp/{model.zip, summary.json}`, `/data/hrl_m1/eval/manager_M1pppp_{60k,final}__*.json`, `/data/hrl_m1/m1pppp/{STOP_M1PPPP_INFORME.md, TABLA_M1PPPP.md, PREREGISTRO_v3.md, visionado/ (6 GIFs + relevo + INDEX), canal_*_v37.json}` |
| **M2** (ablación K=1000 fijo) | 08-21/22 | v3.7 exacto | 0 | 1 h 46 / 19.4 | **1.62 [1.32,1.93]**; **Δ(M2−M1'''') −0.145 [−0.265,−0.04]**; vs oráculo −0.04; P(Δ180\|G)=0.86; P(Δ90\|S)=1.0; jugada completa 1.00 | predicción (colapso) FALLÓ; **firmado "ingrediente del MARGEN, no del MECANISMO"** | `/data/hrl_m1/M2/`, `/data/hrl_m1/eval/manager_M2_final__reactive.json`, `/data/hrl_m1/m1pppp/{STOP_M2_INFORME.md, PREREGISTRO_M2.md}` |
| **M1pppp_r1** (réplica) | 08-22 | v3.7 PINEADO `4bf5024` (worktree `wt_v37_replica`) | **1** | 6 h 04 / 5.63 | **1.69 [1.375,2.01]**; Δ(R1−M1'''') **−0.075 [−0.20,+0.045]**; vs oráculo +0.03 [−0.12,+0.18]; P(Δ90\|S)=1.0; P(Δ180\|G)=0.931; jugada completa 0.955; STALLs 18 | competencia + estructura-S REPRODUCIDAS; estrella y keep\|G = propiedades del run principal; **claim del TFG re-formulado (firmado)** | `/data/hrl_m1/M1pppp_r1/{model.zip, summary.json, PIN_REPLICA.txt}`, `/data/hrl_m1/eval/manager_M1pppp_r1_final__reactive.json`, `/data/hrl_m1/m1pppp/STOP_REPLICA_INFORME.md` |

## 5. D2 — manager jerárquico del bando DRON (`/data/hrl_d2/`; v3.7.1; celdas natural / cebo-2f / manager lobo M1'''' congelado; 100 pares, columna manager n=200)

### 5.1 E0.4 — listones (GO/NO-GO firmado GO)

| defensa | natural | cebo 2f | manager lobo | KNC · gana_guardia · reasignaciones/ep · PENETRADO | artefactos |
|---|---|---|---|---|---|
| Dummy | 1.13 | 3.11 | 2.75 | — | `e04_dummy__*.json` |
| Reactive-est 4-0 | 0.74 | 2.61 | 1.76 (crudo 1.765) | PENETRADO 25/6/20 | `e04_reactive__*.json` |
| **PROPORCIONAL (listón, clip(n_sec,0,2))** | **0.25** | **0.85** | **0.61** | KNC 0.0 · 0.78/0.80/0.82 · 1.95/22.3/9.8 · 32/434/72 | `e04_proporcional__*.json`, `INFORME_GO_NOGO_D2.md` |
| run09 (MARL) | 0.69 | 2.53 | 1.77 (crudo 1.775) | PENETRADO 0/27/10 | `e04_run09__*.json` |

### 5.2 RUN-D2 (seed 0; 122.880 macro-pasos, 2 h 58, fps 11.5, sin NaN; PREREGISTRO_D2 congelado antes; gate 40k PASA)

| | natural | cebo 2f | manager lobo |
|---|---|---|---|
| **manager dron D2** | **0.21** | **1.03** | **0.67** |
| Δ vs Reactive | −0.53 [−0.85,−0.25] | −1.58 [−2.03,−1.14] | −1.09 [−1.35,−0.85] |
| Δ vs proporcional (δ=0.15) | −0.04 [−0.13,+0.05] ✔ | **+0.18 [+0.01,+0.37] ✗** | +0.06 [−0.04,+0.17] ✔ |
| gana_guardia · latencia · reasignaciones | 0.885 · 9.6 · 2.4 | 0.868 · 9.6 · 1.2 | 0.84 · 12.1 · 0.7 |
| PENETRADO D2 / proporcional (2f) | 42 / 32 (67 / 21) | 529 / 434 | 146 / 72 (**36 / 49**) |
| STALLs (eps con STALL) | 153 (32/100) | 20 (17/100) | 16 (11/200) |

Estructura: P(4-0 | 1 clúster) 0.756 · **P(guardia | 2º clúster) 1.000, siempre 2-2 (3-1 = 0)** · KNC 0.0 ·
cambios/ep 0.3 · coste 0.014/ep. **Veredicto firmado: ÉXITO PARCIAL** (2 de 3 celdas no-inferiores; Estructura
PASA; hallazgo no anticipado 2-2; predicción 3 (PENETRADO) FALLIDA = trade-off cobertura/reparto GRAFICADO;
STALLs = seguro aprendido). Artefactos: `/data/hrl_d2/D2/{model.zip, summary.json, eval_ligera.jsonl}`,
`e04_dronemgr__*.json`, `TABLA_D2.md`, `flags_d2.json`, `STOP_D2_INFORME.md` (§FIRMA), `PREREGISTRO_D2.md`,
`visionado/` (reparto_entero_seed43 sev 0 · peor_dronemgr_seed77 sev 6 · decision_4_0_seed4; INDEX.md),
`penetrado_tradeoff.{png,json,py}`.

### 5.3 RÉPLICA D2 (D2_r1, seed 1; receta idéntica; pre-registro congelado ANTES del run; 3 h 20, fps 10.3, sin NaN)

| | natural | cebo 2f | manager lobo |
|---|---|---|---|
| **réplica D2 (seed 1)** | **0.21** | **1.06** | **0.76** |
| Δ vs Reactive | −0.53 [−0.86,−0.22] | −1.55 [−1.98,−1.13] | −1.01 [−1.26,−0.77] |
| Δ vs proporcional (δ=0.15) | −0.04 [−0.12,+0.03] ✔ | **+0.21 [+0.03,+0.40] ✗** | +0.14 [+0.02,+0.28] ✔ (marginal) |
| **Δ conjunto 2 aprendices (200 pares; solo barra de error)** | **−0.04 [−0.10,+0.01]** | **+0.20 [+0.07,+0.33]** | **+0.10 [+0.02,+0.19]** |
| gana_guardia · latencia · reasignaciones | 0.815 · 35.5 · 2.7 | 0.857 · 18.3 · 2.3 | 0.776 · 104.1 · 1.0 |
| PENETRADO réplica / proporcional (2f) | 92 / 32 (288 / 21) | 514 / 434 | 108 / 72 (185 / 49) |
| STALLs (eps) | 112 (33) | 22 (21) | 13 (13) |

Estructura reproducida: P(guardia | 2º clúster) 0.943 · 2-2 0.925 · 3-1 0.019 · P(4-0 | 1 clúster) 0.897. Predicciones
1-4 del pre-registro de la réplica CUMPLIDAS; sin anomalía ⇒ sin visionado. El hallazgo "36 vs 49" de RUN-D2 NO se
reproduce (propiedad del seed 0). Artefactos: `/data/hrl_d2/D2_r1/{model.zip, summary.json, eval_ligera.jsonl}`,
`e04_dronemgr_r1__*.json`, `TABLA_D2_R1.md`, `penetrado_tradeoff_dronemgr_r1.png`, `STOP_D2_INFORME.md` (§ RÉPLICA),
`PREREGISTRO_D2.md` (pre-registro + gate 40k de la réplica).

### 5.4 Resumen D2 en dos runs (claim del bando dron)

Estructura (guardias ante el 2º clúster, siempre 2-2) en **2/2 runs** · aplasta a la Reactive 4-0 en **3/3 celdas × 2 runs**
(IC excluye 0) · no-inferior a la proporcional en natural (2/2) y contra el manager lobo (2/2 en puntual; marginal en la
réplica) · **FALLA contra el cebo scriptado 2f en 2/2 (+0.18, +0.21; conjunto +0.20 [+0.07, +0.33])**.

## 6. Future work (anotado; NINGÚN run nuevo por KILL-DATE)

- **proporcional-2-2**: la regla destilada de D2 (ante un 2º clúster, dos guardias y línea de dos, sin
  parpadeo); no se mide para no contaminar el listón pre-registrado.
- Trade-off cobertura/reparto (PENETRADO ↑ con la línea de dos): graficado, no optimizado.
- STALLs de guardias ociosos en episodios tranquilos: seguro aprendido contra la distribución de train;
  candidato a un término de coste por guardia ocioso (no probado).
- Apilamiento de lobos en PENETRADO (`order[s % n_lobos]`, forense seed 398): decisión pendiente desde Etapa 0.
- E0.3 (quórum) y E0.5 (conmutación) nunca corridos; run09 nunca medido contra M1 (v3.5).
- Paisaje G plano: keep vs Δ180 no distinguibles en celdas; la política varía por semilla donde el paisaje
  no decide.
- Celda cebo-2f del manager dron (+0.18): única celda fallida; la réplica aporta solo la barra de error.

## 7. Fe de erratas / notas de consistencia (detectadas en el inventario del cierre)

1. **STALLs de RUN-D2: "189 en 300 episodios"** (STOP_D2_INFORME §2, firma del dueño, DISEÑO.md, memoria) —
   el denominador correcto es **400 episodios** (100 + 100 + 200 de la columna manager); los 189 STALLs y el
   reparto por celda (153/20/16; eps 32/17/11) son correctos.
2. Fechas "2026-08-23" en DISEÑO.md (cabecera: firmas 3, RUN-D2) y en la memoria: todos esos hechos son del
   **2026-08-22** (firmas M2/réplica 13:39Z, GO 13:40Z, RUN-D2 14:44→17:38, firma STOP-D2 19:12Z).
3. Redondeos: Reactive vs manager lobo 1.76/1.77 (crudo 1.765); run09 1.77/1.78 (1.775); M1'''' 1.76/1.75/1.76
   (1.765/1.755/1.76); B_spawn v3.6 0.99/0.98; M2 fps 19.4 (19.36); M1 5 h 15 / 6.5 fps (18.882 s / 6.51).
4. `PIN_REPLICA.txt` de la réplica M1'''' vivía solo en el worktree; copiado a `/data/hrl_m1/M1pppp_r1/`.
5. El tag `v3.5-sonido` es anotado: objeto `3e0c8a0`, commit `8aeaf89` (citar el commit).
6. Cierre de Etapa 1: firma 2 del dueño el 08-21, commit de cierre `4bf5024` el 08-22.
