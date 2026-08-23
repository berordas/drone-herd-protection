"""v31_parte0.py — DIAGNÓSTICO Parte 0 de v3.1 (SOLO LECTURA, sobre v3.0 = b857be1).
(a) ¿Los lobos disparan la alarma "nada más aparecer" por TERRENO corto o por el reflejo?
    Mide por episodio grouped-2: distancias de NACIMIENTO (lobo→vaca más cercana, lobo→ACTIVE más
    cercano), paso de 1ª detección / SOSPECHA / ESCOLTA, y dónde estaba el lobo confirmado (dist al
    rebaño) al disparar ESCOLTA.
(b) ¿Por qué el timing del cebo falla (se confirma antes de que el asalto esté a 150 m)?
    Rastrea el CONTACTO del investigador paso a paso (el reflejo re-elige el cuerpo MÁS CERCANO A ÉL,
    world.py:1539): ¿vira del asalto al CEBO en pleno vuelo? ¿El cebo baja de r_detect mientras espera?
    ¿Quién confirma primero y cómo (investigador vs dron de barrera de paso)?
JSON -> /data/wolves/diag/v31_parte0.json
"""
import sys, json
sys.path.insert(0, "/workspace")
import numpy as np
from baseline import build_world
from coordinators import ReactiveCoordinator
from world import ACTIVE


def sector_of(i, n1):
    return "cebo" if i < n1 else "asalto"


def run_ep(seed):
    w = build_world(seed, "lobos")
    coord = ReactiveCoordinator(w)
    w.reset()
    if len(w.wolf_group_sizes) != 2:
        return None
    n, n1 = int(w.n_wolves), int(w.wolf_group_sizes[0])

    # --- nacimiento ---
    act0 = w.drones[w.drone_state == ACTIVE]
    d_cow0 = np.linalg.norm(w.wolves[:, None, :] - w.cows[None, :, :], axis=2).min(axis=1)
    d_drn0 = np.linalg.norm(w.wolves[:, None, :] - act0[None, :, :], axis=2).min(axis=1)

    prev_conf = np.zeros(n, bool)
    prev_inv = np.zeros(w.n_drones, bool)
    first_detect = sospecha = escolta = release = None
    conf_events = []          # (paso, lobo, sector, dist_rebano, confirmador_era_investigador, dist_conf_drone)
    inv_contact_hist = []     # (paso, dron, id_cuerpo_mas_cercano) para ver VIRAJES del contacto
    decoy_min_ddrn = np.inf   # dist mín del cebo al ACTIVE más cercano mientras espera
    decoy_detected_pre = False
    d2_at_escolta = None      # dist del centroide del asalto a su presa al disparar ESCOLTA

    while True:
        wp = coord.act(w.get_observation())
        conf = coord._confirmed.copy() if coord._confirmed is not None else np.zeros(n, bool)
        herd_mask = w.cow_alive & ~w.cow_safe
        herd_c = w.cows[herd_mask].mean(axis=0) if herd_mask.any() else np.array([w.W/2, w.H/2])
        act = w.drones[w.drone_state == ACTIVE]
        inv_before = w.drone_investigating.copy()
        _o, _r, term, trunc, _i = w.step(wp)
        t = int(w.step_count)

        if act.shape[0] and n:
            dwd = np.linalg.norm(w.wolves[:, None, :] - act[None, :, :], axis=2).min(axis=1)
            if first_detect is None and (dwd <= w.r_detect).any():
                first_detect = t
            if not w.wolf_decoy_released:
                decoy_min_ddrn = min(decoy_min_ddrn, float(dwd[:n1].min()))
                if (dwd[:n1] <= w.r_detect).any():
                    decoy_detected_pre = True
        if sospecha is None and w.phase == "SOSPECHA":
            sospecha = t
        if release is None and w.wolf_decoy_released:
            release = t
        # contacto del investigador: ¿a qué cuerpo apunta? (id del lobo más cercano al dron)
        for i in np.where(w.drone_investigating)[0]:
            if n:
                j = int(np.argmin(np.linalg.norm(w.wolves - w.drones[i], axis=1)))
                if not inv_contact_hist or inv_contact_hist[-1][1] != i or inv_contact_hist[-1][2] != j:
                    inv_contact_hist.append((t, int(i), j))
        # confirmaciones nuevas (criterio del coordinador = 40 de un ACTIVE, igual que el oráculo)
        new = conf & ~prev_conf
        for wi in np.where(new)[0]:
            dw = np.linalg.norm(w.drones - w.wolves[wi], axis=1)
            near = np.where((w.drone_state == ACTIVE) & (dw <= w.r_confirm + 2))[0]
            was_inv = bool(inv_before[near].any()) if near.size else False
            conf_events.append({"paso": t, "lobo": int(wi), "sector": sector_of(wi, n1),
                                "dist_rebano": round(float(np.linalg.norm(w.wolves[wi] - herd_c)), 1),
                                "confirmador_investigador": was_inv})
        prev_conf = conf
        if escolta is None and w.phase == "ESCOLTA":
            escolta = t
            if w.pack_prey2 >= 0:
                p2 = w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind)
                d2_at_escolta = round(float(np.linalg.norm(w.wolves[n1:].mean(axis=0) - p2)), 1)
        if term or trunc:
            break

    # viraje del investigador: ¿su contacto pasó de un lobo del asalto a uno del cebo?
    viraje = False
    for k in range(1, len(inv_contact_hist)):
        t0, i0, j0 = inv_contact_hist[k - 1]
        t1, i1, j1 = inv_contact_hist[k]
        if i0 == i1 and j0 >= n1 and j1 < n1:
            viraje = True
    primera = conf_events[0] if conf_events else None
    return {
        "seed": seed, "n": n, "reparto": f"{n1}+{n - n1}", "sev": int(w.n_depredadas),
        "nacim_dist_vaca_min": round(float(d_cow0.min()), 1),
        "nacim_dist_dron_min": round(float(d_drn0.min()), 1),
        "paso_deteccion": first_detect, "paso_sospecha": sospecha, "paso_escolta": escolta,
        "primera_confirmacion": primera,
        "escolta_con_asalto_a": d2_at_escolta, "paso_release": release,
        "decoy_dist_min_dron_pre_release": round(decoy_min_ddrn, 1) if np.isfinite(decoy_min_ddrn) else None,
        "decoy_detectado_pre_release": decoy_detected_pre,
        "viraje_investigador_asalto_a_cebo": viraje,
        "confirmaciones": conf_events[:6],
    }


rows = []
for s in range(200):
    r = run_ep(s)
    if r is None:
        continue
    rows.append(r)
    p = r["primera_confirmacion"] or {}
    print(f"seed={s:3d} {r['reparto']} sev={r['sev']} | nace: vaca {r['nacim_dist_vaca_min']:.0f} dron {r['nacim_dist_dron_min']:.0f}"
          f" | detec t={r['paso_deteccion']} sosp t={r['paso_sospecha']} ESCOLTA t={r['paso_escolta']}"
          f" | 1a conf: {p.get('sector')} lobo{p.get('lobo')} a {p.get('dist_rebano')} m del rebano"
          f" (investigador={p.get('confirmador_investigador')}) | asalto a {r['escolta_con_asalto_a']} m de su presa"
          f" | release t={r['paso_release']} | cebo minDron {r['decoy_dist_min_dron_pre_release']}"
          f" detectado={r['decoy_detectado_pre_release']} viraje={r['viraje_investigador_asalto_a_cebo']}", flush=True)
    if len(rows) >= 15:
        break

# resumen del veredicto
nac_v = [r["nacim_dist_vaca_min"] for r in rows]
nac_d = [r["nacim_dist_dron_min"] for r in rows]
primeras = [r["primera_confirmacion"] for r in rows if r["primera_confirmacion"]]
print("\n== RESUMEN ==")
print(f"nacimiento: dist min lobo->vaca [{min(nac_v):.0f}..{max(nac_v):.0f}] | lobo->dron [{min(nac_d):.0f}..{max(nac_d):.0f}]"
      f" (r_confirm=40, r_detect=100)")
print(f"1a confirmacion por sector: cebo {sum(1 for p in primeras if p['sector']=='cebo')} /"
      f" asalto {sum(1 for p in primeras if p['sector']=='asalto')}; por INVESTIGADOR:"
      f" {sum(1 for p in primeras if p['confirmador_investigador'])}/{len(primeras)}")
print(f"dist al rebano del 1er confirmado: {sorted(round(p['dist_rebano']) for p in primeras)}")
print(f"ESCOLTA con el asalto a [m de su presa]: {sorted(r['escolta_con_asalto_a'] for r in rows if r['escolta_con_asalto_a'])}")
print(f"cebo DETECTADO antes del release: {sum(1 for r in rows if r['decoy_detectado_pre_release'])}/{len(rows)}"
      f" | viraje investigador asalto->cebo: {sum(1 for r in rows if r['viraje_investigador_asalto_a_cebo'])}/{len(rows)}")
json.dump(rows, open("/data/wolves/diag/v31_parte0.json", "w"), indent=1)
print("PARTE0_LISTO")
