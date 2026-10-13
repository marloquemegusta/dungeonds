import bpy
import mathutils

fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_path)

obj = bpy.context.scene.objects[0]
print(f"Object: {obj.name}")
print(f"Dimensions: {obj.dimensions}")
print(f"Rotation: {obj.rotation_euler}")

# Check bounding box
bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
for i, axis in enumerate(['X', 'Y', 'Z']):
    vals = [v[i] for v in bbox]
    print(f"  Axis {axis}: min={min(vals):.3f}, max={max(vals):.3f}, span={max(vals)-min(vals):.3f}")
