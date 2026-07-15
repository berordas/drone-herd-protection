"""collect_demos.py — DEMOSTRACIONES del experto (lobos SCRIPTADOS) contra la barrera reactiva.

Plan C (decisión del usuario): los lobos reales YA saben cazar — lo que aprenden ante los
drones es a ADAPTAR su caza. La cuna del RL es el scriptado: aquí se recogen pares
(obs, acción experta) para clonarlo por imitación (rl/bc_pretrain.py) y afinar con PPO.

CÓMO se muestrea (la sincronía es LA parte delicada — misma convención que el env):
- Se corren episodios con `ScriptedWolfController` inyectado (envuelto en un wrapper que solo
  OBSERVA su salida: la dinámica es BIT A BIT la scriptada) contra el `ReactiveCoordinator`
  congelado, con el bucle del arnés (`build_world` + reset + act/step, como
  `baseline.run_episode_metrics`).
- La OBS se construye en las FRONTERAS DE DECISIÓN del env (cada `frame_skip=5` pasos de
  física): ANTES del `coordinator.act()`/`world.step()` del primer paso de la ventana — el
  MISMO instante en que `WolfPackEnv` construye su obs y en que `PolicyWolfController.refresh`
  muestrea (ver policy_wolf_controller.py; equivalencia de fronteras = rl_env_check test 7).
- La ACCIÓN EXPERTA de la frontera (`--label`): **`mean` (default, dataset v3)** = la MEDIA de
  los `v_target` que el scriptado emite en los 5 pasos de física de la ventana — la intención
  NETA que el hold del env ejecuta de verdad. **Motivo (ALIASING medido, ver DISEÑO 2026-07-15
  3ª):** el v_target del scriptado oscila (acercar/retirar/tangente en r_face_safe + cono +
  re-anclaje del envolvente) más rápido de lo que muestrea la frontera: el 31,4% de las
  etiquetas de primer-paso consecutivas (0,5 s) INVIERTEN el sentido (bimodal estable-o-flip)
  → ~⅓ de la supervisión era cuasi-ruido para una política sin memoria y el clon salía ≈0 con
  [128,128] y con [256,256]. La media de la ventana promedia ese flip (ruido → señal).
  `first` = el v_target del PRIMER paso de la ventana (datasets v1/v2, para reproducirlos).
  En ambos casos se normaliza a [-1, 1] (÷ `wolf_speed`, el inverso exacto de la
  desnormalización del env; la media de direcciones unitarias tiene norma ≤ 1 por sí sola) y
  los slots de lobos AUSENTES quedan a 0 (su máscara ya viaja en la obs). Si el episodio
  termina a mitad de ventana, la media es sobre los pasos que corrieron.
- **PRESA DEL CONTRATO RL (consistencia entrenamiento/servicio — el fix del clon ≈0):** tras
  cada `decide()` del scriptado se impone `RLWolfController._write_prey` (ternero-primero), el
  MISMO pin bajo el que el clon servirá (el pin de la vaca lee `pack_prey`; en evaluación lo
  escribe RLWolfController). Sin esto, las demos nacen condicionadas a la fijación con
  HISTÉRESIS del scriptado — un estado OCULTO que no viaja en la obs (contrato: obs sin
  presa) → etiquetas multimodales → la MSE promedia (módulo 0.61, cola de direcciones) y el
  clon salía ≈0. Diagnóstico (10 semillas lobos, deterministas): scriptado puro 2.7 · scriptado
  con hold de 0.5 s 2.7 (el hold no cuesta) · scriptado+hold+presa RL 2.5 (el TECHO honesto de
  la cuna) · clon sobre demos inconsistentes 0.2. El experto de las demos es ese tercero:
  táctica scriptada BIT A BIT + pin del contrato.

Semillas de ENTRENAMIENTO DISJUNTAS del examen: base 10_000 (EVAL_SEEDS = range(100) — la
cuna no debe ver las semillas con las que luego se puntúa); kinds lobos/mixto alternados
~50/50. Dataset comprimido (.npz: obs float32 (N,122), act float32 (N,10)) + manifest.json
a /data/wolves/demos/ — NUNCA al repo.

Los episodios son INDEPENDIENTES (cada uno construye su World sembrado) → se recogen en
paralelo (`--workers`, fork como SubprocVecEnv) manteniendo el dataset DETERMINISTA: el corte
por `--target-pairs` se evalúa en el ORDEN de las semillas, así que el resultado es idéntico
al secuencial sea cual sea el nº de workers.

Uso (dentro del contenedor):
    python rl/collect_demos.py                                   # ~120k pares (def.)
    python rl/collect_demos.py --target-pairs 2000 --out /tmp/x  # smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np

from baseline import EVAL_SEEDS, build_world
from coordinators import ReactiveCoordinator
from wolf_controllers import ScriptedWolfController, WolfController

from rl.obs import N_WOLF_SLOTS, build_obs
from rl.rl_wolf_controller import RLWolfController

DEMO_SEED_BASE = 10_000          # disjunto de EVAL_SEEDS (range(100)): la cuna no ve el examen
DEMO_KINDS = ("lobos", "mixto")  # alternados ~50/50; NUNCA 'corzos'


class _RecordingScripted(WolfController):
    """Táctica SCRIPTADA + presa del CONTRATO RL (ver cabecera): delega la velocidad en el
    scriptado, GUARDA su salida (la etiqueta) y a continuación impone la presa ternero-primero
    (`RLWolfController._write_prey`) — el mismo pin que el clon tendrá en servicio. El
    scriptado del paso siguiente lee esa presa (mismo orden que en evaluación: el pin del paso
    k lee la presa escrita en k−1)."""

    def __init__(self):
        self.inner = ScriptedWolfController()
        self.last_v: np.ndarray | None = None

    def decide(self, world):
        v, coasting = self.inner.decide(world)
        self.last_v = np.asarray(v, dtype=np.float64).copy()
        RLWolfController._write_prey(world)     # el contrato RL manda sobre el pin (y el próximo decide)
        return v, coasting


def collect_episode(seed: int, kind: str, frame_skip: int,
                    label: str = "mean") -> tuple[np.ndarray, np.ndarray, dict]:
    """Un episodio scriptado-vs-barrera; devuelve (obs (B,122), act (B,10), metadatos).
    `label`: 'mean' = media de los v_target de la ventana (v3) | 'first' = el del 1er paso."""
    rec = _RecordingScripted()
    w = build_world(seed, kind, wolf_controller=rec)
    w.reset()
    coord = ReactiveCoordinator(w)
    obs_l: list[np.ndarray] = []
    act_l: list[np.ndarray] = []
    k = 0
    pending: np.ndarray | None = None
    window: list[np.ndarray] = []
    while True:
        if k % frame_skip == 0:
            pending = build_obs(w)                    # LA FRONTERA (mismo instante que el env)
            window = []
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        window.append(rec.last_v[: w.n_wolves] / w.wolf_speed)
        k += 1
        if k % frame_skip == 0 or term or trunc:      # ventana completa (o episodio cortado)
            v = window[0] if label == "first" else np.mean(window, axis=0)
            a = np.zeros((N_WOLF_SLOTS, 2), dtype=np.float32)
            a[: w.n_wolves] = np.clip(v, -1.0, 1.0)
            obs_l.append(pending)
            act_l.append(a.ravel())
        if term or trunc:
            break
    meta = {"seed": seed, "kind": kind, "status": w.status, "steps": int(w.step_count),
            "n_depredadas": int(w.n_depredadas), "n_pairs": len(obs_l)}
    return np.stack(obs_l), np.stack(act_l), meta


def _job(args_tuple):
    """Envoltorio picklable para el Pool (fork)."""
    return collect_episode(*args_tuple)


def main() -> None:
    p = argparse.ArgumentParser(description="Recoge demostraciones del scriptado vs la barrera (plan C).")
    p.add_argument("--target-pairs", type=int, default=120_000, help="pares (obs, acción) objetivo")
    p.add_argument("--max-episodes", type=int, default=600, help="tope de episodios (salvaguarda)")
    p.add_argument("--frame-skip", type=int, default=5, help="pasos de física por decisión (= el env)")
    p.add_argument("--seed-base", type=int, default=DEMO_SEED_BASE,
                   help="primera semilla (disjunta de EVAL_SEEDS)")
    p.add_argument("--out", type=str, default="/data/wolves/demos", help="directorio de salida (en /data)")
    p.add_argument("--workers", type=int, default=6, help="episodios en paralelo (fork; dataset idéntico)")
    p.add_argument("--label", choices=("mean", "first"), default="mean",
                   help="etiqueta: mean = media de la ventana (v3, anti-aliasing) | first = 1er paso (v1/v2)")
    args = p.parse_args()

    assert args.seed_base > max(EVAL_SEEDS), \
        "las semillas de demos deben ser DISJUNTAS de EVAL_SEEDS (la cuna no ve el examen)"

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=== collect_demos: scriptado vs barrera reactiva (fronteras del env, cada %d pasos) ===" % args.frame_skip)
    print(f"  objetivo = {args.target_pairs:,} pares  |  semillas desde {args.seed_base} (disjuntas del examen)")
    print(f"  out = {outdir}")

    # Job list generosa en ORDEN de semilla; el corte por target_pairs se evalúa en ese orden
    # (imap preserva el orden) → dataset DETERMINISTA e idéntico al secuencial.
    from multiprocessing import get_context
    jobs = [(args.seed_base + i, DEMO_KINDS[i % len(DEMO_KINDS)], args.frame_skip, args.label)
            for i in range(args.max_episodes)]
    all_obs, all_act, episodes = [], [], []
    n_pairs = 0
    with get_context("fork").Pool(max(args.workers, 1)) as pool:
        for obs, act, meta in pool.imap(_job, jobs, chunksize=1):
            all_obs.append(obs)
            all_act.append(act)
            episodes.append(meta)
            n_pairs += meta["n_pairs"]
            if len(episodes) % 25 == 0:
                kills = np.mean([e["n_depredadas"] for e in episodes])
                print(f"  {len(episodes)} episodios | {n_pairs:,} pares | muertes/ep del experto = {kills:.2f}",
                      flush=True)
            if n_pairs >= args.target_pairs:
                break
        pool.terminate()                              # descarta los episodios de más allá del corte

    obs_arr = np.concatenate(all_obs).astype(np.float32)
    act_arr = np.concatenate(all_act).astype(np.float32)
    assert np.isfinite(obs_arr).all() and np.isfinite(act_arr).all(), "NaN/inf en el dataset"
    assert (np.abs(act_arr) <= 1.0 + 1e-6).all(), "acción experta fuera de [-1,1] (¿normalización?)"

    np.savez_compressed(outdir / "demos.npz", obs=obs_arr, act=act_arr)
    kills = [e["n_depredadas"] for e in episodes]
    manifest = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "n_pairs": int(len(obs_arr)),
        "n_episodes": len(episodes),
        "seeds": [args.seed_base, args.seed_base + len(episodes) - 1],
        "seeds_disjuntas_de_eval": True,
        "kinds": {k: sum(1 for e in episodes if e["kind"] == k) for k in DEMO_KINDS},
        "frame_skip": args.frame_skip,
        "label": args.label,
        "accion": ("MEDIA de los v_target del scriptado en la ventana (anti-aliasing), ÷ wolf_speed; slots ausentes a 0"
                   if args.label == "mean" else
                   "v_target del scriptado en el 1er paso de la ventana, ÷ wolf_speed (=[-1,1]); slots ausentes a 0"),
        "presa": "contrato RL (ternero-primero) impuesto tras cada decide — el MISMO pin que verá el clon en servicio",
        "obs": "rl/obs.py build_obs en la frontera del env (misma convención que WolfPackEnv/test 7)",
        "experto_muertes_media": float(np.mean(kills)),
        "experto_muertes_std": float(np.std(kills)),
        "experto_terminales": {s: sum(1 for e in episodes if e["status"] == s)
                               for s in ("success", "predation", "timeout")},
        "episodes": episodes,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"  TOTAL: {len(obs_arr):,} pares en {len(episodes)} episodios | "
          f"experto = {manifest['experto_muertes_media']:.2f}±{manifest['experto_muertes_std']:.2f} muertes/ep")
    print(f"  guardado -> {outdir / 'demos.npz'} + manifest.json")


if __name__ == "__main__":
    main()
