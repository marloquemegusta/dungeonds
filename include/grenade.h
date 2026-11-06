#ifndef GRENADE_H
#define GRENADE_H

#include <stdint.h>
#include "game.h"
#include "weapons.h"
#include "gameplay.h"
#include "groundfx.h"

// DESIGN.md 4.9. Constants shared with the host contract test.
#define GRENADE_FUSE_FRAMES 90      // explodes this long after the throw
#define GRENADE_FLIGHT_FRAMES 30    // arc from the muzzle to the target point
#define GRENADE_RADIUS 56           // ground px (2:1 ellipse on screen)
#define GRENADE_DAMAGE_RIM 15       // damage at the rim; the centre uses WeaponTuning.damage_per_hit
#define GRENADE_MAX_ACTIVE 2

void grenade_init(void);
void grenade_shift_y(int dy_px);
// Weapon switched or the arena restarted: drop any aim in progress (thrown grenades keep ticking).
void grenade_cancel(void);
// Player ground position, refreshed every simulated frame (the blast hits the player's real position).
void grenade_set_player_pos(fixed x, fixed y);
// Stylus handling while the grenade is the current weapon. Returns WEAPON_RESULT_* flags
// (WEAPON_RESULT_FIRED when a grenade was thrown this frame).
int grenade_input(PlayerState *player, const WeaponInput *in);
// Advances thrown grenades and explosions; applies the blast damage on detonation.
void grenade_update(Enemy *enemies, int max_enemies, PlayerState *player);
// Draws the aim marker, grenades in flight and the explosion effects (BGR555 page,
// call dirty_row() for every pixel written). Called once per screen.
void grenade_render(uint16_t *buffer, int cam_x, int cam_y);
// Floor pass: the aim marker, warning rings / zone and the shock ring, painted on the ground
// (groundfx.h) under the shadows and sprites.
void grenade_render_floor(const GroundTarget *g);
// Light pass: after the sprites, lights the actors standing in a targeting beam.
void grenade_render_light(const GroundTarget *g);

#endif // GRENADE_H
