# STOP-2 — E0.1 (margen Δ del cebo) + E0.2 (latencias → K) — 2026-08-18

Commit del código: `11bd7f8` (adenda tras STOP-1 implementada; verja 8/8). Artefactos:
`/data/hrl_e0/e01/{config,results}.json` + `REPORT.md` + `lure_rows.npz` + `gifs/` +
`timelines/`; `/data/hrl_e0/e02/{results.json, REPORT.md}`. 2.184 episodios de E0.1, TODOS
auditados: **0 CRITICAL · 0 violaciones de contrato**.

## 1. Compuertas

| compuerta | enunciado | resultado | veredicto |
|---|---|---|---|
| **G1** (confirmatoria) | Δ(CEBO_keep − MASA \| G, n≥3, vs Reactive) > 0 con IC95 excluyendo 0 | **+0.43 [+0.25, +0.62]** (n=346 pares; piloto Δ̂=+0.50, σ̂=1.58 → n=346) | **PASA** |
| G1 (réplica vs run02) | ídem vs run02 congelado | **+0.53 [+0.33, +0.73]** (n=346) | pasa también contra la defensa aprendida |
| **G1b** (informativa, sin gate) | mapa Δ(S × Δ × hold) | TODAS las celdas de S negativas (ver §3) | delimita: **el valor de la decisión vive en G** |
| **G2** (K) | K fijado con ≥5 decisiones/episodio y commit+golpe en ≤2 macro-pasos | regla pre-registrada dispara: p75 t(inicio→commit) = 2.316 (G/keep) y 4.126 (S/Δ90) > 2.000 | **terminación-por-evento = diseño PRINCIPAL de la Etapa 1**; K fijo NO se fija (queda como techo de revisión) |

## 2. Confirmatoria — estrato G (2 grupos de spawn), CEBO_keep vs MASA

- **Δsev +0.43 [+0.25, +0.62]** vs Reactive; **+0.53 [+0.33, +0.73]** vs run02. Por tipo: lobos +0.35, mixto +0.52. Por n: **n=3 +0.84 [+0.52, +1.16]** · n=4 +0.35 [+0.05, +0.65] · n=5 +0.07 [−0.27, +0.42] — el margen del cebo DECRECE con la masa (con 5 lobos, MASA ya arrolla).
- Distribución completa (Reactive): CEBO media 3.42 / mediana 3 / P(0) 2% / **P(≥4) 50%** vs MASA 2.99 / 3 / 3% / 36%. Bimodalidad esperada NO aparece en G (histogramas unimodales desplazados); sí en S (P(0) 14-36% con CEBO vs 5% con MASA — ver §3).
- **Procedencia** (Reactive): CEBO 1.184 muertes, **KNC 25%** (MASA 3%), gotera 30% (MASA 55%), octantes CEBO [298, 84, 97, 169, 214, 141, 100, 81] vs MASA [574, 104, 63, 59, 46, 56, 54, 77] — con CEBO las muertes se REPARTEN por la espalda del ancla (octantes 3-5 = 44% vs 16% en MASA); con MASA el 56% entran por el frente del ancla (octante 0) y por la gotera.
- **Tasas** CEBO_keep: staged **100%** (el show ocurre siempre), LURE_COMMIT 65%, kill-post-release 98%; ancla = señuelo 62%; ESCOLTA prematura 14% — las 48 son "señuelo confirmado primero" (0 asalto, borde 2/48, hacia-corzo 20/48): el singleton cazado al nacer por el barrido — la cola estructural del ~27% de spawn ya documentada en v3.3, ahora medida al 14% con la máquina de la capa.
- **Figura del valle** (muertes acumuladas medias vs tick, G/keep vs MASA, Reactive): CEBO va DETRÁS de MASA hasta el tick **~4.750** (t=1.000: 0.47 vs 0.96 · t=2.000: 2.05 vs 2.95 · t=4.000: 2.87 vs 2.99) y sólo cruza en la cola (final 3.42 vs 2.99). Es la medida directa del valle de relative overgeneralization que run05-run08 no cruzaron: el cebo pierde ~1 muerte durante los primeros 2.000 ticks para ganar +0.43 al final.

## 3. Exploratorias

| celda | Δsev IC95 | staged | commit | kill-post | ESCOLTA prematura (señuelo/asalto) |
|---|---|---|---|---|---|
| G · CEBO(Δ=180) forzado vs Reactive | **−1.07 [−1.43, −0.72]** | 46% | 41% | 39% | 72% (27/45) |
| S · CEBO(Δ=180) vs Reactive | **−1.12 [−1.53, −0.70]** | 46% | 23% | 39% | 60% (7/53) |
| S · CEBO(Δ=90) vs Reactive | −0.44 [−0.83, −0.05] | 77% | 32% | 73% | 41% (2/39) |
| S · CEBO(Δ=90, hold 5) | −0.26 [−0.59, +0.08] | 79% | 14% | 76% | 72% (0/72) |
| S · CEBO(Δ=90, hold −10) | −0.52 [−0.82, −0.23] | 75% | 13% | 68% | 100% (0/100) |
| S · CEBO(Δ=90) vs run02 | −0.45 [−0.79, −0.09] | 72% | 33% | 67% | 42% (6/36) |

Lectura: **re-partir un paquete que ya está junto (S) o re-splitear uno ya partido (G/Δ180) CUESTA severidad**, no la gana. Causa mecánica medida: t(inicio→staged) p50 = 7.500 ticks con Δ=180 y 1.650 con Δ=90 (vs 495 en G/keep) — el tránsito de reposicionamiento a 4 m/s por el anillo oscuro es largo y **se hace ver**: las ESCOLTA prematuras de S son "asalto confirmado primero" (39-100/100), es decir la barrera se ancla al grueso, no al señuelo, y el cebo nace muerto. Δ=90 es el mejor de S pero sigue negativo; el hold más agresivo (−10 → anillo 90) no lo arregla: 100% de prematuras. En S la bimodalidad SÍ aparece (P(0) 14-36% con CEBO — el paquete pierde el episodio entero en el tránsito — frente a 5% con MASA).

## 4. E0.2 — latencias, reloj de escolta, ROC

| celda | inicio→staged p50/p75/p90 | show→confirm | inicio→LURE_COMMIT p50/p75/p90 | release→1ª muerte p50/p90 |
|---|---|---|---|---|
| G/keep vs Reactive | 494 / 1.506 / 3.541 | 418 / 712 / 893 | **1.160 / 2.316 / 4.537** (n=226) | 804 / 1.446 |
| G/keep vs run02 | 450 / 1.351 / 3.361 | 434 / 723 / 991 | 1.071 / 2.330 / 4.143 | 859 / 1.483 |
| S/Δ90 vs Reactive | 1.652 / 4.529 / 9.175 | 382 / 532 / 608 | 2.798 / **4.126** / 8.690 (n=32) | 933 / 1.568 |
| S/Δ180 vs Reactive | 7.536 / 11.356 / 17.599 | 254 / 418 / 646 | 4.036 / 9.195 / 16.543 | 391 / 814 |

staged→show = 0 por construcción de la capa (show ≡ latch, mismo tick). **Reloj de escolta**: T_safe (ESCOLTA→a salvo) p50 ≈ 1.100-1.170 ticks en todas las celdas; **margen restante en el release p50 ≈ 1.400-1.460 en G/keep y P(margen<0) = 0%** en todas las celdas — con la máquina de la capa el disparo prematuro (el bug histórico) NO reaparece: el show llega siempre con >1.000 ticks de rebaño en juego. En S/Δ180 el margen cae a p50 677 (el tránsito consume la ventana).

**Regla pre-registrada:** p75 t(inicio→commit) = 2.316 (G/keep) y 4.126 (S/Δ90) → ambos > 2.000 → **terminación-por-evento pasa a diseño PRINCIPAL de la Etapa 1**: la opción retiene el control hasta evento terminal (STRIKE_RESOLVED / HERD_SAFE / TIMEOUT_OPCION) y K queda como TECHO de revisión (propuesta de techo: p90 de inicio→commit en G/keep ≈ 4.500 → **K_techo = 4.500** múltiplo de 5; a validar en STOP-3). Sanidad de "≥5 decisiones/episodio": con la mediana de episodio G/keep-lobos en 2.189 ticks y p75 4.399, un K fijo de ~2.300 daría ~1 decisión por episodio típico — inviable, coherente con la regla.

**ROC de LURE_COMMIT** (cono 60°, min_drones {2,3,4} × puerta {40,50,60,70}; n=446 episodios G/keep + S/Δ90): mejor Youden = **min_drones=4, puerta=70 m** (TPR 1.00, FPR 0.31, J=0.69); el umbral de la misión (3, 60 m) da J=0.60. **LIMITACIÓN honesta:** la etiqueta "el asalto mató sin expulsión previa" es positiva en casi todos los episodios de G/keep (kill-post-release 98%), así que TPR=1.0 en TODA la rejilla y la ROC sólo mueve el FPR — el detector discrimina poco con esta etiqueta; recomiendo re-etiquetar en la Etapa 1 con "primera muerte del asalto en ≤N ticks tras el commit" (una etiqueta temporal, no binaria por episodio). Umbrales por defecto SIN cambiar en el código (siguen marcados CALIBRAR-E0.2); DECISIÓN HUMANA: adoptar (4, 70) o mantener (3, 60).

## 5. Lote de visionado

`/data/hrl_e0/e01/gifs/` + `timelines/` (`visionado.json`): par de mayor Δ+ (CEBO_keep y su gemelo MASA), par de mayor Δ− (ídem), primer LURE_COMMIT, 2 medianos, ESCOLTA prematura "señuelo" y "asalto" etiquetadas, sev≥5. Sin violadores.

## 6. Hallazgos para DECISIÓN HUMANA (ningún arreglo aplicado)

1. **Instrumentación (corregido en el clasificador, no en física):** la confirmación de equipo se actualiza dentro de `coord.act()` un tick después de que el mundo latchee ESCOLTA → el clasificador de prematura se difiere a la primera frontera con confirmado; y los lobos nacen en el perímetro → los primeros 200 ticks se excluyen del "pinzamiento de borde". Los 481 episodios prematuros se re-etiquetaron re-simulando (determinismo verificado: sev/steps idénticos en 481/481). Pendiente de commit junto al informe.
2. **El re-split desde S es tácticamente malo con la escenificación actual** (tránsito 1.600-7.500 ticks a 4 m/s por el anillo de 150 m, visible por el barrido). Si la Etapa 1 quiere que el manager pueda cebar desde S, la opción necesita otra maniobra de reposicionamiento (p. ej. tránsito por FUERA de r_detect+hold antes de partir, o partir sólo cuando el rumbo objetivo ya está a <90°) — es una decisión de diseño de la opción, no un parámetro.
3. **El margen del cebo se evapora con n=5** (+0.07 [−0.27, +0.42]): el manager debería aprender/heredar "no cebar con 5" — E0.3 lo confirmará por la otra punta (n=2).
4. La etiqueta ROC de LURE_COMMIT no discrimina (TPR=1 en toda la rejilla) — ver §4.
5. Nada nuevo en física/táctica: los agujeros deliberados (gotera 30-55% de las muertes con Reactive; flancos) siguen siendo los de siempre; ningún cruce imposible ni carrera de timing detectada por las aserciones.

## 7. Siguiente (a la espera de OK humano — STOP-2)

E0.3 (frontera de quórum n∈{2,3,4,5}, CEBO_keep vs MASA en G; n=2 forzosamente S: usar CEBO Δ=90 y reportarlo así), E0.4 (espejo dron), E0.5 (conmutación) → STOP-3 (`ETAPA0_INFORME.md` con la tabla de compuertas G0-G5, los números calibrados y las decisiones pendientes).
