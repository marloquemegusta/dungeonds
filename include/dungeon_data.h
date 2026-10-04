#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define TILE_W 16
#define TILE_H 16
#define DUNGEON_NUM_TILES 11

#define MAP_COLS 16
#define MAP_ROWS 12

// Tile identifiers
enum {
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
};

extern const uint16_t g_dungeon_tiles[11][TILE_W * TILE_H];
extern const uint8_t g_dungeon_map[MAP_ROWS][MAP_COLS];
extern const uint8_t g_dungeon_collision[MAP_ROWS][MAP_COLS];

#endif // DUNGEON_DATA_H
