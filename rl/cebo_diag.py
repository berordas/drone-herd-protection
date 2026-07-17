"""cebo_diag.py — Diagnóstico de CEBO (Nivel B): ¿las muertes vienen del frente que la barrera NO atiende?

Mide COMPORTAMIENTO, no solo severidad: distingue "mata más por casualidad" de "mata más PORQUE
ceba". Corre los episodios del arnés (mismas EVAL_SEEDS, CONFIG_V2 grouped, barrera v2.6 congelada
vía SyncedReactiveCoordinator) y SOLO computa métricas de cebo en los episodios con 2 SUBGRUPOS de
spawn (grupos por índice, fijos todo el episodio: grupo 2 = últimos k índices, `wolf_group_sizes`).

Por cada MUERTE (res depredada), con el estado de la FRONTERA anterior al paso en que cae:
  - killer = lobo más cercano a la res muerta; su grupo (1|2).
  - `killer_detectado`: ¿estaba DETECTADO (<= r_detect de un dron ACTIVE — el criterio de la barrera
    v2.6, recomputado en solo-lectura)?
  - `grupo_ancla`: grupo del lobo ANCLA de la barrera (`coordinator.inner._anchor`; None = barrera
    ciega/patrulla). MÉTRICA (b): fracción de muertes del subgrupo NO anclado.
  - `sujecion` — MÉTRICA (a): en las muertes del grupo NO anclado, ¿el OTRO subgrupo tenía >=1 lobo
    detectado en ese instante (= el frente VISTO estaba ocupado mientras mataba el NO visto)?
  - `cebo_puro`: killer NO detectado ∧ el otro grupo SÍ detectado (la firma completa del cebo).
Contexto temporal: fracción de pasos de ESCOLTA con exactamente UN grupo detectado (cuántas veces
existe siquiera la situación explotable) y separación media de frentes en las muertes.

REFERENCIA NULA: correr con --floor (δ≡0 = scriptado puro por el camino residual) da los valores de
estas fracciones SIN cebo aprendido; el cebo emergido en un checkpoint = SUBIDA de estas métricas
respecto al suelo, junto a la subida de severidad (eval_wolves). Solo lectura del estado por paso;
no toca física, checks ni artefactos del repo. JSON a /data.

Uso (dentro del contenedor):
    python rl/cebo_diag.py --floor                                   # referencia nula (scriptado)
    python rl/cebo_diag.py --model /data/wolves/run05_nivelB/checkpoints/ppo_wolves_4000000_steps.zip
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from world import ACTIVE
from baseline import EVAL_SEEDS, build_world
from rl.policy_wolf_controller import SyncedReactiveCoordinator
from rl.residual_wolf_controller import ResidualWolfController
from rl.wolf_env import VALID_KINDS


def _detected_mask(w) -> np.ndarray:
    """Criterio de percepción de la barrera v2.6, recomputado en solo-lectura (mismo que
    ReactiveCoordinator._detected): lobo a <= r_detect de un dron EN VUELO (ACTIVE)."""
    flying = w.drones[w.drone_state == ACTIVE]
    if flying.shape[0] == 0 or w.n_wolves == 0:
        return np.zeros(w.n_wolves, dtype=bool)
    d = np.linalg.norm(np.asarray(w.wolves, dtype=float)[:, None, :] - flying[None, :, :], axis=2)
    return (d <= w.r_detect).any(axis=1)


def run_episode(seed: int, kind: str, model, residual_scale) -> dict | None:
    """Un episodio instrumentado. None si el spawn no salió con 2 subgrupos (no computa cebo)."""
    ctrl = ResidualWolfController(model=model, residual_scale=residual_scale)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n1 = int(w.wolf_group_sizes[0])
    g1 = np.arange(0, n1)
    g2 = np.arange(n1, w.n_wolves)

    kills = []                     # dicts por muerte (estado de la frontera PREVIA al paso letal)
    steps_escolta = 0
    steps_un_grupo_visto = 0
    prev_cow = w.cow_alive.copy()
    prev_calf = w.calf_alive.copy() if w.n_calves > 0 else None

    while True:
        # --- estado en la frontera (antes de actuar) ---
        det = _detected_mask(w)
        anchor = coord.inner._anchor                     # lobo ancla de la barrera (None = ciega)
        anchor_g = None if anchor is None else (1 if anchor < n1 else 2)
        det_g = {1: bool(det[g1].any()), 2: bool(det[g2].any())}
        wolves_pre = np.asarray(w.wolves, dtype=float)
        sep = float(np.linalg.norm(wolves_pre[g1].mean(0) - wolves_pre[g2].mean(0)))
        if w.phase == "ESCOLTA":
            steps_escolta += 1
            if det_g[1] != det_g[2]:
                steps_un_grupo_visto += 1

        # --- actuar y avanzar ---
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))

        # --- muertes de este paso, atribuidas al lobo más cercano (posición actual) ---
        died = []
        for i in np.where(prev_cow & ~w.cow_alive)[0]:
            died.append(w.cows[i])
        prev_cow = w.cow_alive.copy()
        if prev_calf is not None:
            for i in np.where(prev_calf & ~w.calf_alive)[0]:
                died.append(w.calves[i])
            prev_calf = w.calf_alive.copy()
        for pos in died:
            wolves_now = np.asarray(w.wolves, dtype=float)
            killer = int(np.linalg.norm(wolves_now - pos, axis=1).argmin())
            kg = 1 if killer < n1 else 2
            og = 2 if kg == 1 else 1
            kills.append({
                "grupo_killer": kg,
                "killer_detectado": bool(det[killer]),
                "grupo_ancla": anchor_g,                          # None = barrera ciega en ese paso
                "no_anclado": (anchor_g is not None and kg != anchor_g),
                "otro_grupo_detectado": det_g[og],
                "cebo_puro": (not bool(det[killer])) and det_g[og],
                "sep_frentes": round(sep, 1),
            })
        if term or trunc:
            break

    return {
        "seed": seed, "kind": kind, "sizes": [int(x) for x in w.wolf_group_sizes],
        "n_depredadas": int(w.n_depredadas), "status": w.status, "steps": int(w.step_count),
        "steps_escolta": steps_escolta, "steps_un_grupo_visto": steps_un_grupo_visto,
        "kills": kills,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnóstico de CEBO en episodios grouped de 2 subgrupos (barrera v2.6).")
    p.add_argument("--model", default=None, help="checkpoint .zip SB3 (residual); opcional con --floor")
    p.add_argument("--floor", action="store_true", help="δ≡0 (scriptado): la REFERENCIA NULA del cebo")
    p.add_argument("--residual-scale", type=float, default=None, help="escala de δ (def. wolf_speed; = la del run)")
    p.add_argument("--kinds", type=str, default="lobos,mixto")
    p.add_argument("--n-seeds", type=int, default=len(EVAL_SEEDS))
    p.add_argument("--out", type=str, default=None, help="JSON (def.: /data/wolves/cebo_<floor|modelo>.json)")
    args = p.parse_args()
    if not args.floor and not args.model:
        p.error("--model es obligatorio (salvo --floor)")

    kinds = tuple(k.strip() for k in args.kinds.split(",") if k.strip())
    if any(k not in VALID_KINDS for k in kinds):
        p.error("--kinds debe ser subconjunto de %r" % (VALID_KINDS,))
    seeds = tuple(range(args.n_seeds))

    model = None
    if args.model:
        from stable_baselines3 import PPO
        model = PPO.load(str(args.model), device="cpu")
    name = "floor" if args.model is None else Path(args.model).stem
    out = Path(args.out) if args.out else Path("/data/wolves") / f"cebo_{name}.json"

    print("=== cebo_diag: %s | kinds=%s | %d semillas ===" % ("SUELO δ≡0 (referencia nula)" if model is None
                                                              else args.model, kinds, len(seeds)))
    episodes = []
    for kind in kinds:
        for s in seeds:
            r = run_episode(s, kind, model, args.residual_scale)
            if r is not None:
                episodes.append(r)

    all_kills = [k for e in episodes for k in e["kills"]]
    con_ancla = [k for k in all_kills if k["grupo_ancla"] is not None]
    no_anclado = [k for k in con_ancla if k["no_anclado"]]
    sev2g = float(np.mean([e["n_depredadas"] for e in episodes])) if episodes else 0.0
    frac = lambda part, whole: (len(part) / len(whole)) if whole else 0.0  # noqa: E731

    resumen = {
        "n_episodios_2grupos": len(episodes),
        "severidad_media_2grupos": round(sev2g, 3),
        "n_muertes": len(all_kills),
        "frac_pasos_un_grupo_visto": round(float(np.mean(
            [e["steps_un_grupo_visto"] / max(e["steps_escolta"], 1) for e in episodes])), 3) if episodes else 0.0,
        # (b) ¿mata el subgrupo NO anclado por la barrera? (sobre muertes con ancla definida)
        "frac_muertes_no_anclado": round(frac(no_anclado, con_ancla), 3),
        "n_muertes_barrera_ciega": len(all_kills) - len(con_ancla),   # ancla None (patrulla) al caer la res
        # (a) sujeción: de las muertes del NO anclado, ¿el otro grupo estaba detectado (frente visto ocupado)?
        "frac_sujecion_en_no_anclado": round(frac([k for k in no_anclado if k["otro_grupo_detectado"]],
                                                  no_anclado), 3),
        # firma completa: killer NO detectado ∧ otro grupo detectado
        "frac_cebo_puro": round(frac([k for k in all_kills if k["cebo_puro"]], all_kills), 3),
        "frac_killer_no_detectado": round(frac([k for k in all_kills if not k["killer_detectado"]], all_kills), 3),
        "sep_frentes_media_en_muertes": round(float(np.mean([k["sep_frentes"] for k in all_kills])), 1) if all_kills else 0.0,
    }

    print("  episodios con 2 subgrupos: %d | severidad media en ellos: %.2f | muertes: %d"
          % (resumen["n_episodios_2grupos"], resumen["severidad_media_2grupos"], resumen["n_muertes"]))
    print("  (b) muertes del subgrupo NO anclado: %.1f%% (de %d con ancla; %d con barrera ciega)"
          % (100 * resumen["frac_muertes_no_anclado"], len(con_ancla), resumen["n_muertes_barrera_ciega"]))
    print("  (a) sujeción en esas muertes (otro grupo detectado): %.1f%%"
          % (100 * resumen["frac_sujecion_en_no_anclado"]))
    print("  cebo PURO (killer no visto ∧ otro frente visto): %.1f%% | killer no detectado: %.1f%%"
          % (100 * resumen["frac_cebo_puro"], 100 * resumen["frac_killer_no_detectado"]))
    print("  contexto: un-solo-grupo-visto el %.1f%% de los pasos de ESCOLTA | sep frentes media en muertes: %.1f m"
          % (100 * resumen["frac_pasos_un_grupo_visto"], resumen["sep_frentes_media_en_muertes"]))

    payload = {
        "model": str(args.model) if args.model else "FLOOR (δ≡0 = scriptado)",
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "kinds": list(kinds), "n_seeds": len(seeds),
        "resumen": resumen, "episodes": episodes,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print("  guardado -> %s" % out)


if __name__ == "__main__":
    main()
