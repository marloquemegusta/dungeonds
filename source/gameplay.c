#include "gameplay.h"
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

const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES] = {
    [WEAPON_PISTOL] = {
        .damage_per_hit = 8,      // [TUNABLE] low damage
        .pellets = 1,
        .fire_cooldown = 18,      // [TUNABLE] low fire rate
        .max_ammo = 0,            // [TUNABLE] 0 = infinite fallback
        .pickup_ammo_amount = 0
    },
    [WEAPON_SHOTGUN] = {
        .damage_per_hit = 6,      // [TUNABLE] 6 dmg * 5 pellets = 30 max dmg
        .pellets = 5,
        .fire_cooldown = 40,      // [TUNABLE] marked recoil/pump cooldown
        .max_ammo = 50,           // [TUNABLE] medium ammo
        .pickup_ammo_amount = 10  // [TUNABLE] shells per box
    },
    [WEAPON_GATLING] = {
        .damage_per_hit = 5,      // [TUNABLE] sustained rapid damage
        .pellets = 1,
        .fire_cooldown = 4,       // [TUNABLE] fast fire rate
        .max_ammo = 200,          // [TUNABLE] high ammo capacity
        .pickup_ammo_amount = 40  // [TUNABLE] belt per box
    },
    [WEAPON_HEAVY] = {
        .damage_per_hit = 45,     // [TUNABLE] heavy punch
        .pellets = 1,
        .fire_cooldown = 60,      // [TUNABLE] slow reload
        .max_ammo = 20,           // [TUNABLE] scarce ammo
        .pickup_ammo_amount = 5   // [TUNABLE] rockets per box
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
// 3. Player State & Damage (Doom-style 1/3 armor absorption)
// ---------------------------------------------------------------------------

PlayerState g_player_state;

void player_state_init(PlayerState *player) {
    if (!player) return;
    player->max_hp = PLAYER_MAX_HP;
    player->hp = PLAYER_MAX_HP;
    player->max_armor = PLAYER_MAX_ARMOR;
    player->armor = 0;
    player->current_weapon = WEAPON_PISTOL;
    player->is_dead = 0;
    player->invuln_timer = 0;
    for (int i = 0; i < NUM_WEAPON_TYPES; i++) {
        player->ammo[i] = g_weapon_tuning[i].max_ammo > 0 ? (g_weapon_tuning[i].max_ammo / 4) : 0;
    }
}

void player_apply_damage(PlayerState *player, int damage) {
    if (!player || player->is_dead || damage <= 0) return;

    int absorbed = 0;
    if (player->armor > 0) {
        absorbed = damage / 3;
        if (absorbed > player->armor) absorbed = player->armor;
        player->armor -= absorbed;
    }

    int hp_damage = damage - absorbed;
    player->hp -= hp_damage;
    if (player->hp <= 0) {
        player->hp = 0;
        player->is_dead = 1;
    }
}

// ---------------------------------------------------------------------------
// 4. Pickup Pool & Collection
// ---------------------------------------------------------------------------

Pickup g_pickups[MAX_PICKUPS];

void pickups_init(void) {
    for (int i = 0; i < MAX_PICKUPS; i++) {
        g_pickups[i].active = 0;
        g_pickups[i].type = PICKUP_NONE;
        g_pickups[i].x = 0;
        g_pickups[i].y = 0;
        g_pickups[i].amount = 0;
    }
}

Pickup *pickup_spawn(PickupType type, fixed x, fixed y, int amount) {
    for (int i = 0; i < MAX_PICKUPS; i++) {
        if (!g_pickups[i].active) {
            g_pickups[i].active = 1;
            g_pickups[i].type = type;
            g_pickups[i].x = x;
            g_pickups[i].y = y;
            g_pickups[i].amount = amount;
            return &g_pickups[i];
        }
    }
    return NULL;
}

int player_collect_pickup(PlayerState *player, Pickup *pickup) {
    if (!player || !pickup || !pickup->active || player->is_dead) return 0;

    switch (pickup->type) {
        case PICKUP_HEALTH:
            if (player->hp >= player->max_hp) return 0;
            player->hp += pickup->amount > 0 ? pickup->amount : PICKUP_HEALTH_AMOUNT;
            if (player->hp > player->max_hp) player->hp = player->max_hp;
            return 1;

        case PICKUP_ARMOR:
            if (player->armor >= player->max_armor) return 0;
            player->armor += pickup->amount > 0 ? pickup->amount : PICKUP_ARMOR_AMOUNT;
            if (player->armor > player->max_armor) player->armor = player->max_armor;
            return 1;

        case PICKUP_AMMO_SHOTGUN: {
            int max = g_weapon_tuning[WEAPON_SHOTGUN].max_ammo;
            if (player->ammo[WEAPON_SHOTGUN] >= max) return 0;
            player->ammo[WEAPON_SHOTGUN] += pickup->amount > 0 ? pickup->amount : g_weapon_tuning[WEAPON_SHOTGUN].pickup_ammo_amount;
            if (player->ammo[WEAPON_SHOTGUN] > max) player->ammo[WEAPON_SHOTGUN] = max;
            return 1;
        }

        case PICKUP_AMMO_GATLING: {
            int max = g_weapon_tuning[WEAPON_GATLING].max_ammo;
            if (player->ammo[WEAPON_GATLING] >= max) return 0;
            player->ammo[WEAPON_GATLING] += pickup->amount > 0 ? pickup->amount : g_weapon_tuning[WEAPON_GATLING].pickup_ammo_amount;
            if (player->ammo[WEAPON_GATLING] > max) player->ammo[WEAPON_GATLING] = max;
            return 1;
        }

        case PICKUP_AMMO_HEAVY: {
            int max = g_weapon_tuning[WEAPON_HEAVY].max_ammo;
            if (player->ammo[WEAPON_HEAVY] >= max) return 0;
            player->ammo[WEAPON_HEAVY] += pickup->amount > 0 ? pickup->amount : g_weapon_tuning[WEAPON_HEAVY].pickup_ammo_amount;
            if (player->ammo[WEAPON_HEAVY] > max) player->ammo[WEAPON_HEAVY] = max;
            return 1;
        }

        default:
            return 0;
    }
}

int pickups_update_collection(PlayerState *player, fixed player_x, fixed player_y) {
    if (!player || player->is_dead) return 0;
    int collected = 0;
    fixed r_fixed = TO_FIXED(PICKUP_COLLECT_RADIUS_PX);
    int32_t r2 = (r_fixed >> 4) * (r_fixed >> 4);

    for (int i = 0; i < MAX_PICKUPS; i++) {
        Pickup *p = &g_pickups[i];
        if (!p->active) continue;
        fixed dx = (p->x - player_x) >> 4;
        fixed dy = (p->y - player_y) >> 4;
        if (dx * dx + dy * dy <= r2) {
            if (player_collect_pickup(player, p)) {
                p->active = 0;
                collected++;
            }
        }
    }
    return collected;
}

// ---------------------------------------------------------------------------
// 5. Pickup Rendering (8x8 Icons)
// ---------------------------------------------------------------------------

#define C_RED_BORDER   (RGB15(15,0,0) | BIT(15))
#define C_RED_CROSS    (RGB15(31,0,0) | BIT(15))
#define C_WHITE        (RGB15(31,31,31) | BIT(15))

#define C_GREEN_BORDER (RGB15(0,16,0) | BIT(15))
#define C_GREEN_SHIELD (RGB15(0,31,0) | BIT(15))
#define C_GREEN_LIGHT  (RGB15(16,31,16) | BIT(15))

#define C_AMMO_SHELL_B (RGB15(16,8,0) | BIT(15))
#define C_AMMO_SHELL   (RGB15(31,12,0) | BIT(15))
#define C_AMMO_GAT_B   (RGB15(0,8,20) | BIT(15))
#define C_AMMO_GAT     (RGB15(0,24,31) | BIT(15))
#define C_AMMO_HVY_B   (RGB15(16,0,24) | BIT(15))
#define C_AMMO_HVY     (RGB15(31,24,0) | BIT(15))

static const uint16_t s_icon_health[64] = {
    C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER,
    C_RED_BORDER, C_WHITE,      C_WHITE,      C_RED_CROSS,  C_RED_CROSS,  C_WHITE,      C_WHITE,      C_RED_BORDER,
    C_RED_BORDER, C_WHITE,      C_WHITE,      C_RED_CROSS,  C_RED_CROSS,  C_WHITE,      C_WHITE,      C_RED_BORDER,
    C_RED_BORDER, C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_BORDER,
    C_RED_BORDER, C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_CROSS,  C_RED_BORDER,
    C_RED_BORDER, C_WHITE,      C_WHITE,      C_RED_CROSS,  C_RED_CROSS,  C_WHITE,      C_WHITE,      C_RED_BORDER,
    C_RED_BORDER, C_WHITE,      C_WHITE,      C_RED_CROSS,  C_RED_CROSS,  C_WHITE,      C_WHITE,      C_RED_BORDER,
    C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER, C_RED_BORDER
};

static const uint16_t s_icon_armor[64] = {
    0,              0,              C_GREEN_BORDER, C_GREEN_BORDER, C_GREEN_BORDER, C_GREEN_BORDER, 0,              0,
    0,              C_GREEN_BORDER, C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_BORDER, 0,
    C_GREEN_BORDER, C_GREEN_SHIELD, C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_LIGHT,  C_GREEN_SHIELD, C_GREEN_BORDER,
    C_GREEN_BORDER, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_BORDER,
    C_GREEN_BORDER, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_BORDER,
    0,              C_GREEN_BORDER, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_BORDER, 0,
    0,              0,              C_GREEN_BORDER, C_GREEN_SHIELD, C_GREEN_SHIELD, C_GREEN_BORDER, 0,              0,
    0,              0,              0,              C_GREEN_BORDER, C_GREEN_BORDER, 0,              0,              0
};

static const uint16_t s_icon_shotgun[64] = {
    C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B, C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL,   C_AMMO_SHELL_B,
    C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B, C_AMMO_SHELL_B
};

static const uint16_t s_icon_gatling[64] = {
    C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT_B, C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT,   C_AMMO_GAT,   C_AMMO_GAT,   C_AMMO_GAT,   C_AMMO_GAT,   C_AMMO_GAT,   C_AMMO_GAT_B,
    C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B, C_AMMO_GAT_B
};

static const uint16_t s_icon_heavy[64] = {
    0,            0,            0,            C_AMMO_HVY_B, C_AMMO_HVY_B, 0,            0,            0,
    0,            0,            C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, 0,            0,
    0,            C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, 0,
    0,            C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, 0,
    0,            C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, 0,
    C_AMMO_HVY_B, C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, C_AMMO_HVY_B,
    C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY,   C_AMMO_HVY_B, C_AMMO_HVY,   C_AMMO_HVY_B,
    C_AMMO_HVY_B, 0,            C_AMMO_HVY_B, 0,            0,            C_AMMO_HVY_B, 0,            C_AMMO_HVY_B
};

void pickups_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;

    for (int i = 0; i < MAX_PICKUPS; i++) {
        Pickup *p = &g_pickups[i];
        if (!p->active) continue;

        int px = TO_INT(p->x);
        int py = TO_INT(p->y);
        int sx = px - cam_x - 4;
        int sy = py - cam_y - 4;

        if (sx < -8 || sx >= SCREEN_W || sy < -8 || sy >= SCREEN_H) continue;

        const uint16_t *icon = NULL;
        switch (p->type) {
            case PICKUP_HEALTH:       icon = s_icon_health; break;
            case PICKUP_ARMOR:        icon = s_icon_armor; break;
            case PICKUP_AMMO_SHOTGUN: icon = s_icon_shotgun; break;
            case PICKUP_AMMO_GATLING: icon = s_icon_gatling; break;
            case PICKUP_AMMO_HEAVY:   icon = s_icon_heavy; break;
            default: break;
        }
        if (!icon) continue;

        for (int iy = 0; iy < 8; iy++) {
            int dy = sy + iy;
            if (dy < 0 || dy >= SCREEN_H) continue;
            for (int ix = 0; ix < 8; ix++) {
                int dx = sx + ix;
                if (dx < 0 || dx >= SCREEN_W) continue;
                uint16_t col = icon[iy * 8 + ix];
                if (col != 0) {
                    buffer[dy * SCREEN_W + dx] = col;
                }
            }
        }
    }
}
