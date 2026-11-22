#ifndef GLIFO_H
#define GLIFO_H

// Glifo (DESIGN.md 7.5-7.7): the second spell. Thrown to the stylus point, it lands as a rune on the floor with a
// fixed cycle: apertura (the crack opens, no effect), espera (the auras act) and detonacion (one hit to every enemy
// inside), then cierre. All positions are world px of the feet.
//
// Auras are independent bits (any combination); the render is layered: the base seal always, an optional
// TRANSFORMATION of the seal (Redil twists it into a whirl) and optional ADDITIVE layers over whichever mask is
// active (Zarza flames). A future aura is a new bit plus either a new mask in tools/glifo_rune or a new layer.
#include <stdint.h>
#include "game.h"
#include "gameplay.h"

#define GLIFO_AURA_REDIL 1      // transformation: pulls every enemy inside toward the centre during the wait
#define GLIFO_AURA_ZARZA 2      // additive layer: Quemado during the wait and on detonation
// reserved for later auras (Juicio, Marca): 4, 8

void glifo_reset(void);                       // clears every glifo in flight or on the floor (new run)
void glifo_shift_y(int dy_px);                // strip rebase: moves the glifos with the world rows
void glifo_cancel_aim(void);                  // drops an aim in progress (the spell was switched)

// Stylus input for the glifo. Returns 1 while aiming (the hero stands still), else 0.
// touch_x / touch_y are the world pixel under the stylus (same values weapons_input gets).
int glifo_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y);

// Once per simulated frame: flies the projectiles, lands them as runes, runs the cycle and the auras.
void glifo_update(Enemy *enemies, int max_enemies);

// Non-zero when a world ground point lies inside any live glifo.
int glifo_point_in_zone(int x, int y);

void glifo_render_floor(uint16_t *buffer, int cam_x, int cam_y);   // runes and aim ring: under the actors
void glifo_render(uint16_t *buffer, int cam_x, int cam_y);         // flying projectiles: over the actors

#endif
