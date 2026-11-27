#ifndef WEAPONS_H
#define WEAPONS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

typedef struct Enemy Enemy;
typedef struct PlayerState PlayerState;

// DESIGN.md 6.5: one character = one weapon (El Corazon Abierto, sacred ray).
typedef enum {
    WEAPON_SNIPER = 0,
    NUM_WEAPON_TYPES
} WeaponType;

// Weapon parameters (kept as a struct for tuning/upgrades).
typedef struct {
    const char *name;
    int damage_per_hit;         // damage per piercing hit
    int pellets;                // unused (1)
    int fire_cooldown;          // frames before the next shot can start
    fixed projectile_speed;     // unused (0)
    int projectile_range;       // ray length in px
    fixed spread_angle;         // unused (0)
    int aim_min_frames;         // minimum aim time before the shot is armed
    fixed knockback;            // 8.8 px/frame impulse given to a hit enemy
    int stun_frames;            // frames a hit enemy stays staggered
    fixed recoil;               // 8.8 px the player is pushed back on firing
    int shake_amp;              // screen shake amplitude (px)
    int shake_frames;           // screen shake duration
} WeaponTuning;

extern const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES];

// Debug-only effects style (0 = A, 1 = B, 2 = C). The sacred ray always uses C (fuego, DESIGN.md 6.10).
#define FX_STYLE_COUNT 3
extern int g_fx_style;
char weapons_fx_style_letter(void);

// Sniper charge auras (DESIGN.md 4.9, 6.12.6, 6.12.8): a bitmask (1 << AURA_STYLE_*) that stacks. The relic ->
// look mapping lives in relic_aura_mask() (weapons.c): E thorn ring (Aura de Cilicio), H ash (Sed de Ceniza),
// G glow (Viatico), L flames (Corazon Flagelado, only while its instant charge is pending: g_aura_force_mask).
// The sandbox forces one look through g_aura_debug_mask (flag bits 3-4).
#define AURA_STYLE_COUNT 4
enum { AURA_STYLE_L = 0, AURA_STYLE_G = 1, AURA_STYLE_E = 2, AURA_STYLE_H = 3 };
extern int g_aura_debug_mask;
extern int g_aura_force_mask;   // gameplay bits raised by relics (Corazon Flagelado: AURA_STYLE_L while its instant charge is pending)
extern volatile uint8_t g_laser_look;   // sandbox evidence hook: 0 = current laser look, 1..3 = A / B / C (laser round)
char weapons_aura_style_letter(void);

// One frame of touch / button state for the weapon system.
typedef struct {
    int touch_down;      // stylus currently on the screen
    int touch_pressed;   // stylus went down this frame
    int touch_released;  // stylus went up this frame
    int touch_x;         // world pixel under the stylus
    int touch_y;
    fixed player_x;      // player ground position
    fixed player_y;
    fixed muzzle_x;      // ground position of the weapon muzzle
    fixed muzzle_y;
    int muzzle_h;        // height of the muzzle above the ground (px)
} WeaponInput;

// Result of one weapons_input() call.
#define WEAPON_RESULT_FIRED  1
#define WEAPON_RESULT_ROOTED 2   // the player must stand still (sniper aiming)

void weapons_init(void);
void weapons_shift_y(int dy_px);
// Drops a sniper charge in progress without firing (level-up screen).
void weapons_cancel_aim(void);
// Death hook: a burning enemy that dies may explode (Martirio Contagioso). Call with the enemy still intact.
void weapons_enemy_died(const Enemy *e);
void weapons_pira_explode(const Enemy *e);
// Part C relics: the hero feet (world px), once a frame before weapons_update; and a hit the hero took
// (Corazon Flagelado: wave of fire and instant next charge).
void weapons_set_hero_pos(int x, int y);
void weapons_player_hit(void);
// True when a stylus press would start a sniper aim (the player must stop that frame).
int weapons_can_start_aim(const PlayerState *player);
// Sniper charge for the hero's animation: 1 while AIMING or READY, and the collimation progress 0..256.
int weapons_aim_charging(void);
// While the sniper charges: its aiming line (muzzle in world px and the unit ground direction, length 256, y doubled).
int weapons_aim_line(int *mx, int *my, int *gx, int *gy);
int weapons_aim_progress(void);
// Remate: the hero's next sniper charge is READY on press (same mechanism as Corazon Flagelado).
void weapons_ready_instant(void);
int weapons_input(PlayerState *player, const WeaponInput *in, Enemy *enemies, int max_enemies);
void weapons_update(Enemy *enemies, int max_enemies);
void weapons_render(uint16_t *buffer, int cam_x, int cam_y);
// Ground decals (under shadows and sprites) and the light pass (over the sprites); see groundfx.h.
void weapons_render_floor(uint16_t *buffer, int cam_x, int cam_y);
void weapons_render_light(uint16_t *buffer, int cam_x, int cam_y);
void weapons_render_overlay(uint16_t *buffer);      // screen-space look of Llaga Abierta C (bottom screen only)
int weapons_llaga_tint(void);                       // hero glow level 0..2 (Llaga Abierta B), see sprite_glow in main.c
int weapons_consume_tint(int enemy_idx);            // burn tint level 1..4 an enemy keeps while Auto de Fe consumes its burn, else 0
const char *weapons_get_name(WeaponType type);

// Direction (8.8, ground metric) of the last shot, for the player's recoil.
void weapons_last_shot_dir(fixed *dir_x, fixed *dir_y);

// Screen shake currently requested by the weapons (offset to add to the camera).
void weapons_shake_offset(int *dx, int *dy);
// Asks for a screen shake.
void weapons_request_shake(int amp, int frames);

#endif // WEAPONS_H
