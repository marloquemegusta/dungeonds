#!/usr/bin/env python3
"""
convert_dimetric_to_c.py - Converts dimetric floors and vertical walls into C arrays for DungeonDS.
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
        "W00_crypt_wall.png",
        "W01_buttress_wall.png",
        "W02_ossuary_wall.png",
        "W03_broken_pillar.png",
        "W04_soul_pillar.png",
        "W05_ruined_arch.png"
    ]

    with open("include/dungeon_data.h", "w", encoding="utf-8") as h:
        h.write(f"""#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define FLOOR_TILE_SIZE 24
#define NUM_FLOOR_TILES {len(floor_names)}

#define WALL_SPRITE_W 32
#define WALL_SPRITE_H 48
#define NUM_WALL_TYPES {len(wall_names)}

// World Map in World Coordinates
// Dual screen continuous vertical span:
// Top screen: Y in [camera_y - 192, camera_y)
// Bottom screen: Y in [camera_y, camera_y + 192)
#define WORLD_MAP_COLS 20
#define WORLD_MAP_ROWS 24
#define WORLD_W (WORLD_MAP_COLS * FLOOR_TILE_SIZE) // 480 px
#define WORLD_H (WORLD_MAP_ROWS * FLOOR_TILE_SIZE) // 576 px

// Floor Tiles
enum {{
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
}};

// Wall Types
enum {{
    WALL_CRYPT = 0,
    WALL_BUTTRESS = 1,
    WALL_OSSUARY = 2,
    PILLAR_BROKEN = 3,
    PILLAR_SOUL = 4,
    ARCH_RUINS = 5
}};

typedef struct {{
    int16_t x;       // Foot base center X
    int16_t y;       // Foot base center Y (for depth sorting)
    uint8_t type;    // Wall / Pillar type
    uint8_t solid_r; // Collision radius
}} DungeonProp;

#define MAX_DUNGEON_PROPS 64

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_SIZE * FLOOR_TILE_SIZE];
extern const uint16_t g_wall_sprites[NUM_WALL_TYPES][WALL_SPRITE_W * WALL_SPRITE_H];
extern const uint8_t g_world_floor_map[WORLD_MAP_ROWS][WORLD_MAP_COLS];

extern const int g_dungeon_prop_count;
extern const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS];

#endif // DUNGEON_DATA_H
""")

    with open("source/dungeon_data.c", "w", encoding="utf-8") as c:
        c.write("""#include "dungeon_data.h"

// 24x24 Dimetric Floor Tiles (cropped centered from 32x32)
const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_SIZE * FLOOR_TILE_SIZE] __attribute__((aligned(4))) = {
""")
        for idx, fn in enumerate(floor_names):
            p = os.path.join(tiles_dir, fn)
            im = Image.open(p).convert("RGBA")
            # Crop 24x24 center (from 32x32: box (4, 4, 28, 28))
            crop_im = im.crop((4, 4, 28, 28))
            pixels = list(crop_im.getdata())
            c.write(f"    // {fn}\n    {{\n        ")
            for i, (r, g, b, a) in enumerate(pixels):
                val = to_bgr555(r, g, b, a)
                c.write(f"0x{val:04X}, ")
                if (i + 1) % 24 == 0:
                    c.write("\n        ")
            c.write("},\n")
        c.write("};\n\n")

        c.write("""// 32x48 Vertical Walls and Props with Depth Occlusion
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
                if (i + 1) % 32 == 0:
                    c.write("\n        ")
            c.write("},\n")
        c.write("};\n\n")

        # World Floor Layout (20 cols x 24 rows)
        c.write("// World Floor Map (20 cols x 24 rows)\nconst uint8_t g_world_floor_map[WORLD_MAP_ROWS][WORLD_MAP_COLS] = {\n")
        for r in range(24):
            row = []
            for col in range(20):
                # Patterned floor layout
                dist_c = abs(col - 10) + abs(r - 12)
                if dist_c <= 3:
                    row.append(3) # Crimson ritual seal in center
                elif (col in [4, 5, 14, 15]) and (r in [6, 7, 16, 17]):
                    row.append(2) # Bone floor aisles
                elif (col % 4 == 0) or (r % 4 == 0):
                    row.append(1) # Obsidian slabs
                elif (col + r) % 2 == 0:
                    row.append(4) # Worn cobblestone
                else:
                    row.append(0) # Standard crypt flagstone
            c.write("    { " + ", ".join(f"{t}" for t in row) + " },\n")
        c.write("};\n\n")

        # Props list (perimeter walls + pillars with real footprint)
        props = []
        # North wall perimeter (r = 1, y = 36)
        for c_idx in range(1, 19):
            wtype = 2 if (c_idx in [5, 9, 14]) else (1 if c_idx % 3 == 0 else 0)
            props.append((c_idx * 24 + 12, 36, wtype, 12))
        # South wall perimeter (r = 22, y = 540)
        for c_idx in range(1, 19):
            wtype = 2 if (c_idx in [5, 9, 14]) else (1 if c_idx % 3 == 0 else 0)
            props.append((c_idx * 24 + 12, 540, wtype, 12))
        # West and East perimeter
        for r_idx in range(2, 22):
            props.append((36, r_idx * 24 + 12, 0, 12))
            props.append((444, r_idx * 24 + 12, 0, 12))

        # Interior pillars, broken columns & ruined arches
        props.append((120, 144, 3, 10)) # Broken pillar NW
        props.append((360, 144, 3, 10)) # Broken pillar NE
        props.append((120, 432, 4, 10)) # Soul pillar SW
        props.append((360, 432, 4, 10)) # Soul pillar SE
        props.append((240, 200, 5, 14)) # Ruined Arch North entrance
        props.append((240, 380, 5, 14)) # Ruined Arch South entrance
        props.append((180, 288, 3, 10)) # Broken pillar mid
        props.append((300, 288, 4, 10)) # Soul pillar mid

        c.write(f"const int g_dungeon_prop_count = {len(props)};\n")
        c.write(f"const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS] = {{\n")
        for p in props:
            c.write(f"    {{ {p[0]}, {p[1]}, {p[2]}, {p[3]} }},\n")
        c.write("};\n")

    print("[OK] Converted dimetric assets to C!")

if __name__ == "__main__":
    main()
