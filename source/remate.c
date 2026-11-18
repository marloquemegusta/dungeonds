#include "remate.h"
#include "remate_sprites.h"
#include "collision.h"
#include "weapons.h"

// Estado del remate en curso y de los restos que quedan. Enteros, sin float.
static int s_active;
static int s_kind;           // REMATE_KIND_EXVOTO o REMATE_KIND_CIRENEO
static int s_enemy;          // indice en el array de enemigos
static int s_t;              // frames de juego desde el inicio
static int s_mirror;
static int s_ax, s_ay;       // pies finales del heroe = ancla de la celda (px de mundo)
static int s_hero_end_ok;    // 1 si el heroe puede reaparecer en el ancla
static int s_killing;
static int s_rem_t;          // frames de vida restantes de los restos; 0 = no hay
static int s_rem_kind;
static int s_rem_x, s_rem_y, s_rem_mirror;

void remate_reset(void) {
    s_active = 0;
    s_killing = 0;
    s_rem_t = 0;
}

int remate_active(void) { return s_active; }
int remate_kind(void) { return s_kind; }
int remate_killing(void) { return s_killing; }
int remate_mirror(void) { return s_mirror; }

int remate_frame(void) {
    int f = s_t / REMATE_TICKS;
    return f >= REMATE_NUM_FRAMES ? REMATE_NUM_FRAMES - 1 : f;
}

void remate_origin(int *x, int *y) {
    *x = s_ax;
    *y = s_ay;
}

int remate_remnant(int *kind, int *x, int *y, int *mirror, int *visible) {
    if (s_rem_t <= 0) return 0;
    *kind = s_rem_kind;
    *x = s_rem_x;
    *y = s_rem_y;
    *mirror = s_rem_mirror;
    *visible = s_rem_t > REMATE_REMNANT_BLINK || (s_rem_t & 1);
    return 1;
}

void remate_shift_y(int dy_px) {
    s_ay += dy_px;
    s_rem_y += dy_px;
}

int remate_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y) {
    if (s_active || g_player_state.is_dead) return 0;
    int hx = TO_INT(hero_x), hy = TO_INT(hero_y);
    int best = -1, best_d2 = REMATE_RANGE * REMATE_RANGE + 1;
    for (int i = 0; i < max_enemies; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0 || e->state != ENEMY_STATE_WOBBLE) continue;
        if (e->type != ENEMY_TYPE_EXVOTO && e->type != ENEMY_TYPE_CHARGER) continue;
        int dx = TO_INT(e->x) - hx, dy = TO_INT(e->y) - hy;
        int d2 = dx * dx + GROUND_DY2(dy);
        if (d2 < best_d2) { best_d2 = d2; best = i; }
    }
    if (best < 0) return 0;

    Enemy *e = &enemies[best];
    int ex = TO_INT(e->x), ey = TO_INT(e->y);
    s_kind = (e->type == ENEMY_TYPE_CHARGER) ? REMATE_KIND_CIRENEO : REMATE_KIND_EXVOTO;
    const RemateKindInfo *nfo = &g_remate_kind_info[s_kind];

    s_mirror = ex < hx;                                   // vista diagonal con el enemigo a la derecha
    s_ax = ex + (s_mirror ? nfo->enemy_dx : -nfo->enemy_dx);
    s_ay = ey - nfo->enemy_dy;
    s_hero_end_ok = position_is_free(TO_FIXED(s_ax), TO_FIXED(s_ay));
    s_enemy = best;
    s_t = 0;
    s_active = 1;
    e->state = ENEMY_STATE_REMATE;
    e->stun_timer = 0;
    e->hit_timer = 0;
    s_rem_t = 0;                                          // un remate nuevo se lleva los restos del anterior
    weapons_cancel_aim();                                 // el heroe suelta lo que cargaba
    g_player_state.invuln_timer = REMATE_NUM_FRAMES * REMATE_TICKS + 2;   // invulnerable todo el remate
    return 1;
}

void remate_update(Enemy *enemies, int max_enemies, fixed *hero_x, fixed *hero_y, int *hero_dir) {
    (void)max_enemies;
    if (s_rem_t > 0) s_rem_t--;
    if (!s_active) return;
    Enemy *e = &enemies[s_enemy];
    if (g_player_state.is_dead || !e->active || e->state != ENEMY_STATE_REMATE) {
        s_active = 0;                                     // algo lo corto: el enemigo vuelve a lo suyo
        if (e->active && e->state == ENEMY_STATE_REMATE) e->state = ENEMY_STATE_CHASE;
        return;
    }
    if (++s_t < REMATE_NUM_FRAMES * REMATE_TICKS) return;

    // Fin: el enemigo muere (muerte limpia, sin efectos estandar), el heroe reaparece donde acaba
    // la animacion y el rayo queda cargado del todo.
    s_active = 0;
    e->state = ENEMY_STATE_CHASE;
    s_killing = 1;
    enemy_hit(e, 9999, 0, 0);
    s_killing = 0;
    if (s_hero_end_ok) {
        *hero_x = TO_FIXED(s_ax);
        *hero_y = TO_FIXED(s_ay);
    }
    *hero_dir = s_mirror ? DIR_WEST : DIR_EAST;
    g_player_state.invuln_timer = 0;
    weapons_ready_instant();

    const RemateKindInfo *nfo = &g_remate_kind_info[s_kind];
    if (nfo->has_remnant) {
        s_rem_t = REMATE_REMNANT_FRAMES;
        s_rem_kind = s_kind;
        s_rem_x = s_ax;
        s_rem_y = s_ay;
        s_rem_mirror = s_mirror;
    }
}
