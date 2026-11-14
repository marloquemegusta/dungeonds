#include "menu.h"
#include "game.h"
#include <stddef.h>
#include <string.h>

/* Palette matching FX_SH_* in source/weapons.c */
#define MENU_COL_ACT_FILL   (RGB15(8, 2, 2) | BIT(15))
#define MENU_COL_ACT_BDR    (RGB15(27, 20, 11) | BIT(15))
#define MENU_COL_ACT_TXT    (RGB15(29, 25, 19) | BIT(15))

#define MENU_COL_INA_FILL   (RGB15(2, 1, 2) | BIT(15))
#define MENU_COL_INA_BDR    (RGB15(10, 9, 8) | BIT(15))
#define MENU_COL_INA_TXT    (RGB15(15, 13, 12) | BIT(15))

#define MENU_COL_HEADER     MENU_COL_ACT_BDR
#define MENU_COL_BODY       MENU_COL_ACT_TXT

#define FONT_W              5
#define FONT_H              7
#define FONT_STEP           6

#define BTN_W               140
#define BTN_H               21
#define BTN_X0              ((SCREEN_W - BTN_W) / 2)
#define BTN_PITCH           29

typedef struct {
    int x0;
    int y0;
    int w;
    int h;
    const char *label;
} MenuButton;

static MenuState s_state = MENU_NONE;
static MenuState s_parent = MENU_TITLE;
static int s_sel = 0;

/* Self-contained 5x7 bitmap font: A-Z, 0-9, space, '-', ':', '/', '.' */
static const uint8_t s_font_az[26][FONT_H] = {
    {0x0E,0x11,0x11,0x1F,0x11,0x11,0x11}, /* A */
    {0x1E,0x11,0x11,0x1E,0x11,0x11,0x1E}, /* B */
    {0x0E,0x11,0x10,0x10,0x10,0x11,0x0E}, /* C */
    {0x1E,0x11,0x11,0x11,0x11,0x11,0x1E}, /* D */
    {0x1F,0x10,0x10,0x1E,0x10,0x10,0x1F}, /* E */
    {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10}, /* F */
    {0x0E,0x11,0x10,0x17,0x11,0x11,0x0F}, /* G */
    {0x11,0x11,0x11,0x1F,0x11,0x11,0x11}, /* H */
    {0x1F,0x04,0x04,0x04,0x04,0x04,0x1F}, /* I */
    {0x07,0x02,0x02,0x02,0x02,0x12,0x0C}, /* J */
    {0x11,0x12,0x14,0x18,0x14,0x12,0x11}, /* K */
    {0x10,0x10,0x10,0x10,0x10,0x10,0x1F}, /* L */
    {0x11,0x1B,0x15,0x11,0x11,0x11,0x11}, /* M */
    {0x11,0x19,0x15,0x13,0x11,0x11,0x11}, /* N */
    {0x0E,0x11,0x11,0x11,0x11,0x11,0x0E}, /* O */
    {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10}, /* P */
    {0x0E,0x11,0x11,0x11,0x15,0x12,0x0D}, /* Q */
    {0x1E,0x11,0x11,0x1E,0x14,0x12,0x11}, /* R */
    {0x0F,0x10,0x10,0x0E,0x01,0x01,0x1E}, /* S */
    {0x1F,0x04,0x04,0x04,0x04,0x04,0x04}, /* T */
    {0x11,0x11,0x11,0x11,0x11,0x11,0x0E}, /* U */
    {0x11,0x11,0x11,0x11,0x11,0x0A,0x04}, /* V */
    {0x11,0x11,0x11,0x15,0x15,0x1B,0x11}, /* W */
    {0x11,0x11,0x0A,0x04,0x0A,0x11,0x11}, /* X */
    {0x11,0x11,0x0A,0x04,0x04,0x04,0x04}, /* Y */
    {0x1F,0x01,0x02,0x04,0x08,0x10,0x1F}, /* Z */
};

static const uint8_t s_font_09[10][FONT_H] = {
    {0x0E,0x11,0x13,0x15,0x19,0x11,0x0E}, /* 0 */
    {0x04,0x0C,0x04,0x04,0x04,0x04,0x0E}, /* 1 */
    {0x0E,0x11,0x01,0x02,0x04,0x08,0x1F}, /* 2 */
    {0x1E,0x01,0x01,0x0E,0x01,0x01,0x1E}, /* 3 */
    {0x02,0x06,0x0A,0x12,0x1F,0x02,0x02}, /* 4 */
    {0x1F,0x10,0x10,0x1E,0x01,0x01,0x1E}, /* 5 */
    {0x0E,0x10,0x10,0x1E,0x11,0x11,0x0E}, /* 6 */
    {0x1F,0x01,0x02,0x04,0x08,0x08,0x08}, /* 7 */
    {0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E}, /* 8 */
    {0x0E,0x11,0x11,0x0F,0x01,0x01,0x0E}, /* 9 */
};

static const uint8_t s_font_space[FONT_H] = {0x00,0x00,0x00,0x00,0x00,0x00,0x00};
static const uint8_t s_font_dash[FONT_H]  = {0x00,0x00,0x00,0x1F,0x00,0x00,0x00};
static const uint8_t s_font_colon[FONT_H] = {0x00,0x04,0x04,0x00,0x04,0x04,0x00};
static const uint8_t s_font_slash[FONT_H] = {0x01,0x01,0x02,0x04,0x08,0x10,0x10};
static const uint8_t s_font_dot[FONT_H]   = {0x00,0x00,0x00,0x00,0x00,0x0C,0x0C};

static const uint8_t *font_glyph(char c) {
    if (c >= 'A' && c <= 'Z') return s_font_az[c - 'A'];
    if (c >= '0' && c <= '9') return s_font_09[c - '0'];
    if (c == '-') return s_font_dash;
    if (c == ':') return s_font_colon;
    if (c == '/') return s_font_slash;
    if (c == '.') return s_font_dot;
    return s_font_space;
}

static int get_buttons(MenuState state, const MenuButton **out_btns) {
    static const MenuButton title_btns[] = {
        { BTN_X0, 56 + 0 * BTN_PITCH, BTN_W, BTN_H, "NUEVA PARTIDA" },
        { BTN_X0, 56 + 1 * BTN_PITCH, BTN_W, BTN_H, "BESTIARIO"     },
        { BTN_X0, 56 + 2 * BTN_PITCH, BTN_W, BTN_H, "CONTROLES"     },
    };
    static const MenuButton pause_btns[] = {
        { BTN_X0, 42 + 0 * BTN_PITCH, BTN_W, BTN_H, "CONTINUAR" },
        { BTN_X0, 42 + 1 * BTN_PITCH, BTN_W, BTN_H, "REINICIAR" },
        { BTN_X0, 42 + 2 * BTN_PITCH, BTN_W, BTN_H, "BESTIARIO" },
        { BTN_X0, 42 + 3 * BTN_PITCH, BTN_W, BTN_H, "CONTROLES" },
    };
    static const MenuButton bestiary_btns[] = {
        { BTN_X0, 128, BTN_W, BTN_H, "VOLVER" },
    };
    static const MenuButton controls_btns[] = {
        { BTN_X0, 140, BTN_W, BTN_H, "VOLVER" },
    };

    switch (state) {
    case MENU_TITLE:    *out_btns = title_btns;    return 3;
    case MENU_PAUSE:    *out_btns = pause_btns;    return 4;
    case MENU_BESTIARY: *out_btns = bestiary_btns; return 1;
    case MENU_CONTROLS: *out_btns = controls_btns; return 1;
    default:            *out_btns = NULL;          return 0;
    }
}

static MenuAction activate_button(int idx) {
    switch (s_state) {
    case MENU_TITLE:
        if (idx == 0) {
            s_state = MENU_NONE;
            return MENU_ACT_START_NEW;
        }
        if (idx == 1) {
            s_parent = MENU_TITLE;
            s_state = MENU_BESTIARY;
            s_sel = 0;
        } else if (idx == 2) {
            s_parent = MENU_TITLE;
            s_state = MENU_CONTROLS;
            s_sel = 0;
        }
        return MENU_ACT_NONE;

    case MENU_PAUSE:
        if (idx == 0) {
            s_state = MENU_NONE;
            return MENU_ACT_RESUME;
        }
        if (idx == 1) {
            s_state = MENU_NONE;
            return MENU_ACT_START_NEW;
        }
        if (idx == 2) {
            s_parent = MENU_PAUSE;
            s_state = MENU_BESTIARY;
            s_sel = 0;
        } else if (idx == 3) {
            s_parent = MENU_PAUSE;
            s_state = MENU_CONTROLS;
            s_sel = 0;
        }
        return MENU_ACT_NONE;

    case MENU_BESTIARY:
    case MENU_CONTROLS:
        s_state = s_parent;
        s_sel = 0;
        return MENU_ACT_NONE;

    default:
        return MENU_ACT_NONE;
    }
}

static void draw_box(uint16_t *buf, int x0, int y0, int w, int h,
                     uint16_t fill_col, uint16_t bdr_col) {
    int x1 = x0 + w;
    int y1 = y0 + h;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > SCREEN_W) x1 = SCREEN_W;
    if (y1 > SCREEN_H) y1 = SCREEN_H;
    if (x0 >= x1 || y0 >= y1) return;

    dirty_rect(x0, y0, x1, y1);

    for (int y = y0; y < y1; y++) {
        uint16_t *row = &buf[y * SCREEN_W];
        int y_edge = (y == y0 || y == y1 - 1);
        for (int x = x0; x < x1; x++) {
            if (y_edge || x == x0 || x == x1 - 1) {
                row[x] = bdr_col;
            } else {
                uint16_t px = row[x];
                if (px & BIT(15)) {
                    row[x] = (uint16_t)(((px & 0x739Cu) >> 2) | BIT(15));
                } else if ((x ^ y) & 1) {
                    row[x] = fill_col;
                }
            }
        }
    }
}

static void draw_text(uint16_t *buf, int x0, int y0, const char *str, uint16_t col) {
    int len = (int)strlen(str);
    if (len <= 0) return;
    int text_w = len * FONT_STEP - 1;
    dirty_rect(x0, y0, x0 + text_w, y0 + FONT_H);

    for (int i = 0; i < len; i++) {
        const uint8_t *rows = font_glyph(str[i]);
        int gx = x0 + i * FONT_STEP;
        for (int ry = 0; ry < FONT_H; ry++) {
            int py = y0 + ry;
            if ((unsigned)py >= SCREEN_H) continue;
            uint8_t bits = rows[ry];
            for (int rx = 0; rx < FONT_W; rx++) {
                if (bits & (1u << (FONT_W - 1 - rx))) {
                    int px = gx + rx;
                    if ((unsigned)px < SCREEN_W) {
                        buf[py * SCREEN_W + px] = col;
                    }
                }
            }
        }
    }
}

static void draw_text_centered(uint16_t *buf, int cx, int y0, const char *str, uint16_t col) {
    int len = (int)strlen(str);
    if (len <= 0) return;
    int text_w = len * FONT_STEP - 1;
    draw_text(buf, cx - text_w / 2, y0, str, col);
}

void menu_open_title(void) {
    s_state = MENU_TITLE;
    s_parent = MENU_TITLE;
    s_sel = 0;
}

void menu_open_pause(void) {
    s_state = MENU_PAUSE;
    s_parent = MENU_PAUSE;
    s_sel = 0;
}

void menu_close(void) {
    s_state = MENU_NONE;
    s_sel = 0;
}

int menu_is_open(void) {
    return s_state != MENU_NONE;
}

MenuState menu_state(void) {
    return s_state;
}

MenuAction menu_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (s_state == MENU_NONE) return MENU_ACT_NONE;

    const MenuButton *btns = NULL;
    int count = get_buttons(s_state, &btns);
    if (count <= 0) return MENU_ACT_NONE;

    if (touch_pressed) {
        for (int i = 0; i < count; i++) {
            if (touch_x >= btns[i].x0 && touch_x < btns[i].x0 + btns[i].w &&
                touch_y >= btns[i].y0 && touch_y < btns[i].y0 + btns[i].h) {
                s_sel = i;
                return activate_button(i);
            }
        }
    }

    if (keys_down & KEY_UP) {
        s_sel = (s_sel + count - 1) % count;
    } else if (keys_down & KEY_DOWN) {
        s_sel = (s_sel + 1) % count;
    }

    if (keys_down & KEY_A) {
        return activate_button(s_sel);
    }

    if (keys_down & KEY_B) {
        if (s_state == MENU_BESTIARY || s_state == MENU_CONTROLS) {
            s_state = s_parent;
            s_sel = 0;
            return MENU_ACT_NONE;
        }
        if (s_state == MENU_PAUSE) {
            s_state = MENU_NONE;
            return MENU_ACT_RESUME;
        }
    }

    if (keys_down & KEY_START) {
        if (s_state == MENU_PAUSE) {
            s_state = MENU_NONE;
            return MENU_ACT_RESUME;
        }
        if (s_state == MENU_TITLE) {
            return activate_button(0);
        }
    }

    return MENU_ACT_NONE;
}

void menu_render_bottom(uint16_t *buf) {
    if (s_state == MENU_NONE || !buf) return;

    if (s_state == MENU_BESTIARY) {
        draw_box(buf, 38, 36, 180, 72, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 48, "BESTIARIO", MENU_COL_HEADER);
        draw_text_centered(buf, SCREEN_W / 2, 76, "PROXIMAMENTE", MENU_COL_BODY);
    } else if (s_state == MENU_CONTROLS) {
        static const char *const lines[4] = {
            "CRUCETA - MOVERSE",
            "LAPIZ - APUNTAR Y CARGAR",
            "START - PAUSA",
            "SELECT/Y - EFECTOS DEMO"
        };
        draw_box(buf, 34, 24, 188, 100, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 34, "CONTROLES", MENU_COL_HEADER);
        for (int i = 0; i < 4; i++) {
            draw_text(buf, 46, 54 + i * 14, lines[i], MENU_COL_BODY);
        }
    }

    const MenuButton *btns = NULL;
    int count = get_buttons(s_state, &btns);
    for (int i = 0; i < count; i++) {
        int active = (i == s_sel);
        uint16_t fill = active ? MENU_COL_ACT_FILL : MENU_COL_INA_FILL;
        uint16_t bdr  = active ? MENU_COL_ACT_BDR  : MENU_COL_INA_BDR;
        uint16_t txt  = active ? MENU_COL_ACT_TXT  : MENU_COL_INA_TXT;
        draw_box(buf, btns[i].x0, btns[i].y0, btns[i].w, btns[i].h, fill, bdr);
        draw_text_centered(buf, btns[i].x0 + btns[i].w / 2,
                           btns[i].y0 + (btns[i].h - FONT_H) / 2,
                           btns[i].label, txt);
    }
}
