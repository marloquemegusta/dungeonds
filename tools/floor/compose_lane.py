#!/usr/bin/env python3
"""Compose the real DS lane (512 px wide = 2 screens, N screens high) from each floor version.

Floors are viewed axis-aligned: the lab frames at azimuth 45 deg, so each GLB is yawed -45 deg first.
Periodic patches are cropped to one exact period and tiled; the 12 single-tile variant (version A) is
laid as a seeded random mosaic of 32x16 px tiles, the way the kit would use separate tiles.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_rotate import rotate_glb_y  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LANE = ROOT / "assets/models/environment/floor_proc/lane"
LAB = ROOT / "tools/lab/export_map_package_headless.cjs"
PPM = 40.42
WALL = (34, 30, 27)


def render(glb, tag, width=320, light=(3, .3, .25)):
    LANE.mkdir(parents=True, exist_ok=True)
    rot = LANE / f"{tag}_rot.glb"
    rotate_glb_y(glb, rot, -45)
    s = json.loads((ROOT / "assets/sprites/arenas/strip_kit/map_settings.json").read_text(encoding="utf-8"))
    s.pop("labRender", None)
    s.update(width=width, height=width * 2 // 3, pixelsPerMeter=PPM, orthoScaleMeters=width / PPM, shadows=True,
             waitTextures=True, waitTexturesMs=14000, saturation=1.0,
             lighting=dict(preset="custom", key=light[0], fill=light[1], world=light[2], rim=0))
    cfg = LANE / f"{tag}_lab.json"
    cfg.write_text(json.dumps(s, indent=1), encoding="utf-8")
    pkg = LANE / f"{tag}_pkg"
    subprocess.run(["node", str(LAB), str(rot), str(cfg), str(pkg)], check=True, cwd=ROOT)
    return Image.open(pkg / "world.png").convert("RGB")


def render_exact(glb, tag, expect_w, width=320, light=(3, .3, .25)):
    """The lab sets the scale from the model's world AABB, not from the settings: measure the floor
    width in a first pass and re-render at the map size that gives exactly 40.42 px/m."""
    im = render(glb, tag, width, light)
    x0, _, x1, _ = floor_bbox(im)
    w2 = round(width * expect_w / (x1 - x0))
    print(f"  pass 1: floor {x1 - x0}px at width {width} -> re-render at width {w2}")
    return render(glb, tag, w2, light)


def floor_bbox(img, frac=.5):
    m = np.asarray(img).max(axis=2) > 10
    cols, rows = m.mean(0), m.mean(1)
    xs = np.where(cols > frac * cols.max())[0]
    ys = np.where(rows > frac * rows.max())[0]
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1


def crop_period(img, pw, ph):
    x0, y0, x1, y1 = floor_bbox(img)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    print(f"  floor bbox {x1 - x0}x{y1 - y0} (expected {pw}x{ph})")
    return img.crop((x0, y0, x1, y1)).resize((pw, ph), Image.LANCZOS)


def lane_from_patch(patch, H):
    pw, ph = patch.size
    img = Image.new("RGB", (512, H), WALL)
    x = 256 - pw // 2
    while x > -pw:
        x -= pw
    for xx in range(x, 512, pw):
        for yy in range(0, H, ph):
            img.paste(patch, (xx, yy))
    return img


def lane_from_tiles(tiles, H, seed=7):
    rng = random.Random(seed)
    img = Image.new("RGB", (512, H), WALL)
    cols, rows = 480 // 32, H // 16 + 1
    prev = [-1] * cols
    for r in range(rows):
        left = -1
        for c in range(cols):
            k = rng.randrange(len(tiles))
            while k == prev[c] or k == left:
                k = rng.randrange(len(tiles))
            prev[c] = left = k
            img.paste(tiles[k], (16 + c * 32, r * 16))
    return img


def finish(img, label):
    """Side walls, hero and enemies for scale, and one DS screen outline (256x192)."""
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 15, img.height), fill=WALL)
    d.rectangle((496, 0, 511, img.height), fill=WALL)
    chars = ROOT / "assets/sprites/characters"
    def put(name, x, ground_y, flip=False):
        sp = Image.open(chars / name / "frames/4_N/0.png").convert("RGBA")
        bb = sp.getbbox()
        img.paste(sp, (x - 20, ground_y - 34), sp)
    H = img.height
    put("marine", 256, H // 2 + 60)
    put("skeleton", 200, H // 2 - 20)
    put("skeleton", 300, H // 2 - 50)
    put("charger", 250, H // 2 - 110)
    y0 = H // 2 - 96
    d.rectangle((128, y0, 383, y0 + 191), outline=(255, 255, 255))
    d.text((132, y0 + 3), "1 pantalla DS 256x192", fill=(255, 255, 255))
    return img


def main():
    H = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1152
    out = {}
    # version A: 12 individual tiles (4x3 grid, no gap)
    print("A tiles"); g = render_exact(ROOT / "assets/models/environment/floor_proto/floor_grid_4m.glb", "A_grid", 128, width=200)
    x0, y0, x1, y1 = floor_bbox(g); print(f"  grid bbox {x1 - x0}x{y1 - y0} (expected 128x48)")
    yo = y0 + (y1 - y0 - 48) // 2; g = g.crop((x0, yo, x0 + 128, yo + 48))
    tiles = [g.crop((c * 32, r * 16, c * 32 + 32, r * 16 + 16)) for r in range(3) for c in range(4)]
    out["A: 12 baldosas sueltas (textura IA + altura)"] = lane_from_tiles(tiles, H)
    for tag, glb, label in (("v04", "floor_proc_patch_v04.glb", "Hibrido v04"), ("w05", "floor_proc_patch.glb", "Hibrido w05")):
        cached = LANE / f"{tag}_period.png"
        if "reuse" in sys.argv and cached.exists():
            patch = Image.open(cached).convert("RGB"); print(tag, "reused")
        else:
            print(tag); im = render_exact(ROOT / "assets/models/environment/floor_proc" / glb, tag, 192)
            patch = crop_period(im, 192, 128)
            patch.save(cached)
        out[f"{label}: parche periodico repetido"] = lane_from_patch(patch, H)
    sheet = Image.new("RGB", (512 * len(out) + 16 * (len(out) + 1), H + 40), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (label, lane) in enumerate(out.items()):
        lane = finish(lane, label)
        lane.save(LANE / f"lane_{i}.png")
        x = 16 + i * (512 + 16)
        d.text((x, 12), label, fill=(255, 255, 255))
        sheet.paste(lane, (x, 36))
    sheet.save(LANE / "lane_comparison.png")
    print("OK", sheet.size)


if __name__ == "__main__":
    main()
