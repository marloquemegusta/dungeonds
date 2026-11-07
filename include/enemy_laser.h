#ifndef ENEMY_LASER_H
#define ENEMY_LASER_H

#include <stdint.h>
#include "gameplay.h"

// Shooter laser (DESIGN.md 6.9.1). The beam has no state of its own: it is the shooter's FSM
// (ENEMY_STATE_LASER_AIM / LASER_FIX / LASER_FIRE, enemy_ai.c) that follows the player, locks and
// hurts. This only draws it, with the same pixel-line method as the player's aim laser but in green:
//   AIM  thin 1 px line that follows the player
//   FIX  locked and wider (5 px, checkered rim), the last SHOOTER_LASER_FIX_FRAMES of the charge
//   FIRE bright 7 px beam while it is lethal
// Cost per beam is bounded: one loop of at most SHOOTER_LASER_LENGTH steps with at most 7 pixels
// per step; a beam that cannot touch the screen is skipped before the loop.
void enemy_lasers_render(uint16_t *buffer, const Enemy *enemies, int count, int cam_x, int cam_y);

#endif // ENEMY_LASER_H
