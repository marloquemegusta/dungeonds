#include "campanero_boss_text.h"
#include "encounters_act1.h"
#include "lab_tuning.h"
#include "sound_test.h"

// Translation unit never empty (ISO C) when ENCOUNTERS_PROTO=0.
typedef int encounters_act1_translation_unit_not_empty;

#if ENCOUNTERS_PROTO

#include <string.h>
#include "encounters.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "boss.h"
#include "chars_pool.h"
#include "room_kit.h"
#include "arpg_inv.h"

// Life in points (ARPG) can exceed a byte; the stats keep it clamped to 255.
#define HP_U8(v) ((uint8_t)((v) > 255 ? 255 : (v)))
#include "hwshadow.h"
#include "sfx.h"
#include "sfx_voice_len.h"
#include "collision.h"
#include "enemy_ai.h"
#include "groundfx.h"
#include "navfield.h"
#include "strip.h"
#include "strip_kit.h"
#include "upgrades.h"
#include "player_sprite.h"
#include "pickups.h"
#include "enc_relic_gfx.h"
#include "enc_room_gfx.h"
#include "room_light.h"

#include "encounters_act1_tables.h"
#include "encounters_act1_hp.h"

#if ENC_BOT
volatile EncDebug g_enc_debug = { .auto_pick = 2, .seed = 1,
                                  .bot_reaction = 15, .bot_aim_err = 6, .bot_ojo_delay = 20 };   // human-like bot, cards at random, seed 1
#elif ENC_START_BOSS || ENC_START_CAMPANERO
volatile EncDebug g_enc_debug = { .start_boss = 1 };   // console test build: every act (and every retry) starts at the boss
#else
volatile EncDebug g_enc_debug;
#endif
volatile EncStats g_enc_stats;
volatile EncTierDebug g_tier_debug;
volatile uint8_t g_relic_drop_debug;

// ---------------------------------------------------------------------------
// Act plan: which plant, tier and mirror each encounter has. Pure function of the seed.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Zone map (DESIGN.md 11, variant D "cuatro naves cortas"): 12 rooms of 1..3 blocks. Only the room the hero is in exists in
// the strip. Its blocks are "stages" k = 0.. counted from its foot (the hero enters from below); everything above the last
// block is black and solid. A room is always the same (seed = hash of its id).
// ---------------------------------------------------------------------------
#define ENC_STAGES 3                        // blocks of the biggest room
#include "encounters_act1_salas.h"
#define ENC_FIRST_BLOCK 3                   // strip block of block 0 of every room; the blocks below it are the entrance floor

enum { DOOR_LEFT = 0, DOOR_RIGHT, DOOR_UP };
typedef struct { uint8_t side, screen, dest; } RoomDoor;   // screen: lateral doors only, screen counted from the bottom (p1 = lowest)
enum { RT_NORMAL = 0,      // one group per block, taken from the list of groups of its nave
       RT_PARROQUIA,       // Capilla del parroco: always the Parroquia group
       RT_MISA,            // Galeria de la Misa: the fixed group of "la Misa" in special_block, nothing else
       RT_MONJARANA,       // Galeria de la monjarana: the fixed group of the Super Monja and her court in special_block
       RT_CRIPTA };        // boss Abanderado in special_block
typedef struct {
    const char *name;           // shown in the HUD
    uint8_t blocks;             // 1..3 blocks (2 screens each)
    uint8_t level;              // fixed level: life of its enemies, xp and loot level of the kills
    uint8_t nave;               // 1..4: filters the groups and sets the tier of its Ojos and Cireneos
    uint8_t type;               // RT_*
    uint8_t special_block;      // RT_MISA / RT_MONJARANA / RT_CRIPTA: block of the special group or boss
    uint8_t n_doors;
    RoomDoor doors[3];
    uint8_t altar;              // altar at the foot of the room (touching it sets where the next run enters)
    uint8_t chest;              // chest at the far end of the room
    // Fields for the next batch (no logic reads them yet):
    uint8_t prize_min_rar;      // guaranteed minimum rarity of the chest / miniboss prize (ARPG_RAR_*; 0 = the normal roll)
    uint8_t key_door;           // 1 + index in `doors` of the door that needs the key (0 = none)
    uint8_t drops_key;          // 1 = the group of this room drops the key
    uint8_t chapel_gate;        // 1 = the chapel is closed by a reja until the key is taken
} RoomDef;

#define DL(p, d) { DOOR_LEFT, (p), (d) }
#define DR(p, d) { DOOR_RIGHT, (p), (d) }
#define DU(d) { DOOR_UP, 0, (d) }
// pN = screen N counted from the bottom of the room; block = (N-1)/2, the lower screen of the block when N is odd.
// Ids: 0..3 Naves, 4 Galeria del cofre, 5 del secreto, 6 Claustro bajo, 7 Claustro alto, 8 Enfermeria, 9 Osario,
// 10 Capilla del parroco, 11 Galeria de la Misa, 12 Galeria del prisionero, 13 Capilla con llave, 14 Galeria de la monjarana, 15 Cripta.
// Doors come in pairs (the arrival looks for the door that leads back). Doors that leave upwards have no pair below.
static const RoomDef s_rooms[ENC_ROOM_COUNT] = {
    { .name = "Nave 1", .blocks = 3, .level = 1, .nave = 1, .type = RT_NORMAL, .altar = 1,
      .n_doors = 3, .doors = { DL(2, 4), DR(4, 6), DU(1) } },
    { .name = "Nave 2", .blocks = 3, .level = 2, .nave = 2, .type = RT_NORMAL, .altar = 1,
      .n_doors = 3, .doors = { DL(4, 8), DR(4, 7), DU(2) } },
    { .name = "Nave 3", .blocks = 3, .level = 3, .nave = 3, .type = RT_NORMAL, .altar = 1,
      .n_doors = 3, .doors = { DL(4, 9), DR(4, 12), DU(3) } },
    { .name = "Nave 4", .blocks = 3, .level = 4, .nave = 4, .type = RT_NORMAL, .altar = 1, .key_door = 1,
      .n_doors = 3, .doors = { DR(2, 13), DR(4, 14), DU(15) } },
    { .name = "Galería del cofre", .blocks = 1, .level = 1, .nave = 1, .type = RT_NORMAL, .chest = 1,
      .n_doors = 1, .doors = { DR(1, 0) } },
    { .name = "Galería del secreto", .blocks = 1, .level = 1, .nave = 1, .type = RT_NORMAL, .chest = 1,
      .n_doors = 1, .doors = { DL(1, 6) } },
    { .name = "Claustro bajo", .blocks = 3, .level = 1, .nave = 1, .type = RT_NORMAL,
      .n_doors = 3, .doors = { DL(1, 0), DR(4, 5), DU(7) } },
    { .name = "Claustro alto", .blocks = 3, .level = 2, .nave = 2, .type = RT_NORMAL, .chest = 1,
      .n_doors = 1, .doors = { DL(2, 1) } },
    { .name = "Enfermería", .blocks = 3, .level = 2, .nave = 2, .type = RT_NORMAL,
      .n_doors = 3, .doors = { DR(1, 1), DL(5, 10), DU(9) } },
    { .name = "Osario", .blocks = 3, .level = 3, .nave = 3, .type = RT_NORMAL, .chest = 1,
      .n_doors = 2, .doors = { DR(1, 2), DL(4, 11) } },
    { .name = "Capilla del párroco", .blocks = 1, .level = 3, .nave = 3, .type = RT_PARROQUIA, .chest = 1,
      .prize_min_rar = ARPG_RAR_RARE, .drops_key = 1,
      .n_doors = 1, .doors = { DR(1, 8) } },
    { .name = "Galería de la Misa", .blocks = 2, .level = 3, .nave = 3, .type = RT_MISA, .special_block = 1,
      .prize_min_rar = ARPG_RAR_EPIC,
      .n_doors = 1, .doors = { DR(1, 9) } },
    { .name = "Galería del prisionero", .blocks = 2, .level = 3, .nave = 3, .type = RT_NORMAL, .chest = 1,
      .n_doors = 1, .doors = { DL(1, 2) } },
    { .name = "Capilla con llave", .blocks = 1, .level = 4, .nave = 4, .type = RT_NORMAL, .chest = 1,
      .prize_min_rar = ARPG_RAR_LEGENDARY, .chapel_gate = 1,
      .n_doors = 1, .doors = { DL(1, 3) } },
    { .name = "Galería de la monjaraña", .blocks = 2, .level = 4, .nave = 4, .type = RT_MONJARANA, .special_block = 1,
      .prize_min_rar = ARPG_RAR_EPIC,
      .n_doors = 1, .doors = { DL(1, 3) } },
    { .name = "Cripta", .blocks = 1, .level = 5, .nave = 4, .type = RT_CRIPTA, .special_block = 0,
      .prize_min_rar = ARPG_RAR_LEGENDARY, .n_doors = 0 },
};

#if ENC_START_CAMPANERO
static int s_room = ENC_ROOM_CRIPTA;          // test variant: the first strip is the boss room, no camp in between
#else
static int s_room;                            // room loaded now (enc_room_select before strip_start)
#endif
static int s_from_room = -1;                  // room the hero came from (where he lands), -1 = from the camp
static const RoomDef *room_def(void) { return &s_rooms[s_room]; }
static int is_boss_stage(int k) {             // block k holds the boss machinery (Cripta)
    const RoomDef *r = room_def();
    return r->type == RT_CRIPTA && k == r->special_block;
}
// block k holds the fixed group of a special encounter of two blocks (la Misa, la monjarana)
static int is_special_stage(int k) { const RoomDef *r = room_def(); return (r->type == RT_MISA || r->type == RT_MONJARANA) && k == r->special_block; }
static int boss_number(int k) { (void)k; return 0; }   // life: ARPG_BOSS_HP_PCT(n); the Abanderado of the Cripta is the only one
static int tier_of_stage(int k) { (void)k; const int l = room_def()->level; return l <= 2 ? 0 : l <= 4 ? 1 : 2; }
static int boss_mona_cap(int n) { return n == 0 ? 8 : 12; }   // live Monaguillos of each boss

static int s_first_block = ENC_FIRST_BLOCK;
static int s_active_boss_k;                   // block of the boss fight of this room
static uint32_t s_seed;
static uint8_t s_plant[ENC_STAGES];           // plant (props) of each block
static uint8_t s_mirror[ENC_STAGES];
// Placement of the poster (tools/encuentros/gen_salas_rom.py): when a block has one, it replaces the hashed plant and group.
static const RoomLayout *layout_of(int k) {
    if (s_room < 0 || s_room >= ENC_ROOM_COUNT || k < 0 || k >= ENC_STAGES) return 0;
    if (g_enc_debug.force_group) return 0;               // debug: a forced group of the generic table replaces the poster's
    return s_room_layouts[s_room][k].valid ? &s_room_layouts[s_room][k].l : 0;
}
static uint8_t s_tier[ENC_STAGES];            // plant tier of each block (stats only)

// Persistence (g_arpg): what died stays dead until the hero sleeps. A boss or miniboss uses the boss bit of the room, a group
// the bit of its block.
static int block_is_dead(int k) {
    if (is_boss_stage(k) || is_special_stage(k)) return (g_arpg.boss_dead >> s_room) & 1;
    return (g_arpg.dead_groups[s_room] >> k) & 1;
}
static void block_mark_dead(int k) {
    if (is_boss_stage(k) || is_special_stage(k)) {
        g_arpg.boss_dead |= (uint16_t)(1u << s_room);
        g_arpg.boss_ever |= (uint16_t)(1u << s_room);
    } else {
        g_arpg.dead_groups[s_room] |= (uint8_t)(1u << k);
    }
}

static int s_end_demo_pending;                // the Cripta boss fell for the first time: the end-of-demo card is due after its victory

static void prize_relic(const RoomDef *room, int level_bonus, int min_rar, int px, int py) {
    uint32_t rng = (uint32_t)(s_room + 1) * 2246822519u ^ (uint32_t)(px * 73856093 ^ py * 19349663) ^ ((uint32_t)room->level * 3266489917u);
    ArpgInvItem it;
    arpg_relic_roll(&it, room->level + level_bonus, min_rar, &rng);
    if (min_rar == ARPG_RAR_LEGENDARY) {                // the boss reward goes straight to the bag/stash: the hero leaves for the camp at once
        if (arpg_inv_add(&it) >= 0 || arpg_inv_stash_add(&it) >= 0) {
            pickups_toast("Reliquia legendaria", 180);
            arpg_progress_save();
            return;
        }
    }
    pickups_spawn_relic(TO_FIXED(px), TO_FIXED(py - 24), &it);
}

// Guaranteed rewards when a group, a miniboss or the boss of the room falls (DESIGN-ARPG.md 7). The relic drops a little above the hero.
static void clear_rewards(const RoomDef *room, int k, int first_time, int px, int py) {
    if (room->type == RT_PARROQUIA || is_special_stage(k)) arpg_add_xp(ARPG_XP_SPECIAL);   // a special encounter fell whole
    if (is_special_stage(k)) {
        prize_relic(room, 1, ARPG_RAR_EPIC, px, py);                // la Misa and la monjarana: epic
    } else if (room->type == RT_CRIPTA && is_boss_stage(k)) {
        if (first_time) {                                           // later visits give loot and xp only
            prize_relic(room, 1, ARPG_RAR_LEGENDARY, px, py);
            s_end_demo_pending = 1;
        }
    }
    if (room->drops_key && !g_arpg.key_have) {                      // the group of the Capilla del parroco drops the key
        g_arpg.key_have = 1;
        arpg_progress_save();
        sfx_play(SND_PICKUP_ORB, -1);
        pickups_toast("Llave de la capilla", 180);
    }
}

typedef struct {
    uint8_t spawned, awake, cleared, wave2_done, barrier_open, back_closed, verja_opening, verja_lift, back_lift;
    // Rooms (salas ARPG). Offsets 9 and 10 are read by scenarios/salas_captura.json (sizeof is 11).
    uint8_t chest_open, altar_touched;
} EncRuntime;
static EncRuntime s_rt[ENC_STAGES];
// Members of each block placed so far (bit = ordinal in the group): a member is placed when the hero comes close to its post,
// so a room of 35 never needs more than the 24 slots. s_member_full is the mask of the whole group, s_member_seen the ones already
// counted in EncStats.members_placed, s_slot_member the ordinal of the member living in each pool slot (0xFF: not a placed member).
static uint16_t s_member_mask[ENC_STAGES], s_member_full[ENC_STAGES], s_member_seen[ENC_STAGES];
static uint8_t s_slot_member[64];
static int s_exit_room = -1;                  // crossing requested by enc_update(), consumed by main.c
static int s_victory;                         // never set: the dungeon has no victory (enc_victory stays for the HUD)
// Reja de la llave (sala con chapel_gate): cruza la sala de pared a pared entre la entrada y el cofre.
#define ENC_GATE_LOCAL_Y 150        // block-local y of the base of the reja (the chest stands at 90, out of reach through the bars)
#define ENC_GATE_NEAR_PX 40         // with the key, the reja rises when the hero is this close to its line
static uint8_t s_gate_lift, s_gate_opening, s_gate_open;
static uint16_t s_gate_toast_cd;
static int s_boss_locked;                     // the bottom barrier of the boss room is closed (boss mode)
static int s_deaths;
static int s_was_dead;
static int s_fx_timer, s_fx_x, s_fx_y;        // ring on the floor (nothing sets it now: no relicarios)

static uint32_t hash32(uint32_t v) {
    v ^= v >> 16;
    v *= 0x7feb352du;
    v ^= v >> 15;
    v *= 0x846ca68bu;
    v ^= v >> 16;
    return v;
}

static uint32_t pick_hash(int slot, int salt) {
    return hash32(s_seed ^ ((uint32_t)slot * 0x9e3779b9u) ^ ((uint32_t)salt * 0x85ebca6bu) ^ 0x454e4331u);
}

static void boss_set_barriers(int closed);
static void boss_spawn_escort(EnemyType type, int floor_x);

// Sheet of the Abanderado (DESIGN.md 6.13.7). Floors 5 and 10 share the escort of the prototype: 2 Ojos and 1 Cireneo
// per phase, one that falls comes back from the top ~4 s later.
static const BossEscortDef s_abanderado_escort[] = {
    { ENEMY_TYPE_SHOOTER, 2, 240, { 40, 168 } },
    { ENEMY_TYPE_CHARGER, 1, 240, { 104, 104 } },
};
static const BossDef s_abanderado_def = {
    .enemy_type = ENEMY_TYPE_ABANDERADO,
    .name = "EL ABANDERADO",
    .title = "Capitán Íñigo Albar",
    .line_intro = "«Mientras el asta siga en pie,\nnadie se retira.»",
    .line_defeat = "«El asta ha caído.»",
    .sfx_intro = SND_ABANDERADO_INTRO,
    .sfx_defeat = SND_ABANDERADO_DEFEAT,
    .voice_intro_frames = SFX_VOICE_VBLANKS_ABANDERADO_INTRO,
    .voice_defeat_frames = SFX_VOICE_VBLANKS_ABANDERADO_DEFEAT,
    .n_phases = 3,
    .phase_pct = { 100, 66, 33 },
    .n_escort = { 2, 2, 2 },
    .escort = { s_abanderado_escort, s_abanderado_escort, s_abanderado_escort },
};
// Sheet of the Campanero de Animas (DESIGN-ARPG.md 9). Posts in floor coordinates of the boss block (see s_campanero_pieces).
#define CAMP_BOSS_X 104                      // the bell hangs centre-up, in the open
#define CAMP_BOSS_Y 70
#define CAMP_OJO_X 20                        // fixed post of the Ojo, on the left side; he respawns here
#define CAMP_OJO_Y 250
#define CAMP_MONJA_X 74                      // she prays near the boss, in the open (inside ARPG_MONJA_PRAY_RADIUS of him)
#define CAMP_MONJA_Y 82
#if ENC_START_CAMPANERO
static const BossEscortDef s_campanero_escort_1[] = {
    { ENEMY_TYPE_SHOOTER, 1, 720, { CAMP_OJO_X, CAMP_OJO_X } },
    { ENEMY_TYPE_MONJA, 1, 1200, { CAMP_MONJA_X, CAMP_MONJA_X } },
};
static const BossEscortDef s_campanero_escort_2[] = {
    { ENEMY_TYPE_SHOOTER, 1, 720, { CAMP_OJO_X, CAMP_OJO_X } },
    { ENEMY_TYPE_MONJA, 1, 1200, { CAMP_MONJA_X, CAMP_MONJA_X } },
    { ENEMY_TYPE_CHARGER, 1, 900, { 104, 104 } },
};
static const BossDef s_campanero_def = {
    .enemy_type = ENEMY_TYPE_CAMPANERO,
    .name = CAMPANERO_BOSS_NAME,
    .title = CAMPANERO_BOSS_TITLE,
    .line_intro = CAMPANERO_BOSS_LINE_INTRO,
    .line_defeat = CAMPANERO_BOSS_LINE_DEFEAT,
    .sfx_intro = CAMPANERO_BOSS_SFX_INTRO,
    .sfx_defeat = CAMPANERO_BOSS_SFX_DEFEAT,
    .voice_intro_frames = CAMPANERO_BOSS_VOICE_INTRO_FRAMES,
    .voice_defeat_frames = CAMPANERO_BOSS_VOICE_DEFEAT_FRAMES,
    .n_phases = 3,
    .phase_pct = { 100, 66, 33 },
    .n_escort = { 2, 3, 3 },
    .escort = { s_campanero_escort_1, s_campanero_escort_2, s_campanero_escort_2 },
};
#endif
// Test room (variant arpg-campanero): the Cripta block gets 5 columns in staggered rows and 2 statues at the sides.
// Nominal top-left of each piece in block px (the compositor snaps them to the nearest legal phase of the kit).
static const EncPieceDef s_campanero_pieces[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 32, 140 },
    { STRIP_PIECE_COLUMNA_ENTERA, 144, 140 },
    { STRIP_PIECE_COLUMNA_ENTERA, 88, 208 },
    { STRIP_PIECE_COLUMNA_ENTERA, 32, 276 },
    { STRIP_PIECE_COLUMNA_ENTERA, 144, 276 },
    { STRIP_PIECE_SANTO, 0, 196 },
    { STRIP_PIECE_SANTO_DER, 160, 196 },
};
#if ARPG_OJO_TEST
// Test room (variant arpg-ojo): every block of every room holds the same columns, near the foot of the block where the hero
// lands, so one is always at hand to hide from the Ojo of ojo_test.c. Nominal top-left in block px (snapped to the kit phases).
static const EncPieceDef s_ojo_test_pieces[] = {
    { STRIP_PIECE_COLUMNA_ENTERA, 120, 184 },
    { STRIP_PIECE_COLUMNA_ENTERA, 24, 120 },
    { STRIP_PIECE_COLUMNA_ENTERA, 136, 72 },
};
#endif
#if ENC_START_CAMPANERO
static const EncEnemyDef s_campanero_enemies[] = {
    { ENC_E_CAMPANERO, ENC_S_AWAKE, CAMP_BOSS_X, CAMP_BOSS_Y },
    { ENC_E_OJO, ENC_S_AWAKE, CAMP_OJO_X, CAMP_OJO_Y },
    { ENC_E_MONJA, ENC_S_AWAKE, CAMP_MONJA_X, CAMP_MONJA_Y },
};
static const BossDef *boss_def_of(int n) { (void)n; (void)&s_abanderado_def; return &s_campanero_def; }   // the test room has only the Campanero
#else
static const BossDef *boss_def_of(int n) { (void)n; return &s_abanderado_def; }
#endif

static void room_art_prepare_current(void);

void enc_init(uint32_t seed) {
    s_seed = seed ? seed : 1u;
    const RoomDef *room = room_def();
    // Lives of the zone (DESIGN.md 6.13.6): two beams for an Exvoto, three for the Ojo and the Cireneo.
    g_enemy_tuning[ENEMY_TYPE_EXVOTO].max_hp = ENC_HP_EXVOTO;
    g_enemy_tuning[ENEMY_TYPE_MONAGUILLO].max_hp = ENC_HP_MONAGUILLO;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].max_hp = ENC_HP_CIRENEO;
    g_enemy_tuning[ENEMY_TYPE_SHOOTER].max_hp = ENC_HP_OJO;
    g_enemy_tuning[ENEMY_TYPE_ABANDERADO].max_hp = g_enc_debug.boss_hp ? g_enc_debug.boss_hp : ENC_HP_ABANDERADO;
    g_enemy_tuning[ENEMY_TYPE_CAMPANERO].max_hp = g_enc_debug.boss_hp ? g_enc_debug.boss_hp : 3000;   // DESIGN-ARPG.md 9
    // The Cireneo of v2: it chases below the hero's pace so the player can break away and charge the beam,
    // telegraphs 0.75 s and then charges very fast.
    g_enemy_tuning[ENEMY_TYPE_CHARGER].speed = 105;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].telegraph_duration = 45;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].charge_speed = 1000;
    // Plants (props) of each block: a hashed sequence, never the same plant twice in a row (the boss block does not count).
    int prev_plant = -1;
    for (int k = 0; k < ENC_STAGES; k++) {
        s_tier[k] = (uint8_t)tier_of_stage(k);
        s_mirror[k] = (uint8_t)(pick_hash(k, 99) & 1u);
#if ARPG_OJO_TEST
        s_mirror[k] = 0;             // arpg-ojo: the test columns always stand where ojo_test.c expects them
#endif
        if (layout_of(k)) s_mirror[k] = 0;     // the poster's placement is not mirrored
        s_plant[k] = 0;
        if (k >= room->blocks || is_boss_stage(k)) continue;
        const int range = ENC_PLANT_COUNT - (prev_plant >= 0 ? 1 : 0);
        int p = (int)(pick_hash(k, 7) % (uint32_t)range);
        if (prev_plant >= 0 && p >= prev_plant) p++;          // skips the plant of the block before
        s_plant[k] = (uint8_t)p;
        prev_plant = p;
    }
    if (g_enc_debug.force_plant > 0 && g_enc_debug.force_plant <= ENC_PLANT_COUNT) {   // debug: the first block on demand
        s_plant[0] = (uint8_t)(g_enc_debug.force_plant - 1);
        s_mirror[0] = 0;
        if (g_enc_debug.force_tier > 0 && g_enc_debug.force_tier <= 3) s_tier[0] = (uint8_t)(g_enc_debug.force_tier - 1);
    }
    memset(s_rt, 0, sizeof(s_rt));
    memset(s_member_mask, 0, sizeof(s_member_mask));
    memset(s_member_full, 0, sizeof(s_member_full));
    memset(s_member_seen, 0, sizeof(s_member_seen));
    memset(s_slot_member, 0xFF, sizeof(s_slot_member));
    g_enc_stats.members_placed = 0;
    // Rooms have no gates (salas ARPG): both lifts start raised, so no rastrillo is drawn anywhere.
    for (int i = 0; i < ENC_STAGES; i++) { s_rt[i].back_lift = ENC_VERJA_H; s_rt[i].verja_lift = ENC_VERJA_H; }
    s_exit_room = -1;
    s_gate_open = room->chapel_gate ? 0 : 1;               // generic: chapel_gate = reja con llave delante del premio
    s_gate_opening = 0;
    s_gate_lift = room->chapel_gate ? 0 : ENC_VERJA_H;
    s_gate_toast_cd = 0;
    s_first_block = ENC_FIRST_BLOCK;
    // What the hero already did here (g_arpg): the dead stay dead, the chest stays open, the altar stays lit.
    for (int k = 0; k < room->blocks; k++) {
        if (!block_is_dead(k)) continue;
        s_rt[k].spawned = s_rt[k].awake = s_rt[k].cleared = s_rt[k].wave2_done = s_rt[k].barrier_open = 1;
    }
    if (room->chest && ((g_arpg.chests_open >> s_room) & 1)) s_rt[room->blocks - 1].chest_open = 1;
    if (room->altar && ((g_arpg.altars_lo >> s_room) & 1)) s_rt[0].altar_touched = 1;
    g_enc_debug.start_dones = 0;       // a new room never inherits a "apply Dones now" debug request
    s_victory = 0;
    s_boss_locked = 0;
    s_active_boss_k = room->type == RT_CRIPTA ? room->special_block : 0;
    s_was_dead = 0;
    s_fx_timer = 0;
    {
        static const BossHooks hooks = { boss_spawn_escort, boss_set_barriers };
        boss_set_hooks(&hooks);
        boss_reset(boss_def_of(boss_number(0)), s_active_boss_k);
    }
    g_abanderado_max_mona = boss_mona_cap(boss_number(0));
    room_art_prepare_current();
    volatile EncStats *st = &g_enc_stats;
    uint8_t deaths = (uint8_t)s_deaths;
    memset((void *)st, 0, sizeof(EncStats));
    st->deaths = deaths;
    for (int i = 0; i < ENC_STAGES; i++) st->plants[i] = s_plant[i];
    st->plant = s_plant[0];
    st->tier = s_tier[0];
    for (int i = 0; i < ENC_STAGES; i++) st->tiers[i] = s_tier[i];
    st->corridor_enemies = (uint8_t)s_room;
    st->max_hp = HP_U8(g_player_state.max_hp);
    st->hp = HP_U8(g_player_state.hp);
}

static uint32_t s_pick_count;

int enc_pick_index(void) {
    return (int)(hash32(((uint32_t)g_enc_debug.seed << 8) ^ (s_pick_count++ * 0x9e3779b9u) ^ 0x50494b31u) % 3u);
}

// ---------------------------------------------------------------------------
// Block descriptions for the compositor (strip.c) and the painter.
// ---------------------------------------------------------------------------

void enc_block_info(int32_t block, EncBlock *out) {
    memset(out, 0, sizeof(*out));
    out->kind = ENC_BLOCK_CLEAR;
    int32_t k = s_first_block - block;          // block k of the room, counted from its foot
    if (k < 0 || k >= room_def()->blocks) return;   // the entrance floor, and the black above the last block
    out->idx = (uint8_t)k;
    if (is_boss_stage((int)k)) {
        out->kind = ENC_BLOCK_BOSS;
        return;
    }
    out->kind = ENC_BLOCK_ENCOUNTER;
    out->plant = s_plant[k];
    out->tier = s_tier[k];
    out->mirror = s_mirror[k];
}

static int door_block(const RoomDef *r, const RoomDoor *d);
static int door_hole_y(const RoomDoor *d);
int enc_block_pieces(int32_t block, EncPiecePlan *out, int max) {
    EncBlock b;
    enc_block_info(block, &b);
    const EncPieceDef *defs = 0;
    int n = 0;
    if (b.kind == ENC_BLOCK_ENCOUNTER) {
        defs = s_plants[b.plant].pieces;
        n = s_plants[b.plant].n_pieces;
        if (room_def()->chapel_gate) n = 0;           // the room of the reja has a clear floor (nothing between the gate and the entrance)
        const RoomLayout *lay = layout_of(b.idx);
        if (lay) { defs = lay->pieces; n = lay->n_pieces; }
#if ARPG_OJO_TEST
        defs = s_ojo_test_pieces;
        n = (int)(sizeof(s_ojo_test_pieces) / sizeof(s_ojo_test_pieces[0]));
#endif
    } else if (b.kind == ENC_BLOCK_CORRIDOR) {
        defs = s_corridor_pieces;
        n = (int)(sizeof(s_corridor_pieces) / sizeof(s_corridor_pieces[0]));
    }
#if ENC_START_CAMPANERO
    else if (b.kind == ENC_BLOCK_BOSS) {
        defs = s_campanero_pieces;
        n = (int)(sizeof(s_campanero_pieces) / sizeof(s_campanero_pieces[0]));
    }
#else
    else if (b.kind == ENC_BLOCK_BOSS) {        // the crypt of the poster: its props (the fight itself is the boss's)
        const RoomLayout *lay = layout_of(b.idx);
        if (lay) { defs = lay->pieces; n = lay->n_pieces; }
    }
#endif
    int m = 0;
    // The upper door is not a piece: it is the central arch of the back wall (source/strip.c, apply_room_openings).
    // The lateral openings put an occlusion piece in this block: the south module of the wall hides whoever is behind it.
    {
        const RoomDef *rd = room_def();
        const int k = s_first_block - (int)block;
        for (int i = 0; i < rd->n_doors && m < max; i++) {
            const RoomDoor *d = &rd->doors[i];
            if (d->side == DOOR_UP || door_block(rd, d) != k) continue;
            out[m].piece = d->side == DOOR_LEFT ? STRIP_PIECE_HUECO_IZQ : STRIP_PIECE_HUECO_DER;
            out[m].mirror = 0;
            out[m].lx = (int16_t)(d->side == DOOR_LEFT ? ENC_CAM_X - ENC_FLOOR_X : ENC_FLOOR_W);
            out[m].ly = (int16_t)(door_hole_y(d) + 144);
            m++;
        }
    }
    if (n > max - m) n = max - m;
    for (int i = 0; i < n; i++) {
        uint8_t piece = defs[i].piece;
        // One bench group in four is the variant with the broken bench, picked by (block, piece index). Only the
        // groups on tile row 0 of the kit phases have it baked (tile budget; tools/bake_cathedral_kit.py).
        if (piece == STRIP_PIECE_BANCO_GRUPO4 && !layout_of(b.idx) && ((((defs[i].y + 4) >> 3) & 15) == 0) &&
            (hash32(((uint32_t)block * 0x9e3779b9u) ^ ((uint32_t)i * 0x85ebca6bu) ^ 0x42524b4eu) & 3u) == 0)
            piece = STRIP_PIECE_BANCO_GRUPO4_ROTO;
        // The kit has no mirrored piece: the barricade end that opens to the right is the other id when the plan is mirrored.
        if (b.mirror) {
            if (piece == STRIP_PIECE_SACOS_REMATE_DER) piece = STRIP_PIECE_SACOS_REMATE;
            else if (piece == STRIP_PIECE_SACOS_REMATE) piece = STRIP_PIECE_SACOS_REMATE_DER;
            else if (piece == STRIP_PIECE_SANTO) piece = STRIP_PIECE_SANTO_DER;
            else if (piece == STRIP_PIECE_SANTO_DER) piece = STRIP_PIECE_SANTO;
        }
        out[m].piece = piece;
        out[m].mirror = b.mirror;
        out[m].lx = defs[i].x;
        out[m].ly = defs[i].y;
        m++;
    }
    return m;
}

int enc_block_rects(int32_t block, EncRect *out, int max) {
    EncBlock b;
    enc_block_info(block, &b);
    int n = 0;
    if (b.kind == ENC_BLOCK_ENCOUNTER && !ARPG_OJO_TEST) {      // arpg-ojo: no sacos / alambre, only the test columns
        const EncPlant *pl = &s_plants[b.plant];
        const RoomLayout *lay = layout_of(b.idx);
        const EncRectDef *rdefs = lay ? lay->rects : pl->rects;
        const int nr = room_def()->chapel_gate ? 0 : lay ? lay->n_rects : pl->n_rects;
        for (int i = 0; i < nr && n < max; i++) {
            const EncRectDef *r = &rdefs[i];
            out[n].kind = r->kind;
            out[n].x = (int16_t)(ENC_FLOOR_X + (b.mirror ? ENC_FLOOR_W - (r->x + r->w) : r->x));
            out[n].y = r->y;
            out[n].w = r->w;
            out[n].h = r->h;
            n++;
        }
    }
    // The reja of the key (chapel_gate): a barrier line across the floor until it has risen.
    if (b.kind == ENC_BLOCK_ENCOUNTER && !s_gate_open && room_def()->chapel_gate && b.idx == room_def()->blocks - 1 && n < max) {
        out[n].kind = ENC_R_BARRERA;
        out[n].x = ENC_FLOOR_X;
        out[n].y = ENC_GATE_LOCAL_Y - ENC_BARRIER_H / 2;
        out[n].w = ENC_FLOOR_W;
        out[n].h = ENC_BARRIER_H;
        n++;
    }
    // Rooms have no gates (salas ARPG): no top barrier and nothing closes behind the hero. Only the
    // boss lock keeps the bottom edge of its own room closed while the fight lasts.
    if (b.kind == ENC_BLOCK_BOSS && s_boss_locked && b.idx == s_active_boss_k && n < max) {
        out[n].kind = ENC_R_BARRERA;
        out[n].x = ENC_FLOOR_X;
        out[n].y = ENC_BLOCK_H - ENC_BARRIER_H;
        out[n].w = ENC_FLOOR_W;
        out[n].h = ENC_BARRIER_H;
        n++;
    }
    return n;
}

int enc_collision_value(uint8_t rect_kind) {
    // 0 free, 1 bodies, 2 low cover, 3 bodies and bullets: sacos are low cover (the hero crouches behind them, DESIGN.md 6.9),
    // the alambre stops bodies, the barrier stops bullets too
    return rect_kind == ENC_R_BARRERA ? 3 : rect_kind == ENC_R_SACOS ? 2 : 1;
}

// ---------------------------------------------------------------------------
// Runtime
// ---------------------------------------------------------------------------

static int block_of_encounter(int k) { return s_first_block - k; }    // one floor per block, no corridors
static int window_top(int block) { return block * ENC_BLOCK_H + (int)strip_shift_total_px(); }

static EnemyType enemy_type_of(uint8_t t) {
    switch (t) {
    case ENC_E_CIRENEO:    return ENEMY_TYPE_CHARGER;
    case ENC_E_OJO:        return ENEMY_TYPE_SHOOTER;
    case ENC_E_ABANDERADO: return ENEMY_TYPE_ABANDERADO;
    case ENC_E_CAMPANERO:  return ENEMY_TYPE_CAMPANERO;
    case ENC_E_MONAGUILLO: return ENEMY_TYPE_MONAGUILLO;
    case ENC_E_BEBE:       return ENEMY_TYPE_BEBE;
    case ENC_E_PARROCO:    return ENEMY_TYPE_PARROCO;
    case ENC_E_MONJA:      return ENEMY_TYPE_MONJA;
    default:               return ENEMY_TYPE_EXVOTO;
    }
}

// ---------------------------------------------------------------------------
// Rooms (salas ARPG): doors, lateral openings and where the hero lands.
// ---------------------------------------------------------------------------

// Block of a door (stage k of the room) and the top of its hole inside the block.
static int door_block(const RoomDef *r, const RoomDoor *d) { return d->side == DOOR_UP ? r->blocks - 1 : (d->screen - 1) / 2; }
static int door_hole_y(const RoomDoor *d) { (void)d; return ARPG_ROOM_HOLE_Y_PX; }

int enc_room_openings(int32_t block, EncRoomOpening *out, int max) {
    const RoomDef *r = room_def();
    const int k = s_first_block - (int)block;
    int n = 0;
    if (k < 0 || k >= r->blocks) return 0;
    for (int i = 0; i < r->n_doors && n < max; i++) {
        const RoomDoor *d = &r->doors[i];
        if (d->side == DOOR_UP || door_block(r, d) != k) continue;
        out[n].x = (int16_t)(d->side == DOOR_RIGHT ? (ENC_FLOOR_X + ENC_FLOOR_W) : ENC_CAM_X);
        out[n].y = (int16_t)door_hole_y(d);
        out[n].w = (int16_t)ARPG_ROOM_HOLE_W_PX;
        out[n].h = (int16_t)ARPG_ROOM_HOLE_H_PX;
        n++;
    }
    return n;
}

int enc_block_has_door(int32_t block) {
    const RoomDef *r = room_def();
    if (s_first_block - (int)block != r->blocks - 1) return 0;
    for (int i = 0; i < r->n_doors; i++) if (r->doors[i].side == DOOR_UP) return 1;
    return 0;
}

int enc_room_top_block(void) { return s_first_block - (room_def()->blocks - 1); }

void enc_room_select(int room, int from_room) {
    pickups_bank_relics();           // a relic left on the floor must not be lost with the room
    s_room = (room >= 0 && room < ENC_ROOM_COUNT) ? room : 0;
    s_from_room = from_room;
    room_light_load(s_room);       // loading screen: the room's light pack (kit, hero, enemy tables); the clips and remates read from it
    if (!((g_arpg.rooms_seen >> s_room) & 1)) {      // first visit: the overlay map reveals it (kept in the save)
        g_arpg.rooms_seen |= (uint16_t)(1u << s_room);
    }
    arpg_progress_save();            // every room change: xp, kills and chests of the room just left survive a power-off
}

// ---------------------------------------------------------------------------
// Overlay map: the layout is walked from Nave 1 along the doors of the ficha: an upper door stacks the next room on top;
// a lateral door puts the neighbour beside the wall, at the height that lines up both openings.
// ---------------------------------------------------------------------------
#define ENC_MAP_GAP 40
static EncMapRoom s_map[ENC_ROOM_COUNT];
static uint8_t s_map_done;
static uint16_t s_map_mask;
static int map_door_cy(const RoomDoor *d) {       // lateral door: centre of its opening, from the foot of the room
    return ((d->screen - 1) / 2 + 1) * ENC_BLOCK_H - ARPG_ROOM_HOLE_Y_PX - ARPG_ROOM_HOLE_H_PX / 2;
}
static void map_place(int room, int x, int y) {
    const RoomDef *r = &s_rooms[room];
    EncMapRoom *m = &s_map[room];
    m->x = (int16_t)x; m->y = (int16_t)y; m->w = ENC_FLOOR_W; m->h = (int16_t)(r->blocks * ENC_BLOCK_H);
    m->n_doors = r->n_doors; m->altar = r->altar; m->chest = r->chest; m->key = r->drops_key;
    m->altar_x = (int16_t)(x + ENC_FLOOR_W / 2); m->altar_y = (int16_t)(y + ARPG_ROOM_FOOT_OFFSET_PX);
    m->chest_x = m->altar_x; m->chest_y = (int16_t)(y + (r->blocks - 1) * ENC_BLOCK_H + ENC_BLOCK_H - 90);
    for (int i = 0; i < r->n_doors; i++) {
        const RoomDoor *d = &r->doors[i];
        EncMapDoor *o = &m->door[i];
        o->side = d->side; o->dest = d->dest;
        if (d->side == DOOR_UP) { o->cx = (int16_t)(x + ENC_FLOOR_W / 2); o->cy = (int16_t)(m->y + m->h); }
        else {
            o->cx = (int16_t)(d->side == DOOR_LEFT ? x : x + ENC_FLOOR_W);
            o->cy = (int16_t)(y + map_door_cy(d));
        }
    }
}
static void map_walk(int room, int x, int y) {
    s_map_mask |= (uint16_t)(1u << room);
    map_place(room, x, y);
    const RoomDef *r = &s_rooms[room];
    for (int i = 0; i < r->n_doors; i++) {
        const RoomDoor *d = &r->doors[i];
        if ((s_map_mask >> d->dest) & 1) continue;
        const RoomDef *c = &s_rooms[d->dest];
        if (d->side == DOOR_UP) { map_walk(d->dest, x, y + r->blocks * ENC_BLOCK_H); continue; }
        for (int j = 0; j < c->n_doors; j++) {           // the door of the neighbour that leads back here
            const RoomDoor *cd = &c->doors[j];
            if (cd->dest != room || cd->side == DOOR_UP) continue;
            const int cx = d->side == DOOR_LEFT ? x - (ENC_FLOOR_W + ENC_MAP_GAP) : x + ENC_FLOOR_W + ENC_MAP_GAP;
            map_walk(d->dest, cx, y + map_door_cy(d) - map_door_cy(cd));
            break;
        }
    }
}
void enc_map_room(int room, EncMapRoom *out) {
    if (!s_map_done) { s_map_done = 1; s_map_mask = 0; map_walk(0, 0, 0); }
    if (room < 0 || room >= ENC_ROOM_COUNT) room = 0;
    *out = s_map[room];
}
int enc_map_hero(int px, int py, int *mx, int *my) {
    EncMapRoom m;
    enc_map_room(s_room, &m);
    const int foot = window_top(block_of_encounter(0)) + ENC_BLOCK_H;
    *mx = m.x + (px - ENC_FLOOR_X);
    *my = m.y + (foot - py);
    return s_room;
}

uint32_t enc_room_seed(int room) { return hash32(0x53414c41u + (uint32_t)room * 0x9e3779b9u) | 1u; }

int enc_room_entry(void) {
    if (g_enc_debug.start_boss) return ENC_ROOM_CRIPTA;
    if (g_enc_debug.start_room > 0 && g_enc_debug.start_room <= ENC_ROOM_COUNT) return g_enc_debug.start_room - 1;
    return g_arpg.last_altar < ENC_ROOM_COUNT ? g_arpg.last_altar : 0;
}

int enc_room_current(void) { return s_room; }
int enc_room_level(void) { return room_def()->level; }
const char *enc_room_name(void) { return room_def()->name; }

int enc_room_arrival(int *out_x, int *out_y, int *out_dir) {
    const RoomDef *r = room_def();
    if (s_from_room >= 0) {
        for (int i = 0; i < r->n_doors; i++) {          // by the lateral door that leads back to the room he comes from
            const RoomDoor *d = &r->doors[i];
            if (d->dest != s_from_room || d->side == DOOR_UP) continue;
            const int top = window_top(block_of_encounter(door_block(r, d)));
            const int left = d->side == DOOR_LEFT;
            *out_x = left ? ENC_FLOOR_X + 20 : ENC_FLOOR_X + ENC_FLOOR_W - 20;
            *out_y = top + door_hole_y(d) + ARPG_ROOM_HOLE_ARRIVE_PX;
            *out_dir = left ? DIR_EAST : DIR_WEST;       // facing into the room
            return 1;
        }
    }
    // The foot of the room (the Cripta: a few steps from the bottom edge so the boss does not wake on arrival).
    *out_x = ENC_FLOOR_X + ENC_FLOOR_W / 2;
    *out_y = window_top(block_of_encounter(0)) + ENC_BLOCK_H - (r->type == RT_CRIPTA ? 12 : ARPG_ROOM_FOOT_OFFSET_PX);
    *out_dir = DIR_NORTH;
    {   // A prop (the sacos of Nave 3) can sit exactly on the foot: the hero would land inside it and never move. Step north out of it.
        const int32_t blk = block_of_encounter(0);
        const int top = window_top(blk);
        EncRect rc[16];
        const int n = enc_block_rects(blk, rc, 16);
        for (int pass = 0; pass < 4; pass++) {
            int moved = 0;
            for (int i = 0; i < n; i++) {
                const int ly = *out_y - top;
                if (*out_x >= rc[i].x - 6 && *out_x < rc[i].x + rc[i].w + 6 && ly >= rc[i].y - 6 && ly < rc[i].y + rc[i].h + 6) {
                    *out_y = top + rc[i].y - 7;
                    moved = 1;
                }
            }
            if (!moved) break;
        }
    }
    return 0;
}

static int stage_at_py(int py) {
    int32_t block = (int32_t)(py - (int)strip_shift_total_px()) / ENC_BLOCK_H;
    return s_first_block - (int)block;
}

// Furniture of the room: the chest at the far end, the altar at the foot.
static int room_center_x(void) { return ENC_FLOOR_X + ENC_FLOOR_W / 2; }
static int room_chest_block(void) { return room_def()->blocks - 1; }
static int room_chest_y(void) { return window_top(block_of_encounter(room_chest_block())) + 90; }
static int room_altar_x(void) { return ENC_FLOOR_X + 48; }
static int room_altar_y(void) { return window_top(block_of_encounter(0)) + 316; }


// Where the Campanero raises an Exvoto: beside one of the columns of the test room or at a random floor spot of the block.
void enc_camp_spot(uint32_t r, int *x, int *y) {
    const int top = window_top(block_of_encounter(s_active_boss_k));
    const uint32_t h = hash32(r ^ 0x43414d50u);
    if (h & 1u) {
        int cols[8], n = 0;
        for (int i = 0; i < (int)(sizeof(s_campanero_pieces) / sizeof(s_campanero_pieces[0])) && n < 8; i++)
            if (s_campanero_pieces[i].piece == STRIP_PIECE_COLUMNA_ENTERA) cols[n++] = i;
        const EncPieceDef *c = &s_campanero_pieces[cols[(h >> 1) % (uint32_t)n]];
        *x = ENC_FLOOR_X + c->x + 8 + (((h >> 9) & 1u) ? 20 : -20);
        *y = top + c->y + 64;
    } else {
        *x = ENC_FLOOR_X + 20 + (int)((h >> 1) % 168u);
        *y = top + 120 + (int)((h >> 12) % 200u);
    }
}

// A crossing asked by enc_update() is consumed by main.c on the next frame, which fades to black and loads room s_exit_room.
int enc_room_take_exit(int *out_room) {
    if (s_exit_room < 0) return 0;
    *out_room = s_exit_room;
    s_exit_room = -1;
    return 1;
}

// ---------------------------------------------------------------------------
// Rest behaviours (DESIGN-ARPG.md 12): a sleeping enemy (ENEMY_STATE_DORMANT, the AI skips it) wanders around its post until its
// group wakes. The post is implicit: position minus offset (ox, oy), so the world shifting under the strip needs no fixing.
// ---------------------------------------------------------------------------
typedef struct { uint8_t mode, phase, aux; int16_t timer; fixed ox, oy; } RestRec;
static RestRec s_rest[MAX_GAMEPLAY_ENEMIES];
static uint32_t s_rest_group_mask;      // blocks with at least one resting enemy: their wake is by radius or hit, not by the room margin
static uint32_t s_rest_wake_mask;       // blocks whose resting group has to wake now

// 8.8 unit vectors per direction on the 2:1 ground (screen dy is half of ground dy), indexed by DIR_*.
static const int16_t s_rest_vx[8] = { 0, -181, -256, -181, 0, 181, 256, 181 };
static const int16_t s_rest_vy[8] = { 128, 91, 0, -91, -128, -91, 0, 91 };

static void rest_assign(int slot, int mode, Enemy *e) {
    if (slot < 0 || slot >= MAX_GAMEPLAY_ENEMIES) return;
    RestRec *r = &s_rest[slot];
    memset(r, 0, sizeof(*r));
    if (mode < ENC_S_CRAWL || mode > ENC_S_PATROL) return;
    r->mode = (uint8_t)mode;
    r->aux = (uint8_t)(mode == ENC_S_SWEEP ? 0 : (slot & 1));
    r->timer = (int16_t)(slot * 7 % 24);            // desynchronise the members of a group
    if (mode == ENC_S_HIDDEN) e->home_flags |= ENEMY_HOME_HIDDEN;
}

// The rest every role gets when the debug mailbox asks for "as designed" (rest_mode 1), or the forced one.
static int rest_mode_for(int enc_type, int guard) {
    const int dbg = g_enc_debug.rest_mode;
    if (!dbg || guard == 2) return 0;
    if (dbg == 2) return ENC_S_HIDDEN;
    if (dbg == 3) return ENC_S_PATROL;
    switch (enc_type) {
        case ENC_E_BEBE: return ENC_S_CRAWL;
        case ENC_E_MONAGUILLO: return ENC_S_SWAY;
        case ENC_E_OJO: return ENC_S_SWEEP;
        case ENC_E_CIRENEO: return ENC_S_STROLL;
        default: return 0;
    }
}

static int rest_walk(Enemy *e, RestRec *r, int dir, int speed) {
    fixed vx = (s_rest_vx[dir] * speed) >> 8;
    fixed vy = (s_rest_vy[dir] * speed) >> 8;
    const fixed x0 = e->x, y0 = e->y;
    const int ok = sweep_position(&e->x, &e->y, vx, vy);
    r->ox += e->x - x0;
    r->oy += e->y - y0;
    e->dir = dir;
    return ok;
}

static void rest_anim(Enemy *e, int moving) {
    if (!moving) { e->anim_timer = 0; e->frame = 0; return; }
    int period = g_characters[e->char_id].anim_period;
    if (period <= 0) period = 4;
    if (++e->anim_timer >= period) { e->anim_timer = 0; e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES; }
}

// Home direction from an offset (the rest zone is a small box around the post).
static int rest_outside(const RestRec *r) {
    const fixed ax = r->ox < 0 ? -r->ox : r->ox, ay = r->oy < 0 ? -r->oy : r->oy;
    return ax > TO_FIXED(ENC_REST_STROLL_PX) || ay > TO_FIXED(ENC_REST_STROLL_PX / 2);
}

// One frame of rest. phase 0 = moving, 1 = paused; timer = frames left in the leg; aux = heading side / leg / gaze step.
static void rest_step(Enemy *e, RestRec *r) {
    int moving = 0;
    switch (r->mode) {
    case ENC_S_CRAWL:                      // 36 frames of crawl, 28 of pause, then a turn of 135 degrees (back home when too far)
        if (r->timer > 0) {
            r->timer--;
            if (r->phase == 0) { rest_walk(e, r, e->dir, 100); moving = 1; }
        } else if (r->phase == 0) {
            r->phase = 1; r->timer = 28;
        } else {
            r->phase = 0; r->timer = 36;
            e->dir = rest_outside(r) ? enemy_dir_from_vector(-r->ox, -r->oy) : (e->dir + 3) & 7;
        }
        break;
    case ENC_S_SWAY:
    case ENC_S_STROLL: {                   // along x, to one end, pause, to the other
        const int sway = r->mode == ENC_S_SWAY;
        const fixed half = TO_FIXED(sway ? ENC_REST_SWAY_PX : ENC_REST_STROLL_PX);
        if (r->phase == 1) {
            if (--r->timer <= 0) { r->phase = 0; r->aux ^= 1; }
            break;
        }
        const int east = (r->aux & 1) == 0;
        const int ok = rest_walk(e, r, east ? DIR_EAST : DIR_WEST, sway ? 64 : 80);
        moving = 1;
        if (!ok || (east ? r->ox >= half : r->ox <= -half)) { r->phase = 1; r->timer = sway ? 24 : 60; moving = 0; }
        break;
    }
    case ENC_S_SWEEP: {                    // gaze: W, SW, S, SE, E and back, 40 frames per step
        static const uint8_t seq[8] = { DIR_WEST, DIR_SOUTHWEST, DIR_SOUTH, DIR_SOUTHEAST, DIR_EAST, DIR_SOUTHEAST, DIR_SOUTH, DIR_SOUTHWEST };
        if (--r->timer <= 0) { r->timer = 40; r->aux = (r->aux + 1) & 7; }
        e->dir = seq[r->aux & 7];
        break;
    }
    case ENC_S_PATROL: {                   // rectangle: east, south, west, north
        static const uint8_t legs[4] = { DIR_EAST, DIR_SOUTH, DIR_WEST, DIR_NORTH };
        const int leg = r->aux & 3;
        const int ok = rest_walk(e, r, legs[leg], 96);
        moving = 1;
        const int done = leg == 0 ? r->ox >= TO_FIXED(ENC_REST_PATROL_W) : leg == 1 ? r->oy >= TO_FIXED(ENC_REST_PATROL_H)
                       : leg == 2 ? r->ox <= 0 : r->oy <= 0;
        if (!ok || done) r->aux = (uint8_t)((leg + 1) & 3);
        break;
    }
    default: break;                        // HIDDEN: still
    }
    rest_anim(e, moving);
}

// Every frame, before the wake pass: moves the resting enemies and decides which resting groups wake (the hero inside the
// warning radius of any member, or any member hit). Sets s_rest_group_mask / s_rest_wake_mask by block.
static void rest_update(Enemy *enemies, int max_enemies, int px, int py) {
    s_rest_group_mask = s_rest_wake_mask = 0;
    for (int i = 0; i < max_enemies && i < MAX_GAMEPLAY_ENEMIES; i++) {
        Enemy *e = &enemies[i];
        RestRec *r = &s_rest[i];
        if (!r->mode) {
            // Members that do not rest (the Ojo, a garrison): hit or killed while asleep, they wake the group too.
            if (e->pack >= 0 && e->pack < 32 && ((e->active && e->state == ENEMY_STATE_DORMANT && (e->hp < e->max_hp || e->hit_timer > 0)) ||
                                                 (e->hp <= 0 && e->state == ENEMY_STATE_DEAD))) s_rest_wake_mask |= 1u << e->pack;
            continue;
        }
        if (!e->active || e->state != ENEMY_STATE_DORMANT) {       // woken, dead or recycled: the rest is over
            e->home_flags &= (uint8_t)~ENEMY_HOME_HIDDEN;
            r->mode = 0;
            // Killed or hurt while it slept: the group wakes (a one-hit Bebe never shows as "hurt" otherwise).
            if (e->pack >= 0 && e->pack < 32 && ((e->active && (e->hp < e->max_hp || e->hit_timer > 0)) ||
                                                 (e->hp <= 0 && e->state == ENEMY_STATE_DEAD))) s_rest_wake_mask |= 1u << e->pack;
            continue;
        }
        if (e->pack < 0 || e->pack >= 32) continue;
        s_rest_group_mask |= 1u << e->pack;
        if (e->hp > 0) rest_step(e, r);
        const int dx = px - TO_INT(e->x), dy = py - TO_INT(e->y);
        const int rad = r->mode == ENC_S_HIDDEN ? ENC_REST_HIDDEN_WAKE_PX : ENC_REST_WAKE_PX;
        if (e->hp > 0 && dx * dx + GROUND_DY2(dy) <= rad * rad) s_rest_wake_mask |= 1u << e->pack;
        if (e->hit_timer > 0 || e->hp < e->max_hp) s_rest_wake_mask |= 1u << e->pack;
    }
}

// Same field setup as encounters_spawn() / sandbox_place(); the owner encounter goes in `pack`.
static void place_enemy(Enemy *e, const EncEnemyDef *d, int x, int y, int ordinal, int owner, int awake_now) {
    EnemyType type = enemy_type_of(d->type);
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = owner;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = g_enemy_tuning[type].max_hp * BAL_AT(hp_pct, type, 100) / 100;
    if (type == ENEMY_TYPE_ABANDERADO && g_enc_debug.boss_hp) e->max_hp = g_enc_debug.boss_hp;    // scenarios tune the boss
    // Same life in every room; the Abanderado scales by its boss number. The Campanero's 3000 is its sheet.
    if (type == ENEMY_TYPE_ABANDERADO) e->max_hp = e->max_hp * BAL(boss_hp_pct0, ARPG_BOSS_HP_PCT(boss_number(owner))) / 100;
    e->hp = e->max_hp;
    e->dir = (ordinal * 2) % 8;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    // v2: every enemy of an encounter is there from the start and waits still (asleep, untouchable) until the hero
    // crosses the bottom edge; then all wake at once (wake_owner). Only the boss escort reinforcements walk in awake.
    e->state = awake_now ? ENEMY_INITIAL_STATE(type) : ENEMY_STATE_DORMANT;
    // Post of the Ojo (its leash) and of the garrison (DESIGN.md 6.13.9). Set after strafe_dir: the Ojo keeps its post there.
    if (type == ENEMY_TYPE_SHOOTER || d->state == ENC_S_GUARD) {
        e->home_flags = ENEMY_HOME_SET | (d->state == ENC_S_GUARD ? ENEMY_HOME_GUARD : 0);
        *enemy_home_x(e) = x;
        *enemy_home_y(e) = y;
    }
}

static int spawn_group(Enemy *enemies, int max_enemies, const EncEnemyDef *defs, int n, int mirror,
                       int top, int y_override, int owner, int awake_now) {
    int made = 0;
    for (int i = 0; i < n; i++) {
        int slot = -1;
        for (int s = 0; s < max_enemies; s++) {
            if (!enemies[s].active) { slot = s; break; }
        }
        if (slot < 0) break;
        int lx = mirror ? ENC_FLOOR_W - defs[i].x : defs[i].x;
        int ly = y_override >= 0 ? y_override : defs[i].y;
        place_enemy(&enemies[slot], &defs[i], ENC_FLOOR_X + lx, top + ly, i, owner, awake_now);
        rest_assign(slot, awake_now ? 0 : defs[i].state, &enemies[slot]);      // ENC_S_CRAWL.. sleep and move around the post
        made++;
    }
    return made;
}

// ---------------------------------------------------------------------------
// Group population: each block of a room holds one group of fixed composition (max 12), taken from this list, filtered by
// the nave and never the same group in two consecutive blocks. Chosen by hash(room, block): a room is always the same.
// ---------------------------------------------------------------------------
enum { RK_BEBE = 0, RK_EXVOTO, RK_EXVOTO_GUARD, RK_EXVOTO_PRAY, RK_MONAGUILLO, RK_PARROCO, RK_MONJA, RK_OJO, RK_CIRENEO, RK_COUNT };
typedef struct {
    uint8_t enc_type;   // ENC_E_* of the kind
    uint8_t guard;      // 1 = stays at its post, watching, until released; 2 = prays at its post and heals (Monja de cera of the chapel)
} RoomKind;
static const RoomKind s_room_kinds[RK_COUNT] = {
    [RK_BEBE]         = { ENC_E_BEBE, 0 },        // swarm, dies in one hit, a bit faster
    [RK_EXVOTO]       = { ENC_E_EXVOTO, 0 },      // the base Exvoto
    [RK_EXVOTO_GUARD] = { ENC_E_EXVOTO, 1 },      // Exvoto of the garrison (DESIGN.md 6.13.9)
    [RK_EXVOTO_PRAY]  = { ENC_E_EXVOTO, 2 },      // Monja de cera praying at the back: heals those around her until the hero is on her
    [RK_MONAGUILLO]   = { ENC_E_MONAGUILLO, 0 },  // Exvoto branch "chico", tier 2 (walks in, no puddle)
    [RK_PARROCO]      = { ENC_E_PARROCO, 0 },     // Exvoto branch "chico", tier 3: tank, shoves the hero
    [RK_MONJA]        = { ENC_E_MONJA, 1 },       // Exvoto branch "chica", tier 3: prays behind and heals
    [RK_OJO]          = { ENC_E_OJO, 0 },         // tier 1 or 2 by the nave (ENEMY_TIER2)
    [RK_CIRENEO]      = { ENC_E_CIRENEO, 0 },
};
typedef struct { uint8_t kind, count; } GroupPart;
typedef struct {
    const char *name;
    uint8_t nave;       // the nave (1..4) whose rooms draw it; each nave has its own list (DESIGN-ARPG.md 10)
    uint8_t n_parts;
    GroupPart parts[5];
} GroupDef;
// Mixed groups. The Monja de cera (RK_EXVOTO_PRAY) comes first: she takes the back slots and prays there; the Monaguillos
// stand in front of her and the Bebes at the very front (slots fill from the back of the block).
enum { G_REBANO = 0, G_PROCESION, G_CORRILLO,                 // Nave 1
       G_GUARDIA_MONJA, G_PUESTO, G_CARGA,                    // Nave 2
       G_CORO, G_TIRADORES, G_CARGA_DOBLE,                    // Nave 3
       G_GUARDIA, G_CORTEJO, G_ASALTO,                        // Nave 4
       G_NORMAL_COUNT,   // the ones above are drawn by hash from the list of the nave
       G_PARROQUIA = G_NORMAL_COUNT, G_MISA, G_MONJARANA, G_COUNT };   // fixed groups of the special encounters, never drawn
static const GroupDef s_groups[G_COUNT] = {
    [G_REBANO]        = { "Rebaño",           1, 2, { { RK_EXVOTO_PRAY, 1 }, { RK_BEBE, 6 } } },
    [G_PROCESION]     = { "Procesión",        1, 2, { { RK_MONAGUILLO, 2 }, { RK_BEBE, 5 } } },
    [G_CORRILLO]      = { "Corrillo",         1, 3, { { RK_EXVOTO_PRAY, 1 }, { RK_MONAGUILLO, 1 }, { RK_BEBE, 4 } } },
    [G_GUARDIA_MONJA] = { "Guardia de la monja", 2, 3, { { RK_EXVOTO_PRAY, 2 }, { RK_MONAGUILLO, 2 }, { RK_BEBE, 4 } } },
    [G_PUESTO]        = { "Puesto",           2, 3, { { RK_OJO, 1 }, { RK_MONAGUILLO, 2 }, { RK_BEBE, 4 } } },
    [G_CARGA]         = { "Carga",            2, 4, { { RK_EXVOTO_PRAY, 1 }, { RK_CIRENEO, 1 }, { RK_MONAGUILLO, 2 }, { RK_BEBE, 4 } } },
    [G_CORO]          = { "Coro",             3, 3, { { RK_EXVOTO_PRAY, 3 }, { RK_MONAGUILLO, 3 }, { RK_BEBE, 4 } } },
    [G_TIRADORES]     = { "Tiradores",        3, 4, { { RK_EXVOTO_PRAY, 1 }, { RK_OJO, 2 }, { RK_MONAGUILLO, 2 }, { RK_BEBE, 4 } } },
    [G_CARGA_DOBLE]   = { "Carga doble",      3, 4, { { RK_EXVOTO_PRAY, 1 }, { RK_CIRENEO, 2 }, { RK_MONAGUILLO, 2 }, { RK_BEBE, 3 } } },
    [G_GUARDIA]       = { "Guardia",          4, 5, { { RK_EXVOTO_PRAY, 2 }, { RK_OJO, 1 }, { RK_CIRENEO, 1 }, { RK_MONAGUILLO, 3 }, { RK_BEBE, 4 } } },
    [G_CORTEJO]       = { "Cortejo",          4, 4, { { RK_EXVOTO_PRAY, 2 }, { RK_OJO, 2 }, { RK_MONAGUILLO, 3 }, { RK_BEBE, 5 } } },
    [G_ASALTO]        = { "Asalto",           4, 5, { { RK_EXVOTO_PRAY, 2 }, { RK_OJO, 1 }, { RK_CIRENEO, 2 }, { RK_MONAGUILLO, 3 }, { RK_BEBE, 4 } } },
    // Special encounters (the nuns come first: they take the back slots; the Parroco and the Monaguillos stand in front).
    [G_PARROQUIA]  = { "Parroquia",  99, 3, { { RK_EXVOTO_PRAY, 7 }, { RK_MONAGUILLO, 4 }, { RK_PARROCO, 1 } } },
    [G_MISA]       = { "La Misa",    99, 4, { { RK_EXVOTO, 4 }, { RK_MONAGUILLO, 3 }, { RK_PARROCO, 2 }, { RK_MONJA, 2 } } },
    [G_MONJARANA]  = { "La monjaraña", 99, 3, { { RK_MONJA, 1 }, { RK_EXVOTO, 4 }, { RK_MONAGUILLO, 4 } } },
};

// Group of block k of the current room, -1 when the block has none (boss blocks, the walk-in block of a miniboss gallery).
static int group_of_block(int k) {
    const RoomDef *r = room_def();
    if (r->type == RT_CRIPTA) return -1;
    if (g_enc_debug.force_group && g_enc_debug.force_group <= G_NORMAL_COUNT && r->type == RT_NORMAL) return g_enc_debug.force_group - 1;
    if (r->type == RT_MISA) return k == r->special_block ? G_MISA : -1;
    if (r->type == RT_MONJARANA) return k == r->special_block ? G_MONJARANA : -1;
    if (r->type == RT_PARROQUIA) return G_PARROQUIA;
    int prev = -1;
    for (int b = 0; b <= k; b++) {                    // chosen block by block so that no two consecutive blocks repeat
        int cand[G_NORMAL_COUNT], n = 0;
        for (int g = 0; g < G_NORMAL_COUNT; g++) {
            if (s_groups[g].nave != r->nave || g == prev) continue;
            cand[n++] = g;
        }
        prev = cand[hash32(s_seed ^ ((uint32_t)b * 0x45d9f3bu) ^ 0x47525031u) % (uint32_t)n];
    }
    return prev;
}

// Room pool (room_pool.h): empties it and loads the enemy art this room can show: the groups of its blocks, the boss
// and its escort (the Abanderado also summons Monaguillos), the Exvoto when LEVANTAR can raise allies, and the
// Campanero. Whatever this misses is loaded on demand by chars_ready() and counted in g_pool_misses.
static void room_art_prepare_current(void) {
    uint32_t mask = 0;
    int campanero = 0;
    const RoomDef *r = room_def();
    for (int k = 0; k < r->blocks; k++) {
        const RoomLayout *lay = layout_of(k);
        if (lay) {
            for (int i = 0; i < lay->n_members; i++)
                mask |= 1u << g_char_group[enemy_type_char_id(enemy_type_of(lay->members[i].type))];
            continue;
        }
        const int g = group_of_block(k);
        if (g < 0) continue;
        for (int p = 0; p < s_groups[g].n_parts; p++) {
            const EnemyType t = enemy_type_of(s_room_kinds[s_groups[g].parts[p].kind].enc_type);
            mask |= 1u << g_char_group[enemy_type_char_id(t)];
        }
    }
    if (r->type == RT_CRIPTA) {
        const BossDef *bd = boss_def_of(boss_number(0));
        if (bd->enemy_type == ENEMY_TYPE_CAMPANERO) {
            campanero = 1;
            mask |= 1u << CG_EXVOTO;                              // it raises Exvotos from the floor
        } else {
            mask |= 1u << g_char_group[enemy_type_char_id(bd->enemy_type)];
        }
        if (bd->enemy_type == ENEMY_TYPE_ABANDERADO) mask |= 1u << CG_MONAGUILLO;
        for (int ph = 0; ph < bd->n_phases; ph++)
            for (int i = 0; i < bd->n_escort[ph]; i++)
                mask |= 1u << g_char_group[enemy_type_char_id(bd->escort[ph][i].type)];
    }
    if (arpg_inv_has_mechanic(ARPG_MECH_LEVANTAR)) mask |= 1u << CG_EXVOTO;
#if ARPG_OJO_TEST
    mask |= 1u << CG_OJO;            // arpg-ojo: the only enemy is the Ojo (ojo_test.c)
#endif
#if ARPG_EXVOTO_TEST || ARPG_REMATE_TEST
    // Test variants: the rooms are empty and the test code spawns the whole Exvoto family around the hero.
    mask |= (1u << CG_EXVOTO) | (1u << CG_MONAGUILLO) | (1u << CG_PARROCO) | (1u << CG_SMONJA);
#endif
    // Implied art: the Párroco prays with the Exvoto poses; under a Súper Monja's aura the Exvotos and Monaguillos of the
    // room turn into spiders (their spider clips are only loaded in her rooms).
    if (mask & (1u << CG_PARROCO)) mask |= 1u << CG_EXVOTO;
    if (mask & (1u << CG_SMONJA)) {
        if (mask & (1u << CG_EXVOTO)) mask |= 1u << CG_ARANA_EXVOTO;
        if (mask & (1u << CG_MONAGUILLO)) mask |= 1u << CG_ARANA_MONA;
    }
    room_art_prepare(mask, campanero);
    room_kit_load(s_room);                      // the props only this room uses (nitrofiles/rooms/sala_NN.rmk) after its enemy art
}

// Slot of each member in the 4 x 3 grid of the block: kinds[slot] = RK_*, -1 = empty. Ojos take spread-out slots.
static int group_kinds(int g, int8_t *kinds) {
    static const uint8_t spread[3] = { 1, 6, 8 };
    int total = 0;
    for (int i = 0; i < 12; i++) kinds[i] = -1;
    const GroupDef *def = &s_groups[g];
    for (int p = 0; p < def->n_parts; p++) {
        if (def->parts[p].kind != RK_OJO) continue;
        for (int c = 0; c < def->parts[p].count && total < 12; c++) {
            int slot = spread[c % 3];
            while (kinds[slot] >= 0) slot = (slot + 1) % 12;
            kinds[slot] = RK_OJO;
            total++;
        }
    }
    for (int p = 0; p < def->n_parts; p++) {
        if (def->parts[p].kind == RK_OJO) continue;
        for (int c = 0; c < def->parts[p].count && total < 12; c++) {
            int slot = 0;
            while (kinds[slot] >= 0) slot++;
            kinds[slot] = (int8_t)def->parts[p].kind;
            total++;
        }
    }
    return total;
}

// Tier of an Ojo / Cireneo: Parte 1 of the cathedral (this demo) has no tier 2 (DESIGN-ARPG.md 7); Parte 2 brings it back.
static int tier2_of(int k, int slot) { (void)k; (void)slot; return 0; }

static void room_group_slot(int k, int i, int *out_x, int *out_y) {
    const int top = window_top(block_of_encounter(k));
    const int col = i & 3, row = i >> 2;
    uint32_t h = hash32(s_seed ^ ((uint32_t)k * 0x9e3779b9u) ^ ((uint32_t)i * 0x119de1f3u) ^ 0x534c4f54u);
    int x = ENC_FLOOR_X + 28 + col * 48 + (int)(h % 9u) - 4;
    int y = top + 84 + row * 66 + (int)((h >> 8) % 9u) - 4;
    if (x < ENC_FLOOR_X + 12) x = ENC_FLOOR_X + 12;
    if (x > ENC_FLOOR_X + ENC_FLOOR_W - 12) x = ENC_FLOOR_X + ENC_FLOOR_W - 12;
    *out_x = x;
    *out_y = y;
}

static void place_room_enemy(Enemy *e, const RoomKind *kind, int x, int y, int ordinal, int owner, int hp_pct, int tier2) {
    EnemyType type = enemy_type_of(kind->enc_type);
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = owner;
    e->char_id = enemy_type_char_id(type);
    // Same life in every room; then the tier (x2 life) and the miniboss multiplier.
    e->max_hp = g_enemy_tuning[type].max_hp * BAL_AT(hp_pct, type, 100) / 100;
    if (tier2) e->max_hp = e->max_hp * BAL(tier2_hp_pct, ARPG_TIER2_HP_PCT) / 100;
    e->max_hp = e->max_hp * hp_pct / 100;
    e->hp = e->max_hp;
    e->dir = (ordinal * 2) % 8;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->state = ENEMY_STATE_DORMANT;
    if (kind->guard == 2) {              // praying nun: the post is her pose, no home fields (the Exvoto dodge uses them)
        e->home_flags = ENEMY_HOME_GUARD;
        enemy_exvoto_start_praying(e, ordinal & 1, (ordinal * 2) % 8);
    } else if (type == ENEMY_TYPE_SHOOTER || kind->guard) {
        // The Ojo is never garrison (it would hold its post until the hero is within GUARD_RELEASE_DIST): it keeps only its post leash.
        e->home_flags = ENEMY_HOME_SET | (kind->guard && type != ENEMY_TYPE_SHOOTER ? ENEMY_HOME_GUARD : 0);
        *enemy_home_x(e) = x;
        *enemy_home_y(e) = y;
    }
    if (tier2) e->home_flags |= ENEMY_TIER2;
}

static int active_enemies(const Enemy *enemies, int max_enemies) {
    int n = 0;
    for (int i = 0; i < max_enemies; i++) if (enemies[i].active) n++;
    return n;
}

// Places the group of block k asleep. Respects the active cap: with no free slots it leaves the block
// unspawned so a later frame (after the group behind is recycled) can place it.
#if ARPG_BOT
// Balance loop: density of the groups (g_bal.group_pct, 0 or 100 = as designed): below 100 thins the roster out, above adds copies of it.
static void bot_group_density(int8_t *kinds) {
    if (g_bal.group_pct == 0 || g_bal.group_pct == 100) return;
    int valid = 0;
    for (int i = 0; i < 12; i++) if (kinds[i] >= 0) valid++;
    if (valid == 0) return;
    if (g_bal.group_pct < 100) {
        int keep = valid * g_bal.group_pct / 100;
        if (keep < 1) keep = 1;
        int seen = 0;
        for (int i = 0; i < 12; i++) {
            if (kinds[i] < 0) continue;
            seen++;
            if ((seen * keep) / valid == ((seen - 1) * keep) / valid) kinds[i] = -1;
        }
    } else {
        int src[12], ns = 0;
        for (int i = 0; i < 12; i++) if (kinds[i] >= 0 && kinds[i] != RK_OJO) src[ns++] = kinds[i];
        if (ns == 0) for (int i = 0; i < 12; i++) if (kinds[i] >= 0) src[ns++] = kinds[i];
        int extra = valid * (g_bal.group_pct - 100) / 100, c = 0;
        for (int i = 0; i < 12 && extra > 0; i++) {
            if (kinds[i] >= 0) continue;
            kinds[i] = (int8_t)src[c++ % ns];
            extra--;
        }
    }
}
#endif

// Group of the poster: each member at its feet, its state turned into the kind of post (REPOSO_A_ESTADO of gen_salas_rom.py).
// A member is placed when the hero is within ARPG_ROOM_SPAWN_NEAR_PX of its post and it was not placed yet (members_note).
static int member_near(int y, int py) { return y >= py - ARPG_ROOM_SPAWN_NEAR_PX && y <= py + ARPG_ROOM_SPAWN_NEAR_PX; }

static void member_note(int k, int i, int slot) {
    s_member_mask[k] |= (uint16_t)(1u << i);
    if (slot >= 0 && slot < (int)sizeof(s_slot_member)) s_slot_member[slot] = (uint8_t)i;
    if (!(s_member_seen[k] & (1u << i))) {
        s_member_seen[k] |= (uint16_t)(1u << i);
        if (g_enc_stats.members_placed < 255) g_enc_stats.members_placed++;
    }
}

static int spawn_layout_group(Enemy *enemies, int max_enemies, int k, const RoomLayout *lay, int py) {
    const int top = window_top(block_of_encounter(k));
    int active = active_enemies(enemies, max_enemies);
    int made = 0;
    s_member_full[k] = (uint16_t)((1u << lay->n_members) - 1u);
    for (int i = 0; i < lay->n_members && active + made < MAX_GAMEPLAY_ENEMIES; i++) {
        const RoomMember *m = &lay->members[i];
        if ((s_member_mask[k] >> i) & 1u) continue;
        if (!member_near(top + m->y, py)) continue;
        int slot = -1;
        for (int s = 0; s < max_enemies; s++) if (!enemies[s].active) { slot = s; break; }
        if (slot < 0) break;
        RoomKind kind = { m->type, (uint8_t)(m->state == ENC_S_PRAY ? 2 : m->state == ENC_S_GUARD ? 1 : 0) };
        if (m->state == ENC_S_PRAY && m->type != ENC_E_EXVOTO) kind.guard = 1;     // only the Exvoto has the praying pose
        int mx = m->x, my = m->y, state = m->state;
        if (m->type == ENC_E_MONAGUILLO) {                  // group with a wax nun: the acolyte rests at her side (16-24 px), not at its own post
            for (int j = 0; j < lay->n_members; j++) {
                const RoomMember *nun = &lay->members[j];
                if (nun->type != ENC_E_EXVOTO || nun->state != ENC_S_PRAY) continue;
                mx = nun->x + ((i & 1) ? -20 : 20);
                my = nun->y + 4;
                state = ENC_S_DORMANT;
                break;
            }
        }
        const int x = ENC_FLOOR_X + mx, y = top + my;
        int placed = 0;
        for (int t = 0; t < 4 && !placed; t++) {
            int tx = x + (t == 1 ? 12 : t == 2 ? -12 : 0);
            int ty = y + (t == 3 ? 12 : 0);
            if (position_is_free(TO_FIXED(tx), TO_FIXED(ty))) {
                place_room_enemy(&enemies[slot], &kind, tx, ty, i, k, 100, 0);
                rest_assign(slot, state, &enemies[slot]);          // ENC_S_CRAWL.. sleep and move around the post (0 for the others)
                placed = 1;
            }
        }
        if (placed) { made++; member_note(k, i, slot); }
    }
    return made;
}

static int spawn_room_group(Enemy *enemies, int max_enemies, int k, int py) {
    const RoomLayout *lay = layout_of(k);
    if (lay) return spawn_layout_group(enemies, max_enemies, k, lay, py);
    const int g = group_of_block(k);
    if (g < 0) return 0;
    int8_t kinds[12];
    group_kinds(g, kinds);
#if ARPG_BOT
    bot_group_density(kinds);
#endif
    int active = active_enemies(enemies, max_enemies);
    int made = 0;
    s_member_full[k] = 0;
    for (int i = 0; i < 12; i++) if (kinds[i] >= 0) s_member_full[k] |= (uint16_t)(1u << i);
    for (int i = 0; i < 12 && active + made < MAX_GAMEPLAY_ENEMIES; i++) {
        if (kinds[i] < 0 || ((s_member_mask[k] >> i) & 1u)) continue;
        int slot = -1;
        for (int s = 0; s < max_enemies; s++) if (!enemies[s].active) { slot = s; break; }
        if (slot < 0) break;
        int x, y;
        room_group_slot(k, i, &x, &y);
        if (!member_near(y, py)) continue;
        const RoomKind *kind = &s_room_kinds[kinds[i]];
        const int tier2 = (kinds[i] == RK_OJO || kinds[i] == RK_CIRENEO) ? tier2_of(k, i) : 0;
        int placed = 0;
        for (int t = 0; t < 4 && !placed; t++) {           // nudge around a prop before giving up on the slot
            int tx = x + (t == 1 ? 12 : t == 2 ? -12 : 0);
            int ty = y + (t == 3 ? 12 : 0);
            if (position_is_free(TO_FIXED(tx), TO_FIXED(ty))) {
                place_room_enemy(&enemies[slot], kind, tx, ty, i, k, 100, tier2);
                rest_assign(slot, rest_mode_for(kind->enc_type, kind->guard), &enemies[slot]);
                placed = 1;
            }
        }
        if (placed) { made++; member_note(k, i, slot); }
    }
    return made;
}

static int alive_of(const Enemy *enemies, int max_enemies, int owner, int *hurt) {
    int n = 0;
    *hurt = 0;
    for (int i = 0; i < max_enemies; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->pack != owner || e->hp <= 0) continue;
        n++;
        if (e->hp < e->max_hp) *hurt = 1;
    }
    return n;
}

static void wake_owner(Enemy *enemies, int max_enemies, int owner) {
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->pack != owner || e->state != ENEMY_STATE_DORMANT) continue;
        e->state = (e->home_flags & ENEMY_HOME_GUARD) ? ENEMY_STATE_GUARD : ENEMY_INITIAL_STATE(e->type);
        e->state_timer = 0;
        e->home_flags &= (uint8_t)~ENEMY_HOME_HIDDEN;
    }
}

// Escort and phases live in boss.c (BossDef above); these are the hooks it calls. They need the enemy pool and the hero
// position the last enc_update saw.
static Enemy *s_pool;
static int s_pool_n, s_hero_px, s_hero_py;

static void boss_spawn_escort(EnemyType type, int floor_x) {
    if (!s_pool) return;
    const uint8_t t = type == ENEMY_TYPE_SHOOTER ? ENC_E_OJO : type == ENEMY_TYPE_CHARGER ? ENC_E_CIRENEO :
                      type == ENEMY_TYPE_MONJA ? ENC_E_MONJA : ENC_E_EXVOTO;
    // Walk-in from the top for the Abanderado's escort; the Campanero's Ojo and Monja come back at their posts.
    int y = 16;
    if (boss_def_of(boss_number(s_active_boss_k))->enemy_type == ENEMY_TYPE_CAMPANERO)
        y = type == ENEMY_TYPE_SHOOTER ? CAMP_OJO_Y : type == ENEMY_TYPE_MONJA ? CAMP_MONJA_Y : 16;
    EncEnemyDef def = { t, ENC_S_AWAKE, (int16_t)floor_x, (int16_t)y };
    spawn_group(s_pool, s_pool_n, &def, 1, 0, window_top(block_of_encounter(s_active_boss_k)), y, s_active_boss_k, 1);
}

static void boss_set_barriers(int closed) {
    const int k = s_active_boss_k;
    const int top = window_top(block_of_encounter(k));
    s_boss_locked = closed;
    if (closed) {
        s_rt[k].back_closed = 1;
        strip_collision_fill_win(ENC_FLOOR_X, top + ENC_BLOCK_H - ENC_BARRIER_H, ENC_FLOOR_W, ENC_BARRIER_H, enc_collision_value(ENC_R_BARRERA));
    } else {
        s_rt[k].back_closed = 0;
        strip_collision_fill_win(ENC_FLOOR_X, top + ENC_BLOCK_H - ENC_BARRIER_H, ENC_FLOOR_W, ENC_BARRIER_H, 0);
        s_rt[k].verja_opening = 1;
    }
    nav_refresh_begin(s_hero_px, s_hero_py);      // the walkable grid knew the barrier as a wall (or not)
}

static void open_barrier(int k, int px, int py) {
    s_rt[k].barrier_open = 1;
    s_rt[k].back_closed = 0;
    const int top = window_top(block_of_encounter(k));
    strip_collision_fill_win(ENC_FLOOR_X, top, ENC_FLOOR_W, ENC_BARRIER_H, 0);
    strip_collision_fill_win(ENC_FLOOR_X, top + ENC_BLOCK_H - ENC_BARRIER_H, ENC_FLOOR_W, ENC_BARRIER_H, 0);
    nav_refresh_begin(px, py);          // the walkable grid knew the barrier as a wall
}

static void apply_debug(void) {
    if (g_enc_debug.god) g_player_state.god_mode = 1;
    g_enc_debug.start_dones = 0;      // there are no Dones in the dungeon: the debug request is dropped
}

// No relicarios and no Altar: the floors are room after room, nothing to hit besides the enemies.
static int boss_relic_pos(int k, int *x, int *y) { (void)k; (void)x; (void)y; return 0; }
static int altar_pos(int *x, int *y) { (void)x; (void)y; return 0; }

// v3 tier capture (evidence only): place one Bebé, one Párroco and one praying Monja around the hero, all awake
// and already wounded, in the current room so the Monja's green heals show on them. Clears the request.
static void tier_debug_spawn(Enemy *enemies, int max_enemies, int px, int py) {
    static const EnemyType types[3] = { ENEMY_TYPE_BEBE, ENEMY_TYPE_PARROCO, ENEMY_TYPE_MONJA };
    // Tight formation: the two fighters stay within the Monja's ARPG_MONJA_PRAY_RADIUS (48 ground px) so her
    // heals land, and she stands a little above the hero (just out of her own brawl range).
    static const int offs[3][2] = { { 16, -14 }, { -16, -16 }, { 0, -30 } };
    int made = 0;
    for (int t = 0; t < 3; t++) {
        int slot = -1;
        for (int s = 0; s < max_enemies; s++) if (!enemies[s].active) { slot = s; break; }
        if (slot < 0) break;
        Enemy *e = &enemies[slot];
        memset(e, 0, sizeof(*e));
        e->x = TO_FIXED(px + offs[t][0]);
        e->y = TO_FIXED(py + offs[t][1]);
        e->active = 1;
        e->type = types[t];
        e->pack = stage_at_py(py);
        e->char_id = enemy_type_char_id(types[t]);
        e->max_hp = g_enemy_tuning[types[t]].max_hp;
        e->hp = e->max_hp / 2;                       // wounded so the Monja has someone to heal
        if (e->hp < 1) e->hp = 1;
        e->dir = 0;
        e->strafe_dir = 1;
        if (types[t] == ENEMY_TYPE_MONJA) {
            e->state = ENEMY_STATE_PRAY;
            e->char_id = CHAR_EXVOTO_PRAY_STAND;
            *enemy_home_x(e) = TO_INT(e->x);
            *enemy_home_y(e) = TO_INT(e->y);
            e->home_flags = ENEMY_HOME_SET | ENEMY_HOME_GUARD;
        } else {
            e->state = ENEMY_INITIAL_STATE(types[t]);
        }
        made++;
    }
    (void)made;
    g_tier_debug.spawn = 0;
}

void enc_update(Enemy *enemies, int max_enemies, int px, int py) {
    volatile EncStats *st = &g_enc_stats;
    apply_debug();
    if (g_tier_debug.spawn) tier_debug_spawn(enemies, max_enemies, px, py);
#if RELIC_SHOWCASE
    {
        static int s_showcase_done = 0;
        if (!s_showcase_done) { g_relic_drop_debug = 1; s_showcase_done = 1; }
        if (keysDown() & KEY_SELECT) g_relic_drop_debug = 1;
    }
#endif
    if (g_relic_drop_debug) {   // buzon de escenarios: 5 reliquias/tomos en fila sobre el heroe
        static const uint8_t kind[5] = {ARPG_ITEM_RELIC, ARPG_ITEM_RELIC, ARPG_ITEM_RELIC, ARPG_ITEM_RELIC, ARPG_ITEM_TOME};
        static const uint8_t sch[5] = {ARPG_SCHOOL_PECHO, ARPG_SCHOOL_RAYO, ARPG_SCHOOL_EJECUCION, ARPG_SCHOOL_GLIFO, ARPG_SCHOOL_GLIFO};
        uint32_t rng = 7u;
        for (int i = 0; i < 5; i++) {
            ArpgInvItem it;
            arpg_relic_roll(&it, 1, ARPG_RAR_COMMON + i, &rng);
            it.kind = kind[i];
            it.school = sch[i];
            it.rarity = (uint8_t)(ARPG_RAR_COMMON + i);
            pickups_spawn_relic(TO_FIXED(px - 68 + i * 34), TO_FIXED(py - 30), &it);
        }
        g_relic_drop_debug = 0;
    }
    if (g_player_state.is_dead) {
        if (!s_was_dead) {
            s_was_dead = 1;
            s_deaths++;
            st->deaths = (uint8_t)s_deaths;
        }
        st->state = ENC_STATE_DEAD;
        return;
    }
    s_was_dead = 0;
    s_pool = enemies;
    s_pool_n = max_enemies;
    s_hero_px = px;
    s_hero_py = py;
    if (s_victory) return;
    st->state = ENC_STATE_PLAYING;
    if (g_enc_debug.boss_damage > 0) {          // debug: one shot of this damage at the boss, once it is there
        for (int i = 0; i < max_enemies; i++) {
            Enemy *e = &enemies[i];
            if (e->active && e->hp > 0 && (e->type == ENEMY_TYPE_ABANDERADO || e->type == ENEMY_TYPE_CAMPANERO)) {
                enemy_hit(e, g_enc_debug.boss_damage, 0, 0);
                g_enc_debug.boss_damage = 0;
                break;
            }
        }
    }

    // Rooms (salas ARPG): the hero's room, not the cleared count, decides what lives. The group of a
    // room is placed when he gets close, wakes when he steps in, and enemies left two rooms below are
    // recycled so the 24-slot pool always serves the fight around him. No gate blocks the way up.
    const RoomDef *room = room_def();
    const int nblocks = room->blocks;
    int hero_k = stage_at_py(py);
    if (hero_k < 0) hero_k = 0;
    if (hero_k >= nblocks) hero_k = nblocks - 1;
    const int cur = hero_k;
    int alive_cur = 0;
    int lo = hero_k - 1; if (lo < 0) lo = 0;
    int hi = hero_k + 2; if (hi > nblocks) hi = nblocks;

    // Recycle enemies far below the hero (rooms already behind him). Only that member goes: the rest of its group
    // keeps its own life, and its post is placed again (a fresh one) if the hero comes back to it.
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) { if (i < (int)sizeof(s_slot_member)) s_slot_member[i] = 0xFF; continue; }
        if (e->hp <= 0) continue;
        if (TO_INT(e->y) <= py + ARPG_ROOM_DESPAWN_BEHIND_PX) continue;
        int pk = e->pack;
        e->active = 0;
        if (pk >= 0 && pk < nblocks && !is_boss_stage(pk) && !s_rt[pk].cleared) {
            if (i < (int)sizeof(s_slot_member) && s_slot_member[i] != 0xFF) s_member_mask[pk] &= (uint16_t)~(1u << s_slot_member[i]);
        }
        if (i < (int)sizeof(s_slot_member)) s_slot_member[i] = 0xFF;
    }

    // Place the groups ahead (asleep). spawn_room_group respects the pool cap: with no slots the room
    // stays unspawned and retries on a later frame.
    for (int k = lo; k < hi; k++) {
        EncRuntime *rt = &s_rt[k];
#if ARPG_BOXEO || ARPG_EXVOTO_TEST || ARPG_REMATE_TEST || ARPG_OJO_TEST
        continue;               // boxeo: no room ever populates; the only enemy is the dummy of boxeo.c
#endif
#if SOUND_TEST
        if (sound_test_rooms_empty()) continue;     // prueba-sonidos: a scene (1..7) owns the enemies; scene 0 is the normal map
#endif
        if (is_boss_stage(k) ? rt->spawned : rt->cleared) continue;
        const int top = window_top(block_of_encounter(k));
        const int bottom = top + ENC_BLOCK_H;
        if (is_boss_stage(k)) {
            if (bottom < py - ARPG_ROOM_DESPAWN_BEHIND_PX) continue;      // far below: wait
            if (py > bottom + ARPG_ROOM_SPAWN_AHEAD_PX) continue;         // not close yet
        } else if (bottom < py - ARPG_ROOM_SPAWN_NEAR_PX || top > py + ARPG_ROOM_SPAWN_NEAR_PX) {
            continue;                                                     // no post of this block is near the hero
        }
        if (is_boss_stage(k)) {
            rt->spawned = 1;
            s_active_boss_k = k;
            boss_reset(boss_def_of(boss_number(k)), k);
            g_abanderado_max_mona = boss_mona_cap(boss_number(k));
#if ENC_START_CAMPANERO
            spawn_group(enemies, max_enemies, s_campanero_enemies,
                        (int)(sizeof(s_campanero_enemies) / sizeof(s_campanero_enemies[0])), 0, top, -1, k, 0);
#else
            spawn_group(enemies, max_enemies, s_boss_enemies,
                        (int)(sizeof(s_boss_enemies) / sizeof(s_boss_enemies[0])), 0, top, -1, k, 0);
#endif
        } else if (layout_of(k) ? layout_of(k)->n_members == 0 : group_of_block(k) < 0) {
            rt->spawned = rt->awake = rt->cleared = 1;     // a walk-in block: nothing to wake, nothing to remember
        } else if (s_member_mask[k] == s_member_full[k] && rt->spawned) {
            continue;                                      // every member of the group is already out
        } else {
            // Members come out as the hero gets close to their post (spawn_room_group). Those that join a room already awake
            // wake at once; the pool cap of 24 waits for the group behind to be recycled.
            if (spawn_room_group(enemies, max_enemies, k, py) > 0) {
                if (!rt->spawned) rt->awake = 0;
                rt->spawned = 1;
                if (rt->awake) wake_owner(enemies, max_enemies, k);
            }
        }
    }

    rest_update(enemies, max_enemies, px, py);
    // Wake the room the hero steps into, with at most ARPG_ROOM_MAX_AWAKE groups around him.
    for (int k = lo; k < hi; k++) {
        EncRuntime *rt = &s_rt[k];
        if (!rt->spawned || rt->awake) continue;
        const int top = window_top(block_of_encounter(k));
        const int bottom = top + ENC_BLOCK_H;
        int hurt;
        (void)alive_of(enemies, max_enemies, k, &hurt);
        if (s_rest_group_mask & (1u << k)) {
            if (!(s_rest_wake_mask & (1u << k))) continue;           // a resting group wakes by radius or hit, not by the room margin
        } else if (py >= bottom - ENC_WAKE_MARGIN && !hurt) continue;
        if (k != hero_k) {
            int awake = 0;
            for (int j = lo; j < hi; j++) if (s_rt[j].awake && !s_rt[j].cleared) awake++;
            if (awake >= ARPG_ROOM_MAX_AWAKE) continue;               // this group waits its turn
        }
        rt->awake = 1;
        if (s_room + 1 > g_arpg.deepest) g_arpg.deepest = (uint16_t)(s_room + 1);   // progress: the highest room reached
        wake_owner(enemies, max_enemies, k);
        if (st->woken < k + 1) st->woken = (uint8_t)(k + 1);
        if (is_boss_stage(k)) boss_begin(enemies, max_enemies);           // close the room, intro
        if (k == cur) st->wake_frames = 0;
    }

    for (int k = lo; k < hi; k++) {
        EncRuntime *rt = &s_rt[k];
        if (!rt->spawned) continue;
        const int is_boss = is_boss_stage(k);
        int hurt;
        int alive = alive_of(enemies, max_enemies, k, &hurt);
        if (rt->awake) {
            if (k == cur && st->wake_frames < 0xFFFF) st->wake_frames++;
            if (is_boss) {
                // The escort and the Monaguillos do not keep the fight alive: it ends when the Abanderado falls.
                if (!boss_combat_update(enemies, max_enemies)) {
                    for (int i = 0; i < max_enemies; i++)
                        if (enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == k) enemy_hit(&enemies[i], 9999, 0, 0);
                    alive = 0;
                }
            }
            if (alive == 0 && (is_boss || (hurt == 0 && s_member_mask[k] == s_member_full[k]))) {
                if (!rt->cleared) {
                    rt->cleared = 1;
                    const int first_time = !((g_arpg.boss_ever >> s_room) & 1);   // read before block_mark_dead sets it
                    block_mark_dead(k);                   // stays dead until the hero sleeps
                    clear_rewards(room, k, first_time, px, py);
                    if (k < ENC_COUNT) {
                        st->clear_frames[k] = st->wake_frames;
                        st->hp_end[k] = HP_U8(g_player_state.hp);
                        st->dones_at[k] = st->dones;
                    }
                    if (st->cleared < k + 1) st->cleared = (uint8_t)(k + 1);
                    rt->verja_opening = 1;
                    sfx_play(SND_DOOR_OPEN, -1);
                    if (is_boss) {
                        st->boss_frames = st->wake_frames;
                        boss_victory();
                    }
                }
            }
        }
        alive_cur += alive;
    }

    // Room crossings: the upper door (top line of the last block, centred) or a lateral opening asks main.c for a fade;
    // the destination room is the one the door leads to (the ficha in s_rooms).
    if (s_exit_room < 0) {
        for (int i = 0; i < room->n_doors; i++) {
            const RoomDoor *d = &room->doors[i];
            const int top = window_top(block_of_encounter(door_block(room, d)));
            int hit;
            if (d->side == DOOR_UP) {
                const int cx = room_center_x();
                const int ax = px > cx ? px - cx : cx - px;
                hit = py < top + ARPG_ROOM_DOOR_TRIGGER_PX && py > top - 4 && ax <= ARPG_ROOM_DOOR_HALF_W_PX;
            } else {
                // The only way the hero's ground point leaves the floor is through an open hole.
                const int y0 = top + door_hole_y(d);
                hit = py >= y0 + 8 && py <= y0 + ARPG_ROOM_HOLE_H_PX - 8 &&
                      (d->side == DOOR_LEFT ? px < ENC_FLOOR_X - 4 : px > ENC_FLOOR_X + ENC_FLOOR_W + 4);
            }
            if (hit) { s_exit_room = d->dest; break; }
        }
    }

    // The reja of the key: rises when the hero carries the key and comes close; without it, a toast on touching it.
    if (room->chapel_gate && !s_gate_open) {
        const int gy = window_top(block_of_encounter(room_chest_block())) + ENC_GATE_LOCAL_Y;
        if (s_gate_toast_cd) s_gate_toast_cd--;
        if (!s_gate_opening && py >= gy - 24 && py <= gy + ENC_GATE_NEAR_PX) {
            if (g_arpg.key_have && py <= gy + ENC_GATE_NEAR_PX) {
                s_gate_opening = 1;
                sfx_play(SND_DOOR_OPEN, -1);
            } else if (!g_arpg.key_have && py <= gy + 10 && !s_gate_toast_cd) {
                pickups_toast("Necesitas la llave de la capilla", 150);
                s_gate_toast_cd = 240;
            }
        }
        if (s_gate_opening) {
            s_gate_lift = (uint8_t)(s_gate_lift + 2 >= ENC_VERJA_H ? ENC_VERJA_H : s_gate_lift + 2);
            if (s_gate_lift >= ENC_VERJA_H) {
                s_gate_opening = 0;
                s_gate_open = 1;
                strip_collision_fill_win(ENC_FLOOR_X, gy - ENC_BARRIER_H / 2, ENC_FLOOR_W, ENC_BARRIER_H, 0);
                nav_refresh_begin(px, py);
            }
        }
    }

    // The chest of the room and its altar.
    if (room->chest) {
        const int ck = room_chest_block();
        const int cx = room_center_x(), cy = room_chest_y();
        const int dx = px - cx, dy = py - cy;
        if (!s_rt[ck].chest_open && dx * dx + GROUND_DY2(dy) <= ARPG_ROOM_CHEST_REACH_PX * ARPG_ROOM_CHEST_REACH_PX) {
            s_rt[ck].chest_open = 1;
            g_arpg.chests_open |= (uint16_t)(1u << s_room);     // never refilled
            sfx_play(SND_CHEST_OPEN, cx);
            const fixed fx = TO_FIXED(cx), fy = TO_FIXED(cy);
            arpg_add_xp(ARPG_ROOM_CHEST_XP + room->level);
            pickups_spawn(PICKUP_KIND_HEALTH, fx - TO_FIXED(8), fy);
            pickups_spawn(PICKUP_KIND_MANA, fx + TO_FIXED(8), fy);
            uint32_t chest_rng = (uint32_t)(s_room + 1) * 2654435761u ^ (uint32_t)(px * 73856093 ^ py * 19349663);
            ArpgInvItem chest_relic;
            arpg_relic_roll(&chest_relic, room->level, room->prize_min_rar ? room->prize_min_rar : ARPG_RAR_UNCOMMON, &chest_rng);
            pickups_spawn_relic(fx, fy + TO_FIXED(6), &chest_relic);
            if (room->drops_key && !arpg_inv_has_tome(ARPG_SCHOOL_GLIFO)) {   // Capilla del parroco: the Glifo tome
                ArpgInvItem tome;
                arpg_inv_make_tome(&tome, ARPG_SCHOOL_GLIFO);
                pickups_spawn_relic(fx + TO_FIXED(16), fy + TO_FIXED(6), &tome);
            }
        }
    }
    if (room->altar) {
        const int cx = room_altar_x(), cy = room_altar_y();
        const int dx = px - cx, dy = py - cy;
        if (dx * dx + GROUND_DY2(dy) <= ARPG_ROOM_ALTAR_REACH_PX * ARPG_ROOM_ALTAR_REACH_PX) {
            s_rt[0].altar_touched = 1;
            g_arpg.altars_lo |= (1u << s_room);
            if (g_arpg.last_altar != s_room) {          // the next run enters here; saved at once
                g_arpg.last_altar = (uint8_t)s_room;
                arpg_progress_save();
            }
        }
    }

    // Stats for the scenarios.
    for (int k = 0; k < ENC_STAGES; k++) {
        if (s_rt[k].verja_opening && !s_rt[k].barrier_open) {
            if (s_rt[k].verja_lift < ENC_VERJA_H) s_rt[k].verja_lift++;
            if (s_rt[k].verja_lift >= ENC_VERJA_H) {
                s_rt[k].verja_opening = 0;
                open_barrier(k, px, py);
            }
        }
        if (s_rt[k].back_closed && !s_rt[k].cleared) {
            if (s_rt[k].back_lift > 4) s_rt[k].back_lift -= 4;
            else s_rt[k].back_lift = 0;
        } else if (s_rt[k].back_lift < ENC_VERJA_H) {
            s_rt[k].back_lift++;
        }
    }
    st->current = (uint8_t)cur;                // the block of the room the hero is in (blocks are not gated by clearing)
    st->corridor_enemies = (uint8_t)s_room;    // and the room itself (0..11)
    if (!is_boss_stage(cur)) {
        st->plant = s_plant[cur];
        st->tier = s_tier[cur];
    } else {
        st->plant = 0xFF;
        st->tier = 3;
    }
    st->alive = (uint8_t)(alive_cur > 255 ? 255 : alive_cur);
    int hurt_dummy;
    st->boss_alive = (uint8_t)(s_rt[s_active_boss_k].spawned && !s_rt[s_active_boss_k].cleared &&
                               alive_of(enemies, max_enemies, s_active_boss_k, &hurt_dummy) > 0);

    {   // boss diagnostics
        int boss_hp = 0, mona = 0, blocked = 0;
        for (int i = 0; i < max_enemies; i++) {
            const Enemy *e = &enemies[i];
            if (!e->active || e->hp <= 0) continue;
            if (e->state == ENEMY_STATE_DORMANT && !position_is_free(e->x, e->y)) blocked++;
            if (e->type == ENEMY_TYPE_ABANDERADO || e->type == ENEMY_TYPE_CAMPANERO) boss_hp = e->hp;
            else if (e->type == ENEMY_TYPE_MONAGUILLO) mona++;
        }
        st->boss_hp_now = (uint16_t)boss_hp;
        st->blocked_asleep = (uint8_t)blocked;
        st->mona_alive = (uint8_t)(mona > 255 ? 255 : mona);
        if (st->mona_alive > st->mona_alive_max) st->mona_alive_max = st->mona_alive;
        if (boss_hp > 0 && s_rt[s_active_boss_k].awake && st->current == s_active_boss_k && st->wake_frames % 300 == 0 &&
            st->wake_frames / 300 < 16)
            st->boss_hp[st->wake_frames / 300] = (uint16_t)boss_hp;
    }

    st->dbg_relic_x = 0;                       // no relicarios: nothing for the bot to aim at
    st->dbg_relic_y = 0;
    if (s_fx_timer > 0) s_fx_timer--;
}

// ---------------------------------------------------------------------------
// Targets for the ray: none (no relicarios in the dungeon).
// ---------------------------------------------------------------------------

int enc_relic_target(int *x, int *y) { (void)x; (void)y; return 0; }
void enc_relic_hit(int damage) { (void)damage; }

// DESIGN.md 6.13.6: every enemy of an encounter that has not woken takes no damage (the ray goes through it), so the
// corridor cannot hurt the next room before the hero steps in, whatever state the sleeper is in.
int enc_untouchable(const Enemy *e) {
    int k = e->pack;
    // A resting group (crawling, sweeping...) is hittable: the hit wakes it (rest_update), so the ray reaches it from afar.
    return k >= 0 && k < ENC_STAGES && s_rt[k].spawned && !s_rt[k].awake && !(s_rest_group_mask & (1u << k));
}

void enc_note_beam_hit(const Enemy *e) {
    if (e->type == ENEMY_TYPE_ABANDERADO || e->type == ENEMY_TYPE_CAMPANERO) {
        if (g_enc_stats.boss_hits < 0xFFFF) g_enc_stats.boss_hits++;
    } else if (e->type == ENEMY_TYPE_MONAGUILLO) {
        if (g_enc_stats.mona_hits < 0xFFFF) g_enc_stats.mona_hits++;
        if (e->hp <= 0 && g_enc_stats.mona_kills < 0xFFFF) g_enc_stats.mona_kills++;
    }
}

void enc_player_hit(void) {
    int cur = g_enc_stats.current;
    if (!is_boss_stage(cur) && cur < ENC_COUNT && g_enc_stats.hits[cur] < 255) g_enc_stats.hits[cur]++;
    if (g_enc_stats.hits_total < 0xFFFF) g_enc_stats.hits_total++;
}

// ---------------------------------------------------------------------------
// Frame bookkeeping of the stats mailbox: clock, result and the capture triggers of the bot scenarios.
// Runs every frame from the main loop, also after victory or death (enc_update stops then).
// ---------------------------------------------------------------------------

#define ENC_CAP_PERIOD 600          // a capture every 600 frames
#define ENC_CAP_WAKE_DELAY 45       // and this long after an encounter wakes
#define ENC_CAP_CLEAR_DELAY 30      // and after one is cleared
#define ENC_ACT_TIMEOUT 40000       // frames after which the act counts as timed out (the base hero needs ~30000 to reach the boss)
#define ENC_CAP_QUEUE 6

static uint32_t s_cap_due[ENC_CAP_QUEUE];
static uint8_t s_cap_n;
static uint8_t s_seen_woken, s_seen_cleared;
static uint32_t s_end_clock;

static void cap_later(uint32_t clock, int delay) {
    if (s_cap_n < ENC_CAP_QUEUE) s_cap_due[s_cap_n++] = clock + (uint32_t)delay;
}

static void cap_bump(void) {
    if (g_enc_stats.cap_seq < 255) g_enc_stats.cap_seq++;
}

void enc_stats_frame(void) {
    volatile EncStats *st = &g_enc_stats;
    st->clock++;
    st->boss_state = (uint8_t)boss_state();
    st->boss_phase = (uint8_t)boss_phase();
    st->hp = HP_U8(g_player_state.hp);
    st->max_hp = HP_U8(g_player_state.max_hp);
    if (st->hp_min == 0 || (st->hp < st->hp_min && st->result == 0)) st->hp_min = st->hp ? st->hp : st->hp_min;
    if (st->result == 0) {
        if (st->state == ENC_STATE_VICTORY) st->result = 1;
        else if (st->state == ENC_STATE_DEAD || g_player_state.is_dead) { st->result = 2; st->death_enc = st->current; }
        else if (st->act_frames >= ENC_ACT_TIMEOUT) st->result = 3;
        else st->act_frames++;
        if (st->result != 0) s_end_clock = st->clock;
    }
    if (st->woken != s_seen_woken) { s_seen_woken = st->woken; cap_later(st->clock, ENC_CAP_WAKE_DELAY); }
    if (st->cleared != s_seen_cleared) { s_seen_cleared = st->cleared; cap_later(st->clock, ENC_CAP_CLEAR_DELAY); }
    if (st->result == 0 && (st->clock % ENC_CAP_PERIOD) == 0) cap_bump();
    for (int i = 0; i < s_cap_n; ) {
        if (st->clock >= s_cap_due[i]) {
            cap_bump();
            s_cap_due[i] = s_cap_due[--s_cap_n];
        } else {
            i++;
        }
    }
    if (st->result != 0) {
        if (st->clock - s_end_clock == 60) cap_bump();         // the end of the act
        if (st->clock - s_end_clock > 90) st->cap_seq = 255;   // the scenario's remaining steps pass at once
    }
}

int enc_victory(void) { return s_victory; }

int enc_end_demo_take(void) {
    if (!s_end_demo_pending || boss_state() != BOSS_REST) return 0;
    s_end_demo_pending = 0;
    return 1;
}

int enc_current_encounter(void) { return room_def()->level; }

// ---------------------------------------------------------------------------
// Painter: flat provisional obstacles, drawn on the floor under the actors.
// ---------------------------------------------------------------------------

#define COL_SACOS     (RGB15(14, 10, 6) | BIT(15))     // muted brown
#define COL_SACOS_DK  (RGB15(8, 6, 4) | BIT(15))
#define COL_ALAMBRE   (RGB15(6, 6, 7) | BIT(15))       // dark grey (opaque, like the sacos)
#define COL_ALAMBRE_LT (RGB15(15, 14, 13) | BIT(15))   // lighter barbs and top strand
#define COL_BARRERA   (RGB15(13, 5, 6) | BIT(15))      // desaturated garnet
#define COL_BARRERA_DK (RGB15(7, 3, 4) | BIT(15))
#define COL_GOLD      (RGB15(22, 18, 8) | BIT(15))

static void fill_rect(uint16_t *buffer, int cam_x, int cam_y, const EncRect *r, int top) {
    int x0 = r->x - cam_x, x1 = x0 + r->w;
    int y0 = top + r->y - cam_y, y1 = y0 + r->h;
    uint16_t base, dark;
    if (r->kind == ENC_R_SACOS) { base = COL_SACOS; dark = COL_SACOS_DK; }
    else if (r->kind == ENC_R_ALAMBRE) { base = COL_ALAMBRE; dark = COL_ALAMBRE; }
    else { base = COL_BARRERA; dark = COL_BARRERA_DK; }
    if (y1 <= 0 || y0 >= SCREEN_H || x1 <= 0 || x0 >= SCREEN_W) return;
    int cx0 = x0 < 0 ? 0 : x0, cx1 = x1 > SCREEN_W ? SCREEN_W : x1;
    for (int y = y0; y < y1; y++) {
        if (y < 0 || y >= SCREEN_H) continue;
        uint16_t *row = buffer + y * SCREEN_W;
        const int edge = (y >= y1 - 2);
        if (r->kind == ENC_R_ALAMBRE) {
            // Barbed wire, opaque: a dark band with a light strand on top and light barbs every 8 px.
            const int ry = y - y0;
            for (int x = cx0; x < cx1; x++) {
                const int wx = x + cam_x;
                uint16_t c = base;
                if (ry == 0 || ry == 1) c = COL_ALAMBRE_LT;                       // top strand
                else if (((wx + ry * 2) & 7) < 2) c = COL_ALAMBRE_LT;   // barbs, leaning
                else if (edge) c = dark;
                row[x] = c;
            }
        } else {
            uint16_t c = edge ? dark : base;
            for (int x = cx0; x < cx1; x++) row[x] = c;
        }
        dirty_row(y, cx0, cx1);
    }
}

void enc_draw_ground(uint16_t *buffer, int cam_x, int cam_y) {
    // Encounter and boss blocks that reach this screen.
    for (int k = 0; k < room_def()->blocks; k++) {
        const int block = block_of_encounter(k);
        const int top = window_top(block);
        if (top + ENC_BLOCK_H <= cam_y || top >= cam_y + SCREEN_H) continue;
        // Every floor has its top barrier painted here (there are no corridors, so the kit draws no rastrillo).
        EncRect rects[ENC_MAX_RECTS];
        int n = enc_block_rects(block, rects, ENC_MAX_RECTS);
        for (int i = 0; i < n; i++) {
            if (rects[i].kind != ENC_R_BARRERA) continue;
            if (rects[i].y == 0) fill_rect(buffer, cam_x, cam_y, &rects[i], top);
        }
    }
    GroundTarget g = { buffer, cam_x, cam_y };
    if (s_fx_timer > 0)
        gfx_ground_ring(&g, s_fx_x, s_fx_y, 26 - s_fx_timer, RGB15(20, 17, 12), 0);
}

static int dynamic_relic_active(int *out_x, int *out_y, int *out_is_altar) {
    static const int boss_k[3] = { 4, 9, 14 };
    for (int b = 0; b < 3; b++) {
        int rx, ry;
        if (boss_relic_pos(boss_k[b], &rx, &ry)) {
            *out_x = rx; *out_y = ry; *out_is_altar = 0;
            return 1;
        }
    }
    int ax, ay;
    if (altar_pos(&ax, &ay)) {
        *out_x = ax; *out_y = ay; *out_is_altar = 1;
        return 1;
    }
    return 0;
}

int enc_dynamic_relic_item(int cam_x, int cam_y, int *out_depth) {
    int rx, ry, is_altar;
    if (!dynamic_relic_active(&rx, &ry, &is_altar)) return 0;
    int sx = rx - cam_x - ENC_RELIC_SPR_W / 2;
    int sy = ry - cam_y - ENC_RELIC_SPR_H + 6;
    if (sx + ENC_RELIC_SPR_W <= 0 || sx >= SCREEN_W || sy + ENC_RELIC_SPR_H <= 0 || sy >= SCREEN_H) return 0;
    if (out_depth) *out_depth = ry;
    return 1;
}

void enc_dynamic_relic_draw(uint16_t *buffer, int cam_x, int cam_y, int depth) {
    int rx, ry, is_altar;
    if (!dynamic_relic_active(&rx, &ry, &is_altar)) return;
    const uint16_t *src = is_altar ? s_altar_px : s_golden_relic_px;
    int wx0 = rx - ENC_RELIC_SPR_W / 2;
    int wy0 = ry - ENC_RELIC_SPR_H + 6;
    int sx0 = wx0 - cam_x;
    int sy0 = wy0 - cam_y;
    for (int j = 0; j < ENC_RELIC_SPR_H; j++) {
        int sy = sy0 + j;
        if (sy < 0 || sy >= SCREEN_H) continue;
        int wy = wy0 + j;
        uint16_t *row = buffer + sy * SCREEN_W;
        const uint16_t *srow = src + j * ENC_RELIC_SPR_W;
        int min_x = SCREEN_W, max_x = -1;
        for (int i = 0; i < ENC_RELIC_SPR_W; i++) {
            uint16_t c = srow[i];
            if (!c) continue;
            int sx = sx0 + i;
            if (sx < 0 || sx >= SCREEN_W) continue;
            if (world_pixel_hidden(wx0 + i, wy, depth)) continue;
            // 1 = cast shadow of the lit art: halve what is already on screen (same darkening as apply_shadow_fast).
            if (c == 1) {  // the buffer is empty (0) over the floor: read the floor, like draw_shadow_mask
                const uint16_t under = row[sx] ? row[sx] : world_floor_color_at(wx0 + i, wy);
                row[sx] = (uint16_t)(((under & 0x7BDE) >> 1) | BIT(15));
            } else {
                row[sx] = c;
            }
            if (sx < min_x) min_x = sx;
            if (sx > max_x) max_x = sx;
        }
        if (max_x >= min_x) dirty_row(sy, min_x, max_x + 1);
    }
}

// ---------------------------------------------------------------------------
// Room fixtures: chests (closed and open) and travel altars, painted as dynamic sprites over the
// floor so their state can change without repainting the baked tilemap. Their art is the real props
// of assets/environment/cathedral/props/render, baked into include/enc_room_gfx.h.
// ---------------------------------------------------------------------------
#define ENC_FIXTURE_MAX 12
enum { ENC_FIX_CHEST = 0, ENC_FIX_ALTAR = 1 };
typedef struct { int16_t x, y; uint8_t k, kind, sprite; } EncFixture;
static EncFixture s_fixtures[ENC_FIXTURE_MAX];
static int s_fixture_n;

int enc_dynamic_fixture_count(int cam_x, int cam_y) {
    (void)cam_x;
    const RoomDef *room = room_def();
    // The chest blocks the hero (and the enemies) on its ground footprint, on or off screen.
    collision_extra_begin();
    if (room->chest) {
        const int cx = room_center_x(), cy = room_chest_y();
        collision_extra_add(cx - 8, cy - 4, cx + 8, cy + 2);
    }
    s_fixture_n = 0;
    if (room->chest) {
        const int ck = room_chest_block();
        const int top = window_top(block_of_encounter(ck));
        if (top + ENC_BLOCK_H > cam_y && top < cam_y + SCREEN_H && s_fixture_n < ENC_FIXTURE_MAX) {
            s_fixtures[s_fixture_n].x = (int16_t)room_center_x();
            s_fixtures[s_fixture_n].y = (int16_t)room_chest_y();
            s_fixtures[s_fixture_n].k = (uint8_t)ck;
            s_fixtures[s_fixture_n].kind = ENC_FIX_CHEST;
            // The open chest stays in the room: the loot is out, the furniture is not gone.
            s_fixtures[s_fixture_n].sprite = s_rt[ck].chest_open ? ENC_SPR_COFRE_ABIERTO : ENC_SPR_COFRE_CERRADO;
            s_fixture_n++;
        }
    }
    if (room->altar) {
        const int top = window_top(block_of_encounter(0));
        if (top + ENC_BLOCK_H > cam_y && top < cam_y + SCREEN_H && s_fixture_n < ENC_FIXTURE_MAX) {
            s_fixtures[s_fixture_n].x = (int16_t)room_altar_x();
            s_fixtures[s_fixture_n].y = (int16_t)room_altar_y();
            s_fixtures[s_fixture_n].k = 0;
            s_fixtures[s_fixture_n].kind = ENC_FIX_ALTAR;
            s_fixtures[s_fixture_n].sprite = ENC_SPR_ALTAR;
            s_fixture_n++;
        }
    }
    return s_fixture_n;
}

// Lit art of the room (nitro:/arpg_luz/<luz>_fix.bin, source/room_light.c): `meta` is 3 x {left, w, h, anchor_y}.
// Re-points the three fixture sprites at consecutive spans of the shared pixel buffer and returns it, or NULL if
// the set does not fit. The caller then reads the pixels straight into it.
uint16_t *enc_room_gfx_begin(const int16_t meta[3][4]) {
    int total = 0;
    for (int i = 0; i < 3; i++) total += (int)(uint16_t)meta[i][1] * (uint16_t)meta[i][2];
    if (total <= 0 || total > ENC_ROOM_PX_CAP) return NULL;
    int off = 0;
    for (int i = 0; i < 3; i++) {
        EncRoomSprite *sp = &s_enc_room_sprites[i];
        sp->left = meta[i][0];
        sp->w = (uint16_t)meta[i][1];
        sp->h = (uint16_t)meta[i][2];
        sp->anchor_y = (uint16_t)meta[i][3];
        sp->pixels = s_enc_room_px + off;
        off += sp->w * sp->h;
    }
    return s_enc_room_px;
}

// Top-left of a fixture sprite in world px: its ground anchor lands on the fixture's Y.
static void fixture_origin(const EncFixture *f, int *out_x, int *out_y) {
    const EncRoomSprite *s = &s_enc_room_sprites[f->sprite];
    *out_x = f->x + s->left;
    *out_y = f->y - s->anchor_y;
}

int enc_dynamic_fixture_item(int index, int cam_x, int cam_y, int *out_depth) {
    if (index < 0 || index >= s_fixture_n) return 0;
    const EncFixture *f = &s_fixtures[index];
    const EncRoomSprite *s = &s_enc_room_sprites[f->sprite];
    int wx0, wy0;
    fixture_origin(f, &wx0, &wy0);
    if (wx0 + s->w - cam_x <= 0 || wx0 - cam_x >= SCREEN_W ||
        wy0 + s->h - cam_y <= 0 || wy0 - cam_y >= SCREEN_H) return 0;
    if (out_depth) *out_depth = f->y;
    return 1;
}

void enc_dynamic_fixture_draw(int index, uint16_t *buffer, int cam_x, int cam_y, int depth) {
    if (index < 0 || index >= s_fixture_n) return;
    const EncFixture *f = &s_fixtures[index];
    const EncRoomSprite *s = &s_enc_room_sprites[f->sprite];
    int wx0, wy0;
    fixture_origin(f, &wx0, &wy0);
    const int sx0 = wx0 - cam_x, sy0 = wy0 - cam_y;
    for (int j = 0; j < s->h; j++) {
        int sy = sy0 + j;
        if (sy < 0 || sy >= SCREEN_H) continue;
        const int wy = wy0 + j;
        uint16_t *row = buffer + sy * SCREEN_W;
        const uint16_t *srow = s->pixels + j * s->w;
        int min_x = SCREEN_W, max_x = -1;
        for (int i = 0; i < s->w; i++) {
            uint16_t c = srow[i];
            if (!c) continue;
            int sx = sx0 + i;
            if (sx < 0 || sx >= SCREEN_W) continue;
            if (world_pixel_hidden(wx0 + i, wy, depth)) continue;
            // 1 = cast shadow of the lit art: halve what is already on screen (same darkening as apply_shadow_fast).
            if (c == 1) {  // the buffer is empty (0) over the floor: read the floor, like draw_shadow_mask
                const uint16_t under = row[sx] ? row[sx] : world_floor_color_at(wx0 + i, wy);
                row[sx] = (uint16_t)(((under & 0x7BDE) >> 1) | BIT(15));
            } else {
                row[sx] = c;
            }
            if (sx < min_x) min_x = sx;
            if (sx > max_x) max_x = sx;
        }
        if (max_x >= min_x) dirty_row(sy, min_x, max_x + 1);
    }
    // Altar touched: a small muted flame above it (the cheap "it is lit" mark).
    if (f->kind == ENC_FIX_ALTAR && s_rt[f->k].altar_touched) {
        static const uint16_t flame = RGB15(22, 16, 6) | BIT(15);
        static const uint16_t tip = RGB15(28, 22, 10) | BIT(15);
        const int cx = f->x - cam_x;
        const int top = wy0 - cam_y - 2;
        for (int j = 0; j < 9; j++) {
            const int sy = top + j;
            if (sy < 0 || sy >= SCREEN_H) continue;
            const int half = (9 - j) / 3;
            uint16_t *row = buffer + sy * SCREEN_W;
            for (int i = -half; i <= half; i++) {
                const int sx = cx + i;
                if (sx < 0 || sx >= SCREEN_W) continue;
                row[sx] = j < 3 ? tip : flame;
            }
            if (cx - half < cx + half + 1) dirty_row(sy, cx - half, cx + half + 1);
        }
    }
}

void enc_verja_draw(int sub, int cam_x, int cam_y) {
#if HW_SHADOWS
    if (room_def()->chapel_gate && s_gate_lift < ENC_VERJA_H) {
        const int sy = window_top(block_of_encounter(room_chest_block())) + ENC_GATE_LOCAL_Y - ENC_VERJA_H - cam_y;
        if (!(sub == 0 && sy + ENC_VERJA_H > 136) && sy + ENC_VERJA_H > 0 && sy < 192)
            hwshadow_add_verja(sub, ENC_FLOOR_X - cam_x, sy, s_gate_lift, 0);
    }
    for (int k = 0; k < ENC_STAGES; k++) {
        const int block_top = window_top(block_of_encounter(k));
        if (s_rt[k].verja_lift < ENC_VERJA_H) {
            const int sy = block_top - ENC_VERJA_H - cam_y;
            if (sy + ENC_VERJA_H > 0 && sy < 192)
                hwshadow_add_verja(sub, ENC_FLOOR_X - cam_x, sy, s_rt[k].verja_lift, 0);
        }
        if (s_rt[k].back_lift < ENC_VERJA_H) {
            const int sy = block_top + ENC_BLOCK_H - ENC_VERJA_H - cam_y;
            // sub 0 is the bottom screen: a hardware sprite there would cover the HUD band (rows from 136 down).
            if (sub == 0 && sy + ENC_VERJA_H > 136) continue;
            if (sy + ENC_VERJA_H > 0 && sy < 192)
                hwshadow_add_verja(sub, ENC_FLOOR_X - cam_x, sy, s_rt[k].back_lift, 1);
        }
    }
#else
    (void)sub; (void)cam_x; (void)cam_y;
#endif
}

#endif // ENCOUNTERS_PROTO

#if ARPG_BOT
void arpg_bot_room(ArpgBotRoom *o) {
    const RoomDef *r = room_def();
    memset(o, 0, sizeof(*o));
    o->room = s_room;
    o->level = r->level;
    o->nblocks = r->blocks;
    o->up_dest = -1;
    int hk = stage_at_py(s_hero_py);
    o->hero_block = hk < 0 ? 0 : hk >= r->blocks ? r->blocks - 1 : hk;
    for (int i = 0; i < r->n_doors; i++) {
        const RoomDoor *d = &r->doors[i];
        if (d->side != DOOR_UP) continue;
        o->has_up = 1;
        o->up_dest = d->dest;
        o->up_x = room_center_x();
        o->up_y = window_top(block_of_encounter(door_block(r, d))) + 8;
    }
    if (r->chest) {
        o->chest = 1;
        o->chest_open = s_rt[room_chest_block()].chest_open;
        o->chest_x = room_center_x();
        o->chest_y = room_chest_y();
    }
    if (r->altar) {
        o->altar = 1;
        o->altar_x = room_altar_x();
        o->altar_y = room_altar_y();
    }
    o->foot_y = window_top(block_of_encounter(0)) + ENC_BLOCK_H;
    o->top_y = window_top(block_of_encounter(r->blocks - 1));
    for (int i = 0; i < r->n_doors && o->n_side < 3; i++) {
        const RoomDoor *d = &r->doors[i];
        if (d->side == DOOR_UP) continue;
        const int y0 = window_top(block_of_encounter(door_block(r, d))) + door_hole_y(d);
        const int k = o->n_side++;
        o->side_left[k] = d->side == DOOR_LEFT;
        o->side_y0[k] = y0;
        o->side_y1[k] = y0 + ARPG_ROOM_HOLE_H_PX;
        o->side_edge_x[k] = d->side == DOOR_LEFT ? ENC_FLOOR_X : ENC_FLOOR_X + ENC_FLOOR_W;     // the floor line: the door fires 4 px past it
    }
    for (int i = 0; i < r->n_doors && o->n_door < 4; i++) {
        const RoomDoor *d = &r->doors[i];
        const int k = o->n_door++;
        o->door_dest[k] = d->dest;
        if (d->side == DOOR_UP) {
            o->door_side_k[k] = -1;
            o->door_gx[k] = room_center_x();
            o->door_gy[k] = window_top(block_of_encounter(door_block(r, d))) + 8;
        } else {
            int sk = 0;
            for (int j = 0; j < i; j++) if (r->doors[j].side != DOOR_UP) sk++;
            o->door_side_k[k] = sk;
            o->door_gx[k] = d->side == DOOR_LEFT ? 140 : ENC_FLOOR_X + ENC_FLOOR_W + 12;
            o->door_gy[k] = window_top(block_of_encounter(door_block(r, d))) + door_hole_y(d) + ARPG_ROOM_HOLE_H_PX / 2;
        }
    }
}
#endif
