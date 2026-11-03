"""Regenerates the v0.1 arena map packages with one command.

    python.exe tools/export_arenas.py [arena_01 ...]

1. tools/make_arena_glb.py builds assets/models/environment/arenas/arena_0N.glb
   (+ .frame.json with the lab render size and the crop offset).
2. The real tools/lab/export_map_package_headless.cjs renders each model with the
   lab (headless Chromium via Playwright) at 40.42 px/m. The lab frames a model
   by its world AABB, so the render is larger than the arena; see
   make_arena_glb.py for why.
3. The package is cropped to the 384x384 arena (crop offsets are multiples of
   the 4 px collision cell, so the grid stays aligned) and written to
   assets/sprites/arenas/arena_0N/. occlusion_depth.png stores ground-contact Y
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
SIZE = 384
CELL = 4


def write_json(path, data, indent=2):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=indent)
        fh.write("\n")


def crop_png(src, dst, box, mode=None):
    img = Image.open(src)
    img = img.convert(mode) if mode else img
    img.crop(box).save(dst)


def export_arena(name, spec):
    frame = json.loads((MODELS / f"{name}.frame.json").read_text(encoding="utf-8"))
    cx, cy, big_w, big_h = frame["cx"], frame["cy"], frame["map_w"], frame["map_h"]
    ppm = spec["pixels_per_metre"]
    old = json.loads(OLD_SETTINGS.read_text(encoding="utf-8"))
    lab_settings = dict(old, mapName=name, width=big_w, height=big_h,
                        orthoScaleMeters=big_w / ppm, pixelsPerMeter=ppm, shadows=False)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        write_json(tmp / "lab_settings.json", lab_settings)
        raw = tmp / "raw"
        subprocess.run(["node", str(LAB_EXPORT), str(MODELS / f"{name}.glb"),
                        str(tmp / "lab_settings.json"), str(raw)], check=True)
        out = OUT / name
        out.mkdir(parents=True, exist_ok=True)
        box = (cx, cy, cx + SIZE, cy + SIZE)
        crop_png(raw / "world.png", out / "world.png", box, "RGB")
        crop_png(raw / "collision.png", out / "collision.png", box, "L")
        crop_png(raw / "occlusion.png", out / "occlusion.png", box, "L")

        occ = np.array(Image.open(raw / "occlusion_depth.png").convert("RGB"), dtype=np.int32)
        occ = occ[cy:cy + SIZE, cx:cx + SIZE].copy()
        flag = occ[:, :, 2] >= 128
        ground = occ[:, :, 0] * 256 + occ[:, :, 1] - cy
        if flag.any() and int(ground[flag].min()) < 0:
            raise SystemExit(f"{name}: occluder with ground contact above the crop")
        occ[:, :, 0] = np.where(flag, ground >> 8, 0)
        occ[:, :, 1] = np.where(flag, ground & 255, 0)
        Image.fromarray(occ.astype(np.uint8), "RGB").save(out / "occlusion_depth.png")

        col = json.loads((raw / "collision.json").read_text(encoding="utf-8"))
        gx0, gy0, n = cx // CELL, cy // CELL, SIZE // CELL
        col.update(mapName=name, mapWidth=SIZE, mapHeight=SIZE, gridWidth=n, gridHeight=n,
                   walkableGrid=[row[gx0:gx0 + n] for row in col["walkableGrid"][gy0:gy0 + n]])
        write_json(out / "collision.json", col)

        settings = {
            "mapName": name, "width": SIZE, "height": SIZE,
            "orthoScaleMeters": SIZE / ppm, "pixelsPerMeter": ppm,
            "meshScale": old["meshScale"], "cameraElevationDegrees": 30,
            "contrast": old["contrast"], "saturation": old["saturation"],
            "brightness": old["brightness"], "lighting": old["lighting"], "shadows": False,
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
