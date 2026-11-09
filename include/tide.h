#ifndef TIDE_H
#define TIDE_H

#include "gameplay.h"

#define TIDE_START_BELOW_PLAYER_PX 300 // [TUNABLE-PLACEHOLDER] initial distance below player
#define TIDE_SPEED_FIXED 90 // [TUNABLE-PLACEHOLDER] 8.8 fixed px/frame (~0.35 px/frame)
#define TIDE_HIT_FRAMES 75 // [TUNABLE-PLACEHOLDER] submerged frames between damage attempts
#define TIDE_BRIGHTNESS 10 // [TUNABLE-PLACEHOLDER] hardware fade to black (0..16)
#define TIDE_BORDER_PX 3 // [TUNABLE-PLACEHOLDER] visible red edge band width (3 rows: bright to dark)

void tide_init(fixed player_y);
void tide_update(void);
void tide_shift_y(int dy_px);
fixed tide_y(void);
int tide_player_submerged(fixed player_y);
int tide_player_slowed(fixed player_y);
void tide_damage_player(PlayerState *player, fixed player_y);
void tide_render_window(int sub_screen, int camera_y);
int tide_visible_on_screen(int camera_y);
void tide_render_border(uint16_t *buffer, int camera_y);

#endif
