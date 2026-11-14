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
    int attack_cooldown;    // [TUNABLE-PLACEHOLDER] frames between bites (skeleton) / after a sentence (Ojo)
    int preferred_dist_max; // [TUNABLE-PLACEHOLDER] skeleton: melee range (ground px); others: 0
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

// Ojo del Tribunal (DESIGN.md 6.10, "Mirada colimada"), ENEMY_TYPE_SHOOTER:
// CHASE (search) -> TRACK (green band follows the hero) -> LOCK (line frozen) -> SENTENCE (beam from the mouth)
// -> COOLDOWN -> CHASE (POSITION: waiting for a free aiming slot).
#define OJO_SIGHT_RANGE 140        // [TUNABLE-PLACEHOLDER] ground px: it stops and aims from this far with line of sight
#define OJO_RANGE_MARGIN 24        // [TUNABLE-PLACEHOLDER] ground px beyond the sight range where a tracking Ojo still follows the hero
#define OJO_TRACK_FRAMES 40        // [TUNABLE-PLACEHOLDER] frames the band follows the hero while it narrows
#define OJO_LOCK_FRAMES 20         // [TUNABLE-PLACEHOLDER] frames the line stays frozen: the dodge window
#define OJO_AIM_FRAMES (OJO_TRACK_FRAMES + OJO_LOCK_FRAMES) // [TUNABLE-PLACEHOLDER] derived: whole aim, also the mouth charge
#define OJO_BEAM_IMPACT_FRAMES 3   // [TUNABLE-PLACEHOLDER] "llamarada espectral": widest and brightest; it hurts
#define OJO_BEAM_FLARE_FRAMES 20   // [TUNABLE-PLACEHOLDER] wide, burning edges; it still hurts (a temporary wall)
#define OJO_BEAM_FADE_FRAMES 8     // [TUNABLE-PLACEHOLDER] dissipation: narrows and breaks up; it no longer hurts
#define OJO_BEAM_HIT_FRAMES (OJO_BEAM_IMPACT_FRAMES + OJO_BEAM_FLARE_FRAMES) // [TUNABLE-PLACEHOLDER] derived: frames that hurt
#define OJO_BEAM_FRAMES (OJO_BEAM_HIT_FRAMES + OJO_BEAM_FADE_FRAMES) // [TUNABLE-PLACEHOLDER] derived: whole SENTENCE, the Ojo stands still
#define OJO_HIT_HALF_WIDTH 8       // [TUNABLE-PLACEHOLDER] ground px either side of the locked line that the beam hurts
#define OJO_MAX_LOOKING 2          // [TUNABLE-PLACEHOLDER] Ojos aiming at once (TRACK, LOCK, SENTENCE); the rest wait
#define OJO_WAIT_DIST 72           // [TUNABLE-PLACEHOLDER] ground px: an Ojo this close without a free slot waits instead of walking in
#define OJO_TARGET_HEIGHT 14       // [TUNABLE-PLACEHOLDER] px above the hero's feet the gaze and beam aim at (chest)
#define OJO_BEAM_MAX_LEN 200       // [TUNABLE-PLACEHOLDER] ground px; also the bound of the beam and band draw loops

// The sprite of each enemy type: the only place that maps tiers to models.
static inline int enemy_type_char_id(EnemyType type) {
    if (type == ENEMY_TYPE_SHOOTER) return CHAR_OJO;
    if (type == ENEMY_TYPE_SKELETON) return CHAR_SKELETON;
    return CHAR_CHARGER;
}

// State a freshly spawned or woken enemy starts in.
#define ENEMY_INITIAL_STATE(type) ENEMY_STATE_CHASE

extern const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];

// ---------------------------------------------------------------------------
// 2. Generic Enemy Pool
// ---------------------------------------------------------------------------

#ifndef STRESS_TEST
#define STRESS_TEST 0               // 1 = measurement build: big horde, 1 HP enemies, god mode (variants stress / stress-perf)
#endif
#if STRESS_TEST
#define MAX_GAMEPLAY_ENEMIES 64
#else
#define MAX_GAMEPLAY_ENEMIES 24     // every enemy of the dungeon exists from the start (dormant until woken)
#endif

// Skeleton: CHASE <-> ATTACK. Charger: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE (STUNNED from
// a wall hit or a shotgun hit). Ojo (shooter type): CHASE -> TRACK -> LOCK -> SENTENCE -> COOLDOWN -> CHASE.
typedef enum {
    ENEMY_STATE_CHASE = 0,
    ENEMY_STATE_ATTACK,
    ENEMY_STATE_POSITION,
    ENEMY_STATE_TELEGRAPH,
    ENEMY_STATE_CHARGE,
    ENEMY_STATE_RECOVER,
    ENEMY_STATE_STUNNED,
    ENEMY_STATE_TRACK,        // Ojo: stopped, the green band from the lantern follows the hero (state_timer counts down)
    ENEMY_STATE_LOCK,         // Ojo: the line is frozen where the hero was; the shot falls when the timer runs out
    ENEMY_STATE_SENTENCE,     // Ojo: the beam from the mouth along the locked line (one hit)
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
    int aim_dir_x;      // 8.8 unit direction in ground metric: charger lunge / Ojo sentence beam
    int aim_dir_y;
    int strafe_dir;
    int has_los;        // cached view of the player (bit flags, refreshed every few frames)
    fixed knock_vx;     // 8.8 shove velocity applied while stunned
    fixed knock_vy;
    int stun_timer;     // frames the enemy stays staggered after a shotgun hit
    int pack;           // pack index from the arena data (woken, healed and rewarded together)
    int aim_px;         // Ojo: ground world px of the hero where the gaze points (followed in TRACK, frozen in LOCK/SENTENCE)
    int aim_py;
    int beam_len;       // Ojo: ground px of the sentence beam (cut at the first wall), set when it fires
    int gesture;        // Ojo: 0 = none; 1.. = game frames of the sentence gesture (held on its last frame while SENTENCE lasts)
    int beam_mx;        // Ojo: ground world px of the mouth when it fired (the damage line starts here)
    int beam_my;
    int beam_ux;        // Ojo: true-ground unit vector of the damage line, 8.8
    int beam_uy;
};

// Ojo del Tribunal sprite clips (player_sprite.h): the walk is the CHAR_OJO slot; TRACK/LOCK show the look
// loop (e->frame) and the sentence gesture shows the sentence clip (frame from e->gesture).
#define CLIP_OJO_WALK 0
#define CLIP_OJO_LOOK 1
#define CLIP_OJO_SENTENCE 2
#define OJO_LOOK_PERIOD 16          // [TUNABLE-PLACEHOLDER] game frames per frame of the 4-frame look loop (a 64-frame breath)
#define OJO_GESTURE_PERIOD 3        // [TUNABLE-PLACEHOLDER] game frames per frame of the 6-frame sentence gesture (18 frames in all)
#define OJO_GESTURE_FRAMES (OJO_SENTENCE_NUM_FRAMES * OJO_GESTURE_PERIOD)   // [TUNABLE-PLACEHOLDER] derived

static inline int ojo_clip(const struct Enemy *e) {
    if (e->char_id != CHAR_OJO) return CLIP_OJO_WALK;
    if (e->gesture > 0 && (e->state == ENEMY_STATE_SENTENCE || e->state == ENEMY_STATE_COOLDOWN))
        return CLIP_OJO_SENTENCE;
    if (e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK) return CLIP_OJO_LOOK;
    return CLIP_OJO_WALK;
}

// Frame inside the clip ojo_clip() picked.
static inline int ojo_clip_frame(const struct Enemy *e, int clip) {
    if (clip == CLIP_OJO_SENTENCE) {
        int f = (e->gesture - 1) / OJO_GESTURE_PERIOD;
        return f < OJO_SENTENCE_NUM_FRAMES ? f : OJO_SENTENCE_NUM_FRAMES - 1;
    }
    if (clip == CLIP_OJO_LOOK) return e->frame & (OJO_LOOK_NUM_FRAMES - 1);
    return e->frame;
}

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
