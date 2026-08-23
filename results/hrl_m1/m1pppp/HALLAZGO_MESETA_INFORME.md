# HALLAZGO durante el Commit R (paquete M1'''') — 2º MODO DE INTERBLOQUEO DEL GUION: LA MESETA
# DE d_prey. PARAR Y AVISAR (2026-08-21T02:31Z). DECISIÓN HUMANA PENDIENTE.

## Estado del paquete al parar

COMMITTEADOS con verja 8/8 verde: **S1** (20d39db, gate mejor-esfuerzo) · **S2** (494a0cd, ABORT
solo pre-show; replays: ABORTs post-show 268/143/1/470 → 0/0/0/0) · **CENSURA** (cccbbd3) ·
**Q** (4bb5592, coste 0.05 + fallback 0.1 + --delib-cost) · **Q-bis** (5cb1360, tripwire 400).
**SIN COMMITTEAR** (working tree + `patches/r_v37_working_tree.patch`): **Commit R** (v3.7
relevo centinela: world pin + vuelo directo + coordinador con RANURA HEREDADA + re-gold de
battery_check — **battery_check TODO OK**, incluido el gemelo bit a bit: hand-off a 1.89 m del
puesto y cero recolocaciones). La verja de R está ROJA solo por el test [S1] (seed 14) — y la
causa es un HALLAZGO, no un bug de R.

## El hallazgo

Con R, el anillo de patrulla queda POR PRIMERA VEZ perfectamente estático (el fresco HEREDA la
ranura del saliente). Eso revela que el reparto por índice de la patrulla llevaba desde v3.0
ROTANDO a todos los drones una ranura en cada hand-off (bug silencioso de "intercambio entre
activos" — exactamente lo que tu protocolo prohíbe) — y esa rotación periódica SACUDÍA la
geometría y desatascaba jugadas de chiripa. Sin ella:

- **Seed 14 (CEBO Δ90, S) post-R**: alineación termina bien (sin_progreso, t=581) pero el asalto
  queda ESTACIONADO en el anillo oscuro **23.358 ticks** con **d_prey en MESETA a 222-233 m >
  assault_trigger_dist+show_lead = 210** ⇒ `assault_staged` (cláusula b, "a tiro") jamás cierta
  ⇒ ni show, ni STALL (el tripwire cuenta STAGED COMPLETO, tu letra), ni ESCOLTA: **VIGILANCIA
  eterna, sev 0 por timeout (23.570), con 20 relevos** y el anillo imperturbable. Pre-R el mismo
  seed mostraba a t=2775: era la ROTACIÓN espuria quien lo desatascaba.
- Los 9 seeds de interbloqueo post-R: 6 muestran solos (301-1497) · **2 rescatados por tu
  tripwire tal cual** (seeds 3 y 18: alineación lenta re-armando el reloj de sin-progreso;
  STALL a t=400 y jugada sigue) · **1 en el modo meseta** (seed 14, sin cobertura).
- El slide del hold "garantiza (b) en cualquier rumbo" (docstring v3.3) — la garantía FALLA con
  el anillo estático de verdad: el equilibrio empuje/anillo aparca al asalto donde acercarse a
  su presa es acercarse a un dron.

## Por qué paro (tus reglas)

Hallazgo nuevo ⇒ DECISIÓN HUMANA PENDIENTE, nunca arreglo silencioso; el test [S1] ("los 9
llegan TODOS a show") es tuyo y no se re-golda sin firma; y el tripwire es un instrumento
PRE-REGISTRADO cuya definición no amplío por mi cuenta. Con la verja roja, R no se committea y
el paquete queda en pausa exactamente aquí.

## Opciones para tu firma

- **A (tripwire-intención)**: el reloj del tripwire cuenta ESTACIONADO-EN-ANILLO (readiness
  posicional, sin la cláusula a-tiro) y arranca AL TERMINAR la alineación; 400 ⇒ show forzado +
  STALL. Cubre meseta y alineación lenta. Coste: STALL dejará de ser ≈0 en S (pasa a métrica de
  frecuencia de rescate; el gate del PREREGISTRO_v3 se re-formula: "cada STALL listado").
- **B (raíz, espejo de S1 — RECOMENDADA)**: la cláusula (b) del staged pasa a MEJOR-ESFUERZO en
  la capa, con la MISMA plantilla firmada de S1: si el asalto lleva ESTACIONADO en el anillo
  N ticks con d_prey SIN PROGRESO (mejora < Δm en N ticks; p.ej. Δm=5 m, N=300) ⇒ la cláusula
  (b) se da por satisfecha (staged por readiness posicional) ⇒ show por el guion. El tripwire
  queda de verdad ≈0 (solo red de seguridad); constantes CALIBRAR; test = seed 14 muestra y los
  otros 8 no cambian de mecanismo.
- **C (aceptar el modo)**: sev 0 por meseta = "la defensa gana el pulso"; re-gold de [S1] a
  "show O meseta documentada" — pero re-introduce en las celdas S jugadas sin jugar (lo que tu
  adjudicación VERIF-0 quiso eliminar), ahora con etiqueta de censura.

Evidencia: `verif/probe_s14.py` (+salida en este informe), `verif/probe_s1_postR.py` (tabla de
los 9), `verif/probe_r.py` (la rotación de ranuras medida: el hand-off 0→4 movía a 1/2/3 al
puesto del vecino). Los replays de S2 y el resto del paquete quedan en `verif/` y `patches/`.
