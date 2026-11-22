#include "gameplay.h"
#include "dmg_numbers.h"
#include "crashlog.h"
#include "encounters.h"
#include "boss.h"
#include "collision.h"
#include "modifiers.h"
#include "upgrades.h"
#include "sfx.h"
#include "remate.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "arpg_tree.h"
#include "weapons.h"
#include "curse.h"
#include <string.h>
#if ENCOUNTERS_PROTO
#include "encounters_act1.h"
#endif

// ---------------------------------------------------------------------------
// 1. Fixed-Point 8.8 Tuning Tables
// ---------------------------------------------------------------------------

ENEMY_TUNING_CONST EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES] = {
    [ENEMY_TYPE_NONE] = { 0 },
    [ENEMY_TYPE_CHARGER] = {
        .max_hp = 300,            // [TUNABLE-PLACEHOLDER] scale 100 = 1.0 (was 60): 2 sniper hits (150 each)
        .speed = 105,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~58% of the hero (181), so the player can break away and charge the beam
        .telegraph_duration = 45, // [TUNABLE-PLACEHOLDER] 0.75 s standing still and blinking before the lunge
        .charge_speed = 650,      // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~2 x the hero (326), straight line
    },
    [ENEMY_TYPE_SHOOTER] = {
        .max_hp = 300,            // [TUNABLE-PLACEHOLDER] Ojo del Tribunal (DESIGN.md 6.10), scale 100 = 1.0: two sniper hits (150 each)
        .speed = 110,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: about a third of the hero's 326
        .attack_cooldown = 90,    // [TUNABLE-PLACEHOLDER] frames of cooldown after the sentence, then it closes in again
    },
    [ENEMY_TYPE_EXVOTO] = {
        .max_hp = 100,            // [TUNABLE-PLACEHOLDER] scale 100 = 1.0: dies to one sniper hit
        .speed = 130,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~40% of the hero's 326
        .attack_cooldown = 30,    // [TUNABLE-PLACEHOLDER] frames between bites
        .preferred_dist_max = 16, // [TUNABLE-PLACEHOLDER] melee range (ground px)
    },
    [ENEMY_TYPE_ABANDERADO] = {
        .max_hp = 1200,           // [TUNABLE-PLACEHOLDER] 8 charged sniper shots (150 each)
        .speed = 75,              // [TUNABLE-PLACEHOLDER] 8.8 fixed: slow patrol
        .attack_cooldown = ABANDERADO_SUMMON_FRAMES,
    },
    [ENEMY_TYPE_MONAGUILLO] = {
        .max_hp = 100,            // [TUNABLE-PLACEHOLDER] same rules as Exvoto: dies in one hit
        .speed = 130,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: slow prayer-walk
        .attack_cooldown = 30,    // [TUNABLE-PLACEHOLDER] frames between bites
        .preferred_dist_max = 16, // [TUNABLE-PLACEHOLDER] melee range (ground px)
    },
    // ---- Exvoto tiers (v3, walkthroughs/arpg-predemo §10) -----------------------------------------
    // Lives come from the rooms table (encounters_act1.c enc_init): Bebé x1 base, Párroco x4 base, Monja x2.
    [ENEMY_TYPE_BEBE] = {
        .max_hp = 100,            // [TUNABLE-PLACEHOLDER] swarm: dies in one hit (the ray does ARPG_RAY_DAMAGE)
        .speed = 160,             // [TUNABLE-PLACEHOLDER] a bit faster than the Exvoto's 130
        .attack_cooldown = 30,    // [TUNABLE-PLACEHOLDER] frames between bites
        .preferred_dist_max = 14, // [TUNABLE-PLACEHOLDER] melee range (ground px)
    },
    [ENEMY_TYPE_PARROCO] = {
        .max_hp = 400,            // [TUNABLE-PLACEHOLDER] tank: x4 the Exvoto base before the floor scaling
        .speed = 105,             // [TUNABLE-PLACEHOLDER] heavier, below the Exvoto
        .attack_cooldown = 45,    // [TUNABLE-PLACEHOLDER] frames between blows (slower, harder hits)
        .preferred_dist_max = 20, // [TUNABLE-PLACEHOLDER] melee range (ground px), long arms
    },
    [ENEMY_TYPE_MONJA] = {
        .max_hp = 200,            // [TUNABLE-PLACEHOLDER] support: x2 the Exvoto base
        .speed = 105,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: she walks only when the group closes in
        .attack_cooldown = 40,    // [TUNABLE-PLACEHOLDER] frames between bites when forced to fight
        .preferred_dist_max = 16, // [TUNABLE-PLACEHOLDER] melee range (ground px)
    },
};

// ---------------------------------------------------------------------------
// 2. Deterministic Integer RNG (LCG)
// ---------------------------------------------------------------------------

static uint32_t s_rng_state = 123456789;

void rng_seed(uint32_t seed) {
    s_rng_state = seed ? seed : 1;
}

uint32_t rng_next(void) {
    s_rng_state = s_rng_state * 1664525u + 1013904223u;
    return s_rng_state;
}

int rng_range(int min, int max) {
    if (min >= max) return min;
    uint32_t r = rng_next();
    return min + (int)(r % (uint32_t)(max - min + 1));
}

// ---------------------------------------------------------------------------
// 3. Player State & Damage
// ---------------------------------------------------------------------------

PlayerState g_player_state;
int g_hitstop_frames = 0;
int g_arpg_level = 1;

static int s_mana_regen_timer = 0;

// L held past ARPG_L_HOLD_FRAMES: toggles the active spell (Rayo <-> Maldicion) once the curse is unlocked.
void arpg_on_l_hold(void) {
    if (!arpg_tree_has(0)) return;
    g_arpg.spell = g_arpg.spell ? 0 : 1;
    weapons_cancel_aim();
    curse_cancel_aim();
    sfx_play(SND_HEART_CHARGE, -1);
}

int arpg_enemy_damage(int enemy_type) {
    switch (enemy_type) {
    case ENEMY_TYPE_EXVOTO:     return ARPG_DMG_EXVOTO;
    case ENEMY_TYPE_MONAGUILLO: return ARPG_DMG_MONAGUILLO;
    case ENEMY_TYPE_BEBE:       return ARPG_DMG_BEBE;
    case ENEMY_TYPE_PARROCO:    return ARPG_DMG_PARROCO;
    case ENEMY_TYPE_MONJA:      return ARPG_DMG_MONJA;
    case ENEMY_TYPE_CHARGER:    return ARPG_DMG_CIRENEO;
    case ENEMY_TYPE_SHOOTER:    return ARPG_DMG_OJO;
    case ENEMY_TYPE_ABANDERADO: return ARPG_DMG_ABANDERADO;
    default:                    return ARPG_DMG_DEFAULT;
    }
}

void player_regen_mana(PlayerState *player) {
    if (!player || player->is_dead) return;
    if (player->mana >= player->max_mana) {
        s_mana_regen_timer = 0;
        return;
    }
    int denom = 100 + g_mods.mana_regen_pct;
    if (denom < 25) denom = 25;
    int period = (ARPG_MANA_REGEN_FRAMES * 100) / denom;
    if (period < 6) period = 6;
    if (++s_mana_regen_timer >= period) {
        s_mana_regen_timer = 0;
        player->mana++;
    }
}

void player_state_init(PlayerState *player) {
    if (!player) return;
    // g_mods.max_hp is already in life points (Vida and Bone Plate add 20 per heart).
    player->max_hp = ARPG_HP_BASE + (g_arpg_level - 1) * ARPG_HP_PER_LEVEL + g_mods.max_hp;
    player->hp = player->max_hp;
    player->max_mana = ARPG_MANA_BASE + (g_arpg_level - 1) * ARPG_MANA_PER_LEVEL + g_mods.max_mana;
    if (player->max_mana < 10) player->max_mana = 10;
    player->mana = player->max_mana;
    s_mana_regen_timer = 0;
    player->current_weapon = WEAPON_SNIPER;  // the sacred ray is the hero's only weapon (DESIGN.md 6.9.1c)
    player->is_dead = 0;
    player->invuln_timer = 0;
}

int player_take_damage(PlayerState *player, int damage) {
    if (!player || player->is_dead || player->god_mode || player->invuln_timer > 0 || remate_invuln() > 0) return 0;
    player->hp -= damage;
    dmg_numbers_spawn_player(damage, DMG_NUM_PLAYER);
    player->invuln_timer = PLAYER_IFRAMES + g_mods.iframes;
    if (player->hp <= 0) {
        player->hp = 0;
        player->is_dead = 1;
        sfx_stop_charge();
    }
    weapons_player_hit();           // Corazon Flagelado (ignores a hit that kills)
#if ENCOUNTERS_PROTO
    enc_player_hit();
#endif
    sfx_play(SND_PLAYER_HURT, -1);
    return 1;
}

int player_take_hit(PlayerState *player) {
    return player_take_damage(player, ARPG_DMG_DEFAULT);
}

// Párroco tier shove (v3): the hero is nudged back along the blow. The state lives here (not in PlayerState,
// whose layout the scenarios pin by offset) and is applied over a few frames by the main loop, sliding on walls.
static fixed s_push_vx, s_push_vy;
static int s_push_frames;

void player_apply_push(fixed vx, fixed vy, int frames) {
    if (frames <= 0) return;
    s_push_vx = vx;
    s_push_vy = vy;
    s_push_frames = frames;
}

int player_push_step(fixed *out_vx, fixed *out_vy) {
    if (s_push_frames <= 0) return 0;
    s_push_frames--;
    *out_vx = s_push_vx;
    *out_vy = s_push_vy;
    s_push_vx = (s_push_vx * 200) >> 8;      // ease out: it reads as a shove, not a slide
    s_push_vy = (s_push_vy * 200) >> 8;
    if (s_push_frames == 0) { s_push_vx = 0; s_push_vy = 0; }
    return 1;
}

// ---------------------------------------------------------------------------
// 4. Enemy Damage & Death
// ---------------------------------------------------------------------------

static EnemyDeathHook s_enemy_death_hook = NULL;
int g_death_phase = DEATH_ALL;

void enemy_set_death_hook(EnemyDeathHook hook) {
    s_enemy_death_hook = hook;
}

static void enemy_damage(Enemy *e, int damage, fixed hit_vx, fixed hit_vy, int quiet) {
    if (!e || !e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || e->state == ENEMY_STATE_REMATE) return;
#if ENCOUNTERS_PROTO
    if (boss_blocks_damage(e)) return;           // the invulnerable second of a phase change (DESIGN.md 6.13.7)
#endif
    e->hp -= damage;
    dmg_numbers_spawn(e->x, e->y - TO_FIXED(16), damage, quiet ? DMG_NUM_DOT : DMG_NUM_NORMAL);
    if (!quiet) {
        e->hit_timer = 8;
        int hitstop = e->hp <= 0 ? 4 : 3;
        if (g_hitstop_frames < hitstop) g_hitstop_frames = hitstop;
    }
    CRASH_MARK(e->hp <= 0 ? CL_ENEMY_KILL : CL_ENEMY_HIT, e->type, e->hp <= 0 ? e->char_id : e->hp);
    if (e->hp <= 0) {
        if (!quiet) sfx_play(SND_ENEMY_DEATH, TO_INT(e->x));
        if (e->suspend_req) {
            // Viatico: counts as dead now (pack), but stays inert and in place for SUSPEND_FRAMES; the death
            // animation plays when enemy_suspend_update ends it. hp <= 0 keeps every weapon from hitting it again.
            e->suspend_req = 0;
            g_death_phase = DEATH_BOOKKEEPING;
            if (s_enemy_death_hook) s_enemy_death_hook(e, hit_vx, hit_vy);
            g_death_phase = DEATH_ALL;
            e->state = ENEMY_STATE_SUSPENDED;
            e->suspend_timer = SUSPEND_FRAMES;
            e->knock_vx = hit_vx;
            e->knock_vy = hit_vy;
            e->stun_timer = 0;
            e->hit_timer = 0;
            encounters_record_kill(&g_encounter_mgr, e->pack, e->x, e->y);
            return;
        }
        if (s_enemy_death_hook) s_enemy_death_hook(e, hit_vx, hit_vy);
        e->active = 0;
        e->state = ENEMY_STATE_DEAD;
        encounters_record_kill(&g_encounter_mgr, e->pack, e->x, e->y);
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_KILL type=%d hp=0", e->type);
        nocashMessage(msg);
#endif
    } else if (!quiet) {
        // Tambaleo solo por vida baja (DESIGN.md 7.2): ningun golpe lo provoca por si solo; el enemigo se
        // tambalea al quedarle un 25 % de vida o menos, le de lo que le de (rayo, punetazo, zona/quemadura).
        if ((e->type == ENEMY_TYPE_EXVOTO || e->type == ENEMY_TYPE_CHARGER || e->type == ENEMY_TYPE_SHOOTER ||
             e->type == ENEMY_TYPE_BEBE || e->type == ENEMY_TYPE_PARROCO ||
             e->type == ENEMY_TYPE_MONJA || e->type == ENEMY_TYPE_MONAGUILLO) &&
            e->hp * 4 <= e->max_hp &&
            (e->state == ENEMY_STATE_CHASE || e->state == ENEMY_STATE_ATTACK ||
             e->state == ENEMY_STATE_TELEGRAPH || e->state == ENEMY_STATE_CHARGE ||
             e->state == ENEMY_STATE_RECOVER || e->state == ENEMY_STATE_STUNNED ||
             e->state == ENEMY_STATE_WOBBLE)) {
            if (e->state != ENEMY_STATE_WOBBLE) {
                e->state_timer = REMATE_WOBBLE_FRAMES;   // low life: it reels
                sfx_play(SND_WOBBLE_CUE, TO_INT(e->x));
            }
            e->state = ENEMY_STATE_WOBBLE;
            e->aim_px = e->aim_py = 0;                          // a dodge or charge in progress is cancelled
        }
        if (!quiet) {
            sfx_play(SND_ENEMY_HIT, TO_INT(e->x));
#ifdef DEBUG
            char msg[64];
            snprintf(msg, sizeof(msg), "ENEMY_HIT type=%d hp=%d", e->type, e->hp);
            nocashMessage(msg);
#endif
        }
    }
}

// Once a frame: ends the suspended deaths (Viatico): the death animation plays now, the bookkeeping already ran.
void enemy_suspend_update(Enemy *enemies, int max_enemies) {
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->state != ENEMY_STATE_SUSPENDED) continue;
        if (e->suspend_timer > 0) e->suspend_timer--;
        if (e->suspend_timer > 0) continue;
        g_death_phase = DEATH_VISUALS;
        if (s_enemy_death_hook) s_enemy_death_hook(e, e->knock_vx, e->knock_vy);
        g_death_phase = DEATH_ALL;
        e->active = 0;
        e->state = ENEMY_STATE_DEAD;
    }
}

void enemy_hit(Enemy *e, int damage, fixed hit_vx, fixed hit_vy) {
    enemy_damage(e, damage, hit_vx, hit_vy, 0);
}

void enemy_hit_quiet(Enemy *e, int damage) {
    enemy_damage(e, damage, 0, 0, 1);
}

// ---------------------------------------------------------------------------
// Quemado (DESIGN.md 6.12.2, 6.12.10)
// ---------------------------------------------------------------------------

void burn_apply(Enemy *e, int layers) {
    if (!e || !e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE || layers <= 0) return;
    int cap = BURN_BASE_CAP + g_mods.burn_cap_bonus;
    int n = e->burn_layers + layers;
    if (n > cap) n = cap;
    if (e->burn_layers == 0) e->burn_tick = 0;
    e->burn_layers = (uint8_t)n;
    e->burn_timer = (uint16_t)(BURN_BASE_FRAMES + g_mods.burn_dur_bonus);   // every application renews it
}

void burn_clear(Enemy *e) {
    e->burn_layers = 0;
    e->burn_timer = 0;
    e->burn_tick = 0;
}

// Once a frame, outside the AI (the off-screen LOD runs the AI every other frame). Kills by fire go
// through the quiet path, so the death hook (Martirio) still runs without hit stop or sounds.
void burn_update(Enemy *enemies, int max_enemies) {
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->burn_layers) continue;
        if (!e->active || e->hp <= 0) { burn_clear(e); continue; }
        if (e->burn_timer > 0) e->burn_timer--;
        if (e->burn_timer == 0) { burn_clear(e); continue; }
        if (++e->burn_tick >= BURN_TICK_FRAMES) {
            e->burn_tick = 0;
            enemy_hit_quiet(e, upgrades_fire_damage(BURN_TICK_DAMAGE * e->burn_layers));
        }
    }
}
