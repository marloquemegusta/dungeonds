#!/usr/bin/env python3
"""
bake_player.py - Bakes the animated player FBX into an 8-direction spritesheet
using the SAME look as the environment (tools/ds_look.py): identical lights,
identical elevation and identical world pixel scale, plus a baked cast shadow.

Usage:
    python tools/bake_player.py --preset e30
    python tools/bake_player.py --preset e60

Outputs: player_<preset>.png (512x512, 8x8 cells of 64px) and
         player_<preset>_shadow.png (8 facing masks, 96px cells).
Anchor contract: the ground origin projects to the CENTRE of each 64x64 cell.
"""

import os
import sys
import argparse
import subprocess
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
MODEL = r"C:\codexlocal\dungeonds\assets\characters\monster\Walking.fbx"
OUT_DIR = r"C:\codexlocal\dungeonds\assets\characters\monster"
CELL = look.CHAR_CANVAS
SHADOW_CELL = CELL * 3 // 2
NUM_DIRS = 8
NUM_FRAMES = 8
SAMPLES = 48

WORKER = r'''
import bpy, math, os, mathutils

MODEL = r"{model}"
OUT_DIR = r"{out_dir}"
CELL = {cell}
SHADOW_CELL = {shadow_cell}
NUM_DIRS = {dirs}
NUM_FRAMES = {frames}
SAMPLES = {samples}
PX_PER_M = {pxm}
TILE_W = {tile_w}
ANCHOR_Z = {anchor_z}
SCALE = {scale}
ELEV = {elev}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MODEL)

actions = list(bpy.data.actions)
act = actions[0] if actions else None
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if act:
    for arm in armatures:
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = act
    start_f = int(act.frame_range[0]); end_f = int(act.frame_range[1])
else:
    start_f = bpy.context.scene.frame_start; end_f = bpy.context.scene.frame_end

# Lock horizontal root motion so the walk cycle runs in place.
bpy.context.scene.frame_set(start_f)
for arm in armatures:
    for bone_name in ["mixamorig:Hips", "Hips", "root", "Root"]:
        if bone_name in arm.pose.bones:
            bone = arm.pose.bones[bone_name]
            c = bone.constraints.new(type='LIMIT_LOCATION')
            c.owner_space = 'LOCAL'
            c.use_min_x = c.use_max_x = True
            c.min_x = c.max_x = bone.location.x
            c.use_min_z = c.use_max_z = True
            c.min_z = c.max_z = bone.location.z
            break

# Use the imported armature origin as the stable world anchor. Its XY projection
# is the point the game places on the floor; each animation frame is grounded
# independently below so the support foot touches Z=0 throughout the cycle.
bpy.context.view_layer.update()
root_anchor = armatures[0].matrix_world.translation.copy() if armatures else mathutils.Vector((0.0, 0.0, 0.0))
print("ANCHOR_WORLD=%.6f,%.6f,%.6f" % tuple(root_anchor))

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = CELL
scene.render.resolution_y = CELL

# Ground point ends up at the centre of the cell. Keep the camera identical to
# the environment baker: the world is projected from azimuth 45 degrees.
target = bpy.data.objects.new('CamTarget', None)
target.location = (root_anchor.x, root_anchor.y, 0.0)
scene.collection.objects.link(target)

rig = bpy.data.objects.new('CameraRig', None)
rig.location = root_anchor
scene.collection.objects.link(rig)

# Rotate the character, not the camera. The previous version rotated only the
# camera rig, leaving the FBX outside the rig; its eight rows were therefore
# eight viewpoints of the same pose and did not agree with the walls.
for obj in [o for o in bpy.data.objects if o.type in {{'MESH', 'ARMATURE'}}]:
    world_matrix = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_world = world_matrix

cam_data = bpy.data.cameras.new('IsoCam')
cam_data.type = 'ORTHO'
# Preserve the shared world density in the 64x64 character viewport. Using
# the 32 px floor width here made the character twice as large as the floor.
cam_data.ortho_scale = CELL / (PX_PER_M * SCALE)
cam = bpy.data.objects.new('IsoCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

_el = math.radians(ELEV)
_dist = 30.0
_az = math.radians(45.0)
cam.location = (root_anchor.x + _dist * math.cos(_el) * math.cos(_az),
               root_anchor.y + _dist * math.cos(_el) * math.sin(_az),
               _dist * math.sin(_el))
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

{world}

{lights}

# Keep player and shadow in separate passes: the 3D shadow-catcher coverage is
# stored independently so the game can composite it onto the actual floor tile.
temp = os.path.join(OUT_DIR, "tmp_frames")
os.makedirs(temp, exist_ok=True)
shadow_temp = os.path.join(OUT_DIR, "tmp_player_shadows")
os.makedirs(shadow_temp, exist_ok=True)
total = max(1, end_f - start_f)
frame_indices = [int(start_f + (i * total) / NUM_FRAMES) for i in range(NUM_FRAMES)]

for d in range(NUM_DIRS):
    # Mixamo's default forward axis is -Y. Offset it toward the shared camera
    # (+X,+Y), then enumerate the eight world directions clockwise.
    rig.rotation_euler.z = math.radians(135.0 - d * 360.0 / NUM_DIRS)
    bpy.context.view_layer.update()
    for fi, fnum in enumerate(frame_indices):
        scene.frame_set(fnum)
        # Reset to the stable root anchor, measure evaluated geometry for this
        # pose, then lift/drop the complete rig so its lowest point meets the
        # floor. Using one cycle-wide minimum made most frames float.
        rig.location.z = root_anchor.z
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        lowest_z = 1e9
        for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
            ev = obj.evaluated_get(dg)
            for corner in ev.bound_box:
                lowest_z = min(lowest_z, (ev.matrix_world @ mathutils.Vector(corner)).z)
        rig.location.z = root_anchor.z - lowest_z
        bpy.context.view_layer.update()
        scene.render.filepath = os.path.join(temp, "d%02d_f%03d.png" % (d, fi))
        bpy.ops.render.render(write_still=True)

# One shadow per facing, sampled from the planted reference pose. The mask is
# static during an in-place walk; only its true 3D silhouette changes by facing.
bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
catcher = bpy.context.object
catcher.name = 'GroundShadowCatcher'
catcher.is_shadow_catcher = True
scene.view_layers[0].cycles.use_pass_shadow_catcher = True
scene.render.resolution_x = SHADOW_CELL
scene.render.resolution_y = SHADOW_CELL
cam.data.ortho_scale = SHADOW_CELL / (PX_PER_M * SCALE)
matte = bpy.data.materials.new('ShadowCatcherMatte')
matte.diffuse_color = (1.0, 1.0, 1.0, 1.0)
catcher.data.materials.append(matte)
for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
    if obj != catcher:
        obj.visible_camera = False
shadow_tree = bpy.data.node_groups.new('PlayerShadowCompositor', 'CompositorNodeTree')
shadow_tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
scene.compositing_node_group = shadow_tree
scene.render.use_compositing = True
nodes = shadow_tree.nodes
nodes.clear()
layers = nodes.new('CompositorNodeRLayers')
layers.scene = scene
layers.layer = scene.view_layers[0].name
composite = nodes.new('NodeGroupOutput')
shadow_pass = layers.outputs.get('Shadow Catcher')
if shadow_pass is None:
    raise RuntimeError('Cycles did not expose the Shadow Catcher render pass')
shadow_tree.links.new(shadow_pass, composite.inputs['Image'])

for d in range(NUM_DIRS):
    rig.rotation_euler.z = math.radians(135.0 - d * 360.0 / NUM_DIRS)
    scene.frame_set(frame_indices[0])
    rig.location.z = root_anchor.z
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lowest_z = 1e9
    for obj in [o for o in bpy.data.objects if o.type == 'MESH' and o != catcher]:
        ev = obj.evaluated_get(dg)
        for corner in ev.bound_box:
            lowest_z = min(lowest_z, (ev.matrix_world @ mathutils.Vector(corner)).z)
    rig.location.z = root_anchor.z - lowest_z
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(shadow_temp, "d%02d.png" % d)
    bpy.ops.render.render(write_still=True)

print("PLAYER_BAKED")
print("PLAYER_SHADOWS_BAKED")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(look.PRESETS), default="e30")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="sprite scale relative to the true world pixel scale")
    args = ap.parse_args()

    script = WORKER.format(
        model=MODEL, out_dir=OUT_DIR, cell=CELL, shadow_cell=SHADOW_CELL, dirs=NUM_DIRS, frames=NUM_FRAMES,
        samples=SAMPLES, pxm=look.PIXELS_PER_METRE, tile_w=look.FLOOR_TILE_W,
        anchor_z=look.CHAR_ANCHOR_Z, scale=args.scale,
        elev=look.elevation(args.preset),
        world=look.blender_world_snippet(),
        lights=look.blender_lights_snippet(),
    )
    tmp_py = os.path.join(OUT_DIR, "tmp_player.py")
    with open(tmp_py, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py],
                           capture_output=True, text=True)
        if "PLAYER_BAKED" not in p.stdout or "PLAYER_SHADOWS_BAKED" not in p.stdout:
            print(p.stdout[-1200:]); print(p.stderr[-1200:])
            raise RuntimeError("player bake failed")
    finally:
        if os.path.exists(tmp_py):
            os.remove(tmp_py)

    from PIL import Image
    anchor_line = next((line for line in p.stdout.splitlines() if line.startswith("ANCHOR_WORLD=")), None)
    if anchor_line is None:
        raise RuntimeError("player bake did not report its 3D anchor")
    anchor_world = [float(v) for v in anchor_line.split("=", 1)[1].split(",")]
    temp = os.path.join(OUT_DIR, "tmp_frames")
    sheet = Image.new("RGBA", (NUM_FRAMES * CELL, NUM_DIRS * CELL), (0, 0, 0, 0))
    for d in range(NUM_DIRS):
        for f in range(NUM_FRAMES):
            p = os.path.join(temp, "d%02d_f%03d.png" % (d, f))
            with Image.open(p) as im:
                sheet.paste(im, (f * CELL, d * CELL))
            os.remove(p)
    os.rmdir(temp)

    sheet = look.grade(sheet)
    out = os.path.join(OUT_DIR, f"player_{args.preset}.png")
    sheet.save(out)

    shadow_sheet = Image.new("RGBA", (NUM_DIRS * SHADOW_CELL, SHADOW_CELL), (0, 0, 0, 0))
    for d in range(NUM_DIRS):
        shadow_path = os.path.join(os.path.join(OUT_DIR, "tmp_player_shadows"), "d%02d.png" % d)
        with Image.open(shadow_path) as im:
            shadow_sheet.paste(im.convert("RGBA"), (d * SHADOW_CELL, 0))
        os.remove(shadow_path)
    os.rmdir(os.path.join(OUT_DIR, "tmp_player_shadows"))
    shadow_out = os.path.join(OUT_DIR, f"player_{args.preset}_shadow.png")
    shadow_sheet.save(shadow_out)
    anchor_meta = {
        "asset": "player",
        "preset": args.preset,
        "anchor_world_m": anchor_world,
        "anchor_world_semantics": "armature origin in source model; XY projects to sprite anchor, Z is grounded to room floor",
        "anchor_pixel": [CELL // 2, CELL // 2],
        "projection": {"azimuth_deg": 45.0, "elevation_deg": look.elevation(args.preset), "pixels_per_metre": look.PIXELS_PER_METRE},
        "grounding": "per-frame evaluated mesh minimum Z translated to floor Z=0",
        "shadow": "separate Cycles shadow-catcher mask, one planted reference pose per facing",
        "directions": NUM_DIRS,
        "frames_per_direction": NUM_FRAMES,
    }
    meta_out = os.path.join(OUT_DIR, f"player_{args.preset}_anchor.json")
    with open(meta_out, "w", encoding="utf-8") as f:
        json.dump(anchor_meta, f, indent=2)
        f.write("\n")
    print(f"[OK] {out} ({sheet.width}x{sheet.height})")
    print(f"[OK] {shadow_out} ({shadow_sheet.width}x{shadow_sheet.height})")
    print(f"[OK] {meta_out}: pixel anchor={anchor_meta['anchor_pixel']} world={anchor_meta['anchor_world_m']}")


if __name__ == "__main__":
    main()
