import bpy
import math
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree
import bmesh
from pathlib import Path
import os
import time

def bake_all():
    start_time = time.time()
    repo_root = Path(r"C:\codexlocal\dungeonds\.worktrees\fog-and-visibility")
    fbx_path = r"c:\codexlocal\dungeonds\.worktrees\scifi-dungeon-tripo\assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"
    coll_path = repo_root / r"assets\scifi_baked\scifi_coll.npy"

    coll = np.load(coll_path)
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
    
    R = Euler((math.radians(60.0), 0.0, math.radians(45.0)), 'XYZ').to_matrix()
    cam_right = R @ Vector((1, 0, 0))
    cam_up = R @ Vector((0, 1, 0))
    cam_forward = R @ Vector((0, 0, -1))

    FOG_MAP_W = 96
    FOG_MAP_H = 64
    RADIUS_TILES = 12
    BOX_SIZE = RADIUS_TILES * 2 + 1
    BOX_BYTES = (BOX_SIZE * BOX_SIZE + 7) // 8

    # Function to get 3D surface point for any pixel (px, py)
    def get_surface_point(px, py):
        u_pix = ((px + 0.5) / world_w - 0.5) * ortho_scale
        v_pix = (0.5 - (py + 0.5) / world_h) * view_h
        ray_s = cam_pos + cam_right * u_pix + cam_up * v_pix
        hit_co, _, _, _ = bvh.ray_cast(ray_s, cam_forward, 250.0)
        if hit_co is not None:
            return hit_co
        t_g = -ray_s.z / cam_forward.z
        return ray_s + cam_forward * t_g

    # Precompute 4 sample points per tile to guarantee complete coverage
    print("Precomputing 4 surface sample points per 8x8 tile...")
    tile_samples_3d = {}
    tile_centers_3d = {}
    offsets = [(2, 2), (6, 2), (2, 6), (6, 6)]

    for ty in range(FOG_MAP_H):
        for tx in range(FOG_MAP_W):
            tile_centers_3d[(tx, ty)] = get_surface_point(tx * 8 + 4, ty * 8 + 4)
            s_list = []
            for ox, oy in offsets:
                s_list.append(get_surface_point(tx * 8 + ox, ty * 8 + oy))
            tile_samples_3d[(tx, ty)] = s_list

    # Determine walkable tiles
    tile_walkable_index = np.full((FOG_MAP_H, FOG_MAP_W), -1, dtype=np.int16)
    walkable_coords = []
    
    for ty in range(FOG_MAP_H):
        for tx in range(FOG_MAP_W):
            sub_coll = coll[ty*2:(ty+1)*2, tx*2:(tx+1)*2]
            if np.any(sub_coll == 0):
                tile_walkable_index[ty, tx] = len(walkable_coords)
                walkable_coords.append((tx, ty))

    num_walkable = len(walkable_coords)
    print(f"Total walkable tiles: {num_walkable}")

    vis_data = np.zeros((num_walkable, BOX_BYTES), dtype=np.uint8)
    r2_limit = RADIUS_TILES * RADIUS_TILES

    for w_idx, (ptx, pty) in enumerate(walkable_coords):
        if w_idx % 300 == 0:
            print(f"Baking tile {w_idx}/{num_walkable} ({w_idx*100//num_walkable}%)...")
        
        p_surf = tile_centers_3d[(ptx, pty)]
        torch_3d = Vector((p_surf.x, p_surf.y, max(0.0, p_surf.z) + 1.2))

        bit_idx = 0
        for dy in range(-RADIUS_TILES, RADIUS_TILES + 1):
            tty = pty + dy
            for dx in range(-RADIUS_TILES, RADIUS_TILES + 1):
                ttx = ptx + dx
                
                if dx * dx + dy * dy <= r2_limit and 0 <= ttx < FOG_MAP_W and 0 <= tty < FOG_MAP_H:
                    if abs(dx) <= 1 and abs(dy) <= 1:
                        # Immediate neighborhood is always visible
                        vis_data[w_idx, bit_idx >> 3] |= (1 << (bit_idx & 7))
                    else:
                        # Multi-sample: tile is visible if ANY of its 4 sample points is visible
                        samples = tile_samples_3d[(ttx, tty)]
                        is_visible = False
                        for s_pt in samples:
                            to_target = s_pt - torch_3d
                            dist_3d = to_target.length
                            if dist_3d > 0.1:
                                dir_3d = to_target / dist_3d
                                hit, _, _, _ = bvh.ray_cast(torch_3d, dir_3d, dist_3d - 0.20)
                                if hit is None:
                                    is_visible = True
                                    break
                        if is_visible:
                            vis_data[w_idx, bit_idx >> 3] |= (1 << (bit_idx & 7))
                
                bit_idx += 1

    elapsed = time.time() - start_time
    print(f"Bake finished in {elapsed:.2f} seconds!")

    # Write C source and header
    inc_file = repo_root / "include" / "baked_visibility.h"
    src_file = repo_root / "source" / "baked_visibility.c"

    with open(inc_file, "w") as f:
        f.write("#ifndef BAKED_VISIBILITY_H\n#define BAKED_VISIBILITY_H\n\n")
        f.write("#include <nds.h>\n\n")
        f.write(f"#define BAKED_VIS_MAP_W {FOG_MAP_W}\n")
        f.write(f"#define BAKED_VIS_MAP_H {FOG_MAP_H}\n")
        f.write(f"#define BAKED_VIS_RADIUS {RADIUS_TILES}\n")
        f.write(f"#define BAKED_VIS_BOX_SIZE {BOX_SIZE}\n")
        f.write(f"#define BAKED_VIS_BOX_BYTES {BOX_BYTES}\n")
        f.write(f"#define BAKED_VIS_NUM_WALKABLE {num_walkable}\n\n")
        f.write("extern const int16_t g_baked_walkable_index[BAKED_VIS_MAP_H][BAKED_VIS_MAP_W];\n")
        f.write("extern const uint8_t g_baked_vis_masks[BAKED_VIS_NUM_WALKABLE][BAKED_VIS_BOX_BYTES];\n\n")
        f.write("#endif // BAKED_VISIBILITY_H\n")

    with open(src_file, "w") as f:
        f.write('#include "baked_visibility.h"\n\n')
        f.write("const int16_t g_baked_walkable_index[BAKED_VIS_MAP_H][BAKED_VIS_MAP_W] = {\n")
        for ty in range(FOG_MAP_H):
            f.write("    { " + ", ".join(f"{tile_walkable_index[ty, tx]:4d}" for tx in range(FOG_MAP_W)) + " },\n")
        f.write("};\n\n")
        
        f.write("const uint8_t g_baked_vis_masks[BAKED_VIS_NUM_WALKABLE][BAKED_VIS_BOX_BYTES] __attribute__((aligned(4))) = {\n")
        for w_idx in range(num_walkable):
            row_bytes = ", ".join(f"0x{b:02X}" for b in vis_data[w_idx])
            f.write(f"    {{ {row_bytes} }},\n")
        f.write("};\n")

    print(f"Wrote {inc_file} and {src_file}")

if __name__ == "__main__":
    bake_all()
