#include "enemy_laser.h"
#include "enemy_ai.h"

#define LASER_CORE   (RGB15(6, 30, 10) | BIT(15))     // the thin line
#define LASER_DIM    (RGB15(2, 14, 5) | BIT(15))      // checkered rim of the wide line
#define LASER_BODY   (RGB15(3, 24, 8) | BIT(15))
#define LASER_BRIGHT (RGB15(22, 31, 22) | BIT(15))    // lethal core

static inline void laser_px(uint16_t *buffer, int x, int y, uint16_t color) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    buffer[y * SCREEN_W + x] = color;
    dirty_row(y, x, x + 1);
}

static int laser_width(EnemyState state) {
    if (state == ENEMY_STATE_LASER_FIRE) return 3;
    if (state == ENEMY_STATE_LASER_FIX) return 2;
    return 0;
}

static void draw_laser(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
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

    int fx = (ox << 8) + 128;
    int fy = (oy << 8) + 128;
    for (int d = 1; d <= SHOOTER_LASER_LENGTH; d++) {
        fx += dir_x;
        fy += dir_y;
        int px = fx >> 8;
        int py = fy >> 8;
        if (w == 0) {
            laser_px(buffer, px, py, LASER_CORE);
            continue;
        }
        for (int o = -w; o <= w; o++) {
            int x = px + ((perp_x * o) >> 8);
            int y = py + ((perp_y * o) >> 8);
            int edge = o == w || o == -w;
            if (lethal) laser_px(buffer, x, y, edge ? LASER_BODY : LASER_BRIGHT);
            else if (edge) { if (((x + y) & 1) == 0) laser_px(buffer, x, y, LASER_DIM); }
            else laser_px(buffer, x, y, o == 0 ? LASER_CORE : LASER_BODY);
        }
    }
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
