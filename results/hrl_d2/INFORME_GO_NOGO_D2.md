# INFORME GO/NO-GO — D2-FASE-1 (E0.4 completo; SOLO evaluación, ninguna física tocada)

**Recomendación: GO** (firma del dueño pendiente). Las dos preguntas del encargo, respondidas:

## 1. ¿La proporcional bate a 4-0 contra el cebo? — SÍ, de forma aplastante

E0.4 (100 semillas emparejadas por celda; mundo v3.7.1; capa del atacante completa):

| defensa \ atacante | natural | cebo 2f | manager M1'''' (congelado) |
|---|---|---|---|
| Dummy | 1.13 | 3.11 | 2.75 |
| Reactive-est (4-0) | 0.74 | 2.61 | 1.77 |
| **PROPORCIONAL** | **0.25** | **0.85** | **0.61** |
| run09 | 0.69 | 2.53 | 1.78 |

- Contra el **cebo scriptado 2f**: 0.85 vs 2.61 de la 4-0 (**−67%**); contra el **manager lobo
  ENTRENADO** (el atacante más duro del proyecto): **0.61 vs 1.77 (−66%)** — la regla
  proporcional de 30 líneas neutraliza al resultado principal de la Etapa 1.
- **KNC = 0.0 en las tres columnas** (Reactive: 35-46%): con guardia, el canal trasero MUERE —
  toda muerte llega con el killer CONFIRMADO. La firma del cebo (KNC ×2) desaparece.
- Subconjunto 2-frentes en natural: 0.96 vs 3.00 de la 4-0.

## 2. ¿Quién gana la carrera guardia-vs-asalto? — EL GUARDIA

gana_guardia = **0.78 / 0.80 / 0.82** (natural / cebo2f / manager; n = 23/84/107 carreras);
**latencia de la proporcional 3-4.5 ticks** (≈ 1 frontera de frame_skip); reasignaciones/ep
1.95 / 22.3 / 9.8 (la columna cebo2f parpadea más: listón para el gate de estabilidad de D2).

## FLAG pre-registrado (DECISIÓN HUMANA, no se arregla): PENETRADO sube

PENETRADO (ticks/ep) de la proporcional: natural 32 · **cebo2f 433.6** · manager 71.5
(Reactive 4-0: 24.6 / 5.8 / 19.7). Con 3-1/2-2 la línea del frente queda más corta y el clúster
primario la penetra más — la sev cae IGUALMENTE (el guardia mata el canal trasero y la rama
PENETRADO contiene), pero el contador sube fuerte y queda aquí REPORTADO tal como se
pre-registró. Es además el hueco natural que un manager D2 APRENDIDO podría gestionar mejor que
la regla fija (cuándo volver a 4-0).

## Para la Fase-2 (si firmas el GO)

- Borrador PREREGISTRO_D2 en `/data/hrl_d2/PREREGISTRO_D2_BORRADOR.md` (receta espejo del
  manager lobo; Discrete(3) {4-0, 3-1, 2-2}; obs ~40; train vs mezcla natural + manager lobo
  congelado; gates espejo con no-inferioridad vs PROPORCIONAL δ=0.15 — un listón DURO: 0.61).
- **ETA Fase-2 ≈ 1 día**: env del manager dron + tests de verja + smoke + retrain (~2-6 h según
  fps del semi-MDP) + evals + STOP.
- Commit D2a hecho (guardia revalidado bajo sonido; cf48b90); v3.7.1 oficial (inocuidad 0.000).

Artefactos: `/data/hrl_d2/e04_<defensa>__<atacante>.json` (12 celdas, episodios completos) ·
`e04.py` · este informe. NADA de Fase-2 arranca sin tu firma.
