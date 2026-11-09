"""Generate a full-lane trench floor band with Blender."""
import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
WORKER = Path(__file__).with_name("proc_floor.py")
OUTPUT_DIR = ROOT / "assets/models/environment/floor_proc"
DEFAULT_MUD_IMAGE = ROOT / "assets/models/environment/floor_proto/source/albedo_tileable.png"


def inspect_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise RuntimeError("Invalid GLB header/length")
    json_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON":
        raise RuntimeError("GLB JSON chunk is missing")
    doc = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \0"))
    unsupported = set(doc.get("extensionsUsed", [])) | set(doc.get("extensionsRequired", []))
    if unsupported:
        raise RuntimeError("Unexpected glTF extensions: " + ", ".join(sorted(unsupported)))
    images = doc.get("images", [])
    if not images or any("bufferView" not in image for image in images):
        raise RuntimeError("GLB image data is not embedded in buffer views")
    tris = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if "indices" in primitive:
                accessor = doc["accessors"][primitive["indices"]]
                tris += accessor["count"] // 3
            else:
                accessor = doc["accessors"][primitive["attributes"]["POSITION"]]
                tris += accessor["count"] // 3
    texture_materials = sum(bool(m.get("pbrMetallicRoughness", {}).get("baseColorTexture")) for m in doc.get("materials", []))
    print(f"GLB valid: {tris:,} triangles; {len(doc.get('materials', []))} materials; {texture_materials} textured materials; embedded_images={len(images)}; extensions={doc.get('extensionsUsed', [])}")
    if not texture_materials:
        raise RuntimeError("No baseColorTexture found in exported materials")
    if any("COLOR_0" in primitive.get("attributes", {})
           for mesh in doc.get("meshes", []) for primitive in mesh.get("primitives", [])):
        raise RuntimeError("COLOR_0 found; lab consumes material base colors and textures only")
    if any("normalTexture" in material.get("pbrMetallicRoughness", {}) or "normalTexture" in material
           for material in doc.get("materials", [])):
        raise RuntimeError("Unexpected normal map in generated materials")
    return tris, len(doc.get("materials", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--look", choices=["w05", "v04"], default="w05",
                        help="Visual style: w05 (continuous, dark umber, intermediate wire) or v04 (rugged, high contrast, orange wire)")
    parser.add_argument("--variant", type=int, default=0,
                        help="Variant index 0..5 (changes object layer, keeps mud identical)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Variant seed (defaults to 32026 + variant * 1007)")
    parser.add_argument("--mud-seed", type=int, default=32026,
                        help="Fixed seed for mud base relief (identical across all variants)")
    parser.add_argument("--lane-width-m", type=float, default=11.88,
                        help="Lane width in meters (default 11.88 m = 480 px at 40.42 px/m)")
    parser.add_argument("--band-depth-m", type=float, default=6.336,
                        help="Band depth in meters along Y (default 6.336 m = 128 px on screen)")
    parser.add_argument("--spacing", type=float, default=0.024,
                        help="Vertex spacing for mud relief grid (default 0.024 m)")
    parser.add_argument("--mud-source", choices=["image", "procedural"], default="image",
                        help="Mud base color source: image (default) or procedural value-noise")
    parser.add_argument("--mud-image", type=Path, default=DEFAULT_MUD_IMAGE,
                        help="Tileable mud albedo image path for --mud-source image")
    parser.add_argument("--mud-tone", type=float, default=0.75,
                        help="Brightness tone multiplier for mud image (default 0.75)")
    parser.add_argument("--mud-desat", type=float, default=0.15,
                        help="Desaturation amount [0..1] for mud image (default 0.15)")
    parser.add_argument("--tex-span", type=float, default=3.168,
                        help="Texture repeat length in meters (default 3.168 = 4 tiles)")
    parser.add_argument("--debris", type=int, default=550,
                        help="Small stone/bone/brass/scrap count (default 550)")
    parser.add_argument("--puddles", type=int, default=6,
                        help="Puddle count (default 6)")
    parser.add_argument("--wire", type=int, default=5,
                        help="Barbed-wire tangles/runs (default 5)")
    parser.add_argument("--rags", type=int, default=2,
                        help="Faded cloth scraps (default 2)")
    parser.add_argument("--loose-planks", type=int, default=8,
                        help="Loose boards on the flanks (default 8)")
    parser.add_argument("--wood-variants", type=int, default=4,
                        help="Distinct atlas wood looks (2-4)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output GLB path")
    parser.add_argument("--blender", type=Path, default=BLENDER)

    # Legacy options for backward compatibility
    parser.add_argument("--patch-tiles-y", type=int, default=None)
    parser.add_argument("--patch-tiles-x", type=int, default=None)
    parser.add_argument("--planks", type=int, default=32)
    parser.add_argument("--walk-width", type=float, default=1.22)
    parser.add_argument("--walk-wander", type=float, default=0.18)
    parser.add_argument("--panel-length", type=float, default=1.20)
    parser.add_argument("--missing-chance", type=float, default=0.13)
    parser.add_argument("--mud-res", type=int, default=2048)

    args = parser.parse_args()

    if args.patch_tiles_x:
        args.lane_width_m = args.patch_tiles_x * 0.792
    if args.patch_tiles_y:
        args.band_depth_m = args.patch_tiles_y * 0.792

    if args.seed is None:
        args.seed = args.mud_seed + args.variant * 1007

    if not (0 <= args.variant <= 5):
        parser.error("Variant must be in range 0..5")
    if not (5.0 <= args.lane_width_m <= 20.0 and 2.0 <= args.band_depth_m <= 15.0):
        parser.error("Lane dimensions out of valid range")
    if not args.blender.is_file():
        raise SystemExit(f"Blender executable not found: {args.blender}")
    if args.mud_source == "image" and not args.mud_image.is_file():
        raise SystemExit(f"Mud image file not found: {args.mud_image}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output is None:
        glb_path = OUTPUT_DIR / f"floor_band_{args.look}_v{args.variant}.glb"
    else:
        glb_path = Path(args.output)

    mud_texture_path = OUTPUT_DIR / f"mud_albedo_{args.look}.png"
    if not mud_texture_path.is_file():
        img = Image.open(args.mud_image).convert("RGB")
        arr = np.asarray(img, dtype=np.float32)
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        arr = arr * (1.0 - args.mud_desat) + lum[:, :, None] * args.mud_desat
        arr = arr * args.mud_tone
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        Image.fromarray(arr).save(mud_texture_path, format="PNG")

    wood_texture_path = OUTPUT_DIR / f"wood_atlas_{args.look}_v{args.variant}.png"
    preview_path = OUTPUT_DIR / f"preview_{args.look}_v{args.variant}.png"

    task_path = OUTPUT_DIR / f".build_task_{os.getpid()}.json"
    task_path.write_text(json.dumps({
        "seed": args.seed,
        "mud_seed": args.mud_seed,
        "look": args.look,
        "variant": args.variant,
        "lane_width_m": args.lane_width_m,
        "band_depth_m": args.band_depth_m,
        "spacing": args.spacing,
        "mud_source": args.mud_source,
        "mud_image": str(args.mud_image),
        "mud_tone": args.mud_tone,
        "mud_desat": args.mud_desat,
        "tex_span": args.tex_span,
        "loose_planks": args.loose_planks,
        "debris": args.debris,
        "puddles": args.puddles,
        "wire": args.wire,
        "rags": args.rags,
        "wood_variants": args.wood_variants,
        "output": str(glb_path),
        "preview": str(preview_path),
        "wood_texture": str(wood_texture_path),
        "mud_texture": str(mud_texture_path),
    }), encoding="utf-8")

    cmd = [str(args.blender), "--background", "--python", str(WORKER), "--", str(task_path)]
    print("Running:", subprocess.list2cmdline(cmd))
    try:
        result = subprocess.run(cmd, cwd=ROOT, check=False)
    finally:
        task_path.unlink(missing_ok=True)

    if result.returncode != 0 or not glb_path.is_file():
        raise SystemExit(f"Blender failed (exit {result.returncode}); {glb_path} was not generated")
    tris, mats = inspect_glb(glb_path)
    return glb_path, tris, mats


if __name__ == "__main__":
    main()
