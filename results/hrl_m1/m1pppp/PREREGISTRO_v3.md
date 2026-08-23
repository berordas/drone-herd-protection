# PREREGISTRO_v3 — RUN-M1'''' (CONGELADO 2026-08-21T13:10Z, ANTES de lanzar el retrain; ninguna eval del
# manager vista — el ckpt M1pp NO se ha evaluado sobre la capa nueva salvo los replays de
# mecanismo de S2)

**Motivo del re-nivelado ÚNICO**: paquete M1'''' (adjudicación VERIF-0 + firma MESETA del dueño
— la raíz se arregla, el watchdog queda de tripwire): S1 (gate de rumbo mejor-esfuerzo), S2
(ABORT solo pre-show), CENSURA (hitos + tasa de jugada completa), Q (coste de deliberación
0.05), Q-bis (tripwire), S3 (staged mejor-esfuerzo por meseta), R (física v3.7
relevo-centinela + ranura heredada), V2 (señuelo directo con espera). Commits 20d39db → 89a5896,
tag v3.7-relevo-centinela; verja 8/8 verde en los 8.

## Configuración congelada

- Física **v3.7-relevo-centinela** · patrulla estática v3.6 · capa S1+S2+S3+CENSURA+Q-bis+V2 +
  regla de caza K + fallback de quórum N.
- Receta EXACTA M1/M1'': PPO SB3 MlpPolicy [64,64], lr 3e-4, γ=1.0, gae_λ=0.95, ent 0.02→0.005,
  clip 0.2, n_steps 256, batch 512, 10 epochs, 24 envs, **120.000 macro-pasos**, terminación por
  evento (K_MAX 4500; ABORT ±60°/3-de-4/gracia 50, **solo pre-show**), ckpt 5k, ligera 10k.
  Oponente TRAIN: Reactive-estática. TRAIN n~U{3,4,5}; EVAL natural U{1..5}.
- **DELIB_COST = 0.05**. **FALLBACK ÚNICO** (no se tantea): si en la ligera de **40k** los
  ABORTs/ep siguen **> 10** ⇒ relanzar desde 0 con `--delib-cost 0.1` (una sola vez).
  La sev de TODAS las tablas es SIEMPRE sin coste.

## Listones CONGELADOS (100 semillas emparejadas 0-99 × {lobos, mixto}; IC bootstrap 10k; capa
## y física NUEVAS; censura estándar)

| baseline | vs Reactive-est | vs run02 | jugada completa | con show | stalls |
|---|---|---|---|---|---|
| B_masa | 0.56 [0.40, 0.74] | 0.61 [0.45, 0.78] | n/a | n/a | 0 |
| B_spawn | 0.95 [0.71, 1.22] | 0.90 [0.67, 1.16] | **1.00** | 1.00 | 0 |
| **B_oracle** | **1.66 [1.36, 1.97]** | **1.64 [1.35, 1.95]** | **1.00** | 1.00 | 9 / 15 |

Gap de transferencia del oráculo (run02 − reactive, emparejado): **−0.02 [−0.24, +0.20]**.
Δ(oracle − spawn) vs reactive: +0.71 [+0.48, +0.96].

**Celdas S LIMPIAS** (100 pares, n≥3, vs Reactive-est — el paisaje S real por primera vez;
contaminadas v3.6: 0.33/0.58/0.50): **MASA 0.30 [0.13, 0.51] · Δ90 1.71 [1.29, 2.14] · Δ180
1.42 [1.02, 1.84]**; Δ(Δ90−MASA) = +1.41 [+0.98, +1.86]; **Δ(Δ180−Δ90) = −0.29 [−0.76, +0.17]**
(Δ90 mejor brazo en punto; IC cruza 0). Jugada completa **1.00** y show **100%** en ambos brazos
Δ. Composición del staged: Δ90 = 39 a_tiro / 61 meseta · Δ180 = 61 / 39. Error de rumbo
CONSEGUIDO en el show: Δ90 mediana 48.5° (p90 101) · Δ180 mediana 158.7° (≈ muestra casi sin
reposicionar — "Δ pretendido" ≠ conseguido, documentado). **Tripwire en brazos forzados: Δ90
9/100 · Δ180 25/100 (alineación lenta re-armando el reloj de sin-progreso — NOTA FIRMADA del
dueño: se reporta tal cual, S3 NO se amplía; el contador es la métrica).**

Sanity E0.1 (G, 50 pares): Δ(keep−MASA) = **+1.16 [+0.38, +1.94]** — clavada en la referencia
v3.6 (+1.16 [+0.42, +1.90]); keep con jugada completa 1.0 y 0 stalls. RE-FIJADA aquí.
Metro v3.7: Reactive-est 0.93/0/0.69 · run02(est) 0.79/0.58 · run09(est) 0.77/0.62 · Dummy
1.91/2.06 · floor 0.94/0.73 · cebo scriptado 2f: sev 2.47, KNC 42.7%, ancla-cebo 77.1% (n=58).

## Compuertas M1''''

- **Emergencia**: P(cebo|G, n≥3) ≥ 0.8 al final, juzgada NO-vacua junto a Estructura.
- **Estructura**: P(keep|G, n≥3) alta Y P(Δ90|S, n≥3) alta; P(Δ180) ≈ 0; re-targets con causa
  "protegida" y cadencia ≥ cooldown. Nota: las celdas LIMPIAS ya respaldan Δ90 como mejor brazo
  de S (en punto). **Si el manager re-prefiere Δ180|S** (estocástica, H(a|S,n≥3) < 0.9): se
  adjudica contra las celdas limpias de arriba con el procedimiento de desempate YA FIRMADO.
- **Competencia**: ≥ B_spawn con IC emparejado excluyendo 0; **no-inferior a B_oracle = 1.66**
  (δ=0.15); superarlo = estrella. (Listón MÁS ALTO que en M1'': el oráculo ya juega siempre.)
- **Transferencia**: gap Reactive→run02/run09 no peor que el del oráculo (−0.02).
- **Auditoría**: 0 CRITICAL; churn/re-targets/PENETRADO + patrulla + relevos en el informe.
- **NUEVAS (adjudicación VERIF-0 + firma MESETA)**:
  - **Tasa de jugada completa ≥ 0.8 del MANAGER** (episodios con cebo y n≥3). En los brazos
    forzados del re-nivelado ya está medida: 1.00 en todos.
  - **STALL del manager ≈ 0** en la eval final; **cualquier disparo, LISTADO episodio a episodio
    = DECISIÓN HUMANA PENDIENTE** (en los brazos forzados el tripwire es el rescate legítimo de
    la alineación lenta y va REPORTADO: 9%/25%, ver arriba).
  - **ABORTs/ep del manager ≤ 5** en la eval final.

## Predicciones pre-registradas

1. **(Dueño — ya CUMPLIDA en los listones)** B_oracle en S sube (1.00 → 1.66 global; celda S
   Δ90 0.58 → 1.71) ⇒ **la ventaja del manager ENCOGERÁ respecto a +1.26**. Éxito = estructura +
   no-inferioridad (δ=0.15); superar al oráculo = estrella.
2. ABORTs/ep del manager cae de 45 a ≤5 (S2 mata el metrónomo post-show; el coste Q grava el
   churn pre-show); el molinillo de rumbo NO reaparece.
3. Jugada completa ≥ 0.8 también en el manager; STALL del manager ≈ 0 (puede ELEGIR brazos que
   no necesiten rescate, a diferencia de los forzados).
4. Re-targets de la regla K escasos y con causa (S1/S2/S3 no tocan la caza).

## RUN-M1'''' y STOP

`--run M1pppp --total 120000 --n-envs 24 --seed 0 --opponent reactive --wolves-min 3`
(delib 0.05 default). STOP-M1'''' con el orden de firmas de siempre; **pregunta única del
visionado (dueño)**: ¿se ve la jugada simple ENTERA — un lobo muestra, el resto entra por el
otro lado — y el manager decidiendo CUÁNDO? Cola tras el STOP: **RUN-M2 (K=1000) → 1 réplica**.

---
**ADJUDICACIÓN DEL FALLBACK (gate de 40k, 2026-08-21T15:06Z)**: ligera de 40k con
ABORTs/ep = 0.4 ≤ 10 ⇒ **el fallback NO se activa**; el run continúa con DELIB_COST = 0.05
(único punto de decisión pre-registrado del entrenamiento; sin más intervenciones).
