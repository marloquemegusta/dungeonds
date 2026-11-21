#include "inventory.h"
#include "game.h"
#include "arpg_inv.h"
#include "arpg_progress.h"
#include "bestiary_font.h"
#include <stdio.h>
#include <string.h>

// Pantalla inferior (256x192): pestañas, fila de estado (engarce de destino), rejilla 6x3 de 36 px
// y ficha. Los engarces grandes y la vista previa del cambio viven en la pantalla superior.
#define INV_BG      (RGB15(2, 1, 1) | BIT(15))
#define INV_PANEL   (RGB15(3, 2, 2) | BIT(15))
#define INV_PANEL2  (RGB15(5, 4, 3) | BIT(15))
#define INV_EDGE    (RGB15(13, 11, 7) | BIT(15))
#define INV_GOLD    (RGB15(25, 20, 13) | BIT(15))
#define INV_TXT     (RGB15(27, 25, 20) | BIT(15))
#define INV_DIM     (RGB15(17, 15, 12) | BIT(15))
#define INV_GREEN   (RGB15(17, 21, 16) | BIT(15))
#define INV_RED     (RGB15(23, 14, 12) | BIT(15))

static const uint16_t s_rar_bdr[5] = {
    RGB15(19, 17, 16) | BIT(15), RGB15(13, 19, 13) | BIT(15), RGB15(13, 16, 21) | BIT(15),
    RGB15(18, 14, 21) | BIT(15), RGB15(25, 17, 8) | BIT(15)
};
static const uint16_t s_school_col[5] = {
    RGB15(27, 24, 15) | BIT(15), RGB15(24, 14, 11) | BIT(15), RGB15(15, 20, 14) | BIT(15),
    RGB15(19, 15, 21) | BIT(15), RGB15(21, 19, 18) | BIT(15)
};

#define INV_COLS      6
#define INV_CELL      36
#define INV_GX        20
#define INV_GY        38
#define INV_TAB_Y     2
#define INV_TAB_H     18
#define INV_TAB_W     50
#define INV_TAB_X0    3
#define INV_INFO_Y    22
#define INV_ARR_Y     20
#define INV_ARR_L     206
#define INV_ARR_R     236
#define INV_ARR_W     18
#define INV_ARR_H     15
#define INV_CARD_X    4
#define INV_CARD_Y    146
#define INV_CARD_W    248
#define INV_CARD_H    44

// Pantalla superior: cabecera con la escuela, icono, engarces grandes y vista previa.
#define TOP_ICON_X    44
#define TOP_ICON_Y    50
#define TOP_SOCK_Y    100
#define TOP_SOCK_PITCH 80
#define TOP_SUM_Y     144

static int s_tab = 0;
static int s_sel = 0;
static int s_socket_sel = 0;
static int s_confirm = -1;
// La pantalla superior es de un solo buffer: solo se repinta cuando su contenido cambia
// (evita pasarse del VBlank y el tearing que eso provoca).
static int s_top_dirty = 1;

// ---------------------------------------------------------------------------
// Drawing helpers
// ---------------------------------------------------------------------------

static void fill_rect(uint16_t *buf, int x0, int y0, int w, int h, uint16_t col) {
    dirty_rect(x0, y0, x0 + w, y0 + h);
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        for (int x = x0; x < x0 + w; x++)
            if ((unsigned)x < SCREEN_W) buf[y * SCREEN_W + x] = col;
    }
}

static void frame_rect(uint16_t *buf, int x0, int y0, int w, int h, uint16_t col) {
    for (int x = x0; x < x0 + w; x++) {
        if ((unsigned)x >= SCREEN_W) continue;
        if ((unsigned)y0 < SCREEN_H) { buf[y0 * SCREEN_W + x] = col; dirty_row(y0, x, x + 1); }
        if ((unsigned)(y0 + h - 1) < SCREEN_H) { buf[(y0 + h - 1) * SCREEN_W + x] = col; dirty_row(y0 + h - 1, x, x + 1); }
    }
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        if ((unsigned)x0 < SCREEN_W) { buf[y * SCREEN_W + x0] = col; dirty_row(y, x0, x0 + 1); }
        if ((unsigned)(x0 + w - 1) < SCREEN_W) { buf[y * SCREEN_W + x0 + w - 1] = col; dirty_row(y, x0 + w - 1, x0 + w); }
    }
}

static void text_at(uint16_t *buf, int x, int y, const char *s, uint16_t col) {
    if (!s || !*s) return;
    dirty_rect(x, y, x + bestiary_font_measure_utf8(s) + 1, y + bestiary_font_line_height());
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

// El nombre grande de la escuela se dibuja a 1x en un cepo temporal (el font asume stride 256)
// y se estampa al doble. Solo se usa mientras el inventario está abierto. 12 filas bastan para
// mayúsculas y minúsculas acentuadas del font (no se usan versales con tilde).
#define BIG_ROWS 12
static uint16_t s_big_buf[SCREEN_W * BIG_ROWS];

static void text_big(uint16_t *buf, int x, int y, const char *s, uint16_t col) {
    int w = bestiary_font_measure_utf8(s);
    if (w <= 0 || w * 2 > SCREEN_W - 24) return;
    memset(s_big_buf, 0, sizeof(s_big_buf));
    bestiary_font_draw_utf8(s_big_buf, 0, 0, s, 0xFFFF);   // 0xFFFF = marca opaca
    dirty_rect(x, y, x + w * 2, y + BIG_ROWS * 2);
    for (int gy = 0; gy < BIG_ROWS; gy++) {
        for (int gx = 0; gx < w; gx++) {
            if (!s_big_buf[gy * SCREEN_W + gx]) continue;
            int sx = x + gx * 2, sy = y + gy * 2;
            for (int dy = 0; dy < 2; dy++)
                for (int dx = 0; dx < 2; dx++)
                    if ((unsigned)(sx + dx) < SCREEN_W && (unsigned)(sy + dy) < SCREEN_H)
                        buf[(sy + dy) * SCREEN_W + sx + dx] = col;
        }
    }
}

// Flechas de la vista previa (el font no trae ▲▼→).
static void tri_up(uint16_t *buf, int x, int y, uint16_t col) {
    for (int i = 0; i < 7; i++) {
        int w = 1 + i * 2;
        if (w > 11) w = 11;
        fill_rect(buf, x + (11 - w) / 2, y + i, w, 1, col);
    }
}

static void tri_down(uint16_t *buf, int x, int y, uint16_t col) {
    for (int i = 0; i < 7; i++) {
        int w = 11 - i * 2;
        if (w < 1) w = 1;
        fill_rect(buf, x + (11 - w) / 2, y + i, w, 1, col);
    }
}

static void arrow_right(uint16_t *buf, int x, int y, uint16_t col) {
    for (int i = 0; i < 7; i++) {
        int d = i - 3;
        if (d < 0) d = -d;
        int head = 3 - d;
        fill_rect(buf, x, y + i, 4, 1, col);
        if (head > 0) fill_rect(buf, x + 4, y + i, head, 1, col);
    }
}

// ---------------------------------------------------------------------------
// Item helpers
// ---------------------------------------------------------------------------

static const ArpgInvItem *bag_sel_item(void) {
    return arpg_inv_bag_item(s_sel);
}

static void item_display_name(const ArpgInvItem *it, char *buf, int n) {
    if (!it) { buf[0] = 0; return; }
    if (it->kind == ARPG_ITEM_TOME) {
        snprintf(buf, (size_t)n, "Tomo de %s", arpg_inv_school_name(it->school));
        return;
    }
    if (it->kind == ARPG_ITEM_RAYO) { snprintf(buf, (size_t)n, "Rayo"); return; }
    if (it->mech != ARPG_MECH_NONE) {
        const char *m = arpg_inv_mechanic_name(it->mech);
        snprintf(buf, (size_t)n, "%s", (*m) ? m : "Reliquia");
        return;
    }
    snprintf(buf, (size_t)n, "Reliquia");
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

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

static void act_equip(void) {
    const ArpgInvItem *it = arpg_inv_bag_item(s_sel);
    if (!it) return;
    if (it->kind == ARPG_ITEM_TOME) {
        if (arpg_inv_equip_tome(s_sel)) { arpg_inv_recalc(); arpg_progress_save(); keep_sel_valid(); }
        return;
    }
    if (it->kind != ARPG_ITEM_RELIC) return;

    // Cambiar a la pestaña de la reliquia si no estamos en ella.
    if ((int)it->school != s_tab) { s_tab = it->school; s_socket_sel = 0; }

    int target = s_socket_sel;
    if (target >= arpg_inv_socket_count(s_tab)) target = 0;
    int ok;
    if (arpg_inv_socket_item(s_tab, target) == 0) ok = arpg_inv_equip_relic(s_sel, s_tab, target);
    else ok = arpg_inv_swap_relic(s_sel, s_tab, target);
    if (ok) { arpg_inv_recalc(); arpg_progress_save(); keep_sel_valid(); }
}

static void act_scrap(void) {
    if (arpg_inv_scrap(s_sel)) { arpg_inv_recalc(); arpg_progress_save(); s_confirm = -1; keep_sel_valid(); }
}

static void select_tab(int tab) {
    if ((unsigned)tab >= ARPG_INV_SCHOOLS) return;
    s_tab = tab;
    if (s_socket_sel >= arpg_inv_socket_count(s_tab)) s_socket_sel = 0;
    s_confirm = -1;
}

// El engarce de destino se elige de uno en uno: L/R o las flechas táctiles de la inferior
// (el lápiz de la DS solo alcanza la pantalla inferior).
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
    keep_sel_valid();
}

int inventory_top_redraw_pending(void) {
    return s_top_dirty;
}

int inventory_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (keys_down || touch_pressed) s_top_dirty = 1;
    if (touch_pressed) {
        // Pestañas.
        if (touch_y >= INV_TAB_Y && touch_y < INV_TAB_Y + INV_TAB_H) {
            int t = (touch_x - INV_TAB_X0) / INV_TAB_W;
            if (touch_x >= INV_TAB_X0 && (unsigned)t < ARPG_INV_SCHOOLS) { select_tab(t); return 0; }
        }
        // Flechas < > del engarce de destino.
        if (touch_y >= INV_ARR_Y && touch_y < INV_ARR_Y + INV_ARR_H) {
            if (touch_x >= INV_ARR_L && touch_x < INV_ARR_L + INV_ARR_W) { cycle_socket(-1); return 0; }
            if (touch_x >= INV_ARR_R && touch_x < INV_ARR_R + INV_ARR_W) { cycle_socket(1); return 0; }
        }
        // Rejilla de bolsa.
        if (touch_x >= INV_GX && touch_y >= INV_GY) {
            int c = (touch_x - INV_GX) / INV_CELL;
            int r = (touch_y - INV_GY) / INV_CELL;
            if (c >= 0 && c < INV_COLS && r >= 0 && r < 3) {
                int idx = r * INV_COLS + c;
                if ((unsigned)idx < ARPG_INV_BAG && !arpg_inv_bag_empty(idx)) {
                    s_sel = idx;
                    s_confirm = -1;
                }
            }
            return 0;
        }
        return 0;
    }

    if (keys_down & KEY_LEFT)  { if (s_sel % INV_COLS > 0) s_sel--; s_confirm = -1; }
    if (keys_down & KEY_RIGHT) { if (s_sel % INV_COLS < INV_COLS - 1 && s_sel + 1 < ARPG_INV_BAG) s_sel++; s_confirm = -1; }
    if (keys_down & KEY_UP)    { if (s_sel - INV_COLS >= 0) s_sel -= INV_COLS; s_confirm = -1; }
    if (keys_down & KEY_DOWN)  { if (s_sel + INV_COLS < ARPG_INV_BAG) s_sel += INV_COLS; s_confirm = -1; }
    if (keys_down & KEY_L) cycle_socket(-1);
    if (keys_down & KEY_R) cycle_socket(1);

    if (keys_down & KEY_A) {
        if (s_confirm == s_sel) act_scrap();
        else act_equip();
        return 0;
    }
    if (keys_down & KEY_Y) {
        if (arpg_inv_bag_empty(s_sel)) return 0;
        if (s_confirm == s_sel) act_scrap();
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
// Rendering
// ---------------------------------------------------------------------------

static void render_tabs(uint16_t *buf) {
    for (int i = 0; i < ARPG_INV_SCHOOLS; i++) {
        int x = INV_TAB_X0 + i * INV_TAB_W;
        int active = (i == s_tab);
        fill_rect(buf, x, INV_TAB_Y, INV_TAB_W - 1, INV_TAB_H, active ? INV_PANEL : INV_PANEL2);
        frame_rect(buf, x, INV_TAB_Y, INV_TAB_W - 1, INV_TAB_H, active ? INV_GOLD : INV_EDGE);
        text_center(buf, x + (INV_TAB_W - 1) / 2, INV_TAB_Y + 2,
                    arpg_inv_school_name(i), active ? INV_GOLD : INV_DIM);
    }
}

static int school_defined(int school) {
    // LÍMITE decidido: solo Rayo y Ejecución tienen contenido; Glifo y Levantar existen vacíos.
    return school == ARPG_SCHOOL_RAYO || school == ARPG_SCHOOL_EJECUCION || school == ARPG_SCHOOL_PECHO;
}

// Fila de estado: bolsa/cera y el engarce de destino con sus flechas táctiles.
static void render_status(uint16_t *buf) {
    char line[48];
    snprintf(line, sizeof(line), "Bolsa %d/16 · Cera %d", arpg_inv_bag_count(), (int)g_arpg.inv.wax);
    text_at(buf, INV_CARD_X + 2, INV_INFO_Y, line, INV_DIM);

    int n = arpg_inv_socket_count(s_tab);
    if (n <= 0 || !school_defined(s_tab)) return;
    snprintf(line, sizeof(line), "Engarce %d/%d", s_socket_sel + 1, n);
    text_right(buf, INV_ARR_L - 6, INV_INFO_Y, line, INV_GOLD);
    fill_rect(buf, INV_ARR_L, INV_ARR_Y, INV_ARR_W, INV_ARR_H, INV_PANEL2);
    frame_rect(buf, INV_ARR_L, INV_ARR_Y, INV_ARR_W, INV_ARR_H, INV_EDGE);
    text_center(buf, INV_ARR_L + INV_ARR_W / 2, INV_ARR_Y + 2, "<", INV_TXT);
    fill_rect(buf, INV_ARR_R, INV_ARR_Y, INV_ARR_W, INV_ARR_H, INV_PANEL2);
    frame_rect(buf, INV_ARR_R, INV_ARR_Y, INV_ARR_W, INV_ARR_H, INV_EDGE);
    text_center(buf, INV_ARR_R + INV_ARR_W / 2, INV_ARR_Y + 2, ">", INV_TXT);
}

static void render_grid(uint16_t *buf) {
    for (int i = 0; i < INV_COLS * 3; i++) {
        int c = i % INV_COLS, r = i / INV_COLS;
        int x = INV_GX + c * INV_CELL;
        int y = INV_GY + r * INV_CELL;
        const ArpgInvItem *it = arpg_inv_bag_item(i);      // i >= 16 devuelve NULL
        fill_rect(buf, x, y, INV_CELL - 2, INV_CELL - 2, (it && item_fits_tab(it)) ? INV_PANEL2 : INV_PANEL);
        frame_rect(buf, x, y, INV_CELL - 2, INV_CELL - 2, it ? s_rar_bdr[it->rarity] : INV_EDGE);
        if (it) {
            uint16_t dcol = item_fits_tab(it) ? s_school_col[it->school]
                                              : (uint16_t)(((s_school_col[it->school] & 0x7BDEu) >> 1) | BIT(15));
            diamond(buf, x + (INV_CELL - 2) / 2, y + (INV_CELL - 2) / 2, 9, dcol);
            if (it->kind == ARPG_ITEM_TOME) ring(buf, x + (INV_CELL - 2) / 2, y + (INV_CELL - 2) / 2, 13, INV_GOLD);
        }
        if (i == s_sel) frame_rect(buf, x - 1, y - 1, INV_CELL, INV_CELL, (s_confirm == i) ? INV_RED : INV_GOLD);
    }
}

static void render_card(uint16_t *buf) {
    const ArpgInvItem *it = bag_sel_item();
    uint16_t bdr = it ? s_rar_bdr[it->rarity] : INV_EDGE;
    fill_rect(buf, INV_CARD_X, INV_CARD_Y, INV_CARD_W, INV_CARD_H, INV_PANEL);
    frame_rect(buf, INV_CARD_X, INV_CARD_Y, INV_CARD_W, INV_CARD_H, bdr);

    char line[64];
    if (!it) {
        text_at(buf, INV_CARD_X + 6, INV_CARD_Y + 4, "Toca una reliquia de la bolsa", INV_DIM);
        return;
    }

    char name[40];
    item_display_name(it, name, sizeof(name));
    if (s_confirm == s_sel) {
        snprintf(line, sizeof(line), "Desguazar %s?", name);
        text_at(buf, INV_CARD_X + 6, INV_CARD_Y + 2, line, INV_RED);
        snprintf(line, sizeof(line), "+%d cera", arpg_inv_wax_value(it->rarity));
        text_right(buf, INV_CARD_X + INV_CARD_W - 6, INV_CARD_Y + 2, line, INV_GOLD);
        text_at(buf, INV_CARD_X + 6, INV_CARD_Y + 15, "Y/A confirma · B cancela", INV_DIM);
        return;
    }

    text_at(buf, INV_CARD_X + 6, INV_CARD_Y + 2, name, s_rar_bdr[it->rarity]);
    snprintf(line, sizeof(line), "A engarzar · Y desguazar (+%d)", arpg_inv_wax_value(it->rarity));
    text_right(buf, INV_CARD_X + INV_CARD_W - 6, INV_CARD_Y + 2, line, INV_GOLD);

    snprintf(line, sizeof(line), "%s · %s", arpg_inv_rarity_name(it->rarity), arpg_inv_school_name(it->school));
    text_at(buf, INV_CARD_X + 6, INV_CARD_Y + 15, line, INV_DIM);
    if (it->kind == ARPG_ITEM_TOME)
        snprintf(line, sizeof(line), "Tomo de hechizo");
    else if (it->mech != ARPG_MECH_NONE)
        snprintf(line, sizeof(line), "Mecánica: %s", arpg_inv_mechanic_name(it->mech));
    else
        snprintf(line, sizeof(line), "Sin mecánica");
    text_right(buf, INV_CARD_X + INV_CARD_W - 6, INV_CARD_Y + 15, line, INV_GOLD);

    // Líneas de la reliquia (la comparación ▲/▼ vive en la pantalla superior).
    for (int i = 0; i < it->nlines && i < 2; i++) {
        snprintf(line, sizeof(line), "%s %d", arpg_inv_line_name(it->line_kind[i]), it->line_val[i]);
        text_at(buf, INV_CARD_X + 6 + i * 122, INV_CARD_Y + 28, line, INV_TXT);
    }
}

// ---------------------------------------------------------------------------
// Pantalla superior: escuela activa, icono, engarces grandes y vista previa del cambio.
// Solo se dibuja mientras el inventario está abierto.
// ---------------------------------------------------------------------------

static void preview_line(uint16_t *buf, int y, int up, const char *label, int before, int after) {
    uint16_t col = up ? INV_GREEN : INV_RED;
    if (up) tri_up(buf, 14, y, col);
    else tri_down(buf, 14, y, col);

    char a[24], b[8];
    snprintf(a, sizeof(a), "%s %d", label, before);
    snprintf(b, sizeof(b), "%d", after);
    int x = 30;
    text_at(buf, x, y, a, INV_TXT);
    x += bestiary_font_measure_utf8(a) + 4;
    arrow_right(buf, x, y + 3, col);
    text_at(buf, x + 9, y, b, col);
}

void inventory_render_top(uint16_t *buf) {
    if (!buf) return;
    fill_rect(buf, 0, 0, SCREEN_W, SCREEN_H, INV_BG);
    fill_rect(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8, INV_PANEL);
    frame_rect(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8, INV_EDGE);

    char line[64];
    text_big(buf, 14, 8, arpg_inv_school_name(s_tab), INV_GOLD);
    snprintf(line, sizeof(line), "Nivel %d", (int)g_arpg.level);
    text_right(buf, SCREEN_W - 14, 12, line, INV_DIM);

    if (!school_defined(s_tab)) {
        text_center(buf, SCREEN_W / 2, 96, "Sin definir", INV_DIM);
        s_top_dirty = 0;
        return;
    }

    // Icono del hechizo/escuela: anillo dorado con el rombo del color de la escuela.
    ring(buf, TOP_ICON_X, TOP_ICON_Y, 20, INV_GOLD);
    diamond(buf, TOP_ICON_X, TOP_ICON_Y, 12, s_school_col[s_tab]);

    int n = arpg_inv_socket_count(s_tab);
    snprintf(line, sizeof(line), "Engarce %d de %d", s_socket_sel + 1, n);
    text_at(buf, 78, 40, line, INV_TXT);
    text_at(buf, 78, 54, "L / R cambia el engarce", INV_DIM);

    int x0 = SCREEN_W / 2 - ((n - 1) * TOP_SOCK_PITCH) / 2;
    for (int i = 0; i < n; i++) {
        int cx = x0 + i * TOP_SOCK_PITCH;
        const ArpgInvItem *it = arpg_inv_socket_item(s_tab, i);
        if (it) {
            ring(buf, cx, TOP_SOCK_Y, 18, s_rar_bdr[it->rarity]);
            diamond(buf, cx, TOP_SOCK_Y, 12, s_school_col[it->school]);
        } else {
            ring(buf, cx, TOP_SOCK_Y, 18, INV_EDGE);
        }
        if (i == s_socket_sel) ring(buf, cx, TOP_SOCK_Y, 22, INV_GOLD);

        char name[40];
        if (it) item_display_name(it, name, sizeof(name));
        else snprintf(name, sizeof(name), "vacío");
        text_center(buf, cx, 124, name, it ? INV_DIM : INV_EDGE);
    }

    fill_rect(buf, 14, 141, SCREEN_W - 28, 1, INV_EDGE);

    // Resumen: qué cambian los totales de la escuela al engarzar la reliquia seleccionada.
    ArpgInvPreview pv;
    if (arpg_inv_preview_socket(s_sel, s_tab, s_socket_sel, &pv)) {
        int shown = 0;
        for (int k = 0; k < ARPG_LINE_COUNT && shown < 3; k++) {
            if (pv.before[k] == pv.after[k]) continue;
            preview_line(buf, TOP_SUM_Y + shown * 14, pv.after[k] > pv.before[k],
                         arpg_inv_line_name(k), pv.before[k], pv.after[k]);
            shown++;
        }
        if (shown == 0)
            text_at(buf, 14, TOP_SUM_Y, "Sin cambios en las líneas", INV_DIM);
    } else {
        text_at(buf, 14, TOP_SUM_Y, "Elige una reliquia de la bolsa para engarzarla", INV_DIM);
    }
    s_top_dirty = 0;
}

void inventory_render(uint16_t *buf) {
    if (!buf) return;
    fill_rect(buf, 0, 0, SCREEN_W, SCREEN_H, INV_BG);
    render_tabs(buf);
    render_status(buf);
    render_grid(buf);
    render_card(buf);
}
