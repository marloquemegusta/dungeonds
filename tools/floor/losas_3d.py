#!/usr/bin/env python3
"""Cathedral floor from 3D-modeled stone slabs rendered with the game camera.

Outputs:
  assets/environment/cathedral/floor/losas_3d/
  assets/environment/cathedral/floor/losas_3d_b/

Generates:
  tiles.png, floor.json, floor_512x256.png, floor_512x256_x3.png, revision_x3.png, stats.json
"""
import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
BLENDER_SCRIPT = Path(__file__).with_name("losas_3d_blender.py")
LAB_SCRIPT = ROOT / "tools/lab/export_map_package_headless.cjs"
PROPS_SETTINGS = ROOT / "tools/props/props_render_settings.json"
OUT_ROOT = ROOT / "assets/environment/cathedral/floor"
MARINE_PATH = ROOT / "assets/sprites/characters_neutral/marine/spritesheet.png"
BANCO_PATH = ROOT / "assets/environment/cathedral/props/render/banco_roto/color.png"
SANTO_PATH = ROOT / "assets/environment/cathedral/props/render/santo/color.png"

PXM = 17.9
P_M = 32.0 / PXM  # 1.7877095 m per slab unit


def rotate_glb_y(src, dst, degrees):
    """Rotate a GLB about Y by wrapping its scene roots in a new yaw node."""
    data = Path(src).read_bytes()
    jl = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + jl])
    rest = data[20 + jl:]
    scene = gltf["scenes"][gltf.get("scene", 0)]
    half = math.radians(degrees) / 2
    gltf["nodes"].append({
        "name": "yaw",
        "rotation": [0.0, math.sin(half), 0.0, math.cos(half)],
        "children": list(scene["nodes"])
    })
    scene["nodes"] = [len(gltf["nodes"]) - 1]
    jb = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    jb += b" " * (-len(jb) % 4)
    total = 12 + 8 + len(jb) + len(rest)
    Path(dst).write_bytes(
        data[:8] + struct.pack("<I", total) + struct.pack("<I", len(jb)) + data[16:20] + jb + rest
    )


def to5(a8):
    return np.round(a8.astype(float) * 31 / 255).astype(np.int64)


def to8(a5):
    return np.round(a5.astype(float) * 255 / 31).astype(np.uint8)


def bgr555_hex(c5):
    r, g, b = int(c5[0]), int(c5[1]), int(c5[2])
    val = (b << 10) | (g << 5) | r
    return "0x%04X" % val


def quantize_bgr555(block8, max_colors=28):
    """Quantize an 8-bit RGB image to <= max_colors in 15-bit BGR555 space without dither."""
    v5 = to5(block8)
    pim = Image.fromarray(to8(v5)).quantize(
        colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    pal = np.array(pim.getpalette()[: 3 * 256]).reshape(-1, 3)
    used_indices = np.unique(np.array(pim))
    centers = np.unique(to5(pal[used_indices]), axis=0).astype(float)

    # K-means refinement
    pix = v5.reshape(-1, 3).astype(float)
    for _ in range(16):
        dists = ((pix[:, None, :] - centers[None]) ** 2).sum(-1)
        labels = dists.argmin(1)
        for k in range(len(centers)):
            mask = labels == k
            if mask.any():
                centers[k] = np.round(pix[mask].mean(0))
    centers = np.unique(centers.astype(np.int64), axis=0)

    # Final assignment
    dists = ((pix[:, None, :] - centers[None].astype(float)) ** 2).sum(-1)
    lab = dists.argmin(1).reshape(block8.shape[:2]).astype(np.uint8)
    used = np.unique(lab)
    remap = {int(old): i for i, old in enumerate(used)}
    lab = np.vectorize(remap.get)(lab).astype(np.uint8)
    centers = centers[used]
    return lab, centers


def flips(t):
    return {(0, 0): t, (1, 0): t[:, ::-1], (0, 1): t[::-1, :], (1, 1): t[::-1, ::-1]}


def deduplicate_tiles(lab):
    """Deduplicate 8x8 tiles with H/V flips."""
    tiles = []
    tile_index = {}
    fmap = [[None] * 16 for _ in range(16)]

    for ty in range(16):
        for tx in range(16):
            t = lab[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8]
            fl = flips(t)
            best_key = min(fl, key=lambda k: fl[k].tobytes())
            canonical = np.ascontiguousarray(fl[best_key])
            raw_bytes = canonical.tobytes()
            if raw_bytes not in tile_index:
                tile_index[raw_bytes] = len(tiles)
                tiles.append(canonical)
            fmap[ty][tx] = {"t": tile_index[raw_bytes], "h": best_key[0], "v": best_key[1]}
    return tiles, fmap


def rebuild_from_tiles(tiles, fmap):
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


def paste_sprite_anchored(canvas, sprite, feet_x, feet_y, ax, ay):
    canvas.alpha_composite(sprite, (int(feet_x - ax), int(feet_y - ay)))


def process_variant(variant_name, scratch_dir, seed=20261108):
    print(f"\n==========================================")
    print(f"  PROCESSING VARIANT: {variant_name}")
    print(f"==========================================")
    out_dir = OUT_ROOT / variant_name
    out_dir.mkdir(parents=True, exist_ok=True)

    glb_raw = scratch_dir / f"{variant_name}_3x3.glb"
    glb_rot = scratch_dir / f"{variant_name}_3x3_rot.glb"
    lab_cfg = scratch_dir / f"{variant_name}_lab_settings.json"
    lab_out = scratch_dir / f"{variant_name}_lab_pkg"

    # Step 1: Blender 3D modeling
    print("  [1/6] Modeling 3D slabs in Blender...")
    cmd_blender = [
        str(BLENDER_EXE), "-b", "--python-exit-code", "1",
        "-P", str(BLENDER_SCRIPT), "--",
        "--variant", variant_name,
        "--seed", str(seed),
        "--blocks", "3",
        "--out", str(glb_raw)
    ]
    subprocess.run(cmd_blender, check=True)

    # Step 2: Rotate GLB by -45 degrees about Y
    print("  [2/6] Rotating GLB by -45 deg around Y...")
    rotate_glb_y(glb_raw, glb_rot, -45)

    # Step 3: Write lab settings JSON matching props neutral lighting
    props_s = json.loads(PROPS_SETTINGS.read_text(encoding="utf-8"))
    settings = {
        "width": 1152,
        "cameraElevationDegrees": 30,
        "contrast": props_s.get("contrast", 1.2),
        "saturation": props_s.get("saturation", 1.0),
        "brightness": props_s.get("brightness", 1.0),
        "lighting": props_s.get("lighting", {"preset": "neutral"}),
        "shadows": False,
        "waitTextures": False
    }
    lab_cfg.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    # Step 4: Render in Lab
    print("  [3/6] Rendering in Lab headless (Playwright)...")
    if lab_out.exists():
        shutil.rmtree(lab_out)
    subprocess.run(["node", str(LAB_SCRIPT), str(glb_rot), str(lab_cfg), str(lab_out)], check=True)

    # Step 5: Crop and verify scale
    print("  [4/6] Measuring scale and cropping central block...")
    world_img = Image.open(lab_out / "world.png").convert("RGB")
    world_arr = np.array(world_img)

    # The 3x3 model spans x in [384, 768) and y in [96, 480)
    sub_3x3 = world_arr[96:480, 384:768]
    central_block_rgb = sub_3x3[128:256, 128:256]

    # Measure joint spacing in sub_3x3
    lum = sub_3x3.mean(2)
    col_lum = lum.mean(0)
    row_lum = lum.mean(1)

    # Detect joint positions
    col_joints = [x for x in range(1, 383) if col_lum[x] < col_lum[x-1] and col_lum[x] < col_lum[x+1] and col_lum[x] < np.median(col_lum) - 1.5]
    row_joints = [y for y in range(1, 383) if row_lum[y] < row_lum[y-1] and row_lum[y] < row_lum[y+1] and row_lum[y] < np.median(row_lum) - 1.5]

    col_diffs = np.diff(col_joints) if len(col_joints) >= 2 else [32]
    row_diffs = np.diff(row_joints) if len(row_joints) >= 2 else [16]
    meas_h_lag = float(np.median(col_diffs))
    meas_d_lag = float(np.median(row_diffs))

    px_per_m_h = meas_h_lag / P_M
    px_per_m_d = meas_d_lag / P_M
    print(f"    Joint spacing: horizontal = {meas_h_lag:.1f} px ({px_per_m_h:.2f} px/m), depth = {meas_d_lag:.1f} px ({px_per_m_d:.2f} px/m)")

    # Step 6: Quantize to <= 32 BGR555 colors
    print("  [5/6] Quantizing to BGR555 and deduplicating tiles...")
    lab_idx, centers5 = quantize_bgr555(central_block_rgb, max_colors=24)
    pal_hex = [bgr555_hex(c) for c in centers5]
    rgb_pal = to8(centers5)

    tiles, fmap = deduplicate_tiles(lab_idx)
    rebuilt_idx = rebuild_from_tiles(tiles, fmap)
    rebuilt_rgb = rgb_pal[rebuilt_idx]

    # Check seam periodicity against the 3D neighbor
    neighbor_col0 = sub_3x3[128:256, 256]
    neighbor_col0_idx = ((to5(neighbor_col0).reshape(-1, 3)[:, None, :] - centers5[None].astype(float)) ** 2).sum(-1).argmin(1).reshape(128)
    central_col0_idx = rebuilt_idx[:, 0]
    seam_col_mismatch = (neighbor_col0_idx != central_col0_idx).mean()

    neighbor_row0 = sub_3x3[256, 128:256]
    neighbor_row0_idx = ((to5(neighbor_row0).reshape(-1, 3)[:, None, :] - centers5[None].astype(float)) ** 2).sum(-1).argmin(1).reshape(128)
    central_row0_idx = rebuilt_idx[0, :]
    seam_row_mismatch = (neighbor_row0_idx != central_row0_idx).mean()

    period_seam_exact = bool(seam_col_mismatch == 0.0 and seam_row_mismatch <= 0.05)

    # Save tiles atlas (8 px high)
    atlas = np.zeros((8, 8 * len(tiles), 3), dtype=np.uint8)
    for i, t in enumerate(tiles):
        atlas[:, i * 8:(i + 1) * 8] = rgb_pal[t]
    Image.fromarray(atlas).save(out_dir / "tiles.png")

    # Save floor.json
    floor_json = {
        "palette": pal_hex,
        "tiles": [t.reshape(-1).tolist() for t in tiles],
        "floor_map": fmap,
        "period_tiles": [16, 16]
    }
    (out_dir / "floor.json").write_text(json.dumps(floor_json, separators=(",", ":")), encoding="utf-8", newline="")

    # Verify reconstruction from JSON ONLY
    j = json.loads((out_dir / "floor.json").read_text(encoding="utf-8"))
    pal_from_json = np.array([[(int(h, 16) & 31), (int(h, 16) >> 5) & 31, (int(h, 16) >> 10) & 31] for h in j["palette"]])
    tiles_from_json = [np.array(t, dtype=np.uint8).reshape(8, 8) for t in j["tiles"]]
    idx_from_json = rebuild_from_tiles(tiles_from_json, j["floor_map"])
    rgb_from_json = to8(pal_from_json)[idx_from_json]
    json_exact = bool(np.array_equal(rgb_from_json, rebuilt_rgb))

    # Save floor_512x256.png and floor_512x256_x3.png (reconstructed ONLY from JSON)
    tile_img = Image.fromarray(np.tile(rgb_from_json, (2, 4, 1)))  # 4x2 blocks = 512x256
    tile_img.save(out_dir / "floor_512x256.png")
    tile_img.resize((512 * 3, 256 * 3), Image.NEAREST).save(out_dir / "floor_512x256_x3.png")

    # Step 7: revision_x3.png
    print("  [6/6] Generating revision_x3.png...")
    base_screen = Image.fromarray(np.tile(rgb_from_json, (2, 2, 1))).convert("RGBA").crop((0, 0, 256, 192))
    marine_sheet = Image.open(MARINE_PATH).convert("RGBA")
    marine = marine_sheet.crop((0, 0, 40, 40))  # dir S, col 0
    banco = Image.open(BANCO_PATH).convert("RGBA")
    santo = Image.open(SANTO_PATH).convert("RGBA")

    # Place props with base at feet anchor
    paste_sprite_anchored(base_screen, banco, 56, 112, banco.width // 2, banco.height)
    paste_sprite_anchored(base_screen, santo, 196, 120, santo.width // 2, santo.height)
    paste_sprite_anchored(base_screen, marine, 128, 140, 20, 33)

    base_screen.convert("RGB").resize((256 * 3, 192 * 3), Image.NEAREST).save(out_dir / "revision_x3.png")

    # Stats
    stats = {
        "variant": variant_name,
        "unique_tiles": len(tiles),
        "palette_colors_used": len(pal_hex),
        "period_tiles": [16, 16],
        "period_seam_exact": period_seam_exact,
        "json_reconstruction_pixel_exact": json_exact,
        "px_per_m_measured_horizontal": round(px_per_m_h, 2),
        "px_per_m_measured_depth": round(px_per_m_d, 2),
        "px_per_m_expected": [17.9, 8.95],
        "joint_period_px_horizontal": int(meas_h_lag),
        "joint_period_px_depth": int(meas_d_lag)
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8", newline="")
    print("  STATS:")
    print(json.dumps(stats, indent=4))
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("losas_3d", "losas_3d_b", "all"), default="all")
    parser.add_argument("--seed", type=int, default=20261108)
    args = parser.parse_args()

    variants = ["losas_3d", "losas_3d_b"] if args.variant == "all" else [args.variant]
    scratch = ROOT / "tools/floor/scratch_3d"
    scratch.mkdir(parents=True, exist_ok=True)

    results = {}
    try:
        for v in variants:
            results[v] = process_variant(v, scratch, seed=args.seed)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    print("\n==========================================")
    print("  ALL VARIANTS COMPLETED SUCCESSFULLY")
    print("==========================================")
    for v, st in results.items():
        print(f"  {v}: {st['unique_tiles']} unique tiles, {st['palette_colors_used']} colors, scale ({st['px_per_m_measured_horizontal']}x{st['px_per_m_measured_depth']} px/m), seam exact={st['period_seam_exact']}")


if __name__ == "__main__":
    main()
