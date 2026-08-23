# STOP-NIVELADO — M1'' parado en el re-nivelado por DOS compuertas pre-registradas (2026-08-20)

**Estado**: Commits K (`610e6da`), K-bis (`54d2546`) y L (`caeb683`, tag `v3.6-patrol-estatica`)
hechos, verja 8/8 verde en cada uno, pusheados. El pipeline M1'' está **PARADO antes de
PREREGISTRO_v2 y RUN-M1''** porque dispararon dos reglas pre-registradas del plan:

1. **Sanity de capa (re-nivelado §1)**: Δ(CEBO_keep−MASA | G, n≥3, 50 pares) = **+1.16 [+0.42, +1.90]**
   → |1.16 − 0.85| = **0.31 > 0.30** → "parar y escalar con GIFs".
2. **Mini-E0.3**: **CAZA DETECTADA a n=2** (el caso pre-avisado "n=2+ternero vs Dummy" y más)
   → "reportar y PARAR: decisión del dueño".

Firmas en el orden de siempre: 1º aserciones (verja 8/8 y tests K1-K4 verdes) · 2º **VISIONADO
DEL DUEÑO** (`/data/hrl_m1/m1pp/gifs/INDEX.md`, 4 GIFs con timelines) · 3º este análisis.

---

## 1. Compuerta 1 — sanity de capa: disparo MARGINAL y ATRIBUIDO

Celda E0.1 (G, n≥3), CEBO_keep-forzado vs MASA-forzado, 50 pares, capa K, Reactive-estática:
Δ = +1.16 [+0.42, +1.90] (cebo 2.86, masa 1.70) vs referencia v3.5 = +0.85. **Sin conducta rara**:
re-targets ≈ 0 en el brazo CEBO (0.34/ep en MASA, causa "protegida", cadencia ≥ cooldown).

**Atribución (mismas 50 semillas, diferencias EMPAREJADAS por semilla):**

| configuración | Δ celda | efecto emparejado |
|---|---|---|
| A: capa pre-K (`ded2123`) + órbita = réplica v3.5 exacta | +0.52 [−0.18, +1.24] | — |
| B: capa K + órbita | +0.64 [0.00, +1.32] | regla K: **+0.12 [−0.12, +0.34]** |
| C: capa K + estática (la sanity) | +1.16 [+0.42, +1.90] | patrulla: **+0.52 [−0.18, +1.24]** |

Lecturas: (i) la referencia +0.85 venía del corpus E0.1 (n=375, otro pool de semillas); re-medida
en ESTAS 50 semillas la v3.5 exacta da +0.52 → el estimador de 50 pares es ruidoso (SE≈0.37) y la
compuerta disparó por 0.01; (ii) la **regla K apenas mueve la celda** (+0.12, IC cruza 0) — el
botón del exploit está cerrado sin distorsionar el cebo; (iii) el movimiento real viene de la
**patrulla estática**, y va TODO al brazo CEBO (cebo C−A: +0.50; masa C−A: −0.14): con el anillo
quieto, el señuelo ancla más y el asalto encuentra la espalda más despejada. Coherente con el
metro: el **cebo scriptado 2f sube 2.60 → 2.97** y el ancla-cebo 65.5% → **79.2%** en v3.6.

**GIF del caso extremo (seed 84, CEBO_keep, G)**: v3.5 = success 0 muertes; v3.6 = 6 muertes
(2442-2919) con el MISMO timing del cebo (show ~1700, ESCOLTA ~1900). No es un bug: es la
patrulla estática dejando el flanco del asalto más limpio (agujero deliberado nº2, ahora mayor).

**Decisión pendiente (dueño)**: dar por buena la celda en v3.6 (la desviación es del CONFIG
oficial nuevo, no de la capa; la regla K es limpia) y re-fijar la referencia de la sanity a la
celda v3.6, o re-calibrar algo (¿la patrulla? ¿las constantes K?). Constantes K vigentes:
THREAT_GUARD_DIST=25 m · GUARD_HOLD=50 ticks · RETARGET_MARGIN=30 m · RETARGET_COOLDOWN=250.

## 2. Compuerta 2 — mini-E0.3: n≤2 SÍ caza

n=2 forzado (60 semillas/celda, brazos MASA y CEBO_keep, capa K) y n=1 (30, MASA):

| celda | sev media | P(sev>0) |
|---|---|---|
| n=2 + ternero, **Dummy**, MASA | **1.98** | 0.63 |
| n=2 + ternero, Dummy, CEBO_keep | 0.78 | 0.62 |
| n=2 sin ternero, Dummy, MASA | **1.40** | 0.63 |
| n=2 sin ternero, Dummy, CEBO_keep | 0.00 | 0.00 |
| n=2 + ternero, Reactive-estática, MASA | 0.18 | 0.10 |
| n=2 + ternero, Reactive-estática, CEBO_keep | 0.07 | 0.05 |
| n=2 sin ternero, Reactive-estática, MASA | 0.15 | 0.12 |
| n=2 sin ternero, Reactive-estática, CEBO_keep | 0.00 | 0.00 |
| n=1, Dummy, MASA | 0.03 | 0.03 |

El criterio de exclusión (sev < 0.05 en TODOS los brazos) **NO se cumple**: n=2 caza de verdad
contra Dummy (1.4-2.0) y algo contra la defensa real (0.15-0.18). n=1 sí es ≈0. **Decisión
pendiente (dueño)**: ¿train n~U{3,4,5} igualmente (la señal contra la defensa REAL a n=2 es
0.15-0.18: pobre pero no cero) o incluir n=2? El fallback de capa CEBO→MASA con asalto <2 queda
SIN implementar hasta esta decisión (iba "tras verificar").

## 3. Commit L — patrulla estática: motivos MEDIDOS (A/B 100 semillas/tipo emparejadas)

| métrica | órbita (0.02) | estática (0.0) |
|---|---|---|
| espera anuncio→hand-off (media/máx) | 298 / 777 ticks | **102 / 408** |
| STRANDED/ep | 2.95 (corzos: 8.0) | **0.00** |
| hand-offs/ep | 17.9 | 9.8 |
| relevos en patrulla vs barrera | 15.1 / 2.8 | 7.7 / 2.1 |
| Δsev estática−órbita | — | **+0.08 [−0.06, +0.22]** (IC cruza 0; < umbral 0.3) |

El problema observado por el dueño queda cuantificado: el hand-off a ≤2 m contra blanco EN
ÓRBITA producía esperas de ~300 ticks y drones tirados; con el anillo quieto desaparecen. El
coste en severidad es pequeño y no concluyente (mixto +0.17, lobos +0.06). GIFs del peor caso
y su gemelo en el INDEX.

## 4. Escalera v3.6 (patrulla estática · física v3.5 · capa K) — 100 semillas/tipo

| defensa | lobos | corzos | mixto | notas |
|---|---|---|---|---|
| Dummy (v3.5, sin cambio) | 1.90 | 0 | 2.02 | no usa patrulla |
| **Reactive-estática (nota a batir)** | **0.94** | 0 | **0.93** | órbita era 0.88/0.76 |
| Suelo residual (δ≡0) | 0.99 | 0 | 0.91 | v3.5: 0.92/0.81 |
| run02 @ estática | 0.86 | 0 | 0.84 | mismatch (entrenado órbita) |
| run02 @ órbita (su config) | 1.09 | 0 | 0.78 | = su medida v3.5 exacta (continuidad OK) |
| run09 @ estática | 0.88 | 0 | 0.86 | mismatch (entrenado órbita) |
| **run09 @ órbita (su config)** | **0.79** | 0 | **0.78** | bate a run02 (1.09→0.79 lobos) |
| cebo scriptado 2f | sev-2f **2.97** · KNC 39.0% · ancla-cebo **79.2%** · gotera 0/ep | | | v3.5: 2.60 / 37.7% / 65.5% |

Baselines del manager (200 episodios emparejados, capa K, vs Reactive-estática; IC bootstrap):
**B_masa 0.57 [0.41, 0.75] · B_spawn 0.99 [0.72, 1.27] · B_oracle 1.00 [0.74, 1.28]**.
(M1/v3.5 eran 0.585 / 0.82 / 0.885.) Contadores K-bis activos: re-targets 0.04-0.27/ep con causa
"protegida"; re-fijaciones por muerte/refugio dominan (~0.9/0.7 por ep en los brazos cebo).

**run09 (20M, 5h15... [ver /data/drones/run09_v35/summary.json])**: pacto re-calibrado documentado
en su config.json (suelo 0.50, EROSION 1.2); la ligera vivió en 0.5-0.7 todo el run. En su config
(órbita) mejora a run02 en lobos (0.79 vs 1.09) — entra como defensa de transferencia en el
PREREGISTRO_v2 cuando se desbloquee, con el mismatch de patrulla documentado (dos filas).

## 5. Corpus E0.1 v3.5 — severidades ABSOLUTAS por n y brazo (total-vs-mejora; solo lectura)

vs Reactive (órbita, v3.5): G/keep 2.68 (n3) · 2.34 (n4) · 2.21 (n5) — MASA G 1.48 / 1.49 / 1.76;
S/Δ90 0.15 / 0.78 / 0.50 — MASA S 0.00 / 0.25 / 0.27. vs run02: G/keep 3.04 / 2.33 / 2.22 —
MASA G 1.72 / 1.74 / 1.90. (El valor del cebo vive en G a todo n; en S el cebo solo asoma en n4-n5.)

## 6. Qué queda BLOQUEADO y qué está listo

- **BLOQUEADO (decisión del dueño)**: PREREGISTRO_v2 (congelación de listones y compuertas),
  RUN-M1'', fallback CEBO→MASA (asalto <2), distribución de n del train, y la cola M2/réplica/M4.
- **LISTO**: capa K con regla de caza (tests K1-K4), instrumentación K-bis (P(a) estocástica +
  entropía + contadores de caza en la ligera y en eval_manager), config v3.6 con métricas de
  relevo en arnés y auditor, metro v3.6 completo, baselines nuevos medidos (no congelados),
  scripts de RUN-M1'' (`train_manager.py` corre tal cual con el oponente ya estático; falta solo
  el flag de n del train, una línea, tras tu decisión).
- Sin CRITICAL nuevos; hallazgo B (apilamiento PENETRADO) sigue como contador pasivo.

## 7. Propuesta (si firmas las dos compuertas tal cual)

1. Re-fijar la referencia de la sanity a la celda v3.6 (+1.16) y seguir: PREREGISTRO_v2 con
   B_oracle 1.00 [0.74, 1.28] como listón, gates de Estructura como en el plan.
2. Train n~U{3,4,5} + fallback CEBO→MASA (+test) — la caza real de n=2 contra la defensa es 0.15-0.18
   y n=2 es forzosamente S (sin cebo útil): mantengo tu exclusión, con la evidencia del §2 anotada.
3. RUN-M1'' (receta M1 exacta) → STOP-M1''.

*Artefactos*: sanity_capaK.json · atrib_sanity_{A,B,C}.json · mini_e03.json · ab_patrulla.json ·
metro/ (6 JSON) · eval/{masa,spawn,oracle}_v36__reactive.json · gifs/ + INDEX.md ·
verif/ (scripts efímeros y logs). Verjas: verja_K.log · verja_L.log · reactive_check_L2.log.
