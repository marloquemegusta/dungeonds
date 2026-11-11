#!/usr/bin/env python3
"""Bake the cathedral floor, wall cycle, lancets and props into the strip kit."""
import argparse
import json
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
                 "lapida_cruz2_h", "lapida_cruz2_v", "lapida_caballero2_h", "lapida_caballero2_v",
                 "banco_entero", "sacos", "columna_entera")
# Piezas que solo llevan una fase (lapidas: sin colision ni sombra y el presupuesto de tiles no da para 4).
SINGLE_PHASE_PREFIXES = ("lapida_",)
# Piece ids emitted in StripStamp.piece_id; must match enum STRIP_PIECE_* in include/strip_kit.h.
PIECE_IDS = {
    "banco_entero": 1, "banco_roto": 2, "banco_volcado": 3, "columna": 4,
    "columna_entera": 5, "relicario": 6, "santo": 7, "vela": 8, "sacos": 9,
    "lapida_cruz_h": 10, "lapida_cruz_v": 11, "lapida_caballero_h": 12,
    "lapida_caballero_v": 13, "lapida_cruz2_h": 14, "lapida_cruz2_v": 15,
    "lapida_caballero2_h": 16, "lapida_caballero2_v": 17,
}


def piece_id(name):
    return PIECE_IDS.get(name, 0)
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
        result.append({"name": name, "piece_id": piece_id(name), "w": W // 8, "h": H // 8,
                       "phase_col": pc, "phase_row": pr,
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
    value = 0 if name.startswith("lapida_") else (3 if name in ("columna", "columna_entera", "santo") else 1)
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


def crop_shadow_layout(lay, margin_px=8):
    """Crop a layout to body + margin on each side so wide shadow canvases stop blocking
    neighbouring reticle slots. Kept in memory for pieces that also ship in `--mode actual`."""
    if lay["shadow"] is None or margin_px < 0:
        return lay
    sw, sh = lay["w"], lay["h"]
    ox, oy = lay["ox"], lay["oy"]
    opaque = lay["rgba"][:, :, 3] >= 128
    ys, xs = np.nonzero(opaque)
    if not len(xs):
        return lay
    bx0, bx1 = int(xs.min()), int(xs.max()) + 1
    by0, by1 = int(ys.min()), int(ys.max()) + 1
    x0 = max(0, (bx0 - margin_px) // 8 * 8)
    x1 = min(sw, ((bx1 + margin_px + 7) // 8) * 8)
    y0 = max(0, (by0 - margin_px) // 8 * 8)
    y1 = min(sh, ((by1 + margin_px + 7) // 8) * 8)
    if (x0, y0, x1, y1) == (0, 0, sw, sh):
        return lay
    new = dict(lay)
    new["rgba"] = lay["rgba"][y0:y1, x0:x1]
    new["shadow"] = lay["shadow"][y0:y1, x0:x1]
    new["ox"] = ox - x0
    new["oy"] = oy - y0
    new["w"] = x1 - x0
    new["h"] = y1 - y0
    new["foot_runs"] = [(x - x0 // 4, y - y0 // 4, n) for x, y, n in lay["foot_runs"]]
    new["foot_anchor_y_px"] = lay["foot_anchor_y_px"] - y0
    new["depth_runs"] = [(x - x0, y - y0, n, d) for x, y, n, d in lay["depth_runs"]]
    return new


def crop_bench_canvas(lay, target_h_px=None):
    """Clamp a bench stamp to a 32 px (4-tile) canvas anchored at the footprint base so two
    benches 32 px apart never share a tile row. banco_entero only loses its empty bottom row;
    banco_roto loses its 8 px top row (back-post tips), keeping the footprint row and base."""
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


def piece_phases(name, phases):
    return phases[:1] if name.startswith(SINGLE_PHASE_PREFIXES) else phases


def load_pieces(names, phases, floor_pixels, floor_grid, floor_palette, prop_colors, prop_lab, tiles,
                phase_map=None, shadow_crop=(), bench_crop=()):
    def build_layout(name):
        lay = piece_layout(name)
        if name in shadow_crop:
            lay = crop_shadow_layout(lay)
        if name in bench_crop:
            lay = crop_bench_canvas(lay)
        return lay

    layouts = [build_layout(name) for name in names]

    def phases_for(name):
        return phase_map.get(name, phases) if phase_map else phases

    # Entradas nuevas de paleta: suelo oscurecido bajo la sombra de cada pieza, en sus fases usadas.
    shadow_colors = []
    for lay in layouts:
        if lay["shadow"] is None: continue
        ys, xs = np.nonzero(lay["shadow"])
        for pc, pr in piece_phases(lay["name"], phases_for(lay["name"])):
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
            result.extend(lapida_stamps(lay, phases_for(name), floor_pixels, floor_palette, floor_grid,
                                        prop_lab, floor_count, tone_index, joint_index, tiles))
            continue
        q = quantize_props(Image.fromarray(rgba), prop_lab)
        foot_runs = lay["foot_runs"]
        for pc, pr in piece_phases(name, phases_for(name)):
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
            result.append({"name": name, "piece_id": piece_id(name), "w": w//8, "h": h//8,
                           "phase_col": pc, "phase_row": pr,
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


CATEDRAL_COLUMNS = (8, 48)   # columna_entera (6-tile canvas): bodies px 72..112 and 392..432
# Zona inicial sin piezas. C manda (source/strip.c): las ultimas STRIP_START_CLEAR_BANDS bandas de
# las STRIP_INITIAL_BANDS iniciales. En la variante de debug `lapidas` (LAPIDA_DEBUG) C ademas salta
# las bandas 11..15; esa variante no se modela en la vista previa.
STRIP_INITIAL_BANDS = 16     # STRIP_BAND_TILES = 128/8 = 16; 2048 px / 128 px = 16 bandas
STRIP_START_CLEAR_BANDS = 3
CATEDRAL_CLEAR_BANDS = range(STRIP_INITIAL_BANDS - STRIP_START_CLEAR_BANDS, STRIP_INITIAL_BANDS)
S_COL_L, S_COL_R = 0x1a2b3c4d, 0x5e6f7a8b
S_BANK_TYPE = 0x2f9e1b77     # banco_entero / banco_roto por banco (banda, fila, slot)
S_BANK_LEN = 0x9be2f431      # tamano del grupo (4/5/6) por fila y tramo
S_BANK_START = 0x5bd1e995    # posicion de inicio del grupo dentro de los 8 slots del tramo
S_BARRICADE, S_DECOR = 0x73c1d0a5, 0x41c64e6d
FLOOR_LEFT_PX, FLOOR_RIGHT_PX = 48, 464
# Inner faces of the two columna_entera rows (x=8 -> px 72..112, x=48 -> px 392..432).
CENTRAL_LEFT_PX, CENTRAL_RIGHT_PX = 112, 392
CROSS_SANTOS = (16, 40)      # santo (6-tile canvas, ox=2): body centres px 160 and 352
BENCH_ROWS = (19, 35)        # carriles centrados en x=256: cuerpos px 160..224 y 288..352
BENCH_STEP_TILES = 4         # bancos pegados: una fila cada 32 px (4 tiles), y_local 0/4/8/12
BENCH_CANVAS_H_PX = 32       # alto del lienzo de un banco: caben 4 filas sin solapar tiles
BENCH_SLOTS = 8              # 8 posiciones de 32 px por fila y tramo (4 por banda)
BENCH_GROUP_LENS = (4, 5, 6)  # tamano del grupo: 25 % / 50 % / 25 %
SACOS_LINE = (16, 24, 32)    # staggered in y so adjacent stamps share no 2-D tile
TOMB_X = 16                  # lapida_cruz_h canvas is 18 tiles: fits between the columns
VELA_XS = (8, 24, 32, 48)
RELIC_XS = (8, 48)


def catedral_phase_map():
    """(piece -> list of (phase_col, phase_row)) that the composer can use. Baking only these
    keeps the kit within the tile budget; every position the rules allow is included."""
    def add(xs, ys):
        return sorted({(x & 15, y) for x in xs for y in ys})
    return {
        "columna_entera": add(CATEDRAL_COLUMNS, (0,)),
        "columna": add(CATEDRAL_COLUMNS, (8,)),
        "banco_entero": add(BENCH_ROWS, (0, 4, 8, 12)),
        "banco_roto": add(BENCH_ROWS, (0, 4, 8, 12)),
        "banco_volcado": add((16,), (8,)),
        "sacos": add((16, 24, 32, 40), (0, 8)),
        "santo": add(CROSS_SANTOS, (0,)),
        "vela": add(VELA_XS, (0, 8)),
        "relicario": add(RELIC_XS, (8,)),
        "lapida_cruz_h": add((TOMB_X,), (0,)),
    }


def _stamp_for(stamps, name, x, y):
    """Return the stamp index whose baked floor phase matches world tile (x, y)."""
    pc, pr = x & 15, y & 15
    for i, s in enumerate(stamps):
        if s["name"] == name and s["phase_col"] == pc and s["phase_row"] == pr:
            return i
    return None


def _overlaps(occupied, x, y, w, h):
    return any(x < ox + ow and ox < x + w and y < oy + oh and oy < y + h
               for ox, oy, ow, oh in occupied)


def bench_groups(seed, tramo):
    """One glued group of 4-6 benches per bench row and tramo (8 slots of 32 px = 2 bands x 4).

    Length is hashed per (tramo, row) with a 25/50/25 split for 4/5/6; the start is hashed inside
    [0, 8 - length], so a group never crosses the tramo border and there are no holes inside it.
    Both rows use distinct hash keys; if the two groups would land on exactly the same slots, the
    right row moves one valid start so the rows stagger. Deterministic and stateless.
    """
    groups = []
    for row_i, row_x in enumerate(BENCH_ROWS):
        row_key = (tramo << 1) + row_i
        r = band_hash(seed, row_key, S_BANK_LEN) % 100
        length = (BENCH_GROUP_LENS[0] if r < 25 else
                  BENCH_GROUP_LENS[2] if r >= 75 else BENCH_GROUP_LENS[1])
        start = band_hash(seed, row_key, S_BANK_START) % (BENCH_SLOTS - length + 1)
        groups.append([row_x, length, start])
    if groups[0][1] == groups[1][1] and groups[0][2] == groups[1][2]:
        length = groups[1][1]
        groups[1][2] = (groups[1][2] + 1) % (BENCH_SLOTS - length + 1)
    return groups


def _column_state(seed, band, salt):
    r = band_hash(seed, band, salt) % 100
    if r < 55:
        return "entera"
    if r < 85:
        return "rota"
    return "caida"


def _effective_column_state(seed, band, salt):
    """55/30/15 split, but a raw hole right after another raw hole becomes a broken stump:
    two holes never sit back to back on the same row."""
    state = _column_state(seed, band, salt)
    if state == "caida" and _column_state(seed, band - 1, salt) == "caida":
        return "rota"
    return state


def _stamp_nz(stamp):
    """Tiles the stamp actually writes (tile != 0). Empty shadow-canvas margins stay free."""
    tiles = stamp.get("tiles")
    if tiles is None:
        return np.ones((stamp["h"], stamp["w"]), dtype=bool)
    return np.array([[int(v) & 0x3ff != 0 for v in row] for row in tiles], dtype=bool)


def _masks_overlap(ax, ay, am, bx, by, bm):
    x0, y0 = max(ax, bx), max(ay, by)
    x1 = min(ax + am.shape[1], bx + bm.shape[1])
    y1 = min(ay + am.shape[0], by + bm.shape[0])
    if x0 >= x1 or y0 >= y1:
        return False
    return bool(np.any(am[y0 - ay:y1 - ay, x0 - ax:x1 - ax] & bm[y0 - by:y1 - by, x0 - bx:x1 - bx]))


def catedral_plan(stamps, seed=0xC0DE1234, n_bands=64):
    """Deterministic cathedral floor plan, identical in Python and in C (source/strip.c).

    The band number decides what goes where; hashes only pick variants. Every stamp keeps its
    baked floor phase (x_tile = phase_col + 16k, y_tile = phase_row + 16k) and never crosses a
    band border. `tramo = band >> 1`, `pos = tramo & 3`: 0/1 bancadas, 2 barricada, 3 crucero.
    """
    left_x, right_x = CATEDRAL_COLUMNS
    entries, occupied = [], {}

    def place(name, x, y_local, band, kind):
        idx = _stamp_for(stamps, name, x, band * 16 + y_local)
        if idx is None:
            return False
        s = stamps[idx]
        if x < 6 or x + s["w"] > 58:
            return False
        if y_local < 0 or y_local + s["h"] > 16:
            return False
        occ = occupied.setdefault(band, [])
        nz = _stamp_nz(s)
        if any(_masks_overlap(x, y_local, nz, ox, oy, om) for ox, oy, om in occ):
            return False
        occ.append((x, y_local, nz))
        entries.append({"kind": kind, "name": name, "idx": idx, "x": x,
                        "y": band * 16 + y_local, "band": band})
        return True

    for band in range(n_bands):
        if band in CATEDRAL_CLEAR_BANDS:
            continue
        tramo = band >> 1
        pos = tramo & 3
        ciclo = tramo >> 2
        left_state = _effective_column_state(seed, band, S_COL_L)
        right_state = _effective_column_state(seed, band, S_COL_R)

        # Columnata: one stamp per row and band, except in the crossing (pos 3).
        if pos != 3:
            for side, state, x in (("L", left_state, left_x), ("R", right_state, right_x)):
                if state == "entera":
                    place("columna_entera", x, 0, band, "entera")
                elif state == "rota":
                    place("columna", x, 8, band, "rota")   # base aligned with the full column
                else:
                    entries.append({"kind": "caida", "name": None, "idx": None,
                                    "x": x, "y": band * 16, "band": band, "side": side})

        if pos in (0, 1):
            # One glued group of 4-6 benches per row and tramo (bench_groups). Each band places
            # only the slots that fall inside it; type 75/25 per bench by (band, row, slot).
            sub = band & 1
            for row_i, (_row_x, length, start) in enumerate(bench_groups(seed, tramo)):
                for slot in range(start, start + length):
                    if (slot >> 2) != sub:
                        continue
                    y_local = (slot & 3) * BENCH_STEP_TILES
                    r = band_hash(seed, band, (S_BANK_TYPE ^ ((row_i * 0x9e3779b9)
                                                              ^ (slot * 0x85ebca6b)) & 0xffffffff)) % 100
                    name = "banco_roto" if r < 25 else "banco_entero"
                    place(name, BENCH_ROWS[row_i], y_local, band, "banco")
        elif pos == 2:
            if band_hash(seed, ciclo, S_BARRICADE) % 3 == 0:
                # Cleared tramo: 0-2 candles / a flat tomb (no collision) in the open nave.
                h = band_hash(seed, band, S_DECOR)
                count = h % 3
                if count >= 1:
                    if (h >> 4) & 1:
                        place("lapida_cruz_h", TOMB_X, 0, band, "lapida")
                    else:
                        place("vela", 40, 0, band, "vela")
                if count >= 2:
                    place("vela", 40, 8, band, "vela")
            else:
                # Barricade: three sacks staggered in y (adjacent x shares no 2-D tile) plus
                # a fallen bench on the second band. On odd cycles the line leans to the right
                # side when the right column is down, which alternates the open side.
                shift = 8 if ((ciclo & 1) and right_state == "caida") else 0
                xs = tuple(x + shift for x in SACOS_LINE)
                if band & 1:
                    place("sacos", xs[1], 0, band, "sacos")
                    place("sacos", xs[2], 8, band, "sacos")
                    place("banco_volcado", 16, 8, band, "barricada")
                else:
                    place("sacos", xs[0], 0, band, "sacos")
                    place("sacos", xs[1], 8, band, "sacos")
                    place("sacos", xs[2], 0, band, "sacos")
        else:
            # Crucero: open arena. Symmetric saints, candles and one lateral reliquary.
            for x in CROSS_SANTOS:
                place("santo", x, 0, band, "santo")
            place("vela", 8, 0, band, "vela")
            place("vela", 24, 0, band, "vela")
            place("vela", 32, 8, band, "vela")
            place("vela", 48, 0, band, "vela")
            place("relicario", 48 if ciclo & 1 else 8, 8, band, "relicario")
    return entries


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
        plan = catedral_plan(stamps, seed, tilemap.shape[0] // 16)
        chosen = [(e["band"], e["idx"], e["x"], e["y"] - e["band"] * 16)
                  for e in plan if e["idx"] is not None]
        for band, idx, x, y in chosen:
            s = stamps[idx]
            for sy in range(s["h"]):
                for sx in range(s["w"]):
                    e = int(s["tiles"][sy, sx])
                    if e:
                        tilemap[band * 16 + y + sy, x + sx] = e
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

    result = []
    for ty in range(period.shape[0] // 8):
        row = []
        for tx in range(64):
            tile = period[ty*8:ty*8+8, tx*8:tx*8+8]
            row.append(tiles.add(tile.tobytes()))
        result.append(row)
    return result


def emit(output, palette, tiles, floor_map, stamps, packed, floor_source, worst,
         worst_occlusion, floor_n, props_n, mode="actual"):
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
        pid = s["piece_id"] if mode == "catedral" else 0
        out.append(f"    {{ {s['w']}, {s['h']}, {s['phase_col']}, {s['phase_row']}, {s['foot_anchor_y_px']}, {s['foot_value']}, {pid}, s_stamp_{i}_tiles, {fr}, {dr} }}, // {s['name']}\n")
    out += ["};\n\n", "const StripKit g_strip_kit = {\n", "    .palette = s_palette,\n", "    .tiles = s_tiles,\n",
            f"    .num_tiles = {len(tiles.data)},\n", f"    .map_h_tiles = {len(floor_map)},\n",
            "    .floor_h_tiles = 16,\n", "    .floor_map = s_floor_map,\n",
            "    .floor_collision = s_floor_collision,\n", f"    .num_stamps = {len(stamps)},\n", "    .stamps = s_stamps,\n", "};\n"]
    with output.open("w", encoding="utf-8", newline="") as f: f.write("".join(out))


def format_metrics(entries, stamps, label="catedral", bands=64, worst=0, worst_occlusion=0):
    from collections import Counter
    rows = catedral_metrics(entries, stamps, bands)
    lines = ["| modo | ventana (bandas) | huella % suelo util | pasillo central min | paso lateral min |",
             "| :--- | :--- | ---: | :---: | :---: |"]
    for r in rows:
        lines.append(f"| {label} | {r['window']} | {r['footprint_pct']:.2f} | "
                     f"{r['central']} px (banda {r['central_band']}) | "
                     f"{r['lateral']} px (banda {r['lateral_band']}) |")
    states, names = Counter(), Counter()
    for e in entries:
        if e["kind"] in ("entera", "rota", "caida"):
            states[e["kind"]] += 1
        elif e["idx"] is not None:
            names[e["name"]] += 1
    benches = names.get("banco_entero", 0) + names.get("banco_roto", 0)
    total_foot = sum(n * 16 for e in entries if e["idx"] is not None
                     for _, _, n in stamps[e["idx"]]["foot_runs"])
    lines += ["",
              f"- Huella total ({bands} bandas): {100.0 * total_foot / (416 * bands * 128):.2f} % del suelo util.",
              f"- Peor ventana de 33x25 tiles: **{worst}** (< 440).",
              f"- Peor oclusion de 16 bandas: **{worst_occlusion}** runs (< {OCCLUSION_CAPACITY})."]
    if sum(states.values()):
        lines.append("- Columnas por estado: entera={} (`columna_entera`), rota={} (`columna`), "
                     "caida={} (hueco).".format(states["entera"], states["rota"], states["caida"]))
    if benches:
        lines.append("- Bancos: entero={} ({:.1f} %), roto={} ({:.1f} %).".format(
            names.get("banco_entero", 0), 100.0 * names.get("banco_entero", 0) / benches,
            names.get("banco_roto", 0), 100.0 * names.get("banco_roto", 0) / benches))
    lines.append("- Piezas por tipo: " + ", ".join(f"{k}={v}" for k, v in sorted(names.items())) + ".")
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
    missing = [name for name in prop_names if not (PROP_DIR / name / "color.png").is_file()]
    for name in missing:
        print(f"warning: prop {name!r} has no render/color.png; skipped")
    prop_names = tuple(name for name in prop_names if name not in missing)
    if not prop_names: raise ValueError("no prop has render/color.png")
    all_phases = [(0, 0), (8, 0), (0, 8), (8, 8)]
    if mode == "catedral":
        # Bake only (piece, phase) pairs the deterministic composer can use, and only the
        # pieces it places. `actual` keeps the full 4-phase kit and its old behaviour.
        phase_map = catedral_phase_map()
        prop_names = tuple(name for name in prop_names if name in phase_map)
        shadow_crop = ("banco_roto",)
        bench_crop = ("banco_entero", "banco_roto")
        print(f"catedral kit: {len(prop_names)} pieces, {sum(len(v) for v in phase_map.values())} (piece, phase) stamps")
    else:
        phase_map, shadow_crop, bench_crop = None, (), ()
    floor_colors, raw_floor, grid = read_floor(floor_dir)
    tiles = Tiles()
    palette, floor_pixels, floor_map = make_floor_tiles(floor_colors, raw_floor, grid, tiles)
    props, prop_lab = read_prop_palette()
    stamps, shadow_colors, decor_colors = load_pieces(prop_names, all_phases,
                                                     floor_pixels, grid, palette, props, prop_lab, tiles,
                                                     phase_map=phase_map, shadow_crop=shadow_crop,
                                                     bench_crop=bench_crop)
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
    map_map = make_cathedral_map(floor_map, tiles, palette)
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
        dumped = [{"band": e["band"], "piece_id": stamps[e["idx"]]["piece_id"],
                   "phase_col": stamps[e["idx"]]["phase_col"],
                   "phase_row": stamps[e["idx"]]["phase_row"],
                   "x": e["x"], "y": e["y"]} for e in plan if e["idx"] is not None]
        dump_plan.parent.mkdir(parents=True, exist_ok=True)
        dump_plan.write_text(json.dumps(dumped), encoding="utf-8")
        print(f"plan: {dump_plan} ({len(dumped)} stamps)")
    print(f"palette entries: floor={floor_n}, props={props_n}, shadow={len(shadow_colors)} new, lapida={len(decor_colors)} new, wall_palette=8, shared={len(palette)}/256")
    print(f"tiles: {len(tiles.data)}/1024; worst window: {worst}/<440; selected pieces in 64 bands: {len(chosen)}")
    print(f"worst 16-band occlusion runs: {worst_occlusion}/{OCCLUSION_CAPACITY}")
    if mode == "catedral" or metrics:
        if mode == "catedral":
            entries, label = plan, "catedral"
        else:
            entries = [{"kind": "piece", "name": stamps[i]["name"], "idx": i, "x": x,
                        "y": band * 16 + y, "band": band} for band, i, x, y in chosen]
            label = "actual"
        text = format_metrics(entries, stamps, label, worst=worst,
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
                   help="comma-separated props (default: " + ",".join(DEFAULT_PROPS) + ")")
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--preview", type=Path, default=Path(os.environ.get("TEMP", "/tmp")) / "cathedral_strip_preview.png")
    p.add_argument("--mode", choices=("actual", "catedral"), default="actual",
                   help="actual: random 1-4 pieces per band (default); catedral: deterministic 4-tramo composer")
    p.add_argument("--metrics", type=Path, default=None,
                   help="write the catedral metrics Markdown table here")
    p.add_argument("--dump-plan", type=Path, default=None,
                   help="write the deterministic cathedral plan as JSON (parity test)")
    a = p.parse_args()
    build(a.floor, a.phases, a.output, a.preview, a.props, a.mode, a.metrics, a.dump_plan)


if __name__ == "__main__": main()
