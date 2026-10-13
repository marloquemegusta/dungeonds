#include "fog_of_war.h"
#include <string.h>

uint8_t g_fog_explored[FOG_MAP_BYTES] __attribute__((aligned(4)));
uint8_t g_fog_visible[FOG_MAP_BYTES] __attribute__((aligned(4)));

#define NUM_FOV_RAYS 64

static const int8_t s_ray_dx[NUM_FOV_RAYS] = {
    24, 24, 24, 23, 22, 21, 20, 19,
    17, 15, 13, 11,  9,  7,  5,  2,
     0, -2, -5, -7, -9, -11, -13, -15,
    -17, -19, -20, -21, -22, -23, -24, -24,
    -24, -24, -24, -23, -22, -21, -20, -19,
    -17, -15, -13, -11, -9, -7, -5, -2,
     0,  2,  5,  7,  9, 11, 13, 15,
    17, 19, 20, 21, 22, 23, 24, 24,
};
static const int8_t s_ray_dy[NUM_FOV_RAYS] = {
     0,  2,  5,  7,  9, 11, 13, 15,
    17, 19, 20, 21, 22, 23, 24, 24,
    24, 24, 24, 23, 22, 21, 20, 19,
    17, 15, 13, 11,  9,  7,  5,  2,
     0, -2, -5, -7, -9, -11, -13, -15,
    -17, -19, -20, -21, -22, -23, -24, -24,
    -24, -24, -24, -23, -22, -21, -20, -19,
    -17, -15, -13, -11, -9, -7, -5, -2,
};

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
    memset(g_fog_visible, 0, sizeof(g_fog_visible));

    int pcx = player_px / COLLISION_SCALE;
    int pcy = player_py / COLLISION_SCALE;
    int newly_revealed = 0;

    for (int p = 0; p < NUM_FOV_RAYS; p++) {
        int target_dx = s_ray_dx[p];
        int target_dy = s_ray_dy[p];

        int x = pcx;
        int y = pcy;
        int target_x = pcx + target_dx;
        int target_y = pcy + target_dy;

        int adx = target_dx < 0 ? -target_dx : target_dx;
        int ady = target_dy < 0 ? -target_dy : target_dy;
        int sx = target_dx < 0 ? -1 : 1;
        int sy = target_dy < 0 ? -1 : 1;
        int err = (adx > ady ? adx : -ady) / 2;

        while (1) {
            if ((uint32_t)x >= COLLISION_W || (uint32_t)y >= COLLISION_H) break;

            int tx = x >> 1;
            int ty = y >> 1;
            if ((uint32_t)tx < FOG_MAP_W && (uint32_t)ty < FOG_MAP_H) {
                uint32_t idx = (uint32_t)ty * FOG_MAP_W + (uint32_t)tx;
                g_fog_visible[idx >> 3] |= (uint8_t)(1u << (idx & 7));
                if (!((g_fog_explored[idx >> 3] >> (idx & 7)) & 1)) {
                    g_fog_explored[idx >> 3] |= (uint8_t)(1u << (idx & 7));
                    newly_revealed = 1;
                }
            }

            if (get_collision_flags(x, y) == 3) break;
            if (x == target_x && y == target_y) break;

            int e2 = err;
            if (e2 > -adx) { err -= ady; x += sx; }
            if (e2 < ady)  { err += adx; y += sy; }
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

__attribute__((target("arm"), optimize("O3"), noinline))
void draw_fog_penumbra(uint16_t *buffer, int cam_x, int cam_y) {
    int start_tx = cam_x >> 3;
    int start_ty = cam_y >> 3;
    int fine_x = cam_x & 7;
    int fine_y = cam_y & 7;

    for (int by = 0; by < (SCREEN_H / 8 + 1); by++) {
        int ty = start_ty + by;
        int screen_y0 = by * 8 - fine_y;
        if (screen_y0 >= SCREEN_H) break;

        for (int bx = 0; bx < (SCREEN_W / 8 + 1); bx++) {
            int tx = start_tx + bx;
            int screen_x0 = bx * 8 - fine_x;
            if (screen_x0 >= SCREEN_W) break;

            if (fog_is_explored(tx, ty) && !fog_is_visible(tx, ty)) {
                if (screen_x0 >= 0 && screen_x0 + 8 <= SCREEN_W &&
                    screen_y0 >= 0 && screen_y0 + 8 <= SCREEN_H) {
                    uint32_t pat_even = ((screen_x0 + screen_y0) & 1) ? 0x80000000 : 0x00008000;
                    uint32_t pat_odd  = ((screen_x0 + screen_y0) & 1) ? 0x00008000 : 0x80000000;
                    for (int y = 0; y < 8; y++) {
                        uint32_t *dst = (uint32_t *)&buffer[(screen_y0 + y) * SCREEN_W + screen_x0];
                        uint32_t pat = (y & 1) ? pat_odd : pat_even;
                        dst[0] = pat;
                        dst[1] = pat;
                        dst[2] = pat;
                        dst[3] = pat;
                    }
                } else {
                    int y0 = screen_y0 < 0 ? -screen_y0 : 0;
                    int y1 = (screen_y0 + 8 > SCREEN_H) ? (SCREEN_H - screen_y0) : 8;
                    int x0 = screen_x0 < 0 ? -screen_x0 : 0;
                    int x1 = (screen_x0 + 8 > SCREEN_W) ? (SCREEN_W - screen_x0) : 8;

                    for (int y = y0; y < y1; y++) {
                        int sy = screen_y0 + y;
                        uint16_t *dst = &buffer[sy * SCREEN_W + screen_x0];
                        for (int x = x0; x < x1; x++) {
                            if (((screen_x0 + x + sy) & 1) == 0) {
                                dst[x] = (uint16_t)(RGB15(0, 0, 0) | BIT(15));
                            }
                        }
                    }
                }
            }
        }
    }
}
