# ENCARGO 2 — SEÑUELO v2 "directo con espera" (ESPECIFICADO; CONGELADO hasta el STOP-M1'')

Adenda post-visionado seed 84 (2026-08-20), v2 — única versión válida. Confirmado por el dueño
tras aclaración: **dirección, no destino**. PROHIBIDO implementar antes de la decisión en el
STOP-M1'' (opción A vs B).

## Especificación

- **Spawn del señuelo**: lado opuesto al frente principal (Δ180 ya lo induce; en CEBO_keep se
  respeta el spawn agrupado).
- **Aproximación**: rumbo RECTO hacia el centroide del rebaño, deteniéndose en el borde de la
  zona de merodeo (`decoy_hold_dist=130` del ACTIVE más cercano) — jamás más adentro antes del
  show (la expulsión a ≤20 lo hace inviable). **Se elimina el bordeo perimetral largo.**
- **Espera**: quieto/merodeo mínimo en ese borde hasta STAGED del asalto (latch existente);
  después show + ala rota SIN cambios.
- **Alcance**: solo la trayectoria de aproximación del señuelo, en la CAPA
  (`hrl/options_wolf.py`); `wolf_controllers.py` y `world.py` intactos.

## Qué debe presentar el informe del STOP-M1''

- **Opción A (aplicar)**: re-medir E0.1 sanity + B_spawn + B_oracle + cebo scriptado 2f,
  PREREGISTRO_v3, relanzar el manager — con horas estimadas.
- **Opción B (future work)**: documentado con el GIF de la seed 84.
- **Evidencia adjunta**: el sobrecoste del rodeo actual medido en el Encargo 1d —
  t(inicio→posición de merodeo) del señuelo REAL vs t teórico en línea recta a 4 m/s
  (`/data/hrl_m1/m1pp/audit_patrulla_sanity.json`, clave `decoy_1d`).

## Estado

- Encargo 1 (auditoría de patrulla) EJECUTADO: auditor permanente en el arnés (commit M) +
  pasada retroactiva (`AUDITORIA_PATRULLA.md`).
- Encargo 2: SIN código. Este documento es la especificación de referencia.
