#include "minirom.h"

#if MINIROM

#include <string.h>
#include "collision.h"
#include "arpg.h"
#include "arpg_inv.h"
#include "arpg_progress.h"

#define MINIROM_STR2(x) #x
#define MINIROM_STR(x) MINIROM_STR2(x)
#ifndef MINIROM_SPEC
#error "MINIROM needs -DMINIROM_SPEC=<nombre> (tools/minirom.py sets it)"
#endif
#include MINIROM_STR(minirom_gen/MINIROM_SPEC.h)

#define MR_RESPAWN_FRAMES 120      // a dead enemy of the list comes back this many frames later (reaparecen)
#define MR_DEATH_FRAMES 90         // dead hero: the room restarts after this
#define MR_MAX_LIST 16

volatile MiniromDbg g_minirom_dbg;

static int s_spawned;                          // the list has been placed in this run of the room
static int8_t s_slot[MR_MAX_LIST];             // slot of each listed enemy, -1 = none
static uint8_t s_type[MR_MAX_LIST];            // its EnemyType, to tell it from a later tenant of the slot
static int16_t s_px[MR_MAX_LIST], s_py[MR_MAX_LIST];   // where it was placed (respawn goes back there)
static uint16_t s_dead_for[MR_MAX_LIST];
static int s_dead_frames;
static int s_booted;

static int list_n(void) { return MR_N_ENEMIGOS < MR_MAX_LIST ? MR_N_ENEMIGOS : MR_MAX_LIST; }

int minirom_boot(void) {
    int room = 0;                              // "pruebas" = the first room (Nave 1) with no population
    if (!MR_SALA_PRUEBAS) {
        room = enc_room_find(MR_SALA);
        if (room < 0) { g_minirom_dbg.error = 1; return 0; }
    }
    g_enc_debug.start_room = (uint8_t)(room + 1);
    g_enc_debug.god = MR_INVULNERABLE;
    g_enc_debug.boss_hp = MR_VIDA_JEFE;
#if MR_EQUIPO_TODO
    g_arpg.level = 10;
    g_arpg.points = 0;
    arpg_inv_unlock_all();
    g_arpg_level = g_arpg.level;
#else
    arpg_inv_new_game();
#endif
    if (MR_N_MECANICAS > 0) {
        if (g_arpg.level < 10) { g_arpg.level = 10; g_arpg_level = g_arpg.level; }   // its sockets are open
        for (int i = 0; i < MR_N_MECANICAS; i++) arpg_inv_minirom_equip(MR_MECANICAS[i]);
    }
    return 1;
}

void minirom_boot_done(void) {
    s_booted = 1;
    g_minirom_dbg.restarts = 0;
}

void minirom_on_restart(void) {
    s_spawned = 0;
    s_dead_frames = 0;
    for (int i = 0; i < MR_MAX_LIST; i++) { s_slot[i] = -1; s_dead_for[i] = 0; }
    if (s_booted) g_minirom_dbg.restarts++;
}

int minirom_skip_population(void) { return MR_SALA_PRUEBAS || MR_N_ENEMIGOS > 0; }

uint32_t minirom_art_mask(void) {
    uint32_t mask = 0;
    for (int i = 0; i < list_n(); i++) {
        const EncEnemyDef d = { MR_ENEMIGOS[i].tipo, MR_ENEMIGOS[i].estado, 0, 0 };
        mask |= enc_minirom_art(&d);
    }
    return mask;
}

static void place_at(Enemy *enemies, int max_enemies, int i, int x, int y) {
    const EncEnemyDef d = { MR_ENEMIGOS[i].tipo, MR_ENEMIGOS[i].estado, 0, 0 };
    const int slot = enc_minirom_place(enemies, max_enemies, &d, x, y, i);
    s_slot[i] = (int8_t)slot;
    s_type[i] = slot >= 0 ? (uint8_t)enemies[slot].type : 0;
    s_dead_for[i] = 0;
}

int minirom_frame(int hero_x, int hero_y, Enemy *enemies, int max_enemies) {
    // Listed enemies: placed once per run of the room (dx/dy from the hero, falling back towards him in steps when the
    // spot is a wall, as exvoto_test.c does) and, with "reaparecen", again 120 frames after each death at the same spot.
    if (list_n() > 0) {
        if (!s_spawned) {
            for (int i = 0; i < list_n(); i++) {
                int x = hero_x + MR_ENEMIGOS[i].dx, y = hero_y + MR_ENEMIGOS[i].dy;
                for (int t = 0; t < 6 && !position_is_free(TO_FIXED(x), TO_FIXED(y)); t++) {
                    x = hero_x + MR_ENEMIGOS[i].dx * (5 - t) / 6;
                    y = hero_y + MR_ENEMIGOS[i].dy * (5 - t) / 6;
                }
                s_px[i] = (int16_t)x;
                s_py[i] = (int16_t)y;
                place_at(enemies, max_enemies, i, x, y);
            }
            s_spawned = 1;
        } else if (MR_REAPARECEN) {
            for (int i = 0; i < list_n(); i++) {
                const int s = s_slot[i];
                const Enemy *e = s >= 0 ? &enemies[s] : 0;
                if (e && e->active && e->hp > 0 && e->type == s_type[i]) { s_dead_for[i] = 0; continue; }
                if (++s_dead_for[i] >= MR_RESPAWN_FRAMES) place_at(enemies, max_enemies, i, s_px[i], s_py[i]);
            }
        }
    }

    int alive = 0, boss = 0;
    int32_t hp_sum = 0;
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;
        if (MR_INMORTALES && e->hp > 0) e->hp = e->max_hp;
        if (e->hp <= 0) continue;
        alive++;
        hp_sum += e->hp;
        if (!boss && (e->type == ENEMY_TYPE_ABANDERADO || e->type == ENEMY_TYPE_CAMPANERO)) boss = e->hp;
    }
    g_minirom_dbg.room = (int16_t)enc_room_current();
    g_minirom_dbg.room_ok = (uint8_t)(MR_SALA_PRUEBAS ? enc_room_current() == 0 : strcmp(enc_room_name(), MR_SALA) == 0);
    g_minirom_dbg.enemies = (int16_t)alive;
    g_minirom_dbg.enemy_hp = hp_sum;
    g_minirom_dbg.boss_hp = boss;
    g_minirom_dbg.hero_hp = g_player_state.hp;
    g_minirom_dbg.frames++;
    g_minirom_dbg.frozen = 0;

    if (g_player_state.is_dead || g_player_state.hp <= 0) {
        if (++s_dead_frames >= MR_DEATH_FRAMES) return 1;
    } else {
        s_dead_frames = 0;
    }
    return 0;
}

#else
typedef int minirom_disabled_translation_unit;
#endif
