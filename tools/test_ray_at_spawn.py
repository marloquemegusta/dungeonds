import math, bpy
from mathutils import Vector
import bmesh
from mathutils.bvhtree import BVHTree
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

px, py = 388, 280
u = ((px + 0.5) / world_w - 0.5) * ortho_scale
v = (0.5 - (py + 0.5) / world_h) * view_h
ray_start = cam_origin + cam_right * u + cam_up * v

# Ground intersection for this screen pixel:
t_ground = -ray_start.z / cam_forward.z
gw = ray_start + cam_forward * t_ground
print(f"Screen pixel ({px}, {py}) projects to ground Z=0 at: {gw}")

# Now, project gw back to screen!
# What screen pixel does gw project to?
gp = gw - cam_origin
u_proj = gp.dot(cam_right)
v_proj = gp.dot(cam_up)
px_proj = int(round(((u_proj / ortho_scale) + 0.5) * world_w - 0.5))
py_proj = int(round((0.5 - (v_proj / view_h)) * world_h - 0.5))
print(f"Ground point {gw} projects to screen: ({px_proj}, {py_proj})")

# Now check the hit_co:
hit_co, hit_norm, hit_idx, _ = bvh.ray_cast(ray_start, cam_forward, 250.0)
print(f"Camera ray hits geometry at: {hit_co}")

# If we project hit_co directly down to ground: (hit_co.x, hit_co.y, 0)
# What screen pixel does THAT ground point project to?
gp_base = Vector((hit_co.x, hit_co.y, 0.0)) - cam_origin
u_base = gp_base.dot(cam_right)
v_base = gp_base.dot(cam_up)
px_base = int(round(((u_base / ortho_scale) + 0.5) * world_w - 0.5))
py_base = int(round((0.5 - (v_base / view_h)) * world_h - 0.5))
print(f"Wall point {hit_co} has ground footprint at screen: ({px_base}, {py_base})")
