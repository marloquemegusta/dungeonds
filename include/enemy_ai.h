#ifndef ENEMY_AI_H
#define ENEMY_AI_H

#include "gameplay.h"

// Updates AI state machines for all active enemies:
// - Skeleton FSM: CHASE <-> ATTACK
// - Charger FSM: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE (STUNNED by a wall or a shotgun hit)
// - Ojo del Tribunal FSM (shooter type): CHASE -> TRACK (40 frames, the band follows the hero) -> LOCK (20 frames, frozen line)
//   -> SENTENCE -> COOLDOWN -> CHASE (DESIGN.md 6.10)
// Handles separation repulsion between enemies.
// Handles obstacle navigation with sweep_position / sliding.
void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y);

// World position of the enemy's muzzle and its height above the ground (px); the Ojo sentence beam leaves from it.
void enemy_muzzle(const Enemy *e, fixed *mx, fixed *my, int *mh);
void enemy_ai_set_strip_mode(int enabled);

// Level of detail: enemies outside the world window shown by the two screens (cam_x..cam_x+256 wide,
// cam_top_y..cam_bottom_y tall, plus ENEMY_AI_VIEW_MARGIN) run their walking AI every 2nd frame with a doubled step.
// Never calling it keeps every enemy at full rate.
#define ENEMY_AI_VIEW_MARGIN 64
void enemy_ai_set_view(int cam_x, int cam_top_y, int cam_bottom_y);

#endif // ENEMY_AI_H
