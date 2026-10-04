#!/usr/bin/env python3
"""
convert_authentic_to_c.py - Converts authentic dimetric floors and correctly oriented walls to C.
Generates:
  - include/dungeon_data.h
  - source/dungeon_data.c
"""

import os
from PIL import Image

def to_bgr555(r, g, b, a=255):
    if a < 32:
        return 0
    return ((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10) | 0x8000

def main():
    tiles_dir = r"C:\codexlocal\dungeonds\assets\dungeon_tiles"
    
    floor_names = [
        "F00_crypt_floor.png",
        "F01_obsidian_floor.png",
        "F02_bone_floor.png",
        "F03_crimson_floor.png",
        "F04_worn_floor.png"
    ]
    
    wall_names = [
        "W00_crypt_wall_front.png",
        "W01_buttress_wall_front.png",
        "W02_ossuary_wall_front.png",
        "W03_arch_front.png",
        "W10_crypt_wall_side.png",
        "W11_buttress_wall_side.png",
        "P00_broken_pillar.png",
        "P01_soul_pillar.png"
    ]

    with open("include/dungeon_data.h", "w", encoding="utf-8") as h:
        h.write(f"""#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define FLOOR_TILE_W 32
#define FLOOR_TILE_H 16
#define NUM_FLOOR_TILES {len(floor_names)}

#define WALL_SPRITE_W 32
#define WALL_SPRITE_H 48
#define NUM_WALL_TYPES {len(wall_names)}

#define WORLD_COLS 16
#define WORLD_ROWS 32
#define WORLD_W (WORLD_COLS * FLOOR_TILE_W) // 512 px
#define WORLD_H (WORLD_ROWS * FLOOR_TILE_H) // 512 px

// Floor Tile IDs
enum {{
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
}};

// Wall / Prop IDs
enum {{
    WALL_CRYPT_FRONT = 0,
    WALL_BUTTRESS_FRONT = 1,
    WALL_OSSUARY_FRONT = 2,
    WALL_ARCH_FRONT = 3,
    WALL_CRYPT_SIDE = 4,
    WALL_BUTTRESS_SIDE = 5,
    PROP_BROKEN_PILLAR = 6,
    PROP_SOUL_PILLAR = 7
}};

typedef struct {{
    int16_t x;       // Center X
    int16_t y;       // Baseline Y (for sorting and collision)
    uint8_t type;    // Wall / Prop ID
    uint8_t solid_r; // Radius of collision
}} DungeonProp;

#define MAX_DUNGEON_PROPS 128

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H];
extern const uint16_t g_wall_sprites[NUM_WALL_TYPES][WALL_SPRITE_W * WALL_SPRITE_H];
extern const uint8_t g_world_floor_map[WORLD_ROWS][WORLD_COLS];

extern const int g_dungeon_prop_count;
extern const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS];

#endif // DUNGEON_DATA_H
""")

    with open("source/dungeon_data.c", "w", encoding="utf-8") as c:
        c.write("""#include "dungeon_data.h"

// 32x16 Dimetric Floor Tiles (2:1 aspect ratio matching 60 degree pitch)
const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H] __attribute__((aligned(4))) = {
""")
        for idx, fn in enumerate(floor_names):
            p = os.path.join(tiles_dir, fn)
            im = Image.open(p).convert("RGBA")
            pixels = list(im.getdata())
            c.write(f"    // {fn}\n    {{\n        ")
            for i, (r, g, b, a) in enumerate(pixels):
                val = to_bgr555(r, g, b, a)
                c.write(f"0x{val:04X}, ")
                if (i + 1) % 16 == 0:
                    c.write("\n        ")
            c.write("},\n")
        c.write("};\n\n")

        c.write("""// 32x48 Vertical Walls, Pillars and Arches with True Height & Depth
const uint16_t g_wall_sprites[NUM_WALL_TYPES][WALL_SPRITE_W * WALL_SPRITE_H] __attribute__((aligned(4))) = {
""")
        for idx, wn in enumerate(wall_names):
            p = os.path.join(tiles_dir, wn)
            im = Image.open(p).convert("RGBA")
            pixels = list(im.getdata())
            c.write(f"    // {wn}\n    {{\n        ")
            for i, (r, g, b, a) in enumerate(pixels):
                val = to_bgr555(r, g, b, a)
                c.write(f"0x{val:04X}, ")
                if (i + 1) % 16 == 0:
                    c.write("\n        ")
            c.write("},\n")
        c.write("};\n\n")

        # 16 cols x 32 rows floor map (512x512 px)
        c.write("// World Floor Map (16 cols x 32 rows)\nconst uint8_t g_world_floor_map[WORLD_ROWS][WORLD_COLS] = {\n")
        for r in range(32):
            row = []
            for col in range(16):
                # Central Ritual Sanctuary (rows 12..20, cols 5..10)
                dist_r = abs(r - 16)
                dist_c = abs(col - 8)
                if dist_r <= 2 and dist_c <= 2:
                    row.append(3) # Crimson ritual seal
                elif dist_r <= 4 and dist_c <= 4:
                    row.append(2) # Bone inlay mosaic
                elif (col % 4 == 0) or (r % 4 == 0):
                    row.append(1) # Obsidian slabs
                elif (col + r) % 2 == 0:
                    row.append(4) # Worn cobblestone
                else:
                    row.append(0) # Crypt flagstone
            c.write("    { " + ", ".join(f"{t}" for t in row) + " },\n")
        c.write("};\n\n")

        # Architectural placement: Real enclosing dungeon hall
        props = []
        # 1. Back/North Enclosing Wall (horizontal across X: cols 2..13 at row 4 -> Y = 64)
        for col in range(2, 14):
            wtype = 2 if col in [4, 8, 11] else (1 if col in [2, 13] else 0)
            props.append((col * 32 + 16, 64, wtype, 14))
        # Arch over north doorway
        props.append((8 * 32, 64, 3, 14))

        # 2. West Wall (vertical depth walls running north-south: col 2 -> X = 80, rows 5..27)
        for r in range(5, 28, 2):
            wtype = 5 if (r % 4 == 0) else 4
            props.append((80, r * 16, wtype, 12))

        # 3. East Wall (vertical depth walls: col 13 -> X = 432, rows 5..27)
        for r in range(5, 28, 2):
            wtype = 5 if (r % 4 == 0) else 4
            props.append((432, r * 16, wtype, 12))

        # 4. Front/South Wall (horizontal: cols 2..13 at row 28 -> Y = 448)
        for col in range(2, 14):
            if col in [7, 8]: continue # Open archway at south entrance
            wtype = 2 if col in [4, 11] else (1 if col in [2, 13] else 0)
            props.append((col * 32 + 16, 448, wtype, 14))
        props.append((8 * 32, 448, 3, 14)) # South entrance arch

        # 5. Grand Hall Columns and Soul Lantern Pillars
        props.append((160, 160, 7, 10)) # Soul Pillar NW
        props.append((352, 160, 7, 10)) # Soul Pillar NE
        props.append((160, 256, 6, 10)) # Broken Pillar Mid-W
        props.append((352, 256, 6, 10)) # Broken Pillar Mid-E
        props.append((160, 352, 7, 10)) # Soul Pillar SW
        props.append((352, 352, 7, 10)) # Soul Pillar SE

        c.write(f"const int g_dungeon_prop_count = {len(props)};\n")
        c.write(f"const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS] = {{\n")
        for p in props:
            c.write(f"    {{ {p[0]}, {p[1]}, {p[2]}, {p[3]} }},\n")
        c.write("};\n")

    print("[OK] Converted authentic dungeon assets to C!")

if __name__ == "__main__":
    main()
