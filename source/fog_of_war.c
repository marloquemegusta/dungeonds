#include "fog_of_war.h"
#include "baked_visibility.h"
#include <string.h>

uint8_t g_fog_explored[FOG_MAP_BYTES] __attribute__((aligned(4)));
uint8_t g_fog_visible[FOG_MAP_BYTES] __attribute__((aligned(4)));

static inline uint8_t get_collision_flags(int cx, int cy) {
    if ((uint32_t)cx >= COLLISION_W || (uint32_t)cy >= COLLISION_H) return 3;
    uint32_t index = (uint32_t)cy * COLLISION_W + (uint32_t)cx;
    return (g_dungeon_collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

void fog_init(int spawn_px, int spawn_py) {
    memset(g_fog_explored, 0, sizeof(g_fog_explored));
    memset(g_fog_visible, 0, sizeof(g_fog_visible));
    fog_update(spawn_px, spawn_py);
}

__attribute__((target("arm"), optimize("O3"), noinline))
int fog_update(int player_px, int player_py) {
    int ptx = player_px >> 3;
    int pty = player_py >> 3;
    if ((uint32_t)ptx >= FOG_MAP_W || (uint32_t)pty >= FOG_MAP_H) return 0;

    static int s_last_ptx = -999;
    static int s_last_pty = -999;
    if (ptx == s_last_ptx && pty == s_last_pty) return 0;
    s_last_ptx = ptx;
    s_last_pty = pty;

    memset(g_fog_visible, 0, sizeof(g_fog_visible));

    int16_t w_idx = g_baked_walkable_index[pty][ptx];
    if (w_idx < 0) {
        for (int r = 1; r <= 3; r++) {
            if (pty - r >= 0 && g_baked_walkable_index[pty - r][ptx] >= 0) { w_idx = g_baked_walkable_index[pty - r][ptx]; pty -= r; break; }
            if (pty + r < FOG_MAP_H && g_baked_walkable_index[pty + r][ptx] >= 0) { w_idx = g_baked_walkable_index[pty + r][ptx]; pty += r; break; }
            if (ptx - r >= 0 && g_baked_walkable_index[pty][ptx - r] >= 0) { w_idx = g_baked_walkable_index[pty][ptx - r]; ptx -= r; break; }
            if (ptx + r < FOG_MAP_W && g_baked_walkable_index[pty][ptx + r] >= 0) { w_idx = g_baked_walkable_index[pty][ptx + r]; ptx += r; break; }
        }
    }
    if (w_idx < 0) return 0;

    const uint8_t *mask = g_baked_vis_masks[w_idx];
    int newly_revealed = 0;
    int bit_idx = 0;

    for (int dy = -BAKED_VIS_RADIUS; dy <= BAKED_VIS_RADIUS; dy++) {
        int tty = pty + dy;
        for (int dx = -BAKED_VIS_RADIUS; dx <= BAKED_VIS_RADIUS; dx++) {
            int ttx = ptx + dx;
            if ((mask[bit_idx >> 3] >> (bit_idx & 7)) & 1) {
                if ((uint32_t)ttx < FOG_MAP_W && (uint32_t)tty < FOG_MAP_H) {
                    uint32_t idx = (uint32_t)tty * FOG_MAP_W + (uint32_t)ttx;
                    g_fog_visible[idx >> 3] |= (uint8_t)(1u << (idx & 7));
                    if (!((g_fog_explored[idx >> 3] >> (idx & 7)) & 1)) {
                        g_fog_explored[idx >> 3] |= (uint8_t)(1u << (idx & 7));
                        newly_revealed = 1;
                    }
                }
            }
            bit_idx++;
        }
    }
    return newly_revealed;
}

int fog_has_line_of_sight(int x0, int y0, int x1, int y1) {
    int dx = x1 - x0;
    int dy = y1 - y0;
    int max_dist_sq = (FOG_VISION_RADIUS_TILES * 8) * (FOG_VISION_RADIUS_TILES * 8);
    if (dx * dx + dy * dy > max_dist_sq) return 0;

    int c0x = x0 / COLLISION_SCALE;
    int c0y = y0 / COLLISION_SCALE;
    int c1x = x1 / COLLISION_SCALE;
    int c1y = y1 / COLLISION_SCALE;

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

void draw_fog_penumbra(uint16_t *buffer, int cam_x, int cam_y) {
    (void)buffer;
    (void)cam_x;
    (void)cam_y;
}
