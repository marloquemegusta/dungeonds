#ifndef GAMEPLAY_H
#define GAMEPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"

// ---------------------------------------------------------------------------
// 1. Enemy & Weapon Types & Tuning Tables (Fixed-Point 8.8)
// ---------------------------------------------------------------------------

typedef enum {
    ENEMY_TYPE_NONE = 0,
    ENEMY_TYPE_CHARGER,
    ENEMY_TYPE_SHOOTER,
    NUM_ENEMY_TYPES
} EnemyType;

typedef enum {
    WEAPON_PISTOL = 0,
    WEAPON_SHOTGUN,
    WEAPON_GATLING,
    WEAPON_HEAVY,
    NUM_WEAPON_TYPES
} WeaponType;

typedef struct {
    int max_hp;             // [TUNABLE] base health points
    fixed speed;            // [TUNABLE] 8.8 fixed movement speed
    int contact_damage;     // [TUNABLE] melee/contact damage dealt to player
    int attack_cooldown;    // [TUNABLE] frames between attacks
    int preferred_dist_min; // [TUNABLE] min distance band (world pixels)
    int preferred_dist_max; // [TUNABLE] max distance band (world pixels)
} EnemyTuning;

typedef struct {
    int damage_per_hit;     // [TUNABLE] damage per projectile/pellet
    int pellets;            // [TUNABLE] pellets per shot
    int fire_cooldown;      // [TUNABLE] frames between shots
    int max_ammo;           // [TUNABLE] max ammo pool capacity (0 = infinite)
    int pickup_ammo_amount; // [TUNABLE] ammo restored by pickup
} WeaponTuning;

extern const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];
extern const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES];

// ---------------------------------------------------------------------------
// 2. Generic Enemy Pool
// ---------------------------------------------------------------------------

#define MAX_GAMEPLAY_ENEMIES 10

typedef enum {
    ENEMY_STATE_IDLE = 0,
    ENEMY_STATE_ALERT,
    ENEMY_STATE_CHASE,
    ENEMY_STATE_ATTACK,
    ENEMY_STATE_SEARCH,
    ENEMY_STATE_DEAD
} EnemyState;

typedef struct {
    fixed x;
    fixed y;
    int dir;
    int frame;
    int anim_timer;
    int char_id;
    int active;
    int step_count;
    int step_limit;
    int hp;
    int max_hp;
    int hit_timer;
    EnemyType type;
    EnemyState state;
    int state_timer;
} Enemy;

// ---------------------------------------------------------------------------
// 3. Player Stats & Damage Function (Doom-style 1/3 armor absorption)
// ---------------------------------------------------------------------------

#define PLAYER_MAX_HP 100
#define PLAYER_MAX_ARMOR 100

typedef struct {
    int hp;
    int max_hp;
    int armor;
    int max_armor;
    int ammo[NUM_WEAPON_TYPES];
    WeaponType current_weapon;
    int is_dead;
    int invuln_timer;
} PlayerState;

extern PlayerState g_player_state;

/**
 * Applies damage to player with Doom-style armor absorption:
 * Rule:
 * - If armor > 0, armor absorbs 1/3 of the incoming damage (absorbed = damage / 3).
 * - absorbed is clamped to available armor.
 * - Remaining damage (damage - absorbed) is deducted from player HP.
 * - Player armor is reduced by absorbed.
 * - If HP drops to <= 0, player HP is clamped to 0 and is_dead is set to 1.
 */
void player_apply_damage(PlayerState *player, int damage);

/**
 * Initializes player stats (HP=100, Armor=0, default ammo, pistol selected).
 */
void player_state_init(PlayerState *player);

// ---------------------------------------------------------------------------
// 4. Pickup Pool & Collection System
// ---------------------------------------------------------------------------

typedef enum {
    PICKUP_NONE = 0,
    PICKUP_HEALTH,
    PICKUP_ARMOR,
    PICKUP_AMMO_SHOTGUN,
    PICKUP_AMMO_GATLING,
    PICKUP_AMMO_HEAVY,
    NUM_PICKUP_TYPES
} PickupType;

#define MAX_PICKUPS 16
#define PICKUP_COLLECT_RADIUS_PX 12

#define PICKUP_HEALTH_AMOUNT 25
#define PICKUP_ARMOR_AMOUNT 25

typedef struct {
    int active;
    PickupType type;
    fixed x; // 8.8 fixed world x
    fixed y; // 8.8 fixed world y
    int amount;
} Pickup;

extern Pickup g_pickups[MAX_PICKUPS];

void pickups_init(void);
Pickup *pickup_spawn(PickupType type, fixed x, fixed y, int amount);
int player_collect_pickup(PlayerState *player, Pickup *pickup);
int pickups_update_collection(PlayerState *player, fixed player_x, fixed player_y);
void pickups_render(uint16_t *buffer, int cam_x, int cam_y);

// ---------------------------------------------------------------------------
// 5. Deterministic Integer RNG (LCG)
// ---------------------------------------------------------------------------

void rng_seed(uint32_t seed);
uint32_t rng_next(void);
int rng_range(int min, int max);

#endif // GAMEPLAY_H
