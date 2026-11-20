#include "encounters_act1.h"

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
#include "sfx_voice_len.h"
#include "collision.h"
#include "enemy_ai.h"
#include "groundfx.h"
#include "navfield.h"
#include "strip.h"
#include "strip_kit.h"
#include "upgrades.h"
#include "player_sprite.h"
#include "enc_relic_gfx.h"

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
} EncRuntime;
static EncRuntime s_rt[ENC_STAGES];
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
    for (int i = 0; i < ENC_STAGES; i++) s_rt[i].back_lift = ENC_VERJA_H;
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
    if (n > max) n = max;
    int m = 0;
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
    if ((b.kind == ENC_BLOCK_ENCOUNTER || b.kind == ENC_BLOCK_BOSS) && !s_rt[b.idx].barrier_open) {
        if (n < max) {
            out[n].kind = ENC_R_BARRERA;
            out[n].x = ENC_FLOOR_X;
            out[n].y = 0;
            out[n].w = ENC_FLOOR_W;
            out[n].h = ENC_BARRIER_H;
            n++;
        }
    }
    if (b.kind == ENC_BLOCK_BOSS && s_boss_locked && b.idx == s_active_boss_k && n < max) {      // boss mode: the same barrier closes the bottom edge
        out[n].kind = ENC_R_BARRERA;
        out[n].x = ENC_FLOOR_X;
        out[n].y = ENC_BLOCK_H - ENC_BARRIER_H;
        out[n].w = ENC_FLOOR_W;
        out[n].h = ENC_BARRIER_H;
        n++;
    }
    if (b.kind == ENC_BLOCK_ENCOUNTER && s_rt[b.idx].back_closed && !s_rt[b.idx].cleared && n < max) {   // rear barrier closes behind the hero once the room wakes
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
    default:               return ENEMY_TYPE_EXVOTO;
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

static const EncPopulation *population_of(int k) {
    return &s_plants[s_plant[k]].pop[s_tier[k]];
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

void enc_update(Enemy *enemies, int max_enemies, int px, int py) {
    volatile EncStats *st = &g_enc_stats;
    apply_debug();
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

    // Only the first floor not cleared, and the one above it, can change this frame (a floor spawns when the one
    // below is cleared, and nothing higher has spawned yet). Keeps the frame cost flat at 100 floors.
    int cur = ENC_BOSS;                       // the floor the hero faces next
    for (int k = 0; k < ENC_STAGES; k++) {
        if (!s_rt[k].cleared) { cur = k; break; }
    }
    int alive_cur = 0;
    const int last = cur + 2 < ENC_STAGES ? cur + 2 : ENC_STAGES;

    for (int k = cur; k < last; k++) {
        EncRuntime *rt = &s_rt[k];
        if (rt->cleared) continue;
        const int top = window_top(block_of_encounter(k));
        const int bottom = top + ENC_BLOCK_H;
        const int is_boss = is_boss_stage(k);

        if (!rt->spawned) {
            if ((k == 0 || s_rt[k - 1].cleared) && top >= 0 && py <= bottom + ENC_SPAWN_AHEAD) {
                rt->spawned = 1;
                if (is_boss) {
                    s_active_boss_k = k;
                    boss_reset(boss_def_of(boss_number(k)), k);
                    g_abanderado_max_mona = boss_mona_cap(boss_number(k));
                    spawn_group(enemies, max_enemies, s_boss_enemies,
                                (int)(sizeof(s_boss_enemies) / sizeof(s_boss_enemies[0])), 0, top, -1, k, 0);
                } else {
                    const EncPopulation *pop = population_of(k);
                    spawn_group(enemies, max_enemies, pop->enemies, pop->n, s_mirror[k], top, -1, k, 0);
                }
            }
            continue;
        }

        int hurt;
        int alive = alive_of(enemies, max_enemies, k, &hurt);
        if (!rt->awake) {
            if (py < bottom - ENC_WAKE_MARGIN || hurt) {
                rt->awake = 1;
                if (k + 1 > g_arpg.deepest) g_arpg.deepest = (uint16_t)(k + 1);   // progress: the deepest floor reached
                wake_owner(enemies, max_enemies, k);
                if (st->woken < k + 1) st->woken = (uint8_t)(k + 1);
                if (is_boss) {
                    boss_begin(enemies, max_enemies);                 // the hero is in the room: close it, intro
                } else {                                              // normal room: close the rear barrier behind the hero
                    strip_collision_fill_win(ENC_FLOOR_X, bottom - ENC_BARRIER_H, ENC_FLOOR_W, ENC_BARRIER_H,
                                             enc_collision_value(ENC_R_BARRERA));
                    rt->back_closed = 1;
                    nav_refresh_begin(px, py);
                }
                if (k == cur) st->wake_frames = 0;
            }
            continue;
        }
        if (k == cur && st->wake_frames < 0xFFFF) st->wake_frames++;

        if (!is_boss && !rt->wave2_done) {
            const EncPopulation *pop = population_of(k);
            if (pop->n2 > 0 && alive <= 1) {
                rt->wave2_done = 1;
                spawn_group(enemies, max_enemies, pop->wave2, pop->n2, s_mirror[k], top, 16, k, 1);
                alive = alive_of(enemies, max_enemies, k, &hurt);
            } else if (pop->n2 == 0) {
                rt->wave2_done = 1;
            }
        }
        if (is_boss) {
            // The escort and the Monaguillos do not keep the fight alive: it ends when the Abanderado falls.
            // boss.c runs the phases and the escort while it lives.
            if (!boss_combat_update(enemies, max_enemies)) {
                for (int i = 0; i < max_enemies; i++)
                    if (enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == k) enemy_hit(&enemies[i], 9999, 0, 0);
                alive = 0;
            }
        }
        if (k == cur) alive_cur = alive;

        if (alive == 0 && (is_boss || rt->wave2_done)) {
            rt->cleared = 1;
            if (!is_boss) {
                if (k < ENC_COUNT) {
                    st->clear_frames[k] = st->wake_frames;
                    st->hp_end[k] = HP_U8(g_player_state.hp);
                    st->dones_at[k] = st->dones;
                }
                st->cleared = (uint8_t)(k + 1);
                rt->verja_opening = 1;
            } else {
                st->cleared = (uint8_t)(k + 1);
                st->boss_frames = st->wake_frames;
                rt->verja_opening = 1;             // the top barrier rises: the hero walks on into the next floor
                boss_victory();                    // the bottom barrier opens again when the victory ends (boss hook)
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
    cur = ENC_BOSS;
    for (int k = 0; k < ENC_STAGES; k++) {
        if (!s_rt[k].cleared) { cur = k; break; }
    }
    st->current = (uint8_t)cur;
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
