#ifndef ENEMY_AI_H
#define ENEMY_AI_H

#include "gameplay.h"

void enemy_ai_init(void);

// Updates AI state machines for all active enemies:
// - Charger FSM: IDLE -> ALERT -> CHASE -> ATTACK -> CHASE (with SEARCH on lost LOS after ~3s)
// - Shooter FSM: IDLE -> ALERT -> POSITION -> AIM -> BURST -> COOLDOWN -> POSITION (with SEARCH on lost LOS after ~3s)
// Handles separation repulsion between enemies.
// Handles obstacle navigation with sweep_position / sliding.
// Handles burst shooting with linear lead prediction on player velocity.
void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y, fixed player_vx, fixed player_vy);

#endif // ENEMY_AI_H
