#include "gameplay.h"
#include "crashlog.h"
#include "encounters.h"
#include "diablo_dungeon.h"
#include <string.h>

// ---------------------------------------------------------------------------
// 1. Fixed-Point 8.8 Tuning Tables
// ---------------------------------------------------------------------------

const EnemyTuning g_enemy_tuning[NUM_ENEMY_TYPES] = {
    [ENEMY_TYPE_NONE] = { 0 },
    [ENEMY_TYPE_CHARGER] = {
        .max_hp = 60,             // [TUNABLE-PLACEHOLDER] high HP (~3x shooter)
        .speed = 163,             // [TUNABLE-PLACEHOLDER] 8.8 fixed (~90% of player speed 181)
        .contact_damage = 15,     // [TUNABLE-PLACEHOLDER] moderate melee bite
        .attack_cooldown = 30,    // [TUNABLE-PLACEHOLDER] frames between melee attacks
        .preferred_dist_min = 0,
        .preferred_dist_max = 16, // [TUNABLE-PLACEHOLDER] melee engagement range (px)
        .los_range = 160,         // [TUNABLE-PLACEHOLDER] LOS detection range (px)
        .alert_duration = 20,     // [TUNABLE-PLACEHOLDER] frames in ALERT (0.33s)
        .search_duration = 90,    // [TUNABLE-PLACEHOLDER] frames in SEARCH (1.5s)
        .los_lost_limit = 180,    // [TUNABLE-PLACEHOLDER] frames without LOS before SEARCH (3s)
        .position_duration = 0,
        .aim_duration = 0,
        .burst_count = 0,
        .burst_interval = 0,
        .projectile_speed = 0,
        .projectile_damage = 0
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
// 4. World Collision
//
// The baked grid is the only walkability source: the lab exports floor that is
// reachable and free of any geometry inside the body slab, so dark render
// pixels never act as invisible walls.
// ---------------------------------------------------------------------------

static inline uint8_t world_collision_flags(int cx, int cy) {
    uint32_t index = (uint32_t)cy * COLLISION_W + (uint32_t)cx;
    return (g_dungeon_collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

// The body footprint is a circle on the ground (radius 6), which the 2:1
// projection turns into an ellipse of 6 x 3 screen pixels.
int position_is_free(fixed x, fixed y) {
    int wx = (int)(x >> FIXED_SHIFT);
    int wy = (int)(y >> FIXED_SHIFT);
    const int radius = 6;
    const int radius_y = radius >> GROUND_Y_SHIFT;
    if (wx - radius < 0 || wy - radius_y < 0) return 0;

    int cell_x0 = (wx - radius) / COLLISION_SCALE;
    int cell_x1 = (wx + radius) / COLLISION_SCALE;
    int cell_y0 = (wy - radius_y) / COLLISION_SCALE;
    int cell_y1 = (wy + radius_y) / COLLISION_SCALE;
    const int radius_sq = radius * radius;
    for (int cy = cell_y0; cy <= cell_y1; cy++) {
        for (int cx = cell_x0; cx <= cell_x1; cx++) {
            if (cx < 0 || cx >= COLLISION_W || cy < 0 || cy >= COLLISION_H) return 0;
            if ((world_collision_flags(cx, cy) & 0x01) == 0) continue;
            int left = cx * COLLISION_SCALE;
            int top = cy * COLLISION_SCALE;
            int nearest_x = wx < left ? left : (wx > left + COLLISION_SCALE - 1 ? left + COLLISION_SCALE - 1 : wx);
            int nearest_y = wy < top ? top : (wy > top + COLLISION_SCALE - 1 ? top + COLLISION_SCALE - 1 : wy);
            int dx = wx - nearest_x;
            int dy = wy - nearest_y;
            if (dx * dx + GROUND_DY2(dy) <= radius_sq) return 0;
        }
    }
    return 1;
}

int bullet_position_is_free(fixed x, fixed y) {
    int px = (int)(x >> FIXED_SHIFT);
    int py = (int)(y >> FIXED_SHIFT);
    if (px < 0 || py < 0) return 0;
    int cx = px / COLLISION_SCALE;
    int cy = py / COLLISION_SCALE;
    if (cx < 0 || cx >= COLLISION_W || cy < 0 || cy >= COLLISION_H) return 0;
    return (world_collision_flags(cx, cy) & 0x02) == 0;
}

// Sweep in <=1px increments so a frame cannot skip a thin blocked cell.
// Incremental 32-bit interpolation: next = start + trunc(d * step / steps) is
// evaluated as q * step + floor(|r| * step / steps) (q = d / steps, r = d % steps),
// carrying the fractional part with a Bresenham accumulator. No division per
// step and no int64 (software on ARM9).
int sweep_position(fixed *x, fixed *y, fixed dx, fixed dy) {
    fixed start_x = *x, start_y = *y;
    int ax = dx < 0 ? -dx : dx;
    int ay = dy < 0 ? -dy : dy;
    int major = ax > ay ? ax : ay;
    int steps = (major + 255) / 256;
    if (steps < 1) steps = 1;

    fixed qx = dx / steps, qy = dy / steps;
    int rx = (dx % steps) < 0 ? -(dx % steps) : (dx % steps);
    int ry = (dy % steps) < 0 ? -(dy % steps) : (dy % steps);
    int sgn_x = dx < 0 ? -1 : 1, sgn_y = dy < 0 ? -1 : 1;
    int acc_x = 0, acc_y = 0;
    fixed off_x = 0, off_y = 0;
    for (int step = 1; step <= steps; step++) {
        off_x += qx;
        off_y += qy;
        acc_x += rx;
        if (acc_x >= steps) { acc_x -= steps; off_x += sgn_x; }
        acc_y += ry;
        if (acc_y >= steps) { acc_y -= steps; off_y += sgn_y; }
        if (!position_is_free(start_x + off_x, start_y + off_y)) return 0;
    }
    *x = start_x + dx;
    *y = start_y + dy;
    return 1;
}

// ---------------------------------------------------------------------------
// 5. Enemy Damage & Death
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
