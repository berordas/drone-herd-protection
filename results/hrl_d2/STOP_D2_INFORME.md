# STOP-D2 — RUN-D2 (manager del bando DRON): ÉXITO PARCIAL según el pre-registro — Estructura
# EMERGE (reparte SIEMPRE ante un 2º frente, con 2-2) y aplasta a la Reactive 4-0 en las 3 celdas,
# iguala a la PROPORCIONAL contra el manager lobo entrenado y en mezcla natural, pero FALLA la
# no-inferioridad contra el cebo scriptado 2f (+0.18 [+0.01, +0.37]). Dos flags pre-registrados a
# tu decisión (STALLs, PENETRADO). Tiempo del ciclo completo: env+tests+smoke ≈ 6 h · retrain 2 h 58 ·
# evals+visionado ≈ 1,5 h.

**Firmas en el orden de siempre**: 1º aserciones (PASAN: sin NaN; FrozenWolfManager ≡ ManagerEnv bit a
bit; replays del visionado deterministas) · **2º VISIONADO** (`visionado/INDEX.md` — la pregunta única:
¿se ve el REPARTO — la barrera aguanta y un guardia cubre el otro frente — y el manager decidiendo
CUÁNDO?) · 3º este análisis.

## 0. El run

122.880 macro-pasos, 2 h 58 (fps 11.5), sin NaN. PREREGISTRO_D2 congelado antes del env; gate de 40k
PASA (cambios/ep 0.6 ≤ 10; sin fallback). Atacantes de train 50/50 {natural, manager lobo M1''''
congelado — reproducido BIT A BIT}. Curva de ligera: 0.17 (10k) → 0.23 → 0.20 (120k); entre 60-70k la
política exploró "guardias siempre" (STALLs 125/40 eps) y volvió a la disciplina (STALLs 2-7 al final).

## 1. TABLA (100 semillas emparejadas por celda; `TABLA_D2.md`)

| defensa \ atacante | natural | cebo 2f | manager lobo M1'''' |
|---|---|---|---|
| Reactive-est (4-0) | 0.74 | 2.61 | 1.76 |
| **PROPORCIONAL (listón)** | **0.25** | **0.85** | **0.61** |
| **manager dron (D2)** | **0.21** | **1.03** | **0.67** |

Δ(D2 − Reactive): **−0.53 [−0.85, −0.25] · −1.58 [−2.03, −1.14] · −1.09 [−1.35, −0.85]** (IC excluye 0
en las tres). Δ(D2 − proporcional): **−0.04 [−0.13, +0.05] · +0.18 [+0.01, +0.37] · +0.06 [−0.04, +0.17]**.
KNC = 0.0 (canal trasero muerto, como la proporcional) · guardia gana la carrera 0.885 / 0.868 / 0.84 ·
latencia 9.6 / 9.6 / 12.1 ticks · reasignaciones/ep 2.4 / 1.2 / 0.7 (proporcional: 1.95 / 22.3 / 9.8 —
**sin parpadeo**) · jugada completa del atacante 0.22 / 1.00 / 0.67 (igual que contra las demás).

## 2. Compuertas (PREREGISTRO_D2)

- **Estructura — PASA**: P(4-0 | 1 clúster) = 0.756 · **P(guardia | 2º clúster) = 1.000** (ligera final,
  determinista) — y la partición elegida ante el 2º frente es **2-2 (1.000), no 3-1**: el manager prefiere
  dos guardias y una línea de dos; reasignaciones muy por debajo de la proporcional (no parpadea).
- **Competencia — PARCIAL**: ≥ Reactive con IC excluyendo 0 en las 3 celdas ✔; no-inferior a la
  proporcional (δ=0.15, estimador puntual): natural ✔ (−0.04) · manager lobo ✔ (+0.06; IC hasta +0.17) ·
  **cebo-2f ✗ (+0.18, IC excluye 0)**. Sin estrella. ⇒ **criterio de éxito (Estructura + no-inferioridad
  en las celdas manager-lobo Y cebo-2f) NO se cumple por la celda del cebo scriptado.**
- **Asignación estable — PARCIAL**: cambios-tras-interrupción/ep 0.3 (≤5 ✔) · coste pagado 0.014/ep ·
  **STALL ≠ 0: 189 disparos en 300 episodios — LISTADOS (§3)**.
- **Auditoría — flag**: 0 CRITICAL ✔ · KNC 0.0 ✔ · **PENETRADO por encima de la proporcional en las 3
  celdas (§3)**.

## 3. Los dos flags pre-registrados (DECISIÓN HUMANA PENDIENTE; no se arregla nada)

| celda | eps con STALL | STALLs | en 2f | con sev 0 | guardias antes del 2º clúster | PENETRADO D2 / prop | PENETRADO 2f D2 / prop |
|---|---|---|---|---|---|---|---|
| natural | 32/100 | 153 | 5 | 28 | 0.05 | 41.7 / 32.1 | 66.9 / 21.0 |
| cebo 2f | 17/100 | 20 | 17 | 13 | 0.17 | 529 / 434 | 529 / 434 |
| manager lobo | 11/200 | 16 | 6 | 5 | 0.02 | 146.5 / 71.5 | **36.1 / 49.1** |

- **STALLs**: el grueso (153) está en la columna NATURAL y en episodios de sev 0 (28/32): episodios
  tranquilos (solo-corzos / lobos lejanos) en los que el manager mantiene guardias sin 2º clúster y
  acepta el coste — guardias OCIOSOS, inofensivos en sev pero contra la letra del gate. En las celdas
  con atacante real son pocos (17 y 11 episodios) y la mayoría sin coste en muertes.
- **PENETRADO**: sube en las 3 celdas porque la partición preferida es 2-2 (línea de DOS: se penetra
  más) — pero contra el manager lobo entrenado, en el subconjunto de 2 frentes, el D2 PENETRA MENOS que
  la proporcional (36 vs 49) con sev 2f 1.10 vs 0.98. Tal como se pre-registró: reportado, no arreglado.

## 4. Predicciones pre-registradas

1. "≈ proporcional, estrella improbable" — **CUMPLIDA** (sin estrella; ≈ en 2 celdas, peor en cebo-2f).
2. "4-0 con 1 clúster y guardias con 2º clúster emergen; la dimensión libre es CUÁNDO volver a 4-0" —
   **CUMPLIDA** (con el matiz 2-2 ≠ 3-1; la vuelta a 4-0 es justo donde se concentran los STALLs).
3. "PENETRADO del manager ≤ proporcional" — **FALLA** (sube en las 3 celdas; baja solo en el 2f del
   manager lobo).

## 5. Lectura (para tu firma)

El manager dron aprendido **iguala a la regla fija donde el atacante es adaptativo** (manager lobo:
0.67 vs 0.61) y en mezcla natural (0.21 vs 0.25), y **aplasta a la clásica 4-0** (−1.1 a −1.6 contra
el cebo), pero **no mejora a la proporcional contra el cebo scriptado 2f** (+0.18): contra un
atacante rígido, la regla de 30 líneas es mejor que 120k pasos de PPO. El valor añadido del
aprendizaje aparece como (a) menos parpadeo (reasignaciones 1.2 vs 22) y (b) la elección 2-2 que
la regla no contempla (y que explica el PENETRADO alto). Opciones: (A) aceptar D2 como "no-inferior
en 2 de 3 celdas" y cerrar con este informe; (B) una réplica (seed 1) para la barra de error de
+0.18; (C) ampliar el listón de la proporcional a clip(·,0,2) con 2-2 y re-medir. NADA arranca sin
tu firma. KILL-DATE vigente.

Artefactos: `TABLA_D2.md` · `flags_d2.json` · `e04_dronemgr__*.json` · `PREREGISTRO_D2.md` (gate 40k
anotado) · `/data/hrl_d2/D2/` (model.zip, ligera, ckpts) · `visionado/` (GIFs + timelines + INDEX).

---
## §FIRMA DEL DUEÑO (2026-08-22T19:12Z) — STOP-D2 FIRMADO: éxito PARCIAL según pre-registro; opción B con KILL-DATE

Registro explícito (dueño + diseñador):

- **Estructura PASA**: P(guardia | 2º clúster) = 1.000 — el invariante espejo (del P(Δ90|S)=1.000
  del bando lobo) se reproduce en el bando dron.
- **Hallazgo NO anticipado**: el manager **NUNCA usa 3-1** (P(3-1 | 2º clúster) = 0.000): reparte a
  **2-2**, y contra el manager lobo en dos frentes **penetra MENOS que la proporcional (36 vs 49)** —
  una preferencia de despliegue que **no está contenida en ninguna regla nuestra** (la proporcional
  hace clip(n_sec, 0, 2) por tamaño del 2º clúster; el manager elige dos guardias aunque el 2º clúster
  sea de uno).
- **Predicción 3 FALLIDA**: PENETRADO sube en la línea de dos (42/529/146 vs 32/434/72). Lectura:
  **trade-off cobertura/reparto** — dos guardias ganan la carrera al 2º frente a costa de una barrera
  de dos que se penetra más. Se **GRAFICA** (`penetrado_tradeoff.png`), **no se arregla**.
- **STALLs (189/300 eps)** = **seguro aprendido contra la distribución de train** (guardias ociosos en
  episodios tranquilos, aceptando el coste 0.05 por no volver a 4-0): se reporta tal cual, sin tocar
  el tripwire ni el coste.
- **Decisión: opción B** — RÉPLICA D2 (seed 1; receta, mundo v3.7.1 y las mismas 3 celdas × 100)
  con **único objetivo = barra de error**, en particular del **+0.18** contra el cebo scriptado. Sin
  visionado nuevo salvo anomalía o CRITICAL. Pre-registro de la réplica congelado en
  `PREREGISTRO_D2.md` ANTES del lanzamiento.
- **KILL-DATE ABSOLUTO**: al terminar la réplica (o al vencer el timebox del día 5, lo que llegue
  antes) ⇒ **CIERRE TOTAL del pipeline**: commit final, entrada de cierre del proyecto en DISEÑO.md,
  **tabla maestra** de TODOS los runs y celdas con sus artefactos, contenedor parado. Desde ahí,
  **ningún run nuevo por ningún hallazgo**: todo lo que aparezca se anota como future work.

### Future work (anotado, NO ejecutado)

- **proporcional-2-2** = la regla destilada de D2 (ante un 2º clúster, siempre dos guardias y línea
  de dos, sin parpadeo): **candidata a future work; no se mide para no contaminar el listón
  pre-registrado** (la proporcional clip(·,0,2) sigue siendo el único listón de D2).
- Trade-off cobertura/reparto (PENETRADO vs sev por celda): graficado, no optimizado.

**Fe de erratas (inventario del cierre, 2026-08-22T19:26Z)**: donde este informe y la firma dicen "STALL
= 189 disparos en 300 episodios", el denominador es **400 episodios** (100 natural + 100 cebo-2f + 200 de
la columna manager lobo); los 189 STALLs y su reparto por celda (153/20/16; episodios 32/17/11) son correctos.

---
## § RÉPLICA D2 (seed 1) — adjudicación contra el pre-registro de la réplica (2026-08-22T22:36Z; cierre)

Run D2_r1: 122.880 macro-pasos, **3 h 20** (fps 10.3), sin NaN; gate 40k PASA (cambios/ep 0.50). Evals:
`e04_dronemgr_r1__*.json`, tabla `TABLA_D2_R1.md`, gráfica `penetrado_tradeoff_dronemgr_r1.png`.

| | natural | cebo 2f | manager lobo |
|---|---|---|---|
| RUN-D2 (seed 0) | 0.21 | 1.03 | 0.67 |
| **réplica (seed 1)** | **0.21** | **1.06** | **0.76** |
| Δ réplica − Reactive | −0.53 [−0.86, −0.22] | −1.55 [−1.98, −1.13] | −1.01 [−1.26, −0.77] |
| Δ réplica − proporcional (δ=0.15) | −0.04 [−0.12, +0.03] ✔ | **+0.21 [+0.03, +0.40] ✗** | +0.14 [+0.02, +0.28] ✔ (puntual; marginal) |
| **Δ CONJUNTO (200 pares, 2 aprendices; SOLO barra de error)** | **−0.04 [−0.10, +0.01]** | **+0.20 [+0.07, +0.33]** | **+0.10 [+0.02, +0.19]** |
| gana_guardia · latencia · reasignaciones | 0.815 · 35.5 · 2.7 | 0.857 · 18.3 · 2.3 | 0.776 · 104.1 · 1.0 |
| PENETRADO réplica / prop (2f) | 92 / 32 (288 / 21) | 514 / 434 | 108 / 72 (**185 / 49**) |
| STALLs (eps; con sev 0) | 112 (33; 28) | 22 (21; 16) | 13 (13; 6) |

Predicciones: **1 CUMPLIDA** (P(guardia|2cl) = 0.943 ≥ 0.90; P(3-1|2cl) = 0.019 ≤ 0.10; P(4-0|1cl) = 0.897) ·
**2 CUMPLIDA** (Δ vs proporcional en cebo-2f positivo, +0.21, IC solapa con [+0.01, +0.37]: la celda NO se
vuelve no-inferior) · **3 CUMPLIDA** (IC vs Reactive excluye 0 en las 3 celdas) · **4 CUMPLIDA** (PENETRADO
≥ proporcional en las 3 celdas). Sin anomalía (NaN/CRITICAL/P(guardia|2cl)<0.5/sev>2×) ⇒ sin visionado.

Lectura de cierre (barra de error, nada nuevo se adjudica): (a) el **fallo del cebo scriptado 2f se
reproduce** — +0.18 y +0.21; conjunto +0.20 [+0.07, +0.33]: la regla fija es mejor que el aprendiz contra el
atacante rígido, con IC que excluye 0; (b) **natural se reproduce** (−0.04 en ambos); (c) contra el
**manager lobo** la réplica queda en +0.14 (puntual < δ, IC hasta +0.28): no-inferioridad **marginal**, no
la holgura de RUN-D2 (+0.06); (d) la **estructura** se reproduce (2/2 runs: guardias ante el 2º clúster
≥ 0.94, siempre 2-2, 3-1 ≈ 0); (e) el hallazgo "penetra MENOS que la proporcional en el 2f contra el manager
lobo (36 vs 49)" **NO se reproduce** (réplica 185 vs 49): era una propiedad del seed 0, se registra como tal;
(f) la réplica **tarda más en apostar guardias** (latencia 35/18/104 ticks vs 10/10/12) y gana menos carreras
(0.78-0.86 vs 0.84-0.89) — el CUÁNDO es la dimensión que varía por semilla, como se pre-registró en D2;
(g) STALLs 147 (vs 189), mismo patrón (el grueso en natural, con sev 0). Future work, no ejecutado:
proporcional-2-2; término de coste por guardia ocioso; latencia del reparto como métrica de Estructura.
