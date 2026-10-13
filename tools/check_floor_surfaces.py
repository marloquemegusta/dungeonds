import bpy
import numpy as np

fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

obj = bpy.context.scene.objects[0]
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

SCALE = 15.0
for v in obj.data.vertices:
    v.co *= SCALE

# Check upward-facing polygons
up_polys_z = []
for p in obj.data.polygons:
    if p.normal.z > 0.7:  # roughly horizontal floor
        # average Z of polygon vertices
        avg_z = sum(obj.data.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        up_polys_z.append((avg_z, p.area))

up_polys_z.sort(key=lambda x: x[0])
print(f"Total upward facing floor polygons: {len(up_polys_z)}")

# Group by Z level
z_levels = {}
for z, area in up_polys_z:
    key = round(z, 1)
    z_levels[key] = z_levels.get(key, 0.0) + area

print("\nUpward floor surface area by Z level (in m^2):")
for z, area in sorted(z_levels.items()):
    if area > 1.0:
        print(f"  Z={z:.1f}m: area={area:.2f} m^2")
