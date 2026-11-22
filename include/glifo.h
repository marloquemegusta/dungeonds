#ifndef GLIFO_H
#define GLIFO_H

// Glifo (DESIGN.md 7.5-7.7): the second spell. The stylus touches the floor, the hero prays (clip corazon_pray) and on
// the frame the hands close the seal appears at that point as a rune on the floor with a fixed cycle: apertura (the crack opens, no effect), espera (the auras act) and detonacion (one hit to every enemy
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

// Stylus input for the glifo. Returns 1 while aiming (the hero stands still), else 0; praying does not root him. Releasing the stylus
// starts the prayer (mana is paid then) facing `hero_dir`.
// touch_x / touch_y are the world pixel under the stylus (same values weapons_input gets).
int glifo_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y, int hero_dir);

// Prayer in progress (the hero walks freely, punches are refused and the hero is drawn with the clip below).
int glifo_busy(void);
// Current prayer frame for drawing (like punch_pixels): pixels, runs, bounds {x, y, w, h} in the 48x48 cell and the
// feet row of the cell. NULL while not praying.
const uint16_t *glifo_pray_pixels(void);
const uint16_t *glifo_pray_runs(void);
const uint8_t *glifo_pray_bounds(void);
int glifo_pray_anchor(void);
int glifo_pray_dir(void);     // facing of the clip being drawn (follows the hero while he walks)
int glifo_pray_frame(void);   // clip frame being drawn

// Once per simulated frame: advances the prayer (the seal appears when the hands close), runs the cycle and the auras.
void glifo_update(Enemy *enemies, int max_enemies);

// Non-zero when a world ground point lies inside any live glifo.
int glifo_point_in_zone(int x, int y);

// Silencing (Campanero de Animas, DESIGN-ARPG.md 9): a tanido wave puts a glyph out. No detonation, no mana back.
int glifo_zone_count(void);                                          // zone slots to iterate with glifo_silenceable
int glifo_silenceable(int zone, int *cx, int *cy, int *radius);      // 1 when the zone is live, not silenced and before its detonation; writes centre and ground radius
void glifo_silence(int zone, int from_x, int from_y);                // starts the ~24 frame silencing; (from_x, from_y) is where the wave comes from (it sets the side the green enters)

void glifo_render_floor(uint16_t *buffer, int cam_x, int cam_y);   // runes and aim ring: under the actors

#endif
