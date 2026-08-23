# VERIFICACIÓN DEL PAPER — cifras, figuras y referencias (solo lectura; ningún run nuevo)

Generado 2026-08-23 13:19 a partir de los artefactos de `/data` (= `rl_data`) y del repo. Cada valor de §1 se ha leído de un
archivo concreto (JSON/log/código; "secundario" = solo en un informe .md). Nada viene de memoria. Figuras en `figs/` (PNG 300 dpi,
etiquetas en castellano, sin rutas personales). Tabla maestra de referencia: `/data/TABLA_MAESTRA.md`.

## 0. Resumen de veredictos (lo que hay que tocar en el paper)

| # | afirmación del paper | veredicto | valor correcto + ruta |
|---|---|---|---|
| 1 | "mejores planos 0.57–0.72 vs suelo 2.68" | **CORREGIR (versiones mezcladas)** | run02/run03 (0.57–0.72) se midieron en v2.4.1 contra un scriptado de **2.77 / 2.80** (`/data/wolves/run02/eval_final_10M.txt`, `run03/eval_final_10M.txt`, `run04_floor.txt`); **2.68** es Reactive/scriptado de **v3.4** (`/data/wolves/run08_dieta50/eval_floor_v34.json`). Escribir "0.57–0.72 vs 2.77 (v2.4.1)" o usar run08 para v3.4 (2.17 vs 2.68). |
| 2 | "B_masa 0.57" | **CORREGIR → 0.56** | `/data/hrl_m1/eval/masa_v37__reactive.json` `resumen.sev = [0.56, 0.395, 0.735]`; 0.57 es el B_masa de v3.6 (`/data/hrl_m1/m1pp/TABLA_M1PP.md`). |
| 3 | "3.2 decisiones/episodio" | **CORREGIR → 3.5** (crudo 3.465) | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` `resumen.decisiones_media = 3.465` (vs run02 3.5; vs run09 3.43). |
| 4 | "run01: 1 muerte en ~2.400 episodios" | **NO VERIFICABLE en primario / DUDA** | `/data/wolves/run01/train.log` tiene `ep_rew_mean = 0.010` en DOS ventanas separadas (≈1,08–1,16 M y ≈1,70–1,77 M pasos) ⇒ compatible con **2 muertes**; episodios ≈ **2.270** (Σ Δpasos/ep_len_mean); "~2.400" solo en DISEÑO.md. Recomendado: "una o dos muertes espontáneas en ≈2.300 episodios (2,48 M pasos)". |
| 5 | "M2 ×3.3 cómputo" | OK con reserva → "≈×3.25" | segundos 20622.4 / 6347.1 = 3.249 (`/data/hrl_m1/M1pppp/summary.json`, `/data/hrl_m1/M2/summary.json`). |
| 6 | "Δ vs Reactive −0.53/−1.55/−1.01" (D2) | OK pero **atribuir** | son de la **réplica** (seed 1); RUN-D2 = −0.53/−1.58/−1.09; conjunto = −0.53/−1.56/−1.05 (`/data/hrl_d2/TABLA_D2_R1.md`). |
| 7 | "3-1 = 0.019" | OK pero atribuir | es de la réplica (`/data/hrl_d2/D2_r1/summary.json`); RUN-D2 3-1 = 0.000 y 2-2 = 1.000. |
| 8 | "KNC 0" (D2) | OK con matiz | `knc_frac = 0.0` en natural y cebo-2f; en la celda manager lobo es `None` (no definido). |
| 9 | "STALLs 189/400 y 147" | OK | 189 = 153+20+16 y 147 = 112+22+13 sobre **400** episodios cada uno (los informes originales decían 300: fe de erratas ya anotada). |
| 10 | valle ≈2.250 / ≈4.750 | OK (rejilla de 250) | cruce exacto tick a tick: **2057** (v3.5) / **4686** (v3.4) (recalculado desde `episodes[].deaths[].t`; ver fig_valle). |
| — | todo lo demás (§1) | **OK** | constantes del mundo, K_MAX, ε, δ, KNC 26.6→13 %, reparto 5.7→5.3 %, run09 0.77 vs 0.93, celdas S, B_spawn/B_oracle, +0.10 [+0.03,+0.19], réplica 1.69 y +0.03, transferencia, jugada 1.00, ABORTs 0.28, coste ≈0, P(Δ90|S)=1 en 3/3, tabla D2 y Δ conjuntos, P(guardia) 1.000/0.943, carrera 78–89 %, +0.42, 45→0.28, 9/20, seed 21 7→6→0. Redondeos dobles a vigilar en §4.6. |

## 2. Figuras (`/data/paper/figs/`; copia en `results/paper/figs/` del repo)

| archivo | tamaño | contenido | artefactos de origen | notas |
|---|---|---|---|---|
| `fig_valle.png` | 106 KB | Valle del cebo: muertes acumuladas medias CEBO_keep vs MASA (estrato G, vs Reactive), v3.5 en trazo continuo (375 pares) y v3.4 punteado (346 pares); cruce marcado. | /data/hrl_e0/v35/e01/results.json y /data/hrl_e0/e01/results.json (episodes[].deaths[].t, brazos cebo_keep_h50_reactive vs masa_reactive emparejados por (seed, kind)) | Cruce EXACTO (tick a tick): v3.5 t=2057, v3.4 t=4686; los informes dan ≈2.250 / ≈4.750 porque usan rejilla de 250 ticks (primer punto con CEBO ≥ MASA). Para el pie: 'cruce ≈2.100 (v3.5) / ≈4.700 (v3.4)' o mantener los de rejilla diciendo 'rejilla de 250 ticks'. Valores finales v3.5: CEBO 2.42 vs MASA 1.57; a t=1000: [0.28, 0.55]. 8,5 cm. |
| `fig_tradeoff.png` | 93 KB | Trade-off cobertura/reparto (versión de columna, 1 panel, eje x log): PENETRADO vs severidad por celda (natural/cebo-2f/manager lobo) y defensa (Reactive 4-0, proporcional, manager dron seed 0 y seed 1), IC 95 %. | /data/hrl_d2/e04_{reactive,proporcional,dronemgr,dronemgr_r1}__{natural,cebo2f,manager}.json (episodes[].penetrado, .sev) | 8,5 cm. Versión doble columna con 3 paneles: fig_tradeoff_ancho.png (17,5 cm). |
| `fig_tradeoff_ancho.png` | 85 KB | Idem, 3 paneles (uno por atacante), 17,5 cm. | ídem | — |
| `fig_cebo_frames.png` | 232 KB | Tira de 3 fotogramas de la jugada entera del manager lobo (seed 98, mixto, S, Δ90): (a) show t=1231, (b) suelta t=1419, (c) golpe t=2375; anotaciones señuelo/asalto/rebaño/patrulla/barrera/establo. | /data/hrl_m1/m1pppp/visionado/gifs/jugada_entera_S_seed98_mixto_sev2.gif (frame = t//3; 860 frames de 2.579 ticks) + timeline /data/hrl_m1/m1pppp/visionado/timelines/jugada_entera_S_seed98_mixto_sev2.txt (t_staged 901, t_show 1231, t_suelta 1419, t_strike 2375, sev 2) | 17,5 cm (doble columna). Versión vertical de columna (8,5 cm): fig_cebo_frames_col.png. Las posiciones de las flechas se fijaron a ojo sobre el render; la cabecera del render (FASE/paso/a salvo/cazadas) se conserva. |
| `fig_cebo_frames_col.png` | 381 KB | Idem en columna (3 filas), 8,5 cm. | ídem | — |
| `fig_heatmap.png` | 196 KB | (a) P(primera opción | estrato, nº de lobos) del manager lobo final (200 episodios vs Reactive): keep en G 0.89/0.93/1.00 (n=3/4/5), Δ90 en S 1.00 en todos los n. (b) Emergencia en la ligera de RUN-M1'''' (40 semillas): P(CEBO|G,n≥3), P(Δ90|S), P(keep|G) y severidad media. | /data/hrl_m1/eval/manager_M1pppp_final__reactive.json (resumen.P_a_first; conteos por estrato/n desde episodes) y /data/hrl_m1/M1pppp/eval_ligera.jsonl | 17,5 cm. OJO: P(keep|G) en la ligera oscila 0↔1 porque la ligera solo tiene n_G_n3 = 6 episodios de G con n≥3; el valor fiable es el de la eval final (0.931). Opcional. |
| `fig_mundo.png` | 105 KB | Esquema del mundo: parcela 500×500 m, establo r=60 m en el centro, estación r=25 m, rebaño, radios del dron (expulsión 20 / confirmación 40 / detección 100 m), lobos entrando por un lado, huida de las vacas. | constantes: baseline.py CONFIG_V2 (parcel 500×500, dt 0.1, r_detect 100, r_confirm 40, wolf_speed 4, cow_speed 1.2), world.py (DRONE_MAX_SPEED 15, DETER_RADIUS 20, safe_radius 0.12·500=60, station_radius 0.05·500=25, estación a safe_radius+station_radius+gap sobre el establo) | 8,5 cm. Esquemático (posiciones de rebaño y lobos ilustrativas). Opcional. |

### 2.1 Juego en inglés (`/data/paper/figs_en/`; copia en `results/paper/figs_en/`; `figs_en.zip` 1.42 MB, sha256 `279e50d9ad045e86722d64ad5d19e9ea9c70ccfbc045ec527218d681c967614f`)

Mismos 7 archivos, mismos tamaños y datos (`figs_paper.py --lang en`; todas las cadenas visibles en `LABELS['es'|'en']`).
Glosario aplicado: muertes acumuladas → cumulative kills · cruce → crossing · severidad → severity (livestock lost/episode) ·
PENETRADO → line penetrations · señuelo → decoy · asalto → assault · rebaño → herd · barrera → barrier · patrulla → patrol ·
establo → shelter · estación de carga → charging station · detección/confirmación/expulsión → detection/confirmation/expulsion ·
proporcional → proportional · manager → manager · MASA/CEBO → MASS/DECOY · ligera → light eval.
**Cabecera de `fig_cebo_frames`: RE-RENDER, no recorte** — `rerender_seed98.py` repite el episodio de la seed 98 (mixto) con el código
v3.7 EXACTO (worktree pineado `4bf5024`, el mismo del GIF) y el ckpt M1''''; el replay es determinista (hitos 901/1231/1419/2375, sev 2,
mismas decisiones que el timeline) y los 3 fotogramas se renderizan con el renderer del repo SIN modificarlo, traduciendo los objetos
de texto de la figura (cabecera PHASE/step/wolves/prey/episode/safe/killed/outside y leyenda) antes de guardar. Los snapshots usados
son los mismos índices que la figura ES (tick 1230/1419/2373 = frames 410/473/791 del GIF); `figs_en/_frame_*_{es,en}.png` son los
fotogramas re-renderizados en ambos idiomas (el ES sirve de control: idéntico al frame del GIF salvo la cuantización del GIF).
`figs/figs_notas.json` guarda ahora ambos idiomas (claves `es`/`en`, con `cebo_frames.cabecera = original | re-render`).

Script reproducible: `figs_paper.py [--lang es|en]` (solo lee artefactos; `figs_notas.json` guarda los valores calculados para los pies de figura).

## 1. Tabla de verificación (afirmación → artefacto)

### 1. Mundo / constantes

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| Campo | 500×500 m | `parcel_size=(500.0, 500.0)` en CONFIG_V2 (el default de `World` es 300×300, solo para los checks) | repo `baseline.py` línea 102 (`CONFIG_V2`); `world.py` línea 160 (default 300×300); `hrl/manager_env.py` línea 50/133 y `hrl/manager_drone.py` línea 50/351 importan `CONFIG_V2` | OK |
| dt | 0.1 s | `dt=0.1` | `baseline.py` línea 103; `world.py` línea 167 | OK |
| Episodio máximo | ≤ 23.570 ticks | `int(4·√(500²+500²)/1.2/0.1) = 23570` (derivado); máximo observado 23570 | `world.py` líneas 370-373 (fórmula); `baseline.py` línea 83 (comentario "=23570"); `/data/hrl_e0/e01/results.json` → max(`episodes[].steps`) = 23570; `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` → max Σ`log[].ticks` = 23570 | OK |
| Velocidad dron | 15 m/s | `DRONE_MAX_SPEED = 15.0` | `world.py` línea 48 | OK |
| Velocidad lobo | 4 m/s | `wolf_speed=4.0` | `baseline.py` línea 112; `world.py` línea 193 | OK |
| Velocidad vaca | 1.2 m/s | `cow_speed=1.2` (jitter ±0.4; ternero `calf_speed=0.8`) | `baseline.py` líneas 109, 117; `world.py` líneas 171, 187 | OK |
| Quórum adulta | 2 lobos | `n_min_adult=2`; regla "Adultas cazables: >= n_min_adult flanqueadores a la vez" | `baseline.py` línea 113; `world.py` líneas 204, 1677, 1690 | OK |
| Quórum ternero | 1 flanqueador | "Terneros cazables: >= 1 flanqueador del cono de su DEFENSORA"; `quorum_n = 1 if pack_prey_kind == "calf"` | `world.py` líneas 1655-1656, 1815 | OK |
| r_detect | 100 m | `r_detect=100.0` | `baseline.py` línea 125; `world.py` línea 213 | OK |
| r_confirm | 40 m | `r_confirm=40.0` | `baseline.py` línea 125; `world.py` línea 214 | OK |
| DETER_RADIUS | 20 m | `DETER_RADIUS = 20.0` | `world.py` línea 79 | OK |
| Techo de opción K_MAX | 4.500 ticks | `K_MAX = 4500` (lobo); D2 importa el mismo `K_MAX` | `hrl/manager_env.py` línea 64; `hrl/manager_drone.py` líneas 25, 53, 147 | OK |
| Coste de deliberación ε (lobo) | 0.05 | `DELIB_COST = 0.05` | `hrl/manager_env.py` línea 70 | OK |
| Coste de deliberación ε (dron) | 0.05 | `DELIB_COST_D2 = 0.05` | `hrl/manager_drone.py` línea 68 | OK |
| Margen de no-inferioridad δ | 0.15 | "δ = 0.15" en los cuatro pre-registros | `/data/hrl_m1/PREREGISTRO.md` línea 27; `/data/hrl_m1/m1pp/PREREGISTRO_v2.md` líneas 46, 58; `/data/hrl_m1/m1pppp/PREREGISTRO_v3.md` líneas 59, 74; `/data/hrl_d2/PREREGISTRO_D2.md` líneas 51, 69 | OK |

### 2. Plano (RL no jerárquico)

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| run01 lobos: nº de muertes | 1 muerte | `train.log`: `ep_rew_mean= 0.010` en DOS ventanas no contiguas (pasos 1.081.344–1.155.072 y 1.695.744–1.769.472; el resto 0.000); la línea final del log (escrita a mano) dice "una única muerte espontánea aislada a ~1.08M" | `/data/wolves/run01/train.log` líneas 52-55, 79-83, 119 | DUDA — el log es compatible con 2 muertes (ver §C); la cifra "1" solo está en texto (línea 119 del log y DISEÑO.md línea 1067) |
| run01 lobos: nº de episodios | ~2.400 episodios | No hay contador de episodios en el artefacto. Estimación desde `train.log` (Σ Δpasos/ep_len_mean hasta 2,56 M pasos) ≈ 2.270 episodios; abortado a 2,48 M pasos | `/data/wolves/run01/train.log` (104 líneas `pasos=…ep_len_mean=…`); secundario: DISEÑO.md línea 1067-1068 ("~2.400 episodios") | NO ENCONTRADO (primario); solo secundario (DISEÑO.md). Sugerencia: "~2.300-2.400 episodios" o citar "2,48 M pasos" |
| Mejores planos: run02 final | 0.57 (lobos) | solo-lobos 0.57±0.72 / mixto 0.60±0.75 | `/data/wolves/run02/eval_final_10M.txt` líneas 5-6; `eval_final_10M.json` `by_kind.*.severity_mean` | OK |
| Mejores planos: run02 best 5.5M | (incluido en 0.57–0.72) | 0.57 / 0.56 | `/data/wolves/run02/eval_best_5.5M.txt` líneas 5-6 | OK (el mínimo real del rango es 0.56 en mixto best) |
| Mejores planos: run03 final | 0.72 (mixto) | 0.65 / 0.72 | `/data/wolves/run03/eval_final_10M.txt` líneas 5-6 | OK |
| Mejores planos: run03 best 4M | (incluido) | 0.66 / 0.71 | `/data/wolves/run03/eval_best_4M.txt` líneas 5-6 | OK |
| Suelo con que se compararon run02/run03 (v2.4.1) | "suelo 2.68" | scriptado **2.77 (lobos) / 2.80 (mixto)** en el arnés v2.4.1; suelo residual δ≡0 = 2.78 / 2.81 | columna "scriptados" de `/data/wolves/run02/eval_final_10M.txt`, `run03/eval_final_10M.txt`; `/data/wolves/run04_floor.txt` líneas 5-6; `run04_floor.json` | CORREGIR → 2.77/2.80 (v2.4.1). El 2.68 NO es de esa versión del mundo |
| Valor 2.68 (Reactive v3.4) | 2.68 | `scripted_reference.lobos = 2.68`, `by_kind.lobos.severity_mean = 2.68` (mixto 2.77) | `/data/wolves/run08_dieta50/eval_floor_v34.json` claves `scripted_reference`, `by_kind.lobos.severity_mean` | OK como cifra, pero **el paper mezcla versiones**: 0.57–0.72 son v2.4.1 (julio, campo y arnés distintos) y 2.68 es v3.4 (agosto). run02/run03 nunca se evaluaron en v3.4 |
| Erosión KNC run08 | 26.6 % → 13 % | `frac_killer_no_confirmado`: suelo 0.266 → best 2.5M 0.21 → final 10M 0.13 | `/data/wolves/run08_dieta50/cebo_floor_v34.json`, `cebo_best_2p5M.json`, `cebo_final_10M.json` clave `resumen.frac_killer_no_confirmado` | OK |
| Drones run02_v34: reparto | 5.7 % → 5.3 % | `frac_ambos_frentes_atendidos`: suelo 0.057 → final 20M 0.053 (best 18M 0.033) | `/data/drones/run02_v34/comportamiento_suelo.json` y `comportamiento_final20M.json` clave `resumen.frac_ambos_frentes_atendidos` | OK |
| run09 en v3.7 solo-lobos | 0.77 | `by_kind.lobos.severity_mean = 0.77` (mixto 0.62) | `/data/hrl_m1/m1pppp/metro/run09_en_v37_estatica.json`; log `renivelado_logs/metro_run09e.log` | OK |
| Reactive en v3.7 solo-lobos | 0.93 | `by_kind.lobos.severity_mean = 0.93` (mixto 0.69) | `/data/hrl_m1/m1pppp/metro/reactive_estatica_v37.json`; log `renivelado_logs/metro_reactive.log` | OK |

### 3. Valle (cruce de muertes acumuladas CEBO_keep vs MASA, estrato G, vs Reactive)

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| Cruce v3.5 | ≈ 2.250 ticks | curva `valle.cebo` < `valle.masa` hasta t=2000 (1.472 vs 1.496) y ≥ en t=2250 (1.595 vs 1.528); rejilla de 250 ticks | `/data/hrl_e0/v35/e01/results.json` → `resumen.G_keep_h50_reactive.valle.{cebo,masa}` y `.grid`; secundario `/data/hrl_e0/v35/STOP2prima_INFORME.md` línea 48 | OK (primer punto de rejilla con CEBO ≥ MASA) |
| Cruce v3.4 | ≈ 4.750 ticks | CEBO < MASA hasta t=4500 (2.974 vs 2.988) y ≥ en t=4750 (3.000 vs 2.988) | `/data/hrl_e0/e01/results.json` → `resumen.G_keep_h50_reactive.valle.{cebo,masa}`, `.grid`; secundario `/data/hrl_e0/STOP2_INFORME.md` línea 23 | OK |
| (contexto) Δ(CEBO_keep−MASA \| G) v3.4 / v3.5 | — | +0.434 [+0.251, +0.621] n=346 / +0.851 [+0.603, +1.093] n=375 | mismos JSON, clave `resumen.G_keep_h50_reactive.delta.todos` | (no pedido; informativo) |

### 4. Celdas S v3.7

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| MASA | 0.30 | `[0.3, 0.13, 0.51]` | `/data/hrl_m1/m1pppp/celdas_s_v37.json` → `celdas.MASA.sev` | OK |
| Δ90 | 1.71 [1.29, 2.14] | `[1.71, 1.29, 2.14]` | ídem → `celdas.D90.sev` | OK |
| Δ180 | 1.42 | `[1.42, 1.02, 1.84]` | ídem → `celdas.D180.sev` | OK |

### 5. Escalera del bando lobo (v3.7, 100 semillas × {lobos, mixto} = 200 pares)

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| B_masa vs Reactive | 0.57 | `sev = [0.56, 0.395, 0.735]` (vs run02 0.605; vs run09 0.515) | `/data/hrl_m1/eval/masa_v37__reactive.json` → `resumen.sev`; `TABLA_M1PPPP.md` fila B_masa "0.56"; `PREREGISTRO_v3.md` línea 29 "0.56" | CORREGIR → 0.56 (0.57 es B_masa de **v3.6**, `TABLA_M1PP.md` fila masa_v36) |
| B_spawn vs Reactive | 0.95 | `sev = [0.95, 0.705, 1.215]` (run02 0.90; run09 0.88) | `/data/hrl_m1/eval/spawn_v37__reactive.json` → `resumen.sev` | OK |
| B_oracle vs Reactive | 1.66 [1.36, 1.97] | `sev = [1.66, 1.355, 1.97]` (run02 1.64; run09 1.69) | `/data/hrl_m1/eval/oracle_v37__reactive.json` → `resumen.sev` | OK (IC bajo crudo 1.355) |
| Manager M1'''' vs Reactive | 1.76 | `sev = [1.765, 1.445, 2.09]` | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` → `resumen.sev`; `renivelado_logs/mgr_final_reactive.log`; `TABLA_M1PPPP.md` "1.76" | OK (crudo 1.765) |
| Δ(M1'''' − oráculo) | +0.10 [+0.03, +0.19] | "0.10 [0.03, 0.19]"; recalculado desde episodios: 0.105 [0.025, 0.19] | `/data/hrl_m1/m1pppp/TABLA_M1PPPP.md` fila "manager final" y línea "Δ(manager − B_oracle) vs reactive"; primario = `episodes[].sev` de `manager_M1pppp_final__reactive.json` vs `oracle_v37__reactive.json` | OK |
| Réplica M1pppp_r1 vs Reactive | 1.69 [1.38, 2.01] | `sev = [1.69, 1.375, 2.01]` | `/data/hrl_m1/eval/manager_M1pppp_r1_final__reactive.json` → `resumen.sev`; `STOP_REPLICA_INFORME.md` línea 13 | OK (IC bajo crudo 1.375) |
| Δ(réplica − oráculo) | +0.03 [−0.12, +0.18] | "+0.03 [−0.12, +0.175]" (línea 13) y "+0.03 [−0.12, +0.18]" (líneas 32, 48); recalculado 0.03 [−0.115, +0.17] | `/data/hrl_m1/m1pppp/STOP_REPLICA_INFORME.md` líneas 13, 32, 48; primario `episodes[].sev` de `manager_M1pppp_r1_final__reactive.json` vs `oracle_v37__reactive.json` | OK |
| Transferencia vs run02 | 1.75 | `sev = [1.755, 1.449875, 2.07]` | `/data/hrl_m1/eval/manager_M1pppp_final__run02.json` → `resumen.sev` | OK (crudo 1.755) |
| Transferencia vs run09 | 1.76 | `sev = [1.76, 1.45, 2.08]` | `/data/hrl_m1/eval/manager_M1pppp_final__run09.json` → `resumen.sev` | OK |
| Decisiones por episodio | 3.2 | `decisiones_media = 3.465` (vs run02 3.5; vs run09 3.43; 60k 3.4) | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` → `resumen.decisiones_media`; TABLA_MAESTRA §4.2 "dec/ep 3.5" | CORREGIR → 3.5 (crudo 3.465) |
| Jugada completa | 1.00 | `censura.jugada_completa_frac = 1.0` (n_eps_cebo_n3 = 134) | ídem → `resumen.censura.jugada_completa_frac` | OK |
| ABORTs / episodio | 0.28 | `aborts_por_ep = 0.28` (`eventos.ABORT_BAIT_FAILED = 56` / 200) | ídem → `resumen.aborts_por_ep`, `resumen.eventos` | OK |
| Coste de deliberación pagado | ≈ 0 | Σ`episodes[].delib_pagado`/200 = **0.000** (réplica 0.001; M2 0.006) | ídem → `episodes[].delib_pagado` (no hay clave `delib_por_ep` en `resumen`; calculado) | OK |
| P(Δ90 \| S) = 1.000 — M1'''' | 1.000 | `P_a_first.S.CEBO_d90 = 1.0` | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` → `resumen.P_a_first.S` | OK |
| P(Δ90 \| S) = 1.000 — M2 | 1.000 | `P_a_first.S.CEBO_d90 = 1.0`; ligera final `eval_final.P_a_S_first.CEBO_d90 = 1.0` | `/data/hrl_m1/eval/manager_M2_final__reactive.json` → `resumen.P_a_first.S`; `/data/hrl_m1/M2/summary.json` | OK |
| P(Δ90 \| S) = 1.000 — M1pppp_r1 | 1.000 | `P_a_first.S.CEBO_d90 = 1.0`; ligera `eval_final.P_a_S_first.CEBO_d90 = 1.0` | `/data/hrl_m1/eval/manager_M1pppp_r1_final__reactive.json` → `resumen.P_a_first.S`; `/data/hrl_m1/M1pppp_r1/summary.json` | OK (3/3) |
| M2 ×3.3 de cómputo | ×3.3 | segundos 20622.4 / 6347.1 = **3.249**; fps 19.36 / 5.96 = 3.248 | `/data/hrl_m1/M1pppp/summary.json` (`segundos`, `fps`) vs `/data/hrl_m1/M2/summary.json`; secundario `STOP_M2_INFORME.md` líneas 13, 71 "×3.3" | OK con reserva: crudo ×3.25 (→ "×3.2" con redondeo estricto; el informe usa 19.4/5.96 ≈ 3.3). Sugerencia: "≈ ×3.2–3.3" o "×3.25" |
| (contexto) Δ(M2 − M1'''') | — | −0.145 [−0.26, −0.04] (recalculado) | `manager_M2_final__reactive.json` vs `manager_M1pppp_final__reactive.json` `episodes[].sev` | (informativo) |

### 6. D2 (v3.7.1; celdas natural / cebo-2f / manager lobo; n = 100 / 100 / 200)

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| Reactive | 0.74 / 2.61 / 1.76 | `sev` = 0.74 / 2.61 / **1.765** | `/data/hrl_d2/e04_reactive__{natural,cebo2f,manager}.json` clave `sev` | OK (crudo 1.765) |
| Proporcional | 0.25 / 0.85 / 0.61 | 0.25 / 0.85 / 0.61 | `/data/hrl_d2/e04_proporcional__*.json` clave `sev` | OK |
| RUN-D2 (seed 0) | 0.21 / 1.03 / 0.67 | 0.21 / 1.03 / 0.67 | `/data/hrl_d2/e04_dronemgr__*.json` clave `sev`; `TABLA_D2.md` | OK |
| Réplica D2_r1 (seed 1) | 0.21 / 1.06 / 0.76 | 0.21 / 1.06 / **0.755** | `/data/hrl_d2/e04_dronemgr_r1__*.json` clave `sev`; `TABLA_D2_R1.md` | OK (crudo 0.755) |
| Δ conjunto (2 aprendices, 200 pares) vs proporcional — natural | −0.04 [−0.10, +0.01] | "−0.04 [−0.10, +0.01]"; recalculado −0.04 [−0.10, +0.015] | `/data/hrl_d2/TABLA_D2_R1.md` línea "Δ(AMBOS aprendices − proporcional) vs natural"; primario `episodes[].sev` de `e04_dronemgr__natural.json`, `e04_dronemgr_r1__natural.json`, `e04_proporcional__natural.json` | OK |
| Δ conjunto vs proporcional — cebo-2f | +0.20 [+0.07, +0.33] | "+0.20 [+0.07, +0.33]"; recalculado 0.195 [0.07, 0.33] | ídem, línea "… vs cebo2f" | OK |
| Δ conjunto vs proporcional — manager | +0.10 [+0.02, +0.19] | "+0.10 [+0.02, +0.19]"; recalculado 0.102 [0.022, 0.188] | ídem, línea "… vs manager" | OK |
| Δ vs Reactive −0.53 / −1.55 / −1.01 | −0.53 / −1.55 / −1.01 | Son los de la **RÉPLICA (seed 1)**: "Δ(réplica − reactive)" natural −0.53 [−0.86, −0.22], cebo2f −1.55 [−1.98, −1.13], manager −1.01 [−1.26, −0.77]. RUN-D2 (seed 0): −0.53 [−0.85, −0.25] / −1.58 [−2.03, −1.14] / −1.09 [−1.35, −0.85]. Conjunto: −0.53 [−0.76, −0.32] / −1.56 [−1.88, −1.26] / −1.05 [−1.23, −0.88] | `/data/hrl_d2/TABLA_D2_R1.md` (tres bloques Δ vs reactive); `TABLA_D2.md` (RUN-D2) | OK si el paper los atribuye a la réplica; si los presenta como RUN-D2 o conjunto → CORREGIR (ver valores) |
| P(guardia \| 2º clúster) RUN-D2 | 1.000 | `eval_final.P_guardia_2clusters = 1.0` | `/data/hrl_d2/D2/summary.json` | OK |
| P(guardia \| 2º clúster) réplica | 0.943 | `eval_final.P_guardia_2clusters = 0.943` | `/data/hrl_d2/D2_r1/summary.json` | OK |
| 2-2 ante 2º clúster | entre 0.925 y 1.000 | `P_a_2clusters.2-2` = 1.0 (D2) / 0.925 (D2_r1) | `/data/hrl_d2/D2/summary.json`, `D2_r1/summary.json` → `eval_final.P_a_2clusters` | OK |
| 3-1 ante 2º clúster | 0.019 | `P_a_2clusters.3-1` = 0.0 (D2) / 0.019 (D2_r1); (4-0 = 0.057 en la réplica) | ídem | OK (0.019 es de la réplica; RUN-D2 = 0) |
| KNC | 0 | `knc_frac = 0.0` en natural y cebo2f (D2 y D2_r1); `None` en la celda manager (no aplica) | `/data/hrl_d2/e04_dronemgr__*.json`, `e04_dronemgr_r1__*.json` clave `knc_frac` | OK (matizar: no definido en la celda manager) |
| Carrera: gana_guardia | 78–89 % | mín **0.776** (dronemgr_r1 vs manager) · máx **0.885** (dronemgr vs natural). Todos: proporcional 0.783/0.798/0.822; dronemgr 0.885/0.868/0.84; dronemgr_r1 0.815/0.857/0.776 | `/data/hrl_d2/e04_{proporcional,dronemgr,dronemgr_r1}__*.json` → `carrera.gana_guardia_frac` | OK (77.6 %–88.5 %, redondeado 78–89 %) |
| STALLs RUN-D2 | 189 / 400 | Σ`stalls_def` = 153 (natural, 32 eps) + 20 (cebo2f, 17 eps) + 16 (manager, 11 eps) = **189**; episodios 100 + 100 + 200 = **400** | `/data/hrl_d2/e04_dronemgr__*.json` → `episodes[].stalls_def`, `n` | OK (nota: STOP_D2_INFORME y DISEÑO decían "300"; fe de erratas TABLA_MAESTRA §7.1) |
| STALLs réplica | 147 | Σ`stalls_def` = 112 (33 eps) + 22 (21 eps) + 13 (13 eps) = **147** sobre 400 episodios | `/data/hrl_d2/e04_dronemgr_r1__*.json` → `episodes[].stalls_def` | OK |

### 7. Gaming / higiene

| afirmación | valor en el paper | valor en el artefacto | ruta del artefacto (+clave/línea) | VEREDICTO |
|---|---|---|---|---|
| Exploit de re-fijación de presas (M1) | +0.42 | "+0.42 [+0.23, +0.63]" vs B_oracle; recalculado desde episodios 0.425 [0.235, 0.635]; M1 1.31 [1.02, 1.62] vs oráculo v3.5 0.885 [0.645, 1.14]; mecanismo: "cada re-decisión CEBO re-arranca la opción y RE-FIJA la presa del asalto a la res MÁS LIBRE" | `/data/hrl_m1/STOP_M1_INFORME.md` líneas 23, 32, 59-63; primario `/data/hrl_m1/eval/manager_M1_final__reactive.json` (`resumen.sev = [1.31,1.02,1.62]`, `decisiones_media = 101.27`) vs `oracle__reactive.json` (`resumen.sev = [0.885,0.645,1.14]`) | OK |
| Molinillo M1'' | 45 ABORTs/ep | `eventos.ABORT_BAIT_FAILED = 9036` / 200 eps = **45.18**/ep; dec/ep 49.095 | `/data/hrl_m1/eval/manager_M1pp_final__reactive.json` → `resumen.eventos`, `resumen.decisiones_media`; `/data/hrl_m1/m1pp/STOP_M1PP_INFORME.md` línea 56 | OK |
| Tras la corrección (M1'''') | 0.28 ABORTs/ep | `aborts_por_ep = 0.28` | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json`; `TABLA_M1PPPP.md` | OK |
| Interbloqueo 9/20 con gate ±25° | 9/20 | `arms`: 20 episodios `oracle`, 9 con `staged_noshow_max ≥ 400` (`arms_resumen.episodios_stall_400 = 9`, máx 23570); gate `ASSAULT_BEARING_TOL_DEG = 25.0` | `/data/hrl_m1/m1pppp/verif/verif0.json` → `arms[]`, `arms_resumen`; `VERIF0_INFORME.md` líneas 31, 37; repo `hrl/options_wolf.py` línea 96 | OK |
| Seed 21 (lobos): M1 | sev 7 | `episodes[seed=21,kind=lobos].sev = 7` (n_wolves 4, S) | `/data/hrl_m1/eval/manager_M1_final__reactive.json`; `/data/hrl_m1/M1/visionado/INDEX.md` línea 11 | OK |
| Seed 21 (lobos): M1'' | sev 6 | `.sev = 6` | `/data/hrl_m1/eval/manager_M1pp_final__reactive.json`; `/data/hrl_m1/m1pp/visionado/INDEX.md` línea 3 | OK |
| Seed 21 (lobos): M1'''' | sev 0 | `.sev = 0` (réplica r1 también 0; oráculo v3.7 0) | `/data/hrl_m1/eval/manager_M1pppp_final__reactive.json`; `/data/hrl_m1/m1pppp/visionado/INDEX.md` línea 11 | OK |

## 3. Referencias bibliográficas (volcado literal de los docs; NO se ha añadido nada)

### B.1 DISEÑO.md, sección "## 12. Referencias" (repo, líneas 2348-2377) — transcripción literal

| # | autores | año | título | venue / URL | qué se cita (tal como está escrito) |
|---|---|---|---|---|---|
| 1 | Muro, C., Escobedo, R., Spector, L., Coppinger, R.P. | 2011 | Wolf-pack (Canis lupus) hunting strategies emerge from simple rules in computational simulations | *Behavioural Processes*, 88(3), 192–197 | n/d (en §12 sin nota; en DISEÑO.md línea 1527 "Reutiliza el lobo de Muro et al. (2011)") |
| 2 | Janeiro-Otero, A., et al. | 2020 | Grey wolf (Canis lupus) predation on livestock in relation to prey availability | n/d | (Selección de presa / depredación de ganado.) |
| 3 | Madden, J.D., Arkin, R.C., MacNulty, D.R. | 2011 | Multi-robot system based on model of wolf hunting behavior | n/d | (Robótica inspirada en Muro.) |
| 4 | ICWDM (Internet Center for Wildlife Damage Management) | n/d | "Wolf Damage Identification" | n/d | El ataque se concentra en grupa, flancos y cuartos traseros; preferencia por terneros frente a adultas. (Fundamenta el ataque por flanco y el ternero como objetivo blando preferente — §4.1/§4.2.) |
| 5 | BeefResearch.ca | n/d | "Cows & Wolves" (estudio con collares GPS en Alberta) | n/d | composición de presas de lobo ~40% terneros / 40% añojos / <20% adultas. (Fundamenta la presencia de terneros y su peso como presa preferente.) |
| 6 | Wolf Song of Alaska | n/d | caza en manada de presa grande | n/d | la manada caza en grupo y rara vez toda toca a la presa a la vez. (Fundamenta la regla de número mínimo `n_min_adult` para tumbar a una adulta — basta un subconjunto flanqueando, no toda la manada.) |
| 7 | Ng, A., Harada, D., Russell, S. | 1999 | Policy invariance under reward transformations: theory and application to reward shaping | n/d | (Shaping basado en potencial.) |
| 8 | Yu, C., et al. | 2022 | The surprising effectiveness of PPO in cooperative multi-agent games (MAPPO) | n/d | n/d |
| 9 | Terry, J., et al. | 2021 | PettingZoo: Gym for multi-agent reinforcement learning | n/d | n/d |
| 10 | Bettini, M., Prorok, A., Moens, V. | 2024 | BenchMARL: Benchmarking Multi-Agent Reinforcement Learning (TorchRL) | n/d | n/d |
| 11 | YOLO26 (Ultralytics) | enero 2026 | n/d | n/d | detección en tiempo real, end-to-end / sin NMS, orientada a drones y robótica, con asignación consciente de objetos pequeños (STAL). |
| 12 | Halter (Nueva Zelanda) | n/d | n/d | n/d | collares GPS de *virtual fencing* / *guided herding*. |
| 13 | Strömbom, D., et al. | 2014 | n/d | n/d | (Modelo matemático de *shepherding*, por si se necesita en la escolta.) |

### B.2 Repo `BIBLIOGRAFIA.md` (154 líneas; "consolidadas desde DISEÑO.md §12") — transcripción literal de cada entrada

Nota: este archivo está en el repo, no en `/data`. En `/data/**/*.md` NO hay ninguna otra lista de referencias (grep de "arxiv|referencias|bibliograf": 0 resultados).

**## Fase RL (lobos y, después, drones)**

| # | autores | año | título | venue / URL | "Se usa para" (literal) |
|---|---|---|---|---|---|
| R1 | Silver, T., Allen, K. R., Tenenbaum, J. B., & Kaelbling, L. P. | 2018 | Residual Policy Learning | arXiv:1812.06298 | la arquitectura de run04: el scriptado (política a mano, no diferenciable) vive dentro del controlador y la red aprende solo una corrección aditiva δ con RL sin modelo; explica por qué el RL desde cero fracasa en horizonte largo / recompensa rala (runs 01–03) y por qué el residuo MEJORA controladores a mano en vez de reaprenderlos. |
| R2 | n/d *(verificar autores al citar en la memoria)* | 2021 | Grasp and Motion Planning for Dexterous Manipulation for the Real Robot Challenge | arXiv:2101.02842 | el entrenamiento en dos fases de run04: fase 1 solo-crítico (política congelada mientras el value function aprende cuánto vale el controlador base) e inicialización a cero de la última capa de la media (δ inicial ≡ 0) con σ inicial pequeña. |
| R3 | Uchendu, I., et al. | 2023 | Jump-Start Reinforcement Learning | ICML 2023 (PMLR v202); arXiv:2204.02372 | alternativa CONSIDERADA Y DESCARTADA para el arranque desde el scriptado (guía por roll-in del experto en vez de residuo aditivo); se descartó porque el residual conserva el suelo del script en TODO momento (guardia del suelo medible). |
| R4 | n/d | 2025 | Residual Policy Gradient: A Reward View of KL-regularized Objective | arXiv:2503.11019 | conexión teórica del residual con la regularización KL (enlace con el temario de RL del autor); lectura de por qué corregir una política base equivale a un objetivo regularizado hacia ella. |
| R5 | Ng, A. Y., Harada, D., & Russell, S. | 1999 | Policy invariance under reward transformations: theory and application to reward shaping | ICML | el shaping por potencial de run02/run03 (r_shape = γ·Φ(s′) − Φ(s) con el γ EXACTO del agente no cambia la política óptima; verificado en rl_env_check test 8). |
| R6 | Schulman, J., et al. | 2017 | Proximal Policy Optimization Algorithms | arXiv:1707.06347 | el algoritmo de TODOS los runs de lobos (y previsiblemente del MARL). |
| R7a | Wei, E., & Luke, S. | 2016 | Lenient Learning in Independent-Learner Stochastic Cooperative Games | JMLR | (conjunto R7) el DIAGNÓSTICO del "valle del cebo" = relative overgeneralization: la política óptima (cebo coordinado de 2 frentes) da MALA recompensa si un solo lobo la intenta, así que PPO se queda en el óptimo local "atacar juntos"; es la razón de que el cebo no emergiera en 5 campañas. *(autores/venue exactos: verificar al citar; ver también arXiv:2411.11099, Mitigating Relative Over-Generalization in MARL.)* |
| R7b | Panait, L., Tuyls, K., & Luke, S. | 2008 | Theoretical Advantages of Lenient Learners | n/d | ídem R7 |
| R7c | Guo, J., et al. | 2024 | Joint Intrinsic Motivation (JIM) for Coordinated Exploration in Multi-Agent Deep RL | arXiv:2402.03972 | ídem R7 ("que AJUSTA y mide la patología en un entorno sintético") |
| R7d | n/d | n/d | Mitigating Relative Over-Generalization in MARL | arXiv:2411.11099 | "ver también" en R7 |
| R8a | Bengio, Y., Louradour, J., Collobert, R., & Weston, J. | 2009 | Curriculum Learning | ICML | el CURRÍCULO de separación de spawn (v2.7): se arranca al lobo AL OTRO LADO del valle (cebo casi servido por el spawn: 2 frentes opuestos, ~180°, ambos letales) y se endurece por niveles hasta el spawn normal, para que la política CRUCE el valle de recompensa en vez de quedarse en el óptimo local. Currículo FIJO por pasos (legible/diagnosticable) frente a automático. |
| R8b | Narvekar, S., et al. *(autores completos verificar al citar)* | 2020 | Curriculum Learning for Reinforcement Learning Domains: A Framework and Survey | JMLR | ídem R8 |
| R9a | Zheng, L., et al. | 2021 | EMC: Episodic Multi-agent RL with Curiosity-Driven Exploration | arXiv:2111.11032 (NeurIPS) | Vías de RESERVA de EXPLORACIÓN INTRÍNSECA COORDINADA (CONSIDERADAS, NO implementadas — si el currículo NO cruza el valle): dar CURIOSIDAD COORDINADA a los lobos (recompensa intrínseca por novedad CONJUNTA) para muestrear la desviación coordinada que la exploración gaussiana por-paso no encuentra; sería la vía siguiente si el currículo demuestra que "el cebo se aprende con ayuda pero no se forma solo". La otra reserva = control JERÁRQUICO de formación (elegir el reparto de frentes como acción de alto nivel). *(autores/venue exactos: verificar al citar en la memoria.)* |
| R9b | Iqbal, S., & Sha, F. | 2019 | Coordinated Exploration via Intrinsic Rewards for Multi-Agent RL | n/d *(arXiv id verificar al citar)* | ídem R9 |
| R9c | MACE — Xu, H., et al. | 2024 | Settling Decentralized Multi-Agent Coordinated Exploration by Novelty Sharing | arXiv:2402.02097 (AAAI) | ídem R9 |
| R9d | SMMAE — Zhang, S., et al. | 2023 | Self-Motivated Multi-Agent Exploration | arXiv:2301.02083 (AAMAS) | ídem R9 |
| R10 | Raffin, A., et al. | 2021 | Stable-Baselines3: Reliable Reinforcement Learning Implementations | JMLR 22(268) | la implementación de PPO (política, buffer, VecEnv) usada en rl/. |
| R11 | Towers, M., et al. | 2024 | Gymnasium | arXiv:2407.17032 | el envoltorio single-agent del env de lobos (`WolfPackEnv`) y el env conjunto de drones (`DroneTeamEnv`). |
| R12 | Sheikh, H. U., & Bölöni, L. | 2020 | Multi-Agent Reinforcement Learning for Problems with Combined Individual and Team Reward | arXiv:2003.10598 (DE-MADDPG) | la RECOMPENSA del MARL de drones: componente GLOBAL de equipo (−1/res muerta, compartida) + componente LOCAL por dron (disuasión atribuida), el marco "individual + team reward" demostrado precisamente en un problema de ESCOLTA DEFENSIVA. Nosotros lo SIMPLIFICAMOS: un solo crítico centralizado MAPPO y la componente local sumada a la recompensa del stream (sin el doble crítico global/local de DE-MADDPG — descartado por sobre-ingeniería con 4 agentes; las componentes se registran POR SEPARADO en el log, vigilancia anti-proxy). |
| R13 | Sheikh, H. U., & Bölöni, L. | 2020 | Designing a Multi-Objective Reward Function for Creating Teams of Robotic Bodyguards Using Deep Reinforcement Learning / Defensive Escort Teams via Multi-Agent Deep RL *(título exacto: verificar al citar en la memoria)* | arXiv:1910.04537 | precedente DIRECTO del problema (equipo que aprende la FORMACIÓN alrededor de un bien a proteger frente a amenazas móviles) — el análogo publicado de nuestra barrera aprendida. |
| R14 | Foerster, J., Farquhar, G., Afouras, T., Nardelli, N., & Whiteson, S. | 2018 | Counterfactual Multi-Agent Policy Gradients (COMA) | AAAI 2018; arXiv:1705.08926 | referencia de CREDIT ASSIGNMENT contrafactual — CONSIDERADA Y DESCARTADA por sobre-ingeniería: con 4 puestos y la componente local de disuasión ya hay señal por-agente; la ablación con/sin componente local es el sustituto barato del contrafactual. |
| R15 | Wolpert, D. H., & Tumer, K. | 2002 *(año/venue: verificar al citar)* | Optimal Payoff Functions for Members of Collectives (difference rewards) | n/d | la idea madre del crédito por diferencia ("¿qué cambia si este agente no actúa?"); mismo veredicto que COMA: descartada, la registra la bibliografía como contexto del diseño de recompensa. |
| R16a | Sunehag, P., et al. | 2018 | Value-Decomposition Networks (VDN) | arXiv:1706.05296 | familia de DESCOMPOSICIÓN DE VALOR del CTDE — descartadas (son para Q-learning discreto; nuestro CTDE va por crítico centralizado de política, MAPPO — ver Yu et al. 2022 abajo, ya consolidado). |
| R16b | Rashid, T., et al. | 2018 | QMIX | arXiv:1803.11485 | ídem R16 |

**## Fase de mundo (consolidadas desde DISEÑO.md §12; URLs pendientes de verificación)**

| # | autores | año | título | venue / URL | "Se usa para" (literal) |
|---|---|---|---|---|---|
| W1 | Muro, C., Escobedo, R., Spector, L., Coppinger, R.P. | 2011 | Wolf-pack (Canis lupus) hunting strategies emerge from simple rules in computational simulations | Behavioural Processes, 88(3), 192–197 | el modelo de caza del paquete (reglas simples: acercarse + mantener distancia + flanquear) que inspira el scriptado. |
| W2 | Janeiro-Otero, A., et al. | 2020 | Grey wolf (Canis lupus) predation on livestock in relation to prey availability | n/d | selección de presa / depredación de ganado. |
| W3 | Madden, J.D., Arkin, R.C., MacNulty, D.R. | 2011 | Multi-robot system based on model of wolf hunting behavior | n/d | precedente de robótica inspirada en Muro. |
| W4 | ICWDM (Internet Center for Wildlife Damage Management) | n/d | "Wolf Damage Identification" | n/d | el ataque se concentra en grupa/flancos/cuartos traseros y hay preferencia por terneros → fundamenta el ataque por flanco y el ternero como objetivo blando (selección de crías). |
| W5 | BeefResearch.ca | n/d | "Cows & Wolves" (collares GPS en Alberta) | n/d | composición de presas (~40% terneros / 40% añojos / <20% adultas) → presencia y peso de los terneros. |
| W6 | Wolf Song of Alaska | n/d | (caza en manada de presa grande) | n/d | rara vez toda la manada toca a la presa → la regla de quórum `n_min_adult` (basta un subconjunto flanqueando). |
| W7 | n/d | n/d | Criterio DRI de Johnson (Detect/Recognize/Identify, resolución angular) | n/d | `r_detect`=100 m (~8–13 px sobre un lobo de ~1,2 m: reconocer que hay algo) y `r_confirm`=40 m (~130 px: identificar la especie) de la fase detectar→confirmar. |
| W8 | n/d *(Cita formal pendiente — en DISEÑO está como razonamiento de diseño, sin fuente puntual.)* | n/d | Hazing de depredadores y HABITUACIÓN a disuasores estáticos | n/d | el SUSTO POR MOVIMIENTO de v2.4 (base conceptual del susto v2.3→v2.4: lo que disuade es el disuasor ACTIVO que se echa encima; los depredadores se habitúan a postes/luces fijas). |
| W9 | n/d *(Cifras FID de la literatura de comportamiento; cita puntual PENDIENTE de verificar al pasar a la memoria)* | n/d | Distancia de inicio de fuga (FID, Flight Initiation Distance) en cánidos ante amenazas que se aproximan (huida a ~100 m, rango ~17–310 m) | n/d | el SUSTO DE DOS RADIOS de v2.7: expulsión por movimiento (radio grande, la huida de v2.4) + PARED BLANDA estática (radio pequeño `STATIC_DETER_RADIUS`, mínimo que no se cruza ni con el dron quieto; escalado al campo 300×300 — un radio real de ~100 m haría a los drones invencibles). Reconcilia habituación (poste a distancia = ignorable) con obstáculo (poste encima = no se cruza). |
| W10 | n/d *(Referencia/URL pendiente de recuperar — no consta en DISEÑO.md.)* | n/d | Vídeo de ataque real de lobos a ganado | n/d | verosimilitud del comportamiento del paquete. |
| W11 | Yu, C., et al. | 2022 | The surprising effectiveness of PPO in cooperative multi-agent games (MAPPO) | n/d | candidato de algoritmo para la fase MARL de drones. |
| W12 | Terry, J., et al. | 2021 | PettingZoo: Gym for multi-agent reinforcement learning | n/d | API multi-agente prevista para la fase de drones. |
| W13 | Bettini, M., Prorok, A., Moens, V. | 2024 | BenchMARL: Benchmarking Multi-Agent Reinforcement Learning (TorchRL) | n/d | referencia de benchmarking MARL. |
| W14 | Strömbom, D., et al. | 2014 | Modelo matemático de *shepherding* | n/d | reserva conceptual para la escolta/guiado. |
| W15 | Halter (Nueva Zelanda) | n/d | Collares GPS de *virtual fencing / guided herding* | n/d | verosimilitud de los collares/guiado del rebaño como infraestructura. |

**## Pendiente — fase percepción**

| # | autores | año | título | venue / URL | "Se usará para" (literal) |
|---|---|---|---|---|---|
| P1 | Ultralytics | n/d *(Anotar la VERSIÓN exacta al usarlo.)* | YOLO26 (detección en tiempo real, end-to-end / sin NMS, orientada a drones y robótica, asignación consciente de objetos pequeños — STAL) | n/d | el clasificador real que sustituya al ORÁCULO de `r_confirm`. |

Regla final literal de BIBLIOGRAFIA.md: "al pasar cualquier entrada a la memoria final, verificar autores/año contra arXiv/DOI (varias entradas de la fase de mundo vienen de DISEÑO.md sin URL y están marcadas como pendientes de verificación)."

Citas en el diario de DISEÑO.md fuera de §12 (todas ya consolidadas en BIBLIOGRAFIA.md): línea 600 "MAPPO, Yu et al. 2022"; línea 624 "DE-MADDPG, Sheikh & Bölöni 2020 — arXiv:2003.10598"; línea 909 "Silver et al. 2018 — Residual Policy Learning, arXiv:1812.06298"; línea 921 "Real Robot Challenge, arXiv:2101.02842"; línea 961 "Ng et al."; línea 1527 "Muro et al. (2011)".


**Marcado para el dueño**: toda entrada sin venue/URL/DOI en las tablas anteriores (campos "n/d") y las marcadas "verificar al citar" son
**NO VERIFICABLE AQUÍ** — se verifican en Scholar/arXiv antes de citar. En concreto: Janeiro-Otero 2020, Madden 2011, ICWDM, BeefResearch.ca,
Wolf Song of Alaska, Yu 2022 (MAPPO), Terry 2021 (PettingZoo), Bettini 2024 (BenchMARL), Strömbom 2014, Halter, YOLO26, criterio DRI de Johnson,
hazing/habituación (W8), FID (W9), vídeo (W10), R2 (autores), R4 (autores), R7b/R7d, R8b, R9b, R13 (título exacto), R15 (año/venue).

## 4. Dudas y ambigüedades detectadas

1. **Versiones del mundo mezcladas en la frase "mejores planos 0.57–0.72 vs suelo 2.68"**: 0.57–0.72 (run02/run03) se midieron en el arnés v2.4.1 contra un scriptado de 2.77/2.80 (`/data/wolves/run0{2,3}/eval_*.txt`); 2.68 es el scriptado/Reactive de v3.4 (`/data/wolves/run08_dieta50/eval_floor_v34.json`). Los planos run02/run03 no tienen medición en v3.4; si se quiere una comparación homogénea en v3.4 el único plano es run08 (2.17/2.25 vs 2.68/2.77).
2. **run01 "1 muerte en ~2.400 episodios"**: `train.log` muestra `ep_rew_mean=0.010` en dos ventanas separadas (~1,08–1,16 M y ~1,70–1,77 M pasos), lo que con una media móvil de 100 episodios sugiere 2 muertes, no 1; la línea 119 del log y DISEÑO.md dicen "una única". "~2.400" no está en ningún artefacto primario (estimación ≈ 2.270 desde el log).
3. **B_masa 0.57 vs 0.56**: 0.56 es v3.7 (`masa_v37__reactive.json`); 0.57 aparece solo como `masa_v36` (`/data/hrl_m1/m1pp/TABLA_M1PP.md`). Posible arrastre de versión.
4. **Decisiones/episodio "3.2"**: ningún artefacto da 3.2; el manager final da 3.465 (vs Reactive), 3.5 (vs run02), 3.43 (vs run09), 3.4 (60k). TABLA_MAESTRA redondea a 3.5.
5. **M2 "×3.3"**: cociente crudo de segundos 3.249 (y de fps 3.248). Con redondeo estricto es ×3.2; el informe STOP_M2 escribe ×3.3 (19.4/5.96). Recomendable "≈ ×3.25".
6. **Dobles redondeos documentados** (TABLA_MAESTRA §7.3): Reactive vs manager lobo 1.765 (1.76/1.77); run09 1.775 (1.77/1.78); M1'''' 1.765/1.755/1.76; réplica D2 manager 0.755 (0.76); B_oracle IC bajo 1.355 (1.36); réplica M1 IC bajo 1.375 (1.38); Δ réplica−oráculo IC alto 0.175 (0.18).
7. **Δ vs Reactive −0.53/−1.55/−1.01** son de la réplica D2 (seed 1). RUN-D2 da −0.53/−1.58/−1.09 y el conjunto −0.53/−1.56/−1.05. El paper debe decir de cuál habla.
8. **"3-1 = 0.019"** es de la réplica; en RUN-D2 3-1 = 0.000 (y 2-2 = 1.000). En la réplica además 4-0 ante 2º clúster = 0.057 (no mencionado).
9. **KNC 0 en D2**: `knc_frac` = 0.0 solo en natural y cebo-2f; en la celda "manager lobo" es `None` (no definido), no 0.
10. **STALLs 189**: los informes originales (STOP_D2_INFORME §2, DISEÑO.md) decían "en 300 episodios"; el denominador correcto es 400 (fe de erratas TABLA_MAESTRA §7.1). La réplica (147) también es sobre 400.
11. **Cruces del valle (2.250 / 4.750)**: son el primer punto de una rejilla de 250 ticks en el que la curva CEBO_keep iguala o supera a MASA (v3.5: 2.000→2.250; v3.4: 4.500→4.750); el cruce real está entre los dos puntos. "≈" es correcto.
12. **"Coste de deliberación pagado ≈ 0"**: no existe clave `delib_por_ep` en los JSON de evaluación del manager lobo; el valor 0.000 se calcula sumando `episodes[].delib_pagado`. (Sí existe `delib_por_ep` en los `summary.json` de D2: 0.014 / 0.019.)
13. **Referencias**: varias entradas de §12 de DISEÑO.md carecen de venue/URL (Janeiro-Otero, Madden, ICWDM, BeefResearch, Wolf Song of Alaska, Yu, Terry, Bettini, Strömbom, Halter, YOLO26); BIBLIOGRAFIA.md marca explícitamente como "verificar al citar" R2, R7, R8b, R9, R13, R15 y toda la fase de mundo. Ninguna lista de referencias en `/data`.
