#ifndef GAMEPLAY_H
#define GAMEPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "weapons.h"
#include "collision.h"

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
    int attack_cooldown;    // [TUNABLE-PLACEHOLDER] frames between bites (charger) / bursts (shooter)
    int preferred_dist_min; // [TUNABLE-PLACEHOLDER] min distance band (ground px); charger: 0
    int preferred_dist_max; // [TUNABLE-PLACEHOLDER] max distance band (ground px); charger: melee range
    int position_duration;  // [TUNABLE-PLACEHOLDER] shooter: frames settling before it telegraphs
    int telegraph_duration; // [TUNABLE-PLACEHOLDER] shooter: frames of weapon flash before a burst
    int burst_count;        // [TUNABLE-PLACEHOLDER] shooter: projectiles per burst
    int burst_interval;     // [TUNABLE-PLACEHOLDER] shooter: frames between burst shots
    fixed projectile_speed; // [TUNABLE-PLACEHOLDER] shooter: 8.8 fixed projectile speed
} EnemyTuning;

extern const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];

// ---------------------------------------------------------------------------
// 2. Generic Enemy Pool
// ---------------------------------------------------------------------------

#define MAX_GAMEPLAY_ENEMIES 10

// Charger: CHASE <-> ATTACK. Shooter: POSITION -> TELEGRAPH -> BURST -> COOLDOWN -> POSITION.
typedef enum {
    ENEMY_STATE_CHASE = 0,
    ENEMY_STATE_ATTACK,
    ENEMY_STATE_POSITION,
    ENEMY_STATE_TELEGRAPH,
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
    int hp;
    int max_hp;
    int hit_timer;
    EnemyType type;
    EnemyState state;
    int state_timer;
    int burst_shots_left;
    int burst_interval_timer;
    int strafe_dir;
    int has_los;        // cached view of the player (bit flags, refreshed every few frames)
    fixed knock_vx;     // 8.8 shove velocity applied while stunned
    fixed knock_vy;
    int stun_timer;     // frames the enemy stays staggered after a shotgun hit
};

// Applies damage to an enemy. On a kill it marks the enemy dead, records the kill
// with the encounter manager and notifies the death hook.
void enemy_hit(Enemy *e, int damage, fixed hit_vx, fixed hit_vy);

// Presentation hook called by enemy_hit() when an enemy dies (e.g. death chunks).
// The renderer owns the visuals; gameplay code never depends on it directly.
typedef void (*EnemyDeathHook)(const Enemy *e, fixed hit_vx, fixed hit_vy);
void enemy_set_death_hook(EnemyDeathHook hook);

// ---------------------------------------------------------------------------
// 3. Player Stats (DESIGN.md 4.2: a handful of hits)
// ---------------------------------------------------------------------------

#define PLAYER_MAX_HP 5              // hits the player can take
#define PLAYER_IFRAMES 60            // invulnerability frames after a hit

struct PlayerState {
    int hp;
    int max_hp;
    WeaponType current_weapon;
    int is_dead;
    int invuln_timer;
    int god_mode;      // debug: L+R+B toggles; damage is ignored (headless scenarios)
};

extern PlayerState g_player_state;

// Frames the whole simulation freezes after an impact (hitstop). The main loop
// consumes it; enemy_hit() raises it.
extern int g_hitstop_frames;

/**
 * A hit from an enemy: removes one hit point, starts the i-frames and kills the
 * player at zero. Returns 1 when the hit landed (0 during i-frames, in god mode
 * or when already dead).
 */
int player_take_hit(PlayerState *player);

/**
 * Initializes the player for a new arena: full health, shotgun, no i-frames.
 */
void player_state_init(PlayerState *player);

// ---------------------------------------------------------------------------
// 4. Deterministic Integer RNG (LCG)
// ---------------------------------------------------------------------------

void rng_seed(uint32_t seed);
uint32_t rng_next(void);
int rng_range(int min, int max);

#endif // GAMEPLAY_H
