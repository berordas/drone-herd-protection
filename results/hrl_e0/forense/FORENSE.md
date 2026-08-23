# FORENSE — hallazgos del visionado humano de STOP-1/2 (solo lectura, replay determinista)

Fecha 2026-08-18 · código `6beb8bd` + Commit F (render) · scripts:
`/data/hrl_e0/verif/forense_e01.py` (replay tick a tick, JSON en `/data/hrl_e0/forense/`) y
`forense_b.py` (ventana del apilamiento). Nada arreglado. E0.3-E0.5 y Etapa 1 CONGELADOS.

## 1. Identificación de los GIFs 1 y 2 de e01

| GIF | fichero | semilla / tipo | celda | motivo de selección |
|---|---|---|---|---|
| 1 | `dpos_max_cebo_keep_cebo_keep_h50_reactive_seed398_mixto_sev7.gif` | 398 / mixto | **G** (spawn [1, 2], n=3) · CEBO_keep vs Reactive | par de MAYOR Δ+ (sev 7 vs 0) |
| 2 | `dpos_max_masa_masa_reactive_seed398_mixto_sev0.gif` | 398 / mixto | **G** · MASA vs Reactive (gemelo) | mismo par, brazo MASA (sev 0, timeout 23.570) |

Ambos re-renderizados con el Commit F (cuadrado rojo = detectado; rombo naranja = confirmado
por la barrera; anillo azul de DETER_RADIUS=20 en cada ACTIVE ya existía).

## 2. Hallazgo A — "el frente GRANDE dispara las alarmas en vez del señuelo"

Cadena reconstruida (primera detección = ≤ r_detect de un ACTIVE; primera confirmación =
latch de equipo de la barrera):

- **GIF 1 (G/CEBO_keep)**: detección lobo 0 (señuelo) t=903 · lobos 1-2 (asalto) t=972 ·
  **confirmación: SOLO el lobo 0, t=989** (ESCOLTA t=988, ancla = lobo 0). El asalto NUNCA
  es confirmado (KNC: los 6 primeros matadores no confirmados). Cadena canónica del cebo:
  **no contradice el informe de STOP-2, no hay bug** en el brazo confirmatorio.
- **GIF 2 (G/MASA)**: detección lobo 0 t=186 → confirmación t=231 (ESCOLTA); lobos 2 y 1
  detectados t=797/807, confirmados t=873/877. En MASA no hay roles: la opción FUSIONA el
  paquete (pack_prey2=−1); el "frente grande" que se ve disparar alarmas es el paquete
  entero convergiendo — comportamiento diseñado de MASA. Aquí también el primer confirmado
  es el lobo 0 (el singleton del spawn, cazado por el barrido primero).
- Conclusión: el modo "asalto confirmado primero" existe (E0.1: 345/481 prematuras, TODAS
  en celdas S/manager con reposicionamiento largo), pero **no en este par**. Si el dueño vio
  el fenómeno en el GIF 1, lo que se ve a t≈972-989 es la DETECCIÓN (cuadrado) del asalto
  16 ticks antes de la confirmación del señuelo — visualmente parecido, mecánicamente
  distinto: el render nuevo lo separa (cuadrado vs rombo).

## 3. Hallazgo B — drones apilados

- **GIF 1**: 0 ticks-par de apilamiento fuera de hand-off (3 ticks-par de hand-off legítimo a
  2.06-2.57 m, estados ACTIVE-INCOMING).
- **GIF 2**: **246 ticks-par de apilamiento real** (dist mín 0.10 m; drones 0-6 a 0.5-0.75 m
  durante 12+ ticks seguidos en t=889-900; tríos 0-5-6 a <3 m) + 47 de hand-off.
  Ventana: t=802-1282, **exactamente la ventana en que el coordinador está en PENETRADO**
  (392 ticks); ninguno con investigación activa; ninguno en rama CLEAN.
- Contraste de hipótesis:
  - **(a) PENETRADO manda a todos al mismo par lobo-vaca — CONFIRMADA.** `_cover_engaged`
    (coordinators.py:359-373) asigna la ranura `order[s % order.size]`: con UN lobo
    confirmado los 4 drones libres reciben el MISMO slot (replay t=861-870: slots
    `[(0,[210.6,310.1])×4]`, wp de los 4 drones idéntico); con 3 confirmados, 4 % 3 → dos
    drones al lobo 2 (t=876+: `[(2,…),(1,…),(0,…),(2,…)]`, drones 5 y 6 al mismo punto,
    wp_dist=0.0). El vuelo converge y se apilan a <1 m.
  - (b) degeneración del eje: descartada — en PENETRADO no se calcula eje ni pose.
  - (c) apilamiento de investigadores: descartada (inv=[] en toda la ventana).
  - (d) pareja de hand-off (≤2 m, diseño): existe (47 ticks-par) pero es DISTINTO — 
    estados [ACTIVE, INCOMING], transitorio ≤3 ticks; los apilamientos largos son
    ACTIVE-ACTIVE.
- Agravante de diseño observado: la entrada en PENETRADO usa `d(ancla, centroide) ≤ herd_r`
  con `herd_r` = distancia MÁXIMA de una res al centroide (29 m en este rebaño mixto
  disperso): un lobo a 25 m del centroide ya cuenta como "dentro del rebaño". Con el
  rebaño disperso PENETRADO se dispara pronto y dura mucho (392 ticks aquí; en E0.1 los
  cruces de gotera y las muertes en PENETRADO no se auditaron por separado — pendiente).
- **Diagnóstico: BUG de diseño del coordinador** (`_cover_engaged` no reparte ranuras
  únicas por dron cuando hay menos lobos que drones; el módulo pone a varios drones en el
  MISMO punto, que además está a `engage_standoff`=12 m de la vaca — dentro del rebaño y
  sin efecto disuasorio: 4 drones apilados = 1 poste). Es la clase de comportamiento que
  ningún test cubre y que el visionado destapó. Propuesta (para la ventana de enmienda,
  commit separado con test dirigido, sujeto a OK): en `_cover_engaged`, ranuras ÚNICAS
  por dron — si hay menos lobos que drones, los drones sobrantes se reparten en ARCO
  alrededor del lobo más enganchado (offsets angulares equiespaciados a engage_standoff
  de la vaca) en vez de superponerse; test_apilamiento = la situación del replay (1 lobo
  confirmado, 4 libres) produce 4 waypoints con separación mínima ≥ 2·STATIC_DETER_RADIUS.
  **DECISIÓN HUMANA PENDIENTE** (alternativa: aceptar como conducta de la baseline).

## 4. Hallazgo C — cruce por el punto medio (causa raíz confirmada por tick)

- GIF 1: 0 cruces de corredor hacia el rebaño (todo el daño entra por la espalda del ancla:
  octantes 2-5, KNC 6/7 — el cebo, no la gotera).
- **GIF 2, t=672, lobo 0**: cruza el segmento entre dos drones libres contiguos separados
  **20.0 m** (el corredor nominal) a **frac 0.50 del segmento** (el punto medio EXACTO),
  0.12 m de la línea; distancia al dron más cercano **9.96 m** (dentro de la pared, fuera del
  radio de… no: dentro de DETER=20 también); **approach de ese dron −0.57 m/s < 1.0 =
  SCARE_APPROACH_MIN ⇒ EXPULSIÓN INACTIVA** (`scared_mundo=False`); pared blanda ACTIVA
  (`walled_mundo=True`) pero **|empuje| = 0.01 m/s ≈ 0**: en el punto medio los dos empujes
  radiales salientes se cancelan por simetría y `v_slide` sólo quita la componente hacia el
  dron más cercano (que ahí es ~perpendicular al avance). El lobo cruza a paso casi pleno.
- Confirma la causa raíz enunciada por el dueño: **la expulsión exige aproximación >1 m/s y
  la pared vale 0 en el punto medio** — la línea rígida quieta es permeable en cada corredor
  (con Reactive: 30-55% de las muertes de E0.1 tras un cruce de gotera).
- La regla del sonido (expulsión a ≤20 de CUALQUIER ACTIVE, sin approach) lo cierra por
  construcción: el punto medio está a 10 m de dos ACTIVE ⇒ expulsado.

## 5. Estado y siguiente

- Commit F (render) listo para commit tras la verja: cuadrado detectado (+ leyenda), rombo
  confirmado (desde `confirmed_mask` en snapshot, lo escribe el arnés HRL), anillo de sonido
  ya existente. GIFs 1 y 2 regenerados con el render nuevo (mismas semillas).
- **STOP-F1: VISIONADO HUMANO PRIMERO.** Sin OK del dueño no se toca física (FASE 2) ni
  coordinators.py (arreglo de B).
