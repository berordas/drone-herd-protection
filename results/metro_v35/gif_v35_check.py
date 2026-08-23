"""GIF de comprobación v3.5 para el dueño: el gemelo MASA seed 398 mixto (el del cruce por el punto
medio a t=672 y el apilamiento) en el mundo v3.5, mismo render nuevo (cuadrados + anillo + 🔊)."""
import sys
sys.path.insert(0, "/workspace"); sys.path.insert(0, "/data/hrl_e0/verif")
import pathlib
from hrl import run_e0
run_e0.OUT_BASE = "/data/metro_v35"
job = {"seed": 398, "kind": "mixto", "arm": dict(run_e0.ARM_MASA, name="masa_reactive")}
g = run_e0.render_gif(job, "v35_masa_reactive_gemelo_gif2", pathlib.Path("/data/metro_v35"))
print(g)
job2 = {"seed": 398, "kind": "mixto", "arm": run_e0._arm_cebo(50.0, "reactive", membership="keep")}
g2 = run_e0.render_gif(job2, "v35_cebo_keep_gemelo_gif1", pathlib.Path("/data/metro_v35"))
print(g2)
