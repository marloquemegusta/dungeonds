#include "enemy_laser.h"
#include "enemy_ai.h"
#include <nds.h>

#define LASER_CORE   (RGB15(6, 30, 10) | BIT(15))     // the thin line
#define LASER_DIM    (RGB15(2, 14, 5) | BIT(15))      // checkered rim of the wide line
#define LASER_BODY   (RGB15(3, 24, 8) | BIT(15))
#define LASER_BRIGHT (RGB15(22, 31, 22) | BIT(15))    // lethal core

// Painted x range per screen row of the beam being drawn: the dirty spans are bounding ranges, so
// one dirty_row() per touched row gives the same union as one call per pixel.
static uint32_t s_row_x0[SCREEN_H], s_row_x1[SCREEN_H];

static int laser_width(EnemyState state) {
    if (state == ENEMY_STATE_LASER_FIRE) return 3;
    if (state == ENEMY_STATE_LASER_FIX) return 2;
    return 0;
}

__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void draw_laser(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    int ox = TO_INT(mx) - cam_x;
    int oy = TO_INT(my) - mh - cam_y;
    int dir_x = e->aim_dir_x;      // 8.8 world step per ground px (the 2:1 ground makes dir_y shorter)
    int dir_y = e->aim_dir_y;

    // End point: skip the whole beam when it cannot reach this screen.
    int ex = ox + ((dir_x * SHOOTER_LASER_LENGTH) >> 8);
    int ey = oy + ((dir_y * SHOOTER_LASER_LENGTH) >> 8);
    if ((ox < 0 && ex < 0) || (ox >= SCREEN_W && ex >= SCREEN_W) ||
        (oy < 0 && ey < 0) || (oy >= SCREEN_H && ey >= SCREEN_H)) return;

    int w = laser_width(e->state);
    int lethal = e->state == ENEMY_STATE_LASER_FIRE;

    // Screen-space unit perpendicular (8.8): one division per beam, none per step.
    int perp_x = 0, perp_y = 256;
    if (w > 0) {
        int m2 = dir_x * dir_x + dir_y * dir_y;
        int m = 1;
        while ((m + 1) * (m + 1) <= m2) m++;               // m2 <= 2^17: this is at most ~362 steps, once per beam
        perp_x = (-dir_y * 256) / m;
        perp_y = (dir_x * 256) / m;
    }

    // The 2w+1 pixels of a step, once per beam: perpendicular offsets (same expression as always),
    // colour, and a dither mask (the dim rim of the wide, non-lethal line paints only (x + y) even).
    const int n = 2 * w + 1;
    int off_x[7], off_y[7], dither[7];
    uint16_t colour[7];
    if (w == 0) {
        off_x[0] = off_y[0] = dither[0] = 0;
        colour[0] = LASER_CORE;
    }
    for (int o = -w; w > 0 && o <= w; o++) {
        int k = o + w;
        int edge = o == w || o == -w;
        off_x[k] = (perp_x * o) >> 8;
        off_y[k] = (perp_y * o) >> 8;
        dither[k] = (!lethal && edge) ? 1 : 0;
        colour[k] = lethal ? (edge ? LASER_BODY : LASER_BRIGHT)
                           : (edge ? LASER_DIM : (o == 0 ? LASER_CORE : LASER_BODY));
    }
    for (int y = 0; y < SCREEN_H; y++) { s_row_x0[y] = SCREEN_W; s_row_x1[y] = 0; }

    int fx = (ox << 8) + 128;
    int fy = (oy << 8) + 128;
    for (int d = 1; d <= SHOOTER_LASER_LENGTH; d++) {
        fx += dir_x;
        fy += dir_y;
        int px = fx >> 8;
        int py = fy >> 8;
        // Steps whose centre is further off screen than the beam is wide paint nothing (|offset| <= w <= 3).
        if (px < -4 || px >= SCREEN_W + 4 || py < -4 || py >= SCREEN_H + 4) continue;
        const int inside = px >= 4 && px < SCREEN_W - 4 && py >= 4 && py < SCREEN_H - 4;
        for (int k = 0; k < n; k++) {
            int x = px + off_x[k];
            int y = py + off_y[k];
            if (dither[k] && ((x + y) & 1)) continue;
            if (!inside && ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H)) continue;
            buffer[(y << 8) + x] = colour[k];
            if (x < (int)s_row_x0[y]) s_row_x0[y] = (uint32_t)x;
            if (x >= (int)s_row_x1[y]) s_row_x1[y] = (uint32_t)(x + 1);
        }
    }
    for (int y = 0; y < SCREEN_H; y++)
        if (s_row_x1[y] > s_row_x0[y]) dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);
}

void enemy_lasers_render(uint16_t *buffer, const Enemy *enemies, int count, int cam_x, int cam_y) {
    if (!buffer || !enemies) return;
    for (int i = 0; i < count; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->type != ENEMY_TYPE_SHOOTER) continue;
        if (e->state != ENEMY_STATE_LASER_AIM && e->state != ENEMY_STATE_LASER_FIX &&
            e->state != ENEMY_STATE_LASER_FIRE) continue;
        draw_laser(buffer, e, cam_x, cam_y);
    }
}
