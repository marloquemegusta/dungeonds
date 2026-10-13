#!/usr/bin/env python3
"""
bake_scifi_dungeon.py - Complete 2.5D dimetric bake pipeline for the AI 3D sci-fi dungeon.
Bakes:
  1. Rendered world background image -> 8bpp hardware tiles
  2. 2-bit collision grid (walkable / solid wall / cover) with doorway clearance
  3. Sorted RLE occlusion runs for archways and walls
  4. diablo_dungeon.h / .c and dungeon_occlusion.c
"""

import math
import os
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

WT = Path(__file__).resolve().parents[1]
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
FBX_PATH = str(WT / "assets" / "environment" / "scifi_dungeon" / "tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx")
OUT_DIR = WT / "assets" / "scifi_baked"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WORLD_W = 768
WORLD_H = 512
COLLISION_SCALE = 4
COLLISION_W = WORLD_W // COLLISION_SCALE
COLLISION_H = WORLD_H // COLLISION_SCALE
ORTHO_SCALE = 38.0  # ~20 px/m; dungeon footprint 24m fits within 34m width

blender_script = f'''
import os, math, bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree
import bmesh

fbx_path = r"{FBX_PATH}"
out_dir = r"{OUT_DIR}"
world_w = {WORLD_W}
world_h = {WORLD_H}
ortho_scale = {ORTHO_SCALE}
coll_w = {COLLISION_W}
coll_h = {COLLISION_H}
coll_scale = {COLLISION_SCALE}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

# 1. Prepare mesh
obj = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

SCALE = 24.0
for v in obj.data.vertices:
    v.co *= SCALE

# Ground baseline
floor_samples = [v.co.z for p in obj.data.polygons if p.normal.z > 0.8 for v in [obj.data.vertices[i] for i in p.vertices]]
floor_z = float(np.median(floor_samples))

for v in obj.data.vertices:
    v.co.z -= floor_z

# Adjust materials for clean diffuse look
for mat in obj.data.materials:
    if mat and mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                if "Metallic" in node.inputs and not node.inputs["Metallic"].is_linked:
                    node.inputs["Metallic"].default_value = 0.05
                node.inputs["Roughness"].default_value = 0.85
        for link in list(mat.node_tree.links):
            if link.to_socket.name in ("Metallic", "Normal"):
                mat.node_tree.links.remove(link)

bpy.context.view_layer.update()
bm = bmesh.new()
bm.from_mesh(obj.data)
bvh = BVHTree.FromBMesh(bm)

# 2. Lighting setup (gothic / scifi torch & rim)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = world_w
scene.render.resolution_y = world_h
scene.world = bpy.data.worlds.new("World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.28, 0.28, 0.32, 1.0)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

sun_data = bpy.data.lights.new("Sun", type="SUN")
sun_data.energy = 3.2
sun_data.color = (1.0, 0.95, 0.88)
sun_obj = bpy.data.objects.new("Sun", sun_data)
sun_obj.rotation_euler = (math.radians(48), math.radians(-22), math.radians(35))
bpy.context.collection.objects.link(sun_obj)

fill_data = bpy.data.lights.new("Fill", type="SUN")
fill_data.energy = 1.6
fill_data.color = (0.75, 0.85, 1.0)
fill_obj = bpy.data.objects.new("Fill", fill_data)
fill_obj.rotation_euler = (math.radians(-35), math.radians(40), math.radians(-120))
bpy.context.collection.objects.link(fill_obj)

# 3. Camera setup: Preset e30 (elevation 30 deg, azimuth 45 deg)
cam_data = bpy.data.cameras.new("DSCam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = ortho_scale
cam_obj = bpy.data.objects.new("DSCam", cam_data)
el = math.radians(30.0)
az = math.radians(45.0)
dist = 100.0
cam_obj.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
cam_obj.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
bpy.context.collection.objects.link(cam_obj)
scene.camera = cam_obj
bpy.context.view_layer.update()

# Camera basis vectors
cam_rot_mat = cam_obj.matrix_world.to_3x3()
cam_right = cam_rot_mat @ Vector((1, 0, 0))
cam_up = cam_rot_mat @ Vector((0, 1, 0))
cam_forward = cam_rot_mat @ Vector((0, 0, -1))
cam_origin = cam_obj.matrix_world.translation
view_h = ortho_scale * (world_h / world_w)

# 4. Render Background
scene.render.film_transparent = False
full_world_img = os.path.join(out_dir, "scifi_world.png")
scene.render.filepath = full_world_img
bpy.ops.render.render(write_still=True)
print(f"Rendered world image: {{full_world_img}}")

# 5. Compute 2-bit Collision Grid
# 0 = Walkable & Bullet passes
# 1 = Low Cover (Walk blocked, bullet passes)
# 3 = Solid Wall (Walk blocked, bullet blocked)
coll_grid = np.zeros((coll_h, coll_w), dtype=np.uint8)

for cy in range(coll_h):
    py = cy * coll_scale + coll_scale // 2
    v = (0.5 - (py + 0.5) / world_h) * view_h
    for cx in range(coll_w):
        px = cx * coll_scale + coll_scale // 2
        u = ((px + 0.5) / world_w - 0.5) * ortho_scale
        p_cam = cam_origin + cam_right * u + cam_up * v
        
        # Intersect camera ray with Z=0 ground plane
        if abs(cam_forward.z) > 1e-6:
            t_ground = -p_cam.z / cam_forward.z
            gw = p_cam + cam_forward * t_ground
            
            # Floor check [Z = -0.5 .. 0.5]
            hit_floor, _, _, _ = bvh.ray_cast(Vector((gw.x, gw.y, 0.5)), Vector((0, 0, -1)), 1.0)
            
            if hit_floor is None:
                # Outside dungeon or void pit
                coll_grid[cy, cx] = 3
            else:
                # Torso space clearance [Z = 0.3 .. 1.4]
                hit_torso, _, _, _ = bvh.ray_cast(Vector((gw.x, gw.y, 1.4)), Vector((0, 0, -1)), 1.1)
                if hit_torso is None:
                    # Torso clear: WALKABLE (doorways, open halls, plazas)!
                    coll_grid[cy, cx] = 0
                else:
                    # Obstacle present: check if high wall or low cover
                    hit_high, _, _, _ = bvh.ray_cast(Vector((gw.x, gw.y, 2.2)), Vector((0, 0, -1)), 0.8)
                    if hit_high is not None:
                        coll_grid[cy, cx] = 3  # Tall solid wall
                    else:
                        coll_grid[cy, cx] = 1  # Low cover
        else:
            coll_grid[cy, cx] = 3

np.save(os.path.join(out_dir, "scifi_coll.npy"), coll_grid)
walk_cnt = int(np.sum(coll_grid == 0))
cover_cnt = int(np.sum(coll_grid == 1))
solid_cnt = int(np.sum(coll_grid == 3))
print(f"Collision cells: WALKABLE={{walk_cnt}} ({{walk_cnt*100//(coll_w*coll_h)}}%), COVER={{cover_cnt}}, SOLID={{solid_cnt}}")

# 6. Compute Occlusion Depth Map
occ_depth = np.full((world_h, world_w), -1, dtype=np.int16)

for py in range(world_h):
    v = (0.5 - (py + 0.5) / world_h) * view_h
    for px in range(world_w):
        u = ((px + 0.5) / world_w - 0.5) * ortho_scale
        ray_start = cam_origin + cam_right * u + cam_up * v
        hit_co, _, _, _ = bvh.ray_cast(ray_start, cam_forward, 250.0)
        
        # If hits geometry strictly above ground floor (> 0.80m: walls, arches, props)
        if hit_co is not None and hit_co.z > 0.80:
            gp = Vector((hit_co.x, hit_co.y, 0.0)) - cam_origin
            v_ground = gp.dot(cam_up)
            py_ground = int(round((0.5 - v_ground / view_h) * world_h - 0.5))
            occ_depth[py, px] = max(py, min(world_h - 1, py_ground))

np.save(os.path.join(out_dir, "scifi_occ.npy"), occ_depth)
print("Occlusion depth map computed!")
bm.free()
'''

bpath = OUT_DIR / "_blender_bake_scifi.py"
with open(bpath, "w", encoding="utf-8") as f:
    f.write(blender_script)

print("Running Blender render and raycasting...")
subprocess.run([BLENDER, "-b", "-P", str(bpath)], check=True)

# 7. Convert image to BGR555 raw
img = Image.open(OUT_DIR / "scifi_world.png").convert("RGB")
rgb = np.asarray(img, dtype=np.uint16)
r5 = (rgb[:, :, 0] >> 3) & 31
g5 = (rgb[:, :, 1] >> 3) & 31
b5 = (rgb[:, :, 2] >> 3) & 31
bgr555 = (0x8000 | r5 | (g5 << 5) | (b5 << 10)).flatten()
raw_world = OUT_DIR / "scifi_world_bgr555.raw"
bgr555.astype("<u2", copy=False).tofile(raw_world)
print(f"Saved raw BGR555 image: {raw_world}")

coll = np.load(OUT_DIR / "scifi_coll.npy")
occ = np.load(OUT_DIR / "scifi_occ.npy")

# Visual collision overlay
overlay = img.copy().convert("RGBA")
ov_layer = Image.new("RGBA", (WORLD_W, WORLD_H), (0, 0, 0, 0))
ov_draw = ImageDraw.Draw(ov_layer)
for cy in range(COLLISION_H):
    for cx in range(COLLISION_W):
        val = int(coll[cy, cx])
        x0, y0 = cx * COLLISION_SCALE, cy * COLLISION_SCALE
        if val == 0:
            # Walkable: translucent green
            ov_draw.rectangle([x0, y0, x0 + COLLISION_SCALE - 1, y0 + COLLISION_SCALE - 1], fill=(40, 220, 60, 60))
        elif val == 1:
            # Low cover: yellow
            ov_draw.rectangle([x0, y0, x0 + COLLISION_SCALE - 1, y0 + COLLISION_SCALE - 1], fill=(255, 210, 0, 140))
        elif val == 3:
            # Solid wall: red
            ov_draw.rectangle([x0, y0, x0 + COLLISION_SCALE - 1, y0 + COLLISION_SCALE - 1], fill=(235, 45, 45, 120))

overlay_comp = Image.alpha_composite(overlay, ov_layer).convert("RGB")
overlay_path = OUT_DIR / "scifi_collision_overlay.png"
overlay_comp.save(overlay_path)
print(f"Saved collision overlay: {overlay_path}")

# 8. Find valid spawn point near center in a clear walkable area
center_cx = COLLISION_W // 2
center_cy = COLLISION_H // 2

contract_offsets = ((0, 0), (-16, 0), (16, 0), (0, -12), (0, 12), (-12, -8), (-12, 8), (12, -8), (12, 8))
valid_spawns = []
for py in range(24, WORLD_H - 24):
    for px in range(24, WORLD_W - 24):
        ok = True
        for dx, dy in contract_offsets:
            cx = (px + dx) // COLLISION_SCALE
            cy = (py + dy) // COLLISION_SCALE
            if cx < 0 or cx >= COLLISION_W or cy < 0 or cy >= COLLISION_H or (coll[cy, cx] & 1) != 0:
                ok = False
                break
        if ok and occ[py, px] == -1:
            d = (px - WORLD_W // 2)**2 + (py - WORLD_H // 2)**2
            valid_spawns.append((d, px, py))
valid_spawns.sort()
spawn_px, spawn_py = valid_spawns[0][1], valid_spawns[0][2]
print(f"Chosen spawn: pixel ({spawn_px}, {spawn_py})")

# 9. Write diablo_dungeon.h
coll_bytes = (COLLISION_W * COLLISION_H + 3) // 4
(WT / "include" / "diablo_dungeon.h").write_text(
    "#ifndef DIABLO_DUNGEON_H\n#define DIABLO_DUNGEON_H\n\n"
    "#include <nds.h>\n\n"
    f"#define WORLD_W {WORLD_W}\n#define WORLD_H {WORLD_H}\n"
    f"#define COLLISION_W {COLLISION_W}\n#define COLLISION_H {COLLISION_H}\n"
    f"#define COLLISION_SCALE {COLLISION_SCALE}\n"
    f"#define DUNGEON_OCCLUSION_SEGMENTS 1\n"
    f"#define COLLISION_BYTES {coll_bytes}\n\n"
    f"#define SPAWN_PIXEL_X {spawn_px}\n#define SPAWN_PIXEL_Y {spawn_py}\n\n"
    "extern const uint8_t g_dungeon_collision[COLLISION_BYTES];\n\n"
    "#endif // DIABLO_DUNGEON_H\n",
    encoding="utf-8",
)

# 10. Write source/diablo_dungeon.c
coll_flat = coll.flatten().astype(np.uint8)
if coll_flat.size % 4:
    coll_flat = np.pad(coll_flat, (0, 4 - coll_flat.size % 4))
coll_packed = (coll_flat[0::4] | (coll_flat[1::4] << 2) |
               (coll_flat[2::4] << 4) | (coll_flat[3::4] << 6))
c_lines = [
    '#include "diablo_dungeon.h"\n\n',
    f"const uint8_t g_dungeon_collision[COLLISION_BYTES] = {{\n",
]
for i in range(0, len(coll_packed), 32):
    chunk = ", ".join(f"0x{int(v):02X}" for v in coll_packed[i : i + 32])
    c_lines.append(f"    {chunk},\n")
c_lines.append("};\n")

with open(WT / "source" / "diablo_dungeon.c", "w", encoding="utf-8") as f:
    f.writelines(c_lines)

# 11. Encode RLE runs for source/dungeon_occlusion.c
runs = []
for y in range(WORLD_H):
    x = 0
    while x < WORLD_W:
        if occ[y, x] < 0:
            x += 1
            continue
        x0 = x
        min_d = occ[y, x]
        max_d = occ[y, x]
        while x < WORLD_W and occ[y, x] >= 0:
            d = occ[y, x]
            if max(max_d, d) - min(min_d, d) > 16:
                break
            min_d = min(min_d, d)
            max_d = max(max_d, d)
            x += 1
        if x - x0 >= 2:
            runs.append((x0, y, x - x0, int(max_d)))

occ_lines = [
    '#include "dungeon_occlusion.h"\n\n',
    'const DungeonOcclusionRun g_dungeon_occlusion_runs[] __attribute__((aligned(4))) = {\n',
]
for x0, y, length, d in runs:
    occ_lines.append(f"    {{{x0}, {y}, {length}, {d}}},\n")
if not runs:
    occ_lines.append("    {0, 0, 0, -1},\n")
occ_lines.append("};\n\n")
occ_lines.append(f"const uint32_t g_dungeon_occlusion_run_count = {len(runs)}u;\n")
occ_lines.append("\nconst DungeonOcclusionSegmentOffset g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS] = {\n")
occ_lines.append("    {0, 0},\n")
occ_lines.append("};\n")

with open(WT / "source" / "dungeon_occlusion.c", "w", encoding="utf-8") as f:
    f.writelines(occ_lines)

print(f"Generated {len(runs)} occlusion runs!")

# 12. Run generate_fbx_bg_tiles.py to produce VRAM hardware tiles
subprocess.run([sys.executable, str(WT / "tools" / "generate_fbx_bg_tiles.py"), str(raw_world)], check=True)
print("Hardware BG tiles generated successfully!")
