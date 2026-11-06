#ifndef PICKUPS_H
#define PICKUPS_H

#include "gameplay.h"

#define HEAL_PICKUP_CHANCE_DENOMINATOR 12 // [TUNABLE-PLACEHOLDER] one drop per this many kills on average
#define HEAL_PICKUP_MAX_ACTIVE 4 // [TUNABLE-PLACEHOLDER] active pickup cap
#define HEAL_PICKUP_RADIUS 10 // [TUNABLE-PLACEHOLDER] pickup radius in ground pixels
#define HEAL_PICKUP_SIZE 8 // [TUNABLE-PLACEHOLDER] cross visual size in pixels

void pickups_init(uint32_t seed);
void pickups_shift_y(int dy_px);
void pickups_enemy_killed(const Enemy *enemy);
void pickups_update(fixed player_x, fixed player_y, fixed tide_y, PlayerState *player);
void pickups_render(uint16_t *buffer, int cam_x, int cam_y);

#endif
