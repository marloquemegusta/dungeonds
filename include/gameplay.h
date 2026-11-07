#ifndef GAMEPLAY_H
#define GAMEPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "weapons.h"
#include "collision.h"
#include "player_sprite.h"

// ---------------------------------------------------------------------------
// 1. Enemy Types & Tuning Tables (Fixed-Point 8.8)
// ---------------------------------------------------------------------------

typedef enum {
    ENEMY_TYPE_NONE = 0,
    ENEMY_TYPE_CHARGER,
    ENEMY_TYPE_SHOOTER,
    ENEMY_TYPE_SKELETON,    // 0.3.1: slow melee mass (the old v0.3 charger AI); the new charger lunges
    NUM_ENEMY_TYPES
} EnemyType;

typedef struct {
    int max_hp;             // [TUNABLE-PLACEHOLDER] base health points
    fixed speed;            // [TUNABLE-PLACEHOLDER] 8.8 fixed movement speed
    int attack_cooldown;    // [TUNABLE-PLACEHOLDER] frames between bites (skeleton) / after a laser shot (shooter)
    int preferred_dist_min; // [TUNABLE-PLACEHOLDER] min distance band (ground px); melee types: 0
    int preferred_dist_max; // [TUNABLE-PLACEHOLDER] max distance band (ground px); skeleton: melee range
    int position_duration;  // [TUNABLE-PLACEHOLDER] shooter: frames settling before it starts a laser
    int telegraph_duration; // [TUNABLE-PLACEHOLDER] charger: frames standing still and blinking before the charge
    fixed charge_speed;     // [TUNABLE-PLACEHOLDER] charger: 8.8 fixed speed of the charge
} EnemyTuning;

// Charger (DESIGN.md 6.9.1): APPROACH (CHASE) -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE.
#define CHARGER_ENGAGE_DIST 160     // [TUNABLE-PLACEHOLDER] ground px: with a clear view this close it telegraphs
#define CHARGER_CHARGE_FRAMES 63    // [TUNABLE-PLACEHOLDER] frames of charge (~160 px at 650)
#define CHARGER_RECOVER_FRAMES 60   // [TUNABLE-PLACEHOLDER] frames standing still after the charge, vulnerable
#define CHARGER_STUN_WALL_FRAMES 90 // [TUNABLE-PLACEHOLDER] stunned after hitting a wall or column
#define CHARGER_STUN_HIT_FRAMES 60  // [TUNABLE-PLACEHOLDER] stunned by a shotgun hit during telegraph or charge
#define CHARGER_HIT_RADIUS 14       // [TUNABLE-PLACEHOLDER] ground px: the charge hurts the player this close

// Shooter laser (DESIGN.md 6.9.1): POSITION -> LASER_AIM -> LASER_FIX -> LASER_FIRE -> COOLDOWN -> POSITION.
#define SHOOTER_LASER_TRACK_FRAMES 40  // [TUNABLE-PLACEHOLDER] thin green line follows the player
#define SHOOTER_LASER_FIX_FRAMES 20    // [TUNABLE-PLACEHOLDER] last frames of the charge: the line is locked and wider
#define SHOOTER_LASER_FIRE_FRAMES 8    // [TUNABLE-PLACEHOLDER] frames the beam is lethal
#define SHOOTER_LASER_LENGTH 320       // [TUNABLE-PLACEHOLDER] ground px; also the bound of the draw loop
#define SHOOTER_LASER_HALF_WIDTH 7     // [TUNABLE-PLACEHOLDER] ground px either side of the line that hurt
#define SHOOTER_MAX_CHARGING 2         // [TUNABLE-PLACEHOLDER] shooters charging a laser at once; the rest wait in their band

// The sprite of each enemy type: the only place that maps tiers to models.
static inline int enemy_type_char_id(EnemyType type) {
    if (type == ENEMY_TYPE_SHOOTER) return CHAR_NECRON;
    if (type == ENEMY_TYPE_SKELETON) return CHAR_SKELETON;
    return CHAR_CHARGER;
}

// State a freshly spawned or woken enemy starts in.
#define ENEMY_INITIAL_STATE(type) ((type) == ENEMY_TYPE_SHOOTER ? ENEMY_STATE_POSITION : ENEMY_STATE_CHASE)

extern const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];

// ---------------------------------------------------------------------------
// 2. Generic Enemy Pool
// ---------------------------------------------------------------------------

#define MAX_GAMEPLAY_ENEMIES 24     // every enemy of the dungeon exists from the start (dormant until woken)

// Skeleton: CHASE <-> ATTACK. Charger: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE (STUNNED from
// a wall hit or a shotgun hit). Shooter: POSITION -> LASER_AIM -> LASER_FIX -> LASER_FIRE -> COOLDOWN -> POSITION.
typedef enum {
    ENEMY_STATE_CHASE = 0,
    ENEMY_STATE_ATTACK,
    ENEMY_STATE_POSITION,
    ENEMY_STATE_TELEGRAPH,
    ENEMY_STATE_CHARGE,
    ENEMY_STATE_RECOVER,
    ENEMY_STATE_STUNNED,
    ENEMY_STATE_LASER_AIM,
    ENEMY_STATE_LASER_FIX,
    ENEMY_STATE_LASER_FIRE,
    ENEMY_STATE_COOLDOWN,
    ENEMY_STATE_DEAD,
    ENEMY_STATE_DORMANT       // v0.2: standing still in its pack until the pack wakes (DESIGN.md 5)
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
    int charge_hit;     // charger: 1 once this charge has hurt the player (one hit per charge)
    int aim_dir_x;      // 8.8 unit direction in ground metric: charger lunge / shooter laser line
    int aim_dir_y;
    int strafe_dir;
    int has_los;        // cached view of the player (bit flags, refreshed every few frames)
    fixed knock_vx;     // 8.8 shove velocity applied while stunned
    fixed knock_vy;
    int stun_timer;     // frames the enemy stays staggered after a shotgun hit
    int pack;           // pack index from the arena data (woken, healed and rewarded together)
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
