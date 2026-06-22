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
    # Realce de la presa fijada de la manada (commitment).
    prey_hl = ax.scatter(*empty.T, s=260, facecolors="none", edgecolors="black", linewidths=1.6,
                         marker="o", label="presa fijada", zorder=4)
    cow_sc = ax.scatter(*empty.T, c="saddlebrown", s=60, label="vacas", zorder=5)
    # Lobos: el color se actualiza por frame (oro = frenado en el cono / rojo = flanqueando).
    wolf_sc = ax.scatter(*empty.T, c="red", s=110, marker="X", label="lobos", zorder=6)
    active_sc = ax.scatter(*empty.T, c="royalblue", s=90, marker="^", label="drones activos")
    reserve_sc = ax.scatter(*empty.T, c="lightskyblue", s=70, marker="^",
                            edgecolors="royalblue", label="drones reserva")
    txt = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", fontsize=9,
                  bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    ax.legend(loc="upper right", fontsize=7)

    def update(frame):
        snap = history[frame]
        cows = snap["cows"]
        drones = snap["drones"]
        head = snap["cow_heading"]
        wolves = snap["wolves"]
        prey = snap["pack_prey"]
        cow_sc.set_offsets(cows)

        # Cuña del cono frontal: centrada en cada vaca, orientada a su heading, radio r_face_safe.
        for i in range(len(cows)):
            a = np.linspace(head[i] - cone_half, head[i] + cone_half, K_ARC)
            arc = cows[i] + r_face * np.column_stack([np.cos(a), np.sin(a)])
            cone_polys[i].set_xy(np.vstack([cows[i], arc]))

        # Presa fijada de la manada (si la hay).
        prey_hl.set_offsets(cows[prey][None, :] if prey >= 0 else empty)

        # Lobos: color según su relación con el cono de la presa (oro = a raya / rojo = flanqueando).
        wolf_sc.set_offsets(wolves)
        if prey >= 0 and len(wolves):
            f = np.array([np.cos(head[prey]), np.sin(head[prey])])
            rel = wolves - cows[prey]
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

        txt.set_text(f"t={snap['t']:.1f}s   paso={snap['step']}   "
                     f"lobos={len(snap['wolves'])}   presa={prey}   estado={snap['status']}")
        return (cow_sc, prey_hl, wolf_sc, active_sc, reserve_sc, cow_box, txt, *cone_polys)

    anim = FuncAnimation(fig, update, frames=len(history),
                         interval=interval, blit=False, repeat=False)

    if save_path:
        anim.save(save_path, fps=max(1, int(1000 / interval)))
    else:
        plt.show()
    return anim
