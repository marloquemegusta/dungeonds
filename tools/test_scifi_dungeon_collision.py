import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector
import numpy as np

fbx_path = r"c:\codexlocal/dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

obj = bpy.context.scene.objects[0]
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Scale up so total width is ~24 meters (scale factor 24.0)
SCALE = 24.0
for v in obj.data.vertices:
    v.co *= SCALE

# Find true floor Z (the most frequent upward polygon Z)
floor_samples = [v.co.z for p in obj.data.polygons if p.normal.z > 0.8 for v in [obj.data.vertices[i] for i in p.vertices]]
floor_z = float(np.median(floor_samples))
print(f"Detected Floor Z: {floor_z:.2f}m")

# Shift mesh so Floor Z is exactly 0.0
for v in obj.data.vertices:
    v.co.z -= floor_z

# Build BVH tree
bm = bmesh.new()
bm.from_mesh(obj.data)
bvh = BVHTree.FromBMesh(bm)

# Sample a grid of points across the dungeon (-10m to +10m in X and Y)
# Grid step 0.25m (similar to 4px cells in NDS)
xs = np.linspace(-10, 10, 80)
ys = np.linspace(-10, 10, 80)

grid = np.zeros((len(ys), len(xs)), dtype=str)
walk_count = 0
solid_count = 0

for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        # Raycast for torso clearance: from Z = 1.4m down to Z = 0.2m
        # If there is geometry in [0.2m, 1.4m], it's a solid wall!
        hit, _, _, _ = bvh.ray_cast(Vector((x, y, 1.4)), Vector((0, 0, -1)), 1.2)
        if hit is None:
            grid[j, i] = '.' # WALKABLE floor / open doorway!
            walk_count += 1
        else:
            grid[j, i] = '#' # SOLID wall
            solid_count += 1

print(f"\nCollision Sampling Results:")
print(f"  Walkable cells: {walk_count} ({walk_count/(walk_count+solid_count)*100:.1f}%)")
print(f"  Solid wall cells: {solid_count} ({solid_count/(walk_count+solid_count)*100:.1f}%)")

# Print a mini ASCII map of the dungeon layout
print("\nMini ASCII map of detected corridors and rooms (. = walk, # = wall):")
step = 2
for j in range(0, len(ys), step):
    row_str = "".join(grid[j, i] for i in range(0, len(xs), step))
    print(row_str)
