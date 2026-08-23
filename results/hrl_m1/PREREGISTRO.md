# PREREGISTRO — Etapa 1, RUN-M1 (manager de lobos, semi-MDP sobre opciones congeladas)

Fecha de congelación: 2026-08-19 (ANTES de lanzar RUN-M1 y de ver ningún checkpoint del manager).
Código: commits G `73389dc` · H `4f40af5` · I `dc02b6f` · I-bis `5049017` (flags adenda 4, OFF).
Mundo: v3.5-sonido (`8aeaf89`). Oponente de entrenamiento: Reactive v3.5 congelado.

## Listón congelado — B_oracle (regla destilada de E0 en v3.5)
Regla: CEBO_keep si G ∧ n≥3 · CEBO(Δ90) si S ∧ n≥3 · MASA si n≤2; decidida en t=0 y MANTENIDA
(sin memoria: tras un ABORT_BAIT_FAILED vuelve a pedir la misma opción). Metro 100 semillas
emparejadas (0-99 × lobos/mixto), políticas deterministas.

| B_oracle | sev media [IC95 bootstrap 10k] | lobos | mixto | G | S | decisiones/ep | eventos |
|---|---|---|---|---|---|---|---|
| vs Reactive v3.5 | **0.885 [0.645, 1.140]** | 0.94 | 0.83 | 2.60 | 0.18 | 72.4 | MUERTE 143 · ABORT 14.050 · K_MAX 95 · success 116/200 |
| vs run02-eval | **1.020 [0.775, 1.285]** | 1.13 | 0.91 | 2.52 | 0.41 | 74.0 | MUERTE 155 · ABORT 14.377 · K_MAX 75 · success 105/200 |

Observación pre-registrada sobre el listón: la regla sin memoria entra en BUCLE de re-CEBO tras
cada ABORT_BAIT_FAILED (~70 abortos/ep de 50 ticks): es legítimo para la regla y es precisamente
una de las "vías esperables" por las que el manager puede superarla (pasar a MASA tras el aborto).
Artefactos: /data/hrl_m1/eval/oracle__reactive.json · oracle__run02.json. (B_masa y B_spawn se
miden después, sin prisa; run09 se añade a la tabla al terminar.)

## Compuertas M1-* (tal cual la misión; sin cambios por la adenda 4)
- **M1-Emergencia**: P(cebo | G, n≥3) ≥ 0.8 al final + curva de aparición (eval_ligera.jsonl,
  40 semillas fijas, cada 10k macro-pasos).
- **M1-Competencia**: sev(manager) ≤ sev(B_spawn) con IC emparejado excluyendo 0; NO-INFERIOR a
  B_oracle con δ = 0.15 (IC emparejado de Δ(manager − oracle) con límite superior < +0.15);
  superar a B_oracle (IC < 0) = resultado estrella.
- **M1-Estructura**: P(cebo|n=2) baja vs P(cebo|n≥3) alta; P(Δ180) ≈ 0; en S prefiere Δ90.
- **M1-Auditoría**: 0 CRITICAL; aserciones de siempre; contador PENETRADO en el informe.
- Adenda 4 §1 (solo eval): tabla-escalera contra {Reactive v3.5, run02-eval, run09}; gap de
  transferencia Δsev(Reactive→run09) del manager vs el de B_oracle.
- Adenda 4 §2 (contingencia, SOLO AVISO en log, jamás auto-activada): si en la ligera de 40k
  P(cebo|G,n≥3) < 0.3 → candidato a relanzar con warmup G 60% los primeros 30k (decisión humana).

## RUN-M1 (receta congelada)
PPO SB3 MlpPolicy [64,64], lr 3e-4, γ=1.0, gae_λ 0.95, ent 0.02→0.005, clip 0.2, n_steps 256,
batch 512, 10 epochs, 24 envs SubprocVecEnv, 120k macro-pasos, checkpoints 5k, ligera 10k.
Predicción pre-registrada RUN-M2 (K=1000 fijo): colapso a MASA o emergencia muy degradada.

## Orden de firmas del STOP-M1
1º aserciones · 2º VISIONADO DEL DUEÑO con log por GIF · 3º análisis externo.
