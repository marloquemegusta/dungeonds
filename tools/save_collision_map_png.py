import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector
import numpy as np

fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"
out_raw = r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a\scifi_collision_map.raw"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

obj = bpy.context.scene.objects[0]
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

SCALE = 24.0
for v in obj.data.vertices:
    v.co *= SCALE

# Floor level in scaled space
floor_samples = [v.co.z for p in obj.data.polygons if p.normal.z > 0.8 for v in [obj.data.vertices[i] for i in p.vertices]]
floor_z = float(np.median(floor_samples))

for v in obj.data.vertices:
    v.co.z -= floor_z

bm = bmesh.new()
bm.from_mesh(obj.data)
bvh = BVHTree.FromBMesh(bm)

# High resolution grid: 256 x 256
W, H = 256, 256
xs = np.linspace(-11.5, 11.5, W)
ys = np.linspace(-11.5, 11.5, H)

img_data = np.zeros((H, W, 3), dtype=np.uint8)

for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        # 1. Check if there is floor below (Z in [-0.5, +0.5])
        hit_floor, _, _, _ = bvh.ray_cast(Vector((x, y, 0.5)), Vector((0, 0, -1)), 1.0)
        
        # 2. Check if there is wall in torso space [0.2, 1.4]
        hit_wall, _, _, _ = bvh.ray_cast(Vector((x, y, 1.4)), Vector((0, 0, -1)), 1.2)
        
        if hit_floor is None:
            # Void outside dungeon
            img_data[j, i] = [20, 20, 25]
        elif hit_wall is not None:
            # Solid wall / obstacle
            img_data[j, i] = [220, 50, 50] # Red
        else:
            # Walkable floor!
            img_data[j, i] = [50, 180, 80] # Green

# Flip Y so North is UP
img_data = np.flipud(img_data)
with open(out_raw, "wb") as f:
    f.write(img_data.tobytes())
print(f"Saved raw collision data to {out_raw}")
