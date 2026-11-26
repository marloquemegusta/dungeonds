#include "boxeo.h"

#if ARPG_BOXEO

#include <string.h>
#include "collision.h"

#define SACO_DIST 28            // px al lado del heroe (este, misma altura): con el suelo 2:1 el vertical cuenta doble, al norte no llegaria el golpe
#define SACO_MAX_HP 2000        // holgura: ningun golpe del heroe lo mata de un solo golpe
#define SACO_HOME_PX 2          // si tras el retroceso queda a mas de esto de su punto, vuelve a el...
#define SACO_CALM_FRAMES 60     // ...tras ~1 s sin recibir golpes ni aturdimiento

const char *const g_boxeo_type_names[BOXEO_TYPE_COUNT] = {
    "Exvoto", "Cargador", "Monaguillo", "Bebé", "Párroco", "Monja", "Ojo",
};
static const EnemyType s_types[BOXEO_TYPE_COUNT] = {
    ENEMY_TYPE_EXVOTO, ENEMY_TYPE_CHARGER, ENEMY_TYPE_MONAGUILLO, ENEMY_TYPE_BEBE,
    ENEMY_TYPE_PARROCO, ENEMY_TYPE_MONJA, ENEMY_TYPE_SHOOTER,
};

static int s_have_anchor;
static int s_ax, s_ay;          // punto del saco
static int s_slot = -1;
static int s_placed_type = -1;  // tipo del saco que vive ahora (para reemplazarlo al cambiar en el menu)
static int s_calm;

void boxeo_reset(void) {
    s_have_anchor = 0;
    s_slot = -1;
    s_placed_type = -1;
    s_calm = 0;
}

// Mismos campos que place_enemy() de encounters_act1.c, dormido no: despierto y quieto (la IA lo congela).
static void saco_place(Enemy *e, EnemyType type, int x, int y) {
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = 0;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = SACO_MAX_HP;
    e->hp = e->max_hp;
    e->dir = 4;                                  // mirando al heroe (sur)
    e->strafe_dir = 1;
    e->state = ENEMY_INITIAL_STATE(type);
}

static void pick_anchor(int hx, int hy) {
    static const int8_t off[][2] = { {SACO_DIST, 0}, {-SACO_DIST, 0}, {0, -SACO_DIST}, {24, -SACO_DIST},
                                     {-24, -SACO_DIST}, {0, SACO_DIST} };
    s_ax = hx + SACO_DIST;
    s_ay = hy;
    for (unsigned i = 0; i < sizeof(off) / sizeof(off[0]); i++) {
        if (position_is_free(TO_FIXED(hx + off[i][0]), TO_FIXED(hy + off[i][1]))) {
            s_ax = hx + off[i][0];
            s_ay = hy + off[i][1];
            break;
        }
    }
    s_have_anchor = 1;
}


#if ARPG_BOXEO_MELEE
// Variante arpg-boxeo-mele: en vez del saco, una tropa de monaguillos que persigue al heroe (vida normal); al caer uno entra otro.
#define MELEE_COUNT 12
#define MELEE_RING 90            // px del heroe a los que aparecen
static int s_melee_wait;

static void melee_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    static const int8_t dirs[12][2] = { {1,0}, {1,1}, {0,1}, {-1,1}, {-1,0}, {-1,-1}, {0,-1}, {1,-1}, {2,1}, {-2,1}, {2,-1}, {-2,-1} };
    int live = 0;
    for (int i = 0; i < max_enemies; i++) {
        if (enemies[i].active && enemies[i].type == ENEMY_TYPE_MONAGUILLO) live++;
    }
    if (live >= MELEE_COUNT) return;
    if (s_melee_wait > 0) { s_melee_wait--; return; }
    int added = 0;
    for (int k = 0; k < 12 && live + added < MELEE_COUNT; k++) {
        const int x = hero_x + dirs[k][0] * MELEE_RING / 2;
        const int y = hero_y + dirs[k][1] * MELEE_RING / 4;
        if (!position_is_free(TO_FIXED(x), TO_FIXED(y))) continue;
        for (int i = 0; i < max_enemies; i++) {
            if (enemies[i].active) continue;
            saco_place(&enemies[i], ENEMY_TYPE_MONAGUILLO, x, y);
            enemies[i].max_hp = enemies[i].hp = g_enemy_tuning[ENEMY_TYPE_MONAGUILLO].max_hp;
            added++;
            break;
        }
    }
    s_melee_wait = live == 0 ? 0 : 45;   // la tropa inicial de golpe; las reposiciones, a ritmo
}
#endif

#if ARPG_BOXEO_DUELO
// Duelo: un solo Exvoto de vida normal que persigue al heroe; al caer, otro a 60 px. Sirve de evidencia del aviso del mordisco.
static int s_duelo_wait;
static void duelo_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    for (int i = 0; i < max_enemies; i++) {
        if (enemies[i].active) { s_duelo_wait = 30; return; }
    }
    if (s_duelo_wait > 0) { s_duelo_wait--; return; }
    saco_place(&enemies[0], ENEMY_TYPE_EXVOTO, hero_x + 60, hero_y);
    enemies[0].max_hp = enemies[0].hp = g_enemy_tuning[ENEMY_TYPE_EXVOTO].max_hp;
    enemies[0].state = ENEMY_STATE_CHASE;
    enemies[0].dir = 0;
}
#endif

void boxeo_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
#if ARPG_BOXEO_DUELO
    duelo_update(enemies, max_enemies, hero_x, hero_y);
    return;
#endif
#if ARPG_BOXEO_MELEE
    melee_update(enemies, max_enemies, hero_x, hero_y);
    return;
#endif
    if (!s_have_anchor) pick_anchor(hero_x, hero_y);
    int want = g_lab_saco_type;
    if (want < 0 || want >= BOXEO_TYPE_COUNT) want = 0;

    // Cambiar de tipo en el menu reemplaza el saco.
    if (s_slot >= 0 && s_placed_type != want) {
        enemies[s_slot].active = 0;
        s_slot = -1;
    }
    if (s_slot >= 0 && (!enemies[s_slot].active || enemies[s_slot].hp <= 0)) s_slot = -1;

    if (s_slot < 0) {                            // falta (o murio por una via que no es un golpe): reaparece en su sitio
        for (int i = 0; i < max_enemies; i++) {
            if (enemies[i].active) continue;
            saco_place(&enemies[i], s_types[want], s_ax, s_ay);
            s_slot = i;
            s_placed_type = want;
            s_calm = 0;
            break;
        }
        return;
    }

    Enemy *e = &enemies[s_slot];
    // Vida infinita: recibe el golpe entero, pero nunca llega al tambaleo ni al remate.
    if (e->hp * 2 < e->max_hp) e->hp = e->max_hp;
    if (e->state == ENEMY_STATE_WOBBLE || e->state == ENEMY_STATE_REMATE) {
        e->state = ENEMY_INITIAL_STATE(e->type);
        e->state_timer = 0;
    }
    // Vuelve a su punto si el retroceso lo ha desplazado y lleva ~1 s sin recibir golpes.
    if (e->hit_timer > 0 || e->stun_timer > 0) {
        s_calm = 0;
    } else if (s_calm < SACO_CALM_FRAMES) {
        s_calm++;
    } else {
        const int dx = TO_INT(e->x) - s_ax, dy = TO_INT(e->y) - s_ay;
        if (dx * dx + dy * dy > SACO_HOME_PX * SACO_HOME_PX) {
            e->x = TO_FIXED(s_ax);
            e->y = TO_FIXED(s_ay);
            e->knock_vx = e->knock_vy = 0;
        }
    }
}

#else
typedef int boxeo_disabled_translation_unit;
#endif
