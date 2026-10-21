#!/usr/bin/env python3
"""
bake_isometric_shooter_bl.py
Full pipeline to bake isometric_shooter_bl map files into Nintendo DS runtime C sources:
1. World background image -> 256-color 8bpp tiles & tilemap (dungeon_bg_tiles.c / .h)
2. 2-bit collision grid -> packed bytes (diablo_dungeon.c / .h)
3. Wall occlusion -> sorted RLE runs (dungeon_occlusion.c / .h)
"""

import os
import re
import sys
import numpy as np
from PIL import Image

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_DIR = os.path.join(WT, 'assets', 'sprites', 'dungeon', 'isometric_shooter_bl')

# Map dimensions: 1536x857 -> padded to 1536x864 (multiple of 8)
ORIG_W = 1536
ORIG_H = 857
TILE = 8
WORLD_W = 1536
WORLD_H = ((ORIG_H + TILE - 1) // TILE) * TILE # 864

COLLISION_SCALE = 4
COLLISION_W = WORLD_W // COLLISION_SCALE # 384
COLLISION_H = WORLD_H // COLLISION_SCALE # 216
COLLISION_BYTES = (COLLISION_W * COLLISION_H * 2 + 7) // 8 # 20736 bytes

SPAWN_PIXEL_X = 754
SPAWN_PIXEL_Y = 466

print(f"=== BAKING ISOMETRIC SHOOTER BL MAP ===")
print(f"World: {WORLD_W}x{WORLD_H} (padded from {ORIG_W}x{ORIG_H})")
print(f"Collision: {COLLISION_W}x{COLLISION_H} ({COLLISION_BYTES} bytes)")
print(f"Spawn: ({SPAWN_PIXEL_X}, {SPAWN_PIXEL_Y})")

# ---------------------------------------------------------------------------
# 1. BAKE BACKGROUND TILES (dungeon_bg_tiles.h / .c)
# ---------------------------------------------------------------------------
world_png = os.path.join(MAP_DIR, 'world.png')
im_world = Image.open(world_png).convert('RGB')
padded_world = Image.new('RGB', (WORLD_W, WORLD_H), (0, 0, 0))
padded_world.paste(im_world, (0, 0))

# Quantize to 255 colors (color 0 reserved for void black)
im_p = padded_world.quantize(colors=255, method=Image.MEDIANCUT)
pal_raw = im_p.getpalette()[:255*3]

pal_bgr = [0x0000]
for i in range(0, len(pal_raw), 3):
    r5 = (pal_raw[i] >> 3) & 0x1F
    g5 = (pal_raw[i+1] >> 3) & 0x1F
    b5 = (pal_raw[i+2] >> 3) & 0x1F
    pal_bgr.append(r5 | (g5 << 5) | (b5 << 10) | 0x8000)

while len(pal_bgr) < 256:
    pal_bgr.append(0x0000)

indexed = np.array(im_p, dtype=np.uint8) + 1
# Detect black void in world image
arr_rgb = np.array(padded_world)
black_mask = (arr_rgb[:,:,0] < 5) & (arr_rgb[:,:,1] < 5) & (arr_rgb[:,:,2] < 5)
indexed[black_mask] = 0

map_w_tiles = WORLD_W // TILE
map_h_tiles = WORLD_H // TILE

tile_ids = {}
tiles = []
blank_tile = bytes([0] * 64)
tile_ids[blank_tile] = 0
tiles.append(blank_tile)

tilemap = np.zeros((map_h_tiles, map_w_tiles), dtype=np.uint16)
for ty in range(map_h_tiles):
    for tx in range(map_w_tiles):
        cell = indexed[ty*8:(ty+1)*8, tx*8:(tx+1)*8]
        t_bytes = bytes(cell.flatten())
        if t_bytes not in tile_ids:
            tid = len(tiles)
            tile_ids[t_bytes] = tid
            tiles.append(t_bytes)
        tilemap[ty, tx] = tile_ids[t_bytes]

num_tiles = len(tiles)
print(f"Tiles generated: {num_tiles} unique 8x8 tiles (Atlas size: {num_tiles * 64} bytes)")

# Write dungeon_bg_tiles.h
header_bg = f"""#ifndef DUNGEON_BG_TILES_H
#define DUNGEON_BG_TILES_H

#include <nds.h>

#define DUNGEON_BG_PALETTE_SIZE 256
#define DUNGEON_BG_NUM_TILES {num_tiles}
#define DUNGEON_BG_MAP_WIDTH_TILES {map_w_tiles}
#define DUNGEON_BG_MAP_HEIGHT_TILES {map_h_tiles}

extern const uint16_t g_dungeon_bg_palette[DUNGEON_BG_PALETTE_SIZE];
extern const uint8_t g_dungeon_bg_tiles[DUNGEON_BG_NUM_TILES][64];
extern const uint16_t g_dungeon_bg_map[DUNGEON_BG_MAP_HEIGHT_TILES][DUNGEON_BG_MAP_WIDTH_TILES];

#endif // DUNGEON_BG_TILES_H
"""
with open(os.path.join(WT, 'include', 'dungeon_bg_tiles.h'), 'w', encoding='utf-8') as f:
    f.write(header_bg)

# Write dungeon_bg_tiles.c
with open(os.path.join(WT, 'source', 'dungeon_bg_tiles.c'), 'w', encoding='utf-8') as f:
    f.write('#include "dungeon_bg_tiles.h"\n\n')
    f.write('const uint16_t g_dungeon_bg_palette[256] __attribute__((aligned(4))) = {\n')
    for start in range(0, 256, 16):
        f.write("    " + ", ".join(f"0x{x:04X}" for x in pal_bgr[start:start+16]) + ",\n")
    f.write('};\n\n')
    
    f.write(f'const uint8_t g_dungeon_bg_tiles[{num_tiles}][64] __attribute__((aligned(4))) = {{\n')
    for t_bytes in tiles:
        f.write("    {\n        ")
        f.write(", ".join(f"0x{b:02X}" for b in t_bytes))
        f.write("\n    },\n")
    f.write('};\n\n')
    
    f.write(f'const uint16_t g_dungeon_bg_map[{map_h_tiles}][{map_w_tiles}] __attribute__((aligned(4))) = {{\n')
    for row in tilemap:
        f.write("    { " + ", ".join(str(int(x)) for x in row) + " },\n")
    f.write('};\n')

print(f"dungeon_bg_tiles.c and .h written!")

# ---------------------------------------------------------------------------
# 2. BAKE COLLISION (diablo_dungeon.h / .c)
# ---------------------------------------------------------------------------
coll_png = os.path.join(MAP_DIR, 'collision.png')
im_c = Image.open(coll_png).convert('L')
arr_c = np.array(im_c)

padded_c = np.zeros((WORLD_H, WORLD_W), dtype=np.uint8)
padded_c[:ORIG_H, :ORIG_W] = arr_c

coll_grid = np.zeros((COLLISION_H, COLLISION_W), dtype=np.uint8)
for cy in range(COLLISION_H):
    y0 = cy * COLLISION_SCALE
    y1 = min((cy + 1) * COLLISION_SCALE, WORLD_H)
    for cx in range(COLLISION_W):
        x0 = cx * COLLISION_SCALE
        x1 = min((cx + 1) * COLLISION_SCALE, WORLD_W)
        cell = padded_c[y0:y1, x0:x1]
        # White (>= 128) is walkable (0)
        # Black (< 128) is solid wall (3)
        if np.mean(cell >= 128) > 0.40:
            coll_grid[cy, cx] = 0
        else:
            coll_grid[cy, cx] = 3

walk_cnt = int(np.sum(coll_grid == 0))
solid_cnt = int(np.sum(coll_grid == 3))
print(f"Collision grid {COLLISION_W}x{COLLISION_H}: WALKABLE={walk_cnt} ({walk_cnt*100//(COLLISION_W*COLLISION_H)}%), SOLID={solid_cnt}")

# Pack 2 bits per cell
coll_flat = coll_grid.flatten().astype(np.uint8)
if coll_flat.size % 4:
    coll_flat = np.pad(coll_flat, (0, 4 - coll_flat.size % 4))
coll_packed = (coll_flat[0::4] | (coll_flat[1::4] << 2) |
               (coll_flat[2::4] << 4) | (coll_flat[3::4] << 6))

header_diablo = f"""#ifndef DIABLO_DUNGEON_H
#define DIABLO_DUNGEON_H

#include <nds.h>

#define WORLD_W {WORLD_W}
#define WORLD_H {WORLD_H}
#define COLLISION_W {COLLISION_W}
#define COLLISION_H {COLLISION_H}
#define COLLISION_SCALE {COLLISION_SCALE}
#define DUNGEON_OCCLUSION_SEGMENTS 1
#define COLLISION_BYTES {COLLISION_BYTES}

#define SPAWN_PIXEL_X {SPAWN_PIXEL_X}
#define SPAWN_PIXEL_Y {SPAWN_PIXEL_Y}

extern const uint8_t g_dungeon_collision[COLLISION_BYTES];

#endif // DIABLO_DUNGEON_H
"""
with open(os.path.join(WT, 'include', 'diablo_dungeon.h'), 'w', encoding='utf-8') as f:
    f.write(header_diablo)

with open(os.path.join(WT, 'source', 'diablo_dungeon.c'), 'w', encoding='utf-8') as f:
    f.write('#include "diablo_dungeon.h"\n\n')
    f.write(f'const uint8_t g_dungeon_collision[COLLISION_BYTES] = {{\n')
    for i in range(0, len(coll_packed), 32):
        chunk = ", ".join(f"0x{int(v):02X}" for v in coll_packed[i:i+32])
        f.write(f"    {chunk},\n")
    f.write('};\n')

print("diablo_dungeon.c and .h written!")

# ---------------------------------------------------------------------------
# 3. BAKE OCCLUSION (dungeon_occlusion.h / .c)
# ---------------------------------------------------------------------------
is_black_pixel = (arr_rgb[:,:,0] < 5) & (arr_rgb[:,:,1] < 5) & (arr_rgb[:,:,2] < 5)
is_wall = (padded_c < 128) & (~is_black_pixel)

foot_y = np.full((WORLD_H, WORLD_W), -1, dtype=np.int16)
for x in range(WORLD_W):
    walk_indices = np.where(padded_c[:, x] >= 128)[0]
    if len(walk_indices) == 0:
        continue
    for y in range(WORLD_H):
        if is_wall[y, x]:
            below = walk_indices[walk_indices > y]
            if len(below) > 0:
                foot_y[y, x] = below[0]
            else:
                foot_y[y, x] = walk_indices[-1]

runs = []
for y in range(WORLD_H):
    x = 0
    while x < WORLD_W:
        if foot_y[y, x] < 0:
            x += 1
            continue
        x0 = x
        min_d = foot_y[y, x]
        max_d = foot_y[y, x]
        while x < WORLD_W and foot_y[y, x] >= 0:
            d = foot_y[y, x]
            if max(max_d, d) - min(min_d, d) > 16:
                break
            min_d = min(min_d, d)
            max_d = max(max_d, d)
            x += 1
        if x - x0 >= 2:
            runs.append((x0, y, x - x0, int(max_d)))

num_runs = len(runs)
print(f"Generated {num_runs} occlusion runs!")

header_occ = f"""#ifndef DUNGEON_OCCLUSION_H
#define DUNGEON_OCCLUSION_H

#include <nds.h>
#include "diablo_dungeon.h"

typedef struct {{
    uint16_t x;
    uint16_t y;
    uint16_t length;
    int16_t depth;
}} DungeonOcclusionRun;

typedef struct {{
    int16_t x;
    int16_t y;
}} DungeonOcclusionSegmentOffset;

extern const DungeonOcclusionRun g_dungeon_occlusion_runs[];
extern const uint32_t g_dungeon_occlusion_run_count;
extern const DungeonOcclusionSegmentOffset g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS];

#endif // DUNGEON_OCCLUSION_H
"""
with open(os.path.join(WT, 'include', 'dungeon_occlusion.h'), 'w', encoding='utf-8') as f:
    f.write(header_occ)

with open(os.path.join(WT, 'source', 'dungeon_occlusion.c'), 'w', encoding='utf-8') as f:
    f.write('#include "dungeon_occlusion.h"\n\n')
    f.write('const DungeonOcclusionRun g_dungeon_occlusion_runs[] __attribute__((aligned(4))) = {\n')
    for x0, y, length, d in runs:
        f.write(f"    {{{x0}, {y}, {length}, {d}}},\n")
    if not runs:
        f.write("    {0, 0, 0, -1},\n")
    f.write('};\n\n')
    f.write(f'const uint32_t g_dungeon_occlusion_run_count = {num_runs}u;\n\n')
    f.write('const DungeonOcclusionSegmentOffset g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS] = {\n')
    f.write('    {0, 0},\n')
    f.write('};\n')

print(f"dungeon_occlusion.c and .h written!")
print(f"=== BAKE COMPLETE! ===")
