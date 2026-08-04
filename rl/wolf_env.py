"""wolf_env.py — Envoltorio Gymnasium SINGLE-AGENT del paquete de lobos (WolfPackEnv).

Un cerebro ÚNICO mueve a TODOS los lobos contra la BARRERA REACTIVA congelada (v2.4): cada
episodio construye un `World` con `wolf_controller=RLWolfController(...)` inyectado y el
`ReactiveCoordinator` moviendo los drones POR DENTRO (el env llama al coordinador y pasa sus
waypoints a `world.step`, exactamente como hace `baseline.run_episode_metrics`). PettingZoo
queda para la fase de drones.

Decisiones (documentadas también en DISEÑO.md):
- **Acción**: `Box(-1, 1, (10,))` = velocidad deseada por SLOT de lobo (5 slots × 2), decidida
  cada `frame_skip=5` pasos de física (0.5 s) y MANTENIDA entre decisiones. Se desnormaliza
  ×`wolf_speed` y el CAP por norma vive en el controlador (frontera). Slots de lobos
  inexistentes (n_wolves < 5) se ignoran.
- **Recompensa RALA**: +1 por res matada (Δ `world.n_depredadas` acumulado en los pasos del
  frame-skip), compartida por el paquete. Sin castigo por tiempo ni por vacas a salvo.
- **SHAPING POR POTENCIAL (plan B, opcional — `shaping=True` para ENTRENAR, default OFF)**:
  r = r_kills + r_shape con r_shape = γ·Φ(s′) − Φ(s) (Ng et al. 1999: no cambia la política
  óptima SI γ es EXACTAMENTE el del PPO — por eso entra como parámetro `shaping_gamma`).
  Φ(s) = −β · mean_i dist(lobo_i, presa designada) / D_norm, con la presa de la MISMA regla
  ternero-primero que escribe el controlador (RLWolfController._write_prey, un solo criterio
  de verdad; aquí se aplica con GUARDAR/RESTAURAR — la física lee pack_prey del paso anterior
  y NO debe ver el cálculo de la frontera), media sobre los lobos PRESENTES y D_norm = la
  diagonal del campo (≈424 m) → Φ ∈ (−β, 0]. Sin res cazable (coasting) → Φ = 0. s y s′ son
  las FRONTERAS del step del env (tras el frame-skip), no los pasos internos de física.
  `info` lleva las componentes (`r_kills`, `r_shape`) y, al terminar, los totales del episodio
  (`ep_kills`, `ep_shape`). La EVALUACIÓN (eval_wolves / eval ligera) va por el World directo
  y puntúa muertes: NUNCA ve el shaping. Con `shaping=False` el env es BIT A BIT el de run01
  (verificado en rl_env_check test 8).
- **DIETA DE DOS FRENTES (run08, `train_two_front_rate` — SOLO entrenamiento)**: fracción de
  episodios FORZADA a 2 subgrupos por muestreo por RECHAZO del spawn real v3.4 (semillas
  re-sorteadas hasta que el spawn natural da el nº de grupos pedido; nada sintético — ni
  posiciones ni masas; el cebo scriptado queda exactamente como lo produce el mundo). La EVAL
  no pasa por aquí: sigue midiendo el mundo real (~29% de 2 frentes).
- **terminated/truncated**: los del mundo (success/predation ↔ resolución; timeout ↔ tiempo).
- **Episodios**: kinds ~uniforme entre `kinds` (def. lobos/mixto ~50/50). NUNCA 'corzos'
  (sin lobos no hay nada que aprender). Cada `reset()` toma semilla NUEVA de una secuencia
  propia del env (recuerda: `World.reset(seed=None)` REPITE el mismo episodio; aquí SIEMPRE
  semilla fresca). Mismo seed del env ⇒ misma secuencia de episodios (determinista,
  verificado en rl_env_check).
- **MODO RESIDUAL (`residual=True`, run04 — RPL, ver rl/residual_wolf_controller.py):** el
  controlador es `ResidualWolfController` (el SCRIPTADO vivo dentro, con SU presa/histéresis/
  coasting); la acción del env es la CORRECCIÓN δ normalizada (`Box(-1,1,(10,))` ×
  `residual_scale`, def. wolf_speed — autoridad plena) y la obs son las 132 (122 + la acción
  del script normalizada, la pista de su estado oculto). Recompensa como siempre (para run04:
  RALA PURA — con el script dentro ya hay ~2.8 muertes/episodio de señal; shaping off).
  Con δ≡0 el env ES el scriptado puro (test 9).

La OBSERVACIÓN (layout, normalizaciones e instante de muestreo) vive en `rl/obs.py` —
la ÚNICA fuente de verdad, compartida con el controlador de evaluación
(`rl/policy_wolf_controller.py`); equivalencia verificada en rl_env_check test 7. Este
módulo re-exporta las constantes del layout por compatibilidad.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np

from coordinators import ReactiveCoordinator
from world import World
from baseline import CONFIG_V2

from rl.rl_wolf_controller import RLWolfController
from rl.residual_wolf_controller import RESIDUAL_OBS_SIZE, ResidualWolfController
from rl.obs import (build_obs,  # noqa: F401 — re-export: el layout vive en rl/obs.py
                    CALF_FEAT, COW_FEAT, DRONE_FEAT, GLOBAL_FEAT, N_CALF_SLOTS, N_COW_SLOTS,
                    N_DRONE_SLOTS, N_WOLF_SLOTS, OBS_SIZE, OFF_CALF, OFF_COW, OFF_DRONE,
                    OFF_GLOBAL, OFF_WOLF, WOLF_FEAT)

VALID_KINDS = ("lobos", "mixto")    # NUNCA 'corzos' (sin lobos no hay nada que aprender)


class WolfPackEnv(gym.Env):
    """Paquete de lobos (cerebro único) contra la barrera reactiva congelada. Ver módulo."""

    metadata = {"render_modes": []}

    def __init__(self, kinds: tuple[str, ...] = ("lobos", "mixto"), frame_skip: int = 5,
                 seed: int | None = None, config: dict | None = None,
                 shaping: bool = False, shaping_beta: float = 1.0, shaping_gamma: float = 0.999,
                 residual: bool = False, residual_scale: float | None = None,
                 curriculum_separation_deg: float | None = None, curriculum_min_mass: int = 0,
                 train_two_front_rate: float | None = None):
        super().__init__()
        kinds = tuple(kinds)
        if not kinds or any(k not in VALID_KINDS for k in kinds):
            raise ValueError("kinds debe ser un subconjunto no vacío de %r (nunca 'corzos'); recibido %r"
                             % (VALID_KINDS, kinds))
        if frame_skip < 1:
            raise ValueError("frame_skip >= 1")
        if shaping and not (shaping_beta > 0.0 and 0.0 < shaping_gamma <= 1.0):
            raise ValueError("shaping requiere beta > 0 y gamma en (0, 1] (el MISMO gamma del PPO)")
        self._kinds = kinds
        self._frame_skip = int(frame_skip)
        self._config = dict(CONFIG_V2 if config is None else config)
        self._shaping = bool(shaping)
        self._shaping_beta = float(shaping_beta)
        self._shaping_gamma = float(shaping_gamma)   # DEBE ser el gamma del PPO (inocuidad de Ng et al.)
        self._phi_prev = 0.0
        self._d_norm = 1.0                           # diagonal del campo (se fija en reset, con el World)
        # CURRÍCULO DE SEPARACIÓN DE SPAWN (SOLO ENTRENAMIENTO; ver set_curriculum + _apply_curriculum):
        # override del spawn grouped que fuerza la separación angular entre los 2 subgrupos (y, con
        # min_mass>0, que cada frente tenga masa >= min_mass forzando wolves_min). NO toca el mundo
        # congelado ni la EVALUACIÓN (que va por baseline.build_world, spawn grouped normal de v2.7).
        # Usa un RNG PROPIO (no el substream congelado) -> la eval no se ve afectada.
        self._curric_sep_deg = curriculum_separation_deg   # None => spawn grouped normal (nivel 4)
        self._curric_min_mass = int(curriculum_min_mass)
        self._curric_rng = np.random.default_rng(None if seed is None else seed + 7_000_003)
        # DIETA DE DOS FRENTES (run08, SOLO ENTRENAMIENTO): fuerza que una fracción
        # `train_two_front_rate` de los episodios tenga 2 SUBGRUPOS de spawn, por MUESTREO POR
        # RECHAZO del spawn REAL v3.4 (se sortean semillas de mundo hasta que el spawn natural
        # produce el nº de grupos pedido) — NO se sintetizan posiciones (a diferencia del
        # currículo de separación): ángulos, masas (cebo 1 / asalto n−1, wolf_decoy_size=1) y
        # toda la maquinaria del cebo v3.4 quedan EXACTAMENTE como los produce el mundo; solo
        # cambia la FRECUENCIA con que el entrenamiento los ve (~29% natural → rate). La EVAL
        # (eval_wolves/cebo_diag/eval ligera, vía baseline.build_world) NO usa este env: mide
        # siempre el mundo real al ~29%. RNG PROPIO (seed+11_000_003) → determinista por env.
        if train_two_front_rate is not None and not (0.0 < train_two_front_rate < 1.0):
            raise ValueError("train_two_front_rate debe estar en (0,1) o ser None")
        self._diet_rate = train_two_front_rate
        self._diet_rng = np.random.default_rng(None if seed is None else seed + 11_000_003)
        # Secuencia PROPIA de semillas de episodio (independiente de self.np_random de gym).
        self._seed_rng = np.random.default_rng(seed)
        self._residual = bool(residual)
        self._residual_scale = residual_scale        # None => wolf_speed del mundo (autoridad plena)
        if self._residual:
            self._controller = ResidualWolfController(N_WOLF_SLOTS, residual_scale=residual_scale)
            obs_size = RESIDUAL_OBS_SIZE             # 132 = 122 + pista del script
        else:
            self._controller = RLWolfController(N_WOLF_SLOTS)
            obs_size = OBS_SIZE
        self._world: World | None = None
        self._coordinator: ReactiveCoordinator | None = None

        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(N_WOLF_SLOTS * 2,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(obs_size,), dtype=np.float32)

    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:                      # re-sembrar la secuencia de episodios (API gym)
            self._seed_rng = np.random.default_rng(seed)
        world_seed = int(self._seed_rng.integers(0, 2**31 - 1))   # SIEMPRE semilla fresca
        kind = self._kinds[int(self._seed_rng.integers(len(self._kinds)))]

        self._controller.reset()
        cfg = self._config
        if self._curric_sep_deg is not None and self._curric_min_mass > 0:
            # Nivel con masa mínima por frente: fuerza wolves_min >= 2·min_mass (cada frente letal).
            cfg = dict(cfg)
            wmax = cfg.get("wolves_max", 5)
            cfg["wolves_min"] = min(max(cfg.get("wolves_min", 1), 2 * self._curric_min_mass), wmax)
        if self._diet_rate is not None:
            # DIETA (run08): decide si este episodio debe ser de 2 frentes y RE-SORTEA la semilla
            # de mundo (spawn real, rechazo) hasta conseguirlo. Sondas SIN controlador (el spawn
            # solo depende de la semilla); el mundo definitivo se construye una vez, abajo.
            want_two = bool(self._diet_rng.random() < self._diet_rate)
            for _ in range(80):                       # P(fallar 80 sorteos) < 1e-11 con p>=0.29
                probe = World(seed=world_seed, episode_kind=kind, **cfg)
                if (len(probe.wolf_group_sizes) == 2) == want_two:
                    break
                world_seed = int(self._seed_rng.integers(0, 2**31 - 1))
        self._world = World(seed=world_seed, episode_kind=kind,
                            wolf_controller=self._controller, **cfg)
        if self._curric_sep_deg is not None:
            self._apply_curriculum(self._world)          # override SOLO de entrenamiento (eval no lo usa)
        self._coordinator = ReactiveCoordinator(self._world)
        self._ep_kills = 0.0
        self._ep_shape = 0.0
        if self._shaping:
            self._d_norm = float(np.hypot(self._world.W, self._world.H))   # diagonal (≈424 m)
            self._phi_prev = self._phi()                                   # Φ(s_0)
        info = {"episode_kind": kind, "world_seed": world_seed,
                "n_wolves": int(self._world.n_wolves), "n_calves": int(self._world.n_calves),
                "two_front": bool(len(self._world.wolf_group_sizes) == 2)}
        return self._obs(), info

    # ------------------------------------------------------------------ #
    def set_curriculum(self, separation_deg: float | None, min_mass: int = 0) -> None:
        """Cambia el nivel del currículo EN CALIENTE (lo llama el entrenador vía
        `venv.env_method` en las fronteras de nivel). Toma efecto en el PRÓXIMO reset()
        (episodio). separation_deg=None => spawn grouped normal de v2.7 (nivel 4, sin override)."""
        self._curric_sep_deg = None if separation_deg is None else float(separation_deg)
        self._curric_min_mass = int(min_mass)

    def _apply_curriculum(self, w) -> None:
        """CURRÍCULO (solo entrenamiento): re-coloca los lobos en 2 SUBGRUPOS a
        `_curric_sep_deg` grados de separación, con reparto BALANCEADO (ambos >= 1; con
        wolves_min forzado, >= min_mass). Anclas al BORDE como el spawn real (misma distancia);
        grupo 1 en el ángulo de spawn PRIMARIO del mundo (`wolf_spawn_angle`, del stream
        principal), grupo 2 a +separación. Dispersión gaussiana `wolf_spawn_dispersion` con el
        RNG PROPIO del currículo (no el substream congelado -> eval intacta). Solo posiciones y
        velocidad; `pack_prey` (fijado en reset por las vacas) NO se toca."""
        n = int(w.n_wolves)
        if n < 2:
            return                                        # no se puede partir (raro con wolves_min forzado)
        sep = np.radians(self._curric_sep_deg)
        center = np.array([w.W / 2.0, w.H / 2.0])

        def anchor(a):
            d = np.array([np.cos(a), np.sin(a)])
            t = min((w.W / 2.0) / max(abs(d[0]), 1e-9), (w.H / 2.0) / max(abs(d[1]), 1e-9))
            return center + d * t                         # misma regla de distancia (borde) que el spawn

        a1 = float(w.wolf_spawn_angle)
        a2 = a1 + sep
        an1, an2 = anchor(a1), anchor(a2)
        k = n // 2                                        # grupo 2 = k ÚLTIMOS índices; grupo 1 = n-k (balanceado)
        disp = w.wolf_spawn_dispersion
        pts = w.wolves.copy()
        pts[: n - k] = an1 + self._curric_rng.normal(0.0, disp, size=(n - k, 2))
        pts[n - k:] = an2 + self._curric_rng.normal(0.0, disp, size=(k, 2))
        w._clip_to_parcel(pts)                            # dentro de la parcela (como el spawn real)
        w.wolves = pts
        w.wolf_vel[:] = 0.0
        w.wolf_group_sizes = [n - k, k]
        w.wolf_spawn_angles = [float(a1 % (2 * np.pi)), float(a2 % (2 * np.pi))]

    def step(self, action):
        w = self._world
        a = np.clip(np.asarray(action, dtype=np.float32).reshape(N_WOLF_SLOTS, 2), -1.0, 1.0)
        if self._residual:
            scale = self._residual_scale if self._residual_scale is not None else w.wolf_speed
            self._controller.set_delta(a * scale)      # δ mantenida; el script recalcula cada paso
        else:
            self._controller.set_action(a * w.wolf_speed)   # desnormaliza; el cap por norma, en el controlador

        deaths0 = w.n_depredadas
        terminated = truncated = False
        info: dict = {}
        for _ in range(self._frame_skip):               # la acción se mantiene entre decisiones
            waypoints = self._coordinator.act(w.get_observation())   # la barrera se recoloca cada paso
            _obs, _r, terminated, truncated, info = w.step(waypoints)
            if terminated or truncated:
                break
        r_kills = float(w.n_depredadas - deaths0)       # RALA: +1 por res matada en el tramo
        if self._shaping:
            phi = self._phi()                           # Φ(s′), en la FRONTERA (tras el frame-skip)
            r_shape = self._shaping_gamma * phi - self._phi_prev
            self._phi_prev = phi
        else:
            r_shape = 0.0
        self._ep_kills += r_kills
        self._ep_shape += r_shape
        info["r_kills"] = r_kills                       # componentes por separado (logging/tests)
        info["r_shape"] = r_shape
        if terminated or truncated:
            info["ep_kills"] = self._ep_kills           # totales del episodio (TrainLog los recoge)
            info["ep_shape"] = self._ep_shape
        return self._obs(), r_kills + r_shape, terminated, truncated, info

    # ------------------------------------------------------------------ #
    def _phi(self) -> float:
        """Potencial Φ(s) = −β · mean_i dist(lobo_i, presa designada) / D_norm ∈ (−β, 0].

        La presa designada la fija la MISMA regla ternero-primero del controlador
        (RLWolfController._write_prey — un solo criterio de verdad), re-aplicada sobre el
        estado de la frontera con GUARDAR/RESTAURAR: la física lee `pack_prey` del final del
        paso ANTERIOR (las vacas se actualizan antes que los lobos) y no debe ver este
        cálculo. Sin res cazable (coasting) → Φ = 0."""
        w = self._world
        if w.n_wolves == 0 or w._targets_exhausted():
            return 0.0
        saved = (w.pack_prey, w.pack_prey_kind)
        RLWolfController._write_prey(w)
        prey_idx, prey_kind = w.pack_prey, w.pack_prey_kind
        w.pack_prey, w.pack_prey_kind = saved
        if prey_idx < 0:
            return 0.0
        prey = w.calves[prey_idx] if prey_kind == "calf" else w.cows[prey_idx]
        d_mean = float(np.linalg.norm(w.wolves - prey, axis=1).mean())
        return -self._shaping_beta * d_mean / self._d_norm

    # ------------------------------------------------------------------ #
    def _obs(self) -> np.ndarray:
        """Delegado al builder COMPARTIDO (rl/obs.py) — única fuente de verdad del layout.
        En modo residual, el controlador añade la pista del script (132; misma frontera)."""
        if self._residual:
            return self._controller.residual_obs(self._world)
        return build_obs(self._world)
