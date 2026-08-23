# STOP-2' — Re-calibración de la Etapa 0 en el mundo v3.5 "regla del sonido" — 2026-08-19

Código `8aeaf89` (tag `v3.5-sonido`, verja 8/8). Artefactos: `/data/hrl_e0/v35/{e0a,e01,e02}/`
(results.json, REPORT.md, gifs/, timelines/, visionado.json, INDEX.md). Metro v3.5 en
`/data/metro_v35/`. E0.1: 2.300 episodios auditados, **0 CRITICAL · 0 violaciones**.

## 0. Orden de firmas (obligatorio)
1. Aserciones verdes ✔ (0 CRITICAL / 0 violaciones en E0.A+E0.1: 2.398 episodios).
2. **VISIONADO DEL DUEÑO** ☐ — `INDEX.md` de este directorio (12 GIFs con el render nuevo:
   cuadrado naranja = detectado, rojo = confirmado, anillo azul = sonido, 🔊 = dron con lobo a ≤20).
3. Análisis numérico (este informe) — VÁLIDO SOLO tras la firma 2.

## 1. Predicciones PRE-REGISTRADAS (FASE 4) — contraste

| predicción | v3.4 | v3.5 | veredicto |
|---|---|---|---|
| sev(MASA) baja | 2.99 (G, Reactive) | **1.57** | ✔ (Dummy 3.82→1.90, Reactive 2.68→0.88, MASA-G 2.99→1.57) |
| Δ(CEBO_keep−MASA \| G, n≥3, Reactive) sube respecto a +0.43 | +0.43 [+0.25, +0.62] | **+0.85 [+0.60, +1.09]** (n=375) | ✔ (se DUPLICA; el cebo vale más cuando la línea quieta suena) |
| cruces de corredor ≈ 0 | gotera 30% de las muertes CEBO / 55% MASA | **0.5% / 0.2%** de las muertes; 0.07 / 0.06 cruces/ep | ✔ (el corredor está cerrado; residuo = empujones en aglomeración) |
| prematura "señuelo confirmado primero" persiste (no depende del sonido) | 48/48 en G/keep (14%) | **61/61 en G/keep (16%)**, borde 2/61 | ✔ (es el singleton cazado por el barrido al nacer: geometría de spawn) |

## 2. Compuertas en v3.5

| | v3.5 | veredicto |
|---|---|---|
| **G0** E0.A(ii) re-anclado al suelo v3.5 del cebo (2.60 / 37.7% / 65.5%) | **58/58 severidades idénticas**; sev 2.60, KNC 37.7%, ancla-cebo 65.5% | **PASA** (impuesto de interfaz = 0 exacto, también en v3.5) |
| **G1** Δ(CEBO_keep−MASA \| G, n≥3, vs Reactive) > 0, IC95 excluye 0 | **+0.85 [+0.60, +1.09]** (n=375; piloto Δ̂=+0.80, σ̂=2.63) | **PASA** |
| réplica vs run02 (política v3.4 en v3.5) | +0.75 [+0.50, +1.01] | pasa |
| **G1b** mapa S | Δ180 +0.16 [−0.11, +0.46] · **Δ90 +0.32 [+0.04, +0.64]** · hold 5 −0.07 · hold −10 −0.02 · Δ90 vs run02 +0.34 [+0.00, +0.70] | en v3.5 el re-split desde S deja de COSTAR (v3.4: −0.44…−1.12) y Δ90 pasa a positivo débil; G/Δ180 forzado sigue negativo (−0.93) |
| **G2** (K) | p75 t(inicio→commit) = 2.299 (G/keep) y 4.345 (S/Δ90) > 2.000 | regla pre-registrada → **terminación-por-evento = diseño principal** (igual que en v3.4); K techo ≈ 4.500 (p90 G/keep 4.518) |

## 3. Confirmatoria G/CEBO_keep vs MASA (Reactive) — lo nuevo de v3.5

- Δ por n: **n=3 +1.21 [+0.83, +1.58]** · n=4 +0.85 [+0.41, +1.27] · n=5 +0.45 [−0.01, +0.91] — el
  margen sigue decreciendo con la masa pero ya NO se evapora en n=5 (v3.4: +0.07). Por tipo:
  lobos +0.93, mixto +0.78.
- **Distribución BIMODAL (la esperada en la adenda) aparece ahora en G**: CEBO P(0) 37% / P(≥4)
  38% (hist [139,26,32,34,54,54,24,12]) vs MASA P(0) 47% / P(≥4) 19%. Con la línea sonando el
  paquete o no consigue nada (el señuelo cazado / la línea lo mantiene fuera) o el asalto entra
  por la espalda y hace matanza: el cebo es una apuesta todo-o-nada más marcada que en v3.4.
- Procedencia (Reactive): CEBO 906 muertes, **KNC 45%** (v3.4: 25%; MASA v3.5: 27%), gotera 0.5%,
  octantes CEBO [100,80,126,154,142,144,83,77] vs MASA [126,105,68,43,40,42,77,85]: con CEBO el
  62% de las muertes entran por los octantes 2-5 (espalda/flancos del ancla) — la línea quieta
  que suena cubre su frente pero no su espalda: el agujero deliberado que queda.
- Tasas CEBO_keep: staged 100%, LURE_COMMIT 60%, kill-post-release 63% (v3.4: 98% — la línea
  que suena mata muchos asaltos), t→staged 1.302 [1.077, 1.547]; ESCOLTA prematura 16% (61/61
  "señuelo", borde 2, hacia-corzo 24/61).
- **Figura del valle**: CEBO detrás de MASA hasta el tick **~2.250** (v3.4: ~4.750); a t=1.000:
  0.28 vs 0.55; t=2.000: 1.47 vs 1.50; t=4.000: 2.00 vs 1.56; final 2.42 vs 1.57. El valle se
  ACORTA a la mitad: la ventana en que "cebar sale caro" es de ~2.000 ticks.
- Reloj de escolta: T_safe p50 988-1.011 (G/keep); margen del release p50 1.620, **P(<0)=0%** en
  todas las celdas — el disparo prematuro no reaparece.

## 4. Exploratorias — cambio de signo en S

| celda | Δsev v3.4 | Δsev v3.5 | staged | commit | kill-post | prematura (señuelo/asalto) |
|---|---|---|---|---|---|---|
| G · CEBO(180) forzado | −1.07 | **−0.93 [−1.38, −0.47]** | 29% | 33% | 17% | 71/100 |
| S · CEBO(180) | −1.12 | +0.16 [−0.11, +0.46] | 23% | 11% | 8% | — |
| S · CEBO(90) | −0.44 | **+0.32 [+0.04, +0.64]** | 60% | 15% | 12% | — |
| S · CEBO(90, hold 5) | −0.26 | −0.07 [−0.24, +0.12] | | | | |
| S · CEBO(90, hold −10) | −0.52 | −0.02 [−0.17, +0.13] | | | | |
| S · CEBO(90) vs run02 | −0.45 | +0.34 [+0.00, +0.70] | | | | |

Lectura: en v3.5 MASA en S rinde muy poco (0.17 al final del valle S/Δ90 vs 0.49 con CEBO):
la línea que suena frena al paquete compacto; partirse ya no pierde nada y Δ90 gana algo. El
re-split en G (Δ180 forzado) sigue costando (−0.93): el señuelo se re-mueve y el asalto hace
un tránsito largo que se hace ver (71/100 prematuras "asalto"). Un manager que ceba debe
CEBAR EN SITIO (keep), no re-partir la geometría.

## 5. E0.2 v3.5

- Latencias G/keep: inicio→staged 498/1.496/3.471 · show→confirm 346/660/887 · inicio→commit
  1.073/**2.299**/4.518 · release→1ª muerte 626/1.238 (p50/p75/p90; p50/p90).
- **Regla pre-registrada dispara igual que en v3.4**: p75 inicio→commit > 2.000 en ambas
  celdas del manager → terminación-por-evento; K techo 4.500 (múltiplo de 5).
- ROC LURE_COMMIT: mejor Youden = 4 drones / puerta 60 m (J=0.73; TPR 1.0, FPR 0.27) — vuelve a
  ser TPR=1 en toda la rejilla (misma limitación de etiqueta que en v3.4); umbrales sin cambiar.
- Duración de episodios G/keep-lobos: p50 3.931, p75 23.570 (timeout) — con la línea sonando el
  paquete se atasca fuera y muchos episodios agotan el reloj: otra razón para terminar por evento.

## 6. Hallazgos / decisiones humanas pendientes (nada arreglado)
1. **B — apilamiento en PENETRADO** (`_cover_engaged`): sigue pendiente de tu decisión
   (arreglo con test dirigido en commit separado, o aceptar). En v3.5 PENETRADO ocurre menos
   (la línea suena) pero el código sigue igual.
2. **La espalda del ancla es ahora EL agujero**: 62% de las muertes CEBO por octantes 2-5 con
   KNC 45%. Deliberado; lo hereda el manager de drones (E0.4) — no se toca.
3. **Timeouts largos en G/keep** (p75 = 23.570 ticks): el terminal del episodio no distingue
   "el paquete se rindió" — para la Etapa 1 conviene un evento de "asedio estéril" (opción sin
   progreso N ticks) además de STRIKE_RESOLVED/HERD_SAFE. Es diseño de la Etapa 1, lo anoto.
4. Con la regla del sonido run02 (política v3.4) queda 1.09/0/0.78 vs Reactive 0.88/0.76: la
   nota a batir del MARL de drones es ahora 0.88/0/0.76 y run02 es histórico.

## 7. Siguiente (a la espera de firma 2 y OK)
E0.3 (quórum n∈{2..5}; CEBO_keep en G, n=2 → S/Δ90), E0.4 (espejo dron con Reactive v3.5 /
proporcional / run02-histórico), E0.5 (conmutación) → STOP-3.
