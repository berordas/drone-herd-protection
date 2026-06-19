"""
world.py — Núcleo de la simulación.

El World es la ÚNICA fuente de verdad del estado y de la dinámica. NO depende de
matplotlib, PettingZoo ni ROS: esos serán adaptadores finos por encima. Aquí solo
hay NumPy.

Convenciones de diseño:
  - Unidades SI: posiciones en metros, tiempo en segundos.
  - El suelo es un plano 2D (x, y). Es una sim 2.5D porque los drones "vuelan",
    pero la altura aún NO es estado (no influye en ninguna dinámica de esta versión).
  - Cada grupo de entidades es un array de NumPy (N, 2) -> vectorizable y trivial
    de trocear por agente cuando llegue el MARL.
  - Toda la aleatoriedad pasa por self.rng -> episodios reproducibles con seed.

FASE 1: dinámicas deliberadamente tontas (vacas en paseo aleatorio acotado, lobos
yendo recto al centroide, drones quietos). Sin batería, sin caza de Muro, sin miedo.
"""

from __future__ import annotations
import numpy as np


class World:
    def __init__(
        self,
        n_active_drones: int = 4,
        n_reserve_drones: int = 4,
        n_cows: int = 6,
        wolves_min: int = 1,            # nº de lobos sorteado en reset() ...
        wolves_max: int = 5,            # ... entre [wolves_min, wolves_max]
        parcel_size: tuple[float, float] = (100.0, 100.0),
        safe_radius: float | None = None,     # establo (centro del campo)
        station_radius: float | None = None,  # estación central de carga
        station_gap: float | None = None,     # separación establo<->estación
        station_dir: tuple[float, float] = (0.0, 1.0),  # dirección estación respecto al establo
        cow_spawn: tuple[float, float] | None = None,   # punto de aparición del rebaño (esquina)
        cow_spread: float | None = None,      # radio del cluster de vacas (límite provisional)
        dt: float = 0.1,
        max_steps: int = 600,
        cow_step: float = 1.5,        # m/s, magnitud del paseo aleatorio de las vacas
        drone_speed: float = 6.0,     # m/s, escala/tope de las acciones de los drones
        capture_radius: float | None = None,  # m, a qué distancia MATA (default derivado de geometría)
        # --- Modelo de caza de Muro et al. (2011) ---
        wolf_speed: float = 4.0,                       # m/s del lobo (lejos de la presa)
        wolf_speed_near: float | None = None,          # m/s cerca de la presa (None -> = wolf_speed)
        d_safe: float | None = None,                   # distancia de seguridad lobo-presa
        wolf_repulsion_radius: float | None = None,    # alcance de la repulsión entre lobos
        wolf_repulsion_strength: float = 1.0,          # peso del término de repulsión
        wolf_engage_band: float | None = None,         # margen sobre d_safe para contar como "en el anillo"
        seed: int | None = None,
    ):
        # --- configuración (inmutable durante el episodio) ---
        self.n_active = n_active_drones
        self.n_reserve = n_reserve_drones
        self.n_drones = n_active_drones + n_reserve_drones
        self.n_cows = n_cows
        self.wolves_min = wolves_min
        self.wolves_max = wolves_max
        self.W, self.H = parcel_size
        m = min(self.W, self.H)  # escala de referencia para los defaults (sin números mágicos)

        # Geometría central: establo en el centro del campo; estación pegada a su
        # borde pero SIN solaparse (son cosas distintas).
        self.safe_radius = safe_radius if safe_radius is not None else 0.12 * m
        self.station_radius = station_radius if station_radius is not None else 0.05 * m
        self.station_gap = station_gap if station_gap is not None else 0.01 * m
        safe_center = np.array([self.W / 2.0, self.H / 2.0])
        self.safe_zone = np.array([safe_center[0], safe_center[1], self.safe_radius])

        d = np.asarray(station_dir, dtype=float)
        d = d / max(np.linalg.norm(d), 1e-9)
        station_center = safe_center + d * (self.safe_radius + self.station_radius + self.station_gap)
        self.central_station = np.array([station_center[0], station_center[1], self.station_radius])

        # Rebaño: aparece agrupado lejos del centro (por defecto, hacia una esquina).
        self.cow_spawn = np.asarray(
            cow_spawn if cow_spawn is not None else (0.25 * self.W, 0.75 * self.H),
            dtype=float,
        )
        self.cow_spread = cow_spread if cow_spread is not None else 0.10 * m

        self.dt = dt
        self.max_steps = max_steps
        self.cow_step = cow_step
        self.drone_speed = drone_speed

        # capture_radius (a qué distancia MATA) y d_safe (a qué distancia se ATREVE a
        # quedarse) son INDEPENDIENTES: cada uno derivado de la geometría del campo,
        # no uno del otro. d_safe > capture_radius para que el cerco no mate de pasada.
        self.capture_radius = capture_radius if capture_radius is not None else 0.03 * m
        self.d_safe = d_safe if d_safe is not None else 0.06 * m

        # Muro et al. (2011): radio/banda del anillo derivados de d_safe (la regla 2 no cambia).
        self.wolf_speed = wolf_speed
        self.wolf_speed_near = wolf_speed_near if wolf_speed_near is not None else wolf_speed
        self.wolf_repulsion_radius = (
            wolf_repulsion_radius if wolf_repulsion_radius is not None else 2.0 * self.d_safe
        )
        self.wolf_repulsion_strength = wolf_repulsion_strength
        self.wolf_engage_band = wolf_engage_band if wolf_engage_band is not None else 0.5 * self.d_safe

        self._seed = seed

        # --- estado mutable (se inicializa en reset) ---
        self.rng: np.random.Generator | None = None
        self.cows: np.ndarray | None = None
        self.wolves: np.ndarray | None = None
        self.drones: np.ndarray | None = None
        self.n_wolves: int = 0          # se sortea en cada reset
        self.step_count: int = 0
        self.status: str = "running"    # running | success | predation | timeout
        self.reset()

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def reset(self, seed: int | None = None) -> dict:
        if seed is not None:
            self._seed = seed
        self.rng = np.random.default_rng(self._seed)

        # Vacas: agrupadas dentro del cluster de spawn (círculo de radio cow_spread).
        ang = self.rng.uniform(0.0, 2 * np.pi, size=self.n_cows)
        rad = self.cow_spread * np.sqrt(self.rng.uniform(0.0, 1.0, size=self.n_cows))
        self.cows = self.cow_spawn + np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])

        # Drones activos: en las esquinas del bounding box INICIAL del rebaño.
        # (Solo posición de partida; cuando haya coordinación, las decidirá el coordinador.)
        xmin, ymin, xmax, ymax = self.cows_bbox(self.cows)
        corners = np.array([[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]])
        active = corners[np.arange(self.n_active) % 4]

        # Drones de reserva: en fila recta dentro de la central, como cola de espera
        # (preparado para la futura lógica de cola de carga; sin comportamiento aún).
        scx, scy, sr = self.central_station
        half = 0.7 * sr  # margen para no salirse de la región central
        reserve = np.column_stack([np.linspace(scx - half, scx + half, self.n_reserve),
                                   np.full(self.n_reserve, scy)])
        self.drones = np.vstack([active, reserve])  # filas [0:n_active] activos, resto reserva

        # Lobos: nº aleatorio por episodio; cada uno aparece en el perímetro del campo.
        self.n_wolves = int(self.rng.integers(self.wolves_min, self.wolves_max + 1))
        self.wolves = self._random_perimeter_points(self.n_wolves)

        self.step_count = 0
        self.status = "running"
        return self.get_observation()

    # ------------------------------------------------------------------ #
    # Observación (cruda y global; se troceará por agente con el MARL)
    # ------------------------------------------------------------------ #
    def get_observation(self) -> dict:
        return {
            "drones": self.drones.copy(),
            "cows": self.cows.copy(),
            "wolves": self.wolves.copy(),
            "step": self.step_count,
        }

    # ------------------------------------------------------------------ #
    # Step: una transición de la dinámica (firma estilo gym/PettingZoo)
    # ------------------------------------------------------------------ #
    def step(self, actions):
        """
        Avanza dt. `actions`: array (n_drones, 2) = velocidad deseada en m/s
        (se recorta a drone_speed). Devuelve la 5-tupla estilo gym:
            (obs, reward, terminated, truncated, info)
        """
        self._apply_drone_actions(actions)  # fase 1: control
        self._update_cows()                 # fase 2: dinámica del entorno
        self._update_wolves()
        self.step_count += 1

        terminated, truncated = self._check_terminal()
        reward = self._compute_reward(terminated, truncated)
        info = {"status": self.status}
        return self.get_observation(), reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    # Dinámicas (deliberadamente tontas en esta versión)
    # ------------------------------------------------------------------ #
    def _apply_drone_actions(self, actions) -> None:
        if actions is None:
            return
        vel = np.asarray(actions, dtype=float).reshape(self.n_drones, 2)
        speed = np.linalg.norm(vel, axis=1, keepdims=True)
        scale = np.minimum(1.0, self.drone_speed / np.maximum(speed, 1e-9))
        self.drones = self.drones + vel * scale * self.dt
        self._clip_to_parcel(self.drones)

    def _update_cows(self) -> None:
        # Paseo aleatorio gaussiano.
        self.cows = self.cows + self.rng.normal(0.0, self.cow_step, size=self.cows.shape) * self.dt

        # TODO provisional: sustituir por modelo de cohesión/collar.
        # Sin cohesión, el paseo aleatorio dispersaría al rebaño y el bounding box
        # se dispararía. Límite blando temporal: mantener cada vaca dentro del
        # cluster de spawn recortándola al borde del círculo (radio cow_spread).
        off = self.cows - self.cow_spawn
        dist = np.linalg.norm(off, axis=1, keepdims=True)
        outside = (dist > self.cow_spread).ravel()
        if outside.any():
            self.cows[outside] = (
                self.cow_spawn + off[outside] / np.maximum(dist[outside], 1e-9) * self.cow_spread
            )

    def _update_wolves(self) -> None:
        """Modelo de caza de Muro et al. (2011): dos reglas descentralizadas por lobo.

        Cada lobo solo usa la posición de su presa y la de los demás lobos
        (sin comunicación ni jerarquía). NO hay busca-huecos, amago ni evasión de
        drones: eso es para cuando los drones se muevan.
        """
        if self.n_wolves == 0:
            return

        # --- Capa biológica: selección de presa ---
        # Cada lobo apunta a la vaca más expuesta = la más alejada del centroide
        # (el individuo rezagado). Versión simple: la misma presa para todos.
        centroid = self.cows.mean(axis=0)
        exposure = np.linalg.norm(self.cows - centroid, axis=1)
        prey = self.cows[int(np.argmax(exposure))]                  # (2,)

        to_prey = prey - self.wolves                                # (n_wolves, 2)
        dist_prey = np.linalg.norm(to_prey, axis=1, keepdims=True)  # (n_wolves, 1)
        # Vaca MÁS PRÓXIMA a cada lobo (no solo su presa): vector y distancia.
        d_cows = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)  # (n_wolves, n_cows)
        nearest = self.cows[d_cows.argmin(axis=1)]                  # (n_wolves, 2)
        to_nearest = nearest - self.wolves
        dist_nearest = np.linalg.norm(to_nearest, axis=1, keepdims=True)                  # (n_wolves, 1)

        # --- Regla 1 (Muro): MANTENER d_safe respecto al rebaño ---
        # Si está lejos (dist_nearest > d_safe) se acerca a la presa (la rezagada);
        # si una vaca entra dentro de d_safe, RETROCEDE de la más próxima. Así cerca el
        # grupo desde fuera sin atravesarlo, manteniendo su distancia de seguridad.
        # (No es evasión de obstáculos/rutas: es el standoff del depredador.)
        dir_prey = to_prey / np.maximum(dist_prey, 1e-9)
        dir_nearest = to_nearest / np.maximum(dist_nearest, 1e-9)
        approach = dir_prey * (dist_nearest > self.d_safe) - dir_nearest * (dist_nearest < self.d_safe)

        # --- Regla 2: repulsión entre lobos próximos al anillo de seguridad ---
        # Un lobo "en el anillo" (dist_prey <= d_safe + banda) se aparta de los
        # OTROS lobos que también estén en el anillo y dentro del radio de repulsión.
        # Es lo que produce el cerco emergente (se reparten alrededor de la presa).
        engaged = (dist_prey <= self.d_safe + self.wolf_engage_band).ravel()   # (n_wolves,)
        delta = self.wolves[:, None, :] - self.wolves[None, :, :]              # (n,n,2): i - j (alejarse de j)
        dd = np.linalg.norm(delta, axis=2)                                     # (n,n)
        near = (dd < self.wolf_repulsion_radius) & engaged[None, :]            # j en el anillo y cerca de i
        np.fill_diagonal(near, False)
        rep_units = delta / np.maximum(dd[:, :, None], 1e-9)
        repulsion = (rep_units * near[:, :, None]).sum(axis=1)                 # (n,2)
        repulsion *= engaged[:, None] * self.wolf_repulsion_strength           # solo repele quien está en el anillo

        # --- Acción combinada, normalizada a la velocidad del lobo ---
        action = approach + repulsion
        norm = np.linalg.norm(action, axis=1, keepdims=True)
        move_dir = action / np.maximum(norm, 1e-9)
        # Hook preparado: velocidad distinta cerca/lejos de la presa (por defecto, igual).
        speed = np.where(engaged[:, None], self.wolf_speed_near, self.wolf_speed)
        self.wolves = self.wolves + move_dir * speed * self.dt
        self._clip_to_parcel(self.wolves)

        # Zonas prohibidas (clamp geométrico por paso, NO navegación ni evasión):
        # si un lobo terminaría dentro del establo o de la central, se le desliza
        # radialmente al borde para que quede fuera. Misma idea que el límite de las vacas.
        self._push_outside_circle(self.wolves, self.safe_zone)
        self._push_outside_circle(self.wolves, self.central_station)

    # ------------------------------------------------------------------ #
    # Recompensa (placeholder de equipo; per-agente vendrá con el MARL)
    # ------------------------------------------------------------------ #
    def _compute_reward(self, terminated: bool, truncated: bool) -> float:
        reward = -0.01  # penalización por paso (incentiva resolver rápido)
        if self.status == "success":
            reward += 1.0
        elif self.status == "predation":
            reward += -1.0
        return reward

    # ------------------------------------------------------------------ #
    # Condiciones terminales
    # ------------------------------------------------------------------ #
    def _check_terminal(self) -> tuple[bool, bool]:
        # 1) Depredación: algún lobo a <= capture_radius de alguna vaca.
        d = np.linalg.norm(self.cows[None, :, :] - self.wolves[:, None, :], axis=2)  # (n_wolves, n_cows)
        if d.min() <= self.capture_radius:
            self.status = "predation"
            return True, False

        # 2) Éxito: todas las vacas dentro de la zona segura y todos los lobos fuera.
        cows_safe = self._in_safe_zone(self.cows).all()
        wolves_out = (~self._in_safe_zone(self.wolves)).all()
        if cows_safe and wolves_out:
            self.status = "success"
            return True, False

        # 3) Fin por tiempo.
        if self.step_count >= self.max_steps:
            self.status = "timeout"
            return False, True

        return False, False

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    def _in_safe_zone(self, points: np.ndarray) -> np.ndarray:
        center, radius = self.safe_zone[:2], self.safe_zone[2]
        return np.linalg.norm(points - center, axis=1) <= radius

    def _clip_to_parcel(self, pts: np.ndarray) -> None:
        np.clip(pts[:, 0], 0.0, self.W, out=pts[:, 0])
        np.clip(pts[:, 1], 0.0, self.H, out=pts[:, 1])

    def _push_outside_circle(self, pts: np.ndarray, circle: np.ndarray) -> None:
        """Clamp geométrico (NO navegación ni evasión): empuja al borde los puntos
        que caen dentro del círculo (cx, cy, r), deslizándolos radialmente hacia fuera."""
        center, r = circle[:2], circle[2]
        off = pts - center
        dist = np.linalg.norm(off, axis=1, keepdims=True)
        inside = (dist < r).ravel()
        if inside.any():
            d_in = dist[inside]
            # dirección radial; si el punto cae justo en el centro (off=0), empuja en +x.
            direction = np.where(d_in > 1e-9, off[inside] / np.maximum(d_in, 1e-9),
                                 np.array([1.0, 0.0]))
            pts[inside] = center + direction * (r * (1.0 + 1e-6))

    def _random_perimeter_points(self, n: int) -> np.ndarray:
        """n puntos aleatorios sobre el perímetro de la parcela [0,W]x[0,H]."""
        side = self.rng.integers(0, 4, size=n)   # 0 abajo, 1 arriba, 2 izq, 3 der
        t = self.rng.uniform(0.0, 1.0, size=n)
        pts = np.empty((n, 2))
        pts[side == 0] = np.column_stack([t[side == 0] * self.W, np.zeros((side == 0).sum())])
        pts[side == 1] = np.column_stack([t[side == 1] * self.W, np.full((side == 1).sum(), self.H)])
        pts[side == 2] = np.column_stack([np.zeros((side == 2).sum()), t[side == 2] * self.H])
        pts[side == 3] = np.column_stack([np.full((side == 3).sum(), self.W), t[side == 3] * self.H])
        return pts

    @staticmethod
    def cows_bbox(cows: np.ndarray) -> tuple[float, float, float, float]:
        """Bounding box (derivado) de las vacas: (x_min, y_min, x_max, y_max).
        Cantidad SOLO para dibujar y para colocar drones; no encierra a nadie."""
        xmin, ymin = cows.min(axis=0)
        xmax, ymax = cows.max(axis=0)
        return float(xmin), float(ymin), float(xmax), float(ymax)

    def herd_centroid(self) -> np.ndarray:
        return self.cows.mean(axis=0)

    def snapshot(self) -> dict:
        """Copia del estado para el render. Copias obligatorias: los arrays mutan."""
        return {
            "step": self.step_count,
            "t": self.step_count * self.dt,
            "cows": self.cows.copy(),
            "wolves": self.wolves.copy(),
            "drones": self.drones.copy(),
            "status": self.status,
        }
