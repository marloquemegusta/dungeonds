import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector
import numpy as np

fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"

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

floor_samples = [v.co.z for p in obj.data.polygons if p.normal.z > 0.8 for v in [obj.data.vertices[i] for i in p.vertices]]
floor_z = float(np.median(floor_samples))

for v in obj.data.vertices:
    v.co.z -= floor_z

bm = bmesh.new()
bm.from_mesh(obj.data)
bvh = BVHTree.FromBMesh(bm)

# Sample a line across a doorway: around X = -6.0 to -2.0, Y = 0.0 or similar
# Let's find cells that have floor at Z=0 and arch above Z=1.5
arch_points = []
for y in np.linspace(-10, 10, 81):
    for x in np.linspace(-10, 10, 81):
        hit_floor, _, _, _ = bvh.ray_cast(Vector((x, y, 0.5)), Vector((0, 0, -1)), 1.0)
        if hit_floor is None:
            continue
        # Check obstacle at 0.5m
        hit_low, _, _, _ = bvh.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)), 0.8)
        # Check obstacle at 2.0m
        hit_high, _, _, _ = bvh.ray_cast(Vector((x, y, 2.5)), Vector((0, 0, -1)), 0.8)
        if hit_low is None and hit_high is not None:
            arch_points.append((x, y, hit_high.z))

print(f"Found {len(arch_points)} points under archways/doorways!")
if arch_points:
    arch_zs = [p[2] for p in arch_points]
    print(f"Arch soffit min Z: {min(arch_zs):.2f}m, max Z: {max(arch_zs):.2f}m, mean: {np.mean(arch_zs):.2f}m")
