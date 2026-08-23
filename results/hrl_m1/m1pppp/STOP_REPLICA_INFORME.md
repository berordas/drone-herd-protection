# STOP-RÉPLICA (M1pppp_r1, seed 1, mundo v3.7 PINEADO @ 4bf5024) — LA BARRA DE ERROR DEL
# RESULTADO PRINCIPAL: la COMPETENCIA y la ESTRUCTURA-EN-S se REPLICAN; la ESTRELLA y el
# keep-EN-G no (eran del seed 0). El núcleo robusto del resultado queda acotado.

**Firmas**: 1º aserciones (PASAN: sin NaN, 6h04, replay determinista de la receta; mundo v3.7
exacto vía worktree pineado — regla de versiones del diseñador) · 2º visionado (opcional: sin
GIFs nuevos — la conducta es la de M2 en G y la de M1'''' en S, ambas ya visionadas) · 3º esto.

## Números (200 semillas emparejadas vs Reactive-est)

| | M1'''' (seed 0) | RÉPLICA (seed 1) | ¿se replica? |
|---|---|---|---|
| sev | 1.76 | 1.69 [1.38, 2.01] | **SÍ** — Δ(R1−M1'''') = −0.075 [−0.20, +0.045] |
| Δ vs B_oracle | +0.10 [+0.03, +0.19] ★ | +0.03 [−0.12, +0.175] | no-inferioridad (δ=0.15) **SÍ**; **estrella NO** |
| P(Δ90\|S) 1ª | 1.000 | **1.000** | **SÍ** (también en M2: el invariante) |
| P(keep\|G) 1ª | 0.931 | **0.000** (Δ180 0.931) | **NO** (como M2) |
| jugada completa | 1.00 | 0.955 | ~sí (6 eps sin show; stalls 18) |
| ABORTs/ep | 0.28 | 0.46 | sí (≪ 5) |

## Lectura (para tu firma)

- **Núcleo REPRODUCIBLE del resultado principal**: cebo siempre (P(cebo)=1.0) · **Δ90 en S**
  (3 de 3 runs: M1'''', M2, R1 — el invariante duro, respaldado por las celdas limpias) ·
  competencia ≥ B_spawn y **no-inferior al oráculo sano** · jugada completa ~1 · sin molinillo
  (aborts ≪ 5).
- **Sensible a la semilla**: la ESTRELLA (superar al oráculo: +0.10 era del seed 0) y **keep|G**
  (2 de 3 runs prefieren Δ180 en G). Nota: el paisaje G entre keep y Δ180 NUNCA se midió en
  celdas (E0.1-G midió keep vs MASA, +1.16); puede ser PLANO y la semilla decide — si quieres
  celdas G keep-vs-Δ180 antes de escribir la memoria, es 1 medición (~30 min), tu firma.
- Para la MEMORIA del TFG: el claim defendible es "estructura-en-S + no-inferioridad,
  reproducido en réplica"; la superioridad (+0.10) se reporta como del run principal con su
  réplica al lado (+0.03 [−0.12, +0.18]).

Artefactos: eval/manager_M1pppp_r1_final__reactive.json · /data/hrl_m1/M1pppp_r1/ · worktree
wt_v37_replica @ 4bf5024 (PIN_REPLICA.txt).

## Cola

VACÍA — todo lo firmado está ejecutado. Pendientes de TU firma: lectura del STOP-M2
("margen, no mecanismo") · este STOP-réplica (± celdas G keep-vs-Δ180) · GO/NO-GO de D2.

---

## FIRMA DEL DUEÑO (2026-08-22T13:39Z): STOP-RÉPLICA FIRMADO — CLAIM PRINCIPAL DEL TFG RE-FORMULADO

**"Estructura-en-S (P(Δ90|S) = 1.000 en 3/3 runs) + no-inferioridad al oráculo sano (δ=0.15),
reproducido en réplica."** La estrella (+0.10 [+0.03, +0.19]) y keep|G (0.931) quedan como
PROPIEDADES DEL RUN PRINCIPAL, reportadas junto a la réplica (+0.03 [−0.12, +0.18]; Δ180|G
0.931). Celdas G (keep vs Δ180, 100 pares, v3.7 pineado) LANZADAS por orden del dueño — su
resultado se anota aquí abajo y en DISEÑO.md: si Δ≈0 con IC estrecho ⇒ "paisaje G plano — la
política converge donde el paisaje decide (S) y varía por semilla donde no distingue (G)"; si
Δ≠0 ⇒ se reporta tal cual y se anota qué run acertó.

### Celdas G medidas (2026-08-22T13:45Z; v3.7 pineado, 100 pares, G n≥3, vs Reactive-est)

keep **2.76 [2.33, 3.21]** · Δ180 **2.84 [2.40, 3.28]** · Δ90 2.51 [2.08, 2.94] ·
**Δ(Δ180 − keep) = +0.08 [−0.22, +0.38]** · Δ(Δ90 − keep) = −0.25 [−0.71, +0.21]. Jugada completa
1.0 en los tres brazos. **Anotación firmada: "paisaje G PLANO — la política converge donde el
paisaje decide (S: Δ90 1.71 vs MASA 0.30, 3/3 runs) y varía por semilla donde no distingue (G:
keep ≈ Δ180 ≈ Δ90)."** Ningún run "acertó" ni "falló" en G: keep (seed 0) y Δ180 (réplica, M2)
son equivalentes al paisaje. `celdas_g_v37.json`.
