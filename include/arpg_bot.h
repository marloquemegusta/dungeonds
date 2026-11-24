#ifndef ARPG_BOT_H
#define ARPG_BOT_H

#include <stdint.h>
#include <stddef.h>
#include "game.h"
#include "gameplay.h"

// Autopilot of the variant "arpg-bot": plays the ARPG cathedral like a human of configurable skill so the difficulty
// and the balance can be measured without one. Test code: it only exists in that variant, never in the shipping ROM.
// Combat and progression in bajadas: it follows a scripted route through the side rooms (chests, the key of the Capilla del parroco)
// and the Naves 1 -> 4 -> Cripta (s_script in arpg_bot.c); the bot only decides the combat; it goes back to the camp when hurt, sleeps (levels only on sleep) and comes back by the last altar. No inventory.

#if ARPG_BOT && ENCOUNTERS_PROTO

// Knobs the scenario writes (symbol g_arpg_bot_debug). `profile` fills the human knobs; profile 3 keeps them as poked.
// The bot idles until `go` is 1: the scenario first writes the balance overrides (g_bal), the level and the mode, then `go`.
typedef struct {
    uint8_t profile;         // 0  0 normal, 1 torpe (clumsy), 2 bueno (good), 3 manual
    uint8_t applied;         // 1  internal: profile already copied into the knobs (0xFF = none yet)
    uint8_t reaction;        // 2  frames of delay before it reacts to what the enemies do
    uint8_t aim_err;         // 3  aiming error of the ray, px (+-)
    uint8_t miss_pct;        // 4  % of telegraphs (Cireneo lunge, Ojo gaze) it does not see
    uint8_t remate_miss_pct; // 5  % of reeling enemies it does not notice for the first 2 s
    uint8_t panic_pct;       // 6  below this % of life it backs off from melee enemies
    uint8_t punch_jitter;    // 7  frames of random extra pause between punches
    uint16_t seed;           // 8  seed of the bot's dice
    uint16_t timeout_frames; // 10 single modes: frames after which the run ends as a timeout (0 = 36000)
    uint8_t god;             // 12 1 = the hero ignores damage (measure a room without dying)
    uint8_t goal_room;       // 13 room id that ends the run when entered (0 = the boss killed)
    uint8_t ojo_delay;       // 14 frames an Ojo must have been looking before the bot reacts
    uint8_t pad;             // 15
    uint8_t go;              // 16 0 = idle; 1 = start (stats cleared, level set, the run restarted)
    uint8_t mode;            // 17 0 single bajada, never retreats (death ends it); 1 campaign (bajadas, camp, sleep); 2 single bajada that ends when it retreats
    uint8_t start_level;     // 18 hero level at the start (0 = 1); life and mana follow the g_bal formulas
    uint8_t fast;            // 19 1 = skips the rendering (faster emulation; no useful captures)
    uint8_t retreat_pct;     // 20 below this % of life (and no heal orb near) it goes back to the camp (campaign, mode 2)
    uint8_t kite_dist;       // 21 ground px it keeps from a group of melee enemies (0 = it trades blows)
    uint8_t mana_reserve;    // 22 mana it keeps unspent for the Ojo and the Cireneo (0 = shoots whatever is worth it)
    uint8_t max_bajadas;     // 23 campaign: stops after this many bajadas (0 = 60; the stats keep the first 16)
    uint32_t campaign_frames;// 24 campaign: frames after which it stops (0 = 324000, 90 game minutes)
    uint32_t pad2;           // 28
} ArpgBotDebug;
_Static_assert(sizeof(ArpgBotDebug) == 32 && offsetof(ArpgBotDebug, seed) == 8 && offsetof(ArpgBotDebug, timeout_frames) == 10 &&
               offsetof(ArpgBotDebug, god) == 12 && offsetof(ArpgBotDebug, goal_room) == 13 && offsetof(ArpgBotDebug, go) == 16 &&
               offsetof(ArpgBotDebug, retreat_pct) == 20 && offsetof(ArpgBotDebug, campaign_frames) == 24,
               "ArpgBotDebug layout is written by scenarios by offset");
extern volatile ArpgBotDebug g_arpg_bot_debug;

// Measurements (symbol g_arpg_bot_stats), read by the scenarios by offset.
#define ARPG_BOT_ROOMS 16
#define ARPG_BOT_BAJADAS 16
typedef struct {
    uint8_t result;          // 0   0 running, 1 boss killed (or goal room), 2 dead (single modes), 3 timeout, 4 bajadas cap, 5 retreated (mode 2)
    uint8_t room;            // 1
    uint8_t rooms_cleared;   // 2
    uint8_t hp;              // 3
    uint8_t hp_min;          // 4
    uint8_t max_hp;          // 5
    uint8_t mana;            // 6
    uint8_t level;           // 7
    uint32_t frames;         // 8   frames since go (camp included)
    uint16_t xp;             // 12
    uint8_t death_room;      // 14  room of the last death (0xFF none)
    uint8_t killer;          // 15  enemy type of the last blow
    uint16_t mana_empty_frames; // 16
    uint16_t shots;          // 18
    uint16_t punches;        // 20
    uint16_t remates_done;   // 22
    uint16_t remates_missed; // 24
    uint16_t orbs;           // 26
    uint16_t stuck_events;   // 28
    uint16_t kills;          // 30
    uint8_t rule;            // 32  1 ojo, 2 cireneo, 3 retreat, 4 shoot, 5 advance, 6 stuck, 7 melee, 8 remate, 9 orb, 10 give up, 11 kite, 12 altar, 13 camp walk, 14 pause menu
    uint8_t awake;           // 33  enemies the bot counts as threats
    int16_t hero_x, hero_y;  // 34, 36 hero ground point as the bot sees it
    int16_t goal_x, goal_y;  // 38, 40 where it is heading (0 when nowhere)
    uint16_t give_ups;       // 42  times it dropped the hunt and went for the door
    uint16_t damage_total;   // 44  life lost in all
    uint16_t hits;           // 46  hits taken
    uint16_t room_frames[ARPG_BOT_ROOMS];   // 48  frames spent in each room (saturates at 65535; room_frames32 does not)
    uint16_t room_damage[ARPG_BOT_ROOMS];   // 80  life lost in each room
    uint8_t room_hp_exit[ARPG_BOT_ROOMS];   // 112 life when leaving each room (0 = not left)
    uint8_t room_kills[ARPG_BOT_ROOMS];     // 128 kills in each room
    uint16_t visited;        // 144 bit r = room r entered
    uint16_t dmg_type[9];    // 146 life lost per EnemyType (index = EnemyType)
    uint8_t max_alive;       // 164 most live enemies at once in the room (performance: the DS must keep 60 FPS; cap 24)
    uint8_t max_awake;       // 165 most awake threats at once
    uint8_t near_type;       // 166 type of the threat the bot is hunting (debug)
    uint8_t near_state;      // 167 its AI state
    // ---- campaign ----
    uint8_t bajadas;         // 168 bajadas started
    uint8_t boss_result;     // 169 0 not reached, 1 boss killed, 2 the hero died fighting it
    uint8_t max_level;       // 170 highest hero level reached
    uint8_t phase;           // 171 internal phase of the state machine
    uint32_t dungeon_frames; // 172 frames inside the cathedral
    uint32_t camp_frames;    // 176 frames in the camp
    uint32_t mana_spent;     // 180
    uint32_t screens;        // 184 screens crossed in all (a screen = 192 px of room; counted again on every bajada)
    uint32_t b_frames[ARPG_BOT_BAJADAS];    // 188 frames of each bajada (inside the cathedral)
    uint32_t room_frames32[ARPG_BOT_ROOMS]; // 252 frames in each room, all bajadas
    uint16_t b_damage[ARPG_BOT_BAJADAS];    // 316 life lost in each bajada
    uint8_t b_deep[ARPG_BOT_BAJADAS];       // 348 deepest room of each bajada: 1..4 Nave 1..4, 5 Cripta
    uint8_t b_level[ARPG_BOT_BAJADAS];      // 364 hero level at the start of each bajada
    uint8_t b_cause[ARPG_BOT_BAJADAS];      // 380 how each ended: 1 died, 2 retreated, 3 boss killed, 4 timeout
    uint8_t b_screens[ARPG_BOT_BAJADAS];    // 396 screens crossed in each bajada
    uint8_t room_screens[ARPG_BOT_ROOMS];   // 412 screens crossed in each room, all bajadas
    uint16_t level_minute[8];               // 428 game second (since go) in which the hero reached level 2..9 (0 = not yet)
    uint32_t pad3;                          // 444
    uint32_t first_visit_frames;            // 448 dungeon frames in a room that has not been cleared yet in this save
    uint32_t repeat_frames;                 // 452 dungeon frames in rooms already cleared before in this save
    uint16_t rooms_seen;                    // 456 bit r = room r ever entered
    uint16_t script_skips;                  // 458 route steps it could not do (door that does not match, chapel without the key)
} ArpgBotStats;
_Static_assert(sizeof(ArpgBotStats) == 460 && offsetof(ArpgBotStats, first_visit_frames) == 448 &&
               offsetof(ArpgBotStats, repeat_frames) == 452 && offsetof(ArpgBotStats, rooms_seen) == 456 && offsetof(ArpgBotStats, frames) == 8 && offsetof(ArpgBotStats, rule) == 32 &&
               offsetof(ArpgBotStats, room_frames) == 48 && offsetof(ArpgBotStats, room_damage) == 80 &&
               offsetof(ArpgBotStats, room_hp_exit) == 112 && offsetof(ArpgBotStats, room_kills) == 128 &&
               offsetof(ArpgBotStats, visited) == 144 && offsetof(ArpgBotStats, dmg_type) == 146 &&
               offsetof(ArpgBotStats, give_ups) == 42 && offsetof(ArpgBotStats, bajadas) == 168 &&
               offsetof(ArpgBotStats, dungeon_frames) == 172 && offsetof(ArpgBotStats, screens) == 184 &&
               offsetof(ArpgBotStats, b_frames) == 188 && offsetof(ArpgBotStats, room_frames32) == 252 &&
               offsetof(ArpgBotStats, b_damage) == 316 && offsetof(ArpgBotStats, b_deep) == 348 &&
               offsetof(ArpgBotStats, b_level) == 364 && offsetof(ArpgBotStats, b_cause) == 380 &&
               offsetof(ArpgBotStats, b_screens) == 396 && offsetof(ArpgBotStats, room_screens) == 412 &&
               offsetof(ArpgBotStats, level_minute) == 428,
               "ArpgBotStats layout is read by scenarios by offset");
extern volatile ArpgBotStats g_arpg_bot_stats;

typedef struct {
    int hx, hy;                 // hero ground point, world px
    int cam_x, cam_y;           // camera, world px
    int muzzle_x, muzzle_y, muzzle_h;   // muzzle of the hero this frame (world px, px above the ground)
    int shake_x, shake_y;
} ArpgBotView;
typedef struct { uint32_t keys; int touch_down, touch_x, touch_y; } ArpgBotInput;

// Once per frame from the main loop: replaces what the buttons and the stylus say.
void arpg_bot_step(const ArpgBotView *v, Enemy *enemies, int max_enemies, ArpgBotInput *out);

#endif // ARPG_BOT && ENCOUNTERS_PROTO
#endif // ARPG_BOT_H
