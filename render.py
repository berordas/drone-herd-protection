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
    active_sc = ax.scatter(*empty.T, c="royalblue", s=90, marker="^", label="drones activos")
    reserve_sc = ax.scatter(*empty.T, c="lightskyblue", s=70, marker="^",
                            edgecolors="royalblue", label="drones reserva")
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

        active_sc.set_offsets(drones[:world.n_active])
        reserve_sc.set_offsets(drones[world.n_active:])

        # Zona vacas: derivada de las posiciones actuales -> flota con el rebaño.
        xmin, ymin, xmax, ymax = world.cows_bbox(cows)
        cow_box.set_bounds(xmin, ymin, xmax - xmin, ymax - ymin)

        prey_lbl = "ternero" if snap["prey_is_calf"] else ("adulta" if prey_pos is not None else "-")
        txt.set_text(f"FASE: {snap['phase']}    t={snap['t']:.1f}s   paso={snap['step']}   "
                     f"lobos={len(wolves)}   presa={prey_lbl}\n"
                     f"a salvo={snap['n_safe']}   cazadas={snap['n_depredadas']}   fuera={snap['n_fuera']}")

        # Banner del terminal: aparece cuando el episodio se ha resuelto (status != running).
        if snap["status"] in _TERMINAL:
            label, color = _TERMINAL[snap["status"]]
            banner.set_text(f"{label}   ·   a salvo {snap['n_safe']} / cazadas {snap['n_depredadas']} / fuera {snap['n_fuera']}")
            banner.get_bbox_patch().set_facecolor(color)
        else:
            banner.set_text("")
        return (cow_sc, calf_sc, prey_hl, defender_hl, wolf_sc, active_sc, reserve_sc,
                cow_box, txt, banner, *cone_polys, *calf_lines)

    anim = FuncAnimation(fig, update, frames=len(history),
                         interval=interval, blit=False, repeat=False)

    if save_path:
        anim.save(save_path, fps=max(1, int(1000 / interval)))
    else:
        plt.show()
    return anim
