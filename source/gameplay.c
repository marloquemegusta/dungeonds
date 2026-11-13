#include "gameplay.h"
#include "crashlog.h"
#include "encounters.h"
#include "collision.h"
#include "modifiers.h"
#include "sfx.h"
#include <string.h>

// ---------------------------------------------------------------------------
// 1. Fixed-Point 8.8 Tuning Tables
// ---------------------------------------------------------------------------

const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES] = {
    [ENEMY_TYPE_NONE] = { 0 },
    [ENEMY_TYPE_CHARGER] = {
        .max_hp = 300,            // [TUNABLE-PLACEHOLDER] scale 100 = 1.0 (was 60): 2 sniper hits (150 each)
        .speed = 150,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: slow approach (the 0.3 charger ran at 293)
        .telegraph_duration = 30, // [TUNABLE-PLACEHOLDER] frames standing still and blinking before the lunge
        .charge_speed = 650,      // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~2 x the hero (326), straight line
    },
    [ENEMY_TYPE_SHOOTER] = {
        .max_hp = 200,            // [TUNABLE-PLACEHOLDER] scale 100 = 1.0 (was 20)
        .speed = 180,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~55% of the hero, enough to back off
        .attack_cooldown = 90,    // [TUNABLE-PLACEHOLDER] frames of cooldown after the laser fires (was 70 between bursts)
        .preferred_dist_min = 56, // [TUNABLE-PLACEHOLDER] band: backs off closer than this (ground px)
        .preferred_dist_max = 104,// [TUNABLE-PLACEHOLDER] closes in beyond this (ground px)
        .position_duration = 30,  // [TUNABLE-PLACEHOLDER] frames settling before it starts a laser
    },
    [ENEMY_TYPE_SKELETON] = {
        .max_hp = 100,            // [TUNABLE-PLACEHOLDER] scale 100 = 1.0: dies to one sniper hit or a point-blank shotgun
        .speed = 130,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~40% of the hero's 326
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
    player->current_weapon = WEAPON_SHOTGUN;
    player->is_dead = 0;
    player->invuln_timer = 0;
}

int player_take_hit(PlayerState *player) {
    if (!player || player->is_dead || player->god_mode || player->invuln_timer > 0) return 0;
    player->hp--;
    player->invuln_timer = PLAYER_IFRAMES + g_mods.iframes;
    if (player->hp <= 0) {
        player->hp = 0;
        player->is_dead = 1;
        sfx_stop_charge();
    }
    sfx_play(SND_PLAYER_HURT, -1);
    return 1;
}

// ---------------------------------------------------------------------------
// 4. Enemy Damage & Death
// ---------------------------------------------------------------------------

static EnemyDeathHook s_enemy_death_hook = NULL;

void enemy_set_death_hook(EnemyDeathHook hook) {
    s_enemy_death_hook = hook;
}

void enemy_hit(Enemy *e, int damage, fixed hit_vx, fixed hit_vy) {
    if (!e || !e->active || e->hp <= 0) return;
    e->hp -= damage;
    e->hit_timer = 8;
    int hitstop = e->hp <= 0 ? 4 : 3;
    if (g_hitstop_frames < hitstop) g_hitstop_frames = hitstop;
    CRASH_MARK(e->hp <= 0 ? CL_ENEMY_KILL : CL_ENEMY_HIT, e->type, e->hp <= 0 ? e->char_id : e->hp);
    if (e->hp <= 0) {
        sfx_play(SND_ENEMY_DEATH, TO_INT(e->x));
        if (s_enemy_death_hook) s_enemy_death_hook(e, hit_vx, hit_vy);
        e->active = 0;
        e->state = ENEMY_STATE_DEAD;
        encounters_record_kill(&g_encounter_mgr, e->pack, e->x, e->y);
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_KILL type=%d hp=0", e->type);
        nocashMessage(msg);
#endif
    } else {
        sfx_play(SND_ENEMY_HIT, TO_INT(e->x));
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_HIT type=%d hp=%d", e->type, e->hp);
        nocashMessage(msg);
#endif
    }
}
