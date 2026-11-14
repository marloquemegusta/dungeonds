#include "pickups.h"
#include "collision.h"
#include "hud_icons_gfx.h"

#define HEAL_PICKUP_RECYCLE_BELOW_PX 400 // [TUNABLE-PLACEHOLDER]
#define HEAL_PICKUP_HOVER_PX 3           // base height above ground shadow

typedef struct { fixed x, y; int active; } HealPickup;
static HealPickup s_pickups[HEAL_PICKUP_MAX_ACTIVE];
static uint32_t s_rng = 1;
static uint32_t s_anim_tick = 0;

void pickups_init(uint32_t seed) {
    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) s_pickups[i].active = 0;
    s_rng = seed ? seed : 1u;
    s_anim_tick = 0;
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
    s_anim_tick++;
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
    static const int8_t bob_lut[16] = {
        0, 0, -1, -1, -2, -2, -2, -1, -1, 0, 1, 1, 2, 2, 1, 1
    };
    const int bob_y = bob_lut[(s_anim_tick >> 2) & 15];
    const uint16_t shadow_col = RGB15(4, 3, 3) | BIT(15);
    const int half_w = HUD_ICON_W >> 1;

    for (int i = 0; i < HEAL_PICKUP_MAX_ACTIVE; i++) {
        HealPickup *p = &s_pickups[i];
        if (!p->active) continue;
        int cx = TO_INT(p->x) - cam_x;
        int cy = TO_INT(p->y) - cam_y;
        int x0 = cx - half_w;
        int y0 = cy - HUD_ICON_H - HEAL_PICKUP_HOVER_PX + bob_y;
        if (x0 >= SCREEN_W || x0 + HUD_ICON_W <= 0 || cy + 1 <= 0 || y0 >= SCREEN_H) continue;

        // Subtle ground shadow beneath the levitating heart.
        for (int sy = cy - 1; sy <= cy; sy++) {
            if ((unsigned)sy >= SCREEN_H) continue;
            dirty_row(sy, cx - 3, cx + 4);
            for (int sx = cx - 3; sx <= cx + 3; sx++) {
                if ((unsigned)sx < SCREEN_W) buffer[sy * SCREEN_W + sx] = shadow_col;
            }
        }

        for (int gy = 0; gy < HUD_ICON_H; gy++) {
            int sy = y0 + gy;
            if ((unsigned)sy >= SCREEN_H) continue;
            dirty_row(sy, x0, x0 + HUD_ICON_W);
            const uint16_t *row = &g_hud_heart_full[gy * HUD_ICON_W];
            for (int gx = 0; gx < HUD_ICON_W; gx++) {
                uint16_t c = row[gx];
                if (!c) continue;
                int sx = x0 + gx;
                if ((unsigned)sx < SCREEN_W) buffer[sy * SCREEN_W + sx] = c;
            }
        }
    }
}
