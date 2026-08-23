"""v34_split_frentes.py — DIAGNÓSTICO 1 (solo lectura): severidad 1-frente vs 2-frentes DENTRO de
v3.4, contrastada con v3.2, desde los ARTEFACTOS por-episodio del arnés (mismas 100 semillas/tipo).

Aísla: (a) episodios de 1 GRUPO — el camino del lobo es IDÉNTICO v3.2≡v3.4 (la inversión v3.3 solo
toca el despachador de 2 sectores) → el Δ es PURO de la defensa (trinquete + línea rígida sin
cierres); (b) episodios de 2 GRUPOS — Δ = defensa nueva + CEBO INVERTIDO. El nº de grupos por
(tipo, semilla) es determinista del substream de spawn (idéntico en ambas versiones): se lee con
un reset barato, sin correr episodios.
"""
import sys, json
import numpy as np

sys.path.insert(0, "/workspace")
from baseline import build_world

V34 = "/workspace/baseline_v2_reactive.json"
V32 = "/data/wolves/diag/reactive_v32_artifact.json"
V34_D = "/workspace/baseline_v2.json"
V32_D = "/data/wolves/diag/dummy_v32_artifact.json"


def groups_of(kind, seed):
    w = build_world(seed, kind)
    w.reset()
    return len(w.wolf_group_sizes)


def split(path, gmap):
    d = json.load(open(path))
    out = {}
    for kind in ("lobos", "mixto"):
        eps = d["by_kind"][kind]["episodes"]
        seeds = d["seeds"]
        assert len(eps) == len(seeds)
        sev1 = [e["n_depredadas"] for s, e in zip(seeds, eps) if gmap[(kind, s)] == 1]
        sev2 = [e["n_depredadas"] for s, e in zip(seeds, eps) if gmap[(kind, s)] == 2]
        out[kind] = (np.array(sev1, float), np.array(sev2, float))
    return out


def fmt(a):
    if a.size == 0:
        return "n=0"
    return f"{a.mean():.2f}±{a.std() / np.sqrt(a.size):.2f} (n={a.size})"


gmap = {(k, s): groups_of(k, s) for k in ("lobos", "mixto") for s in range(100)}
n2 = {k: sum(1 for s in range(100) if gmap[(k, s)] == 2) for k in ("lobos", "mixto")}
print(f"episodios de 2 grupos: lobos {n2['lobos']}/100 · mixto {n2['mixto']}/100 (idéntico v3.2/v3.4: spawn intacto)\n")

r32, r34 = split(V32, gmap), split(V34, gmap)
d32, d34 = split(V32_D, gmap), split(V34_D, gmap)

print("=== REACTIVE: severidad media±SEM por nº de FRENTES ===")
print(f"{'':10s} {'v3.2 (1 fr)':>22s} {'v3.4 (1 fr)':>22s} {'Δ1fr':>7s} | {'v3.2 (2 fr)':>22s} {'v3.4 (2 fr)':>22s} {'Δ2fr':>7s}")
for kind in ("lobos", "mixto"):
    a1, a2 = r32[kind]
    b1, b2 = r34[kind]
    print(f"{kind:10s} {fmt(a1):>22s} {fmt(b1):>22s} {b1.mean() - a1.mean():+7.2f} | "
          f"{fmt(a2):>22s} {fmt(b2):>22s} {b2.mean() - a2.mean():+7.2f}")
print("\n  Δ1fr = efecto PURO de la defensa nueva (trinquete + línea rígida; lobo idéntico)")
print("  Δ2fr − Δ1fr ≈ premio del CEBO INVERTIDO (sobre la misma defensa)")
print("\n=== dentro de v3.4: premio del cebo = 2fr − 1fr (misma versión) ===")
for kind in ("lobos", "mixto"):
    b1, b2 = r34[kind]
    sem = np.sqrt(b1.std() ** 2 / b1.size + b2.std() ** 2 / b2.size)
    print(f"  {kind}: 2fr {b2.mean():.2f} − 1fr {b1.mean():.2f} = {b2.mean() - b1.mean():+.2f} (SEM comb {sem:.2f})")
    a1, a2 = r32[kind]
    sem32 = np.sqrt(a1.std() ** 2 / a1.size + a2.std() ** 2 / a2.size)
    print(f"    (v3.2 era: 2fr {a2.mean():.2f} − 1fr {a1.mean():.2f} = {a2.mean() - a1.mean():+.2f}, SEM {sem32:.2f})")

print("\n=== DUMMY (control): mismo desglose ===")
for kind in ("lobos", "mixto"):
    a1, a2 = d32[kind]
    b1, b2 = d34[kind]
    print(f"  {kind}: 1fr {a1.mean():.2f}->{b1.mean():.2f} ({b1.mean() - a1.mean():+.2f}) | "
          f"2fr {a2.mean():.2f}->{b2.mean():.2f} ({b2.mean() - a2.mean():+.2f})")
