#include "encounters.h"
#include "arena.h"
#include "gameplay.h"
#include "modifiers.h"
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
        enemies[i].max_hp = 0;
        enemies[i].pack = -1;
    }
    memset(mgr->pack_alive, 0, sizeof(mgr->pack_alive));
    memset(mgr->pack_awake, 0, sizeof(mgr->pack_awake));
    memset(mgr->kill_x, 0, sizeof(mgr->kill_x));
    memset(mgr->kill_y, 0, sizeof(mgr->kill_y));

    int spawned = 0;
    for (int i = 0; i < g_arena->num_enemies && spawned < max_enemies; i++) {
        const ArenaEnemy *spec = &g_arena->enemies[i];
        EnemyType type = (EnemyType)spec->type;
        Enemy *e = &enemies[spawned];
        e->x = TO_FIXED(spec->x);
        e->y = TO_FIXED(spec->y);
        e->active = 1;
        e->type = type;
        e->pack = spec->pack < MAX_PACKS ? spec->pack : MAX_PACKS - 1;
        e->char_id = enemy_type_char_id(type);
        e->max_hp = g_enemy_tuning[type].max_hp;
        e->hp = e->max_hp;
        e->dir = (spawned * 2) % 8;
        e->frame = 0;
        e->anim_timer = 0;
        e->state = ENEMY_STATE_DORMANT;      // asleep until its pack wakes (DESIGN.md 5)
        e->state_timer = 0;
        e->hit_timer = 0;
        e->knock_vx = 0;
        e->knock_vy = 0;
        e->stun_timer = 0;
        e->charge_hit = 0;
        e->strafe_dir = (spawned & 1) ? 1 : -1;
        e->has_los = 0;
        e->aim_px = e->aim_py = e->beam_len = 0;
        e->gesture = 0;
        mgr->pack_alive[e->pack]++;
        spawned++;
    }

    mgr->packs_total = 0;
    for (int p = 0; p < MAX_PACKS; p++) mgr->packs_total += mgr->pack_alive[p] > 0;
    mgr->packs_cleared = 0;
    mgr->enemies_total = spawned;
    mgr->enemies_remaining = spawned;
    mgr->state = ENCOUNTER_STATE_ACTIVE;
    mgr->clear_timer = 0;
    mgr->advance = 0;
    return spawned;
}

static void wake_pack(Enemy *enemies, int max_enemies, int pack) {
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->pack != pack || e->state != ENEMY_STATE_DORMANT) continue;
        e->state = ENEMY_INITIAL_STATE(e->type);
        e->state_timer = 0;
    }
}

void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies, fixed player_x, fixed player_y) {
    if (!mgr || !enemies || max_enemies <= 0) return;

    if (mgr->state == ENCOUNTER_STATE_CLEARED) {
        if (!mgr->advance && --mgr->clear_timer <= 0) mgr->advance = 1;
        return;
    }

    // One pass: who is alive in each pack, and which packs must wake up now. A pack wakes when
    // a sleeping member is near the player or when any member has been hurt (even killed).
    uint8_t alive[MAX_PACKS] = {0};
    uint8_t wake[MAX_PACKS] = {0};
    int px = TO_INT(player_x), py = TO_INT(player_y);
    for (int i = 0; i < max_enemies; i++) {
        const Enemy *e = &enemies[i];
        if (e->pack < 0 || e->pack >= MAX_PACKS) continue;
        if (e->hp > 0 && e->active) alive[e->pack]++;
        if (mgr->pack_awake[e->pack]) continue;
        if (e->hp < e->max_hp) wake[e->pack] = 1;
        else if (e->active && e->state == ENEMY_STATE_DORMANT) {
            int dx = TO_INT(e->x) - px, dy = TO_INT(e->y) - py;
            if (dx * dx + GROUND_DY2(dy) <= PACK_WAKE_RADIUS * PACK_WAKE_RADIUS) wake[e->pack] = 1;
        }
    }

    int total_alive = 0;
    for (int p = 0; p < MAX_PACKS; p++) {
        if (wake[p] && !mgr->pack_awake[p]) {
            mgr->pack_awake[p] = 1;
            wake_pack(enemies, max_enemies, p);
        }
        total_alive += alive[p];
        if (mgr->pack_alive[p] > 0 && alive[p] == 0) {          // the pack just died
            mgr->packs_cleared++;
            if (g_player_state.hp < g_player_state.max_hp && !g_player_state.is_dead) g_player_state.hp++;
            if (mgr->packs_cleared < mgr->packs_total) mods_offer(mgr->kill_x[p], mgr->kill_y[p]);
        }
        mgr->pack_alive[p] = alive[p];
    }
    mgr->enemies_remaining = total_alive;

    if (total_alive == 0 && mgr->enemies_total > 0) {
        mgr->state = ENCOUNTER_STATE_CLEARED;
        mgr->clear_timer = RUN_COMPLETE_FRAMES;
        mgr->total_cleared++;
    }
}

void encounters_record_kill(EncounterManager *mgr, int pack, fixed x, fixed y) {
    if (!mgr || pack < 0 || pack >= MAX_PACKS) return;
    mgr->kill_x[pack] = (int16_t)TO_INT(x);
    mgr->kill_y[pack] = (int16_t)TO_INT(y);
}
