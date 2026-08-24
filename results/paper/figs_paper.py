"""figs_paper.py — figuras del paper (solo lectura de artefactos; ningún run). PNG 300 dpi, ancho de columna
8.5 cm (o 17.5 cm doble columna donde se indica), sin rutas personales. Uso: python3 figs_paper.py [--lang es|en]
Todas las cadenas visibles viven en LABELS; la lógica de datos es idéntica en ambos idiomas.
fig_cebo_frames: en EN usa los fotogramas RE-RENDERIZADOS (rerender_seed98.py, cabecera/leyenda traducidas)
si existen en figs_en/_frame_<name>_en.png; si no, recorta la franja de cabecera y lo anota en figs_notas.json."""
import os, sys, json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch
from PIL import Image
LANG = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "es"
D = "/data"; OUT = f"{D}/paper/figs" if LANG == "es" else f"{D}/paper/figs_{LANG}"
os.makedirs(OUT, exist_ok=True)
COL, DBL = 8.5 / 2.54, 17.5 / 2.54
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "legend.fontsize": 6,
                     "xtick.labelsize": 6, "ytick.labelsize": 6, "font.family": "DejaVu Sans"})
C_CEBO, C_MASA = "#2a7f3f", "#7a7a7a"

LABELS = {
 "es": {
  "valle_cebo": "CEBO_keep ({v})", "valle_masa": "MASA ({v})", "valle_cruce": "cruce {v}: t≈{t}",
  "valle_x": "tick del episodio", "valle_y": "muertes acumuladas (media por episodio)",
  "valle_title": "Valle del cebo (estrato G, vs Reactive): {n5} pares v3.5 · {n4} pares v3.4",
  "atk": {"natural": "mezcla natural", "cebo2f": "cebo scriptado 2f", "manager": "manager lobo"},
  "def": {"reactive": "Reactive 4-0", "proporcional": "proporcional", "dronemgr": "manager dron (seed 0)", "dronemgr_r1": "manager dron (seed 1)"},
  "to_x": "PENETRADO (ticks con lobo dentro de la línea; escala log)", "to_y": "severidad (muertes/episodio)",
  "to_title": "Trade-off cobertura/reparto (100 pares por celda; IC 95 %)",
  "to_ancho_title": "atacante: {a}", "to_ancho_x": "PENETRADO (ticks)", "to_ancho_y": "severidad",
  "fr_panels": ["(a) muestra — t = 1231", "(b) suelta — t = 1419", "(c) golpe — t = 2375"],
  "fr_ann": {"decoy_show": "señuelo (muestra)", "assault_ready": "asalto a tiro", "herd": "rebaño", "patrol": "patrulla (4 drones)",
             "shelter": "establo", "station": "estación", "decoy_released": "señuelo suelto", "assault_detected": "asalto detectado",
             "drone_invest": "dron investiga", "assault_confirmed": "asalto confirmado", "wolves_in_herd": "lobos en el rebaño", "barrier": "drones (barrera)"},
  "fr_sup": "Jugada entera del manager lobo (seed 98, mixto, estrato S, opción Δ90): preparado 901 → muestra 1231 → suelta 1419 → golpe 2375; sev 2",
  "hm_rows": ["G, n=3", "G, n=4", "G, n=5", "S, n=1", "S, n=2", "S, n=3", "S, n=4", "S, n=5"],
  "hm_acts": ["MASA", "CEBO keep", "CEBO Δ90", "CEBO Δ180"],
  "hm_title": "(a) P(1ª opción | estrato, n lobos), run principal vs Reactive\n200 episodios = 100 semillas × {lobos, mixto}", "hm_row_n": "{l} (n={n})",
  "lig_cebo": "P(CEBO | G, n≥3)", "lig_d90": "P(Δ90 | S)", "lig_keep": "P(keep | G)", "lig_sev": "severidad (ligera)",
  "lig_x": "macro-pasos de PPO", "lig_y": "probabilidad (ligera, 40 semillas)", "lig_y2": "severidad media (ligera)",
  "lig_title": "(b) emergencia en la ligera\ndel run principal (40 semillas)",
  "mu_shelter": "establo\n(zona segura, r = 60 m)", "mu_station": "estación de carga\n(r = 25 m, plazas fijas)",
  "mu_herd": "rebaño (pasto, ±40 m)", "mu_drone": "dron", "mu_exp": "expulsión 20 m", "mu_conf": "confirmación 40 m", "mu_det": "detección 100 m",
  "mu_wolves": "lobos\n(4 m/s)", "mu_flee": "huida al establo\n(vacas 1,2 m/s)", "mu_head": "parcela 500 × 500 m · dt = 0,1 s · drones 15 m/s", "mu_axis": "m",
 },
 "en": {
  "valle_cebo": "DECOY_keep ({v})", "valle_masa": "MASS ({v})", "valle_cruce": "crossing {v}: t≈{t}",
  "valle_x": "episode tick", "valle_y": "cumulative kills (mean per episode)",
  "valle_title": "Decoy valley (stratum G, vs Reactive): {n5} pairs v3.5 · {n4} pairs v3.4",
  "atk": {"natural": "natural mix", "cebo2f": "scripted 2-front decoy", "manager": "wolf manager"},
  "def": {"reactive": "Reactive 4-0", "proporcional": "proportional", "dronemgr": "drone manager (seed 0)", "dronemgr_r1": "drone manager (seed 1)"},
  "to_x": "line penetrations (ticks with a wolf inside the line; log scale)", "to_y": "severity (livestock lost/episode)",
  "to_title": "Coverage/split trade-off (100 pairs per cell; 95 % CI)",
  "to_ancho_title": "attacker: {a}", "to_ancho_x": "line penetrations (ticks)", "to_ancho_y": "severity",
  "fr_panels": ["(a) show — t = 1231", "(b) release — t = 1419", "(c) strike — t = 2375"],
  "fr_ann": {"decoy_show": "decoy (show)", "assault_ready": "assault in range", "herd": "herd", "patrol": "patrol (4 drones)",
             "shelter": "shelter", "station": "charging station", "decoy_released": "decoy released", "assault_detected": "assault detected",
             "drone_invest": "drone investigating", "assault_confirmed": "assault confirmed", "wolves_in_herd": "wolves in the herd", "barrier": "drones (barrier)"},
  "fr_sup": "Full play of the wolf manager (seed 98, mixed, stratum S, option Δ90): staged 901 → show 1231 → release 1419 → strike 2375; severity 2",
  "hm_rows": ["G, n=3", "G, n=4", "G, n=5", "S, n=1", "S, n=2", "S, n=3", "S, n=4", "S, n=5"],
  "hm_acts": ["MASS", "DECOY keep", "DECOY Δ90", "DECOY Δ180"],
  "hm_title": "(a) P(first option | stratum, n wolves), main run vs Reactive\n200 episodes = 100 seeds × {wolves, mixed}", "hm_row_n": "{l} (n={n})",
  "lig_cebo": "P(DECOY | G, n≥3)", "lig_d90": "P(Δ90 | S)", "lig_keep": "P(keep | G)", "lig_sev": "severity (light eval)",
  "lig_x": "PPO macro-steps", "lig_y": "probability (light eval, 40 seeds)", "lig_y2": "mean severity (light eval)",
  "lig_title": "(b) emergence during training\nmain run (light eval, 40 seeds)",
  "mu_shelter": "shelter\n(safe zone, r = 60 m)", "mu_station": "charging station\n(r = 25 m, fixed slots)",
  "mu_herd": "herd (grazing, ±40 m)", "mu_drone": "drone", "mu_exp": "expulsion 20 m", "mu_conf": "confirmation 40 m", "mu_det": "detection 100 m",
  "mu_wolves": "wolves\n(4 m/s)", "mu_flee": "flight to shelter\n(cows 1.2 m/s)", "mu_head": "plot 500 × 500 m · dt = 0.1 s · drones 15 m/s", "mu_axis": "m",
 },
}
L = LABELS[LANG]
notes = {}

# ------------------------------------------------------------------ fig_valle
def valle(path, T=23570):
    r = json.load(open(path)); eps = r["episodes"]
    cebo = {(e["seed"], e["kind"]): e for e in eps if e["arm"] == "cebo_keep_h50_reactive"}
    masa = {(e["seed"], e["kind"]): e for e in eps if e["arm"] == "masa_reactive"}
    keys = sorted(set(cebo) & set(masa))
    def curve(dic):
        acc = np.zeros(T + 1)
        for k in keys:
            for d in dic[k]["deaths"]:
                acc[min(int(d["t"]), T):] += 1
        return acc / len(keys)
    c, m = curve(cebo), curve(masa); diff = c - m
    behind = np.where(diff < 0)[0]
    cross = int(np.where(diff[behind[0]:] >= 0)[0][0] + behind[0]) if behind.size else None
    return c, m, cross, len(keys)
c5, m5, x5, n5 = valle(f"{D}/hrl_e0/v35/e01/results.json")
c4, m4, x4, n4 = valle(f"{D}/hrl_e0/e01/results.json")
notes["valle"] = {"v35_cruce": x5, "v35_pares": n5, "v34_cruce": x4, "v34_pares": n4,
                  "v35_t1000": (round(c5[1000], 2), round(m5[1000], 2)), "v35_t2000": (round(c5[2000], 2), round(m5[2000], 2)),
                  "v35_final": (round(c5[-1], 2), round(m5[-1], 2)), "v34_final": (round(c4[-1], 2), round(m4[-1], 2))}
fig, ax = plt.subplots(figsize=(COL, COL * 0.72)); t = np.arange(len(c5)); TM = 8000
ax.plot(t[:TM], c5[:TM], color=C_CEBO, lw=1.3, label=L["valle_cebo"].format(v="v3.5"))
ax.plot(t[:TM], m5[:TM], color=C_MASA, lw=1.3, label=L["valle_masa"].format(v="v3.5"))
ax.plot(t[:TM], c4[:TM], color=C_CEBO, lw=0.9, ls=":", label=L["valle_cebo"].format(v="v3.4"))
ax.plot(t[:TM], m4[:TM], color=C_MASA, lw=0.9, ls=":", label=L["valle_masa"].format(v="v3.4"))
for x, c, lab in [(x5, c5, "v3.5"), (x4, c4, "v3.4")]:
    if x:
        ax.plot([x], [c[x]], "o", color="k", ms=3.5, zorder=5)
        ax.annotate(L["valle_cruce"].format(v=lab, t=x), (x, c[x]), xytext=(8, -14 if lab == "v3.5" else 10), textcoords="offset points", fontsize=6, arrowprops=dict(arrowstyle="-", lw=0.5))
ax.fill_between(t[:x5 + 1], c5[:x5 + 1], m5[:x5 + 1], color=C_CEBO, alpha=0.12, lw=0)
ax.set_xlabel(L["valle_x"]); ax.set_ylabel(L["valle_y"]); ax.set_title(L["valle_title"].format(n5=n5, n4=n4), fontsize=7)
ax.legend(loc="lower right", frameon=False); ax.grid(alpha=0.25, lw=0.4)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_valle.png", dpi=300); plt.close(fig)

# ------------------------------------------------------------------ fig_tradeoff (columna) + ancho (3 paneles)
ATK = [("natural", "#1f77b4"), ("cebo2f", "#d62728"), ("manager", "#9467bd")]
DEF = [("reactive", "s"), ("proporcional", "o"), ("dronemgr", "*"), ("dronemgr_r1", "P")]
rng = np.random.default_rng(1)
def ci(v):
    v = np.asarray(v, float); b = v[rng.integers(0, v.size, size=(5000, v.size))].mean(axis=1)
    return float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
pts = {}
for a, _ in ATK:
    for d, _ in DEF:
        eps = json.load(open(f"{D}/hrl_d2/e04_{d}__{a}.json"))["episodes"]
        pts[(d, a)] = (ci([e["penetrado"] for e in eps]), ci([e["sev"] for e in eps]), len(eps))
fig, ax = plt.subplots(figsize=(COL, COL * 0.9))
for a, col in ATK:
    xs = []
    for d, mk in DEF:
        (p, pl, ph), (s, sl, sh), n = pts[(d, a)]; p1 = max(p, 1)
        ax.errorbar(p1, s, xerr=[[p1 - max(pl, 1)], [ph - p1]], yerr=[[s - sl], [sh - s]], fmt=mk, color=col,
                    ms=7 if mk == "*" else 4.5, mfc=col if d != "dronemgr_r1" else "white", capsize=1.5, elinewidth=0.5, lw=0.5)
        xs.append((p1, s))
    ax.plot([x for x, _ in xs[1:]], [y for _, y in xs[1:]], color=col, lw=0.6, alpha=0.6)
    ax.annotate(L["atk"][a], {"natural": (22, 0.40), "cebo2f": (110, 1.30), "manager": (28, 0.98)}[a], fontsize=6, color=col, ha="left")
for d, mk in DEF:
    ax.plot([], [], mk, color="k", mfc="k" if d != "dronemgr_r1" else "white", ms=6 if mk == "*" else 4, label=L["def"][d])
ax.set_xscale("log"); ax.set_xlabel(L["to_x"]); ax.set_ylabel(L["to_y"]); ax.set_title(L["to_title"], fontsize=7)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2); ax.grid(alpha=0.25, lw=0.4, which="both")
fig.tight_layout(); fig.savefig(f"{OUT}/fig_tradeoff.png", dpi=300); plt.close(fig)
fig, axs = plt.subplots(1, 3, figsize=(DBL, DBL * 0.36))
for ax, (a, col) in zip(axs, ATK):
    for d, mk in DEF:
        (p, pl, ph), (s, sl, sh), n = pts[(d, a)]; c = col if d != "reactive" else "#444"
        ax.errorbar(p, s, xerr=[[p - pl], [ph - p]], yerr=[[s - sl], [sh - s]], fmt=mk, color=c, ms=7 if mk == "*" else 4.5,
                    mfc=c if d != "dronemgr_r1" else "white", capsize=1.5, elinewidth=0.5, lw=0.5, label=L["def"][d])
    ax.set_title(L["to_ancho_title"].format(a=L["atk"][a])); ax.set_xlabel(L["to_ancho_x"]); ax.set_ylabel(L["to_ancho_y"]); ax.grid(alpha=0.25, lw=0.4)
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
fig.tight_layout(rect=(0, 0.09, 1, 1)); fig.savefig(f"{OUT}/fig_tradeoff_ancho.png", dpi=300); plt.close(fig)
notes["tradeoff"] = {f"{d}|{a}": {"pen": round(pts[(d, a)][0][0], 1), "sev": round(pts[(d, a)][1][0], 2)} for (d, a) in pts}

# ------------------------------------------------------------------ fig_cebo_frames
GIF = f"{D}/hrl_m1/m1pppp/visionado/gifs/jugada_entera_S_seed98_mixto_sev2.gif"
X0, X1, Y0, Y1 = 90.0, 628.0, 621.0, 85.0       # píxeles del eje [0,500] en el render 700x700
FR = [("show", 1230), ("suelta", 1419), ("strike", 2373)]  # índice del snapshot (tick); frame del GIF = tick // 3; el re-render usa el mismo snapshot
rerender = all(os.path.exists(f"{OUT}/_frame_{n}_{LANG}.png") for n, _ in FR)
header_crop = (LANG != "es") and not rerender
CROP = (88, 84, 631, 492) if not header_crop else (88, 124, 631, 492)   # recorte de la franja de cabecera si no hay re-render
def w2p(x, y):
    return X0 + x / 500 * (X1 - X0) - CROP[0], Y0 - y / 500 * (Y0 - Y1) - CROP[1]
A = L["fr_ann"]
PANELS = [
    (L["fr_panels"][0], FR[0], [(A["decoy_show"], (339, 492), (440, 400)), (A["assault_ready"], (342, 257), (420, 215)), (A["herd"], (150, 363), (55, 440)),
                                 (A["patrol"], (214, 304), (110, 210)), (A["shelter"], (250, 250), (330, 150)), (A["station"], (250, 342), (320, 452))]),
    (L["fr_panels"][1], FR[1], [(A["decoy_released"], (286, 458), (400, 445)), (A["assault_detected"], (339, 276), (420, 230)), (A["drone_invest"], (297, 283), (380, 160)),
                                 (A["herd"], (149, 360), (55, 440))]),
    (L["fr_panels"][2], FR[2], [(A["assault_confirmed"], (246, 309), (420, 385)), (A["wolves_in_herd"], (167, 327), (60, 440)), (A["barrier"], (240, 350), (330, 452)),
                                 (A["shelter"], (250, 250), (330, 150))]),
]
def frame_image(name, idx):
    if rerender:
        return Image.open(f"{OUT}/_frame_{name}_{LANG}.png").convert("RGB")
    im = Image.open(GIF); im.seek(idx // 3); return im.convert("RGB")   # frame del GIF = tick // 3
def draw_panels(axs):
    for ax, (title, (name, idx), anns) in zip(axs, PANELS):
        ax.imshow(frame_image(name, idx).crop(CROP)); ax.set_title(title, loc="left"); ax.set_xticks([]); ax.set_yticks([])
        for lab, tgt, txt in anns:
            ax.annotate(lab, xy=w2p(*tgt), xytext=w2p(*txt), fontsize=5.5, ha="center",
                        arrowprops=dict(arrowstyle="->", lw=0.6, color="#b3001b"), color="#b3001b",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
fig, axs = plt.subplots(1, 3, figsize=(DBL, DBL / 3 * 0.86)); draw_panels(axs)
fig.suptitle(L["fr_sup"], fontsize=6.5); fig.tight_layout(); fig.savefig(f"{OUT}/fig_cebo_frames.png", dpi=300); plt.close(fig)
fig, axs = plt.subplots(3, 1, figsize=(COL, COL * 2.4)); draw_panels(axs)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_cebo_frames_col.png", dpi=300); plt.close(fig)
notes["cebo_frames"] = {"fuente": ("re-render (rerender_seed98.py, código v3.7 pineado, textos traducidos en la figura)" if rerender else "GIF original"),
                        "cabecera": ("re-render" if rerender else ("recortada" if header_crop else "original")), "crop_px": CROP, "frames": FR}

# ------------------------------------------------------------------ fig_heatmap: P(acción | estrato, n) + curva de la ligera
r = json.load(open(f"{D}/hrl_m1/eval/manager_M1pppp_final__reactive.json")); P = r["resumen"]["P_a_first"]
keys = ["G_n3", "G_n4", "G_n5", "S_n1", "S_n2", "S_n3", "S_n4", "S_n5"]; acts = ["MASA", "CEBO_keep", "CEBO_d90", "CEBO_d180"]
M = np.array([[P[k][a] for a in acts] for k in keys]); cnt = {}
for e in r["episodes"]:
    k = ("G" if e["two_front"] else "S") + f"_n{e['n_wolves']}"; cnt[k] = cnt.get(k, 0) + 1
LG = [json.loads(l) for l in open(f"{D}/hrl_m1/M1pppp/eval_ligera.jsonl")]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(DBL, DBL * 0.36), gridspec_kw={"width_ratios": [1, 1.3]})
a1.title.set_fontsize(6.5)
a1.imshow(M, cmap="Greens", vmin=0, vmax=1, aspect="auto")
a1.set_xticks(range(4)); a1.set_xticklabels(L["hm_acts"], rotation=20); a1.set_yticks(range(len(keys)))
a1.set_yticklabels([L["hm_row_n"].format(l=l, n=cnt.get(k, 0)) for l, k in zip(L["hm_rows"], keys)])
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        a1.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=5.5, color="white" if M[i, j] > 0.6 else "black")
a1.set_title(L["hm_title"])
steps = [d["pasos"] for d in LG]
a2.plot(steps, [d["P_cebo_G_n3"] for d in LG], "-o", ms=2.5, color=C_CEBO, label=L["lig_cebo"])
a2.plot(steps, [d["P_a_S_first"]["CEBO_d90"] for d in LG], "-s", ms=2.5, color="#1f77b4", label=L["lig_d90"])
a2.plot(steps, [d["P_a_G_first"]["CEBO_keep"] for d in LG], "-^", ms=2.5, color="#e6a100", label=L["lig_keep"])
a2.set_ylim(-0.03, 1.05); a2.set_xlabel(L["lig_x"]); a2.set_ylabel(L["lig_y"])
a2b = a2.twinx(); a2b.plot(steps, [d["sev_media"] for d in LG], "--", color="#b3001b", lw=0.9, label=L["lig_sev"])
a2b.set_ylabel(L["lig_y2"], color="#b3001b"); a2b.tick_params(axis="y", colors="#b3001b")
h1, l1 = a2.get_legend_handles_labels(); h2, l2 = a2b.get_legend_handles_labels(); a2.legend(h1 + h2, l1 + l2, frameon=False, loc="center right")
a2.set_title(L["lig_title"]); a2.grid(alpha=0.25, lw=0.4)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_heatmap.png", dpi=300); plt.close(fig)
notes["heatmap"] = {"P_a_first": {k: P[k] for k in keys}, "ligera_final": {k: LG[-1][k] for k in ("pasos", "P_cebo_G_n3", "aborts_por_ep", "sev_media")}}

# ------------------------------------------------------------------ fig_mundo (esquema)
fig, ax = plt.subplots(figsize=(COL, COL))
ax.add_patch(Rectangle((0, 0), 500, 500, fc="#f4f7ef", ec="#888", lw=0.8))
ax.add_patch(Circle((250, 250), 60, fc="#cfe9cf", ec="#2a7f3f", lw=0.8)); ax.text(250, 250, L["mu_shelter"], ha="center", va="center", fontsize=5.5)
ax.add_patch(Circle((250, 340), 25, fc="#ffe3c2", ec="#e6a100", lw=0.8, ls="--")); ax.text(282, 352, L["mu_station"], ha="left", va="center", fontsize=5.5)
ax.add_patch(Rectangle((60, 330), 80, 70, fc="none", ec="#555", lw=0.8, ls="--")); ax.text(100, 408, L["mu_herd"], ha="center", fontsize=5.5)
dx, dy = 150, 160
ax.add_patch(Circle((dx, dy), 100, fc="none", ec="#1f77b4", lw=0.6, ls=":")); ax.add_patch(Circle((dx, dy), 40, fc="none", ec="#1f77b4", lw=0.6, ls="--")); ax.add_patch(Circle((dx, dy), 20, fc="#cde3f5", ec="#1f77b4", lw=0.8))
ax.plot([dx], [dy], marker="^", color="#1f77b4", ms=5); ax.text(dx + 4, dy + 6, L["mu_drone"], fontsize=5.5, color="#1f77b4")
ax.text(dx, dy - 26, L["mu_exp"], ha="center", fontsize=5, color="#1f77b4"); ax.text(dx, dy - 46, L["mu_conf"], ha="center", fontsize=5, color="#1f77b4"); ax.text(dx, dy - 106, L["mu_det"], ha="center", fontsize=5, color="#1f77b4")
for (wx, wy) in [(470, 282), (481, 306), (464, 322)]:
    ax.plot([wx], [wy], marker="x", color="#b3001b", ms=4, mew=1)
ax.add_patch(FancyArrowPatch((452, 300), (335, 300), arrowstyle="->", mutation_scale=8, color="#b3001b", lw=0.8)); ax.text(472, 262, L["mu_wolves"], ha="center", va="top", fontsize=5.5, color="#b3001b")
ax.add_patch(FancyArrowPatch((140, 345), (202, 282), arrowstyle="->", mutation_scale=8, color="#555", lw=0.8)); ax.text(40, 292, L["mu_flee"], fontsize=5, color="#555")
ax.text(5, 488, L["mu_head"], fontsize=5.5, va="top")
ax.set_xlim(-5, 505); ax.set_ylim(-5, 505); ax.set_aspect("equal"); ax.set_xticks([0, 100, 200, 300, 400, 500]); ax.set_yticks([0, 100, 200, 300, 400, 500]); ax.set_xlabel(L["mu_axis"]); ax.set_ylabel(L["mu_axis"])
fig.tight_layout(); fig.savefig(f"{OUT}/fig_mundo.png", dpi=300); plt.close(fig)

# notas: un solo figs_notas.json en figs/ con ambos idiomas (clave por idioma)
NP = f"{D}/paper/figs/figs_notas.json"
old = json.load(open(NP)) if os.path.exists(NP) else {}
if "valle" in old and LANG != "es" and "es" not in old:   # formato antiguo (solo es) -> anidar
    old = {"es": old}
old[LANG] = {**notes, "dir": OUT, "labels": L}
json.dump(old, open(NP, "w"), indent=1, ensure_ascii=False)
print(json.dumps(notes["valle"]), notes["cebo_frames"]["cabecera"]); print("FIGS_OK", LANG, OUT)
