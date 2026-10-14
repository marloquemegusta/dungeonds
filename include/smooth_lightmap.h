#ifndef SMOOTH_LIGHTMAP_H
#define SMOOTH_LIGHTMAP_H

#include <nds.h>

#ifndef SCREEN_W
#define SCREEN_W 256
#endif
#ifndef SCREEN_H
#define SCREEN_H 192
#endif

#define LIGHTMAP_MAP_W 96
#define LIGHTMAP_MAP_H 64
#define LIGHTMAP_RADIUS 10
#define LIGHTMAP_GRID_DIM 21
#define LIGHTMAP_BYTES_PER_TILE 221
#define LIGHTMAP_NUM_WALKABLE 1614

extern const int16_t g_lightmap_walkable_index[LIGHTMAP_MAP_H][LIGHTMAP_MAP_W];
extern const uint8_t g_lightmap_data[LIGHTMAP_NUM_WALKABLE][LIGHTMAP_BYTES_PER_TILE];

void render_smooth_torch_lighting(uint16_t *buffer, int cam_x, int cam_y, int player_px, int player_py);

#endif // SMOOTH_LIGHTMAP_H
