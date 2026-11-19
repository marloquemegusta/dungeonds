#ifndef HORDE_H
#define HORDE_H

#include <stdint.h>
#include "gameplay.h"

#if STRESS_TEST
// Measurement build: the horde reaches 48 alive within ~30 s and spawns fast.
#define HORDE_INITIAL_INTERVAL 12
#define HORDE_MIN_INTERVAL 6
#define HORDE_INTERVAL_RAMP_FRAMES 600
#define HORDE_INITIAL_CAP 6
#define HORDE_MAX_CAP 48
#define HORDE_CAP_RAMP_FRAMES 1800
#else
#define HORDE_INITIAL_INTERVAL 60 // [TUNABLE-PLACEHOLDER] frames between spawns at run start (was 90)
#define HORDE_MIN_INTERVAL 12 // [TUNABLE-PLACEHOLDER] minimum frames between spawns (was 20)
#define HORDE_INTERVAL_RAMP_FRAMES 18000 // [TUNABLE-PLACEHOLDER] frames to reach the minimum interval (~5 min)
#define HORDE_INITIAL_CAP 10 // [TUNABLE-PLACEHOLDER] initial active enemy cap (was 6)
#define HORDE_MAX_CAP MAX_GAMEPLAY_ENEMIES // [TUNABLE-PLACEHOLDER] maximum active enemy cap
#define HORDE_CAP_RAMP_FRAMES 18000 // [TUNABLE-PLACEHOLDER] frames to reach the maximum active cap (~5 min)
#endif
#define HORDE_SPAWN_GROUP_CHANCE 35 // [TUNABLE-PLACEHOLDER] percent chance to spawn a group (was 25)
#define HORDE_SPAWN_GROUP_MIN 2 // [TUNABLE-PLACEHOLDER] smallest group size
#define HORDE_SPAWN_GROUP_MAX 3 // [TUNABLE-PLACEHOLDER] largest group size
#define HORDE_SPAWN_GAP_MIN 16 // [TUNABLE-PLACEHOLDER] nearest spawn distance above the upper screen
#define HORDE_SPAWN_GAP_MAX 64 // [TUNABLE-PLACEHOLDER] farthest spawn distance above the upper screen
#define HORDE_RECYCLE_BEHIND_PX 400 // [TUNABLE-PLACEHOLDER] distance behind player before recycling
#define HORDE_SPAWN_X_MIN 20 // [TUNABLE-PLACEHOLDER] left safe spawn coordinate in strip
#define HORDE_SPAWN_X_MAX 492 // [TUNABLE-PLACEHOLDER] right safe spawn coordinate in strip
#define STRIP_DEATH_SCREEN_FRAMES 60 // [TUNABLE-PLACEHOLDER] minimum death summary duration
#define HORDE_EXVOTO_PERCENT 60 // [TUNABLE-PLACEHOLDER] share of Exvoto spawns (the mass tier; they replaced the skeleton)
#define HORDE_CHARGER_PERCENT 15 // [TUNABLE-PLACEHOLDER] share of charger spawns; shooters take the remaining 25%
#define HORDE_CHARGER_MAX_ALIVE 3 // [TUNABLE-PLACEHOLDER] chargers alive at once; a charger roll over it spawns a skeleton
#define HORDE_RAMP_STEP_FRAMES 375 // [TUNABLE-PLACEHOLDER] interval tuning cadence: 48 steps = 18,000 frames (~5 min) to the minimum
#define HORDE_SPAWN_ATTEMPTS 24 // [TUNABLE-PLACEHOLDER] free-cell probes per spawned enemy
#define HORDE_SHOOTER_TOP_LIMIT_PX 288 // [TUNABLE-PLACEHOLDER] visible world height above player across both screens
#define HORDE_CLUSTER_HALF_WIDTH_PX 16 // [TUNABLE-PLACEHOLDER] horizontal radius for grouped spawns
#define HORDE_CLUSTER_HALF_HEIGHT_PX 8 // [TUNABLE-PLACEHOLDER] vertical radius for grouped spawns
#define HORDE_EXVOTO_GROUP_MAX 4 // [TUNABLE-PLACEHOLDER] Exvotos of one burst that pray to the same devout piece
#define HORDE_EXVOTO_SPACING_PX 14 // [TUNABLE-PLACEHOLDER] ground px: nearest an Exvoto is seated to any other enemy
#define HORDE_EXVOTO_CLAIM_RADIUS_PX 24 // [TUNABLE-PLACEHOLDER] ground px beyond a piece's footprint that count as its praying spot
#define HORDE_EXVOTO_SIDE_PX 7 // [TUNABLE-PLACEHOLDER] px beside a piece's footprint where the 6 px body circle first fits
#define HORDE_EXVOTO_FRONT_PX 4 // [TUNABLE-PLACEHOLDER] screen rows in front of a piece's footprint where the body first fits
#define HORDE_DEVOUT_CANDIDATES 16 // [TUNABLE-PLACEHOLDER] devout pieces looked at per spawn burst

void horde_init(uint32_t seed);
void horde_update(Enemy *enemies, int count, fixed player_y, int upper_screen_y);
uint32_t horde_run_frames(void);

#endif
