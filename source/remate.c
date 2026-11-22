#include "remate.h"
#include "remate_sprites.h"
#include "punch.h"
#include "collision.h"
#include "enemy_ai.h"
#include "hwshadow.h"
#include "weapons.h"
#include "sfx.h"
#include "pickups.h"
#include "allies.h"
#include "arpg_inv.h"
#include <stdio.h>

// Bin del remate: cabecera fija (magic + tamanos) seguida de los arrays del tipo. La cabecera completa se interpreta
// a mano en remate_load_bin() porque cambia de tamano con el numero de fotogramas (12 Exvoto/Cireneo, 38 Ojo); ver
// tools/generate_remate_sprites.py. En vez de cargar el bin entero (206 KB con el Ojo), se lee de NitroFS solo el
// fotograma que toca (pixeles + runs + mascara) a buffers estaticos: el pico de EWRAM baja de 206 KB a ~24 KB.
typedef struct {
    uint32_t magic;
    uint32_t pix_bytes;
    uint32_t runs_bytes;
    uint32_t mask_bytes;
} RemateBinHead;

static FILE *s_bin_f;                                   // abierto mientras dura la celda (streaming por fotograma)
static uint8_t s_hdr[REMATE_HEADER_BYTES] __attribute__((aligned(4)));
static uint8_t s_pix[REMATE_PIX_BYTES] __attribute__((aligned(4)));
static uint8_t s_runs[REMATE_RUN_BYTES] __attribute__((aligned(4)));
static uint8_t s_mask[REMATE_MASK_BYTES] __attribute__((aligned(4)));
static int s_loaded_kind = -1;
static int s_loaded_dir = -1;
static int s_cur_frame = -1;                            // fotograma cargado en los buffers (-1 = ninguno)
static uint32_t s_payload;                              // offset del payload (pixeles) dentro del fichero
static uint32_t s_pix_bytes, s_runs_bytes, s_mask_bytes;
static const uint8_t *s_fb, *s_sb, *s_db;               // bounds de fotogramas, sombras y capa de restos
static const uint32_t *s_fp, *s_fr, *s_so, *s_dp, *s_dr;
static const uint16_t *s_pix_a, *s_pix_b, *s_run_a, *s_run_b;
static const uint8_t *s_shadow;

static const char *kind_slug(int kind) {
    if (kind == REMATE_KIND_CIRENEO) return "cireneo";
    if (kind == REMATE_KIND_OJO) return "ojo";
    if (kind == REMATE_KIND_MONAGUILLO) return "monaguillo";
    if (kind == REMATE_KIND_BEBE) return "exvoto_bebe";
    return "exvoto";
}

static uint32_t kind_header_bytes(int kind) {
    const uint32_t f = g_remate_kind_info[kind].frames;
    return sizeof(RemateBinHead) + (f + 1) * 4 * 3 + f * 4 * 2 + (f + 1) * 4 * 3;
}

static void remate_close_bin(void) {
    if (s_bin_f) { fclose(s_bin_f); s_bin_f = NULL; }
#if HW_SHADOWS
    hwshadow_invalidate(s_mask);
#endif
    s_loaded_kind = -1;
    s_loaded_dir = -1;
    s_cur_frame = -1;
}

// Lee `n` bytes del fichero en `off` dentro del destino.
static void read_at(uint32_t off, void *dst, uint32_t n) {
    if (!s_bin_f || n == 0) return;
    fseek(s_bin_f, (long)off, SEEK_SET);
    fread(dst, 1, n, s_bin_f);
}

static int remate_load_bin(int kind, int dir) {
    if (kind < 0 || kind >= REMATE_NUM_KINDS) return 0;
    if (s_loaded_kind == kind && s_loaded_dir == dir && s_bin_f) return 1;
    remate_close_bin();
    char path[48];
    snprintf(path, sizeof(path), "nitro:/remate/%s_d%d.bin", kind_slug(kind), dir);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    const uint32_t hb = kind_header_bytes(kind);
    const uint32_t fr = g_remate_kind_info[kind].frames;
    if (hb > sizeof(s_hdr) || fread(s_hdr, 1, hb, f) != hb) { fclose(f); return 0; }
    const RemateBinHead *h = (const RemateBinHead *)s_hdr;
    if (h->magic != REMATE_BIN_MAGIC) { fclose(f); return 0; }
    const uint8_t *p = s_hdr + sizeof(RemateBinHead);
    s_fb = p; p += (fr + 1) * 4;
    s_fp = (const uint32_t *)p; p += (fr + 1) * 4;
    s_fr = (const uint32_t *)p; p += (fr + 1) * 4;
    s_sb = p; p += fr * 4;
    s_so = (const uint32_t *)p; p += fr * 4;
    s_db = p; p += (fr + 1) * 4;
    s_dp = (const uint32_t *)p; p += (fr + 1) * 4;
    s_dr = (const uint32_t *)p;
    // Cada fotograma tiene que caber en los buffers estaticos (lo garantiza el generador).
    for (uint32_t i = 0; i < fr; i++) {
        if ((s_fp[i + 1] - s_fp[i] + s_dp[i + 1] - s_dp[i]) * 2 > sizeof(s_pix) ||
            (s_fr[i + 1] - s_fr[i] + s_dr[i + 1] - s_dr[i]) * 2 > sizeof(s_runs)) {
            fclose(f);
            return 0;
        }
        uint32_t end = h->mask_bytes;
        for (uint32_t j = i + 1; j < fr; j++) if (s_so[j] > s_so[i]) { end = s_so[j]; break; }
        if (end - s_so[i] > sizeof(s_mask)) { fclose(f); return 0; }
    }
    // Fotograma de restos (solo capa A, sin sombra).
    if (h->pix_bytes - s_fp[fr] * 2 > sizeof(s_pix) || h->runs_bytes - s_fr[fr] * 2 > sizeof(s_runs)) {
        fclose(f);
        return 0;
    }
    s_bin_f = f;
    s_payload = hb;
    s_pix_bytes = h->pix_bytes;
    s_runs_bytes = h->runs_bytes;
    s_mask_bytes = h->mask_bytes;
    s_loaded_kind = kind;
    s_loaded_dir = dir;
    s_cur_frame = -1;
    return 1;
}

// Carga en los buffers el fotograma `f` (o el de restos, f == frames) del bin abierto.
static void remate_prepare_frame(int f) {
    if (!s_bin_f || f == s_cur_frame) return;
    const int fr = g_remate_kind_info[s_loaded_kind].frames;
    if (f < 0 || f > fr) return;
    uint32_t pix_a, pix_b, run_a, run_b;
    if (f == fr) {
        // Fotograma de restos: el ultimo del bin, solo capa A y sin sombra (no tiene entradas siguientes).
        pix_a = s_pix_bytes / 2 - s_fp[f];
        pix_b = 0;
        run_a = s_runs_bytes / 2 - s_fr[f];
        run_b = 0;
    } else {
        pix_a = s_fp[f + 1] - s_fp[f];
        pix_b = s_dp[f + 1] - s_dp[f];
        run_a = s_fr[f + 1] - s_fr[f];
        run_b = s_dr[f + 1] - s_dr[f];
    }
    read_at(s_payload + s_fp[f] * 2, s_pix, pix_a * 2);
    read_at(s_payload + s_dp[f] * 2, s_pix + pix_a * 2, pix_b * 2);
    const uint32_t runs_base = s_payload + s_pix_bytes;
    read_at(runs_base + s_fr[f] * 2, s_runs, run_a * 2);
    read_at(runs_base + s_dr[f] * 2, s_runs + run_a * 2, run_b * 2);
    if (f < fr && (s_cur_frame < 0 || s_cur_frame >= fr || s_so[f] != s_so[s_cur_frame])) {
        uint32_t end = s_mask_bytes;
        for (int j = f + 1; j < fr; j++) if (s_so[j] > s_so[f]) { end = s_so[j]; break; }
        read_at(s_payload + s_pix_bytes + s_runs_bytes + s_so[f], s_mask, end - s_so[f]);
#if HW_SHADOWS
        hwshadow_invalidate(s_mask);
#endif
    }
    s_pix_a = (const uint16_t *)s_pix;
    s_pix_b = (const uint16_t *)(s_pix + pix_a * 2);
    s_run_a = (const uint16_t *)s_runs;
    s_run_b = (const uint16_t *)(s_runs + run_a * 2);
    s_shadow = s_mask;
    s_cur_frame = f;
}

const uint16_t *remate_layer_pixels(int layer) {
    return layer ? s_pix_b : s_pix_a;
}

const uint16_t *remate_layer_runs(int layer) {
    return layer ? s_run_b : s_run_a;
}

const uint8_t *remate_shadow_mask(void) {
    return s_shadow;
}

const uint8_t *remate_layer_bounds(int layer, int f) {
    return (layer ? s_db : s_fb) + f * 4;
}

const uint8_t *remate_shadow_bounds(int f) {
    return s_sb + f * 4;
}

// Estado del remate en curso y de los restos que quedan. Enteros, sin float.
static int s_active;         // 1 = suena la celda combinada
static int s_approach;       // 1 = embestida previa (el heroe corre al punto de inicio)
static int s_dash_t;         // frames de embestida
static int s_kind;           // REMATE_KIND_EXVOTO, REMATE_KIND_CIRENEO o REMATE_KIND_OJO
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

static int kind_frames(void) { return g_remate_kind_info[s_kind].frames; }
static int kind_ticks(void) { return g_remate_kind_info[s_kind].ticks; }

void remate_reset(void) {
    s_active = 0;
    s_approach = 0;
    s_killing = 0;
    s_rem_t = 0;
    s_post_invuln_t = 0;
    remate_close_bin();
}

int remate_active(void) { return s_active; }
int remate_approaching(void) { return s_approach; }
int remate_invuln(void) { return s_post_invuln_t; }
int remate_kind(void) { return s_kind; }
int remate_killing(void) { return s_killing; }
int remate_dir(void) { return s_dir; }

int remate_frame(void) {
    int f = s_t / kind_ticks();
    const int nf = kind_frames();
    return f >= nf ? nf - 1 : f;
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
        if (g_enemy_ally[i] || !e->active || e->hp <= 0 || e->state != ENEMY_STATE_WOBBLE) continue;
        if (e->type != ENEMY_TYPE_EXVOTO && e->type != ENEMY_TYPE_CHARGER && e->type != ENEMY_TYPE_SHOOTER &&
            e->type != ENEMY_TYPE_BEBE && e->type != ENEMY_TYPE_PARROCO &&
            e->type != ENEMY_TYPE_MONJA && e->type != ENEMY_TYPE_MONAGUILLO) continue;
        int dx = TO_INT(e->x) - hx, dy = TO_INT(e->y) - hy;
        int d2 = dx * dx + GROUND_DY2(dy);
        if (d2 < best_d2) { best_d2 = d2; best = i; }
    }
    if (best < 0) return 0;

    Enemy *e = &enemies[best];
    int ex = TO_INT(e->x), ey = TO_INT(e->y);
    if (e->type == ENEMY_TYPE_CHARGER) s_kind = REMATE_KIND_CIRENEO;
    else if (e->type == ENEMY_TYPE_SHOOTER) s_kind = REMATE_KIND_OJO;
    else if (e->type == ENEMY_TYPE_MONAGUILLO) s_kind = REMATE_KIND_MONAGUILLO;
    else if (e->type == ENEMY_TYPE_BEBE) s_kind = REMATE_KIND_BEBE;
    else s_kind = REMATE_KIND_EXVOTO;

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
    // El Exvoto y el Ojo miran al heroe (que ataca desde s_dir); el Cireneo le da la espalda: el heroe le arranca la
    // cruz por detras. En la celda del Ojo el propio Ojo esta de cara al heroe, como en la del Exvoto.
    e->dir = (s_kind == REMATE_KIND_CIRENEO) ? s_dir : (uint8_t)((s_dir + 4) & 7);
    e->stun_timer = 0;
    e->hit_timer = 0;
    s_rem_t = 0;                                          // un remate nuevo se lleva los restos del anterior
    punch_reset();                                        // si venia de un combo de punetazos, no dejar el golpe colgado
    weapons_cancel_aim();                                 // el heroe suelta lo que cargaba
    // invulnerable toda la embestida y la celda
    g_player_state.invuln_timer = REMATE_DASH_MAX_FRAMES + kind_frames() * kind_ticks() + 4;
    if (s_hero_end_ok) s_approach = 1;                    // sin sitio final libre: como antes, sin embestida
    else { s_active = 1; remate_prepare_frame(0); }
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
    g_player_state.invuln_timer = kind_frames() * kind_ticks() + 2;
    remate_prepare_frame(0);
    sfx_play(SND_REMATE_EXEC, s_ax);
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
        remate_close_bin();
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

    const int nf = kind_frames(), tk = kind_ticks();
    const int tot = nf * tk;
    if (++s_t < tot) {
        if (s_hero_end_ok) {
            // El heroe sigue sus pies horneados de cada fotograma (interpolados entre fotogramas) y la camara con el.
            const int f = s_t / tk, sub = s_t % tk;
            const int8_t *o0 = g_remate_hero_off[s_kind][s_dir][f];
            int ox = o0[0], oy = o0[1];
            if (f + 1 < nf) {
                const int8_t *o1 = g_remate_hero_off[s_kind][s_dir][f + 1];
                ox += ((o1[0] - o0[0]) * sub) / tk;
                oy += ((o1[1] - o0[1]) * sub) / tk;
            }
            *hero_x = TO_FIXED(s_ax + ox);
            *hero_y = TO_FIXED(s_ay + oy);
        }
        remate_prepare_frame(remate_frame());
        return;
    }

    // Fin: el enemigo muere (muerte limpia, sin efectos estandar), el heroe reaparece donde acaba
    // la animacion y el rayo queda cargado del todo.
    s_active = 0;
    e->state = ENEMY_STATE_CHASE;
    const RemateKindInfo *nfo = &g_remate_kind_info[s_kind];
    // Los restos son el ultimo fotograma del bin, sin heroe: se dejan cargados antes de cerrar el fichero.
    if (nfo->has_remnant && s_rem_t <= 0) {
        remate_prepare_frame(nfo->remnant_frame);
        s_rem_t = REMATE_REMNANT_FRAMES;
        s_rem_kind = s_kind;
        s_rem_x = s_ax;
        s_rem_y = s_ay;
        s_rem_dir = s_dir;
    }
    remate_close_bin();
    s_killing = 1;
    if (arpg_inv_has_mechanic(ARPG_MECH_PIRA)) weapons_pira_explode(e);
    enemy_hit(e, 9999, 0, 0);
    pickups_remate_drops(e->x, e->y);            // ARPG: the finisher drops health and mana orbs
    s_killing = 0;
    if (s_hero_end_ok) {
        *hero_x = TO_FIXED(s_ax);
        *hero_y = TO_FIXED(s_ay);
    }
    *hero_dir = s_dir;
    g_player_state.invuln_timer = 0;
    s_post_invuln_t = REMATE_POST_INVULN_FRAMES;
    weapons_ready_instant();
}
