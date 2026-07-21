"""train_wolves.py — Entrenador PPO del paquete de lobos (SB3) contra la barrera reactiva.

PPO("MlpPolicy") de Stable-Baselines3 sobre WolfPackEnv (cerebro único, recompensa
+1/muerte y, por defecto desde run02, + SHAPING POR POTENCIAL —plan B, ver wolf_env.py;
`--shaping off` reproduce la rala pura de run01—), con SubprocVecEnv (n envs en paralelo)
+ VecMonitor. TODOS los artefactos
(checkpoints, TensorBoard, model.zip, config.json, summary.json) van al outdir — que debe
vivir en /data (= ~/rl_data del host, FUERA del repo; persiste aunque el contenedor muera).

Uso (dentro del contenedor, ver docker/):
    python rl/train_wolves.py --smoke --outdir /data/wolves/smoke     # humo: ~60k pasos, 4 envs, CPU
    python rl/train_wolves.py --total-steps 2000000 --n-envs 8        # entrenamiento de verdad (futuro)

Device: por defecto CPU — la red es un MLP diminuto y en la DGX compartida CPU es lo cortés
(y suele ser igual de rápido: el cuello es la simulación, no la red).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# El repo (padre de rl/) importable como scripts sueltos Y en los workers de SubprocVecEnv
# (forkserver/spawn heredan PYTHONPATH, no sys.path). En el contenedor ya viene PYTHONPATH=/workspace.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ["PYTHONPATH"] = str(_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor

from rl.wolf_env import VALID_KINDS, WolfPackEnv

# Hiperparámetros por defecto (razonables, NO afinados; quedan anotados en config.json).
HYPER = dict(
    n_steps=2048,            # rollout por env (episodios largos: hasta ~2830 pasos de env)
    batch_size=512,
    gamma=0.999,             # horizonte LARGO (~1000 decisiones ≈ 500 s sim: la recompensa rala llega tarde)
    gae_lambda=0.95,
    learning_rate=3e-4,
    ent_coef=0.01,           # algo de exploración (recompensa RALA)
    clip_range=0.2,
    n_epochs=10,
)
# [128,128]→[256,256] (plan C, decisión del usuario 2026-07-15): la [128,128] INFRAAJUSTABA la
# asignación discontinua de huecos del envolvente al clonar al scriptado (train≈val alto en BC,
# |pred|~0.62 vs |exp|=1.000 → 0 muertes en cerrado); π del BC y del fine-tune DEBEN coincidir
# (--init-from copia tensores por forma). run02 ([128,128]) queda como ablación CROSS-ARQUITECTURA.
NET_ARCH = [256, 256]

# Criterios de ABORTO pactados (el que toque se escribe en train.log al arrancar y en config.json).
# - SHAPING (run02, plan B): decide ep_kills_mean ≈ 0.00 a ~3M → parar.
# - WARM-START (run03, plan C, --init-from): el modo de fallo es que el crítico IGNORANTE (value
#   fresco) desaprenda la política clonada — se vigila con la eval ligera vs el nivel del clon.
ABORT_NOTE_SHAPING = (
    "CRITERIO DE ABORTO (pactado, shaping): ep_shape_mean debe ser != 0 desde el "
    "principio (señal de que el gradiente llega); lo que decide es ep_kills_mean — si a "
    "~3.000.000 de pasos sigue ~0.00 (sin muertes emergiendo pese al acercamiento), parar "
    "el run y reportar. El plan C (currículo/BC) lo decide el usuario — NO implementarlo "
    "por cuenta propia.")
ABORT_NOTE_WARMSTART = (
    "CRITERIO DE ABORTO (pactado, warm-start/--init-from, run03): si a ~3.000.000 de pasos ni "
    "ep_kills_mean ni las evals ligeras superan CON CLARIDAD el nivel del clon (%s), PARAR el "
    "run y reportar — estancamiento y colapso del warm-start (el crítico fresco desaprendiendo "
    "el prior) quedan cubiertos con el mismo umbral. Las mitigaciones las decide el usuario — "
    "NO aplicarlas por cuenta propia.")
ABORT_NOTE_RALA = (
    "CRITERIO DE ABORTO (pactado, rala pura): si a ~2.000.000 de pasos ep_kills_mean sigue en "
    "0.00 (ninguna muerte espontánea), parar el run y reportar.")
ABORT_NOTE_RESIDUAL = (
    "CRITERIOS (pactados, run05/Nivel B — residual sobre v2.6 grouped, recompensa de EQUIPO PURA, "
    "sin ninguna pista de cebo): (1) GUARDIA DEL SUELO: el suelo es el scriptado (~2.7-2.8 en la "
    "eval ligera; en la FASE 1, política congelada y δ=0, las evals deben CLAVARSE ahí). Si en la "
    "FASE 2 la eval ligera cae por debajo de 2.4 de forma SOSTENIDA (>=1.000.000 de pasos), PARAR "
    "y reportar — PPO estaría EROSIONANDO al script. (2) ESTANCAMIENTO: el objetivo es SUPERAR "
    "2.74/2.82 (scriptado v2.6); si a ~4.000.000 de pasos la eval ligera NO ha subido con CLARIDAD "
    "por encima del suelo (~2.8), PARAR y reportar — el cebo no emerge con recompensa pura "
    "(siguientes pasos —pista al cebo / control de formación— los decide el usuario, NO "
    "implementarlos por cuenta propia). [Histórico: run04 usó guardia 2.3 y sin estancamiento.]")

# Init del residual (RPL + truco del Real Robot Challenge, arXiv:2101.02842): última capa de la
# media a CERO (δ inicial ≡ 0 → el lobo del paso 0 ES el script) y σ inicial pequeña para que la
# exploración apenas perturbe al arrancar.
RESIDUAL_LOG_STD_INIT = -2.0   # σ ≈ 0.14 (en unidades de acción normalizada)

# CURRÍCULO de separación de spawn (cruzar el valle del cebo — relative overgeneralization):
# 4 niveles fijos de 5M pasos cada uno (20M total). SOLO afecta al ENTRENAMIENTO (override del env,
# `WolfPackEnv.set_curriculum`); la EVAL es SIEMPRE spawn grouped normal de v2.7 (mide el cebo REAL,
# no el servido). Nivel 1 = frentes casi opuestos + masa >=2 por frente (cebo casi servido -> atacar
# juntos casi imposible); se endurece hasta el spawn normal (el lobo debe FORMAR el cebo por sí mismo).
CURRICULUM_SCHEDULE = [
    # (hasta_paso_agente, separación_grados | None, min_mass_por_frente)
    (5_000_000, 180.0, 2),    # Nivel 1: opuestos, ambos frentes letales
    (10_000_000, 135.0, 0),   # Nivel 2
    (15_000_000, 90.0, 0),    # Nivel 3
    (20_000_000, None, 0),    # Nivel 4: spawn grouped NORMAL de v2.7 (sin override)
]

ABORT_NOTE_CURRICULUM = (
    "CRITERIOS (pactados, CURRÍCULO del cebo — residual sobre v2.7 grouped, recompensa de EQUIPO "
    "PURA +1/muerte, shaping OFF, SIN pista de cebo; δ autoridad plena; 4 niveles de separación de "
    "spawn de 5M —180°/135°/90°/normal—, override SOLO de entrenamiento, la EVAL es SIEMPRE spawn "
    "normal). El SUELO es el scriptado v2.7 (eval ligera 10 semillas lobos = 2.20 EXACTO, MEDIDO al "
    "arrancar; en FASE 1, δ=0, se CLAVA ahí; el arnés de 100 semillas da 2.30/2.42). GUARDIA DEL "
    "SUELO: si en fase 2 la eval ligera cae por debajo de ~1.9 (suelo 2.20 − 0.3) de forma SOSTENIDA "
    "(>=1.500.000 pasos = 6 evals), PARAR y reportar — PPO EROSIONA al script. ÉXITO PARCIAL POR NIVEL: en el "
    "NIVEL 1 (cebo casi servido) la severidad DEBE subir con claridad sobre el suelo; si NO sube, es "
    "mala señal temprana (ni con el cebo regalado el lobo lo aprovecha -> el problema es más profundo "
    "que el valle) — REPORTAR (no abortar por ello). CRITERIO DE FIN (nivel 4): la pregunta es si el "
    "cebo aprendido con ayuda SOBREVIVE al spawn normal; si en nivel 4 la severidad CAE de vuelta al "
    "suelo, el resultado clave es 'el cebo se aprende con ayuda pero no se forma solo' -> siguiente "
    "vía (curiosidad coordinada / control jerárquico de formación) = decisión del usuario, NO "
    "implementarla. La vara REAL es eval_wolves 100 semillas (spawn normal) + cebo_diag "
    "(killer-no-detectado > 0 certifica que la subida es CEBO, no casualidad).")


def curriculum_level(num_timesteps: int):
    """(idx 1..4, separación|None, min_mass) del nivel de currículo para un nº de pasos-agente."""
    for i, (until, sep, mm) in enumerate(CURRICULUM_SCHEDULE):
        if num_timesteps < until:
            return i + 1, sep, mm
    return len(CURRICULUM_SCHEDULE), CURRICULUM_SCHEDULE[-1][1], CURRICULUM_SCHEDULE[-1][2]


def make_env(seed: int, kinds: tuple[str, ...], frame_skip: int,
             shaping: bool, shaping_beta: float, shaping_gamma: float,
             residual: bool = False, residual_scale: float | None = None):
    """Thunk picklable para SubprocVecEnv (cada worker importa rl.wolf_env vía PYTHONPATH)."""
    def _thunk():
        return WolfPackEnv(kinds=kinds, frame_skip=frame_skip, seed=seed,
                           shaping=shaping, shaping_beta=shaping_beta, shaping_gamma=shaping_gamma,
                           residual=residual, residual_scale=residual_scale)
    return _thunk


class EpisodeLog(BaseCallback):
    """Recoge (timestep, recompensa, longitud) de cada episodio terminado (vía VecMonitor);
    con shaping, también las COMPONENTES del episodio (kills/shape, del info del env)."""

    def __init__(self):
        super().__init__()
        self.episodes: list[dict] = []

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", ()):
            ep = info.get("episode")
            if ep is not None:
                e = {"t": int(self.num_timesteps), "r": float(ep["r"]), "l": int(ep["l"])}
                if "ep_kills" in info:
                    e["kills"] = float(info["ep_kills"])
                    e["shape"] = float(info["ep_shape"])
                self.episodes.append(e)
        return True


class TrainLog(BaseCallback):
    """Log periódico LEGIBLE a outdir/train.log (lo que se consulta con `tail -f`): una línea
    por rollout con timestamp, pasos, fps y medias móviles (últimos 100 episodios) de
    recompensa TOTAL, ep_kills_mean (LA señal que importa), ep_shape_mean (el término de
    shaping — debe ser != 0 desde el principio si el shaping está ON) y longitud.
    La cabecera documenta el criterio de aborto pactado."""

    def __init__(self, logpath: Path, run_config: str, abort_note: str):
        super().__init__()
        self.logpath = logpath
        self.run_config = run_config
        self.abort_note = abort_note
        self._t0 = None
        self._kills = deque(maxlen=100)     # componentes por episodio (info del env, al done)
        self._shape = deque(maxlen=100)

    def _write(self, line: str) -> None:
        with open(self.logpath, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _on_training_start(self) -> None:
        if self._t0 is not None:
            return                      # segunda learn() (fase 2 del residual): sin cabecera repetida
        self._t0 = time.time()
        self._write("=" * 100)
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] ARRANQUE  {self.run_config}")
        self._write(self.abort_note)
        self._write("columnas: timestamp | pasos | fps | ep_rew_mean (total, últimos 100 eps) | "
                    "ep_kills_mean | ep_shape_mean | ep_len_mean")

    def _on_rollout_end(self) -> None:
        buf = self.model.ep_info_buffer
        rew = float(np.mean([e["r"] for e in buf])) if buf else float("nan")
        length = float(np.mean([e["l"] for e in buf])) if buf else float("nan")
        kills = float(np.mean(self._kills)) if self._kills else float("nan")
        shape = float(np.mean(self._shape)) if self._shape else float("nan")
        fps = self.num_timesteps / max(time.time() - self._t0, 1e-9)
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] pasos={self.num_timesteps:>10,}  "
                    f"fps={fps:7.1f}  ep_rew_mean={rew:7.3f}  ep_kills_mean={kills:6.3f}  "
                    f"ep_shape_mean={shape:7.3f}  ep_len_mean={length:8.1f}")

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", ()):
            if "ep_kills" in info:          # solo llega al done (terminal del episodio)
                self._kills.append(float(info["ep_kills"]))
                self._shape.append(float(info["ep_shape"]))
        return True

    def _on_training_end(self) -> None:
        self._write(f"[{datetime.now().isoformat(timespec='seconds')}] FIN  pasos={self.num_timesteps:,}")


class LightEval(BaseCallback):
    """Eval periódica LIGERA (cada eval_every pasos): 10 episodios DETERMINISTAS en semillas
    fijas de 'lobos' con la política actual contra la barrera (mismo mecanismo que el
    evaluador: PolicyWolfController + SyncedReactiveCoordinator) → media de muertes al
    train.log. SIEMPRE SIN SHAPING (va por el World directo y cuenta muertes: lo que se
    puntúa). La eval COMPLETA (100 semillas) es solo con rl/eval_wolves.py, manual."""

    EVAL_SEEDS_LIGHT = tuple(range(10))

    def __init__(self, logpath: Path, eval_every: int = 250_000,
                 residual: bool = False, residual_scale: float | None = None,
                 curriculum: bool = False):
        super().__init__()
        self.logpath = logpath
        self.eval_every = int(eval_every)
        self.residual = residual
        self.residual_scale = residual_scale
        self.curriculum = curriculum   # si True, prefija el nivel de currículo vigente (eval SIEMPRE spawn normal)
        self._next_at = self.eval_every

    def _on_step(self) -> bool:
        if self.eval_every <= 0 or self.num_timesteps < self._next_at:
            return True
        self._next_at += self.eval_every
        from baseline import build_world
        from rl.policy_wolf_controller import PolicyWolfController, SyncedReactiveCoordinator
        from rl.residual_wolf_controller import ResidualWolfController
        t0 = time.time()
        deaths = []
        for s in self.EVAL_SEEDS_LIGHT:
            if self.residual:               # δ determinista de la política (sin ruido) sobre el script
                ctrl = ResidualWolfController(model=self.model, residual_scale=self.residual_scale)
            else:
                ctrl = PolicyWolfController(model=self.model)
            w = build_world(s, "lobos", wolf_controller=ctrl)
            w.reset()
            coord = SyncedReactiveCoordinator(w)
            while True:
                _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
                if term or trunc:
                    break
            deaths.append(w.n_depredadas)
        nivel_txt = ""
        if self.curriculum:
            lvl, sep, mm = curriculum_level(self.num_timesteps)
            sep_txt = "normal" if sep is None else f"{sep:.0f}°"
            nivel_txt = f"NIVEL {lvl} (entren. sep={sep_txt}, masa>={mm}; eval=spawn NORMAL)  "
        line = (f"[{datetime.now().isoformat(timespec='seconds')}] EVAL_LIGERA pasos={self.num_timesteps:>10,}  "
                f"{nivel_txt}muertes_media={np.mean(deaths):.2f}  (n=10 semillas lobos, determinista; "
                f"detalle={deaths}; {time.time() - t0:.0f}s)")
        with open(self.logpath, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True


def _reward_por_tramos(episodes: list[dict], n_tramos: int = 4) -> list[dict]:
    """Media/máx de recompensa por tramos consecutivos de episodios (progresión del smoke)."""
    if not episodes:
        return []
    rs = np.array([e["r"] for e in episodes], dtype=float)
    tramos = []
    for chunk in np.array_split(rs, min(n_tramos, len(rs))):
        tramos.append({"n_episodios": int(chunk.size),
                       "reward_media": float(chunk.mean()), "reward_max": float(chunk.max())})
    return tramos


def main() -> None:
    p = argparse.ArgumentParser(description="Entrena PPO (paquete de lobos) contra la barrera reactiva.")
    p.add_argument("--total-steps", type=int, default=1_000_000, help="pasos totales de env (suma de todos los envs)")
    p.add_argument("--n-envs", type=int, default=8, help="envs en paralelo (SubprocVecEnv)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", type=str, default=None, help="def. /data/wolves/<timestamp> (¡fuera del repo!)")
    p.add_argument("--kinds", type=str, default="lobos,mixto", help="tipos de episodio (coma; nunca 'corzos')")
    p.add_argument("--device", type=str, default="cpu", help="cpu (def., lo cortés en la DGX compartida) | cuda")
    p.add_argument("--frame-skip", type=int, default=5, help="pasos de física por decisión (0.5 s)")
    p.add_argument("--smoke", action="store_true", help="preset humo: 60k pasos, 4 envs (demuestra que gira)")
    p.add_argument("--resume", type=str, default=None, help="checkpoint .zip del que RETOMAR (PPO.load, sin resetear el contador)")
    p.add_argument("--eval-every", type=int, default=250_000, help="eval ligera (10 eps deterministas) cada N pasos; 0 = off")
    p.add_argument("--shaping", choices=("on", "off"), default="on",
                   help="shaping por potencial (plan B) al ENTRENAR; def. on (la eval nunca lo ve)")
    p.add_argument("--shaping-beta", type=float, default=1.0, help="β del potencial Φ = −β·dist_media/D_norm")
    p.add_argument("--init-from", type=str, default=None,
                   help="model.zip del que COPIAR la POLÍTICA (warm-start/BC, plan C); el value "
                        "function nace FRESCO. Incompatible con --resume.")
    p.add_argument("--lr", type=float, default=None,
                   help="override de learning_rate (p.ej. 1e-4 en fine-tune para no destrozar el prior)")
    p.add_argument("--abort-ref", type=float, default=None,
                   help="nivel del clon (muertes_media de su eval ligera) para el criterio de aborto warm-start")
    p.add_argument("--residual", action="store_true",
                   help="política RESIDUAL sobre el scriptado (RPL, run04): acción = δ, obs = 132, dos fases")
    p.add_argument("--residual-scale", type=float, default=None,
                   help="escala de δ en m/s (def. wolf_speed — autoridad plena)")
    p.add_argument("--phase1-steps", type=int, default=1_000_000,
                   help="residual: pasos de FASE 1 (solo crítico, política congelada); 0 = sin fase 1")
    p.add_argument("--curriculum", action="store_true",
                   help="CURRÍCULO del cebo: 4 niveles de separación de spawn (180/135/90/normal, 5M c/u = 20M). "
                        "Implica --residual y fuerza shaping OFF (recompensa de equipo pura). Override SOLO de "
                        "entrenamiento; la eval es SIEMPRE spawn normal de v2.7.")
    args = p.parse_args()
    shaping = args.shaping == "on"
    if args.init_from and args.resume:
        p.error("--init-from (solo pesos de política, contador a 0) y --resume (run completo) son excluyentes")
    if args.residual and args.init_from:
        p.error("--residual e --init-from son excluyentes (el residual arranca en δ≡0, no de un clon)")
    if args.curriculum:
        if not args.residual:
            p.error("--curriculum implica --residual (el cebo se aprende como δ sobre el scriptado)")
        if shaping:
            p.error("--curriculum exige recompensa de EQUIPO PURA: pasa --shaping off")
        args.total_steps = CURRICULUM_SCHEDULE[-1][0]     # el schedule define el total (20M)
    if args.curriculum:
        abort_note = ABORT_NOTE_CURRICULUM
    elif args.residual:
        abort_note = ABORT_NOTE_RESIDUAL
    elif args.init_from:
        ref = ("%.2f muertes_media en las 10 semillas de la eval ligera" % args.abort_ref
               if args.abort_ref is not None else "su eval ligera; ver --abort-ref")
        abort_note = ABORT_NOTE_WARMSTART % ref
    elif shaping:
        abort_note = ABORT_NOTE_SHAPING
    else:
        abort_note = ABORT_NOTE_RALA

    if args.smoke:
        args.total_steps = 60_000
        args.n_envs = 4
        if args.curriculum:
            # Schedule ESCALADO para que el humo CRUCE los 4 niveles en 60k (demuestra las
            # transiciones en el log). El run serio usa el schedule de 5M por nivel.
            CURRICULUM_SCHEDULE[:] = [(15_000, 180.0, 2), (30_000, 135.0, 0),
                                      (45_000, 90.0, 0), (60_000, None, 0)]
            args.phase1_steps = min(args.phase1_steps, 8_000)

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    if any(k not in VALID_KINDS for k in kinds):
        p.error("--kinds debe ser subconjunto de %r (nunca 'corzos')" % (VALID_KINDS,))

    outdir = Path(args.outdir) if args.outdir else Path("/data/wolves") / datetime.now().strftime("%Y%m%d-%H%M%S")

    hyper = dict(HYPER)
    if args.lr is not None:
        hyper["learning_rate"] = args.lr             # fine-tune: LR bajo para no destrozar el prior

    shaping_desc = (f"shaping ON (β={args.shaping_beta}, γ={HYPER['gamma']} = el del PPO)"
                    if shaping else "shaping OFF (rala pura)")
    if args.init_from:
        shaping_desc += f" init-from={args.init_from} lr={hyper['learning_rate']}"
    if args.residual:
        shaping_desc += (f" RESIDUAL (RPL: δ sobre el scriptado; scale={args.residual_scale or 'wolf_speed'}; "
                         f"fase1={args.phase1_steps:,} solo-crítico; lr={hyper['learning_rate']})")
    print("=== train_wolves (PPO, cerebro único del paquete, +1/muerte + %s) ===" % shaping_desc)
    print(f"  envs = {args.n_envs} (SubprocVecEnv)  |  device = {args.device}  |  seed = {args.seed}")
    print(f"  kinds = {kinds}  |  frame_skip = {args.frame_skip}  |  total_steps = {args.total_steps:,}")
    print(f"  outdir = {outdir}")

    # outdir escribible ANTES de entrenar (que no se pierda una noche de run por un typo).
    outdir.mkdir(parents=True, exist_ok=True)
    probe = outdir / ".write_test"
    probe.write_text("ok"); probe.unlink()

    config = {
        "args": vars(args) | {"kinds": list(kinds), "outdir": str(outdir)},
        "hyper": hyper, "net_arch": NET_ARCH, "algo": "PPO(MlpPolicy)",
        "reward": "+1 por res matada (rala, compartida); sin castigo por tiempo ni por a-salvo"
                  + ("; + shaping por potencial (plan B, Ng et al.)" if shaping else ""),
        "shaping": {"on": shaping, "beta": args.shaping_beta, "gamma": HYPER["gamma"],
                    "phi": "-beta * mean_i dist(lobo_i, presa ternero-primero) / diagonal_campo; 0 si coasting",
                    "nota": "gamma EXACTAMENTE el del PPO (inocuidad de Ng et al.); la eval NUNCA ve el shaping"},
        "init_from": args.init_from,
        "residual": {"on": args.residual, "scale": args.residual_scale or "wolf_speed",
                     "phase1_steps": args.phase1_steps, "log_std_init": RESIDUAL_LOG_STD_INIT,
                     "obs": "132 = 122 + accion del script normalizada (pista del estado oculto)",
                     "nota": "RPL (Silver et al. 2018): v_final = clip_norma(v_script + delta); "
                             "el script entero vive dentro (su presa/histéresis/coasting)"}
                    if args.residual else {"on": False},
        "curriculum": {"on": args.curriculum,
                       "schedule": [{"hasta_paso": u, "separacion_grados": s, "min_mass": m}
                                    for (u, s, m) in CURRICULUM_SCHEDULE],
                       "recompensa": "EQUIPO PURA (+1/muerte, shaping OFF, SIN pista de cebo)",
                       "nota": "override SOLO de entrenamiento (WolfPackEnv.set_curriculum); la EVAL "
                               "es SIEMPRE spawn grouped normal de v2.7 (mide el cebo REAL)"}
                      if args.curriculum else {"on": False},
        "abort": abort_note,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    (outdir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False))

    # start_method="fork" (Linux): los workers HEREDAN el estado del padre. El default de SB3
    # (forkserver) arranca un proceso limpio que re-importa el stack y moría en la imagen del
    # lab importando cv2 (opencv del lockfile) sin libGL (arreglado también en docker/Dockerfile).
    venv = SubprocVecEnv([make_env(args.seed + i, kinds, args.frame_skip,
                                   shaping, args.shaping_beta, HYPER["gamma"],   # γ del PPO, EXACTO
                                   args.residual, args.residual_scale)
                          for i in range(args.n_envs)],
                         start_method="fork")
    venv = VecMonitor(venv)

    if args.resume:
        # Retomar de checkpoint: mismos hiperparámetros embebidos en el .zip; el contador de
        # pasos NO se resetea (learn(reset_num_timesteps=False)) -> checkpoints/log continúan.
        model = PPO.load(args.resume, env=venv, device=args.device,
                         tensorboard_log=str(outdir / "tb"))
        print(f"  RESUME desde {args.resume} (pasos ya entrenados: {model.num_timesteps:,})")
    else:
        model = PPO("MlpPolicy", venv, verbose=1, seed=args.seed, device=args.device,
                    tensorboard_log=str(outdir / "tb"),
                    policy_kwargs=dict(net_arch=NET_ARCH), **hyper)
        if args.init_from:
            # WARM-START (plan C): copia SOLO los tensores de POLÍTICA del zip (red pi, cabeza de
            # acción y log_std); el VALUE FUNCTION queda con su init fresco (en SB3 2.x pi y V son
            # redes separadas). PPO nuevo → optimizador y contador de pasos desde cero.
            src = PPO.load(args.init_from, device=args.device)
            src_sd = src.policy.state_dict()
            dst_sd = model.policy.state_dict()
            pi_prefixes = ("mlp_extractor.policy_net", "action_net", "log_std")
            copiadas = [k for k in dst_sd
                        if k.startswith(pi_prefixes) and k in src_sd and src_sd[k].shape == dst_sd[k].shape]
            assert copiadas, "--init-from: ningún tensor de política compatible (¿arquitectura distinta?)"
            for k in copiadas:
                dst_sd[k] = src_sd[k]
            model.policy.load_state_dict(dst_sd)
            print(f"  INIT-FROM {args.init_from}: {len(copiadas)} tensores de POLÍTICA copiados "
                  f"(value function FRESCO; lr={hyper['learning_rate']})")
        if args.residual:
            # INIT CRÍTICO del residual (RPL + arXiv:2101.02842): media de δ ≡ 0 EXACTO (última
            # capa a cero) y σ pequeña. Verificación obligatoria: la media debe salir 0 exacto
            # para CUALQUIER obs (capa final nula ⇒ salida nula independientemente del rasgo).
            import torch as th
            model.policy.action_net.weight.data.zero_()
            model.policy.action_net.bias.data.zero_()
            model.policy.log_std.data.fill_(RESIDUAL_LOG_STD_INIT)
            probe = th.as_tensor(np.random.default_rng(0).normal(
                size=(5, venv.observation_space.shape[0])).astype(np.float32))
            with th.no_grad():
                mu = model.policy.get_distribution(probe).distribution.mean
            assert (mu == 0.0).all(), "init residual roto: la media de δ no es 0 exacto"
            print(f"  RESIDUAL: init verificado — media de δ = 0 EXACTO (5 obs aleatorias); "
                  f"log_std = {RESIDUAL_LOG_STD_INIT} (σ≈{np.exp(RESIDUAL_LOG_STD_INIT):.2f})")

    run_desc = (f"total_steps={args.total_steps:,} n_envs={args.n_envs} seed={args.seed} "
                f"device={args.device} kinds={kinds} frame_skip={args.frame_skip} "
                f"{shaping_desc} resume={args.resume or '-'} outdir={outdir}")
    ep_log = EpisodeLog()
    train_log = TrainLog(outdir / "train.log", run_desc, abort_note)
    light_eval = LightEval(outdir / "train.log", eval_every=args.eval_every,
                           residual=args.residual, residual_scale=args.residual_scale,
                           curriculum=args.curriculum)
    checkpoints = CheckpointCallback(save_freq=max(500_000 // args.n_envs, 1),   # ~cada 500k pasos totales
                                     save_path=str(outdir / "checkpoints"), name_prefix="ppo_wolves")
    callbacks = [ep_log, train_log, light_eval, checkpoints]

    def _mark(msg: str) -> None:
        print("  " + msg)
        with open(outdir / "train.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")

    def _set_level(lvl: int) -> None:
        """Aplica el nivel de currículo a TODOS los envs (env_method) y lo marca en el log."""
        until, sep, mm = CURRICULUM_SCHEDULE[lvl - 1]
        venv.env_method("set_curriculum", sep, mm)
        sep_txt = "spawn NORMAL (sin override)" if sep is None else f"separación {sep:.0f}°"
        _mark(f"=== CURRÍCULO NIVEL {lvl}/{len(CURRICULUM_SCHEDULE)}: {sep_txt}, masa>={mm} por frente "
              f"(hasta {until:,} pasos) — override SOLO de entrenamiento; eval = spawn normal ===")

    t0 = time.time()
    try:
        if args.residual and not args.resume and args.phase1_steps > 0:
            if args.curriculum:
                _set_level(1)                          # arranca en el nivel 1 (cebo casi servido)
            # FASE 1 — SOLO CRÍTICO (truco del Real Robot Challenge): π y log_std CONGELADOS
            # (δ medio = 0; solo ruido σ≈0.14); el crítico aprende cuánto vale el script antes
            # de que nada se mueva. Las evals ligeras deben CLAVARSE en el suelo (~2.7).
            pi_params = (list(model.policy.mlp_extractor.policy_net.parameters())
                         + list(model.policy.action_net.parameters()) + [model.policy.log_std])
            for p_ in pi_params:
                p_.requires_grad_(False)
            fase1 = min(args.phase1_steps, args.total_steps)
            print(f"  FASE 1 (solo crítico): política CONGELADA durante {fase1:,} pasos")
            model.learn(total_timesteps=fase1, callback=callbacks)
            for p_ in pi_params:
                p_.requires_grad_(True)
            _mark(f"=== FASE 2 (PPO normal): política DESCONGELADA en el paso {model.num_timesteps:,} ===")
            if args.curriculum:
                # FASE 2 por NIVELES: en cada frontera se re-aplica el currículo (toma efecto en el
                # próximo reset de cada worker) y se entrena hasta el límite del nivel.
                for lvl in range(1, len(CURRICULUM_SCHEDULE) + 1):
                    until = CURRICULUM_SCHEDULE[lvl - 1][0]
                    if model.num_timesteps >= until:
                        continue
                    _set_level(lvl)
                    restante = until - model.num_timesteps
                    model.learn(total_timesteps=restante, callback=callbacks, reset_num_timesteps=False)
            else:
                restante = args.total_steps - model.num_timesteps
                if restante > 0:
                    model.learn(total_timesteps=restante, callback=callbacks, reset_num_timesteps=False)
        else:
            model.learn(total_timesteps=args.total_steps, callback=callbacks,
                        reset_num_timesteps=not args.resume)
    finally:
        venv.close()                                   # sin workers colgados (buen vecino)
    elapsed = time.time() - t0

    model.save(str(outdir / "model.zip"))

    rs = np.array([e["r"] for e in ep_log.episodes], dtype=float)
    assert rs.size == 0 or np.isfinite(rs).all(), "recompensas no finitas (NaN/inf) — pipeline roto"
    ks = np.array([e["kills"] for e in ep_log.episodes if "kills" in e], dtype=float)
    summary = {
        "total_steps": int(model.num_timesteps),
        "elapsed_s": round(elapsed, 1),
        "fps": round(model.num_timesteps / max(elapsed, 1e-9), 1),
        "episodios": len(ep_log.episodes),
        "reward_media": float(rs.mean()) if rs.size else None,
        "reward_max": float(rs.max()) if rs.size else None,
        "kills_media": float(ks.mean()) if ks.size else None,   # la señal que importa (sin shaping)
        "kills_max": float(ks.max()) if ks.size else None,
        "reward_por_tramos": _reward_por_tramos(ep_log.episodes),
        "longitud_media_ep": float(np.mean([e["l"] for e in ep_log.episodes])) if ep_log.episodes else None,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("=== resumen ===")
    print(f"  {summary['total_steps']:,} pasos en {summary['elapsed_s']:.0f} s -> {summary['fps']:.0f} fps")
    print(f"  episodios = {summary['episodios']}  |  reward media = {summary['reward_media']}  |  max = {summary['reward_max']}")
    for i, tr in enumerate(summary["reward_por_tramos"]):
        print(f"    tramo {i + 1}: n={tr['n_episodios']}  media={tr['reward_media']:.2f}  max={tr['reward_max']:.0f}")
    print(f"  artefactos -> {outdir} (model.zip, checkpoints/, tb/, config.json, summary.json)")


if __name__ == "__main__":
    main()
