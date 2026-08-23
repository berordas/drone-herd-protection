# INDEX del visionado — STOP-2' (Etapa 0 re-calibrada en v3.5 "regla del sonido")

Render Commit F bis: **cuadrado NARANJA** = lobo detectado (≤ r_detect=100 de un ACTIVE) ·
**cuadrado ROJO** = lobo confirmado (latch de la barrera) · **anillo azul punteado** = DETER_RADIUS=20
(el sonido) de cada ACTIVE · **🔊** = dron con algún lobo a ≤20 (v3.5: suena quieto o en marcha) ·
línea azul discontinua = investigación. Timelines sidecar en `timelines/`.

Orden de firmas: 1º aserciones ✔ (0 CRITICAL / 0 violaciones, 2.398 eps) · **2º visionado del dueño
(esta tabla)** ☐ · 3º `../STOP2prima_INFORME.md` (válido tras la firma 2).

| # | GIF (`gifs/`) | semilla · celda | qué mirar | log |
|---|---|---|---|---|
| 1 | `dpos_max_cebo_keep_…_seed470_mixto_sev7` | 470 mixto · G/CEBO_keep vs Reactive (sev 7; gemelo MASA sev 0) | show=latch t=3003 tras 3.000 ticks de merodeo (el asalto tarda en estacionarse: la línea suena); ESCOLTA t=3177 por el señuelo; LURE_COMMIT t=3252 (3-4 drones en cono, puerta 60-68 m); 7 muertes desde t=3538 con el asalto entrando por la ESPALDA del ancla (octantes 0/3): **¿ves algún cruce por un corredor? no debería** | ☐ |
| 2 | `dpos_max_masa_…_seed470_mixto_sev0` | gemelo MASA (sev 0) | la línea que suena mantiene al paquete compacto fuera todo el episodio (timeout): así se ve "MASA baja" en v3.5 | ☐ |
| 3 | `dneg_max_cebo_keep_…_seed100_lobos_sev0` | 100 lobos · G/CEBO_keep (sev 0; MASA sev 6) | el cebo que fracasa: señuelo cazado/anclado y el asalto no encuentra hueco (bimodalidad: P(0) 37%) | ☐ |
| 4 | `dneg_max_masa_…_seed100_lobos_sev6` | gemelo MASA (sev 6) | MASA mata 6 desde t=907 con TODOS los matadores CONFIRMADOS (rojos) por octantes 0-1/5-6: la línea suena pero el paquete de 4 la rodea — flancos + espalda (deliberados) | ☐ |
| 5 | `primer_lure_…_seed2_lobos_sev5` | 2 lobos · G/CEBO_keep | primer LURE_COMMIT de la celda; compárese con el mismo seed en v3.4 (`/data/hrl_e0/e01/gifs/primer_lure_*seed2*`): mismo spawn, mundo distinto | ☐ |
| 6 | `mediano_a_…_seed476_lobos_sev2` | mediano | comportamiento típico G/keep en v3.5 | ☐ |
| 7 | `mediano_b_…_seed460_mixto_sev2` | mediano (mixto: distractores) | ídem con corzos: ¿el investigador se va al corzo? | ☐ |
| 8 | `escolta_prematura_asalto_…_seed2_lobos_sev0` | S · CEBO(180) forzado | tránsito de reposicionamiento largo: el asalto se hace ver (naranja→rojo en un lobo del asalto antes del show) → cebo nace muerto | ☐ |
| 9 | `escolta_prematura_señuelo_…_seed3_lobos_sev0` | S · CEBO(90) vs run02 | el singleton cazado al nacer por el barrido (rojo a t≈93), show 780 ticks tarde | ☐ |
| 10 | `sev5mas_…_seed45_lobos_sev7` | G/CEBO_keep sev 7 | matanza por la espalda del ancla con la línea sonando en su frente | ☐ |
| 11 | `/data/metro_v35/gifs/v35_masa_reactive_gemelo_gif2_seed398_mixto_sev3` | el GIF 2 del forense (v3.4: cruce por el punto medio t=672 + apilamiento) EN v3.5 | **el cruce del punto medio ya no ocurre** (0 gotera); las 3 muertes entran por la espalda (octante 6/0) sin confirmar; ¿sigue habiendo apilamiento en PENETRADO? (hallazgo B, código intacto) | ☐ |
| 12 | `/data/metro_v35/gifs/v35_cebo_keep_gemelo_gif1_seed398_mixto_sev7` | el GIF 1 del forense EN v3.5 | mismo ciclo del cebo; los 🔊 deben encenderse en cada dron con lobo a ≤20 aunque esté quieto | ☐ |

Comprobaciones globales para la firma 2: (a) ningún lobo cruza ENTRE dos drones a 20 m; (b) todo dron
con un lobo dentro de su anillo lleva 🔊; (c) los cuadrados: naranja al detectar, rojo al confirmar.
