# INDEX del visionado — STOP-F1 (forense de los GIFs 1 y 2 de e01, render Commit F)

Leyenda nueva del render (decisión del dueño): **cuadrado NARANJA** = lobo DETECTADO (≤ r_detect=100 de un ACTIVE) ·
**cuadrado ROJO** = lobo CONFIRMADO ante la barrera (latch de equipo; el rojo sustituye al naranja) · **anillo azul
punteado** = DETER_RADIUS=20 de cada ACTIVE (el campo del sonido) · línea azul discontinua =
investigación · 🔊 = dron que embiste (approach > 1 m/s).

| # | GIF | semilla/tipo · celda | qué mirar (ticks del timeline) | log del dueño |
|---|---|---|---|---|
| 1 | `e01/gifs/dpos_max_cebo_keep_cebo_keep_h50_reactive_seed398_mixto_sev7.gif` | 398 mixto · G/CEBO_keep vs Reactive (sev 7) | t≈903 cuadrado naranja sólo en el señuelo (lobo 0, esquina NO); t≈972 cuadrados naranja en el asalto (detectados) **antes** de t=989 cuadrado ROJO en el señuelo (confirmado, ESCOLTA t=988) — DETECCIÓN del grande ≠ CONFIRMACIÓN; la línea rígida se ancla al señuelo (esquina NO) y el asalto (2 lobos, solo naranja, nunca rojo) mata 6 reses dentro del rebaño desde t=1297: KNC. **0 cruces de corredor. 0 apilamiento** (solo hand-off 2-2.6 m a t=1105/1146). | ☐ |
| 2 | `e01/gifs/dpos_max_masa_masa_reactive_seed398_mixto_sev0.gif` | 398 mixto · MASA vs Reactive (sev 0, timeout) | **t=672: CRUCE por el punto medio** del corredor (lobo 0 entre dos drones a 20 m; frac 0.50; dron más cercano a 9.96 m con approach −0.57 → sin 🔊, sin expulsión; pared 0.01) · **t=802-1282 PENETRADO**: los 4 drones libres reciben el MISMO waypoint (1 lobo confirmado) → drones 0 y 6 apilados a 0.5-0.75 m (t=889-900), tríos 0-5-6 a <3 m; con 3 confirmados 4%3 → dos drones al mismo lobo · t=797/807 naranja en lobos 1-2 y rojo a 873/877 (paquete fusionado: MASA no tiene roles). | ☐ |

Timelines sidecar: `e01/timelines/dpos_max_*.txt`. Frames de muestra:
`forense/frame_gif1_conf.png` (t≈1006, señuelo confirmado en rojo), `frame_gif1_late.png`
(t≈1348, asalto matando sólo con naranja), `frame_gif2_penetrado.png`.

Orden de firmas: 1º aserciones (0 CRITICAL en ambos episodios) ✔ · **2º visionado del dueño
(esta tabla)** ☐ · 3º FORENSE.md ✔ (escrito, pendiente de la firma 2).
