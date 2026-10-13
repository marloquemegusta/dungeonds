#ifndef DUNGEON_BG_TILES_H
#define DUNGEON_BG_TILES_H

#include <nds.h>

#define DUNGEON_BG_PALETTE_SIZE 256
#define DUNGEON_BG_NUM_TILES 22952
#define DUNGEON_BG_MAP_WIDTH_TILES 400
#define DUNGEON_BG_MAP_HEIGHT_TILES 240

extern const uint16_t g_dungeon_bg_palette[DUNGEON_BG_PALETTE_SIZE];
extern const uint8_t g_dungeon_bg_tiles[DUNGEON_BG_NUM_TILES][64];
extern const uint16_t g_dungeon_bg_map[DUNGEON_BG_MAP_HEIGHT_TILES][DUNGEON_BG_MAP_WIDTH_TILES];

#endif
