import bpy
import math
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree
import bmesh
from pathlib import Path
import os
import time

def bake_lightgrid():
    start_time = time.time()
    repo_root = Path(__file__).resolve().parent.parent
    fbx_path = repo_root / r"assets\environment\scifi_dungeon\tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx"
    coll_path = repo_root / r"assets\scifi_baked\scifi_coll.npy"

    coll = np.load(coll_path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    
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

    ortho_scale = 38.0 # Matched exactly to _blender_bake_scifi.py!
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
    RADIUS_TILES = 10 # 10 tiles radius = 80 pixels
    GRID_DIM = RADIUS_TILES * 2 + 1 # 21 x 21 cells
    TOTAL_CELLS = GRID_DIM * GRID_DIM # 441 cells
    BYTES_PER_TILE = (TOTAL_CELLS + 1) // 2 # 221 bytes (packed 4-bit nibbles)

    # Function to get 3D surface point for any pixel (px, py)
    def get_surface_point(px, py):
        u_pix = ((px + 0.5) / world_w - 0.5) * ortho_scale
        v_pix = (0.5 - (py + 0.5) / world_h) * view_h
        ray_s = cam_pos + cam_right * u_pix + cam_up * v_pix
        hit_co, hit_norm, _, _ = bvh.ray_cast(ray_s, cam_forward, 250.0)
        if hit_co is not None:
            return hit_co, hit_norm
        t_g = -ray_s.z / cam_forward.z
        return ray_s + cam_forward * t_g, Vector((0, 0, 1))

    print("Precomputing 3D surface points for tile centers...")
    tile_centers_3d = {}
    tile_norms_3d = {}

    for ty in range(FOG_MAP_H):
        for tx in range(FOG_MAP_W):
            co, norm = get_surface_point(tx * 8 + 4, ty * 8 + 4)
            tile_centers_3d[(tx, ty)] = co
            tile_norms_3d[(tx, ty)] = norm

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

    light_data = np.zeros((num_walkable, BYTES_PER_TILE), dtype=np.uint8)
    r2_limit = RADIUS_TILES * RADIUS_TILES

    for w_idx, (ptx, pty) in enumerate(walkable_coords):
        if w_idx % 300 == 0:
            print(f"Baking light grid {w_idx}/{num_walkable} ({w_idx*100//num_walkable}%)...")
        
        p_surf = tile_centers_3d[(ptx, pty)]
        torch_3d = Vector((p_surf.x, p_surf.y, max(0.0, p_surf.z) + 1.2))

        cell_idx = 0
        for dy in range(-RADIUS_TILES, RADIUS_TILES + 1):
            tty = pty + dy
            for dx in range(-RADIUS_TILES, RADIUS_TILES + 1):
                ttx = ptx + dx
                
                light_val = 0
                if dx * dx + dy * dy <= r2_limit and 0 <= ttx < FOG_MAP_W and 0 <= tty < FOG_MAP_H:
                    t_surf = tile_centers_3d[(ttx, tty)]
                    to_target = t_surf - torch_3d
                    dist_3d = to_target.length
                    
                    if dist_3d < 0.2:
                        light_val = 15
                    else:
                        dir_3d = to_target / dist_3d
                        hit, _, _, _ = bvh.ray_cast(torch_3d, dir_3d, dist_3d - 0.15)
                        if hit is None:
                            # 3D Line of Sight clear!
                            # Smoothstep falloff across 10 tiles radius
                            dist_tiles = math.sqrt(dx * dx + dy * dy)
                            u = dist_tiles / 10.0
                            if u < 1.0:
                                t = 1.0 - u
                                smooth = t * t * (3.0 - 2.0 * t)
                                light_val = int(round(smooth * 15.0))
                                if light_val > 15: light_val = 15
                                if light_val < 0: light_val = 0

                # Store 4-bit nibble into packed array
                byte_pos = cell_idx >> 1
                if (cell_idx & 1) == 0:
                    light_data[w_idx, byte_pos] = (light_data[w_idx, byte_pos] & 0xF0) | (light_val & 0x0F)
                else:
                    light_data[w_idx, byte_pos] = (light_data[w_idx, byte_pos] & 0x0F) | ((light_val & 0x0F) << 4)

                cell_idx += 1

    elapsed = time.time() - start_time
    print(f"Bake finished in {elapsed:.2f} seconds!")

    # Write C header
    inc_file = repo_root / "include" / "smooth_lightmap.h"
    src_file = repo_root / "source" / "smooth_lightmap.c"

    # Read the existing C code logic from smooth_lightmap.c (from line static uint16_t s_shaded_palette)
    tail_code = ""
    if src_file.exists():
        with open(src_file, "r") as f:
            content = f.read()
            marker = "static uint16_t s_shaded_palette"
            idx = content.find(marker)
            if idx != -1:
                tail_code = content[idx:]

    with open(inc_file, "w") as f:
        f.write("#ifndef SMOOTH_LIGHTMAP_H\n#define SMOOTH_LIGHTMAP_H\n\n")
        f.write("#include <nds.h>\n\n")
        f.write("#ifndef SCREEN_W\n#define SCREEN_W 256\n#endif\n")
        f.write("#ifndef SCREEN_H\n#define SCREEN_H 192\n#endif\n\n")
        f.write(f"#define LIGHTMAP_MAP_W {FOG_MAP_W}\n")
        f.write(f"#define LIGHTMAP_MAP_H {FOG_MAP_H}\n")
        f.write(f"#define LIGHTMAP_RADIUS {RADIUS_TILES}\n")
        f.write(f"#define LIGHTMAP_GRID_DIM {GRID_DIM}\n")
        f.write(f"#define LIGHTMAP_BYTES_PER_TILE {BYTES_PER_TILE}\n")
        f.write(f"#define LIGHTMAP_NUM_WALKABLE {num_walkable}\n\n")
        f.write("extern const int16_t g_lightmap_walkable_index[LIGHTMAP_MAP_H][LIGHTMAP_MAP_W];\n")
        f.write("extern const uint8_t g_lightmap_data[LIGHTMAP_NUM_WALKABLE][LIGHTMAP_BYTES_PER_TILE];\n\n")
        f.write("void render_smooth_torch_lighting(uint16_t *buffer, int cam_x, int cam_y, int player_px, int player_py);\n\n")
        f.write("#endif // SMOOTH_LIGHTMAP_H\n")

    with open(src_file, "w") as f:
        f.write('#include "smooth_lightmap.h"\n')
        f.write('#include "dungeon_bg_tiles.h"\n\n')
        f.write("const int16_t g_lightmap_walkable_index[LIGHTMAP_MAP_H][LIGHTMAP_MAP_W] = {\n")
        for ty in range(FOG_MAP_H):
            f.write("    { " + ", ".join(f"{tile_walkable_index[ty, tx]:4d}" for tx in range(FOG_MAP_W)) + " },\n")
        f.write("};\n\n")
        
        f.write("const uint8_t g_lightmap_data[LIGHTMAP_NUM_WALKABLE][LIGHTMAP_BYTES_PER_TILE] __attribute__((aligned(4))) = {\n")
        for w_idx in range(num_walkable):
            row_bytes = ", ".join(f"0x{b:02X}" for b in light_data[w_idx])
            f.write(f"    {{ {row_bytes} }},\n")
        f.write("};\n\n")

        if tail_code:
            f.write(tail_code)

    print(f"Successfully baked and preserved C runtime in {src_file}!")

if __name__ == "__main__":
    bake_lightgrid()
