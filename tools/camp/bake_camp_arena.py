#!/usr/bin/env python3
"""Bakes the camp floor + walls: a night courtyard lit by the bonfire, light baked in bands.

The camp reuses the cathedral floor tile geometry (the 16x16 damero of rombos) and the cathedral wall
slice, but recoloured as ruined courtyard: pale paving stones over packed earth, moss and grass towards
the edges, cracks, loose stones and a ruined masonry wall.

Lighting is computed here, not on the console (DESIGN.md 7.5):
  * Every pixel gets a scalar light L = moon ambient (vignette) + bonfire (falloff over the 2:1 ground
    plane, elliptical iso-contours).
  * L is quantised to N_BANDS bands with a 4x4 ordered dither on the band borders (no ugly steps).
  * A pixel's palette index is 1 + band * M + material, with M materials (flat albedos) per band. So the
    palette is "material x band" and the tiles only differ where the band or the material differs.
  * The warm bands are contiguous in the palette (WARM_FIRST..WARM_FIRST+WARM_COUNT-1), so the bonfire
    flicker is a plain copy of one contiguous block of colours (camp_floor_light.c), per flicker step.

Output: include/camp_arena_data.h, source/camp_arena_data.c (art + flicker table) and a preview
(walkthroughs/campamento-nocturno/assets/suelo_*.png). The runtime Arena and the props are in
source/camp.c.

Run:  python tools/camp/bake_camp_arena.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import bake_cathedral_kit as kit  # noqa: E402

FLOOR_DIR = ROOT / "assets/environment/cathedral/floor/rombos_tripo"
PREVIEW_DIR = ROOT / "walkthroughs/campamento-nocturno/assets"

W, H = 256, 384
TILES_W, TILES_H = W // 8, H // 8        # 32 x 48
WALL_INNER_COLS = 3                       # 24 px of wall on each side
WALL_PX = WALL_INNER_COLS * 8
NORTH_BASE_Y = 106                        # ground line of the north wall of modules (muro_norte.png height)

FIRE_X, FIRE_Y = 128, 300                 # ground point of the bonfire (camp.c)
N_BANDS = 7
N_MATERIALS = 32                          # 1 + 7*32 = 225; the wall takes 226..255
WARM_BAND_FIRST = 2                       # bands 0..1 are cold (moon only); 2..6 warm and flicker
N_FLICKER = 4

# Band centres: brightness (0..1) and warmth (0 = moon blue, 1 = fire).
BAND_L = np.array([0.075, 0.15, 0.26, 0.40, 0.56, 0.75, 0.97])
BAND_WARM = np.array([0.0, 0.0, 0.22, 0.48, 0.70, 0.86, 1.0])
MOON_TINT = np.array([0.50, 0.62, 1.00])  # cold night blue
FIRE_TINT = np.array([1.00, 0.70, 0.42])  # warm ember (muted: DESIGN 6.10)
SATURATION_KEEP = 0.82                    # output pulled slightly to grey (muted palette)
# Fire gain per flicker step (1.0 = the base palette): how much brighter/dimmer the warm bands go.
FLICKER_GAIN = [1.00, 0.88, 1.10, 0.94]
FLICKER_GAIN_BAND = np.array([0, 0, 0.35, 0.6, 0.85, 1.0, 1.0])  # how much of the gain each band takes

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float64)
BAYER_T = (BAYER4 + 0.5) / 16.0

rng = np.random.default_rng(20261121)


# ---------------------------------------------------------------------------------------------
# Procedural helpers (all albedo work is on an H x W x 3 float array in 0..255)
# ---------------------------------------------------------------------------------------------
def value_noise(period_x, period_y, w=W, h=H, seed=0):
    """Smooth tileable-ish noise in 0..1 (bicubic upsample of a random grid)."""
    r = np.random.default_rng(seed)
    gx, gy = max(2, w // period_x + 2), max(2, h // period_y + 2)
    g = (r.random((gy, gx)) * 255).astype(np.uint8)
    im = Image.fromarray(g).resize((gx * period_x, gy * period_y), Image.BICUBIC)
    return np.asarray(im, np.float64)[:h, :w] / 255.0


def blob_mask(cx, cy, rx, ry, noise_amt=0.0, seed=0):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    if noise_amt:
        d = d + (value_noise(6, 6, seed=seed) - 0.5) * noise_amt
    return d


def floor_albedo_base():
    """Cathedral damero recoloured to paving stone over earth. Periodic 128 x 128 so tiles repeat."""
    colors, raw, grid = kit.read_floor(FLOOR_DIR)
    grid = kit.reduce_floor_variants(grid, keep=2)       # 92 -> 16 tiles: the tile budget (kit measure)
    tiles = kit.Tiles()
    palette, pixel_tiles, floor_map64 = kit.make_floor_tiles(colors, raw, grid, tiles)
    lum = []
    for c in palette[1:]:
        r, g, b = (c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8
        lum.append(0.3 * r + 0.59 * g + 0.11 * b)
    lo, hi = min(lum), max(lum)
    lut = [(l - lo) / (hi - lo) for l in lum]
    t_img = np.zeros((H, W))
    for ty in range(TILES_H):
        for tx in range(TILES_W):
            e = floor_map64[ty % 16][tx]
            px = np.frombuffer(tiles.data[e & 0x3ff], np.uint8).reshape(8, 8)
            if e & 0x4000:
                px = px[:, ::-1]
            if e & 0x8000:
                px = px[::-1]
            t_img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = np.vectorize(lambda i: lut[i - 1])(px)
    # 4 levels of stone: dark diamonds = packed earth, light diamonds = paving stone.
    q = np.clip(np.round(t_img * 5) / 5, 0, 1)
    earth = np.array([82.0, 74.0, 64.0])
    stone = np.array([128.0, 124.0, 112.0])
    out = earth[None, None, :] + (stone - earth)[None, None, :] * q[:, :, None]
    return out, t_img


# Decals are 8x8 stamps picked per tile from small libraries, so the tile count stays bounded
# (unique tiles ~ base tiles x stamps x light bands) instead of every moss blot being one-off art.
def _stamp_masks(n, density, seed, blobs):
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        m = np.zeros((8, 8), bool)
        for _b in range(blobs):
            cx, cy = r.integers(0, 8), r.integers(0, 8)
            rad = r.uniform(1.2, 2.6)
            yy, xx = np.mgrid[0:8, 0:8]
            m |= ((xx - cx) ** 2 + ((yy - cy) * 1.6) ** 2) < rad ** 2
        m &= r.random((8, 8)) < density
        out.append(m)
    return out


MOSS_HEAVY = _stamp_masks(3, 0.95, 101, 3)
MOSS_LIGHT = _stamp_masks(3, 0.85, 102, 1)
CRACK_STAMPS = []
STONE_STAMPS = []


def _make_crack(seed):
    r = np.random.default_rng(seed)
    m = np.zeros((8, 8), bool)
    x, y = float(r.integers(0, 3)), float(r.integers(1, 7))
    ang = (r.random() - 0.5) * 1.2
    for _ in range(9):
        ang += (r.random() - 0.5) * 1.1
        x += np.cos(ang) * 0.95
        y += np.sin(ang) * 0.6
        if 0 <= int(x) < 8 and 0 <= int(y) < 8:
            m[int(y), int(x)] = True
    return m


CRACK_STAMPS = [_make_crack(200 + i) for i in range(3)]


def _make_stone(w, h):
    m = np.zeros((8, 8), np.int8)          # 1 = lit top, 2 = shadow edge
    x0, y0 = 2, 3
    for dx in range(w):
        m[y0, x0 + dx] = 1
    for dx in range(w - 1):
        m[y0 + 1, x0 + dx + 1] = 2
    if h > 1:
        for dx in range(w - 2):
            m[y0 - 1, x0 + dx + 1] = 1
    return m


STONE_STAMPS = [_make_stone(4, 1), _make_stone(3, 2)]


def apply_stamps(alb, t_img):
    """Per-tile decals on the floor area: moss/grass (edges and dark joins), cracks, loose stones."""
    n1 = value_noise(40, 40, w=TILES_W, h=TILES_H, seed=41)
    n2 = value_noise(12, 12, w=TILES_W, h=TILES_H, seed=42)
    r = np.random.default_rng(77)
    for ty in range(TILES_H):
        for tx in range(WALL_INNER_COLS, TILES_W - WALL_INNER_COLS):
            x0, y0 = tx * 8, ty * 8
            # edge weight in tiles (distance to the floor border)
            e = min(tx - WALL_INNER_COLS, TILES_W - WALL_INNER_COLS - 1 - tx, ty, TILES_H - 1 - ty)
            edge_w = max(0.0, 1.0 - e / 7.0)
            d_fire = np.sqrt((x0 + 4 - FIRE_X) ** 2 + (2 * (y0 + 4 - FIRE_Y)) ** 2)
            score = n1[ty, tx] * 0.5 + n2[ty, tx] * 0.25 + edge_w * 0.55
            patch = alb[y0:y0 + 8, x0:x0 + 8]
            if d_fire < 70:
                continue
            if score > 0.82:
                m = MOSS_HEAVY[int(r.integers(0, len(MOSS_HEAVY)))]
                patch[m] = np.array([84.0, 100.0, 62.0])
                patch[m & ~MOSS_LIGHT[0]] = np.array([64.0, 80.0, 48.0])
            elif score > 0.72:
                m = MOSS_LIGHT[int(r.integers(0, len(MOSS_LIGHT)))]
                patch[m] = np.array([84.0, 100.0, 62.0])
            elif r.random() < 0.04:
                m = CRACK_STAMPS[int(r.integers(0, len(CRACK_STAMPS)))]
                patch[m] *= 0.55
            elif r.random() < 0.04:
                m = STONE_STAMPS[int(r.integers(0, len(STONE_STAMPS)))]
                patch[m == 1] = np.array([118.0, 114.0, 104.0])
                patch[m == 2] = np.array([54.0, 50.0, 47.0])


# ---------------------------------------------------------------------------------------------
# Light
# ---------------------------------------------------------------------------------------------
def light_map():
    """Scalar light L in 0..1 per pixel: moon ambient (with vignette) + bonfire (2:1 ground ellipses)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    # Moon: dim, darker towards the borders ("bordes casi negros"), with a faint spill by the door.
    edge = np.minimum.reduce([xx, (W - 1) - xx, yy * 0.55 + 8, (H - 1 - yy) * 0.55 + 8])
    vign = np.clip(edge / 40.0, 0, 1)
    vign = vign * vign * (3 - 2 * vign)
    amb = 0.125 + 0.09 * vign
    door = np.exp(-(((xx - 128) / 44.0) ** 2 + ((yy - 108) / 26.0) ** 2))
    amb = amb + 0.0 * door
    # Fire: falloff over iso distance, hard cutoff at R so the far field is pure moon.
    d = np.sqrt((xx - FIRE_X) ** 2 + (2 * (yy - FIRE_Y)) ** 2)
    R = 290.0
    f = np.clip(1.0 - d / R, 0, 1)
    fire = f ** 1.9 * 1.0
    fire = fire + 0.35 * np.exp(-(d / 22.0) ** 2)           # hot core
    return np.clip(amb + fire, 0, 1)


def band_positions(L):
    """Continuous band coordinate (0..N-1) from L by interpolating the band centre table."""
    return np.interp(L, BAND_L, np.arange(N_BANDS))


def dithered_band(L, fire_free):
    """Band per pixel. Where the bonfire reaches (fire_free False) the borders are dithered per pixel;
    in the far field (moon only) the band is flat per 8x8 tile, dithered at tile level, so the upper
    screen stays within its 440-tile window."""
    bf = band_positions(L)
    yy, xx = np.mgrid[0:H, 0:W]
    px = np.clip(np.floor(bf + BAYER_T[yy % 4, xx % 4]), 0, N_BANDS - 1).astype(np.int32)
    tb = bf.reshape(TILES_H, 8, TILES_W, 8).mean(axis=(1, 3))
    ty, tx = np.mgrid[0:TILES_H, 0:TILES_W]
    tband = np.clip(np.floor(tb + 0.5), 0, N_BANDS - 1).astype(np.int32)
    flat = np.kron(tband, np.ones((8, 8), np.int32))
    ff = np.kron(fire_free.reshape(TILES_H, 8, TILES_W, 8).all(axis=(1, 3)), np.ones((8, 8), bool))
    wall_cols = np.zeros((H, W), bool)
    wall_cols[:, :WALL_PX] = True
    wall_cols[:, W - WALL_PX:] = True
    return np.where(ff | wall_cols, flat, px)   # walls are flat per tile (they are dark; saves tiles)


def shade(albedo, band, gain=1.0):
    """Final RGB (0..255) of an albedo under band `band`; gain scales the fire part of warm bands."""
    g = 1.0 + (gain - 1.0) * FLICKER_GAIN_BAND[band]
    lv = BAND_L[band] * g
    wm = min(1.0, BAND_WARM[band] * (1.0 + (g - 1.0) * 0.5))
    tint = MOON_TINT * (1 - wm) + FIRE_TINT * wm
    rgb = albedo * tint * lv * 1.55
    grey = (0.3 * rgb[0] + 0.59 * rgb[1] + 0.11 * rgb[2])
    rgb = grey + (rgb - grey) * SATURATION_KEEP
    return np.clip(rgb, 0, 255)


def rgb555(rgb):
    r, g, b = [int(round(float(v) / 8.0)) for v in rgb]
    r, g, b = min(r, 31), min(g, 31), min(b, 31)
    return r | (g << 5) | (b << 10) | 0x8000


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def build():
    alb, t_img = floor_albedo_base()
    apply_stamps(alb, t_img)
    # The wall of modules has its own palette entries; the floor materials are quantised without it, so the
    # wall region of the albedo just repeats the nearest floor.
    # The walls are NOT baked into the floor any more: the frame (tools/camp/marco_build.py) is a sprite drawn
    # over it. The floor runs under it (nearest floor repeated), so no wall tiles and no wall palette entries.
    alb[:, :WALL_PX] = alb[:, WALL_PX:WALL_PX + 1]
    alb[:, W - WALL_PX:] = alb[:, W - WALL_PX - 1:W - WALL_PX]
    alb[:NORTH_BASE_Y] = alb[NORTH_BASE_Y + 6]
    # contact shadow on the floor along the base of the north wall
    for i, k in enumerate((0.55, 0.72, 0.86)):
        alb[NORTH_BASE_Y + i] *= k

    # Material quantisation: flat albedos -> N_MATERIALS entries (median cut, no dither).
    im = Image.fromarray(np.clip(alb, 0, 255).astype(np.uint8), "RGB")
    q = im.quantize(colors=N_MATERIALS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    mat_idx = np.asarray(q, np.int32)
    pal = np.array(q.getpalette()[:N_MATERIALS * 3], np.float64).reshape(-1, 3)
    n_mat = len(pal)

    n_wall = 0

    L = light_map()
    # The walls are lit a bit less (their face is vertical) and the right wall mirrors the left.
    L[:, :WALL_PX] *= 0.85
    L[:, W - WALL_PX:] *= 0.85
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    far = np.sqrt((xx - FIRE_X) ** 2 + (2 * (yy - FIRE_Y)) ** 2) > 1e9
    band = dithered_band(L, far)
    band[:NORTH_BASE_Y] = 0               # under the north wall frame: flat, cold
    # Mirror symmetry of the wall tiles: build the left wall from the left half and mirror the pixels
    # (the lighting is symmetric except for float noise, so identical tiles dedupe by flip).
    band[:, W - WALL_PX:] = band[:, :WALL_PX][:, ::-1]
    mat_idx[:, W - WALL_PX:] = mat_idx[:, :WALL_PX][:, ::-1]

    index_img = 1 + band * n_mat + mat_idx                         # 1..(1 + N_BANDS*n_mat)
    n_colors = 1 + N_BANDS * n_mat

    def palette_for(gain):
        p = np.zeros(256, np.uint16)
        for b in range(N_BANDS):
            for m in range(n_mat):
                p[1 + b * n_mat + m] = rgb555(shade(pal[m], b, gain))
        return p

    base_pal = palette_for(1.0)
    warm_first = 1 + WARM_BAND_FIRST * n_mat
    warm_count = (N_BANDS - WARM_BAND_FIRST) * n_mat
    flicker = [palette_for(g)[warm_first:warm_first + warm_count] for g in FLICKER_GAIN]

    # Cut into tiles (dedupe by flips) and the map.
    tiles = kit.Tiles()
    camp_map = []
    for ty in range(TILES_H):
        row = []
        for tx in range(TILES_W):
            blk = np.ascontiguousarray(index_img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8].astype(np.uint8))
            e = tiles.add(blk.tobytes())
            # Hardware tilemap format: id in bits 0-9, hflip bit 10, vflip bit 11 (the kit returns 0x4000/0x8000).
            row.append((e & 0x3ff) | ((e & 0xc000) >> 4))
        camp_map.append(row)

    # Stats: distinct tile ids in each screen window (top rows 0..24, bottom rows 24..48 incl. the
    # extra streamed row), as BG_VIEW_H = 25 rows are streamed per screen.
    def window_ids(r0, r1):
        return len({e & 0x3ff for row in camp_map[r0:r1] for e in row})

    stats = {
        "tiles_total": len(tiles.data),
        "top_window": window_ids(0, 25),
        "bottom_window": window_ids(23, 48),
        "materials": n_mat,
        "colors": n_colors,
        "warm_first": warm_first,
        "warm_count": warm_count,
    }
    return base_pal, flicker, tiles, camp_map, index_img, stats, (alb, L, band)


def preview(index_img, palette, name):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    rgb = np.zeros((H, W, 3), np.uint8)
    for i in np.unique(index_img):
        v = int(palette[i])
        rgb[index_img == i] = [(v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31]
    Image.fromarray(rgb).resize((W * 4, H * 4), Image.NEAREST).save(PREVIEW_DIR / name)
    return rgb


def write_outputs(base_pal, flicker, tiles, camp_map, stats):
    hdr = [
        "// GENERATED by tools/camp/bake_camp_arena.py. Do not edit.",
        "#ifndef CAMP_ARENA_DATA_H",
        "#define CAMP_ARENA_DATA_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define CAMP_WORLD_W {W}",
        f"#define CAMP_WORLD_H {H}",
        f"#define CAMP_MAP_W {TILES_W}",
        f"#define CAMP_MAP_H {TILES_H}",
        f"#define CAMP_NUM_TILES {len(tiles.data)}",
        "",
        "// Baked bonfire light (see camp_floor_light.h): the warm bands are one contiguous block of palette",
        "// entries that the flicker rewrites; step 0 is the palette as baked.",
        f"#define CAMP_LIGHT_WARM_FIRST {stats['warm_first']}",
        f"#define CAMP_LIGHT_WARM_COUNT {stats['warm_count']}",
        f"#define CAMP_LIGHT_FLICKER_STEPS {N_FLICKER}",
        "",
        "extern const uint16_t g_camp_palette[256];",
        "extern const uint16_t g_camp_floor_map[CAMP_MAP_W * CAMP_MAP_H];",
        "extern const uint16_t g_camp_flicker[CAMP_LIGHT_FLICKER_STEPS][CAMP_LIGHT_WARM_COUNT];",
        "",
        "#endif",
        "",
    ]
    (ROOT / "include" / "camp_arena_data.h").write_text("\n".join(hdr), encoding="utf-8", newline="")

    c = [
        "// GENERATED by tools/camp/bake_camp_arena.py. Do not edit.",
        '#include "camp_arena_data.h"',
        "",
        "const uint16_t g_camp_palette[256] __attribute__((aligned(4))) = {",
    ]
    for i in range(0, 256, 16):
        c.append("    " + ", ".join(f"0x{int(v):04X}" for v in base_pal[i:i + 16]) + ",")
    c += ["};", "", "const uint16_t g_camp_floor_map[CAMP_MAP_W * CAMP_MAP_H] __attribute__((aligned(4))) = {"]
    for row in camp_map:
        c.append("    " + ", ".join(map(str, row)) + ",")
    c += ["};", "",
          "const uint16_t g_camp_flicker[CAMP_LIGHT_FLICKER_STEPS][CAMP_LIGHT_WARM_COUNT] __attribute__((aligned(4))) = {"]
    for step in flicker:
        c.append("    {")
        for i in range(0, len(step), 16):
            c.append("        " + ", ".join(f"0x{int(v):04X}" for v in step[i:i + 16]) + ",")
        c.append("    },")
    c += ["};", ""]
    (ROOT / "source" / "camp_arena_data.c").write_text("\n".join(c), encoding="utf-8", newline="")
    # Floor tiles go to NitroFS (nitrofiles/camp/floor_tiles.bin), not into the ARM9 binary: 1010 x 64 B
    # does not fit the static EWRAM budget. Same order as tiles.data; camp.c loads it once.
    raw = b"".join(bytes(t) for t in tiles.data)
    assert len(raw) == len(tiles.data) * 64
    (ROOT / "nitrofiles" / "camp" / "floor_tiles.bin").write_bytes(raw)


def main():
    base_pal, flicker, tiles, camp_map, index_img, stats, (alb, L, band) = build()
    preview(index_img, base_pal, "suelo_vista.png")
    # Flicker contact sheet: the same floor under each flicker step (only the warm block differs).
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheets = []
    for s in range(N_FLICKER):
        p = base_pal.copy()
        p[stats["warm_first"]:stats["warm_first"] + stats["warm_count"]] = flicker[s]
        rgb = preview(index_img, p, f"_tmp_{s}.png")
        sheets.append(Image.fromarray(rgb[192:384, :]).resize((W * 2, 192 * 2), Image.NEAREST))
        (PREVIEW_DIR / f"_tmp_{s}.png").unlink()
    sheet = Image.new("RGB", (W * 2 * N_FLICKER + 6 * (N_FLICKER - 1), 192 * 2))
    for s, im in enumerate(sheets):
        sheet.paste(im, (s * (W * 2 + 6), 0))
    sheet.save(PREVIEW_DIR / "suelo_parpadeo.png")
    # Band debug map.
    dbg = (band * (255 // (N_BANDS - 1))).astype(np.uint8)
    Image.fromarray(dbg).resize((W * 2, H * 2), Image.NEAREST).save(PREVIEW_DIR / "suelo_bandas.png")
    write_outputs(base_pal, flicker, tiles, camp_map, stats)
    print("camp arena:", stats)
    print(f"  top window {stats['top_window']}/440, bottom window {stats['bottom_window']}/1023, "
          f"total {stats['tiles_total']}/1024")


if __name__ == "__main__":
    main()
