#include "gameplay.h"
#include "crashlog.h"
#include "encounters.h"
#include "boss.h"
#include "collision.h"
#include "modifiers.h"
#include "upgrades.h"
#include "sfx.h"
#include "remate.h"
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

void player_state_init(PlayerState *player) {
    if (!player) return;
    player->max_hp = PLAYER_MAX_HP + g_mods.max_hp;
    player->hp = player->max_hp;
    player->current_weapon = WEAPON_SNIPER;  // the sacred ray is the hero's only weapon (DESIGN.md 6.9.1c)
    player->is_dead = 0;
    player->invuln_timer = 0;
}

int player_take_hit(PlayerState *player) {
    if (!player || player->is_dead || player->god_mode || player->invuln_timer > 0 || remate_invuln() > 0) return 0;
    player->hp--;
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
        if ((e->type == ENEMY_TYPE_EXVOTO || e->type == ENEMY_TYPE_CHARGER || e->type == ENEMY_TYPE_SHOOTER) && e->hp * 2 <= e->max_hp &&
            (e->state == ENEMY_STATE_CHASE || e->state == ENEMY_STATE_ATTACK ||
             e->state == ENEMY_STATE_TELEGRAPH || e->state == ENEMY_STATE_CHARGE ||
             e->state == ENEMY_STATE_RECOVER || e->state == ENEMY_STATE_STUNNED ||
             e->state == ENEMY_STATE_WOBBLE)) {
            if (e->state != ENEMY_STATE_WOBBLE) e->state_timer = REMATE_WOBBLE_FRAMES;   // a hit that does not kill leaves it reeling
            e->state = ENEMY_STATE_WOBBLE;
            e->aim_px = e->aim_py = 0;                          // a dodge or charge in progress is cancelled
        }
        sfx_play(SND_ENEMY_HIT, TO_INT(e->x));
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_HIT type=%d hp=%d", e->type, e->hp);
        nocashMessage(msg);
#endif
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
