#ifndef MODIFIERS_H
#define MODIFIERS_H

#include <stdint.h>
#include "game.h"

// DESIGN.md 5: Isaac-style modifiers. Clearing a pack puts two pedestals on the floor; walking
// onto one takes it and removes the other. Each modifier is a trade: it edits a few numbers
// of the weapons / the player, all kept in `g_mods` so the rest of the code just reads it.
// Everything is lost when the run restarts.

typedef struct {
    int shotgun_pellets;        // extra pellets per shot
    int shotgun_cooldown;       // extra frames between shots
    int shotgun_damage_pct;     // 100 = normal
    int shotgun_pierce;         // enemies a pellet goes through
    int sniper_aim;             // extra aim frames (negative = faster)
    int sniper_damage_pct;
    int max_hp;                 // extra hits the player can take
    int speed_pct;
    int iframes;                // extra invulnerability frames after a hit
    int kill_resets_shotgun;    // every kill readies the shotgun at once
    int knock_pct;              // shotgun shove and stun
    int recoil_pct;
} ModEffects;

extern ModEffects g_mods;

#define MOD_COUNT 8
#define MOD_NONE (-1)

// Frames between a pack dying and its pedestals being usable (so a step does not take one by accident).
#define MOD_PEDESTAL_DELAY 45

void mods_reset(void);                              // new run: nothing owned, no pedestals
void mods_offer(int x, int y);                      // two random pedestals near (x, y), not owned yet
// Returns the id taken this frame or MOD_NONE.
int mods_update(fixed player_x, fixed player_y);
void mods_render(uint16_t *buffer, int cam_x, int cam_y);

const char *mods_name(int id);
int mods_owned_count(void);
int mods_owned_mask(void);
uint16_t mods_color(int id);                        // RGB15 | BIT(15)

// Text for the HUD: the pedestal the player stands near, or the last pick for a while. NULL if none.
const char *mods_hud_text(void);

#endif // MODIFIERS_H
