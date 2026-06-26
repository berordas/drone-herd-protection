# CLAUDE.md — Proyecto escolta (drones / lobos / vacas) · AI Lab, Comillas

Contrato de trabajo para este repo. El razonamiento completo está en `DISEÑO.md`;
esto es lo que no debe perderse entre sesiones ni tras un /compact. Trabajamos en español.

## Disciplina (siempre)
- **UNA cosa cada vez.** Implementa solo lo que pide el paso/prompt actual; no te adelantes.
- El **usuario lleva el diseño**; tú tecleas y verificas. Ante una bifurcación de diseño, **PREGUNTA** — no decidas por tu cuenta.
- Ciclo de cada paso: implementar → correr la **verja de regresión** → si todo verde, commit. **Nunca commitees en rojo.**
- Antes de dar un paso por bueno: mira el render / los checks.

## Verja de regresión (córrela antes de cada commit)
`face_check.py` (12/12) · `battery_check.py` (4/2/2) · `escort_check.py` (terminal+disparador+guiado+disuasión) · `drone_check.py`
Si algo se pone **rojo**: PARA y avisa. Nunca bajes la exigencia de un test para que pase sin decirlo.

## Invariantes CONGELADOS — no los toques sin permiso explícito
- Modelo vaca/lobo **"dar la cara, no apiñamiento"**: cono frontal, flanqueo, presa común fijada en t=0; re-fijación SOLO si la presa se **refugia**; **MÁX. 1 CAZA/EPISODIO** (tras matar, el paquete se **SACIA** y para — `pack_sated`; se desengancha); terneros + defensoras, spawn por sector, rodeo. Verificado en `face_check`.
- **Escala biológica ABSOLUTA** (en metros, NO fracción de `min(W,H)`): `HERD_SPREAD=40`, `HERD_SEPARATION=22`, `wolf_spawn_dispersion=5`, `r_notice=20`, `r_face_safe=6`, `capture_radius=3` (+ derivados).
- **Campo 300×300 m.** El LAYOUT escala con `min(W,H)`; la escala biológica NO.
- **Detección/confirmación:** `r_detect=100` (hay algo), `r_confirm=40` (es un lobo; geométrico determinista, placeholder hasta YOLO). Fases `VIGILANCIA → SOSPECHA → ESCOLTA`.
- **Guiado al refugio (paso 2) + NO-HOLONÓMICO:** en ESCOLTA la vaca corre HACIA DONDE MIRA (huir y dar la cara EXCLUYENTES): **HUIR** (sin lobo en `r_notice`) → heading al establo + avanza de frente a `cow_speed` (velocidad SIEMPRE a lo largo del heading); **ENCARAR/PIN** (lobo en `r_notice`) → gira a encararlo y se PARA → los lobos CLAVAN a la presa (pin-and-flank). **SOLO la PRESA fijada** (y su defensora si es ternero) se para; las no-fijadas siguen HUYENDO aunque tengan lobos cerca. **Ternero a-salvo ⟺ ternero DENTRO** (no cuando lo está su madre; sigue migrando hasta entrar él). Es INFRAESTRUCTURA del mundo (`escort_enabled`), no el coordinador. **Pastoreo/combate sigue HOLONÓMICO** (`escort_enabled=False` = adversario PURO; face_check intacto).
- **DISUASIÓN del dron (`_apply_deterrence`, infraestructura, gateada por `escort_enabled`):** dentro de `DETER_RADIUS=40` de un dron **ACTIVE** el lobo **ESQUIVA** (repulsión con falloff lineal, suma de todos los drones a tiro) y **FRENA** (rapidez máx × `DETER_SLOWDOWN=0.5`); la esquiva se SUMA al impulso de caza → **PARCIAL** (cerca domina la repulsión = despeja el pin; al borde domina la caza = empuja a través). `DETER_REPULSION=8` (> `wolf_speed`). **Sin habituación** (flag #6). Combate puro (`escort_enabled=False`) NO disuade → face_check bit a bit. El POSICIONAMIENTO de los drones = COORDINADOR (post-v2); aquí solo el efecto del mundo.
- **Dron:** `DRONE_MAX_SPEED=15`, `DRONE_MAX_ACCEL=4`; moverse gasta más batería que flotar.
- `baseline.py` **NO** se reescribe hasta congelar v2 (final de la escolta).

## Arquitectura fija
- **Investigar un contacto = REFLEJO** (infraestructura, igual en todos los coordinadores): el dron que detecta va él hacia el contacto, emite un mensaje al coordinador `{drone_id, contact_pos}`, confirma a `r_confirm` → ESCOLTA y se libera al coordinador.
- El **COORDINADOR** (lo que se compara) recoloca a los **demás** drones con ese mensaje. Dummy = no recoloca. Precedencia: el reflejo manda sobre el dron que investiga; el coordinador, sobre el resto.
- Collares/guiado y batería = **infraestructura del mundo**. Solo se compara el coordinador de drones.

## Orden de construcción
3a movimiento de drones ✓ → 3b detectar→confirmar ✓ → **paso 2 guiado al refugio ✓** → **disuasión del dron ✓** → 3c corzos → **congelar v2** → **coordinador: posicionar/interponer drones** (baja la tasa hacia ~50%) + reflejo-reactivo (consume el mensaje) → MARL.
*(Los coordinadores van DESPUÉS de congelar v2: v2 es la referencia que deben batir. Con Dummy+guiado+disuasión PASIVA la TASA baja a **~55%** (era ~80% solo guiado); la SEVERIDAD es ~0.5 muerte/ep (máx. 1 caza/episodio); la tasa la baja MÁS el coordinador posicionando drones para despejar pins activamente.)*

## Convenciones de código
Arrays NumPy `(N,2)` · RNG sembrado (reproducible bit a bit) · SI, `dt=0.1` · geometría derivada de `min(W,H)` · **sin números mágicos** (las constantes físicas son absolutas y etiquetadas cerca de cabecera) · `render.py` es **solo reproducción** (nunca llama a `step()`).

## Estado (commits)
`194a3ad` base · `37910b3` terminal · `e663504` disparador por dron · `4d1e708` campo 300 + escala absoluta · `886bd45` dispersión · `a15e2df` mov. drones (3a) · `fd893b8` detectar→confirmar (3b) · `49e0e22` consolidar docs · `144b7bd` paso 2 guiado · `1d44cdc` máx. 1 caza/episodio · `56ff75d` huida no-holonómica · `f42456f` 2 fixes huida (solo-presa-se-para + ternero-entra) · **disuasión del dron: esquiva+frena, parcial, despeja el pin (este commit)**.
