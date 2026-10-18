#ifndef GAMEPLAY_H
#define GAMEPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "weapons.h"

// ---------------------------------------------------------------------------
// 1. Enemy Types & Tuning Tables (Fixed-Point 8.8)
// ---------------------------------------------------------------------------

typedef enum {
    ENEMY_TYPE_NONE = 0,
    ENEMY_TYPE_CHARGER,
    ENEMY_TYPE_SHOOTER,
    NUM_ENEMY_TYPES
} EnemyType;

typedef struct {
    int max_hp;             // [TUNABLE-PLACEHOLDER] base health points
    fixed speed;            // [TUNABLE-PLACEHOLDER] 8.8 fixed movement speed
    int contact_damage;     // [TUNABLE-PLACEHOLDER] melee/contact damage dealt to player
    int attack_cooldown;    // [TUNABLE-PLACEHOLDER] frames between attacks / burst cooldown
    int preferred_dist_min; // [TUNABLE-PLACEHOLDER] min distance band (world pixels)
    int preferred_dist_max; // [TUNABLE-PLACEHOLDER] max distance band (world pixels)
    int los_range;          // [TUNABLE-PLACEHOLDER] detection radius (world pixels)
    int alert_duration;     // [TUNABLE-PLACEHOLDER] frames in ALERT before action
    int search_duration;    // [TUNABLE-PLACEHOLDER] frames in SEARCH before IDLE
    int los_lost_limit;     // [TUNABLE-PLACEHOLDER] frames without LOS before SEARCH (~3s = 180)
    int position_duration;  // [TUNABLE-PLACEHOLDER] frames in POSITION before AIM
    int aim_duration;       // [TUNABLE-PLACEHOLDER] frames in AIM before BURST
    int burst_count;        // [TUNABLE-PLACEHOLDER] number of projectiles per burst
    int burst_interval;     // [TUNABLE-PLACEHOLDER] frames between burst shots
    fixed projectile_speed; // [TUNABLE-PLACEHOLDER] 8.8 fixed projectile speed
    int projectile_damage;  // [TUNABLE-PLACEHOLDER] damage per projectile
} EnemyTuning;

extern const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];

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
    ENEMY_STATE_POSITION,
    ENEMY_STATE_AIM,
    ENEMY_STATE_BURST,
    ENEMY_STATE_COOLDOWN,
    ENEMY_STATE_DEAD
} EnemyState;

struct Enemy {
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
    fixed last_seen_x;
    fixed last_seen_y;
    int los_lost_timer;
    int burst_shots_left;
    int burst_interval_timer;
    int strafe_dir;
    int has_los;
    int stagger_slot;
};

int world_point_has_floor(int px, int py);
int position_is_free(fixed x, fixed y);
int bullet_position_is_free(fixed x, fixed y);
int sweep_position(fixed *x, fixed *y, fixed dx, fixed dy);

// ---------------------------------------------------------------------------
// 3. Player Stats & Damage Function (Doom-style 1/3 armor absorption)
// ---------------------------------------------------------------------------

#define PLAYER_MAX_HP 100
#define PLAYER_MAX_ARMOR 100

struct PlayerState {
    int hp;
    int max_hp;
    int armor;
    int max_armor;
    int ammo[NUM_WEAPON_TYPES];
    WeaponType current_weapon;
    int is_dead;
    int invuln_timer;
};

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
