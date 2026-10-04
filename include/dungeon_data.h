#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

#define FLOOR_TILE_W 32
#define FLOOR_TILE_H 16
#define NUM_FLOOR_TILES 5

#define WALL_SPRITE_W 32
#define WALL_SPRITE_H 48
#define NUM_WALL_TYPES 8

#define WORLD_COLS 16
#define WORLD_ROWS 32
#define WORLD_W (WORLD_COLS * FLOOR_TILE_W) // 512 px
#define WORLD_H (WORLD_ROWS * FLOOR_TILE_H) // 512 px

// Floor Tile IDs
enum {
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
};

// Wall / Prop IDs
enum {
    WALL_CRYPT_FRONT = 0,
    WALL_BUTTRESS_FRONT = 1,
    WALL_OSSUARY_FRONT = 2,
    WALL_ARCH_FRONT = 3,
    WALL_CRYPT_SIDE = 4,
    WALL_BUTTRESS_SIDE = 5,
    PROP_BROKEN_PILLAR = 6,
    PROP_SOUL_PILLAR = 7
};

typedef struct {
    int16_t x;       // Center X
    int16_t y;       // Baseline Y (for sorting and collision)
    uint8_t type;    // Wall / Prop ID
    uint8_t solid_r; // Radius of collision
} DungeonProp;

#define MAX_DUNGEON_PROPS 128

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H];
extern const uint16_t g_wall_sprites[NUM_WALL_TYPES][WALL_SPRITE_W * WALL_SPRITE_H];
extern const uint8_t g_world_floor_map[WORLD_ROWS][WORLD_COLS];

extern const int g_dungeon_prop_count;
extern const DungeonProp g_dungeon_props[MAX_DUNGEON_PROPS];

#endif // DUNGEON_DATA_H
