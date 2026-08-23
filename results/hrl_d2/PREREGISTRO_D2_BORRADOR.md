# PREREGISTRO_D2 — BORRADOR (adenda D2-Fase-1; NO CONGELADO: se congela, si hay GO, tras la
# firma del informe GO/NO-GO y con los listones de E0.4 dentro)

**Qué se entrena**: manager del bando DRON sobre la capa de opciones de reparto
(`hrl/options_drone.py`, AllocatorCoordinator): decidir CUÁNTOS asientos de barrera van al
FRENTE y cuántos a GUARDIA. Mundo **v3.7.1-plazas-estacion** (config oficial de D2, inocuidad
Δsev=0.000 verificada; conducta del guardia REVALIDADA bajo sonido siempre-activo, Commit D2a).

## Receta (espejo del manager lobo, la que acaba de dar el resultado principal)

- Semi-MDP por eventos (terminación por MUERTE / cambio de nº de clústeres percibidos /
  HERD_SAFE / techo K_MAX) + **coste de deliberación 0.05** (mismo diseño Q: interrupción +
  cambio de partición paga; mantener es gratis) — [el evento de interrupción exacto del bando
  dron se fija al congelar; candidato: flanco de nº de clústeres].
- **Acción Discrete(3)**: {4-0, 3-1, 2-2} (particiones del AllocatorCoordinator).
- **Obs ~40**: clústeres de amenazas (contactos ∪ confirmados — percepción honesta del bando
  dron), tamaño/rumbo/distancia por clúster, octantes de cobertura, estado de la escolta,
  memoria temporal corta. [Layout exacto al congelar.]
- Oponentes de TRAIN (propuesta): **mezcla natural + manager lobo M1'''' CONGELADO** (el
  atacante más duro disponible; ckpt final, sin gradiente).
- PPO SB3 [64,64], misma receta numérica que M1''''; 120k macro-pasos; ligera cada 10k con
  P(a) estocástica + censura.

## Compuertas (espejo)

- **Estructura**: P(4-0 | 1 clúster) alta Y P(3-1 | 2º clúster real) alta; 2-2 residual salvo
  paisaje que lo respalde (celdas E0.4 de la proporcional como referencia).
- **Competencia**: ≥ Reactive-est (4-0) con IC emparejado excluyendo 0; **no-inferior a la
  PROPORCIONAL scripted (δ=0.15)**; superarla = estrella.
- **Asignación estable**: ABORTs/ep ≤ 5 · STALL ≈ 0 · reasignaciones/ep del orden de la
  proporcional (listón de E0.4).
- **Auditoría**: 0 CRITICAL; PENETRADO por celda no peor que E0.4 (si sube: DECISIÓN HUMANA).

## Listones (de E0.4, PENDIENTES de sus 12 celdas)

Tabla defensas × atacantes {natural, cebo2f, manager-M1''''}: sev global y 2f, KNC, carrera
guardia-vs-asalto, latencia/reasignaciones, jugada completa del atacante, PENETRADO.
Anticipo del smoke (3 eps): proporcional vs cebo2f = sev 0.0, gana_guardia 1.0, latencia 3.

## Éxito

Estructura + no-inferioridad vs proporcional (δ=0.15); superar = estrella. STOP con orden de
firmas de siempre. NADA de Fase-2 (env + retrain) sin la firma del GO/NO-GO.
