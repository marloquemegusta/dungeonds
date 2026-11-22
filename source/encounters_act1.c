#include "encounters_act1.h"
#include "lab_tuning.h"

// Translation unit never empty (ISO C) when ENCOUNTERS_PROTO=0.
typedef int encounters_act1_translation_unit_not_empty;

#if ENCOUNTERS_PROTO

#include <string.h>
#include "encounters.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "boss.h"

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

#include "encounters_act1_tables.h"
#include "encounters_act1_hp.h"

#if ENC_BOT
volatile EncDebug g_enc_debug = { .auto_pick = 2, .seed = 1,
                                  .bot_reaction = 15, .bot_aim_err = 6, .bot_ojo_delay = 20 };   // human-like bot, cards at random, seed 1
#elif ENC_START_BOSS
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

#define ENC_STAGES 100                      // floors of the dungeon, room after room (no corridors); every fifth one is a boss
#define ENC_FIRST_BOSS 4                    // floor 5 (0-based stage 4): the first boss
#define ENC_BOSS (ENC_STAGES - 1)           // last stage (floor 100, a boss)
#define ENC_FIRST_BLOCK 3                   // block of the first floor; blocks above 3 are the cleared start

static int is_boss_stage(int k) { return (k % 5) == 4; }
static int boss_number(int k) { return k / 5; }                 // 0 for floor 5, 1 for floor 10, ...
static int tier_of_stage(int k) { return k < 5 ? 0 : k < 10 ? 1 : 2; }
static int boss_mona_cap(int n) { return n == 0 ? 8 : n == 1 ? 12 : 16; }   // live Monaguillos of each boss

static int s_first_block = ENC_FIRST_BLOCK;   // moves down the strip with start_boss so the boss room is the first block
static int s_active_boss_k = ENC_FIRST_BOSS;  // stage index of the active boss fight
static uint32_t s_seed;
static uint8_t s_plant[ENC_STAGES];           // plant of each floor (boss floors ignore it)
static uint8_t s_mirror[ENC_STAGES];
static uint8_t s_tier[ENC_STAGES];            // tier of each floor (tier_of_stage; the debug force applies to floor 1)

typedef struct {
    uint8_t spawned, awake, cleared, wave2_done, barrier_open, back_closed, verja_opening, verja_lift, back_lift;
    // Rooms (salas ARPG). Offsets 9 and 10 are read by scenarios/salas_captura.json (sizeof is 11).
    uint8_t chest_open, altar_touched;
} EncRuntime;
static EncRuntime s_rt[ENC_STAGES];
static int s_exit_room = -1;                  // crossing requested by enc_update(), consumed by main.c
static int s_victory;                         // never set: the dungeon has no victory (enc_victory stays for the HUD)
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
// Floor 15 and the bosses after it: the same sheet as an elite, with 2 Ojos and 2 Cireneos per phase.
static const BossEscortDef s_elite_escort[] = {
    { ENEMY_TYPE_SHOOTER, 2, 240, { 40, 168 } },
    { ENEMY_TYPE_CHARGER, 2, 240, { 72, 136 } },
};
static const BossDef s_elite_def = {
    .enemy_type = ENEMY_TYPE_ABANDERADO,
    .name = "EL ABANDERADO",
    .title = "Élite",
    .line_intro = "«Mientras el asta siga en pie,\nnadie se retira.»",
    .line_defeat = "«El asta ha caído.»",
    .sfx_intro = SND_ABANDERADO_INTRO,
    .sfx_defeat = SND_ABANDERADO_DEFEAT,
    .voice_intro_frames = SFX_VOICE_VBLANKS_ABANDERADO_INTRO,
    .voice_defeat_frames = SFX_VOICE_VBLANKS_ABANDERADO_DEFEAT,
    .n_phases = 3,
    .phase_pct = { 100, 66, 33 },
    .n_escort = { 2, 2, 2 },
    .escort = { s_elite_escort, s_elite_escort, s_elite_escort },
};
static const BossDef *boss_def_of(int n) { return n >= 2 ? &s_elite_def : &s_abanderado_def; }

int enc_start_up_px(void) { return g_enc_debug.start_boss ? 156 : 4 * g_enc_debug.start_up4; }   // hero ~100 px under the boss room's bottom edge

void enc_init(uint32_t seed) {
    s_seed = seed ? seed : 1u;
    // Lives of the act (DESIGN.md 6.13.6): two beams for an Exvoto, three for the Ojo and the Cireneo.
    g_enemy_tuning[ENEMY_TYPE_EXVOTO].max_hp = ENC_HP_EXVOTO;
    g_enemy_tuning[ENEMY_TYPE_MONAGUILLO].max_hp = ENC_HP_MONAGUILLO;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].max_hp = ENC_HP_CIRENEO;
    g_enemy_tuning[ENEMY_TYPE_SHOOTER].max_hp = ENC_HP_OJO;
    g_enemy_tuning[ENEMY_TYPE_ABANDERADO].max_hp = g_enc_debug.boss_hp ? g_enc_debug.boss_hp : ENC_HP_ABANDERADO;
    // The Cireneo of v2: it chases below the hero's pace so the player can break away and charge the beam,
    // telegraphs 0.75 s and then charges very fast.
    g_enemy_tuning[ENEMY_TYPE_CHARGER].speed = 105;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].telegraph_duration = 45;
    g_enemy_tuning[ENEMY_TYPE_CHARGER].charge_speed = 1000;
    // Plants: a hashed sequence over the floors, never the same plant twice in a row (bosses do not count).
    int prev_plant = -1;
    for (int k = 0; k < ENC_STAGES; k++) {
        s_tier[k] = (uint8_t)tier_of_stage(k);
        s_mirror[k] = (uint8_t)(pick_hash(k, 99) & 1u);
        s_plant[k] = 0;
        if (is_boss_stage(k)) continue;
        const int range = ENC_PLANT_COUNT - (prev_plant >= 0 ? 1 : 0);
        int p = (int)(pick_hash(k, 7) % (uint32_t)range);
        if (prev_plant >= 0 && p >= prev_plant) p++;          // skips the plant of the floor before
        s_plant[k] = (uint8_t)p;
        prev_plant = p;
    }
    if (g_enc_debug.force_plant > 0 && g_enc_debug.force_plant <= ENC_PLANT_COUNT) {   // debug: the first encounter on demand
        s_plant[0] = (uint8_t)(g_enc_debug.force_plant - 1);
        s_mirror[0] = 0;
        if (g_enc_debug.force_tier > 0 && g_enc_debug.force_tier <= 3) s_tier[0] = (uint8_t)(g_enc_debug.force_tier - 1);
    }
    memset(s_rt, 0, sizeof(s_rt));
    // Rooms have no gates (salas ARPG): both lifts start raised, so no rastrillo is drawn anywhere.
    for (int i = 0; i < ENC_STAGES; i++) { s_rt[i].back_lift = ENC_VERJA_H; s_rt[i].verja_lift = ENC_VERJA_H; }
    s_exit_room = -1;
    s_first_block = ENC_FIRST_BLOCK;
    if (g_enc_debug.start_boss) {              // debug: the act starts at the first boss (stage 5), stages 1..4 already won
        s_first_block += ENC_FIRST_BOSS;
        for (int i = 0; i < ENC_FIRST_BOSS; i++) {
            s_rt[i].spawned = s_rt[i].awake = s_rt[i].cleared = s_rt[i].wave2_done = s_rt[i].barrier_open = 1;
            s_rt[i].verja_lift = ENC_VERJA_H;
        }
    }
    g_enc_debug.start_dones = 0;       // a new act never inherits a "apply Dones now" debug request
    s_victory = 0;
    s_boss_locked = 0;
    s_active_boss_k = ENC_FIRST_BOSS;
    s_was_dead = 0;
    s_fx_timer = 0;
    {
        static const BossHooks hooks = { boss_spawn_escort, boss_set_barriers };
        boss_set_hooks(&hooks);
        boss_reset(&s_abanderado_def, ENC_FIRST_BOSS);
    }
    g_abanderado_max_mona = boss_mona_cap(0);
    volatile EncStats *st = &g_enc_stats;
    uint8_t deaths = (uint8_t)s_deaths;
    memset((void *)st, 0, sizeof(EncStats));
    st->deaths = deaths;
    if (g_enc_debug.start_boss) st->cleared = ENC_FIRST_BOSS;
    for (int i = 0; i < ENC_COUNT; i++) st->plants[i] = s_plant[i];
    st->plant = s_plant[0];
    st->tier = s_tier[0];
    for (int i = 0; i < ENC_COUNT; i++) st->tiers[i] = s_tier[i];
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
    int32_t k = s_first_block - block;          // one floor per block: each room sits right above the previous one
    if (k < 0 || k >= ENC_STAGES) return;      // the cleared start, and the strip above the last floor
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

int enc_block_pieces(int32_t block, EncPiecePlan *out, int max) {
    EncBlock b;
    enc_block_info(block, &b);
    const EncPieceDef *defs = 0;
    int n = 0;
    if (b.kind == ENC_BLOCK_ENCOUNTER) {
        defs = s_plants[b.plant].pieces;
        n = s_plants[b.plant].n_pieces;
    } else if (b.kind == ENC_BLOCK_CORRIDOR) {
        defs = s_corridor_pieces;
        n = (int)(sizeof(s_corridor_pieces) / sizeof(s_corridor_pieces[0]));
    }
    int m = 0;
    // The upper door: one piece on the top line of every room, centred on the nave axis. The door art
    // is 64 px wide (shadow canvas of the 56 px render), so the nominal x is the axis minus half of it.
    // Its crossing is handled by the room logic, not by this plan.
    if ((b.kind == ENC_BLOCK_ENCOUNTER || b.kind == ENC_BLOCK_BOSS) && max > 0) {
        out[0].piece = STRIP_PIECE_PUERTA;
        out[0].mirror = 0;
        out[0].lx = ENC_FLOOR_W / 2 - ARPG_ROOM_DOOR_ART_W_PX / 2;
        out[0].ly = 0;
        m = 1;
    }
    if (n > max - m) n = max - m;
    for (int i = 0; i < n; i++) {
        uint8_t piece = defs[i].piece;
        if (b.kind == ENC_BLOCK_CORRIDOR && b.idx == ENC_BOSS && piece == STRIP_PIECE_RELICARIO) continue;
        // One bench group in four is the variant with the broken bench, picked by (block, piece index). Only the
        // groups on tile row 0 of the kit phases have it baked (tile budget; tools/bake_cathedral_kit.py).
        if (piece == STRIP_PIECE_BANCO_GRUPO4 && ((((defs[i].y + 4) >> 3) & 15) == 0) &&
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
    if (b.kind == ENC_BLOCK_ENCOUNTER) {
        const EncPlant *pl = &s_plants[b.plant];
        for (int i = 0; i < pl->n_rects && n < max; i++) {
            const EncRectDef *r = &pl->rects[i];
            out[n].kind = r->kind;
            out[n].x = (int16_t)(ENC_FLOOR_X + (b.mirror ? ENC_FLOOR_W - (r->x + r->w) : r->x));
            out[n].y = r->y;
            out[n].w = r->w;
            out[n].h = r->h;
            n++;
        }
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
    case ENC_E_MONAGUILLO: return ENEMY_TYPE_MONAGUILLO;
    case ENC_E_BEBE:       return ENEMY_TYPE_BEBE;
    case ENC_E_PARROCO:    return ENEMY_TYPE_PARROCO;
    case ENC_E_MONJA:      return ENEMY_TYPE_MONJA;
    default:               return ENEMY_TYPE_EXVOTO;
    }
}

// ---------------------------------------------------------------------------
// Rooms (salas ARPG): geometry of the doors and lateral openings.
// ---------------------------------------------------------------------------

// Floors of the act are rooms stacked one per block (DESIGN.md 6.13.6). Every room has an upper door
// centred on its top line, and a lateral opening in the left or right wall, alternating by room.
int enc_room_opening(int32_t block, EncRoomOpening *out) {
    int k = s_first_block - (int)block;
    if (k < 0 || k >= ENC_STAGES) return 0;
    const int right = k & 1;
    out->x = (int16_t)(right ? (ENC_FLOOR_X + ENC_FLOOR_W) : ENC_CAM_X);
    out->y = (int16_t)ARPG_ROOM_HOLE_Y_PX;
    out->w = (int16_t)ARPG_ROOM_HOLE_W_PX;
    out->h = (int16_t)ARPG_ROOM_HOLE_H_PX;
    return 1;
}

int enc_room_dest_pos(int k, int *out_x, int *out_y) {
    if (k < 0 || k >= ENC_STAGES) return 0;
    const int top = window_top(block_of_encounter(k));
    *out_x = ENC_FLOOR_X + ENC_FLOOR_W / 2;
    *out_y = top + ENC_BLOCK_H - ARPG_ROOM_FOOT_OFFSET_PX;    // the foot of the room, just above its bottom line
    return 1;
}

static int stage_at_py(int py) {
    int32_t block = (int32_t)(py - (int)strip_shift_total_px()) / ENC_BLOCK_H;
    return s_first_block - (int)block;
}

// Which room furniture a floor has. Kept as plain predicates so a later pass can retune the rhythm
// without touching the placement or the runtime.
static int room_has_chest(int k) { return k > 0 && (k & 1) == 1; }   // alternate rooms, from the second one
static int room_has_altar(int k) { return (k % 3) == 2; }            // every third room
static int room_center_x(void) { return ENC_FLOOR_X + ENC_FLOOR_W / 2; }   // both sit in the hero's path
static int room_chest_y(int k) { return window_top(block_of_encounter(k)) + 210; }
static int room_altar_y(int k) { return window_top(block_of_encounter(k)) + 120; }

// A crossing asked by enc_update() is consumed by main.c on the next frame, which fades to black and
// teleports the hero to the foot of room s_exit_room. -1 = none.
int enc_room_take_exit(int *out_k) {
    if (s_exit_room < 0) return 0;
    *out_k = s_exit_room;
    s_exit_room = -1;
    return 1;
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
    e->max_hp = g_enemy_tuning[type].max_hp;
    if (type == ENEMY_TYPE_ABANDERADO && g_enc_debug.boss_hp) e->max_hp = g_enc_debug.boss_hp;    // scenarios tune the boss
    // Depth (DESIGN.md 7.1): the floor (`owner`) makes every enemy tougher; the Abanderado also by its boss number.
    // Each step multiplies first and divides after, so no product leaves an int (the boss of floor 100 is ~640k).
    e->max_hp = e->max_hp * ARPG_DEPTH_PCT(owner) / 100;
    if (type == ENEMY_TYPE_ABANDERADO) e->max_hp = e->max_hp * ARPG_BOSS_HP_PCT(boss_number(owner)) / 100;
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
        made++;
    }
    return made;
}

// ---------------------------------------------------------------------------
// Group population (v3 §5): each room holds one group of 4..12 that wakes on approach.
// Types are the real tiers now (v3 tiers): Bebé swarm, Exvoto base, Párroco tank and Monja support.
// `hp_x` stays as a per-room multiplier on top of the type's tuning (the tiers carry their own base life:
// Bebé x1, Párroco x4 and Monja x2 over the Exvoto base, see gameplay.c / enc_init).
// ---------------------------------------------------------------------------
typedef struct {
    uint8_t enc_type;   // ENC_E_* of the tier
    uint8_t hp_x;       // extra life multiplier for this slot (1 = the type's own tuning)
    uint8_t guard;      // 1 = stays at its post and prays (the Monja)
    uint8_t weight;     // mix weight inside a group
} RoomKind;
static const RoomKind s_room_kinds[] = {
    { ENC_E_BEBE,       1, 0, 3 },   // bebé: swarm, dies in one hit, a bit faster
    { ENC_E_EXVOTO,     1, 0, 2 },   // adulta: the base Exvoto
    { ENC_E_PARROCO,    1, 0, 2 },   // Párroco: tank, x4 life (its own tuning), harder hits, shoves the hero
    { ENC_E_MONJA,      1, 1, 2 },   // Monja: support, stays behind praying and heals nearby Exvotos
    { ENC_E_OJO,        1, 0, 1 },   // Ojo, as it is today
    { ENC_E_CIRENEO,    1, 0, 1 },   // Cireneo, as it is today
};
#define ROOM_KIND_COUNT ((int)(sizeof(s_room_kinds) / sizeof(s_room_kinds[0])))

// Indices into s_room_kinds (the order of the table above).
enum { RK_BEBE = 0, RK_EXVOTO, RK_PARROCO, RK_MONJA, RK_OJO, RK_CIRENEO };

static int room_group_count(int k);
static int room_kind_of(int k, int i);

// Difficulty ramp (DESIGN.md, opening rooms): how many Ojos/Cireneos a group carries. None before
// ARPG_MINION_MIN_ROOM; from there until the full mix, 1 in ARPG_MINION_ROOM_FREQ rooms has a single
// one; from ARPG_FULL_MIX_ROOM on, up to ARPG_MINION_MAX_PER_GROUP. Deterministic from the room hash.
static int room_minion_count(int k) {
    if (k < ARPG_MINION_MIN_ROOM) return 0;
    if (k < ARPG_FULL_MIX_ROOM) {
        uint32_t h = hash32(s_seed ^ ((uint32_t)k * 0x2545f491u) ^ 0x4d494e31u);
        return (h % (uint32_t)ARPG_MINION_ROOM_FREQ) == 0 ? 1 : 0;
    }
    return ARPG_MINION_MAX_PER_GROUP;
}

// Weight of a base slot: Ojos/Cireneos only come through the minion slots, and Párroco/Monja only
// from ARPG_TIER_MIN_ROOM on.
static int room_base_weight(int k, int j) {
    if (j == RK_OJO || j == RK_CIRENEO) return 0;
    if (k < ARPG_TIER_MIN_ROOM && (j == RK_PARROCO || j == RK_MONJA)) return 0;
    return s_room_kinds[j].weight;
}

static int room_base_kind_of(int k, int i) {
    int total = 0;
    for (int j = 0; j < ROOM_KIND_COUNT; j++) total += room_base_weight(k, j);
    uint32_t h = hash32(s_seed ^ ((uint32_t)k * 0x9e3779b9u) ^ ((uint32_t)i * 0x85ebca6bu) ^ 0x524f4f4du);
    int r = (int)(h % (uint32_t)total);
    int pick = RK_BEBE;
    for (int j = 0; j < ROOM_KIND_COUNT; j++) {
        int w = room_base_weight(k, j);
        if (r < w) { pick = j; break; }
        r -= w;
    }
    // Before the full mix, at most ARPG_TIER_CAP_PER_GROUP Párrocos and Monjas each: a second one
    // of the same kind becomes a Bebé.
    if ((pick == RK_PARROCO || pick == RK_MONJA) && k < ARPG_FULL_MIX_ROOM) {
        int seen = 0;
        for (int j = 0; j < i; j++) if (room_kind_of(k, j) == pick) seen++;
        if (seen >= ARPG_TIER_CAP_PER_GROUP) pick = RK_BEBE;
    }
    return pick;
}

static int room_kind_of(int k, int i) {
    const int want = room_group_count(k);
    const int minions = room_minion_count(k);
    if (minions > 0 && i >= want - minions) {     // the last slots carry the Ojo(s)/Cireneo(s)
        uint32_t h = hash32(s_seed ^ ((uint32_t)k * 0x9e3779b9u) ^ ((uint32_t)i * 0x85ebca6bu) ^ 0x534f464fu);
        return (h & 1u) ? RK_CIRENEO : RK_OJO;
    }
    return room_base_kind_of(k, i);
}

static int room_group_count(int k) {
    uint32_t h = hash32(s_seed ^ ((uint32_t)k * 0x45d9f3bu) ^ 0x47525031u);
    return ARPG_ROOM_GROUP_MIN + (int)(h % (uint32_t)(ARPG_ROOM_GROUP_MAX - ARPG_ROOM_GROUP_MIN + 1));
}

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

static void place_room_enemy(Enemy *e, const RoomKind *kind, int x, int y, int ordinal, int owner) {
    EnemyType type = enemy_type_of(kind->enc_type);
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = owner;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = g_enemy_tuning[type].max_hp * kind->hp_x;
    e->max_hp = e->max_hp * ARPG_DEPTH_PCT(owner) / 100;
    e->hp = e->max_hp;
    e->dir = (ordinal * 2) % 8;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->state = ENEMY_STATE_DORMANT;
    if (type == ENEMY_TYPE_SHOOTER || kind->guard) {
        e->home_flags = ENEMY_HOME_SET | (kind->guard ? ENEMY_HOME_GUARD : 0);
        *enemy_home_x(e) = x;
        *enemy_home_y(e) = y;
    }
}

static int active_enemies(const Enemy *enemies, int max_enemies) {
    int n = 0;
    for (int i = 0; i < max_enemies; i++) if (enemies[i].active) n++;
    return n;
}

// Places the group of room k asleep. Respects the active cap: with no free slots it leaves the room
// unspawned so a later frame (after the group behind is recycled) can place it.
static int spawn_room_group(Enemy *enemies, int max_enemies, int k) {
    const int want = room_group_count(k);
    int active = active_enemies(enemies, max_enemies);
    int made = 0;
    for (int i = 0; i < want && active + made < MAX_GAMEPLAY_ENEMIES; i++) {
        int slot = -1;
        for (int s = 0; s < max_enemies; s++) if (!enemies[s].active) { slot = s; break; }
        if (slot < 0) break;
        int x, y;
        room_group_slot(k, i, &x, &y);
        int placed = 0;
        for (int t = 0; t < 4 && !placed; t++) {           // nudge around a prop before giving up on the slot
            int tx = x + (t == 1 ? 12 : t == 2 ? -12 : t == 3 ? 0 : 0);
            int ty = y + (t == 3 ? 12 : 0);
            if (position_is_free(TO_FIXED(tx), TO_FIXED(ty))) {
                place_room_enemy(&enemies[slot], &s_room_kinds[room_kind_of(k, i)], tx, ty, i, k);
                placed = 1;
            }
        }
        if (placed) made++;
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
    }
}

// Escort and phases live in boss.c (BossDef above); these are the hooks it calls. They need the enemy pool and the hero
// position the last enc_update saw.
static Enemy *s_pool;
static int s_pool_n, s_hero_px, s_hero_py;

static void boss_spawn_escort(EnemyType type, int floor_x) {
    if (!s_pool) return;
    const uint8_t t = type == ENEMY_TYPE_SHOOTER ? ENC_E_OJO : type == ENEMY_TYPE_CHARGER ? ENC_E_CIRENEO : ENC_E_EXVOTO;
    EncEnemyDef def = { t, ENC_S_AWAKE, (int16_t)floor_x, 16 };
    spawn_group(s_pool, s_pool_n, &def, 1, 0, window_top(block_of_encounter(s_active_boss_k)), 16, s_active_boss_k, 1);
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
        static const uint8_t kind[5] = {ARPG_ITEM_RELIC, ARPG_ITEM_RELIC, ARPG_ITEM_RELIC, ARPG_ITEM_TOME, ARPG_ITEM_TOME};
        static const uint8_t sch[5] = {ARPG_SCHOOL_PECHO, ARPG_SCHOOL_RAYO, ARPG_SCHOOL_EJECUCION, ARPG_SCHOOL_RAYO, ARPG_SCHOOL_GLIFO};
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
            if (e->active && e->hp > 0 && e->type == ENEMY_TYPE_ABANDERADO) {
                enemy_hit(e, g_enc_debug.boss_damage, 0, 0);
                g_enc_debug.boss_damage = 0;
                break;
            }
        }
    }

    // Rooms (salas ARPG): the hero's room, not the cleared count, decides what lives. The group of a
    // room is placed when he gets close, wakes when he steps in, and enemies left two rooms below are
    // recycled so the 24-slot pool always serves the fight around him. No gate blocks the way up.
    int hero_k = stage_at_py(py);
    if (hero_k < 0) hero_k = 0;
    if (hero_k >= ENC_STAGES) hero_k = ENC_STAGES - 1;
    const int cur = hero_k;
    int alive_cur = 0;
    int lo = hero_k - 1; if (lo < 0) lo = 0;
    int hi = hero_k + 2; if (hi > ENC_STAGES) hi = ENC_STAGES;

    // Recycle enemies far below the hero (rooms already behind him).
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0) continue;
        if (TO_INT(e->y) <= py + ARPG_ROOM_DESPAWN_BEHIND_PX) continue;
        int pk = e->pack;
        e->active = 0;
        if (pk >= 0 && pk < ENC_STAGES && !is_boss_stage(pk) && !s_rt[pk].cleared) {
            s_rt[pk].spawned = 0;      // the room may be repopulated if the hero comes back to it
            s_rt[pk].awake = 0;
        }
    }

    // Place the groups ahead (asleep). spawn_room_group respects the pool cap: with no slots the room
    // stays unspawned and retries on a later frame.
    for (int k = lo; k < hi; k++) {
        EncRuntime *rt = &s_rt[k];
#if ARPG_BOXEO
        continue;               // boxeo: no room ever populates; the only enemy is the dummy of boxeo.c
#endif
        if (rt->spawned) continue;
        const int top = window_top(block_of_encounter(k));
        const int bottom = top + ENC_BLOCK_H;
        if (bottom < py - ARPG_ROOM_DESPAWN_BEHIND_PX) continue;      // far below: wait
        if (py > bottom + ARPG_ROOM_SPAWN_AHEAD_PX) continue;         // not close yet
        if (is_boss_stage(k)) {
            rt->spawned = 1;
            s_active_boss_k = k;
            boss_reset(boss_def_of(boss_number(k)), k);
            g_abanderado_max_mona = boss_mona_cap(boss_number(k));
            spawn_group(enemies, max_enemies, s_boss_enemies,
                        (int)(sizeof(s_boss_enemies) / sizeof(s_boss_enemies[0])), 0, top, -1, k, 0);
        } else if (spawn_room_group(enemies, max_enemies, k) > 0) {
            rt->spawned = 1;
            rt->awake = 0;
        } else {
            break;      // pool full: do not mark the room, try again once something behind is recycled
        }
    }

    // Wake the room the hero steps into, with at most ARPG_ROOM_MAX_AWAKE groups around him.
    for (int k = lo; k < hi; k++) {
        EncRuntime *rt = &s_rt[k];
        if (!rt->spawned || rt->awake) continue;
        const int top = window_top(block_of_encounter(k));
        const int bottom = top + ENC_BLOCK_H;
        int hurt;
        (void)alive_of(enemies, max_enemies, k, &hurt);
        if (py >= bottom - ENC_WAKE_MARGIN && !hurt) continue;
        if (k != hero_k) {
            int awake = 0;
            for (int j = lo; j < hi; j++) if (s_rt[j].awake && !s_rt[j].cleared) awake++;
            if (awake >= ARPG_ROOM_MAX_AWAKE) continue;               // this group waits its turn
        }
        rt->awake = 1;
        if (k + 1 > g_arpg.deepest) g_arpg.deepest = (uint16_t)(k + 1);   // progress: the deepest floor reached
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
            if (alive == 0 && (is_boss || hurt == 0)) {
                if (!rt->cleared) {
                    rt->cleared = 1;
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

    // Room crossings: the upper door (top line, centred) or the lateral opening of the room the hero
    // is in asks main.c for a fade. Destination is the room above (the lateral entrance is the same
    // room for now, as the strip only advances vertically).
    if (s_exit_room < 0 && hero_k + 1 < ENC_STAGES) {
        const int top = window_top(block_of_encounter(hero_k));
        const int cx = room_center_x();
        const int ax = px > cx ? px - cx : cx - px;
        if (py < top + ARPG_ROOM_DOOR_TRIGGER_PX && py > top - 4 && ax <= ARPG_ROOM_DOOR_HALF_W_PX) {
            s_exit_room = hero_k + 1;
        } else {
            // The only way the hero's ground point reaches the wall band is through the open hole
            // (the rest of the wall keeps colliding), so no vertical check is needed here.
            EncRoomOpening op;
            if (enc_room_opening(block_of_encounter(hero_k), &op)) {
                if (op.x == ENC_CAM_X) { if (px < ENC_FLOOR_X - 4) s_exit_room = hero_k + 1; }
                else { if (px > ENC_FLOOR_X + ENC_FLOOR_W + 4) s_exit_room = hero_k + 1; }
            }
        }
    }

    // Chests and travel altars of the rooms around the hero.
    for (int k = hero_k - 1; k <= hero_k + 1; k++) {
        if (k < 0 || k >= ENC_STAGES) continue;
        if (room_has_chest(k) && !s_rt[k].chest_open) {
            const int cx = room_center_x(), cy = room_chest_y(k);
            const int dx = px - cx, dy = py - cy;
            if (dx * dx + GROUND_DY2(dy) <= ARPG_ROOM_CHEST_REACH_PX * ARPG_ROOM_CHEST_REACH_PX) {
                s_rt[k].chest_open = 1;
                sfx_play(SND_CHEST_OPEN, cx);
                const fixed fx = TO_FIXED(cx), fy = TO_FIXED(cy);
                arpg_add_xp(ARPG_ROOM_CHEST_XP + k / 2);
                pickups_spawn(PICKUP_KIND_HEALTH, fx - TO_FIXED(8), fy);
                pickups_spawn(PICKUP_KIND_MANA, fx + TO_FIXED(8), fy);
                uint32_t chest_rng = (uint32_t)(k + 1) * 2654435761u ^ (uint32_t)(px * 73856093 ^ py * 19349663);
                int chest_lvl = (k + 1) < 1 ? 1 : ((k + 1) > 99 ? 99 : (k + 1));
                ArpgInvItem chest_relic;
                arpg_relic_roll(&chest_relic, chest_lvl, ARPG_RAR_UNCOMMON, &chest_rng);
                pickups_spawn_relic(fx, fy + TO_FIXED(6), &chest_relic);
            }
        }
        if (room_has_altar(k) && !s_rt[k].altar_touched) {
            const int cx = room_center_x(), cy = room_altar_y(k);
            const int dx = px - cx, dy = py - cy;
            if (dx * dx + GROUND_DY2(dy) <= ARPG_ROOM_ALTAR_REACH_PX * ARPG_ROOM_ALTAR_REACH_PX) {
                s_rt[k].altar_touched = 1;
                const int a = k / 3;                 // altar index in the progress mask
                if (a < 32) g_arpg.altars_lo |= (1u << a);
                else if (a < 64) g_arpg.altars_hi |= (1u << (a - 32));
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
    st->current = (uint8_t)cur;                // the room the hero is in (rooms are not gated by clearing)
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
            if (e->type == ENEMY_TYPE_ABANDERADO) boss_hp = e->hp;
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
    return k >= 0 && k <= ENC_BOSS && s_rt[k].spawned && !s_rt[k].awake;
}

void enc_note_beam_hit(const Enemy *e) {
    if (e->type == ENEMY_TYPE_ABANDERADO) {
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

int enc_current_encounter(void) {
    int cur = g_enc_stats.current;
    return cur >= ENC_STAGES ? ENC_STAGES : cur + 1;
}

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
    for (int k = 0; k <= ENC_BOSS; k++) {
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
            row[sx] = c;
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
    // Chests block the hero (and the enemies) on their ground footprint in every room, on or off screen.
    collision_extra_begin();
    for (int k = 0; k < ENC_STAGES; k++) {
        if (!room_has_chest(k)) continue;
        const int cx = room_center_x(), cy = room_chest_y(k);
        collision_extra_add(cx - 8, cy - 4, cx + 8, cy + 2);
    }
    s_fixture_n = 0;
    for (int k = 0; k < ENC_STAGES && s_fixture_n < ENC_FIXTURE_MAX; k++) {
        const int top = window_top(block_of_encounter(k));
        if (top + ENC_BLOCK_H <= cam_y || top >= cam_y + SCREEN_H) continue;
        if (room_has_chest(k)) {
            s_fixtures[s_fixture_n].x = (int16_t)room_center_x();
            s_fixtures[s_fixture_n].y = (int16_t)room_chest_y(k);
            s_fixtures[s_fixture_n].k = (uint8_t)k;
            s_fixtures[s_fixture_n].kind = ENC_FIX_CHEST;
            // The open chest stays in the room: the loot is out, the furniture is not gone.
            s_fixtures[s_fixture_n].sprite = s_rt[k].chest_open ? ENC_SPR_COFRE_ABIERTO : ENC_SPR_COFRE_CERRADO;
            s_fixture_n++;
        }
        if (room_has_altar(k)) {
            s_fixtures[s_fixture_n].x = (int16_t)room_center_x();
            s_fixtures[s_fixture_n].y = (int16_t)room_altar_y(k);
            s_fixtures[s_fixture_n].k = (uint8_t)k;
            s_fixtures[s_fixture_n].kind = ENC_FIX_ALTAR;
            s_fixtures[s_fixture_n].sprite = ENC_SPR_ALTAR;
            s_fixture_n++;
        }
    }
    return s_fixture_n;
}

// Top-left of a fixture sprite in world px: its ground anchor lands on the fixture's Y.
static void fixture_origin(const EncFixture *f, int *out_x, int *out_y) {
    const EncRoomSprite *s = &s_enc_room_sprites[f->sprite];
    *out_x = f->x - s->w / 2;
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
            row[sx] = c;
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
