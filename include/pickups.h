#ifndef PICKUPS_H
#define PICKUPS_H

#include "gameplay.h"

#define HEAL_PICKUP_CHANCE_DENOMINATOR 12 // [TUNABLE-PLACEHOLDER] one drop per this many kills on average
#define HEAL_PICKUP_MAX_ACTIVE 24 // [TUNABLE-PLACEHOLDER] active pickup cap (orbs and experience runes)
#define HEAL_PICKUP_RADIUS 10 // [TUNABLE-PLACEHOLDER] pickup radius in ground pixels
#define HEAL_PICKUP_SIZE 8 // [TUNABLE-PLACEHOLDER] heart visual size in pixels

// Orb kinds (ARPG remate drops).
#define PICKUP_KIND_HEALTH 0
#define PICKUP_KIND_MANA 1
#define PICKUP_KIND_XP 2        // experience rune: collecting it banks its amount (arpg_add_xp)

void pickups_init(uint32_t seed);
void pickups_shift_y(int dy_px);
void pickups_enemy_killed(const Enemy *enemy);
void pickups_update(fixed player_x, fixed player_y, PlayerState *player);
// Puts one orb of this kind on the floor (first free slot, else slot 0).
void pickups_spawn(int kind, fixed x, fixed y);
// Finisher (remate) loot: rolls the health and mana orbs of ARPG_REMATE_*_CHANCE.
void pickups_remate_drops(fixed x, fixed y);
// Experience rune on the floor worth `amount` xp. With no free slot the xp is banked at once (never lost).
void pickups_spawn_xp(fixed x, fixed y, int amount);
// Painter's list (render_screen).
int pickups_item(int i, int cam_x, int cam_y, int *depth);
void pickups_draw(uint16_t *buffer, int i, int cam_x, int cam_y);

#endif
