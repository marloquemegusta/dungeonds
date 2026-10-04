#!/usr/bin/env python3
"""
render_spritesheet.py - Headless Blender Isometric Spritesheet Renderer for dungeonds
Bakes 3D models (FBX/GLTF/OBJ) with skeletal animations into multi-directional spritesheets.
Includes automatic in-place lock (removes root-motion translation for stationary walking cycle).
"""

import sys
import os
import math
import subprocess
from pathlib import Path

def parse_args():
    raw_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    cfg = {
        "model": "",
        "anim": "Layer0",
        "dirs": 8,
        "res": 64,
        "frames": 8,
        "engine": "CYCLES",
        "samples": 8,
        "in_place": True,
        "out": "spritesheet.png",
        "temp_dir": os.path.abspath("temp_sprite_frames")
    }
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        val = raw_args[i+1] if i + 1 < len(raw_args) else ""
        if arg in ["--model", "-m"]:
            cfg["model"] = os.path.abspath(val)
            i += 2
        elif arg in ["--anim", "-a"]:
            cfg["anim"] = val
            i += 2
        elif arg in ["--dirs", "-d"]:
            cfg["dirs"] = int(val)
            i += 2
        elif arg in ["--res", "-r"]:
            cfg["res"] = int(val)
            i += 2
        elif arg in ["--frames", "-f"]:
            cfg["frames"] = int(val)
            i += 2
        elif arg in ["--engine", "-e"]:
            cfg["engine"] = val
            i += 2
        elif arg in ["--samples", "-s"]:
            cfg["samples"] = int(val)
            i += 2
        elif arg in ["--in-place"]:
            cfg["in_place"] = (val.lower() not in ["0", "false", "no"])
            i += 2
        elif arg in ["--out", "-o"]:
            cfg["out"] = os.path.abspath(val)
            i += 2
        elif arg in ["--temp"]:
            cfg["temp_dir"] = os.path.abspath(val)
            i += 2
        else:
            i += 1
    return cfg

def run_blender_render(cfg):
    blender_script = os.path.abspath("blender_worker.py")
    script_content = f"""import sys, os, math
import bpy
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)
model_path = r"{cfg['model']}"
ext = os.path.splitext(model_path)[1].lower()
if ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=model_path)
elif ext in [".gltf", ".glb"]:
    bpy.ops.import_scene.gltf(filepath=model_path)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=model_path)

# Apply animation action
actions = list(bpy.data.actions)
q = "{cfg['anim']}".lower()
matching = [a for a in actions if q in a.name.lower()] or actions[:1]
main_act = matching[0] if matching else None

if main_act:
    for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = main_act
    start_f = int(main_act.frame_range[0])
    end_f = int(main_act.frame_range[1])
else:
    start_f = bpy.context.scene.frame_start
    end_f = bpy.context.scene.frame_end

# If in-place requested, lock horizontal displacement on root/hips bone
if {cfg['in_place']}:
    bpy.context.scene.frame_set(start_f)
    for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
        for bone_name in ["mixamorig:Hips", "Hips", "root", "Root"]:
            if bone_name in arm.pose.bones:
                bone = arm.pose.bones[bone_name]
                c = bone.constraints.new(type='LIMIT_LOCATION')
                c.owner_space = 'LOCAL'
                # Lock local X (side-to-side drift) and local Z (forward translation in mixamo local bone space)
                c.use_min_x = True
                c.use_max_x = True
                c.min_x = bone.location.x
                c.max_x = bone.location.x
                c.use_min_z = True
                c.use_max_z = True
                c.min_z = bone.location.z
                c.max_z = bone.location.z
                print(f"[BLENDER] In-place constraint applied to bone: {{bone_name}}")
                break

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
all_z = []
all_dims = []
for o in mesh_objs:
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box] if hasattr(o, 'matrix_world') else []
    for v in corners:
        all_z.append(v.z)
    all_dims.extend([o.dimensions.x, o.dimensions.y, o.dimensions.z])

min_z = min(all_z) if all_z else 0.0
max_z = max(all_z) if all_z else 2.0
center_z = (min_z + max_z) * 0.5
max_dim = max(all_dims) if all_dims else (max_z - min_z)
max_dim = max(1.0, max_dim)

scene = bpy.context.scene
scene.render.engine = "{cfg['engine']}"
if scene.render.engine == "CYCLES":
    scene.cycles.device = 'CPU'
    scene.cycles.samples = {cfg['samples']}
    scene.cycles.preview_samples = {cfg['samples']}
    scene.cycles.use_denoising = False

scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = {cfg['res']}
scene.render.resolution_y = {cfg['res']}
scene.render.resolution_percentage = 100

target = bpy.data.objects.new("CamTarget", None)
target.location = (0.0, 0.0, center_z)
scene.collection.objects.link(target)

rig = bpy.data.objects.new("CameraRig", None)
rig.location = (0.0, 0.0, center_z)
scene.collection.objects.link(rig)

cam_data = bpy.data.cameras.new("IsoCam")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = max_dim * 1.35
cam_obj = bpy.data.objects.new("IsoCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

pitch = math.radians(60.0)
dist = max_dim * 4.0
cam_obj.location = (0.0, -dist * math.cos(pitch), dist * math.sin(pitch))
cam_obj.parent = rig

tt = cam_obj.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

sun_data = bpy.data.lights.new("Sun", type='SUN')
sun_data.energy = 4.0
sun_obj = bpy.data.objects.new("Sun", sun_data)
sun_obj.location = (dist, -dist, dist)
sun_obj.parent = rig
tt_sun = sun_obj.constraints.new(type='TRACK_TO')
tt_sun.target = target
tt_sun.track_axis = 'TRACK_NEGATIVE_Z'
tt_sun.up_axis = 'UP_Y'
scene.collection.objects.link(sun_obj)

fill_data = bpy.data.lights.new("FillSun", type='SUN')
fill_data.energy = 2.0
fill_obj = bpy.data.objects.new("FillSun", fill_data)
fill_obj.location = (-dist, -dist, dist * 0.5)
fill_obj.parent = rig
tt_fill = fill_obj.constraints.new(type='TRACK_TO')
tt_fill.target = target
tt_fill.track_axis = 'TRACK_NEGATIVE_Z'
tt_fill.up_axis = 'UP_Y'
scene.collection.objects.link(fill_obj)

total_f = max(1, end_f - start_f)
num_out = {cfg['frames']}
frame_indices = [int(start_f + (i * total_f) / num_out) for i in range(num_out)]

num_dirs = {cfg['dirs']}
angle_step = 360.0 / num_dirs
temp_dir = r"{cfg['temp_dir']}"
os.makedirs(temp_dir, exist_ok=True)

for d in range(num_dirs):
    rig.rotation_euler.z = math.radians(-d * angle_step)
    bpy.context.view_layer.update()
    for f_idx, f_num in enumerate(frame_indices):
        scene.frame_set(f_num)
        out_f = os.path.join(temp_dir, f"d{{d:02d}}_f{{f_idx:03d}}.png")
        scene.render.filepath = out_f
        bpy.ops.render.render(write_still=True)

print("BLENDER_RENDER_DONE")
"""
    with open(blender_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    blender_exe = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    try:
        p = subprocess.run([blender_exe, "-b", "-P", blender_script], capture_output=True, text=True)
        if "BLENDER_RENDER_DONE" not in p.stdout:
            print("[STDERR]:", p.stderr)
            print("[STDOUT]:", p.stdout[-1500:])
            raise RuntimeError("Blender render failed.")
        print("Frames renderizados exitosamente por Blender.")
    finally:
        if os.path.exists(blender_script):
            os.remove(blender_script)

def stitch_spritesheet(cfg):
    from PIL import Image
    temp_dir = Path(cfg["temp_dir"])
    num_dirs = cfg["dirs"]
    num_frames = cfg["frames"]
    res = cfg["res"]

    sheet = Image.new("RGBA", (num_frames * res, num_dirs * res), (0, 0, 0, 0))
    for d in range(num_dirs):
        for f in range(num_frames):
            frame_path = temp_dir / f"d{d:02d}_f{f:03d}.png"
            if frame_path.exists():
                with Image.open(frame_path) as im:
                    sheet.paste(im, (f * res, d * res))
                try:
                    frame_path.unlink()
                except Exception:
                    pass

    try:
        temp_dir.rmdir()
    except Exception:
        pass

    out_path = Path(cfg["out"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_path))
    print(f"[OK] Spritesheet guardado en: {out_path} ({sheet.width}x{sheet.height})")

    # Generate preview animated GIFs for all directions
    for d in range(num_dirs):
        frames = []
        for f in range(num_frames):
            box = (f * res, d * res, (f + 1) * res, (d + 1) * res)
            frame = sheet.crop(box)
            frames.append(frame)
        gif_path = out_path.parent / f"preview_inplace_dir_{d}.gif"
        frames[0].save(
            str(gif_path),
            save_all=True,
            append_images=frames[1:],
            duration=120,
            loop=0,
            disposal=2
        )
    print(f"[OK] Previews GIF 'in-place' generados en {out_path.parent}")

if __name__ == "__main__":
    cfg = parse_args()
    print(f"Config: {cfg}")
    run_blender_render(cfg)
    stitch_spritesheet(cfg)
