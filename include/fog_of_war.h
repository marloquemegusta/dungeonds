#ifndef FOG_OF_WAR_H
#define FOG_OF_WAR_H

#include <nds.h>
#include <stdint.h>
#include <stdbool.h>
#include "diablo_dungeon.h"
#include "dungeon_bg_tiles.h"

#define FOG_MAP_W DUNGEON_BG_MAP_WIDTH_TILES   // 96
#define FOG_MAP_H DUNGEON_BG_MAP_HEIGHT_TILES  // 64
#define FOG_MAP_TILES (FOG_MAP_W * FOG_MAP_H)  // 6144
#define FOG_MAP_BYTES (FOG_MAP_TILES / 8)      // 768 bytes

#ifndef SCREEN_W
#define SCREEN_W 256
#endif
#ifndef SCREEN_H
#define SCREEN_H 192
#endif

#define FOG_VISION_RADIUS_TILES 12             // ~96 px (~5 meters)
#define FOG_VISION_RADIUS_CELLS 24             // 24 collision cells (4px each)

// Global fog bitmasks in EWRAM
extern uint8_t g_fog_explored[FOG_MAP_BYTES];
extern uint8_t g_fog_visible[FOG_MAP_BYTES];

// Initialize fog (clears memory and reveals spawn area)
void fog_init(int spawn_px, int spawn_py);

// Update fog for current player position; returns 1 if newly explored tiles revealed
int fog_update(int player_px, int player_py);

// Query if a tile is explored (revealed in memory)
static inline int fog_is_explored(int tx, int ty) {
    if ((uint32_t)tx >= FOG_MAP_W || (uint32_t)ty >= FOG_MAP_H) return 0;
    uint32_t idx = (uint32_t)ty * FOG_MAP_W + (uint32_t)tx;
    return (g_fog_explored[idx >> 3] >> (idx & 7)) & 1;
}

// Query if a tile is currently in active line-of-sight
static inline int fog_is_visible(int tx, int ty) {
    if ((uint32_t)tx >= FOG_MAP_W || (uint32_t)ty >= FOG_MAP_H) return 0;
    uint32_t idx = (uint32_t)ty * FOG_MAP_W + (uint32_t)tx;
    return (g_fog_visible[idx >> 3] >> (idx & 7)) & 1;
}

// Query if a world pixel point is in active line-of-sight
static inline int fog_is_point_visible(int px, int py) {
    if (px < 0 || px >= (FOG_MAP_W * 8) || py < 0 || py >= (FOG_MAP_H * 8)) return 0;
    return fog_is_visible(px >> 3, py >> 3);
}

// Check direct Line-Of-Sight between two world points
int fog_has_line_of_sight(int x0, int y0, int x1, int y1);

// Draw 50% dark stipple over explored-but-inactive tiles on the 16bpp actor buffer
void draw_fog_penumbra(uint16_t *buffer, int cam_x, int cam_y);

#endif // FOG_OF_WAR_H
