#ifndef DUNGEON_DATA_H
#define DUNGEON_DATA_H

#include <nds.h>

// Baked view preset: e30 (elevation 30 deg)
#define FLOOR_TILE_W 32
#define FLOOR_TILE_H 16
#define NUM_FLOOR_TILES 5

#define OBJ_SPRITE_W 96
#define OBJ_SPRITE_H 96
#define OBJ_SHADOW_W 96
#define OBJ_SHADOW_H 96
#define OBJ_ANCHOR_Y 48
#define NUM_OBJ_SPRITES 40

#define MAP_COLS 36
#define MAP_ROWS 36
#define MAP_VOID 255

enum {
    FLOOR_CRYPT = 0,
    FLOOR_OBSIDIAN = 1,
    FLOOR_BONE = 2,
    FLOOR_CRIMSON = 3,
    FLOOR_WORN = 4
};

enum {
    OBJ_WR_CRYPT = 0,
    OBJ_WC_CRYPT = 4,
    OBJ_WR_BUTTRESS = 8,
    OBJ_WC_BUTTRESS = 12,
    OBJ_WR_OSSUARY = 16,
    OBJ_WC_OSSUARY = 20,
    OBJ_P_SOUL = 24,
    OBJ_P_BROKEN = 28,
    OBJ_AR_ROW = 32,
    OBJ_AR_COL = 36
};

extern const uint16_t g_floor_tiles[NUM_FLOOR_TILES][FLOOR_TILE_W * FLOOR_TILE_H];
extern const uint16_t g_obj_sprites[NUM_OBJ_SPRITES][OBJ_SPRITE_W * OBJ_SPRITE_H];
extern const uint8_t g_obj_shadow_masks[NUM_OBJ_SPRITES][OBJ_SHADOW_W * OBJ_SHADOW_H / 2];
extern const uint8_t g_obj_shadow_bounds[NUM_OBJ_SPRITES][4];
extern const uint8_t g_floor_map[MAP_ROWS][MAP_COLS];
extern const uint8_t g_obj_map[MAP_ROWS][MAP_COLS];

#endif // DUNGEON_DATA_H
