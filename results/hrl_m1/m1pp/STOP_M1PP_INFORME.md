# STOP-M1'' — RUN-M1'' completado: el churn de PRESA está cerrado, la Competencia da estrella (+1.26 sobre el oráculo), pero la Estructura FALLA con evidencia y aparece un mecanismo nuevo: el MOLINILLO de rumbo (2026-08-20)

**Firmas en el orden de siempre**: 1º aserciones (abajo, PASAN) · **2º VISIONADO DEL DUEÑO**
(`visionado/INDEX.md`, 7 GIFs + referencia, log por GIF) · 3º este análisis.

## 0. El run

122.880 macro-pasos, 5h25, 6.3 fps, **sin NaN** (config del PREREGISTRO_v2: capa K + fallback
quórum + auditor, v3.6-estática, train n~U{3,4,5}, eval natural). Curva: ligera 10k sev 0.55 →
60k ~1.0 (ckpt 60k evalúa 1.58 en el metro) → final 1.38 en ligera / **2.26 en el metro** (la
subida fuerte es de la segunda mitad). Contingencia de currículo: jamás avisada (P(cebo|G)≈1
desde 10k).

## 1. Aserciones (firma 1) — PASAN

0 CRITICAL · 0 violaciones de contrato · gotera 1 cruce en 200 episodios · replays del visionado
deterministas (assert sev exacto) · verja 8/8 en los commits de la config (K→O). KNC 34.5%
(= oráculo 33.5; **nota pactada: KNC ~×2 al cebar — 17.5% MASA → 34% cebo: firma del canal
trasero**).

## 2. TABLA (completa en `TABLA_M1PP.md`; 100 semillas emparejadas; IC bootstrap 10k)

| política | vs Reactive-est | vs run02 | vs run09 | Δ vs B_oracle | gap run02 | gap run09 |
|---|---|---|---|---|---|---|
| B_masa | 0.57 | 0.62 | 0.53 | −0.43 | +0.05 | −0.04 |
| B_spawn | 0.98 | 0.85 | 0.87 | −0.01 | −0.14 | −0.12 |
| B_oracle | 1.00 | 0.91 | 0.99 | — | −0.09 | −0.01 |
| manager 60k | 1.58 | — | — | +0.58 [+0.30, +0.86] | — | — |
| **manager final** | **2.26** | **2.20** | **2.17** | **+1.26 [+0.93, +1.60]** | −0.06 [−0.32, +0.19] | −0.10 [−0.27, +0.08] |

## 3. Compuertas (PREREGISTRO_v2 congelado antes de lanzar + adenda de adjudicación 13:52Z)

- **Emergencia** (P(cebo|G,n≥3) ≥ 0.8): **1.0 — PASA**, pero de nuevo con sabor vacuo: cebo≈1.0
  en TODO (P(MASA|1ª decisión) = 0 en G y en S; el fallback de quórum absorbe n≤2).
- **Estructura**: **FALLA con evidencia**. P(a|S,1ª) = Δ180 1.00 (la cláusula pedía Δ90 alta y
  Δ180≈0). **El disparo de tu adenda se activó** (Pstoch(Δ180|S)=0.948, H(a|S)≈0.25<0.9) → celdas
  S medidas bajo v3.6 ANTES de adjudicar: MASA 0.33 · **Δ90 0.58** · **Δ180 0.50** →
  Δ(Δ180−Δ90) = −0.08 [−0.51, +0.36] → **Δ180 < Δ90: la cláusula falla con evidencia** (regla
  pre-registrada sobre el estimador puntual; nota honesta: IC ancho que cruza 0). En G: keep 0.48
  / Δ180 0.52 (mixto, tampoco el criterio predicho). La SUB-cláusula de re-targets SÍ pasa:
  0.07/ep, todos causa "protegida", cadencia ≥ cooldown (GIF 2: caso de libro).
- **Competencia**: **PASA con ESTRELLA** — ≥ B_spawn con IC excluyendo 0 (+1.27 [+0.93, +1.62]);
  supera a B_oracle en +1.26 [+0.93, +1.60] (no-inferioridad trivial).
- **Transferencia**: **PASA** — gaps del manager (run02 −0.06 [−0.32,+0.19]; run09 −0.10
  [−0.27,+0.08]) no peores que los del oráculo (−0.09 / −0.01) dentro de ruido; el manager
  también rinde 2.17-2.20 contra las defensas MARL.
- **Auditoría**: **PASA** (0 CRITICAL; churn/re-targets/PENETRADO 7.5 ticks/ep en el informe;
  auditor de patrulla activo — abajo).

## 4. El MECANISMO (lo importante): MOLINILLO DE RUMBO — hallazgo, DECISIÓN HUMANA PENDIENTE

La predicción 4 falló en la dirección reveladora: +1.26 (M1 dio +0.42 con el exploit de presa).
El churn de PRESA está **cerrado y verificado** (gemelo seed 21: 0 RETARGETs; re-targets 0.07/ep
en 200 episodios; K1-K4 verdes). Lo nuevo:

- dec/ep 49.1 con **ABORT 45/ep**; option_starts 4.5/ep; P(a|todas las decisiones): en G el 88%
  son Δ90 (tras abrir keep/Δ180), en S keep 59% / Δ90 35% tras abrir Δ180.
- En S el manager saca **1.89** donde el MEJOR brazo estático da 0.58 — la ganancia no está en
  elegir bien UNA opción sino en la SECUENCIA: cada re-arranque de CEBO(Δ) re-computa
  θ_asalto = rumbo ACTUAL del paquete + Δ (regla de capa diseñada para UNA decisión) → una
  cadena ABORT→re-decisión hace ROTAR el asalto alrededor del rebaño más rápido de lo que la
  barrera (anclada al ancla con histéresis) re-apunta. GIFs 3 y 4.
- El ckpt 60k (pre-molinillo) da 1.58; el final 2.26 — emerge en la segunda mitad, con la
  entropía ya baja.
- ¿Legítimo (una manada rodeando de verdad re-evalúa su eje de ataque) o artefacto de interfaz
  (θ_asa re-leído del rumbo actual en cada arranque + ABORT como reloj — el análogo ANGULAR del
  exploit de M1)? Igual que entonces: **no lo arreglo sin tu firma**. Cierres posibles (NO
  aplicados): θ_asa PERSISTENTE entre re-arranques de la misma opción (el espejo exacto del
  Commit K para el rumbo), histéresis/cooldown en el ABORT, o Δ relativo al SPAWN en vez de al
  rumbo actual. Cualquiera cambia el MDP ⇒ re-entrenar.

**Veredicto según el pre-registro**: "éxito = estructura + no-inferioridad" ⇒ **RUN-M1'' NO
cumple el criterio de éxito** (Estructura falla); Competencia/Transferencia/Auditoría pasan y el
+1.26 queda como HALLAZGO del mecanismo dinámico, pendiente de tu adjudicación
(¿capacidad táctica real = "rotar hasta encontrar hueco", o gaming de interfaz v2?).

## 5. Predicciones pre-registradas — adjudicación honesta

1. "Re-arranques/ep caen fuerte": **PARCIAL** — los re-arranques que RE-FIJABAN PRESA cayeron a
   ~0 (eso era el exploit), pero las re-decisiones siguen altas (49/ep vs 37 en M1): el churn
   migró de la presa al rumbo.
2. "Re-targets con causa y cadencia": **CUMPLIDA** (0.07/ep, 100% protegida, cooldown limpio).
3. "Aparece criterio": **FALLA** — G/S difieren algo (keep+Δ90 en G, Δ180+keep en S) pero no el
   criterio predicho, y las celdas S medidas no respaldan su Δ180 inicial.
4. "Ventaja < +0.42": **FALLA** (+1.26) — la dirección del fallo es la señal (mecanismo nuevo).

## 6. Canal/fases, despertar tardío y patrulla (adendas del dueño)

| política | muertes | canal A / B | despertar tardío (eps · muertes · lag) |
|---|---|---|---|
| B_masa | 114 | 114 / 0 | 0 · 0 · — |
| B_spawn | 197 | 197 / 0 | 1 (seed 77) · 8 · 17 |
| B_oracle | 200 | 200 / 0 | 1 (seed 77) · 8 · 17 |
| **manager** | 452 | 452 / **0** | **1 (seed 8 mixto) · 2 · 4** |

**Canal B (muertes) = 0 en todas las políticas — el fenómeno es LATENCIA, no fase** (anotación
pactada). KNC por fase: todo en ESCOLTA-BARRERA (masa 17.5% / spawn 34.0% / oracle 33.5% /
manager 34.5%). d_min al latch: tardíos ~93 m vs ~118 del resto. Pareja ilustrativa en el INDEX
(GIF 7 ↔ seed 77). Patrulla: regla dura D≤200 cumplida (firma previa); el manager no la altera.

## 7. ENCARGO 2 — decisión del señuelo v2 (spec congelada en `ENCARGO2_SENUELO_V2_SPEC.md`)

Evidencia 1d: sobrecoste del rodeo BIMODAL — mediana 10.7 ticks / p90 677 / máx 1078 (media 202);
la mitad ya va recta, la cola del bordeo largo es ~40% de episodios.

- **Opción A (aplicar ahora)**: implementar la aproximación directa-con-espera (solo capa) +
  test → re-medir sanity E0.1 (~20 min) + B_spawn/B_oracle (~40 min) + cebo scriptado 2f
  (~15 min) → PREREGISTRO_v3 → relanzar manager (~5.5 h) + evals del STOP (~1.5 h).
  **Total ≈ 8-9 h de cómputo (una noche)**. Nota: si además decides cerrar el molinillo, es el
  MISMO ciclo de re-entrenar — un solo relanzamiento cubriría ambos.
- **Opción B (future work)**: documentado con el GIF de la seed 84 y el 1d; el manager actual ya
  compensa parte del rodeo con la secuenciación.

## 8. Cola (nada arranca antes de tu firma)

RUN-M2 (K=1000 fijo — la ablación de necesidad; con el molinillo vivo, K fijo también corta su
reloj: lectura doble) → 1 réplica M1'' → (si hay días) M4. Tu adjudicación del molinillo decide
si antes va un M1''' con el cierre angular (± señuelo v2, opción A).

*Artefactos*: TABLA_M1PP.md · eval/{...}_v36__{reactive,run02,run09}.json +
manager_M1pp_{final,60k}__*.json · canal_{masa,spawn,oracle,manager}__reactive.json ·
celdas_s_v36.json · visionado/ (GIFs+timelines+INDEX) · PREREGISTRO_v2.md (con adenda 13:52Z) ·
AUDITORIA_PATRULLA.md (con tu firma) · forense_s77.json · verif/ (scripts y logs).

---

## ADENDA DE RE-ADJUDICACIÓN (firma del dueño tras VERIF-0 de M1''''; escrita 2026-08-20T20:28Z)

- **La compuerta de Estructura pasa de "FALLA con evidencia" a "NO ADJUDICABLE — instrumento
  contaminado"**: las celdas S v3.6 contra las que se adjudicó (MASA 0.33 / Δ90 0.58 / Δ180 0.50)
  se midieron con **9/20 episodios de B_oracle en S en INTERBLOQUEO** (asalto ESTACIONADO sin
  show ≥400 ticks, máx 23.570 = episodio entero, sev 0, 100% de los ticks con bearing_ok=False)
  — causa: el gate de rumbo ±25° de la CAPA (`_bearing_ok`/`_timing_manager`,
  hrl/options_wolf.py). Evidencia: `/data/hrl_m1/m1pppp/verif/verif0.json` +
  `/data/hrl_m1/m1pppp/VERIF0_INFORME.md`.
- **NO se voltea a PASA**: se ANULA y se re-adjudica en el STOP-M1'''' contra celdas S LIMPIAS
  (capa S1+S2, 100 pares por brazo), con el procedimiento de desempate ya firmado si el manager
  re-prefiere Δ180|S.
- La lectura del MOLINILLO queda igualmente re-abierta: parte del churn era DESATASCADOR de una
  opción bloqueada (el re-arranque re-fija θ_asa al rumbo actual ⇒ el show puede disparar).
- **Nota de proceso (dueño)**: la señal existía en E0.A(iii) (60% sin staged) y se leyó como
  "reposicionamiento largo". De ahí nace la MÉTRICA DE CENSURA (hitos staged/show/suelta/strike +
  tasa de jugada completa junto a la severidad, estándar en todas las tablas): sev 0 sin jugar ≠
  sev 0 jugando y fallando.
