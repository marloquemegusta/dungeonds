import bpy
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bmesh
from pathlib import Path
import os

def test():
    artifact_dir = Path(r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a")
    fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"
    world_img_path = r"C:\codexlocal\dungeonds\.worktrees\fog-and-visibility\walkthroughs\scifi-dungeon-tripo\assets\00_spawn.png"

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

    ortho_scale = 38.0
    world_w, world_h = 768, 512
    view_h = ortho_scale * (world_h / world_w)

    el = math.radians(30.0)
    az = math.radians(45.0)
    dist = 100.0
    cam_pos = Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el)))
    
    # Camera rotation
    cam_rot_mat = (
        math.radians(60.0), 0.0, math.radians(45.0)
    ) # Euler XYZ
    from mathutils import Euler
    R = Euler((math.radians(60.0), 0.0, math.radians(45.0)), 'XYZ').to_matrix()
    cam_right = R @ Vector((1, 0, 0))
    cam_up = R @ Vector((0, 1, 0))
    cam_forward = R @ Vector((0, 0, -1))

    # Player position at spawn
    px, py = 361, 233
    u = ((px + 0.5) / world_w - 0.5) * ortho_scale
    v = (0.5 - (py + 0.5) / world_h) * view_h
    ray_start = cam_pos + cam_right * u + cam_up * v
    t_g = -ray_start.z / cam_forward.z
    player_3d = ray_start + cam_forward * t_g
    light_3d = Vector((player_3d.x, player_3d.y, 1.2)) # Torch at 1.2m
    print(f"Light 3D position: {light_3d}")

    # Now, for the DS bottom screen viewport: cam_x=233, cam_y=137, size 256x192
    cam_x, cam_y = 233, 137
    ds_w, ds_h = 256, 192

    # Visibility map: sample every 2 pixels for speed
    vis_map = np.zeros((ds_h, ds_w), dtype=np.float32)

    # Max light reach in meters
    MAX_LIGHT_DIST = 9.0 # 9 meters

    for sy in range(0, ds_h, 2):
        wy = cam_y + sy
        v_pix = (0.5 - (wy + 0.5) / world_h) * view_h
        for sx in range(0, ds_w, 2):
            wx = cam_x + sx
            u_pix = ((wx + 0.5) / world_w - 0.5) * ortho_scale
            ray_s = cam_pos + cam_right * u_pix + cam_up * v_pix
            
            # Find 3D surface hit by camera ray
            hit_co, hit_norm, _, _ = bvh.ray_cast(ray_s, cam_forward, 250.0)
            if hit_co is not None:
                to_surface = hit_co - light_3d
                dist_m = to_surface.length
                if dist_m < MAX_LIGHT_DIST and dist_m > 0.05:
                    dir_light = to_surface / dist_m
                    occ_hit, _, _, _ = bvh.ray_cast(light_3d, dir_light, dist_m - 0.08)
                    if occ_hit is None:
                        # Clear 3D line of sight!
                        atten = 1.0 / (1.0 + (dist_m / 3.0)**2)
                        dot = -dir_light.dot(hit_norm)
                        lambert = max(0.25, dot)
                        vis_val = min(1.0, atten * lambert * 2.2)
                        vis_map[sy:sy+2, sx:sx+2] = vis_val

    out_npy = str(artifact_dir / "vis_map.npy")
    np.save(out_npy, vis_map)
    print("Saved vis_map to:", out_npy)

if __name__ == "__main__":
    test()
