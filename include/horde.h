#ifndef HORDE_H
#define HORDE_H

#include <stdint.h>
#include "gameplay.h"

#define HORDE_INITIAL_INTERVAL 90 // [TUNABLE-PLACEHOLDER] frames between spawns at run start
#define HORDE_MIN_INTERVAL 20 // [TUNABLE-PLACEHOLDER] minimum frames between spawns
#define HORDE_INTERVAL_RAMP_FRAMES 18000 // [TUNABLE-PLACEHOLDER] frames to reach the minimum interval (~5 min)
#define HORDE_INITIAL_CAP 6 // [TUNABLE-PLACEHOLDER] initial active enemy cap
#define HORDE_MAX_CAP MAX_GAMEPLAY_ENEMIES // [TUNABLE-PLACEHOLDER] maximum active enemy cap
#define HORDE_CAP_RAMP_FRAMES 18000 // [TUNABLE-PLACEHOLDER] frames to reach the maximum active cap
#define HORDE_SPAWN_GROUP_CHANCE 25 // [TUNABLE-PLACEHOLDER] percent chance to spawn a group
#define HORDE_SPAWN_GROUP_MIN 2 // [TUNABLE-PLACEHOLDER] smallest group size
#define HORDE_SPAWN_GROUP_MAX 3 // [TUNABLE-PLACEHOLDER] largest group size
#define HORDE_SPAWN_GAP_MIN 16 // [TUNABLE-PLACEHOLDER] nearest spawn distance above the upper screen
#define HORDE_SPAWN_GAP_MAX 64 // [TUNABLE-PLACEHOLDER] farthest spawn distance above the upper screen
#define HORDE_RECYCLE_BEHIND_PX 400 // [TUNABLE-PLACEHOLDER] distance behind player before recycling
#define HORDE_SPAWN_X_MIN 20 // [TUNABLE-PLACEHOLDER] left safe spawn coordinate in strip
#define HORDE_SPAWN_X_MAX 492 // [TUNABLE-PLACEHOLDER] right safe spawn coordinate in strip
#define STRIP_DEATH_SCREEN_FRAMES 60 // [TUNABLE-PLACEHOLDER] minimum death summary duration
#define HORDE_CHARGER_PERCENT 75 // [TUNABLE-PLACEHOLDER] share of charger spawns
#define HORDE_RAMP_STEP_FRAMES 257 // [TUNABLE-PLACEHOLDER] interval tuning cadence (~18,000 frames total)
#define HORDE_SPAWN_ATTEMPTS 24 // [TUNABLE-PLACEHOLDER] free-cell probes per spawned enemy
#define HORDE_SHOOTER_TOP_LIMIT_PX 288 // [TUNABLE-PLACEHOLDER] visible world height above player across both screens
#define HORDE_CLUSTER_HALF_WIDTH_PX 16 // [TUNABLE-PLACEHOLDER] horizontal radius for grouped spawns
#define HORDE_CLUSTER_HALF_HEIGHT_PX 8 // [TUNABLE-PLACEHOLDER] vertical radius for grouped spawns

void horde_init(uint32_t seed);
void horde_update(Enemy *enemies, int count, fixed player_y,
                  int upper_screen_y, fixed tide_y);
uint32_t horde_run_frames(void);

#endif
