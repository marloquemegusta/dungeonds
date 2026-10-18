#include "projectiles.h"
#include "los.h"
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
        g_enemy_projectiles[i].target_x = 0;
        g_enemy_projectiles[i].target_y = 0;
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
            p->target_x = 0;
            p->target_y = 0;
            return p;
        }
    }
    return NULL;
}

EnemyProjectile *enemy_projectile_spawn_hitscan(fixed x, fixed y, fixed target_x, fixed target_y, int damage, fixed player_x, fixed player_y) {
    int hit = 0;
    int wx0 = TO_INT(x);
    int wy0 = TO_INT(y);
    int wx1 = TO_INT(target_x);
    int wy1 = TO_INT(target_y);

    if (los_has_line_of_sight(wx0, wy0, wx1, wy1, 0)) {
        if (!g_player_state.is_dead) {
            int px = TO_INT(player_x);
            int py = TO_INT(player_y);
            int dx = wx1 - px;
            int dy = wy1 - py;
            if (dx * dx + dy * dy <= 16 * 16) {
                hit = 1;
            }
        }
    }

    if (hit) {
        player_apply_damage(&g_player_state, damage);
    }

    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) {
            p->active = 1;
            p->type = PROJ_HITSCAN_TRACER;
            p->x = x;
            p->y = y;
            p->vx = 0;
            p->vy = 0;
            p->damage = damage;
            p->life = 4;
            p->max_life = 4;
            p->target_x = target_x;
            p->target_y = target_y;
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
        } else if (p->type == PROJ_HITSCAN_TRACER) {
            p->life--;
            if (p->life <= 0) {
                p->active = 0;
                continue;
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
            }
        } else if (p->type == PROJ_HITSCAN_TRACER) {
            int x0 = TO_INT(p->x) - cam_x;
            int y0 = TO_INT(p->y) - cam_y;
            int x1 = TO_INT(p->target_x) - cam_x;
            int y1 = TO_INT(p->target_y) - cam_y;

            uint16_t tracer_color = (RGB15(31, 18, 6) | BIT(15)); // hot tracer ray

            int dx = x1 - x0;
            int dy = y1 - y0;
            int adx = dx < 0 ? -dx : dx;
            int ady = dy < 0 ? -dy : dy;
            int sx = dx < 0 ? -1 : 1;
            int sy = dy < 0 ? -1 : 1;
            int err = (adx > ady ? adx : -ady) / 2;

            int cur_x = x0, cur_y = y0;
            for (int step = 0; step < 120; step++) {
                if (cur_x >= 0 && cur_x < SCREEN_W && cur_y >= 0 && cur_y < SCREEN_H) {
                    if ((step & 1) == 0) {
                        buffer[cur_y * SCREEN_W + cur_x] = tracer_color;
                    }
                }
                if (cur_x == x1 && cur_y == y1) break;
                int e2 = err;
                if (e2 > -adx) { err -= ady; cur_x += sx; }
                if (e2 < ady)  { err += adx; cur_y += sy; }
            }
        }
    }
}
