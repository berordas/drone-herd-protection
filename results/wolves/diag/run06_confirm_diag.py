"""run06_confirm_diag.py — SOLO LECTURA: rehacer la geometría del cebo con r_confirm=40 (no r_detect=100).

Parte A (coordinador REAL, sin tocar nada): sobre los mismos episodios de 2 subgrupos
(scriptado δ=0 y mejor ckpt 4M, mismas semillas que run06_killgeom):
  - cobertura del campo a r_confirm=40 vs r_detect=100 (rejilla 50x50, drones ACTIVE, media en ESCOLTA)
  - 2º frente por paso: NO visto (>100) / ANILLO contacto-sin-confirmar (40,100] / confirmable (<=40)
    (min dist de los lobos del grupo 2 al dron ACTIVE más cercano), con racha máxima en anillo
  - muertes reclasificadas: matador <=40 / (40,100] / >100 del dron ACTIVE más cercano

Parte B (CONTRAFACTUAL desechable, NO toca el repo): subclase de ReactiveCoordinator cuya
percepción de barrera exige CONFIRMACIÓN (proxy geométrico: un lobo queda confirmado — latch —
la primera vez que un dron ACTIVE lo tiene a <= r_confirm; visible para la barrera = confirmado
Y actualmente detectado a <= r_detect). El reflejo de investigación del mundo NO se toca.
Lobos = scriptado (canónico). Mide severidad + geometría de muertes + % killer-no-confirmado.
"""
import sys, json; sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from world import ACTIVE
from coordinators import ReactiveCoordinator
from rl.residual_wolf_controller import ResidualWolfController

BEST_4M = "/data/wolves/run06_curric/checkpoints/ppo_wolves_3999936_steps.zip"
GRID = 50

# ---------------- contrafactual: barrera solo-confirmados ----------------
class ConfirmOnlyReactive(ReactiveCoordinator):
    """Igual que ReactiveCoordinator pero la barrera solo VE lobos CONFIRMADOS:
    confirmado (latch por lobo) = alguna vez a <= r_confirm de un dron ACTIVE;
    visible = confirmado & actualmente a <= r_detect de un ACTIVE (la identidad
    persiste, la posición exige contacto). Coherente con el marco DRI."""
    def __init__(self, world):
        super().__init__(world)
        self._confirmed = None
        self._conf_last_step = -1

    def _detected(self):
        w = self.world
        if w.n_wolves == 0:
            return np.zeros(0, dtype=bool)
        step = int(w.step_count)
        if self._confirmed is None or self._confirmed.shape[0] != w.n_wolves or step < self._conf_last_step:
            self._confirmed = np.zeros(w.n_wolves, dtype=bool)
        self._conf_last_step = step
        flying = w.drones[w.drone_state == ACTIVE]
        if flying.shape[0] == 0:
            return np.zeros(w.n_wolves, dtype=bool)
        d = np.linalg.norm(np.asarray(w.wolves, float)[:, None, :] - flying[None, :, :], axis=2).min(axis=1)
        self._confirmed |= (d <= w.r_confirm)
        return self._confirmed & (d <= w.r_detect)

class SyncedCoord:
    """Refresca el controlador de lobos en la frontera (como SyncedReactiveCoordinator) con inner arbitrario."""
    def __init__(self, world, inner_cls):
        self.world = world
        self.inner = inner_cls(world)
    def act(self, observation=None):
        self.world.wolf_controller.refresh(self.world)
        return self.inner.act(observation)

# ---------------- utilidades ----------------
def coverage(active, r, W, H):
    gx, gy = np.meshgrid(np.linspace(0, W, GRID), np.linspace(0, H, GRID))
    pts = np.stack([gx.ravel(), gy.ravel()], axis=1)
    d = np.linalg.norm(pts[:, None, :] - active[None, :, :], axis=2).min(axis=1)
    return float((d <= r).mean())

def run(seed, kind, model, coord_cls):
    ctrl = ResidualWolfController(model=model)
    w = build_world(seed, kind, wolf_controller=ctrl)
    coord = SyncedCoord(w, coord_cls); w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    k2 = int(w.wolf_group_sizes[1]); g2 = np.arange(w.n_wolves - k2, w.n_wolves)
    cov40, cov100 = [], []
    g2_unseen = g2_ring = g2_conf = 0; esc_steps = 0
    ring_run = 0; ring_max = 0
    kills = []
    prev_cow = w.cow_alive.copy(); prev_calf = w.calf_alive.copy() if w.n_calves > 0 else None
    while True:
        _o, _r, term, trunc, _i = w.step(coord.act(w.get_observation()))
        act = w.drones[w.drone_state == ACTIVE]
        if w.phase == "ESCOLTA" and act.shape[0] > 0:
            esc_steps += 1
            if esc_steps % 10 == 0:                      # la rejilla es cara; muestrea 1 Hz
                cov40.append(coverage(act, w.r_confirm, w.W, w.H))
                cov100.append(coverage(act, w.r_detect, w.W, w.H))
            dg2 = np.linalg.norm(np.asarray(w.wolves, float)[g2][:, None, :] - act[None, :, :], axis=2).min()
            if dg2 > w.r_detect:
                g2_unseen += 1; ring_run = 0
            elif dg2 > w.r_confirm:
                g2_ring += 1; ring_run += 1; ring_max = max(ring_max, ring_run)
            else:
                g2_conf += 1; ring_run = 0
        died = []
        for i in np.where(prev_cow & ~w.cow_alive)[0]: died.append(w.cows[i])
        prev_cow = w.cow_alive.copy()
        if prev_calf is not None:
            for i in np.where(prev_calf & ~w.calf_alive)[0]: died.append(w.calves[i])
            prev_calf = w.calf_alive.copy()
        if died and act.shape[0] > 0:
            wn = np.asarray(w.wolves, float)
            for pos in died:
                ki = int(np.linalg.norm(wn - pos, axis=1).argmin())
                kills.append(float(np.linalg.norm(act - wn[ki], axis=1).min()))
        if term or trunc:
            break
    return {"sev": int(w.n_depredadas), "esc": esc_steps,
            "cov40": float(np.mean(cov40)) if cov40 else 0.0,
            "cov100": float(np.mean(cov100)) if cov100 else 0.0,
            "g2_unseen": g2_unseen, "g2_ring": g2_ring, "g2_conf": g2_conf,
            "ring_max_s": ring_max * w.dt, "kills": kills}

def campaign(name, model, coord_cls, want=24):
    eps = []
    for kind in ("lobos", "mixto"):
        for s in range(60):
            r = run(s, kind, model, coord_cls)
            if r is None: continue
            eps.append(r)
            if len(eps) >= want: break
        if len(eps) >= want: break
    ka = np.array([d for e in eps for d in e["kills"]])
    esc = sum(e["esc"] for e in eps)
    un = sum(e["g2_unseen"] for e in eps); ri = sum(e["g2_ring"] for e in eps); co = sum(e["g2_conf"] for e in eps)
    tot = max(1, un + ri + co)
    print(f"\n===== {name}: {len(eps)} episodios de 2 subgrupos, {ka.size} muertes, sev media {np.mean([e['sev'] for e in eps]):.2f} =====")
    print(f"  cobertura media del campo en ESCOLTA: r_confirm=40 -> {100*np.mean([e['cov40'] for e in eps]):.0f}%  |  r_detect=100 -> {100*np.mean([e['cov100'] for e in eps]):.0f}%")
    print(f"  2º frente (min dist al ACTIVE más cercano, % de pasos de ESCOLTA):")
    print(f"    NO visto (>100): {100*un/tot:.0f}%  |  ANILLO contacto-sin-confirmar (40,100]: {100*ri/tot:.0f}%  |  <=40: {100*co/tot:.0f}%")
    print(f"    racha máxima continua en el anillo: {max(e['ring_max_s'] for e in eps):.0f} s")
    if ka.size:
        print(f"  muertes (dist matador -> dron ACTIVE más cercano): media {ka.mean():.0f} m (máx {ka.max():.0f})")
        print(f"    <= r_confirm=40: {100*np.mean(ka <= 40):.0f}%  |  anillo (40,100]: {100*np.mean((ka > 40) & (ka <= 100)):.0f}%  |  > r_detect=100: {100*np.mean(ka > 100):.0f}%")
    return eps

def main():
    from stable_baselines3 import PPO
    m4 = PPO.load(BEST_4M, device="cpu")
    out = {}
    print("### PARTE A — coordinador REAL (barrera a r_detect=100, la de hoy)")
    out["A_scripted"] = campaign("REAL · lobos scriptado", None, ReactiveCoordinator)
    out["A_best4M"] = campaign("REAL · lobos ckpt 4M", m4, ReactiveCoordinator)
    print("\n### PARTE B — CONTRAFACTUAL (barrera solo-confirmados: latch a <=40, visible si ademas <=100)")
    out["B_scripted"] = campaign("CONFIRM-ONLY · lobos scriptado", None, ConfirmOnlyReactive)
    json.dump({k: v for k, v in out.items()}, open("/data/wolves/diag/run06_confirm_diag.json", "w"), default=float)
    print("\nJSON -> /data/wolves/diag/run06_confirm_diag.json")

if __name__ == "__main__":
    main()
