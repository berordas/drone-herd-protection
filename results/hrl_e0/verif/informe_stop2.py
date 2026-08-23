"""informe_stop2.py — Genera /data/hrl_e0/e01/REPORT.md y /data/hrl_e0/e02/REPORT.md a partir
de los results.json (script efímero de la etapa; los números salen de los JSON, nada se
recalcula aquí salvo formateo)."""
import json
import pathlib

BASE = pathlib.Path("/data/hrl_e0")


def fmt_ci(v):
    if not v or v[0] is None:
        return "—"
    s = f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    if len(v) > 3:
        s += f" (n={v[3]})"
    return s


def dist(d):
    if not d:
        return "—"
    return (f"media {d['media']:.2f} · mediana {d['mediana']:.0f} · P(0) {d['p_sev0']:.0%} · "
            f"P(≥4) {d['p_sev4mas']:.0%} · hist {d['hist']}")


def tasas(t):
    if not t:
        return "—"
    o = t.get("oportunidad_ticks_hasta_staged")
    p = t["escolta_prematura"]
    return (f"staged {t['staged']:.0%} · commit {t['commit']:.0%} · kill-post-release "
            f"{t['kill_post_release']:.0%} · t→staged {fmt_ci(o) if o else '—'} · ESCOLTA prematura "
            f"{p['frac']:.0%} (señuelo {p['confirmado_primero_senuelo']}/asalto "
            f"{p['confirmado_primero_asalto']}, →corzo {p['investigador_hacia_corzo']}, borde "
            f"{p['pinzamiento_borde']})")


def prov(p):
    if not p or p.get("n_muertes", 0) == 0:
        return "sin muertes"
    return (f"n={p['n_muertes']} · KNC {p['knc']:.0%} · gotera {p['gotera']:.0%} · ternero "
            f"{p['por_ternero']:.0%} · octantes {p['octantes']}")


def e01():
    r = json.load(open(BASE / "e01" / "results.json"))["resumen"]
    L = ["# E0.1 — Margen Δ del cebo (estratificado, adenda tras STOP-1)", ""]
    pil = r["piloto"]
    L += [f"Piloto (G, CEBO_keep vs MASA vs Reactive, {pil['n']} pares): Δ̂={pil['delta_hat']:+.3f}, "
          f"σ̂={pil['sigma']:.3f} → n confirmatoria = **{pil['n_pares_confirmatoria']} pares**.", ""]
    L += ["| celda | Δsev (CEBO−MASA) IC95 | n3 | n4 | n5 |", "|---|---|---|---|---|"]
    for k, v in r.items():
        if not isinstance(v, dict) or "delta" not in v:
            continue
        d = v["delta"]
        L.append(f"| {k} | **{fmt_ci(d.get('todos'))}** | {fmt_ci(d.get('n3'))} | "
                 f"{fmt_ci(d.get('n4'))} | {fmt_ci(d.get('n5'))} |")
    L += ["", f"Mejor Δ en S: **{r.get('S_mejor_delta')}°**", ""]
    for k, v in r.items():
        if not isinstance(v, dict) or "delta" not in v:
            continue
        L += [f"## {k}", "",
              f"- distribución CEBO: {dist(v['dist']['cebo'])}",
              f"- distribución MASA: {dist(v['dist']['masa'])}",
              f"- procedencia CEBO: {prov(v['procedencia']['cebo'])}",
              f"- procedencia MASA: {prov(v['procedencia']['masa'])}",
              f"- tasas CEBO: {tasas(v['tasas']['cebo'])}",
              f"- tasas MASA: {tasas(v['tasas']['masa'])}", ""]
    (BASE / "e01" / "REPORT.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:20]))


def e02():
    r = json.load(open(BASE / "e02" / "results.json"))
    L = ["# E0.2 — Latencias → K (adenda §6)", "",
         f"**Regla pre-registrada:** {r['regla_preregistrada']}", "",
         f"p75 t(inicio→LURE_COMMIT) en celdas del manager: {r['p75_inicio_commit_manager']} · "
         f"celdas sin commit: {r.get('celdas_manager_sin_commit')}", "",
         f"K propuesto: {r['K_propuesto']} · frac. episodios lobos con ≥5 decisiones: "
         f"{r['frac_eps_con_5_decisiones']}", "",
         f"ROC LURE_COMMIT — mejor Youden: {r['roc_mejor']}", "",
         "| celda | inicio→staged p50/p75/p90 (n) | staged→show | show→confirm | inicio→commit p50/p75/p90 (n) | release→muerte p50/p90 (n) |",
         "|---|---|---|---|---|---|"]

    def q(d):
        return "—" if not d else f"{d['p50']:.0f}/{d['p75']:.0f}/{d['p90']:.0f} ({d['n']})"

    def q2(d):
        return "—" if not d else f"{d['p50']:.0f}/{d['p90']:.0f} ({d['n']})"
    for c, lat in r["latencias"].items():
        L.append(f"| {c} | {q(lat['inicio_staged'])} | {q(lat['staged_show'])} | "
                 f"{q(lat['show_confirm'])} | {q(lat['inicio_commit'])} | {q2(lat['release_muerte'])} |")
    L += ["", "| celda | T_safe (ESCOLTA→a salvo) p50/p75/p90 (n) | margen release p25/p50/p75 · P(<0) |",
          "|---|---|---|"]
    for c, t in r["reloj_escolta"].items():
        m = t["margen_release"]
        ms = "—" if not m else f"{m['p25']:.0f}/{m['p50']:.0f}/{m['p75']:.0f} · {m['p_negativo']:.0%} (n={m['n']})"
        L.append(f"| {c} | {q(t['T_safe'])} | {ms} |")
    L += ["", "## ROC completa (cono 60°)", "", "| min_drones | puerta m | TPR | FPR | Youden |", "|---|---|---|---|---|"]
    for row in r["roc"]:
        L.append(f"| {row['min_drones']} | {row['gate_m']:.0f} | {row['tpr']} | {row['fpr']} | {row['youden']} |")
    (BASE / "e02" / "REPORT.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    import sys
    {"e01": e01, "e02": e02}[sys.argv[1]]()
