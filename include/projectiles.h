#ifndef PROJECTILES_H
#define PROJECTILES_H

#include <stdint.h>
#include <stdbool.h>
#include "gameplay.h"

typedef enum {
    PROJ_NONE = 0,
    PROJ_LINEAR_SLOW
} ProjectileType;

#define MAX_ENEMY_PROJECTILES 32   // 10 enemies x bursts of 3 with ~150 frames of flight

typedef struct {
    int active;
    ProjectileType type;
    fixed x;          // 8.8 fixed world pos X
    fixed y;          // 8.8 fixed world pos Y
    fixed vx;         // 8.8 fixed world velocity X
    fixed vy;         // 8.8 fixed world velocity Y
    int life;         // remaining lifetime in frames
    int max_life;     // total lifetime
    int height;       // px above the ground at which it flies (the muzzle height)
} EnemyProjectile;

extern EnemyProjectile g_enemy_projectiles[MAX_ENEMY_PROJECTILES];

void enemy_projectiles_init(void);

// Spawns a slow linear projectile moving with velocity (vx, vy)
EnemyProjectile *enemy_projectile_spawn_linear(fixed x, fixed y, fixed vx, fixed vy, int height, int life);

// Updates all enemy projectiles: movement, wall collision, player collision, lifetime.
void enemy_projectiles_update(fixed player_x, fixed player_y);

// Renders enemy projectiles (dots/sparks) onto the screen buffer
void enemy_projectiles_render(uint16_t *buffer, int cam_x, int cam_y);

#endif // PROJECTILES_H
