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

# Scale up so wall height is 3.0 meters (scale factor 15.0)
SCALE = 15.0
for v in obj.data.vertices:
    v.co *= SCALE

z_coords = np.array([v.co.z for v in obj.data.vertices])
print("\n--- SCALED MESH ANALYSIS (Scale = 15.0) ---")
print(f"Total vertices: {len(z_coords)}")
print(f"Z min: {z_coords.min():.3f}m, Z max: {z_coords.max():.3f}m, Z mean: {z_coords.mean():.3f}m")

# Histogram of Z
hist, bin_edges = np.histogram(z_coords, bins=10)
for count, edge_l, edge_r in zip(hist, bin_edges[:-1], bin_edges[1:]):
    print(f"  Z [{edge_l:.2f}m .. {edge_r:.2f}m]: {count} verts ({count/len(z_coords)*100:.1f}%)")
