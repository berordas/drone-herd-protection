"""
render.py — Visualización con matplotlib.

REGLA DE ARQUITECTURA: el render SOLO lee estado, nunca avanza la dinámica.
Consume el `history` (lista de snapshots) que produce el bucle de main.py y lo
reproduce. Así el World queda totalmente desacoplado de la visualización.
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from world import ACTIVE, DETER_RADIUS


def render_episode(world, history, interval: int = 40, save_path: str | None = None):
    W, H = world.W, world.H
    sx, sy, sr = world.safe_zone
    cx, cy, cr = world.central_station

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")

    # --- elementos estáticos ---
    ax.add_patch(patches.Rectangle((0, 0), W, H, fill=False, ec="black"))
    # Establo (zona segura): centro del campo.
    ax.add_patch(patches.Circle((sx, sy), sr, fc="#cfe8cf", ec="green",
                                 alpha=0.6, label="zona segura (establo)"))
    # Estación central de carga: pegada al establo pero distinta.
    ax.add_patch(patches.Circle((cx, cy), cr, fc="#ffe4b5", ec="darkorange",
                                 ls=":", lw=1.5, alpha=0.9, label="estación central (reserva)"))
    # Zona vacas: bounding box dinámico (se recalcula cada frame).
    cow_box = patches.Rectangle((0, 0), 0, 0, fill=False, ec="gray", ls="--", lw=1.2,
                                label="zona vacas (bbox)")
    ax.add_patch(cow_box)

    # --- elementos dinámicos ---
    empty = np.empty((0, 2))
    # Cono de seguridad frontal de cada vaca (cuña ±cone_half_angle, radio r_face_safe). Es lo que
    # de verdad cubre al "dar la cara" (sustituye a la flecha). Se dibuja como polígono actualizable.
    cone_half, r_face = float(world.cone_half_angle), float(world.r_face_safe)
    K_ARC = 14
    cone_polys = [patches.Polygon(np.zeros((K_ARC + 1, 2)), closed=True, fc="green", ec="none", alpha=0.13)
                  for _ in range(world.n_cows)]
    for p in cone_polys:
        ax.add_patch(p)
    cone_polys[0].set_label("cono de seguridad (±45°)")
    # Realce de la presa fijada de la manada (commitment); ahora puede ser un ternero.
    prey_hl = ax.scatter(*empty.T, s=260, facecolors="none", edgecolors="black", linewidths=1.6,
                         marker="o", label="presa fijada", zorder=4)
    # Terneros + línea a su defensora + realce de la madre (nº fijo por episodio).
    n_calves = len(history[0]["calves"])
    calf_lines = [ax.plot([], [], color="saddlebrown", lw=0.8, alpha=0.6, zorder=3)[0]
                  for _ in range(n_calves)]
    defender_hl = ax.scatter(*empty.T, s=150, facecolors="none", edgecolors="purple", linewidths=1.4,
                             marker="o", label="defensora", zorder=4)
    calf_sc = ax.scatter(*empty.T, c="navajowhite", s=45, edgecolors="saddlebrown",
                         label="terneros", zorder=5)
    cow_sc = ax.scatter(*empty.T, c="saddlebrown", s=60, label="vacas", zorder=5)
    # Lobos: el color se actualiza por frame (oro = frenado en el cono / rojo = flanqueando).
    wolf_sc = ax.scatter(*empty.T, c="red", s=110, marker="X", label="lobos", zorder=6)
    # Corzos (3c, cuerpos NO-amenaza): rombo verde oliva; gris claro si ya CONFIRMADOS no-amenaza (descartados).
    corzo_sc = ax.scatter(*empty.T, c="olive", s=70, marker="d", edgecolors="black",
                          linewidths=0.5, label="corzos (no amenaza)", zorder=5)
    active_sc = ax.scatter(*empty.T, c="royalblue", s=90, marker="^", label="drones activos")
    reserve_sc = ax.scatter(*empty.T, c="lightskyblue", s=70, marker="^",
                            edgecolors="royalblue", label="drones reserva")
    # Radio de DISUASIÓN (hazing) de cada dron ACTIVE: dentro de él el lobo esquiva + frena. Solo en el
    # escenario de escolta (escort_enabled); en combate puro no hay disuasión -> no se dibuja (render intacto).
    deter_show = bool(getattr(world, "escort_enabled", False))
    deter_rings = [patches.Circle((0, 0), DETER_RADIUS, fill=False, ec="royalblue", ls=":", lw=1.0,
                                  alpha=0.35, visible=False) for _ in range(world.n_drones)]
    for r in deter_rings:
        ax.add_patch(r)
    if deter_show and deter_rings:
        deter_rings[0].set_label("radio disuasión")
    # Línea dron INVESTIGANDO -> su contacto (cuando un dron se despega a verificar un lobo).
    invest_line, = ax.plot([], [], color="royalblue", lw=1.4, ls="--", alpha=0.8, zorder=4,
                           label="investigando")
    txt = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", fontsize=9,
                  bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    # Banner del terminal (ÉXITO / DEPREDACIÓN / TIMEOUT + contadores), visible al resolverse.
    banner = ax.text(0.5, 0.02, "", transform=ax.transAxes, ha="center", va="bottom",
                     fontsize=12, weight="bold", color="white", zorder=10,
                     bbox=dict(boxstyle="round", fc="gray", alpha=0.9))
    ax.legend(loc="upper right", fontsize=7)

    # Colores de las reses según su estado: en juego (marrón) / refugiada (verde) / cazada (gris).
    def _herd_colors(alive, safe, base):
        return [("dimgray" if not a else ("forestgreen" if s else base))
                for a, s in zip(alive, safe)]

    _TERMINAL = {"success": ("ÉXITO", "forestgreen"), "predation": ("DEPREDACIÓN", "firebrick"),
                 "timeout": ("TIMEOUT", "darkorange")}

    def update(frame):
        snap = history[frame]
        cows = snap["cows"]
        drones = snap["drones"]
        head = snap["cow_heading"]
        wolves = snap["wolves"]
        calves = snap["calves"]
        cdef = snap["calf_defender"]
        cow_sc.set_offsets(cows)
        # Color por estado: refugiadas (verde) y cazadas (gris) se distinguen de las en juego.
        cow_sc.set_color(_herd_colors(snap["cow_alive"], snap["cow_safe"], "saddlebrown"))

        # Cuña del cono frontal: centrada en cada vaca, orientada a su heading, radio r_face_safe.
        for i in range(len(cows)):
            a = np.linspace(head[i] - cone_half, head[i] + cone_half, K_ARC)
            arc = cows[i] + r_face * np.column_stack([np.cos(a), np.sin(a)])
            cone_polys[i].set_xy(np.vstack([cows[i], arc]))

        # Terneros + línea a su defensora + realce de la madre.
        calf_sc.set_offsets(calves if len(calves) else empty)
        if len(calves):
            calf_sc.set_color(_herd_colors(snap["calf_alive"], snap["calf_safe"], "navajowhite"))
        defender_hl.set_offsets(cows[cdef] if len(cdef) else empty)
        for k, ln in enumerate(calf_lines):
            ln.set_data([calves[k, 0], cows[cdef[k], 0]], [calves[k, 1], cows[cdef[k], 1]])

        # Presa fijada de la manada (adulta o ternero), si la hay.
        prey_pos = snap["prey_pos"]
        prey_hl.set_offsets(prey_pos[None, :] if prey_pos is not None else empty)

        # Lobos: color según su relación con el cono que defiende a la presa (oro = a raya / rojo = flanco).
        wolf_sc.set_offsets(wolves)
        cone_pos = snap["prey_cone_pos"]
        if cone_pos is not None and len(wolves):
            f = np.array([np.cos(snap["prey_cone_head"]), np.sin(snap["prey_cone_head"])])
            rel = wolves - cone_pos
            d = np.maximum(np.linalg.norm(rel, axis=1), 1e-9)
            in_cone = (rel / d[:, None]) @ f >= np.cos(cone_half)
            wolf_sc.set_color(np.where(in_cone, "gold", "red").tolist())
        else:
            wolf_sc.set_color("red")

        # Corzos (3c): oliva si aún cuentan como contacto, gris claro si ya CONFIRMADOS no-amenaza (descartados).
        corzos = snap.get("corzos")
        if corzos is not None and len(corzos):
            corzo_sc.set_offsets(corzos)
            dism = snap.get("corzo_dismissed")
            if dism is not None and len(dism) == len(corzos):
                corzo_sc.set_color(["lightgray" if d else "olive" for d in dism])
        else:
            corzo_sc.set_offsets(empty)

        active_sc.set_offsets(drones[:world.n_active])
        reserve_sc.set_offsets(drones[world.n_active:])

        # Radio de disuasión alrededor de cada dron ACTIVE (solo en el escenario de escolta).
        dstate = snap.get("drone_state")
        for i, ring in enumerate(deter_rings):
            on = deter_show and dstate is not None and dstate[i] == ACTIVE
            if on:
                ring.center = (drones[i, 0], drones[i, 1])
            ring.set_visible(on)

        # Dron INVESTIGANDO -> línea a su contacto (despegar a verificar el lobo).
        inv = np.where(snap["drone_investigating"])[0]
        if inv.size:
            i = int(inv[0]); cpos = snap["drone_contact"][i]
            invest_line.set_data([drones[i, 0], cpos[0]], [drones[i, 1], cpos[1]])
        else:
            invest_line.set_data([], [])

        # Zona vacas: derivada de las posiciones actuales -> flota con el rebaño.
        xmin, ymin, xmax, ymax = world.cows_bbox(cows)
        cow_box.set_bounds(xmin, ymin, xmax - xmin, ymax - ymin)

        prey_lbl = "ternero" if snap["prey_is_calf"] else ("adulta" if prey_pos is not None else "-")
        ek = snap.get("episode_kind")
        nc = len(corzos) if corzos is not None else 0
        extra = f"   episodio={ek}   corzos={nc}" if ek and ek != "lobos" else ""
        txt.set_text(f"FASE: {snap['phase']}    t={snap['t']:.1f}s   paso={snap['step']}   "
                     f"lobos={len(wolves)}   presa={prey_lbl}{extra}\n"
                     f"a salvo={snap['n_safe']}   cazadas={snap['n_depredadas']}   fuera={snap['n_fuera']}")

        # Banner del terminal: aparece cuando el episodio se ha resuelto (status != running).
        if snap["status"] in _TERMINAL:
            label, color = _TERMINAL[snap["status"]]
            banner.set_text(f"{label}   ·   a salvo {snap['n_safe']} / cazadas {snap['n_depredadas']} / fuera {snap['n_fuera']}")
            banner.get_bbox_patch().set_facecolor(color)
        else:
            banner.set_text("")
        return (cow_sc, calf_sc, prey_hl, defender_hl, wolf_sc, corzo_sc, active_sc, reserve_sc,
                invest_line, cow_box, txt, banner, *cone_polys, *calf_lines, *deter_rings)

    anim = FuncAnimation(fig, update, frames=len(history),
                         interval=interval, blit=False, repeat=False)

    if save_path:
        anim.save(save_path, fps=max(1, int(1000 / interval)))
    else:
        plt.show()
    return anim
