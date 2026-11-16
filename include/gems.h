#ifndef GEMS_H
#define GEMS_H

#include "gameplay.h"

// DESIGN.md 6.12.10: experience gems dropped by every kill (strip mode). Modelled on pickups.c.
#define GEM_MAX_ACTIVE 48       // [TUNABLE-PLACEHOLDER] pool; when full the xp is added directly
#define GEM_MAGNET_RADIUS 24    // [TUNABLE-PLACEHOLDER] ground px
#define GEM_PICKUP_RADIUS 10    // [TUNABLE-PLACEHOLDER] ground px

extern volatile uint8_t g_gems_off;   // sandbox only: kills drop nothing
void gems_init(void);
void gems_shift_y(int dy_px);
void gems_enemy_killed(const Enemy *enemy);
void gems_update(fixed player_x, fixed player_y, fixed tide_y);
// Painter's list (render_screen): gems_item says whether gem i is on this screen and its ground depth; gems_draw
// paints it (shadow and body), hidden by the walls in front of it.
int gems_item(int i, int cam_x, int cam_y, int *depth);
void gems_draw(uint16_t *buffer, int i, int cam_x, int cam_y);

#endif // GEMS_H
