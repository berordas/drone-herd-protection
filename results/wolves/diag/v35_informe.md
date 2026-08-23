# v3.5 — Cerrar la gotera central por GEOMETRÍA (solape de paredes): INFORME DE MEDIDA

**Estado: SIN CONGELAR. El repo sigue limpio en `bfd78bf` (v3.4-baseline); ni un archivo del repo
tocado; face_check 12/12 verde.** La regla del prompt era «re-congelar SOLO si la métrica de cruces
pasa»: la premisa del solape pequeño quedó REFUTADA por la medida (s=18 no mueve la métrica) y el
único régimen que la cumple (s≈4–5) es un cambio de diseño cualitativo (escudo de 12–15 m, no
línea) que además HUNDE la nota a batir del MARL — bifurcación que decide el usuario, no yo.

Todo medido DENTRO del contenedor (metro DGX), sobre v3.4 (`bfd78bf`), con
`ReactiveCoordinator(w, drone_spacing=S)` (equivalente verificado a cambiar el default; el standoff
se deriva solo). Scripts y datos en este directorio (`v35_*`); GIFs en `/data/gifs/v3.5/`.

## 1. La premisa, verificada numéricamente (comprobación pedida en el prompt)

`v35_midpoint_check.py` (+ `.txt`): en el punto medio entre dos drones (0, y), descomposición de
los DOS vectores de pared del modelo real (validada fila a fila contra `World._apply_deterrence`):

- **Σ a-lo-largo de la línea = 0 SIEMPRE** (cancelación por simetría — como decía el diagnóstico).
- **Con solape (s<2R), Σ perpendicular hacia AFUERA > 0 para todo y>0**: el mecanismo del prompt
  EXISTE. Con paredes tangentes (s=2R=20) el lobo solo queda walled sobre la línea misma (y=0),
  donde esa componente es 0 → nada lo frena: la gotera de v3.4, confirmada.
- **PERO la magnitud no da**: con `STATIC_DETER_GAIN=0.6`, a s=18 el frenado neto máximo en el
  corredor es ~+0.08 m/s contra −3.3…−3.9 m/s de intención de caza residual (el deslizamiento solo
  quita la componente hacia el dron MÁS CERCANO, que en el punto medio es casi lateral). El signo
  de v_y solo se invierte (banda de estancamiento) a partir de s≤7.5.
- **Límite duro, para cualquier espaciado**: en y→0 el empuje perpendicular se anula por simetría
  (ambos términos son O(y)) → sobre la propia línea el corredor NUNCA queda sellado; solo se puede
  alejar la banda de equilibrio. Verificado analítica y numéricamente (v_wall(y=0.01)≈(0,−4) hasta
  con s=2).

## 2. La métrica del usuario: curva completa (mismos 28 episodios y contador que v3.4)

`v35_cruces_sweep.py` = contador EXACTO de `v34_cruces_anatomia.py` (seeds 0–13 × lobos/mixto).
Cruces de segmento HACIA DENTRO con línea en pie (v3.4 = 92 ≈ 3.3/ep):

| espaciado s | solape 2R−s | frente (4 drones) | cruces | por ep | rodeos por flancos |
|---:|---:|---:|---:|---:|---:|
| 20 (v3.4) | 0 | 60 m | **92** | 3.29 | 13 |
| 18 (prompt) | 2 | 54 m | **91** | 3.25 | 26 |
| 14 | 6 | 42 m | 91 | 3.25 | 26 |
| 12 | 8 | 36 m | 67 | 2.39 | 27 |
| 10 | 10 | 30 m | 70 | 2.50 | 30 |
| 8 | 12 | 24 m | 28 | 1.00 | 31 |
| 7.5 | 12.5 | 22.5 m | 20 | 0.71 | 27 |
| 7 | 13 | 21 m | 20 | 0.71 | 32 |
| 6.5 | 13.5 | 19.5 m | 13 | 0.46 | 26 |
| 6 | 14 | 18 m | 7 | 0.25 | 32 |
| 5 | 15 | 15 m | 4 | 0.14 | 59 |
| **4** | **16** | **12 m** | **0** | **0.00** | 52 |

- s=20 REPRODUCE v3.4 exacto (149 total / 92 clean / 80 walled / 10 scared / 13 rodeos) — el
  contador está validado extremo a extremo.
- **El solape de 2 m del prompt no mueve la métrica (92→91).**
- Los cruces residuales a cualquier s siguen siendo el corredor: interior, sfrac≈0.5, walled.
- **Solo s=4 da 0.** El diámetro del rebaño vivo en ESCOLTA es ~60 m mediana (p25 29.5, p75 74.5,
  medido): a s=4–5 la «línea» es un ESCUDO de 12–15 m y el tráfico lobuno se reencamina por los
  extremos (rodeos ×4: 13→52–59).

## 3. Anatomía de los residuales (por qué no llega a 0 con banda de estancamiento)

`v35_residual_anatomia.py` (+ `.txt`, s=7.5/7/6): en el paso del cruce la pose está QUIETA
(|Δc| mediana 0.07–0.09 m/paso), NINGÚN dron se echa encima (0/47 con gate de expulsión >1 m/s;
aproximación mediana −0.2 m/s), y el lobo cruza PERPENDICULAR (|cos|≈0.98–1.00) a ~3.0–3.2 m/s
tras ~65–80 pasos amurallado. NO es el atropello de la línea que avanza (hipótesis descartada con
datos): es la banda de estancamiento —fina y con frenado ≤~0.7 m/s neto— cediendo ante las
intenciones cambiantes de la manada (envolvente/separación/presa móvil) hasta colarse por el
saddle de y→0 del §1.

## 4. Testbed dinámico (física real bit a bit, pose quieta = peor caso v3.4)

`v35_corridor_scan.py` / `v35_corridor_fine.py`: integración con la MISMA física
(`_apply_deterrence` real + inercia idéntica; fidelidad bit a bit verificada por
`v35_verify_fidelity.py`, diff = 0.0 exacto): el ataque frontal al corredor CRUZA para todo
s≥8 y se estanca (min_y +7…+9 m) para s≤7.5; a s≤7.5 todos los modos de fallo restantes son
rodeos por el EXTREMO. Con k=4 y s=18 el 3er dron queda a 27 m del punto medio (solo suma pared
a s≤2R/3≈6.7): el solape entre VECINOS es lo único que actúa, como asumía el diseño.

## 5. Severidad (sonda con el arnés real: `baseline.evaluate`, 100 semillas × 3 tipos)

`v35_severity_probe.py` — NO es un congelado; es la consecuencia medida (v3.4: 2.68/0/2.77;
Dummy congelado 3.82/0/3.84):

| s | solo-lobos | solo-distracción | mixto | success (lobos/mixto) | n_safe |
|---:|---:|---:|---:|---:|---:|
| 18 | 2.64±1.62 | 0.00 | 2.71±1.55 | 5/6 | 4.14/4.16 |
| 7 | 1.46±2.00 | 0.00 | 1.24±1.82 | 45/48 | 5.33/5.55 |
| 6 | 1.17±1.99 | 0.00 | 1.01±1.77 | 54/58 | 5.61/5.78 |
| 5 | 1.09±1.99 | 0.00 | 0.79±1.58 | 60/65 | 5.75/6.03 |
| **4** | **1.05±1.96** | **0.00** | **0.87±1.71** | **66/68** | **5.86/6.02** |

- s=18 ≈ v3.4 (2.64/2.71 vs 2.68/2.77, dentro del ruido): coherente con la métrica sin mover.
- **El escudo estrecho DESPLOMA la severidad** (2.68/2.77 → ~1.2/1.0 a s=6): los lobos que rodean
  no capitalizan — el rodeo cuesta tiempo, el guiado mete las vacas al establo (n_safe 4.16→5.8,
  success 5%→58%). El «agujero deliberado» de flancos NO es explotable por el scriptado actual.
- Consecuencia estratégica: congelar s pequeño HUNDE la nota a batir del MARL (de 2.68/2.77 a
  ~1.0-1.2) — cambia la narrativa del proyecto entera.

## 6. GIFs (evidencia, `/data/gifs/v3.5/`)

- `v35_seed20_n1_solape_s18_lobo_cruza_el_corredor_igual.gif` — s=18: cruce por el corredor pese
  al solape de 2 m (11 cruces ese episodio, sev 4). La premisa del prompt, refutada en GIF.
- `v35_seed26_n2_solape_s6_presion_corredor_3036pasos_no_cruza.gif` — s=6: lobo empujando el
  corredor 3.036 pasos (~5 min) SIN cruzar (dmin 8.4 m), sev 0. El GIF pedido por el prompt —
  existe, pero solo en el régimen de frente colapsado.
- `v35_seed19_n2_solape_s4_presion_corredor_2928pasos_no_cruza.gif` y
  `v35_seed6_n3_solape_s4_rodeo_por_el_flanco_linea_estrecha.gif` — s=4 (el único que da 0 cruces):
  presión sostenida sin cruce y el rodeo-por-flanco que acaba en success (sev 0).
- `v35_seed11_n3_solape_s6_rodeo_por_el_flanco_linea_estrecha.gif` — el precio en flancos, s=6.

## 7. Verificación adversaria (workflow, 3 escépticos independientes — NINGUNO refutó)

1. **Contador**: fiel a v3.4 (diff mecánico + re-ejecución determinista) y validado con un detector
   independiente en marco móvil (`v35_verify_counters.py`): ambos contadores colapsan juntos
   (115→26→1); sin túnel; 0 cruces en los pasos no evaluados. Matiz honesto: ambos contadores
   (v3.4 y v3.5 POR IGUAL) evalúan contra el segmento post-step (~±20-25% de ruido definicional en
   valores absolutos a TODOS los espaciados; la forma de la curva es idéntica).
2. **Física**: testbed bit a bit exacto contra `_update_wolves` real; anulación en y→0 correcta;
   mecanismos omitidos (línea en movimiento: jitter/patrulla a 1.6–3.1 m/s) NO sellan s≥14.
   Bug de testbed hallado y anotado: (250,250) coincide con el centro del establo — equivalente a
   campo abierto SOLO porque `run()` omite los clamps (comentario corregido en el script).
3. **Alcance y verja**: `drone_spacing` es el ÚNICO dial geométrico (offsets y standoff derivan de
   él); override ≡ default; los 10 tests estructurales de `reactive_check.py` PASAN con s=4 y s=6
   (`v35_verify_gate.py`) — la verja NO impediría congelar un espaciado pequeño; el único freno
   sería el juicio (GIF/severidad), como manda la disciplina del repo.

## 8. La bifurcación (decisión del usuario — el que lleva el diseño)

La gotera central NO se cierra «con un poco de solape»: el mecanismo perpendicular existe pero es
débil (GAIN=0.6) y nulo en la propia línea para cualquier espaciado. Opciones sobre la mesa:

- **(a) Congelar v3.5 como ESCUDO (s=4–5 = 0.4–0.5·R)**: métrica 0–4 cruces ✓, severidad ~1.0–1.2
  (pendiente medirla exacta a s=4-5 — ver tabla), GIFs listos. Precio: deja de ser una «línea»
  (12–15 m vs rebaño ~60 m), rodeos ×4, y la nota a batir del MARL se hunde — ¿sigue siendo la
  «baseline ingenua» que el MARL debe batir, o es ya otra defensa?
- **(b) Mantener v3.4 (s=20)** y aceptar la gotera central como agujero documentado más (junto a
  flancos, espalda del anillo y 2º frente): el corredor solo es cruzable con presión perpendicular
  sostenida (~8 s amurallado) — material para el MARL.
- **(c) Cerrar por FÍSICA, no por geometría** (fuera del alcance de este prompt: requiere permiso
  para tocar el modelo congelado): p.ej. que el deslizamiento quite la componente hacia LA LÍNEA
  (no hacia el dron más cercano) o subir `STATIC_DETER_GAIN` — cambiaría face_check/baselines y
  re-mediría todo.
- **(d) Punto intermedio medido** (p.ej. s=6: 0.25 cruces/ep, −92% vs v3.4; frente 18 m; severidad
  1.17/0/1.01) si se acepta «≈0» como «residual» en vez de «cero».

**Nada congelado ni commiteado a la espera de esa decisión.**
