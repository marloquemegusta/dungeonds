
import os, math, bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree
import bmesh

fbx_path = r"C:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"
out_dir = r"C:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\scifi_baked"
world_w = 768
world_h = 512
ortho_scale = 38.0
coll_w = 192
coll_h = 128
coll_scale = 4

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
print(f"Rendered world image: {full_world_img}")

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
print(f"Collision cells: WALKABLE={walk_cnt} ({walk_cnt*100//(coll_w*coll_h)}%), COVER={cover_cnt}, SOLID={solid_cnt}")

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
