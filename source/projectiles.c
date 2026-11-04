#include "projectiles.h"
#include <string.h>

#define PROJECTILE_HIT_RADIUS 8      // ground px around the player's centre

EnemyProjectile g_enemy_projectiles[MAX_ENEMY_PROJECTILES];

void enemy_projectiles_init(void) {
    memset(g_enemy_projectiles, 0, sizeof(g_enemy_projectiles));
}

EnemyProjectile *enemy_projectile_spawn_linear(fixed x, fixed y, fixed vx, fixed vy, int height, int life) {
    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) {
            p->active = 1;
            p->type = PROJ_LINEAR_SLOW;
            p->x = x;
            p->y = y;
            p->vx = vx;
            p->vy = vy;
            p->height = height;
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

            // One hit per shot (DESIGN.md 4.2); i-frames are handled by player_take_hit.
            if (!g_player_state.is_dead) {
                int dx = TO_INT(p->x - player_x);
                int dy = TO_INT(p->y - player_y);
                if (dx * dx + GROUND_DY2(dy) <= PROJECTILE_HIT_RADIUS * PROJECTILE_HIT_RADIUS) {
                    player_take_hit(&g_player_state);
                    p->active = 0;
                    continue;
                }
            }
        }
    }
}

// `cam_x/cam_y` and `depth` (the bolt's ground y) let walls hide the bolt like they hide actors.
static inline void shot_px(uint16_t *buffer, int x, int y, uint16_t color, int cam_x, int cam_y, int depth) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    if (world_pixel_hidden(x + cam_x, y + cam_y, depth)) return;
    buffer[y * SCREEN_W + x] = color;
    dirty_row(y, x, x + 1);
}

// Necrotic bolt: bright head, green body and a short fading tail. The shot flies at the
// height of the weapon muzzle, so it is drawn `height` pixels above its ground position.
void enemy_projectiles_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;

    const uint16_t head = RGB15(31, 31, 12) | BIT(15);
    const uint16_t body = RGB15(2, 28, 6) | BIT(15);
    const uint16_t tail = RGB15(0, 17, 3) | BIT(15);

    for (int i = 0; i < MAX_ENEMY_PROJECTILES; i++) {
        EnemyProjectile *p = &g_enemy_projectiles[i];
        if (!p->active) continue;

        int depth = TO_INT(p->y);
        int sx = TO_INT(p->x) - cam_x;
        int sy = TO_INT(p->y) - p->height - cam_y;
        // Tail points back along the velocity (about 2 frames of flight).
        int tx = -(p->vx >> 7);
        int ty = -(p->vy >> 7);

        shot_px(buffer, sx + 2 * tx, sy + 2 * ty, tail, cam_x, cam_y, depth);
        shot_px(buffer, sx + tx, sy + ty, body, cam_x, cam_y, depth);
        shot_px(buffer, sx, sy, head, cam_x, cam_y, depth);
        shot_px(buffer, sx + 1, sy, body, cam_x, cam_y, depth);
        shot_px(buffer, sx - 1, sy, body, cam_x, cam_y, depth);
        shot_px(buffer, sx, sy + 1, body, cam_x, cam_y, depth);
        shot_px(buffer, sx, sy - 1, body, cam_x, cam_y, depth);
    }
}
