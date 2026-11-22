#include "inventory.h"
#include "game.h"
#include "arpg_inv.h"
#include "arpg_progress.h"
#include "bestiary_font.h"
#include "inv_art.h"
#include "inv_item_art.h"
#include <stdio.h>
#include <string.h>

// Inventario táctil B (Relicario Lateral) con estética Diablo II / Sacred:
// - Losa de piedra pizarra texturizada + marco biselado grueso con remaches.
// - Casillas y engarces como huecos negro puro hundidos dentro de la piedra.
// - Cero texto redundante en la bolsa; cajetín de Cera estilo oro de Diablo II.
// - Pantalla superior con cajetines de tabla estilo Diablo II y comparación lado a lado.

#define INV_BLACK   (RGB15(1, 1, 1) | BIT(15))
#define INV_SHAD    (RGB15(0, 0, 0) | BIT(15))
#define INV_BEV_HI  (RGB15(15, 13, 10) | BIT(15))
#define INV_BEV_LO  (RGB15(3, 2, 2) | BIT(15))
#define INV_EDGE    (RGB15(12, 10, 7) | BIT(15))
#define INV_GOLD    (RGB15(25, 20, 13) | BIT(15))
#define INV_TXT     (RGB15(27, 25, 21) | BIT(15))
#define INV_DIM     (RGB15(17, 15, 13) | BIT(15))
#define INV_GREEN   (RGB15(15, 22, 14) | BIT(15))
#define INV_RED     (RGB15(24, 12, 11) | BIT(15))
#define INV_SLATE   (RGB15(5, 5, 5) | BIT(15))
#define INV_SLATE2  (RGB15(7, 6, 6) | BIT(15))

static const uint16_t s_rar_bdr[5] = {
    RGB15(19, 17, 16) | BIT(15), RGB15(13, 20, 13) | BIT(15), RGB15(12, 16, 23) | BIT(15),
    RGB15(19, 13, 23) | BIT(15), RGB15(26, 17, 7) | BIT(15)
};
static const uint16_t s_school_col[5] = {
    RGB15(27, 24, 15) | BIT(15), RGB15(24, 14, 11) | BIT(15), RGB15(15, 20, 14) | BIT(15),
    RGB15(19, 15, 21) | BIT(15), RGB15(21, 19, 18) | BIT(15)
};

// Geometría pantalla inferior (256x192).
#define INV_TAB_Y     2
#define INV_TAB_H     17
#define INV_TAB_W     49
#define INV_TAB_X0    5

// Losa principal inferior.
#define INV_SLAB_X    4
#define INV_SLAB_Y    21
#define INV_SLAB_W    248
#define INV_SLAB_H    168

// Columna izquierda: engarces + Crisol.
#define INV_SOCK_CX   44
#define INV_SOCK_Y0   44
#define INV_SOCK_STEP 38
#define INV_SOCK_SZ   32
#define INV_CRUC_X    14
#define INV_CRUC_Y    155
#define INV_CRUC_W    60
#define INV_CRUC_H    24

// Columna derecha: bolsa 4x4 compacta estilo D2 (bloque continuo) + cajetín Cera.
#define INV_COLS      4
#define INV_ROWS      4
#define INV_GX        102
#define INV_GY        29
#define INV_CELL_SZ   32
#define INV_PITCH_X   33
#define INV_PITCH_Y   33
#define INV_WAX_X     164
#define INV_WAX_Y     165
#define INV_WAX_W     72
#define INV_WAX_H     16

// Pantalla superior: losa + cabecera + cajetines.
#define TOP_CARD_Y    58
#define TOP_CARD_W    116
#define TOP_CARD_H    124

static int s_tab = 0;
static int s_sel = 0;
static int s_socket_sel = 0;
static int s_confirm = -1;
static int s_top_dirty = 1;

static int s_touch_held = 0;
static int s_touch_x = 0;
static int s_touch_y = 0;
static int s_drag_bag = -1;
static int s_drag_active = 0;
static int s_drag_start_x = 0;
static int s_drag_start_y = 0;
static int s_drag_x = 0;
static int s_drag_y = 0;
static int s_hover_socket = -1;
static int s_hover_crucible = 0;
static int s_hover_bag = -1;
static int s_top_bg_saved = 0;
static int s_top_slab_drawn = 0;

// ---------------------------------------------------------------------------
// Drawing helpers (piedra pizarra, huecos hundidos y molduras estilo Diablo II)
// ---------------------------------------------------------------------------

static void darken_screen(uint16_t *buf) {
    dirty_rect(0, 0, SCREEN_W, SCREEN_H);
    for (int i = 0; i < SCREEN_W * SCREEN_H; i++) {
        buf[i] = (uint16_t)(((buf[i] & 0x7BDEu) >> 1) | BIT(15));
    }
}

static void fill_rect(uint16_t *buf, int x0, int y0, int w, int h, uint16_t col) {
    dirty_rect(x0, y0, x0 + w, y0 + h);
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        for (int x = x0; x < x0 + w; x++)
            if ((unsigned)x < SCREEN_W) buf[y * SCREEN_W + x] = col;
    }
}

// Textura real de piedra Rock030 (tile 64x64 de inv_art.h).
static void stone_rect(uint16_t *buf, int x0, int y0, int w, int h) {
    dirty_rect(x0, y0, x0 + w, y0 + h);
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        uint16_t *row = &buf[y * SCREEN_W];
        const uint16_t *trow = &s_stone_tex_64[(y & 63) * 64];
        for (int x = x0; x < x0 + w; x++) {
            if ((unsigned)x < SCREEN_W) row[x] = trow[x & 63];
        }
    }
}

static void hline(uint16_t *buf, int x0, int y, int w, uint16_t col) {
    fill_rect(buf, x0, y, w, 1, col);
}

static void vline(uint16_t *buf, int x, int y0, int h, uint16_t col) {
    fill_rect(buf, x, y0, 1, h, col);
}

static void frame_rect(uint16_t *buf, int x0, int y0, int w, int h, uint16_t col) {
    hline(buf, x0, y0, w, col);
    hline(buf, x0, y0 + h - 1, w, col);
    vline(buf, x0, y0, h, col);
    vline(buf, x0 + w - 1, y0, h, col);
}

// Barra de hierro forjado (4 px de grosor con textura martillada y brillo).
static void iron_bar_h(uint16_t *buf, int x0, int y0, int w) {
    dirty_rect(x0, y0, x0 + w, y0 + 4);
    for (int dy = 0; dy < 4; dy++) {
        int sy = y0 + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        const uint16_t *brow = &s_iron_bar_h_16x4[dy * 16];
        for (int dx = 0; dx < w; dx++) {
            int sx = x0 + dx;
            if ((unsigned)sx < SCREEN_W) buf[sy * SCREEN_W + sx] = brow[dx & 15];
        }
    }
}

static void iron_bar_v(uint16_t *buf, int x0, int y0, int h) {
    dirty_rect(x0, y0, x0 + 4, y0 + h);
    for (int dy = 0; dy < h; dy++) {
        int sy = y0 + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        for (int dx = 0; dx < 4; dx++) {
            int sx = x0 + dx;
            if ((unsigned)sx < SCREEN_W)
                buf[sy * SCREEN_W + sx] = s_iron_bar_h_16x4[dx * 16 + (dy & 15)];
        }
    }
}

// Marco exterior de filigrana dorada envejecida (5 px + esquinas labradas 14x14).
static void gold_frame(uint16_t *buf, int x, int y, int w, int h) {
    dirty_rect(x, y, x + w, y + h);
    for (int dy = 0; dy < 5; dy++) {
        const uint16_t *grow = &s_gold_bar_h_16x5[dy * 16];
        for (int dx = 0; dx < w; dx++) {
            int sx = x + dx;
            if ((unsigned)sx >= SCREEN_W) continue;
            if ((unsigned)(y + dy) < SCREEN_H) buf[(y + dy) * SCREEN_W + sx] = grow[dx & 15];
            if ((unsigned)(y + h - 1 - dy) < SCREEN_H) buf[(y + h - 1 - dy) * SCREEN_W + sx] = grow[dx & 15];
        }
    }
    for (int dy = 0; dy < h; dy++) {
        int sy = y + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        for (int dx = 0; dx < 5; dx++) {
            uint16_t c = s_gold_bar_h_16x5[dx * 16 + (dy & 15)];
            if ((unsigned)(x + dx) < SCREEN_W) buf[sy * SCREEN_W + x + dx] = c;
            if ((unsigned)(x + w - 1 - dx) < SCREEN_W) buf[sy * SCREEN_W + x + w - 1 - dx] = c;
        }
    }
    // Esquinas doradas ornamentadas 14x14 (espejadas en cada esquina).
    for (int cy = 0; cy < 14; cy++) {
        for (int cx = 0; cx < 14; cx++) {
            uint16_t c = s_gold_corner_14[cy * 14 + cx];
            if (!c) continue;
            buf[(y + cy) * SCREEN_W + (x + cx)] = c;
            buf[(y + cy) * SCREEN_W + (x + w - 1 - cx)] = c;
            buf[(y + h - 1 - cy) * SCREEN_W + (x + cx)] = c;
            buf[(y + h - 1 - cy) * SCREEN_W + (x + w - 1 - cx)] = c;
        }
    }
}

static void draw_wax_coin(uint16_t *buf, int x0, int y0) {
    dirty_rect(x0, y0, x0 + 10, y0 + 10);
    for (int sy = 0; sy < 10; sy++) {
        for (int sx = 0; sx < 10; sx++) {
            uint16_t c = s_wax_icon_10[sy * 10 + sx];
            if (c) buf[(y0 + sy) * SCREEN_W + (x0 + sx)] = c;
        }
    }
}

// Hueco hundido con textura de obsidiana/piedra oscura + sombra proyectada arriba.
// rarity_tint >= 0 añade un tinte sutil al fondo (estilo Diablo II) sin bordes de 1 px.
static void sunken_box_rar(uint16_t *buf, int x, int y, int w, int h, int rarity_tint) {
    dirty_rect(x, y, x + w, y + h);
    static const uint16_t s_rar_tint[5] = {
        RGB15(0, 0, 0), RGB15(0, 2, 0), RGB15(0, 1, 3), RGB15(2, 0, 3), RGB15(3, 1, 0)
    };
    uint16_t tint = (rarity_tint >= 0 && rarity_tint < 5) ? s_rar_tint[rarity_tint] : 0;
    int shad_h = (h > 12) ? 4 : 2;
    for (int dy = 1; dy < h - 1; dy++) {
        int sy = y + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        const uint16_t *rrow = &s_stone_tex_64[((sy + 23) & 63) * 64];
        for (int dx = 1; dx < w - 1; dx++) {
            int sx = x + dx;
            if ((unsigned)sx >= SCREEN_W) continue;
            // Reutiliza Rock030 a mitad de brillo y desplazado (0 bytes extra).
            uint16_t c = (uint16_t)(((rrow[(sx + 17) & 63] & 0x7BDEu) >> 1) | BIT(15));
            if (dy <= shad_h) c = (uint16_t)(((c & 0x7BDEu) >> 1) | BIT(15));
            if (tint) c = (uint16_t)((c + tint) | BIT(15));
            buf[sy * SCREEN_W + sx] = c;
        }
    }
    hline(buf, x, y, w, INV_SHAD);
    vline(buf, x, y, h, INV_SHAD);
    hline(buf, x, y + h - 1, w, INV_BEV_HI);
    vline(buf, x + w - 1, y, h, INV_BEV_HI);
}

static void sunken_box(uint16_t *buf, int x, int y, int w, int h, uint16_t unused_bdr) {
    (void)unused_bdr;
    sunken_box_rar(buf, x, y, w, h, -1);
}

static void corner_ticks(uint16_t *buf, int x, int y, int w, int h, uint16_t col) {
    hline(buf, x, y, 5, col); vline(buf, x, y, 5, col);
    hline(buf, x + w - 5, y, 5, col); vline(buf, x + w - 1, y, 5, col);
    hline(buf, x, y + h - 1, 5, col); vline(buf, x, y + h - 5, 5, col);
    hline(buf, x + w - 5, y + h - 1, 5, col); vline(buf, x + w - 1, y + h - 5, 5, col);
}

static void text_at(uint16_t *buf, int x, int y, const char *s, uint16_t col) {
    if (!s || !*s) return;
    dirty_rect(x, y, x + bestiary_font_measure_utf8(s) + 2, y + bestiary_font_line_height() + 1);
    bestiary_font_draw_utf8(buf, x + 1, y + 1, s, INV_SHAD);
    bestiary_font_draw_utf8(buf, x, y, s, col);
}

static void text_right(uint16_t *buf, int xr, int y, const char *s, uint16_t col) {
    text_at(buf, xr - bestiary_font_measure_utf8(s), y, s, col);
}

static void text_center(uint16_t *buf, int cx, int y, const char *s, uint16_t col) {
    text_at(buf, cx - bestiary_font_measure_utf8(s) / 2, y, s, col);
}

static void diamond(uint16_t *buf, int cx, int cy, int r, uint16_t col) {
    dirty_rect(cx - r, cy - r, cx + r + 1, cy + r + 1);
    for (int dy = -r; dy <= r; dy++) {
        int sy = cy + dy;
        if ((unsigned)sy >= SCREEN_H) continue;
        int w = r - (dy < 0 ? -dy : dy);
        for (int dx = -w; dx <= w; dx++) {
            int sx = cx + dx;
            if ((unsigned)sx < SCREEN_W) buf[sy * SCREEN_W + sx] = col;
        }
    }
}

static void ring(uint16_t *buf, int cx, int cy, int r, uint16_t col) {
    dirty_rect(cx - r, cy - r, cx + r + 1, cy + r + 1);
    for (int dy = -r; dy <= r; dy++) {
        for (int dx = -r; dx <= r; dx++) {
            int d = dx * dx + dy * dy;
            if (d > r * r || d < (r - 2) * (r - 2)) continue;
            int sx = cx + dx, sy = cy + dy;
            if ((unsigned)sx < SCREEN_W && (unsigned)sy < SCREEN_H) buf[sy * SCREEN_W + sx] = col;
        }
    }
}

static void tri_up(uint16_t *buf, int x, int y, uint16_t col) {
    for (int i = 0; i < 6; i++) {
        int w = 1 + i * 2;
        if (w > 9) w = 9;
        fill_rect(buf, x + (9 - w) / 2, y + i, w, 1, col);
    }
}

static void tri_down(uint16_t *buf, int x, int y, uint16_t col) {
    for (int i = 0; i < 6; i++) {
        int w = 9 - i * 2;
        if (w < 1) w = 1;
        fill_rect(buf, x + (9 - w) / 2, y + i, w, 1, col);
    }
}

static void draw_sprite_24(uint16_t *buf, const uint16_t *spr, int cx, int cy, int dim) {
    int x0 = cx - 12, y0 = cy - 12;
    dirty_rect(x0, y0, x0 + 24, y0 + 24);
    for (int sy = 0; sy < 24; sy++) {
        int dy = y0 + sy;
        if ((unsigned)dy >= SCREEN_H) continue;
        for (int sx = 0; sx < 24; sx++) {
            uint16_t c = spr[sy * 24 + sx];
            if (!c) continue;
            int dx = x0 + sx;
            if ((unsigned)dx >= SCREEN_W) continue;
            if (dim) c = (uint16_t)(((c & 0x7BDEu) >> 1) | BIT(15));
            buf[dy * SCREEN_W + dx] = c;
        }
    }
}

static void draw_item_glyph(uint16_t *buf, const ArpgInvItem *it, int cx, int cy, int r, int dim) {
    if (!it) return;
    if (it->kind == ARPG_ITEM_TOME) {
        if (it->school == ARPG_SCHOOL_GLIFO) {
            draw_sprite_24(buf, s_tome_glifo_24, cx, cy, dim);
            return;
        }
        if (it->school == ARPG_SCHOOL_LEVANTAR) {
            draw_sprite_24(buf, s_tome_levantar_24, cx, cy, dim);
            return;
        }
        if (it->school == ARPG_SCHOOL_RAYO) {
            draw_sprite_24(buf, s_tome_rayo_24, cx, cy, dim);
            return;
        }
    } else if (it->kind == ARPG_ITEM_RELIC) {
        if (it->school == ARPG_SCHOOL_PECHO) {
            draw_sprite_24(buf, s_heart_24, cx, cy, dim);
            return;
        }
        if (it->school == ARPG_SCHOOL_RAYO) {
            draw_sprite_24(buf, s_relic_lanza_24, cx, cy, dim);
            return;
        }
        if (it->school == ARPG_SCHOOL_EJECUCION) {
            draw_sprite_24(buf, s_relic_nudillera_24, cx, cy, dim);
            return;
        }
        if (it->school == ARPG_SCHOOL_LEVANTAR) {
            draw_sprite_24(buf, s_relic_calavera_24, cx, cy, dim);
            return;
        }
    }
    uint16_t col = s_school_col[it->school];
    if (dim) col = (uint16_t)(((col & 0x7BDEu) >> 1) | BIT(15));
    diamond(buf, cx, cy, r, col);
    if (it->kind == ARPG_ITEM_TOME) ring(buf, cx, cy, r + 4, INV_GOLD);
}

// ---------------------------------------------------------------------------
// Item & Hit-test helpers
// ---------------------------------------------------------------------------

static int school_defined(int school) {
    return school == ARPG_SCHOOL_RAYO || school == ARPG_SCHOOL_EJECUCION || school == ARPG_SCHOOL_PECHO;
}

static const ArpgInvItem *bag_sel_item(void) {
    return arpg_inv_bag_item(s_sel);
}

static void item_display_name(const ArpgInvItem *it, char *buf, int n) {
    if (!it) { buf[0] = 0; return; }
    if (it->kind == ARPG_ITEM_TOME) {
        snprintf(buf, (size_t)n, "Tomo %s", arpg_inv_school_name(it->school));
        return;
    }
    if (it->kind == ARPG_ITEM_RAYO) { snprintf(buf, (size_t)n, "Rayo"); return; }
    if (it->mech != ARPG_MECH_NONE) {
        const char *m = arpg_inv_mechanic_name(it->mech);
        snprintf(buf, (size_t)n, "%s", (*m) ? m : "Reliquia");
        return;
    }
    switch (it->school) {
        case ARPG_SCHOOL_RAYO: snprintf(buf, (size_t)n, "Punta de Lanza"); break;
        case ARPG_SCHOOL_EJECUCION: snprintf(buf, (size_t)n, "Nudillera"); break;
        case ARPG_SCHOOL_LEVANTAR: snprintf(buf, (size_t)n, "Cráneo Votivo"); break;
        case ARPG_SCHOOL_PECHO: snprintf(buf, (size_t)n, "Sagrado Corazón"); break;
        case ARPG_SCHOOL_GLIFO: snprintf(buf, (size_t)n, "Reliquia del Glifo"); break;
        default: snprintf(buf, (size_t)n, "Reliquia"); break;
    }
}

static int item_fits_tab(const ArpgInvItem *it) {
    if (!it) return 0;
    if (s_tab == ARPG_SCHOOL_PECHO) return it->school == ARPG_SCHOOL_PECHO;
    if (it->kind == ARPG_ITEM_TOME) return 1;
    return (int)it->school == s_tab;
}

static void keep_sel_valid(void) {
    if ((unsigned)s_sel >= ARPG_INV_BAG || arpg_inv_bag_empty(s_sel)) {
        for (int i = 0; i < ARPG_INV_BAG; i++)
            if (!arpg_inv_bag_empty(i)) { s_sel = i; return; }
        s_sel = 0;
    }
}

static int hit_bag_slot(int tx, int ty) {
    if (tx < INV_GX || ty < INV_GY) return -1;
    int dx = tx - INV_GX;
    int dy = ty - INV_GY;
    int c = dx / INV_PITCH_X;
    int r = dy / INV_PITCH_Y;
    if (c < 0 || c >= INV_COLS || r < 0 || r >= INV_ROWS) return -1;
    if (dx % INV_PITCH_X >= INV_CELL_SZ || dy % INV_PITCH_Y >= INV_CELL_SZ) return -1;
    int idx = r * INV_COLS + c;
    return (idx < ARPG_INV_BAG) ? idx : -1;
}

static int hit_socket(int tx, int ty) {
    int n = arpg_inv_socket_count(s_tab);
    if (n <= 0 || !school_defined(s_tab)) return -1;
    for (int i = 0; i < n; i++) {
        int cy = INV_SOCK_Y0 + i * INV_SOCK_STEP;
        int x0 = INV_SOCK_CX - INV_SOCK_SZ / 2;
        int y0 = cy - INV_SOCK_SZ / 2;
        if (tx >= x0 - 2 && tx < x0 + INV_SOCK_SZ + 2 &&
            ty >= y0 - 2 && ty < y0 + INV_SOCK_SZ + 2) return i;
    }
    return -1;
}

static int hit_crucible(int tx, int ty) {
    return tx >= INV_CRUC_X && tx < INV_CRUC_X + INV_CRUC_W &&
           ty >= INV_CRUC_Y && ty < INV_CRUC_Y + INV_CRUC_H;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

static void act_equip_to(int bag_idx, int target_socket) {
    const ArpgInvItem *it = arpg_inv_bag_item(bag_idx);
    if (!it) return;
    if (it->kind == ARPG_ITEM_TOME) {
        if (arpg_inv_equip_tome(bag_idx)) { arpg_inv_recalc(); arpg_progress_save(); keep_sel_valid(); }
        return;
    }
    if (it->kind != ARPG_ITEM_RELIC) return;

    if ((int)it->school != s_tab) { s_tab = it->school; s_socket_sel = 0; }
    int n = arpg_inv_socket_count(s_tab);
    if (target_socket < 0 || target_socket >= n) target_socket = 0;

    int ok;
    if (arpg_inv_socket_item(s_tab, target_socket) == 0)
        ok = arpg_inv_equip_relic(bag_idx, s_tab, target_socket);
    else
        ok = arpg_inv_swap_relic(bag_idx, s_tab, target_socket);

    if (ok) {
        s_socket_sel = target_socket;
        arpg_inv_recalc();
        arpg_progress_save();
        keep_sel_valid();
    }
}

static void act_equip(void) {
    act_equip_to(s_sel, s_socket_sel);
}

static void act_scrap_idx(int bag_idx) {
    if (arpg_inv_scrap(bag_idx)) {
        arpg_inv_recalc();
        arpg_progress_save();
        s_confirm = -1;
        keep_sel_valid();
    }
}

static void swap_bag_slots(int a, int b) {
    if (a == b || (unsigned)a >= ARPG_INV_BAG || (unsigned)b >= ARPG_INV_BAG) return;
    ArpgInvItem tmp = g_arpg.inv.bag[a];
    g_arpg.inv.bag[a] = g_arpg.inv.bag[b];
    g_arpg.inv.bag[b] = tmp;
    s_sel = b;
    arpg_progress_save();
}

static void select_tab(int tab) {
    if ((unsigned)tab >= ARPG_INV_SCHOOLS) return;
    s_tab = tab;
    if (s_socket_sel >= arpg_inv_socket_count(s_tab)) s_socket_sel = 0;
    s_confirm = -1;
    s_top_slab_drawn = 0;
}

static void cycle_socket(int step) {
    int n = arpg_inv_socket_count(s_tab);
    if (n <= 0) return;
    s_socket_sel = (s_socket_sel + step + n) % n;
    s_confirm = -1;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

void inventory_open(void) {
    s_tab = 0;
    s_socket_sel = 0;
    s_confirm = -1;
    s_top_dirty = 1;
    s_top_bg_saved = 0;
    s_top_slab_drawn = 0;
    s_drag_bag = -1;
    s_drag_active = 0;
    s_hover_socket = -1;
    s_hover_crucible = 0;
    s_hover_bag = -1;
    keep_sel_valid();
}

void inventory_set_touch_held(int touch_held, int touch_x, int touch_y) {
    s_touch_held = touch_held;
    s_touch_x = touch_x;
    s_touch_y = touch_y;
}

int inventory_top_redraw_pending(void) {
    return s_top_dirty;
}

int inventory_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (keys_down || touch_pressed) s_top_dirty = 1;

    if (touch_pressed) {
        if (touch_y >= INV_TAB_Y && touch_y < INV_TAB_Y + INV_TAB_H) {
            int t = (touch_x - INV_TAB_X0) / INV_TAB_W;
            if (touch_x >= INV_TAB_X0 && (unsigned)t < ARPG_INV_SCHOOLS) {
                select_tab(t);
                return 0;
            }
        }
        int sk = hit_socket(touch_x, touch_y);
        if (sk >= 0) {
            s_socket_sel = sk;
            s_confirm = -1;
            return 0;
        }
        if (hit_crucible(touch_x, touch_y)) {
            if (!arpg_inv_bag_empty(s_sel)) {
                if (s_confirm == s_sel) act_scrap_idx(s_sel);
                else s_confirm = s_sel;
            }
            return 0;
        }
        int bidx = hit_bag_slot(touch_x, touch_y);
        if (bidx >= 0) {
            if (!arpg_inv_bag_empty(bidx)) {
                s_sel = bidx;
                s_confirm = -1;
                s_drag_bag = bidx;
                s_drag_active = 0;
                s_drag_start_x = touch_x;
                s_drag_start_y = touch_y;
                s_drag_x = touch_x;
                s_drag_y = touch_y;
            }
            return 0;
        }
        return 0;
    }

    if (s_drag_bag >= 0) {
        if (s_touch_held) {
            s_drag_x = s_touch_x;
            s_drag_y = s_touch_y;
            if (!s_drag_active) {
                int dx = s_drag_x - s_drag_start_x;
                int dy = s_drag_y - s_drag_start_y;
                if (dx * dx + dy * dy >= 16) {
                    s_drag_active = 1;
                    s_confirm = -1;
                    const ArpgInvItem *it = arpg_inv_bag_item(s_drag_bag);
                    if (it && it->kind == ARPG_ITEM_RELIC && (int)it->school != s_tab) {
                        select_tab(it->school);
                    }
                    s_top_dirty = 1;
                }
            }
            if (s_drag_active) {
                int nh_sock = hit_socket(s_drag_x, s_drag_y);
                int nh_cruc = hit_crucible(s_drag_x, s_drag_y);
                int nh_bag = hit_bag_slot(s_drag_x, s_drag_y);
                if (nh_sock != s_hover_socket || nh_cruc != s_hover_crucible || nh_bag != s_hover_bag) {
                    s_hover_socket = nh_sock;
                    s_hover_crucible = nh_cruc;
                    s_hover_bag = nh_bag;
                    s_top_dirty = 1;
                }
            }
            return 0;
        } else {
            if (s_drag_active) {
                if (s_hover_socket >= 0) {
                    act_equip_to(s_drag_bag, s_hover_socket);
                } else if (s_hover_crucible) {
                    act_scrap_idx(s_drag_bag);
                } else if (s_hover_bag >= 0 && s_hover_bag != s_drag_bag) {
                    swap_bag_slots(s_drag_bag, s_hover_bag);
                }
                s_top_dirty = 1;
            }
            s_drag_bag = -1;
            s_drag_active = 0;
            s_hover_socket = -1;
            s_hover_crucible = 0;
            s_hover_bag = -1;
            return 0;
        }
    }

    if (keys_down & KEY_LEFT)  { if (s_sel % INV_COLS > 0) s_sel--; s_confirm = -1; }
    if (keys_down & KEY_RIGHT) { if (s_sel % INV_COLS < INV_COLS - 1 && s_sel + 1 < ARPG_INV_BAG) s_sel++; s_confirm = -1; }
    if (keys_down & KEY_UP)    { if (s_sel - INV_COLS >= 0) s_sel -= INV_COLS; s_confirm = -1; }
    if (keys_down & KEY_DOWN)  { if (s_sel + INV_COLS < ARPG_INV_BAG) s_sel += INV_COLS; s_confirm = -1; }
    if (keys_down & KEY_L) cycle_socket(-1);
    if (keys_down & KEY_R) cycle_socket(1);

    if (keys_down & KEY_A) {
        if (s_confirm == s_sel) act_scrap_idx(s_sel);
        else act_equip();
        return 0;
    }
    if (keys_down & KEY_Y) {
        if (arpg_inv_bag_empty(s_sel)) return 0;
        if (s_confirm == s_sel) act_scrap_idx(s_sel);
        else s_confirm = s_sel;
        return 0;
    }
    if (keys_down & KEY_B) {
        if (s_confirm >= 0) { s_confirm = -1; return 0; }
        return 1;
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Rendering: Pantalla inferior (losa de piedra + huecos negros estilo Diablo II)
// ---------------------------------------------------------------------------

static void render_tabs(uint16_t *buf) {
    static const char *const s_tab_lbl[ARPG_INV_SCHOOLS] = {
        "Rayo", "Ejecuc.", "Glifo", "Levant.", "Pecho"
    };
    for (int i = 0; i < ARPG_INV_SCHOOLS; i++) {
        int x = INV_TAB_X0 + i * INV_TAB_W;
        int active = (i == s_tab);
        int ty = INV_TAB_Y + (active ? 0 : 2);
        int th = INV_TAB_H - (active ? 0 : 2);
        fill_rect(buf, x, ty, INV_TAB_W - 3, th, active ? INV_SLATE2 : INV_SLATE);
        hline(buf, x, ty, INV_TAB_W - 3, active ? INV_GOLD : INV_BEV_HI);
        vline(buf, x, ty, th, active ? INV_GOLD : INV_EDGE);
        vline(buf, x + INV_TAB_W - 4, ty, th, INV_SHAD);
        text_center(buf, x + (INV_TAB_W - 3) / 2, ty + 2,
                    s_tab_lbl[i], active ? INV_GOLD : INV_DIM);
    }
}

static void render_bottom_slab(uint16_t *buf) {
    stone_rect(buf, INV_SLAB_X, INV_SLAB_Y, INV_SLAB_W, INV_SLAB_H);
    gold_frame(buf, INV_SLAB_X, INV_SLAB_Y, INV_SLAB_W, INV_SLAB_H);
    // Barra de hierro forjado separando engarces (izq) de bolsa (der).
    iron_bar_v(buf, 83, INV_SLAB_Y + 5, INV_SLAB_H - 10);
}

static void render_left_sockets(uint16_t *buf) {
    int n = arpg_inv_socket_count(s_tab);
    if (!school_defined(s_tab) || n <= 0) {
        text_center(buf, INV_SOCK_CX, 86, "—", INV_DIM);
    } else {
        if (n > 1) {
            vline(buf, INV_SOCK_CX, INV_SOCK_Y0, (n - 1) * INV_SOCK_STEP, INV_SHAD);
            vline(buf, INV_SOCK_CX + 1, INV_SOCK_Y0, (n - 1) * INV_SOCK_STEP, INV_BEV_HI);
        }
        for (int i = 0; i < n; i++) {
            int cy = INV_SOCK_Y0 + i * INV_SOCK_STEP;
            int x0 = INV_SOCK_CX - INV_SOCK_SZ / 2;
            int y0 = cy - INV_SOCK_SZ / 2;
            const ArpgInvItem *it = arpg_inv_socket_item(s_tab, i);
            int hl = (s_drag_active && s_hover_socket == i) || (!s_drag_active && i == s_socket_sel);

            sunken_box_rar(buf, x0, y0, INV_SOCK_SZ, INV_SOCK_SZ, it ? (int)it->rarity : -1);
            if (hl) corner_ticks(buf, x0, y0, INV_SOCK_SZ, INV_SOCK_SZ, INV_GOLD);
            if (it) {
                draw_item_glyph(buf, it, INV_SOCK_CX, cy - 1, 9, 0);
            }
        }
    }

    // Crisol de desguace (botón hundido en piedra abajo-izquierda).
    sunken_box(buf, INV_CRUC_X, INV_CRUC_Y, INV_CRUC_W, INV_CRUC_H, 0);
    if (s_hover_crucible || s_confirm >= 0) {
        corner_ticks(buf, INV_CRUC_X, INV_CRUC_Y, INV_CRUC_W, INV_CRUC_H,
                     s_hover_crucible ? INV_GOLD : INV_RED);
    }
    text_center(buf, INV_CRUC_X + INV_CRUC_W / 2, INV_CRUC_Y + 5,
                (s_confirm == s_sel && !arpg_inv_bag_empty(s_sel)) ? "¿Fundir?" : "Fundir",
                s_hover_crucible ? INV_GOLD : (s_confirm >= 0 ? INV_RED : INV_DIM));
}

static void render_right_bag(uint16_t *buf) {
    // Marco exterior de hierro forjado alrededor del bloque compacto 4x4.
    iron_bar_h(buf, INV_GX - 4, INV_GY - 4, INV_COLS * INV_PITCH_X + 7);
    iron_bar_h(buf, INV_GX - 4, INV_GY + INV_ROWS * INV_PITCH_Y - 1, INV_COLS * INV_PITCH_X + 7);
    iron_bar_v(buf, INV_GX - 4, INV_GY - 4, INV_ROWS * INV_PITCH_Y + 7);
    iron_bar_v(buf, INV_GX + INV_COLS * INV_PITCH_X - 1, INV_GY - 4, INV_ROWS * INV_PITCH_Y + 7);

    // Bolsa 4x4: bloque continuo con casillas sombreadas arriba y línea de rareza abajo.
    for (int i = 0; i < ARPG_INV_BAG; i++) {
        int c = i % INV_COLS, r = i / INV_COLS;
        int x = INV_GX + c * INV_PITCH_X;
        int y = INV_GY + r * INV_PITCH_Y;
        const ArpgInvItem *it = arpg_inv_bag_item(i);
        int is_ghost = (s_drag_active && i == s_drag_bag);
        int hl = (s_drag_active && i == s_hover_bag) || (!s_drag_active && i == s_sel);

        sunken_box_rar(buf, x, y, INV_CELL_SZ, INV_CELL_SZ, (it && !is_ghost) ? (int)it->rarity : -1);
        if (hl) corner_ticks(buf, x, y, INV_CELL_SZ, INV_CELL_SZ, (s_confirm == i) ? INV_RED : INV_GOLD);
        if (it && !is_ghost) {
            draw_item_glyph(buf, it, x + INV_CELL_SZ / 2, y + INV_CELL_SZ / 2 - 1, 9, !item_fits_tab(it));
        }
    }

    // Cajetín hundido de Cera abajo-derecha con moneda dorada (estilo oro de Diablo II).
    sunken_box(buf, INV_WAX_X, INV_WAX_Y, INV_WAX_W, INV_WAX_H, 0);
    draw_wax_coin(buf, INV_WAX_X + 5, INV_WAX_Y + 3);
    char wax_s[16];
    snprintf(wax_s, sizeof(wax_s), "%d", (int)g_arpg.inv.wax);
    text_right(buf, INV_WAX_X + INV_WAX_W - 6, INV_WAX_Y + 1, wax_s, INV_TXT);
}

static void render_drag_ghost(uint16_t *buf) {
    if (!s_drag_active || s_drag_bag < 0) return;
    const ArpgInvItem *it = arpg_inv_bag_item(s_drag_bag);
    if (!it) return;
    int x = s_drag_x - 14;
    int y = s_drag_y - 14;
    fill_rect(buf, x + 2, y + 3, 28, 28, INV_SHAD);
    fill_rect(buf, x, y, 28, 28, INV_BLACK);
    frame_rect(buf, x, y, 28, 28, s_rar_bdr[it->rarity]);
    draw_item_glyph(buf, it, s_drag_x, s_drag_y, 9, 0);
}

// ---------------------------------------------------------------------------
// Rendering: Pantalla superior (cajetines estilo Diablo II + comparación)
// ---------------------------------------------------------------------------

// Cajetín de tabla estilo Diablo II: etiqueta en la piedra + valor en caja negra hundida.
static void d2_stat_box(uint16_t *buf, int x, int y, int w, const char *label,
                        const char *val, uint16_t val_col) {
    text_at(buf, x + 2, y + 1, label, INV_DIM);
    int box_w = (w < 140) ? 40 : 54;
    int bx = x + w - box_w;
    sunken_box(buf, bx, y, box_w, 15, 0);
    text_center(buf, bx + box_w / 2, y + 1, val, val_col);
}

static void render_item_card(uint16_t *buf, int x, int y, int w, int h, const char *tag,
                             const ArpgInvItem *it, uint16_t tag_col) {
    sunken_box_rar(buf, x, y, w, h, -1);
    fill_rect(buf, x + 1, y + 1, w - 2, 13, INV_SLATE2);
    text_center(buf, x + w / 2, y + 1, tag, tag_col);

    if (!it) {
        text_center(buf, x + w / 2, y + 56, "—", INV_DIM);
        return;
    }

    char name[40];
    item_display_name(it, name, sizeof(name));
    draw_item_glyph(buf, it, x + 16, y + 31, 8, 0);
    text_at(buf, x + 29, y + 19, name, s_rar_bdr[it->rarity]);
    text_at(buf, x + 29, y + 32, arpg_inv_rarity_name(it->rarity), INV_DIM);
    hline(buf, x + 6, y + 48, w - 12, INV_EDGE);

    int row_y = y + 54;
    if (it->mech != ARPG_MECH_NONE) {
        text_at(buf, x + 8, row_y, arpg_inv_mechanic_name(it->mech), INV_GOLD);
        row_y += 15;
    }
    for (int i = 0; i < it->nlines && i < 2; i++) {
        char val[16];
        snprintf(val, sizeof(val), "%+d", (int)it->line_val[i]);
        d2_stat_box(buf, x + 4, row_y + i * 18, w - 8,
                    arpg_inv_line_name(it->line_kind[i]), val, INV_TXT);
    }
}

static void render_top_comparison(uint16_t *buf, int bag_idx, int sock_idx) {
    const ArpgInvItem *held = arpg_inv_bag_item(bag_idx);
    const ArpgInvItem *eq = arpg_inv_socket_item(s_tab, sock_idx);
    if (!held) return;

    // Tarjeta derecha primero (evita corte de VBlank arriba-derecha).
    sunken_box_rar(buf, 132, TOP_CARD_Y, TOP_CARD_W, TOP_CARD_H, -1);
    fill_rect(buf, 133, TOP_CARD_Y + 1, TOP_CARD_W - 2, 13, INV_SLATE2);
    text_center(buf, 132 + TOP_CARD_W / 2, TOP_CARD_Y + 1, "EN MANO", INV_GOLD);

    char name[40];
    item_display_name(held, name, sizeof(name));
    draw_item_glyph(buf, held, 132 + 16, TOP_CARD_Y + 31, 8, 0);
    text_at(buf, 132 + 29, TOP_CARD_Y + 19, name, s_rar_bdr[held->rarity]);
    text_at(buf, 132 + 29, TOP_CARD_Y + 32, arpg_inv_rarity_name(held->rarity), INV_DIM);
    hline(buf, 138, TOP_CARD_Y + 48, TOP_CARD_W - 12, INV_EDGE);

    int row_y = TOP_CARD_Y + 54;
    if (held->mech != ARPG_MECH_NONE) {
        text_at(buf, 140, row_y, arpg_inv_mechanic_name(held->mech), INV_GOLD);
        row_y += 15;
    }

    ArpgInvPreview pv;
    if (arpg_inv_preview_socket(bag_idx, s_tab, sock_idx, &pv)) {
        int shown = 0;
        for (int k = 0; k < ARPG_LINE_COUNT && shown < 2; k++) {
            int d = pv.after[k] - pv.before[k];
            if (d == 0) continue;
            char val[16];
            snprintf(val, sizeof(val), "%+d", d);
            d2_stat_box(buf, 136, row_y + shown * 18, TOP_CARD_W - 8,
                        arpg_inv_line_name(k), val, d > 0 ? INV_GREEN : INV_RED);
            shown++;
        }
    }

    render_item_card(buf, 8, TOP_CARD_Y, TOP_CARD_W, TOP_CARD_H,
                     eq ? "EQUIPADA" : "VACÍO", eq, INV_DIM);
}

void inventory_render_top(uint16_t *buf) {
    if (!buf) return;
    if (!s_top_bg_saved) {
        darken_screen(buf);
        s_top_bg_saved = 1;
        s_top_slab_drawn = 0;
    }

    char line[48];
    if (!s_top_slab_drawn) {
        // Losa de piedra superior + marco + cabecera: solo al abrir o cambiar de pestaña.
        stone_rect(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8);
        gold_frame(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8);

        sunken_box(buf, 14, 12, 34, 34, INV_GOLD);
        diamond(buf, 31, 29, 10, s_school_col[s_tab]);
        // Título contenido en versalitas/mayúsculas (sin escalado 2x gigante).
        static const char *const s_hdr_names[ARPG_INV_SCHOOLS] = {
            "R A Y O", "E J E C U C I Ó N", "G L I F O", "L E V A N T A R", "P E C H O"
        };
        text_at(buf, 56, 22, s_hdr_names[s_tab], INV_GOLD);

        snprintf(line, sizeof(line), "Nv.%d", (int)g_arpg.level);
        sunken_box(buf, 198, 19, 44, 16, 0);
        text_center(buf, 220, 20, line, INV_TXT);

        iron_bar_h(buf, 10, 50, SCREEN_W - 20);
        s_top_slab_drawn = 1;
    } else {
        // Solo refrescar la zona inferior de tarjetas (cabe holgado en VBlank).
        stone_rect(buf, 10, 54, SCREEN_W - 20, SCREEN_H - 64);
    }

    if (!school_defined(s_tab)) {
        text_center(buf, SCREEN_W / 2, 106, "Sin definir", INV_DIM);
        s_top_dirty = 0;
        return;
    }

    if (s_drag_active && s_hover_socket >= 0) {
        render_top_comparison(buf, s_drag_bag, s_hover_socket);
        s_top_dirty = 0;
        return;
    }

    const ArpgInvItem *sel_it = bag_sel_item();
    if (!sel_it) {
        s_top_dirty = 0;
        return;
    }

    // Ficha superior estilo Diablo II: bloque objeto + cajetines de atributos y delta.
    sunken_box_rar(buf, 12, 58, 232, 42, -1);
    draw_item_glyph(buf, sel_it, 31, 79, 10, 0);
    char name[40];
    item_display_name(sel_it, name, sizeof(name));
    text_at(buf, 50, 62, name, s_rar_bdr[sel_it->rarity]);
    snprintf(line, sizeof(line), "%s · %s", arpg_inv_rarity_name(sel_it->rarity), arpg_inv_school_name(sel_it->school));
    text_at(buf, 50, 76, line, INV_DIM);

    // Cajetín de cera que da al fundir.
    sunken_box(buf, 196, 65, 40, 16, 0);
    draw_wax_coin(buf, 200, 68);
    snprintf(line, sizeof(line), "%d", arpg_inv_wax_value(sel_it->rarity));
    text_right(buf, 232, 66, line, INV_GOLD);

    int ycur = 104;
    if (sel_it->mech != ARPG_MECH_NONE) {
        text_at(buf, 16, ycur, arpg_inv_mechanic_name(sel_it->mech), INV_GOLD);
        ycur += 14;
        hline(buf, 14, ycur, 228, INV_EDGE);
        ycur += 5;
    }

    // Tabla única alineada estilo Sacred / Diablo II (etiqueta a la izq, cajetín a la der).
    for (int i = 0; i < sel_it->nlines && i < 2; i++) {
        char val[16];
        snprintf(val, sizeof(val), "%+d", (int)sel_it->line_val[i]);
        d2_stat_box(buf, 14, ycur, 228,
                    arpg_inv_line_name(sel_it->line_kind[i]), val, INV_TXT);
        ycur += 16;
    }

    ArpgInvPreview pv;
    if (arpg_inv_preview_socket(s_sel, s_tab, s_socket_sel, &pv)) {
        int shown = 0;
        for (int k = 0; k < ARPG_LINE_COUNT && shown < 2 && ycur <= 168; k++) {
            int d = pv.after[k] - pv.before[k];
            if (d == 0) continue;
            uint16_t col = d > 0 ? INV_GREEN : INV_RED;
            if (d > 0) tri_up(buf, 16, ycur + 4, col);
            else tri_down(buf, 16, ycur + 4, col);
            snprintf(line, sizeof(line), "%d -> %d", pv.before[k], pv.after[k]);
            d2_stat_box(buf, 28, ycur, 214, arpg_inv_line_name(k), line, col);
            ycur += 16;
            shown++;
        }
    }
    s_top_dirty = 0;
}

void inventory_render(uint16_t *buf) {
    if (!buf) return;
    darken_screen(buf);
    render_tabs(buf);
    render_bottom_slab(buf);
    render_left_sockets(buf);
    render_right_bag(buf);
    render_drag_ghost(buf);
}
