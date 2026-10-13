import math, bpy
import numpy as np
from mathutils import Vector
import bmesh
from mathutils.bvhtree import BVHTree

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

bpy.context.view_layer.update()
bm = bmesh.new()
bm.from_mesh(obj.data)
bvh = BVHTree.FromBMesh(bm)

cam_data = bpy.data.cameras.new("DSCam")
cam_data.type = "ORTHO"
ortho_scale = 38.0
cam_data.ortho_scale = ortho_scale
cam_obj = bpy.data.objects.new("DSCam", cam_data)
el = math.radians(30.0)
az = math.radians(45.0)
dist = 100.0
cam_obj.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
cam_obj.rotation_euler = (math.radians(60.0), 0.0, math.radians(45.0))
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
bpy.context.view_layer.update()

cam_rot_mat = cam_obj.matrix_world.to_3x3()
cam_right = cam_rot_mat @ Vector((1, 0, 0))
cam_up = cam_rot_mat @ Vector((0, 1, 0))
cam_forward = cam_rot_mat @ Vector((0, 0, -1))
cam_origin = cam_obj.matrix_world.translation

world_w, world_h = 768, 512
view_h = ortho_scale * (world_h / world_w)

occ_count = 0
for py in range(0, world_h, 2):
    v = (0.5 - (py + 0.5) / world_h) * view_h
    for px in range(0, world_w, 2):
        u = ((px + 0.5) / world_w - 0.5) * ortho_scale
        ray_start = cam_origin + cam_right * u + cam_up * v
        hit_co, _, _, _ = bvh.ray_cast(ray_start, cam_forward, 250.0)
        if hit_co is not None and hit_co.z > 0.08:
            occ_count += 1

print(f"Occlusion hits (sampled every 2px): {occ_count}")
