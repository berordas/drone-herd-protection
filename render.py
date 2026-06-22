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
    cow_sc = ax.scatter(*empty.T, c="saddlebrown", s=60, label="vacas")
    # Mirada de las vacas (a quién "dan la cara"): flecha desde cada vaca en su heading.
    face_len = 0.06 * min(W, H)
    cow_face = ax.quiver(np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0),
                         color="saddlebrown", alpha=0.5, angles="xy",
                         scale_units="xy", scale=1.0, width=0.004)
    wolf_sc = ax.scatter(*empty.T, c="red", s=110, marker="X", label="lobos")
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
        cow_sc.set_offsets(cows)
        # Flecha de mirada: origen en cada vaca, dirección = su heading.
        head = snap["cow_heading"]
        cow_face.set_offsets(cows)
        cow_face.set_UVC(np.cos(head) * face_len, np.sin(head) * face_len)
        wolf_sc.set_offsets(snap["wolves"])
        active_sc.set_offsets(drones[:world.n_active])
        reserve_sc.set_offsets(drones[world.n_active:])

        # Zona vacas: derivada de las posiciones actuales -> flota con el rebaño.
        xmin, ymin, xmax, ymax = world.cows_bbox(cows)
        cow_box.set_bounds(xmin, ymin, xmax - xmin, ymax - ymin)

        txt.set_text(f"t={snap['t']:.1f}s   paso={snap['step']}   "
                     f"lobos={len(snap['wolves'])}   estado={snap['status']}")
        return cow_sc, cow_face, wolf_sc, active_sc, reserve_sc, cow_box, txt

    anim = FuncAnimation(fig, update, frames=len(history),
                         interval=interval, blit=False, repeat=False)

    if save_path:
        anim.save(save_path, fps=max(1, int(1000 / interval)))
    else:
        plt.show()
    return anim
