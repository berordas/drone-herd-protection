"""
render.py — Visualización con matplotlib (emojis de color + barra de batería).

REGLA DE ARQUITECTURA: el render SOLO lee estado, nunca avanza la dinámica. Consume el
`history` (lista de snapshots) que produce el bucle de main.py y lo reproduce. Así el World
queda totalmente desacoplado de la visualización.

Emojis: matplotlib NO pinta emojis a color (FreeType sin glifos COLR/CBDT). Se renderizan con
PIL (`embedded_color=True`, fuente de emoji del sistema) a SPRITES RGBA y se colocan con
AnnotationBbox → color de verdad, sin "tofu". Si no hay PIL o fuente de emoji, cae al render
de marcadores de siempre (scatter) — así nunca se rompe.
Barra de batería: encima de cada dron, [0,1], verde llena → roja casi vacía (necesita el campo
"battery" en el snapshot; main.py lo añade). Si no está, no se dibuja.
"""

from __future__ import annotations
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from world import ACTIVE, DETER_RADIUS

# --- Emojis por entidad ---
EMOJI = {"cow": "🐄", "calf": "🐄", "wolf": "🐺", "corzo": "🦌", "jabali": "🐗", "drone": "🚁",
         "sound": "🔊"}   # 🔊 = el dron ACTIVE "emite ruido" (hay un lobo a <= DETER_RADIUS -> disuade)
# Tamaño de los sprites de emoji (afinable). Más pequeño = se distinguen sin dominar la escena.
EMOJI_SCALE = 0.20   # v3.2: otro escalón (0.27 -> 0.20; el usuario los seguía viendo grandes).
                     # Historia: 0.45 (v2.2, terreno 300) -> 0.27 (v3.1: el zoom efectivo escala con
                     # m/300 y a terreno 500 dominaban la escena) -> 0.20 (v3.2, solo estética).


def _find_emoji_font() -> str | None:
    """Primera fuente de emoji A COLOR disponible (Segoe UI Emoji / Noto / Apple)."""
    for p in ("C:/Windows/Fonts/seguiemj.ttf",
              "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
              "/usr/share/fonts/noto/NotoColorEmoji.ttf",
              "/System/Library/Fonts/Apple Color Emoji.ttc"):
        if os.path.exists(p):
            return p
    return None


_EMOJI_FONT = _find_emoji_font()
try:
    from PIL import Image, ImageDraw, ImageFont
    EMOJI_OK = _EMOJI_FONT is not None
except Exception:
    EMOJI_OK = False

_sprite_cache: dict = {}


def _emoji_font(px: int):
    """Fuente de emoji al tamaño pedido. Las fuentes CBDT de MAPA DE BITS (NotoColorEmoji del
    contenedor) solo abren a su tamaño de strike FIJO -> se cargan al nativo y el sprite se
    REESCALA después (v3.0, pieza 6; Segoe UI Emoji de Windows es escalable y abre directo).
    Devuelve (font, native_px)."""
    try:
        return ImageFont.truetype(_EMOJI_FONT, px), px
    except OSError:
        for native in (137, 136, 128, 109, 96, 64, 32):    # strikes habituales de NotoColorEmoji
            try:
                return ImageFont.truetype(_EMOJI_FONT, native), native
            except OSError:
                continue
        raise


def _sprite(name: str, px: int = 96, fade: float = 1.0) -> np.ndarray:
    """Sprite RGBA (numpy [0,1]) del emoji, recortado a su contenido. `fade` atenúa el alfa
    (entidades muertas / corzos descartados). Cacheado."""
    key = (name, px, round(fade, 2))
    if key in _sprite_cache:
        return _sprite_cache[key]
    font, native = _emoji_font(px)
    img = Image.new("RGBA", (native + 12, native + 12), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((6, 6), EMOJI[name], font=font, embedded_color=True)
    img = img.crop(img.getbbox() or (0, 0, native, native))
    if native != px:                                       # bitmap de tamaño fijo -> reescala al pedido
        w0, h0 = img.size
        s = px / max(native, 1)
        img = img.resize((max(int(w0 * s), 1), max(int(h0 * s), 1)), Image.LANCZOS)
    arr = np.asarray(img).astype(float) / 255.0
    if fade < 1.0:
        arr = arr.copy()
        arr[..., 3] *= fade
    _sprite_cache[key] = arr
    return arr


def render_episode(world, history, interval: int = 40, save_path: str | None = None,
                   show_detected: bool = True, show_confirmed: bool = True):
    """Reproduce `history` (snapshots del mundo; NUNCA llama a step()).
    Commit F (misión forense v3.5): `show_detected` dibuja un CUADRADO alrededor de cada lobo
    DETECTADO — geometría PURA recomputada desde el snapshot: lobo a <= r_detect de algún dron
    ACTIVE (el criterio DRI del disparador del mundo, sin estado nuevo) — cuadrado NARANJA con
    entrada en la leyenda; `show_confirmed` dibuja un cuadrado ROJO alrededor del lobo
    CONFIRMADO ante la barrera si el snapshot trae la máscara `confirmed_mask` (la escribe el arnés HRL desde el
    latch de equipo del coordinador — no la calcula el mundo); sin ella no se dibuja nada. El
    círculo de DETER_RADIUS=20 (el campo del "sonido") ya se dibujaba en cada ACTIVE."""
    W, H = world.W, world.H
    sx, sy, sr = world.safe_zone
    cx, cy, cr = world.central_station
    m = min(W, H)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")

    # --- elementos estáticos ---
    ax.add_patch(patches.Rectangle((0, 0), W, H, fill=False, ec="black"))
    ax.add_patch(patches.Circle((sx, sy), sr, fc="#cfe8cf", ec="green",
                                 alpha=0.6, label="zona segura (establo)"))
    ax.add_patch(patches.Circle((cx, cy), cr, fc="#ffe4b5", ec="darkorange",
                                 ls=":", lw=1.5, alpha=0.9, label="estación central (reserva)"))
    cow_box = patches.Rectangle((0, 0), 0, 0, fill=False, ec="gray", ls="--", lw=1.2,
                                label="zona vacas (bbox)")
    ax.add_patch(cow_box)

    # --- elementos dinámicos (estructura: conos, realces, líneas, anillos) ---
    empty = np.empty((0, 2))
    cone_half, r_face = float(world.cone_half_angle), float(world.r_face_safe)
    K_ARC = 14
    cone_polys = [patches.Polygon(np.zeros((K_ARC + 1, 2)), closed=True, fc="green", ec="none", alpha=0.13)
                  for _ in range(world.n_cows)]
    for p in cone_polys:
        ax.add_patch(p)
    cone_polys[0].set_label("cono de seguridad (±45°)")
    # v3.1: SIN círculo de presa fijada (pack_prey/pack_prey2) — decisión de cosmética del usuario
    # (el realce ensuciaba la escena; la presa se sigue leyendo en la línea de estado del título).
    n_calves = len(history[0]["calves"])
    calf_lines = [ax.plot([], [], color="saddlebrown", lw=0.8, alpha=0.6, zorder=3)[0]
                  for _ in range(n_calves)]
    defender_hl = ax.scatter(*empty.T, s=240, facecolors="none", edgecolors="purple", linewidths=1.4,
                             marker="o", label="defensora", zorder=7)
    deter_show = bool(getattr(world, "escort_enabled", False))
    deter_rings = [patches.Circle((0, 0), DETER_RADIUS, fill=False, ec="royalblue", ls=":", lw=1.0,
                                  alpha=0.35, visible=False) for _ in range(world.n_drones)]
    for r in deter_rings:
        ax.add_patch(r)
    if deter_show and deter_rings:
        deter_rings[0].set_label("radio disuasión")
    invest_line, = ax.plot([], [], color="royalblue", lw=1.4, ls="--", alpha=0.8, zorder=4,
                           label="investigando")
    # Commit F: marcadores de percepción del bando dron (solo lectura de snapshots).
    r_detect = float(getattr(world, "r_detect", 100.0))
    # (decisión del dueño, STOP-F1): DETECTADO = cuadrado NARANJA; CONFIRMADO = cuadrado ROJO
    # (mismo marcador, el color dice el nivel de percepción; el rojo pisa al naranja).
    det_hl = ax.scatter(*empty.T, s=330, facecolors="none", edgecolors="darkorange", linewidths=1.4,
                        marker="s", zorder=7, visible=bool(show_detected),
                        label=("cuadrado naranja = lobo detectado (<= r_detect de un ACTIVE)"
                               if show_detected else None))
    conf_hl = ax.scatter(*empty.T, s=330, facecolors="none", edgecolors="red", linewidths=1.6,
                         marker="s", zorder=8, visible=bool(show_confirmed),
                         label=("cuadrado rojo = lobo confirmado (latch de la barrera)"
                                if show_confirmed else None))

    # --- entidades: sprites de emoji (o scatter de reserva si no hay emojis) ---
    zf = EMOJI_SCALE * (m / 300)
    ZOOM = {"cow": 0.42 * zf, "calf": 0.30 * zf, "wolf": 0.40 * zf,
            "corzo": 0.38 * zf, "jabali": 0.38 * zf, "drone": 0.40 * zf, "sound": 0.30 * zf}

    def _pool(name, n, z):
        pool = []
        for _ in range(n):
            oi = OffsetImage(_sprite(name), zoom=z)
            ab = AnnotationBbox(oi, (0, 0), frameon=False, pad=0.0, zorder=6,
                                box_alignment=(0.5, 0.5))
            ab.set_visible(False)
            ax.add_artist(ab)
            pool.append([ab, oi, name])
        return pool

    scatters = {}
    if EMOJI_OK:
        cow_pool = _pool("cow", world.n_cows, ZOOM["cow"])
        calf_pool = _pool("calf", n_calves, ZOOM["calf"])
        wolf_pool = _pool("wolf", len(history[0]["wolves"]) or 5, ZOOM["wolf"])
        corzo_pool = _pool("corzo", len(history[0].get("corzos", [])) or 3, ZOOM["corzo"])
        drone_pool = _pool("drone", world.n_drones, ZOOM["drone"])
        sound_pool = _pool("sound", world.n_drones, ZOOM["sound"])   # 🔊 bajo cada dron que disuade
    else:  # --- FALLBACK (sin emojis): marcadores de siempre ---
        scatters["cow"] = ax.scatter(*empty.T, c="saddlebrown", s=60, label="vacas", zorder=6)
        scatters["calf"] = ax.scatter(*empty.T, c="navajowhite", s=45, edgecolors="saddlebrown", label="terneros", zorder=6)
        scatters["wolf"] = ax.scatter(*empty.T, c="red", s=110, marker="X", label="lobos", zorder=6)
        scatters["corzo"] = ax.scatter(*empty.T, c="olive", s=70, marker="d", edgecolors="black", lw=0.5, label="corzos", zorder=6)
        scatters["drone"] = ax.scatter(*empty.T, c="royalblue", s=90, marker="^", label="drones", zorder=6)

    # --- barra de batería sobre cada dron ---
    BAR_W, BAR_H, BAR_DY = 0.05 * m, 0.011 * m, 0.035 * m
    bat_bg = [patches.Rectangle((0, 0), BAR_W, BAR_H, fc="#e6e6e6", ec="black", lw=0.4,
                                zorder=8, visible=False) for _ in range(world.n_drones)]
    bat_fill = [patches.Rectangle((0, 0), 0, BAR_H, fc="green", ec="none",
                                  zorder=9, visible=False) for _ in range(world.n_drones)]
    for r in bat_bg + bat_fill:
        ax.add_patch(r)
    bat_cmap = plt.get_cmap("RdYlGn")

    txt = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top", fontsize=9,
                  bbox=dict(boxstyle="round", fc="white", alpha=0.8), zorder=11)
    banner = ax.text(0.5, 0.02, "", transform=ax.transAxes, ha="center", va="bottom",
                     fontsize=12, weight="bold", color="white", zorder=12,
                     bbox=dict(boxstyle="round", fc="gray", alpha=0.9))
    ax.legend(loc="lower right", fontsize=6.5, framealpha=0.85, markerscale=0.45)   # solo zonas/estructura + marcadores de percepción (Commit F); markerscale: los marcadores de detectado/confirmado a tamaño de leyenda

    SOUND_DY = 0.035 * m   # desplazamiento del 🔊 justo por DEBAJO del dron (la barra de batería va encima)

    def _faded(alive, safe):  # muertas atenuadas (las a-salvo se quedan normales, junto al establo)
        return [not a for a in alive]

    def _place(pool, positions, faded=None, name_override=None):
        for k, (ab, oi, name) in enumerate(pool):
            if k < len(positions):
                ab.xy = (positions[k, 0], positions[k, 1])
                ab.xybox = (positions[k, 0], positions[k, 1])
                ab.set_visible(True)
                if faded is not None or name_override is not None:   # corzo/jabalí (especie) o atenuación (muerta/descartado)
                    oi.set_data(_sprite(name_override or name, fade=0.3 if (faded is not None and faded[k]) else 1.0))
            else:
                ab.set_visible(False)

    _TERMINAL = {"success": ("ÉXITO", "forestgreen"), "predation": ("DEPREDACIÓN", "firebrick"),
                 "timeout": ("TIMEOUT", "darkorange")}

    def _herd_colors(alive, safe, base):
        return [("dimgray" if not a else ("forestgreen" if s else base)) for a, s in zip(alive, safe)]

    def update(frame):
        snap = history[frame]
        cows, drones, head = snap["cows"], snap["drones"], snap["cow_heading"]
        wolves, calves, cdef = snap["wolves"], snap["calves"], snap["calf_defender"]
        corzos = snap.get("corzos")
        corzos = corzos if corzos is not None else empty

        # Conos frontales.
        for i in range(len(cows)):
            a = np.linspace(head[i] - cone_half, head[i] + cone_half, K_ARC)
            arc = cows[i] + r_face * np.column_stack([np.cos(a), np.sin(a)])
            cone_polys[i].set_xy(np.vstack([cows[i], arc]))

        # Realces + líneas ternero->defensora.
        defender_hl.set_offsets(cows[cdef] if len(cdef) else empty)
        for k, ln in enumerate(calf_lines):
            ln.set_data([calves[k, 0], cows[cdef[k], 0]], [calves[k, 1], cows[cdef[k], 1]])
        prey_pos = snap["prey_pos"]          # (solo para la etiqueta del título; sin realce v3.1)

        # Entidades.
        if EMOJI_OK:
            _place(cow_pool, cows, faded=_faded(snap["cow_alive"], snap["cow_safe"]))
            _place(calf_pool, calves, faded=_faded(snap["calf_alive"], snap["calf_safe"]))
            _place(wolf_pool, wolves)
            dism = snap.get("corzo_dismissed")
            cf = [bool(dism[i]) for i in range(len(corzos))] if (dism is not None and len(dism) == len(corzos)) else None
            dist_name = "jabali" if snap.get("distraction_species") == "jabali" else "corzo"
            _place(corzo_pool, corzos, faded=cf, name_override=dist_name)
            _place(drone_pool, drones)
        else:
            scatters["cow"].set_offsets(cows); scatters["cow"].set_color(_herd_colors(snap["cow_alive"], snap["cow_safe"], "saddlebrown"))
            scatters["calf"].set_offsets(calves if len(calves) else empty)
            scatters["wolf"].set_offsets(wolves)
            scatters["corzo"].set_offsets(corzos if len(corzos) else empty)
            scatters["drone"].set_offsets(drones)

        # Commit F: DETECTADO = geometría pura desde el snapshot (<= r_detect de un ACTIVE);
        # CONFIRMADO = máscara `confirmed_mask` del snapshot si el arnés la escribió.
        dstate = snap.get("drone_state")
        if show_detected:
            if dstate is not None and len(wolves):
                act = drones[np.asarray(dstate) == ACTIVE]
                if act.shape[0]:
                    dd = np.linalg.norm(np.asarray(wolves)[:, None, :] - act[None, :, :], axis=2)
                    det_m = (dd <= r_detect).any(axis=1)
                    cm0 = snap.get("confirmed_mask") if show_confirmed else None
                    if cm0 is not None and len(cm0) == len(wolves):
                        det_m = det_m & ~np.asarray(cm0, dtype=bool)   # confirmado => solo el rojo
                    det_hl.set_offsets(np.asarray(wolves)[det_m])
                else:
                    det_hl.set_offsets(empty)
            else:
                det_hl.set_offsets(empty)
        if show_confirmed:
            cm = snap.get("confirmed_mask")
            if cm is not None and len(wolves) and len(cm) == len(wolves):
                conf_hl.set_offsets(np.asarray(wolves)[np.asarray(cm, dtype=bool)])
            else:
                conf_hl.set_offsets(empty)

        # Radio de disuasión de los ACTIVE (solo escolta).
        for i, ring in enumerate(deter_rings):
            on = deter_show and dstate is not None and dstate[i] == ACTIVE
            if on:
                ring.center = (drones[i, 0], drones[i, 1])
            ring.set_visible(on)

        # 🔊 bajo cada dron ACTIVE que de verdad SE ACERCA a un lobo a tiro (susto por movimiento v2.4). Puro
        # dibujo: el render LEE el flag drone_scaring que calcula el mundo en _apply_deterrence (un dron ESTÁTICO
        # ya no "ladra": solo asusta el que embiste). Sin el flag (snapshots viejos) no se dibuja.
        scaring = snap.get("drone_scaring")
        if EMOJI_OK:
            for i, (ab, _oi, _name) in enumerate(sound_pool):
                noisy = bool(deter_show and scaring is not None and i < len(scaring) and scaring[i])
                if noisy:
                    ab.xy = (drones[i, 0], drones[i, 1] - SOUND_DY)
                    ab.xybox = (drones[i, 0], drones[i, 1] - SOUND_DY)
                ab.set_visible(noisy)

        # Barra de batería sobre cada dron.
        bat = snap.get("battery")
        for i in range(world.n_drones):
            if bat is None:
                bat_bg[i].set_visible(False); bat_fill[i].set_visible(False); continue
            bx, by = drones[i, 0] - BAR_W / 2.0, drones[i, 1] + BAR_DY
            b = float(np.clip(bat[i], 0.0, 1.0))
            bat_bg[i].set_xy((bx, by)); bat_bg[i].set_visible(True)
            bat_fill[i].set_xy((bx, by)); bat_fill[i].set_width(BAR_W * b)
            bat_fill[i].set_facecolor(bat_cmap(b)); bat_fill[i].set_visible(True)

        # Dron investigando -> línea a su contacto.
        inv = np.where(snap["drone_investigating"])[0]
        if inv.size:
            i = int(inv[0]); cpos = snap["drone_contact"][i]
            invest_line.set_data([drones[i, 0], cpos[0]], [drones[i, 1], cpos[1]])
        else:
            invest_line.set_data([], [])

        xmin, ymin, xmax, ymax = world.cows_bbox(cows)
        cow_box.set_bounds(xmin, ymin, xmax - xmin, ymax - ymin)

        prey_lbl = "ternero" if snap["prey_is_calf"] else ("adulta" if prey_pos is not None else "-")
        ek = snap.get("episode_kind")
        nc = len(corzos)
        spn = "jabalíes" if snap.get("distraction_species") == "jabali" else "corzos"
        extra = f"   episodio={ek}   distracción={nc} {spn}" if ek and ek != "lobos" else ""
        txt.set_text(f"FASE: {snap['phase']}    t={snap['t']:.1f}s   paso={snap['step']}   "
                     f"lobos={len(wolves)}   presa={prey_lbl}{extra}\n"
                     f"a salvo={snap['n_safe']}   cazadas={snap['n_depredadas']}   fuera={snap['n_fuera']}")

        if snap["status"] in _TERMINAL:
            label, color = _TERMINAL[snap["status"]]
            banner.set_text(f"{label}   ·   a salvo {snap['n_safe']} / cazadas {snap['n_depredadas']} / fuera {snap['n_fuera']}")
            banner.get_bbox_patch().set_facecolor(color)
        else:
            banner.set_text("")

        arts = [defender_hl, invest_line, cow_box, txt, banner, det_hl, conf_hl,
                *cone_polys, *calf_lines, *deter_rings, *bat_bg, *bat_fill]
        if EMOJI_OK:
            arts += [ab for pool in (cow_pool, calf_pool, wolf_pool, corzo_pool, drone_pool, sound_pool) for ab, _, _ in pool]
        else:
            arts += list(scatters.values())
        return tuple(arts)

    anim = FuncAnimation(fig, update, frames=len(history),
                         interval=interval, blit=False, repeat=False)

    if save_path:
        anim.save(save_path, fps=max(1, int(1000 / interval)))
    else:
        plt.show()
    return anim
