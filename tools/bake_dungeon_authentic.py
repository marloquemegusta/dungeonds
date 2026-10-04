#!/usr/bin/env python3
"""
bake_dungeon_authentic.py - Generates properly oriented dungeon building blocks:
- Dimetric Floors (32x16, 2:1 ratio matching 60° pitch): Flagstone, Obsidian, Bone, Crimson, Worn
- Front Walls (32x48): Crypt wall, Buttressed, Ossuary, Ruined Arch
- Side Walls (16x48): Left and Right depth walls
- Props (32x48): Broken pillar, Soul pillar
"""

import os
import math
import subprocess
from PIL import Image

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
GLB_DIR = r"C:\codexlocal\dungeonds\assets\environment\dreadhollow\GLB"
OUT_DIR = r"C:\codexlocal\dungeonds\assets\dungeon_tiles"

FLOORS = [
    ("F00_crypt_floor", "001_crypt_flagstone.glb"),
    ("F01_obsidian_floor", "002_split_obsidian_slab.glb"),
    ("F02_bone_floor", "003_bone_inlay_tile.glb"),
    ("F03_crimson_floor", "004_crimson_seal_tile.glb"),
    ("F04_worn_floor", "009_worn_cobble_tile.glb"),
]

FRONT_WALLS = [
    ("W00_crypt_wall_front", "021_crypt_wall.glb"),
    ("W01_buttress_wall_front", "022_buttressed_wall.glb"),
    ("W02_ossuary_wall_front", "023_ossuary_wall.glb"),
    ("W03_arch_front", "078_ruined_lancet_arch.glb"),
]

SIDE_WALLS = [
    ("W10_crypt_wall_side", "021_crypt_wall.glb"),
    ("W11_buttress_wall_side", "022_buttressed_wall.glb"),
]

PROPS = [
    ("P00_broken_pillar", "070_broken_pillar.glb", 0.7),
    ("P01_soul_pillar", "068_soul_lantern_pillar.glb", 1.0),
]

def render_floors():
    for name, glb in FLOORS:
        glb_path = os.path.join(GLB_DIR, glb)
        out_png = os.path.join(OUT_DIR, f"{name}.png")
        script = f"""import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path}")
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
obj.rotation_mode = 'XYZ'
obj.rotation_euler = (0, 0, 0)

target = bpy.data.objects.new('T', None)
target.location = (0, 0, 0.1)
bpy.context.scene.collection.objects.link(target)

cam_data = bpy.data.cameras.new('C')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.0
cam = bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

pitch = math.radians(60.0)
dist = 10.0
cam.location = (0.0, -dist * math.cos(pitch), dist * math.sin(pitch) + 0.1)
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

# Studio Key + Fill Light
sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (6, -8, 10)
bpy.context.scene.collection.objects.link(sun)

fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 2.0
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-6, -6, 6)
bpy.context.scene.collection.objects.link(fill)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.film_transparent = True
scene.render.resolution_x = 32
scene.render.resolution_y = 16
scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
"""
        tmp_py = os.path.join(OUT_DIR, "tmp_floor.py")
        with open(tmp_py, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
        if os.path.exists(tmp_py): os.remove(tmp_py)
        print(f"[OK] Floor {name} (32x16)")

def render_front_walls():
    for name, glb in FRONT_WALLS:
        glb_path = os.path.join(GLB_DIR, glb)
        out_png = os.path.join(OUT_DIR, f"{name}.png")
        script = f"""import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path}")
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
obj.rotation_mode = 'XYZ'
obj.rotation_euler = (0, 0, 0)

target = bpy.data.objects.new('T', None)
target.location = (0, 0, 1.2)
bpy.context.scene.collection.objects.link(target)

cam_data = bpy.data.cameras.new('C')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.0 # 2 meters wide
cam = bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

pitch = math.radians(60.0)
dist = 10.0
cam.location = (0.0, -dist * math.cos(pitch), dist * math.sin(pitch) + 1.2)
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (6, -8, 10)
bpy.context.scene.collection.objects.link(sun)

fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 2.0
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-6, -6, 6)
bpy.context.scene.collection.objects.link(fill)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.film_transparent = True
scene.render.resolution_x = 32
scene.render.resolution_y = 48
scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
"""
        tmp_py = os.path.join(OUT_DIR, "tmp_front_wall.py")
        with open(tmp_py, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
        if os.path.exists(tmp_py): os.remove(tmp_py)
        print(f"[OK] Front Wall {name} (32x48)")

def render_side_walls():
    for name, glb in SIDE_WALLS:
        glb_path = os.path.join(GLB_DIR, glb)
        out_png = os.path.join(OUT_DIR, f"{name}.png")
        script = f"""import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path}")
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
obj.rotation_mode = 'XYZ'
obj.rotation_euler = (0, 0, math.radians(90.0)) # Rotated 90 deg along depth axis!

target = bpy.data.objects.new('T', None)
target.location = (0, 0, 1.2)
bpy.context.scene.collection.objects.link(target)

cam_data = bpy.data.cameras.new('C')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.0 # 2 meters along depth
cam = bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

pitch = math.radians(60.0)
dist = 10.0
cam.location = (0.0, -dist * math.cos(pitch), dist * math.sin(pitch) + 1.2)
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (6, -8, 10)
bpy.context.scene.collection.objects.link(sun)

fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 2.0
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-6, -6, 6)
bpy.context.scene.collection.objects.link(fill)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.film_transparent = True
scene.render.resolution_x = 32
scene.render.resolution_y = 48
scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
"""
        tmp_py = os.path.join(OUT_DIR, "tmp_side_wall.py")
        with open(tmp_py, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
        if os.path.exists(tmp_py): os.remove(tmp_py)
        print(f"[OK] Side Wall {name} (32x48)")

def render_props():
    for name, glb, cz in PROPS:
        glb_path = os.path.join(GLB_DIR, glb)
        out_png = os.path.join(OUT_DIR, f"{name}.png")
        script = f"""import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{glb_path}")
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
obj.rotation_mode = 'XYZ'
obj.rotation_euler = (0, 0, 0)

target = bpy.data.objects.new('T', None)
target.location = (0, 0, {cz})
bpy.context.scene.collection.objects.link(target)

cam_data = bpy.data.cameras.new('C')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.0
cam = bpy.data.objects.new('C', cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

pitch = math.radians(60.0)
dist = 10.0
cam.location = (0.0, -dist * math.cos(pitch), dist * math.sin(pitch) + {cz})
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'

sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 4.5
sun = bpy.data.objects.new('Sun', sun_data)
sun.location = (6, -8, 10)
bpy.context.scene.collection.objects.link(sun)

fill_data = bpy.data.lights.new('Fill', 'SUN')
fill_data.energy = 2.0
fill = bpy.data.objects.new('Fill', fill_data)
fill.location = (-6, -6, 6)
bpy.context.scene.collection.objects.link(fill)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.film_transparent = True
scene.render.resolution_x = 32
scene.render.resolution_y = 48
scene.render.filepath = r"{out_png}"
bpy.ops.render.render(write_still=True)
"""
        tmp_py = os.path.join(OUT_DIR, "tmp_prop.py")
        with open(tmp_py, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.run([BLENDER_EXE, "-b", "-P", tmp_py], capture_output=True, check=True)
        if os.path.exists(tmp_py): os.remove(tmp_py)
        print(f"[OK] Prop {name} (32x48)")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    render_floors()
    render_front_walls()
    render_side_walls()
    render_props()
    print("All authentic dungeon pieces rendered!")

if __name__ == "__main__":
    main()
