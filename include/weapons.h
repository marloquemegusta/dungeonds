#ifndef WEAPONS_H
#define WEAPONS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

typedef struct Enemy Enemy;
typedef struct PlayerState PlayerState;

// DESIGN.md 4.3: two weapons with infinite ammo, limited by rate and cost of use.
typedef enum {
    WEAPON_SHOTGUN = 0,
    WEAPON_SNIPER,
    NUM_WEAPON_TYPES
} WeaponType;

// Weapons are defined by parameters so a future upgrade layer can tune them
// without rewriting the weapon code (DESIGN.md 1).
typedef struct {
    const char *name;
    int damage_per_hit;         // damage per pellet / per piercing hit
    int pellets;                // projectiles per shot
    int fire_cooldown;          // frames before the next shot can start
    fixed projectile_speed;     // 8.8 ground px/frame (shotgun pellets)
    int projectile_range;       // lifetime frames (shotgun) or ray length in px (sniper)
    fixed spread_angle;         // 8.8 side spread between neighbouring pellets
    int aim_min_frames;         // sniper: minimum aim time before the shot is armed
    fixed knockback;            // 8.8 px/frame impulse given to a hit enemy
    int stun_frames;            // frames a hit enemy stays staggered
    fixed recoil;               // 8.8 px the player is pushed back on firing
    int shake_amp;              // screen shake amplitude (px)
    int shake_frames;           // screen shake duration
} WeaponTuning;

extern const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES];

// Pellet in flight. x/y live on the ground plane; the shot is drawn `height`
// pixels above it (the muzzle height) so it leaves the weapon, not the feet.
#define MAX_PLAYER_PROJECTILES 32

typedef struct {
    int active;
    WeaponType weapon_type;
    fixed x;             // 8.8 ground position X
    fixed y;             // 8.8 ground position Y
    fixed vx;            // 8.8 velocity X
    fixed vy;            // 8.8 velocity Y
    int height;          // pixels above the ground at which the shot is drawn
    int life;            // remaining frames
    int max_life;        // total frames
    int damage;          // damage at the muzzle (falls off with distance)
    int pierce;          // further enemies the pellet can go through (modifier)
    uint32_t hit_mask;   // enemies already hit by this pellet
} PlayerProjectile;

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
void weapons_cycle(PlayerState *player);
// True when a stylus press would start a sniper aim (the player must stop that frame).
int weapons_can_start_aim(const PlayerState *player);
int weapons_input(PlayerState *player, const WeaponInput *in, Enemy *enemies, int max_enemies);
void weapons_update(Enemy *enemies, int max_enemies);
// An enemy died: the "sed de sangre" modifier readies the shotgun at once.
void weapons_notify_kill(void);
void weapons_render(uint16_t *buffer, int cam_x, int cam_y);
const char *weapons_get_name(WeaponType type);
int weapons_get_active_projectile_count(void);

// Direction (8.8, ground metric) of the last shot, for the player's recoil.
void weapons_last_shot_dir(fixed *dir_x, fixed *dir_y);

// Screen shake currently requested by the weapons (offset to add to the camera).
void weapons_shake_offset(int *dx, int *dy);

#endif // WEAPONS_H
