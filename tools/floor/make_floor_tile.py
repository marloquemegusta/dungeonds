#!/usr/bin/env python3
"""Create deterministic floor GLB variants and lab preview grids at 3 texture scales."""
import argparse
import json
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
WORKER = ROOT / "tools/floor/blender_floor_tile.py"
PREP = ROOT / "tools/floor/prepare_floor_texture.py"
SOURCE = ROOT / "assets/environment/nomansland/textures/suelo_mixto.png"
OUT = ROOT / "assets/models/environment/floor_proto"
TASKS = OUT / "tasks"
TILE_W = TILE_H = 32 / 40.42  # make_arena_glb.py: TILE_W=32, TILE_H=16 screen px (32x32 ground px)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--world-span", type=float, choices=(2, 4, 8), required=True)
    p.add_argument("--tile-w", type=float, default=TILE_W)
    p.add_argument("--tile-h", type=float, default=TILE_H)
    p.add_argument("--seed", type=int, default=32026)
    p.add_argument("--count", type=int, default=12)
    p.add_argument("--skip-render", action="store_true", help="generate GLBs without launching Chromium")
    p.add_argument("--relief", type=float, default=.03, help="max displacement in metres")
    p.add_argument("--height-blur", type=float, default=1.4)
    p.add_argument("--tag", default="", help="suffix for the preview PNG, to compare variants")
    p.add_argument("--light", default="", help="key,fill,world overrides, e.g. 3,0.3,0.2")
    p.add_argument("--saturation", type=float, default=None)
    args = p.parse_args()
    if args.count != 12:
        raise SystemExit("El render de aceptación requiere --count 12 (rejilla 4x3).")
    OUT.mkdir(parents=True, exist_ok=True)
    TASKS.mkdir(parents=True, exist_ok=True)
    source_dir = OUT / "source"
    subprocess.run(["python", str(PREP), str(SOURCE), "--out-dir", str(source_dir), "--height-blur", str(args.height_blur)], check=True)
    color, height = source_dir / "albedo_tileable.png", source_dir / "height.png"
    rng = random.Random(args.seed + int(args.world_span))
    uv_w, uv_h = args.tile_w / args.world_span, args.tile_h / args.world_span
    tiles = []
    for i in range(args.count):
        u0 = rng.uniform(0, 1 - uv_w)
        v0 = rng.uniform(0, 1 - uv_h)
        tiles.append({"u0": u0, "v0": v0, "uv_w": uv_w, "uv_h": uv_h,
                      "tile_w": args.tile_w, "tile_h": args.tile_h, "relief": args.relief,
                      "out": str(OUT / f"floor_{int(args.world_span)}m_{i + 1:02d}.glb")})
    task = {"color": str(color), "height": str(height), "tiles": tiles,
            "grid_out": str(OUT / f"floor_grid_{int(args.world_span)}m.glb")}
    task_path = TASKS / f"floor_{int(args.world_span)}m.json"
    task_path.write_text(json.dumps(task, indent=2), encoding="utf-8")
    subprocess.run([str(BLENDER), "--background", "--python", str(WORKER), "--", str(task_path)], check=True)
    if args.skip_render:
        print(task["grid_out"])
        return
    # Keep the kit's 30-degree camera grade and neutral light, then render at
    # 40 px/m (the 4x grid is about 3.2 m wide) and enlarge only for inspection.
    settings_path = TASKS / f"lab_{int(args.world_span)}m.json"
    settings = json.loads((ROOT / "assets/sprites/arenas/strip_kit/map_settings.json").read_text(encoding="utf-8"))
    settings.update({"mapName": f"floor_proto_{int(args.world_span)}m", "width": 128,
                     "height": 100, "pixelsPerMeter": 40.42, "shadows": True, "waitTextures": True})
    if args.light:
        k, f, w = (float(x) for x in args.light.split(","))
        settings["lighting"] = dict(settings.get("lighting", {}), preset="custom", key=k, fill=f, world=w)
    if args.saturation is not None:
        settings["saturation"] = args.saturation
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    package_dir = TASKS / f"render_{int(args.world_span)}m"
    subprocess.run(["node", str(ROOT / "tools/lab/export_map_package_headless.cjs"),
                    task["grid_out"], str(settings_path), str(package_dir)], check=True)
    preview = Image.open(package_dir / "world.png").convert("RGB")
    preview = preview.resize((preview.width * 4, preview.height * 4), Image.Resampling.NEAREST)
    name = "floor_proto_grid.png" if args.world_span == 4 else f"floor_proto_grid_{int(args.world_span)}m.png"
    if args.tag:
        name = f"floor_proto_grid_{int(args.world_span)}m_{args.tag}.png"
    preview.save(ROOT / "walkthroughs/v032-escenario/assets" / name)
    print(task["grid_out"])


if __name__ == "__main__":
    main()
