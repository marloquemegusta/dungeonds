#include "encounters.h"
#include "gameplay.h"
#include "projectiles.h"
#include "weapons.h"
#include "diablo_dungeon.h"
#include "player_sprite.h"
#include <stdio.h>
#include <string.h>

// ---------------------------------------------------------------------------
// 1. Floor Progression Scaling Tables (Fixed-Point 8.8 friendly, integer bounds)
// ---------------------------------------------------------------------------

/* TUNABLE-PLACEHOLDER: Floor Progression Scaling Table */
const FloorDifficultyTuning g_floor_tuning[MAX_FLOOR_LEVELS] = {
    [0] = {
        .floor_index = 0,
        .enemy_count = 3,              /* TUNABLE-PLACEHOLDER: Floor 1 intro wave (3 enemies) */
        .charger_ratio = 33,           /* TUNABLE-PLACEHOLDER: 33% chargers (1 Charger, 2 Shooters) */
        .guaranteed_health_drops = 1,  /* TUNABLE-PLACEHOLDER: 1 guaranteed health pack */
        .guaranteed_ammo_drops = 2     /* TUNABLE-PLACEHOLDER: 2 guaranteed ammo packs */
    },
    [1] = {
        .floor_index = 1,
        .enemy_count = 5,              /* TUNABLE-PLACEHOLDER: Floor 2 wave (5 enemies) */
        .charger_ratio = 40,           /* TUNABLE-PLACEHOLDER: 40% chargers (2 Chargers, 3 Shooters) */
        .guaranteed_health_drops = 1,  /* TUNABLE-PLACEHOLDER: 1 guaranteed health pack */
        .guaranteed_ammo_drops = 2     /* TUNABLE-PLACEHOLDER: 2 guaranteed ammo packs */
    },
    [2] = {
        .floor_index = 2,
        .enemy_count = 7,              /* TUNABLE-PLACEHOLDER: Floor 3 wave (7 enemies) */
        .charger_ratio = 43,           /* TUNABLE-PLACEHOLDER: 43% chargers (3 Chargers, 4 Shooters) */
        .guaranteed_health_drops = 2,  /* TUNABLE-PLACEHOLDER: 2 guaranteed health packs */
        .guaranteed_ammo_drops = 3     /* TUNABLE-PLACEHOLDER: 3 guaranteed ammo packs */
    },
    [3] = {
        .floor_index = 3,
        .enemy_count = 8,              /* TUNABLE-PLACEHOLDER: Floor 4 wave (8 enemies) */
        .charger_ratio = 50,           /* TUNABLE-PLACEHOLDER: 50% chargers (4 Chargers, 4 Shooters) */
        .guaranteed_health_drops = 2,  /* TUNABLE-PLACEHOLDER: 2 guaranteed health packs */
        .guaranteed_ammo_drops = 3     /* TUNABLE-PLACEHOLDER: 3 guaranteed ammo packs */
    },
    [4] = {
        .floor_index = 4,
        .enemy_count = 10,             /* TUNABLE-PLACEHOLDER: Floor 5 max stress wave (10 enemies) */
        .charger_ratio = 60,           /* TUNABLE-PLACEHOLDER: 60% chargers (6 Chargers, 4 Shooters) */
        .guaranteed_health_drops = 2,  /* TUNABLE-PLACEHOLDER: 2 guaranteed health packs */
        .guaranteed_ammo_drops = 4     /* TUNABLE-PLACEHOLDER: 4 guaranteed ammo packs */
    }
};

EncounterManager g_encounter_mgr;

static inline int abs_val(int v) {
    return v < 0 ? -v : v;
}

// ---------------------------------------------------------------------------
// 2. Encounter Initialization
// ---------------------------------------------------------------------------

void encounters_init(EncounterManager *mgr) {
    if (!mgr) return;
    memset(mgr, 0, sizeof(EncounterManager));
    mgr->current_floor = 0;
    mgr->total_cleared_floors = 0;
    mgr->wave_state = ENCOUNTER_STATE_IDLE;
    mgr->wave_index = 0;
    mgr->enemies_total = 0;
    mgr->enemies_remaining = 0;
    mgr->exit_open = 0;
    mgr->exit_x = TO_FIXED(SPAWN_PIXEL_X);
    mgr->exit_y = TO_FIXED(SPAWN_PIXEL_Y - 64);
    mgr->exit_radius = 24;
    mgr->last_kill_x = 0;
    mgr->last_kill_y = 0;
}

// ---------------------------------------------------------------------------
// 3. Spawning Waves
// ---------------------------------------------------------------------------

int encounters_spawn_wave(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                          fixed anchor_x, fixed anchor_y) {
    if (!mgr || !enemies || max_enemies <= 0) return 0;

    // Reset enemies pool
    for (int i = 0; i < max_enemies; i++) {
        enemies[i].active = 0;
        enemies[i].hp = 0;
    }

    // Reset lingering enemy projectiles
    enemy_projectiles_init();

    int floor_idx = mgr->current_floor;
    if (floor_idx < 0) floor_idx = 0;
    if (floor_idx >= MAX_FLOOR_LEVELS) floor_idx = MAX_FLOOR_LEVELS - 1;

    const FloorDifficultyTuning *tuning = &g_floor_tuning[floor_idx];
    int target_count = tuning->enemy_count;
    if (target_count > max_enemies) target_count = max_enemies;

    int num_chargers = (target_count * tuning->charger_ratio + 50) / 100;
    if (num_chargers < 1 && tuning->charger_ratio > 0 && target_count > 0) num_chargers = 1;
    if (num_chargers > target_count) num_chargers = target_count;
    int num_shooters = target_count - num_chargers;

    int anchor_px = TO_INT(anchor_x);
    int anchor_py = TO_INT(anchor_y);
    if (anchor_px == 0 && anchor_py == 0) {
        anchor_px = SPAWN_PIXEL_X;
        anchor_py = SPAWN_PIXEL_Y;
    }

    static const int s_fallback_coords[10][2] = {
        { 380, 227 - 64 }, { 380 + 64, 227 }, { 380 - 64, 227 }, { 380, 227 + 64 },
        { 380 + 48, 227 + 48 }, { 380 - 48, 227 + 48 }, { 380 + 48, 227 - 48 }, { 380 - 48, 227 - 48 },
        { 380 + 96, 227 }, { 380 - 96, 227 }
    };

    int spawned = 0;
    for (int e_idx = 0; e_idx < target_count; e_idx++) {
        Enemy *e = &enemies[e_idx];
        EnemyType type = (e_idx < num_chargers) ? ENEMY_TYPE_CHARGER : ENEMY_TYPE_SHOOTER;
        int char_id = (type == ENEMY_TYPE_CHARGER) ? CHAR_CHARGER : CHAR_SKELETON;

        int found = 0;
        fixed spawn_x = 0, spawn_y = 0;

        // Search concentric rings for valid walkable coordinates
        for (int radius = 64; radius <= 224 && !found; radius += 32) {
            for (int dy = -radius; dy <= radius && !found; dy += 32) {
                for (int dx = -radius; dx <= radius && !found; dx += 32) {
                    if (abs_val(dx) != radius && abs_val(dy) != radius) continue;
                    int cand_px = anchor_px + dx;
                    int cand_py = anchor_py + dy;

                    if (!world_point_has_floor(cand_px, cand_py)) continue;
                    fixed fx = TO_FIXED(cand_px);
                    fixed fy = TO_FIXED(cand_py);
                    if (!position_is_free(fx, fy)) continue;

                    // Ensure spacing between enemies
                    int clear = 1;
                    for (int j = 0; j < spawned; j++) {
                        int edx = cand_px - TO_INT(enemies[j].x);
                        int edy = cand_py - TO_INT(enemies[j].y);
                        if (edx * edx + edy * edy < 36 * 36) {
                            clear = 0;
                            break;
                        }
                    }
                    if (!clear) continue;

                    spawn_x = fx;
                    spawn_y = fy;
                    found = 1;
                }
            }
        }

        // Fallback if spiral search could not find a candidate
        if (!found) {
            int fb_px = s_fallback_coords[e_idx % 10][0];
            int fb_py = s_fallback_coords[e_idx % 10][1];
            spawn_x = TO_FIXED(fb_px);
            spawn_y = TO_FIXED(fb_py);
            found = 1;
        }

        e->x = spawn_x;
        e->y = spawn_y;
        e->active = 1;
        e->type = type;
        e->char_id = char_id;
        e->max_hp = g_enemy_tuning[type].max_hp;
        e->hp = e->max_hp;
        e->dir = (spawned * 2) % 8;
        e->frame = (spawned * 3) % PLAYER_NUM_FRAMES;
        e->anim_timer = 0;
        e->state = ENEMY_STATE_IDLE;
        e->state_timer = 0;
        e->hit_timer = 0;
        e->last_seen_x = 0;
        e->last_seen_y = 0;
        e->los_lost_timer = 0;
        e->burst_shots_left = 0;
        e->burst_interval_timer = 0;
        e->strafe_dir = (spawned & 1) ? 1 : -1;
        e->step_count = 0;
        e->step_limit = 60 + spawned * 15;
        e->has_los = 0;
        e->stagger_slot = spawned % 2;
        spawned++;
    }

    mgr->enemies_total = spawned;
    mgr->enemies_remaining = spawned;
    mgr->wave_state = ENCOUNTER_STATE_ACTIVE;
    mgr->exit_open = 0;
    mgr->wave_index++;

    char msg[128];
    snprintf(msg, sizeof(msg), "ENCOUNTER_WAVE_START floor=%d enemies=%d chargers=%d shooters=%d",
             mgr->current_floor + 1, spawned, num_chargers, num_shooters);
    nocashMessage(msg);

    return spawned;
}

// ---------------------------------------------------------------------------
// 4. Rewards & Floor Progression
// ---------------------------------------------------------------------------

static void drop_encounter_rewards(const EncounterManager *mgr) {
    int floor_idx = mgr->current_floor;
    if (floor_idx < 0) floor_idx = 0;
    if (floor_idx >= MAX_FLOOR_LEVELS) floor_idx = MAX_FLOOR_LEVELS - 1;

    const FloorDifficultyTuning *tuning = &g_floor_tuning[floor_idx];

    fixed base_x = mgr->last_kill_x ? mgr->last_kill_x : TO_FIXED(SPAWN_PIXEL_X);
    fixed base_y = mgr->last_kill_y ? mgr->last_kill_y : TO_FIXED(SPAWN_PIXEL_Y);

    static const int drop_offsets[8][2] = {
        { -16, 0 }, { 16, 0 }, { 0, -16 }, { 0, 16 },
        { -16, -16 }, { 16, -16 }, { -16, 16 }, { 16, 16 }
    };
    int offset_idx = 0;

    // Guaranteed health drops
    for (int h = 0; h < tuning->guaranteed_health_drops; h++) {
        fixed dx = TO_FIXED(drop_offsets[offset_idx % 8][0]);
        fixed dy = TO_FIXED(drop_offsets[offset_idx % 8][1]);
        offset_idx++;
        fixed drop_x = base_x + dx;
        fixed drop_y = base_y + dy;
        if (!position_is_free(drop_x, drop_y)) {
            drop_x = base_x;
            drop_y = base_y;
        }
        pickup_spawn(PICKUP_HEALTH, drop_x, drop_y, PICKUP_HEALTH_AMOUNT);
    }

    // Guaranteed ammo drops
    static const PickupType ammo_types[3] = {
        PICKUP_AMMO_SHOTGUN,
        PICKUP_AMMO_GATLING,
        PICKUP_AMMO_HEAVY
    };
    for (int a = 0; a < tuning->guaranteed_ammo_drops; a++) {
        fixed dx = TO_FIXED(drop_offsets[offset_idx % 8][0]);
        fixed dy = TO_FIXED(drop_offsets[offset_idx % 8][1]);
        offset_idx++;
        fixed drop_x = base_x + dx;
        fixed drop_y = base_y + dy;
        if (!position_is_free(drop_x, drop_y)) {
            drop_x = base_x;
            drop_y = base_y;
        }
        PickupType type = ammo_types[a % 3];
        int amount = (type == PICKUP_AMMO_SHOTGUN) ? 10 :
                     (type == PICKUP_AMMO_GATLING) ? 40 : 5;
        pickup_spawn(type, drop_x, drop_y, amount);
    }
}

void encounters_record_kill(EncounterManager *mgr, fixed x, fixed y) {
    if (!mgr) return;
    mgr->last_kill_x = x;
    mgr->last_kill_y = y;
}

int encounters_advance_floor(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                             fixed player_x, fixed player_y) {
    if (!mgr) return 0;

    mgr->total_cleared_floors++;
    if (mgr->current_floor < MAX_FLOOR_LEVELS - 1) {
        mgr->current_floor++;
    } else {
        mgr->current_floor = MAX_FLOOR_LEVELS - 1; // Stay at max difficulty
    }
    mgr->exit_open = 0;

    char msg[128];
    snprintf(msg, sizeof(msg), "ENCOUNTER_FLOOR_ADVANCE floor=%d total_cleared=%d",
             mgr->current_floor + 1, mgr->total_cleared_floors);
    nocashMessage(msg);

    return encounters_spawn_wave(mgr, enemies, max_enemies, player_x, player_y);
}

// ---------------------------------------------------------------------------
// 5. Per-frame Update & Exit Handling
// ---------------------------------------------------------------------------

void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                       PlayerState *player, fixed player_x, fixed player_y) {
    (void)player;
    if (!mgr || !enemies || max_enemies <= 0) return;

    if (mgr->wave_state == ENCOUNTER_STATE_ACTIVE) {
        int alive_count = 0;
        for (int i = 0; i < max_enemies; i++) {
            if (enemies[i].active && enemies[i].hp > 0) {
                alive_count++;
            }
        }
        mgr->enemies_remaining = alive_count;

        if (alive_count == 0) {
            // Wave cleared!
            mgr->wave_state = ENCOUNTER_STATE_CLEARED;
            mgr->exit_open = 1;

            // Place exit tile at walkable point north of room center
            fixed exit_x = TO_FIXED(SPAWN_PIXEL_X);
            fixed exit_y = TO_FIXED(SPAWN_PIXEL_Y - 64);
            if (!position_is_free(exit_x, exit_y)) {
                exit_x = TO_FIXED(SPAWN_PIXEL_X + 64);
                exit_y = TO_FIXED(SPAWN_PIXEL_Y);
            }
            mgr->exit_x = exit_x;
            mgr->exit_y = exit_y;
            mgr->exit_radius = 24;

            drop_encounter_rewards(mgr);

            char msg[128];
            snprintf(msg, sizeof(msg), "ENCOUNTER_CLEARED floor=%d exit=%d,%d",
                     mgr->current_floor + 1, TO_INT(mgr->exit_x), TO_INT(mgr->exit_y));
            nocashMessage(msg);
        }
    } else if (mgr->wave_state == ENCOUNTER_STATE_CLEARED && mgr->exit_open) {
        // Check if player reaches exit tile
        int pdx = TO_INT(player_x - mgr->exit_x);
        int pdy = TO_INT(player_y - mgr->exit_y);
        int exit_r = mgr->exit_radius > 0 ? mgr->exit_radius : 20;

        if (pdx * pdx + pdy * pdy <= exit_r * exit_r) {
            encounters_advance_floor(mgr, enemies, max_enemies, player_x, player_y);
        }
    }
}

// ---------------------------------------------------------------------------
// 6. Exit Portal Rendering
// ---------------------------------------------------------------------------

void encounters_render(const EncounterManager *mgr, uint16_t *buffer, int cam_x, int cam_y) {
    if (!mgr || !mgr->exit_open || !buffer) return;

    int sx = TO_INT(mgr->exit_x) - cam_x;
    int sy = TO_INT(mgr->exit_y) - cam_y;

    if (sx < 12 || sx >= SCREEN_W - 12 || sy < 12 || sy >= SCREEN_H - 12) return;

    // Draw glowing runic circle / portal (radius 8-10) in BGR555
    static const uint16_t portal_outer = RGB15(0, 31, 31) | BIT(15);   // Cyan
    static const uint16_t portal_ring  = RGB15(31, 28, 8) | BIT(15);   // Gold
    static const uint16_t portal_core  = RGB15(26, 18, 31) | BIT(15);  // Violet

    for (int dy = -8; dy <= 8; dy++) {
        for (int dx = -8; dx <= 8; dx++) {
            int d2 = dx * dx + dy * dy;
            if (d2 <= 64) {
                int px = sx + dx;
                int py = sy + dy;
                if (px >= 0 && px < SCREEN_W && py >= 0 && py < SCREEN_H) {
                    uint16_t col;
                    if (d2 >= 42) col = portal_ring;
                    else if (d2 >= 16) col = portal_outer;
                    else col = portal_core;
                    buffer[py * SCREEN_W + px] = col;
                }
            }
        }
    }
}
