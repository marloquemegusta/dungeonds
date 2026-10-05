#!/usr/bin/env python3
"""
bake_dungeon_iso.py - Bakes the Dreadhollow modular pieces into 2:1 dimetric
sprites for DungeonDS, using the shared look defined in ds_look.py.

Usage:
    python tools/bake_dungeon_iso.py --preset e30
    python tools/bake_dungeon_iso.py --preset e60

Outputs to assets/dungeon_<preset>/:
    F*_*.png   32xTILE_H  floor diamonds (transparent corners)
    <obj>.png         upright walls / pillars / arches, transparent otherwise
    <obj>_shadow.png  128x128 separate Cycles shadow-catcher pass

Anchor contract (shared with source/main.c):
    the world ground origin (0,0,0) projects to the CENTRE of every sprite, so
    a sprite's centre is its ground point on the tile.
"""

import os
import sys
import math
import argparse
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GLB_DIR = r"C:\codexlocal\dungeonds\assets\environment\dreadhollow\GLB"
BASE_OUT = r"C:\codexlocal\dungeonds\assets"
ROOT = r"C:\codexlocal\dungeonds"

SAMPLES = 48

# The source kit is authored around 2.4 m walls. The game scale is deliberately
# explicit: floor tiles are 2x2 m and the main dungeon walls/arches are 3 m.
WALL_HEIGHT_M = 3.0
SOURCE_WALL_HEIGHT_M = 2.4
SOURCE_ARCH_HEIGHT_M = 2.77
NATIVE_PIVOT = "native-pivot"
BOUNDS_CENTER = "bounds-center"

# (output_name, glb_file, kind, z_rotation_deg)
JOBS = [
    ("F0_crypt", "001_crypt_flagstone.glb", "floor", 0),
    ("F1_obsidian", "002_split_obsidian_slab.glb", "floor", 0),
    ("F2_bone", "003_bone_inlay_tile.glb", "floor", 0),
    ("F3_crimson", "004_crimson_seal_tile.glb", "floor", 0),
    ("F4_worn", "009_worn_cobble_tile.glb", "floor", 0),

    ("WR_crypt", "021_crypt_wall.glb", "wall", 0),
    ("WC_crypt", "021_crypt_wall.glb", "wall", 90),
    ("WR_buttress", "022_buttressed_wall.glb", "wall", 0),
    ("WC_buttress", "022_buttressed_wall.glb", "wall", 90),
    ("WR_ossuary", "023_ossuary_wall.glb", "wall", 0),
    ("WC_ossuary", "023_ossuary_wall.glb", "wall", 90),

    ("P_soul", "068_soul_lantern_pillar.glb", "prop", 0),
    ("P_broken", "070_broken_pillar.glb", "prop", 0),
    ("AR_row", "078_ruined_lancet_arch.glb", "prop", 0),
    ("AR_col", "078_ruined_lancet_arch.glb", "prop", 90),
]

SCRIPT = r'''
import bpy, math, os, mathutils

GLB = r"{glb}"
NAME = "{name}"
KIND = "{kind}"
ZROT = {zrot}
RW = {rw}
RH = {rh}
SAMPLES = {samples}
OUT = r"{out}"
WALL_HEIGHT_M = {wall_height_m}
SOURCE_WALL_HEIGHT_M = {source_wall_height_m}
SOURCE_ARCH_HEIGHT_M = {source_arch_height_m}
ANCHOR_MODE = "{anchor_mode}"
SPRITE_ONLY = {sprite_only}
SHADOW_RES = {shadow_res}
PX_PER_M = {px_per_m}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

# Scale architecture around its ground contact, not around the sprite canvas.
# Origins in this kit are at floor level, so Z-only object scaling preserves the
# foot position while making the physical height match the design scale.
if NAME.startswith(('WR_', 'WC_')) or NAME in ('P_soul', 'AR_row', 'AR_col'):
    source_h = SOURCE_ARCH_HEIGHT_M if NAME.startswith('AR_') else SOURCE_WALL_HEIGHT_M
    factor = WALL_HEIGHT_M / source_h
    for o in meshes:
        o.scale.z *= factor

if NAME.startswith("P_soul"):
    for mat in bpy.data.materials:
        tree = getattr(mat, 'node_tree', None)
        if tree:
            bsdf = tree.nodes.get('Principled BSDF')
            em_tex = [n for n in tree.nodes if n.type == 'TEX_IMAGE' and 'emission' in getattr(n.image, 'name', '').lower()]
            if em_tex and bsdf:
                mult = tree.nodes.new('ShaderNodeVectorMath')
                mult.operation = 'MULTIPLY'
                mult.inputs[1].default_value = (0.05, 0.60, 1.8)
                tree.links.new(em_tex[0].outputs['Color'], mult.inputs[0])
                tree.links.new(mult.outputs['Vector'], bsdf.inputs['Emission Color'])
                bsdf.inputs['Emission Strength'].default_value = 3.5


pts = []
for o in meshes:
    for c in o.bound_box:
        pts.append(o.matrix_world @ mathutils.Vector(c))

if KIND == "floor":
    # Sink the slab so its top face lies on the ground plane (z = 0).
    zmax = max(p.z for p in pts)
    for o in meshes:
        o.location.z -= zmax
elif ANCHOR_MODE == "bounds-center":
    # One deterministic anchor for every prop: centre of the complete ground
    # footprint, with the lowest contact point at z=0. Source asset origins
    # are not consistent (especially the pillars), so never use them as the
    # sprite anchor. This also makes a wall's anchor the centre of its whole
    # bottom edge rather than an arbitrary mesh origin.
    min_x = min(p.x for p in pts); max_x = max(p.x for p in pts)
    min_y = min(p.y for p in pts); max_y = max(p.y for p in pts)
    min_z = min(p.z for p in pts)
    anchor_x = (min_x + max_x) * 0.5
    anchor_y = (min_y + max_y) * 0.5
    for o in meshes:
        o.matrix_world.translation.x -= anchor_x
        o.matrix_world.translation.y -= anchor_y
        o.matrix_world.translation.z -= min_z
elif KIND == "wall":
    # Dreadhollow declares a ground-placement pivot and 2 m standard wall
    # modules. Preserve that authored pivot: it is the modular interface,
    # whereas a decorative buttress changes the visual bounding box.
    span_x = max(p.x for p in pts) - min(p.x for p in pts)
    span_y = max(p.y for p in pts) - min(p.y for p in pts)
    length = max(span_x, span_y)
    if abs(length - 2.0) > 0.05:
        raise RuntimeError("%s is not a 2 m wall module: %.3f m" % (NAME, length))
    print("MODULAR_NATIVE_PIVOT", NAME, "length=%.3f" % length,
          "ground=%.3f" % min(p.z for p in pts))

if ZROT:
    # Rotate the normalized asset around its shared ground anchor, not around
    # each source object's possibly-offset origin.
    pivot = bpy.data.objects.new('GroundAnchor', None)
    scene_collection = bpy.context.scene.collection
    scene_collection.objects.link(pivot)
    for o in meshes:
        world_matrix = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_world = world_matrix
    pivot.rotation_euler.z = math.radians(ZROT)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = RW
scene.render.resolution_y = RH

target = bpy.data.objects.new('T', None)
target_z = {anchor_z}
target.location = (0.0, 0.0, target_z)
scene.collection.objects.link(target)

{world}

{camera}

{lights}

if not SPRITE_ONLY:
    scene.render.filepath = os.path.join(OUT, NAME + ".png")
    bpy.ops.render.render(write_still=True)

# Save a separate shadow-catcher pass. The catcher mask stays independent of
# the floor texture so the compositor can shade whatever tile is underneath.
if KIND != "floor":
    bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
    catcher = bpy.context.object
    catcher.name = "GroundShadowCatcher"
    catcher.is_shadow_catcher = True
    scene.view_layers[0].cycles.use_pass_shadow_catcher = True
    scene.render.resolution_x = SHADOW_RES
    scene.render.resolution_y = SHADOW_RES
    cam.data.ortho_scale = SHADOW_RES / PX_PER_M
    matte = bpy.data.materials.new("ShadowCatcherMatte")
    matte.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    catcher.data.materials.append(matte)
    for obj in meshes:
        obj.visible_camera = False
    shadow_tree = bpy.data.node_groups.new("ShadowPassCompositor", "CompositorNodeTree")
    shadow_tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = shadow_tree
    scene.render.use_compositing = True
    nodes = shadow_tree.nodes
    nodes.clear()
    layers = nodes.new("CompositorNodeRLayers")
    layers.scene = scene
    layers.layer = scene.view_layers[0].name
    composite = nodes.new("NodeGroupOutput")
    shadow_pass = layers.outputs.get("Shadow Catcher")
    if shadow_pass is None:
        raise RuntimeError("Cycles did not expose the Shadow Catcher render pass")
    shadow_tree.links.new(shadow_pass, composite.inputs["Image"])
    scene.render.filepath = os.path.join(OUT, NAME + "_shadow.png")
    bpy.ops.render.render(write_still=True)
print("BAKED", NAME)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(look.PRESETS), default="e30")
    ap.add_argument("--wall-style", choices=("normal", "swap", "reverse"), default="normal")
    ap.add_argument("--only-walls", action="store_true")
    ap.add_argument("--orientation-sheet", action="store_true")
    ap.add_argument("--all-orientations", action="store_true")
    ap.add_argument("--shadow-only", action="store_true",
                    help="Bake only separate 3D shadow-catcher masks; preserve visible sprites")
    ap.add_argument("--anchor-mode", choices=(NATIVE_PIVOT, BOUNDS_CENTER),
                    default=BOUNDS_CENTER)
    args = ap.parse_args()

    elev = look.elevation(args.preset)
    tile_h = look.tile_h(args.preset)
    out_dir = (os.path.join(ROOT, "artifacts", f"orientations_{args.preset}")
               if args.orientation_sheet else
               os.path.join(BASE_OUT, f"dungeon_{args.preset}"))
    os.makedirs(out_dir, exist_ok=True)
    print(f"[preset {args.preset}] elevation={elev} floor_tile=32x{tile_h} -> {out_dir}")

    from PIL import Image

    jobs = [job for job in JOBS if not args.only_walls or job[2] == "wall"]
    if args.orientation_sheet:
        jobs = [(f"{name}_r{rot:03d}", glb, kind, rot)
                for name, glb, kind, _ in jobs if kind != "floor"
                for rot in (0, 90, 180, 270)]
    elif args.all_orientations:
        expanded = []
        for name, glb, kind, zrot in jobs:
            if kind == "floor":
                expanded.append((name, glb, kind, zrot))
            else:
                for rot in (0, 90, 180, 270):
                    expanded.append((f"{name}_r{rot:03d}", glb, kind, zrot + rot))
        jobs = expanded
    for name, glb, kind, zrot in jobs:
        if kind == "wall":
            if args.wall_style == "swap":
                zrot = 90 - zrot
            elif args.wall_style == "reverse":
                zrot = (zrot + 180) % 360
        if kind == "floor":
            rw, rh = look.FLOOR_TILE_W, tile_h
        else:
            rw, rh = look.OBJ_CANVAS, look.OBJ_CANVAS

        script = SCRIPT.format(
            glb=os.path.join(GLB_DIR, glb), name=name, kind=kind, zrot=zrot,
            rw=rw, rh=rh, samples=SAMPLES, out=out_dir,
            wall_height_m=WALL_HEIGHT_M,
            source_wall_height_m=SOURCE_WALL_HEIGHT_M,
            source_arch_height_m=SOURCE_ARCH_HEIGHT_M,
            anchor_mode=args.anchor_mode,
            sprite_only=args.shadow_only,
            shadow_res=128,
            px_per_m=look.PIXELS_PER_METRE,
            anchor_z=0.0 if kind == "floor" else look.GROUND_ANCHOR_Z,
            world=look.blender_world_snippet(),
            camera=look.blender_camera_snippet(rw, rh, elev, 0.0 if kind == "floor" else look.GROUND_ANCHOR_Z),
            lights=look.blender_lights_snippet(),
        )
        tmp = os.path.join(out_dir, "tmp_bake.py")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(script)
        try:
            p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp],
                               capture_output=True, text=True)
            if "BAKED" not in p.stdout:
                print(p.stdout[-900:]); print(p.stderr[-900:])
                raise RuntimeError(f"Blender failed for {name}")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        png = os.path.join(out_dir, name + ".png")
        if not args.shadow_only:
            img = look.grade(Image.open(png).convert("RGBA"))
            img.save(png)
        print(f"[OK] {name} ({rw}x{rh})")

    print("Environment bake complete.")


if __name__ == "__main__":
    main()
