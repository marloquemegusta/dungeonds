#include "projectiles.h"
#include <string.h>

EnemyProjectile g_enemy_projectiles[MAX_ENEMY_PROJECTILES];

void enemy_projectiles_init(void) {
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        g_enemy_projectiles[i].active = 0;
        g_enemy_projectiles[i].type = PROJ_NONE;
        g_enemy_projectiles[i].x = 0;
        g_enemy_projectiles[i].y = 0;
        g_enemy_projectiles[i].vx = 0;
        g_enemy_projectiles[i].vy = 0;
        g_enemy_projectiles[i].life = 0;
        g_enemy_projectiles[i].max_life = 0;
        g_enemy_projectiles[i].damage = 0;
    }
}

EnemyProjectile *enemy_projectile_spawn_linear(fixed x, fixed y, fixed vx, fixed vy, int damage, int life) {
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) {
            p->active = 1;
            p->type = PROJ_LINEAR_SLOW;
            p->x = x;
            p->y = y;
            p->vx = vx;
            p->vy = vy;
            p->damage = damage;
            p->life = life > 0 ? life : 120;
            p->max_life = p->life;
            return p;
        }
    }
    return NULL;
}

void enemy_projectiles_update(fixed player_x, fixed player_y) {
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) continue;

        if (p->type == PROJ_LINEAR_SLOW) {
            p->life--;
            if (p->life <= 0) {
                p->active = 0;
                continue;
            }

            fixed next_x = p->x + p->vx;
            fixed next_y = p->y + p->vy;

            if (!bullet_position_is_free(next_x, next_y)) {
                p->active = 0;
                continue;
            }

            p->x = next_x;
            p->y = next_y;

            if (!g_player_state.is_dead) {
                int dx = TO_INT(p->x - player_x);
                int dy = TO_INT(p->y - player_y);
                if (dx * dx + dy * dy <= 8 * 8) {
                    player_apply_damage(&g_player_state, p->damage);
                    p->active = 0;
                    continue;
                }
            }
        }
    }
}

void enemy_projectiles_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;

    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) continue;

        if (p->type == PROJ_LINEAR_SLOW) {
            int px = TO_INT(p->x);
            int py = TO_INT(p->y);
            int sx = px - cam_x;
            int sy = py - cam_y;

            if (sx >= 1 && sx < SCREEN_W - 1 && sy >= 1 && sy < SCREEN_H - 1) {
                uint16_t core_color = (RGB15(31, 31, 10) | BIT(15));  // bright yellow-white spark
                uint16_t halo_color = (RGB15(0, 28, 4) | BIT(15));    // necrotic green halo

                buffer[sy * SCREEN_W + sx] = core_color;
                buffer[(sy - 1) * SCREEN_W + sx] = halo_color;
                buffer[(sy + 1) * SCREEN_W + sx] = halo_color;
                buffer[sy * SCREEN_W + (sx - 1)] = halo_color;
                buffer[sy * SCREEN_W + (sx + 1)] = halo_color;
                dirty_rect(sx - 1, sy - 1, sx + 2, sy + 2);
            }
        }
    }
}
