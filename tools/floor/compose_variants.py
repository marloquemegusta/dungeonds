#!/usr/bin/env python3
"""Compose full-lane verification images from 6 band variants per look.

For each look (w05, v04):
1. Renders the 6 variants using the lab with yaw -45 deg at exact 40.42 px/m scale (expect_w = 480).
2. Crops each variant to exactly 480x128 px.
3. Composes an 1152 px tall lane (6 DS screens = 9 bands) without repeating the same variant consecutively.
4. Applies finish (side walls, characters, 256x192 DS screen outline).
5. Generates variants_<look>.png and variants_<look>_sheet.png.
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_rotate import rotate_glb_y  # noqa: E402
from compose_lane import finish, floor_bbox, crop_period, WALL, PPM  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "assets/models/environment/floor_proc"
LANE = PROC / "lane"
LAB = ROOT / "tools/lab/export_map_package_headless.cjs"

# Calibrated width for 11.88 x 6.336m model giving 480 px floor width
_CALIBRATED_WIDTH = 734


def render(glb, tag, width=480, light=(3, .3, .25)):
    LANE.mkdir(parents=True, exist_ok=True)
    rot = LANE / f"{tag}_rot.glb"
    rotate_glb_y(glb, rot, -45)
    s = json.loads((ROOT / "assets/sprites/arenas/strip_kit/map_settings.json").read_text(encoding="utf-8"))
    s.pop("labRender", None)
    s.update(width=width, height=round(width * 2 / 3), pixelsPerMeter=PPM, orthoScaleMeters=width / PPM,
             shadows=True, waitTextures=True, waitTexturesMs=8000, saturation=1.0,
             lighting=dict(preset="custom", key=light[0], fill=light[1], world=light[2], rim=0))
    cfg = LANE / f"{tag}_lab.json"
    cfg.write_text(json.dumps(s, indent=1), encoding="utf-8")
    pkg = LANE / f"{tag}_pkg"
    subprocess.run(["node", str(LAB), str(rot), str(cfg), str(pkg)], check=True, cwd=ROOT)
    return Image.open(pkg / "world.png").convert("RGB")


def render_exact(glb, tag, expect_w=480, width=736, light=(3, .3, .25)):
    global _CALIBRATED_WIDTH
    init_w = _CALIBRATED_WIDTH if _CALIBRATED_WIDTH else width
    im = render(glb, tag, init_w, light)
    x0, y0, x1, y1 = floor_bbox(im)
    cur_w = x1 - x0
    print(f"  [{tag}] pass 1: floor bbox {cur_w}x{y1 - y0} at render width {init_w} (target {expect_w})")
    if abs(cur_w - expect_w) <= 2:
        _CALIBRATED_WIDTH = init_w
        return im
    w2 = round(init_w * expect_w / cur_w)
    print(f"  [{tag}] re-render at calibrated width {w2}")
    _CALIBRATED_WIDTH = w2
    im2 = render(glb, tag, w2, light)
    x0, y0, x1, y1 = floor_bbox(im2)
    print(f"  [{tag}] pass 2: floor bbox {x1 - x0}x{y1 - y0} at render width {w2}")
    return im2


def compose_lane_variants(bands, height=1152, seed=32026):
    """Stack 480x128 bands without repeating the same variant on two consecutive bands."""
    rng = random.Random(seed)
    num_bands = (height + 127) // 128
    seq = []
    for _ in range(num_bands):
        v = rng.randrange(len(bands))
        if len(bands) > 1:
            while seq and v == seq[-1]:
                v = rng.randrange(len(bands))
        seq.append(v)
    print(f"  band sequence ({len(seq)} bands): {seq}")

    img = Image.new("RGB", (512, height), WALL)
    for i, v_idx in enumerate(seq):
        y_pos = i * 128
        img.paste(bands[v_idx], (16, y_pos))
    return img, seq


def compose_sheet(bands, labels):
    """Compose a vertical sheet showing all variants with borders and labels."""
    bh = 128
    bw = 480
    header_h = 24
    pad = 8
    total_w = bw + pad * 2
    total_h = len(bands) * (bh + header_h + pad) + pad
    sheet = Image.new("RGB", (total_w, total_h), (22, 20, 18))
    d = ImageDraw.Draw(sheet)
    for i, (b, lbl) in enumerate(zip(bands, labels)):
        y = pad + i * (bh + header_h + pad)
        d.text((pad + 4, y + 4), lbl, fill=(230, 230, 230))
        sheet.paste(b, (pad, y + header_h))
        d.rectangle((pad - 1, y + header_h - 1, pad + bw, y + header_h + bh), outline=(60, 56, 52))
    return sheet


def process_look(look, num_variants=6, seed=32026, reuse=False):
    print(f"\n=== Processing Look: {look.upper()} ===")
    bands = []
    labels = []
    for v in range(num_variants):
        tag = f"{look}_v{v}"
        cached = LANE / f"{tag}_period.png"
        glb = PROC / f"floor_band_{look}_v{v}.glb"
        if reuse and cached.is_file():
            print(f"  reusing cached {cached}")
            patch = Image.open(cached).convert("RGB")
        else:
            if not glb.is_file():
                raise FileNotFoundError(f"GLB not found: {glb}")
            print(f"Rendering {tag} from {glb}...")
            im = render_exact(glb, tag, expect_w=480, width=_CALIBRATED_WIDTH)
            patch = crop_period(im, 480, 128)
            patch.save(cached)
            print(f"  saved cropped band {cached} ({patch.size})")
        bands.append(patch)
        labels.append(f"Variante {v} (seed {seed + v * 1007})")

    # 1. Sheet of all variants
    sheet = compose_sheet(bands, labels)
    sheet_path = LANE / f"variants_{look}_sheet.png"
    sheet.save(sheet_path)
    print(f"Saved sheet: {sheet_path} ({sheet.size})")

    # 2. Composed 1152px lane
    lane_raw, seq = compose_lane_variants(bands, height=1152, seed=seed)
    lane_finished = finish(lane_raw, f"Hibrido {look.upper()} ({num_variants} var, {len(seq)} bandas)")
    lane_path = LANE / f"variants_{look}.png"
    lane_finished.save(lane_path)
    print(f"Saved composed lane: {lane_path} ({lane_finished.size})")
    return lane_path, sheet_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--look", choices=["w05", "v04", "both"], default="both")
    parser.add_argument("--variants", type=int, default=6)
    parser.add_argument("--seed", type=int, default=32026)
    parser.add_argument("--reuse", action="store_true", help="Reuse existing rendered period PNGs")
    args = parser.parse_args()

    looks = ["w05", "v04"] if args.look == "both" else [args.look]
    for lk in looks:
        process_look(lk, num_variants=args.variants, seed=args.seed, reuse=args.reuse)


if __name__ == "__main__":
    main()
