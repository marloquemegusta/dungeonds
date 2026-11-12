#!/usr/bin/env python3
"""Bake the cathedral floor, wall, lapidas, columns, benches, candles and reliquary into the strip kit."""
import argparse
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROP_DIR = ROOT / "assets/environment/cathedral/props/render"
LAPIDA_DIR = ROOT / "assets/environment/cathedral/lapidas"
WALL_PNG = ROOT / "assets/environment/cathedral/muros/muro_izq_128.png"
PROP_PALETTE = ROOT / "assets/environment/cathedral/palette/palette.json"
OUTPUT = ROOT / "source/strip_kit.c"
DEFAULT_PROPS = ("columna_entera", "banco_entero", "relicario", "vela",
                 "lapida_3x2_cruz", "lapida_3x2_cab", "lapida_2x1_cruz", "lapida_2x1_cab",
                 "banco_grupo4")
# Piece ids emitted in StripStamp.piece_id; must match enum STRIP_PIECE_* in include/strip_kit.h.
PIECE_IDS = {
    "columna_entera": 1, "banco_entero": 2, "relicario": 3, "vela": 4,
    "lapida_3x2_cruz": 5, "lapida_3x2_cab": 6, "lapida_2x1_cruz": 7, "lapida_2x1_cab": 8,
    "banco_grupo4": 9,
}
LAPIDA_NAMES = ("lapida_3x2_cruz", "lapida_3x2_cab", "lapida_2x1_cruz", "lapida_2x1_cab")
# Piezas sin carpeta propia: se componen en el baker a partir de otras.
COMPOSITE_NAMES = ("banco_grupo4",)
WALL_BACKDROP_RGB = (0x1c, 0x19, 0x20)
WALL_TILE_COLS = 6            # 48 px por lado
WALL_MAX_NEW_COLORS = 32
# Las lapidas v5 son el propio suelo: floor_origin_px [0, 16] -> fase (pc=0, pr=2) es el origen del arte.
LAPIDA_PHASE = (0, 2)
# Fases horneadas de cada lapida: la del arte y la del damero invertido (2 tiles a la derecha, 1 abajo).
# Una estampa (pc, pr) vale en (x, y) si (x - pc) % 4 == 0 y (y - pr) % 2 == 0 (DESIGN.md 6.9.1b).
LAPIDA_PHASES = ((0, 2), (2, 3))
GROUP_STEP_PX = 24            # paso vertical de banco_grupo4 (3 tiles)
GROUP_BANKS = 4
# Fases de vela: x_tile & 15 en {0,2,4,6,9,11,13,15} con pr en {1,9}; una fase por x.
VELA_PHASES = ((0, 1), (4, 1), (9, 1), (13, 1), (2, 9), (6, 9), (11, 9), (15, 9))
OCCLUSION_CAPACITY = 32768


def color_value(v):
    return (int(v, 16) if isinstance(v, str) else int(v)) | 0x8000


def rgb555(c):
    return np.array([(c & 31) * 255 // 31,
                     ((c >> 5) & 31) * 255 // 31,
                     ((c >> 10) & 31) * 255 // 31], dtype=np.uint8)


def lab(rgb):
    v = np.asarray(rgb, dtype=np.float64) / 255.0
    v = np.where(v <= .04045, v / 12.92, ((v + .055) / 1.055) ** 2.4)
    xyz = v @ np.array([[.4124564, .3575761, .1804375],
                        [.2126729, .7151522, .0721750],
                        [.0193339, .1191920, .9503041]])
    xyz /= np.array([.95047, 1.0, 1.08883])
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def flip_bytes(data, h, v):
    a = np.frombuffer(data, dtype=np.uint8).reshape(8, 8)
    if h: a = a[:, ::-1]
    if v: a = a[::-1, :]
    return a.tobytes()


class Tiles:
    def __init__(self):
        self.data = [bytes(64)]
        self.index = {self.data[0]: 0}

    def add(self, data):
        options = [(flip_bytes(data, h, v), h, v) for v in (0, 1) for h in (0, 1)]
        canonical, h, v = min(options, key=lambda x: x[0])
        idx = self.index.get(canonical)
        # El indice puede quedar desalineado con self.data tras reordenar/remplazar tiles:
        # si la entrada cacheada no guarda esos bytes, hay que añadir el tile de verdad.
        if idx is not None and self.data[idx] != canonical:
            idx = None
        if idx is None:
            idx = len(self.data)
            self.index[canonical] = idx
            self.data.append(canonical)
        return idx | (0x400 if h else 0) | (0x800 if v else 0)


def read_floor(directory):
    src = json.loads((directory / "floor.json").read_text(encoding="utf-8"))
    if src.get("period_tiles") != [16, 16]:
        raise ValueError("period_tiles must be [16, 16]")
    colors = [color_value(c) for c in src["palette"]]
    raw = src["tiles"]
    if not raw or any(len(t) != 64 for t in raw):
        raise ValueError("floor tiles must each contain 64 indices")
    if any(not isinstance(i, int) or i < 0 or i >= len(colors) for t in raw for i in t):
        raise ValueError("floor tile has an invalid palette index")
    grid = src["floor_map"]
    if len(grid) != 16 or any(len(r) != 16 for r in grid):
        raise ValueError("floor_map must be 16x16")
    for row in grid:
        for c in row:
            if not all(k in c for k in ("t", "h", "v")) or c["t"] not in range(len(raw)) or c["h"] not in (0, 1) or c["v"] not in (0, 1):
                raise ValueError("invalid floor_map entry")
    return colors, raw, grid


def make_floor_tiles(colors, raw, grid, tiles):
    palette = [0]
    remap = {}
    for c in colors:
        if c not in remap:
            remap[c] = len(palette)
            palette.append(c)
    raw_to_map = []
    pixel_tiles = []
    for tile in raw:
        pixels = np.array([remap[colors[i]] for i in tile], dtype=np.uint8)
        pixel_tiles.append(pixels)
        raw_to_map.append(tiles.add(pixels.tobytes()))
    floor_map = []
    for row in grid:
        expanded = []
        for cell in row:
            encoded = raw_to_map[cell["t"]]
            requested = (0x400 if cell["h"] else 0) | (0x800 if cell["v"] else 0)
            encoded = (encoded & 0x3ff) | ((encoded ^ requested) & 0xc00)
            expanded.append(encoded)
        # The 16-tile period repeats across the 64-tile lane: repeat the whole row, not each tile.
        floor_map.append(expanded * 4)
    return palette, pixel_tiles, floor_map


def floor_color(pixel_tiles, colors, grid, x, y):
    # x, y are pixels; the 16x16 period grid is indexed in tiles.
    cell = grid[(y >> 3) % 16][(x >> 3) % 16]
    px = x % 8
    py = y % 8
    if cell["h"]: px = 7 - px
    if cell["v"]: py = 7 - py
    pidx = int(pixel_tiles[cell["t"]][py * 8 + px])
    return pidx


def read_prop_palette():
    colors = [color_value(c) for c in json.loads(PROP_PALETTE.read_text(encoding="utf-8"))["bgr555_hex"]["props"]]
    rgbs = np.stack([rgb555(c) for c in colors])
    return colors, lab(rgbs)


def quantize_props(im, prop_lab):
    rgb = np.asarray(im.convert("RGBA"))[:, :, :3]
    points = lab(rgb.reshape(-1, 3))
    result = np.empty(len(points), dtype=np.uint8)
    for i in range(0, len(points), 4096):
        block = points[i:i + 4096]
        dist = ((block[:, None] - prop_lab[None]) ** 2).sum(axis=2)
        result[i:i + len(block)] = np.argmin(dist, axis=1)
    return result.reshape(rgb.shape[:2])


def piece_depth_runs(depth, rgba, foot_anchor_y_px):
    """depth.png holds, per surface pixel, the sprite-local Y of the ground under it (the same
    contract as a map's occlusion_depth.png, in this sprite's pixels). Runs store it relative to
    the footprint anchor, which strip.c adds back to the stamp's world Y."""
    d = np.asarray(depth.convert("RGB"), dtype=np.int32)
    alpha = np.asarray(rgba)[:, :, 3] >= 128
    valid = (d[:, :, 2] >= 128) & alpha
    value = d[:, :, 0] * 256 + d[:, :, 1]
    if not valid.any(): raise ValueError("depth.png has no valid depth")
    if value[valid].min() < 0 or value[valid].max() > len(valid):
        raise ValueError("depth.png values are not sprite-local Y; re-run tools/props/prerender_props.py")
    baseline = foot_anchor_y_px
    runs = []
    for y in range(len(valid)):
        x = 0
        while x < valid.shape[1]:
            if not valid[y, x]:
                x += 1
                continue
            x0, dv = x, int(value[y, x])
            x += 1
            while x < valid.shape[1] and valid[y, x] and abs(int(value[y, x]) - dv) <= 1:
                x += 1
            runs.append((x0, y, x - x0, dv - baseline))
    return runs


def footprint_runs(im):
    """Read white as solid, at 4x4 floor cells. An empty mask is an error, never a full rectangle."""
    a = np.asarray(im.convert("L"))
    grid_h, grid_w = a.shape[0] // 4, a.shape[1] // 4
    cells = np.zeros((grid_h, grid_w), dtype=bool)
    for cy in range(grid_h):
        for cx in range(grid_w):
            cell = a[cy * 4:cy * 4 + 4, cx * 4:cx * 4 + 4]
            cells[cy, cx] = np.mean(cell >= 128) > .40
    if not cells.any():
        raise ValueError("footprint.png has no solid cell; re-run tools/props/prerender_props.py")
    return cells_to_runs(cells)


def cells_to_runs(cells):
    runs = []
    for cy, row in enumerate(cells):
        cx = 0
        while cx < cells.shape[1]:
            if not row[cx]:
                cx += 1
                continue
            x0 = cx
            while cx < cells.shape[1] and row[cx]:
                cx += 1
            runs.append((x0, cy, cx - x0))
    return runs


def shadow_color(c):
    # mismo oscurecimiento al 50 % que apply_shadow_fast (source/main.c)
    return ((c & 0x7BDE) >> 1) | 0x8000


def piece_layout(name):
    folder = PROP_DIR / name
    color = Image.open(folder / "color.png").convert("RGBA")
    depth = Image.open(folder / "depth.png")
    foot = Image.open(folder / "footprint.png")
    w, h = color.size
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    if w % 8 or h % 8: raise ValueError(f"{name}: dimensions must be multiples of 8")
    if meta.get("piece") != name or meta.get("size_px") != [w, h]:
        raise ValueError(f"{name}: meta.json identity or size does not match color.png")
    if depth.size != color.size or foot.size != color.size:
        raise ValueError(f"{name}: color, depth and footprint dimensions must match")
    rgba = np.asarray(color)
    if not np.isin(rgba[:, :, 3], [0, 255]).all(): raise ValueError(f"{name}: alpha must be binary")
    value = 3 if name == "columna_entera" else 1
    try:
        foot_runs = footprint_runs(foot)
    except ValueError as e:
        raise ValueError(f"{name}: {e}") from None
    foot_anchor_y_px = max((y * 4 + 4 for _, y, _ in foot_runs), default=0)
    depth_runs = piece_depth_runs(depth, rgba, foot_anchor_y_px)
    layout = {"name": name, "value": value, "foot_runs": foot_runs,
              "foot_anchor_y_px": foot_anchor_y_px, "depth_runs": depth_runs,
              "rgba": rgba, "shadow": None, "ox": 0, "oy": 0, "w": w, "h": h}
    shadow_path = folder / "shadow.png"
    if shadow_path.exists():
        dx, dy = meta.get("shadow_offset_px", [0, 0])
        sw, sh = meta.get("shadow_canvas_px", [0, 0])
        if dx > 0 or dy > 0 or dx % 8 or dy % 8 or sw % 8 or sh % 8:
            raise ValueError(f"{name}: shadow_offset_px must be <= 0 and multiples of 8; canvas multiples of 8")
        ox, oy = -dx, -dy
        if ox + w > sw or oy + h > sh: raise ValueError(f"{name}: color.png does not fit in shadow canvas")
        shadow_img = np.asarray(Image.open(shadow_path).convert("L")) > 127
        if shadow_img.shape != (sh, sw): raise ValueError(f"{name}: shadow.png size does not match shadow_canvas_px")
        full = np.zeros((sh, sw, 4), np.uint8)
        full[oy:oy + h, ox:ox + w] = rgba
        layout.update(rgba=full, shadow=shadow_img & (full[:, :, 3] < 128), ox=ox, oy=oy, w=sw, h=sh)
        # los datos de colision y profundidad se calculan en el encuadre de color.png y se desplazan
        layout["foot_runs"] = [(x + ox // 4, y + oy // 4, n) for x, y, n in foot_runs]
        layout["foot_anchor_y_px"] += oy
        layout["depth_runs"] = [(x + ox, y + oy, n, d) for x, y, n, d in depth_runs]
    return layout


def lapida_layout(name):
    """Lapida v5: a flat stamp (no footprint, no occlusion) whose pixels are the stone where
    alpha >= 128 and the floor of its phase elsewhere; the baker fills the floor part."""
    meta = json.loads((LAPIDA_DIR / "lapidas_meta.json").read_text(encoding="utf-8"))[name]
    rgba = np.asarray(Image.open(LAPIDA_DIR / f"{name}.png").convert("RGBA"))
    h, w = rgba.shape[:2]
    if [w, h] != meta["size_px"]: raise ValueError(f"{name}: png size does not match lapidas_meta.json")
    if w % 8 or h % 8: raise ValueError(f"{name}: dimensions must be multiples of 8")
    if list(meta["floor_origin_px"]) != [LAPIDA_PHASE[0] * 8, LAPIDA_PHASE[1] * 8]:
        raise ValueError(f"{name}: floor_origin_px must match LAPIDA_PHASE")
    if not np.isin(rgba[:, :, 3], [0, 255]).all(): raise ValueError(f"{name}: alpha must be binary")
    return {"name": name, "value": 0, "foot_runs": [], "foot_anchor_y_px": 0, "depth_runs": [],
            "rgba": rgba, "shadow": None, "ox": 0, "oy": 0, "w": w, "h": h}


def crop_bench_canvas(lay, target_h_px=None):
    """Clamp a bench stamp to a 32 px (4-tile) canvas anchored at the footprint base so two
    benches 32 px apart never share a tile row. banco_entero only loses its empty bottom row."""
    if target_h_px is None:
        target_h_px = BENCH_CANVAS_H_PX
    sh = lay["h"]
    if sh <= target_h_px:
        return lay
    anchor = lay["foot_anchor_y_px"]
    y0 = max(0, min(sh - target_h_px, anchor - target_h_px))
    y1 = y0 + target_h_px
    new = dict(lay)
    new["rgba"] = lay["rgba"][y0:y1, :]
    new["shadow"] = lay["shadow"][y0:y1, :] if lay["shadow"] is not None else None
    new["oy"] = lay["oy"] - y0
    new["h"] = y1 - y0
    new["foot_runs"] = [(x, y - y0 // 4, n) for x, y, n in lay["foot_runs"]]
    new["foot_anchor_y_px"] = anchor - y0
    new["depth_runs"] = [(x, y - y0, n, d) for x, y, n, d in lay["depth_runs"]]
    return new


def compose_bench_group():
    """banco_grupo4: four banco_entero stacked GROUP_STEP_PX apart (3 tiles), painted in order of y
    so each lower bank, body and shadow, covers the one above. The footprint is the union of the
    four. Each depth run keeps the ground of its own bank (rebased to the group's footprint anchor)
    and is kept only where its bank is the visible one."""
    bank = crop_bench_canvas(piece_layout("banco_entero"))
    bh, bw = bank["h"], bank["w"]
    H = GROUP_STEP_PX * (GROUP_BANKS - 1) + bh
    src_rgba = bank["rgba"]
    src_op = src_rgba[:, :, 3] >= 128
    src_sh = (bank["shadow"] if bank["shadow"] is not None else np.zeros((bh, bw), bool)) & ~src_op
    touched = src_op | src_sh
    rgba = np.zeros((H, bw, 4), np.uint8)
    shadow = np.zeros((H, bw), bool)
    owner = np.full((H, bw), -1, np.int16)
    cells = set()
    for i in range(GROUP_BANKS):
        dy = i * GROUP_STEP_PX
        r = rgba[dy:dy + bh]
        s = shadow[dy:dy + bh]
        o = owner[dy:dy + bh]
        r[touched] = 0
        r[src_op, :3] = src_rgba[src_op, :3]
        r[src_op, 3] = 255
        s[touched] = src_sh[touched]
        o[touched] = i
        for x, y, n in bank["foot_runs"]:
            for cx in range(x, x + n):
                cells.add((cx, y + dy // 4))
    grid = np.zeros((H // 4, bw // 4), bool)
    for cx, cy in cells:
        grid[cy, cx] = True
    foot_runs = cells_to_runs(grid)
    anchor_g = max(y * 4 + 4 for _, y, _ in foot_runs)
    depth_runs = []
    for i in range(GROUP_BANKS):
        dy = i * GROUP_STEP_PX
        d_shift = dy + bank["foot_anchor_y_px"] - anchor_g
        for x, y, n, d in bank["depth_runs"]:
            yy = y + dy
            px = x
            while px < x + n:
                if owner[yy, px] != i:
                    px += 1
                    continue
                x0 = px
                while px < x + n and owner[yy, px] == i:
                    px += 1
                depth_runs.append((x0, yy, px - x0, d + d_shift))
    return {"name": "banco_grupo4", "value": 1, "foot_runs": foot_runs,
            "foot_anchor_y_px": anchor_g, "depth_runs": depth_runs,
            "rgba": rgba, "shadow": shadow & (rgba[:, :, 3] < 128), "ox": 0, "oy": 0, "w": bw, "h": H}


def source_layout(name):
    if name in LAPIDA_NAMES: return lapida_layout(name)
    if name in COMPOSITE_NAMES: return compose_bench_group()
    return piece_layout(name)


def has_art(name):
    if name in COMPOSITE_NAMES: return True
    if name in LAPIDA_NAMES: return (LAPIDA_DIR / f"{name}.png").is_file()
    return (PROP_DIR / name / "color.png").is_file()


def load_pieces(names, phases, floor_pixels, floor_grid, floor_palette, prop_lab, tiles, phase_map=None):
    layouts = [source_layout(name) for name in names]

    def phases_for(name):
        if phase_map and name in phase_map: return phase_map[name]
        if name in LAPIDA_NAMES: return [LAPIDA_PHASE]
        return phases

    # Entradas nuevas de paleta: suelo oscurecido bajo la sombra de cada pieza, en sus fases usadas.
    shadow_colors = []
    for lay in layouts:
        if lay["shadow"] is None: continue
        ys, xs = np.nonzero(lay["shadow"])
        for pc, pr in phases_for(lay["name"]):
            for y, x in zip(ys, xs):
                c = shadow_color(floor_palette[floor_color(floor_pixels, floor_palette, floor_grid, pc * 8 + int(x), pr * 8 + int(y))])
                if c not in floor_palette and c not in shadow_colors: shadow_colors.append(c)
    floor_palette.extend(shadow_colors)
    floor_count = len(floor_palette) - 1
    result = []
    for lay in layouts:
        name, w, h, rgba, shadow = lay["name"], lay["w"], lay["h"], lay["rgba"], lay["shadow"]
        value = lay["value"]
        q = quantize_props(Image.fromarray(rgba), prop_lab)
        foot_runs = lay["foot_runs"]
        for pc, pr in phases_for(name):
            stamp_tiles = np.zeros((h // 8, w // 8), dtype=np.uint16)
            for ty in range(h // 8):
                for tx in range(w // 8):
                    sl = rgba[ty*8:ty*8+8, tx*8:tx*8+8]
                    opaque = sl[:, :, 3] >= 128
                    shade = shadow[ty*8:ty*8+8, tx*8:tx*8+8] if shadow is not None else np.zeros((8, 8), bool)
                    if not opaque.any() and not shade.any(): continue
                    pix = np.empty((8, 8), dtype=np.uint8)
                    for py in range(8):
                        for px in range(8):
                            if opaque[py, px]:
                                pix[py, px] = floor_count + 1 + int(q[ty*8+py, tx*8+px])
                            else:
                                fi = floor_color(floor_pixels, floor_palette, floor_grid,
                                                 pc * 8 + tx*8 + px, pr * 8 + ty*8 + py)
                                if shade[py, px]:
                                    pix[py, px] = floor_palette.index(shadow_color(floor_palette[fi]))
                                else:
                                    pix[py, px] = fi
                    stamp_tiles[ty, tx] = tiles.add(pix.tobytes())
            result.append({"name": name, "piece_id": PIECE_IDS.get(name, 0), "w": w//8, "h": h//8,
                           "phase_col": pc, "phase_row": pr,
                           "foot_runs": foot_runs,
                           "foot_anchor_y_px": lay["foot_anchor_y_px"],
                           "foot_value": value, "tiles": stamp_tiles,
                           "depth_runs": lay["depth_runs"]})
    return result, shadow_colors


def hash32(v):
    v ^= v >> 16; v = (v * 0x7feb352d) & 0xffffffff
    v ^= v >> 15; v = (v * 0x846ca68b) & 0xffffffff
    return (v ^ (v >> 16)) & 0xffffffff


def band_hash(seed, band, salt):
    return hash32(seed ^ ((band & 0xffffffff) * 0x9e3779b9 & 0xffffffff) ^ salt)


def placements(stamps, seed, band, occupied):
    wanted = (band_hash(seed, band, 0x68bc21eb) & 3) + 1
    anchor = band >> 2
    step = band & 3
    a = (band_hash(seed, anchor, 0x51ed270b) & 7) - 3
    b = (band_hash(seed, anchor + 1, 0x51ed270b) & 7) - 3
    delta = b - a
    lane = 256 + (a + int(delta * step / 4)) * 4
    for n in range(wanted):
        rh = band_hash(seed, band, (0x02e5be93 + n * 0x9e3779b9) & 0xffffffff)
        idx = rh % len(stamps); s = stamps[idx]
        first_x = s["phase_col"]
        while first_x < 12: first_x += 16
        xs = (64 - 6 - s["w"] - first_x) // 16 + 1
        ys = (16 - s["h"] - s["phase_row"]) // 16 + 1
        if xs <= 0 or ys <= 0 or s["phase_row"] + s["h"] > 16:
            continue
        for attempt in range(16):
            p = hash32((rh + attempt * 0x85ebca6b) & 0xffffffff)
            x, y = first_x + (p % xs) * 16, s["phase_row"] + ((p >> 16) % ys) * 16
            if x * 8 < lane + 32 and lane - 32 < (x + s["w"]) * 8: continue
            if any(x < ox+ow and ox < x+s["w"] and y < oy+oh and oy < y+s["h"] for ox, oy, ow, oh in occupied): continue
            occupied.append((x, y, s["w"], s["h"]))
            yield idx, x, y
            break


# Compositor v2 (DESIGN.md 6.9.1b, "Compositor v2: la pantalla como unidad").
# Bloque = 384 px = 48 filas de tiles = 2 pantallas de 24 filas (A = filas 0..23, B = 24..47) = 3 bandas.
# Mapa banda -> bloque (identico en source/strip.c, band_block()):
#   bandas iniciales b < 16:  bloque b // 3,                  desplazamiento (b % 3) * 16
#   bandas de rebase b >= 16: g = (b - 16) // 6, k = (b - 16) % 6,
#                             bloque -2 * (g + 1) + k // 3,   desplazamiento (k % 3) * 16
# Los bloques consecutivos quedan contiguos en el espacio y dentro de un bloque la fila 0 es la de arriba.
# El bloque mayor esta mas abajo (el jugador sube desde y=1792). Por eso el jugador entra antes por la
# mitad B (filas 24..47) que por la A; el numero de pantalla (2 * bloque + s) crece hacia abajo.
BLOCK_TILES = 48
SCREEN_TILES = 24
BAND_TILES = 16
# Bloques 4 y 5 (bandas 12..15) vacios al inicio: el jugador empieza en la banda 14.
STRIP_START_CLEAR_BANDS = 4
CATEDRAL_CLEAR_BANDS = range(16 - STRIP_START_CLEAR_BANDS, 16)
# Posiciones de tile fijas; la fila va relativa a la pantalla.
COLUMN_X = (7, 51)          # columna_entera izquierda / derecha (fases pc 7 y 3)
COLUMN_DY = 9               # base del sprite (fila 15 de 16) en la fila 23 (A) o 47 (B)
RIGHT_BENCH_X = 35          # banco_grupo4 derecho (pc 3)
LEFT_BENCH_X = (19, 16)     # banco_grupo4 izquierdo: pc 3 o pc 0, por hash; pasillo 64 o 88 px
BENCH_DY = (0, 8)           # fila de inicio del banco dentro de la pantalla (pr 0 u 8)
RELIC_X = 28                # relicario en el eje (pc 12); fila 9 (A, pr 9) o 33 (B, pr 1)
RELIC_DY = 9
TOMB_X_MIN, TOMB_X_MAX = 7, 41   # lapida: x de la estampa dentro de 56..456 px
VELA_REACH = 3              # velas junto a columna: +-3 tiles (+-24 px)
RELIC_VELA_REACH = 5        # velas junto a relicario: +-5 tiles (+-40 px)
BLOCK_MAX_PIECES = 48       # tope de piezas por bloque (strip.c reserva el mismo array)
STRIP_AXIS_PX = 256         # eje de la nave
# Salts nuevos y compartidos con source/strip.c (los de la version 1 se han retirado).
S_SCREEN_TYPE = 0x243F6A88
S_BENCH_LX = 0x85A308D3
S_BENCH_LY = 0x13198A2E
S_BENCH_RY = 0x03707344
S_VELA_N = 0xA4093822
S_VELA_PICK = 0x299F31D0
S_REL_VN = 0x082EFA98
S_REL_PICK = 0xEC4E6C89
S_LAP_N = 0x452821E6
S_LAP_POS = 0x38D01377
S_LAP_VAR = 0xBE5466CF
S_LAP_GRP = 0x34E90C6C
S_LAP_GLEN = 0xC0AC29B7
S_LAP_GPOS = 0xC97C50DD
S_LAP_GVAR = 0x3F84D5B5
FLOOR_LEFT_PX, FLOOR_RIGHT_PX = 48, 464
# Inner faces of the two columna_entera rows (sprite x=64 -> px 112 inside, x=416 -> px 392).
CENTRAL_LEFT_PX, CENTRAL_RIGHT_PX = 112, 392
BENCH_CANVAS_H_PX = 32       # alto del lienzo de un banco: caben 4 filas sin solapar tiles


def catedral_phase_map():
    """(piece -> list of (phase_col, phase_row)) that the composer can use. Baking only these
    keeps the kit within the tile budget. banco_entero is not listed: it is only the source of
    banco_grupo4, which is the bench the composer places."""
    return {
        "columna_entera": [(7, 9), (7, 1), (3, 9), (3, 1)],
        "banco_grupo4": [(3, 0), (3, 8), (0, 0), (0, 8)],
        "relicario": [(12, 9), (12, 1)],
        "vela": list(VELA_PHASES),
        **{name: list(LAPIDA_PHASES) for name in LAPIDA_NAMES},
    }


def _stamp_for(stamps, name, x, y):
    """Return the stamp index whose baked floor phase matches world tile (x, y)."""
    pc, pr = x & 15, y & 15
    for i, s in enumerate(stamps):
        if s["name"] == name and s["phase_col"] == pc and s["phase_row"] == pr:
            return i
    return None


def _masks_overlap(ax, ay, am, bx, by, bm):
    x0, y0 = max(ax, bx), max(ay, by)
    x1 = min(ax + am.shape[1], bx + bm.shape[1])
    y1 = min(ay + am.shape[0], by + bm.shape[0])
    if x0 >= x1 or y0 >= y1:
        return False
    return bool(np.any(am[y0 - ay:y1 - ay, x0 - ax:x1 - ax] & bm[y0 - by:y1 - by, x0 - bx:x1 - bx]))


def _stamp_nz(stamp):
    """Tiles the stamp actually writes (tile != 0). Empty shadow-canvas margins stay free."""
    tiles = stamp.get("tiles")
    if tiles is None:
        return np.ones((stamp["h"], stamp["w"]), dtype=bool)
    return np.array([[int(v) & 0x3ff != 0 for v in row] for row in tiles], dtype=bool)


def band_block(band):
    """Band -> (block, row offset of the band inside its block, in tiles). Same map as strip.c."""
    if band < 16:
        return band // 3, (band % 3) * BAND_TILES
    b = band - 16
    g, k = b // 6, b % 6
    return -2 * (g + 1) + k // 3, (k % 3) * BAND_TILES


def _pick(seed, sidx, salt, sub=0):
    """Hash of (seed, screen index, salt, sub). Same bits as pick_hash() in source/strip.c."""
    return band_hash(seed, sidx, salt ^ ((sub * 0x85EBCA6B) & 0xFFFFFFFF))


def _lapida_phase_fits(pc, pr, x, y):
    """A lapida stamp baked at (pc, pr) fits tile (x, y) when x - pc is a multiple of 4 and y - pr of 2.
    Python % is already positive. Same rule as stamp_for_lapida() in source/strip.c."""
    return (x - pc) % 4 == 0 and (y - pr) % 2 == 0


def _stamp_lookup(stamps, name, x, y):
    """Index of the stamp for piece `name` at block tile (x, y). Lapidas: the stamp whose phase fits
    (x, y) by the damero rule; None when no baked phase fits, and then the piece is not placed."""
    if name in LAPIDA_NAMES:
        for i, s in enumerate(stamps):
            if s["name"] == name and _lapida_phase_fits(s["phase_col"], s["phase_row"], x, y):
                return i
        return None
    return _stamp_for(stamps, name, x, y)


def _try_place(stamps, acc, cat, name, x, y, rows, clip=False):
    """Accept the piece at block tiles (x, y) when it fits the walls, the rows and the non-empty tiles
    of everything already accepted in the block. `clip`: rows below the block's last row are dropped
    (only structure may do it: a columna's last shadow row is the next block's first row). The same
    rule runs in strip.c."""
    idx = _stamp_lookup(stamps, name, x, y)
    if idx is None:
        return False
    s = stamps[idx]
    lo, hi = rows
    if x < 6 or x + s["w"] > 58 or y < lo or y >= hi:
        return False
    if y + s["h"] > hi and not clip:
        return False
    nz = _stamp_nz(s)[:hi - y]
    for r in acc:
        if _masks_overlap(x, y, nz, r["x"], r["y"], r["nz"]):
            return False
    acc.append({"cat": cat, "name": name, "idx": idx, "x": x, "y": y, "nz": nz})
    return True


def _tomb_x0(y):
    """Smallest lapida x >= TOMB_X_MIN with x == 2 * y (mod 4), the damero joint rule of DESIGN.md 6.9.1b."""
    return TOMB_X_MIN + ((((2 * y) & 3) + 1) & 3)


def _vela_cands(stamps, xs, top):
    """Vela positions of one screen (y outer, x inner) whose baked phase exists."""
    out = []
    for y in range(top, top + SCREEN_TILES - 4 + 1):
        for x in xs:
            if x < 6 or x + 4 > 58:
                continue
            if _stamp_lookup(stamps, "vela", x, y) is None:
                continue
            out.append((x, y))
    return out


def _pick_velas(stamps, acc, seed, sidx, salt, sub0, cands, n, rows):
    if not cands:
        return
    placed = 0
    for a in range(4 * n):
        if placed == n:
            break
        x, y = cands[_pick(seed, sidx, salt, sub0 + a) % len(cands)]
        if _try_place(stamps, acc, "vel", "vela", x, y, rows):
            placed += 1


def _block_records(stamps, seed, block):
    """Accepted pieces of one block. Computation order: structure (per screen: two columns, then a
    relicario or two benches), lapidas (checked against the structure, so they never sit under a bench
    or a relicario) and velas last. Emission order is lapidas, structure, velas (_emit_order)."""
    acc = []
    kinds = [_pick(seed, 2 * block + s, S_SCREEN_TYPE) & 1 for s in (0, 1)]   # 1: relicario
    for s in (0, 1):
        sidx = 2 * block + s
        top = s * SCREEN_TILES
        for x in COLUMN_X:
            _try_place(stamps, acc, "struct", "columna_entera", x, top + COLUMN_DY, (0, BLOCK_TILES), clip=True)
        if kinds[s]:
            _try_place(stamps, acc, "struct", "relicario", RELIC_X, top + RELIC_DY, (0, BLOCK_TILES))
        else:
            lx = LEFT_BENCH_X[_pick(seed, sidx, S_BENCH_LX) & 1]
            ly = top + BENCH_DY[_pick(seed, sidx, S_BENCH_LY) & 1]
            ry = top + BENCH_DY[_pick(seed, sidx, S_BENCH_RY) & 1]
            _try_place(stamps, acc, "struct", "banco_grupo4", lx, ly, (0, BLOCK_TILES))
            _try_place(stamps, acc, "struct", "banco_grupo4", RIGHT_BENCH_X, ry, (0, BLOCK_TILES))
    for s in (0, 1):
        sidx = 2 * block + s
        top = s * SCREEN_TILES
        rows = (top, top + SCREEN_TILES)
        for i in range(_pick(seed, sidx, S_LAP_N) % 3):
            y = top + _pick(seed, sidx, S_LAP_POS, i) % 13
            x0 = _tomb_x0(y)
            n_pos = (TOMB_X_MAX - x0) // 4 + 1
            x = x0 + 4 * (_pick(seed, sidx, S_LAP_POS, 16 + i) % n_pos)
            _try_place(stamps, acc, "lap", LAPIDA_NAMES[_pick(seed, sidx, S_LAP_VAR, i) % 4], x, y, rows)
        if _pick(seed, sidx, S_LAP_GRP) % 100 < 20:
            n = 4 + _pick(seed, sidx, S_LAP_GLEN) % 5
            y0 = top + (n - 1) + _pick(seed, sidx, S_LAP_GPOS) % (14 - n)
            x0b = _tomb_x0(y0)
            x_last_max = TOMB_X_MAX - 2 * (n - 1)
            if x0b <= x_last_max:
                n_pos = (x_last_max - x0b) // 4 + 1
                x0 = x0b + 4 * (_pick(seed, sidx, S_LAP_GPOS, 32) % n_pos)
                name = LAPIDA_NAMES[2 + _pick(seed, sidx, S_LAP_GVAR) % 2]
                for i in range(n):
                    _try_place(stamps, acc, "lap", name, x0 + 2 * i, y0 - i, rows)
    for s in (0, 1):
        sidx = 2 * block + s
        top = s * SCREEN_TILES
        rows = (top, top + SCREEN_TILES)
        for side, cx in enumerate(COLUMN_X):
            n = 1 + _pick(seed, sidx, S_VELA_N, side) % 2
            cands = _vela_cands(stamps, range(cx - VELA_REACH, cx + VELA_REACH + 1), top)
            _pick_velas(stamps, acc, seed, sidx, S_VELA_PICK, side * 16, cands, n, rows)
        if kinds[s]:
            n = 3 + _pick(seed, sidx, S_REL_VN) % 3
            cands = _vela_cands(stamps, range(RELIC_X - RELIC_VELA_REACH, RELIC_X + RELIC_VELA_REACH + 1), top)
            _pick_velas(stamps, acc, seed, sidx, S_REL_PICK, 0, cands, n, rows)
    return acc


def _emit_order(acc):
    return [r for cat in ("lap", "struct", "vel") for r in acc if r["cat"] == cat]


def catedral_block_plan(stamps, seed, block):
    """Pieces of one block as (piece_id, pc, pr, x_tile, y_block), in the order strip.c emits them."""
    recs = _emit_order(_block_records(stamps, seed, block))
    if len(recs) > BLOCK_MAX_PIECES:
        raise ValueError(f"block {block} has {len(recs)} pieces; cap is {BLOCK_MAX_PIECES}")
    out = []
    for r in recs:
        s = stamps[r["idx"]]
        out.append((s["piece_id"], s["phase_col"], s["phase_row"], r["x"], r["y"]))
    return out


def catedral_blocks_for_bands(n_bands):
    """Blocks that bands 0..n_bands-1 use, leaving out the cleared initial blocks 4 and 5."""
    blocks = {band_block(b)[0] for b in range(n_bands) if b not in CATEDRAL_CLEAR_BANDS}
    return sorted(b for b in blocks if b not in (4, 5))


def catedral_plan(stamps, seed=0xC0DE1234, n_bands=64):
    """Entries of every block that bands 0..n_bands-1 use, in ascending block order. Each entry keeps
    the stamp index (metrics) and the fields the parity test compares."""
    entries = []
    for block in catedral_blocks_for_bands(n_bands):
        for r in _emit_order(_block_records(stamps, seed, block)):
            s = stamps[r["idx"]]
            entries.append({"block": block, "cat": r["cat"], "name": r["name"], "idx": r["idx"],
                            "piece_id": s["piece_id"], "phase_col": s["phase_col"],
                            "phase_row": s["phase_row"], "x": r["x"], "y": r["y"]})
    return entries


def _screen_central_min(entries, stamps, block, s):
    """Narrowest free run that contains the nave axis over the rows of one screen that carry bench
    footprint. Returns px, or None when the screen has no bench."""
    top = s * SCREEN_TILES
    occ = {}
    for e in entries:
        if e["block"] != block or e["name"] != "banco_grupo4" or not (top <= e["y"] < top + SCREEN_TILES):
            continue
        for fx, fy, n in stamps[e["idx"]]["foot_runs"]:
            row = e["y"] * 2 + fy
            for cx in range(e["x"] * 2 + fx, e["x"] * 2 + fx + n):
                occ.setdefault(row, set()).add(cx)
    axis = STRIP_AXIS_PX // 4
    best = None
    for cells in occ.values():
        left = [c for c in cells if c < axis]
        right = [c for c in cells if c >= axis]
        lo = (max(left) + 1) * 4 if left else FLOOR_LEFT_PX
        hi = min(right) * 4 if right else FLOOR_RIGHT_PX
        width = hi - lo
        best = width if best is None else min(best, width)
    return best


def catedral_metrics_v2(entries, stamps, window=4):
    """Per window of `window` blocks (8 screens = 1536 px): footprint share of the usable floor and the
    narrowest central corridor over its bancada screens."""
    if not entries:
        return []
    blocks = sorted({e["block"] for e in entries})
    rows = []
    for w0 in range(blocks[0], blocks[-1] + 1, window):
        in_w = [b for b in blocks if w0 <= b < w0 + window]
        if not in_w:
            continue
        area = sum(n * 16 for e in entries if w0 <= e["block"] < w0 + window
                   for _, _, n in stamps[e["idx"]]["foot_runs"])
        floor_px = (FLOOR_RIGHT_PX - FLOOR_LEFT_PX) * BLOCK_TILES * 8 * len(in_w)
        central = [c for b in in_w for s in (0, 1)
                   for c in [_screen_central_min(entries, stamps, b, s)] if c is not None]
        rows.append({"window": f"bloques {w0}..{w0 + window - 1}",
                     "footprint_pct": 100.0 * area / floor_px,
                     "central": min(central) if central else None, "bancadas": len(central)})
    return rows


CATEDRAL_BLOCK_MIN, CATEDRAL_BLOCK_MAX = -16, 5   # bloques que cubren las 64 bandas (4 y 5 vacios)


def _catedral_worst_occlusion(plan, stamps):
    """Worst 16-band window of occlusion runs, clipped to each band as strip.c does (a run belongs to
    the band that holds its row)."""
    per_band = [0] * 64
    for b in range(64):
        if b in CATEDRAL_CLEAR_BANDS:
            continue
        block, off = band_block(b)
        for e in plan:
            if e["block"] != block:
                continue
            for x, y, n, d in stamps[e["idx"]]["depth_runs"]:
                local = e["y"] * 8 + y - off * 8
                if 0 <= local < BAND_TILES * 8:
                    per_band[b] += 1
    return max(sum(per_band[start:start + 16]) for start in range(49))


def format_metrics_v2(plan, stamps, worst=0, worst_occlusion=0):
    rows = catedral_metrics_v2(plan, stamps, window=4)
    lines = ["| modo | bloques (4 = 8 pantallas) | huella % suelo util | pasillo central min | pantallas con bancos |",
             "| :--- | :--- | ---: | :---: | :---: |"]
    for r in rows:
        central = f"{r['central']} px" if r["central"] is not None else "-"
        lines.append(f"| catedral | {r['window']} | {r['footprint_pct']:.2f} | {central} | {r['bancadas']} |")
    names = Counter(e["name"] for e in plan)
    total_foot = sum(n * 16 for e in plan for _, _, n in stamps[e["idx"]]["foot_runs"])
    floor_blocks = len({e["block"] for e in plan})
    lines += ["",
              f"- Huella total ({floor_blocks} bloques con piezas): {100.0 * total_foot / (416 * 384 * floor_blocks):.2f} % del suelo util.",
              f"- Peor ventana de 33x25 tiles: **{worst}** (< 440).",
              f"- Peor oclusion de 16 bandas: **{worst_occlusion}** runs (< {OCCLUSION_CAPACITY}).",
              "- Piezas por tipo: " + ", ".join(f"{k}={v}" for k, v in sorted(names.items())) + "."]
    return "\n".join(lines)


def _band_corridors(entries, stamps, band):
    """`central`: widest free run inside the colonnade; `lateral`: widest free opening that is
    not the axis aisle (run containing px 256). Both at the worst cell row of the band."""
    width_cells = (FLOOR_RIGHT_PX - FLOOR_LEFT_PX) // 4
    mask = [[False] * width_cells for _ in range(128 // 4)]
    for e in entries:
        if e["band"] != band or e["idx"] is None:
            continue
        for fx, fy, n in stamps[e["idx"]]["foot_runs"]:
            x0 = (e["x"] * 8 + fx * 4 - FLOOR_LEFT_PX) // 4
            y0 = (e["y"] * 8 + fy * 4 - band * 128) // 4
            if 0 <= y0 < len(mask):
                for xx in range(max(0, x0), min(width_cells, x0 + n)):
                    mask[y0][xx] = True
    central_cols = range((CENTRAL_LEFT_PX - FLOOR_LEFT_PX) // 4,
                         (CENTRAL_RIGHT_PX - FLOOR_LEFT_PX) // 4)
    axis = (256 - FLOOR_LEFT_PX) // 4
    worst_central, worst_lateral = 10 ** 9, 10 ** 9
    for row in mask:
        best = run = 0
        for c in central_cols:
            if row[c]:
                best, run = max(best, run), 0
            else:
                run += 1
        worst_central = min(worst_central, max(best, run) * 4)
        runs, start = [], None
        for c in range(width_cells):
            if not row[c]:
                if start is None:
                    start = c
            elif start is not None:
                runs.append((start, c)); start = None
        if start is not None:
            runs.append((start, width_cells))
        axis_run = next(((a, b) for a, b in runs if a <= axis < b), None)
        if axis_run and (axis_run[1] - axis_run[0]) * 4 >= 96:
            # Wide open hall: the axis run itself is a valid passage.
            lateral = max(((b - a) * 4 for a, b in runs), default=0)
        else:
            lateral = max(((b - a) * 4 for a, b in runs if (a, b) != axis_run), default=0)
        worst_lateral = min(worst_lateral, lateral)
    return {"central": worst_central, "lateral": worst_lateral}


def catedral_metrics(entries, stamps, bands=64, window=12):
    """Footprint share and corridor minimums per 12-band (1536 px = 8 screens of 192 px) window."""
    rows = []
    for b0 in range(0, bands, window):
        b1 = min(bands, b0 + window)
        area = sum(n * 16 for e in entries if b0 <= e["band"] < b1 and e["idx"] is not None
                   for _, _, n in stamps[e["idx"]]["foot_runs"])
        pct = 100.0 * area / (416 * (b1 - b0) * 128) if b1 > b0 else 0.0
        worst_central, worst_lateral = (10 ** 9, None), (10 ** 9, None)
        for b in range(b0, b1):
            cor = _band_corridors(entries, stamps, b)
            if cor["central"] < worst_central[0]:
                worst_central = (cor["central"], b)
            lateral = cor["lateral"]
            if lateral < worst_lateral[0]:
                worst_lateral = (lateral, b)
        rows.append({"window": f"bandas {b0}-{b1 - 1} ({b1 - b0})", "footprint_pct": pct,
                     "central": worst_central[0], "central_band": worst_central[1],
                     "lateral": worst_lateral[0], "lateral_band": worst_lateral[1]})
    return rows


def preview_and_budget(floor_map, stamps, tiles, seed=0xC0DE1234, mode="actual"):
    tile_pixels = [np.frombuffer(t, np.uint8).reshape(8, 8) for t in tiles.data]
    tilemap = np.tile(np.asarray(floor_map, dtype=np.uint16), (max(1, 1024 // len(floor_map)), 1))
    chosen, plan = [], None
    if mode == "catedral":
        # Mundo de bloques: el bloque b ocupa las filas (b - CATEDRAL_BLOCK_MIN) * 48 .. +47.
        n_blocks = CATEDRAL_BLOCK_MAX - CATEDRAL_BLOCK_MIN + 1
        tilemap = np.tile(np.asarray(floor_map, dtype=np.uint16), (n_blocks * BLOCK_TILES // 16, 1))
        plan = catedral_plan(stamps, seed, 64)
        chosen = [(e["block"], e["idx"], e["x"], e["y"]) for e in plan]
        for block, idx, x, y in chosen:
            s = stamps[idx]
            base = (block - CATEDRAL_BLOCK_MIN) * BLOCK_TILES + y
            for sy in range(min(s["h"], BLOCK_TILES - y)):
                for sx in range(s["w"]):
                    e = int(s["tiles"][sy, sx])
                    if e:
                        tilemap[base + sy, x + sx] = e
    else:
        for band in range(64):
            occupied = []
            if band in CATEDRAL_CLEAR_BANDS:
                continue
            for idx, x, y in placements(stamps, seed, band, occupied):
                s = stamps[idx]; chosen.append((band, idx, x, y))
                for sy in range(s["h"]):
                    for sx in range(s["w"]):
                        e = int(s["tiles"][sy, sx])
                        if not e: continue
                        tilemap[band*16+y+sy, x+sx] = e
    worst = 0
    for y in range(tilemap.shape[0] - 24):
        for x in range(64 - 32):
            count = np.unique(tilemap[y:y+25, x:x+33] & 0x3ff).size
            worst = max(worst, int(count))
    if mode == "catedral":
        worst_occlusion = _catedral_worst_occlusion(plan, stamps)
    else:
        worst_occlusion = max(
            sum(len(stamps[i]["depth_runs"]) for band, i, _x, _y in chosen if start <= band < start + 16)
            for start in range(49)
        )
    world = np.zeros((tilemap.shape[0] * 8, 512), dtype=np.uint8)
    for y in range(tilemap.shape[0]):
        for x in range(64):
            e = int(tilemap[y, x]); t = tile_pixels[e & 0x3ff]
            if e & 0x400: t = t[:, ::-1]
            if e & 0x800: t = t[::-1, :]
            world[y*8:y*8+8, x*8:x*8+8] = t
    return worst, worst_occlusion, world, chosen, plan


def make_wall_map(floor_map, tiles, palette, props, prop_lab):
    """Left wall (muro_izq_128.png over the #1c1920 backdrop) in tile columns 0..5, its mirror with
    the H flip in 58..63, and the floor in the centre. The wall repeats every 128 px = 16 tile rows,
    so the map has 16 rows. Wall colours are quantised to the prop palette, like the pieces."""
    src = np.asarray(Image.open(WALL_PNG).convert("RGBA"))
    if src.shape != (128, WALL_TILE_COLS * 8, 4):
        raise ValueError(f"muro_izq_128.png must be 48x128, got {src.shape[1]}x{src.shape[0]}")
    if len(floor_map) != 16:
        raise ValueError("the map period must be 16 tile rows")
    opaque = src[:, :, 3] >= 128
    rgb = np.where(opaque[:, :, None], src[:, :, :3], np.array(WALL_BACKDROP_RGB, np.uint8))
    comp = np.dstack([rgb, np.full(opaque.shape, 255, np.uint8)])
    q = quantize_props(Image.fromarray(comp), prop_lab)
    before = len(palette)
    table = np.zeros(256, np.uint8)
    for i in np.unique(q):
        c = props[int(i)]
        if c not in palette:
            palette.append(c)
        table[int(i)] = palette.index(c)
    new_colors = len(palette) - before
    if new_colors > WALL_MAX_NEW_COLORS:
        raise ValueError(f"wall adds {new_colors} palette colors; limit is {WALL_MAX_NEW_COLORS}")
    if len(palette) > 256:
        raise ValueError(f"shared palette requires {len(palette)} entries including transparent")
    pal_idx = table[q]
    out = []
    for ty in range(16):
        row = [int(v) for v in floor_map[ty]]
        for tx in range(WALL_TILE_COLS):
            entry = tiles.add(np.ascontiguousarray(pal_idx[ty*8:ty*8+8, tx*8:tx*8+8]).tobytes())
            row[tx] = entry
            row[63 - tx] = entry ^ 0x400
        out.append(row)
    return out, new_colors


def emit(output, palette, tiles, floor_map, stamps, packed, floor_source, worst,
         worst_occlusion, floor_n, props_n, mode="actual"):
    floor_path = str(floor_source).replace("\\", "/")
    out = [f"// Generated by tools/bake_cathedral_kit.py from floor {floor_path}, assets/environment/cathedral/props/render and assets/environment/cathedral/lapidas; floor={floor_n}, props={props_n}, shared={len(palette)}, tiles={len(tiles.data)}, worst_window={worst}, worst_occlusion_window={worst_occlusion}. Do not edit.\n",
           '#include "strip_kit.h"\n\n', '// cathedral wall (muro_izq_128) on the floor, lapidas v5 and composed props\n',
           f"static const uint16_t s_palette[256] __attribute__((aligned(4))) = {{\n"]
    palette = palette + [0] * (256-len(palette))
    for i in range(0, 256, 16): out.append("    " + ", ".join(f"0x{c:04X}" for c in palette[i:i+16]) + ",\n")
    out += ["};\n\n", f"static const uint8_t s_tiles[{len(tiles.data)}][64] __attribute__((aligned(4))) = {{\n"]
    for t in tiles.data: out.append("    { " + ", ".join(map(str, t)) + " },\n")
    out += ["};\n\n", f"static const uint16_t s_floor_map[{len(floor_map)*64}] __attribute__((aligned(4))) = {{\n"]
    for r in floor_map: out.append("    " + ", ".join(map(str, r)) + ",\n")
    out += ["};\n\n", f"static const uint8_t s_floor_collision[{len(packed)}] = {{\n"]
    for i in range(0, len(packed), 32): out.append("    " + ", ".join(f"0x{c:02X}" for c in packed[i:i+32]) + ",\n")
    out.append("};\n\n")
    for i, s in enumerate(stamps):
        flat = s["tiles"].reshape(-1)
        out.append(f"static const uint16_t s_stamp_{i}_tiles[{len(flat)}] = {{\n")
        for j in range(0, len(flat), 16): out.append("    " + ", ".join(str(int(x)) for x in flat[j:j+16]) + ",\n")
        out.append("};\n")
        if s["foot_runs"]:
            out.append(f"static const StripFootprintRun s_stamp_{i}_foot[{len(s['foot_runs'])}] = {{\n")
            for x, y, n in s["foot_runs"]: out.append(f"    {{ {x}, {y}, {n} }},\n")
            out.append("};\n")
        if s["depth_runs"]:
            out.append(f"static const StripDepthRun s_stamp_{i}_depth[{len(s['depth_runs'])}] = {{\n")
            for x, y, n, d in s["depth_runs"]: out.append(f"    {{ {x}, {y}, {n}, {d} }},\n")
            out.append("};\n")
    out.append("\nstatic const StripStamp s_stamps[] = {\n")
    for i, s in enumerate(stamps):
        fr = f"{len(s['foot_runs'])}, s_stamp_{i}_foot" if s["foot_runs"] else "0, 0"
        dr = f"{len(s['depth_runs'])}, s_stamp_{i}_depth" if s["depth_runs"] else "0, 0"
        pid = s["piece_id"] if mode == "catedral" else 0
        out.append(f"    {{ {s['w']}, {s['h']}, {s['phase_col']}, {s['phase_row']}, {s['foot_anchor_y_px']}, {s['foot_value']}, {pid}, s_stamp_{i}_tiles, {fr}, {dr} }}, // {s['name']}\n")
    out += ["};\n\n", "const StripKit g_strip_kit = {\n", "    .palette = s_palette,\n", "    .tiles = s_tiles,\n",
            f"    .num_tiles = {len(tiles.data)},\n", f"    .map_h_tiles = {len(floor_map)},\n",
            "    .floor_h_tiles = 16,\n", "    .floor_map = s_floor_map,\n",
            "    .floor_collision = s_floor_collision,\n", f"    .num_stamps = {len(stamps)},\n", "    .stamps = s_stamps,\n", "};\n"]
    with output.open("w", encoding="utf-8", newline="") as f: f.write("".join(out))


def format_metrics(entries, stamps, label="catedral", bands=64, worst=0, worst_occlusion=0):
    rows = catedral_metrics(entries, stamps, bands)
    lines = ["| modo | ventana (bandas) | huella % suelo util | pasillo central min | paso lateral min |",
             "| :--- | :--- | ---: | :---: | :---: |"]
    for r in rows:
        lines.append(f"| {label} | {r['window']} | {r['footprint_pct']:.2f} | "
                     f"{r['central']} px (banda {r['central_band']}) | "
                     f"{r['lateral']} px (banda {r['lateral_band']}) |")
    names = Counter(e["name"] for e in entries if e["idx"] is not None)
    total_foot = sum(n * 16 for e in entries if e["idx"] is not None
                     for _, _, n in stamps[e["idx"]]["foot_runs"])
    lines += ["",
              f"- Huella total ({bands} bandas): {100.0 * total_foot / (416 * bands * 128):.2f} % del suelo util.",
              f"- Peor ventana de 33x25 tiles: **{worst}** (< 440).",
              f"- Peor oclusion de 16 bandas: **{worst_occlusion}** runs (< {OCCLUSION_CAPACITY}).",
              "- Piezas por tipo: " + ", ".join(f"{k}={v}" for k, v in sorted(names.items())) + "."]
    return "\n".join(lines)


def build(floor_dir, phases=4, output=OUTPUT, preview=None, prop_names=DEFAULT_PROPS,
          mode="actual", metrics=None, dump_plan=None):
    if phases != 4: raise ValueError("--phases supports the four specified offsets: 4")
    if isinstance(prop_names, str):
        prop_names = tuple(part.strip() for part in prop_names.split(",") if part.strip())
    else:
        prop_names = tuple(prop_names)
    if not prop_names or len(set(prop_names)) != len(prop_names):
        raise ValueError("--props must be a nonempty comma-separated list without duplicates")
    if any("_v2_" in name for name in prop_names):
        raise ValueError("_v2_ prop variants are not included in this kit")
    missing = [name for name in prop_names if not has_art(name)]
    for name in missing:
        print(f"warning: piece {name!r} has no source art; skipped")
    prop_names = tuple(name for name in prop_names if name not in missing)
    if not prop_names: raise ValueError("no piece has source art")
    all_phases = [(0, 0), (8, 0), (0, 8), (8, 8)]
    if mode == "catedral":
        # Bake only (piece, phase) pairs the deterministic composer can use, and only the
        # pieces it places. `actual` keeps the full 4-phase kit and its old behaviour.
        phase_map = catedral_phase_map()
        prop_names = tuple(name for name in prop_names if name in phase_map)
        print(f"catedral kit: {len(prop_names)} pieces, {sum(len(v) for v in phase_map.values())} (piece, phase) stamps")
    else:
        phase_map = None
    floor_colors, raw_floor, grid = read_floor(floor_dir)
    tiles = Tiles()
    palette, floor_pixels, floor_map = make_floor_tiles(floor_colors, raw_floor, grid, tiles)
    props, prop_lab = read_prop_palette()
    stamps, shadow_colors = load_pieces(prop_names, all_phases, floor_pixels, grid, palette,
                                        prop_lab, tiles, phase_map=phase_map)
    # Hard budget: the 10-bit tile format cannot address more than 1024 unique tiles. Fail here,
    # before any image or source is written, instead of wrapping indices with & 0x3ff.
    if len(tiles.data) > 1024:
        raise ValueError(f"tile budget exceeded: {len(tiles.data)} baked unique tiles > 1024 "
                         f"(mode={mode}, {len(prop_names)} pieces); free tiles before baking")
    prop_remap = {}
    prop_temp_base = len(palette)
    for i, c in enumerate(props):
        if c not in palette:
            palette.append(c)
        prop_remap[prop_temp_base + i] = palette.index(c)
    remap_lut = np.arange(256, dtype=np.uint8)
    for old, new in prop_remap.items(): remap_lut[old] = new
    # Remapear los bytes de paleta de TODOS los tiles una sola vez (los indices temporales
    # floor_count+1+q pasan a indices finales). Se hace por tile, sin depender del dedupe,
    # para que ningun tile referenciado quede con indices temporales.
    for tid in range(len(tiles.data)):
        tiles.data[tid] = remap_lut[np.frombuffer(tiles.data[tid], dtype=np.uint8)].tobytes()
    tiles.index = {t: i for i, t in enumerate(tiles.data)}
    # Fusionar los tiles que han quedado identicos (tambien bajo flip) y reescribir las
    # referencias; sin esto el remapeo en sitio deja duplicados y agota el tope de 1024.
    uniq = Tiles()
    merge = [0] * len(tiles.data)
    for tid in range(len(tiles.data)):
        merge[tid] = uniq.add(tiles.data[tid])
    tiles.data, tiles.index = uniq.data, uniq.index

    def remap_entry(e):
        e = int(e)
        if not e:
            return 0
        ne = merge[e & 0x3ff]
        return (ne & 0x3ff) | ((e ^ ne) & 0xc00)

    floor_map = [[remap_entry(v) for v in row] for row in floor_map]
    for st in stamps:
        st["tiles"] = np.vectorize(remap_entry, otypes=[np.uint16])(st["tiles"])
    map_map, wall_new = make_wall_map(floor_map, tiles, palette, props, prop_lab)
    if mode == "catedral" and len(tiles.data) > 1024:
        raise ValueError(f"tile budget exceeded: {len(tiles.data)} unique tiles including the wall "
                         f"map > 1024 (mode=catedral); free tiles before baking")
    if len(palette) > 256: raise ValueError(f"shared palette requires {len(palette)} entries including transparent")
    collision = np.zeros((32, 128), np.uint8)
    collision[:, :12] = 3; collision[:, 116:] = 3
    flat = collision.reshape(-1)
    packed = (flat[0::4] | (flat[1::4] << 2) | (flat[2::4] << 4) | (flat[3::4] << 6)).astype(np.uint8)
    # Compactar: tras el remapeo de colores los tiles previos de las piezas quedan sin referencia; no se emiten.
    used = {0}
    for row in map_map: used |= {int(v) & 0x3ff for v in row}
    for st in stamps: used |= {int(v) & 0x3ff for v in st["tiles"].flat if int(v)}
    order = sorted(used); new_id = {o: n for n, o in enumerate(order)}
    if len(order) > 1024:
        raise ValueError(f"tile budget exceeded: {len(order)} referenced unique tiles > 1024 "
                         f"(mode={mode}); free tiles before baking")
    def renum(v):
        v = int(v); return v if not v else (new_id[v & 0x3ff] | (v & 0xc00))
    map_map = [[renum(v) if int(v) else 0 for v in row] for row in map_map]
    for st in stamps: st["tiles"] = np.vectorize(renum, otypes=[np.uint16])(st["tiles"])
    tiles.data = [tiles.data[o] for o in order]
    tiles.index = {t: i for i, t in enumerate(tiles.data)}
    if len(tiles.data) > 1024: raise ValueError(f"total tile count {len(tiles.data)} exceeds 1024")
    worst, worst_occlusion, sample, chosen, plan = preview_and_budget(
        map_map, stamps, tiles, mode=mode)
    if worst >= 440: raise ValueError(f"worst 33x25 window has {worst} tiles; must be < 440")
    if worst_occlusion >= OCCLUSION_CAPACITY:
        raise ValueError(f"worst 16-band occlusion window has {worst_occlusion} runs; capacity is {OCCLUSION_CAPACITY}")
    if preview:
        rgb_palette = [0] * 768
        for i, c in enumerate(palette): rgb_palette[i*3:i*3+3] = list(rgb555(c))
        im = Image.fromarray(sample, "P"); im.putpalette(rgb_palette)
        preview.parent.mkdir(parents=True, exist_ok=True); im.convert("RGB").save(preview)
    floor_n = len(set(floor_colors)); props_n = len(set(props))
    emit(output, palette, tiles, map_map, stamps, packed, floor_dir, worst, worst_occlusion, floor_n, props_n, mode)
    if dump_plan is not None and mode == "catedral":
        dumped = [{"block": e["block"], "piece_id": stamps[e["idx"]]["piece_id"],
                   "phase_col": stamps[e["idx"]]["phase_col"],
                   "phase_row": stamps[e["idx"]]["phase_row"],
                   "x": e["x"], "y": e["y"]} for e in plan]
        dump_plan.parent.mkdir(parents=True, exist_ok=True)
        dump_plan.write_text(json.dumps(dumped), encoding="utf-8")
        print(f"plan: {dump_plan} ({len(dumped)} stamps)")
    print(f"palette entries: floor={len(set(floor_colors))}, props={len(set(props))}, shadow={len(shadow_colors)} new, wall={wall_new} new, shared={len(palette)}/256")
    print(f"tiles: {len(tiles.data)}/1024; worst window: {worst}/<440; selected pieces in 64 bands: {len(chosen)}")
    print(f"worst 16-band occlusion runs: {worst_occlusion}/{OCCLUSION_CAPACITY}")
    if mode == "catedral" or metrics:
        if mode == "catedral":
            text = format_metrics_v2(plan, stamps, worst=worst, worst_occlusion=worst_occlusion)
        else:
            entries = [{"kind": "piece", "name": stamps[i]["name"], "idx": i, "x": x,
                        "y": band * 16 + y, "band": band} for band, i, x, y in chosen]
            text = format_metrics(entries, stamps, "actual", worst=worst,
                                  worst_occlusion=worst_occlusion)
        print(text)
        if metrics:
            metrics.parent.mkdir(parents=True, exist_ok=True)
            metrics.write_text("# Metricas de distribucion (vista previa Python)\n\n" + text + "\n",
                               encoding="utf-8")
            print(f"metrics: {metrics}")
    if preview: print(f"preview: {preview}")
    return len(tiles.data), worst


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--floor", required=True, type=Path)
    p.add_argument("--phases", type=int, default=4)
    p.add_argument("--props", default=",".join(DEFAULT_PROPS),
                   help="comma-separated pieces (default: " + ",".join(DEFAULT_PROPS) + ")")
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--preview", type=Path, default=Path(os.environ.get("TEMP", "/tmp")) / "cathedral_strip_preview.png")
    p.add_argument("--mode", choices=("actual", "catedral"), default="actual",
                   help="actual: random 1-4 pieces per band (default); catedral: deterministic composer")
    p.add_argument("--metrics", type=Path, default=None,
                   help="write the catedral metrics Markdown table here")
    p.add_argument("--dump-plan", type=Path, default=None,
                   help="write the deterministic cathedral plan as JSON (parity test)")
    a = p.parse_args()
    build(a.floor, a.phases, a.output, a.preview, a.props, a.mode, a.metrics, a.dump_plan)


if __name__ == "__main__": main()
