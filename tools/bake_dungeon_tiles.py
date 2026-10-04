#!/usr/bin/env python3
"""
bake_dungeon_tiles.py - Bakes Dreadhollow 3D modular pieces to top-down 16x16 dungeon tiles.
"""

import sys
import os
import math
import subprocess
from pathlib import Path
from PIL import Image

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GLB_DIR = r"C:\codexlocal\dungeonds\assets\environment\dreadhollow\GLB"
OUT_DIR = r"C:\codexlocal\dungeonds\assets\dungeon_tiles"

TILES_TO_BAKE = [
    # (output_name, glb_file, ortho_scale, camera_type, z_rot)
    ("T00_crypt_floor", "001_crypt_flagstone.glb", 2.0, "TOP", 0),
    ("T01_obsidian_floor", "002_split_obsidian_slab.glb", 2.0, "TOP", 0),
    ("T02_bone_floor", "003_bone_inlay_tile.glb", 2.0, "TOP", 0),
    ("T03_crimson_floor", "004_crimson_seal_tile.glb", 2.0, "TOP", 0),
    ("T04_worn_floor", "009_worn_cobble_tile.glb", 2.0, "TOP", 0),
    ("T05_crypt_wall_top", "021_crypt_wall.glb", 2.4, "TOP", 0),
    ("T06_buttress_wall_top", "022_buttressed_wall.glb", 2.4, "TOP", 0),
    ("T07_ossuary_wall_top", "023_ossuary_wall.glb", 2.4, "TOP", 0),
    ("T08_broken_pillar_top", "070_broken_pillar.glb", 1.8, "TOP", 0),
    ("T09_soul_pillar_top", "068_soul_lantern_pillar.glb", 1.8, "TOP", 0),
    ("T10_arch_ruins_top", "078_ruined_lancet_arch.glb", 2.8, "TOP", 0),
]

def render_tile_blender(name, glb_filename, ortho_scale, rot_z):
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
scene.render.resolution_x = 16
scene.render.resolution_y = 16

cam_data = bpy.data.cameras.new('TileCam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = {ortho_scale}
cam = bpy.data.objects.new('TileCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# Centered top-down
cam.location = (0, 0, 10)
cam.rotation_euler = (0, 0, math.radians({rot_z}))

# Dramatic Gothic top/side lighting
sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (5, -5, 10)
sun.rotation_euler = (math.radians(50), math.radians(15), math.radians(35))
scene.collection.objects.link(sun)

fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 1.5
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-5, 5, 8)
fill.rotation_euler = (math.radians(130), math.radians(-20), math.radians(20))
scene.collection.objects.link(fill)

scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
print("TILE_BAKE_DONE")
"""
    tmp_py = os.path.join(OUT_DIR, "tmp_bake.py")
    with open(tmp_py, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
    finally:
        if os.path.exists(tmp_py):
            os.remove(tmp_py)
    print(f"[OK] Rendered {name}.png")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, glb, scale, cam_t, rot in TILES_TO_BAKE:
        render_tile_blender(name, glb, scale, rot)
    print("All dungeon tiles rendered successfully!")

if __name__ == "__main__":
    main()
