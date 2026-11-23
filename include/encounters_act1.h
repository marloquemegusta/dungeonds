#ifndef ENCOUNTERS_ACT1_H
#define ENCOUNTERS_ACT1_H

#include <stdint.h>
#include <stddef.h>
#include "game.h"
#include "gameplay.h"

// Prototype of the act I as encounters and corridors (DESIGN.md 6.13.6), build variant "encuentros"
// (ENCOUNTERS_PROTO=1). The design data lives in tools/encuentros/acto1.json and is compiled into
// source/encounters_act1_tables.h by tools/encuentros/gen_act1_tables.py. Nothing here exists in the
// normal build.

#if ENCOUNTERS_PROTO

#define ENC_FLOOR_X 152          // world x of the first floor pixel (the view shows world x 128..384)
#define ENC_FLOOR_W 208          // usable floor width
#define ENC_CAM_X 128            // fixed camera x: the view is one screen wide, no side scroll
#define ENC_BLOCK_H 384          // one block = 2 screens
#define ENC_COUNT 12             // encounters of the act
#define ENC_PLANT_COUNT 6
#define ENC_VERJA_H 56           // rastrillo piece height: stands at the foot of the corridor, base on the barrier line
#define ENC_BARRIER_H 8          // closed barrier: the top 8 px of the encounter block
#define ENC_WAKE_MARGIN 36       // the encounter wakes when the hero is this far inside its bottom edge (the rear barrier closes behind the body)
#define ENC_SPAWN_AHEAD 420      // enemies of an encounter appear (asleep) when the hero is this close to its entrance
#define ENC_MAX_RECTS 4
#define ENC_MAX_PIECES 8

enum { ENC_E_EXVOTO = 0, ENC_E_CIRENEO, ENC_E_OJO, ENC_E_ABANDERADO, ENC_E_MONAGUILLO,
       ENC_E_BEBE, ENC_E_PARROCO, ENC_E_MONJA,   // BEBE, PARROCO, MONJA: Exvoto tiers (v3)
       ENC_E_CAMPANERO };                         // boss of the ARPG (DESIGN-ARPG.md 9)
enum { ENC_S_PRAY = 0, ENC_S_DORMANT, ENC_S_AWAKE, ENC_S_GUARD };   // GUARD: wakes with the room but stays at its post (6.13.9)
enum { ENC_R_SACOS = 0, ENC_R_ALAMBRE, ENC_R_BARRERA };
enum { ENC_BLOCK_CLEAR = 0, ENC_BLOCK_ENCOUNTER, ENC_BLOCK_CORRIDOR, ENC_BLOCK_BOSS };

typedef struct { uint8_t piece; int16_t x, y; } EncPieceDef;
typedef struct { uint8_t kind; int16_t x, y, w, h; } EncRectDef;
typedef struct { uint8_t type, state; int16_t x, y; } EncEnemyDef;
typedef struct {
    const EncEnemyDef *enemies; uint8_t n;
    const EncEnemyDef *wave2; uint8_t n2;
} EncPopulation;
typedef struct {
    const EncPieceDef *pieces; uint8_t n_pieces;
    const EncRectDef *rects; uint8_t n_rects;
    EncPopulation pop[3];            // ligera, media, dura
} EncPlant;

// What a block of the strip is.
typedef struct {
    uint8_t kind;      // ENC_BLOCK_*
    uint8_t idx;       // encounter / corridor index (0..11)
    uint8_t plant;     // encounters only
    uint8_t tier;      // encounters only (0 ligera, 1 media, 2 dura)
    uint8_t mirror;    // 1 = left <-> right
} EncBlock;

// A piece to place in a block, before mirroring and before the legal phase is chosen.
typedef struct { uint8_t piece, mirror; int16_t lx, ly; } EncPiecePlan;
// An obstacle in block coordinates: x is already a WORLD x (mirrored), y is relative to the block top.
typedef struct { uint8_t kind; int16_t x, y, w, h; } EncRect;

void enc_init(uint32_t seed);
void enc_block_info(int32_t block, EncBlock *out);
int enc_block_pieces(int32_t block, EncPiecePlan *out, int max);
// Obstacles of a block plus the barrier when it is closed (read by the compositor and the painter).
int enc_block_rects(int32_t block, EncRect *out, int max);
// Collision value an obstacle writes into the grid: 1 stops bodies, 3 stops bodies and bullets.
int enc_collision_value(uint8_t rect_kind);

// Rooms (salas ARPG, mapa de la zona 1 variante D): the cathedral is a set of 16 rooms of 1..3 blocks. Only the room the
// hero is in exists in the strip; crossing a door loads the next one (main.c: fade, enc_room_select, strip_start, enc_room_arrival).
#define ENC_ROOM_COUNT 16
#define ENC_ROOM_NAVE1 0
#define ENC_ROOM_CRIPTA 15
// A lateral opening of a block: world x, block-relative y.
typedef struct { int16_t x, y, w, h; } EncRoomOpening;
// Chooses the room the next strip_start() builds. `from_room` = room the hero comes from (-1: from the camp or a debug start);
// it decides where enc_room_arrival() lands him. Call it BEFORE strip_start().
void enc_room_select(int room, int from_room);
// Seed for strip_start() of a room: always the same, so every room looks the same each visit.
uint32_t enc_room_seed(int room);
// Room the next restart loads when coming from the camp: the last altar touched (Nave 1 without one) or the debug start.
int enc_room_entry(void);
int enc_room_current(void);
int enc_room_level(void);                   // fixed level of the current room (1..5)
const char *enc_room_name(void);
int enc_room_top_block(void);               // strip block of the last block of the room; everything above it is black and solid
// Lateral openings (holes in the wall) of a strip block; returns how many (0..2).
int enc_room_openings(int32_t block, EncRoomOpening *out, int max);
int enc_block_has_door(int32_t block);      // 1 = the top door piece stands on this block (last block of a room with an exit upwards)
// Window px and facing where the hero lands after strip_start() (door of arrival, or the foot of the room).
int enc_room_arrival(int *out_x, int *out_y, int *out_dir);
// Consumes a crossing requested by enc_update(): 1 and the destination room in *out_room.
int enc_room_take_exit(int *out_room);
// Cripta boss beaten for the first time: 1 once, after its victory sequence has ended (main.c then shows the end-of-demo card).
int enc_end_demo_take(void);
// Campanero fight: a world point where the Campanero raises an Exvoto, picked by `r` (beside a column or a random floor spot).
void enc_camp_spot(uint32_t r, int *x, int *y);

// Overlay map (SELECT): layout of a room in map units, derived from the ficha of rooms (doors, heights of the lateral openings).
// x grows east from the left floor edge of Nave 1, y grows north from its foot (the way the hero climbs).
typedef struct { uint8_t side, dest; int16_t cx, cy; } EncMapDoor;    // side: 0 left, 1 right, 2 up; (cx, cy) on the wall
typedef struct {
    int16_t x, y, w, h;
    uint8_t n_doors, altar, chest, key;       // key: the group of this room drops the key of the zone
    int16_t altar_x, altar_y, chest_x, chest_y;
    EncMapDoor door[3];
} EncMapRoom;
void enc_map_room(int room, EncMapRoom *out);
int enc_map_hero(int px, int py, int *mx, int *my);   // hero (window px) in map units of the current room; returns the room id

// Once per simulated frame, after the strip rebase. px, py: hero ground point in window px.
void enc_update(Enemy *enemies, int max_enemies, int px, int py);
// Ground painter: obstacles and barriers (under the actors, over the floor).
void enc_draw_ground(uint16_t *buffer, int cam_x, int cam_y);
// Depth-sorted dynamic props (boss golden relicario, final Altar): returns 1 if visible on screen.
int enc_dynamic_relic_item(int cam_x, int cam_y, int *out_depth);
void enc_dynamic_relic_draw(uint16_t *buffer, int cam_x, int cam_y, int depth);
// Room fixtures (chests and travel altars) on this screen, depth-sorted with the actors. The list is
// rebuilt by the _count call of each screen; the _item/_draw calls read it.
int enc_dynamic_fixture_count(int cam_x, int cam_y);
int enc_dynamic_fixture_item(int index, int cam_x, int cam_y, int *out_depth);
void enc_dynamic_fixture_draw(int index, uint16_t *buffer, int cam_x, int cam_y, int depth);
// Hardware OBJ sprites for the rastrillo gates (called per screen during render_screen).
void enc_verja_draw(int sub, int cam_x, int cam_y);
// The sniper ray asks for the relicario target in front of the hero: ground point in window px.
int enc_relic_target(int *x, int *y);
void enc_relic_hit(int damage);
int enc_untouchable(const Enemy *e);       // 1 = the enemy belongs to an encounter that has not woken: no damage
void enc_note_beam_hit(const Enemy *e);   // stats: the ray hurt this enemy (after the damage was applied)
void enc_player_hit(void);                 // stats: the hero took a hit
void enc_stats_frame(void);                // stats: once per frame from the main loop (clock, result, capture triggers)
int enc_victory(void);
int enc_current_encounter(void);           // level of the room the hero is in (1..5): xp and loot level of the kills

// Debug / stats mailbox for the headless scenarios (symbols g_enc_debug, g_enc_stats).
typedef struct {
    uint8_t start_dones;     // 0  Dones to apply now, picking the first option each time (cleared when done)
    uint8_t auto_pick;       // 1  1 = every offer picks its first option at once (no menu); 2 = picks at random (seed), no menu
    uint8_t god;             // 2  1 = the hero ignores damage
    uint8_t no_dones;        // 3  1 = relicarios give no Don (the hero stays at base power)
    uint16_t seed;           // 4  seed of the random offer picks (auto_pick 2) and of the bot
    uint8_t bot_reaction;    // 6  bot: frames of delay before it reacts to what the enemies do (0 = instant)
    uint8_t bot_aim_err;     // 7  bot: random aiming error in px, +-
    uint8_t bot_ojo_delay;   // 8  bot: frames an Ojo must be in TRACK before the bot reacts to it
    uint8_t bot_miss_pct;    // 9  bot: % of Cireneo lunges it does not dodge (clumsy profile)
    uint8_t force_plant;     // 10 plant of the first encounter + 1 (0 = the seed decides); mirror forced to 0. Applied at the next restart
    uint8_t force_tier;      // 11 tier of the first encounter + 1 (0 = as planned)
    uint8_t restart;         // 12 1 = restart the act now (new strip, enc_init runs again); cleared by the game
    uint8_t cam_up;          // 13 debug: the camera looks this many px further up (the guide shows the whole block); 0 = normal
    uint16_t boss_hp;        // 14 Abanderado hearts (0 = the table); read when the boss spawns, set before the act starts
    uint8_t start_boss;      // 16 1 = the next restart starts at the boss: encounters 0..11 cleared, hero in the corridor just below the boss room
    uint8_t start_up4;       // 17 debug (recording shortcut): the hero starts this many 4-px steps higher than the usual spot (0 = normal)
    uint16_t boss_damage;    // 18 > 0: one shot of this damage at the boss (as the ray would deal it), then back to 0. Scenarios force phases and the kill
    uint8_t start_room;      // 20 room id + 1 the next restart loads (0 = normal entry: last altar); start_boss = 1 starts at the Cripta
    uint8_t pad_room;        // 21
} EncDebug;
_Static_assert(sizeof(EncDebug) == 22 && offsetof(EncDebug, start_room) == 20 && offsetof(EncDebug, boss_damage) == 18 && offsetof(EncDebug, start_boss) == 16 && offsetof(EncDebug, force_plant) == 10 && offsetof(EncDebug, restart) == 12 && offsetof(EncDebug, cam_up) == 13 && offsetof(EncDebug, bot_reaction) == 6 && offsetof(EncDebug, bot_ojo_delay) == 8 && offsetof(EncDebug, bot_miss_pct) == 9 && offsetof(EncDebug, auto_pick) == 1 && offsetof(EncDebug, god) == 2 &&
               offsetof(EncDebug, no_dones) == 3 && offsetof(EncDebug, seed) == 4,
               "EncDebug layout is read by scenarios by offset");
extern volatile EncDebug g_enc_debug;

// Debug mailbox for the tier captures (v3). `spawn` = 1: enc_update() places one Bebé, one Párroco and one
// praying Monja around the hero (all awake, already wounded so the Monja's heals show) and clears it. Only for
// headless evidence; the game never sets it.
typedef struct { uint8_t spawn; uint8_t pad[3]; } EncTierDebug;
extern volatile EncTierDebug g_tier_debug;

enum { ENC_STATE_PLAYING = 0, ENC_STATE_VICTORY = 1, ENC_STATE_DEAD = 2 };
typedef struct {
    uint8_t state;           // 0  ENC_STATE_*
    uint8_t current;         // 1  encounter the hero faces next (0..11), 12 = the boss
    uint8_t plant;           // 2  plant of `current`
    uint8_t tier;            // 3  tier of `current`
    uint8_t woken;           // 4  encounters woken so far
    uint8_t cleared;         // 5  encounters cleared so far
    uint8_t dones;           // 6  Dones and Reliquias taken
    uint8_t deaths;          // 7  hero deaths
    uint16_t wake_frames;    // 8  frames since the last woken encounter woke
    uint16_t relicarios;     // 10 relicarios broken
    uint16_t clear_frames[ENC_COUNT];   // 12 frames from waking to clearing, per encounter
    uint8_t hits[ENC_COUNT];            // 36 hits taken, per encounter
    uint8_t plants[ENC_COUNT];          // 48 plant chosen for each encounter
    uint8_t corridor_enemies;           // 60 id of the room loaded now (0..11); a scenario reads it as the room
    uint8_t alive;                      // 61 enemies alive now
    uint8_t boss_alive;                 // 62 1 while the Abanderado lives
    uint8_t pad;                        // 63
    // Measurements of the bot runs (ENC_BOT), appended so the offsets above stay put.
    uint8_t hp_end[ENC_COUNT];          // 64 hero hearts when each encounter was cleared
    uint8_t tiers[ENC_COUNT];           // 76 tier of each encounter (0 ligera, 1 media, 2 dura)
    uint32_t act_frames;                // 88 frames played (stops at victory / death)
    uint32_t clock;                     // 92 frames since boot, never stops
    uint8_t result;                     // 96 0 playing, 1 victory, 2 death, 3 30000-frame timeout
    uint8_t death_enc;                  // 97 encounter the hero died in (0..11), 12 = the boss
    uint8_t cap_seq;                    // 98 capture trigger counter for the scenarios (saturates at 255)
    uint8_t hp;                         // 99 hero hearts now
    uint8_t max_hp;                     // 100 hero max hearts now
    uint8_t bot_rule;                   // 101 rule the bot is following (1 ojo, 2 cireneo, 3 retreat, 4 shoot, 5 advance, 6 stuck)
    uint16_t stuck_events;              // 102 times the bot's stuck rule fired
    uint16_t shots;                     // 104 shots fired by the bot
    uint16_t hits_total;                // 106 hits taken in all
    uint8_t dones_at[ENC_COUNT];        // 108 Dones taken when each encounter was cleared
    uint16_t boss_frames;               // 120 frames from waking the boss to killing it
    uint16_t relic_mask;                // 122 bit k = the relicario of corridor k is broken
    uint16_t relic_seen_frames;         // 124 frames the bot had a relicario to deal with
    uint16_t relic_shootable_frames;    // 126 ... and could shoot it
    uint16_t relic_norange_frames;      // 128 ... could not: too far
    uint16_t relic_nolos_frames;        // 130 ... could not: in range but no clear line
    uint8_t hp_min;                     // 132 fewest hearts the hero had during the act
    uint8_t dbg_awake;                  // 133 enemies the bot counts as awake
    uint8_t dbg_awake_state;                 // 134 state and type of the first one
    uint8_t dbg_awake_type;             // 135
    int16_t dbg_relic_x, dbg_relic_y;   // 136 relicario the bot sees (0 when none), ground px
    int16_t dbg_hero_x, dbg_hero_y;     // 140 hero ground point as the bot sees it
    // Boss diagnostics (iteration 3).
    uint16_t boss_hp[16];               // 144 boss hearts every 300 frames since it woke (index = 300-frame step)
    uint16_t boss_hits;                 // 176 beam hits on the Abanderado
    uint16_t mona_hits;                 // 178 beam hits on Monaguillos
    uint16_t boss_shots;                // 180 shots the bot fired while the boss was alive
    uint8_t mona_alive;                 // 182 Monaguillos alive now
    uint8_t mona_alive_max;             // 183 most Monaguillos alive at once
    uint16_t boss_hp_now;               // 184 boss hearts now (0 before it spawns)
    uint16_t mona_kills;                // 186 Monaguillos killed by the beam
    uint8_t blocked_asleep;             // 188 sleeping enemies standing where a body cannot (inside a piece or obstacle)
    uint8_t boss_state;                 // 189 BOSS_* of boss.h (0 inactive, 1 intro, 2 combat, 3 phase change, 4 victory, 5 rest)
    uint8_t boss_phase;                 // 190 phase the boss is in (1..3)
    uint8_t pad4;                       // 191
} EncStats;
_Static_assert(sizeof(EncStats) == 192, "EncStats layout is read by scenarios by offset");
_Static_assert(offsetof(EncStats, wake_frames) == 8 && offsetof(EncStats, relicarios) == 10 &&
               offsetof(EncStats, clear_frames) == 12 && offsetof(EncStats, hits) == 36 &&
               offsetof(EncStats, plants) == 48 && offsetof(EncStats, alive) == 61 &&
               offsetof(EncStats, hp_end) == 64 && offsetof(EncStats, act_frames) == 88 &&
               offsetof(EncStats, result) == 96 && offsetof(EncStats, hits_total) == 106 &&
               offsetof(EncStats, dones_at) == 108 && offsetof(EncStats, boss_frames) == 120 && offsetof(EncStats, relic_mask) == 122 && offsetof(EncStats, relic_shootable_frames) == 126,
               "EncStats layout is read by scenarios by offset");
extern volatile EncStats g_enc_stats;

// Random card for an offer (auto_pick 2): hashed from g_enc_debug.seed and the number of picks so far.
int enc_pick_index(void);

#if ENC_BOT
// Autopilot: plays the act as a careful player so the difficulty can be
// measured without a human. main.c hands it the hero and the camera each frame and replaces what the
// buttons and the stylus say.
typedef struct {
    int hx, hy;                 // hero ground point, world px
    int cam_x, cam_y;           // camera, world px
    int muzzle_x, muzzle_y, muzzle_h;   // muzzle of the hero this frame (world px, px above the ground)
    int shake_x, shake_y;
} EncBotView;
typedef struct { uint32_t keys; int touch_down, touch_x, touch_y; } EncBotInput;
void enc_bot_step(const EncBotView *v, Enemy *enemies, int max_enemies, EncBotInput *out);
#endif

#endif // ENCOUNTERS_PROTO
#endif // ENCOUNTERS_ACT1_H
