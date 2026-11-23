#include "remate_test.h"

#if ARPG_REMATE_TEST

#include <string.h>
#include "collision.h"

#define RT_COUNT 8
#define RT_DELAY_FRAMES 120     // ~2 s tras caer antes de reaparecer en su sitio
#define RT_PACK (-1)            // pack -1: ni el despertar de encounters ni enc_untouchable() los toca
#define RT_MAX_HP 400           // con hp = 101 cualquier punetazo (1..100) lo deja en <= 25 %: tambalea sin morir
#define RT_HP 101

static const EnemyType s_types[RT_COUNT] = {
    // Fila (de oeste a este): la Super Monja queda a 120 px de la Monja de cera y del Monaguillo (> radio de posesion + histeresis)
    ENEMY_TYPE_EXVOTO, ENEMY_TYPE_MONAGUILLO, ENEMY_TYPE_BEBE, ENEMY_TYPE_PARROCO, ENEMY_TYPE_MONJA,
    // Grupo aparte, al norte: Super Monja con una Monja de cera y un Monaguillo pegados (poseidos, en arana)
    ENEMY_TYPE_MONJA, ENEMY_TYPE_EXVOTO, ENEMY_TYPE_MONAGUILLO,
};
// Desplazamientos respecto al heroe (norte = y negativo).
static const int16_t s_off[RT_COUNT][2] = {
    {-80, -60}, {-40, -60}, {0, -60}, {40, -60}, {80, -60},
    {0, -190}, {-26, -176}, {26, -176},
};

static int16_t s_pos[RT_COUNT][2];   // posicion absoluta de cada uno (fijada la primera vez)
static int s_slot[RT_COUNT];         // indice en enemies[] (-1 = ninguno)
static int s_dead[RT_COUNT];         // frames desde que cayo
static int s_ready;

void remate_test_reset(void) {
    s_ready = 0;
    for (int k = 0; k < RT_COUNT; k++) { s_slot[k] = -1; s_dead[k] = 0; }
}

// Mismos campos que place_enemy() de encounters_act1.c: despierto (CHASE) y con la vida justa para tambalear al primer golpe.
static void rt_place(Enemy *e, EnemyType type, int x, int y, int ordinal) {
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = RT_PACK;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = RT_MAX_HP;
    e->hp = RT_HP;
    e->dir = 4;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->state = ENEMY_STATE_CHASE;
}

void remate_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    if (!s_ready) {
        for (int k = 0; k < RT_COUNT; k++) {
            int x = hero_x + s_off[k][0], y = hero_y + s_off[k][1];
            for (int t = 0; t < 6 && !position_is_free(TO_FIXED(x), TO_FIXED(y)); t++) {
                x = hero_x + s_off[k][0] * (5 - t) / 6;
                y = hero_y + s_off[k][1] * (5 - t) / 6;
            }
            s_pos[k][0] = (int16_t)x;
            s_pos[k][1] = (int16_t)y;
            s_slot[k] = -1;
            s_dead[k] = RT_DELAY_FRAMES;     // aparecen ya
        }
        s_ready = 1;
    }
    for (int k = 0; k < RT_COUNT; k++) {
        int i = s_slot[k];
        if (i >= 0 && enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == RT_PACK && enemies[i].type == s_types[k]) {
            s_dead[k] = 0;
            continue;
        }
        s_slot[k] = -1;
        if (s_dead[k] < RT_DELAY_FRAMES) { s_dead[k]++; continue; }
        for (int j = 0; j < max_enemies; j++) {
            if (enemies[j].active) continue;
            rt_place(&enemies[j], s_types[k], s_pos[k][0], s_pos[k][1], k);
            s_slot[k] = j;
            s_dead[k] = 0;
            break;
        }
    }
}

#else
typedef int remate_test_disabled_translation_unit;
#endif
