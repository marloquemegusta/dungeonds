#ifndef ENEMY_AI_H
#define ENEMY_AI_H

#include "gameplay.h"

// Updates AI state machines for all active enemies:
// - Skeleton FSM: CHASE <-> ATTACK
// - Charger FSM: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE (STUNNED by a wall or a shotgun hit)
// - Shooter FSM: POSITION -> LASER_AIM -> LASER_FIX -> LASER_FIRE -> COOLDOWN -> POSITION
// Handles separation repulsion between enemies.
// Handles obstacle navigation with sweep_position / sliding.
void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y);

// World position of the enemy's muzzle and its height above the ground (px); the shooter's laser leaves from it.
void enemy_muzzle(const Enemy *e, fixed *mx, fixed *my, int *mh);
void enemy_ai_set_strip_mode(int enabled);

#endif // ENEMY_AI_H
