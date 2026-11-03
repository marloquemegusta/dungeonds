#include "gameplay.h"
#include "crashlog.h"
#include "encounters.h"
#include "collision.h"
#include <string.h>

// ---------------------------------------------------------------------------
// 1. Fixed-Point 8.8 Tuning Tables
// ---------------------------------------------------------------------------

const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES] = {
    [ENEMY_TYPE_NONE] = { 0 },
    [ENEMY_TYPE_CHARGER] = {
        .max_hp = 60,             // [TUNABLE-PLACEHOLDER] 2 sniper hits (30 each)
        .speed = 293,             // [TUNABLE-PLACEHOLDER] 8.8 fixed: ~90% of the hero's 326 (g_characters)
        .contact_damage = 1,      // one hit (the player has PLAYER_MAX_HP hits)
        .attack_cooldown = 30,    // [TUNABLE-PLACEHOLDER] frames between bites
        .preferred_dist_min = 0,
        .preferred_dist_max = 16, // [TUNABLE-PLACEHOLDER] melee range (ground px)
    },
    [ENEMY_TYPE_SHOOTER] = {
        .max_hp = 20,             // [TUNABLE-PLACEHOLDER] low HP
        .speed = 120,             // [TUNABLE-PLACEHOLDER] slower positioning speed (0.47 px/f)
        .contact_damage = 5,      // [TUNABLE-PLACEHOLDER] weak contact
        .attack_cooldown = 60,    // [TUNABLE-PLACEHOLDER] burst cooldown (1s)
        .preferred_dist_min = 40, // [TUNABLE-PLACEHOLDER] distance band min (px)
        .preferred_dist_max = 80, // [TUNABLE-PLACEHOLDER] distance band max (px)
        .los_range = 180,         // [TUNABLE-PLACEHOLDER] LOS detection range (px)
        .alert_duration = 25,     // [TUNABLE-PLACEHOLDER] frames in ALERT (0.4s)
        .search_duration = 90,    // [TUNABLE-PLACEHOLDER] frames in SEARCH (1.5s)
        .los_lost_limit = 180,    // [TUNABLE-PLACEHOLDER] frames without LOS before SEARCH (3s)
        .position_duration = 35,  // [TUNABLE-PLACEHOLDER] frames in POSITION before AIM
        .aim_duration = 25,       // [TUNABLE-PLACEHOLDER] frames in AIM before BURST (0.4s)
        .burst_count = 3,         // [TUNABLE-PLACEHOLDER] 3 projectiles per burst
        .burst_interval = 10,     // [TUNABLE-PLACEHOLDER] frames between shots (0.16s)
        .projectile_speed = 384,  // [TUNABLE-PLACEHOLDER] 8.8 fixed: 1.5 px/frame (slow)
        .projectile_damage = 8    // [TUNABLE-PLACEHOLDER] damage per projectile
    }
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
    player->max_hp = PLAYER_MAX_HP;
    player->hp = PLAYER_MAX_HP;
    player->current_weapon = WEAPON_SHOTGUN;
    player->is_dead = 0;
    player->invuln_timer = 0;
}

int player_take_hit(PlayerState *player) {
    if (!player || player->is_dead || player->god_mode || player->invuln_timer > 0) return 0;
    player->hp--;
    player->invuln_timer = PLAYER_IFRAMES;
    if (player->hp <= 0) {
        player->hp = 0;
        player->is_dead = 1;
    }
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
        if (s_enemy_death_hook) s_enemy_death_hook(e, hit_vx, hit_vy);
        e->active = 0;
        e->state = ENEMY_STATE_DEAD;
        encounters_record_kill(&g_encounter_mgr, e->x, e->y);
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_KILL type=%d hp=0", e->type);
        nocashMessage(msg);
#endif
    } else {
#ifdef DEBUG
        char msg[64];
        snprintf(msg, sizeof(msg), "ENEMY_HIT type=%d hp=%d", e->type, e->hp);
        nocashMessage(msg);
#endif
    }
}
