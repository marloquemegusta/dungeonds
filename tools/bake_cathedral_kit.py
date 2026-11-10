#!/usr/bin/env python3
"""Bake the cathedral floor, wall cycle, lancets and props into the strip kit."""
import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROP_DIR = ROOT / "assets/environment/cathedral/props/render"
PROP_PALETTE = ROOT / "assets/environment/cathedral/palette/palette.json"
OUTPUT = ROOT / "source/strip_kit.c"
DEFAULT_PROPS = ("banco_roto", "banco_volcado", "columna", "relicario", "santo", "vela",
                 "lapida_cruz_h", "lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v",
                 "lapida_cruz2_h", "lapida_cruz2_v", "lapida_caballero2_h", "lapida_caballero2_v")
# Piezas que solo llevan una fase (lapidas: sin colision ni sombra y el presupuesto de tiles no da para 4).
SINGLE_PHASE_PREFIXES = ("lapida_",)
# Lapidas de suelo: cluster de rombos de un solo tono bajo la pieza y junta oscura alrededor,
# igual que el prototipo aprobado tools/catalogo/cat_lapidas_cluster.py (variante V1).
LAPIDA_PREFIX = "lapida_"
LAPIDA_PAD = 40          # margen en px (multiplo de 8) para que quepan cluster y junta
CLUSTER_MARGIN = 20      # distancia centro de rombo <-> bbox de la lapida (px)
RH_HALF_W, RH_HALF_H = 16, 8   # semiejes del rombo de 32x16 px
JOINT_RGB = (52, 46, 38)       # junta oscura del prototipo
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
    runs = []
    for cy, row in enumerate(cells):
        cx = 0
        while cx < grid_w:
            if not row[cx]:
                cx += 1
                continue
            x0 = cx
            while cx < grid_w and row[cx]:
                cx += 1
            runs.append((x0, cy, cx - x0))
    return runs


def shadow_color(c):
    # mismo oscurecimiento al 50 % que apply_shadow_fast (source/main.c)
    return ((c & 0x7BDE) >> 1) | 0x8000


def bgr555(rgb):
    r, g, b = (min(31, max(0, int(round(float(v) * 31 / 255)))) for v in rgb)
    return (b << 10) | (g << 5) | r | 0x8000


def diamond_mask(shape, cx, cy):
    ys, xs = np.mgrid[0:shape[0], 0:shape[1]]
    return (np.abs(xs - cx) / RH_HALF_W + np.abs(ys - cy) / RH_HALF_H) < 1.0


def shift_mask(mask, dx, dy):
    out = np.zeros_like(mask)
    ys_src = slice(max(0, -dy), mask.shape[0] - max(0, dy))
    ys_dst = slice(max(0, dy), mask.shape[0] - max(0, -dy))
    xs_src = slice(max(0, -dx), mask.shape[1] - max(0, dx))
    xs_dst = slice(max(0, dx), mask.shape[1] - max(0, -dx))
    out[ys_dst, xs_dst] = mask[ys_src, xs_src]
    return out


def lapida_tone(floor_pixels, floor_palette, floor_grid):
    # Tono medio de los rombos del suelo, igual que stone_tone() del prototipo: mediana del
    # color medio de los rombos del periodo 16x16 (un solo tono para toda la lapida).
    rgb = np.zeros((128, 128, 3), dtype=np.float64)
    for y in range(128):
        for x in range(128):
            rgb[y, x] = rgb555(floor_palette[floor_color(floor_pixels, floor_palette, floor_grid, x, y)])
    xs, ys = np.mgrid[0:128, 0:128]
    tones = []
    for cy in range(8, 128, 16):
        for cx in range(16, 128, 32):
            m = (np.abs(xs - cx) / RH_HALF_W + np.abs(ys - cy) / RH_HALF_H) < 1.0
            tones.append(rgb[m].mean(axis=0))
    return bgr555(np.median(np.stack(tones), axis=0))


def lapida_stamps(lay, phases, floor_pixels, floor_palette, floor_grid, prop_lab,
                  floor_count, tone_index, joint_index, tiles):
    # Amplia el lienzo para que quepan el cluster (rombo a rombo) y la junta fuera del bbox.
    name, w, h, rgba = lay["name"], lay["w"], lay["h"], lay["rgba"]
    pad = LAPIDA_PAD
    W, H = w + 2 * pad, h + 2 * pad
    full = np.zeros((H, W, 4), np.uint8)
    full[pad:pad + h, pad:pad + w] = rgba
    solid = full[:, :, 3] >= 128
    ys, xs = np.nonzero(solid)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    cluster = np.zeros((H, W), bool)
    for cy in range(0, H + 2 * RH_HALF_H, 2 * RH_HALF_H):
        for cx in range(0, W + 2 * RH_HALF_W, 2 * RH_HALF_W):
            for ccx, ccy in ((cx, cy), (cx + RH_HALF_W, cy + RH_HALF_H)):
                if not (x0 - CLUSTER_MARGIN <= ccx <= x1 + CLUSTER_MARGIN and
                        y0 - CLUSTER_MARGIN <= ccy <= y1 + CLUSTER_MARGIN):
                    continue
                cluster |= diamond_mask((H, W), ccx, ccy)
    joint = solid.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                joint |= shift_mask(solid, dx, dy)
    joint &= ~solid
    q = quantize_props(Image.fromarray(full), prop_lab)
    result = []
    for pc, pr in piece_phases(name, phases):
        stamp_tiles = np.zeros((H // 8, W // 8), dtype=np.uint16)
        for ty in range(H // 8):
            for tx in range(W // 8):
                sy, sx = ty * 8, tx * 8
                s_solid = solid[sy:sy + 8, sx:sx + 8]
                s_cluster = cluster[sy:sy + 8, sx:sx + 8]
                s_joint = joint[sy:sy + 8, sx:sx + 8]
                if not s_solid.any() and not s_cluster.any() and not s_joint.any():
                    continue
                pix = np.empty((8, 8), dtype=np.uint8)
                for py in range(8):
                    for px in range(8):
                        gy, gx = sy + py, sx + px
                        if solid[gy, gx]:
                            pix[py, px] = floor_count + 1 + int(q[gy, gx])
                        elif joint[gy, gx]:
                            pix[py, px] = joint_index
                        elif cluster[gy, gx]:
                            pix[py, px] = tone_index
                        else:
                            pix[py, px] = floor_color(floor_pixels, floor_palette, floor_grid,
                                                      pc * 8 + gx, pr * 8 + gy)
                stamp_tiles[ty, tx] = tiles.add(pix.tobytes())
        result.append({"name": name, "w": W // 8, "h": H // 8, "phase_col": pc, "phase_row": pr,
                       "foot_runs": [], "foot_anchor_y_px": 0, "foot_value": 0,
                       "tiles": stamp_tiles, "depth_runs": []})
    return result


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
    value = 0 if name.startswith("lapida_") else (3 if name in ("columna", "santo") else 1)
    try:
        foot_runs = [] if value == 0 else footprint_runs(foot)
    except ValueError as e:
        raise ValueError(f"{name}: {e}") from None
    foot_anchor_y_px = max((y * 4 + 4 for _, y, _ in foot_runs), default=0)
    depth_runs = piece_depth_runs(depth, rgba, foot_anchor_y_px) if value != 0 else []
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


def piece_phases(name, phases):
    return phases[:1] if name.startswith(SINGLE_PHASE_PREFIXES) else phases


def load_pieces(names, phases, floor_pixels, floor_grid, floor_palette, prop_colors, prop_lab, tiles):
    layouts = [piece_layout(name) for name in names]
    # Entradas nuevas de paleta: suelo oscurecido bajo la sombra de cada pieza, en las 4 fases.
    shadow_colors = []
    for lay in layouts:
        if lay["shadow"] is None: continue
        ys, xs = np.nonzero(lay["shadow"])
        for pc, pr in piece_phases(lay["name"], phases):
            for y, x in zip(ys, xs):
                c = shadow_color(floor_palette[floor_color(floor_pixels, floor_palette, floor_grid, pc * 8 + int(x), pr * 8 + int(y))])
                if c not in floor_palette and c not in shadow_colors: shadow_colors.append(c)
    floor_palette.extend(shadow_colors)
    # Colores propios de las lapidas: cluster de un tono y junta oscura (no deben alterar los
    # bordes de muro, que eligen su tono entre el resto de la paleta).
    decor_colors = []
    tone_index = joint_index = None
    if any(lay["name"].startswith(LAPIDA_PREFIX) for lay in layouts):
        tone = lapida_tone(floor_pixels, floor_palette, floor_grid)
        joint = bgr555(JOINT_RGB)
        for c in (tone, joint):
            if c not in floor_palette and c not in decor_colors: decor_colors.append(c)
        floor_palette.extend(decor_colors)
        tone_index = floor_palette.index(tone)
        joint_index = floor_palette.index(joint)
    floor_count = len(floor_palette) - 1
    result = []
    for lay in layouts:
        name, w, h, rgba, shadow = lay["name"], lay["w"], lay["h"], lay["rgba"], lay["shadow"]
        value = lay["value"]
        if name.startswith(LAPIDA_PREFIX):
            result.extend(lapida_stamps(lay, phases, floor_pixels, floor_palette, floor_grid,
                                        prop_lab, floor_count, tone_index, joint_index, tiles))
            continue
        q = quantize_props(Image.fromarray(rgba), prop_lab)
        foot_runs = lay["foot_runs"]
        for pc, pr in piece_phases(name, phases):
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
            result.append({"name": name, "w": w//8, "h": h//8, "phase_col": pc, "phase_row": pr,
                           "foot_runs": foot_runs,
                           "foot_anchor_y_px": lay["foot_anchor_y_px"],
                           "foot_value": value, "tiles": stamp_tiles,
                           "depth_runs": lay["depth_runs"]})
    return result, shadow_colors, decor_colors


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


def preview_and_budget(floor_map, stamps, tiles, seed=0xC0DE1234):
    tile_pixels = [np.frombuffer(t, np.uint8).reshape(8, 8) for t in tiles.data]
    tilemap = np.tile(np.asarray(floor_map, dtype=np.uint16), (max(1, 1024 // len(floor_map)), 1))
    chosen = []
    for band in range(64):
        occupied = []
        if 13 <= band < 16:
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
    return worst, worst_occlusion, world, chosen


def make_cathedral_map(floor_map, tiles, palette):
    """Compose a 1024 px cathedral scene cycle over the 128 px floor cycle."""
    def color_index(rgb):
        value = bgr555(rgb)
        if value not in palette:
            palette.append(value)
        return palette.index(value)

    stone = color_index((88, 81, 70))
    stone_light = color_index((118, 108, 91))
    stone_dark = color_index((54, 49, 45))
    lead = color_index((26, 22, 30))
    burgundy = color_index((111, 32, 52))
    violet = color_index((47, 47, 111))
    blue = color_index((45, 74, 106))
    gold = color_index((161, 106, 43))

    period = np.zeros((128, 512), dtype=np.uint8)
    source_tiles = [np.frombuffer(t, np.uint8).reshape(8, 8) for t in tiles.data]
    for ty, row in enumerate(floor_map):
        for tx, entry in enumerate(row):
            entry = int(entry)
            tile = source_tiles[entry & 0x3ff]
            if entry & 0x400: tile = tile[:, ::-1]
            if entry & 0x800: tile = tile[::-1, :]
            period[ty*8:ty*8+8, tx*8:tx*8+8] = tile
    period = np.tile(period, (8, 1))

    for y in range(1024):
        side_cycle = y // 128
        for x in list(range(48)) + list(range(464, 512)):
            lx = x if x < 48 else 511 - x
            # Warm-gray ashlar with a readable plinth, pilaster and quiet mortar joints.
            c = stone if ((lx // 8 + y // 24) & 1) else stone_dark
            if 39 <= lx < 46: c = stone_light
            if lx < 4: c = stone_dark
            if y % 128 in (0, 1, 126, 127): c = stone_dark
            if y % 128 in (2, 3, 124, 125) and lx < 47: c = stone_light
            period[y, x] = c

    def paint_pair(base_y, right=False):
        for py in range(48):
            for px in range(32):
                xx = 31-px if right else px
                x = 480 + xx if right else xx
                y = base_y + py
                # Twin lancets: pointed crowns, warm stone archivolt, lead and jewel tones.
                for cx in (8, 24):
                    dy = py - 3
                    half = max(1, min(6, (dy * 3) // 14))
                    dx = abs(px - cx)
                    if dy < 0 or dy > 42 or dx > half:
                        continue
                    edge = dx == half or dy >= 40
                    if edge:
                        c = stone_light
                    elif dx == 0 or py in (16, 30):
                        c = lead
                    elif (px + py // 5) % 7 == 0:
                        c = gold
                    elif (cx == 8) ^ (py >= 24) ^ ((px // 3) & 1):
                        c = burgundy
                    elif (py // 5) & 1:
                        c = violet
                    else:
                        c = blue
                    period[y, x] = c
        # Central mullion and outer stone casing survive the 8x8 tile reduction.
        for py in range(5, 47):
            for lx in (15, 16):
                x = (480 + (31-lx if right else lx)) if right else lx
                period[base_y+py, x] = stone_light

    # Emitter contract: side alternates every 256 px; the scene repeats after 1024 px.
    for base_y, right in ((80, False), (336, True), (592, False), (848, True)):
        paint_pair(base_y, right)

    # A non-blocking crossing threshold with a rose inlay; at world Y=1056 each cycle.
    for y in range(32, 56):
        for x in range(48, 464):
            period[y, x] = stone_light if y in (32, 33, 54, 55) else stone
    for y in range(16, 72):
        for x in range(228, 284):
            dx, dy = x - 256, y - 44
            radius = dx * dx + dy * dy
            if radius <= 26*26:
                if radius >= 22*22 or abs(dx) <= 1 or abs(dy) <= 1:
                    period[y, x] = gold if (radius // 36) & 1 else lead
                else:
                    sector = ((math.atan2(dy, dx) + math.pi) * 6 / math.pi) % 6
                    period[y, x] = (burgundy, violet, blue, gold, violet, burgundy)[int(sector)]

    result = []
    for ty in range(period.shape[0] // 8):
        row = []
        for tx in range(64):
            tile = period[ty*8:ty*8+8, tx*8:tx*8+8]
            row.append(tiles.add(tile.tobytes()))
        result.append(row)
    return result


def emit(output, palette, tiles, floor_map, stamps, packed, floor_source, worst,
         worst_occlusion, floor_n, props_n):
    floor_path = str(floor_source).replace("\\", "/")
    out = [f"// Generated by tools/bake_cathedral_kit.py from floor {floor_path} and assets/environment/cathedral/props/render; floor={floor_n}, props={props_n}, shared={len(palette)}, tiles={len(tiles.data)}, worst_window={worst}, worst_occlusion_window={worst_occlusion}. Do not edit.\n",
           '#include "strip_kit.h"\n\n', '// first-pass cathedral walls and alternating paired lancets\n',
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
        out.append(f"    {{ {s['w']}, {s['h']}, {s['phase_col']}, {s['phase_row']}, {s['foot_anchor_y_px']}, {s['foot_value']}, s_stamp_{i}_tiles, {fr}, {dr} }}, // {s['name']}\n")
    out += ["};\n\n", "const StripKit g_strip_kit = {\n", "    .palette = s_palette,\n", "    .tiles = s_tiles,\n",
            f"    .num_tiles = {len(tiles.data)},\n", f"    .map_h_tiles = {len(floor_map)},\n",
            "    .floor_h_tiles = 16,\n", "    .floor_map = s_floor_map,\n",
            "    .floor_collision = s_floor_collision,\n", f"    .num_stamps = {len(stamps)},\n", "    .stamps = s_stamps,\n", "};\n"]
    with output.open("w", encoding="utf-8", newline="") as f: f.write("".join(out))


def build(floor_dir, phases=4, output=OUTPUT, preview=None, prop_names=DEFAULT_PROPS):
    if phases != 4: raise ValueError("--phases supports the four specified offsets: 4")
    if isinstance(prop_names, str):
        prop_names = tuple(part.strip() for part in prop_names.split(",") if part.strip())
    else:
        prop_names = tuple(prop_names)
    if not prop_names or len(set(prop_names)) != len(prop_names):
        raise ValueError("--props must be a nonempty comma-separated list without duplicates")
    if any("_v2_" in name for name in prop_names):
        raise ValueError("_v2_ prop variants are not included in this kit")
    missing = [name for name in prop_names if not (PROP_DIR / name / "color.png").is_file()]
    for name in missing:
        print(f"warning: prop {name!r} has no render/color.png; skipped")
    prop_names = tuple(name for name in prop_names if name not in missing)
    if not prop_names: raise ValueError("no prop has render/color.png")
    floor_colors, raw_floor, grid = read_floor(floor_dir)
    tiles = Tiles()
    palette, floor_pixels, floor_map = make_floor_tiles(floor_colors, raw_floor, grid, tiles)
    props, prop_lab = read_prop_palette()
    stamps, shadow_colors, decor_colors = load_pieces(prop_names, [(0, 0), (8, 0), (0, 8), (8, 8)],
                                                     floor_pixels, grid, palette, props, prop_lab, tiles)
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
    map_map = make_cathedral_map(floor_map, tiles, palette)
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
    def renum(v):
        v = int(v); return v if not v else (new_id[v & 0x3ff] | (v & 0xc00))
    map_map = [[renum(v) if int(v) else 0 for v in row] for row in map_map]
    for st in stamps: st["tiles"] = np.vectorize(renum, otypes=[np.uint16])(st["tiles"])
    tiles.data = [tiles.data[o] for o in order]
    tiles.index = {t: i for i, t in enumerate(tiles.data)}
    if len(tiles.data) > 1024: raise ValueError(f"total tile count {len(tiles.data)} exceeds 1024")
    worst, worst_occlusion, sample, chosen = preview_and_budget(map_map, stamps, tiles)
    if worst >= 440: raise ValueError(f"worst 33x25 window has {worst} tiles; must be < 440")
    if worst_occlusion >= OCCLUSION_CAPACITY:
        raise ValueError(f"worst 16-band occlusion window has {worst_occlusion} runs; capacity is {OCCLUSION_CAPACITY}")
    if preview:
        rgb_palette = [0] * 768
        for i, c in enumerate(palette): rgb_palette[i*3:i*3+3] = list(rgb555(c))
        im = Image.fromarray(sample, "P"); im.putpalette(rgb_palette)
        preview.parent.mkdir(parents=True, exist_ok=True); im.convert("RGB").save(preview)
    floor_n = len(set(floor_colors)); props_n = len(set(props))
    emit(output, palette, tiles, map_map, stamps, packed, floor_dir, worst, worst_occlusion, floor_n, props_n)
    print(f"palette entries: floor={floor_n}, props={props_n}, shadow={len(shadow_colors)} new, lapida={len(decor_colors)} new, wall_palette=8, shared={len(palette)}/256")
    print(f"tiles: {len(tiles.data)}/1024; worst window: {worst}/<440; selected pieces in 64 bands: {len(chosen)}")
    print(f"worst 16-band occlusion runs: {worst_occlusion}/{OCCLUSION_CAPACITY}")
    if preview: print(f"preview: {preview}")
    return len(tiles.data), worst


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--floor", required=True, type=Path)
    p.add_argument("--phases", type=int, default=4)
    p.add_argument("--props", default=",".join(DEFAULT_PROPS),
                   help="comma-separated props (default: " + ",".join(DEFAULT_PROPS) + ")")
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--preview", type=Path, default=Path(os.environ.get("TEMP", "/tmp")) / "cathedral_strip_preview.png")
    a = p.parse_args()
    build(a.floor, a.phases, a.output, a.preview, a.props)


if __name__ == "__main__": main()
