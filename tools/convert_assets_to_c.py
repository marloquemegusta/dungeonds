#!/usr/bin/env python3
"""
convert_assets_to_c.py - Converts baked dungeon tiles & player sprite to C arrays for NDS.
Generates:
  - include/dungeon_data.h
  - source/dungeon_data.c
  - include/player_sprite.h
  - source/player_sprite.c
"""

import os
from PIL import Image

def to_bgr555(r, g, b, a=255):
    if a < 128:
        return 0
    return ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10) | 0x8000

def convert_tiles():
    print("[1/2] Converting Dungeon Tiles to C...")
    tiles_dir = r"C:\codexlocal\dungeonds\assets\dungeon_tiles"
    tile_files = sorted([f for f in os.listdir(tiles_dir) if f.endswith(".png")])
    
    num_tiles = len(tile_files)
    tile_w, tile_h = 16, 16
    
    with open("include/dungeon_data.h", "w", encoding="utf-8") as h:
        h.write(f"""#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define TILE_W 16
#define TILE_H 16
#define DUNGEON_NUM_TILES {num_tiles}

#define MAP_COLS 16
#define MAP_ROWS 12

// Tile identifiers
enum {{
    TILE_CRYPT_FLOOR = 0,
    TILE_OBSIDIAN_FLOOR = 1,
    TILE_BONE_FLOOR = 2,
    TILE_CRIMSON_FLOOR = 3,
    TILE_WORN_FLOOR = 4,
    TILE_CRYPT_WALL = 5,
    TILE_BUTTRESS_WALL = 6,
    TILE_OSSUARY_WALL = 7,
    TILE_BROKEN_PILLAR = 8,
    TILE_SOUL_PILLAR = 9,
    TILE_ARCH_RUINS = 10
}};

extern const uint16_t g_dungeon_tiles[{num_tiles}][TILE_W * TILE_H];
extern const uint8_t g_dungeon_map[MAP_ROWS][MAP_COLS];
extern const uint8_t g_dungeon_collision[MAP_ROWS][MAP_COLS];

#endif // DUNGEON_DATA_H
""")

    with open("source/dungeon_data.c", "w", encoding="utf-8") as c:
        c.write("""#include "dungeon_data.h"

// 16x16 15-bit BGR555 Tiles baked from Dreadhollow 3D
const uint16_t g_dungeon_tiles[DUNGEON_NUM_TILES][TILE_W * TILE_H] __attribute__((aligned(4))) = {
""")
        for idx, tf in enumerate(tile_files):
            p = os.path.join(tiles_dir, tf)
            im = Image.open(p).convert("RGBA")
            pixels = list(im.getdata())
            c.write(f"    // Tile {idx}: {tf}\n    {{\n        ")
            for i, (r, g, b, a) in enumerate(pixels):
                val = to_bgr555(r, g, b, a)
                c.write(f"0x{val:04X}, ")
                if (i + 1) % 16 == 0:
                    c.write("\n        ")
            c.write("},\n")
        c.write("};\n\n")

        # Layout for a varied ruined crypt room (16 cols x 12 rows = 256x192 px)
        # 0 = floor, walls around perimeter with ossuary and buttresses, broken pillars and ruins inside
        dungeon_map = [
            [6, 5, 5, 7, 5, 5, 6, 5, 5, 6, 5, 5, 7, 5, 5, 6],
            [5, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 5],
            [5, 0, 8, 0, 0, 2, 2, 0, 0, 2, 2, 0, 0, 8, 0, 5],
            [7, 0, 0, 0, 0, 2, 3, 0, 0, 3, 2, 0, 0, 0, 0, 7],
            [5, 0, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 9, 0, 0, 5],
            [5, 1, 0, 0, 0, 4, 4, 4, 4, 4, 0, 0, 0, 0, 1, 5],
            [6, 1, 0, 0, 0, 4, 10, 0, 0, 4, 0, 0, 0, 0, 1, 6],
            [5, 0, 0, 9, 0, 4, 0, 0, 0, 4, 0, 0, 9, 0, 0, 5],
            [7, 0, 0, 0, 0, 2, 3, 0, 0, 3, 2, 0, 0, 0, 0, 7],
            [5, 0, 8, 0, 0, 2, 2, 0, 0, 2, 2, 0, 0, 8, 0, 5],
            [5, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 5],
            [6, 5, 5, 7, 5, 5, 6, 5, 5, 6, 5, 5, 7, 5, 5, 6]
        ]

        c.write("// 16x12 Map layout (256x192 px)\nconst uint8_t g_dungeon_map[MAP_ROWS][MAP_COLS] = {\n")
        for row in dungeon_map:
            c.write("    { " + ", ".join(f"{t:2d}" for t in row) + " },\n")
        c.write("};\n\n")

        # Collision map: 1 if solid (wall >= 5, pillars >= 8), 0 if walkable floor
        c.write("// Collision map (1 = solid obstacle, 0 = walkable floor)\nconst uint8_t g_dungeon_collision[MAP_ROWS][MAP_COLS] = {\n")
        for row in dungeon_map:
            solid_row = [1 if t >= 5 else 0 for t in row]
            c.write("    { " + ", ".join(str(s) for s in solid_row) + " },\n")
        c.write("};\n")

def convert_player_sprite():
    print("[2/2] Converting Player Sprite to C...")
    sheet_path = r"C:\codexlocal\dungeonds\assets\characters\monster\monster_walk_readable.png"
    im = Image.open(sheet_path).convert("RGBA")
    
    res = 64
    num_dirs = 8
    num_frames = 8

    # We extract each 64x64 frame and convert to 15-bit BGR555
    with open("include/player_sprite.h", "w", encoding="utf-8") as h:
        h.write(f"""#ifndef PLAYER_SPRITE_H
#define PLAYER_SPRITE_H

#include <nds.h>

#define PLAYER_SPRITE_W 64
#define PLAYER_SPRITE_H 64
#define PLAYER_NUM_DIRS {num_dirs}
#define PLAYER_NUM_FRAMES {num_frames}

extern const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];

#endif // PLAYER_SPRITE_H
""")

    with open("source/player_sprite.c", "w", encoding="utf-8") as c:
        c.write("""#include "player_sprite.h"

// 64x64 BGR555 Frames in 8 directions (8 frames each)
// Color 0 = transparent (bit 15 = 0), non-zero = opaque (bit 15 = 1)
const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H] __attribute__((aligned(4))) = {
""")
        for d in range(num_dirs):
            c.write(f"    // Direction {d}\n    {{\n")
            for f in range(num_frames):
                box = (f * res, d * res, (f + 1) * res, (d + 1) * res)
                frame_img = im.crop(box)
                pixels = list(frame_img.getdata())
                c.write(f"        // Frame {f}\n        {{\n            ")
                for i, (r, g, b, a) in enumerate(pixels):
                    val = to_bgr555(r, g, b, a)
                    c.write(f"0x{val:04X}, ")
                    if (i + 1) % 16 == 0:
                        c.write("\n            ")
                c.write("},\n")
            c.write("    },\n")
        c.write("};\n")

if __name__ == "__main__":
    convert_tiles()
    convert_player_sprite()
    print("All C assets generated successfully!")
