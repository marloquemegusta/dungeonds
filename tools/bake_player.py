#!/usr/bin/env python3
"""
bake_player.py - Bakes character FBX models into 8-direction spritesheets
using the SAME look as the environment (tools/ds_look.py): identical lights,
identical elevation and identical world pixel scale, plus a baked cast shadow.

Usage:
    python tools/bake_player.py --preset e30 --character all
    python tools/bake_player.py --preset e30 --character charger
    python tools/bake_player.py --preset e60 --character player
"""

import os
import sys
import argparse
import subprocess
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_look as look

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
CELL = look.CHAR_CANVAS
SHADOW_CELL = CELL * 3 // 2
NUM_DIRS = 8
NUM_FRAMES = 8
SAMPLES = 32

CHARACTERS = {
    "player": {
        "model": os.path.join(ROOT, "assets", "characters", "monster", "Walking.fbx"),
        "out_dir": os.path.join(ROOT, "assets", "characters", "monster"),
        "prefix": "player",
    },
    "charger": {
        "model": os.path.join(ROOT, "assets", "characters", "charger", "Run.fbx"),
        "out_dir": os.path.join(ROOT, "assets", "characters", "charger"),
        "prefix": "charger",
    },
    "skeleton": {
        "model": os.path.join(ROOT, "assets", "characters", "skeleton", "skeleton.fbx"),
        "out_dir": os.path.join(ROOT, "assets", "characters", "skeleton"),
        "prefix": "skeleton",
    },
}

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

# Lock horizontal root motion so the cycle runs in place
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

# Adjust scale and shading if character model is non-standard (e.g. skeleton)
if "skeleton" in MODEL.lower():
    for arm in armatures:
        arm.scale = (0.027, 0.027, 0.027)

    # Fatten fine skeletal geometry so bones retain continuous volume and pixel connectivity in DS ortho projection
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        fat = obj.modifiers.new('Fatten', 'DISPLACE')
        fat.strength = 0.12
        fat.mid_level = 0.0

        # Anatomical vertex coloring: skull is ivory focal point, spine/cavities are deep charcoal, pelvis/joints in shadow
        ca = obj.data.color_attributes.new(name='BoneColor', type='FLOAT_COLOR', domain='POINT')
        vgs = dict((vg.name, vg.index) for vg in obj.vertex_groups)
        head_idx = vgs.get('mixamorig:Head', -1)
        spine_indices = [vgs[n] for n in ['mixamorig:Spine', 'mixamorig:Spine1', 'mixamorig:Spine2', 'mixamorig:Neck'] if n in vgs]
        pelvis_idx = vgs.get('mixamorig:Hips', -1)
        limb_indices = [vgs[n] for n in ['mixamorig:LeftArm', 'mixamorig:LeftForeArm', 'mixamorig:RightArm', 'mixamorig:RightForeArm', 'mixamorig:LeftUpLeg', 'mixamorig:LeftLeg', 'mixamorig:RightUpLeg', 'mixamorig:RightLeg'] if n in vgs]
        joint_indices = [vgs[n] for n in ['mixamorig:LeftHand', 'mixamorig:RightHand', 'mixamorig:LeftFoot', 'mixamorig:RightFoot', 'mixamorig:LeftToeBase', 'mixamorig:RightToeBase'] if n in vgs]

        for vi, vert in enumerate(obj.data.vertices):
            best_type = 'limb'
            best_w = 0.0
            for g in vert.groups:
                if g.group == head_idx and g.weight > best_w:
                    best_w = g.weight; best_type = 'head'
                elif g.group in spine_indices and g.weight > best_w:
                    best_w = g.weight; best_type = 'spine'
                elif g.group == pelvis_idx and g.weight > best_w:
                    best_w = g.weight; best_type = 'pelvis'
                elif g.group in joint_indices and g.weight > best_w:
                    best_w = g.weight; best_type = 'joint'
                elif g.group in limb_indices and g.weight > best_w:
                    best_w = g.weight; best_type = 'limb'

            # High-drama gothic chiaroscuro palette:
            if best_type == 'head':
                col = (0.76, 0.68, 0.54, 1.0)
            elif best_type == 'spine':
                col = (0.08, 0.06, 0.05, 1.0)
            elif best_type == 'pelvis':
                col = (0.16, 0.13, 0.10, 1.0)
            elif best_type == 'joint':
                col = (0.14, 0.12, 0.10, 1.0)
            else: # limb
                col = (0.35, 0.30, 0.24, 1.0)
            ca.data[vi].color = col

    # Shader combining anatomical vertex coloring and high-contrast Cycles Ambient Occlusion (pitch cavity shadows)
    bone_mat = bpy.data.materials.new('GothicBoneDramatic')
    bone_mat.use_nodes = True
    nodes = bone_mat.node_tree.nodes
    links = bone_mat.node_tree.links
    nodes.clear()

    out_node = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    vcol = nodes.new('ShaderNodeAttribute')
    vcol.attribute_name = 'BoneColor'
    bsdf.inputs['Roughness'].default_value = 0.85

    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 24
    ao.inputs['Distance'].default_value = 0.15

    # Ramp on AO to plunge deep cavities into near-black
    ao_ramp = nodes.new('ShaderNodeValToRGB')
    ao_ramp.color_ramp.elements[0].position = 0.30
    ao_ramp.color_ramp.elements[0].color = (0.05, 0.04, 0.04, 1.0)
    ao_ramp.color_ramp.elements[1].position = 0.85
    ao_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(ao.outputs['Color'], ao_ramp.inputs['Fac'])

    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    links.new(ao_ramp.outputs['Color'], mix.inputs[6])
    links.new(vcol.outputs['Color'], mix.inputs[7])

    links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])

    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        obj.data.materials.clear()
        obj.data.materials.append(bone_mat)

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

target = bpy.data.objects.new('CamTarget', None)
target.location = (root_anchor.x, root_anchor.y, 0.0)
scene.collection.objects.link(target)

rig = bpy.data.objects.new('CameraRig', None)
rig.location = root_anchor
scene.collection.objects.link(rig)

for obj in [o for o in bpy.data.objects if o.type in {{'MESH', 'ARMATURE'}}]:
    world_matrix = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_world = world_matrix

cam_data = bpy.data.cameras.new('IsoCam')
cam_data.type = 'ORTHO'
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

temp = os.path.join(OUT_DIR, "tmp_frames")
os.makedirs(temp, exist_ok=True)
shadow_temp = os.path.join(OUT_DIR, "tmp_shadows")
os.makedirs(shadow_temp, exist_ok=True)
total = max(1, end_f - start_f)
frame_indices = [int(start_f + (i * total) / NUM_FRAMES) for i in range(NUM_FRAMES)]

for d in range(NUM_DIRS):
    rig.rotation_euler.z = math.radians(135.0 - d * 360.0 / NUM_DIRS)
    bpy.context.view_layer.update()
    for fi, fnum in enumerate(frame_indices):
        scene.frame_set(fnum)
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

# Shadow pass
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
    for obj in [o for o in bpy.data.objects if o.type == 'MESH' and obj != catcher]:
        ev = obj.evaluated_get(dg)
        for corner in ev.bound_box:
            lowest_z = min(lowest_z, (ev.matrix_world @ mathutils.Vector(corner)).z)
    rig.location.z = root_anchor.z - lowest_z
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(shadow_temp, "d%02d.png" % d)
    bpy.ops.render.render(write_still=True)

print("BAKE_COMPLETE")
print("SHADOWS_COMPLETE")
'''


def bake_character(char_key, preset, scale=1.0):
    char_info = CHARACTERS[char_key]
    model_path = char_info["model"]
    out_dir = char_info["out_dir"]
    prefix = char_info["prefix"]
    os.makedirs(out_dir, exist_ok=True)

    print(f"[{char_key.upper()}] Baking {model_path} (preset {preset})...")
    script = WORKER.format(
        model=model_path, out_dir=out_dir, cell=CELL, shadow_cell=SHADOW_CELL, dirs=NUM_DIRS, frames=NUM_FRAMES,
        samples=SAMPLES, pxm=look.PIXELS_PER_METRE, tile_w=look.FLOOR_TILE_W,
        anchor_z=look.CHAR_ANCHOR_Z, scale=scale,
        elev=look.elevation(preset),
        world=look.blender_world_snippet(),
        lights=look.blender_lights_snippet(),
    )
    tmp_py = os.path.join(out_dir, f"tmp_{prefix}.py")
    with open(tmp_py, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        p = subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py],
                           capture_output=True, text=True)
        if "BAKE_COMPLETE" not in p.stdout or "SHADOWS_COMPLETE" not in p.stdout:
            print(p.stdout[-1200:]); print(p.stderr[-1200:])
            raise RuntimeError(f"{char_key} bake failed")
    finally:
        if os.path.exists(tmp_py):
            os.remove(tmp_py)

    from PIL import Image
    anchor_line = next((line for line in p.stdout.splitlines() if line.startswith("ANCHOR_WORLD=")), None)
    if anchor_line is None:
        raise RuntimeError(f"{char_key} bake did not report its 3D anchor")
    anchor_world = [float(v) for v in anchor_line.split("=", 1)[1].split(",")]

    temp = os.path.join(out_dir, "tmp_frames")
    sheet = Image.new("RGBA", (NUM_FRAMES * CELL, NUM_DIRS * CELL), (0, 0, 0, 0))
    for d in range(NUM_DIRS):
        for f in range(NUM_FRAMES):
            frame_file = os.path.join(temp, "d%02d_f%03d.png" % (d, f))
            with Image.open(frame_file) as im:
                framed = look.apply_outline(im)
                sheet.paste(framed, (f * CELL, d * CELL))
            os.remove(frame_file)
    os.rmdir(temp)

    sheet = look.grade(sheet)
    out = os.path.join(out_dir, f"{prefix}_{preset}.png")
    sheet.save(out)

    shadow_sheet = Image.new("RGBA", (NUM_DIRS * SHADOW_CELL, SHADOW_CELL), (0, 0, 0, 0))
    shadow_temp = os.path.join(out_dir, "tmp_shadows")
    for d in range(NUM_DIRS):
        shadow_path = os.path.join(shadow_temp, "d%02d.png" % d)
        with Image.open(shadow_path) as im:
            shadow_sheet.paste(im.convert("RGBA"), (d * SHADOW_CELL, 0))
        os.remove(shadow_path)
    os.rmdir(shadow_temp)
    shadow_out = os.path.join(out_dir, f"{prefix}_{preset}_shadow.png")
    shadow_sheet.save(shadow_out)

    anchor_meta = {
        "asset": prefix,
        "preset": preset,
        "anchor_world_m": anchor_world,
        "anchor_pixel": [CELL // 2, CELL // 2],
        "projection": {"azimuth_deg": 45.0, "elevation_deg": look.elevation(preset), "pixels_per_metre": look.PIXELS_PER_METRE},
        "directions": NUM_DIRS,
        "frames_per_direction": NUM_FRAMES,
    }
    meta_out = os.path.join(out_dir, f"{prefix}_{preset}_anchor.json")
    with open(meta_out, "w", encoding="utf-8") as f:
        json.dump(anchor_meta, f, indent=2)
        f.write("\n")
    print(f"[OK] {out} ({sheet.width}x{sheet.height})")
    print(f"[OK] {shadow_out} ({shadow_sheet.width}x{shadow_sheet.height})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(look.PRESETS), default="e30")
    ap.add_argument("--character", choices=("player", "charger", "skeleton", "all"), default="all")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="sprite scale relative to the true world pixel scale")
    args = ap.parse_args()

    targets = list(CHARACTERS.keys()) if args.character == "all" else [args.character]
    for char_key in targets:
        bake_character(char_key, args.preset, args.scale)


if __name__ == "__main__":
    main()
