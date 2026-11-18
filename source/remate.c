#include "remate.h"
#include "remate_sprites.h"
#include "collision.h"
#include "enemy_ai.h"
#include "weapons.h"
#include <stdio.h>

static uint8_t s_bin_buf[REMATE_MAX_BIN_BYTES] __attribute__((aligned(4)));
static int s_loaded_kind = -1;
static int s_loaded_dir = -1;

static int remate_load_bin(int kind, int dir) {
    if (s_loaded_kind == kind && s_loaded_dir == dir) return 1;
    char path[48];
    snprintf(path, sizeof(path), "nitro:/remate/%s_d%d.bin",
             kind == REMATE_KIND_CIRENEO ? "cireneo" : "exvoto", dir);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    size_t n = fread(s_bin_buf, 1, sizeof(s_bin_buf), f);
    fclose(f);
    if (n < sizeof(RemateBinHeader)) { s_loaded_kind = -1; return 0; }
    const RemateBinHeader *h = (const RemateBinHeader *)s_bin_buf;
    if (h->magic != REMATE_BIN_MAGIC ||
        sizeof(RemateBinHeader) + h->pix_bytes + h->runs_bytes + h->mask_bytes > n) {
        s_loaded_kind = -1;
        return 0;
    }
    s_loaded_kind = kind;
    s_loaded_dir = dir;
    return 1;
}

const RemateBinHeader *remate_bin(void) {
    return s_loaded_kind >= 0 ? (const RemateBinHeader *)s_bin_buf : NULL;
}

const uint16_t *remate_bin_pixels(void) {
    return (const uint16_t *)(s_bin_buf + sizeof(RemateBinHeader));
}

const uint16_t *remate_bin_runs(void) {
    const RemateBinHeader *h = (const RemateBinHeader *)s_bin_buf;
    return (const uint16_t *)(s_bin_buf + sizeof(RemateBinHeader) + h->pix_bytes);
}

const uint8_t *remate_bin_masks(void) {
    const RemateBinHeader *h = (const RemateBinHeader *)s_bin_buf;
    return (const uint8_t *)(s_bin_buf + sizeof(RemateBinHeader) + h->pix_bytes + h->runs_bytes);
}

// Estado del remate en curso y de los restos que quedan. Enteros, sin float.
static int s_active;         // 1 = suena la celda combinada
static int s_approach;       // 1 = embestida previa (el heroe corre al punto de inicio)
static int s_dash_t;         // frames de embestida
static int s_kind;           // REMATE_KIND_EXVOTO o REMATE_KIND_CIRENEO
static int s_enemy;          // indice en el array de enemigos
static int s_t;              // frames de juego desde el inicio
static int s_dir;            // direccion del ataque (0..7)
static int s_ax, s_ay;       // pies finales del heroe = ancla de la celda (px de mundo)
static int s_hero_end_ok;    // 1 si el heroe puede reaparecer en el ancla
static int s_killing;
static int s_rem_t;          // frames de vida restantes de los restos; 0 = no hay
static int s_rem_kind;
static int s_rem_x, s_rem_y, s_rem_dir;
static int s_post_invuln_t;  // frames de invulnerabilidad tras acabar el remate (sin flash rojo de daño)

void remate_reset(void) {
    s_active = 0;
    s_approach = 0;
    s_killing = 0;
    s_rem_t = 0;
    s_post_invuln_t = 0;
}

int remate_active(void) { return s_active; }
int remate_approaching(void) { return s_approach; }
int remate_invuln(void) { return s_post_invuln_t; }
int remate_kind(void) { return s_kind; }
int remate_killing(void) { return s_killing; }
int remate_dir(void) { return s_dir; }

int remate_frame(void) {
    int f = s_t / REMATE_TICKS;
    return f >= REMATE_NUM_FRAMES ? REMATE_NUM_FRAMES - 1 : f;
}

void remate_origin(int *x, int *y) {
    *x = s_ax;
    *y = s_ay;
}

int remate_remnant(int *kind, int *x, int *y, int *dir, int *visible) {
    if (s_rem_t <= 0) return 0;
    *kind = s_rem_kind;
    *x = s_rem_x;
    *y = s_rem_y;
    *dir = s_rem_dir;
    *visible = s_rem_t > REMATE_REMNANT_BLINK || (s_rem_t & 1);
    return 1;
}

void remate_shift_y(int dy_px) {
    s_ay += dy_px;
    s_rem_y += dy_px;
}

int remate_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir) {
    if (s_active || s_approach || g_player_state.is_dead) return 0;
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

    int dx = ex - hx, dy = ey - hy;
    if (dx * dx + GROUND_DY2(dy) < 16) s_dir = hero_dir & 7;
    else s_dir = enemy_dir_from_vector(TO_FIXED(dx), TO_FIXED(dy));

    if (!remate_load_bin(s_kind, s_dir)) return 0;

    const RemateDirInfo *dnfo = &g_remate_dir_info[s_kind][s_dir];
    s_ax = ex - dnfo->enemy_dx;
    s_ay = ey - dnfo->enemy_dy;
    s_hero_end_ok = position_is_free(TO_FIXED(s_ax), TO_FIXED(s_ay));
    s_enemy = best;
    s_t = 0;
    s_dash_t = 0;
    s_post_invuln_t = 0;
    e->state = ENEMY_STATE_REMATE;                        // quieto (sin tambaleo) mientras el heroe llega
    e->dir = (s_kind == REMATE_KIND_CIRENEO) ? s_dir : (uint8_t)((s_dir + 4) & 7);   // Exvoto mira al heroe (que ataca desde s_dir); Cireneo le da la espalda: el heroe le arranca la cruz por detras
    e->stun_timer = 0;
    e->hit_timer = 0;
    s_rem_t = 0;                                          // un remate nuevo se lleva los restos del anterior
    weapons_cancel_aim();                                 // el heroe suelta lo que cargaba
    // invulnerable toda la embestida y la celda
    g_player_state.invuln_timer = REMATE_DASH_MAX_FRAMES + REMATE_NUM_FRAMES * REMATE_TICKS + 4;
    if (s_hero_end_ok) s_approach = 1;                    // sin sitio final libre: como antes, sin embestida
    else s_active = 1;
    return 1;
}

// Empieza la celda combinada: el heroe ya esta en su punto de inicio (fotograma 0).
static void remate_begin_cell(fixed *hero_x, fixed *hero_y) {
    s_approach = 0;
    s_active = 1;
    s_t = 0;
    if (s_hero_end_ok) {
        *hero_x = TO_FIXED(s_ax + g_remate_hero_off[s_kind][s_dir][0][0]);
        *hero_y = TO_FIXED(s_ay + g_remate_hero_off[s_kind][s_dir][0][1]);
    }
    g_player_state.invuln_timer = REMATE_NUM_FRAMES * REMATE_TICKS + 2;
}

void remate_update(Enemy *enemies, int max_enemies, fixed *hero_x, fixed *hero_y, int *hero_dir) {
    (void)max_enemies;
    if (s_rem_t > 0) s_rem_t--;
    if (s_post_invuln_t > 0) s_post_invuln_t--;
    if (!s_active && !s_approach) return;
    Enemy *e = &enemies[s_enemy];
    if (g_player_state.is_dead || !e->active || e->state != ENEMY_STATE_REMATE) {
        s_active = 0;                                     // algo lo corto: el enemigo vuelve a lo suyo
        s_approach = 0;
        if (e->active && e->state == ENEMY_STATE_REMATE) e->state = ENEMY_STATE_CHASE;
        return;
    }

    if (s_approach) {
        // Embestida: el heroe corre al punto donde empieza la celda, mirando al enemigo (aunque el punto
        // quede detras). Paso de REMATE_DASH_SPEED px de suelo; si algo lo bloquea o se pasa de tiempo, salta.
        *hero_dir = s_dir;
        const int tx = s_ax + g_remate_hero_off[s_kind][s_dir][0][0];
        const int ty = s_ay + g_remate_hero_off[s_kind][s_dir][0][1];
        const int hx = TO_INT(*hero_x), hy = TO_INT(*hero_y);
        const int dx = tx - hx, dy = ty - hy;
        const int adx = dx < 0 ? -dx : dx;
        const int ady = (dy < 0 ? -dy : dy) << 1;         // metrica de suelo 2:1
        const int m = adx > ady ? adx : ady;
        if (++s_dash_t > REMATE_DASH_MAX_FRAMES || m <= REMATE_DASH_SPEED) {
            remate_begin_cell(hero_x, hero_y);
            return;
        }
        const int nx = hx + (dx * REMATE_DASH_SPEED) / m;
        const int ny = hy + (dy * REMATE_DASH_SPEED) / m;
        if (!position_is_free(TO_FIXED(nx), TO_FIXED(ny))) {
            remate_begin_cell(hero_x, hero_y);            // bloqueado: salto como antes
            return;
        }
        *hero_x = TO_FIXED(nx);
        *hero_y = TO_FIXED(ny);
        return;
    }

    const int tot = REMATE_NUM_FRAMES * REMATE_TICKS;
    if (++s_t < tot) {
        if (s_hero_end_ok) {
            // El heroe sigue sus pies horneados de cada fotograma (interpolados entre fotogramas) y la camara con el.
            const int f = s_t / REMATE_TICKS, sub = s_t % REMATE_TICKS;
            const int8_t *o0 = g_remate_hero_off[s_kind][s_dir][f];
            int ox = o0[0], oy = o0[1];
            if (f + 1 < REMATE_NUM_FRAMES) {
                const int8_t *o1 = g_remate_hero_off[s_kind][s_dir][f + 1];
                ox += ((o1[0] - o0[0]) * sub) / REMATE_TICKS;
                oy += ((o1[1] - o0[1]) * sub) / REMATE_TICKS;
            }
            *hero_x = TO_FIXED(s_ax + ox);
            *hero_y = TO_FIXED(s_ay + oy);
        }
        return;
    }

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
    *hero_dir = s_dir;
    g_player_state.invuln_timer = 0;
    s_post_invuln_t = REMATE_POST_INVULN_FRAMES;
    weapons_ready_instant();

    const RemateKindInfo *nfo = &g_remate_kind_info[s_kind];
    if (nfo->has_remnant) {
        s_rem_t = REMATE_REMNANT_FRAMES;
        s_rem_kind = s_kind;
        s_rem_x = s_ax;
        s_rem_y = s_ay;
        s_rem_dir = s_dir;
    }
}
