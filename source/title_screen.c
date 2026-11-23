#include "title_screen.h"
#include "bestiary_font.h"
#include <nds.h>
#include <string.h>

/* Entero puro, sin float ni divisiones en bucles de píxel. Todos los píxeles llevan BIT(15) (opacos). */
#define SW 256
#define SH 192
#define OP BIT(15)

#define TITLE_TEXT "EXVOTION"          /* nombre provisional (DESIGN-ARPG.md §8) */
#define CX 128
#define GLOW_Y 112
#define WICK_Y 118
#define BODY_Y0 126
#define BODY_Y1 168

#define COL_BG   (RGB15(1, 1, 2) | OP)
#define COL_NAME (RGB15(27, 25, 20) | OP)
#define COL_NAME_SH (RGB15(5, 4, 4) | OP)
#define COL_RULE (RGB15(14, 11, 6) | OP)

static uint16_t s_scratch[SW * 16];

static uint16_t bg_pixel(int x, int y) {
    int dx = x - CX, dy = y - GLOW_Y;
    int d2 = dx * dx + dy * dy;
    if (d2 >= 4096) return COL_BG;
    int k = ((4096 - d2) * 8) >> 12;          /* 0..7 */
    int k2 = (k * k) >> 2;                    /* falloff, 0..12 */
    return (uint16_t)(RGB15(1 + k2, 1 + (k2 * 3 >> 2), 2 + (k2 >> 2)) | OP);
}

static void put(uint16_t *buf, int x, int y, uint16_t c) {
    if ((unsigned)x < SW && (unsigned)y < SH) buf[y * SW + x] = c;
}

static void rect(uint16_t *buf, int x0, int y0, int x1, int y1, uint16_t c) {
    for (int y = y0; y < y1; y++)
        for (int x = x0; x < x1; x++) put(buf, x, y, c);
}

static void draw_name(uint16_t *buf, int top) {
    const int gap = 3;
    int n = (int)strlen(TITLE_TEXT), total = 0;
    for (int i = 0; i < n; i++) {
        char s[2] = { TITLE_TEXT[i], 0 };
        total += bestiary_font_measure_utf8(s) + gap;
    }
    total -= gap;
    memset(s_scratch, 0, sizeof(s_scratch));
    int pen = 0;
    for (int i = 0; i < n; i++) {
        char s[2] = { TITLE_TEXT[i], 0 };
        bestiary_font_draw_utf8(s_scratch, pen, 0, s, OP | 1);
        pen += bestiary_font_measure_utf8(s) + gap;
    }
    int x0 = CX - total;                      /* ancho a doble tamaño: 2*total, centrado */
    for (int y = 0; y < 16; y++)
        for (int x = 0; x < total; x++) {
            if (!s_scratch[y * SW + x]) continue;
            int px = x0 + x * 2, py = top + y * 2;
            rect(buf, px + 2, py + 2, px + 4, py + 4, COL_NAME_SH);
        }
    for (int y = 0; y < 16; y++)
        for (int x = 0; x < total; x++) {
            if (!s_scratch[y * SW + x]) continue;
            int px = x0 + x * 2, py = top + y * 2;
            rect(buf, px, py, px + 2, py + 2, COL_NAME);
        }
    /* filete con rombo central */
    int ry = top + 38;
    rect(buf, CX - 56, ry, CX - 6, ry + 1, COL_RULE);
    rect(buf, CX + 6, ry, CX + 56, ry + 1, COL_RULE);
    put(buf, CX, ry - 2, COL_RULE);
    rect(buf, CX - 1, ry - 1, CX + 2, ry, COL_RULE);
    rect(buf, CX - 2, ry, CX + 3, ry + 1, COL_RULE);
    rect(buf, CX - 1, ry + 1, CX + 2, ry + 2, COL_RULE);
    put(buf, CX, ry + 2, COL_RULE);
}

static void draw_candle(uint16_t *buf) {
    const uint16_t wax_l = RGB15(28, 26, 22) | OP, wax = RGB15(24, 22, 18) | OP;
    const uint16_t wax_d = RGB15(16, 14, 11) | OP, rim = RGB15(29, 27, 23) | OP;
    /* cuerpo */
    for (int y = BODY_Y0; y < BODY_Y1; y++) {
        rect(buf, CX - 7, y, CX + 7, y + 1, wax);
        rect(buf, CX - 7, y, CX - 4, y + 1, wax_l);
        rect(buf, CX + 3, y, CX + 7, y + 1, wax_d);
    }
    rect(buf, CX - 7, BODY_Y0 - 1, CX + 7, BODY_Y0 + 1, rim);       /* labio de cera fundida */
    rect(buf, CX - 8, BODY_Y0, CX - 7, BODY_Y0 + 3, wax_l);
    /* chorretones */
    rect(buf, CX - 6, BODY_Y0 + 1, CX - 4, BODY_Y0 + 14, rim);
    rect(buf, CX + 2, BODY_Y0 + 1, CX + 4, BODY_Y0 + 8, wax_l);
    rect(buf, CX + 5, BODY_Y0 + 1, CX + 7, BODY_Y0 + 20, wax_l);
    /* mecha */
    rect(buf, CX - 1, WICK_Y, CX + 1, BODY_Y0, RGB15(4, 3, 3) | OP);
    /* plato */
    rect(buf, CX - 18, BODY_Y1, CX + 18, BODY_Y1 + 4, RGB15(9, 8, 8) | OP);
    rect(buf, CX - 18, BODY_Y1, CX + 18, BODY_Y1 + 1, RGB15(15, 13, 11) | OP);
    rect(buf, CX - 12, BODY_Y1 + 4, CX + 12, BODY_Y1 + 6, RGB15(5, 4, 4) | OP);
}

static uint32_t hash(uint32_t x) {
    x ^= x >> 16; x *= 0x85ebca6bu; x ^= x >> 13; x *= 0xc2b2ae35u;
    return x ^ (x >> 16);
}

#define FL_X0 (CX - 12)
#define FL_X1 (CX + 13)
#define FL_Y0 (WICK_Y - 20)
#define FL_Y1 (WICK_Y + 1)

static void draw_flame(uint16_t *buf, uint32_t step) {
    for (int y = FL_Y0; y < FL_Y1; y++)
        for (int x = FL_X0; x < FL_X1; x++) put(buf, x, y, bg_pixel(x, y));
    uint32_t h = hash(step);
    int sway = (int)(h & 3) - 1;               /* -1..2 → se queda en -1..1 */
    if (sway > 1) sway = 1;
    int hgt = 11 + (int)((h >> 3) % 3);
    static const int8_t halfw[14] = { 1, 2, 2, 3, 3, 3, 2, 2, 2, 1, 1, 1, 0, 0 };
    const uint16_t outer = RGB15(22, 13, 6) | OP, mid = RGB15(28, 21, 10) | OP, core = RGB15(30, 28, 20) | OP;
    for (int i = 0; i < hgt; i++) {
        int y = WICK_Y - 1 - i;
        int cx = CX + ((sway * i) >> 2);
        int w = halfw[i];
        rect(buf, cx - w, y, cx + w + 1, y + 1, outer);
        if (w >= 1 && i < hgt - 2) rect(buf, cx - (w - 1), y, cx + w, y + 1, mid);
        if (i >= 1 && i <= 5) rect(buf, cx - (w > 2 ? 1 : 0), y, cx + 1 + (w > 2 ? 0 : 0), y + 1, core);
    }
}

void title_top_render(uint16_t *buf, uint32_t frame, int full) {
    if (!buf) return;
    if (full) {
        for (int y = 0; y < SH; y++)
            for (int x = 0; x < SW; x++) buf[y * SW + x] = bg_pixel(x, y);
        draw_name(buf, 34);
        draw_candle(buf);
        draw_flame(buf, frame >> 2);
        return;
    }
    if ((frame & 3) == 0) draw_flame(buf, frame >> 2);
}
