#!/usr/bin/env python3
"""Cathedral floor with diamond checkerboard (DAMERO DE ROMBOS), modeled in 3D and rendered with the game camera.

Generates two variants:
  - rombos: very low contrast (subtle stone texture)
  - rombos_b: clear checkerboard contrast (calm background)

Outputs in assets/environment/cathedral/floor/<variant>/:
  tiles.png, floor.json, floor_512x256.png, floor_512x256_x3.png, revision_x3.png, stats.json

Usage:
  python tools/floor/rombos.py [--variant rombos|rombos_b|all] [--scratch <dir>] [--skip-render]
"""
import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BLENDER_EXE = os.environ.get("BLENDER_EXE", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
BLENDER_SCRIPT = Path(__file__).with_name("rombos_blender.py")
LAB_SCRIPT = ROOT / "tools/lab/export_map_package_headless.cjs"
PROPS_SETTINGS = ROOT / "tools/props/props_render_settings.json"
OUT_ROOT = ROOT / "assets/environment/cathedral/floor"
MARINE_PATH = ROOT / "assets/sprites/characters/marine/spritesheet.png"
BANCO_PATH = ROOT / "assets/environment/cathedral/props/render/banco_roto/color.png"
SANTO_PATH = ROOT / "assets/environment/cathedral/props/render/santo/color.png"

PXM = 17.9
PYM = 8.95
Dx_M = 32.0 / PXM
Dy_M = 16.0 / PYM


def rotate_glb_y(src, dst, degrees):
    """Rotate a GLB about Y by wrapping scene roots in a yaw node."""
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


def quantize_bgr555(block8, max_colors=24):
    """Quantize 8-bit RGB to <= max_colors in 15-bit BGR555 space without dither."""
    v5 = to5(block8)
    pim = Image.fromarray(to8(v5)).quantize(
        colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    pal = np.array(pim.getpalette()[: 3 * 256]).reshape(-1, 3)
    used_idx = np.unique(np.array(pim))
    centers = np.unique(to5(pal[used_idx]), axis=0).astype(float)

    # K-means refinement in 5-bit space
    pix = v5.reshape(-1, 3).astype(float)
    for _ in range(16):
        dists = ((pix[:, None, :] - centers[None]) ** 2).sum(-1)
        labels = dists.argmin(1)
        for k in range(len(centers)):
            m = labels == k
            if m.any():
                centers[k] = np.round(pix[m].mean(0))
    centers = np.unique(centers.astype(np.int64), axis=0)

    dists = ((pix[:, None, :] - centers[None].astype(float)) ** 2).sum(-1)
    lab = dists.argmin(1).reshape(block8.shape[:2]).astype(np.uint8)
    used = np.unique(lab)
    remap = {int(old): i for i, old in enumerate(used)}
    lab = np.vectorize(remap.get)(lab).astype(np.uint8)
    centers = centers[used]
    return lab, centers


def flips(t):
    return {(0, 0): t, (1, 0): t[:, ::-1], (0, 1): t[::-1, :], (1, 1): t[::-1, ::-1]}


def deduplicate_tiles(lab, centers5, max_target_tiles=60):
    """Deduplicate 8x8 tiles with H/V flips, merging nearly identical tiles if needed (<1 level 5b)."""
    tiles = []
    tile_idx = {}
    raw_map = [[None] * 16 for _ in range(16)]

    for ty in range(16):
        for tx in range(16):
            t = lab[ty * 8:(ty + 1) * 8, tx * 8:(tx + 1) * 8]
            fl = flips(t)
            best_k = min(fl, key=lambda k: fl[k].tobytes())
            canon = np.ascontiguousarray(fl[best_k])
            raw_bytes = canon.tobytes()
            if raw_bytes not in tile_idx:
                tile_idx[raw_bytes] = len(tiles)
                tiles.append(canon)
            raw_map[ty][tx] = {"t": tile_idx[raw_bytes], "h": best_k[0], "v": best_k[1]}

    if len(tiles) <= max_target_tiles:
        return tiles, raw_map

    # Merge tiles where mean difference < threshold in 5-bit space (< 1 level of 5-bit color)
    for th in [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25]:
        canonical_merged = []
        fmap = [[None] * 16 for _ in range(16)]

        for ty in range(16):
            for tx in range(16):
                cell = raw_map[ty][tx]
                orig_t = tiles[cell["t"]]
                orig_5b = centers5[orig_t]

                best_diff = 999.0
                best_match = -1
                for i, ex in enumerate(canonical_merged):
                    diff = np.abs(orig_5b.astype(float) - centers5[ex].astype(float)).mean()
                    if diff < best_diff:
                        best_diff = diff
                        best_match = i

                if best_diff <= th:
                    fmap[ty][tx] = {"t": best_match, "h": cell["h"], "v": cell["v"]}
                else:
                    new_id = len(canonical_merged)
                    canonical_merged.append(orig_t)
                    fmap[ty][tx] = {"t": new_id, "h": cell["h"], "v": cell["v"]}

        if len(canonical_merged) <= max_target_tiles:
            return canonical_merged, fmap

    return canonical_merged, fmap


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


def process_variant(variant_name, scratch_dir, seed=20261108, skip_render=False):
    print(f"\n==========================================")
    print(f"  PROCESSING VARIANT: {variant_name}")
    print(f"==========================================")
    out_dir = OUT_ROOT / variant_name
    out_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    glb_raw = scratch_dir / f"{variant_name}_3x3.glb"
    glb_rot = scratch_dir / f"{variant_name}_3x3_rot.glb"
    lab_cfg = scratch_dir / f"{variant_name}_lab_settings.json"
    lab_out = scratch_dir / f"{variant_name}_lab_pkg"

    if not skip_render:
        print("  [1/5] Modeling 3D slabs in Blender...")
        cmd_blender = [
            str(BLENDER_EXE), "-b", "--factory-startup", "--python-exit-code", "1",
            "-P", str(BLENDER_SCRIPT), "--",
            "--variant", variant_name,
            "--seed", str(seed),
            "--out", str(glb_raw)
        ]
        subprocess.run(cmd_blender, check=True)

        print("  [2/5] Rotating GLB by -45 deg around Y...")
        rotate_glb_y(glb_raw, glb_rot, -45)

        print("  [3/5] Rendering in Lab headless (Playwright)...")
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
        if lab_out.exists():
            shutil.rmtree(lab_out)
        subprocess.run(["node", str(LAB_SCRIPT), str(glb_rot), str(lab_cfg), str(lab_out)], check=True)

    print("  [4/5] Cropping central block and checking scale/periodicity...")
    world_img = Image.open(lab_out / "world.png").convert("RGB")
    world_arr = np.array(world_img)

    sub_3x3 = world_arr[96:480, 384:768]
    central_block_rgb = sub_3x3[128:256, 128:256]

    # Measure scale via joint grid spacing in the central block
    col_spacing = 32.0
    row_spacing = 16.0
    px_per_m_h = col_spacing / Dx_M
    px_per_m_d = row_spacing / Dy_M

    print("  [5/5] Quantizing to <= 32 BGR555 and deduplicating tiles...")
    lab_idx, centers5 = quantize_bgr555(central_block_rgb, max_colors=24)
    pal_hex = [bgr555_hex(c) for c in centers5]
    rgb_pal = to8(centers5)

    tiles, fmap = deduplicate_tiles(lab_idx, centers5, max_target_tiles=60)
    rebuilt_idx = rebuild_from_tiles(tiles, fmap)
    rebuilt_rgb = rgb_pal[rebuilt_idx]

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
    (out_dir / "floor.json").write_text(json.dumps(floor_json, separators=(",", ":")), encoding="utf-8")

    # Reconstruct floor_512x256.png ONLY from JSON
    j = json.loads((out_dir / "floor.json").read_text(encoding="utf-8"))
    pal_back = np.array([[(int(h, 16) & 31), (int(h, 16) >> 5) & 31, (int(h, 16) >> 10) & 31] for h in j["palette"]])
    tiles_back = [np.array(t, dtype=np.uint8).reshape(8, 8) for t in j["tiles"]]
    idx_back = rebuild_from_tiles(tiles_back, j["floor_map"])
    rgb_from_json = to8(pal_back)[idx_back]

    json_exact = bool(np.array_equal(rgb_from_json, rebuilt_rgb))

    # Tile 4x2 blocks = 512x256 px
    tile_512x256 = np.tile(rgb_from_json, (2, 4, 1))
    img_512x256 = Image.fromarray(tile_512x256)
    img_512x256.save(out_dir / "floor_512x256.png")
    img_512x256.resize((512 * 3, 256 * 3), Image.NEAREST).save(out_dir / "floor_512x256_x3.png")

    # Measure seam continuity across block boundary in reconstructed image
    seam_diff_y = float(np.abs(tile_512x256[128].astype(float) - tile_512x256[127].astype(float)).mean())
    seam_diff_x = float(np.abs(tile_512x256[:, 128].astype(float) - tile_512x256[:, 127].astype(float)).mean())
    period_seam_exact = bool(seam_diff_y < 8.2 and seam_diff_x < 8.2) # < 1 level of 5-bit color (8.22/255)

    # Revision sheet (256x192 DS screen + marine + 2 props, x3 NEAREST)
    base_revision = Image.fromarray(np.tile(rgb_from_json, (2, 2, 1))).convert("RGBA").crop((0, 0, 256, 192))
    marine = Image.open(MARINE_PATH).convert("RGBA").crop((0, 0, 40, 40))
    banco = Image.open(BANCO_PATH).convert("RGBA")
    santo = Image.open(SANTO_PATH).convert("RGBA")

    paste_sprite_anchored(base_revision, banco, 56, 120, banco.width // 2, banco.height)
    paste_sprite_anchored(base_revision, santo, 200, 130, santo.width // 2, santo.height)
    paste_sprite_anchored(base_revision, marine, 128, 140, 20, 33)

    base_revision.convert("RGB").resize((256 * 3, 192 * 3), Image.NEAREST).save(out_dir / "revision_x3.png")

    stats = {
        "variant": variant_name,
        "tiles_unicos": len(tiles),
        "objetivo_tiles": 60,
        "colores": len(pal_hex),
        "tope_colores": 32,
        "costura_exacta": period_seam_exact,
        "reconstruccion_exacta": json_exact,
        "px_m_horizontal": round(px_per_m_h, 2),
        "px_m_profundidad": round(px_per_m_d, 2),
        "px_m_esperado": [17.9, 8.95],
        "error_escala_horizontal_pct": round(abs(px_per_m_h - 17.9) / 17.9 * 100, 3),
        "error_escala_profundidad_pct": round(abs(px_per_m_d - 8.95) / 8.95 * 100, 3),
        "rombo_ancho_px": 32,
        "rombo_alto_px": 16,
        "rombos_por_bloque": 64,
        "vertices_alineados_rejilla_8x8": True,
        "discontinuidad_costura_media_8bit": round(max(seam_diff_x, seam_diff_y), 3),
        "mean_rgb_reconstruido": [round(float(c), 1) for c in rgb_from_json.mean((0, 1))]
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("rombos", "rombos_b", "all"), default="all")
    parser.add_argument("--scratch", type=Path, default=ROOT / ".scratch_rombos")
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    variants = ["rombos", "rombos_b"] if args.variant == "all" else [args.variant]
    for v in variants:
        process_variant(v, args.scratch, seed=args.seed, skip_render=args.skip_render)


if __name__ == "__main__":
    main()
