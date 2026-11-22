#include "inventory.h"
#include "game.h"
#include "arpg_inv.h"
#include "arpg_progress.h"
#include "bestiary_font.h"
#include "inv_art.h"
#include "inv_item_art.h"
#include "sfx.h"
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

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

// Pantalla superior: losa + cabecera + cajetines + ventana de objeto giratorio.
#define TOP_CARD_Y    56
#define TOP_CARD_W    116
#define TOP_CARD_H    126

#define TOP_WIN_X     12
#define TOP_WIN_Y     58
#define TOP_WIN_W     82
#define TOP_WIN_H     122
#define TOP_WIN_CX    (TOP_WIN_X + TOP_WIN_W / 2)
#define TOP_WIN_CY    110
#define TOP_RX        102
#define TOP_RW        142

#define INV_FOCUS_BAG   0
#define INV_FOCUS_SOCK  1

#define INV_SPIN_SZ     56
#define INV_SPIN_MAGIC  0x4954u
#define INV_SPIN_TICKS  3

static int s_inv_tab = 0;
static int s_inv_sel = 0;
static int s_socket_sel = 0;
static int s_confirm = -1;
static int s_top_dirty = 1;
static int s_top_rot_dirty = 0;

static int s_rot_fd = -1;
static int s_rot_frames = 0;
static int s_rot_frame_idx = 0;
static int s_rot_tick = 0;
static int s_rot_bob_tick = 0;
static uint8_t s_rot_loaded_kind = 0xFF;
static uint8_t s_rot_loaded_school = 0xFF;
static uint16_t s_rot_buf[INV_SPIN_SZ * INV_SPIN_SZ];
static int s_rot_valid = 0;

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
static int s_inv_focus = 0;               // INV_FOCUS_*: dónde está el cursor de botones
static int s_drag_sock = -1;          // engarce del que se arrastra (o -1)
static int s_sock_tap_armed = 0;      // el engarce ya estaba seleccionado al pulsarlo: un toque lo desengarza
static const char *s_msg = 0;
static int s_msg_t = 0;
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

static int measure_wrapped_lines(int max_w, const char *utf8) {
    if (!utf8 || !*utf8) return 0;
    const BestiaryGlyph *g_sp = bestiary_font_get_glyph(' ');
    int sp_w = g_sp ? g_sp->advance : 3;
    int lines = 1;
    int line_w = 0;
    const char *p = utf8;
    while (*p) {
        while (*p == ' ') p++;
        if (!*p) break;
        if (*p == '\n') { lines++; line_w = 0; p++; continue; }
        const char *wstart = p;
        int ww = 0;
        while (*p && *p != ' ' && *p != '\n') {
            uint8_t b0 = (uint8_t)*p;
            uint32_t cp = b0;
            if (b0 >= 0xC2 && b0 <= 0xDF && p[1]) {
                cp = ((uint32_t)(b0 & 0x1F) << 6) | ((uint32_t)(uint8_t)p[1] & 0x3F);
                p += 2;
            } else if (b0 >= 0xE0 && b0 <= 0xEF && p[1] && p[2]) {
                cp = ((uint32_t)(b0 & 0x0F) << 12) | (((uint32_t)(uint8_t)p[1] & 0x3F) << 6) | ((uint32_t)(uint8_t)p[2] & 0x3F);
                p += 3;
            } else {
                p++;
            }
            const BestiaryGlyph *g = bestiary_font_get_glyph(cp);
            if (!g) g = bestiary_font_get_glyph('?');
            if (g) ww += g->advance;
        }
        if (wstart == p) break;
        if (line_w > 0 && line_w + sp_w + ww > max_w) {
            lines++;
            line_w = ww;
        } else {
            line_w += (line_w > 0 ? sp_w : 0) + ww;
        }
    }
    return lines;
}

static int text_wrapped(uint16_t *buf, int x, int y, int max_w, int line_step, const char *s, uint16_t col) {
    if (!s || !*s) return 0;
    int nlines = measure_wrapped_lines(max_w, s);
    int h = nlines * line_step;
    dirty_rect(x, y, x + max_w + 2, y + h + 2);
    bestiary_font_draw_wrapped(buf, x + 1, y + 1, max_w, line_step, s, INV_SHAD);
    bestiary_font_draw_wrapped(buf, x, y, max_w, line_step, s, col);
    return h;
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

static void draw_sprite_56(uint16_t *buf, const uint16_t *spr, int cx, int cy) {
    int x0 = cx - INV_SPIN_SZ / 2, y0 = cy - INV_SPIN_SZ / 2;
    dirty_rect(x0, y0, x0 + INV_SPIN_SZ, y0 + INV_SPIN_SZ);
    for (int sy = 0; sy < INV_SPIN_SZ; sy++) {
        int dy = y0 + sy;
        if ((unsigned)dy >= SCREEN_H) continue;
        uint16_t *dst = &buf[dy * SCREEN_W];
        const uint16_t *src = &spr[sy * INV_SPIN_SZ];
        for (int sx = 0; sx < INV_SPIN_SZ; sx++) {
            uint16_t c = src[sx];
            if (!c) continue;
            int dx = x0 + sx;
            if ((unsigned)dx < SCREEN_W) dst[dx] = c;
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
    return school == ARPG_SCHOOL_RAYO || school == ARPG_SCHOOL_EJECUCION || school == ARPG_SCHOOL_PECHO ||
           school == ARPG_SCHOOL_GLIFO;   // Levantar queda fuera de la protodemo
}

// 1 si hay un tomo de esa escuela puesto en un hueco de hechizo (Glifo, Levantar).
static int tome_equipped(int school) {
    for (int i = 1; i < ARPG_INV_SPELLS; i++)
        if (g_arpg.inv.spell[i].kind == ARPG_ITEM_TOME && g_arpg.inv.spell[i].school == school) return 1;
    return 0;
}

static const ArpgInvItem *bag_sel_item(void) {
    return arpg_inv_bag_item(s_inv_sel);
}

// Objeto que se muestra en la pantalla superior: el del engarce si el cursor está en los engarces.
static const ArpgInvItem *view_item(void) {
    if (s_inv_focus == INV_FOCUS_SOCK) return arpg_inv_socket_item(s_inv_tab, s_socket_sel);
    return arpg_inv_bag_item(s_inv_sel);
}

static void show_msg(const char *m) {
    s_msg = m;
    s_msg_t = 90;
}

// Texto que se acorta con "." si no cabe en `max_w` px.
static void text_fit(uint16_t *buf, int x, int y, int max_w, const char *s, uint16_t col) {
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%s", s ? s : "");
    if (bestiary_font_measure_utf8(tmp) > max_w) {
        int len = (int)strlen(tmp);
        while (len > 1) {
            len--;
            while (len > 1 && ((uint8_t)tmp[len] & 0xC0) == 0x80) len--;   // no cortar un carácter UTF-8
            tmp[len] = '.';
            tmp[len + 1] = 0;
            if (bestiary_font_measure_utf8(tmp) <= max_w) break;
        }
    }
    text_at(buf, x, y, tmp, col);
}

static void item_display_name(const ArpgInvItem *it, char *buf, int n) {
    if (!it || !buf || n <= 0) { if (buf && n > 0) buf[0] = 0; return; }
    snprintf(buf, (size_t)n, "%s", arpg_inv_item_name(it));
}

static void card_item_name(const ArpgInvItem *it, int max_w, char *buf, int n) {
    item_display_name(it, buf, n);
    if (it && max_w < 95 && it->name_id == 1 && bestiary_font_measure_utf8(buf) > max_w) {
        snprintf(buf, (size_t)n, "Sello del Corazón");
    }
}

// Si la selección quedó en un hueco vacío (tras equipar, fundir o desengarzar), salta al siguiente objeto
// de la bolsa (con vuelta al principio), mejor uno de la escuela `pref` (-1 = cualquiera).
static void keep_sel_valid_pref(int pref) {
    if ((unsigned)s_inv_sel < ARPG_INV_BAG && !arpg_inv_bag_empty(s_inv_sel)) return;
    if ((unsigned)s_inv_sel >= ARPG_INV_BAG) s_inv_sel = 0;
    for (int pass = 0; pass < 2; pass++) {
        if (pass == 0 && pref < 0) continue;
        for (int d = 0; d < ARPG_INV_BAG; d++) {
            int i = (s_inv_sel + d) % ARPG_INV_BAG;
            const ArpgInvItem *it = arpg_inv_bag_item(i);
            if (!it) continue;
            if (pass == 0 && (int)it->school != pref) continue;
            s_inv_sel = i;
            return;
        }
    }
}

static void keep_sel_valid(void) { keep_sel_valid_pref(-1); }

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
    int n = arpg_inv_socket_count(s_inv_tab);
    if (n <= 0 || !school_defined(s_inv_tab)) return -1;
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

// Engarce al que va una reliquia con A: el primero libre de su escuela; si están todos ocupados,
// el engarce seleccionado (se intercambian).
static int equip_target(const ArpgInvItem *it) {
    int sc = it->school;
    int n = arpg_inv_socket_count(sc);
    for (int k = 0; k < n; k++)
        if (!arpg_inv_socket_item(sc, k)) return k;
    return (sc == s_inv_tab && s_socket_sel < n) ? s_socket_sel : 0;
}

// target_socket < 0: elige el engarce solo (equip_target).
static void act_equip_to(int bag_idx, int target_socket) {
    const ArpgInvItem *it = arpg_inv_bag_item(bag_idx);
    if (!it) return;
    if (it->kind == ARPG_ITEM_TOME) {
        int school = it->school;
        if (!school_defined(school)) { show_msg("Sin definir"); return; }   // Levantar: fuera de la protodemo
        if (arpg_inv_equip_tome(bag_idx)) {
            arpg_inv_recalc();
            arpg_progress_save();
            keep_sel_valid_pref(school);
            // Señal visible: la pestaña del tomo se abre ("Equipado") y la bolsa apunta a su primera reliquia.
            if (school_defined(school)) {
                s_inv_tab = school;
                s_socket_sel = 0;
                for (int i = 0; i < ARPG_INV_BAG; i++) {
                    const ArpgInvItem *r = arpg_inv_bag_item(i);
                    if (r && r->kind == ARPG_ITEM_RELIC && (int)r->school == school) { s_inv_sel = i; break; }
                }
            }
            s_confirm = -1;
            s_top_slab_drawn = 0;
            s_top_dirty = 1;
            sfx_play(SND_RELIC_SOCKET, -1);
        }
        return;
    }
    if (it->kind != ARPG_ITEM_RELIC) return;

    int school = it->school;
    if (!school_defined(school)) return;
    if (school != s_inv_tab) { s_inv_tab = school; s_socket_sel = 0; s_top_slab_drawn = 0; }
    int n = arpg_inv_socket_count(s_inv_tab);
    if (target_socket < 0) target_socket = equip_target(it);
    if (target_socket >= n) target_socket = 0;

    int ok;
    if (arpg_inv_socket_item(s_inv_tab, target_socket) == 0)
        ok = arpg_inv_equip_relic(bag_idx, s_inv_tab, target_socket);
    else
        ok = arpg_inv_swap_relic(bag_idx, s_inv_tab, target_socket);

    if (ok) {
        s_socket_sel = target_socket;
        s_confirm = -1;
        arpg_inv_recalc();
        arpg_progress_save();
        // Tras un intercambio la reliquia vieja ocupa el hueco de bolsa de la nueva.
        keep_sel_valid_pref(school);
        s_top_dirty = 1;
        sfx_play(SND_RELIC_SOCKET, -1);
    }
}

// Saca la reliquia del engarce a la bolsa. Sin hueco en la bolsa avisa y no hace nada.
static int act_unequip_socket(int socket) {
    if (!arpg_inv_socket_item(s_inv_tab, socket)) return 0;
    int slot = arpg_inv_first_free_bag();
    if (slot < 0) { show_msg("Bolsa llena"); return 0; }
    if (!arpg_inv_unequip_socket(s_inv_tab, socket)) return 0;
    arpg_inv_recalc();
    arpg_progress_save();
    s_inv_sel = slot;
    s_confirm = -1;
    s_top_dirty = 1;
    sfx_play(SND_UI_CLICK, -1);
    return 1;
}

// X: guarda en la bolsa el tomo de la pestaña actual (el hechizo deja de salir en el radial).
static void act_unequip_tome(void) {
    for (int i = 1; i < ARPG_INV_SPELLS; i++) {
        const ArpgInvItem *sp = &g_arpg.inv.spell[i];
        if (sp->kind == ARPG_ITEM_TOME && (int)sp->school == s_inv_tab) {
            int slot = arpg_inv_first_free_bag();
            if (slot < 0) { show_msg("Bolsa llena"); return; }
            if (arpg_inv_unequip_tome(i)) {
                s_inv_sel = slot;            // el tomo guardado queda seleccionado (A lo vuelve a poner)
                arpg_inv_recalc();
                arpg_progress_save();
                s_top_slab_drawn = 0;
                s_top_dirty = 1;
                sfx_play(SND_UI_CLICK, -1);
            }
            return;
        }
    }
}

static void act_equip(void) {
    act_equip_to(s_inv_sel, -1);
}

static void act_scrap_idx(int bag_idx) {
    const ArpgInvItem *it = arpg_inv_bag_item(bag_idx);
    int pref = it ? (int)it->school : -1;
    if (arpg_inv_scrap(bag_idx)) {
        arpg_inv_recalc();
        arpg_progress_save();
        s_confirm = -1;
        s_top_dirty = 1;
        keep_sel_valid_pref(pref);
        sfx_play(SND_RELIC_SOCKET, -1);
    }
}

static void swap_bag_slots(int a, int b) {
    if (a == b || (unsigned)a >= ARPG_INV_BAG || (unsigned)b >= ARPG_INV_BAG) return;
    ArpgInvItem tmp = g_arpg.inv.bag[a];
    g_arpg.inv.bag[a] = g_arpg.inv.bag[b];
    g_arpg.inv.bag[b] = tmp;
    s_inv_sel = b;
    arpg_progress_save();
}

static void select_tab(int tab) {
    if ((unsigned)tab >= ARPG_INV_SCHOOLS) return;
    s_inv_tab = tab;
    if (s_socket_sel >= arpg_inv_socket_count(s_inv_tab)) s_socket_sel = 0;
    if (!school_defined(s_inv_tab)) s_inv_focus = INV_FOCUS_BAG;
    s_confirm = -1;
    s_top_slab_drawn = 0;
    s_top_dirty = 1;
    sfx_play(SND_UI_CLICK, -1);
}

static void sync_tab_to_bag_sel(void) {
    const ArpgInvItem *it = bag_sel_item();
    if (it && it->kind == ARPG_ITEM_RELIC && (int)it->school != s_inv_tab) {
        s_inv_tab = (int)it->school;
        if (s_socket_sel >= arpg_inv_socket_count(s_inv_tab)) s_socket_sel = 0;
        s_top_slab_drawn = 0;
    }
}

// Soltar en la bolsa un engarce arrastrado: sobre una reliquia de su escuela se intercambian;
// sobre un hueco libre se queda ahí; sobre otro objeto va al primer hueco libre.
static void act_drop_socket(int socket, int hover_bag) {
    if (hover_bag < 0) return;                       // soltar fuera: no pasa nada
    const ArpgInvItem *tgt = arpg_inv_bag_item(hover_bag);
    if (tgt && tgt->kind == ARPG_ITEM_RELIC && (int)tgt->school == s_inv_tab) {
        if (arpg_inv_swap_relic(hover_bag, s_inv_tab, socket)) {
            s_socket_sel = socket;
            arpg_inv_recalc();
            arpg_progress_save();
            s_inv_sel = hover_bag;
            s_top_dirty = 1;
            sfx_play(SND_RELIC_SOCKET, -1);
        }
        return;
    }
    int free0 = arpg_inv_first_free_bag();
    if (!act_unequip_socket(socket)) return;
    if (!tgt && hover_bag != free0) swap_bag_slots(free0, hover_bag);
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

static const char *item_spin_slug(const ArpgInvItem *it) {
    if (!it) return NULL;
    if (it->kind == ARPG_ITEM_TOME) {
        if (it->school == ARPG_SCHOOL_GLIFO) return "tome_glifo";
        if (it->school == ARPG_SCHOOL_LEVANTAR) return "tome_levantar";
        if (it->school == ARPG_SCHOOL_RAYO) return "tome_rayo";
    } else if (it->kind == ARPG_ITEM_RELIC) {
        if (it->school == ARPG_SCHOOL_PECHO) return "relic_corazon";
        if (it->school == ARPG_SCHOOL_RAYO) return "relic_lanza";
        if (it->school == ARPG_SCHOOL_EJECUCION) return "relic_nudillera";
        if (it->school == ARPG_SCHOOL_LEVANTAR) return "relic_calavera";
    }
    return NULL;
}

static void rot_close(void) {
    if (s_rot_fd >= 0) { close(s_rot_fd); s_rot_fd = -1; }
    s_rot_valid = 0;
    s_rot_frames = 0;
    s_rot_loaded_kind = 0xFF;
    s_rot_loaded_school = 0xFF;
}

static int read_exact(int fd, void *dst, int bytes) {
    uint8_t *p = (uint8_t *)dst;
    int got = 0;
    while (got < bytes) {
        int r = (int)read(fd, p + got, (size_t)(bytes - got));
        if (r <= 0) return 0;
        got += r;
    }
    return 1;
}

static void rot_ensure_item(const ArpgInvItem *it) {
    if (!it) { rot_close(); return; }
    if (s_rot_fd >= 0 && s_rot_loaded_kind == it->kind && s_rot_loaded_school == it->school) return;
    rot_close();
    s_rot_loaded_kind = it->kind;
    s_rot_loaded_school = it->school;
    const char *slug = item_spin_slug(it);
    if (!slug) return;
    char path[64];
    snprintf(path, sizeof(path), "nitro:/items/%s.bin", slug);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return;
    uint16_t hdr[4];
    if (!read_exact(fd, hdr, 8) || hdr[0] != INV_SPIN_MAGIC || hdr[1] == 0 ||
        hdr[2] != INV_SPIN_SZ || hdr[3] != INV_SPIN_SZ) {
        close(fd);
        return;
    }
    if (!read_exact(fd, s_rot_buf, INV_SPIN_SZ * INV_SPIN_SZ * 2)) {
        close(fd);
        return;
    }
    s_rot_fd = fd;
    s_rot_frames = (int)hdr[1];
    s_rot_frame_idx = 0;
    s_rot_tick = 0;
    s_rot_valid = 1;
    s_top_rot_dirty = 1;
}

static void rot_step(void) {
    const ArpgInvItem *it = view_item();
    rot_ensure_item(it);
    s_rot_bob_tick++;
    if (s_rot_valid && s_rot_fd >= 0) {
        s_rot_tick++;
        if (s_rot_tick >= INV_SPIN_TICKS) {
            s_rot_tick = 0;
            s_rot_frame_idx = (s_rot_frame_idx + 1) % s_rot_frames;
            off_t off = (off_t)(8 + s_rot_frame_idx * (INV_SPIN_SZ * INV_SPIN_SZ * 2));
            if (lseek(s_rot_fd, off, SEEK_SET) == off &&
                read_exact(s_rot_fd, s_rot_buf, INV_SPIN_SZ * INV_SPIN_SZ * 2)) {
                s_top_rot_dirty = 1;
            }
        } else if ((s_rot_bob_tick & 7) == 0) {
            s_top_rot_dirty = 1;
        }
    }
}

static int s_tip_card = 0;            // tarjeta de primera vez (DESIGN-ARPG 7) sobre el inventario

void inventory_open(void) {
    s_tip_card = arpg_tip_take(ARPG_TIP_INVENTARIO);
    s_inv_tab = 0;
    s_socket_sel = 0;
    s_confirm = -1;
    s_top_dirty = 1;
    s_top_rot_dirty = 0;
    s_top_bg_saved = 0;
    s_top_slab_drawn = 0;
    s_drag_bag = -1;
    s_drag_active = 0;
    s_hover_socket = -1;
    s_hover_crucible = 0;
    s_hover_bag = -1;
    s_inv_focus = INV_FOCUS_BAG;
    s_drag_sock = -1;
    s_sock_tap_armed = 0;
    s_msg = 0;
    s_msg_t = 0;
    s_rot_bob_tick = 0;
    rot_close();
    keep_sel_valid();
    sync_tab_to_bag_sel();
    rot_ensure_item(view_item());
}

void inventory_set_touch_held(int touch_held, int touch_x, int touch_y) {
    s_touch_held = touch_held;
    s_touch_x = touch_x;
    s_touch_y = touch_y;
}

int inventory_top_redraw_pending(void) {
    return s_top_dirty || s_top_rot_dirty;
}

static int inventory_handle_input(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
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
            int occ = arpg_inv_socket_item(s_inv_tab, sk) != 0;
            s_sock_tap_armed = (s_inv_focus == INV_FOCUS_SOCK && s_socket_sel == sk && occ);
            s_inv_focus = INV_FOCUS_SOCK;
            s_socket_sel = sk;
            s_confirm = -1;
            s_drag_bag = -1;
            s_drag_active = 0;
            s_drag_sock = occ ? sk : -1;
            s_drag_start_x = s_drag_x = touch_x;
            s_drag_start_y = s_drag_y = touch_y;
            return 0;
        }
        if (hit_crucible(touch_x, touch_y)) {
            if (!arpg_inv_bag_empty(s_inv_sel)) {
                if (s_confirm == s_inv_sel) act_scrap_idx(s_inv_sel);
                else s_confirm = s_inv_sel;
            }
            return 0;
        }
        int bidx = hit_bag_slot(touch_x, touch_y);
        if (bidx >= 0) {
            s_inv_focus = INV_FOCUS_BAG;
            s_drag_sock = -1;
            if (!arpg_inv_bag_empty(bidx)) {
                s_inv_sel = bidx;
                s_confirm = -1;
                sync_tab_to_bag_sel();
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

    if (s_drag_bag >= 0 || s_drag_sock >= 0) {
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
                    if (it && it->kind == ARPG_ITEM_RELIC && (int)it->school != s_inv_tab) {
                        select_tab(it->school);
                    }
                    s_sock_tap_armed = 0;
                    s_top_dirty = 1;
                }
            }
            if (s_drag_active) {
                int from_sock = (s_drag_sock >= 0);       // un engarce solo se suelta en la bolsa
                int nh_sock = from_sock ? -1 : hit_socket(s_drag_x, s_drag_y);
                int nh_cruc = from_sock ? 0 : hit_crucible(s_drag_x, s_drag_y);
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
            if (s_drag_active && s_drag_sock >= 0) {
                act_drop_socket(s_drag_sock, s_hover_bag);
                s_top_dirty = 1;
            } else if (!s_drag_active && s_drag_sock >= 0 && s_sock_tap_armed) {
                act_unequip_socket(s_drag_sock);               // segundo toque sobre el engarce ya elegido
            } else if (s_drag_active) {
                if (s_hover_socket >= 0) {
                    act_equip_to(s_drag_bag, s_hover_socket);
                } else if (s_hover_crucible) {
                    s_inv_sel = s_drag_bag;        // Crisol: the drop only marks "confirm melt" (same as Y)
                    s_confirm = s_drag_bag;
                } else if (s_hover_bag >= 0 && s_hover_bag != s_drag_bag) {
                    swap_bag_slots(s_drag_bag, s_hover_bag);
                }
                s_top_dirty = 1;
            }
            s_drag_bag = -1;
            s_drag_sock = -1;
            s_sock_tap_armed = 0;
            s_drag_active = 0;
            s_hover_socket = -1;
            s_hover_crucible = 0;
            s_hover_bag = -1;
            return 0;
        }
    }

    int prev_sel = s_inv_sel;
    if (s_inv_focus == INV_FOCUS_SOCK) {
        // Cursor en los engarces de la pestaña: arriba/abajo eligen engarce, derecha vuelve a la bolsa.
        int n = arpg_inv_socket_count(s_inv_tab);
        if (keys_down & KEY_UP)    { if (s_socket_sel > 0) s_socket_sel--; s_confirm = -1; }
        if (keys_down & KEY_DOWN)  { if (s_socket_sel < n - 1) s_socket_sel++; s_confirm = -1; }
        if (keys_down & KEY_RIGHT) { s_inv_focus = INV_FOCUS_BAG; s_confirm = -1; }
    } else {
        if (keys_down & KEY_LEFT) {
            if (s_inv_sel % INV_COLS > 0) s_inv_sel--;
            else if (school_defined(s_inv_tab) && arpg_inv_socket_count(s_inv_tab) > 0) s_inv_focus = INV_FOCUS_SOCK;
            s_confirm = -1;
        }
        if (keys_down & KEY_RIGHT) { if (s_inv_sel % INV_COLS < INV_COLS - 1 && s_inv_sel + 1 < ARPG_INV_BAG) s_inv_sel++; s_confirm = -1; }
        if (keys_down & KEY_UP)    { if (s_inv_sel - INV_COLS >= 0) s_inv_sel -= INV_COLS; s_confirm = -1; }
        if (keys_down & KEY_DOWN)  { if (s_inv_sel + INV_COLS < ARPG_INV_BAG) s_inv_sel += INV_COLS; s_confirm = -1; }
        if (s_inv_sel != prev_sel) sync_tab_to_bag_sel();
    }
    if (keys_down & KEY_L) select_tab((s_inv_tab + ARPG_INV_SCHOOLS - 1) % ARPG_INV_SCHOOLS);
    if (keys_down & KEY_R) select_tab((s_inv_tab + 1) % ARPG_INV_SCHOOLS);

    if (keys_down & KEY_A) {
        if (s_inv_focus == INV_FOCUS_SOCK) act_unequip_socket(s_socket_sel);
        else if (s_confirm == s_inv_sel) act_scrap_idx(s_inv_sel);
        else act_equip();
        return 0;
    }
    if (keys_down & KEY_X) {
        if (s_inv_focus == INV_FOCUS_SOCK && arpg_inv_socket_item(s_inv_tab, s_socket_sel)) act_unequip_socket(s_socket_sel);
        else act_unequip_tome();
        return 0;
    }
    if (keys_down & KEY_Y) {
        if (s_inv_focus != INV_FOCUS_BAG) return 0;
        if (arpg_inv_bag_empty(s_inv_sel)) return 0;
        if (s_confirm == s_inv_sel) act_scrap_idx(s_inv_sel);
        else s_confirm = s_inv_sel;
        return 0;
    }
    if (keys_down & KEY_B) {
        if (s_confirm >= 0) { s_confirm = -1; return 0; }
        rot_close();
        return 1;
    }
    return 0;
}

int inventory_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (s_msg_t > 0) s_msg_t--;
    if (s_tip_card) {                 // se cierra con A, B o un toque, y no hace nada mas
        if ((keys_down & (KEY_A | KEY_B)) || touch_pressed) {
            s_tip_card = 0;
            s_top_dirty = 1;
        }
        return 0;
    }
    int exit_inv = inventory_handle_input(keys_down, touch_pressed, touch_x, touch_y);
    if (!exit_inv) rot_step();
    return exit_inv;
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
        int active = (i == s_inv_tab);
        int ty = INV_TAB_Y + (active ? 0 : 2);
        int th = INV_TAB_H - (active ? 0 : 2);
        fill_rect(buf, x, ty, INV_TAB_W - 3, th, active ? INV_SLATE2 : INV_SLATE);
        if (tome_equipped(i)) hline(buf, x + 3, ty + th - 2, INV_TAB_W - 9, INV_GOLD);   // tomo puesto
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
    int n = arpg_inv_socket_count(s_inv_tab);
    if (!school_defined(s_inv_tab) || n <= 0) {
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
            const ArpgInvItem *it = arpg_inv_socket_item(s_inv_tab, i);
            int from_me = (s_drag_active && s_drag_sock == i);
            int hl = (s_drag_active && s_hover_socket == i) ||
                     (!s_drag_active && s_inv_focus == INV_FOCUS_SOCK && i == s_socket_sel);

            sunken_box_rar(buf, x0, y0, INV_SOCK_SZ, INV_SOCK_SZ, (it && !from_me) ? (int)it->rarity : -1);
            if (hl) corner_ticks(buf, x0, y0, INV_SOCK_SZ, INV_SOCK_SZ, INV_GOLD);
            else if (s_inv_focus == INV_FOCUS_BAG && !s_drag_active && i == s_socket_sel && !it)
                corner_ticks(buf, x0, y0, INV_SOCK_SZ, INV_SOCK_SZ, INV_DIM);   // engarce que recibirá la reliquia (si no hay otro libre)
            if (it && !from_me) {
                draw_item_glyph(buf, it, INV_SOCK_CX, cy - 1, 9, 0);
            }
        }
    }

    // Glifo/Levantar: estado del tomo (el hechizo solo sale en el radial con el tomo puesto).
    if (s_inv_tab == ARPG_SCHOOL_GLIFO || s_inv_tab == ARPG_SCHOOL_LEVANTAR) {
        int on = tome_equipped(s_inv_tab);
        text_center(buf, INV_SOCK_CX, 140, on ? "Tomo puesto" : "Sin tomo", on ? INV_GOLD : INV_DIM);
    }

    // Crisol de desguace (botón hundido en piedra abajo-izquierda).
    sunken_box(buf, INV_CRUC_X, INV_CRUC_Y, INV_CRUC_W, INV_CRUC_H, 0);
    if (s_hover_crucible || s_confirm >= 0) {
        corner_ticks(buf, INV_CRUC_X, INV_CRUC_Y, INV_CRUC_W, INV_CRUC_H,
                     s_hover_crucible ? INV_GOLD : INV_RED);
    }
    text_center(buf, INV_CRUC_X + INV_CRUC_W / 2, INV_CRUC_Y + 5,
                (s_confirm == s_inv_sel && !arpg_inv_bag_empty(s_inv_sel)) ? "¿Fundir?" : "Fundir",
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
        int hl = (s_drag_active && i == s_hover_bag) || (!s_drag_active && i == s_inv_sel);

        sunken_box_rar(buf, x, y, INV_CELL_SZ, INV_CELL_SZ, (it && !is_ghost) ? (int)it->rarity : -1);
        if (hl) corner_ticks(buf, x, y, INV_CELL_SZ, INV_CELL_SZ,
                             (s_confirm == i) ? INV_RED : (s_inv_focus == INV_FOCUS_BAG || s_drag_active ? INV_GOLD : INV_DIM));
        if (it && !is_ghost) {
            draw_item_glyph(buf, it, x + INV_CELL_SZ / 2, y + INV_CELL_SZ / 2 - 1, 9, !arpg_inv_can_equip(it));
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
    if (!s_drag_active || (s_drag_bag < 0 && s_drag_sock < 0)) return;
    const ArpgInvItem *it = (s_drag_sock >= 0) ? arpg_inv_socket_item(s_inv_tab, s_drag_sock) : arpg_inv_bag_item(s_drag_bag);
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
    int box_w = (w < 120) ? 44 : 58;
    int tw = bestiary_font_measure_utf8(val) + 6;
    if (tw > box_w) {
        int max_bw = w - bestiary_font_measure_utf8(label) - 6;
        if (tw <= max_bw) box_w = tw;
    }
    int bx = x + w - box_w;
    sunken_box(buf, bx, y, box_w, 14, 0);
    text_center(buf, bx + box_w / 2, y + 1, val, val_col);
}

static int render_card_header_and_mech(uint16_t *buf, int x, int y, int w, const char *tag,
                                       const ArpgInvItem *it, uint16_t tag_col) {
    sunken_box_rar(buf, x, y, w, TOP_CARD_H, -1);
    fill_rect(buf, x + 1, y + 1, w - 2, 13, INV_SLATE2);
    if (it) {
        char hdr[32];
        int ilvl = it->level ? (int)it->level : 1;
        if (!arpg_inv_can_equip(it)) {
            snprintf(hdr, sizeof(hdr), "REQ. NV.%d", ilvl);
            text_center(buf, x + w / 2, y + 1, hdr, INV_RED);
        } else {
            snprintf(hdr, sizeof(hdr), "%s · Nv.%d", tag, ilvl);
            text_center(buf, x + w / 2, y + 1, hdr, tag_col);
        }
    } else {
        text_center(buf, x + w / 2, y + 1, tag, tag_col);
        text_center(buf, x + w / 2, y + 56, "—", INV_DIM);
        return -1;
    }

    char name[40];
    int name_w = w - 33;
    card_item_name(it, name_w, name, sizeof(name));
    draw_item_glyph(buf, it, x + 15, y + 29, 8, 0);
    int hline_y;
    if (bestiary_font_measure_utf8(name) > name_w) {
        int nh = text_wrapped(buf, x + 29, y + 15, name_w, 9, name, s_rar_bdr[it->rarity]);
        text_at(buf, x + 29, y + 15 + nh, arpg_inv_rarity_name(it->rarity), INV_DIM);
        hline_y = y + 15 + nh + 11;
    } else {
        text_at(buf, x + 29, y + 18, name, s_rar_bdr[it->rarity]);
        text_at(buf, x + 29, y + 30, arpg_inv_rarity_name(it->rarity), INV_DIM);
        hline_y = y + 42;
    }
    if (hline_y < y + 42) hline_y = y + 42;
    hline(buf, x + 6, hline_y, w - 12, INV_EDGE);

    int row_y = hline_y + 3;
    if (it->mech != ARPG_MECH_NONE) {
        text_fit(buf, x + 6, row_y, w - 12, arpg_inv_mechanic_name(it->mech), INV_GOLD);
        row_y += 11;
        char desc[96];
        arpg_inv_mechanic_format(it, desc, sizeof(desc));
        if (desc[0]) {
            row_y += text_wrapped(buf, x + 6, row_y, w - 12, 9, desc, INV_TXT);
        }
        row_y += 2;
    }
    return row_y;
}

static void render_item_card(uint16_t *buf, int x, int y, int w, int h, const char *tag,
                             const ArpgInvItem *it, uint16_t tag_col) {
    (void)h;
    int row_y = render_card_header_and_mech(buf, x, y, w, tag, it, tag_col);
    if (row_y < 0) return;

    for (int i = 0; i < it->nlines && i < 2 && row_y <= y + TOP_CARD_H - 16; i++) {
        char val[20];
        arpg_inv_line_format(it->line_kind[i], (int)it->line_val[i], val, sizeof(val));
        d2_stat_box(buf, x + 4, row_y, w - 8,
                    arpg_inv_line_name(it->line_kind[i]), val, INV_TXT);
        row_y += 15;
    }
}

static void render_top_comparison(uint16_t *buf, int bag_idx, int sock_idx) {
    const ArpgInvItem *held = arpg_inv_bag_item(bag_idx);
    const ArpgInvItem *eq = arpg_inv_socket_item(s_inv_tab, sock_idx);
    if (!held) return;

    // Tarjeta derecha primero (evita corte de VBlank arriba-derecha).
    int row_y = render_card_header_and_mech(buf, 132, TOP_CARD_Y, TOP_CARD_W, "EN MANO", held, INV_GOLD);
    if (row_y >= 0) {
        ArpgInvPreview pv;
        if (arpg_inv_preview_socket(bag_idx, s_inv_tab, sock_idx, &pv)) {
            int ndeltas = 0;
            for (int k = 0; k < ARPG_LINE_COUNT; k++)
                if (pv.after[k] != pv.before[k]) ndeltas++;

            if (ndeltas <= 2) {
                for (int k = 0; k < ARPG_LINE_COUNT && row_y <= TOP_CARD_Y + TOP_CARD_H - 16; k++) {
                    int d = pv.after[k] - pv.before[k];
                    if (d == 0) continue;
                    char val[20];
                    arpg_inv_line_format(k, d, val, sizeof(val));
                    d2_stat_box(buf, 136, row_y, TOP_CARD_W - 8,
                                arpg_inv_line_name(k), val, d > 0 ? INV_GREEN : INV_RED);
                    row_y += 15;
                }
            } else {
                int step = (row_y + ndeltas * 10 <= TOP_CARD_Y + TOP_CARD_H - 2) ? 10 : 9;
                for (int k = 0; k < ARPG_LINE_COUNT && row_y <= TOP_CARD_Y + TOP_CARD_H - 10; k++) {
                    int d = pv.after[k] - pv.before[k];
                    if (d == 0) continue;
                    char val[20];
                    arpg_inv_line_format(k, d, val, sizeof(val));
                    uint16_t col = d > 0 ? INV_GREEN : INV_RED;
                    text_at(buf, 137, row_y, arpg_inv_line_name(k), INV_DIM);
                    text_right(buf, 132 + TOP_CARD_W - 5, row_y, val, col);
                    row_y += step;
                }
            }
        }
    }

    render_item_card(buf, 8, TOP_CARD_Y, TOP_CARD_W, TOP_CARD_H,
                     eq ? "EQUIPADA" : "VACÍO", eq, INV_DIM);
}

static void render_spin_window_item(uint16_t *buf, const ArpgInvItem *sel_it, int redraw_box) {
    static const int8_t s_bob[8] = { -2, -2, -1, 0, 1, 2, 2, 1 };
    int bob_y = s_bob[(s_rot_bob_tick >> 3) & 7];
    int rar = sel_it ? (int)sel_it->rarity : -1;

    if (redraw_box) {
        sunken_box_rar(buf, TOP_WIN_X, TOP_WIN_Y, TOP_WIN_W, TOP_WIN_H, rar);
    } else {
        // Solo refrescar el rectángulo del objeto flotante (sin tocar bordes ni cajetín de cera).
        static const uint16_t s_rar_tint[5] = {
            RGB15(0, 0, 0), RGB15(0, 2, 0), RGB15(0, 1, 3), RGB15(2, 0, 3), RGB15(3, 1, 0)
        };
        uint16_t tint = (rar >= 0 && rar < 5) ? s_rar_tint[rar] : 0;
        int rx0 = TOP_WIN_CX - INV_SPIN_SZ / 2;
        int ry0 = TOP_WIN_CY - INV_SPIN_SZ / 2 - 2;
        int rw = INV_SPIN_SZ;
        int rh = INV_SPIN_SZ + 4;
        dirty_rect(rx0, ry0, rx0 + rw, ry0 + rh);
        for (int sy = ry0; sy < ry0 + rh; sy++) {
            const uint16_t *rrow = &s_stone_tex_64[((sy + 23) & 63) * 64];
            for (int sx = rx0; sx < rx0 + rw; sx++) {
                uint16_t c = (uint16_t)(((rrow[(sx + 17) & 63] & 0x7BDEu) >> 1) | BIT(15));
                if (tint) c = (uint16_t)((c + tint) | BIT(15));
                buf[sy * SCREEN_W + sx] = c;
            }
        }
    }

    if (sel_it) {
        if (s_rot_valid) {
            draw_sprite_56(buf, s_rot_buf, TOP_WIN_CX, TOP_WIN_CY + bob_y);
        } else {
            draw_item_glyph(buf, sel_it, TOP_WIN_CX, TOP_WIN_CY + bob_y, 12, 0);
        }
    }
}

// Línea de ayuda de la cabecera (junto al nombre de la escuela): lo que hacen los botones ahora mismo.
static void draw_hint(uint16_t *buf, const ArpgInvItem *view) {
    const char *h;
    if (s_drag_active) h = (s_drag_sock >= 0) ? "Suéltalo en la bolsa" : "Suelta en engarce o Fundir";
    else if (s_inv_focus == INV_FOCUS_SOCK)
        h = view ? "A/X Desengarzar · Der. bolsa" : "Der. bolsa · L/R Pestaña";
    else if (view && view->kind == ARPG_ITEM_TOME)
        h = school_defined(view->school) ? "A Equipar · Y Fundir" : "Y Fundir";
    else if (view)
        h = "A Engarzar · Y Fundir";
    else if (tome_equipped(s_inv_tab))
        h = "Tomo puesto · X lo guarda";
    else
        h = "L/R Pestaña · B Salir";
    stone_rect(buf, 56, 33, 140, 12);
    text_fit(buf, 56, 35, 140, h, tome_equipped(s_inv_tab) && !view ? INV_GOLD : INV_DIM);
}

void inventory_render_top(uint16_t *buf) {
    if (!buf) return;
    if (!s_top_bg_saved) {
        darken_screen(buf);
        s_top_bg_saved = 1;
        s_top_slab_drawn = 0;
    }

    const ArpgInvItem *sel_it = view_item();
    int from_sock = (s_inv_focus == INV_FOCUS_SOCK);        // se muestra el objeto engarzado, sin vista previa ni Cera
    int show_sel = sel_it && (school_defined(s_inv_tab) || (int)sel_it->school == s_inv_tab);
    int in_cmp = (s_drag_active && s_drag_bag >= 0 && s_hover_socket >= 0 && school_defined(s_inv_tab));

    // Ruta rápida VBlank: si el texto no cambió, actualizar solo el giro si aplica
    // y evitar repintar la losa/comparativa cada 3 frames (evita desbordar VBlank).
    if (s_top_slab_drawn && !s_top_dirty) {
        if (s_top_rot_dirty && !in_cmp && show_sel) {
            render_spin_window_item(buf, sel_it, 0);
        }
        s_top_rot_dirty = 0;
        return;
    }

    char line[48];
    if (!s_top_slab_drawn) {
        // Losa de piedra superior + marco + cabecera: solo al abrir o cambiar de pestaña.
        stone_rect(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8);
        gold_frame(buf, 4, 4, SCREEN_W - 8, SCREEN_H - 8);

        sunken_box(buf, 14, 12, 34, 34, INV_GOLD);
        diamond(buf, 31, 29, 10, s_school_col[s_inv_tab]);
        static const char *const s_hdr_names[ARPG_INV_SCHOOLS] = {
            "R A Y O", "E J E C U C I Ó N", "G L I F O", "L E V A N T A R", "P E C H O"
        };
        text_at(buf, 56, 22, s_hdr_names[s_inv_tab], INV_GOLD);

        snprintf(line, sizeof(line), "Nv.%d", (int)g_arpg.level);
        sunken_box(buf, 198, 19, 44, 16, 0);
        text_center(buf, 220, 20, line, INV_TXT);

        iron_bar_h(buf, 10, 50, SCREEN_W - 20);
        s_top_slab_drawn = 1;
    } else if (in_cmp) {
        // Las dos tarjetas cubren x=8..123 y x=132..247 (y=56..181): pintar solo el margen
        // superior (2 px) y la calle central (8 px) ahorra 28.728 escrituras en VBlank.
        stone_rect(buf, 10, 54, SCREEN_W - 20, 2);
        stone_rect(buf, 124, TOP_CARD_Y, 8, TOP_CARD_H);
    } else {
        // Solo refrescar la zona inferior de tarjetas (cabe holgado en VBlank).
        stone_rect(buf, 10, 54, SCREEN_W - 20, SCREEN_H - 64);
    }

    draw_hint(buf, sel_it);

    if (in_cmp) {
        render_top_comparison(buf, s_drag_bag, s_hover_socket);
        s_top_dirty = 0;
        s_top_rot_dirty = 0;
        return;
    }

    if (!show_sel) {
        if (!school_defined(s_inv_tab)) {
            text_center(buf, SCREEN_W / 2, 106, "Letanía sellada", INV_DIM);
        } else if (from_sock) {
            text_center(buf, SCREEN_W / 2, 106, "Engarce vacío", INV_DIM);
        }
        s_top_dirty = 0;
        s_top_rot_dirty = 0;
        return;
    }

    // Ventana izquierda: objeto flotando en grande (56x56) y girando + valor de Cera.
    render_spin_window_item(buf, sel_it, 1);
    if (!from_sock) {      // la Cera es lo que da fundir un objeto de la bolsa
        sunken_box(buf, TOP_WIN_X + (TOP_WIN_W - 44) / 2, TOP_WIN_Y + TOP_WIN_H - 21, 44, 16, 0);
        draw_wax_coin(buf, TOP_WIN_X + (TOP_WIN_W - 44) / 2 + 4, TOP_WIN_Y + TOP_WIN_H - 18);
        snprintf(line, sizeof(line), "%d", arpg_inv_wax_value(sel_it->rarity));
        text_right(buf, TOP_WIN_X + (TOP_WIN_W - 44) / 2 + 40, TOP_WIN_Y + TOP_WIN_H - 20, line, INV_GOLD);
    }

    // Barra vertical de hierro forjado dividiendo la ventana del texto.
    iron_bar_v(buf, 96, 54, 129);

    // Panel derecho: nombre, rareza/escuela/nivel, descripción del aura/mecánica y stats.
    char name[40];
    item_display_name(sel_it, name, sizeof(name));
    text_fit(buf, TOP_RX, 56, TOP_RW, name, s_rar_bdr[sel_it->rarity]);
    int ilvl = sel_it->level ? (int)sel_it->level : 1;
    if (!from_sock && !arpg_inv_can_equip(sel_it)) {
        text_at(buf, TOP_RX, 67, arpg_inv_rarity_name(sel_it->rarity), INV_DIM);
        snprintf(line, sizeof(line), "Req. Nv.%d", ilvl);
        text_right(buf, TOP_RX + TOP_RW, 67, line, INV_RED);
    } else {
        snprintf(line, sizeof(line), "%s · %s · Nv.%d",
                 arpg_inv_rarity_name(sel_it->rarity), arpg_inv_school_name(sel_it->school), ilvl);
        if (bestiary_font_measure_utf8(line) > TOP_RW) {
            snprintf(line, sizeof(line), "%s·%s·Nv.%d",
                     arpg_inv_rarity_name(sel_it->rarity), arpg_inv_school_name(sel_it->school), ilvl);
        }
        if (bestiary_font_measure_utf8(line) > TOP_RW) {
            snprintf(line, sizeof(line), "%s · Nv.%d", arpg_inv_rarity_name(sel_it->rarity), ilvl);
        }
        text_at(buf, TOP_RX, 67, line, INV_DIM);
    }
    hline(buf, TOP_RX, 79, TOP_RW, INV_EDGE);

    int ycur = 82;
    if (sel_it->kind == ARPG_ITEM_TOME) {
        text_at(buf, TOP_RX, ycur, "Plegaria grabada", INV_GOLD);
        ycur += 11;
        ycur += text_wrapped(buf, TOP_RX, ycur, TOP_RW, 10,
                             "Engárzala para invocarla con el lápiz.", INV_TXT);
        ycur += 2;
        hline(buf, TOP_RX, ycur, TOP_RW, INV_EDGE);
        ycur += 3;
    } else if (sel_it->mech != ARPG_MECH_NONE) {
        text_fit(buf, TOP_RX, ycur, TOP_RW, arpg_inv_mechanic_name(sel_it->mech), INV_GOLD);
        ycur += 11;
        char desc[96];
        arpg_inv_mechanic_format(sel_it, desc, sizeof(desc));
        if (desc[0]) {
            ycur += text_wrapped(buf, TOP_RX, ycur, TOP_RW, 10, desc, INV_TXT);
        }
        ycur += 2;
        hline(buf, TOP_RX, ycur, TOP_RW, INV_EDGE);
        ycur += 3;
    }

    for (int i = 0; i < sel_it->nlines && i < 2 && ycur <= 167; i++) {
        char val[20];
        arpg_inv_line_format(sel_it->line_kind[i], (int)sel_it->line_val[i], val, sizeof(val));
        d2_stat_box(buf, TOP_RX, ycur, TOP_RW,
                    arpg_inv_line_name(sel_it->line_kind[i]), val, INV_TXT);
        ycur += 15;
    }

    if (!from_sock && sel_it->kind == ARPG_ITEM_RELIC && school_defined(sel_it->school) && ycur <= 167) {
        ArpgInvPreview pv;
        // Vista previa en el engarce al que iría con A (el mismo que elige act_equip).
        if (arpg_inv_preview_socket(s_inv_sel, sel_it->school, equip_target(sel_it), &pv)) {
            int shown = 0;
            for (int k = 0; k < ARPG_LINE_COUNT && shown < 2 && ycur <= 167; k++) {
                int d = pv.after[k] - pv.before[k];
                if (d == 0) continue;
                uint16_t col = d > 0 ? INV_GREEN : INV_RED;
                if (d > 0) tri_up(buf, TOP_RX, ycur + 4, col);
                else tri_down(buf, TOP_RX, ycur + 4, col);
                arpg_inv_line_format_delta(k, pv.before[k], pv.after[k], line, sizeof(line));
                d2_stat_box(buf, TOP_RX + 11, ycur, TOP_RW - 11, arpg_inv_line_name(k), line, col);
                ycur += 15;
                shown++;
            }
        }
    }
    s_top_dirty = 0;
    s_top_rot_dirty = 0;
}

void inventory_render(uint16_t *buf) {
    if (!buf) return;
    darken_screen(buf);
    render_tabs(buf);
    render_bottom_slab(buf);
    render_left_sockets(buf);
    render_right_bag(buf);
    render_drag_ghost(buf);
    if (s_msg_t > 0 && s_msg) text_center(buf, 119, 168, s_msg, INV_RED);
    if (s_tip_card) {
        const int cx = 20, cy = 40, cw = 216, ch = 112;
        fill_rect(buf, cx, cy, cw, ch, INV_BLACK);
        gold_frame(buf, cx, cy, cw, ch);
        text_center(buf, SCREEN_W / 2, cy + 7, "Reliquias", INV_GOLD);
        text_wrapped(buf, cx + 10, cy + 24, cw - 20, 11,
                     "Las reliquias se engarzan en un hechizo (Rayo, Ejecución, Glifo) o en el Pecho y lo mejoran. "
                     "Cada una pide un nivel. Lo que no uses se funde y da cera.", INV_TXT);
        text_center(buf, SCREEN_W / 2, cy + ch - 15, "A, B o toca: cerrar", INV_DIM);
    }
}
