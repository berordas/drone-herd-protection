"""bc_pretrain.py — CLONACIÓN por imitación (BC) del scriptado sobre la política PPO (plan C).

Instancia el MISMO PPO de train_wolves (misma arquitectura NET_ARCH, mismos espacios del env)
y entrena SOLO la POLÍTICA por imitación: MSE entre la MEDIA de la gaussiana
(`policy.get_distribution(obs).distribution.mean` — con gradientes) y la acción experta del
dataset de rl/collect_demos.py. El VALUE FUNCTION no se toca (queda con su init aleatorio =
"fresco"; en SB3 2.x π y V son redes SEPARADAS: mlp_extractor.policy_net/action_net vs
mlp_extractor.value_net/value_net — el optimizador de aquí solo ve las de política; log_std
tampoco se toca: la media no depende de él).

La pérdida se calcula SOLO sobre los slots de lobos PRESENTES (máscara del flag present de la
propia obs): los ausentes (objetivo 0) diluían la pérdida y gastaban capacidad sin enseñar
nada — en servicio `decide()` recorta a n_wolves y esos slots nunca se usan.

DOS pérdidas (`--loss`):
- `mse` — MSE plana sobre la acción (la receta original).
- `dir` (default) — POR SLOT presente: (1 − cos(pred, exp)) + (|pred| − |exp|)². Motivo
  (medido, ver DISEÑO): la acción experta es una DIRECCIÓN a módulo 1.000 SIEMPRE; con MSE
  plana el clon infraajusta la asignación discontinua de huecos del envolvente y la media
  ENCOGE el módulo (0.62) y promedia direcciones (17% opuestas) → en cerrado los lobos llegan
  a la presa pero jamás completan el flanqueo (0 muertes). La pérdida direccional separa
  ambos errores y castiga el encogimiento. En frames de coasting (|exp| = 0) solo aplica el
  término de módulo (el coseno no está definido).

Split train/val 90/10 (barajado sembrado), early-stop simple por pérdida de validación
(paciencia fija, se restaura el MEJOR estado), Adam. Hiperparámetros al bc_config.json.
Salida: bc_model.zip en formato SB3 estándar (model.save) → cargable por PolicyWolfController
(evaluación), por eval_wolves.py y por train_wolves.py --init-from / --resume.

Uso (dentro del contenedor):
    python rl/bc_pretrain.py                       # /data/wolves/demos/{demos.npz -> bc_model.zip}
    python rl/bc_pretrain.py --epochs 5            # más corto
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


def main() -> None:
    p = argparse.ArgumentParser(description="Clona al scriptado (BC) sobre la política PPO (plan C).")
    p.add_argument("--demos", type=str, default="/data/wolves/demos/demos.npz")
    p.add_argument("--out", type=str, default="/data/wolves/demos/bc_model.zip")
    p.add_argument("--epochs", type=int, default=60, help="tope de épocas (early-stop por val)")
    p.add_argument("--batch-size", type=int, default=1024)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--patience", type=int, default=5, help="épocas sin mejorar val antes de parar")
    p.add_argument("--loss", choices=("dir", "mse"), default="dir",
                   help="dir = (1−cos)+(Δ|·|)² por slot (default; ver cabecera) | mse = receta original")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    import torch as th
    from stable_baselines3 import PPO

    from rl.obs import N_WOLF_SLOTS, OFF_WOLF, WOLF_FEAT
    from rl.train_wolves import HYPER, NET_ARCH        # la MISMA arquitectura que el entrenamiento
    from rl.wolf_env import WolfPackEnv

    th.manual_seed(args.seed)

    data = np.load(args.demos)
    obs = th.as_tensor(data["obs"], dtype=th.float32)
    act = th.as_tensor(data["act"], dtype=th.float32)
    n = len(obs)
    # Máscara (N,10) de slots PRESENTES desde el flag present de la propia obs (2 dims por slot).
    present = obs[:, [OFF_WOLF + WOLF_FEAT * i + 5 for i in range(N_WOLF_SLOTS)]]  # (N,5) en {0,1}
    mask = present.repeat_interleave(2, dim=1)                                     # (N,10)
    print("=== bc_pretrain: clonación del scriptado (MSE sobre la media de la gaussiana) ===")
    print(f"  dataset = {args.demos} ({n:,} pares)  |  arch = {NET_ARCH}  |  lr = {args.lr}")
    print(f"  slots presentes: {float(present.mean()) * N_WOLF_SLOTS:.2f}/5 de media (la MSE solo los mira a ellos)")

    idx = np.random.default_rng(args.seed).permutation(n)
    n_val = max(int(n * args.val_frac), 1)
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    obs_tr, act_tr, mask_tr = obs[tr_idx], act[tr_idx], mask[tr_idx]
    obs_val, act_val, mask_val = obs[val_idx], act[val_idx], mask[val_idx]

    # El MISMO PPO que train_wolves (el env solo fija los espacios; aquí no se hace RL).
    model = PPO("MlpPolicy", WolfPackEnv(kinds=("lobos",), seed=0), seed=args.seed, device="cpu",
                policy_kwargs=dict(net_arch=NET_ARCH), **HYPER)
    policy = model.policy
    pi_params = (list(policy.mlp_extractor.policy_net.parameters())
                 + list(policy.action_net.parameters()))       # SOLO política (ni value net ni log_std)
    opt = th.optim.Adam(pi_params, lr=args.lr)

    def _mean(o: th.Tensor) -> th.Tensor:
        return policy.get_distribution(o).distribution.mean

    def _loss_fn(pred: th.Tensor, target: th.Tensor, m: th.Tensor) -> th.Tensor:
        if args.loss == "mse":
            return (m * (pred - target) ** 2).sum() / m.sum().clamp(min=1.0)
        # 'dir': por SLOT presente, (1 − cos) sobre slots con acción experta no nula + (Δ módulo)².
        p2 = pred.view(-1, N_WOLF_SLOTS, 2)
        t2 = target.view(-1, N_WOLF_SLOTS, 2)
        mslot = m.view(-1, N_WOLF_SLOTS, 2)[:, :, 0]                  # (B,5) presencia por slot
        np_ = p2.norm(dim=2)
        nt = t2.norm(dim=2)
        activo = mslot * (nt > 1e-6).float()                          # coseno solo si |exp| > 0
        cos = (p2 * t2).sum(dim=2) / (np_ * nt + 1e-8)
        l_dir = (activo * (1.0 - cos)).sum() / activo.sum().clamp(min=1.0)
        l_mod = (mslot * (np_ - nt) ** 2).sum() / mslot.sum().clamp(min=1.0)
        return l_dir + l_mod

    def _val_loss() -> float:
        policy.set_training_mode(False)
        with th.no_grad():
            losses, ws = [], []
            for j in range(0, len(obs_val), 8192):
                sl = slice(j, j + 8192)
                losses.append(float(_loss_fn(_mean(obs_val[sl]), act_val[sl], mask_val[sl])))
                ws.append(len(obs_val[sl]))
        return float(np.average(losses, weights=ws))

    base = float(_loss_fn(th.zeros_like(act_val), act_val, mask_val)) if args.loss == "mse" else None
    print(f"  train/val = {len(tr_idx):,}/{len(val_idx):,}  |  loss = {args.loss}"
          + (f"  |  base (predecir 0) = {base:.4f}" if base is not None else ""))

    best_val, best_state, best_epoch, sin_mejora = float("inf"), None, -1, 0
    history = []
    g = th.Generator().manual_seed(args.seed)
    for epoch in range(args.epochs):
        policy.set_training_mode(True)
        perm = th.randperm(len(obs_tr), generator=g)
        tr_losses = []
        for j in range(0, len(perm), args.batch_size):
            b = perm[j:j + args.batch_size]
            loss = _loss_fn(_mean(obs_tr[b]), act_tr[b], mask_tr[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tr_losses.append(loss.item())
        vl = _val_loss()
        history.append({"epoch": epoch, "train_loss": float(np.mean(tr_losses)), "val_loss": vl})
        print(f"  época {epoch:2d}: train {args.loss} = {np.mean(tr_losses):.5f}  |  val {args.loss} = {vl:.5f}",
              flush=True)
        if vl < best_val - 1e-6:
            best_val, best_epoch, sin_mejora = vl, epoch, 0
            best_state = {k: v.detach().clone() for k, v in policy.state_dict().items()}
        else:
            sin_mejora += 1
            if sin_mejora >= args.patience:
                print(f"  early-stop: {args.patience} épocas sin mejorar val (mejor = época {best_epoch})")
                break

    policy.load_state_dict(best_state)                 # restaura el MEJOR estado por val
    policy.set_training_mode(False)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out))
    cfg = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "demos": args.demos, "n_pairs": int(n),
        "split": {"train": int(len(tr_idx)), "val": int(len(val_idx))},
        "hyper": {"epochs_max": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
                  "patience": args.patience, "seed": args.seed, "net_arch": NET_ARCH},
        "loss": args.loss + " (enmascarada: solo slots de lobos PRESENTES, flag de la obs)",
        "base_val": base,
        "mejor": {"epoch": best_epoch, "val_loss": best_val},
        "history": history,
        "nota": "solo la POLÍTICA entrenada por MSE; value net y log_std con su init (frescos)",
    }
    Path(str(out).replace(".zip", "_config.json")).write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"  mejor val {args.loss} = {best_val:.5f} (época {best_epoch})")
    print(f"  guardado -> {out} (+ bc_model_config.json)")


if __name__ == "__main__":
    main()
