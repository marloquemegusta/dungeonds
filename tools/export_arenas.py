"""Regenerates the arena map packages with one command.

    python.exe tools/export_arenas.py [dungeon_01 ...]

1. tools/make_arena_glb.py builds assets/models/environment/arenas/<name>.glb
   (+ .frame.json with the lab render size and the crop offset).
2. The real tools/lab/export_map_package_headless.cjs renders each model with the
   lab (headless Chromium via Playwright) at 40.42 px/m. The lab frames a model
   by its world AABB, so the render is larger than the arena; see
   make_arena_glb.py for why.
3. The package is cropped to the arena image size (crop offsets are multiples of
   the 4 px collision cell, so the grid stays aligned) and written to
   assets/sprites/arenas/<name>/. occlusion_depth.png stores ground-contact Y
   in image pixels, so its Y is shifted by the crop offset.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_arena_glb  # noqa: E402

LAB_EXPORT = ROOT / "tools/lab/export_map_package_headless.cjs"
OLD_SETTINGS = ROOT / "assets/sprites/dungeon/isometric_shooter_bl/map_settings.json"
MODELS = ROOT / "assets/models/environment/arenas"
OUT = ROOT / "assets/sprites/arenas"
CELL = 4


def write_json(path, data, indent=2):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=indent)
        fh.write("\n")


def crop_png(src, dst, box, mode=None):
    img = Image.open(src)
    img = img.convert(mode) if mode else img
    img.crop(box).save(dst)


ACCENT_RGB = {"cyan": (60, 220, 255), "magenta": (255, 60, 200), "amber": (255, 170, 40)}
SHADOW_TINT = (0.60, 0.62, 0.74)       # multiplies the floor colour inside a baked shadow
GLOW_BANDS = ((0, 8, 0.14), (8, 16, 0.08))   # (from, to, strength) south of a wall's shadow


def bake_light(world_png, occlusion_png, arena, spec, size_w, size_h):
    """Bakes neon glow (baked_glow) and, optionally, drawn contact shadows (baked_shadows) onto the
    floor of the lab render (DESIGN.md 5). The shadows normally come from the lab's own key light
    ("shadows": true, widened shadow camera in export_map_package_headless.cjs), so they match the
    characters; baked_shadows is the fallback that draws them from the spec instead: light from the north-west, so every block throws an L shaped shadow
    to its east and south (multiples of 8 px so the tile budget survives). Floor only: pixels
    of walls and pillars (the occlusion mask) and the block footprints stay as rendered. Each
    wall also lights the floor in front of it with its zone accent in three flat bands."""
    img = np.array(Image.open(world_png).convert("RGB"), dtype=np.float64)
    solid = np.array(Image.open(occlusion_png).convert("L")) > 0
    floor = ~solid
    fx0, fy0, fx1, fy1 = spec["floor"]["rect"]
    ppm = spec["pixels_per_metre"]
    for b in arena["blocks"]:
        x0, y0, x1, y1 = b["rect"]
        floor[y0:y1, x0:x1] = False
    shadow = np.zeros_like(floor)

    def add(mask, x0, y0, x1, y1):
        mask[max(y0, 0):min(y1, size_h), max(x0, 0):min(x1, size_w)] = True

    es = 8
    for b in arena["blocks"]:
        x0, y0, x1, y1 = b["rect"]
        ex = 8 * max(1, round(b["height_m"] * ppm * 0.25 / 8))
        add(shadow, x1, y0 + es, x1 + ex, y1 + es)
        add(shadow, x0, y1, x1 + ex, y1 + es)
    add(shadow, fx0, fy0 + es, fx0 + 24, fy1)          # west boundary wall
    add(shadow, fx0, fy0, fx1, fy0 + es)               # north boundary wall
    shadow &= floor

    glow = np.zeros(floor.shape + (4,))                # rgb of the accent + strength
    for b in arena["blocks"]:
        if b.get("kind") != "wall":
            continue
        x0, y0, x1, y1 = b["rect"]
        if (x1 - x0) < (y1 - y0):
            continue                                   # only horizontal walls show a neon strip to the south
        cx, cy = (x0 + x1) // 2, y1 + es
        accent = next((z["accent"] for z in arena["zones"]
                       if z["rect"][0] <= cx < z["rect"][2] and z["rect"][1] <= cy < z["rect"][3]), None)
        if accent not in ACCENT_RGB:
            continue
        for a, c, k in GLOW_BANDS:
            ys, ye = y1 + es + a, y1 + es + c
            sl = (slice(max(ys, 0), min(ye, size_h)), slice(max(x0, 0), min(x1, size_w)))
            glow[sl[0], sl[1], :3] = ACCENT_RGB[accent]
            glow[sl[0], sl[1], 3] = k
    lit = floor & ~shadow & (glow[:, :, 3] > 0)
    for ch in range(3):
        c = img[:, :, ch]
        c[lit] = c[lit] * (1 - glow[:, :, 3][lit]) + glow[:, :, ch][lit] * glow[:, :, 3][lit]
        if spec.get("baked_shadows"):
            c[shadow] *= SHADOW_TINT[ch]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(world_png)


def export_arena(name, spec):
    frame = json.loads((MODELS / f"{name}.frame.json").read_text(encoding="utf-8"))
    size_w, size_h = frame["image"]
    cx, cy, big_w, big_h = frame["cx"], frame["cy"], frame["map_w"], frame["map_h"]
    ppm = spec["pixels_per_metre"]
    old = json.loads(OLD_SETTINGS.read_text(encoding="utf-8"))
    old = dict(old, lighting=dict(old["lighting"], **spec.get("lighting", {})))   # arenas.json may retune the lab lighting
    lab_settings = dict(old, mapName=name, width=big_w, height=big_h,
                        orthoScaleMeters=big_w / ppm, pixelsPerMeter=ppm, shadows=bool(spec.get("shadows", False)))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        write_json(tmp / "lab_settings.json", lab_settings)
        raw = tmp / "raw"
        subprocess.run(["node", str(LAB_EXPORT), str(MODELS / f"{name}.glb"),
                        str(tmp / "lab_settings.json"), str(raw)], check=True)
        out = OUT / name
        out.mkdir(parents=True, exist_ok=True)
        box = (cx, cy, cx + size_w, cy + size_h)
        crop_png(raw / "world.png", out / "world.png", box, "RGB")
        crop_png(raw / "collision.png", out / "collision.png", box, "L")
        crop_png(raw / "occlusion.png", out / "occlusion.png", box, "L")
        if spec.get("baked_shadows") or spec.get("baked_glow"):
            arena = next(a for a in spec["arenas"] if a["name"] == name)
            bake_light(out / "world.png", out / "occlusion.png", arena, spec, size_w, size_h)

        occ = np.array(Image.open(raw / "occlusion_depth.png").convert("RGB"), dtype=np.int32)
        occ = occ[cy:cy + size_h, cx:cx + size_w].copy()
        flag = occ[:, :, 2] >= 128
        ground = occ[:, :, 0] * 256 + occ[:, :, 1] - cy
        if flag.any() and int(ground[flag].min()) < 0:
            raise SystemExit(f"{name}: occluder with ground contact above the crop")
        occ[:, :, 0] = np.where(flag, ground >> 8, 0)
        occ[:, :, 1] = np.where(flag, ground & 255, 0)
        Image.fromarray(occ.astype(np.uint8), "RGB").save(out / "occlusion_depth.png")

        col = json.loads((raw / "collision.json").read_text(encoding="utf-8"))
        gx0, gy0, gw, gh = cx // CELL, cy // CELL, size_w // CELL, size_h // CELL
        col.update(mapName=name, mapWidth=size_w, mapHeight=size_h, gridWidth=gw, gridHeight=gh,
                   walkableGrid=[row[gx0:gx0 + gw] for row in col["walkableGrid"][gy0:gy0 + gh]])
        write_json(out / "collision.json", col)

        settings = {
            "mapName": name, "width": size_w, "height": size_h,
            "orthoScaleMeters": size_w / ppm, "pixelsPerMeter": ppm,
            "meshScale": old["meshScale"], "cameraElevationDegrees": 30,
            "contrast": old["contrast"], "saturation": old["saturation"],
            "brightness": old["brightness"], "lighting": old["lighting"], "shadows": bool(spec.get("shadows", False)),
            "labRender": {"width": big_w, "height": big_h, "cropX": cx, "cropY": cy,
                          "note": "rendered by the lab at pixelsPerMeter, then cropped to the arena"},
        }
        write_json(out / "map_settings.json", settings)
    print(f"{name}: {OUT / name}")


def main():
    make_arena_glb.main()
    spec = json.loads(make_arena_glb.SPEC.read_text(encoding="utf-8"))
    wanted = set(sys.argv[1:])
    if OUT.exists() and not wanted:
        shutil.rmtree(OUT)
    for arena in spec["arenas"]:
        if not wanted or arena["name"] in wanted:
            export_arena(arena["name"], spec)


if __name__ == "__main__":
    main()
