"""penetrado_tradeoff.py — gráfica del trade-off cobertura/reparto (firma STOP-D2: GRAFICAR, no arreglar).
Entrada: e04_<defensa>__<atacante>.json (100 pares por celda). Salida: penetrado_tradeoff.png + .json.
Panel por atacante: x = PENETRADO medio (ticks con algún lobo dentro de la línea), y = sev media.
Panel 4: subconjunto de episodios con 2 frentes (two_front) — donde vive el hallazgo 36 vs 49."""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

B = "/data/hrl_d2"
RUN = sys.argv[1] if len(sys.argv) > 1 else "dronemgr"
DEFS = [("reactive", "Reactive 4-0", "tab:red", "s"), ("run09", "MARL run09", "tab:gray", "v"),
        ("proporcional", "Proporcional (listón)", "tab:blue", "o"), (RUN, "Manager dron D2", "tab:green", "*")]
ATKS = [("natural", "mezcla natural"), ("cebo2f", "cebo scriptado 2f"), ("manager", "manager lobo M1''''")]
rng = np.random.default_rng(1)


def ci(v):
    v = np.asarray(v, float)
    if v.size == 0:
        return (np.nan, np.nan, np.nan)
    b = v[rng.integers(0, v.size, size=(5000, v.size))].mean(axis=1)
    return (float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


pts = {}
fig, axs = plt.subplots(1, 4, figsize=(18, 4.6))
for j, (a, atit) in enumerate(ATKS):
    ax = axs[j]
    for d, lab, col, mk in DEFS:
        try:
            r = json.load(open(f"{B}/e04_{d}__{a}.json"))
        except FileNotFoundError:
            continue
        eps = r["episodes"]
        pen = ci([e["penetrado"] for e in eps]); sev = ci([e["sev"] for e in eps])
        pts[f"{d}|{a}"] = {"penetrado": pen, "sev": sev, "n": len(eps)}
        ax.errorbar(pen[0], sev[0], xerr=[[pen[0] - pen[1]], [pen[2] - pen[0]]],
                    yerr=[[sev[0] - sev[1]], [sev[2] - sev[0]]], fmt=mk, color=col, ms=11 if mk == "*" else 7,
                    capsize=3, label=lab if j == 0 else None)
        ax.annotate(d, (pen[0], sev[0]), textcoords="offset points", xytext=(6, 4), fontsize=8, color=col)
    ax.set_title(f"atacante: {atit}"); ax.set_xlabel("PENETRADO medio (ticks)"); ax.set_ylabel("sev media")
    ax.grid(alpha=0.3)
# Panel 4: solo episodios de 2 frentes, proporcional vs manager, por atacante
ax = axs[3]
for a, atit in ATKS:
    for d, lab, col, mk in DEFS[2:]:
        try:
            r = json.load(open(f"{B}/e04_{d}__{a}.json"))
        except FileNotFoundError:
            continue
        eps = [e for e in r["episodes"] if e.get("two_front")]
        if not eps:
            continue
        pen = ci([e["penetrado"] for e in eps]); sev = ci([e["sev"] for e in eps])
        pts[f"{d}|{a}|2f"] = {"penetrado": pen, "sev": sev, "n": len(eps)}
        ax.errorbar(pen[0], sev[0], xerr=[[pen[0] - pen[1]], [pen[2] - pen[0]]],
                    yerr=[[sev[0] - sev[1]], [sev[2] - sev[0]]], fmt=mk, color=col, ms=11 if mk == "*" else 7, capsize=3)
        ax.annotate(f"{d[:4]}·{a} (n={len(eps)})", (pen[0], sev[0]), textcoords="offset points", xytext=(6, 4), fontsize=7, color=col)
ax.set_title("solo episodios con 2 frentes"); ax.set_xlabel("PENETRADO medio (ticks)"); ax.set_ylabel("sev media (2f)")
ax.grid(alpha=0.3)
axs[0].legend(fontsize=8, loc="upper left")
fig.suptitle("Trade-off cobertura/reparto — PENETRADO (línea de dos se penetra más) vs severidad; IC bootstrap 95 % (100 pares/celda)", fontsize=10)
fig.tight_layout()
out = f"{B}/penetrado_tradeoff{'' if RUN == 'dronemgr' else '_' + RUN}"
fig.savefig(out + ".png", dpi=130)
json.dump(pts, open(out + ".json", "w"), indent=1)
for k, v in pts.items():
    print(f"{k:28s} pen {v['penetrado'][0]:7.1f} [{v['penetrado'][1]:.0f},{v['penetrado'][2]:.0f}]  sev {v['sev'][0]:.2f} [{v['sev'][1]:.2f},{v['sev'][2]:.2f}]  n={v['n']}")
print("TRADEOFF_OK", out + ".png")
