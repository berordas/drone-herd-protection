# PREREGISTRO_D2 — RUN-D2 (manager del bando DRON). CONGELADO 2026-08-22T13:40Z (firma GO del dueño),
# ANTES de escribir el env; la sección "Config del env" se añade con su commit, ANTES del run.

**Mundo**: v3.7.1-plazas-estacion (oficial; inocuidad Δsev=0.000). Capa dron:
hrl/options_drone.py (AllocatorCoordinator {4-0, 3-1, 2-2}; guardia revalidado, Commit D2a).
Capa lobo (atacante): la completa de M1'''' (S1+S2+S3+CENSURA+Q-bis+V2 + regla K + quórum N).

## Listones (E0.4, 100 semillas emparejadas por celda; mundo v3.7.1)

| defensa \ atacante | natural | cebo 2f | manager lobo M1'''' (congelado) |
|---|---|---|---|
| Dummy | 1.13 | 3.11 | 2.75 |
| Reactive-est (4-0) | 0.74 | 2.61 | 1.77 |
| **PROPORCIONAL (listón DURO)** | **0.25** | **0.85** | **0.61** |
| run09 | 0.69 | 2.53 | 1.78 |

Proporcional: KNC 0.0 · gana_guardia 0.78/0.80/0.82 · latencia 3-4.5 ticks · reasignaciones
1.95/22.3/9.8 por ep · **PENETRADO 32/433.6/71.5 ticks/ep (FLAG pre-registrado: reportado,
sin arreglar; si el manager lo SUBE más: DECISIÓN HUMANA)**.

## Receta (espejo del manager lobo — la que dio el resultado principal)

- Semi-MDP por EVENTOS: la decisión (partición) dura hasta MUERTE · CAMBIO del nº de clústeres
  percibidos (la INTERRUPCIÓN del bando dron; gracia 50 ticks) · HERD_SAFE · techo K_MAX=4500 ·
  FIN. **Coste de deliberación 0.05** (Q espejo): decisión tras INTERRUPCIÓN que CAMBIA de
  partición paga; mantener es gratis; tras terminal natural es gratis. **Fallback único
  pre-registrado: 0.1 si en la ligera de 40k las interrupciones-con-cambio/ep > 10.**
- **Acción Discrete(3)**: {4-0, 3-1, 2-2}. **Recompensa = −Δmuertes del tramo − coste**
  (la defensa minimiza). γ=1.0 episódico.
- **Obs ~40** (percepción HONESTA del bando dron: contactos ∪ confirmados vía analyze_threats;
  layout exacto en "Config del env"): clústeres (nº, tamaño/confirmados/rumbo/distancia de
  primario y secundario, cierre Δdist), octantes de amenaza (8), defensa (ACTIVE libres,
  partición vigente one-hot, ESCOLTA/ancla), rebaño/reloj (en juego, terneros, muertes, reloj),
  contexto (último evento one-hot, nº decisión), memoria temporal corta.
- **TRIPWIRE D2 (espejo de Q-bis)**: guardias asignados ≥400 ticks SIN clúster secundario
  percibido ⇒ vuelta forzada a 4-0 + evento STALL (salud; disparo en eval = listado = DHP).
- Oponentes de TRAIN: **mezcla natural (lobo scriptado) + manager lobo M1'''' CONGELADO**
  (50/50 por episodio, ckpt final reproducido DENTRO del env con su misma lógica de eventos —
  test de equivalencia bit a bit con ManagerEnv). EVAL: celdas de E0.4 (natural / cebo2f /
  manager) para comparar con los listones, mismas semillas.
- PPO SB3 MlpPolicy [64,64], lr 3e-4, γ=1.0, gae_λ=0.95, ent 0.02→0.005, clip 0.2, n_steps
  256, batch 512, 10 epochs, 24 envs, 120.000 macro-pasos, ckpt 5k, ligera 10k (40 semillas
  fijas, P(a) estocástica + contadores). Seed 0.

## Compuertas D2

- **Estructura (espejo)**: P(4-0 | 1 clúster percibido) alta Y P(3-1 ∪ 2-2 | 2º clúster
  percibido) alta (1ª decisión tras percibir el 2º clúster, n≥3); la partición NO parpadea
  (reasignaciones/ep ≤ las de la proporcional en la misma celda).
- **Competencia**: ≥ Reactive-est (4-0) con IC emparejado excluyendo 0 (las tres columnas);
  **no-inferior a la PROPORCIONAL (δ=0.15) en la celda manager-lobo (0.61) y en cebo2f (0.85)**;
  superarla = estrella.
- **Asignación estable**: interrupciones-con-cambio/ep ≤ 5 · STALL ≈ 0 (disparos listados) ·
  coste pagado reportado.
- **Auditoría**: 0 CRITICAL · PENETRADO por celda REPORTADO vs E0.4 (subida = DHP) · KNC ·
  carrera guardia-vs-asalto · censura del atacante.

## Predicciones pre-registradas

1. La proporcional es un listón DURO: el manager aprendido quedará ≈ proporcional
   (no-inferior), la estrella es improbable en 120k.
2. Estructura: 4-0 con 1 clúster y guardias con 2º clúster emergen (el paisaje lo decide con
   claridad: −66% de sev); la dimensión libre es CUÁNDO volver a 4-0 (PENETRADO).
3. PENETRADO del manager ≤ el de la proporcional (el manager puede retirar guardias que la
   regla fija mantiene) — si sube, DHP.

## Éxito y STOP

Éxito = Estructura + no-inferioridad vs proporcional (δ=0.15); superarla = estrella.
KILL-DATE vigente: lo que haya al final del día 5 se congela. STOP-D2 con el orden de firmas
de siempre; **pregunta única del visionado (dueño)**: ¿se ve el REPARTO — la barrera aguanta y
un guardia cubre el otro frente — y el manager decidiendo CUÁNDO?

---

## Config del env CONGELADA (2026-08-22T13:46Z; añadida con el commit del env, ANTES del run)

- `hrl/manager_drone.py`: **DroneManagerEnv** — acción Discrete(3) {4-0, 3-1, 2-2} sobre
  AllocatorCoordinator; **obs DRONE_OBS_SIZE=44** (layout exacto en la cabecera del módulo:
  clústeres percibidos vía analyze_threats — contactos ∪ confirmados —, primario/secundario
  (tamaño, frac confirmados, rumbo sin/cos, distancia), cierre Δdist, 8 octantes, ACTIVE libres,
  partición vigente one-hot, ESCOLTA/ancla del propio frente, rebaño/reloj, último evento
  one-hot(7), nº decisión; 2 reservadas); eventos terminales MUERTE / CLUSTER_CHANGE (gracia 50)
  / HERD_SAFE / K_MAX=4500 / STALL (tripwire guardia: ≥400 ticks sin 2º clúster ⇒ 4-0 forzado) /
  FIN; **DELIB_COST_D2 = 0.05** (interrupción = CLUSTER_CHANGE o STALL; paga solo al cambiar de
  partición); recompensa = −Δmuertes − coste.
- Atacantes de TRAIN: 50/50 por episodio {natural scriptado, **FrozenWolfManager** = ckpt
  M1'''' reproducido con la lógica de eventos de ManagerEnv — **equivalencia BIT A BIT verificada
  (hrl_check [D2-1])**}; tipos de episodio de TRAIN {lobos, mixto} 50/50 (solo-corzos no tiene
  decisiones que aprender; la EVAL E0.4 'natural' sí los incluye).
- Tests en verja: [D2-1] frozen ≡ ManagerEnv · [D2-2] env 4-0 ≡ Reactive bit a bit · [D2-3]
  determinismo + coste dirigido · [D2-4] tripwire dirigido · [D2a] guardia revalidado.
- Comando: `python3 -m hrl.train_drone_manager --run D2 --total 120000 --n-envs 24 --seed 0`
  (fallback único: `--delib-cost 0.1` si en la ligera de 40k interrupciones-con-cambio/ep > 10;
  en la ligera: `cambios_por_ep` sobre episodios con interrupción — se lee como tal).
- Eval del STOP: e04.py con defensa `dronemgr:<ckpt>` × atacantes {natural, cebo2f, manager}
  (100 semillas emparejadas, mismas celdas/listones que E0.4).
- Precisión del coste (antes del run, tras el smoke): "cambiar de partición" se evalúa respecto a
  la partición VIGENTE — tras un STALL la vigente es el 4-0 forzado, de modo que re-pedir guardias
  de inmediato PAGA (el smoke con la lectura ingenua mostró el tripwire degenerado en metrónomo:
  25 interrupciones/ep, 0 cambios, coste 0). Misma letra del pre-registro, cerrada la laguna.

---
**ADJUDICACIÓN DEL FALLBACK (gate de 40k, 2026-08-22T15:45Z)**: ligera de 40k con
cambios-tras-interrupción/ep = 0.6 ≤ 10 ⇒ **el fallback NO se activa**; el run continúa con
DELIB_COST_D2 = 0.05. (Lectura de la ligera: sev 0.25 · P(guardia|2º clúster) 1.0 · stalls 9/40 eps
· PENETRADO 26 · H 0.91.)

---
# PREREGISTRO RÉPLICA D2 (congelado 2026-08-22T19:12Z, ANTES del lanzamiento; firma del dueño: STOP-D2 opción B)

- **Objetivo ÚNICO**: barra de error del resultado de RUN-D2 — en particular del Δ(D2 − proporcional)
  contra el cebo scriptado 2f (+0.18 [+0.01, +0.37]). La réplica **NO adjudica nada nuevo**: ni abre
  opciones, ni arregla flags, ni cambia el listón.
- **Receta idéntica** salvo la semilla del aprendiz: `python3 -m hrl.train_drone_manager --run D2_r1
  --total 120000 --n-envs 24 --seed 1` (código = 313cb51, mundo v3.7.1-plazas-estacion, atacantes de
  train 50/50 {natural, FrozenWolfManager M1''''}, DELIB_COST_D2 0.05, mismo fallback de 40k:
  `--delib-cost 0.1` si cambios-tras-interrupción/ep > 10). Las semillas de MUNDO (eval ligera y
  E0.4) son las mismas que en RUN-D2: solo cambia la semilla del PPO/env.
- **Eval del STOP**: `stop_d2.sh /data/hrl_d2/D2_r1/model.zip` ⇒ las mismas 3 celdas × 100 pares
  (natural / cebo2f / manager lobo) contra los MISMOS listones de E0.4 (emparejados).
- **Predicciones** (se adjudican, no se persiguen):
  1. Estructura se reproduce: P(guardia | 2º clúster) ≥ 0.90 y la partición ante el 2º frente sigue
     siendo 2-2 (P(3-1 | 2º clúster) ≤ 0.10).
  2. Δ(D2_r1 − proporcional) vs cebo-2f es **positivo** (la réplica NO convierte la celda en
     no-inferior): IC de la réplica solapa con [+0.01, +0.37]. Tabla final: media de los dos runs
     con su IC conjunto (200 pares, 2 aprendices) SOLO como barra de error.
  3. Δ vs Reactive 4-0 con IC excluyendo 0 en las 3 celdas (se reproduce).
  4. PENETRADO ≥ proporcional en natural y cebo-2f (trade-off cobertura/reparto se reproduce).
- **Sin visionado nuevo** salvo anomalía (NaN, CRITICAL, P(guardia|2cl) < 0.5 o sev de una celda
  > 2× la de RUN-D2) — en ese caso PARAR y avisar, sin arreglar.
- **KILL-DATE ABSOLUTO**: al acabar la réplica (o al vencer el timebox del día 5) ⇒ CIERRE TOTAL:
  STOP final = parte de cierre con la tabla maestra (orden de firmas de siempre); ningún run nuevo.

**ADJUDICACIÓN DEL FALLBACK — RÉPLICA (gate de 40k, 2026-08-22T20:16Z)**: ligera de 40k con
cambios-tras-interrupción/ep = 0.50 ≤ 10 ⇒ **el fallback NO se activa**; la réplica continúa con
DELIB_COST_D2 = 0.05. (Lectura: sev 0.17 · P(guardia|2º clúster) 1.0 · P(2-2|2cl) 0.986 · stalls 7/40 eps ·
PENETRADO 19 · H 0.88; fps 12.1.)
