"""Throwaway: suelo EXACTO de la eval ligera del run01 de drones (5 lobos + 5 mixto, δ=0)."""
import sys
sys.path.insert(0, "/workspace")
from baseline import build_world, run_episode_metrics
from rl.residual_drone_coordinator import ResidualDroneCoordinator

specs = [(s, "lobos") for s in range(5)] + [(s, "mixto") for s in range(5)]
det = {}
for s, kind in specs:
    w = build_world(s, kind)
    coord = ResidualDroneCoordinator(w, model=None)
    det[(s, kind)] = run_episode_metrics(w, coord)["n_depredadas"]
lob = [det[(s, "lobos")] for s in range(5)]
mix = [det[(s, "mixto")] for s in range(5)]
allv = lob + mix
print("lobos  seeds 0-4:", lob, "media %.2f" % (sum(lob) / 5))
print("mixto  seeds 0-4:", mix, "media %.2f" % (sum(mix) / 5))
print("GLOBAL (10 eps): %.2f  detalle=%s" % (sum(allv) / 10, allv))
