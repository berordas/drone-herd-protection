# Proyecto AI Lab — Drones que protegen ganado de lobos (simulación)

> **Qué es este documento.** Es la memoria viva del proyecto: recoge todo el diseño, las
> decisiones tomadas, las herramientas, el plan, las referencias y —muy importante— las
> "banderas levantadas" (cosas aparcadas para más adelante). Sirve como borrador de la
> memoria final (70% de la nota) y como contexto para retomar el trabajo en un chat nuevo.
> **Última actualización:** **PRESA COMÚN de la manada** (commitment) sobre el modelo "dar la cara":
> la manada fija UNA presa (la más rodeada = min dist al centroide de lobos; lentitud emergente) y la
> MANTIENE (histéresis: abandona solo si se refugia o escapa) → todos confluyen y **flanquean** en vez
> de N duelos. Re-fijaciones ≈ **0**, ~1 vaca atacada a la vez. **Instrumentado el flanqueo (#3):
> quórum de 2 flanqueadores → muerte CONFIRMADA (84/84)**. Render: el cono se dibuja como **cuña ±45°**
> y los lobos se colorean (oro=a raya / rojo=flanqueando), con realce de la presa fijada. Tasa sin
> drones = **84%** (no se persigue; el lobo
> completo y los drones llegan en v2). Baseline v1 (49%) ya no aplica; se re-congela como v2.

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
  1. **Clásica**: reglas escritas a mano (FSM/comportamiento). Terreno conocido (viene de la
     asignatura de Robots Móviles Autónomos).
  2. **Aprendida**: aprendizaje por refuerzo multiagente (MARL). Más avanzado.
  La **comparación** clásico vs aprendido es el corazón del trabajo y la columna del paper.

---

## 2. Arquitectura del sistema

### 2.1. Tres capas (clave para reducir dificultad)

1. **Estabilización**: delegada a un autopiloto (PX4). No se programa el control de bajo nivel
   del dron (igual que en el TurtleBot se comandaba (v, w) y el simulador actuaba las ruedas).
2. **Guiado**: "ve a este waypoint / mantente / sigue a este objetivo" → emite referencias de
   velocidad. Se construye reutilizando el **pure pursuit** de la asignatura de robots.
   **Compartido** por las dos ramas.
3. **Coordinación**: decide *modos y objetivos* de alto nivel para cada dron. Es **lo único que
   se implementa dos veces** (FSM clásica vs política MARL) y **lo único que se compara**.

> El espacio de acción de la capa 3 es de **alto nivel** (qué modo, qué objetivo), no
> velocidades crudas. Esto aísla la comparación al nivel de *decisión* y le quita dificultad al
> RL (elige entre pocas decisiones sensatas, no pilota).

### 2.2. Coordinador intercambiable

Interfaz fija `coordinador(observación) → acciones`. Se construye **el mundo una sola vez** y
detrás de esa interfaz se enchufan las dos implementaciones (FSM y MARL). Misma observación
entra, mismo formato de acción sale, mismo juez (métricas). Es lo que hace válida la comparación.

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
- Empezar con acciones **discretas** (mejor para MARL y casi 1:1 con las salidas de la FSM →
  misma interfaz real para ambas ramas). Velocidades continuas = extensión realista.
- **Número variable de vacas/compañeros:** la observación para el MARL debe ser de tamaño fijo
  → empezar con rasgos agregados (centroide, dispersión, k más cercanos); luego subir a un
  **codificador invariante a permutaciones** (Deep Sets o atención), que además da escalabilidad
  (entrenar con N vacas, evaluar con 2N). Para la FSM clásica, basta iterar.

---

## 4. Modelo del mundo

### 4.1. Lobo — caza direccional (cono frontal + flanqueo + nº mínimo)  ✅ IMPLEMENTADO

Reutiliza el lobo de **Muro et al. (2011)** (*"Wolf-pack hunting strategies emerge from simple
rules…"*, Behavioural Processes 88(3), 192–197) pero lo hace **DIRECCIONAL** y con **PRESA COMÚN**:
1. **Presa COMÚN de la manada (commitment):** toda la manada comparte UNA presa fijada (`pack_prey`),
   no "cada lobo la suya" (sin eso → N duelos 1-contra-1, no pincer). **Selección** (`_select_prey`,
   factorizada para enchufar terneros luego): la adulta **más rodeada** = la que minimiza la dist al
   **centroide de los lobos** (oportunista); la lentitud importa **emergente** (la lenta se descuelga →
   acaba siendo la más rodeada). **Fijación** en modo caza (≥ `n_min_adult` lobos y un lobo a ≤ `r_notice`
   de la presa elegida). **Histéresis**: se mantiene hasta volverse **inviable** (se refugia en zona
   prohibida, o escapa > `prey_abandon_dist` del lobo más cercano; `prey_abandon_dist` > `r_notice`).
   Verificado: re-fijaciones ≈ 0, ~1 vaca atacada a la vez (`face_check.py`).
2. **Aproximación respetando el cono frontal:** si el lobo está **en el cono** de la presa (±45°)
   **circula** hacia el flanco manteniendo `r_face_safe`; si está en el **flanco/grupa** **cierra a
   matar**. El standoff de Muro pasa de omnidireccional a **solo en el cono**.
3. **Regla de número mínimo (`n_min_adult`=2):** un lobo solo **NO ataca** (standoff amplio
   `r_standoff`, sin fijar presa). Con ≥ `n_min_adult` lobos, la **manada sí**.
4. **Repulsión entre lobos** alrededor de la presa única → reparto angular = **pincer** (uno de
   frente, los demás a los flancos). **Banda muerta** (`cone_band`) → no entra-sale en el borde.

**Muerte por FLANQUEO:** la adulta muere cuando **≥ `n_min_adult` lobos** están **a la vez** dentro de
`capture_radius` **y fuera de su cono**. Con 1 lobo (encarado) → 0 flanqueadores → **no muere**.
**Instrumentado (#3)** (`_instrument_flanking`): cada paso cuenta lobos en `capture_radius` y
flanqueadores válidos, loggea el primer quórum y si dispara la muerte, y desglosa los "toques" que no
matan. **Confirmado: 84/84 episodios con quórum → muerte** en ese paso (era síntoma de #2: sin presa
común casi nunca confluían 2 flanqueadores en la misma vaca).

**Número de lobos aleatorio por episodio** (1–5): de lobo solitario (no puede) a manada (sí puede).
**Escalera de adversarios:** ingenuo → **manada direccional (ACTUAL)** → busca-huecos → con amago
(los dos últimos cuando los drones se muevan). Disuasión (ladrido/dron subiendo la distancia
efectiva, con habituación) y EKF de estimación del lobo: PENDIENTES (ver plan).

### 4.2. Vacas adultas — "DAR LA CARA" (confrontación direccional)  ✅ IMPLEMENTADO (escolta PENDIENTE)

Modelo de amenaza basado en cómo cazan los lobos de verdad: **el ganado grande no se apiña, planta
cara** (se gira al lobo y lo confronta); el lobo va a la débil y ataca por el flanco/grupa, evitando
la cabeza. *(Sustituye al modelo de apiñamiento: al medirlo, el huddle quedaba **más apretado** que
el pasto y se tragaba a la rezagada → nadie aislado a quien cazar limpiamente. Se conservan pasto
disperso y heterogeneidad de velocidad.)* Sin terneros aún (paso siguiente): solo vacas adultas.

- **Pasto (sin amenaza cerca):** disperso y tranquilo = separación + **deambular firme** (paseo
  **angular lento** del rumbo, no aleatorio fresco cada paso) + valla blanda. **SIN cohesión/apiñamiento
  y SIN huida.**
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
  giro medio ~**0.10 rad/paso** (vacas) y ~**0.10** (lobos); la vibración daría ~π/2.
- **Verificación (`face_check.py`):** 1) lobo solo → 0 muertes, lo mantiene a `r_standoff`=12 m;
  2) manada → encara a uno, los demás flanquean, **muere la débil** con ≥2 flanqueadores; 3) métrica
  de tembleque baja; 4) **tasa sin drones = 83%** (no se persigue); 5) reproducible.
- **Escolta — PENDIENTE:** **collares** conducen el rebaño al refugio; **drones escoltan** (pantalla
  + disuasión). "Escolta" = proteger el traslado, no empujar.

### 4.3. Batería y estación de carga  ✅ IMPLEMENTADO (mecánica del mundo)

**Implementado** (`world.py: _init_battery/_step_battery`, verificado en `battery_check.py`):
máquina de estados por dron `ACTIVE → RETURNING → CHARGING → READY → ACTIVE`; batería fracción
[0,1] con tasas DERIVADAS de las capacidades (`drain=1/600 s⁻¹`, `charge=1/300 s⁻¹`); **cola sin
emparejamiento** (al liberarse un puesto sale el más cargado de la central, sin esperar al 100%);
**arranque escalonado** (RNG, solo en operación continua). Régimen permanente verificado:
**4 activos / 2 cargando / 2 listos**, relevos escalonados (~1 cada 125 s, 0 simultáneos), siempre
4 puestos cubiertos, **baseline intacto** (49%). Es **automático por umbral** (regla del mundo), no
acción del coordinador (seam para exponer "pedir relevo" luego). **Hooks**: `battery_activity`
(coste de persecución, bandera #7), `relay_travel_time` (vuelo de vuelta + hueco de cobertura),
`drone_stranded` (dron tirado), y stagger/randomización de batería inicial de episodio.

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

### 4.4. Estructura de episodio y criterio de éxito (DECIDIDO)

Tarea **episódica** (terminal claro, bueno para RL):

`Fase 0 vigilancia` (vacas pastando, drones monitorizando) → **disparador** (aparece el lobo y se
aproxima) → `Fase 1 escolta/defensa` (collares conducen al refugio, drones apantallan y disuaden)
→ **terminal**.

- **ÉXITO** = todas las vacas dentro de la zona segura **y** todos los lobos fuera del recinto.
- **FRACASO/parcial** = vacas cazadas; **cuantas más cace el lobo, más negativo**.
- Clavar: qué pasa si un lobo entra en el recinto tras las vacas (por eso "lobos fuera" importa),
  y un **límite de tiempo** para que el episodio no sea infinito.
- La **disuasión (ladrido)** es una **táctica durante la escolta** (ganar tiempo subiendo la
  `d_safe` del lobo), no la condición de victoria. La victoria es resguardar.

---

## 5. Métricas (juez compartido) y recompensa (solo RL)

> **Distinción clave:** las **métricas** juzgan ambas ramas; la **recompensa** solo entrena el
> MARL. La FSM no usa recompensa (se ajusta a mano), pero se la juzga con las mismas métricas.

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
- **Justicia:** ajustar la FSM honestamente contra estas mismas métricas (grid/random search o
  CMA-ES sobre umbrales/ganancias). Si no, "el MARL gana" = "no afiné la base".

### 5.2. Recompensa (solo MARL)

**Principio nº1:** no recompensar *proxies* (acercarse, cubrir, ladrar, compactar) → eso es
*reward hacking*. Recompensar **resultados** y dejar que el comportamiento emerja.

Para densificar la señal sin abrir agujeros: **shaping basado en potencial** (Ng, Harada &
Russell, 1999): `F(s,s') = γ·Φ(s') − Φ(s)` → **demostrado** que no cambia la política óptima
(no crea óptimos explotables; oscilar da cero neto).

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
- Cuando toque, pedir a Claude el `requirements.txt` (`torch`, `pettingzoo`, `benchmarl`,
  `numpy`, `matplotlib`) y el `docker-compose.yaml` exactos.

---

## 8. Plan de implementación por fases

- **Fase 1 — Mundo compartido + arnés + métricas.** Simulador ligero (Python/NumPy, sin render
  en el bucle), entidades, dinámica, episodio, registrador de métricas, **sustituto de
  percepción** (confianza de detección según distancia/altitud). Entregable: episodio ejecutable
  con métricas.
- **Fase 2 — Coordinador clásico (la línea base).** FSM/comportamiento detrás de la interfaz +
  pure pursuit. Ajustarlo honestamente contra las métricas. Entregable: sistema completo +
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
recompensa↔métricas no es opcional; currículo; **la línea base clásica es tu mejor depurador**
(si el MARL no iguala a una FSM decente, hay un bug). Sin render en el bucle → el DGX va sobrado.

---

## 9. Estado actual del código

Carpeta `AI_LAB/` (proyecto Python local). Estructura:
- `world.py` — clase `World`: estado, dinámica, recompensa, terminal. **Sin** ROS/render dentro.
- `render.py` — animación matplotlib (por reproducción: lee estado, nunca llama a `step`). Dibuja el **cono** como cuña ±45°, colorea los lobos por su relación con el cono de la presa, y realza la **presa fijada**.
- `coordinators.py` — `DummyCoordinator` (ignora obs, devuelve "todos quietos"); FSM y MARL después.
- `main.py` — bucle: reset → obs → coordinador → acciones → step → terminal → métricas.
- `baseline.py` — **adversario congelado** (config + seeds + métrica de referencia); `build_baseline_world(seed)` y self-check de deriva.
- `battery_check.py` — verificación macro del subsistema de batería (régimen permanente 4/2/2, escalonado, reproducible).
- `face_check.py` — verificación del modelo "dar la cara": lobo solo no mata, manada flanquea (con presa común) y mata, **coordinación** (~1 vaca a la vez, re-fijaciones≈0), **instrumentación de #3** (quórum→muerte), tembleque, tasa sobre range(100), reproducibilidad.

Decisiones de diseño ratificadas:
- Cada grupo de entidades = array `(N, 2)` de NumPy (vectoriza y se trocea por agente para MAPPO).
- Lobo como `(n_wolves, 2)` aunque varíe el número (no caso especial).
- `step(actions)` estilo gym (transición atómica); la observación se construye aparte en el bucle.
- **Render por reproducción** (separación limpia mundo↔dibujo; deja libre el adaptador ROS).
- Unidades SI (m, s; `dt=0.1`), **RNG sembrado** dentro del World (reproducibilidad bit a bit).
- Geometría sin números mágicos (derivada de `min(W,H)`): **establo (zona segura) en el centro**;
  **central de carga pegada a su borde pero sin solaparse**; **vacas pastan fuera** (spawn hacia
  una esquina); **"zona vacas" = bounding box dinámico** de las vacas (helper derivado, no
  encierra a nadie). **8 drones**: 4 activos en las esquinas del bbox inicial + 4 reserva en fila
  dentro de la central.

✅ **Modelo "DAR LA CARA" — IMPLEMENTADO (vacas adultas + lobos direccionales):**
- **Vaca adulta:** pasta dispersa (separación + deambular angular firme + valla blanda, **sin
  apiñarse, sin huir**); **encara** al lobo dentro de `r_notice` girando a `turn_rate`; **cono frontal**
  ±`cone_half_angle` lo mantiene a `r_face_safe` (empuje acotado, no salta); **enfriamiento** de giro
  → el flanco queda abierto. Débil = la más LENTA (`cow_speed_jitter`).
- **Lobo direccional con PRESA COMÚN:** la manada fija UNA presa (`pack_prey` = la más rodeada =
  min dist al centroide de lobos; lentitud emergente) y la **mantiene** (commitment con histéresis:
  abandona solo si se refugia o escapa > `prey_abandon_dist`). **Respeta el cono** (circula
  manteniendo `r_face_safe`) y **cierra por el flanco/grupa**; **lobo solo NO ataca** (standoff
  `r_standoff`, sin fijar presa); ≥ `n_min_adult`=2 → manada flanquea; repulsión → **pincer**.
  **Muerte por flanqueo**: ≥ `n_min_adult` lobos a la vez en `capture_radius` y fuera del cono.
- **Instrumentación de #3** (`_instrument_flanking`): lobos en `capture_radius`, flanqueadores válidos,
  primer quórum→muerte, desglose de toques, y nº de vacas atacadas a la vez (coordinación).
- **Inercia** en vaca y lobo (velocidad en el estado; bandera #1 avanzada) → movimiento **firme**.
- **Zonas prohibidas:** clamp geométrico por paso fuera de establo/central (NO navegación).
- **Verificado (`face_check.py`):** lobo solo = **0 muertes**; manada = **muere** (presa fijada) con
  ≥2 flanqueadores; **coordinación** ~1 vaca a la vez, **re-fijaciones≈0**; **#3 quórum→muerte 84/84**;
  tembleque bajo (~0.10 rad/paso); **tasa 84%** sin drones; guardia limpia; reproducible.
- *(Descartado el modelo de apiñamiento/Muro-pounce: el huddle se tragaba a la rezagada. Parámetros
  del modelo viejo —`k_cohesion_*`, `r_alarm/r_calm`, `d_safe`, `pounce_*`— quedan **deprecados pero
  aceptados** para no romper baseline.py v1; ignorados en la dinámica.)*

🧊 **Baseline del mundo CONGELADO (`baseline.py`):** tras calibrar vacas + lobo, se fija el
adversario (config + 100 seeds) para que FSM y MARL se midan contra lo mismo.
- **Métrica de referencia (sin drones):** `predation = 49/100 = 49.0%` (Wilson 95% IC 39.4–58.7%).
  Es lo que los coordinadores deben **mejorar** (bajar la depredación).
- ⚠️ El baseline v1 (49%) era del **modelo de apiñamiento**, ahora **DESCARTADO** por el modelo
  "dar la cara". v1 ya no aplica (su self-check deriva a propósito; mide ~72% con los kwargs viejos
  ignorados). Se **re-congela como v2** tras la escolta, con la dinámica vaca/lobo definitiva.
- La batería es **ortogonal** (qué drones hay disponibles, no la dinámica vaca/lobo) → no mueve el
  baseline. busca-huecos/amago son adversarios posteriores de la escalera, no este baseline.
- ⚠️ NO tocar estos parámetros una vez empiece la comparación; si se recalibra, re-medir ambas ramas.

🔋 **Batería + cola de carga — IMPLEMENTADO** (`_init_battery`/`_step_battery`, `battery_check.py`):
régimen permanente 4 activos / 2 cargando / 2 listos, relevos escalonados (~1 cada 125 s, 0
simultáneos), invariante "4 puestos siempre cubiertos", reproducible, **baseline intacto (49%)**.
Automático por umbral; arrays de batería paralelos a posiciones; hooks para persecución
(`battery_activity`) / travel-time (`relay_travel_time`) / dron tirado (`drone_stranded`). Sin
movimiento de drones todavía (el relevo es un swap de puesto instantáneo).

---

## 10. 🚩 Banderas levantadas / pendientes para después

> Lista deliberada de cosas aparcadas, para no perderlas.

1. 🟡 **Velocidad en el estado (PARCIAL).** Ya está en **vacas y lobos** (inercia → movimiento
   firme, `cow_vel`/`wolf_vel`). Falta para los **drones** cuando llegue su dinámica real (inercia,
   límites de aceleración).
2. **Altura/z como estado.** Conceptual ahora; **añadir al modelar el cono de visión de la
   cámara** (más altura = más área, peor resolución = el compromiso de detección de objetos
   pequeños, donde YOLO26 con su STAL viene bien).
3. ✅ **RESUELTA — Límite provisional de las vacas.** El clamp duro al spawn se ha sustituido por
   la **valla blanda** (fuerza de retorno hacia la zona de pasto) + cohesión. Contención dura solo
   en límites reales (parcela + establo/central, reutilizando el clamp de exclusión existente).
4. **Variedad de escenarios para el MARL.** El spawn de las vacas es fijo `(0.25W, 0.75H)` y los
   lobos entran por un lado aleatorio. **Aleatorizar también el spawn del rebaño** (y consolidar
   variedad de ataques) para que la política **no memorice** "el ataque viene de tal sitio". Para
   la fase de entrenamiento, no antes.
5. **Zonas prohibidas del lobo.** Ya implementadas como clamp, pero **cobran sentido real en la
   escolta** (cuando el lobo persiga a las vacas hacia el establo central). Enlaza con "lobos
   fuera del recinto" del criterio de éxito.
6. **Disuasión con habituación.** No implementada. El ladrido sube la `d_safe` efectiva del lobo;
   el efecto **decae con el uso repetido**. Es lo que hace que la estrategia sea "ganar tiempo
   para escoltar", no "ladrar para siempre".
7. **Batería: coste de persecución (HOOK puesto).** El subsistema base ya está (§4.3); falta el
   coste extra al perseguir. Hook listo: `battery_activity` multiplica el drenaje (1.0 = patrulla).
   Con movimiento, perseguir gastará más y el dron no debe comprometerse a una persecución que no
   pueda costear (proteger reserva de retorno). El negativo por "dron tirado" (`drone_stranded`,
   flag preparado) se activa cuando haya travel-time.
8. **Alerta como acción aprendible.** En la v1 la alerta es **automática por umbral**. Dejar que
   la política aprenda *cuándo/qué* comunicar es **extensión avanzada** (y zona inestable del
   MARL: premiar/penalizar el avisar directamente puede enseñar a callar amenazas — ir con pies
   de plomo). El **umbral de alerta** es un parámetro de diseño de primer orden: en la FSM se
   fija a mano; el MARL puede aprenderlo (resultado bonito para la comparación).
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
    Tasa 83% sin drones. Ver §4.1/§4.2.
12. **Pure pursuit y filtro de estimación del lobo.** Reutilizar el pure pursuit (de Robots) en la
    capa de guiado; implementar un **EKF/filtro de partículas** para estimar la trayectoria del
    lobo a partir de detecciones ruidosas (análogo al MCL de la asignatura — el GPS da la
    posición propia, así que la estimación es del *lobo*, no del ego).
13. **Tests del "juez".** Conviene añadir tests que fuercen cada terminal (vaca en zona segura →
    success; lobo encima de vaca → predation; agotar tiempo → timeout). Verificar el terminal
    antes de construir comportamientos encima.

---

## 11. SIGUIENTE PASO

**Adversario vaca+lobo cerrado con el modelo "dar la cara".** Las adultas plantan cara, el lobo
flanquea, la regla de nº mínimo distingue lobo-solo (no mata) de manada (mata a la débil), y el
movimiento es firme (inercia). Verificado en `face_check.py`; tasa 83% sin drones (no perseguida).

**Siguiente paso = TERNEROS + defensores** (el paso que se aparcó aquí a propósito): añadir terneros
(presa preferente: "los lobos van siempre al ternero") y vacas **defensoras** que se interponen entre
el ternero y el lobo. Es donde el "dar la cara" gana sentido de grupo (la madre/defensora encara, el
ternero detrás). Luego: escolta / capa de movimiento (pure pursuit, collares al refugio, drones
apantallando; activa los hooks de batería) → percepción (sustituto) → coordinador clásico → MARL →
comparación. **Re-congelar baseline v2** cuando la dinámica vaca/lobo quede definitiva (tras la escolta).

*(Decisiones de diseño tomadas en este paso, a confirmar: `n_min_adult`=2, `cone_half_angle`=45°,
`r_notice`=20, `r_face_safe`=6, `r_standoff`=12, `face_cooldown`=1 s, `turn_rate`=2 rad/s, inercia
vaca/lobo 0.25/0.35, deambular angular `wander_drift`=0.12 rad/paso. Se conservó la repulsión entre
lobos para el pincer. La tasa 83% se aterriza en v2 con terneros/defensores + drones.)*

---

## 12. Referencias

- **Muro, C., Escobedo, R., Spector, L., Coppinger, R.P. (2011).** Wolf-pack (Canis lupus)
  hunting strategies emerge from simple rules in computational simulations. *Behavioural
  Processes*, 88(3), 192–197.
- **Janeiro-Otero, A., et al. (2020).** Grey wolf (Canis lupus) predation on livestock in
  relation to prey availability. (Selección de presa / depredación de ganado.)
- **Madden, J.D., Arkin, R.C., MacNulty, D.R. (2011).** Multi-robot system based on model of wolf
  hunting behavior. (Robótica inspirada en Muro.)
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
