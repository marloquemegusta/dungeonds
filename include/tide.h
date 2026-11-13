#ifndef TIDE_H
#define TIDE_H

#include "gameplay.h"

#define TIDE_START_BELOW_PLAYER_PX 300 // [TUNABLE-PLACEHOLDER] initial distance below player
#define TIDE_SPEED_MIN_FIXED 40        // [TUNABLE-PLACEHOLDER] 8.8 fixed px/frame when near/above player (~0.16 px/frame)
#define TIDE_SPEED_MAX_FIXED 190       // [TUNABLE-PLACEHOLDER] 8.8 fixed px/frame when far below player (~0.74 px/frame)
#define TIDE_SPRING_NEAR_PX 80         // [TUNABLE-PLACEHOLDER] distance (px) at or below which tide runs at min speed
#define TIDE_SPRING_SPAN_SHIFT 8       // 256 px elastic ramp -> far threshold = 80 + 256 = 336 px (no division)
#define TIDE_SPRING_FAR_PX (TIDE_SPRING_NEAR_PX + (1 << TIDE_SPRING_SPAN_SHIFT))
#define TIDE_HIT_FRAMES 75             // [TUNABLE-PLACEHOLDER] submerged frames between damage attempts
#define TIDE_BRIGHTNESS 10             // [TUNABLE-PLACEHOLDER] hardware fade to black (0..16)
#define TIDE_BORDER_PX 3               // [TUNABLE-PLACEHOLDER] visible red edge band width (3 rows: bright to dark)

void tide_init(fixed player_y);
fixed tide_speed_for_distance(int dist_px);
void tide_update(fixed player_y);
void tide_shift_y(int dy_px);
fixed tide_y(void);
int tide_player_submerged(fixed player_y);
int tide_player_slowed(fixed player_y);
void tide_damage_player(PlayerState *player, fixed player_y);
void tide_render_window(int sub_screen, int camera_y);
int tide_visible_on_screen(int camera_y);
void tide_render_border(uint16_t *buffer, int camera_y);

#endif
