#!/usr/bin/env python3
"""Cathedral floor from modelled 3D slabs, rendered with the game camera (30 deg, ortho).

Pipeline (run from the worktree root):
  python tools/floor/losas3d_h.py --variant h --scratch <tmp dir>
  python tools/floor/losas3d_h.py --variant b --scratch <tmp dir>

Steps:
  1. tools/floor/losas3d_h_render.py (Blender headless) builds slabs and renders a 3x3-block area
     (1536 px, 4x4 supersampled per output pixel); the centre block is the tile, the rest tests the seam.
  2. The block is box-downsampled to 128x128, quantized to <= 32 BGR555 colours (no dither).
  3. 8x8 tiles are deduplicated; flips H/V count as the same tile.
  4. Writes assets/environment/cathedral/floor/losas_3d_h[_b]/ (tiles.png, floor.json,
     floor_512x256.png, floor_512x256_x3.png, revision_x3.png, stats.json).
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "tools/floor/losas3d_h_render.py"
MARINE = ROOT / "assets/sprites/characters_neutral/marine/spritesheet.png"
BANCO = ROOT / "assets/environment/cathedral/props/render/banco_roto/color.png"
SANTO = ROOT / "assets/environment/cathedral/props/render/santo/color.png"
BLENDER = os.environ.get("BLENDER_EXE", "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe")
PXM = 17.9
P_M = 32.0 / PXM


def to5(a8):
    return np.round(np.asarray(a8).astype(float) * 31 / 255).astype(np.int64)


def to8(a5):
    return np.round(np.asarray(a5).astype(float) * 255 / 31).astype(np.uint8)


def bgr555(c):
    r, g, b = (int(v) for v in c)
    return (b << 10) | (g << 5) | r


def nearest(v5, centers):
    d = ((v5.reshape(-1, 3)[:, None, :].astype(float) - centers[None].astype(float)) ** 2).sum(-1)
    return d.argmin(1).reshape(v5.shape[:2]).astype(np.uint8)


def quantize(block8, colors=32):
    v5 = to5(block8)
    pim = Image.fromarray(to8(v5)).quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                                            dither=Image.Dither.NONE)
    pal = np.array(pim.getpalette()[: 3 * 256]).reshape(-1, 3)
    used = np.unique(np.array(pim))
    centers = np.round(to5(pal[used])).astype(float)
    pix = v5.reshape(-1, 3).astype(float)
    for _ in range(12):
        lab = ((pix[:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)
        for k in range(len(centers)):
            m = lab == k
            if m.any():
                centers[k] = np.round(pix[m].mean(0))
    uniq = []
    for c in centers:
        if not any((c == u).all() for u in uniq):
            uniq.append(c)
    centers = np.array(uniq, dtype=np.int64)
    lab = nearest(v5, centers)
    used = np.unique(lab)
    remap = {int(old): i for i, old in enumerate(used)}
    lab = np.vectorize(remap.get)(lab).astype(np.uint8)
    return lab, centers[used]


def flips(t):
    return {(0, 0): t, (1, 0): t[:, ::-1], (0, 1): t[::-1, :], (1, 1): t[::-1, ::-1]}


def dedupe(lab):
    tiles, index, fmap = [], {}, [[None] * 16 for _ in range(16)]
    for ty in range(16):
        for tx in range(16):
            t = lab[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8]
            fl = flips(t)
            best = min(fl, key=lambda k: fl[k].tobytes())
            c = np.ascontiguousarray(fl[best])
            key = c.tobytes()
            if key not in index:
                index[key] = len(tiles)
                tiles.append(c)
            fmap[ty][tx] = {"t": index[key], "h": best[0], "v": best[1]}
    return tiles, fmap


def rebuild(tiles, fmap):
    block = np.zeros((128, 128), dtype=np.uint8)
    for ty in range(16):
        for tx in range(16):
            cell = fmap[ty][tx]
            rec = tiles[cell["t"]]
            if cell["h"]:
                rec = rec[:, ::-1]
            if cell["v"]:
                rec = rec[::-1, :]
            block[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8] = rec
    return block


def block_to_rgb(lab, centers5):
    rgb = to8(np.asarray(centers5))
    return rgb[lab]


def dark_valleys(p):
    """Columns (or rows) of one block that are dark joint lines: local minima below the midpoint level."""
    t = (p.min() + np.median(p)) / 2
    n = len(p)
    return [i for i in range(n) if p[i] < t and p[i] <= p[i - 1] and p[i] <= p[(i + 1) % n]]


def period_lag(profile, lo, hi):
    x = profile - profile.mean()
    n = len(x)
    f = np.fft.rfft(x, n=n)
    ac = np.fft.irfft(f * np.conj(f), n=n)
    ac = ac / ac[0]
    seg = ac[lo:hi + 1]
    # fundamental period: smallest lag whose correlation is close to the maximum (avoids harmonics)
    best = int(np.flatnonzero(seg >= 0.9 * seg.max())[0]) + lo
    return best, float(ac[best])


def render(variant, blocks, samples, seed, out_png, layout_json):
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(RENDER), "--",
           "--variant", variant, "--seed", str(seed), "--blocks", str(blocks), "--samples", str(samples),
           "--out", str(out_png)]
    if layout_json:
        cmd += ["--layout-out", str(layout_json)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def paste_sprite(canvas, sprite, feet_xy, anchor_xy=None):
    """Paste an RGBA sprite so that its anchor (default: bottom centre) lands on feet_xy."""
    w, h = sprite.size
    ax, ay = anchor_xy if anchor_xy else (w // 2, h)
    canvas.alpha_composite(sprite, (int(feet_xy[0] - ax), int(feet_xy[1] - ay)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("h", "b"), required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args()

    outname = "losas_3d_h" if a.variant == "h" else "losas_3d_h_b"
    out = ROOT / "assets/environment/cathedral/floor" / outname
    out.mkdir(parents=True, exist_ok=True)
    a.scratch.mkdir(parents=True, exist_ok=True)
    area_png = a.scratch / f"{outname}_area3x3.png"
    lay = a.scratch / f"{outname}_layout.json"
    if not a.skip_render:
        # 3x3 blocks so the centre block sees its real neighbours on all four sides
        render(a.variant, 3, a.samples, a.seed, area_png, lay)

    area512 = np.asarray(Image.open(area_png).convert("RGB"))
    block512 = area512[512:1024, 512:1024]
    block128 = np.asarray(Image.fromarray(block512).reduce(4))
    lab, centers5 = quantize(block128, 32)
    tiles, fmap = dedupe(lab)
    layout = json.loads(lay.read_text(encoding="utf-8"))

    # palette as BGR555 hex
    pal_hex = ["0x%04X" % bgr555(c) for c in centers5]
    rgb5 = centers5  # (R,G,B) 5-bit per palette entry
    rebuilt_idx = rebuild(tiles, fmap)
    exact_json = bool((rebuilt_idx == lab).all())
    floor_block_rgb = block_to_rgb(rebuilt_idx, rgb5)

    # seam test: each of the 9 blocks of the 3x3 area, quantized with the same palette, compared with
    # the centre block on the interior (the outer pixel ring of a block lacks its outside neighbours).
    mism = []
    for r in range(3):
        for c in range(3):
            sub = np.asarray(Image.fromarray(area512[r * 512:(r + 1) * 512, c * 512:(c + 1) * 512])
                             .reduce(4))
            idx = nearest(to5(sub), rgb5)
            mism.append(float((idx[1:-1, 1:-1] != lab[1:-1, 1:-1]).mean() * 100))
    seam_pct = max(m for k, m in enumerate(mism) if k != 4)

    # tiles atlas (8 px high)
    atlas = np.zeros((8, 8 * len(tiles), 3), dtype=np.uint8)
    for i, t in enumerate(tiles):
        atlas[:, i * 8:(i + 1) * 8] = block_to_rgb(t, rgb5)
    Image.fromarray(atlas).save(out / "tiles.png")

    floor_json = {"palette": pal_hex, "tiles": [t.reshape(-1).tolist() for t in tiles],
                  "floor_map": fmap, "period_tiles": [16, 16]}
    (out / "floor.json").write_text(json.dumps(floor_json, separators=(",", ":")), encoding="utf-8")

    # reconstruction from JSON only
    j = json.loads((out / "floor.json").read_text(encoding="utf-8"))
    pal_back = np.array([[(int(h, 16) & 31), (int(h, 16) >> 5) & 31, (int(h, 16) >> 10) & 31] for h in j["palette"]])
    tiles_back = [np.array(t, dtype=np.uint8).reshape(8, 8) for t in j["tiles"]]
    idx_back = rebuild(tiles_back, j["floor_map"])
    rgb_back = to8(pal_back)[idx_back]
    ok_json = bool((rgb_back == to8(rgb5)[lab]).all())
    tile_img = Image.fromarray(np.tile(rgb_back, (2, 4, 1)))  # 4 x 2 blocks = 512 x 256
    tile_img.save(out / "floor_512x256.png")
    tile_img.resize((tile_img.width * 3, tile_img.height * 3), Image.NEAREST).save(out / "floor_512x256_x3.png")

    # scale check on the rendered block: joint lines (dark valleys of the luminance profile)
    lum = rgb_back.astype(float) @ np.array([0.299, 0.587, 0.114])
    col = lum.mean(axis=0)[:128]
    row = lum.mean(axis=1)[:128]
    joint_cols = dark_valleys(col)
    joint_rows = dark_valleys(row)
    grid_ok = all(x % 32 in (0, 31) for x in joint_cols) and all(y % 16 in (0, 15, 1) for y in joint_rows)
    all_1x1 = set(layout["counts"]) == {"1x1"}
    lag_h, c_h = period_lag(col, 8, 64) if all_1x1 else (None, None)
    lag_v, c_v = period_lag(row, 6, 40) if all_1x1 else (None, None)

    # revision sheet: 256 x 192 floor + marine + two props, x3
    base = Image.fromarray(np.tile(rgb_back, (2, 2, 1))).convert("RGBA").crop((0, 0, 256, 192))
    marine = Image.open(MARINE).convert("RGBA").crop((0, 0, 40, 40))
    banco = Image.open(BANCO).convert("RGBA")
    santo = Image.open(SANTO).convert("RGBA")
    paste_sprite(base, banco, (56, 120))
    paste_sprite(base, santo, (200, 130))
    paste_sprite(base, marine, (120, 150), anchor_xy=(20, 33))
    base.convert("RGB").resize((768, 576), Image.NEAREST).save(out / "revision_x3.png")

    shapes = layout["counts"]
    stats = {
        "variant": a.variant,
        "unique_tiles": len(tiles),
        "palette_colors_used": len(pal_hex),
        "period_tiles": [16, 16],
        "pieces_per_block": shapes,
        "slab_variants_used": {k: len(v) for k, v in layout["variants_used"].items()},
        "period_seam_max_mismatch_pct": round(seam_pct, 3),
        "period_seam_exact": seam_pct == 0.0,
        "period_seam_note": "interior pixels (outer ring excluded) of the 8 neighbours vs the centre block",
        "json_reconstruction_pixel_exact": ok_json,
        "joint_cols_block128": joint_cols,
        "joint_rows_block128": joint_rows,
        "joints_on_unit_grid_32x16": grid_ok,
        "px_per_m_measured_horizontal": round(lag_h / P_M, 3) if all_1x1 else None,
        "px_per_m_measured_depth": round(lag_v / P_M, 3) if all_1x1 else None,
        "px_per_m_measured_note": "autocorrelation of the joint pattern; only valid for the regular 1x1 layout",
        "px_per_m_expected": [17.9, 8.95],
        "render_samples": a.samples,
        "render_seed": a.seed,
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print("OUT", out)


if __name__ == "__main__":
    main()
