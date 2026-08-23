# VERIFICACIÓN 0 del PLAN M1'''' — RESULTADO: PARAR Y AVISAR (2026-08-20)

Orden del dueño: "confirmar que los ABORTs interrumpen jugadas a punto de completarse, y que en
brazos SIN manager el show se dispara con normalidad. Si el guion también se atasca solo ⇒ PARAR
y avisar." **La segunda comprobación FALLA** ⇒ este informe es el aviso; ningún commit del plan
(Q / Q-bis / R / señuelo v2) se ha aplicado; el repo está intacto.

## (a) Manager (seed 63 mixto + 5 S con más ABORTs) — CONFIRMADO

**El 100% de los ABORTs interrumpen jugadas a punto de completarse** (frac_a_punto = 1.0 en los
6 episodios). Dos sabores:

| episodio | sev | ABORTs | ¿show? | sabor |
|---|---|---|---|---|
| s63 mixto | 8 | 1 | t=18667 | pre-show: STAGED con rumbo NO alcanzado (d2=18.8 m) |
| s35 lobos | 0 | 470 | t=919 | 17 pre-show staged + 453 post-show |
| s5 mixto | 0 | 469 | t=389 | 6 pre-show staged + 463 post-show |
| s67 lobos | 1 | 268 | t=4589 | post-show puro, d2 mediana **1.2 m** |
| s98 lobos | 4 | 199 | t=12656 | post-show puro, d2 mediana 5.7 m |
| s86 lobos | 6 | 143 | t=12727 | post-show puro, d2 mediana **1.1 m** |

- **Post-show** (el grueso): con el show ya disparado y el asalto ENCIMA de su presa (d2 ≈ 1-6 m),
  la condición del ABORT (ESCOLTA + 3/4 ACTIVE en el cono del asalto) se mantiene cierta de forma
  continua ⇒ el ABORT es un METRÓNOMO de 50 ticks (la gracia). Cada re-decisión = re-arranque =
  θ_asalto nuevo. El coste de deliberación (Commit Q) grava exactamente esto.
- **Pre-show**: ABORT con el asalto ESTACIONADO y el gate de rumbo bloqueado (bearing_ok=False).

## (b) Brazos SIN manager — **EL GUION SE ATASCA SOLO** (aquí salta la parada)

- **B_oracle en S** (CEBO Δ90, membership=manager, 20 episodios): solo **8/20 llegan a show**;
  **9/20 con STAGED sin show ≥ 400 ticks** (máx **23.570 ticks = el episodio ENTERO**); en los 9,
  el **100% de los ticks atascados tienen bearing_ok=False**; los 9 acaban sev 0.
- **B_spawn en G** (membership=spawn, sin gate de rumbo, 10 episodios): **9/10 shows, espera
  máxima 1 tick** ⇒ el CAMINO DEL SCRIPT está sano.

**Causa localizada**: el gate de rumbo de la CAPA (`_timing_manager`/`_bearing_ok`,
ASSAULT_BEARING_TOL_DEG=±25°, hrl/options_wolf.py — decisión de capa del Commit A, "se revisará
con E0.2") exige que el centroide del asalto alcance θ_asa=rumbo_inicial+Δ ANTES de disparar el
show; en S el deslizamiento por el borde oscuro no cierra los ±25° y el asalto queda ESTACIONADO
para siempre. Es EXACTAMENTE el modo de fallo que el script eliminó en v3.3 (docstring de
`assault_staged`: la alineación angular de v3.2 "tardaba cientos de pasos o no cerraba -> el cebo
no llegaba a mostrarse") — la capa lo REINTRODUJO para materializar Δ. wolf_controllers.py está
limpio: el interbloqueo es 100% de la capa.

## Consecuencias (por qué esto merece tu adjudicación antes de seguir)

1. **Las celdas S v3.6 están contaminadas**: Δ90 0.58 / Δ180 0.50 se midieron con 9/20 episodios
   en interbloqueo (sev 0 sin jugada). El paisaje S real de los brazos Δ con el show garantizado
   es DESCONOCIDO — la adjudicación de Estructura del STOP-M1'' ("falla con evidencia") se apoyó
   en ese paisaje.
2. **El molinillo cambia de naturaleza**: cada re-arranque re-fija θ_asa al rumbo ACTUAL ⇒
   bearing_ok pasa ⇒ el show puede disparar (s35: show en t=919 tras el churn; s63: t=18667). El
   manager aprendió, en parte, a DESATASCAR una opción bloqueada — no solo a "rotar hasta
   encontrar hueco". Parte del +1.26 sobre B_oracle es ventaja sobre un oráculo que en S se queda
   9/20 veces sin jugar.
3. **Q-bis (watchdog 400) cierra exactamente este agujero** — y al cerrarlo para TODOS, B_oracle
   en S subirá (9 sev-0 pasan a jugar). El re-nivelado del plan ya re-mide B_* y el metro, así
   que el PAQUETE TAL CUAL quedaría bien medido; lo que cambia es la LECTURA del hallazgo del
   STOP-M1'' y qué es exactamente lo que el coste de deliberación debe enseñar.

## Datos

`verif/verif0.json` (por-ABORT y por-episodio) · guion `verif/verif0_abort.py` · evals de origen
en `/data/hrl_m1/eval/*_v36__reactive.json`. Repo sin tocar; contenedor parado.

## Diagnóstico opcional (adjudicación del dueño): ¿lo agravó la patrulla estática?

**NO.** Los mismos 9 seeds bajo patrulla ÓRBITA v3.5 (omega=0.02), capa PRE-S1: **9/9 con
interbloqueo ≥400 ticks igualmente** (máx 21.849; solo s14 llega a show, en t=4788 tras 4.047
ticks atascado; sev 0 en los 9). El gate de rumbo se bloquea con AMBAS patrullas — el
interbloqueo es estructural del gate, no de la config de patrulla. `verif/verif0_orbita.json`.

## Post-S1 (test [S1] de hrl_check, capa con gate mejor-esfuerzo)

9/9 seeds con show (antes 0/9); TODAS las alineaciones terminan por `sin_progreso` (300 ticks
sin mejora de 2°) con error conseguido 43-110° — la alineación en S no progresa: era bloqueo
estructural. Con la jugada JUGADA, la defensa la gana igualmente en esos 9 seeds (sev 0), pero
los episodios colapsan de 23.570 a ~1.300-4.300 ticks (HERD_SAFE temprano). El paisaje S real:
celdas limpias del re-nivelado (100 pares).
