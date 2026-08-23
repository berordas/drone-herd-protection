# STOP-M2 — LA ABLACIÓN DE LA TERMINACIÓN-POR-EVENTO: NI COLAPSO NI EMPATE — M2 pierde LAS DOS
# SEÑAS del resultado principal (la estrella y la estructura en G) con Δ = −0.145 [−0.265, −0.04],
# pero la JUGADA sobrevive al troceo (completa 1.00). Adjudicación de la lectura = DEL DUEÑO
# (el pre-registro contemplaba "colapso fuerte" o "≈"; esto cae ENTRE las dos ramas).

**Firmas en el orden de siempre**: 1º aserciones (PASAN: sin NaN; jugada completa 1.00; replay
del visionado determinista) · 2º VISIONADO (1 GIF, abajo) · 3º análisis.

## El run

RUN-M2 = receta y capa EXACTAS de M1'''' con UNA variable: **K=1000 FIJO** en lugar de la
terminación-por-evento (PREREGISTRO_M2 congelado antes de lanzar). 122.880 macro-pasos en
**1 h 46 (fps 19.4** — el troceo abarata el semi-MDP ×3.3; dato operativo, no de mérito).

## Números (200 semillas emparejadas vs Reactive-est)

| | M1'''' (control) | M2 (K=1000) |
|---|---|---|
| sev | **1.76** | 1.62 [1.32, 1.93] |
| Δ vs M1'''' emparejado | — | **−0.145 [−0.265, −0.04]** (IC excluye 0) |
| Δ vs B_oracle emparejado | **+0.10 [+0.03, +0.19]** (estrella) | **−0.04 [−0.17, +0.08]** (estrella PERDIDA) |
| P(a\|G) 1ª | keep 0.931 | **Δ180 0.862** (keep 0.03) — estructura G PERDIDA |
| P(a\|S) 1ª | Δ90 1.000 | Δ90 1.000 (igual) |
| jugada completa / show | 1.00 / 1.00 | 1.00 / 1.00 |
| ABORTs/ep · stalls | 0.28 · 9 | 0.20 · 10 |
| decisiones/ep | 3.5 | 3.4 |

## Lectura (para tu adjudicación)

- **La predicción pre-registrada ("colapso o degradación FUERTE de la emergencia") NO se cumple
  tal cual**: P(cebo)=1.0, jugada completa 1.00 — el mecanismo de la jugada NO se rompe con el
  troceo (el re-arranque re-abre alineación/meseta pero los relojes de S1/S3 vuelven a sacarla).
- **Tampoco es "M2 ≈ M1''''"**: la degradación es REAL (IC excluye 0) y quirúrgica — se pierde
  exactamente lo que distinguía al resultado principal: (a) la SUPERIORIDAD sobre el oráculo
  (la estrella), y (b) el CRITERIO en G (keep — la decisión de "no reposicionar cuando la
  geometría ya existe" — sustituido por Δ180 genérico). En S (donde el brazo dominante es
  robusto) el troceo no cambia nada.
- Lectura que propongo (tuya la firma): la terminación-por-evento no es NECESARIA para que la
  jugada exista, pero SÍ para el REFINAMIENTO que dio la estrella y la estructura fina en G —
  "ingrediente del margen, no del mecanismo". El coste computacional va al revés (M2 ×3.3 más
  rápido): el trade-off queda medido.

## Visionado (firma 2)

`visionado/gifs/m2_jugada_cortada_seed76_lobos_sev2.gif` (+timeline): episodio G con la conducta
nueva (Δ180 en G) y cortes K_MAX en mitad de la jugada — se ve el corte y la re-decisión sin que
la jugada muera. Artefactos: `eval/manager_M2_final__reactive.json` · `PREREGISTRO_M2.md` ·
`/data/hrl_m1/M2/`.

## Cola

La RÉPLICA de M1'''' (seed 1, mundo v3.7 PINEADO en wt_v37_replica @ 4bf5024) ya corre —
su STOP dará la barra de error del resultado principal. E0.4 (D2-Fase-1) en curso en paralelo.

---

## FIRMA DEL DUEÑO (2026-08-22T13:39Z): lectura adjudicada = "INGREDIENTE DEL MARGEN, NO DEL MECANISMO"

**Registro explícito**: la predicción FUERTE pre-registrada ("colapso o degradación fuerte de la
emergencia — la opción interrumpida a mitad de valle no puede sostener la jugada") **FALLÓ**.
La sustituye la lectura firmada: con S1/S3 sacando el show a ~300 ticks, el arco crítico
staged→show→suelta→strike cabe casi siempre dentro de un tramo de 1000 (seed 76: 292→790), y
la política re-elige la misma opción en cada corte ⇒ el MECANISMO de la jugada sobrevive al
troceo; lo que la terminación-por-evento compra es el MARGEN (la estrella sobre el oráculo y
el criterio fino keep|G).

| | M1'''' (por eventos) | M2 (K=1000 fijo) |
|---|---|---|
| **Margen**: sev / Δ vs oráculo | 1.76 / **+0.10 [+0.03, +0.19]** ★ | 1.62 / −0.04 [−0.17, +0.08] (★ perdida); Δ vs M1'''' −0.145 [−0.265, −0.04] |
| **Mecanismo**: P(cebo) / jugada completa / Δ90\|S | 1.0 / 1.00 / 1.000 | 1.0 / 1.00 / 1.000 (idéntico) |
| **Cómputo**: tiempo / fps | 5 h 44 / 6.0 | **1 h 46 / 19.4 (×3.3 más barato)** |
| **Disciplina de decisión**: decisiones/ep · ABORTs/ep · coste pagado | 3.5 · 0.28 · ≈0 | 3.4 · 0.20 · ≈0 (K_MAX domina por construcción) |
| **Criterio en G** | keep 0.931 | Δ180 0.862 (también la RÉPLICA: Δ180 — ver STOP-réplica) |
