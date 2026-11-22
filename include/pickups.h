#ifndef PICKUPS_H
#define PICKUPS_H

#include "gameplay.h"
#include "arpg_inv.h"

#define HEAL_PICKUP_CHANCE_DENOMINATOR 12 // [TUNABLE-PLACEHOLDER] one drop per this many kills on average
#define HEAL_PICKUP_MAX_ACTIVE 24 // [TUNABLE-PLACEHOLDER] active pickup cap (orbs and relic drops)
#define HEAL_PICKUP_RADIUS 10 // [TUNABLE-PLACEHOLDER] pickup radius in ground pixels
#define HEAL_PICKUP_SIZE 8 // [TUNABLE-PLACEHOLDER] heart visual size in pixels

// Orb & drop kinds.
#define PICKUP_KIND_HEALTH 0
#define PICKUP_KIND_MANA 1
#define PICKUP_KIND_XP 2        // legacy: banks XP directly
#define PICKUP_KIND_RELIC 3     // ground relic drop -> arpg_inv_add()

void pickups_init(uint32_t seed);
void pickups_shift_y(int dy_px);
void pickups_enemy_killed(const Enemy *enemy);
void pickups_update(fixed player_x, fixed player_y, PlayerState *player);
// Puts one orb of this kind on the floor (first free slot, else slot 0).
void pickups_spawn(int kind, fixed x, fixed y);
// Finisher (remate) loot: rolls the health and mana orbs of ARPG_REMATE_*_CHANCE.
void pickups_remate_drops(fixed x, fixed y);
// Experience helper (now banks XP directly; no ground rune).
void pickups_spawn_xp(fixed x, fixed y, int amount);
// Spawns a rolled relic drop on the floor.
void pickups_spawn_relic(fixed x, fixed y, const ArpgInvItem *item);
// Rolls and drops loot on enemy death (normal, elite, boss).
void pickups_drop_enemy_loot(int enemy_type, int floor, fixed x, fixed y);
// Last loot pickup toast message for HUD (NULL if expired).
const char *pickups_loot_toast(void);
// Painter's list (render_screen).
int pickups_item(int i, int cam_x, int cam_y, int *depth);
void pickups_draw(uint16_t *buffer, int i, int cam_x, int cam_y);

#endif
