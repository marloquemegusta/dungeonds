#include "pickups.h"
#include "collision.h"

#define HEAL_PICKUP_RECYCLE_BELOW_PX 400 // [TUNABLE-PLACEHOLDER]

typedef struct { fixed x, y; int active; } HealPickup;
static HealPickup s_pickups[HEAL_PICKUP_MAX_ACTIVE];
static uint32_t s_rng = 1;

void pickups_init(uint32_t seed) {
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) s_pickups[i].active = 0;
    s_rng = seed ? seed : 1u;
}

void pickups_shift_y(int dy_px) {
    fixed shift = TO_FIXED(dy_px);
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++)
        if (s_pickups[i].active) s_pickups[i].y += shift;
}

void pickups_enemy_killed(const Enemy *enemy) {
    if (!enemy) return;
    s_rng = s_rng * 1664525u + 1013904223u;
    if ((s_rng % HEAL_PICKUP_CHANCE_DENOMINATOR) != 0) return;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        if (s_pickups[i].active) continue;
        s_pickups[i].x = enemy->x;
        s_pickups[i].y = enemy->y;
        s_pickups[i].active = 1;
        return;
    }
}

void pickups_update(fixed player_x, fixed player_y, fixed tide_y, PlayerState *player) {
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        HealPickup *p = &s_pickups[i];
        if (!p->active) continue;
        if (p->y >= tide_y) { p->active = 0; continue; }
        if (p->y > player_y + TO_FIXED(HEAL_PICKUP_RECYCLE_BELOW_PX)) {
            p->active = 0;
            continue;
        }
        int dx = TO_INT(p->x - player_x);
        int dy = TO_INT(p->y - player_y);
        if (dx * dx + GROUND_DY2(dy) > HEAL_PICKUP_RADIUS * HEAL_PICKUP_RADIUS) continue;
        if (player && player->hp < player->max_hp) player->hp++;
        p->active = 0;
    }
}

void pickups_render(uint16_t *buffer, int cam_x, int cam_y) {
    uint16_t fill = RGB15(3, 31, 10) | BIT(15);
    uint16_t edge = RGB15(31, 31, 22) | BIT(15);
    int half = HEAL_PICKUP_SIZE / 2;
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        HealPickup *p = &s_pickups[i];
        if (!p->active) continue;
        int cx = TO_INT(p->x) - cam_x;
        int cy = TO_INT(p->y) - cam_y;
        if (cx < -half || cx >= SCREEN_W + half || cy < -half || cy >= SCREEN_H + half) continue;
        for (int dy = -half; dy < half; dy++) {
            int sy = cy + dy;
            if ((unsigned)sy >= SCREEN_H) continue;
            int x0 = (dy == 0) ? cx - half : cx - 1;
            int x1 = (dy == 0) ? cx + half : cx + 1;
            dirty_row(sy, x0, x1);
            for (int x = x0; x < x1; x++) {
                if ((unsigned)x >= SCREEN_W) continue;
                buffer[sy * SCREEN_W + x] = (x == cx || dy == 0 || dy == -half || dy == half - 1) ? edge : fill;
            }
        }
    }
}
