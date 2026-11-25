#include "exvoto_test.h"

#if ARPG_EXVOTO_TEST

#include <string.h>
#include "collision.h"
#include "enemy_ai.h"

#if ARPG_MONJA_CURA_TEST
// Monja curandera (DESIGN-ARPG.md, 2026-11-24): 3 Bebes in front and one Monja de cera behind them, all of one pack.
#define EXT_COUNT 4
#else
#define EXT_COUNT 7
#endif
#define EXT_DELAY_FRAMES 120    // ~2 s tras caer el ultimo antes de reponerlos
#define EXT_PACK (-1)           // pack -1: ni el despertar de encounters ni enc_untouchable() los toca, y el Rayo les da

#if ARPG_MONJA_CURA_TEST
static const EnemyType s_types[EXT_COUNT] = { ENEMY_TYPE_EXVOTO, ENEMY_TYPE_BEBE, ENEMY_TYPE_BEBE, ENEMY_TYPE_BEBE };
static const int8_t s_off[EXT_COUNT][2] = { {0, -110}, {-24, -74}, {24, -74}, {0, -84} };
#else
static const EnemyType s_types[EXT_COUNT] = {
    ENEMY_TYPE_MONJA, ENEMY_TYPE_EXVOTO, ENEMY_TYPE_EXVOTO, ENEMY_TYPE_MONAGUILLO, ENEMY_TYPE_MONAGUILLO,
    ENEMY_TYPE_PARROCO, ENEMY_TYPE_BEBE,
};
// Desplazamientos respecto al heroe (norte = y negativo): Super Monja al centro y el resto alrededor.
static const int8_t s_off[EXT_COUNT][2] = {
    {0, -80}, {-36, -66}, {36, -66}, {-56, -86}, {56, -86}, {-24, -108}, {26, -108},
};
#endif

static int s_wait;      // frames con el encuentro entero muerto
static int s_started;

void exvoto_test_reset(void) {
    s_wait = 0;
    s_started = 0;
}

// Mismos campos que place_enemy() de encounters_act1.c: despierto y con la vida normal del tipo.
static void ext_place(Enemy *e, EnemyType type, int x, int y, int ordinal) {
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = EXT_PACK;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = g_enemy_tuning[type].max_hp;
    e->hp = e->max_hp;
    e->dir = 4;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->state = ENEMY_INITIAL_STATE(type);
#if ARPG_MONJA_CURA_TEST
    if (type == ENEMY_TYPE_EXVOTO) { e->home_flags = ENEMY_HOME_GUARD; enemy_exvoto_start_praying(e, 0, 4); }   // as place_room_enemy does
#endif
}

static void spawn_all(Enemy *enemies, int max_enemies, int hx, int hy) {
    int slot = 0;
    for (int k = 0; k < EXT_COUNT; k++) {
        while (slot < max_enemies && enemies[slot].active) slot++;
        if (slot >= max_enemies) return;
        int x = hx + s_off[k][0], y = hy + s_off[k][1];
        // Si cae en pared, prueba mas cerca del heroe en pasos de 8 px.
        for (int t = 0; t < 6 && !position_is_free(TO_FIXED(x), TO_FIXED(y)); t++) {
            x = hx + s_off[k][0] * (5 - t) / 6;
            y = hy + s_off[k][1] * (5 - t) / 6;
        }
        ext_place(&enemies[slot], s_types[k], x, y, k);
        slot++;
    }
}

void exvoto_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    int alive = 0;
    for (int i = 0; i < max_enemies; i++) {
        if (enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == EXT_PACK) alive++;
    }
    if (alive > 0) { s_wait = 0; return; }
    if (s_started && s_wait < EXT_DELAY_FRAMES) { s_wait++; return; }
    spawn_all(enemies, max_enemies, hero_x, hero_y);
    s_started = 1;
    s_wait = 0;
}

#else
typedef int exvoto_test_disabled_translation_unit;
#endif
