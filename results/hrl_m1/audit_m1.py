"""audit_m1.py — M1-Auditoría: EpisodeAudit (aserciones CRITICAL, contratos, procedencia) sobre los
episodios del manager en el metro (100 semillas lobos+mixto vs Reactive), en pool."""
import json, multiprocessing as mp, sys
sys.path.insert(0, "/workspace")
from hrl.manager_env import ManagerEnv
from hrl.behavior_checks import EpisodeAudit
CKPT = sys.argv[1]; OUT = sys.argv[2]
_M = {}
def run(job):
    s, kind = job
    if CKPT not in _M:
        from stable_baselines3 import PPO; _M[CKPT] = PPO.load(CKPT, device="cpu")
    model = _M[CKPT]
    env = ManagerEnv(kinds=(kind,), seed=0, opponent="reactive")
    obs, info = env.reset_to(s, kind)
    w, layer = env.world, env._layer
    audit = EpisodeAudit(w, env._coord, wolf_controller=layer, meta={"seed": s, "kind": kind},
                         decoy_indices=layer.decoy_indices, assault_indices=layer.assault_indices,
                         option_name="CEBO_manager")
    env.on_boundary = lambda w_, c_, l_: audit.on_boundary()
    env.on_tick = lambda w_, c_, l_: audit.after_step()
    done = False
    while not done:
        a, _ = model.predict(obs, deterministic=True)
        obs, r, term, trunc, info = env.step(int(a)); done = term or trunc
    rec = audit.finalize()
    return {"seed": s, "kind": kind, "sev": rec["sev"], "critical": rec["critical"],
            "violations": rec["violations"], "n_deaths": len(rec["deaths"]),
            "knc": sum(1 for d in rec["deaths"] if not d["killer_confirmado"]),
            "gotera": rec["gotera_cruces"], "premature": rec.get("premature")}
if __name__ == "__main__":
    jobs = [(s, k) for k in ("lobos", "mixto") for s in range(100)]
    with mp.Pool(24) as pool:
        recs = pool.map(run, jobs, chunksize=1)
    crit = sum(1 for r in recs if r["critical"]); viol = sum(1 for r in recs if r["violations"])
    deaths = sum(r["n_deaths"] for r in recs); knc = sum(r["knc"] for r in recs)
    res = {"n": len(recs), "critical": crit, "violations": viol, "deaths": deaths,
           "knc_frac": (knc / deaths if deaths else None), "gotera_total": sum(r["gotera"] for r in recs),
           "sev_media": sum(r["sev"] for r in recs) / len(recs), "episodes": recs}
    json.dump(res, open(OUT, "w"), ensure_ascii=False)
    print("AUDIT", {k: v for k, v in res.items() if k != "episodes"})
