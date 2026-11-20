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
    ENEMY_TYPE_EXVOTO,      // wax nun: slow melee mass (DESIGN.md 6.10); replaces the skeleton. Prays, wakes, then the old skeleton AI
    ENEMY_TYPE_ABANDERADO,  // Boss (minimal v1): patrols, points banner, summons cream puddles + monaguillos
    ENEMY_TYPE_MONAGUILLO,  // Exvoto variant summoned by Abanderado: 1-hit, slow prayer-walk, emerges from puddle
    ENEMY_TYPE_BEBE,        // Exvoto tier: swarm, dies in one hit, a bit faster than the base (v3 tiers)
    ENEMY_TYPE_PARROCO,     // Exvoto tier: melee tank, x4 life, hits harder and shoves the hero (v3 tiers)
    ENEMY_TYPE_MONJA,       // Exvoto tier: support, stays behind praying and heals nearby Exvotos (v3 tiers)
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

// Exvoto (DESIGN.md 6.10, "Exvoto en el juego, versión mínima"): PRAY (still, loop of the pose) -> wake ->
// RISE (kneeling ones only, stand_up clip, still) -> CHASE <-> ATTACK like the old skeleton.
#define EXVOTO_WAKE_RADIUS 96          // [TUNABLE-PLACEHOLDER] ground px: the hero this close wakes a praying Exvoto
#define EXVOTO_CHAIN_WAKE_RADIUS 48    // [TUNABLE-PLACEHOLDER] ground px: a waking Exvoto wakes the praying ones this close
#define EXVOTO_KNEEL_PERCENT 100       // [TUNABLE-PLACEHOLDER] share of praying Exvotos on their knees (100: all of them; the horde mass arrives walking, so the ones met praying kneel and rise when woken)
#define EXVOTO_RISE_FRAMES 72          // [TUNABLE-PLACEHOLDER] frames of the stand_up clip (8 frames x 9 ticks, characters.json)
#define EXVOTO_PRAY_SEARCH_PX 24       // [TUNABLE-PLACEHOLDER] a praying Exvoto this close to a devout piece has claimed it

// Charger (DESIGN.md 6.9.1): APPROACH (CHASE) -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE.
#define CHARGER_ENGAGE_DIST 160     // [TUNABLE-PLACEHOLDER] ground px: with a clear view this close it telegraphs
#if ENCOUNTERS_PROTO
#define CHARGER_CHARGE_FRAMES 45    // [TUNABLE-PLACEHOLDER] v2 (variant "encuentros"): ~175 px at 1000
#define CHARGER_RECOVER_FRAMES 20   // [TUNABLE-PLACEHOLDER] v2: short recovery when the charge hits nothing
#else
#define CHARGER_CHARGE_FRAMES 63    // [TUNABLE-PLACEHOLDER] frames of charge (~160 px at 650)
#define CHARGER_RECOVER_FRAMES 60   // [TUNABLE-PLACEHOLDER] frames standing still after the charge, vulnerable
#endif
#define CHARGER_STUN_WALL_FRAMES 90 // [TUNABLE-PLACEHOLDER] stunned after hitting a wall or column
#define CHARGER_STUN_HIT_FRAMES 60  // [TUNABLE-PLACEHOLDER] stunned by a ray hit during telegraph or charge
#define CHARGER_HIT_RADIUS 14       // [TUNABLE-PLACEHOLDER] ground px: the charge hurts the player this close

// Ojo del Tribunal (DESIGN.md 6.10, "Mirada colimada"), ENEMY_TYPE_SHOOTER:
// CHASE (search) -> TRACK (green band follows the hero) -> LOCK (line frozen) -> SENTENCE (beam from the mouth)
// -> COOLDOWN -> CHASE (POSITION: waiting for a free aiming slot).
#define OJO_SIGHT_RANGE 1000       // [TUNABLE-PLACEHOLDER] ground px (dy counts double): "no range, line of sight only": the farthest point of a room is ~800, so any distance inside one is in range; sq 1.05M fits int32 with the margin
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
#define OJO_BEAM_MAX_LEN 1100      // [TUNABLE-PLACEHOLDER] ground px (hit test, wall march) >= OJO_SIGHT_RANGE + OJO_RANGE_MARGIN so the beam reaches the hero from anywhere; also the bound of the beam and band draw loops

// El Abanderado (jefe, version minima, DESIGN.md 6.10):
#define ABANDERADO_SIGHT_RANGE 160       // [TUNABLE-PLACEHOLDER] ground px: ~1 screen
#define ABANDERADO_SIGHT_MARGIN 24       // [TUNABLE-PLACEHOLDER] hysteresis while pointing
#define ABANDERADO_LOSE_SIGHT_FRAMES 120 // [TUNABLE-PLACEHOLDER] 2 s out of sight before returning to patrol
#define ABANDERADO_SUMMON_FRAMES 180     // [TUNABLE-PLACEHOLDER] ~3 s between cream puddles
#define ABANDERADO_SPAWN_FRAMES 7200     // [TUNABLE-PLACEHOLDER] 2:00 (at 60 FPS) first spawn and respawn after death
extern int g_abanderado_max_mona;        // [TUNABLE-PLACEHOLDER] cap of live monaguillos at once (8, 12 or 16: set per boss floor)
#define MONAGUILLO_EMERGE_FRAMES 30      // [TUNABLE-PLACEHOLDER] ~0.5 s emerging from puddle (invulnerable, still)

// The sprite of each enemy type: the only place that maps tiers to models.
static inline int enemy_type_char_id(EnemyType type) {
    if (type == ENEMY_TYPE_SHOOTER) return CHAR_OJO;
    if (type == ENEMY_TYPE_EXVOTO) return CHAR_EXVOTO;     // base walk slot; a praying Exvoto swaps char_id per pose
    if (type == ENEMY_TYPE_ABANDERADO) return CHAR_ABANDERADO;
    if (type == ENEMY_TYPE_MONAGUILLO) return CHAR_MONAGUILLO;
    // Exvoto tiers: only the Bebé has its own baked sheet; the Párroco and the Monja borrow the Exvoto slot
    // (their own sheets do not fit in EWRAM yet, see TECHNICAL.md). A praying Monja swaps to the pray slot.
    if (type == ENEMY_TYPE_BEBE) return CHAR_EXVOTO_BEBE;
    if (type == ENEMY_TYPE_PARROCO) return CHAR_EXVOTO;
    if (type == ENEMY_TYPE_MONJA) return CHAR_EXVOTO;
    return CHAR_CHARGER;
}

// State a freshly spawned or woken enemy starts in.
#define ENEMY_INITIAL_STATE(type) ENEMY_STATE_CHASE

// The variant "encuentros" overwrites the lives at boot (enc_init, tools/encuentros/acto1.json): its table is writable.
#if ENCOUNTERS_PROTO
#define ENEMY_TUNING_CONST
#else
#define ENEMY_TUNING_CONST const
#endif
extern ENEMY_TUNING_CONST EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES];

// ---------------------------------------------------------------------------
// 2. Generic Enemy Pool
// ---------------------------------------------------------------------------

#ifndef STRESS_TEST
#define STRESS_TEST 0               // 1 = measurement build: big horde, 1 HP enemies, god mode (variants stress / stress-perf)
#endif
// Demo ROM (DESIGN.md 6.9.1c): the sacred ray (WEAPON_SNIPER) is the only weapon.
#if STRESS_TEST
#define MAX_GAMEPLAY_ENEMIES 64
#else
#define MAX_GAMEPLAY_ENEMIES 24     // every enemy of the dungeon exists from the start (dormant until woken)
#endif

// Exvoto (ex skeleton): PRAY -> RISE -> CHASE <-> ATTACK. Charger: CHASE -> TELEGRAPH -> CHARGE -> RECOVER -> CHASE (STUNNED from
// a wall hit or a ray hit). Ojo (shooter type): CHASE -> TRACK -> LOCK -> SENTENCE -> COOLDOWN -> CHASE.
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
    ENEMY_STATE_POINT,        // Abanderado: stopped, head up, staff tilted forward, summoning puddles
    ENEMY_STATE_EMERGE,       // Monaguillo: emerging from a cream puddle (~0.5 s, invulnerable, no damage/move)
    ENEMY_STATE_DEAD,
    ENEMY_STATE_DORMANT,      // v0.2: standing still in its pack until the pack wakes (DESIGN.md 5)
    ENEMY_STATE_PRAY,         // Exvoto: praying in front of a devout piece until the hero comes close or hits it
    ENEMY_STATE_RISE,         // Exvoto: getting up from its knees (stand_up clip), then CHASE
    ENEMY_STATE_SUSPENDED,    // Viatico: killed (counted dead) but held inert ~0.3 s while the thread leaves its body
    ENEMY_STATE_WOBBLE,       // Exvoto: reeling after a hit that did not kill (glows, still, no dodge); L finishes it (remate.h)
    ENEMY_STATE_REMATE,       // Exvoto: held inert while the hero's finisher animation plays (remate.h)
    ENEMY_STATE_GUARD         // Exvoto / Cireneo of the garrison (DESIGN.md 6.13.9): awake but holding its post, facing the hero, until released
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
    uint8_t kneel;      // Exvoto: 1 = prays on its knees (and rises when woken), 0 = prays standing (fits in enum padding)
    uint8_t home_flags; // ENEMY_HOME_*: post and garrison bits (encounter rooms, see enemy_home_x); fits the last byte of the enum padding
    int state_timer;
    int charge_hit;     // charger: 1 once this charge has hurt the player (one hit per charge)
    int aim_dir_x;      // 8.8 unit direction in ground metric: charger lunge / Ojo sentence beam
    int aim_dir_y;
    int strafe_dir;
    int has_los;        // cached view of the player (bit flags, refreshed every few frames)
    fixed knock_vx;     // 8.8 shove velocity applied while stunned
    fixed knock_vy;
    int stun_timer;     // frames the enemy stays staggered after a ray hit
    int pack;           // pack index from the arena data (woken, healed and rewarded together)
    int aim_px;         // Ojo: ground world px of the hero where the gaze points (followed in TRACK, frozen in LOCK/SENTENCE)
    int aim_py;
    int beam_len;       // Ojo: ground px of the sentence beam (cut at the first wall), set when it fires
    int gesture;        // Ojo: 0 = none; 1.. = game frames of the sentence gesture (held on its last frame while SENTENCE lasts)
    int beam_mx;        // Ojo: ground world px of the mouth when it fired (the damage line starts here)
    int beam_my;
    int beam_ux;        // Ojo: true-ground unit vector of the damage line, 8.8
    int beam_uy;
    // Quemado (DESIGN.md 6.12.2): layers stack up to the cap, the timer renews on every application.
    uint8_t burn_layers;    // 0..cap (5 + Rescoldo)
    uint8_t burn_tick;      // frames since the last fire tick
    uint8_t burn_ember;     // frames until the next ember of the visual (weapons.c)
    uint8_t votive_hits;    // Llama Votiva: frames of contact with the aim line since the last layer
    uint16_t burn_timer;    // frames of Quemado left
    uint8_t suspend_timer;  // Viatico: frames left of the suspended death (fits the tail padding: sizeof stays 124)
    uint8_t suspend_req;    // Viatico: the next lethal hit suspends the death instead of finishing it
};

// Garrison and Ojo leash (DESIGN.md 6.13.9). The post ("home", world px) lives in fields the type does not use, so sizeof(Enemy) stays
// (scenarios read g_enemies by offset): the Ojo in charge_hit / strafe_dir, the Exvoto and the Cireneo in aim_px / aim_py (zeroed on release).
#define ENEMY_HOME_SET 1       // the enemy has a post (encounter spawns: every Ojo and every guard)
#define ENEMY_HOME_GUARD 2     // spawned as garrison: when the room wakes it goes to ENEMY_STATE_GUARD instead of CHASE
static inline int *enemy_home_x(struct Enemy *e) { return e->type == ENEMY_TYPE_SHOOTER ? &e->charge_hit : &e->aim_px; }
static inline int *enemy_home_y(struct Enemy *e) { return e->type == ENEMY_TYPE_SHOOTER ? &e->strafe_dir : &e->aim_py; }
#define GUARD_RELEASE_DIST 220   // [TUNABLE-PLACEHOLDER] ground px (dy counts double) from its post: the hero this close releases a guard
#define GUARD_OJO_BOND_DIST 90   // [TUNABLE-PLACEHOLDER] ground px between the guard's post and an Ojo's post: the Ojos it guards; it is released when none of them lives
#define OJO_PURSUE_TICKS 8             // [TUNABLE-PLACEHOLDER] frames between the Ojo's checks of its line to the hero (power of two)
#define OJO_PURSUE_LOOKAHEAD 30        // [TUNABLE-PLACEHOLDER] frames ahead (at the hero's current velocity) whose position the Ojo also wants in view
#define OJO_PURSUE_IN_COOLDOWN 1       // [TUNABLE-PLACEHOLDER] 1 = the Ojo also keeps the hero in view while it waits out the cooldown after a sentence
#define OJO_REPOSITION_SPEED_PCT 100   // [TUNABLE-PLACEHOLDER] % of its normal speed while repositioning
#define OJO_LEASH_DIST 288             // [TUNABLE-PLACEHOLDER] ground px: it never goes farther than this from its post
#define OJO_SEARCH_COL_PX 24           // [TUNABLE-PLACEHOLDER] px between the candidate columns of the reposition search
#define OJO_SEARCH_COLS 12             // [TUNABLE-PLACEHOLDER] columns each side of the post (covers the leash)
#define OJO_SEARCH_ROW_PX 32           // [TUNABLE-PLACEHOLDER] px between the candidate rows
#define OJO_SEARCH_ROWS 5              // [TUNABLE-PLACEHOLDER] rows above and below the post's row (the leash and OJO_LEASH_DOWN_PX trim them)
#define OJO_LEASH_DOWN_PX 80           // [TUNABLE-PLACEHOLDER] screen px: it never goes lower than its post row plus this

// Quemado: layers, tick and slow (DESIGN.md 6.12.10). burn_update runs once a frame from weapons_update.
#define BURN_BASE_CAP 5          // [TUNABLE-PLACEHOLDER] layers
#define BURN_BASE_FRAMES 120     // [TUNABLE-PLACEHOLDER] duration, renewed on every application
#define BURN_TICK_FRAMES 15      // [TUNABLE-PLACEHOLDER] frames between fire ticks
#define BURN_TICK_DAMAGE 3       // [TUNABLE-PLACEHOLDER] fire damage per layer per tick
void burn_apply(struct Enemy *e, int layers);
void burn_clear(struct Enemy *e);
void burn_update(struct Enemy *enemies, int max_enemies);

// Walking speed under Quemado: 10 % less per layer, up to 50 % (26/256 ~ 10.2 %).
static inline fixed burn_slow(const struct Enemy *e, fixed speed) {
    int l = e->burn_layers;
    if (l <= 0) return speed;
    if (l > 5) l = 5;
    return speed - ((speed * l * 26) >> 8);
}

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

// Abanderado sprite clips: walk (CHAR_ABANDERADO slot) or point (head up + staff tilted forward).
#define CLIP_ABANDERADO_WALK 0
#define CLIP_ABANDERADO_POINT 1
#define ABANDERADO_POINT_PERIOD 2   // [TUNABLE-PLACEHOLDER] game frames per transition frame (16 frames total, holds last)

static inline int abanderado_clip(const struct Enemy *e) {
    if (e->char_id != CHAR_ABANDERADO) return CLIP_ABANDERADO_WALK;
    if (e->state == ENEMY_STATE_POINT) return CLIP_ABANDERADO_POINT;
    return CLIP_ABANDERADO_WALK;
}

static inline int abanderado_clip_frame(const struct Enemy *e, int clip) {
    if (clip == CLIP_ABANDERADO_POINT) {
        int f = (e->gesture > 0 ? e->gesture - 1 : 0) / ABANDERADO_POINT_PERIOD;
        return f < ABANDERADO_POINT_NUM_FRAMES ? f : ABANDERADO_POINT_NUM_FRAMES - 1;
    }
    return e->frame;
}

// Applies damage to an enemy. On a kill it marks the enemy dead, records the kill
// with the encounter manager and notifies the death hook.
void enemy_hit(Enemy *e, int damage, fixed hit_vx, fixed hit_vy);
// Fire damage (burn ticks, explosions): same kill path and death hook, but no hit stop, flash or sounds.
void enemy_hit_quiet(Enemy *e, int damage);

// Presentation hook called by enemy_hit() when an enemy dies (e.g. death chunks).
// The renderer owns the visuals; gameplay code never depends on it directly.
// g_death_phase tells the hook what to do: 0 everything, 1 only the bookkeeping (counters; the
// death is suspended), 2 only the visuals (the suspension ended).
#define DEATH_ALL 0
#define DEATH_BOOKKEEPING 1
#define DEATH_VISUALS 2
extern int g_death_phase;
#define SUSPEND_FRAMES 18            // [TUNABLE-PLACEHOLDER] Viatico: ~0.3 s inert before the death animation
void enemy_suspend_update(Enemy *enemies, int max_enemies);
typedef void (*EnemyDeathHook)(const Enemy *e, fixed hit_vx, fixed hit_vy);
void enemy_set_death_hook(EnemyDeathHook hook);

// Cream puddles summoned by El Abanderado (DESIGN.md 6.10).
void enemy_puddles_init(void);
void enemy_puddles_shift_y(int dy_px);
void enemy_puddles_update(void);
void enemy_puddles_render(uint16_t *buffer, int cam_x, int cam_y);

// ---------------------------------------------------------------------------
// 3. Player Stats (DESIGN.md 4.2: a handful of hits)
// ---------------------------------------------------------------------------

#define PLAYER_MAX_HP 5              // hits the player can take
#define PLAYER_IFRAMES 60            // invulnerability frames after a hit

struct PlayerState {
    int hp;             // life in points (ARPG: arpg.h)
    int max_hp;
    WeaponType current_weapon;
    int is_dead;
    int invuln_timer;
    int god_mode;      // debug: L+R+B toggles; damage is ignored (headless scenarios)
    int mana;           // ARPG: spent by spells, regenerates slowly (arpg.h). Appended: scenarios read the fields above by offset
    int max_mana;
};

extern PlayerState g_player_state;

// Frames the whole simulation freezes after an impact (hitstop). The main loop
// consumes it; enemy_hit() raises it.
extern int g_hitstop_frames;

/**
 * A hit that removes `damage` points of life, starts the i-frames and kills the
 * player at zero. Returns 1 when the hit landed (0 during i-frames, in god mode
 * or when already dead).
 */
int player_take_damage(PlayerState *player, int damage);

/**
 * A hit with the default damage (ARPG_DMG_DEFAULT). Wrapper of player_take_damage.
 */
int player_take_hit(PlayerState *player);

/**
 * Initializes the player for a new arena: full health, sacred ray, no i-frames.
 */
void player_state_init(PlayerState *player);

// Párroco tier shove (v3): the hero is pushed this 8.8 velocity for `frames` frames (ground metric). No-op if already pushing.
void player_apply_push(fixed vx, fixed vy, int frames);
// The shove state lives outside PlayerState (its layout is fixed by the scenarios): read it here, and spend one
// frame (decrements the counter and eases the velocity). Returns 1 while a shove is active this frame.
int player_push_step(fixed *out_vx, fixed *out_vy);

// ---------------------------------------------------------------------------
// 4. Deterministic Integer RNG (LCG)
// ---------------------------------------------------------------------------

void rng_seed(uint32_t seed);
uint32_t rng_next(void);
int rng_range(int min, int max);

#endif // GAMEPLAY_H
