# STOP-M1 — RUN-M1: manager de lobos (semi-MDP sobre opciones congeladas) — 2026-08-19

Código: G `73389dc` · H `4f40af5` · I `dc02b6f` · I-bis `5049017` · J `2fbbcfd` (+ gancho de
observación on_tick/on_boundary en ManagerEnv, pendiente de commit de docs). Mundo v3.5-sonido.
Listón congelado ANTES del run: `/data/hrl_m1/PREREGISTRO.md` (B_oracle 0.885 vs Reactive · 1.02 vs run02).
RUN-M1: 122.880 macro-pasos, 24 envs, 5 h 15 min, 6.5 macro-pasos/s, sin NaN. Artefactos en
`/data/hrl_m1/M1/` (model.zip, checkpoints/ cada 5k, eval_ligera.jsonl, train.log, visionado/).

## 0. ORDEN DE FIRMAS
1. Aserciones: ver §6 (auditoría de 200 episodios del manager con EpisodeAudit).
2. **VISIONADO DEL DUEÑO** ☐ — `/data/hrl_m1/M1/visionado/INDEX.md` (5 GIFs + timelines con las
   decisiones del manager por tick).
3. Análisis (este informe) — válido solo tras la firma 2.

## 1. Tabla-escalera (100 semillas emparejadas, 0-99 × lobos/mixto; IC bootstrap 10k)

| política | vs Reactive v3.5 | vs run02-eval | Δ vs B_masa (React.) | Δ vs B_oracle (React.) | Δ vs B_oracle (run02) | gap React.→run02 |
|---|---|---|---|---|---|---|
| B_masa | 0.58 [0.42, 0.76] | 0.69 [0.52, 0.86] | 0 | −0.30 [−0.52, −0.10] | | +0.10 |
| B_spawn | 0.82 [0.58, 1.06] | 0.94 [0.70, 1.18] | +0.23 [+0.05, +0.43] | −0.07 [−0.16, +0.02] | | +0.12 |
| **B_oracle** (listón) | **0.89 [0.65, 1.14]** | **1.02 [0.78, 1.28]** | +0.30 [+0.10, +0.52] | 0 | 0 | +0.135 [−0.06, +0.33] |
| manager M1 60k | 1.36 [1.06, 1.67] | — | +0.78 [+0.51, +1.04] | +0.47 [+0.29, +0.68] | — | — |
| **manager M1 final** | **1.31 [1.02, 1.62]** | **1.20 [0.94, 1.48]** | **+0.72 [+0.47, +0.99]** | **+0.42 [+0.23, +0.63]** | +0.18 [−0.03, +0.40] | **−0.11 [−0.29, +0.07]** |

vs B_spawn (Reactive): **+0.49 [+0.31, +0.69]**. run09 (drones v3.5) se añadirá cuando termine (a 19M).

## 2. Compuertas pre-registradas

| compuerta | resultado | veredicto |
|---|---|---|
| **M1-Emergencia** P(cebo \| G, n≥3) ≥ 0.8 al final + curva | **1.0 desde la primera ligera (10k) hasta el final** — pero TRIVIAL: P(cebo)=1.0 en TODOS los estratos (S, n=2, n=1) | PASA numéricamente; la "emergencia" es "cebo siempre", no una discriminación |
| **M1-Competencia** ≥ B_spawn (IC excluye 0) · no-inferior a B_oracle (δ=0.15) · superarlo = estrella | vs B_spawn **+0.49 [+0.31, +0.69]** ✔ · vs B_oracle **+0.42 [+0.23, +0.63]** → SUPERA (vs Reactive); vs run02 +0.18 [−0.03, +0.40] (no-inferior ✔, superar no concluyente) | **PASA** (estrella vs Reactive; no-inferior vs run02) |
| **M1-Estructura** P(cebo\|n=2) baja vs P(cebo\|n≥3) alta · P(Δ180)≈0 · en S prefiere Δ90 | P(cebo\|n=2)=1.0 (=n≥3) ✗ · P(Δ180) primera decisión 0, re-decisiones 0.33 ✗ · en S primera decisión CEBO_keep (no Δ90), luego alterna keep/Δ90/Δ180 ✗ | **FALLA** |
| **M1-Auditoría** 0 CRITICAL · aserciones · PENETRADO | 0 CRITICAL, 0 violaciones (200 eps); PENETRADO 13 ticks/ep (oracle 6.9) | **PASA** |

## 3. Curva de emergencia (eval_ligera.jsonl, 40 semillas fijas, política determinista)
- Primera decisión: **CEBO_keep = 1.0 en G y en S desde 10k hasta 122.880** — plana. sev ligera 0.12 constante
  (la ligera v3.5 es casi degenerada: 36/40 episodios a 0).
- Re-decisiones (todas las decisiones, G): 10k Δ180 0.997 → 20-30k Δ90 ~0.98 → 40k Δ180 0.96 → 50k mezcla →
  ≥70k reparto ~1/3 keep / 1/3 Δ90 / 1/3 Δ180; **MASA ≈ 0.001 en todas** — el manager aprendió "cebo sí, MASA no"
  y NO distingue variantes de cebo tras el aborto.
- Buffer de entrenamiento (estocástico, solo 'lobos'): ep_sev 0.89 (10k) → 1.24 (70k) → 1.36/1.44 (80k/120k);
  P(a) 0.24/0.25/0.25/0.26 → 0.13/0.30/0.30/0.27 (MASA cae monótona); decisiones/ep 6 → 17-22;
  ABORT_BAIT_FAILED 5.6k → 72k acumulados (la cadencia de 50 ticks domina el recuento de eventos).

## 4. Heatmap P(primera acción | estrato, n) — manager final vs Reactive
CEBO_keep = 1.00 en G, S, n1, n2, n3, n4, n5 (todo lo demás 0). Decisiones/ep 101 (oracle 72); ABORT 19.759
(oracle 14.050); PENETRADO ticks/ep 13.0 (oracle 6.9); success 86/200 (oracle 116).

## 5. MECANISMO del resultado (descomposición por estrato, vs Reactive)

| subconjunto | manager | oracle | masa | spawn | Δ(mgr−oracle) IC |
|---|---|---|---|---|---|
| G n≥3 (58) | 2.76 | 2.60 | 1.79 | 2.60 | +0.16 [−0.03, +0.40] |
| **S n≥3 (76)** | **1.34** | 0.33 | 0.16 | 0.16 | **+1.01 [+0.55, +1.49]** |
| n≤2 (66) | 0.00 | 0.01 | 0.01 | 0.01 | −0.02 |
| n=3 / 4 / 5 | 2.02 / 1.87 / 2.04 | 1.52 / 1.13 / 1.36 | | | +0.50 / +0.73 / +0.68 |

**Toda la ventaja vive en S n≥3.** Secuencias típicas en S: (keep, Δ90, keep, Δ90, …) ×29, (keep) ×22,
(keep, Δ90, Δ90, …) ×22. Mecánica (timeline seed 21 lobos, n=4, S: manager sev 7 vs oracle 0): CEBO_keep
1.356 ticks hasta el primer ABORT (show a t=1.085), y a partir de ahí **cada re-decisión CEBO re-arranca la
opción y RE-FIJA la presa del asalto a la res MÁS LIBRE en ese instante** (regla documentada de la capa: presa
leída al iniciar la opción, `freest_prey_for`) → el asalto se re-dirige cada 50-400 ticks hacia donde NO están
los drones; 7 muertes en ~1.000 ticks. El oracle, con Δ90 fijo, mantiene una presa y no mata. En G la
ganancia es pequeña (+0.16, IC cruza 0): ahí el cebo "de verdad" ya lo hace el oracle.
- Lectura: el manager ha encontrado una **re-decisión post-evento que la regla no hace** (vía esperable
  pre-registrada) — pero NO es "cebar mejor": es **re-targeting adaptativo del asalto usando el ciclo
  ABORT (50 ticks de gracia) + el re-arranque de opción como un reloj de 5 s**. Contra run02 (drones que
  se mueven) el truco rinde menos (+0.18 vs oracle, IC cruza 0; gap de transferencia −0.11 vs +0.135 del
  oracle): la "res más libre" cambia más deprisa que el bucle.
- El agujero que explota es el de siempre (espalda/flancos del ancla: KNC alto), no el corredor.

## 6. Auditoría (M1-Auditoría) — 200 episodios del manager vs Reactive con EpisodeAudit
200 episodios (seeds 0-99 × lobos/mixto, manager final, Reactive): **0 CRITICAL · 0 violaciones de contrato**; 262 muertes (sev 1.31, idéntica a la eval = replay determinista); **KNC 40.1%**; cruces de gotera 1 en 200 episodios (v3.5 cerrada). `/data/hrl_m1/M1/audit_final.json`.

## 7. Hallazgos → DECISIÓN HUMANA PENDIENTE (nada arreglado)
1. **Re-targeting por re-arranque de opción**: la semántica "presa del asalto leída al iniciar la opción" +
   ABORT a 50 ticks convierte la re-decisión en un reloj de re-targeting. ¿Es comportamiento legítimo del
   manager (sí según las reglas del env tal como se pre-registraron) o un artefacto de la capa que
   conviene cerrar (p. ej. mantener pack_prey2 entre re-arranques de la MISMA opción, o gracia del ABORT
   mayor)? Si se cierra, hay que re-entrenar (cambia el MDP).
2. **M1-Estructura falla**: el manager no discrimina estratos ni n (cebo en n≤2 es gratis: asalto de 1 no
   puede matar adultas y el señuelo no cuesta). La obs de 35 dims lleva n/5 y nº de clústeres — la señal
   existe; no hay gradiente para usarla porque MASA nunca gana al cebo-con-re-targeting en este MDP.
3. **Cadencia de ABORT**: 50 ticks de gracia (decisión mía en el Commit H) fija el periodo del bucle; con
   gracia mayor el re-targeting sería más lento. Parámetro nombrado (ABORT_GRACE_TICKS) — candidato a
   ablación, no se toca sin OK.
4. Ligera determinista como termómetro: inútil cuando el argmax colapsa (12 evals idénticas); la curva
   que informa es la del buffer (estocástica). Para las réplicas/M2 propongo añadir a la ligera la
   distribución estocástica (P(a) muestreada) además del argmax — cambio de instrumentación, no de receta.
5. PENETRADO (hallazgo B, contador pasivo): 13 ticks/ep con el manager vs 6.9 oracle (más tiempo del
   asalto dentro del rebaño). Sin arreglo, como se decidió.

## 8. Siguiente (cola de cómputo, tras tu firma)
2 réplicas de M1 (semillas nuevas) → RUN-M2 (K=1000 fijo; predicción pre-registrada: colapso a MASA o
emergencia degradada) → RUN-M4 (sin rasgos de progreso) → RUN-M3 (mix). run09 termina en ~1 h → se añade a
la escalera (gap Reactive→run09 manager vs oracle).
