#!/usr/bin/env python3
"""
generate_dungeon_bg_tiles.py - Generates indexed 8bpp tileset, palette, and full tilemap
for DungeonDS hardware background scrolling.
"""
import os, sys, re, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(ROOT, 'source', 'dungeon_data.c'), 'r', encoding='utf-8') as f:
    text = f.read()

m_map = re.search(r'const uint8_t g_floor_map\[\d+\]\[\d+\] = \{(.*?)\};', text, re.DOTALL)
floor_map = np.array([int(x) for x in re.findall(r'\b\d+\b', m_map.group(1))], dtype=np.uint8).reshape((36, 36))

m_tiles = re.search(r'const uint16_t g_floor_tiles\[NUM_FLOOR_TILES\]\[FLOOR_TILE_W \* FLOOR_TILE_H\][^=]*=\s*\{(.*?)\n\};', text, re.DOTALL)
tile_vals = [int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', m_tiles.group(1))]
floor_tiles = np.array(tile_vals, dtype=np.uint16).reshape((5, 16, 32))

m_obj = re.search(r'const uint8_t g_obj_map\[\d+\]\[\d+\] = \{(.*?)\};', text, re.DOTALL)
obj_map = np.array([int(x) for x in re.findall(r'\b\d+\b', m_obj.group(1))], dtype=np.uint8).reshape((36, 36))

m_bounds = re.search(r'const uint8_t g_obj_shadow_bounds\[NUM_OBJ_SPRITES\]\[4\]\s*=\s*\{(.*?)\};', text, re.DOTALL)
shadow_bounds = np.array([int(x) for x in re.findall(r'\b\d+\b', m_bounds.group(1))], dtype=np.uint8).reshape((40, 4))

m_masks = re.search(r'const uint8_t g_obj_shadow_masks\[NUM_OBJ_SPRITES\]\[OBJ_SHADOW_W \* OBJ_SHADOW_H / 2\]\s*=\s*\{(.*?)\n\};', text, re.DOTALL)
shadow_masks = np.array([int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', m_masks.group(1))], dtype=np.uint8).reshape((40, 96*96//2))

m_sprites = re.search(r'const uint16_t g_obj_sprites\[NUM_OBJ_SPRITES\]\[OBJ_SPRITE_W \* OBJ_SPRITE_H\][^=]*=\s*\{(.*?)\nconst', text, re.DOTALL)
sprite_blocks = re.findall(r'\{(.*?)\}', m_sprites.group(1), re.DOTALL)

CACHE_X0, CACHE_Y0, CACHE_W, CACHE_H = -576, -96, 1152, 664
cache = np.zeros((CACHE_H, CACHE_W), dtype=np.uint16)

# 1) Composite floor diamonds
for row in range(36):
    for col in range(36):
        t = floor_map[row, col]
        if t == 255: continue
        left = (col - row) * 16 - 16 - CACHE_X0
        top = (col + row) * 8 - 8 - CACHE_Y0
        src = floor_tiles[t]
        for sy in range(16):
            dy = top + sy
            if dy < 0 or dy >= CACHE_H: continue
            for sx in range(32):
                dx = left + sx
                if dx < 0 or dx >= CACHE_W: continue
                c = src[sy, sx]
                if c & 0x8000: cache[dy, dx] = c

# 2) Composite static shadows
def apply_shadow(color, coverage):
    keep = 255 - (int(coverage) * 160) // 255
    r = ((color & 0x1F) * keep) // 255
    g = (((color >> 5) & 0x1F) * keep) // 255
    b = (((color >> 10) & 0x1F) * keep) // 255
    return r | (g << 5) | (b << 10) | 0x8000

for row in range(36):
    for col in range(36):
        obj = obj_map[row, col]
        if obj == 0: continue
        id = obj - 1
        left = (col - row) * 16 - 48 - CACHE_X0
        top = (col + row) * 8 - 48 - CACHE_Y0
        b = shadow_bounds[id]
        sx0, sy0, bw, bh = int(b[0]), int(b[1]), int(b[2]), int(b[3])
        mask = shadow_masks[id]
        for y in range(sy0, sy0 + bh):
            dy = top + y
            if dy < 0 or dy >= CACHE_H: continue
            for x in range(sx0, sx0 + bw):
                dx = left + x
                if dx < 0 or dx >= CACHE_W: continue
                pixel = y * 96 + x
                packed = mask[pixel >> 1]
                nibble = (packed >> 4) if (pixel & 1) else (packed & 0x0F)
                if nibble:
                    c = cache[dy, dx]
                    if c != 0: cache[dy, dx] = apply_shadow(c, nibble * 17)

# 3) Composite perimeter walls (id < 24)
for row in range(36):
    for col in range(36):
        obj = obj_map[row, col]
        if obj == 0: continue
        id = obj - 1
        if id >= 24: continue
        nums = [int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', sprite_blocks[id])]
        left = (col - row) * 16 - 48 - CACHE_X0
        top = (col + row) * 8 - 48 - CACHE_Y0
        for y in range(96):
            dy = top + y
            if dy < 0 or dy >= CACHE_H: continue
            for x in range(96):
                dx = left + x
                if dx < 0 or dx >= CACHE_W: continue
                c = nums[y * 96 + x]
                if c & 0x8000: cache[dy, dx] = c

# Build palette: index 0 is 0x0000 (black / transparent)
unique_colors = [0x0000] + [int(c) for c in sorted(np.unique(cache)) if int(c) != 0]
color_to_idx = {c: i for i, c in enumerate(unique_colors)}

# Pad palette to 256 colors
while len(unique_colors) < 256:
    unique_colors.append(0x0000)

zero_tile = tuple([0] * 64)
tiles_list = [zero_tile]
tiles_dict = {zero_tile: 0}

MAP_TILES_X = CACHE_W // 8  # 144
MAP_TILES_Y = CACHE_H // 8  # 76
tilemap = np.zeros((MAP_TILES_Y, MAP_TILES_X), dtype=np.uint16)

for ty in range(MAP_TILES_Y):
    for tx in range(MAP_TILES_X):
        block = cache[ty*8:(ty+1)*8, tx*8:(tx+1)*8]
        idx_block = tuple(color_to_idx[int(c)] for c in block.flatten())
        if idx_block not in tiles_dict:
            tiles_dict[idx_block] = len(tiles_list)
            tiles_list.append(idx_block)
        tilemap[ty, tx] = tiles_dict[idx_block]

TARGET_MAX_TILES = 448
if len(tiles_list) > TARGET_MAX_TILES:
    def to_rgb(c):
        return np.array([(c & 0x1F), ((c >> 5) & 0x1F), ((c >> 10) & 0x1F)], dtype=np.float32)
    pal_rgb = np.array([to_rgb(c) for c in unique_colors])
    unq_rgb = np.array([[pal_rgb[idx] for idx in t] for t in tiles_list])

    pair_dists = []
    for i in range(1, len(tiles_list)):
        for j in range(i+1, len(tiles_list)):
            mse = np.mean((unq_rgb[i] - unq_rgb[j])**2)
            if mse < 5.0:
                pair_dists.append((mse, i, j))
    pair_dists.sort()

    active = set(range(len(tiles_list)))
    remap = {i: i for i in range(len(tiles_list))}
    needed = len(tiles_list) - TARGET_MAX_TILES
    merges = 0
    for mse, i, j in pair_dists:
        root_i = remap[i]
        root_j = remap[j]
        if root_i != root_j and root_i in active and root_j in active:
            active.remove(root_j)
            for k in range(len(tiles_list)):
                if remap[k] == root_j:
                    remap[k] = root_i
            merges += 1
            if merges == needed:
                break

    sorted_active = sorted(list(active))
    compact_map = {old: new for new, old in enumerate(sorted_active)}
    new_tiles_list = [tiles_list[old] for old in sorted_active]
    for ty in range(MAP_TILES_Y):
        for tx in range(MAP_TILES_X):
            old_idx = int(tilemap[ty, tx])
            merged_old = remap[old_idx]
            tilemap[ty, tx] = compact_map[merged_old]
    tiles_list = new_tiles_list
    print(f'[OK] Compressed tileset to {len(tiles_list)} tiles (merges: {merges}).')

print(f'[OK] Final tileset: {len(tiles_list)} unique 8x8 tiles for {MAP_TILES_X}x{MAP_TILES_Y} tilemap.')

# Emit dungeon_bg_tiles.h
header_path = os.path.join(ROOT, 'include', 'dungeon_bg_tiles.h')
with open(header_path, 'w', encoding='utf-8') as h:
    h.write(f'''#ifndef DUNGEON_BG_TILES_H
#define DUNGEON_BG_TILES_H

#include <nds.h>

#define DUNGEON_BG_PALETTE_SIZE 256
#define DUNGEON_BG_NUM_TILES {len(tiles_list)}
#define DUNGEON_BG_MAP_WIDTH_TILES {MAP_TILES_X}
#define DUNGEON_BG_MAP_HEIGHT_TILES {MAP_TILES_Y}

extern const uint16_t g_dungeon_bg_palette[DUNGEON_BG_PALETTE_SIZE];
extern const uint8_t g_dungeon_bg_tiles[DUNGEON_BG_NUM_TILES][64];
extern const uint16_t g_dungeon_bg_map[DUNGEON_BG_MAP_HEIGHT_TILES][DUNGEON_BG_MAP_WIDTH_TILES];

#endif // DUNGEON_BG_TILES_H
''')

# Emit dungeon_bg_tiles.c
source_path = os.path.join(ROOT, 'source', 'dungeon_bg_tiles.c')
with open(source_path, 'w', encoding='utf-8') as c:
    c.write('#include "dungeon_bg_tiles.h"\n\n')
    c.write('const uint16_t g_dungeon_bg_palette[DUNGEON_BG_PALETTE_SIZE] __attribute__((aligned(4))) = {\n')
    for i, col in enumerate(unique_colors):
        c.write(f'0x{col:04X},' if (i + 1) % 16 == 0 else f'0x{col:04X}, ')
        if (i + 1) % 16 == 0: c.write('\n')
    c.write('};\n\n')

    c.write(f'const uint8_t g_dungeon_bg_tiles[DUNGEON_BG_NUM_TILES][64] __attribute__((aligned(4))) = {{\n')
    for t_idx, t in enumerate(tiles_list):
        c.write(f'    // Tile {t_idx}\n    {{\n        ')
        for i, px in enumerate(t):
            c.write(f'0x{px:02X},' if (i + 1) % 16 == 0 else f'0x{px:02X}, ')
            if (i + 1) % 16 == 0: c.write('\n        ' if i + 1 < 64 else '\n')
        c.write('    },\n')
    c.write('};\n\n')

    c.write(f'const uint16_t g_dungeon_bg_map[DUNGEON_BG_MAP_HEIGHT_TILES][DUNGEON_BG_MAP_WIDTH_TILES] __attribute__((aligned(4))) = {{\n')
    for row in range(MAP_TILES_Y):
        c.write('    { ')
        for col in range(MAP_TILES_X):
            c.write(f'{tilemap[row, col]}, ')
        c.write('},\n')
    c.write('};\n')

print('[OK] Generated include/dungeon_bg_tiles.h and source/dungeon_bg_tiles.c successfully!')
