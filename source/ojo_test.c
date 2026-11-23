#include "ojo_test.h"

#if ARPG_OJO_TEST

#include <string.h>
#include <nds.h>
#include "collision.h"
#include "encounters_act1.h"

#define OT_DELAY_FRAMES 120     // ~2 s tras caer el Ojo antes de reponerlo
#define OT_PACK (-1)            // pack -1: ni el despertar de encounters ni enc_untouchable() lo tocan
#define OT_BOXES 8
#define OT_DIST 150             // distancia de suelo heroe-Ojo (el suelo cuenta el doble en vertical: 75 px de pantalla)

volatile int g_ojo_test_dbg[48];

typedef struct { int x0, y0, x1, y1; } OtBox;

static int s_wait;
static int s_started;
static int s_x, s_y;            // sitio del Ojo (se calcula una vez al empezar)
static int s_placed;
static int s_boot;             // frames desde el arranque: la colision de la sala tarda unos frames en estar lista
#define OT_BOOT_FRAMES 30

void ojo_test_reset(void) {
    s_wait = 0;
    s_started = 0;
    s_placed = 0;
    s_boot = 0;
}

static int ot_free(int x, int y) { return position_is_free(TO_FIXED(x), TO_FIXED(y)); }
static int ot_solid(int x, int y) { return !bullet_position_is_free(TO_FIXED(x), TO_FIXED(y)); }

// Columnas: celdas que paran balas (valor 3) en el suelo de la sala, agrupadas en cajas.
static int ot_find_boxes(int hx, int hy, OtBox *box) {
    int n = 0;
    for (int y = hy - 210; y <= hy + 4; y += 4) {
        for (int x = ENC_FLOOR_X + 12; x <= ENC_FLOOR_X + ENC_FLOOR_W - 12; x += 4) {
            if (!ot_solid(x, y)) continue;
            int k;
            for (k = 0; k < n; k++) {
                if (x >= box[k].x0 - 8 && x <= box[k].x1 + 8 && y >= box[k].y0 - 8 && y <= box[k].y1 + 8) break;
            }
            if (k == n) {
                if (n >= OT_BOXES) continue;
                box[n].x0 = box[n].x1 = x;
                box[n].y0 = box[n].y1 = y;
                n++;
            } else {
                if (x < box[k].x0) box[k].x0 = x;
                if (x > box[k].x1) box[k].x1 = x;
                if (y < box[k].y0) box[k].y0 = y;
                if (y > box[k].y1) box[k].y1 = y;
            }
        }
    }
    return n;
}

// Sitio del Ojo: al norte del heroe con linea limpia, algo escorado hacia la columna elegida, que queda a un costado
// (el heroe se pone detras de ella en 1-2 s).
static void ot_place(int hx, int hy) {
    OtBox box[OT_BOXES];
    const int n = ot_find_boxes(hx, hy, box);
    int best = -1, best_gd = 0;
    for (int k = 0; k < n; k++) {
        const int cx = (box[k].x0 + box[k].x1) / 2, cy = (box[k].y0 + box[k].y1) / 2;
        const int dx = cx - hx, dy = cy - hy;
        const int gd = sqrt32(dx * dx + 4 * dy * dy);
        if (gd < 30 || gd > 130 || cy >= hy) continue;
        if (best < 0 || gd < best_gd) { best = k; best_gd = gd; }
    }
    int ox = hx, oy = hy - OT_DIST / 2;
    if (best >= 0) {
        const int cx = (box[best].x0 + box[best].x1) / 2;
        ox = hx + ((cx > hx) ? 16 : -16);
    }
    for (int t = 0; t < 12 && !ot_free(ox, oy); t++) oy += 4;      // si cae en pared, lo acerca al heroe
    s_x = ox; s_y = oy;
    s_placed = 1;
    g_ojo_test_dbg[0] = hx; g_ojo_test_dbg[1] = hy;
    g_ojo_test_dbg[2] = ox; g_ojo_test_dbg[3] = oy;
    if (best >= 0) {
        g_ojo_test_dbg[4] = box[best].x0; g_ojo_test_dbg[5] = box[best].y0;
        g_ojo_test_dbg[6] = box[best].x1; g_ojo_test_dbg[7] = box[best].y1;
    }
    g_ojo_test_dbg[8] = n;
    for (int k = 0; k < n; k++) {
        g_ojo_test_dbg[12 + 4 * k] = box[k].x0; g_ojo_test_dbg[13 + 4 * k] = box[k].y0;
        g_ojo_test_dbg[14 + 4 * k] = box[k].x1; g_ojo_test_dbg[15 + 4 * k] = box[k].y1;
    }
    g_ojo_test_dbg[9] = bullet_line_is_free(ox, oy, hx, hy);
}

// Mismos campos que place_enemy() de encounters_act1.c: despierto, con la vida del tipo y su puesto fijado (correa del Ojo).
static void ot_spawn(Enemy *enemies, int max_enemies) {
    for (int slot = 0; slot < max_enemies; slot++) {
        if (enemies[slot].active) continue;
        Enemy *e = &enemies[slot];
        memset(e, 0, sizeof(*e));
        e->x = TO_FIXED(s_x);
        e->y = TO_FIXED(s_y);
        e->active = 1;
        e->type = ENEMY_TYPE_SHOOTER;
        e->pack = OT_PACK;
        e->char_id = enemy_type_char_id(ENEMY_TYPE_SHOOTER);
        e->max_hp = g_enemy_tuning[ENEMY_TYPE_SHOOTER].max_hp;
        e->hp = e->max_hp;
        e->dir = 4;
        e->strafe_dir = 1;
        e->state = ENEMY_INITIAL_STATE(ENEMY_TYPE_SHOOTER);
        e->home_flags = ENEMY_HOME_SET;
        *enemy_home_x(e) = s_x;
        *enemy_home_y(e) = s_y;
        return;
    }
}

void ojo_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    if (s_boot < OT_BOOT_FRAMES) { s_boot++; return; }
    int alive = 0;
    for (int i = 0; i < max_enemies; i++) {
        if (enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == OT_PACK) alive++;
    }
    if (alive > 0) { s_wait = 0; return; }
    if (s_started && s_wait < OT_DELAY_FRAMES) { s_wait++; return; }
    if (!s_placed) ot_place(hero_x, hero_y);
    ot_spawn(enemies, max_enemies);
    s_started = 1;
    s_wait = 0;
}

#else
typedef int ojo_test_disabled_translation_unit;
#endif
