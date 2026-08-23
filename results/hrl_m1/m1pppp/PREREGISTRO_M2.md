# PREREGISTRO_M2 — RUN-M2, ABLACIÓN DE LA TERMINACIÓN-POR-EVENTO (CONGELADO 2026-08-21T21:15Z, antes de
# lanzar; firma 2 del dueño del 2026-08-21: "colapso o degradación fuerte de la emergencia")

**Qué se ablaciona**: la TERMINACIÓN-POR-EVENTO del semi-MDP (la decisión del manager dura hasta
MUERTE / HERD_SAFE / ABORT pre-show / FIN / techo) se sustituye por **K=1000 FIJO**: toda opción
se interrumpe y re-decide cada 1000 ticks, pase lo que pase. TODO lo demás idéntico a RUN-M1''''
(misma capa S1+S2+S3+CENSURA+Q+Q-bis+V2, física v3.7, receta exacta, DELIB_COST 0.05, seed 0,
wolves-min 3, Reactive-estática). Comando:
`--run M2 --total 120000 --n-envs 24 --seed 0 --opponent reactive --wolves-min 3 --fixed-k 1000`

**Contexto de M1'''' (el control, mismo todo salvo K)**: 1.76 [IC en TABLA_M1PPPP] vs
Reactive-est · estructura keep|G 0.931 / Δ90|S 1.000 / Δ180 0.000 · jugada completa 1.00 ·
ABORTs/ep 0.28 · P(cebo|G,n≥3)=1.0. Listones B_* v3.7 vigentes (PREREGISTRO_v3).

## Predicción pre-registrada (dueño)

**Colapso o degradación FUERTE de la emergencia**: la opción interrumpida a mitad de valle no
puede sostener la jugada: la jugada típica CRUZA la frontera de K=1000 (t_show mediana del
manager = 558; suelta 974-1419; strike hasta 2375 — el arco staged→show→suelta→strike abarca
1500-2400 ticks). Mecanismo esperado: cada corte re-arranca CEBO ⇒ re-abre
la fase de alineación (S1) y el reloj de meseta (S3) ⇒ el show se retrasa o no llega; P(cebo) y/o
la jugada completa caen, o la sev del manager cae hacia B_masa/B_spawn.

## Lectura pre-registrada

- Si **sev_M2 ≪ sev_M1''''** (Δ emparejado en las mismas 100×2 semillas con IC excluyendo 0 por
  margen claro) **y/o** la Emergencia/Estructura/jugada completa se degradan fuerte ⇒ **la
  terminación-por-evento queda DEMOSTRADA como ingrediente NECESARIO del resultado principal, no
  decorativo** — la ablación de necesidad que faltaba.
- Si M2 ≈ M1'''' ⇒ hallazgo (la terminación-por-evento no era el ingrediente) ⇒ DECISIÓN HUMANA
  PENDIENTE (nada se re-adjudica en silencio).
- Métricas del STOP-M2: tabla emparejada vs M1'''' y vs B_*; censura completa (jugada completa /
  show / suelta / strike); ABORTs/ep; STALLs listados; P(a) por estrato; eventos terminales
  (K_MAX dominará por construcción — se reporta la composición).

## STOP-M2

Orden de firmas de siempre (1º aserciones · 2º visionado — GIF de una jugada CORTADA por K=1000
si el mecanismo aparece · 3º análisis). Tras el STOP-M2: **1 RÉPLICA de M1''''** (semilla nueva,
`--run M1pppp_r1 --seed 1`, misma receta) para la barra de error del resultado principal — ya
firmada en la cola; su lanzamiento no espera a la firma del STOP-M2 (pipeline de cómputo), su
STOP sí lleva firmas. Nada más entra sin firma.
