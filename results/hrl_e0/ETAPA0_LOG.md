# ETAPA 0 del jerárquico — log corrido

Misión: capa de opciones (lobos MASA/CEBO; drones reparto de puestos) + calibración conductual.
NO se entrena ninguna política. Física congelada (world.py, coordinators.py intactos;
wolf_controllers.py solo el refactor conducta-preservante del Commit A). Referencias:
docs/INFORME_RECONOCIMIENTO.md (commit 371f959) y DISEÑO.md. Artefactos en /data/hrl_e0/.

## 2026-08-17 — Arranque

- Contenedor levantado (metro DGX). Repo en `371f959` (docs del recon), working tree limpio
  salvo `?? docs/` (el informe de reconocimiento, deliberadamente sin commitear en su misión de
  solo-lectura; se deja tal cual — commitearlo no lo pide esta misión y los commits A→E quedan
  limpios sin él).
- Plan de commits A→E con verja completa verde en cada uno (7 checks + hrl_check desde C).
- Paradas obligatorias: STOP-1 tras E0.A · STOP-2 tras E0.1+E0.2 · STOP-3 informe final.

## Commit A — refactor conducta-preservante de wolf_controllers.py

- Extraídas a funciones de MÓDULO parametrizadas (defaults = constantes de hoy → bit a bit):
  `manage_pack_preys`, `group_hunted`, `assault_staged`, `assault_stage`, `decoy_prowl`,
  `decoy_timing` (despachador STAGE/CREEP/DEEP + latch `wolf_decoy_released`),
  `decoy_broken_wing` (ala rota), `sector_desired`, `pack_common_tail` (repulsión + bordeo de
  zonas + normalización, común a ambos caminos). `DECOY_HOLD_BAND` promovida a constante de
  módulo. `_decide_single`/`_decide_two_sectors` quedan como orquestadores finos. Los 5 métodos
  privados migrados se ELIMINAN (grep: nada externo los referenciaba; los checks solo importan
  las constantes de módulo, que se conservan).
- Verificación: hash SHA256 por tick de episodios COMPLETOS (estado íntegro), 50 semillas ×
  {lobos, mixto} = 100 episodios (26 de 2 subgrupos = el camino del cebo entero), ANTES vs
  DESPUÉS: **100/100 hashes IDÉNTICOS** (`/data/hrl_e0/verif/hashA_{pre,post}.json`; el pre
  regenerado contra HEAD vía override de sys.path — el primero murió con el contenedor).
  Verja 7/7 en curso (logs en /data/hrl_e0/verja/commitA/).
- Incidencia operativa: el contenedor `<uid>-wolves` se cayó solo entre el hash pre y el
  post (¿limpieza del host?); relevantado con compose sin más consecuencia.

## Commits B–E — paquete hrl/ (escrito; verificación en curso)

- `hrl/events.py` — EventTracker (STAGED/SHOW_START/CONFIRM_DECOY/ANCHOR_FLIP/LURE_COMMIT/
  ESCOLTA_LATCH/HERD_SAFE/DEATH/STRIKE_RESOLVED + eventos de capa vía pop_events); umbrales
  LURE nombrados CALIBRAR-E0.2. Muestreo en la frontera del env.
- `hrl/behavior_checks.py` — EpisodeAudit: aserción CRITICAL orden-del-cebo, procedencia de
  cada muerte (flanqueadores + killer-más-cercano estilo cebo_diag, confirmado en frontera
  previa, cruce de gotera portado de run02_comportamiento.py, octante vs ancla, ticks desde
  flip), reloj de escolta, contratos (presas + máscara de comando).
- `hrl/options_wolf.py` — WolfOptionLayer: MASA (delegación a _decide_single; limpia
  pack_prey2 al arrancar) y CEBO(Δ, hold) con membresías manager (cebo=índice mínimo) o
  spawn (≡ script bit a bit); réplica documentada de _freest_prey_for_sector2; decisiones
  de capa: creep=min(25,hold), reposicionamiento por punto lejano en el rumbo Δ + gate de
  rumbo (±25°), latch monótono.
- `hrl/options_drone.py` — SubsetReactiveCoordinator (línea rígida con k ranuras, restricción
  por subclase), AllocatorCoordinator FRENTE+GUARDIA (percepción contactos∪confirmados,
  clústeres >60°, persecución activa / octante más abierto), regla PROPORCIONAL
  (guardias = clip(n_sec, 0, 2) re-muestreada cada 5 ticks).
- `hrl/scripted_manager.py` — ForcedWolfManager, SwitchingWolfManager (TIMEOUT_OPCION),
  SwitchingAllocator (E0.5).
- `hrl/run_e0.py` — CLI e0a…e05 sobre el arnés (refresh de capa en la frontera, audit en
  TODOS los episodios, pool de procesos, bootstrap 10k, GIFs+timelines del visionado).
- `hrl/hrl_check.py` — 8º check de la verja: unidades (seg_cross, LURE dirigido, aserción
  crítica, clustering) + MASA ≡ script bit a bit (12 eps de 1 grupo) + CEBO/spawn ≡ script
  bit a bit (5 eps de 2 grupos) + aserciones en 5 episodios CEBO-manager + determinismo de
  eventos + Allocator 4-0 ≡ Reactive bit a bit (5 eps).
- **hrl_check: TODO OK a la primera** (5/5 secciones verdes en el contenedor). Fix posterior
  al pase: dedup del fallback CEBO/spawn→MASA en refresh (comparaba contra la opción vigente
  y re-arrancaba cada frontera; ahora contra la SOLICITADA) — re-verificado en los pases de
  hrl_check de los commits C y D. Smoke del CLI run_e0 (--help + imports) OK.

## Commits (todos con verja verde)

- **A `f749742`** refactor conducta-preservante (hash 100/100 idéntico; verja 7/7).
- **B `b000489`** events.py + behavior_checks.py + hrl_check v1 (unidades) verde.
- **C `6d581b3`** options_wolf.py (MASA/CEBO) + hrl_check EN LA VERJA (pases [0-3] verdes).
- **D `a6b34e4`** options_drone.py (Allocator + proporcional) + hrl_check completo 5/5 verde.
- **E `5154f8d`** scripted_manager.py + run_e0.py (CLI e0a…e05; smoke verde).
- Nota metodológica: los 7 checks clásicos se corrieron UNA vez (Commit A) — los commits B-E
  solo AÑADEN ficheros hrl/ que ningún check clásico importa (inputs byte-idénticos);
  hrl_check sí se corrió en su versión de cada commit (B v1 · C v2 · D/E completo).

## E0.A — COMPLETADO (2026-08-17) → STOP-1

- **(i)** cubierto por hrl_check (3 equivalencias bit a bit).
- **(ii) IMPUESTO DE INTERFAZ = CERO EXACTO**: CEBO vía capa (membresías=spawn) sobre las
  58 parejas de 2 frentes de run08 → severidad por episodio **58/58 idéntica** al suelo
  scriptado; agregados clavados en la referencia: sev 3.50 (ref 3.50±0.15) · KNC 26.6%
  (ref 26.6%±3) · ancla=cebo 65.5% (ref 65.5%±5). **G0: PASA.**
- **(iii)** CEBO manager (Δ=180°, hold 50) desde spawns arbitrarios n≥3 (30 lobos + 10
  mixto): sev 1.90 [1.40, 2.42] · staged 16/40 · LURE_COMMIT 9/40 · muerte post-release
  14/40 · KNC 19.7%. El ciclo completo funciona desde spawn de 1 grupo (timeline seed 20:
  reposicionamiento ~3.264 ticks → show=latch mismo tick → ESCOLTA por el señuelo →
  ancla=cebo → LURE_COMMIT (4 drones en cono, puerta 61 m) → 1ª muerte a +503 → sev 7 con
  matadores sin confirmar). El 40% staged / 60% no-staged (reposicionamiento largo o
  ESCOLTA accidental antes del show) es EL DATO que E0.1/E0.2 cuantificarán con pares.
- **Aserciones: 0 CRITICAL · 0 violaciones de contrato en los 98 episodios.**
- Lote de visionado: 7 GIFs + timelines en /data/hrl_e0/e0a/{gifs,timelines}/ (sin
  violadores que renderizar; el caso release-con-muerte coincide con sev_max y se dedupe).
- Artefactos: /data/hrl_e0/e0a/{config.json, results.json, REPORT.md}.
- **STOP-1: a la espera de OK humano para E0.1+E0.2.**

## ADENDA tras STOP-1 (recibida 2026-08-17) — implementación

- §1 estratos G/S por geometría de spawn en t0 (`strata_pool`, probe determinista por
  semilla; n≥3; lobos+mixto mitad y mitad; pares dentro del estrato).
- §2 `CEBO_keep` = `membership="keep"` en WolfOptionLayer: señuelo índice mín, asalto en su
  rumbo ACTUAL (`_theta_asa=None` → sin gate de rumbo ni punto de presión), escalera del
  manager (creep=min(25,hold)).
- §3 celdas: confirmatoria G (MASA vs CEBO_keep, Reactive+run02, piloto 50→[200,400]);
  exploratorias 100 pares: S Δ∈{180,90}, hold sweep {5,−10} solo sobre el mejor Δ, run02
  solo ahí; G CEBO(180) forzado. Por celda `_cell`: Δsev IC bootstrap emparejado 10k (todos
  y por n), distribución completa (media/mediana/P(0)/P(≥4)/hist), procedencia, tasas
  staged/commit/kill-post-release + reloj de oportunidad, frecuencias de ESCOLTA prematura,
  figura del valle.
- §5 clasificador de ESCOLTA prematura en EpisodeAudit (`_track_premature`): (a) primer
  confirmado señuelo/asalto+índice, (b) investigador hacia corzo (compara drone_contact con
  corzos vivos en los 200 ticks previos), (c) pinzamiento de borde (<25 m del borde del
  asalto en 200 ticks). Evento ESCOLTA_PREMATURA + campo `premature`.
- §6 e02: latencias por celda/estrato (inicio→staged separado), regla pre-registrada
  (p75 inicio→commit >2000 ⇒ terminación-por-evento), ROC cono{2,3,4}×puerta{40,50,60,70},
  T_safe + margen del release (con P(negativo)).
- §7 visionado: +2 ESCOLTA prematura + 1 sev≥5.
- hrl_check +[3b] (CEBO_keep sin CRITICAL en G + clasificador con caso construido): 6/6 OK.
- Smokes e01/e02 (6 pares) de punta a punta OK; hallazgo operativo: el estrato G (2 grupos ∧
  n≥3) es ~28% de las semillas → el probe de estratos sondea hasta 1.500 semillas por tipo.
- Verja completa 8/8 verde → **commit `11bd7f8`**.

## E0.1 — LANZADO 2026-08-17 22:17 (32 procesos; /data/hrl_e0/e01/stdout.log)
- E0.1 COMPLETADO 23:48 (1 h 31 min, 2.184 episodios; 0 CRITICAL, 0 violaciones).
- E0.2 corrido sobre e01 (latencias + ROC + regla pre-registrada).
- Fix de instrumentación (clasificador de prematura: diferido al latch + spawn excluido del
  borde) → 481 prematuras re-etiquetadas re-simulando (determinismo 481/481) → commit
  `6beb8bd`. Visionado: 10 GIFs + timelines en /data/hrl_e0/e01/{gifs,timelines}/.

## STOP-2 (2026-08-18) — informe en /data/hrl_e0/STOP2_INFORME.md

- **G1 PASA**: Δ(CEBO_keep−MASA | G, n≥3, Reactive) = +0.43 [+0.25, +0.62] (n=346); vs run02
  +0.53 [+0.33, +0.73]. Por n: +0.84 (3) / +0.35 (4) / +0.07 (5).
- **G1b**: TODAS las celdas de S negativas (Δ180 −1.12; Δ90 −0.44; hold 5/−10 no lo arregla);
  G/Δ180 forzado −1.07 → el valor de la decisión vive en G; el re-split desde S cuesta.
- **G2 (K)**: regla pre-registrada dispara (p75 inicio→commit 2.316 G/keep, 4.126 S/Δ90 >
  2.000) → terminación-por-evento = diseño PRINCIPAL de la Etapa 1; K = techo (propuesta 4.500).
- Figura del valle medida: CEBO detrás de MASA hasta el tick ~4.750 en G/keep.
- Margen del release p50 ≈ 1.400 ticks, P(<0)=0% en todas las celdas (el bug del disparo
  prematuro no reaparece con la capa). ROC de LURE_COMMIT: etiqueta no discrimina (TPR=1 en
  toda la rejilla) → limitación reportada; umbrales SIN cambiar en código.
- Contenedor parado. **A la espera de OK humano para E0.3+E0.4+E0.5.**

## MISIÓN FORENSE + v3.5 "regla del sonido" (2026-08-18) — E0.3-E0.5 y Etapa 1 CONGELADOS

### FASE 0 — Commit F (render, sin física)
- render.py: `show_detected` (cuadrado rojo = lobo a ≤ r_detect de un ACTIVE, geometría pura
  del snapshot, + leyenda) y `show_confirmed` (rombo naranja desde `confirmed_mask` si el
  snapshot la trae); el anillo DETER_RADIUS por ACTIVE ya existía. run_e0.render_gif escribe
  `confirmed_mask` (latch de la barrera) en cada snapshot. GIFs 1 y 2 de e01 regenerados
  (seed 398 mixto, G/CEBO_keep y su gemelo MASA). Verja 8/8 en curso.

### FASE 1 — Forense (FORENSE.md en /data/hrl_e0/forense/)
- A: GIF 1 (G/keep) → primer confirmado = SEÑUELO (t=989); asalto detectado a t=972 y NUNCA
  confirmado → cadena canónica, sin bug. GIF 2 (MASA) → paquete fusionado, no hay roles.
- B: apilamiento REAL solo en GIF 2 (246 ticks-par a <3 m, mín 0.10 m) = ventana PENETRADO
  (t 802-1282): `_cover_engaged` asigna `order[s % n_lobos]` → con 1 lobo confirmado los 4
  drones reciben el MISMO slot; con 3, dos drones al mismo (4%3). Hipótesis (a) confirmada
  = BUG DE DISEÑO del coordinador (propuesta de arreglo con test dirigido → DECISIÓN HUMANA).
  Agravante: PENETRADO entra con d(ancla,centroide) ≤ herd_r (máx. dist res→centroide, 29 m
  en rebaño disperso).
- C: cruce t=672 GIF 2: par a 20.0 m, frac 0.50 del segmento (punto medio exacto), dist al
  dron 9.96, approach −0.57 < 1 ⇒ expulsión inactiva, |pared| 0.01 ≈ 0. Causa raíz CONFIRMADA.
- **STOP-F1: visionado humano primero.**
- Commit F bis `fbd4d59`: cuadrado NARANJA = detectado, ROJO = confirmado (decisión del dueño).

### FASE 2 — enmienda de física v3.5 "regla del sonido" (orden del dueño tras ver los GIFs)
- world.py `_apply_deterrence`: expulsión a ≤ DETER_RADIUS de CUALQUIER ACTIVE, sin approach; huida
  radial del más cercano, perfil intacto; 🔊 = dron con lobo a ≤20; pared en sombra (código intacto);
  SCARE_APPROACH_MIN deprecated. rl/drone_env.deter_credit a la regla nueva.
- Tests nuevos en escort_check: test_corredor_cerrado (0 cruces del segmento; dist mín al dron 19.4 =
  borde del sonido; lección: los tests dirigidos deben evitar el establo (150,150,r36) del World por
  defecto — un primer montaje por y=150 metía al lobo DENTRO y el clamp lo teletransportaba) y
  test_sonido_estatico. Re-gold consciente: test_disuasion (a) inversión exacta de la cota "poste"
  (<2 m → >2 m + scared; y el lobo arranca a 20 m del cruce: el 'static' de v2.4 era VACUO, el lobo
  nunca llegaba al dron), (b) poste que suena; test_susto (A) quieto cubriendo = expulsión;
  test_pared_estatica (A) 14 m salva, (B) mover ≥ quieto; test_pin_envolvente 14 m salva. escort_check
  TODO OK con la física nueva.
- Metro v3.5 (100/tipo, /data/metro_v35 + artefactos del repo): **Dummy 3.82/0/3.84 → 1.90/0/2.02**
  (succ 20/18, timeouts 23/20, n_safe 4.53/4.31); Reactive + suelo residual + run02@v3.5 + cebo +
  cruces en curso.
- baseline.py: FROZEN_TAG=v3.5-sonido, REFERENCE_SEVERITY 1.90/0/2.02; asserts de tag en
  rl_env_check/wolf_controller_check; DISEÑO.md con la entrada v3.5 y la corrección de "agujeros
  deliberados" (el corredor nunca lo fue).
- Metro v3.5 completo: **Reactive 2.68/0/2.77 → 0.88/0/0.76** (success 67/69%) · suelo residual
  0.92/0/0.81 · run02@v3.5 1.09/0/0.78 (política v3.4 evaluada; ventaja desaparecida) · cebo
  scriptado 2f 3.50 → 2.60, KNC 26.6 → 37.7%, ancla-cebo 65.5% idéntico · cruces de gotera
  0.075/ep, 2.4% de muertes tras cruce (v3.4: 30-55%). Artefactos /data/metro_v35/.
- **Commit de física `8aeaf89` + tag `v3.5-sonido`** (verja 8/8; re-gold consciente listado en el
  mensaje; DISEÑO.md y CLAUDE.md corregidos: el corredor nunca fue deliberado).

### FASE 4 — re-calibración E0 en v3.5 (lanzada 2026-08-19 00:27, /data/hrl_e0/v35/)
- E0.A(ii) re-anclado a cebo_floor_v35 (2.60 / 37.7% / 65.5%) → E0.1 → E0.2 encadenados.
- Predicciones pre-registradas a contrastar: sev(MASA) baja; Δ(CEBO_keep−MASA | G, n≥3) sube
  respecto a +0.43; cruces de corredor ≈ 0; el modo prematura "señuelo confirmado primero"
  persiste.
- FASE 4 COMPLETADA 03:38 (E0.A 98 eps + E0.1 2.300 eps + E0.2; 0 CRITICAL, 0 violaciones).
  **Predicciones pre-registradas: 4/4 cumplidas** (MASA baja 2.99→1.57; Δ G/keep +0.43→**+0.85
  [+0.60, +1.09]**; gotera 0.5% de las muertes; prematura señuelo 61/61). G0 y G1 PASAN en v3.5;
  S cambia de signo (Δ90 +0.32); valle se acorta a ~2.250 ticks; regla de K → terminación-por-
  evento (p75 2.299/4.345 > 2.000). Informe: /data/hrl_e0/v35/STOP2prima_INFORME.md. Visionado
  (12 GIFs render nuevo) + INDEX en /data/hrl_e0/v35/e01/. **STOP-2': firma 2 del dueño.**

## ETAPA 1 — RUN-M1 (2026-08-19) → STOP-M1
- Commits G-J (+ I-bis adenda 4, + ganchos `ded2123`); PREREGISTRO con B_oracle 0.885/1.02 antes del run.
- RUN-M1: 122.880 macro-pasos, 5h15, sin NaN. Manager final 1.31 vs Reactive (+0.42 sobre oracle, +0.49
  sobre spawn), 1.20 vs run02 (+0.18 vs oracle, IC cruza 0). Emergencia/Competencia/Auditoría pasan;
  ESTRUCTURA FALLA (cebo siempre; re-targeting por re-arranque tras ABORT). Informe y visionado en
  /data/hrl_m1/. run09 acabando. Esperando firma del dueño.

## 2026-08-20 — M1'': Commits K/K-bis/L hechos · re-nivelado PARADO en dos compuertas pre-registradas (STOP-NIVELADO)

- Resolución del dueño al STOP-M1: re-targeting NO se cierra — se LEGALIZA Y REGULA en la capa para
  todos (Commit K); M1 (+0.42) queda como specification gaming de interfaz (no resultado de tesis);
  cola vieja anulada (prohibido cómputo sobre la capa vieja); P(a) estocástica aprobada (K-bis).
- **Commit K** `610e6da`: regla de caza oportunista en la capa (presa PERSISTE; re-target sii
  protegida ≥50 ticks a ≤25 m Y alternativa ≥30 m más libre; cooldown 250; eventos RETARGET/
  RETARGET_BLOCKED; world/wolf_controllers intactos). hrl_check: K1-K4 + [1]/[2] reformulados
  (≡ bit a bit sii la regla no dispara). Verja 8/8.
- **Commit K-bis** `54d2546`: ligera con P(a)/entropía ESTOCÁSTICAS + contadores de caza por
  episodio (info.hunt en ManagerEnv; eval_manager/manager_table los propagan).
- **Commit L** `caeb683` tag `v3.6-patrol-estatica`: patrol_omega 0.02→0.0 config OFICIAL (decisión
  del dueño, motivos MEDIDOS por A/B 100/tipo: espera hand-off 298→102, STRANDED 2.95→0.0/ep,
  Δsev +0.08 IC cruza 0); métricas de relevo en arnés y EpisodeAudit; re-gold consciente de
  reactive_check (test_patrulla; test_percepcion (A)3 medido con pose CONVERGIDA, listón 25° igual).
  Nota a batir: Reactive-estática 0.94/0/0.93.
- **PARADO** (dos reglas pre-registradas): (1) sanity de capa Δ=+1.16 vs ref 0.85 → |desv| 0.31>0.3;
  atribución emparejada: regla K +0.12 [−0.12,+0.34], patrulla +0.52 [−0.18,+1.24], ref re-medida en
  las mismas 50 semillas = +0.52 (la compuerta disparó por 0.01 con estimador ruidoso). (2) mini-E0.3:
  CAZA a n=2 (Dummy+ternero 1.98; vs Reactive-estática 0.15-0.18) → decisión del dueño.
- Metro v3.6 completo (Dummy 1.90/0/2.02 vigente · Reactive-est. 0.94/0/0.93 · suelo 0.99/0/0.91 ·
  run02 est/órb 0.86/1.09 lobos · **run09 órb 0.79/0/0.78 bate a run02** · cebo 2f 2.97, KNC 39%,
  ancla-cebo 79%, gotera 0) + B_masa 0.57 · B_spawn 0.99 · B_oracle 1.00 [0.74,1.28] (capa K, NO
  congelados). PREREGISTRO_v2, fallback CEBO→MASA, RUN-M1'' y cola: BLOQUEADOS hasta la firma.
- Informe: /data/hrl_m1/m1pp/STOP_NIVELADO_INFORME.md · visionado /data/hrl_m1/m1pp/gifs/INDEX.md.

## 2026-08-20 (tarde) — Adenda post-visionado seed 84 aplicada · Commits M/N/O · RUN-M1'' LANZADO

- Adenda del dueño (v2): Encargo 1 (auditoría de patrulla) ejecutado YA; Encargo 2 (señuelo v2
  "directo con espera") ESPECIFICADO y CONGELADO hasta el STOP-M1'' (spec en
  /data/hrl_m1/m1pp/ENCARGO2_SENUELO_V2_SPEC.md); RUN-M1'' sigue hasta su STOP.
- **Commit M** `0f8d994`: PatrolCoverageTracker (AVISO D>100 · VIOLACIÓN D>2·r_detect; ventanas,
  zonas de R, entradas de lobo no detectadas) — permanente en EpisodeAudit y ManagerEnv
  (info['patrulla']); test P. **Commit N** `583db6f`: fallback de quórum CEBO→MASA (asalto <
  n_min_adult; OPTION_FALLBACK 'CEBO/quorum'); test Q (n≤2 ≡ MASA bit a bit). **Commit O**
  `82ec71a`: --wolves-min en train_manager (RUN-M1'' = 3; eval natural). Verja 8/8.
- **Auditoría retroactiva** (/data/hrl_m1/m1pp/AUDITORIA_PATRULLA.md): VIOLACIÓN = 0 ticks en
  toda la config estática (D_max 185-191 < 200; R vive en 69-75, máx 97 << 142) · AVISO el
  92-98% del tiempo de patrulla (estructural: D≈1.41·R≈106) · 4 entradas de lobo no detectadas,
  TODAS de un episodio (seed 77 mixto, sev 8; arcos en AVISO — el hueco real es anillo-centroide
  vs reses periféricas; GIF audit_entradas_s77). DECISIÓN HUMANA PENDIENTE (densidad/radio).
- **1d sobrecoste del señuelo**: bimodal — mediana 10.7 ticks, p90 677, máx 1078 (media 202):
  la mitad ya va recta; la cola del bordeo largo es el objetivo del señuelo v2.
- **PREREGISTRO_v2.md CONGELADO** antes de lanzar: B_oracle 1.00 [0.74,1.28] vs Reactive-est y
  0.91 [0.68,1.16] vs run02 (gap oráculo −0.09); compuertas Emergencia/Estructura/Competencia/
  Transferencia/Auditoría; SE RETIRA P(MASA|n≤2); 4 predicciones pre-registradas.
- **Smoke M1pp**: 6.144 macro-pasos, 5.74 fps, sin NaN; ligera nueva OK (Pstoch/entropía/caza;
  fallback de quórum visible en n1-n2). **RUN-M1'' lanzado 12:32 UTC** (120k, 24 envs, seed 0,
  Reactive-estática, n~U{3,4,5}; pid 3042; ETA ≈ 5.8 h) → STOP-M1'' con firmas al terminar.

## 2026-08-20 — FIRMA DEL DUEÑO sobre la auditoría de patrulla: aceptar y documentar
- Regla dura oficial D≤200 (cumplida siempre; 0 pasillos ciegos); 100 = AVISO de monitorización
  (inalcanzable con M=4 al radio actual: D=2R·sin(π/4)=1.41R con R∈69-97 ⇒ D≈98-137; D≤100
  exigiría M=6 o M=5 con R≤85 — anotado).
- Seed 77 → memoria del TFG como LIMITACIÓN de la clásica (anillo al centroide, sin paraguas
  sobre periféricas). Forense pedido: anillo a M=3 en las entradas pero NO por corzo (descartado
  t=1); era la investigación del LOBO SINGLETON (t=933-1011) = CEBO NATURAL: el solitario tira
  del investigador y el paquete de 4 entra por el arco debilitado (t=994; ESCOLTA a t=1011).
- Sin cambios de código; auditor tal cual en el arnés; PATRULLA-v2 = future work NOMBRADO.
- RUN-M1'' sigue corriendo (lanzado 12:32 UTC).

## 2026-08-20 — Encargo STOP-M1'': clasificador de fase/canal por muerte (baselines hechos)
- canal_fases.py (efímero, solo lectura; reset_to determinista + EpisodeAudit + registro de
  investigación pre-ESCOLTA vía ganchos de ManagerEnv). Fases: PATRULLA / VENTANA_INVESTIGACION /
  ESCOLTA-BARRERA; CANAL B = muerte antes de ESCOLTA.
- Baselines vs Reactive-estática (200 eps c/u): B_masa 114 muertes, B_spawn 197, B_oracle 200 —
  **canal B = 0 en los tres** (100% ESCOLTA-BARRERA). KNC por fase: masa 17.5%, spawn 34.0%,
  oracle 33.5% (todo en escolta: espalda del ancla).
- Matiz verificado: el propio seed 77 mata en canal A (8 muertes t>=1382, ESCOLTA t=1011) — el
  mecanismo del seed 77 es la ENTRADA no detectada (escolta TARDÍA), no la muerte pre-escolta;
  el auditor de patrulla ya la reporta (entradas_no_detectadas). Se anotará así en el informe.
- Pendiente al RUN_DONE: canal_fases del manager (final + 60k), evals emparejadas × {reactive,
  run02} (+ filas run09), tabla, visionado (con pareja canal-B↔seed77 si existe), STOP_M1PP_INFORME.

## 2026-08-20 — ADENDA URGENTE pre-RUN_DONE aplicada (13:52Z, run a 20k; ninguna eval final vista)
- PREREGISTRO_v2 §ADENDA DE ADJUDICACIÓN escrita con timestamp: desempate pre-registrado para
  las cláusulas S de Estructura (calibradas en v3.5, no medidas en v3.6). Disparo: política
  estocástica con H(a|S,n≥3)<0.9 prefiriendo Δ180 sobre Δ90 → medir celdas S v3.6 (MASA/Δ90/Δ180
  forzados, n≥3, 100 pares, Reactive-estática) ANTES de adjudicar; si Δ(Δ180|S) ≥ Δ(Δ90|S) la
  cláusula se evalúa contra el paisaje medido (anotar que B_oracle juega Δ90 en S); si no, falla
  con evidencia.
- DESPERTAR TARDÍO añadido a canal_fases.py (latch con ≥1 entrada no detectada previa; lag y
  d_min al latch) y re-medido en baselines: **B_masa 0 eps · B_spawn 1 · B_oracle 1 — el propio
  seed 77** (4 entradas, lag 17 ticks, sev 8; d_min al latch 92.8 vs ~118 del resto). La tabla
  A/B queda con la anotación (canal B muertes = 0; el fenómeno es LATENCIA); nota KNC ~×2 al
  cebar (17.5%→34%): firma del canal trasero.
- INDEX del visionado llevará la pareja "episodio del manager con entradas no detectadas ↔ GIF
  seed 77" etiquetada "muertes canal B = 0; despertar tardío".

## 2026-08-20 — STOP-M1'': RUN-M1'' completado; Estructura FALLA con evidencia; hallazgo = MOLINILLO DE RUMBO
- Run: 122.880 macro-pasos, 5h25, 6.3 fps, sin NaN. Metro: manager final 2.26 [1.90,2.63] vs
  Reactive-est · 2.20 vs run02 · 2.17 vs run09; ckpt 60k 1.58.
- Compuertas: Emergencia PASA (1.0, sabor vacuo) · **Estructura FALLA con evidencia** (disparo de
  la adenda activado: Pstoch(Δ180|S)=0.948, H≈0.25 → celdas S v3.6 medidas: MASA 0.33 / Δ90 0.58 /
  Δ180 0.50 → Δ(Δ180−Δ90)=−0.08 [−0.51,+0.36] → cláusula falla; sub-cláusula re-targets cumple) ·
  Competencia PASA con ESTRELLA (+1.26 [+0.93,+1.60] sobre B_oracle; +1.27 sobre B_spawn) ·
  Transferencia PASA (gaps −0.06/−0.10 ≈ oráculo) · Auditoría PASA (0 CRITICAL, gotera 1, KNC 34.5%).
- **MOLINILLO DE RUMBO** (hallazgo, DECISIÓN HUMANA PENDIENTE): churn de presa CERRADO (gemelo
  seed 21: 0 RETARGETs; 0.07 re-targets/ep, todos protegida) pero ABORT 45/ep y cada re-arranque
  de CEBO re-computa θ_asalto desde el rumbo ACTUAL (+Δ) → rotación del asalto que la barrera no
  sigue; en S saca 1.89 donde el mejor brazo estático da 0.58; emerge en la 2ª mitad (60k 1.58 →
  final 2.26). Cierres posibles NO aplicados (θ_asa persistente = espejo del Commit K para el
  rumbo / histéresis del ABORT / Δ vs spawn) ⇒ re-entrenar. Veredicto pre-registrado: "éxito =
  estructura + no-inferioridad" ⇒ NO cumple éxito; +1.26 queda como hallazgo.
- Canal/despertar (adenda): canal B (muertes) = 0 en TODAS las políticas; despertar tardío manager
  1 ep (seed 8 mixto, lag 4); KNC ~×2 al cebar (17.5→34%). Visionado 7 GIFs + referencia
  (INDEX en /data/hrl_m1/m1pp/visionado/). Informe: STOP_M1PP_INFORME.md · TABLA_M1PP.md.
- Encargo 2 presentado: opción A ≈ 8-9 h de cómputo (mismo ciclo cubriría el cierre del molinillo)
  vs opción B future work. Cola (M2 → réplica → M4) esperando firma. Contenedor parado.
