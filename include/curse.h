#ifndef CURSE_H
#define CURSE_H

// Maldicion (DESIGN.md 7.3): the second spell. Thrown to the stylus point, it lands and leaves a zone
// on the floor that applies Quemado to the enemies standing inside it. All positions are world px of the feet.
#include <stdint.h>
#include "game.h"
#include "gameplay.h"

void curse_reset(void);                       // clears every curse in flight or on the floor (new run)
void curse_shift_y(int dy_px);                // strip rebase: moves the curses with the world rows
void curse_cancel_aim(void);                  // drops an aim in progress (the spell was switched)

// Stylus input for the curse. Returns 1 while aiming (the hero stands still), else 0.
// touch_x / touch_y are the world pixel under the stylus (same values weapons_input gets).
int curse_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y);

// Once per simulated frame: flies the projectiles, lands them as zones and burns the enemies inside.
void curse_update(Enemy *enemies, int max_enemies);

// Non-zero when a world ground point lies inside any live zone.
int curse_point_in_zone(int x, int y);

void curse_render_floor(uint16_t *buffer, int cam_x, int cam_y);   // zones and aim ring: under the actors
void curse_render(uint16_t *buffer, int cam_x, int cam_y);         // flying projectiles: over the actors

#endif
