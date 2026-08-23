# STOP-M1'''' — RUN-M1'''' CUMPLE EL CRITERIO DE ÉXITO PRE-REGISTRADO (estructura + no-inferioridad),
# CON ESTRELLA: supera a un oráculo SANO (+0.10 [+0.03, +0.19]) y el criterio keep|G / Δ90|S APARECIÓ.
# ETA consumida del paquete completo (firma meseta → este informe): ≈ 11,5 h (commits+re-nivelado ≈ 4 h ·
# retrain 5 h 44 · evals 1 h 15 · visionado ≈ 0,5 h).

**Firmas en el orden de siempre**: 1º aserciones (abajo, PASAN) · **2º VISIONADO DEL DUEÑO**
(`visionado/INDEX.md` — la pregunta única: ¿se ve la jugada simple ENTERA y el manager decidiendo
CUÁNDO?) · 3º este análisis.

## 0. El run

122.880 macro-pasos, 5 h 44 (fps 5.96), **sin NaN**. Config del PREREGISTRO_v3 (congelado antes de
lanzar): capa S1+S2+S3+CENSURA+Q+Q-bis+V2, física v3.7-relevo-centinela, receta EXACTA M1,
DELIB_COST 0.05. **Gate de 40k: PASA** (ABORTs/ep 0.4 ≤ 10; fallback no activado — anotado con
timestamp en el preregistro). Curva de ligera: 0.93 (10k) → 1.20 (40k) → 1.18 (120k); el ckpt de
60k evalúa 1.73 en el metro vs 1.76 el final — el aprendizaje está esencialmente completo a mitad
de run, SIN la "subida de la segunda mitad" que en M1'' fabricaba el molinillo.

## 1. Aserciones (firma 1) — PASAN

0 CRITICAL · 0 violaciones de contrato · gotera 16 cruces/200 eps (0.08/ep) · canal B (muertes) = 0
· **despertar tardío = 0 episodios** (el fenómeno del seed 77 DESAPARECE bajo v3.7 — el relevo
centinela con ranura heredada no abre ventanas) · replays del visionado deterministas (assert sev)
· verja 8/8 en los 8 commits del paquete. KNC manager 36.3% (oráculo 40.4%).

## 2. TABLA (completa en `TABLA_M1PPPP.md`; 100 semillas emparejadas; IC bootstrap 10k)

| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_oracle | jugada completa | aborts/ep | stalls |
|---|---|---|---|---|---|---|---|
| B_masa | 0.56 | 0.60 | 0.52 | −1.10 | n/a | 0 | 0 |
| B_spawn | 0.95 | 0.90 | 0.88 | −0.71 | 1.00 | 0 | 0 |
| B_oracle | 1.66 | 1.64 | 1.69 | — | 1.00 | 0.28 | 9 |
| manager 60k | 1.73 | — | — | +0.07 [−0.01, +0.15] | 1.00 | 0.29 | 9 |
| **manager final** | **1.76** | **1.75** | **1.76** | **+0.10 [+0.03, +0.19]** | **1.00** | **0.28** | **9** |

Δ(manager − B_spawn) = +0.81 [+0.56, +1.09]. Gaps de transferencia: manager −0.01 [−0.24, +0.20]
(run02) y −0.01 [−0.14, +0.14] (run09) ≈ oráculo (−0.02 / +0.03).

## 3. Compuertas (PREREGISTRO_v3, congelado antes del retrain)

- **Emergencia**: P(cebo|G,n≥3) = 1.0 — **PASA** (P(MASA)=0 en todo, como siempre: se juzga
  no-vacua JUNTO a la Estructura, que esta vez discrimina de verdad).
- **Estructura**: **PASA — POR PRIMERA VEZ EN LA ETAPA 1.** P(keep|G,n≥3) 1ª decisión = **0.931** ·
  P(Δ90|S) = **1.000** · **P(Δ180) = 0.000 en ambos estratos** — exactamente la cláusula
  pre-registrada, y ahora RESPALDADA por el paisaje medido (celdas limpias: Δ90 1.71 mejor brazo
  de S; Δ(Δ180−Δ90) = −0.29). Estocástica: Pstoch(Δ90|S)=0.962, H=0.77 — el disparo del desempate
  NO se activa (prefiere Δ90). Re-targets 0.065/ep, 0 bloqueados, causa "protegida" (sub-cláusula
  PASA).
- **Competencia**: **PASA con ESTRELLA** — ≥ B_spawn con IC excluyendo 0 (+0.81) y **SUPERA a
  B_oracle (+0.10 [+0.03, +0.19])** — no-inferioridad (δ=0.15) trivial, y la estrella esta vez es
  sobre un oráculo SANO (1.66, jugando el 100% de sus jugadas), no sobre uno interbloqueado.
- **Transferencia**: **PASA** (gaps ≈ oráculo, ver tabla).
- **Auditoría**: **PASA** (0 CRITICAL; relevos v3.7 sin STRANDED anómalo; patrulla D≤200).
- **NUEVAS**: jugada completa del manager **1.00** (≥0.8 ✔) · ABORTs/ep **0.28** (≤5 ✔) ·
  **STALL = 9 ≠ 0 ⇒ LISTADOS (decisión humana pendiente, pre-registrada)** — ver §5.

**VEREDICTO según el pre-registro ("éxito = estructura + no-inferioridad"): RUN-M1'''' CUMPLE EL
CRITERIO DE ÉXITO**, con estrella, y con el único asterisco de §5.

## 4. Predicciones pre-registradas — adjudicación

1. **(Dueño) CUMPLIDA**: B_oracle subió (1.00 → 1.66; celda S Δ90 0.58 → 1.71) y la ventaja del
   manager ENCOGIÓ de +1.26 a **+0.10** — y aun así el IC excluye 0.
2. **CUMPLIDA**: ABORTs/ep 45 → **0.28** (eventos: 56 ABORT vs 285 MUERTE en 200 eps); decisiones
   49 → 3.2/ep; coste de deliberación PAGADO ≈ 0.00/ep (el manager ni siquiera cambia de opción
   tras un ABORT: mantiene o el episodio avanza) — el molinillo NO reaparece.
3. **PARCIAL**: jugada completa 1.00 ✔; STALL 9 ≠ 0 (ver §5 — propiedad del brazo, no de la política).
4. **CUMPLIDA**: re-targets 0.065/ep con causa y cadencia (la caza K intacta).

## 5. Los 9 STALL del manager (único item para tu adjudicación; pre-registrado como DHP)

Los 9 episodios con tripwire del manager (vs Reactive) son **EXACTAMENTE los 9 del oráculo**
(solape 100%): seeds 3/18/61/68 (lobos y mixto) + 74 lobos — **todos S**, 1 rescate/ep, t_show
400-1130, y la jugada se COMPLETA tras el rescate (s68 sev 3, s74 sev 4). Es la ALINEACIÓN LENTA
del brazo Δ90-en-S re-armando el reloj de sin-progreso de S1 (los seeds tipo 3/18 de tu nota de la
firma meseta): una propiedad del BRAZO en la capa actual, idéntica en manager y oráculo — no una
conducta del manager. Frecuencias en brazos forzados (celdas): Δ90 9%, Δ180 25%. Tal como
firmaste: se reporta, S3 no se amplía, el contador es la métrica. GIF 5 del visionado muestra un
rescate completo (s68: STALL a t=400 → show → 3 muertes).

## 6. Censura y mecánica (estándar nuevo, primera cosecha)

Manager: jugada completa 1.00 · con show 1.00 · con staged 1.00 · con strike 0.597 (el 40% de las
jugadas completas mueren en la barrera: la defensa NIEGA el strike jugando — sev 0 JUGANDO, no sin
jugar) · t_show mediana 558. El señuelo v2 elimina el bordeo (barrido <45° en test; el 1d bimodal
muere). Relevos v3.7 en todas las evals sin recolocaciones.

## 7. Cola (nada arranca antes de tu firma)

**RUN-M2 (K=1000 fijo — la ablación de necesidad)** → **1 réplica M1''''**. Artefactos:
`TABLA_M1PPPP.md` · `PREREGISTRO_v3.md` (con gate 40k anotado) · eval/*_v37 + manager_M1pppp_* ·
`celdas_s_v37.json` · `sanity_capa_v37.json` · `metro/` · `canal_{manager,oracle}_v37.json` ·
`visionado/` (GIFs + timelines + INDEX) · `renivelado_logs/` · verif/ (guiones).
