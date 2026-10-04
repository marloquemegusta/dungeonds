#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define FLOOR_TILE_SIZE 24
#define NUM_FLOOR_TILES 5

#define WALL_SPRITE_W 32
#define WALL_SPRITE_H 48
#define NUM_WALL_TYPES 6

// World Map in World Coordinates
// Dual screen continuous vertical span:
// Top screen: Y in [camera_y - 192, camera_y)
// Bottom screen: Y in [camera_y, camera_y + 192)
#define WORLD_MAP_COLS 20
#define WORLD_MAP_ROWS 24
#define WORLD_W (WORLD_MAP_COLS * FLOOR_TILE_SIZE) // 480 px
#define WORLD_H (WORLD_MAP_ROWS * FLOOR_TILE_SIZE) // 576 px

// Floor Tiles
enum {
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
};

// Wall Types
enum {
    WALL_CRYPT = 0,
    WALL_BUTTRESS = 1,
    WALL_OSSUARY = 2,
    PILLAR_BROKEN = 3,
    PILLAR_SOUL = 4,
    ARCH_RUINS = 5
};

typedef struct {
    int16_t x;       // Foot base center X
    int16_t y;       // Foot base center Y (for depth sorting)
    uint8_t type;    // Wall / Pillar type
    uint8_t solid_r; // Collision radius
} DungeonProp;

#define MAX_DUNGEON_PROPS 128

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_SIZE * FLOOR_TILE_SIZE];
extern const uint16_t g_wall_sprites[NUM_WALL_TYPES][WALL_SPRITE_W * WALL_SPRITE_H];
extern const uint8_t g_world_floor_map[WORLD_MAP_ROWS][WORLD_MAP_COLS];

extern const int g_dungeon_prop_count;
extern const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS];

#endif // DUNGEON_DATA_H
