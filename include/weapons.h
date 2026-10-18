#ifndef WEAPONS_H
#define WEAPONS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

typedef struct Enemy Enemy;
typedef struct PlayerState PlayerState;

typedef enum {
    WEAPON_PISTOL = 0,
    WEAPON_SHOTGUN,
    WEAPON_GATLING,
    WEAPON_HEAVY,
    NUM_WEAPON_TYPES
} WeaponType;

typedef enum {
    FIRE_MODE_HITSCAN = 0,
    FIRE_MODE_PROJECTILE
} WeaponFireMode;

typedef struct {
    const char *name;              // [TUNABLE-PLACEHOLDER] Weapon display name
    WeaponFireMode fire_mode;      // [TUNABLE-PLACEHOLDER] HITSCAN vs PROJECTILE
    int damage_per_hit;            // [TUNABLE-PLACEHOLDER] Damage per projectile/tracer
    int pellets;                   // [TUNABLE-PLACEHOLDER] Pellets/projectiles per shot
    int fire_cooldown;             // [TUNABLE-PLACEHOLDER] Frames between shots
    int max_ammo;                  // [TUNABLE-PLACEHOLDER] Max ammo pool capacity (0 = infinite)
    int pickup_ammo_amount;        // [TUNABLE-PLACEHOLDER] Ammo restored by pickup
    int ammo_cost;                 // [TUNABLE-PLACEHOLDER] Ammo consumed per fire (0 = infinite)
    fixed projectile_speed;        // [TUNABLE-PLACEHOLDER] 8.8 fixed speed
    int projectile_range;          // [TUNABLE-PLACEHOLDER] Lifetime frames (short range for shotgun)
    fixed spread_angle;            // [TUNABLE-PLACEHOLDER] 8.8 spread dispersion factor
    int spinup_delay;              // [TUNABLE-PLACEHOLDER] Frames to spin up (Gatling)
    fixed speed_penalty;           // [TUNABLE-PLACEHOLDER] 8.8 movement speed factor during firing
    int explosion_radius;          // [TUNABLE-PLACEHOLDER] Splash radius (Heavy rocket)
    int explosion_damage;          // [TUNABLE-PLACEHOLDER] Splash damage (Heavy rocket)
} WeaponTuning;

extern const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES];

// Projectile entity for player shots (pellets, rockets)
#define MAX_PLAYER_PROJECTILES 32

typedef struct {
    int active;
    WeaponType weapon_type;
    fixed x;             // 8.8 world position X
    fixed y;             // 8.8 world position Y
    fixed vx;            // 8.8 velocity X
    fixed vy;            // 8.8 velocity Y
    int life;            // remaining frames
    int max_life;        // total frames
    int damage;          // damage on hit
    int is_explosive;    // 1 if explodes on impact (HEAVY)
    int explosion_radius;// radius in world pixels
    int explosion_damage;// splash damage
    uint16_t hit_mask;   // bitmask of enemy IDs already hit
    uint8_t seed;        // seed for visual rendering jitter
} PlayerProjectile;

// Tracer entity for hitscans (pistol, gatling)
#define MAX_TRACERS 8

typedef struct {
    int active;
    WeaponType weapon_type;
    fixed start_x;       // 8.8 world pos
    fixed start_y;
    fixed end_x;         // 8.8 world pos
    fixed end_y;
    int life;            // frames to display
} WeaponTracer;

// Area of effect explosion entity (heavy rocket)
#define MAX_EXPLOSIONS 4

typedef struct {
    int active;
    fixed x;             // 8.8 world pos
    fixed y;
    int radius;          // max radius in pixels
    int life;            // remaining frames
    int max_life;        // total frames
} WeaponExplosion;

// System management
void weapons_init(void);
void weapons_cycle(PlayerState *player, int delta); // delta: -1 for L, +1 for R
int weapons_can_fire(const PlayerState *player);
int weapons_fire(PlayerState *player, fixed player_x, fixed player_y,
                 int aim_screen_x, int aim_screen_y, int cam_x, int cam_y,
                 int is_firing_held, Enemy *enemies, int max_enemies);
void weapons_update(Enemy *enemies, int max_enemies, fixed player_x, fixed player_y);
void weapons_render(uint16_t *buffer, int cam_x, int cam_y);
fixed weapons_get_speed_factor(const PlayerState *player, int is_firing_held);
const char *weapons_get_name(WeaponType type);
int weapons_get_active_projectile_count(void);

// Callback to damage enemy with impulse and death chunk spawning
void enemy_hit(Enemy *e, int damage, fixed hit_vx, fixed hit_vy);

#endif // WEAPONS_H
