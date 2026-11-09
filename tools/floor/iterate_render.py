#!/usr/bin/env python3
"""One-shot loop step for agents: (optionally regenerate the floor) -> render in the lab -> PNG.

Usage (from the worktree root):
  python tools/floor/iterate_render.py --tag v01 [-- <args for make_proc_floor.py>]

With `--` and extra args it first runs tools/floor/make_proc_floor.py with them; without it
it renders the existing GLB. It writes
  assets/models/environment/floor_proc/iter/<tag>_lab4x.png   (lab render, 4x nearest-neighbour)
and prints that path plus the render size. Look at the PNG, judge it against the brief, edit
the generator, and run this again with a new --tag.
"""
import argparse
import copy
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "assets/models/environment/floor_proc"
ITER = PROC / "iter"
LAB = ROOT / "tools/lab/export_map_package_headless.cjs"


def tile_glb(src, dst, nx=2, nz=2):
    """Write a GLB with the patch repeated nx x nz times (glTF is Y-up: the floor spans X and Z).

    The period is read from the mud mesh POSITION bounds. If a seam is visible in the render of
    this file, the patch is not really tileable.
    """
    data = src.read_bytes()
    jl = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + jl])
    rest = data[20 + jl:]
    bounds = None
    for mesh in gltf["meshes"]:
        if "mud" in mesh.get("name", "").lower():
            acc = gltf["accessors"][mesh["primitives"][0]["attributes"]["POSITION"]]
            lo, hi = np.array(acc["min"]), np.array(acc["max"])
            bounds = (hi[0] - lo[0], hi[2] - lo[2])
    if bounds is None:
        raise SystemExit("tile_glb: no mud mesh found to measure the period")
    px, pz = bounds
    nodes = gltf["nodes"]
    scene = gltf["scenes"][gltf.get("scene", 0)]
    roots = list(scene["nodes"])
    n0 = len(nodes)
    new_roots = list(roots)
    for ix in range(nx):
        for iz in range(nz):
            if ix == 0 and iz == 0:
                continue
            off = len(nodes) - n0 + n0
            mapping = {}
            def clone(i):
                node = copy.deepcopy(nodes[i])
                idx = len(nodes)
                mapping[i] = idx
                nodes.append(node)
                node["children"] = [clone(c) for c in node.get("children", [])] or None
                if node["children"] is None:
                    del node["children"]
                return idx
            for r in roots:
                ri = clone(r)
                t = nodes[ri].get("translation", [0, 0, 0])
                nodes[ri]["translation"] = [t[0] + ix * px, t[1], t[2] + iz * pz]
                if "matrix" in nodes[ri]:
                    m = nodes[ri]["matrix"]
                    m[12] += ix * px; m[14] += iz * pz
                new_roots.append(ri)
    scene["nodes"] = new_roots
    jb = json.dumps(gltf, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    total = 12 + 8 + len(jb) + len(rest)
    dst.write_bytes(data[:8] + struct.pack("<I", total) + struct.pack("<I", len(jb)) + data[16:20] + jb + rest)
    return px, pz


def main():
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--glb", type=Path, default=PROC / "floor_proc_patch.glb")
    p.add_argument("--width", type=int, default=320, help="lab render width in px (40.42 px/m)")
    p.add_argument("--wait-ms", type=int, default=12000, help="time for textures to decode before the final render")
    p.add_argument("--light", default="3,0.3,0.25", help="key,fill,world (lab lighting)")
    p.add_argument("--tile-check", choices=("y", "x", "xy"), default=None,
                   help="extra slow render (~3 min) repeating the patch along Y (the strip direction), X or both, to look for seams")
    args = p.parse_args(argv)
    if extra:
        subprocess.run([sys.executable, str(ROOT / "tools/floor/make_proc_floor.py"), *extra], check=True, cwd=ROOT)
    ITER.mkdir(parents=True, exist_ok=True)
    settings = json.loads((ROOT / "assets/sprites/arenas/strip_kit/map_settings.json").read_text(encoding="utf-8"))
    settings.pop("labRender", None)
    k, f, w = (float(x) for x in args.light.split(","))
    settings.update(width=args.width, height=args.width * 2 // 3, pixelsPerMeter=40.42, shadows=True,
                    waitTextures=True, waitTexturesMs=args.wait_ms, saturation=1.0,
                    lighting=dict(preset="custom", key=k, fill=f, world=w, rim=0))
    cfg = ITER / f"{args.tag}_lab.json"
    cfg.write_text(json.dumps(settings, indent=1), encoding="utf-8")
    pkg = ITER / f"{args.tag}_pkg"
    subprocess.run(["node", str(LAB), str(args.glb), str(cfg), str(pkg)], check=True, cwd=ROOT)
    img = Image.open(pkg / "world.png").convert("RGB")
    out = ITER / f"{args.tag}_lab4x.png"
    img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(out)
    print(f"LAB_RENDER={out} native={img.size}")
    if args.tile_check:
        nx, nz = {"y": (1, 2), "x": (2, 1), "xy": (2, 2)}[args.tile_check]
        tiled = ITER / f"{args.tag}_tile{nx}x{nz}.glb"
        px, pz = tile_glb(args.glb, tiled, nx, nz)
        cfg2 = ITER / f"{args.tag}_tile2x2_lab.json"
        s2 = dict(settings, width=args.width, height=args.width * 2 // 3, waitTexturesMs=4000)
        cfg2.write_text(json.dumps(s2, indent=1), encoding="utf-8")
        pkg2 = ITER / f"{args.tag}_tile2x2_pkg"
        subprocess.run(["node", str(LAB), str(tiled), str(cfg2), str(pkg2)], check=True, cwd=ROOT)
        im2 = Image.open(pkg2 / "world.png").convert("RGB")
        out2 = ITER / f"{args.tag}_tilecheck_lab3x.png"
        im2.resize((im2.width * 3, im2.height * 3), Image.NEAREST).save(out2)
        print(f"TILE_CHECK={out2} period_m=({px:.3f},{pz:.3f})  <- look for visible seams at the joins")


if __name__ == "__main__":
    main()
