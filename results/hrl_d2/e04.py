"""e04.py — E0.4 (D2-FASE-1, adenda del dueno; SOLO evaluacion): 100 semillas emparejadas,
defensas {dummy, reactive (4-0), proporcional, run09} x atacantes {natural, cebo2f, manager}.
Metricas por celda: sev global + subconjunto 2-frentes, KNC (donde hay confirmacion), CARRERA
guardia-vs-asalto (t llegada guardia al 2o cluster vs t llegada del asalto al rebano), latencia
y reasignaciones de la proporcional, jugada completa del atacante, PENETRADO. Si PENETRADO sube
por celda: DECISION HUMANA, no arreglar.
Uso: python3 e04.py <defensa> <atacante> <out.json>"""
import json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp
import numpy as np

sys.path.insert(0, "/workspace")
from baseline import CONFIG_V2, build_world
from coordinators import DummyCoordinator, ReactiveCoordinator
from world import ACTIVE, DETER_RADIUS, World
from hrl.behavior_checks import EpisodeAudit
from hrl.options_drone import ProportionalAllocatorCoordinator, analyze_threats

DEF, ATK, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CKPT = "/data/hrl_m1/M1pppp/model.zip"
RUN09 = "/data/drones/run09_v35/model.zip"


def make_defense(w):
    if DEF == "dummy":
        return DummyCoordinator(w.n_drones)
    if DEF == "reactive":
        return ReactiveCoordinator(w)
    if DEF == "proporcional":
        return ProportionalAllocatorCoordinator(w)
    if DEF.startswith("dronemgr:"):
        from hrl.manager_drone import LearnedAllocatorCoordinator
        return LearnedAllocatorCoordinator(w, DEF.split(":", 1)[1])
    if DEF == "run09":
        from stable_baselines3 import PPO
        from rl.residual_drone_coordinator import ResidualDroneCoordinator
        if "m" not in _M:
            _M["m"] = PPO.load(RUN09, device="cpu")
        return ResidualDroneCoordinator(w, model=_M["m"])
    raise SystemExit(DEF)


_M: dict = {}


def reactive_core(coord):
    return coord.inner if hasattr(coord, "inner") else (coord if hasattr(coord, "_confirmed") else None)


class Carrera:
    """CARRERA guardia-vs-asalto + latencia/reasignaciones (solo con la proporcional)."""

    def __init__(self, w, coord):
        self.w, self.coord = w, coord
        self.t_sec = None            # 1ª percepción de 2º clúster
        self.t_guard = None          # 1ª partición con ng>0 (en cualquier momento)
        self.t_guard_post = None     # 1ª partición con ng>0 DESPUÉS de percibir el 2º clúster
        self.t_llegada_guardia = None
        self.t_llegada_asalto = None
        self.reasignaciones = 0
        self._prev_part = None

    def tick(self):
        w, coord = self.w, self.coord
        if not hasattr(coord, "particion") or not hasattr(coord, "_seats"):
            return
        part = coord.particion
        if self._prev_part is not None and part != self._prev_part:
            self.reasignaciones += 1
        self._prev_part = part
        info = analyze_threats(w, coord.inner)
        t = int(w.step_count)
        sec_w = np.array([], dtype=int)
        if info["secundario"] is not None:
            if self.t_sec is None:
                self.t_sec = t
            cl = info["clusters"][info["secundario"]]
            sec_w = info["wolf_idx"][cl]
            sec_w = sec_w[sec_w >= 0]
        if part[1] > 0 and self.t_guard is None:
            self.t_guard = t
        if part[1] > 0 and self.t_sec is not None and self.t_guard_post is None:
            self.t_guard_post = t
        if sec_w.size:
            seats = coord._seats.seats()
            guards = [int(d) for d in seats[4 - part[1]:] if d >= 0] if part[1] else []
            if guards and self.t_llegada_guardia is None:
                dg = np.linalg.norm(w.wolves[sec_w][:, None, :] - w.drones[guards][None, :, :],
                                    axis=2).min()
                if dg <= DETER_RADIUS:
                    self.t_llegada_guardia = t
            if self.t_llegada_asalto is None:
                m = w.cow_alive & ~w.cow_safe
                herd = np.vstack([w.cows[m]] + ([w.calves[w.calf_alive & ~w.calf_safe]]
                                                if w.n_calves else []))
                if herd.shape[0]:
                    da = np.linalg.norm(w.wolves[sec_w][:, None, :] - herd[None, :, :], axis=2).min()
                    if da <= DETER_RADIUS:
                        self.t_llegada_asalto = t

    def out(self):
        return {"t_sec": self.t_sec, "t_guard": self.t_guard, "t_guard_post": self.t_guard_post,
                "guardias_antes_2cl": (self.t_guard is not None and self.t_sec is not None
                                       and self.t_guard < self.t_sec),
                "latencia": (self.t_guard_post - self.t_sec if self.t_guard_post is not None
                             and self.t_sec is not None else None),
                "t_llegada_guardia": self.t_llegada_guardia,
                "t_llegada_asalto": self.t_llegada_asalto,
                "gana_guardia": (self.t_llegada_guardia is not None
                                 and (self.t_llegada_asalto is None
                                      or self.t_llegada_guardia <= self.t_llegada_asalto)),
                "reasignaciones": self.reasignaciones}


def run_script(job):
    """Atacante scriptado (natural | cebo2f): bucle plano de mundo."""
    seed, kind = job
    if kind is None:
        w = World(seed=seed, **CONFIG_V2)
    else:
        w = build_world(seed, kind)
    coord = make_defense(w)
    w.reset()
    core = reactive_core(coord)
    audit = EpisodeAudit(w, core, meta={"seed": seed}) if core is not None else None
    car = Carrera(w, coord)
    t_show = t_escolta = None
    pen = 0
    while True:
        if audit:
            audit.on_boundary()
        wp = coord.act(w.get_observation())
        if core is not None and getattr(core, "_pose_last_step", -10) != int(w.step_count) \
                and w.phase == "ESCOLTA" and getattr(core, "_anchor", None) is not None:
            pen += 1
        _o, _r, term, trunc, _i = w.step(wp)
        if audit:
            audit.after_step()
        car.tick()
        if t_show is None and w.wolf_decoy_released:
            t_show = int(w.step_count)
        if t_escolta is None and w.phase == "ESCOLTA":
            t_escolta = int(w.step_count)
        if term or trunc:
            break
    rec = audit.finalize() if audit else None
    core = getattr(coord, "core", None)
    return {"seed": seed, "kind": w.episode_kind, "sev": int(w.n_depredadas),
            "cambios": (int(core.n_cambios) if core is not None else None),
            "stalls_def": (int(core.n_stalls) if core is not None else None),
            "two_front": bool(len(w.wolf_group_sizes) == 2),
            "knc": (sum(1 for d in rec["deaths"] if not d["killer_confirmado"]) if rec else None),
            "deaths": (len(rec["deaths"]) if rec else int(w.n_depredadas)),
            "jugada_completa": (bool(t_show is not None and t_escolta is not None)
                                if w.wolf_decoy_size is not None else None),
            "penetrado": pen, "carrera": car.out()}


def run_manager(job):
    seed, kind = job
    from hrl.manager_env import ManagerEnv
    from hrl.eval_manager import policy_fn
    ManagerEnv._make_coord = lambda self, w: make_defense(w)   # parche de EVALUACIÓN
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    obs, info = env.reset_to(seed, kind)
    w = env.world
    car = Carrera(w, env._coord)
    env.on_tick = lambda w_, c_, l_: car.tick()
    pol = policy_fn("manager:" + CKPT)
    first, done = True, False
    while not done:
        a = int(pol(obs, info, first)); first = False
        obs, r, term, trunc, info = env.step(a)
        done = term or trunc
    core = getattr(env._coord, "core", None)
    return {"seed": seed, "kind": kind, "sev": int(info["ep_sev"]),
            "cambios": (int(core.n_cambios) if core is not None else None),
            "stalls_def": (int(core.n_stalls) if core is not None else None),
            "two_front": info["two_front"], "knc": None, "deaths": int(info["ep_sev"]),
            "jugada_completa": info["jugada"]["completa"],
            "stalls": info.get("stalls"), "aborts": info.get("aborts"),
            "penetrado": info["penetrado_ticks"], "carrera": car.out()}


def seeds_2f(count):
    out, s = [], 0
    while len(out) < count and s < 4000:
        w = build_world(s, "lobos")
        w.reset()
        if len(w.wolf_group_sizes) == 2:
            out.append(s)
        s += 1
    return out


if __name__ == "__main__":
    if ATK == "natural":
        jobs, fn = [(s, None) for s in range(100)], run_script
    elif ATK == "cebo2f":
        jobs, fn = [(s, "lobos") for s in seeds_2f(100)], run_script
    elif ATK == "manager":
        jobs, fn = [(s, k) for k in ("lobos", "mixto") for s in range(100)], run_manager
    else:
        raise SystemExit(ATK)
    if os.environ.get("E04_SMOKE"):
        jobs = jobs[:int(os.environ["E04_SMOKE"])]
    ctx = mp.get_context("spawn" if (ATK == "manager" or DEF == "run09" or DEF.startswith("dronemgr:")) else "fork")
    with ctx.Pool(10) as pool:
        recs = pool.map(fn, jobs, chunksize=2)
    sev = np.array([r["sev"] for r in recs], float)
    tf = [r for r in recs if r["two_front"]]
    deaths = sum(r["deaths"] for r in recs)
    kncs = [r["knc"] for r in recs if r["knc"] is not None]
    lat = [r["carrera"]["latencia"] for r in recs if r["carrera"]["latencia"] is not None]
    car_g = [r["carrera"]["gana_guardia"] for r in recs
             if r["carrera"]["t_llegada_guardia"] is not None or r["carrera"]["t_llegada_asalto"] is not None]
    jug = [r["jugada_completa"] for r in recs if r["jugada_completa"] is not None]
    cambios = [r.get("cambios") for r in recs if r.get("cambios") is not None]
    res = {"defensa": DEF, "atacante": ATK, "n": len(recs),
           "cambios_particion_media": (round(float(np.mean(cambios)), 2) if cambios else None),
           "sev": round(float(sev.mean()), 3),
           "sev_2f": (round(float(np.mean([r["sev"] for r in tf])), 3) if tf else None),
           "n_2f": len(tf),
           "knc_frac": (round(float(sum(kncs)) / max(deaths, 1), 3) if kncs else None),
           "jugada_completa_frac": (round(float(np.mean(jug)), 3) if jug else None),
           "penetrado_medio": round(float(np.mean([r["penetrado"] for r in recs])), 1),
           "carrera": {"latencia_media": (round(float(np.mean(lat)), 1) if lat else None),
                       "guardias_antes_2cl_frac": round(float(np.mean(
                           [bool(r["carrera"]["guardias_antes_2cl"]) for r in recs])), 3),
                       "reasignaciones_media": round(float(np.mean(
                           [r["carrera"]["reasignaciones"] for r in recs])), 2),
                       "gana_guardia_frac": (round(float(np.mean(car_g)), 3) if car_g else None),
                       "n_carreras": len(car_g)},
           "episodes": recs}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "episodes"}, ensure_ascii=False))
    print("E04_CELDA_OK", DEF, ATK)
