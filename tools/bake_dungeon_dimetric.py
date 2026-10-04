#!/usr/bin/env python3
"""
bake_dungeon_dimetric.py - Bakes Dreadhollow 3D modular pieces in true 60-degree dimetric projection.
Produces:
  1. Flat floor tiles (32x16 dimetric or 32x32)
  2. Vertical wall / pillar / arch sprites with real vertical height (32x48) for depth sorting and occlusion.
"""

import os
import math
import subprocess
from PIL import Image

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GLB_DIR = r"C:\codexlocal\dungeonds\assets\environment\dreadhollow\GLB"
OUT_DIR = r"C:\codexlocal\dungeonds\assets\dungeon_tiles"

# (name, glb_file, res_w, res_h, ortho_scale, center_z, is_wall)
MODELS_TO_BAKE = [
    # Floors (32x32 dimetric tile, base centered)
    ("F00_crypt_floor", "001_crypt_flagstone.glb", 32, 32, 2.8, 0.1, False),
    ("F01_obsidian_floor", "002_split_obsidian_slab.glb", 32, 32, 2.8, 0.1, False),
    ("F02_bone_floor", "003_bone_inlay_tile.glb", 32, 32, 2.8, 0.1, False),
    ("F03_crimson_floor", "004_crimson_seal_tile.glb", 32, 32, 2.8, 0.1, False),
    ("F04_worn_floor", "009_worn_cobble_tile.glb", 32, 32, 2.8, 0.1, False),

    # Vertical Objects (32x48 with height, base at Y=32..48)
    ("W00_crypt_wall", "021_crypt_wall.glb", 32, 48, 2.5, 1.0, True),
    ("W01_buttress_wall", "022_buttressed_wall.glb", 32, 48, 2.5, 1.0, True),
    ("W02_ossuary_wall", "023_ossuary_wall.glb", 32, 48, 2.5, 1.0, True),
    ("W03_broken_pillar", "070_broken_pillar.glb", 32, 48, 2.5, 0.7, True),
    ("W04_soul_pillar", "068_soul_lantern_pillar.glb", 32, 48, 2.5, 1.0, True),
    ("W05_ruined_arch", "078_ruined_lancet_arch.glb", 32, 48, 2.8, 1.2, True),
]

def render_model(name, glb_filename, w, h, ortho_scale, center_z, is_wall):
    glb_path = os.path.join(GLB_DIR, glb_filename)
    out_png = os.path.join(OUT_DIR, f"{name}.png")

    script = f"""import bpy, math, os
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path}")

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.film_transparent = True
scene.render.resolution_x = {w}
scene.render.resolution_y = {h}

cam_data = bpy.data.cameras.new('IsoCam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = {ortho_scale}
cam = bpy.data.objects.new('IsoCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# 60 deg pitch matching character sprite
pitch = math.radians(60.0)
dist = 10.0
cam.location = (0, -dist * math.cos(pitch), dist * math.sin(pitch) + {center_z})

target = bpy.data.objects.new('T', None)
target.location = (0, 0, {center_z})
scene.collection.objects.link(target)

tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

# Key light
sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (6, -8, 10 + {center_z})
sun.parent = target
tt_s = sun.constraints.new(type='TRACK_TO')
tt_s.target = target
tt_s.track_axis = 'TRACK_NEGATIVE_Z'
tt_s.up_axis = 'UP_Y'
scene.collection.objects.link(sun)

# Fill light
fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 2.0
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-6, -6, 6 + {center_z})
fill.parent = target
tt_f = fill.constraints.new(type='TRACK_TO')
tt_f.target = target
tt_f.track_axis = 'TRACK_NEGATIVE_Z'
tt_f.up_axis = 'UP_Y'
scene.collection.objects.link(fill)

scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
print("BAKE_DONE")
"""
    tmp_py = os.path.join(OUT_DIR, f"tmp_{name}.py")
    with open(tmp_py, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
    finally:
        if os.path.exists(tmp_py):
            os.remove(tmp_py)
    print(f"[OK] Rendered {name}.png ({w}x{h})")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for item in MODELS_TO_BAKE:
        render_model(*item)
    print("All dimetric dungeon assets baked successfully!")

if __name__ == "__main__":
    main()
