#include "encounters.h"
#include "arena.h"
#include "gameplay.h"
#include "projectiles.h"
#include "player_sprite.h"
#include <string.h>

EncounterManager g_encounter_mgr;

_Static_assert(ARENA_ENEMY_CHARGER == ENEMY_TYPE_CHARGER && ARENA_ENEMY_SHOOTER == ENEMY_TYPE_SHOOTER,
               "arena enemy codes must match EnemyType");

void encounters_init(EncounterManager *mgr) {
    memset(mgr, 0, sizeof(EncounterManager));
    mgr->state = ENCOUNTER_STATE_ACTIVE;
}

int encounters_next_arena(const EncounterManager *mgr) {
    return (mgr->arena + 1) % g_num_arenas;
}

int encounters_spawn(EncounterManager *mgr, Enemy *enemies, int max_enemies) {
    if (!mgr || !enemies || max_enemies <= 0 || !g_arena) return 0;

    for (int i = 0; i < max_enemies; i++) {
        enemies[i].active = 0;
        enemies[i].hp = 0;
    }
    enemy_projectiles_init();

    int spawned = 0;
    for (int i = 0; i < g_arena->num_enemies && spawned < max_enemies; i++) {
        const ArenaEnemy *spec = &g_arena->enemies[i];
        EnemyType type = (EnemyType)spec->type;
        Enemy *e = &enemies[spawned];
        e->x = TO_FIXED(spec->x);
        e->y = TO_FIXED(spec->y);
        e->active = 1;
        e->type = type;
        e->char_id = (type == ENEMY_TYPE_CHARGER) ? CHAR_CHARGER : CHAR_SKELETON;
        e->max_hp = g_enemy_tuning[type].max_hp;
        e->hp = e->max_hp;
        e->dir = (spawned * 2) % 8;
        e->frame = 0;
        e->anim_timer = 0;
        // The arena is closed: every enemy is active from the start (DESIGN.md 4.6).
        e->state = (type == ENEMY_TYPE_CHARGER) ? ENEMY_STATE_CHASE : ENEMY_STATE_POSITION;
        e->state_timer = 0;
        e->hit_timer = 0;
        e->knock_vx = 0;
        e->knock_vy = 0;
        e->stun_timer = 0;
        e->burst_shots_left = 0;
        e->burst_interval_timer = 0;
        e->strafe_dir = (spawned & 1) ? 1 : -1;
        e->has_los = 0;
        spawned++;
    }

    mgr->enemies_total = spawned;
    mgr->enemies_remaining = spawned;
    mgr->state = ENCOUNTER_STATE_ACTIVE;
    mgr->clear_timer = 0;
    mgr->advance = 0;
    return spawned;
}

void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies) {
    if (!mgr || !enemies || max_enemies <= 0) return;

    if (mgr->state == ENCOUNTER_STATE_ACTIVE) {
        int alive = 0;
        for (int i = 0; i < max_enemies; i++) {
            if (enemies[i].active && enemies[i].hp > 0) alive++;
        }
        mgr->enemies_remaining = alive;
        if (alive == 0 && mgr->enemies_total > 0) {
            mgr->state = ENCOUNTER_STATE_CLEARED;
            mgr->clear_timer = ENCOUNTER_CLEAR_PAUSE_FRAMES;
            mgr->total_cleared++;
        }
    } else if (mgr->state == ENCOUNTER_STATE_CLEARED && !mgr->advance) {
        if (--mgr->clear_timer <= 0) mgr->advance = 1;
    }
}

void encounters_record_kill(EncounterManager *mgr, fixed x, fixed y) {
    (void)mgr;
    (void)x;
    (void)y;
}
