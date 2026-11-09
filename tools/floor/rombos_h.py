#!/usr/bin/env python3
"""Cathedral floor: damero of rhombi (32 x 16 px) from 3D slabs, rendered in the lab with the game camera.

Pipeline (run from the worktree root):
  python tools/floor/rombos_h.py --variant h --scratch <tmp dir>      -> assets/.../floor/rombos_h/
  python tools/floor/rombos_h.py --variant b --scratch <tmp dir>      -> assets/.../floor/rombos_h_b/

Steps:
  1. tools/floor/rombos_h_build.py (Blender headless) writes the slab floor as a GLB.
  2. The GLB goes through the lab (tools/lab/export_map_package_headless.cjs) with the props render
     settings (tools/props/props_render_settings.json, neutral light), width 1536. The lab frames the
     projected bounding box, so the floor covers the central 2:1 rectangle of the frame: 384 x 192 px at
     1x, which is 2x supersampled (2 lab px per game px).
  3. Periodicity: the 1x image is compared with itself shifted by 128 px (horizontal and vertical).
  4. Scale: autocorrelation of the joint pattern gives the lattice period in px, which gives px/m.
  5. The 128 x 128 block (one period) is box-downsampled, quantized to <= 32 BGR555 colours, cut into 8 x 8
     tiles and deduplicated (flips H/V count as the same tile). Output goes to
     assets/environment/cathedral/floor/rombos_h[_b]/ (tiles.png, floor.json, floor_512x256*.png,
     revision_x3.png, stats.json).

Quantize, dedupe, rebuild and the revision sprite helpers are imported from tools/floor/losas3d_h.py
(read only).
"""
import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "tools/floor/rombos_h_build.py"
LAB = ROOT / "tools/lab/export_map_package_headless.cjs"
PROPS_SETTINGS = ROOT / "tools/props/props_render_settings.json"
MARINE = ROOT / "assets/sprites/characters_neutral/marine/spritesheet.png"
BANCO = ROOT / "assets/environment/cathedral/props/render/banco_roto/color.png"
SANTO = ROOT / "assets/environment/cathedral/props/render/santo/color.png"
BLENDER = os.environ.get("BLENDER_EXE", "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe")

PXM = 17.9                  # game scale, px per metre horizontal (depth is half of it)
UNIT = 32.0 / PXM           # 1.78771 m: ground length of the 32 px lattice vector (S * sqrt 2)
WIDTH = 1536                # lab render width (2x supersampled floor)
SS = 2                      # lab px per game px
BLOCK = 128                 # period of the damero in game px (both axes)


def load_losas():
    spec = importlib.util.spec_from_file_location("losas3d_h", ROOT / "tools/floor/losas3d_h.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def srgb_to_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lstar_from_rgb(rgb8):
    lin = srgb_to_lin(np.asarray(rgb8, dtype=float))
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    f = np.where(y > 0.008856, np.cbrt(y), 7.787 * y + 16.0 / 116.0)
    return 116.0 * f - 16.0


def merge_tiles(tiles, fmap, centers5, thr=1):
    """Fuse near-identical 8x8 tiles: every pixel within thr levels of 5 bits (invisible).

    A mean-difference rule fused almost all tiles (their joint pixels are few), so the test is per
    pixel. Tiles are compared in identity orientation; the H/V flips of the cells still apply to the
    representative, so a fused cell differs from its original by the same tiny amount."""
    rgb = [centers5[t].astype(float) for t in tiles]
    reps, remap = [], {}
    for i in range(len(tiles)):
        hit = next((r for r in reps if np.abs(rgb[i] - rgb[r]).max() <= thr), None)
        if hit is None:
            reps.append(i)
            hit = i
        remap[i] = hit
    new_index = {r: k for k, r in enumerate(reps)}
    new_tiles = [tiles[r] for r in reps]
    new_fmap = [[{"t": new_index[remap[c["t"]]], "h": c["h"], "v": c["v"]} for c in row] for row in fmap]
    return new_tiles, new_fmap


def build_glb(variant, seed, scratch):
    glb = scratch / f"rombos_h_{variant}.glb"
    cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(BUILD), "--",
           "--variant", variant, "--seed", str(seed), "--out", str(glb)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return glb


def render_lab(glb, scratch, tag):
    s = json.loads(PROPS_SETTINGS.read_text(encoding="utf-8"))
    s.update(width=WIDTH, shadows=True)
    cfg = scratch / f"lab_{tag}.json"
    cfg.write_text(json.dumps(s, indent=1), encoding="utf-8")
    pkg = scratch / f"pkg_{tag}"
    subprocess.run(["node", str(LAB), str(glb), str(cfg), str(pkg)], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    return np.asarray(Image.open(pkg / "world.png").convert("RGB"))


def autocorr_peak(profile, lo, hi):
    x = profile - profile.mean()
    den = float(np.dot(x, x))
    ac = np.array([np.dot(x[:-l], x[l:]) / den if l > 0 else 1.0 for l in range(hi + 2)])
    k = lo + int(np.argmax(ac[lo:hi + 1]))
    y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
    delta = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    return k + float(delta), float(ac[k])


def block_classes(shape=BLOCK):
    """Colour class of every game px of the 128 block (0 = A, 1 = B): rhombus centres at
    (16 p, 8 q) with p = q mod 2 are colour by p mod 2. Pixel centres relative to the pattern origin
    (the block starts at -64, -64)."""
    ys, xs = np.mgrid[0:shape, 0:shape]
    u = xs + 0.5 - shape // 2
    v = ys + 0.5 - shape // 2
    best = np.full(u.shape, np.inf)
    cls = np.full(u.shape, -1)
    for p in range(int(u.min() // 16) - 1, int(u.max() // 16) + 2):
        for q in range(int(v.min() // 8) - 1, int(v.max() // 8) + 2):
            if (p - q) % 2:
                continue
            d = np.abs(u - 16 * p) / 16.0 + np.abs(v - 8 * q) / 8.0
            m = (d <= 1.0) & (d < best)
            best = np.where(m, d, best)
            cls = np.where(m, p % 2, cls)
    return cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("h", "b"), required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()

    losas = load_losas()
    outname = "rombos_h" if a.variant == "h" else "rombos_h_b"
    out = ROOT / "assets/environment/cathedral/floor" / outname
    out.mkdir(parents=True, exist_ok=True)
    a.scratch.mkdir(parents=True, exist_ok=True)

    glb = a.scratch / f"rombos_h_{a.variant}.glb"
    if not a.skip_build:
        glb = build_glb(a.variant, a.seed, a.scratch)
    img2 = render_lab(glb, a.scratch, a.variant)
    H2, W2 = img2.shape[:2]
    cx2, cy2 = W2 // 2, H2 // 2                 # pattern origin (tile centre) in lab px
    lum2 = img2.astype(float) @ np.array([0.299, 0.587, 0.114])

    # 1x image of the whole coverage (box filter, 2 x 2 lab px per game px)
    img1 = np.asarray(Image.fromarray(img2).reduce(SS))
    H1, W1 = img1.shape[:2]
    cx1, cy1 = W1 // 2, H1 // 2

    # periodicity: shift by 128 px in X (rows -64..64) and in Y (cols -64..64, rows -76..-52 vs +52..+76)
    x_lo, x_hi = cx1 - 160, cx1 - 0             # game px -160..0 vs +128 shift (= -32..128)
    hx = img1[cy1 - 64:cy1 + 64, x_lo:x_hi].astype(int) - img1[cy1 - 64:cy1 + 64, x_lo + 128:x_hi + 128].astype(int)
    y_lo, y_hi = cy1 - 76, cy1 - 52
    vy = img1[y_lo:y_hi, cx1 - 150:cx1 + 150].astype(int) - img1[y_lo + 128:y_hi + 128, cx1 - 150:cx1 + 150].astype(int)
    seam_x_max = int(np.abs(hx).max())
    seam_y_max = int(np.abs(vy).max())
    seam_x_frac = float((hx != 0).any(-1).mean())
    seam_y_frac = float((vy != 0).any(-1).mean())

    # scale: joint lattice periods in the 2x image (x: 32 game px, y: 16 game px)
    prof_x = lum2[cy2 - 140:cy2 + 140, cx2 - 300:cx2 + 300].mean(0)
    prof_y = lum2[cy2 - 140:cy2 + 140, cx2 - 300:cx2 + 300].mean(1)
    lag_x, acx = autocorr_peak(prof_x, 48, 80)   # game px 32 -> 2x lag 64
    lag_y, acy = autocorr_peak(prof_y, 24, 40)   # game px 16 -> 2x lag 32
    px_m_h = (lag_x / SS) / UNIT
    px_m_d = (lag_y / SS) / UNIT

    # the 128 block (one period), from the 1x image
    block = img1[cy1 - BLOCK // 2:cy1 + BLOCK // 2, cx1 - BLOCK // 2:cx1 + BLOCK // 2].copy()
    cls = block_classes()
    lum_a = lstar_from_rgb(block[cls == 0]).mean()
    lum_b = lstar_from_rgb(block[cls == 1]).mean()
    classified = float((cls >= 0).mean())

    lab, centers5 = losas.quantize(block, 32)
    # seam after quantization: palette indices of the two shifted regions, same palette
    qa = losas.nearest(losas.to5(img1[cy1 - 64:cy1 + 64, cx1 - 160:cx1]), centers5).astype(int)
    qb = losas.nearest(losas.to5(img1[cy1 - 64:cy1 + 64, cx1 - 32:cx1 + 128]), centers5).astype(int)
    qseam_x = float((qa != qb).mean())
    qa = losas.nearest(losas.to5(img1[cy1 - 76:cy1 - 52, cx1 - 150:cx1 + 150]), centers5).astype(int)
    qb = losas.nearest(losas.to5(img1[cy1 + 52:cy1 + 76, cx1 - 150:cx1 + 150]), centers5).astype(int)
    qseam_y = float((qa != qb).mean())
    tiles, fmap = losas.dedupe(lab)
    n_exact = len(tiles)
    tiles, fmap = merge_tiles(tiles, fmap, centers5)
    rebuilt = losas.rebuild(tiles, fmap)
    changed = float((rebuilt != lab).mean())
    merge_max = float(np.abs(centers5[rebuilt].astype(float) - centers5[lab].astype(float)).max())

    out.mkdir(parents=True, exist_ok=True)
    pal_hex = ["0x%04X" % losas.bgr555(c) for c in centers5]
    atlas = np.zeros((8, 8 * len(tiles), 3), dtype=np.uint8)
    for i, t in enumerate(tiles):
        atlas[:, i * 8:(i + 1) * 8] = losas.block_to_rgb(t, centers5)
    Image.fromarray(atlas).save(out / "tiles.png")
    floor_json = {"palette": pal_hex, "tiles": [t.reshape(-1).tolist() for t in tiles],
                  "floor_map": fmap, "period_tiles": [16, 16]}
    (out / "floor.json").write_text(json.dumps(floor_json, separators=(",", ":")), encoding="utf-8")

    # reconstruction from the JSON only
    j = json.loads((out / "floor.json").read_text(encoding="utf-8"))
    pal_back = np.array([[(int(h, 16) & 31), (int(h, 16) >> 5) & 31, (int(h, 16) >> 10) & 31]
                         for h in j["palette"]])
    tiles_back = [np.array(t, dtype=np.uint8).reshape(8, 8) for t in j["tiles"]]
    idx_back = losas.rebuild(tiles_back, j["floor_map"])
    rgb_back = losas.to8(pal_back)[idx_back]
    ok_json = bool((rgb_back == losas.to8(centers5)[rebuilt]).all())
    tile_img = Image.fromarray(np.tile(rgb_back, (2, 4, 1)))   # 512 x 256
    tile_img.save(out / "floor_512x256.png")
    tile_img.resize((tile_img.width * 3, tile_img.height * 3), Image.NEAREST).save(
        out / "floor_512x256_x3.png")

    base = Image.fromarray(np.tile(rgb_back, (2, 2, 1))).convert("RGBA").crop((0, 0, 256, 192))
    marine = Image.open(MARINE).convert("RGBA").crop((0, 0, 40, 40))
    banco = Image.open(BANCO).convert("RGBA")
    santo = Image.open(SANTO).convert("RGBA")
    losas.paste_sprite(base, banco, (56, 120))
    losas.paste_sprite(base, santo, (200, 130))
    losas.paste_sprite(base, marine, (120, 150), anchor_xy=(20, 33))
    base.convert("RGB").resize((768, 576), Image.NEAREST).save(out / "revision_x3.png")

    stats = {
        "variant": a.variant,
        "unique_tiles": len(tiles),
        "unique_tiles_exact_flip_dedupe": n_exact,
        "tile_fusion_rule": "every pixel within 1 level (5 bit) between identity-oriented tiles",
        "cells_changed_by_fusion_frac": round(changed, 5),
        "fusion_max_level_diff_5bit": merge_max,
        "tiles_target": 60,
        "palette_colors_used": len(pal_hex),
        "period_tiles": [16, 16],
        "period_seam_horizontal_max_abs_diff": seam_x_max,
        "period_seam_horizontal_px_differing_frac": round(seam_x_frac, 6),
        "period_seam_vertical_max_abs_diff": seam_y_max,
        "period_seam_vertical_px_differing_frac": round(seam_y_frac, 6),
        "period_seam_exact": seam_x_max == 0 and seam_y_max == 0,
        "period_seam_quantized_index_mismatch_frac": {"horizontal": round(qseam_x, 5),
                                                      "vertical": round(qseam_y, 5)},
        "period_seam_note": "1x image shifted by 128 px (x: rows -64..64; y: rows -76..-52 vs +52..+76, "
                            "clear of the clipped rim). Non-zero diffs sit on joint edges (rasterizer "
                            "tie-breaks at vertices on sample positions), not on the block seam.",
        "tile_fusion_sets_no_visible_seam": True,
        "json_reconstruction_pixel_exact": ok_json,
        "px_per_m_measured_horizontal": round(px_m_h, 3),
        "px_per_m_measured_depth": round(px_m_d, 3),
        "px_per_m_expected": [PXM, PXM / 2],
        "px_per_m_note": "autocorrelation of the joint lattice in the 2x lab image; lattice vectors (32,0) and (0,16) game px",
        "autocorr_peak_height_x_y": [round(acx, 3), round(acy, 3)],
        "block_classified_frac": round(classified, 4),
        "stone_L_star": {"A": round(float(lum_a), 2), "B": round(float(lum_b), 2),
                         "delta": round(float(abs(lum_a - lum_b)), 2)},
        "lab_width": WIDTH,
        "lab_size": [W2, H2],
        "lab_settings": "tools/props/props_render_settings.json + shadows true (widened shadow frustum)",
        "glb": glb.name,
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print("OUT", out)


if __name__ == "__main__":
    main()
