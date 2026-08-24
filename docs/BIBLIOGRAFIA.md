# BIBLIOGRAFIA.md — Referencias del proyecto escolta (drones / lobos / vacas)

Toda decisión "porque lo dice un paper" entra AQUÍ **antes** de implementarse, con su
"se usa para". Las entradas provienen de este archivo o de DISEÑO.md §12 (consolidadas aquí).

## Fase RL (lobos y, después, drones)

- **Silver, T., Allen, K. R., Tenenbaum, J. B., & Kaelbling, L. P. (2018).** *Residual Policy
  Learning.* arXiv:1812.06298. — **Se usa para:** la arquitectura de **run04**: el scriptado
  (política a mano, no diferenciable) vive dentro del controlador y la red aprende solo una
  corrección aditiva δ con RL sin modelo; explica por qué el RL desde cero fracasa en horizonte
  largo / recompensa rala (runs 01–03) y por qué el residuo MEJORA controladores a mano en vez
  de reaprenderlos.
- **Grasp and Motion Planning for Dexterous Manipulation for the Real Robot Challenge (2021).**
  arXiv:2101.02842. *(verificar autores al citar en la memoria)* — **Se usa para:** el
  entrenamiento en dos fases de run04: **fase 1 solo-crítico** (política congelada mientras el
  value function aprende cuánto vale el controlador base) e **inicialización a cero** de la
  última capa de la media (δ inicial ≡ 0) con σ inicial pequeña.
- **Uchendu, I., et al. (2023).** *Jump-Start Reinforcement Learning.* ICML 2023 (PMLR v202);
  arXiv:2204.02372. — **Se usa para:** alternativa CONSIDERADA Y DESCARTADA para el arranque
  desde el scriptado (guía por roll-in del experto en vez de residuo aditivo); se descartó
  porque el residual conserva el suelo del script en TODO momento (guardia del suelo medible).
- **Residual Policy Gradient: A Reward View of KL-regularized Objective (2025).**
  arXiv:2503.11019. — **Se usa para:** conexión teórica del residual con la regularización KL
  (enlace con el temario de RL del autor); lectura de por qué corregir una política base
  equivale a un objetivo regularizado hacia ella.
- **Ng, A. Y., Harada, D., & Russell, S. (1999).** *Policy invariance under reward
  transformations: theory and application to reward shaping.* ICML. — **Se usa para:** el
  shaping por potencial de run02/run03 (r_shape = γ·Φ(s′) − Φ(s) con el γ EXACTO del agente no
  cambia la política óptima; verificado en rl_env_check test 8).
- **Schulman, J., et al. (2017).** *Proximal Policy Optimization Algorithms.* arXiv:1707.06347.
  — **Se usa para:** el algoritmo de TODOS los runs de lobos (y previsiblemente del MARL).
- **Wei, E., & Luke, S. (2016)** *Lenient Learning in Independent-Learner Stochastic Cooperative
  Games* (JMLR); **Panait, L., Tuyls, K., & Luke, S. (2008)** *Theoretical Advantages of Lenient
  Learners* — y su nombre moderno en **Guo, J., et al. (2024)** *Joint Intrinsic Motivation (JIM)
  for Coordinated Exploration in Multi-Agent Deep RL*, arXiv:2402.03972 (que AJUSTA y mide la
  patología en un entorno sintético). — **Se usa para:** el DIAGNÓSTICO del "valle del cebo" =
  **relative overgeneralization**: la política óptima (cebo coordinado de 2 frentes) da MALA
  recompensa si un solo lobo la intenta, así que PPO se queda en el óptimo local "atacar juntos";
  es la razón de que el cebo no emergiera en 5 campañas. *(autores/venue exactos: verificar al
  citar; ver también arXiv:2411.11099, *Mitigating Relative Over-Generalization in MARL*.)*
- **Bengio, Y., Louradour, J., Collobert, R., & Weston, J. (2009).** *Curriculum Learning.* ICML.
  · **Narvekar, S., et al. (2020).** *Curriculum Learning for Reinforcement Learning Domains: A
  Framework and Survey.* JMLR. — **Se usa para:** el CURRÍCULO de separación de spawn (v2.7): se
  arranca al lobo AL OTRO LADO del valle (cebo casi servido por el spawn: 2 frentes opuestos, ~180°,
  ambos letales) y se endurece por niveles hasta el spawn normal, para que la política CRUCE el valle
  de recompensa en vez de quedarse en el óptimo local. Currículo FIJO por pasos (legible/diagnosticable)
  frente a automático. *(Narvekar et al.: autores completos verificar al citar.)*
- **Vías de RESERVA de EXPLORACIÓN INTRÍNSECA COORDINADA (CONSIDERADAS, NO implementadas — si el
  currículo NO cruza el valle):** **Zheng, L., et al. (2021)** *EMC: Episodic Multi-agent RL with
  Curiosity-Driven Exploration*, arXiv:2111.11032 (NeurIPS) · **Iqbal, S., & Sha, F. (2019)**
  *Coordinated Exploration via Intrinsic Rewards for Multi-Agent RL* *(arXiv id verificar al citar)*
  · **MACE — Xu, H., et al. (2024)** *Settling Decentralized Multi-Agent Coordinated Exploration by
  Novelty Sharing*, arXiv:2402.02097 (AAAI) · **SMMAE — Zhang, S., et al. (2023)** *Self-Motivated
  Multi-Agent Exploration*, arXiv:2301.02083 (AAMAS). — **Se usa para:** dar CURIOSIDAD COORDINADA a
  los lobos (recompensa intrínseca por novedad CONJUNTA) para muestrear la desviación coordinada que
  la exploración gaussiana por-paso no encuentra; sería la vía siguiente si el currículo demuestra que
  "el cebo se aprende con ayuda pero no se forma solo". La otra reserva = control JERÁRQUICO de
  formación (elegir el reparto de frentes como acción de alto nivel). *(autores/venue exactos:
  verificar al citar en la memoria.)*
- **Raffin, A., et al. (2021).** *Stable-Baselines3: Reliable Reinforcement Learning
  Implementations.* JMLR 22(268). — **Se usa para:** la implementación de PPO (política, buffer,
  VecEnv) usada en rl/.
- **Towers, M., et al. (2024).** *Gymnasium.* arXiv:2407.17032. — **Se usa para:** el envoltorio
  single-agent del env de lobos (`WolfPackEnv`) y el env conjunto de drones (`DroneTeamEnv`).
- **Sheikh, H. U., & Bölöni, L. (2020).** *Multi-Agent Reinforcement Learning for Problems with
  Combined Individual and Team Reward.* arXiv:2003.10598 (DE-MADDPG). — **Se usa para:** la
  RECOMPENSA del MARL de drones: componente GLOBAL de equipo (−1/res muerta, compartida) +
  componente LOCAL por dron (disuasión atribuida), el marco "individual + team reward"
  demostrado precisamente en un problema de ESCOLTA DEFENSIVA. Nosotros lo SIMPLIFICAMOS:
  un solo crítico centralizado MAPPO y la componente local sumada a la recompensa del stream
  (sin el doble crítico global/local de DE-MADDPG — descartado por sobre-ingeniería con 4
  agentes; las componentes se registran POR SEPARADO en el log, vigilancia anti-proxy).
- **Sheikh, H. U., & Bölöni, L. (2020).** *Designing a Multi-Objective Reward Function for
  Creating Teams of Robotic Bodyguards Using Deep Reinforcement Learning* / *Defensive Escort
  Teams via Multi-Agent Deep RL.* arXiv:1910.04537. — **Se usa para:** precedente DIRECTO del
  problema (equipo que aprende la FORMACIÓN alrededor de un bien a proteger frente a amenazas
  móviles) — el análogo publicado de nuestra barrera aprendida. *(título exacto: verificar al
  citar en la memoria)*
- **Foerster, J., Farquhar, G., Afouras, T., Nardelli, N., & Whiteson, S. (2018).**
  *Counterfactual Multi-Agent Policy Gradients (COMA).* AAAI 2018; arXiv:1705.08926. — **Se usa
  para:** referencia de CREDIT ASSIGNMENT contrafactual — CONSIDERADA Y DESCARTADA por
  sobre-ingeniería: con 4 puestos y la componente local de disuasión ya hay señal por-agente;
  la ablación con/sin componente local es el sustituto barato del contrafactual.
- **Wolpert, D. H., & Tumer, K. (2002).** *Optimal Payoff Functions for Members of Collectives.*
  (difference rewards). — **Se usa para:** la idea madre del crédito por diferencia ("¿qué
  cambia si este agente no actúa?"); mismo veredicto que COMA: descartada, la registra la
  bibliografía como contexto del diseño de recompensa. *(año/venue: verificar al citar)*
- **Sunehag, P., et al. (2018).** *Value-Decomposition Networks (VDN).* arXiv:1706.05296 ·
  **Rashid, T., et al. (2018).** *QMIX.* arXiv:1803.11485. — **Se usa para:** familia de
  DESCOMPOSICIÓN DE VALOR del CTDE — descartadas (son para Q-learning discreto; nuestro CTDE va
  por crítico centralizado de política, MAPPO — ver Yu et al. 2022 abajo, ya consolidado).

## Fase de mundo (consolidadas desde DISEÑO.md §12; URLs pendientes de verificación)

- **Muro, C., Escobedo, R., Spector, L., Coppinger, R.P. (2011).** *Wolf-pack (Canis lupus)
  hunting strategies emerge from simple rules in computational simulations.* Behavioural
  Processes, 88(3), 192–197. — **Se usa para:** el modelo de caza del paquete (reglas simples:
  acercarse + mantener distancia + flanquear) que inspira el scriptado.
- **Janeiro-Otero, A., et al. (2020).** *Grey wolf (Canis lupus) predation on livestock in
  relation to prey availability.* — **Se usa para:** selección de presa / depredación de ganado.
- **Madden, J.D., Arkin, R.C., MacNulty, D.R. (2011).** *Multi-robot system based on model of
  wolf hunting behavior.* — **Se usa para:** precedente de robótica inspirada en Muro.
- **ICWDM (Internet Center for Wildlife Damage Management), "Wolf Damage Identification".** —
  **Se usa para:** el ataque se concentra en grupa/flancos/cuartos traseros y hay preferencia
  por terneros → fundamenta el ataque por flanco y el ternero como objetivo blando (selección
  de crías).
- **BeefResearch.ca, "Cows & Wolves"** (collares GPS en Alberta). — **Se usa para:** composición
  de presas (~40% terneros / 40% añojos / <20% adultas) → presencia y peso de los terneros.
- **Wolf Song of Alaska** (caza en manada de presa grande). — **Se usa para:** rara vez toda la
  manada toca a la presa → la regla de quórum `n_min_adult` (basta un subconjunto flanqueando).
- **Criterio DRI de Johnson** (Detect/Recognize/Identify, resolución angular). — **Se usa
  para:** `r_detect`=100 m (~8–13 px sobre un lobo de ~1,2 m: reconocer que hay algo) y
  `r_confirm`=40 m (~130 px: identificar la especie) de la fase detectar→confirmar.
- **Hazing de depredadores y HABITUACIÓN a disuasores estáticos** (base conceptual del susto
  v2.3→v2.4: lo que disuade es el disuasor ACTIVO que se echa encima; los depredadores se
  habitúan a postes/luces fijas). — **Se usa para:** el SUSTO POR MOVIMIENTO de v2.4.
  *(Cita formal pendiente — en DISEÑO está como razonamiento de diseño, sin fuente puntual.)*
- **Distancia de inicio de fuga (FID, Flight Initiation Distance) en cánidos ante amenazas que
  se aproximan** (ante una amenaza que se ACERCA el lobo huye a una distancia media del orden de
  ~100 m, rango amplio ~17–310 m; a la vez, un disuasor ESTÁTICO al que el animal se habitúa aún
  impone una zona mínima de incomodidad que NO cruza si lo tiene encima). — **Se usa para:** el
  SUSTO DE DOS RADIOS de v2.7: expulsión por movimiento (radio grande, la huida de v2.4) + PARED
  BLANDA estática (radio pequeño `STATIC_DETER_RADIUS`, mínimo que no se cruza ni con el dron
  quieto; escalado al campo 300×300 — un radio real de ~100 m haría a los drones invencibles).
  Reconcilia habituación (poste a distancia = ignorable) con obstáculo (poste encima = no se
  cruza). *(Cifras FID de la literatura de comportamiento; cita puntual PENDIENTE de verificar
  al pasar a la memoria — en DISEÑO como razonamiento de diseño con el rango numérico.)*
- **Vídeo de ataque real de lobos a ganado.** — **Se usa para:** verosimilitud del
  comportamiento del paquete. *(Referencia/URL pendiente de recuperar — no consta en DISEÑO.md.)*
- **Yu, C., et al. (2022).** *The surprising effectiveness of PPO in cooperative multi-agent
  games (MAPPO).* — **Se usa para:** candidato de algoritmo para la fase MARL de drones.
- **Terry, J., et al. (2021).** *PettingZoo: Gym for multi-agent reinforcement learning.* —
  **Se usa para:** API multi-agente prevista para la fase de drones.
- **Bettini, M., Prorok, A., Moens, V. (2024).** *BenchMARL: Benchmarking Multi-Agent
  Reinforcement Learning (TorchRL).* — **Se usa para:** referencia de benchmarking MARL.
- **Strömbom, D., et al. (2014).** Modelo matemático de *shepherding*. — **Se usa para:**
  reserva conceptual para la escolta/guiado.
- **Halter (Nueva Zelanda).** Collares GPS de *virtual fencing / guided herding*. — **Se usa
  para:** verosimilitud de los collares/guiado del rebaño como infraestructura.

## Pendiente — fase percepción

- **Ultralytics YOLO26** (detección en tiempo real, end-to-end / sin NMS, orientada a drones y
  robótica, asignación consciente de objetos pequeños — STAL). — **Se usará para:** el
  clasificador real que sustituya al ORÁCULO de `r_confirm`. *(Anotar la VERSIÓN exacta al
  usarlo.)*

---

**Regla:** toda decisión "porque lo dice un paper" entra aquí **ANTES** de implementarse;
al pasar cualquier entrada a la memoria final, **verificar autores/año contra arXiv/DOI**
(varias entradas de la fase de mundo vienen de DISEÑO.md sin URL y están marcadas como
pendientes de verificación).
