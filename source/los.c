#include "los.h"
#include "diablo_dungeon.h"

static inline uint8_t get_collision_flags(int cx, int cy) {
    if ((uint32_t)cx >= COLLISION_W || (uint32_t)cy >= COLLISION_H) return 3;
    uint32_t index = (uint32_t)cy * COLLISION_W + (uint32_t)cx;
    return (g_dungeon_collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

int los_has_line_of_sight(int px0, int py0, int px1, int py1, int max_radius_px) {
    int dx = px1 - px0;
    int dy = py1 - py0;
    if (max_radius_px > 0) {
        int max_dist_sq = max_radius_px * max_radius_px;
        if (dx * dx + dy * dy > max_dist_sq) return 0;
    }

    int c0x = px0 / COLLISION_SCALE;
    int c0y = py0 / COLLISION_SCALE;
    int c1x = px1 / COLLISION_SCALE;
    int c1y = py1 / COLLISION_SCALE;

    int adx = c1x - c0x;
    int ady = c1y - c0y;
    int abs_dx = adx < 0 ? -adx : adx;
    int abs_dy = ady < 0 ? -ady : ady;
    int sx = adx < 0 ? -1 : 1;
    int sy = ady < 0 ? -1 : 1;
    int err = (abs_dx > abs_dy ? abs_dx : -abs_dy) / 2;

    int x = c0x, y = c0y;
    while (1) {
        if (x == c1x && y == c1y) return 1;
        if (get_collision_flags(x, y) == 3) return 0;

        int e2 = err;
        if (e2 > -abs_dx) { err -= abs_dy; x += sx; }
        if (e2 < abs_dy)  { err += abs_dx; y += sy; }
    }
}
