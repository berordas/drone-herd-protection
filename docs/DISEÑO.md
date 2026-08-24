# Proyecto AI Lab — Drones que protegen ganado de lobos (simulación)

> **Qué es este documento.** Es la memoria viva del proyecto: recoge todo el diseño, las
> decisiones tomadas, las herramientas, el plan, las referencias y —muy importante— las
> "banderas levantadas" (cosas aparcadas para más adelante). Sirve como borrador de la
> memoria final (70% de la nota) y como contexto para retomar el trabajo en un chat nuevo.
>
> **Última actualización: 2026-08-23 — PROYECTO CERRADO (KILL-DATE del dueño): ver §0 justo debajo de este bloque.** · ***ETAPA 1 CERRADA — RESULTADO PRINCIPAL: RUN-M1'''' (manager
> jerárquico de lobos) es el PRIMER run del proyecto que CUMPLE su criterio de éxito PRE-REGISTRADO***
> (PREREGISTRO_v3 congelado antes del retrain; firma 2 del dueño 2026-08-21). **Números**: manager final
> **1.76/1.75/1.76** vs Reactive-estática/run02/run09 (100 semillas emparejadas) · **supera al ORÁCULO SANO
> (1.66) en +0.10 [+0.03, +0.19]** (estrella: IC excluye 0; no-inferioridad δ=0.15 trivial) · Δ vs B_spawn
> +0.81 · gaps de transferencia ≈ oráculo · **ESTRUCTURA COMPLETA por primera vez: P(keep|G,n≥3)=0.931,
> P(Δ90|S)=1.000, P(Δ180)=0.000** — y respaldada por el paisaje MEDIDO (celdas S limpias: MASA 0.30 / Δ90
> 1.71 / Δ180 1.42) · jugada completa 1.00 · ABORTs/ep 45→0.28 · canal B=0 · 0 CRITICAL. El camino fue el
> resultado: (i) el +0.42 de M1 era exploit de interfaz (re-fijación de presa por churn → Commit K la
> legaliza REGULADA para todos); (ii) el +1.26 de M1'' era en parte MOLINILLO DE RUMBO sobre celdas
> CONTAMINADAS (VERIF-0: el gate duro ±25° interbloqueaba 9/20 episodios del oráculo en S — Estructura
> re-adjudicada como NO ADJUDICABLE); (iii) el paquete M1'''' cerró las DOS raíces con la MISMA plantilla
> mejor-esfuerzo (S1 alineación: tolerancia/sin-progreso/techo · S3 meseta de d_prey — ambos umbrales
> geométricos ABSOLUTOS que la defensa podía negar), quitó el falso terminal (S2: ABORT solo pre-show,
> el metrónomo post-show de 50 ticks muere), añadió CENSURA estándar (staged/show/suelta/strike + tasa de
> jugada completa: sev 0 sin jugar ≠ sev 0 jugando y fallando), cerró la decisión por INCENTIVOS (Q: coste
> de deliberación 0.05 — el manager SOSTIENE la opción tras ABORTs en vez de molinillear, coste pagado ≈0),
> watchdog degradado a tripwire (Q-bis), **física v3.7-relevo-centinela** (R: el bajo se CLAVA, el fresco
> vuela DIRECTO al puesto y HEREDA la ranura — destapando el bug silencioso v3.0-v3.6 de la ROTACIÓN de
> ranuras por hand-off, bandera 14) y señuelo v2 directo (Encargo 2). **Tres arcos para la memoria**: la
> TRILOGÍA del seed 21 (sev 7 con exploit de presa → 6 con molinillo → **0 limpio**: sin churn que explotar,
> el episodio malo es simplemente malo); el ARCO del seed 77 (de LIMITACIÓN de la clásica —entradas no
> detectadas, despertar tardío— a DEMOSTRACIÓN: bajo v3.7 el despertar tardío es **0 episodios** en 200 y el
> propio seed 77 es ahora el GIF de la jugada entera en G, keep sostenido, sev 7 = oráculo); y los **9
> STALLs EXONERADOS** (los 9 episodios con tripwire del manager son EXACTAMENTE los 9 del oráculo — solape
> 100%, todos S: la alineación lenta del brazo Δ90-en-S es propiedad del BRAZO, no de la política;
> pre-registrado como decisión humana, adjudicado por el dueño en la firma 2). Artefactos:
> `/data/hrl_m1/m1pppp/` (STOP_M1PPPP_INFORME.md · TABLA · PREREGISTRO_v3 · visionado 6 GIFs + relevo ·
> celdas/sanity/metro v3.7 · canal). **Cola firmada**: RUN-M2 (K=1000 fijo — ablación de la
> terminación-por-evento; predicción pre-registrada: colapso o degradación fuerte de la emergencia) →
> 1 RÉPLICA de M1'''' (semilla nueva, barra de error del resultado principal). Nada más sin firma.
> **(2026-08-22, firmas 3) CLAIM PRINCIPAL DEL TFG re-formulado tras RUN-M2 y la RÉPLICA:
> "estructura-en-S (P(Δ90|S) = 1.000 en 3/3 runs: M1'''', M2, réplica) + no-inferioridad al oráculo
> sano (δ=0.15), REPRODUCIDO en réplica (seed 1, mundo v3.7 pineado: sev 1.69 [1.38, 2.01], Δ vs
> M1'''' −0.075 [−0.20, +0.045], Δ vs oráculo +0.03 [−0.12, +0.18])."** La estrella (+0.10) y keep|G
> (0.931) son PROPIEDADES DEL RUN PRINCIPAL, reportadas junto a la réplica (Δ180|G 0.931). Celdas G
> (keep vs Δ180 vs Δ90, 100 pares): Δ(Δ180−keep) = +0.08 [−0.22, +0.38] ⇒ **paisaje G PLANO — la
> política converge donde el paisaje decide (S) y varía por semilla donde no distingue (G)**.
> **RUN-M2 (K=1000 fijo, ablación firmada "ingrediente del MARGEN, no del MECANISMO")**: la
> predicción fuerte (colapso) FALLÓ — la jugada cabe en un tramo de 1000 (S1/S3 sacan el show a
> ~300) y el mecanismo sobrevive (jugada completa 1.00, Δ90|S 1.000); lo que la terminación-por-
> evento compra es el margen: Δ(M2−M1'''') = −0.145 [−0.265, −0.04], estrella perdida (−0.04 ≈ 0),
> keep|G perdido; cómputo ×3.3 más barato (fps 19.4 vs 6.0). **D2 (manager del bando DRON) en
> marcha**: v3.7.1-plazas-estacion oficial (inocuidad Δsev = 0.000), E0.4 con la PROPORCIONAL como
> listón duro (0.85 vs cebo-2f, **0.61 contra el manager lobo entrenado**, KNC = 0.0, guardia gana la
> carrera 78-82%; PENETRADO sube — flag reportado sin arreglar), GO firmado, PREREGISTRO_D2 congelado.
> **RUN-D2 COMPLETADO (2026-08-22; 122.880 macro-pasos, 2 h 58, sin NaN; manager lobo M1'''' congelado
> reproducido BIT A BIT como atacante de train)** — STOP-D2 adjudicado contra el preregistro: **Competencia
> vs Reactive 4-0 APLASTANTE en las 3 celdas** (natural 0.21 vs 0.74 · cebo-2f 1.03 vs 2.61 · manager lobo
> 0.67 vs 1.76; Δ con IC excluyendo 0: −0.53 / −1.58 / −1.09) · **vs la PROPORCIONAL (δ=0.15): no-inferior
> en natural (−0.04 [−0.13, +0.05]) y contra el manager lobo entrenado (+0.06 [−0.04, +0.17]), pero FALLA en
> cebo-2f (+0.18 [+0.01, +0.37])** ⇒ criterio de éxito PARCIAL (2 de 3 celdas) · **Estructura emerge**:
> P(4-0 | 1 clúster) 0.756, P(guardia | 2º clúster) 1.000 — y elige **2-2, no 3-1** · KNC 0.0 (canal trasero
> muerto, como la proporcional) · guardia gana la carrera 84-89% · reasignaciones MENORES que la proporcional
> (1.2 vs 22 en cebo-2f: sin parpadeo) · dos FLAGS pre-registrados a decisión humana: STALLs 189/400 eps
> (guardias ociosos aceptando el coste) y PENETRADO por encima de la proporcional en las 3 celdas
> (42/529/146 vs 32/434/72: la línea de 2 se penetra más). Lectura: el manager aprendido iguala a la regla
> fija donde el atacante es adaptativo (manager lobo) y la supera a la Reactive por −1.1, pero no mejora
> a la proporcional contra el cebo scriptado. Artefactos: /data/hrl_d2/ (STOP_D2_INFORME.md, TABLA_D2.md,
> PREREGISTRO_D2.md, visionado/).

**(2026-08-24) Reorganización de carpetas del repo público, sin cambios de conducta**: el núcleo del simulador pasa a `sim/`, las entradas a `scripts/`, los 8 checks y sus fixtures (`baseline_v2*`) a `tests/` (`bash tests/run_all.sh` = la verja), los documentos a `docs/`; `pyproject.toml` + `PYTHONPATH=/workspace:/workspace/sim` en el compose + un shim de 2 líneas en scripts/tests mantienen los imports de nivel superior (`from world import World`). Las rutas citadas en las entradas anteriores de este diario son las de la época (raíz del repo).

## 0. CIERRE TOTAL DEL PROYECTO (2026-08-23) — KILL-DATE absoluto firmado por el dueño en el STOP-D2

**Qué se cierra.** Con la réplica D2 terminada se ejecuta el CIERRE TOTAL firmado: último commit, esta entrada, la
**tabla maestra de todos los runs y celdas** (`/data/TABLA_MAESTRA.md`, copia condensada abajo) y el contenedor
parado. **Desde aquí no arranca ningún run nuevo por ningún hallazgo: todo lo que aparezca es future work.**

### 0.1 Réplica D2 (seed 1, receta y mundo v3.7.1 idénticos, pre-registro congelado antes; 3 h 20, fps 10.3, sin NaN)

| | natural | cebo 2f | manager lobo M1'''' |
|---|---|---|---|
| RUN-D2 (seed 0) | 0.21 | 1.03 | 0.67 |
| **réplica (seed 1)** | **0.21** | **1.06** | **0.76** |
| Δ réplica − Reactive 4-0 | −0.53 [−0.86, −0.22] | −1.55 [−1.98, −1.13] | −1.01 [−1.26, −0.77] |
| Δ réplica − proporcional (δ=0.15) | −0.04 [−0.12, +0.03] ✔ | **+0.21 [+0.03, +0.40] ✗** | +0.14 [+0.02, +0.28] ✔ (marginal) |
| **Δ conjunto, 2 aprendices (200 pares; SOLO barra de error)** | **−0.04 [−0.10, +0.01]** | **+0.20 [+0.07, +0.33]** | **+0.10 [+0.02, +0.19]** |

Estructura reproducida: P(guardia | 2º clúster) 0.943, 2-2 0.925, 3-1 0.019, P(4-0 | 1 clúster) 0.897. Las 4 predicciones
del pre-registro de la réplica CUMPLIDAS; sin anomalía ⇒ sin visionado. Lo que **no** se reproduce: "penetra MENOS que la
proporcional en el 2f contra el manager lobo" (36 vs 49 en RUN-D2; **185 vs 49** en la réplica) — propiedad del seed 0. Lo
que varía por semilla: el CUÁNDO (latencia de reparto 35/18/104 ticks vs 10/10/12; gana_guardia 0.78-0.86 vs 0.84-0.89);
STALLs 147 (vs 189), mismo patrón (guardias ociosos en episodios tranquilos de sev 0).

### 0.2 Claims finales del TFG (tal como quedan, con su réplica al lado)

- **Bando LOBO (Etapa 1)**: el manager jerárquico aprende **estructura-en-S** (P(Δ90 | S) = 1.000 en 3/3 runs: M1'''',
  M2, réplica) y es **no-inferior al oráculo sano** (δ=0.15), **reproducido** en réplica (1.69 [1.38, 2.01]; Δ vs M1''''
  −0.075 [−0.20, +0.045]). La estrella (+0.10 [+0.03, +0.19]) y keep|G (0.931) son propiedades del run principal
  (paisaje G plano: Δ(Δ180−keep) +0.08 [−0.22, +0.38]). La terminación-por-evento es ingrediente del MARGEN, no del
  MECANISMO (M2: −0.145 [−0.265, −0.04], mecanismo intacto).
- **Bando DRON (D2)**: el manager aprende **estructura** (guardias ante el 2º clúster ≥ 0.94 y siempre **2-2** — una
  preferencia que ninguna regla nuestra contenía) en **2/2 runs**; **aplasta a la Reactive 4-0 en 3/3 celdas × 2 runs**
  (IC excluye 0); **no-inferior a la proporcional** en natural (2/2) y contra el manager lobo entrenado (2/2 en puntual,
  marginal en la réplica); **FALLA contra el cebo scriptado 2f en 2/2** (+0.18, +0.21; conjunto +0.20 [+0.07, +0.33]):
  contra un atacante rígido la regla de 30 líneas sigue siendo mejor. Coste: PENETRADO sube con la línea de dos
  (trade-off cobertura/reparto, graficado en `/data/hrl_d2/penetrado_tradeoff*.png`, no arreglado).
- **Camino como resultado**: el cebo (2 frentes) NO emerge por PPO puro en 5 runs de lobos (run05-run08; la dieta lo
  EROSIONA: KNC 26.6 → 13 %), y el MARL de drones bate la barrera pero NO reparte (run01/02/09: reparto 5-6 %). La
  jerarquía (capa de opciones + manager por eventos) es lo que hace emerger ambas conductas — y las medidas de
  higiene (pre-registro congelado, gates, censura, coste de deliberación, verificación del instrumento) son lo que
  permitió distinguir aprendizaje de exploit (M1 +0.42 = churn de presa; M1'' +1.26 = molinillo sobre celdas
  contaminadas).

### 0.3 Tabla maestra condensada (completa con artefactos: `/data/TABLA_MAESTRA.md`)

| bloque | run / celda | física | resultado clave | veredicto |
|---|---|---|---|---|
| MARL drones | run01 (07-18) | v2.6 | 2.35/0/2.34 vs 2.74/0/2.82 | histórico (v2.7) |
| | **run02_v34** (08-03) | v3.4 | **2.40/0/2.27** vs 2.68/0/2.77; gotera −32 %; reparto NO emerge | bate la barrera v3.4 |
| | run09_v35 (08-19) | v3.5 | defensa de transferencia: E0.4 0.69 / 2.53 / 1.78 | listón en E0.4 |
| Lobos PPO | run01-04 (07-14/16) | v2.4.1 | rala 0 → shaping 0.57/0.60 → cuna 0.65/0.72 → residual ≈ suelo (2.82/2.81) | cierre "lobos aprendidos" |
| | run05-07 (07-17/22) | v2.6-2.8 | cebo 0.0 % en todos los ckpts; currículo agotado | cebo NO emerge ×3 |
| | **run08_dieta50** (08-04) | v3.4 | KNC 26.6 → 13.0 %, sev-2f 3.50 → 2.65 | ESTRUCTURAL ⇒ jerárquico |
| Etapa 0 | E0.A / E0.1 / E0.2 (08-17/18) | v3.4 | impuesto 0; Δ(keep−MASA | G) **+0.43 [+0.25, +0.62]**; p75 2.316/4.126 | G0, G1 PASAN |
| | forense s398 → **v3.5 sonido** | v3.5 | Reactive 2.68 → **0.88/0/0.76**; E0.1' **+0.85 [+0.60, +1.09]**, Δ90|S +0.32 | G1 PASA (4/4 predicciones) |
| Etapa 1 | re-nivelados v3.5 / v3.6 / **v3.7** | — | B_oracle 0.885 → 1.00 → **1.66 [1.36, 1.97]**; celdas S limpias MASA 0.30 / Δ90 1.71 / Δ180 1.42 | instrumento verificado |
| | M1 (08-19) | v3.5 | 1.31; +0.42 vs oráculo; P(keep)=1.0 | exploit de interfaz ⇒ Commit K |
| | M1'' (08-20) | v3.6 | 2.26; +1.26 vs oráculo | NO ADJUDICABLE (VERIF-0) |
| | **M1'''' (08-21)** | v3.7 | **1.76/1.75/1.76; +0.10 [+0.03, +0.19]; keep|G 0.931 · Δ90|S 1.000** | **CUMPLE (resultado principal)** |
| | M2 K=1000 (08-22) | v3.7 | 1.62; −0.145 [−0.265, −0.04] | margen, no mecanismo |
| | réplica M1pppp_r1 (08-22) | v3.7 @4bf5024 | 1.69; −0.075 [−0.20, +0.045]; Δ90|S 1.0 | reproducido |
| | celdas G (08-22) | v3.7 | keep 2.76 / Δ180 2.84 / Δ90 2.51 | paisaje G plano |
| D2 | E0.4 listones (08-22) | v3.7.1 | proporcional **0.25 / 0.85 / 0.61**; Reactive 0.74 / 2.61 / 1.76 | GO |
| | **RUN-D2 (08-22)** | v3.7.1 | **0.21 / 1.03 / 0.67**; vs prop −0.04 / **+0.18** / +0.06; guardia|2cl 1.0 (2-2) | éxito PARCIAL (firmado) |
| | **réplica D2_r1 (08-23)** | v3.7.1 | **0.21 / 1.06 / 0.76**; vs prop −0.04 / **+0.21** / +0.14; guardia|2cl 0.943 | barra de error; fallo 2f reproducido |

### 0.4 Future work (anotado, NO ejecutado)

proporcional-2-2 (la regla destilada de D2; no se mide para no contaminar el listón) · término de coste por guardia
ocioso (STALLs) · latencia del reparto como métrica de Estructura · trade-off cobertura/reparto (PENETRADO) ·
apilamiento de lobos en PENETRADO (forense s398, pendiente desde Etapa 0) · E0.3/E0.5 nunca corridos · run09 nunca
medido contra M1 · bandera 14 cerrada pero la regla "ningún comportamiento se apoya en movimiento no ordenado" queda
como principio de diseño para cualquier versión futura.

### 0.5 Fe de erratas del cierre

STALLs de RUN-D2: 189 en **400** episodios (no 300) · varios hechos del 2026-08-22 estaban fechados 08-23 en esta
cabecera y en la memoria (corregidos) · redondeos (Reactive vs manager lobo 1.76/1.77 = 1.765; run09 1.77/1.78 =
1.775) · `PIN_REPLICA.txt` copiado a `/data/hrl_m1/M1pppp_r1/`.

### 0.6 Estado final

Código = `313cb51` (último commit con conducta; D2b) + commits de docs; tags `v3.4-baseline` … `v3.7.1-plazas-estacion`;
worktree `wt_v37_replica` @ `4bf5024` conservado (pin de la réplica M1''''); artefactos en `/data` (`hrl_e0/`,
`hrl_m1/`, `hrl_d2/`, `drones/`, `wolves/`, `metro_v35/`, `gifs/`, `TABLA_MAESTRA.md`); verja 8/8 verde en el commit
de cierre; contenedor `<uid>-wolves` parado. **No hay siguiente paso ejecutable** (§11 queda como histórico).


>
> *(2026-08-18)* ***v3.5 "REGLA DEL SONIDO" (tag `v3.5-sonido`) — ENMIENDA DE FÍSICA
> tras el FORENSE de la Etapa 0 del jerárquico + CORRECCIÓN de la entrada de "agujeros deliberados".** El visionado
> humano de STOP-1/2 (E0.1, GIF 2 = seed 398 mixto, MASA vs Reactive) mostró lobos cruzando la línea rígida por el
> PUNTO MEDIO entre dos drones y drones apilados; el forense (replay determinista, `/data/hrl_e0/forense/FORENSE.md`)
> confirmó la causa raíz por tick: **t=672, cruce a frac 0.50 del corredor de 20 m, dron más cercano a 9.96 m con
> approach −0.57 < SCARE_APPROACH_MIN=1 ⇒ expulsión v2.4 INACTIVA; empuje de pared 0.01 ≈ 0 (cancelación simétrica)**.
> **CORRECCIÓN: el corredor central NUNCA fue un agujero deliberado — era este defecto de la regla del susto por
> movimiento (v2.4-v3.4). Flancos de la línea estrecha, espalda del anillo de 50 y 2º frente libre SIGUEN siendo
> deliberados (no se tocan).** Especificación del dueño (regla del sonido, `world._apply_deterrence`): un lobo queda
> EXPULSADO siempre que esté a ≤ DETER_RADIUS=20 de ALGÚN dron ACTIVE — SIN requisito de velocidad de aproximación;
> huida radial del ACTIVE más cercano (sin acumular), perfil clip(4·(1−d/20), 0.8, 4) intacto, la huida sustituye la
> intención y excluye matar ese tick; "detectado" se cumple solo (≤20 ⊂ ≤100); corzos sin cambio; pared blanda (≤10)
> INTACTA en código pero en SOMBRA; `SCARE_APPROACH_MIN` deprecated (se conserva por imports); 🔊 = dron con lobo a ≤20.
> Tests nuevos (nacen de los ojos del dueño, en la verja): `test_corredor_cerrado` (lobo al punto medio exacto de dos
> ACTIVE quietos a 20 m → expulsado, 0 cruces del segmento, dist mín a un dron 19.4 = el borde del sonido),
> `test_sonido_estatico` (dron quieto, lobo entra a <20 → huye; el dron no se mueve 0.00 m). RE-GOLD CONSCIENTE de los
> tests que codificaban "quieto = poste" (cada cambio en el mensaje del commit): test_disuasion (a) el dron QUIETO a
> 12 m ahora EXPULSA (inversión exacta de la cota 'poste' <2 m → >2 m + scared) y (b) el poste que suena mantiene al
> lobo fuera de la presa; test_susto (A) quieto cubriendo = expulsión (no pared); test_pared_estatica (A) el dron a
> 14 m con los lobos a ≤20 SALVA a la presa (antes no) y (B) mover ≥ quieto en vez de mover > quieto +3 m;
> test_pin_envolvente el dron a 14 m salva. **RE-MEDIDO (metro DGX, 100/tipo): Dummy 3.82/0/3.84 → 1.90/0/2.02
> (los drones CLAVADOS vuelven a disuadir a corta) · Reactive 2.68/0/2.77 → **0.88±1.82/0/0.76±1.70** (success 67/69%, n_safe 5.99/6.09: la línea rígida quieta ya SUENA en todo su frente) · suelo residual drones
> (NonRigidBarrier δ≡0) 0.92/0/0.81 · run02 (política v3.4 EVALUADA en v3.5, sin re-entrenar) 1.09/0/0.78 — su ventaja de v3.4 ('moverse para disuadir', 2.40/0/2.27 vs 2.68/2.77) DESAPARECE: en v3.5 el sonido ya no exige movimiento y el δ aprendido queda por debajo de la Reactive quieta en lobos (+0.21) y ≈ en mixto (+0.02); es HISTÓRICO, no se re-entrena en esta misión · suelo del
> cebo scriptado (2 frentes, 58 eps) 3.50 → 2.60 (KNC 26.6% → 37.7%: el asalto sigue matando sin confirmar, y ahora es la MAYOR fuente de muertes; ancla-cebo 65.5% IDÉNTICO — el spawn y el timing del cebo no cambian; gotera 0/ep) · cruces de corredor Reactive 0.075/ep con 2.4% de las muertes tras un cruce (v3.4: 30-55%) — el corredor está CERRADO en la práctica (los 0.075 residuales = lobos empujados por la propia huida en aglomeraciones).** Hallazgo B (drones apilados) =
> BUG de diseño de `_cover_engaged` (PENETRADO asigna `order[s % n_lobos]` → varios drones al MISMO slot; 246
> ticks-par a <3 m en el GIF 2) — DECISIÓN HUMANA PENDIENTE (arreglo con test dirigido en commit separado, o aceptar).
> Etapa 0 (E0.A/E0.1/E0.2) se RE-CALIBRA en v3.5 (FASE 4) con predicciones pre-registradas; E0.3-E0.5 y la Etapa 1
> siguen CONGELADOS hasta el STOP-2'.
>
> *(2026-08-05: run08 de LOBOS (DIETA 50% DE DOS FRENTES) COMPLETADO — DESENLACE (3),
> ESTRUCTURAL, con agravante: la dieta NO hace asomar el cebo; PPO con recompensa de equipo pura EROSIONA el cebo
> scriptado.** Paso acotado pre-jerárquico (commit `250f278`): el residual de run05/07 (equipo pura +1/muerte,
> shaping OFF, sin pista, δ autoridad plena, dos fases) con UN cambio — `--train-two-front-rate 0.5`: 50% de los
> episodios de ENTRENAMIENTO con 2 subgrupos por muestreo por RECHAZO del spawn real v3.4 (nada sintético; cebo 1 /
> asalto n−1 como los produce el mundo; natural ~29-35%; la EVAL siempre al ~29% real). SUELOS (paso 0): arnés δ≡0
> = 2.68/2.77 con Δ +0.00 EXACTO · ligera 3.20 [1,0,5,4,5,3,3,5,3,3] · REFERENCIA del cebo scriptado v3.4
> (cebo_diag --floor, 58 eps/203 muertes): killer-NO-CONFIRMADO 26.6%, cebo-confirmado 26.6%, no-anclado 79.3%,
> sev-2-frentes 3.50, ancla=sector-cebo 65.5% (¡no nula — v2.8 daba 0.0%: el cebo a mano de v3.4 funciona!). CURSO
> (10M, 8 envs, 5h53, 472 fps): fase 1 CLAVADA en 3.20; fase 2 osciló 2.4–3.6 con picos 3.50/3.60 (1.25M/3.25M) y
> desde ~6.75M EROSIÓN SOSTENIDA — GUARDIA DISPARADA a 8.0M (6 evals consecutivas <2.9: 2.70/2.80/2.50/2.80/2.50/
> 2.50); la parada SIGTERM pactada NO llegó a ejecutarse (fallo de permisos de la sesión en ese momento) y el run
> completó los 10M con las últimas 8 ligeras en 2.0–2.5 — sin consecuencia para el veredicto (el mejor checkpoint
> es muy anterior, 2.5M; el tramo final solo CONFIRMA la erosión). VEREDICTO (100 semillas, eval real): FINAL (10M)
> **2.17/2.25 (Δ −0.51/−0.52 vs scriptado — erosión en el arnés)** · mejor por ligeras (2.5M) **2.71/2.58**
> (Δ +0.03/−0.19 ≈ suelo). CEBO (58 eps de 2 frentes): killer-NO-CONFIRMADO **26.6% (scriptado) → 21.0% (mejor) →
> 13.0% (final)** · sev-2-frentes 3.50 → 3.36 → 2.65 · ancla=cebo 65.5% → 62.1% → 53.4%. **Lectura (séptima del
> cebo, la más limpia): subir la dieta del escenario ×1.7 NO arranca el cebo aprendido — el gradiente greedy de la
> caza se come la desviación coordinada del propio script (cuanto más entrena, menos ceba). El problema es
> ESTRUCTURAL (política plana), no de dieta: el JERÁRQUICO queda justificado con evidencia** (siguiente paso =
> decisión del usuario; la dieta queda disponible como flag para componerla con él). GIFs gemelos (seed 76 lobos
> 1+3: suelo = cebo scriptado pleno, 6 muertas todas no-confirmadas; política = lo conserva degradado, 5/5) en
> /data/gifs/run08_dieta50/; artefactos en /data/wolves/run08_dieta50/ (evals, cebo_diag ×3, ancla ×3, 20
> checkpoints, train.log con pacto y marca de guardia).* ·
> *(2026-08-04: **run02 del MARL de DRONES COMPLETADO (sobre el mundo terminado v3.4;
> infra `573e679`) — EL MARL BATE LA BARRERA v3.4: Reactive 2.68/0/2.77 → FINAL (20M) 2.40±1.78/0/2.27±1.54
> (Δ −0.28/−0.50, ~1.6/3.2 SEM), SIN tocar mundo ni barrera congelada.** Dos cambios de diseño sobre la infra run01
> (decisión del usuario): **(1) residual SIN RIGIDEZ** — `NonRigidBarrier` (rl/, la v3.4 sin el gobernador del más
> rezagado; percepción v2.8/ancla/trinquete/anillo/PENETRADO/patrulla intactos): con el gobernador la δ LUCHA contra
> la base (sacar un dron de su ranura congela la pose entera); autoridad PLENA por dron. SUELO RE-MEDIDO (δ≡0, 100
> semillas): **2.74±1.68/0/2.63±1.67** (Δ vs rígida +0.06/−0.14 = ruido; quitar el gobernador ni ayuda ni estropea a
> la scriptada). **(2) obs con CONTACTOS y CONFIRMADOS etiquetados** (LOCAL 131→162, AGENT 253→284): contactos =
> ahora a ≤r_detect y nunca confirmado (bulto sin clasificar, sin memoria); confirmados = latch v2.8 de equipo de la
> barrera interior (UNA fuente de verdad, tracking) — la barrera solo reacciona a confirmados (baseline tonta); los
> contactos dan al MARL ANTICIPACIÓN (asimetría de información a favor del aprendido, realista pre-YOLO). Verja 7/7
> (test 10 ADAPTADO sin bajar el listón: suelo δ=0 ≡ NonRigidBarrier bit a bit + test (e) dirigido
> contacto→confirmado→memoria) + smoke; commit ANTES del run. RUN: 20M pasos-agente, 12 mundos, cpu
> (CUDA_VISIBLE_DEVICES="" — sin reserva de GPU), 6h03, 920 fps, checkpoints ~250k (el nuevo sistema de reservas
> puede cortar); fase 1 CLAVADA en la ligera re-medida (3.00 EXACTO ×4, detalle idéntico); GUARDIAS invertidas +
> anti-proxy JAMÁS disparadas (0/76 evals >3.2; ep_deter osciló mientras ep_sev bajaba). 100 semillas: FINAL (20M)
> **2.40/0/2.27** (vs suelo −0.34/−0.36; n_safe 4.09/4.14→4.45/4.62) · mejor por ligeras (17,99M) 2.41/0/2.39 —
> ROBUSTO al checkpoint. **DIAGNÓSTICO de comportamiento (58 gemelos de 2 frentes, suelo vs política): el Δ NO es
> repartirse** (ambos frentes atendidos 5.7%→5.3%; severidad del subconjunto 2-frentes PLANA 3.33≡3.33) — **es
> MOVERSE PARA DISUADIR** (vel ACTIVE 3.47→3.82 m/s +10%; sustos/paso 0.642→0.737 +15%) **más un cierre PARCIAL de
> la GOTERA** (cruces de segmento entre drones contiguos, contador v3.4: 3.47→2.36/ep, −32%). Lección de esta
> ablación: con la RIGIDEZ eliminada y los CONTACTOS en la obs (las dos sospechas de run01), el reparto entre
> frentes SIGUE sin emerger → nueva confirmación de que el cuello es la EXPLORACIÓN/estructura de la política (no la
> información ni la autoridad); el cebo v3.4 sigue ganando su duelo al aprendido (agujeros deliberados: flancos,
> espalda, 2º frente y gotera residual siguen ahí para la siguiente iteración). **GIF nº4 de la narrativa** (gemelos
> seed 37 lobos, cebo 1 + asalto 3: suelo 6 muertas → MARL 2) en /data/gifs/run02_v34/; artefactos completos en
> /data/drones/run02_v34/ (evals FINAL/mejor/suelo, comportamiento ×3, 80 checkpoints, train.log con el pacto).
> **Nota del MARL de drones vigente → 2.40/0/2.27**; siguiente paso = decisión del usuario (aceptar como coordinador
> MARL v2 / más presupuesto --resume / atacar el reparto: curiosidad coordinada · jerárquico · co-evolución).* ·
> *(2026-07-24: **v3.4: LA BARRERA COMO LÍNEA RÍGIDA + (v3.3, aceptada por el usuario
> EN GIF) TRINQUETE DEL AVANCE Y ROLES INVERTIDOS DEL CEBO (RE-CONGELADO tag `v3.4-baseline`) — EL MULTI-FRENTE
> POR FIN RINDE: Reactive 1.91/1.96 → 2.68±1.66/2.77±1.71 (+0.77/+0.81); el mundo cambió bastante y la nota a
> batir del MARL cambia con él — los 1.91/1.96 quedan OBSOLETOS.** Tres piezas congeladas juntas (v3.3 quedó sin
> congelar a la espera del juicio en GIF; este tag la incluye): **(1) TRINQUETE del avance (v3.3,
> coordinators.py):** el aim de la barrera es MONÓTONO hacia fuera dentro del episodio — métrica del usuario
> (dist centro→vaca no-a-salvo más próxima CRECE mientras los lobos se acercan): 58% por ventanas de 3 s, series
> 13→50-60 sostenidas (el aim v3.2 perseguía al ancla TAMBIÉN hacia dentro = paseo aleatorio 44.6%). **(2) ROLES
> INVERTIDOS del cebo (v3.3, wolf_controllers.py — causa raíz del ancla robada: ancla = PRIMER confirmado y el
> reflejo confirmaba al grueso):** el CEBO se deja confirmar PRIMERO (tras el disparo SE MUESTRA cargando y hace
> el ALA ROTA — retrocede arrastrando al investigador) y el ASALTO espera OSCURO por anillos (STAGE r_detect+50 →
> CREEP r_detect+25 → DEEP r_confirm+25, protegidos por la investigación-ÚNICA del reflejo) hasta ESTACIONARSE
> (pegado al sobre Y a ≤ trigger + DECOY_SHOW_LEAD=60 de su presa); ataca al saltar ESCOLTA o si le cazan
> (cierre >8 m/s alineado, ≤200). Medido (78 eps de 2 frentes): ancla = sector-cebo 13% → 60% (techo ~73%: en el
> 27% restante el asalto NACE a 108-130 m de un dron y el barrido lo caza — spawn, irreducible del lado del
> lobo); asalto ≤150 de su presa al saltar ESCOLTA 42-45% (frontera ancla↔profundidad ~1:1 medida en 8 configs;
> vías refutadas CON MEDIDA documentadas en wolf_controllers.py: show-al-dron-más-cercano = carrusel ·
> estacionamiento-con-alineación = interbloqueo 77/78 · CREEP+5/DEEP+10 = primer-contacto/roba-ancla · detector
> solo-cierre = falsos positivos de la patrulla). **(3) LÍNEA RÍGIDA (v3.4, regla del usuario: si un dron
> avanza, avanzan TODOS — la línea no se puede deformar):** la barrera es UN cuerpo con UNA pose (centro C +
> eje u) y offsets FIJOS — waypoint_i = C + off_i·perp SIEMPRE, ningún objetivo individual; el CIERRE LOCAL v3.3
> queda ELIMINADO (deformación por definición) y el avance lo GOBIERNA el MÁS REZAGADO: paso_pose = max(0,
> DRONE_MAX_SPEED·dt − err_max), desplazamiento (traslación+rotación) ≤ λ·(|Δc| + |Δφ|·r_max), λ = min(1,
> paso_pose/desplaz) — lazo realimentado (equilibrio analítico ~3.1 m/s con err ~1.2 m = el retraso del perfil
> de frenada v²/(2·ACCEL)); pose idempotente por paso; en la (re)formación NACE en el objetivo y espera QUIETA a
> que los drones lleguen (la línea se forma en el sitio y solo entonces avanza, rígida). RIGIDEZ MEDIDA (28 eps,
> estado FORMADA = 85% de los pasos CLEAN): error de estación p50 0.77 / p95 1.66 / máx 4.71 m (umbral aceptado
> 6 ≈ 4× el presupuesto por paso de 1.5 m); espaciado real p5-p95 19.7-20.3 m (nominal 20); colinealidad p95
> 0.20 m; velocidad de pose p50 1.74 / máx 13.2 m/s (moverse rápido es legal si TODOS siguen — el err queda
> acotado). COSTE del cierre eliminado, MEDIDO y reportado sin parches por-dron (mismas 28 eps): cruces de
> segmento 56 → 149 (hacia dentro con la línea en pie 33 → 92 ≈ 3.3/ep; mediana del hueco cruzado 20.0 = el
> corredor central; 104/149 amurallados — la pared blanda congelada solo quita la componente hacia el dron y
> CANALIZA: es muro frontal, no valla) y PENETRADO 4159 → 13593 pasos; la M1 del usuario sigue intacta (57.9%).
> **AGUJEROS CONOCIDOS Y DELIBERADOS de la baseline rígida (los que el MARL de drones deberá aprender a
> cubrir): rodeo por los FLANCOS de la línea estrecha (~60 m) · CRUCES residuales por los corredores entre
> paredes (4 drones vs enjambre de 5) · espalda del anillo de 50 · 2º frente libre — ahora EXPLOTADO de verdad
> por el cebo invertido.** Tests adaptados SIN bajar el listón (reactive_check 2 = reposición EN EL TIEMPO,
> mismo umbral 3 m · 10 = clones deepcopy que difieren SOLO en el frente ciego + convergencia gobernada 200
> pasos · 12 REHECHO = regla+trinquete en el objetivo, cuerpo rígido EXACTO con lobo apretando —resid<1e-6,
> spacing exacto, nadie se descuelga NI cierra—, 2 frentes bit a bit, gobernador acotado ≤1.5+ε y no-vacuo,
> err formada ≤6 · wolf_controller timing = gate de estacionamiento + show ≤ r_detect); verja 7/7. RE-MEDIDO
> (metro DGX, 100/tipo, 2ª pasada sin deriva): Dummy 3.77/0/3.74 → **3.82±2.41/0/3.84±2.43** (+0.05/+0.10: el
> lado lobo apenas mueve al Dummy clavado) · Reactive 1.91/0/1.96 → **2.68±1.66/0/2.77±1.71** (n_safe 4.16/4.10,
> success 5/7): la inversión ancla la línea única al cebo y el asalto entra por el frente libre — POR FIN el
> multi-frente scriptado paga contra la defensa (sexta lectura del cebo, la primera positiva). GIFs
> /data/gifs/v3.4/ + copias en la raíz (nº1 seed95: ancla=cebo, la línea rígida sale de 2 a 50 m FORMADA el 88%
> de los pasos · nº2 seed76: asalto a 146 m al saltar ESCOLTA, 6 muertes del asalto con la línea comprometida
> al cebo — candidato al GIF nº3 de la narrativa). **Nota a batir del MARL → 2.68/0/2.77.*** ·
> *(2026-07-23 (3ª): v3.2: BARRERA SIN HUECOS + AVANCE REAL + TIMING MEDIDO
> (RE-CONGELADO tag `v3.2-baseline`) — la defensa compacta que persigue baja a 1.91/1.96; el criterio de
> aceptación fue el COMPORTAMIENTO EN GIF, no el test.** Patrón corregido: los tests de v3.1 daban verde con la
> barrera QUIETA (pegada al rebaño: centro ≤37 m del centroide, solo perseguía con el ancla a <27 = la banda de su
> propio test 12), AGUJEREADA (spacing 32 > 2·STATIC=20 → franjas de 12 m sin pared: ~4.6 cruces de línea/ep y
> 75.4% de encuentros cercanos SILENCIOSOS —lobo a ≤DETER sin susto ni pared—) y con el timing MAL MEDIDO (el
> "13/15 acompasado" de v3.1 media el estado al asentarse el merodeo, no el instante del disparo: con LA MÉTRICA
> CORRECTA —dist del asalto a su presa en el paso exacto en que salta ESCOLTA— daba 58% ≤150, mediana 144).
> Diagnósticos con datos ANTES de tocar (v32_parte0/v32_race.py): anatomía de la carrera del timing — la
> investigación se lanza el MISMO paso de la detección (78/78) y confirma ~15 m más adentro → pasa ⟺ el barrido
> de patrulla detecta al asalto a ≤~165 de su presa. Arreglos: **(1) spacing = 2·STATIC_DETER_RADIUS = 20** (las
> paredes blandas ADYACENTES se tocan → 0 cruces limpios medidos; la línea estrecha ~60 m se RODEA por los
> flancos — limitación ACEPTADA, agujero deliberado; standoff derivado 17.3); **(2) persecución acotada — regla
> del usuario:** `aim = clip(d_ancla+10, suelo, MAX_ADVANCE_FROM_HERD=50)` desde el CENTROIDE de collares (la
> formación SALE al anillo de 50 y persigue dentro de él: 45% de pasos de ESCOLTA con algún dron cerrando >1 m/s
> sobre un confirmado; silenciosos 75.4→62.5%; centro ≤ anillo con 0 violaciones); **(3) ARCO OSCURO + PICADO del
> asalto** pre-disparo (`_assault_approach`: orbita a >r_detect+30 de todo ACTIVE —invisible: el reloj de la
> métrica no corre— hasta alinearse ±20° con el rumbo de SU presa y pica; detectado o investigador cerrando >8 m/s
> → carga pura) → timing **63% ≤150, mediana 143**; el resto es ESTRUCTURAL (13% cebo cazado al NACER a 4 vs
> 15 m/s — cola 300+ irreducible—; ~9% asalto barrido en su tránsito de nacimiento; detección lejana con el rebaño
> disperso). **4 vías refutadas CON MEDIDA** (esquive radial 58→51 · falda tangencial+sprint 58→47 · disparo
> adelantado gateado 56 · evasión anticipatoria neutra) documentadas en wolf_controllers.py; **(4)** emojis 0.20.
> Tests 11/12 rehechos (paredes que tocan; fórmula del anillo; dinámico con centro ≤ anillo); verja 7/7.
> RE-MEDIDO (100/tipo, 2ª pasada sin deriva): Dummy 3.74/0/3.69 → **3.77/0/3.74** (+0.03/+0.05 ≈ ruido: al Dummy
> solo le mueve el arco) · Reactive 2.18/0/2.21 → **1.91±1.35/0/1.96±1.56** (−0.27/−0.25: compacta + perseguidora
> defiende MEJOR, como anticipaba el prompt; n_safe 4.90/4.95). GIFs versionados /data/gifs/v3.2/ (nº1 asedio sin
> huecos sev=0 · nº2 barrera que avanza, 97% persecución · nº3 timing con el asalto a 142 m) + v32_frame_emojis.png.
> Nota a batir del MARL en v3.2 → 1.91/0/1.96 (agujeros deliberados: 2º frente libre + flancos + espalda del anillo).)* ·
> *(2ª: v3.1: BARRERA EN CONJUNTO + TIMING BLINDADO (RE-CONGELADO tag
> `v3.1-baseline`) — el experimento por fin JUSTO: la defensa coherente sube a 2.18/2.21; el 1.00 de v3.0 era en
> parte ARTEFACTO del dron-que-persigue.* Parte 0 diagnosticada ANTES de tocar: (a) el terreno NO era corto (lobos
> nacen a 114-329 m del dron más cercano, jamás confirmables ni detectables al nacer; la "alarma nada más aparecer"
> es el REFLEJO: el investigador a 15 m/s confirma con el lobo aún a 94-184 m del rebaño — percepción del GIF);
> (b) el timing del cebo fallaba porque el cebo BAJABA de r_detect=100 al asentar el merodeo (nace a ~114-135 del
> dron) → se volvía EL contacto y el investigador lo cazaba (hasta 0.3-2 m; 15 vs 4 m/s no se escapa) confirmándolo
> con el asalto a 238-440 m de su presa (5/15 episodios). Arreglos: **la barrera avanza EN CONJUNTO** (la embestida
> por-dron de v3.0 ELIMINADA; `adv = clip(L + STATIC_DETER_RADIUS, 12, 36.7)` = SOBRE-APUNTADO de formación — apuntar
> AL lobo deja escolta lateral con aproximación ~0; 10 m más allá garantiza cierre y expulsión del frente entero;
> DOS frentes → la línea ENTERA al ancla y el 2º LIBRE, defensa deliberadamente explotable = el agujero del MARL;
> test 12: colineales, spacing exacto, nadie se descuelga, mover el 2º frente no cambia ni un waypoint, expulsión
> sin re-subidas) + **decoy_hold_dist 100→130** (r_detect + 30 de buffer de evasión) con huida radial PURA al
> invadir (13/15 acompasados; residual 2/15 benigno: cebo cazado al nacer dentro del sobre de patrulla — ancla la
> barrera igual y el asalto entra libre, confirmado a 5-18 m del rebaño) + emojis 0.27 y sin círculo de presa.
> RE-MEDIDO (100/tipo, 2ª pasada sin deriva): Dummy 3.85/0/3.69 → **3.74/0/3.69** · Reactive 1.00/0/1.14 →
> **2.18±1.38/0/2.21±1.44** (+1.18/+1.07). **El premio PROPIO del cebo dentro de v3.1 sigue en RUIDO: episodios
> 2-grupos 2.34/2.34 vs 1-grupo 2.11/2.15 (+0.23/+0.19 ≈ 0.9 SEM)** — la línea única ocupada en cualquier frente
> deja huecos también sin cebo (quinta lectura consistente: el multi-frente scriptado no paga contra esta defensa).
> GIFs versionados /data/gifs/v3.1/ (nº1 Dummy pasivo · nº2 barrera clásica · nº3 cebo con formación en conjunto).
> Nota a batir del MARL en v3.1 → 2.18/0/2.21.)* ·
> *(1ª: v3.0: EL CEBO PERFECTO (RE-CONGELADO tag `v3.0-baseline`) — VEREDICTO
> (con el asterisco de v3.1): el cebo NO RINDE ni perfecto; la defensa arreglada lo aplasta.** Seis piezas juntas (decisión del
> usuario; el número no es atribuible a cada una): terreno 500×500 (solo CONFIG_V2; colchón ≥100 m, lobo naciente
> jamás confirmable al nacer; defaults 300 → face 12/12 bit a bit) + reparto de masa FIJO (`wolf_decoy_size=1` capado
> a n−2; medido 1-vs-2: **anclaje IDÉNTICO 0.28** — la masa no compra anclaje; con 1 el asalto mata el doble) +
> TIMING programado del cebo (merodeo `_decoy_prowl` fuera de r_confirm + disparo con el asalto a 150 m; latch
> `wolf_decoy_released` en el World) + FIX barrera que PRESIONA (`adv=clip(L,12,36.7)` + EMBESTIDA local 30 m; v2.9
> retrocedía y un dron que retrocede jamás expulsa) + FIX relevo SIN PARÁLISIS (el anunciado sigue comandable hasta
> el hand-off a blanco móvil; STRANDED se congela in situ) + render con emojis a color (fuente Noto en la imagen +
> fix del strike CBDT). RE-MEDIDO (100/tipo, 2ª pasada sin deriva): Dummy 3.98/0/3.88 → **3.85/0/3.69** · Reactive
> 2.46/0/2.44 → **1.00±1.66/0/1.14±1.81** (success 53%/50%, n_safe 5.79/5.58) — la severidad se HUNDE: presión +
> relevo continuo + margen de confirmación del terreno dominan al cebo perfecto, que sigue EJECUTANDO en micro
> (test 13; kills-del-asalto 1.16/ep en 2-frentes). Cuarta y definitiva confirmación (run05/06/07 + v3.0): **cebo
> scriptado DESCARTADO con prueba**. GIFs versionados en /data/gifs/v3.0/. **Nota a batir del MARL → 1.00/0/1.14**
> (margen absoluto pequeño; si el MARL sigue teniendo recorrido = decisión del usuario).* ·
> *(2026-07-22 (2ª): v2.9: BARRERA QUE AVANZA + CEBO DISEÑADO (RE-CONGELADO tag
> `v2.9-baseline`) — la prueba de existencia del cebo sale NULA en agregado.* La línea avanza al ancla (tope derivado
> 36.7 m, retaguardia confirmable) y el 2º sector fija la presa MÁS LIBRE (`pack_prey2`; diseñado, NO emergente; timing
> sin forzar; 1 grupo = bit a bit v2.8). Dummy 3.98/0/3.88 (±0.01) · Reactive **2.46/0/2.44** (v2.8: 2.56/2.26 →
> −0.10/+0.18); **ablación: cebo PURO +0.02/+0.10 ≈ RUIDO** — ejecuta en micro (5 capturas del 2º sector, test 13) pero
> no rinde: sectores con menos masa/quórum y una barrera que re-planifica a 15 m/s cubren el multi-frente casi gratis.
> Etapa 2 (RL del timing) con poco premio tal cual. **Nota a batir del MARL → 2.46/0/2.44.*** ·
> *(1ª: run07 CERRADO: el cebo NO emerge NI con frente ciego real.** Currículo de
> run06 sobre v2.8 (barrera honesta) con métrica corregida (killer-NO-CONFIRMADO de la memoria de la barrera; nula del
> scriptado 0.0% — señal límpida). Fase 1 clavada en el suelo 2.70; niveles nunca por encima del suelo; GUARDIA DE
> EROSIÓN disparada a 14.75M (stop fallido: SIGINT ignorado en runs desacoplados → lección SIGTERM); 100 semillas FINAL
> 1.93/1.87 (Δ −0.63/−0.39) · mejor 7.5M 2.25/2.21 (≈suelo); **cebo_diag 0.0% en TODOS los checkpoints**. Tercera
> confirmación: el cuello es la EXPLORACIÓN, no la geometría; currículo de spawn AGOTADO. Reservas: curiosidad
> coordinada / jerárquico / co-evolución (decisión del usuario).* · *(2026-07-21: v2.8 BARRERA HONESTA (RE-CONGELADO tag `v2.8-baseline`).* La barrera del
> ReactiveCoordinator reacciona SOLO a lobos **CONFIRMADOS de equipo con memoria** (alguna vez a ≤ `r_confirm`=40 de un
> dron ACTIVE; latch por episodio; tracking) — fin de la **percepción-oráculo** de v2.6 (reaccionaba a contactos a
> `r_detect`=100 sabiendo el tipo por verdad-terreno → no dejaba frente ciego → el cebo era imposible por ARTEFACTO). +
> **standoff DERIVADO** `sqrt(R²−(s/2)²)=12 m` (la línea pegada: sin hueco entre barrera y rebaño fuera de disuasión).
> Cambio SOLO en `coordinators.py`; FÍSICA ≡ v2.7 → Dummy **BIT A BIT 3.97/0/3.89**; Reactive re-medido 2.30/0/2.42 →
> **2.56±1.55/0/2.26±1.32** (la honestidad encarece +0.26 en solo-lobos, el standoff pegado abarata −0.16 en mixto;
> margen vs Dummy −1.41/−1.63). **Nota a batir del MARL de drones → 2.56/0/2.26** (la 2.30/2.42 era contra la barrera-
> oráculo; run01 sigue histórico). El frente ciego EXISTE por fin — el cebo deja de ser geométricamente imposible.* ·
> *(2026-07-19: v2.7 SUSTO DE DOS RADIOS (RE-CONGELADO tag `v2.7-baseline`).* Cambio de FÍSICA del susto: se mantiene la EXPULSIÓN por movimiento de v2.4 (radio grande `DETER_RADIUS`=20) y se AÑADE una **PARED BLANDA** estática (radio pequeño `STATIC_DETER_RADIUS`=10): un dron ACTIVE **quieto** a corta ya NO se cruza (repulsión radial que frena/desvía, `_wolf_walled`) y **no deja matar a través**; un poste a distancia se sigue ignorando (habituación) y mover sigue siendo ESTRICTAMENTE mejor (radio mayor + expulsión plena). Fiel a los datos de fuga (FID ~106 m, escalado). RE-MEDIDO (metro DGX, 100/tipo): Dummy 4.42/0/4.34 → **3.97/0/3.89** (Δ −0.45/−0.45: los drones clavados repelen a corta), Reactive 2.74/0/2.82 → **2.30/0/2.42** (Δ −0.44/−0.40: la barrera se hace pared). El margen Reactive−Dummy se mantiene (−1.67/−1.47); es MEDIDA, no objetivo. face_check 12/12 bit a bit (susto gateado por escort_enabled en combate) + `test_pared_estatica` dirigido nuevo (cobertor bloquea la matanza / lejano no / embestida expulsa más). **INVALIDA la baseline del MARL de drones run01** (medido sobre v2.6, barrera atravesable): run01 = histórico; el MARL se reentrenará sobre v2.7 (nota a batir 2.30/0/2.42) en fase posterior — NO reentrenado aquí. Motivación: la barrera atravesable quitaba presión selectiva al CEBO (no había que engañar una pared que se cruza).* *(2026-07-18 3ª: RUN01 del MARL de DRONES COMPLETADO — EL MARL BATE LA BARRERA v2.6.** 100 semillas: modelo FINAL (20M) **2.35±1.33 / 0.00 / 2.34±1.42** → Δ **−0.39/−0.48** vs barrera 2.74/0/2.82; mejor ckpt (18,99M) 2.41/0/2.42 (Δ −0.33/−0.40). Guardias del pacto JAMÁS disparadas; DIAGNÓSTICO: el Δ es **MOVERSE PARA DISUADIR** (rapidez ACTIVE +17%, lobos huyendo/paso +26%) y NO repartirse entre frentes (6.2%→6.5%): vence la HABITUACIÓN v2.4. La mejora seguía creciendo (evals >18M media 2.125).* *(2ª: INFRA MARL construida y verificada. 1ª: run05 — el cebo NO emerge con recompensa de equipo pura.)* 100 semillas (arnés canónico): modelo FINAL (20M) **2.35±1.33 / 0.00 / 2.34±1.42** → Δ **−0.39/−0.48** vs barrera 2.74/0/2.82 (~2,8–3,4 SEM); mejor ckpt por ligeras (18,99M) 2.41/0/2.42 (Δ −0.33/−0.40) — ROBUSTO al checkpoint; n_safe 4.16/4.06→4.54/4.54; vs Dummy −2.01/−1.92. Guardias del pacto (`c215689`) JAMÁS disparadas: fase 1 clavada en el suelo de la ligera (2.80 EXACTO, detalle idéntico ×4), cero evals >2.9 en fase 2 (sin erosión), patrón proxy nunca presente (la disuasión osciló mientras la severidad bajaba). DIAGNÓSTICO de comportamiento (58 episodios GEMELOS de 2 frentes, suelo vs política): el Δ es **MOVERSE PARA DISUADIR** — rapidez ACTIVE 3.76→4.39 m/s (+17%), lobos huyendo/paso 1.19→1.50 (+26%), severidad 2-frentes 3.31→2.90 — y NO repartirse entre frentes (ambos atendidos 6.2%→6.5%, idéntico): la política vence la HABITUACIÓN v2.4; el agujero de la línea única queda sin explotar (coherente con run05: el scriptado no ceba → sin presión selectiva). La mejora seguía CRECIENDO al agotar el presupuesto (evals >18M: media 2.125). Siguiente = decisión del usuario: aceptar el FINAL como coordinador MARL v1 / más presupuesto (--resume) / co-evolución / YOLO.* *(2ª de hoy: INFRA MARL construida y verificada — suelo δ=0 Δ +0.00 exacto, test 10, sin deps nuevas. 1ª: DESENLACE run05 — el cebo NO emerge con recompensa de equipo pura; cebo_diag 0.0% = nula del scriptado; el cebo es una desviación coordinada temporalmente extendida con valle de recompensa en medio que la exploración por-paso no muestrea.)*
>
> **CIERRE de la primera campaña RL de lobos (runs 01–03) — la ablación completa, breve y factual:**
> **run01** (rala pura, de cero) ABORTADO a 2,48M: 1 muerte espontánea en ~2.400 episodios, 0 señal · **run02**
> (shaping por potencial β=1, de cero) 10M: **0.57/0.60** (100 semillas) · **run03** (shaping + warm-start desde el
> clon BC v3) 10M: **0.65/0.72**. Referencias fijas: cuna BC 0.2 · techo de la etiqueta media (oráculo en vivo) 2.60 ·
> scriptado vs barrera **2.77/2.80**. **Lección 1 (medida):** la cuna aporta — run02 y run03 solo difieren en el init
> (+0.08/+0.12 y arranque mucho más rápido). **Lección 2 (medida por capas):** la MANIOBRA de flanqueo (la que dispara
> el quórum de captura) es el muro de las dos vías — la imitación no la representa (clon 0.2 con techo 2.60;
> estratificación: viaje cos 0.83 / maniobra cos 0.26) y la exploración de PPO no la descubre (el Φ de distancia
> premia acercarse, no flanquear). **Motivación de run04 (RPL):** si la red no puede APRENDER la caza, que no la
> aprenda — el script la ejecuta y la red solo la CORRIGE; el suelo queda garantizado por construcción.
> **Hecho:** terminal (el "juez") · disparador realista por detección de dron · reescalado a 300×300 (~9 ha) con
> escala biológica absoluta · dispersión del rebaño · movimiento de drones · detectar→acercarse→confirmar ·
> **guiado al refugio (paso 2)** · **huida NO-HOLONÓMICA en ESCOLTA** (pin) · **DISUASIÓN del dron** (radio CORTO + bordeo, parcial) ·
> **MATANZA EXCEDENTE** (el paquete caza hasta agotar) · **ATAQUE ENVOLVENTE** (una adulta clavada es matable) ·
> **EVITACIÓN al huir** (las no-fijadas RODEAN a los lobos camino del establo) · **la MADRE no abandona al ternero**
> (huyen juntos al ritmo de la cría, más lenta) · **los LOBOS no se pillan en la zona segura** (la BORDEAN, no entran) ·
> **CORZOS (3c)** (cuerpos NO-amenaza: deambulan+huyen, detectables, ORÁCULO a r_confirm, 3 tipos de episodio) ·
> **v2 CONGELADA (tag `v2-baseline`)** (la física NO cambia más; `baseline.py` = arnés de evaluación POR TIPO,
> severidad Dummy solo-lobos 4.45 / solo-corzos 0.00 / mixto 4.41, N=100) ·
> **ReactiveCoordinator** (1er coordinador clásico: BARRERA de apantallado; regla fija, NO aprende) →
> severidad (v2.4.1, metro DGX) **2.77 / 0 / 2.80** (−1.77 / − / −1.66 vs Dummy 4.54/0/4.46; en el metro portátil
> v2.4 era 2.80/2.78 vs 4.41/4.34) — SUBE desde v2.3 (0.16/0.18) porque la barrera clavada es un POSTE, pero SIGUE
> batiendo al Dummy (su barrera se recoloca) ·
> **RELEVO de flota REALISTA (v2.1)** (hand-off, SIN teletransporte: la reserva VUELA al puesto, el bajo cubre
> hasta el relevo, vuelve a cargar; STRANDED bajo estrés → moverse tiene COSTE real) ·
> **RENDER: emojis a color + barra de batería + `main.py --coordinador`** ·
> **JABALÍ 🐗 como 2ª distracción (v2.2, tag `v2.2-baseline`)** (~50/50 con el corzo, mismo comportamiento,
> substream RNG separado → spawns intactos; emojis más pequeños; mismos números, RE-CONGELADO).
> **Retoques visuales + fix del ARRANQUE del reactivo** (emojis aún más pequeños `EMOJI_SCALE`=0.45, SIN leyenda de
> entidades, **🔊 al disuadir**; la PATRULLA ancla la fase a la posición angular ACTUAL → los drones se abren a su ranura
> más cercana desde t=0, sin cruzar el centro; Reactive 3.27/3.40→**3.36/3.42**, Dummy/física INTACTOS, NO re-congela).
> **SUSTO FUERTE + rombo de carga (v2.3, tag `v2.3-baseline`)** (la disuasión pasa de PARCIAL a FUERTE: un dron ACTIVE a
> ≤DETER_RADIUS EXPULSA al lobo —campo de fuerza estático—; Dummy 4.45/4.41→2.36/2.24, Reactive 3.36/3.42→0.16/0.18).
> **SUSTO POR MOVIMIENTO + baterías espejo + carga 1.5× (v2.4, tag `v2.4-baseline`)** (el lobo se HABITÚA a disuasores
> estáticos: solo el dron que SE ECHA ENCIMA —aproximación > `SCARE_APPROACH_MIN`— expulsa; el QUIETO es un OBSTÁCULO que
> se rodea. Baterías iniciales aleatorias + reserva espejo (substream separado); carga = 1.5× el vuelo pleno ≈160 s. La
> disuasión estática se evapora → Dummy 2.36/2.24→**4.41/4.34** (≈v2.2), Reactive 0.16/0.18→**2.80/2.78** (sube, pero sigue batiendo al Dummy)).
> **SUSTO DE DOS RADIOS (v2.7, tag `v2.7-baseline`)** (la expulsión por movimiento de v2.4 INTACTA + una PARED BLANDA
> estática `STATIC_DETER_RADIUS`=10: un dron ACTIVE quieto a corta ya no se cruza —repulsión que frena/desvía, `_wolf_walled`—
> y no deja matar a través; poste a distancia ignorable —habituación— y mover ESTRICTAMENTE mejor. Metro DGX: Dummy
> 4.42/4.34→**3.97/3.89**, Reactive 2.74/2.82→**2.30/2.42**; INVALIDA la baseline del MARL run01 —histórico sobre v2.6—).
> **Refactor — CONTROLADOR DE LOBOS ENCHUFABLE (`wolf_controllers.py`)** (scripted | learned; el scriptado es el
> default BIT A BIT idéntico a v2.4). Extrae la POLÍTICA del lobo (táctica: fijación de presa, flanqueo, rodeo,
> envolvente, coasting) a una interfaz `decide(world) -> (v_target, coasting)`; el mundo impone la FÍSICA (susto,
> inercia+integración, cap, captura). Prepara la fase RL (lobos que burlan la barrera). CERO cambio de comportamiento,
> CERO re-congelación (fingerprint bit a bit vs v2.4; verja verde SIN adaptar).
> **Pendiente:** **fase RL** — (1) lobos: campaña 01–04 CERRADA (rala 0 · shaping 0.57/0.60 · cuna+shaping 0.65/0.72 ·
> residual Δ≈+0.0); el scriptado = lobo canónico. La v2.5 abre el MULTI-FRENTE (Nivel A, mundo) y la v2.6 lo hace
> EXPLOTABLE de verdad (la barrera solo ve lo detectado): **run05 (Nivel B) CERRADO por la guardia de estancamiento
> (4.2M)** — con recompensa de equipo PURA el cebo NO emerge (Δ ≈ +0.0; cebo_diag 0.0% = nula del scriptado);
> candidatos si se insiste: pista al cebo / control de formación / co-evolución; (2) **MARL de
> drones: run01 COMPLETADO Y BATE LA BARRERA** — FINAL (20M) **2.35/0/2.34** (Δ **−0.39/−0.48** vs 2.74/0/2.82),
> aprendió a MOVERSE para disuadir (+17% rapidez, +26% sustos; vence la habituación v2.4), sin repartirse entre
> frentes. **run01 medido sobre v2.6 → INVALIDADO como baseline por v2.7 (pared blanda); histórico.** (3) **v2.7 SUSTO DE
> DOS RADIOS** (la barrera se hace pared: dron quieto repele a corta): re-medido Dummy **3.97/0/3.89** · Reactive **2.30/0/2.42**;
> el MARL de drones se REENTRENARÁ sobre v2.7 (nota a batir 2.30/0/2.42) en fase posterior. Siguiente paso = decisión del usuario
> (barrido 3+3 vs 4+4 drones / reentrenar el MARL sobre v2.7 / co-evolución). (4) **CURRÍCULO del cebo (lobos, v2.7):** ataca el
> **valle del cebo** = *relative overgeneralization* (BIBLIOGRAFIA: JIM/lenient learners) — la política óptima (cebo coordinado)
> da mala recompensa si un solo lobo la intenta → PPO se queda en "atacar juntos". v2.7 cerró el agujero de "atravesar" (dio
> propósito al cebo) pero NO elimina el valle. **Vía: CURRÍCULO de separación de spawn** (Bengio 2009 / Narvekar 2020) —
> arranca al lobo AL OTRO LADO del valle (nivel 1: 2 frentes ~180° opuestos + ambos letales masa≥2 → el cebo casi ocurre solo)
> y endurece por niveles (135°/90°/normal, 5M c/u, 20M total) hasta que debe FORMAR el cebo solo. Residual sobre el scriptado,
> recompensa de EQUIPO PURA (shaping off, sin pista de cebo), 2 fases. **El currículo es SOLO un override del ENV de
> ENTRENAMIENTO** (`WolfPackEnv.set_curriculum` → re-coloca los 2 subgrupos con RNG propio tras `reset()`; NO toca el mundo
> congelado); la EVAL es SIEMPRE spawn grouped normal de v2.7 (mide el cebo REAL, no el servido). **Paso 0 (verificado):** el
> suelo residual (δ=0) contra la pared v2.7 está SANO (los lobos RODEAN/atacan —predation, rapidez ~2.6 m/s, alcanzan la presa a
> 0.6 m—, NO zombis contra la pared). **run06 COMPLETADO (20M) — EL CEBO NO CRUZA EL VALLE NI CON EL SPAWN SERVIDO.** Fase 1
> clavada en el suelo (eval ligera 10 semillas = 2.20 EXACTO; guardia recalibrada a <1.9 = suelo−0.3; el arnés de 100 da 2.30/2.42).
> Trayectoria por nivel (eval ligera, spawn normal): L1 ~2.52 → L2 ~2.5 → L3 ~2.30 → **L4 ~2.12** (degradación MONÓTONA al estrechar
> la separación hacia el spawn real). **100 semillas (arnés): FINAL (20M) 1.90/1.88 → Δ −0.40/−0.54 (POR DEBAJO del suelo: el
> residual curricular EROSIONA al script) · mejor ckpt 4M 2.18/2.35 (Δ −0.12/−0.07 ≈ suelo) · 6.5M 2.14/2.37 (≈ suelo).** `cebo_diag`
> en TODOS los checkpoints: **killer-no-detectado 0.0% / cebo PURO 0.0% = la nula EXACTA del scriptado** — ni una muerte desde el
> frente no visto, ni siquiera a 4M con el cebo casi servido (allí la severidad en episodios de 2 grupos sube a 2.93, pero es
> flanqueo más agresivo de los frentes VISTOS, no cebo). **Veredicto: el cebo NO se forma — ni con el spawn servido la política
> aprende a matar desde el frente no visto; el currículo de separación no cruza el valle (relative overgeneralization) y al
> endurecer erosiona levemente.** Confirma y profundiza run05 (recompensa pura). **Vías de reserva (BIBLIOGRAFIA, NO implementadas —
> decisión del usuario): exploración intrínseca COORDINADA (curiosidad: EMC/MACE/SMMAE/JIM) → control JERÁRQUICO de formación.**
> **Commits:** `194a3ad` base · `37910b3` terminal · `e663504` disparador por dron · `4d1e708` campo
> 300×300 + escala biológica absoluta · `886bd45` dispersión del rebaño · `a15e2df` movimiento de
> drones (3a) · `fd893b8` detectar→confirmar (3b) · `49e0e22` consolidar DISEÑO+CLAUDE · `144b7bd` guiado (paso 2)
> · `1d44cdc` máx. 1 caza/episodio (REVERTIDO) · `56ff75d` huida no-holonómica · `f42456f` dos correcciones huida ·
> `26bce79` disuasión del dron · `bd57a8f` matanza excedente · `1b54b49` fix pin + envolvente · `bbee8c0`
> evitación al huir · `e15d43d` el más cercano investiga · `5a9dddb` afinar disuasión (radio corto + bordeo) ·
> `101558f` la madre no abandona al ternero · `4250488` los lobos no se pillan en la zona segura ·
> `bda6156` corzos (3c) · `e44d7c2` fix: main.py no spawneaba corzos + `--escenario` · `9e11a29` afinar corzos
> (vuela e investiga, agrupados, SOSPECHA, render natural) · `b04e8d9` congelar v2 (tag `v2-baseline`) ·
> `2ad268b` ReactiveCoordinator (barrera de apantallado) · `bcd407f` relevo de flota REALISTA (v2.1, tag
> `v2.1-baseline`) · `e14206a` render: emojis a color + barra de batería + `--coordinador` · `11dc90d`
> jabalí como 2ª distracción + emojis más pequeños (v2.2, RE-CONGELADO tag `v2.2-baseline`) · `a97362d`
> retoques visuales + fix arranque del reactivo (patrulla anclada, sin cruces; Reactive 3.36/0/3.42) · `49fd8c4`
> SUSTO FUERTE + rombo de carga (v2.3, RE-CONGELADO tag `v2.3-baseline`; Dummy 2.36/0/2.24, Reactive 0.16/0/0.18) · `7cf7381`
> SUSTO POR MOVIMIENTO + baterías espejo + carga 1.5× (v2.4, RE-CONGELADO tag `v2.4-baseline`; Dummy 4.41/0/4.34, Reactive 2.80/0/2.78) · `aa77e0a`
> refactor: controlador de lobos ENCHUFABLE (scripted | learned), bit a bit vs v2.4 — prepara la fase RL (SIN re-congelar) ·
> `6b936c4` ANDAMIAJE RL de lobos (docker/ + rl/: WolfPackEnv, RLWolfController, train_wolves + rl_env_check en la
> verja) **+ v2.4.1-baseline: mismo mundo, METRO DGX** (la baseline del portátil no se reproducía entre plataformas —deriva
> FP amplificada por el caos—; re-medición canónica DENTRO del contenedor: Dummy 4.54/0/4.46, Reactive 2.77/0/2.80; tag
> `v2.4.1-baseline`) · `e1e1b31` EVALUADOR de lobos aprendidos (rl/obs.py origen único + PolicyWolfController +
> SyncedReactiveCoordinator + rl/eval_wolves.py; equivalencia env↔evaluador bit a bit = rl_env_check test 7) + train serio
> (gamma 0.999, --resume, train.log, eval ligera) — run01 10M lanzado desacoplado tras el commit · `9fc906f` docs:
> desenlace del run01 (ABORTADO a 2,48M por el criterio pactado — la rala no arranca) · `<este commit>` plan B ACTIVADO:
> SHAPING POR POTENCIAL en WolfPackEnv (Φ = −β·dist media a la presa ternero-primero / diagonal; r_shape = γΦ′−Φ con el
> γ del PPO; componentes en info/log; eval SIEMPRE sin shaping) + test 8 (telescopia/signo/kills/off≡run01) + run02 de
> cero (10M, shaping ON) lanzado desacoplado tras el commit (`c77686d`) · `2620471` run02 COMPLETADO (tablas de
> ablación 0.57/0.60) + plan C CONSTRUIDO (collect_demos con presa del contrato + bc_pretrain enmascarado/dir +
> train_wolves --init-from) — cuna BC ≈0, investigación completa, run03 NO lanzado (puerta pactada) · `0d1e5fb` docs:
> tabla del mejor ckpt de run02 · `<este commit>` opción A (π [256,256]): clon SIGUE ≈0 → hallazgo del ALIASING de la
> etiqueta (31% de flips a 0,5 s); run03 sigue sin lanzarse (rama ≈0 del árbol); candidatos A′/C/B documentados ·
> `3d99c13` opción A′: --label mean (v3) + TECHO en vivo 2.60 (etiqueta exonerada); clon 0.2/10 → el cuello es la RED
> (viaje sí, maniobra no) · `058dbfd` DECISIÓN (C): run03 desde el clon v3 CON shaping (β=1; red de seguridad +
> run02 vs run03 aísla la cuna); aborto adaptado (~3M sin superar ~0.2); lanzado desacoplado tras el commit ·
> `ed16a81` docs: DESENLACE run03 (10M completos; 100 semillas: FINAL 0.65/0.72, mejor 4M 0.66/0.71 — la cuna
> aporta vs run02, el scriptado sigue lejos; la maniobra de flanqueo es el muro) · `74b3bab` run04 RESIDUAL
> (RPL): residual_wolf_controller + env residual + train 2 fases (init a cero verificado, guardia del suelo 2.3) +
> test 9 (δ=0 ≡ scriptado bit a bit) + eval_wolves --residual/--floor + BIBLIOGRAFIA.md; run04 lanzado tras el commit ·
> `7f36144` docs: DESENLACE run04 (Δ ≈ +0.0 sobre el scriptado en 100 semillas — mejor 2.82/2.81, final
> 2.61/2.66; andamiaje RPL impecable, sin adaptación que generalice) + cierre de la fase de lobos aprendidos ·
> `9401b78` v2.5: SPAWN EN SUBGRUPOS (Nivel A, tag `v2.5-baseline`) — grouped en CONFIG_V2/main (default
> clustered ≡ v2.4.1 bit a bit; substream seed+3_000_003); hipótesis multi-frente MEDIDA y NO confirmada en el
> scriptado (Dummy 4.42/0/4.34 · Reactive 2.71/0/2.76, ~1 SEM de bajada); el MARL pasa a batir 2.71/0/2.76 ·
> `19a97ab` v2.6: BARRERA REACTIVA CON PERCEPCIÓN REALISTA (tag `v2.6-baseline`) — la barrera se ancla al lobo
> DETECTADO (criterio r_detect/ACTIVE del mundo, solo-lectura; ancla = primer detectado con histéresis; PENETRADO
> solo sobre detectados; sin detectados → patrulla) en vez de a `wolves.mean()` omnisciente; SOLO coordinators.py,
> física ≡ v2.5 → Dummy BIT A BIT 4.42/0/4.34 · Reactive 2.74/0/2.82 (+0.03/+0.06, dentro del ruido); el frente
> NO visto ya no influye → el cebo del Nivel B es físicamente real; el MARL pasa a batir 2.74/0/2.82 ·
> `8f44d0e` run05 NIVEL B (lanzado tras el commit): residual de run04 tal cual sobre v2.6 grouped, recompensa
> de EQUIPO PURA (+1/muerte compartida, shaping OFF, sin pista de cebo), δ autoridad plena, 2 fases, 12 envs, lr 1e-4,
> 10M, /data/wolves/run05_nivelB; guardias suelo 2.4 (≥1M, fase 2) y estancamiento a ~4M (~2.8); suelo v2.6 grouped
> verificado 2.74/2.83 (+0.00/+0.01); `rl/cebo_diag.py` NUEVO (nula del scriptado: 0.0% cebo puro / 0.0% killer no
> detectado; no-anclado 46.1% post-fusión; 25.6% de pasos con un solo grupo visto) ·
> `f5c0d8a` docs: DESENLACE run05 — guardia de ESTANCAMIENTO saltó a 4.2M (ligeras 2.50-3.10 ≈ suelo 2.90 sin
> tendencia); 100 semillas: 4M Δ −0.07/−0.11 · 3.5M Δ +0.06/−0.11; cebo_diag 0.0%/0.0% en ambos = nula del scriptado
> (ni una muerte desde el frente no visto); el cebo NO emerge con recompensa pura — siguiente movimiento = usuario ·
> `aac480d` INFRA MARL de DRONES (sin run serio): rl/drone_obs.py (obs por PUESTO: local 131 con lobos solo
> DETECTADOS + ego + pista base; global privilegiada = build_obs) + rl/residual_drone_coordinator.py (barrera v2.6
> viva dentro, δ enmascarada ACTIVE&~inv&~hold, model=None⇒suelo) + rl/drone_env.py (DroneTeamEnv 3 kinds, recompensa
> global+local por separado, TeamUnstackVecEnv M mundos→4M streams) + rl/train_drones.py (MAPPO sobre SB3 pinneado:
> SplitMlpExtractor π←local/V←global, 2 fases, init δ≡0 assert) + rl/drone_eval.py (arnés 100 semillas) + test 10 de
> rl_env_check; SUELO verificado Δ +0.00 exacto (2.74/0/2.82); verja 7/7; smoke ~880 fps-agente; BIBLIOGRAFIA
> +DE-MADDPG/escolta/COMA/difference/VDN/QMIX; sin dependencias nuevas ·
> `c215689` run01 MARL de drones: PACTO de guardias fijado en el entrenador ANTES del run (EROSIÓN: ligera sostenida
> >~2.9 en fase 2 ≥1,5M · ANTI-PROXY: ep_deter sube sin bajar ep_sev ≥2M, par impreso en cada eval · SIN aborto por
> estancamiento) + eval ligera del pacto = 10 semillas FIJAS 5 lobos+5 mixto (suelo δ=0 medido 2.80 EXACTO, detalle
> [3,0,3,4,4|4,0,3,2,5]); verja 7/7; run01 (20M pasos-agente, 12 mundos, lr 1e-4, /data/drones/run01) lanzado tras
> el commit ·
> `<este commit>` docs: DESENLACE run01 MARL de drones — **EL MARL BATE LA BARRERA**: 100 semillas FINAL (20M)
> 2.35±1.33/0/2.34±1.42 (Δ −0.39/−0.48) · mejor ckpt 18,99M 2.41/0/2.42 (Δ −0.33/−0.40) — robusto al checkpoint;
> guardias jamás disparadas (fase 1 clavada 2.80 ×4; cero erosión; cero proxy); diagnóstico de comportamiento (58
> gemelos de 2 frentes): +17% rapidez ACTIVE, +26% lobos huyendo/paso, sev 2-frentes 3.31→2.90, SIN reparto entre
> frentes — la política vence la habituación v2.4; siguiente movimiento = decisión del usuario.
>
> **Patch — run02 COMPLETADO (ablación desde-cero) + plan C CONSTRUIDO pero PARADO: la cuna BC no valida (2026-07-15).**
> **run02 (shaping, 10M completos, ~3 h a ~920 fps):** ep_kills_mean del buffer 0.00→**0.35–0.40** (a 1M: 0.02; 3M: 0.16;
> 5M: 0.33; 10M: 0.35) — el criterio de aborto (kills ≈ 0 a 3M) NO saltó; ep_shape_mean ~0.5 estable todo el run;
> ep_len_mean 340→~2.000 (los lobos alargan la partida presionando la barrera); evals ligeras deterministas 0.00 (hasta
> 1M) → 0.30–0.80 (pico 0.80 a 6,25M). **Tablas de 100 semillas (eval_wolves, arnés v2.4.1):** modelo FINAL (10M):
> solo-lobos **0.57±0.72** / mixto **0.60±0.75** (success 16/15, predation 44/45, timeout 40/40; n_safe 5.57/5.48) vs
> scriptados 2.77/2.80. Mejor checkpoint por evals ligeras (5,5M): **0.57±0.71 / 0.56±0.67** (success 28/24) — la meseta
> de run02 es ROBUSTA al checkpoint (final ≡ mejor); ambas tablas en /data/wolves/run02/eval_*.json.
> **Queda como ABLACIÓN desde-cero del plan C** (motivación de diseño del usuario: los lobos reales YA saben cazar; ante
> los drones aprenden a ADAPTAR la caza → clonar al scriptado y afinar).
> **Plan C construido:** `rl/collect_demos.py` (episodios scriptado-vs-barrera con el bucle del arnés; pares (obs,
> acción) muestreados en las FRONTERAS del env —misma convención que test 7—; acción = v_target del scriptado ÷
> wolf_speed; semillas 10_000+ DISJUNTAS del examen; paralelo por episodios con corte determinista; 120.214 pares / 150
> episodios, experto 2.59±1.37 muertes/ep) · `rl/bc_pretrain.py` (la MISMA política PPO [128,128]; entrena SOLO π —value
> y log_std frescos—; pérdida ENMASCARADA a slots presentes; `--loss mse` (receta) o `dir`=(1−cos)+(Δ|·|)²; split 90/10 +
> early-stop; bc_model.zip SB3 estándar) · `train_wolves.py --init-from` (copia SOLO los tensores de π; value FRESCO;
> `--lr` para fine-tune; criterio de aborto warm-start —eval ligera < mitad del clon ≥1,5M— en la cabecera del log).
> **LA CUNA NO VALIDA — investigación (la rama "para e investiga" del prompt):** el clon salió 0.2 → diagnóstico:
> **(a) pipeline EXONERADO** — el scriptado por el MISMO camino: puro 2.7 · con hold de 0.5 s **2.7** (el frame-skip no
> cuesta) · con hold + PRESA DEL CONTRATO RL (ternero-primero pinada cada paso) **2.5** = el TECHO honesto de la cuna;
> **(b) 1ª causa real encontrada — desajuste entrenamiento/servicio:** las demos v1 nacían con el pinning del scriptado
> (histéresis, estado OCULTO que no viaja en la obs) y el clon sirve bajo el pin ternero-primero → se re-colectó con la
> presa del contrato IMPUESTA tras cada decide (collect_demos documenta el orden exacto); **(c) pese a (b) y a la
> máscara, el clon quedó en 0.0** con AMBAS pérdidas (mse y dir): en abierto |exp| = 1.000 SIEMPRE (la acción experta es
> una DIRECCIÓN pura) pero |pred| ≈ 0.62 (p10 0.10) con 17% de cosenos NEGATIVOS y **train ≈ val ALTO en ambas losses →
> INFRAAJUSTE**: la [128,128] no representa la asignación DISCONTINUA de huecos del envolvente (qué lobo toma qué ángulo);
> **(d) en cerrado el clon SÍ cruza la barrera y merodea a r_face_safe (~6 m) miles de pasos sin sustos, pero jamás
> completa el flanqueo que dispara el quórum** → 0 muertes. Conclusión: no es un bug — es capacidad/representación para
> la maniobra que mata. **La puerta pactada (cuna ≥~1.5 antes de run03) NO se cumple → run03 NO LANZADO.** Opciones
> (sin implementar, decisión del usuario): **(A)** ampliar la política (p.ej. [256,256]) en BC+PPO — ataca la causa
> medida; rompe "misma arquitectura que run02" (la ablación pasa a ser cross-arquitectura, documentable); **(B)**
> DAgger-lite (consultar al scriptado en los estados del clon) — ataca el compounding, NO el infraajuste (train≈val);
> **(C)** run03 desde el clon ≈0 igualmente — el prior ya resuelve lo que mató a run01 (llegar a la presa a través de la
> barrera); contraviene la puerta pactada, solo con OK explícito; **(D)** warm-start + shaping (plan B) combinados.
> Artefactos en /data/wolves: demos/ (dataset+manifest+bc_model.zip+config), demos_v1_inconsistentes/ (histórico del
> diagnóstico), run02/eval_final_10M.json + eval_best_5.5M.json. Verja tras el plan C: rl_env_check 8/8 + face_check +
> wolf_controller_check verdes (los checks 1–8 intactos; el código nuevo no toca env/mundo/obs).
>
> **Patch — DESENLACE run01 del MARL de DRONES: EL MARL BATE LA BARRERA — el primer coordinador que baja del
> suelo, y el diagnóstico dice POR QUÉ: se mueve para disuadir (2026-07-18, 3ª).** Run limpio de 20.054.016
> pasos-agente (~5,5 h a ~1.010 fps-agente; 12 mundos → 48 streams; lr 1e-4; δ escala 20 m; local_coef 0.01;
> /data/drones/run01). **Pacto de guardias fijado ANTES del run (`c215689`):** eval ligera = 10 semillas FIJAS
> 5 lobos + 5 mixto (suelo δ=0 MEDIDO antes de lanzar: 2.80 EXACTO, detalle [3,0,3,4,4|4,0,3,2,5]); guardia de
> EROSIÓN (ligera sostenida >~2.9 en fase 2 durante ≥1,5M → parar) + ANTI-PROXY (ep_deter sube sin que ep_sev
> baje ≥2M → parar; el par (ep_sev, ep_deter) del buffer impreso en CADA eval para leer la vigilancia eval a
> eval) + SIN aborto por estancamiento (a diferencia de los lobos, el suelo es útil: δ≈0 = la barrera).
> **NINGUNA guardia saltó:** fase 1 (solo-crítico, 1M) clavada en 2.80 con detalle idéntico ×4 (termómetro del
> suelo con el crítico centralizado calentando); en fase 2 CERO evals >2.9 (sin erosión) y el patrón proxy
> jamás apareció (deter osciló 850–2.100 sin tendencia monótona MIENTRAS la severidad bajaba — eso es el
> mecanismo, no el proxy). **Trayectoria:** ligeras 2.5–2.9 alrededor del suelo hasta ~6M → banda 2.2–2.5 →
> el MEJOR tramo es el FINAL (evals >18M: media 2.125, mín 1.80) — la mejora seguía creciendo al agotar el
> presupuesto. **TABLAS 100 semillas (arnés canónico, mismas semillas, metro DGX):** modelo FINAL (20M)
> solo-lobos **2.35±1.33** / solo-corzos 0.00 / mixto **2.34±1.42** → Δ **−0.39 / −0.48** vs barrera
> (2.74/0/2.82), ~2,8–3,4 SEM por tipo y consistente en ambos; n_safe 4.54/4.54 (barrera: 4.16/4.06); vs
> Dummy 4.42/0/4.34: −2.07/−2.00 · mejor ckpt por ventana de ligeras (18.998.784) **2.41±1.44 / 0 /
> 2.42±1.37** (Δ −0.33/−0.40) — ROBUSTO al checkpoint (el final ≥ el mejor: sin sobreajuste a la ligera).
> **DIAGNÓSTICO de comportamiento (espíritu cebo_diag, bando drones; script en /data/drones/diag/
> run01_comportamiento.py; 58 episodios GEMELOS de 2 subgrupos, mismas semillas, suelo δ=0 vs política):**
> el Δ es **MOVERSE PARA DISUADIR**, no repartirse — rapidez media de los ACTIVE en ESCOLTA 3.76→**4.39 m/s**
> (+17%), lobos huyendo por paso (`_wolf_scared` del propio mundo) 1.19→**1.50** (+26%), severidad en esos
> episodios 3.31→**2.90**; el REPARTO entre frentes NO cambia (ambos frentes atendidos a ≤40 m mientras
> sep>60 m: 6.2%→6.5%; dist. al frente peor atendido 118.0→117.3 m). Lectura: la política aprendió EXACTAMENTE
> lo que la habituación v2.4 exigía (el dron parado es un poste; embestir expulsa) y el agujero de la LÍNEA
> ÚNICA queda sin explotar — coherente con run05 (el scriptado converge a la presa común y no ceba → sin
> presión selectiva para partirse; solo el ~41% de los pasos de ESCOLTA tienen dos frentes reales).
> CERTIFICACIÓN anti-proxy del Δ: la disuasión SUBE JUNTO A la bajada de muertes en los mismos episodios
> (defensa real); el patrón proxy habría sido deter↑ con severidad plana. **Artefactos:** /data/drones/run01/
> (model.zip = FINAL, 40 checkpoints, train.log con 80 evals + pacto en cabecera, config/summary,
> eval_model.json, checkpoints/eval_mappo_drones_18998784_steps.json, comportamiento_run01.json,
> comportamiento_stdout.log). **Siguiente (decisión del usuario):** aceptar el FINAL (20M) como coordinador
> MARL v1 / más presupuesto (`--resume`; la curva no estaba plana) / co-evolución lobos-drones / fase YOLO.
>
> **Patch — MARL de DRONES: INFRAESTRUCTURA MAPPO/CTDE residual sobre la barrera, construida y con el SUELO
> verificado (2026-07-18, 2ª — SIN run serio).** Toda la fontanería de la fase de drones, sobre el SB3 PINNEADO
> (SIN dependencias nuevas — sin PettingZoo/BenchMARL: la API multi-agente se reduce al desapilador de abajo).
> **Arquitectura (MAPPO, Yu et al. 2022, con la mecánica de SB3):** actor COMPARTIDO y DESCENTRALIZADO (una red π;
> cada puesto la evalúa con SU obs local) + crítico CENTRALIZADO (CTDE): la obs por agente es COMPUESTA
> [local_i (131) ‖ global privilegiada (122)] y `SplitMlpExtractor` (rl/train_drones.py) enruta — π ve solo la
> mitad local, V la global; en ejecución solo se usa π ⇒ descentralizada de verdad. La global del crítico
> REUTILIZA `rl.obs.build_obs` (122: lobos por verdad-terreno incl. NO detectados — privilegio legítimo del
> entrenamiento centralizado). **AGENTE = PUESTO de barrera** (asiento k=0..3 = k-ésimo dron EN ESTACIÓN,
> ACTIVE∪STRANDED por índice; `seats()`): el puesto persiste aunque el relevo cambie el dron físico — con política
> compartida el intercambio es benigno; esquiva el problema del "agente que se va a cargar a mitad de episodio".
> **Obs local por puesto (`rl/drone_obs.py`, 131, layout con índices en su docstring):** EGO (pos/vel/is_active/
> commandable + el WAYPOINT BASE que la barrera propone — la pista de la intención de la base: la histéresis del
> ancla v2.6 y la fase de patrulla son estado oculto, lección del plan C) · 5 slots de LOBO solo si DETECTADO
> (criterio DRI compartido del mundo, `detected_mask` — la verdad-terreno NO viaja en la local) · vacas · terneros ·
> roster de drones · [reses, reloj, nº detectados]. SIN batería, SIN corzos (su efecto llega vía is_active/
> investigating de los compañeros). **Controlador (`rl/residual_drone_coordinator.py`):** la BARRERA v2.6 VIVE
> DENTRO (ReactiveCoordinator intacto) y la red aprende δ ADITIVA al waypoint por puesto (escala def.
> DETER_RADIUS=20 m, flag), aplicada SOLO a los drones COMANDABLES — **máscara LOAD-BEARING**
> (ACTIVE&~investigating&~relief_hold): el reconocimiento mostró que el mundo solo protege al investigador y al
> relevo (world._apply_drone_actions); un δ sobre un RETURNING lo desviaría y rompería el ciclo de carga. Con
> model=None y sin δ, `act()` DELEGA sin tocar un float = SUELO por construcción. Sin SyncedReactiveCoordinator:
> este coordinador ES a quien llama el arnés (se auto-sincroniza con countdown, frontera de 5 pasos como toda la
> fase RL). **Env (`rl/drone_env.py`):** `DroneTeamEnv` gym.Env CONJUNTO (un mundo, obs/acción de los 4 puestos
> apiladas → SubprocVecEnv(fork) sirve TAL CUAL) + `TeamUnstackVecEnv` (M mundos → 4M streams por-agente para el
> PPO = parameter sharing). Episodios de los TRES tipos (lobos/mixto/corzos ~1/3 — en corzos se aprende a NO
> malgastar), semilla fresca por reset; adversario = ScriptedWolfController v2.6 (default del World).
> **Recompensa (estilo DE-MADDPG, Sheikh & Bölöni 2020 — arXiv:2003.10598, escolta defensiva con recompensa
> individual+equipo; BIBLIOGRAFIA.md ampliada con COMA/difference rewards/VDN/QMIX como DESCARTADAS por
> sobre-ingeniería):** GLOBAL compartida −1×Δ(n_depredadas) + LOCAL por puesto (+local_coef=0.01 por (lobo,paso)
> expulsado atribuido al dron del puesto — `deter_credit`, la regla del mundo (huye del dron ACTIVE acercándose
> más cercano) recomputada determinista del estado expuesto, medio paso después, SIN tocar el mundo). Las DOS
> componentes van POR SEPARADO en info y en train.log (ep_sev / ep_deter) — VIGILANCIA ANTI-PROXY: la vara es la
> severidad del arnés, nunca la recompensa. **Entrenador (`rl/train_drones.py`):** hiperparámetros y receta de la
> fase de lobos (HYPER/NET_ARCH [256,256] importados), init δ≡0 EXACTO verificado por assert + log_std −2, DOS
> FASES (fase 1 solo-crítico con π congelada), TrainLog/LightEval adaptados a SEVERIDAD (MENOS=mejor — ¡signo
> contrario a los lobos!; guardia de EROSIÓN en ABORT_NOTE_DRONES; el pacto del run serio se fijará al lanzarlo).
> Contabilidad: num_timesteps = pasos-AGENTE (mundo ≈ /4). **Evaluador (`rl/drone_eval.py`):** el arnés de siempre
> (`evaluate(coordinator_factory=...)`, 100 semillas, CONFIG_V2) con referencias de los artefactos vigentes.
> **VERIFICADO (contenedor):** SUELO 100 semillas δ=0 → **2.74 / 0.00 / 2.82 con Δ +0.00 EXACTO en los tres
> tipos** (= la barrera bit a bit por el camino residual) · rl_env_check **test 10** NUEVO (a: layout/percepción
> —un lobo NO detectado no viaja—, b: suelo bit a bit episodio completo, c: máscara —δ enorme no desvía a un
> RETURNING ni al investigador—, d: canal de recompensa —Σr_global == −muertes exacto, componentes separadas— +
> atribución dirigida) · verja completa 7/7 verde · smoke MAPPO (init 0 exacto, 2 fases, ~880 fps-agente, fase 1
> clavada en el suelo en la eval ligera). **Decisión de diseño registrada:** la idea de §3.2 ("empezar con
> acciones DISCRETAS para el MARL") queda SUPERADA por la δ continua sobre el waypoint de la barrera — el residual
> necesita corrección fina y el suelo lo garantiza la barrera, no la discretización. PARADO en infra verificada:
> el run serio (pacto de guardias incluido) es el siguiente paso, decisión del usuario.
>
> **Patch — DESENLACE run05: la guardia de ESTANCAMIENTO saltó a 4.2M — el CEBO NO EMERGE con recompensa de equipo
> pura, y el diagnóstico de comportamiento lo confirma con un CERO limpio (2026-07-18).** El run fue impecable
> técnicamente (fase 1 clavada en 2.90 con detalle idéntico ×4 = termómetro del suelo; ~614 fps; shape 0.000 todo el
> run) y la guardia pactada decidió: **12 ligeras de fase 2 entre 2.50 y 3.10 oscilando alrededor del suelo (~2.90),
> media ≈2.92, sin tendencia** → PARADO a 4.227.072 pasos (kill -INT; checkpoints 0.5M–4M en /data/wolves/run05_nivelB).
> **Tablas 100 semillas (arnés v2.6, mismas semillas):** ckpt 4M (último) **2.67±1.47 / 2.71±1.49** → Δ **−0.07/−0.11**
> (erosión leve, patrón run04) · ckpt 3.5M (mejor ligera empatada) **2.80±1.60 / 2.71±1.55** → Δ **+0.06/−0.11** (ruido).
> Suelo 2.74/2.83; scriptado 2.74/2.82. **Δ ≈ +0.0 otra vez.** **La métrica clave — cebo_diag (58 episodios de 2
> subgrupos, ~180-190 muertes):** killer-no-detectado **0.0%** y cebo puro **0.0%** en AMBOS checkpoints — IGUAL que la
> referencia nula del scriptado (0.0%): la política **ni una sola vez** mató desde el frente no visto; no-anclado
> 40.4-40.8% (nula 46.1%: ruido post-fusión, sin cambio real) y la severidad en los episodios de 2 grupos BAJÓ
> (3.33 → 3.09/3.24). δ SÍ cambió el comportamiento (los detalles por semilla difieren del suelo desde 1.25M) pero en
> dirección de ruido/erosión, no de cebo. **Lectura estructural (por qué era esperable a posteriori):** el cebo es una
> desviación COORDINADA y TEMPORALMENTE EXTENDIDA (partir el paquete y SUJETAR un frente cientos de pasos) que el ruido
> gaussiano por-paso (σ≈0.14) alrededor de la trayectoria convergente del script prácticamente nunca muestrea; y el
> paisaje de recompensa tiene un VALLE en medio — un cebo a medias QUITA lobos de la presa (menos quórum → menos
> muertes a corto) antes de dar nada a cambio → el gradiente empuja de vuelta a converger. Recompensa de equipo pura
> = señal correcta pero sin camino. **Siguientes pasos (candidatos, decisión del usuario, NO implementados):** pista
> al cebo (shaping hacia mantener-frentes-separados, con el cuidado anti-proxy de §5.2) · control explícito de
> formación (acción jerárquica: asignación de subgrupos + objetivos, Nivel B avanzado) · co-evolución · o aceptar el
> scriptado como adversario definitivo y arrancar el MARL de drones (batir 2.74/0/2.82). Artefactos: evals y cebo_*.json
> en /data/wolves/run05_nivelB/ y /data/wolves/; el diagnóstico quedó commiteado en `rl/cebo_diag.py` (8f44d0e).
>
> **Patch — run05 NIVEL B: lobos residuales que aprendan el CEBO, recompensa de equipo PURA (2026-07-17, 4ª — LANZADO).**
> La campaña más difícil de la saga (el usuario asume el riesgo): sobre el mundo v2.6 (spawn grouped + barrera con
> percepción realista), entrenar la política RESIDUAL de run04 SIN tocarla (el ScriptedWolfController vive dentro — ya
> caza, ya nace disperso en grouped; la red solo aprende δ, autoridad PLENA `residual_scale`=wolf_speed porque el cebo
> exige desviaciones grandes: QUEDARSE SUJETANDO en vez de converger) con recompensa de EQUIPO PURA: +1 por muerte del
> paquete, compartida; **shaping OFF; SIN término de cebo, SIN pista de "frente ocupado", SIN nada por-lobo** (confirmado
> en config.json). La hipótesis: la barrera v2.6 es UNA línea anclada al lobo detectado → una política que aprenda a NO
> converger (un subgrupo sujeta el frente visto mientras el otro entra por el invisible) supera el 2.74/2.82 del
> scriptado; el cebo debe EMERGER de que eso sube las muertes totales. **Config:** run04 calcado — 2 fases (init δ≡0
> EXACTO verificado; fase 1 = 1M solo-crítico), 12 envs, lr 1e-4, 10M, seed 0, cpu, `/data/wolves/run05_nivelB`.
> **GUARDIAS (cabecera del log, ABORT_NOTE_RESIDUAL actualizado; run04 usó 2.3 sin estancamiento — histórico):**
> (1) SUELO: ligera <2.4 sostenida ≥1M en fase 2 → parar (PPO erosionando al script); (2) ESTANCAMIENTO: a ~4M sin
> superar CON CLARIDAD el suelo (~2.8) → parar — el cebo no emerge con recompensa pura (siguientes pasos —pista al
> cebo / control explícito de formación— los decide el usuario). **Verificación pre-run:** suelo δ≡0 sobre v2.6 grouped
> = **2.74/2.83** (Δ +0.00/+0.01, `/data/wolves/run05_floor_v26.json`) + test 9 (δ=0 ≡ scriptado bit a bit) verde en la
> verja 7/7; smoke residual 2 fases (init 0 exacto, kills 2.77 en el 1er tramo = el script mata desde el paso 0).
> **`rl/cebo_diag.py` NUEVO (diagnóstico de COMPORTAMIENTO — qué aprendió, no solo cuánto):** en los episodios del arnés
> con 2 subgrupos (58/200), por cada muerte: grupo del killer vs grupo del lobo ANCLA de la barrera (métrica (b):
> muertes del subgrupo NO anclado), ¿killer DETECTADO? y ¿el OTRO subgrupo detectado en ese instante? (métrica (a):
> SUJECIÓN — frente visto ocupado mientras mata el no visto; CEBO PURO = killer no visto ∧ otro visto). **Referencia
> NULA (scriptado, --floor): killer-no-detectado 0.0% y cebo puro 0.0%** (el scriptado JAMÁS mata sin estar detectado)
> · no-anclado 46.1% (ruido post-fusión: sep media en muertes 20.9 m — (b) solo discrimina ANTES de fusionar) ·
> situación explotable (un solo grupo visto) el 25.6% de los pasos de ESCOLTA · severidad en episodios de 2 grupos 3.33.
> La firma limpia del cebo emergido = subida de killer-no-detectado/cebo-puro + severidad > suelo. Al terminar:
> eval_wolves 100 semillas (último y mejor) vs 2.74/2.82 + suelo + runs 01–04, y cebo_diag de los checkpoints buenos.
>
> **Patch — v2.9: BARRERA QUE AVANZA + CEBO DISEÑADO en el 2º sector (etapa 1/2) + RE-CONGELACIÓN y medida (2026-07-22,
> 2ª).** Dos arreglos del mundo tras mirar episodios sobre v2.8: la barrera se plantaba PEGADA al rebaño en vez de avanzar
> a espantar, y TODOS los lobos fijaban la misma presa (la protegida) → el 2º frente no servía de nada. **Nota de
> honestidad: el arreglo B PROGRAMA el cebo en el scriptado (diseñado, NO emergente) — esta v2.9 es la PRUEBA DE
> EXISTENCIA (¿rinde el cebo si se ejecuta bien?); el timing NO se fuerza (queda para el RL, etapa 2).**
> **Arreglo A (coordinators.py):** la línea AVANZA hacia el lobo ANCLA — `adv = clip(dist(vacas→ancla) − DETER_RADIUS,
> 12, advance_max)` (se planta DETER_RADIUS por delante del punto de encuentro); tope DERIVADO `advance_max =
> sqrt(r_confirm² − (spacing/2)²) ≈ 36.7 m` — la retaguardia sigue CONFIRMABLE (la barrera honesta no se ciega a sí
> misma: cualquier lobo que alcance las vacas por detrás queda confirmado y la re-planificación por paso lo cubre; a
> 15 vs 4 m/s repliega a tiempo); con el ancla a ≤ 32 m repliega al mínimo v2.8 (12 m, garantía trasera plena).
> **Arreglo B (world.py + wolf_controllers.py):** presa POR SECTOR con spawn grouped de 2 subgrupos (sector = índices del
> spawn v2.5): el 1º mantiene `pack_prey` (maquinaria INTACTA), el 2º fija `pack_prey2` = la res CAZABLE **MÁS LIBRE**
> (máx. distancia al dron ACTIVE más cercano; ternero-primero; capacidad del sector para adultas —quórum local—;
> EXCLUYE la presa del 1º si hay alternativa del mismo tipo —romper la convergencia es el propósito—; sin ACTIVE cae a
> la más cercana; re-fija solo por muerte/refugio, anti-oscilación). Representación LIMPIA: `pack_prey2/pack_prey2_kind`
> nuevos en el World (contrato compartido); el PIN encara AMBAS presas/defensoras; `_process_predation` NO se toca (ya
> era agnóstica: mata cualquier res con quórum); capturas con `is_pack_prey2`; snapshot con `prey2_pos` (el render
> ignora claves nuevas). Controlador: despachador — con 1 grupo el camino v2.8 ÍNTEGRO (bit a bit, face_check 12/12);
> con 2 grupos, `_sector_desired` aplica la MISMA táctica (cono/flanqueo/rodeo/envolvente POR SECTOR; repulsión y
> bordeo de zonas globales). **Verificación:** test 12 (avance al tope 36.7 con ancla lejos; repliegue 17.4 por fórmula
> al apretar; hypot(advance_max, s/2) ≤ r_confirm) · test 13 (existencia micro: presas DISTINTAS por sector y **5
> capturas de la presa del 2º sector por lobos del 2º sector**) · `test_presa_por_sector` en wolf_controller_check
> (regla verificada contra recomputación; 1 grupo → pack_prey2=-1) · test 11 adaptado (el empírico verifica el TEJIDO
> de ranuras; la garantía trasera del modo replegado queda por constantes — la línea puede estar avanzada, test 12 la
> cubre). Verja 7/7 verde. **RE-MEDIDO (100/tipo, metro DGX; 2ª pasada sin deriva): Dummy 3.97/0/3.89 → 3.98/0/3.88**
> (±0.01: el cebo apenas mueve al Dummy — sus drones clavados custodian ≈igual a la "más libre"; solo cambian los
> episodios grouped de 2 subgrupos) · **Reactive 2.56/0/2.26 → 2.46±1.36/0/2.44±1.37 (−0.10/+0.18). ABLACIÓN**
> (/data/wolves/diag/ablacion_v29.*): **cebo SIN avance** (línea fija v2.8 vs lobos v2.9) = **2.58/0/2.36 → efecto PURO
> del cebo diseñado +0.02/+0.10 ≈ RUIDO** (SEM ~0.14); avance a lobos constantes −0.12/+0.08 ≈ ruido. **VEREDICTO
> (honesto, la cifra clave): la prueba de existencia sale NULA EN AGREGADO — el cebo diseñado EJECUTA (micro: el 2º
> sector fija y mata a la presa libre) pero NO sube la severidad.** Mecanismo plausible: al partir el paquete cada
> sector pierde masa (quórum local: una pareja pierde el quórum con UN lobo espantado) y la barrera re-planificada a
> 15 m/s cubre frentes secuenciales casi gratis; además la "más libre" del momento de fijar deja de serlo cuando la
> barrera se recoloca (sin re-evaluación, anti-oscilación). Implicación: la etapa 2 (RL aprendiendo el TIMING del cebo)
> tendría poco premio TAL CUAL contra esta defensa — decisión del usuario. **Nota a batir del MARL de drones →
> 2.46/0/2.44** (run01 sigue histórico).
>
> **Patch — run07: currículo del cebo sobre la BARRERA HONESTA (v2.8) — CERRADO: el cebo NO emerge ni con frente ciego
> REAL (2026-07-22).** Reintento de run06 con el artefacto de percepción eliminado: sobre v2.8 el frente sin confirmar es
> de verdad invisible para la barrera (la hipótesis: el valle sería más somero con un agujero real que explotar). MISMO
> currículo (4 niveles de separación de spawn ×5M = 20M; override solo de entrenamiento; eval SIEMPRE spawn normal),
> residual + recompensa de EQUIPO PURA (shaping off, sin pista), 12 envs, lr 1e-4. **MÉTRICA CORREGIDA** (`rl/cebo_diag.py`,
> commit `124476e` ANTES del run): killer-NO-CONFIRMADO + cebo-confirmado leídos de la MEMORIA DE CONFIRMACIÓN real de la
> barrera (`coordinator.inner._confirmed`, la máscara que decidió los waypoints de ese paso); las métricas por r_detect
> (0% por construcción) se conservan por continuidad. **Paso 0 (medido antes de entrenar):** suelo δ=0 SANO sobre v2.8
> (sev 3.50 en 2 frentes, amurallado 15.3% de lobo-pasos, 0 timeouts, rapidez 2.70 m/s — no zombi); suelo de la EVAL
> LIGERA v2.8 = 2.70 (detalle [2,0,3,3,5,2,3,4,3,2]; guardia recalibrada a <2.4 sostenida = suelo−0.3); **NULA del
> scriptado con la métrica corregida = 0.0%** (la premisa del ~47.6% era "no disuadido" a DETER=20, otra métrica: el
> scriptado converge a la presa común y el matador pasa a ~19-20 m de un dron → confirmado antes de matar) → señal
> límpida; la oportunidad EXISTE (un-solo-grupo-CONFIRMADO el 36.4% de ESCOLTA). **Desenlace:** fase 1 clavada en 2.70
> EXACTO ×3 (detalle idéntico); niveles 1-3 oscilando EN o BAJO el suelo (nunca por encima; picos aislados 2.80/2.70 ≈
> suelo con n=10); éxito parcial del NIVEL 1 NO cumplido (checkpoint 5M: killer-no-confirmado 0.0%, sev 2-grupos 2.65 vs
> suelo 2.86 — ni con el cebo servido a 180°+masa≥2); **GUARDIA DE EROSIÓN DISPARADA a 14.75M** (6 ligeras consecutivas
> <2.4: 1.90/1.80/1.80/1.70/2.00/2.00 = 1.5M sostenidos). **Incidencia operativa (honestidad del registro):** la orden de
> parada NO surtió efecto — los runs desacoplados (`docker exec -d bash -c "nohup … &"`) arrancan como job asíncrono de
> bash no interactivo → heredan SIGINT IGNORADO → Python nunca instala KeyboardInterrupt → `pkill -INT` fue un no-op (y
> el envoltorio bash del kill se auto-mató por contener el patrón → el ps salió vacío y pareció muerto); LECCIÓN: parar
> guardias con **SIGTERM** directo (`docker exec <cont> pkill -TERM -f …`, sin bash -c) y verificar con pgrep + log
> congelado. El run completó los 20M por su cuenta: el nivel 4 (spawn normal) quedó clavado en 1.6-2.3 — registro extra
> que CONFIRMA el veredicto de la guardia. **Tablas 100 semillas (arnés v2.8, vs scriptado 2.56/2.26): FINAL (20M)
> 1.93±1.13/1.87±1.03 → Δ −0.63/−0.39 (bajo el suelo = erosión) · mejor por ligeras (7.5M, pico 2.80) 2.25±1.34/2.21±1.34
> → Δ −0.31/−0.05 (≈suelo). `cebo_diag` corregido en TODOS los checkpoints (5M/7.5M/10M/20M): killer-NO-CONFIRMADO 0.0%
> y cebo-confirmado 0.0%** — ni una muerte de un lobo invisible para la barrera honesta (el final mata algo más separado
> —sep 34.5 m vs 17.5 nula— y más del no-anclado —47.3% vs 34.3%— pero SIEMPRE confirmado: reparto/ruido, no ocultación).
> **Veredicto: tercera confirmación (run05 recompensa pura · run06 currículo+oráculo · run07 currículo+frente ciego
> real) — el cuello es la EXPLORACIÓN (el cebo = desviación coordinada temporalmente extendida con valle de recompensa;
> la exploración gaussiana por-paso no la muestrea), NO la geometría del mundo. El currículo de separación de spawn queda
> AGOTADO como vía. Reservas (BIBLIOGRAFIA, NO implementadas — decisión del usuario): curiosidad coordinada
> (EMC/MACE/SMMAE/JIM) → control jerárquico de formación → co-evolución con el MARL sobre "confirmado pero no disuadido"
> (el hueco real: ~50% de muertes sin dron a ≤DETER_RADIUS).** Artefactos: /data/wolves/run07_curric_v28/ (checkpoints,
> train.log, eval_final_20M/eval_best_7p5M.json) + /data/wolves/run07_cebo_*.json + diag/run07_paso0.py.
>
> **Patch — v2.8: BARRERA HONESTA (reacciona SOLO a lobos confirmados con memoria) + standoff derivado + RE-CONGELACIÓN
> y medida (2026-07-21).** Corrección de una TRAMPA de realismo detectada por el diagnóstico del cebo (solo-lectura,
> post-run06): el marco DRI del mundo distingue `r_detect`=100 ("hay un CONTACTO" — bulto sin clasificar, podría ser un
> corzo) de `r_confirm`=40 ("es un LOBO", oráculo stand-in de YOLO), pero la barrera del ReactiveCoordinator (v2.6)
> reaccionaba a los lobos a `r_detect` sabiendo su TIPO por verdad-terreno (`_detected` filtraba `w.wolves` a 100 m; los
> corzos jamás entraban) → formaba barrera contra bultos sin clasificar → NO dejaba frente ciego. Además el mundo solo
> confirma UNA vez por episodio (`_update_phase` retorna con ESCOLTA latcheada): el único lobo jamás confirmado por el
> oráculo era el primero. **Cambio (SOLO `coordinators.py`; world.py INTACTO ≡ v2.7):** (1) `_confirmed_wolves()`
> sustituye a `_detected()` — un lobo queda **CONFIRMADO** en cuanto está a ≤ `r_confirm` de algún dron ACTIVE
> (confirmación de EQUIPO) y **se recuerda el resto del episodio** (latch `|=`, memoria/tracking; sin drones en vuelo no
> se olvida — conocimiento de flota, no línea de vista; reset solo ante episodio nuevo); la barrera/ancla/PENETRADO
> operan SOLO sobre confirmados; un contacto NUNCA confirmado NO existe para la barrera (aunque esté a ≤ `r_detect`) —
> el reflejo de investigación del mundo (que SÍ es DRI en dos etapas) se ocupa de él. Modelado como oráculo determinista;
> la fase de percepción lo sustituirá por YOLO+tracking con la MISMA interfaz de decisión (máscara por lobo). La máquina
> de fases del mundo NO cambia (ESCOLTA ya disparaba por confirmación a `r_confirm`; los contactos sin confirmar solo
> mantienen SOSPECHA). (2) **STANDOFF DERIVADO** (los GIFs mostraban la línea lejos y lobos colándose): la barrera se
> coloca de modo que el punto PEOR de la línea de vacas frontales (a mitad lateral entre dos drones adyacentes) quede a
> ≤ `DETER_RADIUS` del dron más cercano: `standoff = sqrt(DETER_RADIUS² − (spacing/2)²) = sqrt(20² − 16²) = 12 m`
> (antes 20 = R → peor punto a sqrt(20²+16²) = 25.6 m FUERA de disuasión — coherente con el diagnóstico: ~50% de las
> muertes sin dron a tiro). **Verificación:** reactive_check test 10 REHECHO (dirigido A: contacto a 57 m —dentro de
> r_detect, fuera de r_confirm— NO dispara barrera → patrulla; cruza los 40 m → confirmado → barrera err 1.2°; se aleja
> a 249 m > r_detect → SIGUE confirmado, la barrera lo rastrea; dirigido B: frente contacto-sin-confirmar movido →
> waypoints IDÉNTICOS, eje al confirmado 7.6° vs media global 102.9° — el FRENTE CIEGO existe) + test 11 NUEVO
> (standoff: peor hueco real medido 20.0 ≤ DETER_RADIUS) + umbral de test_reactivo recalibrado 5→3 m (el desplazamiento
> del centro escala con el standoff 12/20; misma propiedad). Verja 7/7 verde en el contenedor; face_check bit a bit (la
> barrera no interviene en combate puro). **RE-MEDIDO (metro DGX, 100/tipo): Dummy 3.97/0/3.89 BIT A BIT ≡ v2.7 (sin
> deriva; no usa la barrera y la física no se tocó) · Reactive 2.30/0/2.42 → 2.56±1.55/0/2.26±1.32** (n_safe 4.33/4.61;
> succ/pred/to 4/89/7 y 4/87/9). Dos fuerzas CONTRARIAS que casi se cancelan: la honestidad ENCARECE (reacciona al
> confirmar, no al contacto → solo-lobos +0.26, ~1.7 SEM) y el standoff pegado ABARATA (mixto −0.16, ~1.2 SEM); margen
> vs Dummy −1.41/−1.63 (v2.7: −1.67/−1.47). Es MEDIDA, no objetivo (sin tunear). **INVALIDA la nota a batir del MARL de
> drones** (2.30/0/2.42 era contra la barrera-oráculo v2.7): el MARL se reentrenará sobre v2.8 con nota a batir
> **2.56/0/2.26**; run01 de drones sigue histórico (v2.6). Consecuencia de diseño: el frente ciego (contacto sin
> confirmar) EXISTE por fin — el cebo del Nivel B deja de ser geométricamente imposible por percepción-oráculo.
> **Fix colateral destapado por v2.8 (`rl/residual_wolf_controller.py`):** el test 9 (residual δ=0 ≡ scriptado BIT A
> BIT) saltó en rojo con la barrera nueva — causa raíz: con δ≡0 el `decide()` residual seguía RENORMALIZANDO
> `v_script` (clip a `wolf_speed`), que NO es un no-op numérico cuando la normalización del propio script deja la
> norma 1 ulp por encima (p.ej. `4.000000000000001`; el mundo integra la salida del scriptado SIN recorte): diferencia
> ~9e-16 en el paso 23 amplificada por el caos hasta divergir de forma visible en el paso ~479. Bug LATENTE
> pre-existente (las trayectorias v2.6/v2.7 del seed del test no lo pisaban); arreglo mínimo = con δ≡0 PASS-THROUGH
> EXACTO (sin suma ni clip), con δ≠0 el cap sigue intacto (la semántica de entrenamiento no cambia). El residual de
> DRONES ya lo hacía bien (`_delta_active`: delegación pura sin tocar un float). rl_env_check 10/10 verde tras el fix.
>
> **Patch — v2.7: SUSTO DE DOS RADIOS (el dron quieto también repele) + RE-CONGELACIÓN y medida (2026-07-19).** Cambio de
> FÍSICA del susto (prompt del usuario), anclado en datos reales: los lobos ATRAVESABAN la barrera porque el susto era SOLO por
> movimiento (v2.4) — un dron quieto era un poste que se bordea → el CEBO nunca tuvo presión selectiva (no hay que engañar una
> barrera atravesable). Datos de fuga (FID): ante una amenaza que se acerca, huida media ~106 m (rango 17–310); + habituación a
> disuasores estáticos (el susto por movimiento era realista). Modelo fiel = **DOS radios**: disuasión fuerte al acercarse
> (grande, el actual) + zona de incomodidad mínima que no se cruza ni con el dron quieto (pequeña, escalada al campo 300×300 —
> un radio real de ~100 m haría a los drones invencibles). **Implementación (SOLO la física del susto, `_apply_deterrence`):**
> se MANTIENE la expulsión por movimiento (dron ACTIVE acercándose > `SCARE_APPROACH_MIN` dentro de `DETER_RADIUS`=20 → huida
> plena) y se AÑADE `STATIC_DETER_RADIUS`=10 m (la mitad): un lobo NO expulsado a ≤ ese radio de un dron ACTIVE (aunque QUIETO o
> alejándose) recibe una PARED BLANDA — se le quita la componente de velocidad hacia el dron (desliza) + empuje radial saliente
> de frenado (`STATIC_DETER_GAIN`=0.6, acotado a la rapidez de caza → frena/desvía, MÁS DÉBIL que la huida) → NO cruza; marca
> `_wolf_walled` → NO mata a través (excluido de `_process_predation`, como `_wolf_scared`). **Jerarquía:** dentro del radio
> pequeño → pared siempre; si además se acerca (radio grande) → EXPULSIÓN domina → moverse es ESTRICTAMENTE mejor (radio mayor +
> más fuerza), preserva el incentivo que el MARL run01 aprendió. Un poste a > `STATIC_DETER_RADIUS` no tiene efecto (habituación
> a distancia; un poste LATERAL se rodea). Solo ACTIVE; gateado por `escort_enabled` (combate puro → `_wolf_scared`/`_wolf_walled`
> todo False → **face_check bit a bit**, fingerprint v2.3≡v2.4≡v2.7). **NO se tocó:** caza (cono/flanqueo/envolvente/matanza
> excedente), huida de vacas, madre-ternero, batería/relevo, detección, spawn grouped v2.5, barrera v2.6, coordinadores,
> controladores de lobos, el nº de drones (4+4; el barrido 3+3 es prompt posterior), el andamiaje RL. **Verificación:**
> `test_pared_estatica` dirigido NUEVO en escort_check (A: dron QUIETO cubriendo la presa a ≤10 m BLOQUEA la matanza —None— vs
> SIN dron/LEJANO 14 m/FUERA 26 m que matan en 20 pasos = pared + habituación a distancia; B: la EMBESTIDA expulsa al lobo a
> 44 m vs la pared que lo frena a 20 m → mover > quieto) + `test_susto` (A) adaptado (dron cubriendo → HELD FUERA, `_wolf_walled`,
> NO scared) + `test_pin_envolvente`/`test_disuasion` (comentarios al modelo de dos radios; un poste a 14/12 m sigue fuera de la
> pared → mata/rodea igual). **RE-MEDIDO (100/tipo, metro DGX, contenedor):** Dummy 4.42/0/4.34 → **3.97/0/3.89** (Δ −0.45/−0.45:
> los drones CLAVADOS del Dummy ya repelen a corta —la pared no exige moverse—; n_safe 2.73/2.81) · Reactive 2.74/0/2.82 →
> **2.30/0/2.42** (Δ −0.44/−0.40: la barrera se hace pared, defiende mejor; n_safe 4.57/4.45; el margen Reactive−Dummy se mantiene
> −1.67/−1.47). Es MEDIDA, no objetivo. `REFERENCE_SEVERITY`/`FROZEN_TAG`/asserts de tag (wolf_controller_check/rl_env_check) → v2.7;
> artefactos regenerados (`baseline_v2.json`/`.csv`, `baseline_v2_reactive.json`/`.csv`). **INVALIDA la baseline del MARL de drones
> run01** (medido sobre v2.6, barrera atravesable): run01 = histórico; el MARL se reentrenará sobre v2.7 (nota a batir 2.30/0/2.42)
> — NO reentrenado aquí. BIBLIOGRAFIA +entrada FID/dos-radios. verja 7/7 verde en el contenedor.
>
> **Patch — v2.6: BARRERA REACTIVA CON PERCEPCIÓN REALISTA + RE-CONGELACIÓN y medida (2026-07-17, 3ª).** Corrección de
> REALISMO del coordinador clásico (prompt del usuario), motivada por el reconocimiento de solo-lectura previo (¿engaña el
> cebo a la barrera?): la barrera usaba `pack_c = wolves.mean()` — información de ORÁCULO (lobos que ningún dron había
> visto entraban en la media; con dos frentes, el no visto orientaba la colocación). **Regla nueva (SOLO
> `coordinators.py`; el mundo NO se toca):** DETECTADO = lobo a ≤ `r_detect` de un dron EN VUELO (ACTIVE) — el MISMO
> criterio DRI del disparador (`_update_phase`/`_pick_investigator`), recomputado en solo-lectura cada paso; el EJE se
> ancla al lobo ANCLA = el PRIMER detectado (memoria de primera detección en el coordinador; desempate índice menor) con
> HISTÉRESIS (mientras siga detectado se mantiene; al perderse pasa al siguiente más antiguo); PENETRADO y la cobertura
> lobo-a-lobo operan SOLO sobre detectados (sin esto el frente no visto seguiría atrayendo drones por la puerta de
> atrás); en ESCOLTA sin NINGÚN detectado → PATRULLA hasta re-detectar. Fórmulas intactas (standoff / ranuras / reparto /
> patrulla): solo cambia A QUÉ lobos mira. **Verificación:** `test_percepcion` NUEVO (nº 10 de reactive_check): con el
> ancla visible y el resto tele-transportado fuera de detección, mover el frente NO visto deja los waypoints IDÉNTICOS
> (antes cambiaban vía la media); eje |vs ancla|=3.7° frente a |vs media global|=61.5°; sin detectados → anillo de
> patrulla; re-detección → barrera de nuevo. Tests 1–9 SIN cambios de aserción (con un solo frente clustered el paquete
> entero está detectado en ESCOLTA y la barrera ≈ la de antes); verja completa 7/7 verde dentro del contenedor.
> **RE-MEDIDO (100/tipo, contenedor, 2ª pasada bit a bit — md5 idénticos):** Dummy **4.42/0/4.34** BIT A BIT ≡ v2.5 (no
> usa la barrera; física idéntica; REFERENCE_SEVERITY sin cambio) · Reactive **2.74±1.47 / 0 / 2.82±1.49** (v2.5
> omnisciente: 2.71/0/2.76 → **+0.03/+0.06, DENTRO del ruido**, ~0.4 SEM). **Lectura:** quitar la omnisciencia apenas
> cuesta contra el scriptado CONVERGENTE — todos sus lobos van a la presa común y los que amenazan están casi siempre a
> ≤ 100 m de algún dron (detectados): la media global ≈ la percepción local. Lo que cambia DE VERDAD es el caso de DOS
> FRENTES: el no visto ya NO influye en la colocación → el CEBO del Nivel B pasa a ser FÍSICAMENTE real (mantener un
> frente a la vista mientras el otro entra sin ser visto), no un artefacto de la media. Artefactos regenerados
> (frozen_tag v2.6), `FROZEN_TAG` + asserts de tag (wolf_controller_check / rl_env_check) → v2.6. **El MARL pasa a batir
> 2.74/0/2.82.** PARADO tras congelar, como pactó el prompt (sin re-correr la campaña de lobos).
>
> **Patch — v2.5: SPAWN DE LOBOS EN SUBGRUPOS (Nivel A) + RE-CONGELACIÓN y medida (2026-07-17, 2ª).** Cambio de MUNDO
> (hipótesis del usuario: el paquete apilado deja que la barrera defienda UN solo frente; con subgrupos, un grupo
> puede cebar mientras otro mata por otro lado). **Nivel A = el MUNDO sortea la formación** (el RL la explotará en una
> fase posterior). **Implementación (`world.py`, solo el spawn):** `wolf_spawn_mode="clustered"|"grouped"` (default
> World = clustered ≡ v2.4.1 BIT A BIT — face/battery/escort/drone intactos; `CONFIG_V2` y `main.py` piden grouped);
> en grouped, tras el spawn clustered de siempre, `_split_wolves_groups` decide con el substream `_wolf_group_rng`
> (seed+3_000_003, como distracción/batería): n<=2 lobos → SIEMPRE 1 grupo; n>2 → 1 ó 2 al 50/50; con 1 grupo NO se
> toca nada (posiciones clustered EXACTAS); con 2, tamaño del 2º grupo k~uniforme{1..n−1} (DESIGUAL permitido; k=1 =
> CEBO) sobre los k últimos índices, sector 2º a >=`WOLF_GROUP_MIN_ANGLE_SEP`=60° (uniforme en el arco restante) y
> ancla proyectada al MISMO borde que el 1º (misma distancia de spawn: cambia el eje de llegada, no cuándo), mismo
> cúmulo gaussiano. Instrumentación: `wolf_group_sizes`/`wolf_spawn_angles`. **Verificado (diagnóstico en
> /data/wolves/diag/v25_spawn_diag.py):** determinismo (misma seed → misma formación) · substream (20 semillas × 3
> tipos: vacas/drones/corzos/terneros/baterías BIT A BIT vs clustered; 34 episodios con 1 grupo ≡ clustered también
> en lobos) · geometría (58 episodios con 2 grupos: sep >=60°, ancla en el borde, cúmulos separados) · distribución
> (200 semillas: 58/114 elegibles parten en 2 ≈ 50/50; repartos variados incl. cebo 1+4/4+1) · render
> `v25_spawn_grouped.gif` (seed 26: cebo al este + paquete de 3 al oeste) · fidelidad `CONFIG_V2 ≡ defaults + corzos
> + grouped` OK. **RE-MEDICIÓN (100 semillas/tipo, dentro del contenedor) — la hipótesis NO se confirma en Nivel A:**
> Dummy solo-lobos **4.42**±2.24 / corzos 0.00 / mixto **4.34**±2.27 (v2.4.1: 4.54/0/4.46 → −0.12/−0.12) · Reactive
> **2.71**±1.42 / 0 / **2.76**±1.52 (v2.4.1: 2.77/0/2.80 → −0.06/−0.04); n_safe Dummy 2.37/2.49, Reactive 4.18/4.11.
> Todo ~1 SEM: **el multi-frente por sí solo NO ayuda al scriptado** — su táctica fija UNA presa común (el 2º grupo
> no ceba: converge a la misma presa desde otro eje, a veces llega tarde al quórum). La bajada leve es coherente:
> paquete partido = flanqueo inicial más débil. **Es medida, no objetivo** — números reportados tal cual, sin tunear.
> La puerta queda ABIERTA para el Nivel B (lobos RL que EXPLOTEN el multi-frente: cebo deliberado). RE-CONGELADO
> tag `v2.5-baseline`; `REFERENCE_SEVERITY`/`FROZEN_TAG` actualizados; artefactos regenerados (2ª pasada
> REPRODUCIDA exacta); asserts de tag de wolf_controller_check/rl_env_check → v2.5. **El objetivo del MARL pasa a
> 2.71 / 0 / 2.76.** PARADO aquí (sin re-correr la campaña de lobos), como pactó el prompt.
>
> **Patch — DESENLACE run04: el andamiaje RPL perfecto, el Δ ≈ +0.0 — el scriptado ya está en el techo explotable
> contra esta barrera (2026-07-17).** run04 (residual, rala pura, 2 fases, 10M, ~4,3 h a ~650 fps) completó limpio.
> **El andamiaje funcionó exactamente como se diseñó:** init δ≡0 verificado; FASE 1 con las 4 evals ligeras CLAVADAS
> en 2.90 con detalle por semilla IDÉNTICO (el termómetro del suelo); FASE 2 sin desplome (rango 2.60–3.20; la guardia
> de 2.3 jamás se acercó); buffer estocástico ~2.0–2.4 todo el run (σ≈0.14 cuesta ~0.5 vs el determinista — esperado).
> **Tablas de 100 semillas (modo residual):** MEJOR por evals ligeras (ckpt 1,5M; su 3.20 en n=10): **2.82±1.49 /
> 2.81±1.43** → **Δ sobre el scriptado +0.05/+0.01** (≈ el suelo medido 2.78/2.81; DENTRO del ruido, SEM≈0.14) ·
> FINAL (10M): **2.61±1.36 / 2.66±1.44** → **Δ −0.16/−0.14** (erosión LEVE de sobreentrenamiento — ~1 SEM, nunca
> catastrófica: la guardia hizo su trabajo de no saltar). Los picos 3.10–3.20 de la eval ligera NO generalizaron a la
> muestra oficial (ruido de n=10). **Lectura (la cifra se reporta aunque sea +0.0, como se pactó):** con autoridad
> plena sobre δ, 10M de pasos y el suelo garantizado, PPO no encontró adaptación anti-dron que generalice → contra
> ESTA barrera reactiva, la táctica scriptada (pin-and-flank + envolvente) ya extrae ≈ todo lo extraíble; el margen
> del lado del lobo parece estar en co-evolución (cuando el adversario también aprenda), no en más RL unilateral.
> **CIERRE de la fase de lobos aprendidos (4 runs medidos):** rala 0 → shaping 0.57/0.60 → cuna+shaping 0.65/0.72 →
> residual ≈ suelo (2.82/2.81 mejor). El SCRIPTADO queda como el lobo canónico contra la barrera; los artefactos de
> los 4 runs en /data/wolves/run01..run04 (checkpoints + evals JSON). Siguiente movimiento = decisión del usuario.
>
> **Patch — run04: POLÍTICA RESIDUAL sobre el scriptado (RPL) + BIBLIOGRAFIA.md (2026-07-16, 2ª).** Cambio de enfoque
> (decisión del usuario, respaldado por Silver et al. 2018 — Residual Policy Learning, arXiv:1812.06298): la red ya no
> aprende la caza, la CORRIGE. **`rl/residual_wolf_controller.py`:** `ResidualWolfController` lleva DENTRO una
> instancia real de `ScriptedWolfController` que decide cada paso de física con TODA su lógica (SU fijación de presa —
> escribe pack_prey como siempre, nada del contrato RL aquí—, su histéresis, su coasting); la red aporta δ (por lobo,
> 2D) cada 5 pasos (misma sincronía de fronteras que el env/PolicyWolfController, vía SyncedReactiveCoordinator en
> evaluación) y `v_final = clip_norma(v_script + δ, wolf_speed)`; en coasting δ NO se aplica (pass-through, como el
> susto). **Entrada de la red (obs residual, 132)** = las 122 (obs.py INTACTO) + la acción del script normalizada
> (÷wolf_speed): la histéresis del script es estado oculto (la lección del plan C) — darle a la red lo que el script
> QUIERE hacer es la pista mínima para corregirlo con sentido; la pista es el último v_target del script (llamar a
> decide() fuera de turno duplicaría sus efectos laterales), 0 en la primera frontera. **Env residual**
> (`WolfPackEnv(residual=True, residual_scale=)`, def. wolf_speed — autoridad plena): acción = δ normalizado, obs =
> 132, recompensa RALA PURA (con el script dentro ya hay ~2.4–2.6 muertes/ep de señal en el buffer — medido en el
> smoke; shaping off). **Entrenador en dos fases** (truco del Real Robot Challenge, arXiv:2101.02842):
> `--residual --phase1-steps` — init CRÍTICO verificado (última capa de la media a CERO ⇒ δ≡0 EXACTO comprobado con
> assert sobre obs aleatorias; log_std=−2.0 ⇒ σ≈0.14), FASE 1 solo-crítico (π y log_std con requires_grad=False; el
> crítico aprende cuánto vale el script), FASE 2 PPO normal (descongela, lr 1e-4, resto como run03); transición
> marcada en el log; evals ligeras deterministas cada 250k DESDE la fase 1 (δ=0 ⇒ deben CLAVARSE en el suelo ~2.7 —
> el termómetro del warm-up). **Verificaciones ANTES del run:** `rl_env_check` **test 9** (δ=0 ⇒ episodio COMPLETO
> BIT A BIT igual al scriptado puro contra la barrera, presa incluida — 1.023 pasos; δ desbocado ⇒ ‖v‖ ≤ wolf_speed
> intención y efectiva; coasting pass-through; obs 132 con pista 0 en t=0 y viva después) + **suelo en el arnés**
> (`eval_wolves --floor`: δ≡0 sobre las 100 semillas ≈ 2.77/2.80 — reportado en el hilo del run) + smoke residual
> (init verificado, dos fases giran, kills ~2.4 desde el primer rollout). **Guardia del suelo (criterio de aborto,
> cabecera del log):** si en la FASE 2 la eval ligera cae por debajo de 2.3 (suelo − margen) sostenido ≥1M → PARAR
> (PPO estaría erosionando al script; palancas —bajar lr, alargar fase 1— decisión del usuario). **La cifra que
> importa al final: Δ sobre el scriptado** (todo lo que suba de 2.77/2.80 es adaptación anti-dron descubierta por
> RL; se reporta aunque sea +0.0). **BIBLIOGRAFIA.md NUEVO en el repo** (junto a DISEÑO.md): RPL, RRC-2fases,
> JSRL (descartada), residual↔KL, Ng et al., PPO, SB3, Gymnasium + consolidación de las referencias de la fase de
> mundo de §12 (URLs pendientes de verificación donde no constaban) + regla: todo paper entra ahí ANTES de
> implementarse.
>
> **Patch — DESENLACE run03: 10M completos, la CUNA APORTA (0.65/0.72 vs run02 0.57/0.60), el scriptado sigue lejos
> (2026-07-16).** run03 (PPO desde el clon v3, shaping ON β=1, lr 1e-4, π [256,256], 12 envs CPU, ~4,6 h a ~615–810
> fps) completó los 10M SIN disparar el criterio: la eval ligera arrancó en 0.10–0.20 (= el nivel del clon → prueba de
> que los pesos de π cargaron; value fresco) y subió 0.30 (1M) → 0.70 (3,25M, ≫ el umbral ~0.2) → pico 0.80 (4M y
> 8,5M) → 0.60 al cierre; ep_kills_mean del buffer 0.42 (1M) → 0.45–0.48 (final) — nótese que a 900k ya estaba al
> nivel FINAL de run02 (el prior del viaje paga desde el arranque). **Tablas de 100 semillas (eval_wolves, mismas
> semillas):** FINAL (10M) solo-lobos **0.65±0.68** / mixto **0.72±0.85** (succ 8/8, pred 54/51, timeout 38/41;
> n_safe 5.43/5.34) · MEJOR por evals ligeras (ckpt 4M, vecindario 0.70/0.80/0.60) **0.66±0.79 / 0.71±0.85**
> (succ 21/19) — otra vez ROBUSTO al checkpoint. **Contra las cuatro referencias: scriptado 2.77/2.80 · cuna 0.2 ·
> run02 0.57/0.60 · techo de la etiqueta 2.60.** Lecturas: (1) **la cuna aporta** — run02 y run03 son idénticos salvo
> el init (+0.08 lobos / +0.12 mixto, y en el buffer 0.45–0.48 vs 0.35–0.40); (2) **la maniobra sigue siendo el
> muro** — ni la imitación la representa (el clon la falla y el techo 2.60 queda inalcanzado) ni 10M de PPO con
> shaping de distancia la descubren (el Φ actual premia ACERCARSE, no FLANQUEAR); (3) el margen hasta 2.77 no se
> cierra con esta receta — candidatos si se sigue por lobos: más presupuesto sobre run03 (--resume), Φ de flanqueo
> (con el principio nº1 de §5.2 en mente: cuidado con recompensar proxies), DAgger, o aceptar 0.65/0.72 como lobos
> aprendidos v1 y avanzar al MARL (el adversario de los drones puede ser el scriptado congelado, que ya es más duro).
> Artefactos: /data/wolves/run03/ (train.log, checkpoints 500k–10M, eval_final_10M.json, eval_best_4M.json).
> Contenedor abajo al cierre; decisión del siguiente movimiento = usuario.
>
> **Patch — DECISIÓN (C): run03 = PPO desde el clon v3, con shaping (2026-07-15, 5ª).** El usuario elige la vía C con un
> cambio razonado sobre el diseño original de run03 (que era shaping off): **--shaping on (β=1, γ=0.999, como run02)**.
> Razonamiento: (1) la cuna REAL rinde 0.2 — no da la recompensa densa que el diseño original suponía (un clon ≥1.5
> sí la daría); (2) el shaping por potencial es INVARIANTE a la política óptima (Ng et al., ya verificado en test 8) →
> red de seguridad gratuita en el bache del warm-start (crítico fresco); (3) comparabilidad: run02 (shaping, DESDE CERO)
> vs run03 (shaping, DESDE EL CLON) deja el valor de la cuna como ÚNICA diferencia. Config: `--init-from
> /data/wolves/demos/bc_model.zip --shaping on --lr 1e-4 --total-steps 10000000 --seed 0 --device cpu --outdir
> /data/wolves/run03` (π [256,256]; resto de hiperparámetros = run02), protocolo desacoplado de siempre. **Criterio de
> aborto adaptado a esta cuna (en la cabecera del train.log, `--abort-ref 0.2`):** si a ~3M ni ep_kills_mean ni las
> evals ligeras superan CON CLARIDAD el nivel del clon (~0.2) → PARAR y reportar — estancamiento y colapso cubiertos
> por el mismo umbral. Monitorización inicial: la eval ligera del arranque debe salir ~0.2 (prueba de que los pesos de
> π cargaron; el value nace fresco). Al terminar: tablas de 100 semillas (último + mejor por evals ligeras) contra las
> CUATRO referencias — scriptado 2.77/2.80 · cuna 0.2 · run02 0.57/0.60 · techo de la etiqueta 2.60.
>
> **Patch — Opción A′ ejecutada: etiqueta MEDIA (dataset v3) + TECHO medido 2.60; el clon sigue ≈0 → el cuello es la RED, no la etiqueta (2026-07-15, 4ª).**
> Decisión del usuario: re-etiquetar con la MEDIA de los 5 v_target de la ventana (la intención NETA que el hold
> ejecuta; anti-aliasing) + medir el techo de la etiqueta nueva + árbol escalonado. **(1) `collect_demos --label
> mean|first`** (default mean = v3; first reproduce v1/v2): mismos episodios BIT A BIT (mismas semillas 10.000+,
> 120.214 pares/150 eps, experto 2.59) — solo cambia la etiqueta. **(2) TECHO medido — held-mean-label EN VIVO
> (oráculo, script en /data/wolves/diag/techo_mean_label.py):** en cada frontera se hace deepcopy((mundo,
> coordinador)), se rueda la copia 5 pasos con el experto de las demos para leer sus v_target, y su MEDIA se ejecuta
> MANTENIDA en el mundo real vía RLWolfController (la semántica de servicio exacta del clon) = un clon PERFECTO de la
> etiqueta mean → **2.60 en las 10 semillas** (≈ el experto 2.5–2.7): **la etiqueta queda EXONERADA**. **(3) BC
> [256,256] sobre v3: clon 0.2/10** ([0,0,0,0,0,1,0,1,0,0]) → **rama ≈0 del árbol: run03 NO lanzado**. **(4) La
> estratificación por régimen CIERRA el diagnóstico** (val de v3, solo slots presentes): VIAJE (|exp|>0.7, 60% del
> dataset) cos 0.83 y módulos 0.87 vs 0.99 — por eso el clon cruza la barrera y llega a la presa; MIXTA (0.3–0.7,
> 21%) cos 0.65; **MANIOBRA (|exp|<0.3, 19%) cos 0.26 con 37% de direcciones OPUESTAS** — la danza fina del flanqueo
> (la que dispara el quórum) sigue sin ser representable por la MLP sobre la obs congelada (posiciones absolutas
> relativas al establo: la maniobra depende de geometría RELATIVA lobo–presa–manada que la red debe sintetizar).
> Secuencia completa del descarte: pipeline ✓ (scriptado por el mismo camino 2.5–2.7) → presa del contrato ✓ →
> capacidad ([256,256]) ✗ no era → etiqueta (aliasing 31%, media de ventana, techo 2.60) ✓ arreglada → **queda la
> RED/REPRESENTACIÓN**. **Candidatos (decisión del usuario, nada implementado):** **(C) run03 desde el clon v3** —
> LA RECOMENDACIÓN: el prior ya resuelve el viaje (la exploración global que mató a run01) y hasta araña muertes
> (0.2); la maniobra se aprende mejor de la señal de muerte (RL) que por imitación; todo listo (--init-from,
> aborto por colapso) · pesos por régimen o π más ancha en el BC (seguir empujando la imitación; rendimientos
> decrecientes a la vista) · DAgger (marginal: el fallo es de ajuste, no de drift) · tocar la obs = descartado por
> contrato.
>
> **Patch — Opción A ejecutada (π [256,256]) y NUEVO diagnóstico: ALIASING de la etiqueta (2026-07-15, 3ª).** Decisión
> del usuario: re-entrenar el BC con política [256,256] (NET_ARCH de train_wolves cambia [128,128]→[256,256] — π del BC
> y del fine-tune deben coincidir para --init-from; **la ablación run02 pasa a ser CROSS-ARQUITECTURA**, conscientemente,
> porque la [128,128] infraajustaba lo medido) y árbol escalonado sobre el clon nuevo: ≥1.5 → run03 · 0.5–1.5 con bucle
> cerrado sano → run03 con puerta RELAJADA anotada · ≈0 → PARAR. **Resultado: rama ≈0** — val dir 0.424→0.406 (mejora
> marginal pese a 4× parámetros) y clon 0.0/10 → doblar la anchura NO era la palanca; la eval de 100 semillas se omitió
> (10/10 a cero la hace redundante). **HALLAZGO (medido sobre las 244.681 parejas de etiquetas consecutivas del
> dataset):** el **31,4% invierten el sentido entre fronteras** (cos<0 a 0,5 s; mediana 0.995 → distribución BIMODAL:
> o estable o flip) — el v_target del scriptado oscila (acercar/retirar/tangente alrededor de r_face_safe + cono +
> re-anclaje del envolvente) MÁS RÁPIDO de lo que muestrea la frontera del env → la etiqueta de PRIMER PASO es
> cuasi-ruido en ~⅓ del dataset para una política sin memoria. Encaja todo: train≈val alto e insensible a la capacidad,
> módulos encogidos (la media de direcciones que flipean ≈ 0), el clon llega y MERODEA pero no ejecuta la danza, y el
> "held scripted" sí mata 2.7 (evalúa la superficie exacta EN VIVO en vez de predecirla). **Candidatos para la próxima
> decisión (sin implementar):** (A′) etiqueta = MEDIA de los 5 v_target de la ventana (la intención NETA que el hold
> ejecuta de verdad; suaviza el flip; sigue siendo clonar al scriptado — un flag en collect_demos) · (C) run03 desde el
> clon actual (la exploración global —cruzar la barrera, llegar a la presa— YA está resuelta por el prior; PPO solo debe
> descubrir la maniobra final) · (B) DAgger (menos indicado: el problema es el OBJETIVO, no solo el drift) · memoria en
> la política (LSTM/frame-stack) descartada por contrato (obs congelada).
>
> **Patch — PLAN B ACTIVADO: SHAPING POR POTENCIAL + run02 de cero (decisión del usuario, 2026-07-15).** run01 demostró
> que la rala pura no arranca (1 muerte en 2,5M pasos: la exploración gaussiana por-lobo no coordina flanqueos por
> accidente antes de que el rebaño se refugie). Se activa el plan B ya esbozado en §5.2: **shaping basado en potencial**
> (Ng, Harada & Russell 1999 — añadir r_shape = γ·Φ(s′) − Φ(s) NO cambia la política óptima si γ es EXACTAMENTE el del
> descuento del agente; por eso el γ del PPO entra al env como parámetro, no se hardcodea dos veces). **Potencial:**
> Φ(s) = −β · mean_i dist(lobo_i, presa designada) / D_norm, con la presa de la MISMA regla ternero-primero que escribe
> el controlador (`RLWolfController._write_prey` — un solo criterio de verdad, re-aplicada en la frontera con
> GUARDAR/RESTAURAR: las vacas se actualizan ANTES que los lobos en `World.step`, así que el pin lee el pack_prey del
> paso anterior y NO debe ver el cálculo de la frontera), media sobre los lobos PRESENTES, D_norm = diagonal del campo
> (≈424 m) → Φ ∈ (−β, 0]; sin res cazable (coasting) → Φ = 0. β afinable (`--shaping-beta`, def. 1.0). s y s′ son las
> FRONTERAS del step del env (tras el frame-skip de 5), no los pasos internos de física. **Recompensa** r = r_kills +
> r_shape (el +1/muerte INTACTO); `info` lleva las componentes (r_kills/r_shape por paso, ep_kills/ep_shape al terminal)
> y `train.log` reporta ep_rew_mean / **ep_kills_mean (LA señal que importa)** / ep_shape_mean / ep_len_mean.
> **La EVALUACIÓN NUNCA ve el shaping** (eval_wolves y la eval ligera van por el World directo y cuentan muertes — lo
> que se puntúa); `--shaping off` reproduce el env de run01 BIT A BIT. **Verificación (rl_env_check test 8):**
> TELESCOPIA (Σ γ^t·r_shape == γ^T·Φ(s_T) − Φ(s_0) exacto — el término está acotado por 2β sea cual sea T: no es
> cultivable), SIGNO (acercarse a la presa acumula r_shape > 0; alejarse, < 0), KILLS INTACTOS (r_kills == Δn_depredadas
> con shaping ON) y OFF ≡ run01 (obs bit a bit idénticas on/off paso a paso: el shaping no toca la DINÁMICA). Smoke 60k
> con shaping ON: ep_shape_mean ~0.8–0.95 ≠ 0 desde el primer rollout (el gradiente ya ve señal), kills 0 (esperado).
> **run02 (10M, shaping ON, β=1, DE CERO — sin --resume):** mismo protocolo desacoplado que run01, artefactos en
> /data/wolves/run02. **CRITERIO DE ABORTO adaptado (en la cabecera del train.log):** ep_shape_mean debe ser ≠ 0 desde
> el principio; lo que DECIDE es ep_kills_mean — si a ~3M sigue ≈ 0.00 (sin muertes emergiendo pese al acercamiento),
> parar y reportar; **el plan C (currículo / BC desde demostraciones del scriptado) lo decide el usuario**. Si las
> muertes despegan: 10M completos y eval_wolves (100 semillas) sobre el último checkpoint y el mejor según evals ligeras.
> Nada más cambia: ni hiperparámetros (solo el γ ya existente entra al env), ni obs, ni mundo; los checks 1–7 quedan
> intactos (solo se AÑADE el 8).
>
> **Patch — EVALUADOR de lobos aprendidos + primer RUN serio (run01, 10M).** Dos piezas sobre el andamiaje verde:
> **(1) OBS DE UN SOLO ORIGEN (`rl/obs.py`):** el constructor de la observación (layout 122 + normalizaciones) se extrae
> a `build_obs(world)` — lo consumen el env de entrenamiento Y el evaluador; si divergieran, el evaluador mediría OTRA
> política. **(2) `PolicyWolfController` (`rl/policy_wolf_controller.py`):** WolfController autónomo de EVALUACIÓN que
> lleva el modelo SB3 dentro (predict determinista, mismo frame-skip 5, desnormaliza y HEREDA de RLWolfController el cap
> por norma + presa ternero-primero + coasting). **Sutileza clave — el INSTANTE de muestreo:** el env construye la obs en
> la FRONTERA del step, pero `decide()` corre DENTRO de la física (drones/vacas ya movidos dt) → el refresco va enganchado
> al coordinador: **`SyncedReactiveCoordinator`** (envuelve al Reactive congelado) llama a `controller.refresh(world)` en
> cada `act()` — el mismo instante que el env — y `decide()` solo APLICA la acción vigente. **Equivalencia BIT A BIT
> verificada** (rl_env_check **test 7**, hermético con un PPO sembrado sin entrenar: 2.829 fronteras idénticas
> lobos+vacas+muertes+reloj en un episodio completo). **(3) `rl/eval_wolves.py`:** evalúa un model.zip con el ARNÉS DE
> SIEMPRE (`evaluate`, MISMAS 100 semillas, misma CONFIG_V2, barrera congelada) y compara contra los lobos SCRIPTADOS
> (2.77 lobos / 2.80 mixto, leídos de baseline_v2_reactive.json; MÁS muertes = mejores lobos); JSON a /data, nunca al
> repo. Smoke del evaluador con el modelo del smoke (política ~aleatoria, 10 semillas): severidad ~0, pipeline limpio.
> **(4) `train_wolves.py` para el run serio:** gamma 0.995→**0.999** (la recompensa rala llega tarde), `--resume <ckpt>`,
> checkpoints ~cada 500k, `train.log` legible (timestamp/pasos/fps/ep_rew_mean/ep_len_mean por rollout; la cabecera
> documenta el CRITERIO DE ABORTO pactado: si a ~2M de pasos ep_rew_mean sigue en 0.00, parar y reportar — el shaping por
> potencial es plan B y lo DECIDE EL USUARIO) y **eval ligera periódica** (cada 250k pasos: 10 episodios deterministas de
> lobos con el mecanismo del evaluador → muertes_media al log; la eval completa de 100 semillas es manual con
> eval_wolves). **run01 lanzado DESACOPLADO** (docker exec -d + exec dentro del contenedor; sobrevive a desconexiones
> SSH): 10M pasos, n_envs=12 (224 cores, load ~14 — buen vecino), CPU, seed 0, artefactos en /data/wolves/run01
> (checkpoints/, tb/, train.log, nohup.out, train.pid). Verja tocada por estos cambios: rl_env_check 7/7 + face_check +
> wolf_controller_check verdes dentro.
> **DESENLACE run01 — ABORTADO a 2,48M pasos por el criterio pactado (la recompensa RALA no arranca).** fps ~1.070
> sostenidos; ep_len_mean ~1.000–1.500 pasos de env (los episodios se RESUELVEN: la barrera + el guiado llevan al rebaño
> al refugio); **ep_rew_mean 0.000 en todo el run** salvo UNA ventana (0.010 a ~1,08M = UNA única muerte espontánea en
> ~2.400 episodios, que PPO no aprovechó — el gradiente no tuvo señal); **10/10 evals ligeras deterministas (250k→2,5M)
> con muertes_media 0.00**. Parado LIMPIO con SIGINT (workers cerrados, sin zombis); checkpoints conservados en
> ~/rl_data/wolves/run01/checkpoints (500k/1M/1,5M/2M/2,5M). Lectura: contra la barrera reactiva una política inicial
> ~aleatoria casi nunca llega a matar (la manada necesita flanquear COORDINADA a una presa concreta antes de que el
> rebaño se refugie) → exploración insuficiente para la rala pura. **El shaping por potencial (plan B pactado) NO se ha
> implementado: la decisión es del usuario** (alternativas a valorar: shaping Φ, currículo —lobos más cerca / barrera
> debilitada al inicio—, ent_coef mayor, arranque desde demostraciones del scriptado).
>
> **Patch — ANDAMIAJE RL de LOBOS: contenedor + envoltorio Gymnasium + train_wolves + smoke (SIN entrenar en serio).**
> Toda la FONTANERÍA del entrenamiento de lobos, demostrada girando; la física v2.4 INTACTA (`world.py`/`wolf_controllers.py`
> SIN tocar; `make_wolf_controller("learned")` SIGUE en NotImplementedError — el entrenamiento INYECTA
> `wolf_controller=RLWolfController(...)` directo; el cableado del modelo entrenado a la factoría/main = paso posterior).
> **Decisiones:** cerebro ÚNICO del paquete (una política mueve a TODOS los lobos); **PPO (Stable-Baselines3) + Gymnasium
> single-agent** (`rl/wolf_env.py: WolfPackEnv`; PettingZoo queda para la fase de drones); **recompensa RALA** = +1 por res
> matada (compartida, Δ`n_depredadas` por tramo), SIN castigo por tiempo ni por a-salvo (shaping = plan B futuro); **acción**
> = velocidad deseada por lobo (`Box(-1,1,(10,))` = 5 slots × 2, desnormalizada ×`wolf_speed`), decidida cada **frame_skip=5**
> pasos de física (0.5 s) y MANTENIDA entre decisiones (slots de lobos inexistentes se ignoran); **obs de tamaño FIJO
> (122, float32)** con padding y máscaras — 5 lobos×[pos,vel,scared,present] + 6 vacas×[pos,vel,alive,safe] +
> 2 terneros×[pos,vel,alive,safe,present] + 8 drones×[pos,vel,is_active] + [reses en juego, reloj] — marco RELATIVO al
> establo, posiciones /(W/2,H/2), velocidades /v_max de su especie; SIN corzos, SIN batería, SIN presa fijada (layout con
> índices = docstring de `rl/wolf_env.py`, la referencia); se construye leyendo ATRIBUTOS del World (get_observation() es
> parcial). **Episodios lobos/mixto ~50/50, NUNCA corzos** (sin lobos no hay nada que aprender); adversario =
> **ReactiveCoordinator congelado** DENTRO del env (mismo bucle que evaluate). **Semillas:** cada reset() toma semilla FRESCA
> de una secuencia propia del env (`World.reset(None)` REPITE el mismo episodio) → mismo seed del env = misma secuencia
> (reproducible, verificado).
> **CAP EN LA FRONTERA (decisión):** el contrato del refactor decía "el mundo recortará la salida del aprendido"; world.py
> está CONGELADO y no se toca, así que el recorte prometido vive en la FRONTERA del controlador (`rl/rl_wolf_controller.py`
> recorta la NORMA de cada velocidad a `wolf_speed` ANTES de devolverla → el mundo nunca ve una intención por encima del cap;
> equivalente, verificado en el check, y REVISABLE si algún día se descongela el mundo). **pack_prey por REGLA FIJA** (no lo
> decide la red; el pin de la vaca la lee): ternero vivo no-a-salvo más cercano al centroide del paquete; si no, vaca viva
> no-a-salvo más cercana; nada → -1/None (índices según convención: en `cows` si "adult", en `calves` si "calf").
> **coasting DETERMINISTA** (True solo sin res viva no-a-salvo = `_targets_exhausted`, como el scriptado; v=0).
> **Arnés extendido RETROCOMPATIBLE:** `build_world(seed, kind, wolf_controller=None)` y
> `evaluate(..., wolf_controller_factory=None)` (factory SIN args → instancia fresca por episodio) — con None TODO queda
> bit a bit como estaba (verificado: `python baseline.py` DENTRO del contenedor → números idénticos, deriva verde);
> `_verify_fidelity`/`REFERENCE_SEVERITY`/artefactos SIN tocar.
> **Contenedor del PROYECTO (`docker/`):** imagen CALCADA de la del lab (mismo requirements.txt lockfile: numpy 2.2.6 ·
> matplotlib 3.10.6 · pillow 11.3.0 · torch 2.8.0 · gymnasium 1.2.1 · SB3 2.7.0 · tensorboard 2.20.0; SIN
> pettingzoo/benchmarl —fase de drones—; + libgl1/libglib2.0-0: el opencv del lockfile moría sin libGL en servidor sin X),
> contenedor `${USER}-wolves` IDLE para docker exec (`conectar.sh`; sin Jupyter), **GPU count:1** (buen vecino; el smoke va
> en CPU), shm 2gb (SubprocVecEnv), repo→`/workspace` + `~/rl_data`→`/data` (TODOS los checkpoints/logs FUERA del repo;
> persisten), `PYTHONPATH=/workspace`, uid remapeado al del host (NB_UID/GID vía docker/.env) → los archivos quedan del
> usuario. **`rl/train_wolves.py`:** PPO MlpPolicy [128,128] (hiperparámetros anotados en config.json), SubprocVecEnv
> (**fork**: el forkserver default de SB3 re-importa el stack y moría con cv2 sin libGL) + VecMonitor, CheckpointCallback +
> TensorBoard + summary.json (fps, episodios, recompensa por tramos) en el outdir (verifica que es escribible ANTES de
> entrenar); `--smoke` = 60k pasos / 4 envs / CPU.
> **Verificación (TODO dentro del contenedor):** **`rl_env_check.py` NUEVO (ENTRA en la verja), 6 tests VERDES:**
> formas/máscaras del layout · determinismo (misma semilla = misma secuencia y trayectoria) · CAP (acción desbocada →
> intención y velocidad efectiva ≤ wolf_speed) · regla de presa (calf→adult→refugiada se suelta→-1/coasting) ·
> **CANAL DE RECOMPENSA dirigido, el más importante** (política de mano que caza → ≥1 muerte y recompensa ==
> n_depredadas EXACTO episodio a episodio; 21 muertes en 6 semillas: obs→acción→mundo→recompensa conectado de VERDAD) ·
> física intacta (spot-check semillas 0/1/7 × 3 tipos == baseline_v2.json + 'learned' sigue NotImplementedError) ·
> **smoke** de principio a fin SIN NaNs (65.536 pasos, 96 s, **681 fps**, 60 episodios; recompensa 0.0 — política
> aleatoria vs barrera con recompensa RALA: el punto de partida esperado, el canal está probado por el test dirigido)
> con artefactos PERSISTENTES en ~/rl_data. Diff acotado: `docker/` + `rl/` + `rl_env_check.py` + `baseline.py`
> (extensión) + `.gitignore` + docs.
> **⚠️ HALLAZGO — LA BASELINE CONGELADA ES DEPENDIENTE DEL ENTORNO (deriva FP portátil↔DGX), DECISIÓN PENDIENTE.**
> Al reproducir `python baseline.py` DENTRO del contenedor: solo-lobos **4.54** y mixto **4.46** vs los congelados
> 4.41/4.34 (solo-corzos 0.00 exacto — sus métricas son insensibles por construcción: siempre timeout limpio).
> Diagnóstico (código EXONERADO): (1) el `baseline.py` de HEAD (sin la extensión) da EN el contenedor los MISMOS
> valores derivados (seed 2 lobos 2 muertes/14142 steps vs congelado 4/868) → la extensión no es la causa; (2) la
> imagen ORIGINAL del lab (mismo lockfile numpy 2.2.6 / python 3.13.14) da también los MISMOS valores derivados →
> ningún entorno de la DGX reproduce los números congelados; (3) ~70% de los episodios con LOBOS difieren en ±pocos
> steps y ~13/100 voltean muertes (en ambos sentidos) → patrón de diferencias de ÚLTIMA ULP en coma flotante entre
> plataformas (libm/hardware; la v2.4 se midió presumiblemente en el portátil —macOS—) AMPLIFICADAS por el caos; los
> spawns/RNG son idénticos (semillas 0/1/7 exactas; fidelidad verde). La reproducibilidad "bit a bit" del mundo es
> POR ENTORNO, no entre plataformas. **Consecuencia:** en el contenedor, el spot-check de `wolf_controller_check`
> (semillas 0,1,**2**,3,7) caía en ROJO (seed 2 lobos 4→2) — no porque nada hubiera cambiado, sino porque la
> REFERENCIA era de otro entorno.
> **DECISIÓN (usuario, 2026-07-14): opción (a) — el contenedor de la DGX (docker/) es desde ahora el ENTORNO
> CANÓNICO de medida ("mismo mundo, metro DGX").** Re-medición COMPLETA dentro del contenedor (baseline.py +
> reactive_eval.py, mismas semillas range(100) × 3 tipos, sin tunear NADA — es medida, no objetivo):
> `REFERENCE_SEVERITY` y TODOS los artefactos actualizados con lo que salió; `FROZEN_TAG` y tag git
> **`v2.4.1-baseline`** (la física v2.4 NO cambió: mismos spawns, mismo RNG, mismas reglas — solo cambia el metro).
> El PORTÁTIL deja de ser referencia de números: sus spot-checks contra los artefactos (wolf_controller_check
> test 4, rl_env_check test 6, la deriva de baseline.py) pueden salir ROJOS fuera del contenedor — ESPERADO y
> documentado en los propios checks. **NÚMEROS v2.4.1 (N=100/tipo, dentro del contenedor):** Dummy solo-lobos
> **4.54**±2.21 (succ 4/pred 88/tout 8; n_safe 2.25) · solo-corzos **0.00** (100 timeout) · mixto **4.46**±2.27
> (succ 5/pred 86/tout 9; n_safe 2.38); Reactive solo-lobos **2.77**±1.46 (Δ−1.77; n_safe 4.12; succ 4/pred 90/
> tout 6) · solo-corzos **0.00** · mixto **2.80**±1.48 (Δ−1.66; n_safe 4.08; succ 4/pred 88/tout 8) — casi
> calcados a los del portátil (2.80/2.78): mismo mundo, otro metro. **El objetivo del MARL pasa a ser batir
> 2.77 / 0 / 2.80.** Verja completa (7 checks) VERDE dentro del contenedor con la nueva referencia.
>
> **Patch — REFACTOR: controlador de lobos ENCHUFABLE (scripted | learned), SIN cambio de comportamiento.** Refactor
> PURO que prepara la fase RL (lobos APRENDIDOS que burlen la barrera): extrae la toma de decisiones de los lobos a
> una interfaz `WolfController` (`wolf_controllers.py`), con el SCRIPTADO actual como default BIT A BIT idéntico a
> v2.4. CERO cambio de comportamiento, CERO re-congelación (la baseline NO se toca).
> **FRONTERA POLÍTICA / FÍSICA (el corazón del refactor; será el contrato del RL — el controlador DECIDE, el mundo IMPONE):**
> *POLÍTICA* (va al controlador, un cerebro aprendido podrá sustituirlo): a dónde quiere ir cada lobo — fijación/re-fijación
> de la presa común (matanza excedente), standoff, cierre por el cono/flanqueo, rodeo del rebaño, ataque ENVOLVENTE,
> repulsión entre lobos, bordeo de zonas, coasting al agotar. **Salida:** `decide(world) -> (v_target (nw,2), coasting)`
> = VELOCIDAD deseada por lobo (será la ACCIÓN del RL). *FÍSICA* (se queda en el mundo, innegociable para CUALQUIER
> controlador): el CAP de velocidad (wolf_speed=4.0) y la integración (inercia); el **SUSTO** (v2.4, `_apply_deterrence`)
> —si un dron embiste, el mundo IMPONE la huida SOBRE la intención; un lobo huyendo NO mata ni flanquea, el miedo NO es
> opcional—; la evitación suave del dron estático; las reglas de captura/muerte (radio, dar-la-cara/r_face_safe, cadáveres);
> la percepción, la dinámica de vacas/terneros/corzos y la detección/confirmación de drones; los clamps de zona.
> **AMBIGÜEDAD RESUELTA (pregunté al usuario):** la **presa común** (`pack_prey`, `pack_prey_kind`, `n_refix`,
> `_ever_committed`, `_wolf_attacking`) es TÁCTICA del lobo PERO la LEEN partes que no son del lobo —el **PIN** de la vaca
> (una vaca solo encara si es la presa fijada), la instrumentación (`is_pack_prey`) y el render—. Decisión (usuario): VIVE en
> el **World** (contrato compartido); el controlador la ESCRIBE. Cuando llegue el controlador APRENDIDO tendrá que emitir
> TAMBIÉN su 'presa objetivo' para que el pin funcione (se decide en la fase RL). **Salida = VELOCIDAD** (no dirección,
> decisión del usuario): el mundo la trata como intención; el cap es física pero el mundo NO recorta al scriptado (que ya
> emite a tope) para el bit a bit —recortará al aprendido—. **`_update_wolves`** pasa a ser un ORQUESTADOR fino
> (`v_target, coasting = wolf_controller.decide(self)`; si no coasting → `_apply_deterrence`; inercia + integración + clamps);
> el scriptado se movió TAL CUAL a `ScriptedWolfController` (mismos números). Selección análoga a `--coordinador`:
> `World(wolf_policy="scripted"|"learned", wolf_controller=<instancia>)`, `main.py --lobos scripted` (default; `learned` =
> `NotImplementedError`, hueco RL). **NO toca:** ningún comportamiento observable, la config congelada, la baseline.
> **Verificación:** **fingerprint de equivalencia bit a bit** (SHA del estado de combate + escolta Dummy + escolta Reactive
> —drones móviles, susto activo, coast, re-fijación— en episodios completos, `git stash` HEAD vs refactor → IDÉNTICO
> `4425c866…`). **Verja verde SIN adaptar** (face 12/12 · battery · escort · drone · reactive). `wolf_controller_check.py`
> nuevo (interfaz · el controlador no integra/asusta · **susto INNEGOCIABLE**: la embestida sobrescribe la intención de caza
> · spot-check 15 episodios == baseline v2.4). Diff acotado: `wolf_controllers.py` (nuevo) + `world.py` (orquestador + param)
> + `main.py` (flag) + docs. SIN re-congelación (v2.4-baseline sigue vigente).
>
> **Patch — SUSTO POR MOVIMIENTO + baterías iniciales realistas + carga 1.5× (v2.4) + RE-CONGELAR.** TRES cambios de
> FÍSICA del mundo en una re-congelación (por eso RE-MIDE la baseline). **Motivo:** (1) el susto de v2.3 era un "campo de
> fuerza" —el lobo no podía acercarse a un dron aunque estuviera QUIETO—; irreal: los depredadores se HABITÚAN a disuasores
> estáticos, lo que asusta es algo lanzándose hacia ti. (2) Todos los drones arrancaban a tope; una flota real está a mitad
> de ciclo. (3) La carga debe recuperar más deprisa de lo que el vuelo gasta, explícito.
> **(1) SUSTO POR MOVIMIENTO (`_apply_deterrence`):** para cada lobo se mira la velocidad de APROXIMACIÓN de cada dron ACTIVE
> a tiro (`≤ DETER_RADIUS=20`, = componente de la velocidad del dron hacia el lobo). **Acercándose** (aprox. `> SCARE_APPROACH_MIN`
> =1.0) → EXPULSIÓN plena (mecanismo v2.3: huida radial del dron acercándose MÁS CERCANO, `clip(wolf_speed·(1−d/R), SCARE_SPEED_MIN,
> wolf_speed)`, la huida SUSTITUYE a la caza, `_wolf_scared` → no mata mientras huye). **Estático/alejándose** (`≤ SCARE_STATIC_RADIUS`
> =6) → miedo REDUCIDO: el lobo SIGUE cazando (v_target manda) pero esquiva suave el poste (repulsión radial renormalizada a la
> rapidez de caza, solo redirige) → **puede matar con un dron parado al lado**. Marca `_drone_scaring` (drones que embisten) → el
> render dibuja 🔊 solo al embestir de verdad. Solo ACTIVE; gateado por `escort_enabled` → combate puro NO asusta, `_wolf_scared`/
> `_drone_scaring` todo False → **face_check bit a bit** (verificado: fingerprint de combate SHA idéntico v2.3≡v2.4).
> **(2) Baterías iniciales:** los 4 ACTIVE en vuelo con batería ALEATORIA en `[battery_init_min=0.25, 1]` (>umbral → sin relevo
> en t=0) y cada reserva EN CARGA es el ESPEJO de su pareja (`1−bat_activo_i`). Del SUBSTREAM `_battery_rng=default_rng(seed+2_000_003)`
> → NO consume del stream principal → spawns bit a bit (verificado: distinto `battery_init_min` → spawns idénticos, baterías distintas).
> **(3) Carga:** `charge_rate = CHARGE_TO_FLIGHT_RATIO=1.5 · drenaje_vuelo_pleno` (`drain_rate_active·(1+DRONE_MOVE_DRAIN)`) → tiempo de
> carga completa DERIVADO ≈ **160 s** (antes `charge_full=300` fijo, ahora DEPRECATED). **NO toca:** caza (cono/flanqueo/envolvente/
> matanza excedente), huida, madre-ternero, LÓGICA del relevo (umbrales/hand-off/estados/rombo), detección, coordinadores.
> **RE-MEDIDO (N=100/tipo):** la disuasión estática se evapora → Dummy 2.36/0/2.24 → **4.41/0/4.34** (≈ v2.2 4.45/4.41: los drones
> CLAVADOS del Dummy ya casi no disuaden; n_safe 4.19→2.38). Reactive 0.16/0.18 → **2.80/0/2.78** (−1.61/−1.56 vs Dummy; SUBE mucho
> —la barrera clavada es un poste— pero SIGUE batiendo al Dummy porque se recoloca; MEDIDA, no objetivo). **Conclusión de diseño:**
> casi toda la ventaja del clásico en v2.3 venía del campo de fuerza estático; con el susto por movimiento **defender bien exige
> MOVER los drones con intención** — el trabajo del MARL (batir 2.80/2.78, no ya 0.16/0.18). **Verja:** `test_susto`/`test_disuasion`
> adaptados (QUIETO=obstáculo sigue cazando · EMBISTE=expulsión + PERSISTENTE · huida acotada), `test_pin_envolvente` (un POSTE ya
> no protege → k_con≠None), battery_check +arranque espejo +ratio de carga (estrés 2.5→5.0× porque la carga más rápida ya no agotaba
> reservas a 2.5×). face 12/12 bit a bit · battery · escort (24 OK) · drone · reactive verdes; tag `v2.4-baseline`.
>
> **Patch — SUSTO FUERTE (la disuasión pasa de PARCIAL a FUERTE) + rombo de carga (v2.3) + RE-CONGELAR.** CAMBIO de FÍSICA
> del mundo (por eso RE-MIDE la baseline). **Motivo (visto en render):** un lobo alcanzaba una vaca clavada y se quedaba
> PEGADO indefinidamente —la disuasión parcial le dejaba "empujar a través" y matar—; cuadro congelado lobo-vaca-dron.
> **Modelo nuevo (`_apply_deterrence`):** un lobo con un dron ACTIVE a ≤`DETER_RADIUS`=20 HUYE del dron (velocidad RADIAL
> alejándose, módulo CRECIENTE al acercarse `clip(wolf_speed·(1−d/R), SCARE_SPEED_MIN=0.8, wolf_speed)`, dirección = suma de
> los repulsores a tiro, módulo del MÁS CERCANO) y NO caza mientras huye (la huida SUSTITUYE a la caza). **SIN excepción a
> corta:** un dron ENCIMA SIEMPRE lo expulsa (fuera `deter_w`/`DETER_REPULSION`/`DETER_TANGENT`/`DETER_SLOWDOWN`). Los que
> huyen se marcan (`_wolf_scared`) y NO cuentan como flanqueadores en `_process_predation` → no matan huyendo. EXPULSADO ≠
> rendido: fuera del radio retoma la caza (sin cooldown). Solo drones ACTIVE; gateado por `escort_enabled` (combate puro NO
> asusta, `_wolf_scared` todo False → **face_check bit a bit**). **Rombo de carga:** los 4 slots de reserva pasan de fila
> recta a ROMBO (4 vértices) en la central (determinista, no consume RNG → spawns bit a bit; solo cambia su posición de
> partida, lo recoge la re-medición). **NO toca:** caza (cono/flanqueo/envolvente/matanza excedente SIN drones), huida,
> madre-ternero, batería/relevo (lógica), detección, coordinadores. **RE-MEDIDO (N=100/tipo):** Dummy 4.45/0/4.41 →
> **2.36/0/2.24** (el susto casi la halva; incluso los drones QUIETOS del Dummy expulsan a los que se acercan; n_safe
> 2.39→4.19). Reactive 3.36/3.42 → **0.16/0/0.18** (−2.20/−2.06; barrera+susto ≈ protección total, 85% success). MEDIDA, no
> objetivo (no se tuneó `SCARE_*`). **Verja:** `test_susto` dirigido nuevo (lobo pegado+dron→expulsado y vaca sobrevive ·
> dron lejos→cero efecto · huida acotada) + tests de disuasión adaptados (k_con=None: el dron ya no deja "empujar a través")
> + fix de un BUG latente del `sev()` de `reactive_check` (construía el coordinador con un world CONGELADO distinto al que
> corría → el reactivo salía artificialmente mal). face 12/12 bit a bit · battery · escort · drone · reactive verdes; tag
> `v2.3-baseline`.
>
> **Patch — Retoques visuales + fix del ARRANQUE del reactivo.** Dos bloques, sin tocar la física del mundo.
> **(1) Cosmética (solo `render.py`):** emojis un escalón más pequeños (`EMOJI_SCALE` 0.55→0.45); FUERA la leyenda de
> entidades de abajo-izq (se explican solos; queda la de zonas); **🔊** bajo el dron ACTIVE que "emite ruido" (algún lobo
> a ≤`DETER_RADIUS` → disuade) — puro dibujo: el render LEE lobos/estado del snapshot y usa el mismo radio de config, NO
> toca la lógica de disuasión. **(2) Bug del arranque del reactivo (solo `coordinators.py`):** los drones salían TODOS al
> medio y se CRUZABAN. CAUSA (diagnóstico empírico): nacen en las ESQUINAS del rebaño (~225°+90°i) pero `_patrol` los
> mandaba a la ranura `i·2π/k` (~135° OPUESTA) → cruzaban el centro (error angular 135°, sep mínima ~16 m). FIX: la PATRULLA
> ancla la FASE de la formación (media circular) a la posición angular ACTUAL → cada dron va a su ranura MÁS CERCANA (error
> 10°, sep 41 m, sin cruces) y luego órbita rígida sin reasignaciones. Solo el coordinador: Reactive 3.27/3.40→**3.36/3.42**
> (+0.09/+0.02 — el bug apoyaba números en un center-hugging accidental), Dummy/física/baseline INTACTOS (**NO re-congela**).
> `test_arranque` nuevo + `test_severidad_muestra` n=15→30 (con n=15 caía en el slice de menor beneficio y el ruido cambiaba
> el signo). **face 12/12 bit a bit · battery · escort · drone · reactive verdes.** **Rombo de carga: NO hecho** — los slots
> de reserva viven en `world.py` (reset, fila recta) → tocarlos movería la baseline; PARADO a la espera de decisión.
>
> **Patch — JABALÍ 🐗 como 2ª distracción + emojis más pequeños (v2.2) + RE-CONGELAR.** La distracción era siempre
> un corzo; ahora es corzo O **jabalí** ~50/50 (`distraction_species_prob`), MISMO comportamiento (mismo array
> `corzos`, misma dinámica: deambula en grupo, detectable, ORÁCULO a `r_confirm` → el dron DESCARTA igual). La
> especie se elige con un **SUBSTREAM RNG SEPARADO** (`_distraction_rng = default_rng(seed+offset)`) → NO consume del
> stream principal → spawns de lobo/vaca **bit a bit** iguales → baseline comparable. El oráculo solo gana un tipo
> más. Render: 🐗 con su sprite (según `distraction_species`); **emojis más pequeños** (`EMOJI_SCALE`). Solo mundo
> (distracción) + render/main; **NO** toca caza/disuasión/detección/coordinadores/relevo. **face_check 12/12 bit a
> bit** (el substream no perturba; solo-lobos == corzos-OFF). **RE-CONGELADO v2.2** (tag `v2.2-baseline`): Dummy
> 4.45/0/4.41 y Reactive 3.27/0/3.40 SIN cambios (re-medidos). Verificado en `escort_check` 1j (especie ~50/50 ·
> substream no perturba · jabalí descartado · reproducible).
>
> **Patch — RELEVO de flota REALISTA (v2.1) + RE-CONGELAR.** El relevo de batería era un **swap INSTANTÁNEO**
> (teletransporte de rol+posición). Ahora **con hand-off, SIN teletransporte** (`_step_battery`, estados nuevos
> `INCOMING`/`STRANDED`): al bajar de `announce_threshold`=0.20 el ACTIVE se **CLAVA en su puesto** (sigue
> cubriendo/disuadiendo; el coordinador ya no lo comanda) y la central despacha al READY más cargado, que **VUELA**
> al puesto (`INCOMING`); al llegar ENCIMA (≤`relay_handoff_tol`=2 m) → **hand-off** (relevo→ACTIVE, bajo→`RETURNING`
> →central→`CHARGING`). **Cobertura CONTINUA** salvo **`STRANDED`** (bajo a ~0 antes del relevo: en el puesto, SIN
> disuadir, hasta el hand-off) = el hueco real bajo estrés que un buen coordinador evita (no agotar la flota
> moviéndose de más). Moverse pasa a tener **coste energético REAL** (compromiso para el MARL). Solo el relevo:
> `_step_battery`/`_init_battery` + free-mask de `_apply_drone_actions` + pool de investigación + enum; **NO** toca
> caza/disuasión/reflejo/coordinadores (la disuasión sigue keyed en ACTIVE → INCOMING/RETURNING/STRANDED no disuaden).
> **NO usa el RNG** → **face_check 12/12 bit a bit**; `battery_check` actualizado (4/2/2 + tránsito · sin teletransporte
> · stranded bajo estrés · reproducible); escort/drone verdes. **RE-CONGELADO v2.1** (tag `v2.1-baseline`): Dummy
> **4.45/0/4.41** y Reactive **3.27/0/3.40** SIN cambios (re-medidos; la cobertura se mantiene).
>
> **Patch — CORZOS afinados (que se vean e investiguen bien).** Cuatro mejoras del escenario de corzos. **(1) BUG del
> reflejo:** un corzo dejaba la fase **PILLADA en SOSPECHA** (solo se latcheaba ESCOLTA para lobos) y el dron
> descartado **no volvía**. Ahora el dron **VUELA al contacto**, solo a `r_confirm` el oráculo dicta el tipo (no de
> lejos); al descartar el corzo **VUELVE a su puesto** (`drone_home`) y la **fase vuelve a VIGILANCIA** si no queda
> contacto (lobo→ESCOLTA, no vuelve). El reset de fase NO afecta la dinámica (solo ESCOLTA importa) → baseline bit a
> bit. **(2) AGRUPADOS:** spawn de un grupo (`CORZO_GROUP_DISPERSION`=6) + cohesión suave (`CORZO_COHESION`=0.05) +
> separación (`CORZO_SEPARATION`=4) → salen y se mantienen juntos. **(3) Dentro de SOSPECHA:** el centroide en la banda
> `[cow_spread+r_notice, r_detect]` → **100%** de episodios disparan SOSPECHA (medido). **(4) REGRESIÓN del render:**
> el submuestreo aceleraba la reproducción; ahora `main.py` renderiza solo la **ventana relevante** a ritmo natural
> (no comprime el timeout de solo-corzos). Solo render/`main.py` → la sim NO cambia (fingerprint idéntico). **NO** toca
> el modelo del lobo/vaca, la disuasión, ni la baseline (corzos-OFF = 4.40). Verificado en `escort_check` 1i (deambula+huye · detectable · oráculo
> lobo→ESCOLTA/corzo→descarta · solo-corzos sev 0 · reparto ~1/3 reproducible) + 9b (severidad POR TIPO) + 2 renders.
>
> **Patch — FIX PIN: 4 lobos no mataban a una adulta CLAVADA en ESCOLTA (+ ataque ENVOLVENTE + disuasión
> parcial a corta).** Regresión: una adulta clavada era **invulnerable** a un paquete que la rodeaba.
> **Diagnóstico** (instrumentado, seed 11/24): los lobos se **APIÑABAN dentro del cono frontal** (offsets
> del morro −28°/+1°, ambos <45°) → "dar la cara" los mantenía a TODOS a `r_face_safe`=6 m, ninguno a flanco
> limpio; y la **disuasión** sumada de varios drones los clavaba a ~3.5–5.5 m (sin dron SÍ mataban). **Dos
> fixes:** (1) **ATAQUE ENVOLVENTE** (`wolf_envelop_gain`, `_envelop_slots`): el paquete reparte sus rumbos
> en ángulos EQUIESPACIADOS alrededor de la presa (4→~N/E/S/O, 3→~120°) → salen del cono a flancos limpios.
> (2) **DISUASIÓN PARCIAL A CORTA** (`deter_w`): un lobo PEGADO a su presa (≤`r_face_safe`) ignora el dron y
> **empuja a través** (rampa a disuasión completa en 2·`r_face_safe`) → el dron **REDUCE/RETRASA** la caza y
> despeja pines, pero NO invulnerabiliza. **Baseline HONESTA** (el bug FALSEABA la severidad a la baja):
> severidad v2 **~1.55 → ~2.73 muertes/ep** (tasa 52%→78%; reparto `predation 31/timeout 3/success 6`),
> adversario puro **~6.33**. **face_check 12/12** (envolvente es código de lobo compartido, pero en combate la
> presa se mueve y ya flanqueaba — muerte paso 27→29, intacto). **NO** toca guiado, detección/confirmación,
> coordinador (Dummy), baseline.py. Verificado en `escort_check` (test 1e: clavada matable con/sin dron +
> envolvente) + renders `escort_pin_envolvente.gif` (mata a una clavada) y `escort_pin_con_dron.gif` (el dron
> la RETRASA 52→88 frames, no la impide).
>
> **Patch — MATANZA EXCEDENTE (el paquete caza hasta agotar; revierte el tope de 1 caza de `1d44cdc`).**
> En presa CONFINADA (pasto cercado, reses clavadas) una manada real mata más de lo que come. Quitado
> `pack_sated`: tras MATAR o REFUGIARSE la presa, el paquete **RE-FIJA la res viva no-a-salvo MÁS CERCANA**
> (`_recommit_nearest_prey`, al centroide del paquete) y **SIGUE** cazando hasta **agotar** objetivos (todas
> muertas o a salvo); entonces se **DESENGANCHA y FRENA** (coastea a parada — el mismo coast del saciado,
> ahora gateado por `_targets_exhausted`; mantiene `face_check` test 3 firme). La **caza en sí** (cono /
> flanqueo / fijación en t=0 / rodeo) es IDÉNTICA; solo cambia a quién se re-fija después y cuándo para.
> Re-fijar-tras-refugio intacto; `n_refix` sigue contando SOLO re-fijaciones por refugio. **La SEVERIDAD
> vuelve a ser la métrica principal** (cabezas perdidas): candidata a v2 (Dummy + guiado + disuasión)
> **~1.55 muertes/ep** (tasa ≥1 ~52%), adversario puro **~6.33** (máx. 8). El trabajo del coordinador pasa a
> ser **minimizarla**. **face_check 12/12** (comportamiento intacto; conteo de capturas actualizado a
> multi-muerte). **NO** toca disuasión, guiado, no-holonómico, detección/confirmación, drones, baseline.py.
> Verificado en `escort_check` (multi-caza, re-fijar-más-cercana, refugio, parar-al-agotar) + renders
> `escort_matanza_excedente.gif` (3 cazas) y `escort_rebano_a_salvo.gif` (rebaño entero a salvo).
>
> **Patch — DISUASIÓN del dron (el lobo ESQUIVA + FRENA cerca de un dron · le da DIENTES a la escolta).**
> Es CÓMO responde el mundo al dron (infraestructura, gateada por `escort_enabled`), **no el coordinador**.
> Dentro de `DETER_RADIUS`=40 m de un dron **ACTIVE**, el lobo **ESQUIVA** (repulsión radial con *falloff*
> lineal, más fuerte cuanto más cerca; suma la de todos los drones a tiro) y **FRENA** (rapidez máx ×
> `DETER_SLOWDOWN`). La esquiva se **SUMA al impulso de caza** → competencia **PARCIAL**: cerca la repulsión
> domina (el lobo se desvía/retrocede → **despeja el pin** y la vaca reanuda), al borde del radio la caza
> domina (empuja a través, frenado) → *uno huye, otros aguantan* (como en el hazing real; lo que disuade es
> el **sonido**, el dron "ladra"). **Sin habituación** todavía (flag #6). **Efecto en la tasa (Dummy):** con
> disuasión PASIVA (los lobos esquivan a los drones quietos y al investigador liberado tras confirmar) la
> tasa baja de **~80% → ~55%**, severidad **~0.5** (sigue máx. 1 caza); el **posicionamiento** del coordinador
> la bajará más (post-v2). **face_check 12/12 SIN cambios** (combate puro `escort_enabled=False` → bit a bit).
> **NO** toca posicionamiento estratégico (coordinador), pastoreo/combate, detección, baseline.py. Verificado
> en `escort_check` (esquiva+frena, parcial, despeja el pin, tasa) + animación `escort_disuasion.gif`.
>
> **Patch — DOS CORRECCIONES EN LA HUIDA (ESCOLTA).** **Bug 1 (solo la presa se para):** SOLO la **presa
> fijada** por el paquete (y su defensora si es ternero) entra en ENCARAR (parar+encarar); las **no-fijadas
> siguen HUYENDO** aunque tengan lobos en `r_notice` (el paquete está comprometido con UNA presa). Antes se
> paraban TODAS las vacas cerca de un lobo → ahora el **resto del rebaño llega a salvo** (`n_safe` medio
> ~2.6→**6/6**). **Bug 2 (ternero entra tras su madre):** un ternero se marca a salvo (verde) **SOLO cuando él
> mismo está dentro** (NO cuando lo está su madre); hasta entonces sigue migrando al establo (la madre a-salvo
> dentro es el ancla; al apuntar al centro, cruza el umbral). Implicaciones medidas: el **ÉXITO orgánico SÍ
> ocurre** (rebaño entero cuando el paquete falla); **lobo-solo SIN ternero → ÉXITO**, **CON ternero → TIMEOUT**
> (defensora clavada). Tasa ~80%, severidad ~1 (sin cambios). **face_check 12/12.** **NO** toca disuasión
> (siguiente), pastoreo/combate, 1-caza-por-episodio. Verificado en `escort_check` (Bug 1, Bug 2, tasa).
>
> **Patch — VACAS NO-HOLONÓMICAS EN ESCOLTA (correr de frente, o girar y parar a encarar).** Una vaca real
> corre **hacia donde mira**; no puede correr mientras encara. En `ESCOLTA`, huir y dar la cara pasan a ser
> **EXCLUYENTES**: **HUIR** (sin lobo en `r_notice`) → gira el heading al establo y avanza **de frente** a
> `cow_speed` (velocidad **siempre a lo largo del heading**, flanco expuesto); **ENCARAR/PIN** (lobo dentro de
> `r_notice`) → gira a encararlo y **se PARA**. Esto crea el **pin** (los lobos clavan a la vaca → pin-and-flank)
> y hace concreto el trabajo del dron: **despejar lobos para que la vaca reanude**. Solo ESCOLTA; pastoreo/combate
> sigue **holonómico** (la restricción no cambia nada con las vacas casi quietas → face_check intacto, **12/12**).
> Implicaciones medidas (no bugs): **lobo-solo → TIMEOUT** (clava pero no flanquea; antes ÉXITO), **tasa v2 ~80%**
> (la presa clavada es muy cazable), **severidad ~1** (sigue máx. 1 caza). ÉXITO orgánico ahora = llegar **antes**
> de ser fijada (lo desbloqueará el apantallado de drones, post-v2). Verificado en `escort_check` (huir/pin/reanudar
> no-holonómico, lobo-solo→timeout, tasa). **NO** toca disuasión (siguiente), pastoreo/combate, detección.
>
> **Patch — MÁX. 1 CAZA POR EPISODIO (modelo del lobo).** Antes el paquete RE-FIJABA tras matar → ~3
> muertes/episodio (matanza, irreal). Ahora, como una manada real (una caza por ataque, se alimenta), el
> paquete **caza UNA vez y se SACIA** (`pack_sated`): para permanentemente y **se desengancha** (frena
> cerca de la caza, no orbita). La **primera caza es IDÉNTICA** (cono/flanqueo/fijación en t=0/rodeo sin
> tocar); solo cambia lo que pasa **después**. El tope lo impone `_process_predation` (cae UNA res y para,
> robusto frente al doble-flanqueo simultáneo). **Re-fijar-tras-REFUGIO intacto** (si la presa se refugia,
> el paquete elige otra y sigue cazando hasta 1 muerte o que todas se refugien). **Severidad de la v2
> (Dummy+guiado): ~1 muerte/episodio** (antes ~3); la **TASA (≥1 muerte) queda ~igual (~78–82%)**: el
> paquete consigue su única caza en la mayoría de episodios; la TASA la bajará el apantallado de los drones
> (post-v2). **face_check 12/12 SIN cambios** (la primera caza es idéntica). **NO** toca disuasión, guiado,
> detección/confirmación. Verificado en `escort_check` (máx. 1 caza, re-fijar-tras-refugio, tasa+severidad).
>
> **Paso 2 — GUIADO al refugio (collares conducen el rebaño al establo). CIERRA EL BUCLE.** Al CONFIRMAR
> (fase `ESCOLTA`), los collares conducen el rebaño hacia el establo (la fuga) → **ÉXITO** pasa a ser
> alcanzable de forma orgánica (antes solo forzado). Es **INFRAESTRUCTURA del mundo** (gateada por la fase,
> `escort_enabled`), no el coordinador → igual para todos; los **terneros** migran anclados a su defensora y
> se marcan a salvo con ella. Pastoreo/combate sigue **holonómico** e intacto (**face_check 12/12**,
> `escort_enabled=False` = combate puro). El **movimiento de la fuga** (y el pin) lo fija el patch
> *no-holonómico* (arriba); la **severidad** (≤1) el patch *máx. 1 caza*. Verificado en `escort_check.py`.
> **NO** sprint de pánico, **NO** corzos, **NO** drones que apantallen (post-v2), **NO** baseline.py.
> **Paso 3b — disparador realista: DETECTAR → ACERCARSE → CONFIRMAR.** El salto a ESCOLTA ya no es
> instantáneo a 100 m. Dos radios, tres fases: `r_detect`=100 m ("hay algo") → **SOSPECHA**;
> `r_confirm`=40 m ("es un lobo", confirmación **geométrica determinista**, placeholder hasta YOLO) →
> **ESCOLTA**. **Reflejo de investigación** (infraestructura, no decisión del coordinador): ante un contacto
> entra en **INVESTIGANDO** el dron ACTIVE **libre más CERCANO** al contacto (`_pick_investigator`; el más
> cercano llega antes; si está ocupado va el siguiente más cercano libre; desempate determinista por menor
> índice, **sin aleatoriedad**), vuela hacia el contacto (lobo más cercano) con el
> movimiento de 3a, y al llegar a `r_confirm` confirma y se **libera** al pool del coordinador. **Mensaje**
> legible por el coordinador en la observación (`investigations`: {drone_id, contact_pos, state}).
> **Precedencia**: mientras investiga, manda el reflejo (el coordinador no lo toca); el resto, el
> coordinador (Dummy = quietos). Verificado en `escort_check.py` (dos etapas, el dron se mueve y confirma,
> precedencia, mensaje, timing: SOSPECHA mediana ~251 → ESCOLTA ~298, hueco de investigación ~47 pasos) +
> sin regresiones. **NO** corzos (3c), **NO** clasificador (YOLO), **NO** guiado (paso 2). Animación del arco.
>
> **Paso 3a — MOVIMIENTO de drones (mecánica aislada).** Cuadricóptero **holonómico** con dinámica de
> vuelo (`drone_vel`): persigue un **waypoint** (`command_waypoint(i,(x,y))`) con `DRONE_MAX_SPEED`=15 m/s
> y `DRONE_MAX_ACCEL`=4 m/s², **acelera/cruza/frena y se para**. **Coste de batería por moverse** (flag #7):
> drenaje ACTIVE = flote × (1 + `DRONE_MOVE_DRAIN`·v/vmax) → flotar = suelo, reposicionar a tope ~2.5×.
> Verificado en **`drone_check.py`** (topes 15/4 exactos, mover drena 2.2× flotar) + sin regresiones.
>
> **Escala del mundo: campo 300×300 m (~9 ha) con ESCALA BIOLÓGICA ABSOLUTA.** El campo era ~100 m ≈
> `r_detect` (100 m) → no había sitio para que un lobo se acercara sin ser detectado (escolta en t≈0).
> Ahora el campo es 300×300 (×3) y `r_detect` sigue 100 m (= ⅓ del campo): los lobos salen del perímetro
> lejos, se acercan, y un dron los detecta a 100 m → **vigilancia previa real** (paso a ESCOLTA: mediana
> **~281 pasos**, antes ~0). Para que agrandar el campo NO desparrame nada, la **escala biológica se fija
> ABSOLUTA** (m, no fracción de `min(W,H)`): extensión del rebaño (`cow_spread`=**40**, `r_separation`=**22**,
> abiertos para que pasten DISPERSOS en el campo de 300 m — par afinable `HERD_SPREAD`/`HERD_SEPARATION`),
> cúmulo de spawn (`wolf_spawn_dispersion`=5) y **radios de combate/percepción** (`r_notice`=20,
> `r_face_safe`=6, `capture_radius`=3) — el lobo es un lobo a cualquier parcela. **Escala = LAYOUT**
> (establo, central, spawn, perímetro, `max_episode_steps`). `face_check` (modelo, invariante de escala)
> corre en el campo calibrado 100×100; la **fijación** se prueba a 300 (espaciado **~20 m**, dispersión 4 m).
> Tasa de episodio completo a 300 = **~87%** (igual que antes; solo tarda más). Todo verde.
>
> **Escolta · paso 1 — el TERMINAL (el "juez").** Antes de añadir guiado al
> refugio (bandera #13), se construye y verifica el terminal del episodio: **máquina de fases**
> `VIGILANCIA→ESCOLTA` (disparador = **DETECCIÓN por dron**: un dron EN VUELO ve un lobo a ≤ `r_detect`
> ≈100 m; sin retorno, informativa) + **terminal de 3 estados** evaluado cada step — **ÉXITO** (todas las reses
> vivas a salvo, ninguna cazada, ningún lobo dentro), **DEPREDACIÓN** (≥1 res cazada; **multi-muerte**:
> una captura ya NO termina el episodio → cuenta `n_depredadas`), **TIMEOUT** (`max_episode_steps`). Dos
> ganchos: (a) res en el establo = **a salvo** y no cazable (histéresis `refuge_margin`); (b) presa
> refugiada → la manada **re-selecciona** (única re-fijación). **Exclusión del lobo** re-asegurada tras
> el cono. Render: fase + reses refugiadas (verde) / cazadas (gris) + **banner del terminal**. Verificado
> en **`escort_check.py` (8 tests)** + **sin regresiones** (`face_check` 12/`battery_check` 4/2/2 verdes).
> Drones aún quietos, **SIN guiado** (es el paso 2). Tasa sin drones ≈ **88%** (medida; v1 congelado=49%
> OBSOLETO, v2 al final de la escolta).

---

## 1. Visión y contexto

Sistema multi-dron que **protege un rebaño de vacas de ataques de lobos**, desarrollado
**en simulación** como primer paso de lo que podría ser un proyecto en producción.

- **Inspiración real:** la empresa neozelandesa **Halter** (collares GPS con *virtual fencing*
  / *guided herding*: guían a las vacas con sonido y vibración, y solo como último recurso un
  pulso suave; enfoque centrado en el bienestar animal). Da el ancla industrial y la dimensión
  ético-social (competencia CG12 de la guía).
- **Idea central:** los **collares** hacen el guiado del rebaño (lo conducen a un refugio); los
  **drones escoltan** (forman una pantalla protectora entre los lobos y el rebaño, detectan y
  disuaden). No son los drones los que arrean a las vacas (una vaca no responde a un dron como
  una oveja a un perro).
- **Objetivo del trabajo:** hacer **dos versiones del "cerebro" (coordinador)** y compararlas:
  1. **Clásica = reflejo trivial**: unas pocas reglas escritas a mano que reutilizan la capa de
     movimiento (p. ej. cada dron va hacia el lobo más cercano e intenta interponerse entre él y la
     presa). **NO un FSM completo afinado** — eso se **descartó por demasiado costoso de programar y
     ajustar** para el alcance del TFG (ver §9/§11). Mantiene el eje *clásico* (controlador a mano).
  2. **Aprendida**: aprendizaje por refuerzo multiagente (MARL). Más avanzado.
  La **comparación** clásico vs aprendido sigue siendo el corazón del trabajo. La **columna de la
  evaluación** pasa a ser: **baseline sin drones + reflejo trivial vs MARL**, más las **ablaciones
  aprendido-vs-aprendido** (MAPPO vs IPPO, codificador invariante, currículo) y la **rejilla de
  robustez** (§5.1) — no la comparación contra un FSM elaborado.

---

## 2. Arquitectura del sistema

### 2.1. Tres capas (clave para reducir dificultad)

1. **Estabilización**: delegada a un autopiloto (PX4). No se programa el control de bajo nivel
   del dron (igual que en el TurtleBot se comandaba (v, w) y el simulador actuaba las ruedas).
2. **Guiado**: "ve a este waypoint / mantente / sigue a este objetivo" → emite referencias de
   velocidad. Se construye reutilizando el **pure pursuit** de la asignatura de robots.
   **Compartido** por las dos ramas.
3. **Coordinación**: decide *modos y objetivos* de alto nivel para cada dron. Es **lo único que
   se implementa dos veces** (reflejo trivial vs política MARL) y **lo único que se compara**.

> El espacio de acción de la capa 3 es de **alto nivel** (qué modo, qué objetivo), no
> velocidades crudas. Esto aísla la comparación al nivel de *decisión* y le quita dificultad al
> RL (elige entre pocas decisiones sensatas, no pilota).

### 2.2. Coordinador intercambiable

Interfaz fija `coordinador(observación) → acciones`. Se construye **el mundo una sola vez** y
detrás de esa interfaz se enchufan las dos implementaciones (**reflejo trivial** y MARL). Misma
observación entra, mismo formato de acción sale, mismo juez (métricas). Es lo que hace válida la
comparación. (El coordinador intercambiable no cambia; solo la implementación clásica es mínima.)

### 2.3. Modelo de información: descentralizado con comunicación (DECIDIDO)

Cada dron actúa por su cuenta con su vista parcial, pero comparten información barata:

- **Latido continuo (bajo ritmo):** cada dron emite periódicamente su estado básico
  (posición, batería, modo/rol). Va en la observación de los demás.
- **Evento de alerta (esporádico):** cuando un dron detecta una posible amenaza, avisa al resto
  (dónde está, confianza, quién la vio). Dispara la respuesta coordinada.

Decisiones de comunicación para la v1 (NO convertir el realismo de comunicación en otro eje de
comparación):
- **Fiabilidad:** comunicación perfecta (pérdidas = experimento de robustez posterior).
- **Latencia:** cero al principio.
- **Alcance:** comunicación **global** (todos oyen a todos). Si se quiere realismo, asumir que
  los collares/estación hacen de repetidor (como las torres de Halter), en vez de un radio
  entre drones (que dejaría incomunicados a drones separados por el perímetro).
- **Alerta = automática por umbral** en la v1 (si confianza > umbral, se emite). Dejar que la
  política decida *cuándo/qué* comunicar es extensión avanzada (ver banderas).

El esquema **CTDE** (entrenamiento centralizado, ejecución descentralizada) de MAPPO/QMIX encaja
exactamente con este despliegue descentralizado.

---

## 3. Interfaz de la capa de coordinación (observación y acción)

### 3.1. Observación de cada dron

- **Propio:** posición (x, y, z) y velocidad, nivel de batería, modo/rol actual, sector asignado.
- **Percepción (de YOLO o su sustituto):** ¿hay amenaza?, confianza de clase, rumbo (ángulo) y
  rango estimado a la detección — o el estado del lobo (posición, velocidad, incertidumbre) que
  produzca el filtro de estimación.
- **Rebaño (GPS de los collares, info compartida):** centroide, dispersión (radio que lo
  contiene), y la vaca más expuesta (la más cercana a la amenaza / más alejada del grupo).
- **Compañeros (por comunicación = latidos):** posición, batería y modo de los otros drones, y
  las alertas de amenaza emitidas.
- **Estación/cola:** ¿hay relevo disponible y en qué estado está la cola?

### 3.2. Acciones de cada dron

- **Movimiento (modo + objetivo, discreto para empezar):** ir a mi sector / ir a la amenaza /
  mantener / subir / bajar / volver a la estación. Lo ejecuta la capa de guiado (pure pursuit).
- **Eventos (discreto):** ladrar, pedir relevo de carga, iniciar/votar la escolta al refugio.

Notas:
- Empezar con acciones **discretas** (mejor para MARL y casi 1:1 con las salidas del **reflejo
  trivial** → misma interfaz real para ambas ramas). Velocidades continuas = extensión realista.
- **Número variable de vacas/compañeros:** la observación para el MARL debe ser de tamaño fijo
  → empezar con rasgos agregados (centroide, dispersión, k más cercanos); luego subir a un
  **codificador invariante a permutaciones** (Deep Sets o atención), que además da escalabilidad
  (entrenar con N vacas, evaluar con 2N). Para el reflejo trivial, basta iterar.

---

## 4. Modelo del mundo

### 4.1. Lobo — caza direccional (cono frontal + flanqueo + nº mínimo)  ✅ IMPLEMENTADO

Reutiliza el lobo de **Muro et al. (2011)** (*"Wolf-pack hunting strategies emerge from simple
rules…"*, Behavioural Processes 88(3), 192–197) pero lo hace **DIRECCIONAL** y con **PRESA COMÚN**:
1. **Presa COMÚN de la manada (commitment):** toda la manada comparte UNA presa fijada
   (`pack_prey` + `pack_prey_kind`), no "cada lobo la suya" (sin eso → N duelos, no pincer).
   **Selección** (`_select_prey`): si hay **terneros** → la presa es un ternero (override duro; con
   varios, el más accesible al centroide de lobos). Si NO → la adulta más **EXPUESTA** = la más LEJOS
   del centroide del **rebaño** (la del borde/descolgada; la "más céntrica" estaba protegida por las
   demás — era la queja). La lentitud reengancha **emergente** (la lenta se queda en el borde).
   **Fijación en t=0** (`_commit_initial_prey` en el reset, no se espera a que un lobo cruce
   `r_notice`): en modo caza (con ternero basta **1 lobo**; sin ternero, ≥ `n_min_adult`) la manada
   elige la presa y va a por ella **desde el primer paso**; el lobo solo sin ternero no se compromete.
   Se **mantiene** hasta que deja de ser cazable (MUERE o se REFUGIA). **MATANZA EXCEDENTE** (presa
   confinada: pasto cercado, reses clavadas): tras matar O refugiarse la presa, el paquete **RE-FIJA la res
   viva no-a-salvo MÁS CERCANA** al centroide del paquete (`_recommit_nearest_prey`) y **SIGUE** cazando
   **hasta agotar** objetivos (todas muertas o a salvo) → la **SEVERIDAD** (cabezas perdidas) es la métrica.
   Al **agotar** (`_targets_exhausted`) el paquete **se DESENGANCHA y FRENA** (coastea a parada; no orbita —
   mantiene la firmeza de `face_check` test 3). La **caza en sí** (cono / flanqueo / fijación en t=0 / rodeo)
   es IDÉNTICA; solo cambia **a quién se re-fija después y cuándo para**. Se quitó el abandono por distancia
   (`prey_abandon_dist` **DEPRECADO**). `n_refix` cuenta SOLO re-fijaciones por **refugio** (oscilación); la
   muerte re-fija pero no es oscilación. *(Histórico: `1d44cdc` introdujo `pack_sated` = máx. 1 caza/ep,
   REVERTIDO aquí — en presa confinada el paquete excede.)* Verificado: multi-caza, re-fijar-a-la-más-cercana,
   re-fijar-tras-refugio, parar-al-agotar.
2. **Aproximación respetando el cono frontal + ATAQUE ENVOLVENTE:** si el lobo está **en el cono** de la
   presa (±45°) **circula** hacia el flanco manteniendo `r_face_safe`; si está en el **flanco/grupa** **cierra
   a matar**. El standoff de Muro pasa de omnidireccional a **solo en el cono**. **Envolvente**
   (`_envelop_slots`, `wolf_envelop_gain`): el paquete reparte sus rumbos en ángulos **EQUIESPACIADOS**
   alrededor de la presa (N→2π/N; 4→~N/E/S/O), anclado al ángulo medio actual → los lobos salen del cono a
   flancos LIMPIOS y la presa **clavada** no puede cubrir todos los costados. **Imprescindible contra una
   adulta CLAVADA** (parada): sin reparto se apiñan en el cono y "dar la cara" los mantiene a TODOS a raya
   (era invulnerable, regresión arreglada).
3. **Regla de número mínimo (`n_min_adult`=2):** un lobo solo **NO ataca** (standoff amplio
   `r_standoff`, sin fijar presa). Con ≥ `n_min_adult` lobos, la **manada sí**.
4. **Repulsión entre lobos** alrededor de la presa única → reparto angular = **pincer** (uno de
   frente, los demás a los flancos). **Banda muerta** (`cone_band`) → no entra-sale en el borde.
5. **Spawn por sector** (`_spawn_wolves_sector`): todos los lobos salen **agrupados** de un mismo
   sector del perímetro (sorteado por episodio, RNG) → la manada llega **junta y de una dirección**
   (dispersión del cúmulo `wolf_spawn_dispersion`). De paso **aleatoriza la dirección de ataque**
   entre episodios (avanza la bandera #4, útil para que el MARL no memorice de dónde viene el ataque).
6. **Bordear el rebaño, no atravesarlo** (`wolf_skirt_gain`): si las **no-presa** se interponen entre
   el lobo y la presa, una **componente TANGENCIAL** (perpendicular a lobo→presa, hacia el lado opuesto
   al cúmulo, comprometida con un lado) hace que el lobo **arquee alrededor** del rebaño-obstáculo
   (centroide + extensión + `wolf_skirt_margin`) hasta el costado de la presa, en vez de beelinear y
   atascarse contra las vacas que lo encaran. Tangencial (no repulsión radial, que lo dejaría parado de
   frente). La repulsión entre lobos los reparte a lados distintos → flanqueo desde varios costados.

**Muerte por FLANQUEO (según el tipo de presa):**
- **Adulta:** muere con **≥ `n_min_adult` lobos** a la vez dentro de `capture_radius` y fuera de su
  cono. Con 1 lobo (encarado) → no muere.
- **Ternero:** muere con **≥ 1 lobo** dentro de `capture_radius` del ternero y fuera del cono de su
  **defensora** (la madre encara a uno; un lobo por el flanco que no cubre llega a la cría).
**Instrumentado (#3)** (`_instrument_flanking`): cuenta lobos en `capture_radius` y flanqueadores
válidos (umbral 1 para ternero, `n_min_adult` para adulta), primer quórum y si dispara la muerte, y
desglosa los "toques". **Confirmado: con quórum → muerte** (era síntoma de #2). **TERNEROS**
(§4.2): la manada caza al ternero 38/40; **lobo solo vs ternero = 0%** (la madre siempre frena con los
parámetros actuales; spec: reportar, **no tunear** `face_cooldown`/`r_face_safe` aquí).

**Número de lobos aleatorio por episodio** (1–5): de lobo solitario (no puede) a manada (sí puede).
**Escalera de adversarios:** ingenuo → **manada direccional (ACTUAL)** → busca-huecos → con amago
(los dos últimos cuando los drones se muevan).
**SUSTO DE DOS RADIOS del dron ✅ IMPLEMENTADO (v2.7; extiende el susto por movimiento de v2.4)** (`_apply_deterrence`,
infraestructura gateada por `escort_enabled`): el miedo del lobo depende de **si el dron SE LE ECHA ENCIMA** (los depredadores se
HABITÚAN a disuasores estáticos A DISTANCIA), pero un lobo **NO CRUZA** un obstáculo que tiene **ENCIMA**. Modelo fiel a los datos
de fuga (FID: huida media ~106 m ante una amenaza que se acerca, rango 17–310; escalado al campo 300×300). **DOS radios anidados
(mover > quieto, SIEMPRE):** **(a) EXPULSIÓN PLENA (radio GRANDE `DETER_RADIUS`=20 m, v2.4 INTACTA):** dron **ACERCÁNDOSE** (aprox.
`> SCARE_APPROACH_MIN`=1.0 m/s) → el lobo **HUYE** RADIAL del dron acercándose MÁS CERCANO, `clip(wolf_speed·(1−d/R), SCARE_SPEED_MIN=0.8,
wolf_speed)`; la huida **SUSTITUYE** a la caza y **NO mata mientras huye** (`_wolf_scared` excluido de `_process_predation`). **(b)
PARED BLANDA (radio PEQUEÑO `STATIC_DETER_RADIUS`=10 m = la mitad, v2.7 NUEVO):** un dron **ACTIVE** (aunque esté **QUIETO** o
alejándose) a `≤ STATIC_DETER_RADIUS` y lobo NO expulsado → el lobo **NO CRUZA** hacia el dron: se le **quita la componente de
velocidad que apunta al dron** (se desliza/desvía) y se le suma un **empuje radial saliente de frenado** (crece al acercarse,
`STATIC_DETER_GAIN`=0.6, acotado a la rapidez de caza) → **FRENA y DESVÍA, no lanza** (más débil que la huida plena). Marca
`_wolf_walled` → **NO mata a través** del dron (excluido de `_process_predation`). Un dron estático a `> STATIC_DETER_RADIUS`
**NO tiene efecto** (habituación al disuasor estático a distancia, v2.4 preservado: un poste LATERAL se rodea). **Jerarquía:** si
además se acerca (dentro de `DETER_RADIUS`), la **EXPULSIÓN DOMINA** (radio mayor + más fuerza) → moverse hacia el lobo es
**ESTRICTAMENTE mejor** que estar quieto (preserva el incentivo a moverse que el MARL run01 ya aprendió). EXPULSADO ≠ rendido: al
salir de ambos radios el lobo retoma la caza (sin cooldown). Marca `_drone_scaring` (drones que embisten) → el render dibuja 🔊 solo
al embestir de verdad. Solo en escolta (combate puro `escort_enabled=False` NO asusta ni amuralla, `_wolf_scared`/`_wolf_walled`/
`_drone_scaring` todo False → **face_check bit a bit**, fingerprint de combate idéntico v2.3≡v2.4≡v2.7). **Efecto de diseño:** el
dron quieto vuelve a REPELER a corta (deja de ser un poste atravesable) → la barrera se hace **PARED** y el CEBO multi-frente gana
presión selectiva (una barrera atravesable no había que engañarla). **RE-MIDE la baseline (v2.7, metro DGX, 100/tipo):** Dummy
4.42/0/4.34 → **3.97/0/3.89** (Δ −0.45/−0.45: sus drones CLAVADOS ya repelen a corta —la pared no exige moverse—; n_safe 2.73/2.81),
Reactive 2.74/0/2.82 → **2.30/0/2.42** (Δ −0.44/−0.40: la barrera se hace pared, defiende mejor; n_safe 4.57/4.45); el margen
Reactive−Dummy se mantiene (−1.67/−1.47). Es MEDIDA, no objetivo (no se tuneó `STATIC_DETER_RADIUS`/`STATIC_DETER_GAIN`). **Este
cambio INVALIDA la baseline del MARL de drones run01** (medido sobre v2.6, barrera atravesable): run01 queda como resultado histórico
sobre v2.6; el MARL se reentrenará sobre v2.7 (nueva nota a batir **2.30/0/2.42**) en una fase posterior. EKF de estimación del lobo:
PENDIENTE (ver plan).

### 4.2. Vacas adultas — "DAR LA CARA" (confrontación direccional)  ✅ IMPLEMENTADO (+ guiado al refugio ✅)

Modelo de amenaza basado en cómo cazan los lobos de verdad: **el ganado grande no se apiña, planta
cara** (se gira al lobo y lo confronta); el lobo va a la débil y ataca por el flanco/grupa, evitando
la cabeza. *(Sustituye al modelo de apiñamiento: al medirlo, el huddle quedaba **más apretado** que
el pasto y se tragaba a la rezagada → nadie aislado a quien cazar limpiamente. Se conservan pasto
disperso y heterogeneidad de velocidad.)*

**🐮 TERNEROS (0/1/2) + DEFENSORAS  ✅ IMPLEMENTADO:** nº de terneros sorteado en el reset (RNG
sembrado, fijo en el episodio; array `calves`). Cada ternero recibe en el spawn una adulta
**defensora** fija (`calf_defender`, su "madre"), y nace **a un lado** de ella (a `calf_personal_space`,
no encima). El **ternero** se mantiene **AL LADO** de su defensora mediante un **muelle a longitud
natural = `calf_personal_space`** (~1.5 m; tira si se aleja, separa si se le echa encima) + deambular
leve, con inercia; **NO encara, NO huye** (indefenso; su protección es la madre). La **defensora** se
ancla a su cría con el **mismo muelle recíproco** (`k_defender_anchor`) → se queda junto a ella
(dist media verificada **1.46 m**) y la encara con la lógica normal — sin interposición, solo
"quédate junto a tu cría y dale la cara". El lobo
prefiere al ternero (override en `_select_prey`) y, al rodear el cono de la madre, el flanco que ella
no cubre llega a la cría → muere con **1 flanqueador**. **Nota (a verificar, NO tunear):** lobo solo
vs ternero salió **0%** (la madre frena siempre con los parámetros actuales); se afina en otro paso.

- **Pasto (sin amenaza cerca):** disperso, **repartido**, tranquilo y **casi quieto** = separación +
  **deambular firme** (paseo **angular lento** del rumbo) + valla blanda. **SIN cohesión/apiñamiento y
  SIN huida.** Espaciado de equilibrio amplio y ABSOLUTO (`cow_spread`=40 m = zona de pasto/valla blanda,
  `r_separation`=22 m ≈ 0.55·`cow_spread`; par `HERD_SPREAD`/`HERD_SEPARATION` afinable por render):
  vecino más cercano medio **~20 m** en el campo de 300 (rebaño disperso, no apelotonado). La suma de fuerzas ya **NO se normaliza a `cow_speed`**
  (antes pastaban a tope siempre); su **magnitud** es la rapidez (capada a `cow_speed`), así que
  `wander_calm` fija la rapidez de pastoreo (verificado **0.019 m/paso** vs 0.120 a tope), mientras
  separación/valla/ancla siguen reaccionando fuerte.
- **Dirección de confrontación (`cow_heading`, estado nuevo):** con un lobo dentro de `r_notice`, la
  vaca **gira a encarar** al más amenazante (el más cercano que se acerca) a velocidad angular máx
  `turn_rate` (suave, no salto instantáneo).
- **Cono de seguridad frontal (`cone_half_angle`=45°, `r_face_safe`):** un lobo dentro del cono y a
  < `r_face_safe` es **empujado** (acotado por paso, sin teletransporte) a `r_face_safe` — le planta
  cara. Fuera del cono (flancos/grupa) **no hay repulsión**: el lobo entra.
- **Enfriamiento de giro (`face_cooldown`):** tras encarar a un lobo, espera antes de re-encarar a
  otro → **mientras está comprometida con uno, el flanco queda abierto** (la ventana que la manada
  explota). Es la clave del pincer: **no puede dar la cara a todos**.
- **Débil emergente:** velocidad heterogénea (`cow_speed_jitter`); la **más lenta** es la débil →
  objetivo del lobo (sin terneros).
- **Inercia (bandera #1, ahora para vaca y lobo):** llevan **velocidad en el estado**; el
  desplazamiento suaviza la dirección hacia la deseada (no salta). Movimiento **firme**, verificado:
  giro medio ~**0.05 rad/paso** (vacas, terneros y lobos); la vibración daría ~π/2.
- **Verificación (`face_check.py`):** 1) lobo solo → 0 muertes, lo mantiene a `r_standoff`=12 m;
  2) manada → encara a uno, los demás flanquean, **muere la débil** con ≥2 flanqueadores; 3) métrica
  de tembleque baja + pastoreo casi quieto (0.019 m/paso); 4) **tasa sin drones = 88%** (no se
  persigue); 5) reproducible.
- **Escolta — GUIADO al refugio ✅ (paso 2 + NO-HOLONÓMICO):** en `ESCOLTA` la vaca corre **HACIA DONDE
  MIRA** (no-holonómico; una vaca real no corre mientras encara). Huir y dar la cara son **EXCLUYENTES**:
  **HUIR** (no es la presa fijada) → gira el `cow_heading` a `turn_rate` hacia un rumbo objetivo que **MEZCLA**
  hacia-el-establo (`W_REFUGIO`, domina el neto) + **alejándose de los lobos cercanos** (`W_EVITAR`·Σ con
  *falloff* dentro de `COW_AVOID_RADIUS`=30 m) → **RODEA** a los lobos en su camino (no atraviesa la pelea) y
  avanza **de frente** a `cow_speed` (la velocidad es **siempre a lo largo del heading**, nunca lateral → el
  flanco/grupa queda expuesto; el rodeo emerge del no-holonómico: arquea sin frenar); la evitación es LOCAL
  (falloff) → el establo sigue ganando y la vaca **llega**; **ENCARAR/PIN** (lobo dentro de `r_notice`) → gira a encararlo y **se PARA**
  (no avanza al refugio hasta que el lobo se va). **Solo la PRESA fijada** por el paquete (y su defensora si
  es ternero) puede ENCARAR; las **no-fijadas siguen HUYENDO** aunque tengan lobos en `r_notice` (el paquete
  está comprometido con UNA presa, no con ellas). Esto crea el **pin**: los lobos **CLAVAN** a la presa (uno la
  fija, otro la flanquea = pin-and-flank), y hace concreto el trabajo del dron: **despejar lobos para que la
  vaca reanude la huida**. El cono/`face_cooldown` aplican igual; los terneros migran **anclados** a su
  defensora (la pareja para/huye junta) y se marcan a salvo **solo cuando el ternero está dentro** (sigue
  migrando hasta entrar él, aunque su madre ya esté a salvo). **La MADRE no abandona al ternero:** el ternero
  huye a su rapidez propia `calf_speed`=0.8 m/s (< `cow_speed`; la cría es más lenta) y una **DEFENSORA que HUYE
  no lo ADELANTA** → su avance se capa a `calf_speed` (la más lenta de la pareja) → migran **JUNTAS** a ese ritmo
  → la pareja es **más LENTA = más vulnerable** (los depredadores van a por las crías; trabajo claro para los
  drones: proteger a la pareja lenta). Solo mientras el ternero siga en juego; si ENCARA, avanza 0 (el pin manda).
  **Pastoreo/combate sigue HOLONÓMICO e intacto** (face_check no se
  toca: en pastoreo las vacas están casi quietas → la restricción no cambia nada ahí). El dron que **despeja
  el pin** ya existe: ver **DISUASIÓN ✅** (§4.1) — un dron ACTIVE cerca hace al lobo esquivar+frenar y sale
  de `r_notice` → la vaca reanuda. Pendiente: **POSICIONAMIENTO del coordinador** (mandar los drones a
  interponerse, post-v2). "Escolta" = proteger el traslado, no empujar.

### 4.3. Batería y estación de carga  ✅ IMPLEMENTADO (mecánica del mundo)

**Implementado** (`world.py: _init_battery/_step_battery`, verificado en `battery_check.py`):
máquina de estados por dron **`READY → INCOMING → ACTIVE → RETURNING → CHARGING → READY`** (+ `STRANDED`);
batería fracción [0,1] con tasas DERIVADAS (`drain=1/600 s⁻¹`, `charge=1/300 s⁻¹`); **arranque escalonado**
(RNG, solo en operación continua).
**RELEVO REALISTA (hand-off, SIN teletransporte):** cuando un ACTIVE baja de `announce_threshold`=0.20 se
**CLAVA en su puesto** (sigue cubriendo/disuadiendo; el coordinador ya no lo comanda —`drone_relief_hold`—) y
la central **DESPACHA al READY más cargado**, que **VUELA** hasta el puesto (`INCOMING`, la reserva se mueve de
verdad con la dinámica de vuelo). Al llegar **ENCIMA** (≤ `relay_handoff_tol`=2 m) → **hand-off**: el relevo pasa
a `ACTIVE` y el bajo a `RETURNING` (vuela a la central → al entrar `CHARGING`). **Cobertura CONTINUA** (el bajo
NO se va hasta que llega el relevo). Sin reserva lista, el bajo sigue drenando; si llega a ~0 → **`STRANDED`**
(en el puesto, SIN disuadir —ya no es ACTIVE—, hasta el hand-off): el hueco de cobertura real que un buen
coordinador debe evitar (no agotar la flota moviéndose de más). El **tiempo de vuelo del relevo EMERGE** de la
dinámica (ya no es un hook fijo). Régimen permanente verificado: **~4 ACTIVE / ~2 CHARGING / ~2 READY** (+ tránsito
INCOMING/RETURNING ocasional), ~1 hand-off cada ~118 s, 4 puestos SIEMPRE cubiertos a carga hover (STRANDED solo
bajo estrés), **sin saltos de posición** (salto máx/paso = tope físico). Es **automático** (regla del mundo, no
acción del coordinador); **NO usa el RNG** (determinista → dinámica vaca/lobo intacta, face_check bit a bit).
**Hooks REALIZADOS**: `RETURNING` (antes sin usar), travel-time (ahora emergente), `drone_stranded`;
`battery_activity` (coste de persecución/movimiento, #7) sigue multiplicando el drenaje.

Diseño de referencia (sigue válido):
- **8 drones**: 4 activos + 4 en reserva cargando. **Batería = 10 min, carga = 5 min** (elegido
  para ver bien los relevos). Ratio vuelo:carga = 2:1 → para 4 activos continuos hacen falta 6;
  con 8 hay holgura (en régimen permanente: 4 volando, ~2 cargando, ~2 listos).
- **Cola de carga** (no emparejamiento fijo): cuando un dron activo avisa de poca batería, sale
  de la central el **más cargado**. El dron avisa "cuando le quede la justa para aguantar hasta
  que llegue el relevo" (cubre hasta el recambio → cierra el hueco de cobertura).
- **Desincronizar** ciclos (arranque escalonado de batería) para que los relevos no se junten.
- Supuesto provisional aceptado: *"mientras resuelve un problema no pierde batería"* — pero OJO,
  es irreal (perseguir es cuando MÁS se gasta) y lo mejor es que perseguir sí gaste y que el dron
  nunca se comprometa a una persecución que no pueda costear (proteger la reserva de retorno).
  Marcado como supuesto a relajar.
- El negativo por "dron tirado lejos sin batería" en la recompensa **sigue haciendo falta** (la
  seguridad por construcción del ratio 2:1 solo vale en patrulla; persiguiendo se puede quedar
  tirado).

### 4.4. Estructura de episodio + TERMINAL (el "juez")  ✅ IMPLEMENTADO (+ guiado al refugio ✅)

Tarea **episódica** (terminal claro, bueno para RL). **Máquina de fases** (`world.phase`):

`VIGILANCIA` → **DETECTAR** (un dron **EN VUELO** `ACTIVE` tiene un lobo ≤ `r_detect`=100 m; los aparcados
no vigilan) → `SOSPECHA` → **ACERCARSE** (REFLEJO de investigación: entra en `INVESTIGANDO` el dron ACTIVE
**libre más CERCANO** al contacto —`_pick_investigator`, el que llega antes; ocupado→siguiente libre;
desempate determinista por menor índice— y vuela hacia el contacto con el movimiento de 3a) → **CONFIRMAR** (a ≤ `r_confirm`=40 m; geométrico,
determinista — placeholder hasta YOLO) → `ESCOLTA` (el dron se libera al coordinador) → **terminal**.
La fase es informativa y **no vuelve atrás** (sin SOSPECHA→VIGILANCIA: innecesario sin corzos, llega en 3c).
En `ESCOLTA` se activa el **GUIADO al refugio** (paso 2 ✅), con movimiento **NO-HOLONÓMICO**: la vaca corre
hacia donde mira → **HUIR** de frente al establo a `cow_speed` (sin lobo en `r_notice`) o **ENCARAR/PIN** (gira
al lobo y se PARA, si lo hay dentro de `r_notice`); excluyentes → los lobos **clavan** a la presa (pin-and-flank).
Es INFRAESTRUCTURA del mundo, gateada por la fase (`escort_enabled`), NO el coordinador — igual para todos.
Pastoreo/combate sigue **holonómico** (face_check intacto). El reflejo emite un **mensaje** en la observación (`investigations`) que el
coordinador podrá leer; **precedencia**: el reflejo manda sobre el dron que investiga, el coordinador sobre
el resto.

**Terminal (3 estados, evaluado cada step; multi-muerte: una captura ya NO termina el episodio):**
- **ÉXITO** = todas las reses **vivas** a salvo (refugiadas) **y** ninguna cazada **y** ningún lobo
  dentro del establo.
- **DEPREDACIÓN** (fracaso/parcial) = se resuelve / agota el tiempo con **≥ 1 res cazada**. Cuanta
  más, peor → se devuelve como **cuenta** (`n_depredadas`); el escalado de recompensa es de la Fase 3.
- **TIMEOUT** = se agota `max_episode_steps` sin éxito y sin cazadas (p. ej. lobo solo que no puede).
- El episodio **se RESUELVE** cuando no queda ninguna res cazable (todas a salvo o cazadas) o por tiempo.
  `step()`/`info` devuelven **estado, n_safe, n_depredadas, n_fuera, terminal_step**.

**Dos ganchos del refugio** (lo único que toca el flanqueo/presa, por diseño):
- (a) Toda res que entra al establo se marca **a salvo** (`cow_safe`/`calf_safe`, con histéresis de
  borde `refuge_margin`) y sale del conjunto **cazable** (`_select_prey` y el flanqueo la ignoran; se
  congela dentro del establo, no se la expulsa).
- (b) Si la **presa fijada** se refugia, la manada **re-selecciona** presa — la **ÚNICA re-fijación**
  permitida (`n_refix`+1 solo al refugiarse; la muerte de la presa también re-selecciona, pero no cuenta).

**Exclusión del lobo (clamp #5):** ningún lobo entra nunca al establo; el empuje del cono (vacas que
pastan cerca del borde) podría meterlo, así que se re-aplica el clamp como ÚLTIMA palabra del step.

- `r_detect`=100 m (criterio DRI de Johnson reconocer/identificar — ~8-13 px sobre un lobo de ~1,2 m,
  GSD ~1,2 cm/px a ~52 m AGL, patrulla ~40-50 m, margen por ángulo oblicuo/movimiento → ~80-120 m;
  horizontal porque la z del dron aún es conceptual (flag #2); candidato a eje de robustez §5.1);
  `max_episode_steps`=`episode_time_factor`·diag/`cow_speed`/`dt` (~4× cruzar el campo); `refuge_margin`=0.1·`safe_radius`.
- `r_confirm`=40 m (DRI **identificación de especie** — ~130 px sobre el lobo a esa distancia). La
  **confirmación es geométrica y determinista**: como por ahora solo hay lobos, siempre confirma «sí»
  (placeholder). Con YOLO pasará a una **curva de confianza-vs-distancia** (flag #10) y los **corzos** (3c)
  harán que el «¿es un lobo o no?» signifique algo (y habilitan la rama de abortar SOSPECHA→VIGILANCIA).
- La **disuasión (ladrido) ✅** es una **táctica durante la escolta** (ganar tiempo: despejar el pin para
  que la vaca reanude), no la condición de victoria. La victoria es resguardar. Guiado al refugio ✅ +
  disuasión del dron ✅; falta el **POSICIONAMIENTO** del coordinador (interponer los drones) y la
  **habituación** del lobo (flag #6).

---

## 5. Métricas (juez compartido) y recompensa (solo RL)

> **Distinción clave:** las **métricas** juzgan ambas ramas; la **recompensa** solo entrena el
> MARL. El reflejo trivial no usa recompensa (es a mano), pero se le juzga con las mismas métricas.

### 5.1. Métricas (perfil, no un número único)

- **Resultado:** tasa de éxito (todas resguardadas), nº de depredaciones por episodio, tiempo
  hasta resguardar. (La verdad, pero ruidoso.)
- **Indicadores adelantados (menos ruidosos):** latencia de detección, cobertura (fracción del
  área alrededor del rebaño vigilada en el tiempo), huecos de cobertura.
- **Coste/eficiencia:** energía/distancia volada, eventos de dron tirado (~0 en buen sistema),
  falsas alarmas.
- **Robustez (la rejilla del paper):** estrategias de lobo × tamaño de rebaño × nº de drones ×
  (más tarde) pérdidas de comunicación. **Varias semillas e intervalos de confianza.**
- Reportar resultado + adelantados juntos. Hay tensiones (protección vs energía; rapidez vs
  falsas alarmas) → el frente de Pareto es un resultado en sí mismo.
- **Justicia:** medir **ambas ramas con las mismas métricas**. La rama clásica es un **reflejo
  trivial** (no se afina a fondo: pocas reglas a mano), así que la equidad de la comparación no
  descansa en "afinar un FSM" sino en contrastar el MARL contra **varios puntos de referencia
  honestos**: el **baseline sin drones** (cota inferior), el **reflejo trivial** (controlador a mano
  mínimo) y las **ablaciones aprendido-vs-aprendido** + la **rejilla de robustez**. El MARL tiene que
  batir a esos referentes para que "gana el MARL" signifique algo.

### 5.2. Recompensa (solo MARL)

**Principio nº1:** no recompensar *proxies* (acercarse, cubrir, ladrar, compactar) → eso es
*reward hacking*. Recompensar **resultados** y dejar que el comportamiento emerja.

Para densificar la señal sin abrir agujeros: **shaping basado en potencial** (Ng, Harada &
Russell, 1999): `F(s,s') = γ·Φ(s') − Φ(s)` → **demostrado** que no cambia la política óptima
(no crea óptimos explotables; oscilar da cero neto). *(Estrenado ya en la fase de LOBOS:
run02 entrena con Φ = −β·dist media del paquete a la presa designada — ver el patch del
plan B en la cabecera y `rl/wolf_env.py`; verificado en rl_env_check test 8.)*

Componentes propuestos:
- **Negativo grande compartido** cuando un lobo alcanza a una vaca (el resultado a evitar).
- **Positivo compartido** cuando una amenaza se repele (atado al resultado "el lobo se retira",
  no a la acción de ladrar — además la habituación ya castiga el spam en la dinámica).
- **Shaping por potencial** Φ = progreso del rebaño al refugio (p. ej. `Φ = −(nº de vacas aún
  fuera)` o `−(suma de distancias de las vacas a la zona segura)`), + cobertura del sector
  amenazado.
- **Coste de energía por paso, individual**, pequeño.
- **Negativo grande individual** por quedarse tirado sin batería lejos de la estación.
- **Crédito multiagente:** recompensa de **equipo compartida** para el resultado + términos
  **individuales** (energía, tirado) para evitar *free-riding*. El crítico centralizado de CTDE
  ayuda al reparto.

**Validación obligatoria:** comprobar que **la recompensa correlaciona con las métricas** (las
políticas de más recompensa puntúan mejor en depredación/cobertura/etc.). Si divergen, la
recompensa está hackeada — saberlo antes de la defensa.

---

## 6. Herramientas (y en qué fase entra cada una)

| Herramienta | Para qué | Fase |
|---|---|---|
| **Python** | lenguaje base | todas |
| **NumPy** | física del mundo (posiciones, batería, visión) en arrays | 1–4 |
| **matplotlib** | **solo dibujar/animar** (la "ventana", como la vista 3D de CoppeliaSim) | 1–4 (local) |
| **Claude Code** | escribir el código mientras tú diriges | todas |
| **PettingZoo** | API estándar multi-agente (adaptador para el MARL) | 3 |
| **MAPPO + BenchMARL (TorchRL)** | entrenar la coordinación (CTDE). BenchMARL = hecho para benchmarking reproducible | 3 (en DGX) |
| **YOLO26** | detección real del lobo (cámara) | 5 |
| **CoppeliaSim + ROS 2** | demo 3D realista (despliegue de la política entrenada) | 5 |

> **matplotlib NO es el simulador.** El simulador es tu `world.py` (hace la física). matplotlib
> solo dibuja; podrías quitarlo y la simulación funcionaría igual (a ciegas). El "realismo" está
> en lo bien modelados que estén sensores y dinámica, **no en los píxeles**.

> **Elección de algoritmo:** empezar por **MAPPO** (robusto, perdona, maneja recompensa mixta,
> CTDE = tu despliegue). **IPPO** como sanity-check/ablación (si IPPO ≈ MAPPO, el crítico
> centralizado no aporta → hallazgo). **QMIX** como contraste value-based opcional.

> **No entrenar a través de ROS/CoppeliaSim** (lentísimo): entrenar en el sim ligero y
> **desplegar la política entrenada como nodo ROS 2** solo para la demo (Fase 5).

---

## 7. Entorno de cómputo: servidor DGX de Comillas

- **Hardware:** 8 × **NVIDIA H200** (143 GB VRAM c/u). Son GPUs de cómputo puro (Hopper),
  **sin núcleos RT** → buenísimas para entrenar MARL y YOLO; flojas para renderizado
  fotorrealista (pieza ya minimizada). Blender (datos de YOLO) funciona bien (usa CUDA).
- **Cuándo entra:** Fase 3 (entrenar MARL) y Fase 5 (entrenar YOLO). **Fases 1 y 2 = portátil.**
- **Flujo:** VPN GlobalProtect → VS Code Remote-SSH a `tucódigo@dgx.comillas.edu` → trabajar por
  **Docker** (contenedor aislado). Editar en local → `git push` → en DGX `git pull` → lanzar.
- **Almacenamiento:** código en `/workspace`, datasets/checkpoints/logs/resultados en
  `/workdata` (persiste; el contenedor es efímero).
- **Buenas prácticas:** `container_name` con tu código de alumno (evita choques), `count: 1` GPU
  (MAPPO no necesita más), elegir GPU libre con `nvidia-smi` + `export CUDA_VISIBLE_DEVICES=<n>`,
  `docker compose down` al terminar.
- El valor del DGX para este proyecto es la **velocidad** (muchas semillas × configuraciones para
  la comparación), no la memoria (la política es diminuta). Las animaciones se **guardan y se
  descargan** (no se ven por SSH).
- **HECHO (fase RL de lobos): el contenedor del PROYECTO vive en `docker/`** (imagen calcada de la del
  lab + mismo `requirements.txt` lockfile — torch/gymnasium/SB3/tensorboard pinned; `pettingzoo`/`benchmarl`
  se añadirán con la fase de drones). **Flujo de trabajo en la DGX:** `mkdir -p ~/rl_data` (una vez) →
  `cd docker && docker compose up -d --build` → `./conectar.sh` (bash como jovyan en `/workspace` = el repo)
  → dentro: correr la VERJA (`python face_check.py` … `python rl_env_check.py`), reproducir la baseline
  (`python baseline.py`) y entrenar (`python rl/train_wolves.py --smoke --outdir /data/wolves/smoke`);
  los checkpoints/logs/TensorBoard quedan en `~/rl_data` del host (= `/data` del contenedor, FUERA del
  repo) → al terminar la sesión, `docker compose down` (buen vecino). OJO: el python3 del HOST no tiene
  numpy — TODO corre dentro del contenedor.

---

## 8. Plan de implementación por fases

- **Fase 1 — Mundo compartido + arnés + métricas.** Simulador ligero (Python/NumPy, sin render
  en el bucle), entidades, dinámica, episodio, registrador de métricas, **sustituto de
  percepción** (confianza de detección según distancia/altitud). Entregable: episodio ejecutable
  con métricas.
- **Fase 2 — Coordinador clásico = reflejo trivial (línea base mínima).** Pocas reglas a mano
  detrás de la interfaz, reutilizando la capa de movimiento (p. ej. cada dron va al lobo más
  cercano e intenta interponerse entre él y la presa) + pure pursuit. **No** un FSM completo
  afinado (descartado por coste). Medirlo con las mismas métricas. Entregable: sistema completo +
  números base. **Fases 1+2 = proyecto defendible por sí solo (red de seguridad).**
- **Fase 3 — Coordinador MARL.** Envolver el mundo en PettingZoo (solo aquí; la rama clásica no
  lo necesita). Política con codificador invariante a permutaciones. Entrenar con MAPPO
  (BenchMARL). Validar recompensa↔métricas. Currículo (fácil→difícil). Entregable: política +
  curvas.
- **Fase 4 — Comparación (columna del paper).** Misma batería de evaluación, varias semillas,
  intervalos de confianza, tablas + frente de Pareto. Entregable: sección de resultados.
- **Fase 5 — Percepción real + demo ROS 2 (si da tiempo).** Entrenar YOLO26 con datos
  renderizados (Blender) y autoetiquetados; demo en CoppeliaSim + ROS 2 con la política
  desplegada. Entregable: validación cualitativa + vídeo.

**Avisos de MARL:** mucha varianza entre semillas (reportar intervalos); la comprobación
recompensa↔métricas no es opcional; currículo; **los referentes son tu mejor depurador** (si el
MARL **no bate al reflejo trivial / al baseline sin drones**, hay un bug). Sin render en el bucle →
el DGX va sobrado.

---

## 9. Estado actual del código

Carpeta `AI_LAB/` (proyecto Python local). Estructura:
- `world.py` — clase `World`: estado, dinámica, recompensa, **terminal de escolta + máquina de fases + guiado al refugio NO-HOLONÓMICO** (`escort_enabled`). **Sin** ROS/render dentro.
- `render.py` — animación matplotlib (por reproducción: lee estado, nunca llama a `step`). **Entidades como EMOJIS de color** (🐄 vaca / 🐺 lobo / 🦌 corzo / 🐗 jabalí / 🚁 dron / ternero): matplotlib no pinta emojis a color, así que se renderizan con **PIL `embedded_color`** (fuente de emoji del sistema) a **sprites RGBA** colocados con `AnnotationBbox` → color de verdad, sin "tofu"; tamaño **`EMOJI_SCALE`** (afinable, pequeños); la distracción se dibuja 🦌 o 🐗 según `distraction_species`; **fallback** a marcadores (scatter) si no hay PIL/fuente. **Barra de batería** sobre cada dron ([0,1], verde llena → roja casi vacía; sube cargando / baja volando; lee `battery` del snapshot, que añade `main.py`). Además: **cono** ±45°, realce de **presa fijada**/**defensora**, **línea ternero→defensora**, **radio de disuasión** de los ACTIVE, muertas/descartados **atenuados**, **FASE**, **línea del INVESTIGADOR**, **banner del terminal**, leyenda (emojis + estructura).
- `coordinators.py` — `DummyCoordinator` (no comanda nada → drones mantienen waypoint = quietos, BASELINE) y **`ReactiveCoordinator`** (1er coordinador CLÁSICO, regla FIJA: **BARRERA de apantallado** entre la manada y las vacas más cercanas + PATRULLA sin amenaza + caso PENETRADO; solo comanda a los ACTIVE libres, no usa la presa fijada, no toca `world.py`). MARL después. El movimiento es capacidad del mundo (`command_waypoint`).
- `reactive_check.py` — verificación del **ReactiveCoordinator** (comportamiento, NO física): barrera repartida entre manada y rebaño, reactivo (sigue al paquete), NO usa `pack_prey`, caso penetrado (cubre a las vacas), patrulla en órbita (solo-corzos), severidad de muestra (Reactive ≤ Dummy), reproducibilidad, sin regresiones. Guarda `reactive_barrera.gif` + `reactive_patrulla.gif`.
- `reactive_eval.py` — evalúa el `ReactiveCoordinator` con el MISMO arnés (`baseline.evaluate`, mismas semillas/CONFIG_V2) y lo compara con la baseline Dummy CONGELADA (`baseline_v2.json`). Guarda `baseline_v2_reactive.json`/`.csv` (tabla comparada POR TIPO).
- `main.py` — bucle: reset → obs → coordinador → acciones → step → terminal → métricas (incluye fase final, n_safe/n_depredadas/n_fuera). **`--coordinador dummy|reactive`** (default dummy; con reactive los drones se mueven = barrera/patrulla) combinable con `--escenario` y la seed; imprime coordinador + escenario; añade `battery` a cada snapshot del history para la barra del render (solo LEE el estado).
- `baseline.py` — **arnés de EVALUACIÓN de la v2 CONGELADA** (tag `v2-baseline`): `CONFIG_V2` (config del mundo, **corzos ON**, 3 tipos) + cross-check de **fidelidad** (`CONFIG_V2 ≡ defaults+corzos` bit a bit) + `evaluate(coordinator_factory)` que corre el `DummyCoordinator` sobre `range(100)` semillas × 3 tipos (tipo forzado) y reporta **POR TIPO** (severidad media±desv, terminales, n_safe). Guarda `baseline_v2.json` (por episodio) + `baseline_v2.csv` (tabla); self-check de deriva vs `REFERENCE_SEVERITY`. **Protocolo de comparación:** un coordinador nuevo se mide con el MISMO arnés (misma config/semillas), cambiando solo el coordinador.
- `battery_check.py` — verificación macro del subsistema de batería (régimen permanente 4/2/2, escalonado, reproducible).
- `face_check.py` — verificación del modelo (12 tests): lobo solo no mata adultas, manada flanquea, **retoque** (presa expuesta), **terneros**, coordinación, instrumentación de #3, tembleque, tasa, **espaciado del rebaño (#1)**, **spawn por sector (#2)**, **rodeo (#3)**, reproducibilidad. *(Combate en campo CALIBRADO 100×100 —el modelo es invariante de escala, radios biológicos absolutos—; la **fijación** se prueba a 300 en los tests de espaciado/dispersión. Muertes por `captures`; cap corto.)*
- `escort_check.py` — verificación del **TERMINAL de escolta + disparador en DOS ETAPAS + GUIADO al refugio**: detección→SOSPECHA + 1 dron investigando + mensaje, investigar (se mueve al contacto)→confirmar→ESCOLTA + dron liberado, **precedencia** reflejo>coordinador, ÉXITO forzado **y ÉXITO ORGÁNICO** (el guiado lleva el rebaño al establo), **"dar la cara" intacto en la fuga** (encara mientras se traslada; terneros anclados), DEPREDACIÓN/TIMEOUT forzados, **refugio = soltar presa**, **exclusión del lobo**, reproducibilidad, **sin regresiones** (`face_check`+`battery_check`), **timing** (SOSPECHA/ESCOLTA), y **tasa de la escolta** (Dummy+guiado, candidata a v2: tasa+severidad). Guarda animación por terminal + arco detección→ESCOLTA + **bucle completo** (detectar→fuga→terminal).
- `drone_check.py` — verificación de la **DINÁMICA DE VUELO del dron** (paso 3a): punto-a-punto (acelera/cruza/frena/para), topes (`DRONE_MAX_SPEED`/`DRONE_MAX_ACCEL`), **coste de moverse** (reposicionar drena más que flotar; flote=suelo), reproducibilidad, sin regresiones (face+battery+escort). Guarda una animación del dron en vuelo.

Decisiones de diseño ratificadas:
- **Rama clásica = reflejo trivial, NO un FSM completo** (descartado por coste de programar/afinar
  para el alcance del TFG). Pocas reglas a mano sobre la capa de movimiento (dron → lobo más cercano,
  interponerse entre lobo y presa). Conserva el eje clásico-vs-aprendido. **Pendiente: revisar qué
  pide la rúbrica sobre "comparar enfoques"** y, si hiciera falta más sustancia clásica, decidir
  entonces; la columna de la evaluación se apoya además en baseline sin drones + ablaciones + robustez.
- Cada grupo de entidades = array `(N, 2)` de NumPy (vectoriza y se trocea por agente para MAPPO).
- Lobo como `(n_wolves, 2)` aunque varíe el número (no caso especial).
- `step(actions)` estilo gym (transición atómica); la observación se construye aparte en el bucle.
- **Render por reproducción** (separación limpia mundo↔dibujo; deja libre el adaptador ROS).
- Unidades SI (m, s; `dt=0.1`), **RNG sembrado** dentro del World (reproducibilidad bit a bit).
- **Dos escalas separadas (clave tras pasar a 300×300):** el **LAYOUT** deriva de `min(W,H)`/`diag` y
  **escala** con el campo (establo en el centro, central pegada a su borde, spawn de vacas hacia una
  esquina `(0.25W,0.75H)`, perímetro de spawn de lobos, homes de drones en las esquinas del bbox,
  `max_episode_steps`, `refuge_margin`); la **ESCALA BIOLÓGICA** es **ABSOLUTA en metros** y NO escala
  (extensión del rebaño `cow_spread`/`r_separation`, cúmulo de spawn `wolf_spawn_dispersion`, y combate/
  percepción `r_notice`/`r_face_safe`/`capture_radius` con sus derivados). Sin números mágicos: el layout
  sigue derivado; lo biológico son constantes calibradas a `min(W,H)`=100. **8 drones**: 4 activos en las
  esquinas del bbox inicial + 4 reserva en fila dentro de la central. `r_detect`=100 m (detección).

✅ **Modelo "DAR LA CARA" — IMPLEMENTADO (vacas adultas + lobos direccionales):**
- **Vaca adulta:** pasta dispersa (separación + deambular angular firme + valla blanda, **sin
  apiñarse, sin huir**); **encara** al lobo dentro de `r_notice` girando a `turn_rate`; **cono frontal**
  ±`cone_half_angle` lo mantiene a `r_face_safe` (empuje acotado, no salta); **enfriamiento** de giro
  → el flanco queda abierto. Débil = la más LENTA (`cow_speed_jitter`).
- **Terneros (0/1/2) + defensoras:** presa preferente (override en `_select_prey`); cada ternero con
  una adulta defensora fija que lo encara; el flanco no cubierto llega a la cría → muere con **1
  flanqueador**. Ternero **AL LADO** de la madre (muelle a `calf_personal_space` ~1.5 m, recíproco con
  el anclaje de la defensora; + inercia; no encara/no huye).
- **Lobo direccional con PRESA COMÚN:** la manada fija UNA presa **en t=0** (`_commit_initial_prey`):
  un **ternero** si lo hay, si no la adulta más **EXPUESTA** (lejos del centroide del rebaño); va a por
  ella **desde el primer paso**. La **mantiene** todo el episodio (solo la suelta si se **refugia**;
  abandono por distancia DEPRECADO). Respeta el cono (circula a `r_face_safe`) y cierra por el flanco.
  Modo caza: ternero → basta **1 lobo**; adulta → ≥ `n_min_adult`=2. Repulsión → **pincer**. Inercia en
  vaca/lobo/ternero → movimiento **firme**; el pastoreo en calma es **casi quieto** (magnitud del
  deambular = rapidez, ya no se normaliza a tope) y **más repartido** (`r_separation`↑).
- **Spawn por sector + rodeo del rebaño:** los lobos salen **agrupados de un sector** del perímetro
  (`_spawn_wolves_sector`, sorteado por episodio → dirección de ataque aleatoria, bandera #4); y cuando
  el rebaño se interpone, el lobo lo **BORDEA** con una componente **tangencial** (`wolf_skirt_gain`,
  obstáculo = cúmulo de no-presa + `wolf_skirt_margin`) en vez de atravesarlo.
- **Instrumentación de #3** (`_instrument_flanking`): flanqueadores válidos (umbral 1 ternero /
  `n_min_adult` adulta), primer quórum→muerte, desglose de toques, presas atacadas a la vez.
- **Verificado (`face_check.py`, 12 tests):** lobo solo vs adulta = **0**; manada flanquea→muere (#3
  quórum→muerte); **retoque** presa expuesta (18.2 vs 11.9 m), fijada en **t=0** (re-fijaciones 0);
  **ternero**: AL LADO (dist ~1.5 m), manada caza 38/40, **lobo solo vs ternero 0%** (madre frena;
  reportado, sin tunear); pastoreo casi quieto (0.019 m/paso) y **más repartido** (vecino ~10 vs 6 m);
  **spawn por sector** (cúmulo ~4 m, sector varía); **rodeo del rebaño** (con el rebaño en medio, dist
  mín lobo→presa **45.7→6.0 m**); firmeza intacta; **tasa 88%**; reproducible.
- *(Descartado el modelo de apiñamiento/Muro-pounce: el huddle se tragaba a la rezagada. Parámetros
  del modelo viejo —`k_cohesion_*`, `r_alarm/r_calm`, `d_safe`, `pounce_*`— quedan **deprecados pero
  aceptados** para no romper baseline.py v1; ignorados en la dinámica.)*

🧊 **Baseline del mundo (sin drones) — números UNIFICADOS:**
- **v1 = 49% (`predation = 49/100`, Wilson 95% IC 39.4–58.7%) — CONGELADO pero OBSOLETO.** Era del
  **modelo de apiñamiento**, **DESCARTADO** por el pivote a "dar la cara". Ya **no aplica**: su
  self-check `baseline.py` está pensado para **derivar a propósito** (pasa los kwargs viejos, que la
  dinámica nueva **ignora**), así que hoy mide ≈ la tasa del modelo actual, **no 49%**.
- **Modelo actual ≈ 88% sin drones** (medida en `face_check.py` range(100); el self-check de
  `baseline.py`, con su config y seeds congelados, da una cifra cercana). Es una **medida, NO un objetivo**:
  no se persigue ni se aterriza; es la cota que los coordinadores (reflejo trivial / MARL) deben **bajar**.
  En **episodio completo a 300×300** con el rebaño disperso (`HERD_SPREAD`=40) baja a **~82%** (era ~87%
  antes de dispersar): el modelo es el mismo y en "dar la cara" cada vaca encara **sola**, así que aflojar
  el rebaño apenas mueve la letalidad (no hay defensa colectiva que se "abra"). El **88%** es el combate
  medido en el campo **calibrado 100×100** (invariante de escala); ambas cifras describen el mismo modelo.
  ~1/5 de episodios son lobo-solo → TIMEOUT.
- **Candidata a v2 (Dummy + GUIADO + NO-HOLONÓMICO + DISUASIÓN + MATANZA EXCEDENTE + ENVOLVENTE + EVITACIÓN) —
  BASELINE HONESTA:** medida en `escort_check` (`escort_enabled=True`). La **SEVERIDAD** (cabezas perdidas) es la
  métrica principal: **~4.40 muertes/episodio** (tasa ≥1 ~82%; reparto `predation 33 / timeout 3 / success 4` en
  40 seeds). *Trayectoria: el bug del pin la FALSEABA a ~1.55 (clavada invulnerable → cazas suprimidas, TIMEOUT
  espurio); el ENVOLVENTE + disuasión parcial la subió a su valor REAL ~2.73 (clavada matable, TIMEOUT 13→3);
  la EVITACIÓN al huir la bajó a ~2.27 (las no-fijadas RODEAN al paquete y escapan más); el reflejo del más
  cercano la dejó en ~2.33; afinar la disuasión (radio 40→20 + bordeo, frenazo 0.5→0.7) la subió a ~4.17 —el dron
  reacciona solo de CERCA, así que el Dummy QUIETO cubre mucho menos; antes el radio ancho daba demasiada
  disuasión PASIVA—; la pareja madre-ternero LENTA la dejó en ~4.05 (≈igual); que los lobos dejen de PILLARSE en la
  zona segura la subió a ~4.40 (más eficientes, ya no pierden tiempo en el borde; el bug la bajaba artificialmente).*
  Frente al **adversario
  puro** (`escort_enabled=False`): **~6.33 muertes/ep** (tasa ~87%, máx. 8). Es decir, **guiado + disuasión
  PASIVA + rodeo bajan la severidad de ~6.3 a ~4.4** aun con Dummy (parcial, ahora más flojo a propósito). El balance
  huida/lobo sigue locked (no se tocan `cow_speed`/`wolf_speed` ni se mete sprint): la **SEVERIDAD** la bajará el
  **POSICIONAMIENTO** del coordinador (interponer drones CERCA, despejar pins activamente, post-v2 — ahora importa MÁS).
  **Esta severidad honesta (~4.40) es la referencia a batir.**
- **v2 CONGELADA (tag `v2-baseline`)** — la física definitiva (disuasión + matanza excedente + envolvente +
  madre-ternero + bordeo de zona + corzos) queda fijada como el adversario contra el que se miden ambas ramas.
  Se evalúa con `baseline.py` (`CONFIG_V2`, **corzos ON**, `range(100)` semillas × 3 tipos forzados, `DummyCoordinator`):
  **SEVERIDAD por tipo (N=100) — solo-lobos 4.45±2.15** (succ 4 / pred 88 / time 8; n_safe 2.39; tasa ≥1 muerta
  = 88%, el resto es lobo-solo que hace timeout / éxito orgánico) · **solo-corzos 0.00** (100/100 timeout, n_safe 0: SIN amenaza) · **mixto 4.41±2.18**
  (succ 4 / pred 88 / time 8; n_safe 2.43; ≈ solo-lobos, los corzos solo gastan ciclos de investigación) · agregado
  2.95±2.74. Guardado en `baseline_v2.json`/`.csv`. **Reproducible bit a bit** (RNG sembrado: las medias son enteros/100,
  exactas). De aquí en adelante la física **NO cambia**; el coordinador baja la severidad POR TIPO con el MISMO arnés.
- La batería es **ortogonal** (qué drones hay disponibles, no la dinámica vaca/lobo) → no mueve el
  baseline. busca-huecos/amago son adversarios posteriores de la escalera, no este baseline.
- ⚠️ NO tocar estos parámetros una vez empiece la comparación; si se recalibra, re-medir ambas ramas.

🔋 **Batería + cola de carga + RELEVO REALISTA — IMPLEMENTADO (v2.1)** (`_init_battery`/`_step_battery`,
`battery_check.py`): régimen permanente ~4 activos / ~2 cargando / ~2 listos (+ tránsito INCOMING/RETURNING),
~1 hand-off cada ~118 s escalonados, invariante "4 puestos cubiertos" a carga hover (STRANDED solo bajo
estrés), **sin teletransporte** (salto máx/paso = tope físico), reproducible, **dinámica vaca/lobo intacta**
(la batería no usa el RNG → no mueve la tasa sin drones; face_check bit a bit).
Automático por umbral; el relevo VUELA al puesto (hand-off) y el saliente vuelve a cargar por `RETURNING`;
hooks REALIZADOS (persecución `battery_activity`, travel-time emergente, dron tirado `STRANDED`/`drone_stranded`).
Ver §4.3.

---

## 10. 🚩 Banderas levantadas / pendientes para después

> Lista deliberada de cosas aparcadas, para no perderlas.

1. ✅ **RESUELTA — Velocidad en el estado.** En **vacas y lobos** (inercia, `cow_vel`/`wolf_vel`) y
   ahora también en **drones** (`drone_vel`, paso 3a): vuelo holonómico hacia waypoint con
   `DRONE_MAX_SPEED`/`DRONE_MAX_ACCEL`, acelera/cruza/frena/para. Ver §4.3 / `drone_check.py`.
2. **Altura/z como estado.** Conceptual ahora; **añadir al modelar el cono de visión de la
   cámara** (más altura = más área, peor resolución = el compromiso de detección de objetos
   pequeños, donde YOLO26 con su STAL viene bien).
3. ✅ **RESUELTA — Límite provisional de las vacas.** El clamp duro al spawn se ha sustituido por
   la **valla blanda** (fuerza de retorno hacia la zona de pasto) + cohesión. Contención dura solo
   en límites reales (parcela + establo/central, reutilizando el clamp de exclusión existente).
4. 🟡 **Variedad de escenarios para el MARL (PARCIAL).** Ya: los lobos entran **agrupados por un
   sector aleatorio** del perímetro (`_spawn_wolves_sector`) → la **dirección de ataque varía** entre
   episodios (la política no puede memorizar de dónde viene). Falta **aleatorizar el spawn del rebaño**
   (hoy fijo `(0.25W, 0.75H)`) para la fase de entrenamiento (no antes).
5. 🟡 **Zonas prohibidas del lobo — ACTIVAS en la escolta.** El clamp de exclusión del lobo se
   **re-aplica como ÚLTIMA palabra del step** (tras el empuje del cono, que si no podría meter un lobo
   en el establo) y entra ya en el **terminal** ("ningún lobo dentro del establo" = condición de ÉXITO);
   verificado en `escort_check`. Cobrará aún más sentido con el guiado (lobo persiguiendo a las vacas
   hacia el establo central). Enlaza con "lobos fuera del recinto" del criterio de éxito.
6. **Disuasión con habituación.** **Disuasión BASE ✅ implementada** (`_apply_deterrence`: el lobo esquiva
   + frena dentro de `DETER_RADIUS` de un dron ACTIVE; competencia parcial con la caza; gateada por
   `escort_enabled`). **Falta la HABITUACIÓN:** el efecto debería **decaer con el uso repetido** (el lobo se
   acostumbra al ladrido) → es lo que hace que la estrategia sea "ganar tiempo para escoltar", no "ladrar
   para siempre". También pendientes (refinamientos): ladrido explícito con toggle/decaimiento y que la
   fuerza dependa de la velocidad del dron (hoy: solo proximidad → disuade).
7. ✅ **RESUELTA (coste de persecución) — Batería que crece con el movimiento.** Con la dinámica de
   vuelo (paso 3a), `battery_activity` ya se calcula del **esfuerzo** (drenaje ACTIVE = flote ×
   (1+`DRONE_MOVE_DRAIN`·v/vmax)): flotar es el suelo, reposicionar a tope gasta ~2.5×. Verificado en
   `drone_check.py` (mover drena 2.2× flotar). **RELEVO REALISTA ✅ (v2.1):** el `relay_travel_time` ya NO es un
   hook fijo — el relevo VUELA al puesto (hand-off, sin teletransporte; ver §4.3), el saliente vuelve por
   `RETURNING` a cargar, y bajo estrés un dron puede quedar **`STRANDED`** (batería a ~0 esperando relevo → sin
   cobertura efectiva). Así **moverse mucho tiene coste real** (más relevos → reservas en tránsito → huecos/
   stranded): la energía es un COMPROMISO que el coordinador (y el MARL) deben gestionar, no un recurso gratis.
   **Pendiente (política, no mecánica):** que el coordinador no agote la flota moviéndose de más (proteger la
   reserva de retorno). El **hueco de cobertura** también lo abre el dron que sale a investigar (deja su sector).
8. **Alerta como acción aprendible.** En la v1 la alerta es **automática por umbral**. Dejar que
   la política aprenda *cuándo/qué* comunicar es **extensión avanzada** (y zona inestable del
   MARL: premiar/penalizar el avisar directamente puede enseñar a callar amenazas — ir con pies
   de plomo). El **umbral de alerta** es un parámetro de diseño de primer orden: en el reflejo
   trivial se fija a mano; el MARL puede aprenderlo (resultado bonito para la comparación).
9. **Codificador invariante a permutaciones** (Deep Sets / atención) para el número variable de
   vacas/compañeros → da escalabilidad (entrenar con N, evaluar con 2N).
10. **Percepción: sustituto vs YOLO real.** Entrenar la coordinación con un **sustituto rápido**
    (confianza vs distancia/altitud) para no meter YOLO en el bucle de RL (mata la velocidad);
    **validar end-to-end con YOLO26 real** en evaluación (Fase 5). Como es sim-only, train y eval
    comparten el renderizado → la brecha sim-to-real de percepción casi desaparece. Dataset del
    lobo: renderizar lobos sintéticos (Blender / Isaac) — no hay detector de "lobo aéreo" de
    estantería.
11. ✅ **RESUELTA — Captura, vía "dar la cara" (pivote).** El modelo de apiñamiento + pounce
    (relativo o absoluto) se **descartó**: el huddle se tragaba a la rezagada y no había a quién
    cazar limpiamente. Ahora la captura es por **FLANQUEO** (≥ `n_min_adult` lobos a la vez dentro de
    `capture_radius` y fuera del cono frontal de la adulta): un lobo solo no puede, la manada sí.
    Tasa 88% sin drones. Ver §4.1/§4.2.
12. **Pure pursuit y filtro de estimación del lobo.** Reutilizar el pure pursuit (de Robots) en la
    capa de guiado; implementar un **EKF/filtro de partículas** para estimar la trayectoria del
    lobo a partir de detecciones ruidosas (análogo al MCL de la asignatura — el GPS da la
    posición propia, así que la estimación es del *lobo*, no del ego).
13. ✅ **RESUELTA — Tests del "juez".** El terminal de escolta (3 estados + contadores) y la máquina
    de fases VIGILANCIA→ESCOLTA (disparador por **detección de dron**) están **implementados y verificados**
    (`escort_check.py`, 8 tests: disparador, ÉXITO/DEPREDACIÓN/TIMEOUT forzados, refugio=soltar presa,
    exclusión del lobo, reproducibilidad, sin regresiones). Hecho ANTES del guiado al refugio. Ver §4.4.
14. ✅ **RESUELTA (v3.7) — Rotación espuria de ranuras en cada relevo (silenciosa desde v3.0).**
    La patrulla repartía las ranuras del anillo **por orden de índice** de los drones libres: en cada
    hand-off el fresco entraba con OTRO índice y **todos los drones rotaban una ranura** — una
    recolocación no ordenada que además sacudía la geometría (medido: desatascaba de chiripa jugadas
    del cebo en meseta — ver Commit S3 de la Etapa 1). Descubierta al implementar el **RELEVO DE
    CENTINELA** (Commit R, v3.7: el bajo anuncia y se CLAVA en su puesto; el READY más cargado vuela
    DIRECTO al puesto; traspaso a 2 m; ranura **ESTABLE por dron** — el fresco la HEREDA del
    saliente; verificado con mundo GEMELO bit a bit en `battery_check`). **Principio de diseño
    (dueño): "ningún comportamiento del sistema debe volver a apoyarse en movimiento no ordenado."**

---

## 11. SIGUIENTE PASO

**(2026-08-23) CIERRE TOTAL: no hay siguiente paso ejecutable — KILL-DATE absoluto del dueño. Lo que sigue es el histórico de pasos; el future work está en §0.4 y en `/data/TABLA_MAESTRA.md` §6.**

**Adversario vaca+lobo CERRADO ("dar la cara" + presa común + terneros/defensoras, pulido).** Las
adultas plantan cara y pastan **casi quietas y repartidas**; los lobos entran **agrupados por un sector**
(dirección de ataque variable); la manada **fija la presa en t=0** (ternero si lo hay, si no la adulta
más expuesta), **bordea el rebaño** si se interpone y va a por ella desde el primer paso; el ternero,
**al lado** de su madre, muere con 1 flanqueador, la adulta con `n_min_adult`. Movimiento firme.
Verificado en `face_check.py` (12 tests); tasa **88%** sin drones (no perseguida).

**Escolta · paso 1 HECHO — el TERMINAL (el "juez").** Máquina de fases VIGILANCIA→ESCOLTA (disparador
por **detección de dron**) + terminal de 3 estados (ÉXITO/DEPREDACIÓN/TIMEOUT) con contadores, multi-muerte,
ganchos de refugio y exclusión del lobo. Verificado en `escort_check.py` (8 tests). Ver §4.4.

**Escolta · paso 3a+3b HECHOS — MOVIMIENTO de drones + disparador realista.** 3a: vuelo holonómico hacia
waypoint (`drone_vel`, `command_waypoint`, `DRONE_MAX_SPEED`/`DRONE_MAX_ACCEL`, acelera/cruza/frena/para) +
coste de batería por moverse (flag #7). 3b: disparador en dos etapas detectar(`r_detect`)→SOSPECHA→acercarse
(reflejo de investigación, el dron vuela al contacto)→confirmar(`r_confirm`)→ESCOLTA, con mensaje al
coordinador y precedencia reflejo>coordinador. Verificado en `drone_check.py` + `escort_check.py` + sin
regresiones. DummyCoordinator no recoloca (solo Dummy + interfaz del mensaje). Ver §4.3/§4.4, banderas #1/#7.

**Escolta · paso 2 HECHO — GUIADO al refugio (NO-HOLONÓMICO).** En ESCOLTA la vaca corre **hacia donde mira**:
**HUIR** de frente al establo a `cow_speed` / **ENCARAR-PIN** (gira al lobo y se PARA); excluyentes → los lobos
**clavan** a la presa (pin-and-flank). INFRAESTRUCTURA del mundo (`escort_enabled`), no el coordinador;
pastoreo/combate **holonómico** intacto (face_check); terneros anclados. **Lobo-solo → TIMEOUT** (clava pero no
flanquea). ÉXITO orgánico = llegar **antes** de ser fijada / que el paquete agote. Ver §4.1/§4.2/§4.4.

**Escolta · DISUASIÓN HECHA — el dron tiene DIENTES.** Dentro de `DETER_RADIUS`=40 m de un dron ACTIVE el lobo
**ESQUIVA** (repulsión con *falloff*, suma de todos los drones a tiro) y **FRENA** (× `DETER_SLOWDOWN`); la
esquiva se SUMA al impulso de caza → competencia **PARCIAL** (cerca domina la repulsión = despeja el pin; al
borde domina la caza = empuja a través). Infraestructura del mundo (`escort_enabled`), **no el coordinador**;
sin habituación (flag #6). **face_check 12/12** (combate puro no disuade, bit a bit). `_apply_deterrence`.

**Escolta · MATANZA EXCEDENTE HECHA — la SEVERIDAD es la métrica.** Revertido el tope de 1 caza (`1d44cdc`):
tras matar/refugiarse la presa, el paquete **re-fija la res viva no-a-salvo MÁS CERCANA** y SIGUE hasta
**agotar** (todas muertas o a salvo); al agotar **coastea a parada**. La caza en sí es IDÉNTICA.
`_recommit_nearest_prey` / `_targets_exhausted`. **face_check 12/12** (conteo a multi-muerte). Ver §4.1/§9.

**Escolta · FIX PIN HECHO — adulta clavada matable (envolvente + disuasión parcial a corta).** Regresión: una
adulta clavada era invulnerable (los lobos se apiñaban en el cono + la disuasión los clavaba). **(1) ATAQUE
ENVOLVENTE** (`wolf_envelop_gain`, `_envelop_slots`): rumbos EQUIESPACIADOS alrededor de la presa → flancos
limpios. **(2) DISUASIÓN PARCIAL A CORTA** (`deter_w`): el flanqueador pegado a su presa (≤`r_face_safe`) empuja
a través; el dron REDUCE/RETRASA, no invulnerabiliza. **Baseline HONESTA: severidad v2 ~1.55→~2.73** (el bug la
falseaba a la baja; tasa 52%→78%, timeout 13→3); adversario puro **~6.33**. **face_check 12/12**. Ver §4.1/§9.

**Escolta · EVITACIÓN al HUIR HECHA — las no-fijadas RODEAN a los lobos.** En modo HUIR (solo no-fijadas) el
rumbo objetivo mezcla hacia-el-establo (`W_REFUGIO`, domina) + alejándose de los lobos en `COW_AVOID_RADIUS`=30 m
(`W_EVITAR`, con falloff) → la vaca **bordea** a los lobos en su camino y sigue llegando (no atraviesa la pelea).
La presa fijada sigue ENCARANDO (no esquiva). **Severidad v2 ~2.73→~2.27** (las no-fijadas escapan más). **face_check
12/12** (rama ESCOLTA, bit a bit). Ver §4.2/§9 + `escort_rodeo.gif`.

**Escolta · EL MÁS CERCANO INVESTIGA HECHO — fix del reflejo (no aleatorio).** Ante un contacto, el reflejo de
investigación (`_pick_investigator`, infraestructura igual en todos los coordinadores) elige el dron ACTIVE
**libre más CERCANO** al contacto (= el que llega antes), no el primero por índice; si el más cercano está
ocupado va el siguiente más cercano libre; desempate **determinista por menor índice** (sin aleatoriedad).
Sustituye la selección por orden de índice. NO toca coordinador/disuasión/combate/detección-confirmación/guiado.
**Severidad v2 ~2.27→~2.33** (medida, NO objetivo: cambia qué dron va → dinámica de disuasión ligeramente
distinta; mismo reparto `predation 29/timeout 5/success 6` → **dentro del ruido**, +0.06). **face_check 12/12**
(el reflejo no corre en combate puro, `escort_enabled=False`). Verificado en `escort_check` 0c (el más cercano
va en 4 posiciones · ocupado→siguiente libre · determinista/empate→menor índice). Ver §4.2 (máquina de fases).

**Escolta · DISUASIÓN AFINADA HECHA — radio CORTO + el lobo BORDEA con naturalidad.** Dos quejas del render: (1)
radio demasiado grande (reaccionaban de lejos); (2) un dron QUIETO interpuesto dejaba al lobo "super lento" (la
repulsión RADIAL cancelaba la caza → neto≈0 → atasco geométrico). Dos cambios: **`DETER_RADIUS` 40→20** (lobo
AUDAZ, reacciona solo de cerca) y **componente TANGENCIAL** `DETER_TANGENT`=6 (el lobo ARQUEA alrededor del dron
hacia la presa en vez de empujar de frente; máx. de frente) + frenazo **`DETER_SLOWDOWN` 0.5→0.7** (fluye, no se
para). El PIN intacto (`deter_w` escala radial+tangencial; el comprometido empuja a través). **Severidad v2 ~2.33→
~4.17** (tasa 80%; medida, NO objetivo): el radio corto + frenazo suave dejan al Dummy QUIETO cubrir mucho menos
(antes el radio ancho daba demasiada disuasión PASIVA) → **el posicionamiento del coordinador importa MÁS**.
**face_check 12/12** (no corre en combate puro). Verificado en `escort_check` 1d (esquiva+frena · parcial · APARTA
al que se ACERCA de lejos: con radio corto un dron quieto PREVIENE pines pero ya no expulsa uno cerrado —eso es el
coordinador—) + `escort_bordeo.gif` (el lobo ignora al dron de lejos y arquea ~9.5 m al entrar en R=20).

**Escolta · LA MADRE NO ABANDONA AL TERNERO HECHO — huyen juntos al ritmo del ternero.** Una vaca con ternero
huía a rapidez de adulta y lo dejaba atrás. Ahora, en HUIR (ESCOLTA): el ternero tiene rapidez propia
`calf_speed`=0.8 m/s (< `cow_speed`=1.2; la cría es más lenta) y una DEFENSORA que HUYE **no lo ADELANTA** (su
avance se capa a `calf_speed`, la más lenta de la pareja) → migran **JUNTAS** a ese ritmo, a su lado (el anclaje
ya los junta). Solo mientras el ternero siga en juego; si ENCARA (presa/defensora fijada) avanza 0 → **Bug 1
intacto**. `calf_safe`⟺ternero DENTRO **intacto** (Bug 2). En pastoreo el ternero sigue capado a `cow_speed`
(combate/face_check **bit a bit**). **Consecuencia (no bug):** la pareja es más LENTA → más vulnerable (realista:
los depredadores van a por las crías) → trabajo claro para los drones. **Severidad v2 ~4.17→~4.05** (≈igual,
ruido; mismo reparto 32/4/4; medida, NO objetivo). **face_check 12/12.** Verificado en `escort_check` 1g (no la
deja atrás: gap ≤2.2 m, rapidez madre ≤`calf_speed` · llegan juntos · pareja más lenta que adulta sola: 1123 vs
730 pasos · fijado→ENCARAR intacto) + `escort_madre_ternero.gif`.

**Escolta · LOS LOBOS NO SE PILLAN EN LA ZONA SEGURA HECHO — la BORDEAN.** Un lobo que perseguía HACIA la zona
segura (su presa se refugió, o su objetivo está al otro lado) se quedaba CLAVADO en el borde: la persecución
apunta DENTRO y el clamp `_push_outside_circle` lo frena de frente → fuerza neta ~0 (mismo ATASCO RADIAL que con
el dron; medido: desplaz. neto ~3.6 m en 200 pasos). Fix: cerca de la frontera (`WOLF_ZONE_SKIRT_BAND`=20 m) una
componente **TANGENCIAL** (`WOLF_ZONE_SKIRT_GAIN`=3, escala `block`·`falloff`, sumada a `desired` antes de
normalizar → solo redirige, no acelera; desempate de lado DETERMINISTA → robusto al saddle colineal exacto) hace
que el lobo **BORDEE** la zona **por FUERA** (no entra: el clamp sigue) hasta el objetivo del otro lado. La presa
refugiada ya se **soltaba al instante** (`_prey_lost_reason`=="refuge" el mismo paso que `cow_safe` → re-fija la
viva no-a-salvo más cercana, FUERA; verificado, sin cambios). Gateado por `escort_enabled` (en combate la presa
no se refugia → **face_check bit a bit**). **Tamaño de la zona (reportado, NO cambiado):** `safe_radius`=0.12·min(W,H)=**36 m**
(12% del lado, 4.5% del área del campo 300×300; central 15 m) — decisión de diseño del usuario. **Consecuencia
(no bug):** los lobos son más eficientes (no pierden tiempo pillados) → **severidad v2 ~4.05→~4.40** (el bug la
bajaba artificialmente; medida, NO objetivo). **face_check 12/12.** Verificado en `escort_check` 1h (bordea: min
dist a la presa del otro lado 100→6 m incl. saddle colineal · NO entra · suelta la refugiada al instante) + `escort_zona_bordeo.gif`.

**Escolta · CORZOS (3c) HECHO — cuerpos que NO son amenaza (última pieza del mundo antes de congelar v2).** No todo
contacto es un lobo. **El corzo** (entidad nueva, `corzos (N,2)`, `corzo_speed`=4.0): **DEAMBULA** (wander lento) +
**HUYE** (repulsión con falloff, `CORZO_FLEE_RADIUS`=30 m, `CORZO_FLEE_GAIN`=3) de lobos y drones ACTIVE; **NO caza,
NO va al rebaño, NO ataca**; las vacas NO lo encaran (no es amenaza → no dispara `r_notice`). Spawn aleatorio fuera
de zonas y del rebaño (sembrado). **Como CONTACTO** (`_contact_bodies`): a ≤`r_detect` dispara el reflejo de
investigación IGUAL que un lobo (va el dron libre más cercano); el tipo es desconocido hasta `r_confirm`. **ORÁCULO**
(verdad-terreno, stand-in determinista de YOLO) a `r_confirm`: **lobo → ESCOLTA** y el dron se libera; **corzo → el
dron DESCARTA** (`corzo_dismissed`, no se reinvestiga) y se libera, SIN ESCOLTA. **3 tipos de episodio** (~1/3 cada
uno, sembrado, `corzo_episode_probs`): solo-lobos / solo-corzos / mixto; en **solo-corzos** ESCOLTA jamás → el rebaño
pasta, **severidad 0**. **OFF por defecto** (`corzos_max`=0 → cero draws RNG → mundo actual **bit a bit**; combate
puro sin corzos → **face_check 12/12**). El reflejo de investigación se GENERALIZÓ a "cuerpos" (lobo o corzo) que SIN
corzos se reduce EXACTAMENTE al lobo más cercano (bit a bit). **NO** toca el modelo del lobo/vaca, la zona segura, los
radios `r_detect`/`r_confirm`, ni el coordinador (Dummy → None; el descarte es infra de confirmación/reflejo).
**Severidad POR TIPO** (corzos activos, Dummy): **solo-lobos ~4.4 (= corzos OFF), solo-corzos = 0, mixto ≈ solo-lobos**
(los corzos solo consumen ciclos de investigación; el agregado mezclado es poco informativo). Verificado en
`escort_check` 1i (deambula+huye de lobo/dron · detectable · oráculo lobo→ESCOLTA/corzo→descarta · solo-corzos sev 0 ·
reparto ~1/3 reproducible) + 9b (severidad por tipo) + `escort_corzos_solo.gif` / `escort_corzos_mixto.gif`.

**Escolta · CORZOS — afinado (que se vean e investiguen bien).** Tras el fix de `main.py` (los corzos estaban OFF
por defecto y `main.py` usaba el default → no aparecían; render SÍ los dibuja), cuatro mejoras del escenario: **(1)
BUG del reflejo:** un corzo dejaba la fase **PILLADA en SOSPECHA** (solo se latcheaba ESCOLTA para lobos) y el dron
descartado **no volvía**. Ahora el dron **VUELA al contacto**, solo a `r_confirm` el oráculo dicta (no de lejos),
y al descartar el corzo **VUELVE a su puesto** (`drone_home`) y la **fase vuelve a VIGILANCIA** si no queda contacto
investigándose (lobo→ESCOLTA, no vuelve). El reset de fase NO afecta la dinámica (solo ESCOLTA importa) → baseline
bit a bit. **(2) AGRUPADOS:** spawn de un GRUPO (centroide + `CORZO_GROUP_DISPERSION`=6) + cohesión suave
(`CORZO_COHESION`=0.05) + separación (`CORZO_SEPARATION`=4) → salen y se mantienen juntos. **(3) Dentro de SOSPECHA:**
el centroide cae en la banda `[cow_spread+r_notice, r_detect]` del rebaño → **100%** de los episodios disparan
SOSPECHA (medido). **(4) REGRESIÓN del render:** el submuestreo de `main.py` aceleraba la reproducción; ahora
renderiza solo la **ventana relevante** (hasta poco tras el último evento) a **ritmo natural** (stride pequeño), sin
comprimir el timeout de solo-corzos. Solo render/`main.py` → la sim no cambia (fingerprint idéntico). Verificado en
`escort_check` 1i (d/d2: el dron vuela a ≤`r_confirm`, descarta, vuelve al puesto, fase VIGILANCIA; tipo solo a
`r_confirm`; h: agrupados spread ~5 m, 100% en SOSPECHA) + `main.py --escenario solo-corzos`.

**v2 CONGELADA HECHO — la física definitiva, fijada y medida (tag `v2-baseline`).** Última pieza ANTES de los
coordinadores: el mundo (lobo/vaca/corzo/zona segura/detección-confirmación + disuasión + guiado + envolvente +
madre-ternero + bordeo de zona) queda **congelado**; de aquí en adelante NO cambia. `baseline.py` reescrito como
**arnés de EVALUACIÓN** (no el mundo —el viejo, del modelo de apiñamiento a 100×100, estaba obsoleto—): `CONFIG_V2`
fija la config (**corzos ON**, 3 tipos), un **cross-check de fidelidad** verifica `CONFIG_V2 ≡ defaults de World +
corzos ON` **bit a bit**, y `evaluate(coordinator_factory)` corre el `DummyCoordinator` sobre `range(100)` semillas ×
3 tipos forzados, reportando **POR TIPO** (severidad media±desv, terminales, n_safe) + agregado, guardado en
`baseline_v2.json` (por episodio) + `baseline_v2.csv` (tabla). **SEVERIDAD CONGELADA: solo-lobos 4.45±2.15** (succ 4 /
pred 88 / time 8; n_safe 2.39) · **solo-corzos 0.00** (100/100 timeout; SIN amenaza, n_safe 0) · **mixto 4.41±2.18**
(succ 4 / pred 88 / time 8; ≈ solo-lobos) · agregado 2.95±2.74. Las medias son enteros/100 → **exactas y reproducibles**
(RNG sembrado; self-check de deriva vs `REFERENCE_SEVERITY`). **PROTOCOLO DE COMPARACIÓN (apples-to-apples):** un
coordinador nuevo se evalúa con el MISMO `baseline.py` (`evaluate(su_factory)`), mismas semillas y `CONFIG_V2`,
cambiando SOLO el coordinador → se compara la severidad POR TIPO. **Verja 12/12 verde bit a bit** (no se tocó
`world.py` → face_check MUERTE paso 29 idéntico). Esto fue **FIJAR Y MEDIR**: la baseline es la que salió; NO se tuneó
la física para "mejorarla" — bajar la severidad es trabajo del COORDINADOR (post-v2).

**COORDINADOR REACTIVO HECHO — barrera de apantallado (1er coordinador de verdad, regla FIJA).** El primer
coordinador que BATE al Dummy: una heurística a mano (SIN aprendizaje) que posiciona los drones LIBRES para
APANTALLAR al rebaño. `ReactiveCoordinator` (en `coordinators.py`) recibe el estado del mundo, devuelve waypoints
para los **ACTIVE libres** (NO toca el reflejo/investigador ni los relevos de batería: les deja su waypoint) y deja
que la **DISUASIÓN** del mundo (automática, de los ACTIVE a ≤`DETER_RADIUS` de un lobo) haga el trabajo. **ESCOLTA:**
BARRERA perpendicular al eje rebaño→manada, entre el paquete y las vacas más cercanas, a `barrier_standoff`=`DETER_RADIUS`
por delante, con los drones REPARTIDOS a `drone_spacing`≈1.6·`DETER_RADIUS` (los campos de disuasión TEJEN un frente)
— **COORDINADO** (no cada uno a por un lobo) y **REACTIVO** (recalcula cada paso). **Defiende a TODO el rebaño:** NO usa
la presa fijada (`pack_prey`); solo ve posiciones de lobos y de vacas vivas no-a-salvo (incl. terneros). **PENETRADO**
(la manada ya está entre las vacas): degrada con gracia a cubrir a los lobos MÁS CERCANOS a ellas (`engage_standoff`=
2·`r_face_safe`), no una barrera externa inútil. **Sin amenaza** (VIGILANCIA/SOSPECHA, solo-corzos): PATRULLA en órbita
alrededor del rebaño. **NO toca la física** (`world.py`/`baseline.py` intactos → baseline Dummy IDÉNTICA, verja 12/12
verde). **Evaluado con el MISMO arnés** (`reactive_eval.py` → `baseline.evaluate`, mismas semillas/CONFIG_V2):
**SEVERIDAD solo-lobos 4.45→3.27 (−1.18) · mixto 4.41→3.40 (−1.01) · solo-corzos 0→0** (n_safe SUBE 2.39→3.59 /
2.43→3.44; el reparto de terminales apenas cambia —sigue habiendo alguna caza por episodio— pero se pierden MENOS
cabezas y se salvan MÁS). Es la referencia CLÁSICA que el MARL deberá batir; **MEDIDA, no objetivo** (el frente es
finito y a corta distancia la disuasión es PARCIAL → no es un escudo perfecto). Parámetros etiquetados/afinables.
Verificado en `reactive_check.py` (8 tests) + `reactive_barrera.gif` / `reactive_patrulla.gif`.

**RELEVO de flota REALISTA HECHO (v2.1) — sin teletransporte + RE-CONGELAR.** El relevo de batería era un swap
INSTANTÁNEO (teletransporte de rol+posición). Ahora el bajo se **CLAVA en su puesto** y cubre hasta que llega el
relevo, que **VUELA** desde la central (hand-off al estar ENCIMA); el saliente vuelve por `RETURNING` a cargar.
Estados nuevos `INCOMING`/`STRANDED`; bajo estrés un dron puede quedar **STRANDED** (batería a ~0 esperando relevo
→ hueco de cobertura real). Ver §4.3 y bandera #7. Moverse pasa a tener **coste energético REAL** → la energía es un
COMPROMISO que el coordinador/MARL debe gestionar (no agotar la flota moviéndose de más). Solo el relevo (`_step_battery`/
`_init_battery` + free-mask + enum); NO toca caza/disuasión/reflejo/coordinadores; **NO usa el RNG** → **face_check
12/12 bit a bit**; `battery_check` actualizado (4/2/2 + tránsito · sin teletransporte · stranded bajo estrés · reproducible).
**RE-CONGELADO v2.1** (tag `v2.1-baseline`): Dummy **4.45/0/4.41** y Reactive **3.27/0/3.40** SIN cambios (re-medidos;
la cobertura se mantiene, solo cambia el coste de moverse).

**RETOQUES VISUALES + FIX DEL ARRANQUE DEL REACTIVO (HECHO).** (1) `render.py`: emojis más pequeños (`EMOJI_SCALE`
0.55→0.45), sin la leyenda de entidades (se explican solos; queda la de zonas), y **🔊 bajo el dron ACTIVE que disuade**
(algún lobo a ≤`DETER_RADIUS`; el render calcula la condición con los mismos radios, NO toca la disuasión). (2)
`coordinators.py`: la PATRULLA mandaba a los drones (que nacen en las esquinas del rebaño, ~225°+90°i) a la ranura
`i·2π/k` ~135° OPUESTA → cruzaban el centro al arrancar (diagnóstico: error angular 135°, sep mínima ~16 m). Ahora ANCLA
la fase de la formación a su posición angular ACTUAL → cada dron va a su ranura MÁS CERCANA (error 135°→10°, sep 16→41 m,
sin cruces) y órbita rígida. Solo el coordinador: **Reactive 3.27/3.40 → 3.36/3.42** (+0.09/+0.02; el bug apoyaba números
en un center-hugging accidental), Dummy/física INTACTOS (**NO re-congela**). `test_arranque` nuevo + `test_severidad_muestra`
n=15→30. face 12/12 bit a bit · verja verde. (Rombo de carga PARADO: los slots de reserva viven en `world.py`.)

**SUSTO FUERTE (la disuasión pasa de PARCIAL a FUERTE) + rombo de carga (HECHO, v2.3, RE-CONGELADO tag `v2.3-baseline`).**
CAMBIO de FÍSICA (re-mide la baseline). Visto en render: un lobo alcanzaba una vaca clavada y se quedaba PEGADO
indefinidamente (la disuasión parcial le dejaba "empujar a través" y matar; cuadro congelado lobo-vaca-dron). Nuevo
`_apply_deterrence`: un lobo con un dron ACTIVE a ≤`DETER_RADIUS`=20 HUYE del dron (RADIAL, módulo CRECIENTE al acercarse
`clip(wolf_speed·(1−d/R), SCARE_SPEED_MIN=0.8, wolf_speed)`, dirección = suma de repulsores a tiro, módulo del MÁS CERCANO)
y NO caza mientras huye (la huida SUSTITUYE a la caza). SIN excepción a corta (fuera `deter_w`/`DETER_REPULSION`/
`DETER_TANGENT`/`DETER_SLOWDOWN`) → un dron ENCIMA siempre lo EXPULSA. Los que huyen se marcan (`_wolf_scared`) y NO cuentan
como flanqueadores en `_process_predation` → no matan huyendo (arregla el cuadro congelado: el lobo sale despedido al llegar
el dron y la vaca deja de tener lobo en `r_notice`). Solo drones ACTIVE; gateado por `escort_enabled` (combate puro NO asusta,
`_wolf_scared` todo False) → **face_check bit a bit**. Slots de reserva en ROMBO (determinista, no consume RNG → spawns bit a
bit). NO toca caza/huida/madre-ternero/batería-relevo(lógica)/detección/coordinadores. **RE-MEDIDO (N=100/tipo):** Dummy
4.45/0/4.41 → **2.36/0/2.24** (el susto casi la halva; n_safe 2.39→4.19); Reactive 3.36/3.42 → **0.16/0/0.18** (barrera+susto
≈ protección casi total, 85% success). MEDIDA, no objetivo (no se tuneó `SCARE_*`). `test_susto` dirigido + tests de disuasión
adaptados (k_con=None: el dron ya no deja "empujar a través") + fix de un bug latente del `sev()` de `reactive_check` (world
CONGELADO distinto al que corría). face 12/12 · battery · escort · drone · reactive verdes.

**SIGUIENTE (opciones):**
- **MARL (MAPPO):** aprender la coordinación de drones y **BATIR la barrera reactiva** (0.16 / 0 / 0.18) sobre la v2.3
  congelada, con el MISMO arnés, **gestionando la energía** (relevos/tránsito/stranded ahora cuestan). Con corzos: aprender a **NO malgastar drones** en lo que no es amenaza (solo-corzos ya 0).
- **Afinar/variar el coordinador clásico:** tunear standoff/spacing/ancho del frente por render; o un **reflejo-reactivo**
  que CONSUMA el mensaje del reflejo de investigación (recolocar a los DEMÁS drones con el contacto). + hooks de batería.
Luego: percepción imperfecta (YOLO). Todo **sobre la v2 ya congelada** (la referencia fija).

**Ruta sugerida (orden tentativo, aún sin decidir):** 3a ✓ → 3b ✓ → **paso 2 (guiado) ✓** → **disuasión del
dron ✓** → **matanza excedente ✓** → **fix pin + envolvente ✓** → **evitación al huir ✓** → **el más cercano
investiga ✓** → **afinar disuasión (radio corto + bordeo) ✓** → **madre no abandona al ternero ✓** → **lobos no se pillan en la zona segura ✓** (severidad v2 honesta ~4.40) → **3c (corzos) ✓** → **congelar v2 ✓ (tag `v2-baseline`; sev por tipo solo-lobos 4.45 / solo-corzos 0.00 / mixto 4.41, N=100)** → **coordinador reactivo: barrera de apantallado ✓ (sev 3.27 / 0 / 3.40 vs Dummy 4.45 / 0 / 4.41)** → **relevo de flota REALISTA ✓ (v2.1: hand-off sin teletransporte)** → **render: emojis + barra de batería + `--coordinador` ✓** → **jabalí como 2ª distracción + emojis más pequeños ✓ (v2.2: RE-CONGELADO tag `v2.2-baseline`, mismos números)** → **retoques visuales + fix arranque del reactivo ✓ (patrulla anclada, sin cruces; Reactive → 3.36/0/3.42; Dummy/física intactos)** → **SUSTO FUERTE + rombo de carga ✓ (v2.3: disuasión PARCIAL→FUERTE, RE-CONGELADO tag `v2.3-baseline`; Dummy 2.36/0/2.24, Reactive 0.16/0/0.18)** → **MARL** (debe batir la barrera 0.16/0.18, gestionando la energía).

*(Pendiente de decisión menor, NO en este paso: lobo solo vs ternero salió 0% — la madre frena siempre.
Si se quiere que sea disputado (a veces se cuela), afinar `face_cooldown`/`r_face_safe`. Parámetros del
modelo vaca/ternero: `calf_count_probs`=(1/3,1/3,1/3), `calf_speed`=0.8 m/s (< `cow_speed`; la cría es más
lenta, la madre no la adelanta al huir), `k_calf_cohesion`=1.0, `k_defender_anchor`=0.6,
`calf_personal_space`=0.5·`capture_radius`≈1.5 m (ternero al lado), `wander_calm`=0.2 (rapidez de
pastoreo); `cow_spread`=`HERD_SPREAD`=40 m, `r_separation`=`HERD_SEPARATION`=22 m (rebaño disperso, ABSOLUTO);
`wolf_spawn_dispersion`=0.05·min (cúmulo de spawn); `wolf_skirt_gain`=1.5, `wolf_skirt_margin`=`r_face_safe`
(rodeo del rebaño); fuga en ESCOLTA NO-HOLONÓMICA (HUIR de frente a `cow_speed` / ENCARAR-PIN parado, gira a
`turn_rate`); **DISUASIÓN: `DETER_RADIUS`=20 m (radio CORTO, lobo audaz; eje de sensibilidad clave), `DETER_REPULSION`=8
m/s (esquiva radial; > `wolf_speed` → cerca domina la esquiva), `DETER_TANGENT`=6 m/s (BORDEO: arquea alrededor del
dron hacia la presa, rompe el atasco radial), `DETER_SLOWDOWN`=0.7 (rapidez máx dentro del radio; no se para);
parcial a corta `deter_w` (≤`r_face_safe` empuja a través)**; **ENVOLVENTE: `wolf_envelop_gain`=3.0
(reparto angular equiespaciado alrededor de la presa)**; **EVITACIÓN al HUIR: `COW_AVOID_RADIUS`=30 m,
`W_REFUGIO`=1.0, `W_EVITAR`=1.3 (las no-fijadas rodean a los lobos; el establo domina el neto)**; **BORDEO de
ZONAS PROHIBIDAS por el lobo: `WOLF_ZONE_SKIRT_BAND`=20 m (banda fuera de la frontera), `WOLF_ZONE_SKIRT_GAIN`=3
(tangencial: bordea la zona por fuera, no se clava ni entra; `safe_radius`=0.12·min=36 m, NO se toca)**; **CORZOS
(3c, NO-amenaza): `corzos_max`=0 por defecto (OFF, mundo actual bit a bit; >0 activa 3 tipos de episodio),
`corzo_speed`=4.0 m/s, `CORZO_FLEE_RADIUS`=30 m, `CORZO_FLEE_GAIN`=3 (deambula+huye de lobos/drones), AGRUPADOS
(`CORZO_GROUP_DISPERSION`=6 m, `CORZO_COHESION`=0.05, `CORZO_SEPARATION`=4 m) en la banda `[cow_spread+r_notice,
r_detect]` (dentro de SOSPECHA), el dron VUELA al contacto y solo a `r_confirm` el oráculo dicta (lobo→ESCOLTA /
corzo→descarta + vuelve al puesto + fase→VIGILANCIA), `corzo_episode_probs`=(1/3,1/3,1/3)** — constantes
ABSOLUTAS cerca de cabecera, afinables; presa adulta por exposición, fijada en t=0; presa ternero override con
1 lobo; `prey_abandon_dist` DEPRECADO. Todos afinables por render.)*

---

## 12. Referencias

- **Muro, C., Escobedo, R., Spector, L., Coppinger, R.P. (2011).** Wolf-pack (Canis lupus)
  hunting strategies emerge from simple rules in computational simulations. *Behavioural
  Processes*, 88(3), 192–197.
- **Janeiro-Otero, A., et al. (2020).** Grey wolf (Canis lupus) predation on livestock in
  relation to prey availability. (Selección de presa / depredación de ganado.)
- **Madden, J.D., Arkin, R.C., MacNulty, D.R. (2011).** Multi-robot system based on model of wolf
  hunting behavior. (Robótica inspirada en Muro.)
- **ICWDM (Internet Center for Wildlife Damage Management), "Wolf Damage Identification".** El ataque
  se concentra en **grupa, flancos y cuartos traseros**; **preferencia por terneros** frente a adultas.
  (Fundamenta el ataque por flanco y el ternero como objetivo blando preferente — §4.1/§4.2.)
- **BeefResearch.ca, "Cows & Wolves"** (estudio con collares GPS en Alberta): composición de presas de
  lobo ~**40% terneros / 40% añojos / <20% adultas**. (Fundamenta la presencia de terneros y su peso
  como presa preferente.)
- **Wolf Song of Alaska, caza en manada de presa grande:** la manada caza en grupo y **rara vez toda
  toca a la presa** a la vez. (Fundamenta la regla de **número mínimo** `n_min_adult` para tumbar a una
  adulta — basta un subconjunto flanqueando, no toda la manada.)
- **Ng, A., Harada, D., Russell, S. (1999).** Policy invariance under reward transformations:
  theory and application to reward shaping. (Shaping basado en potencial.)
- **Yu, C., et al. (2022).** The surprising effectiveness of PPO in cooperative multi-agent games
  (MAPPO).
- **Terry, J., et al. (2021).** PettingZoo: Gym for multi-agent reinforcement learning.
- **Bettini, M., Prorok, A., Moens, V. (2024).** BenchMARL: Benchmarking Multi-Agent Reinforcement
  Learning (TorchRL).
- **YOLO26** (Ultralytics, enero 2026): detección en tiempo real, end-to-end / sin NMS, orientada
  a drones y robótica, con asignación consciente de objetos pequeños (STAL).
- **Halter** (Nueva Zelanda): collares GPS de *virtual fencing* / *guided herding*.
- **Strömbom, D., et al. (2014).** (Modelo matemático de *shepherding*, por si se necesita en la
  escolta.)
