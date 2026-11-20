#include "menu.h"
#include "game.h"
#include "upgrades.h"
#include "bestiary_font.h"
#include "levelup_cards.h"
#include "hud_icons_gfx.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "arpg_tree.h"
#include <stddef.h>
#include <stdio.h>
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
static int s_pick = 0;
static int s_title_has_save = 0;        /* read once when the title opens (the card is slow to ask) */
static char s_camp_msg[48] = "";

/* Skill tree screen (DESIGN.md 7.3). Node ids: 0 Maldicion (top), 1..12 in branch columns of 3 (ids 1+3*col+row). */
#define TREE_COLS       4               /* Metralleta, Quemadura (left half: rayo), Veneno, Resurreccion (right half) */
#define TREE_NODE_W     56
#define TREE_NODE_H     28              /* two lines of the 13 px font */
#define TREE_ROW_Y0     60
#define TREE_ROW_PITCH  32
#define TREE_ROOT_X     84
#define TREE_ROOT_Y     20
#define TREE_ROOT_W     88
#define TREE_ROOT_H     18
#define TREE_BRANCH_Y   44
#define TREE_STRIP_Y    158
#define TREE_STRIP_H    32
static const int s_tree_col_x[TREE_COLS] = { 8, 68, 132, 192 };
static int s_tree_sel = 1;              /* selected node id */
static int s_tree_col = 0;              /* column of the last branch node visited: DOWN from node 0 lands there */

/* Camp buttons (four): smaller and closer together so all of them fit above y=192. */
#define CAMP_BTN_Y0     102
#define CAMP_BTN_PITCH  22
#define CAMP_BTN_H      18

/* Level-up screen (DESIGN.md 6.12.8): header, 3 cards side by side (76x76 animated art + name), effect strip. */
#define LV_CARD_W     80
#define LV_CARD_H     108
#define LV_CARD_GAP   5
#define LV_CARD_X0    ((SCREEN_W - 3 * LV_CARD_W - 2 * LV_CARD_GAP) / 2)
#define LV_CARD_Y0    22
#define LV_LIFT       4
#define LV_ART        76
#define LV_NAME_Y     80
#define LV_STRIP_X    6
#define LV_STRIP_Y    138
#define LV_STRIP_W    244
#define LV_STRIP_H    50
#define LV_ICON       16

static int s_lv_anim = 0;

static int get_buttons(MenuState state, const MenuButton **out_btns) {
    /* Title and camp buttons are filled at run time: the title drops "Continuar" when there is no save. */
    static MenuButton title_btns[4];
    static const char *const title_labels[4] = { "Continuar", "Nueva partida", "Códice", "Controles" };
    static const MenuButton pause_btns[] = {
        { BTN_X0, 42 + 0 * BTN_PITCH, BTN_W, BTN_H, "Continuar" },
#if ENCOUNTERS_PROTO
        { BTN_X0, 42 + 1 * BTN_PITCH, BTN_W, BTN_H, "Volver al campamento" },
#else
        { BTN_X0, 42 + 1 * BTN_PITCH, BTN_W, BTN_H, "Reiniciar" },
#endif
        { BTN_X0, 42 + 2 * BTN_PITCH, BTN_W, BTN_H, "Códice"    },
        { BTN_X0, 42 + 3 * BTN_PITCH, BTN_W, BTN_H, "Controles" },
    };
    static MenuButton camp_btns[4];
    static const MenuButton bestiary_btns[] = {
        { BTN_X0, 128, BTN_W, BTN_H, "Volver" },
    };
    static const MenuButton controls_btns[] = {
        { BTN_X0, 140, BTN_W, BTN_H, "Volver" },
    };

    switch (state) {
    case MENU_TITLE: {
        const char *const *labels = title_labels + (s_title_has_save ? 0 : 1);
        int n = s_title_has_save ? 4 : 3;
        for (int i = 0; i < n; i++)
            title_btns[i] = (MenuButton){ BTN_X0, 56 + i * BTN_PITCH, BTN_W, BTN_H, labels[i] };
        *out_btns = title_btns;
        return n;
    }
    case MENU_CAMP: {
        static const char *const camp_labels[4] = { "Dormir", "Árbol", "Entrar en la Catedral", "Códice" };
        for (int i = 0; i < 4; i++)
            camp_btns[i] = (MenuButton){ BTN_X0, CAMP_BTN_Y0 + i * CAMP_BTN_PITCH, BTN_W, CAMP_BTN_H, camp_labels[i] };
        *out_btns = camp_btns;
        return 4;
    }
    case MENU_PAUSE:    *out_btns = pause_btns;    return 4;
    case MENU_BESTIARY: *out_btns = bestiary_btns; return 1;
    case MENU_CONTROLS: *out_btns = controls_btns; return 1;
    default:            *out_btns = NULL;          return 0;
    }
}

static MenuAction activate_button(int idx) {
    switch (s_state) {
    case MENU_TITLE: {
        /* Same order as the labels in get_buttons(): the first one is missing without a save. */
        int k = idx + (s_title_has_save ? 0 : 1);
        if (k == 0) {
            s_state = MENU_NONE;
            return MENU_ACT_CONTINUE;
        }
        if (k == 1) {
            s_state = MENU_NONE;
            return MENU_ACT_START_INTRO;
        }
        if (k == 2) {
            s_parent = MENU_TITLE;
            s_state = MENU_BESTIARY;
            s_sel = 0;
        } else if (k == 3) {
            s_parent = MENU_TITLE;
            s_state = MENU_CONTROLS;
            s_sel = 0;
        }
        return MENU_ACT_NONE;
    }

    case MENU_CAMP:
        if (idx == 0) return MENU_ACT_SLEEP;          /* the camp stays open; main reports the result */
        if (idx == 1) {
            menu_open_tree();
            return MENU_ACT_NONE;
        }
        if (idx == 2) {
            s_state = MENU_NONE;
            return MENU_ACT_ENTER_DUNGEON;
        }
        if (idx == 3) {
            s_parent = MENU_CAMP;
            s_state = MENU_BESTIARY;
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
#if ENCOUNTERS_PROTO
            return MENU_ACT_TO_CAMP;
#else
            return MENU_ACT_START_NEW;
#endif
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

/* Menu text uses the bestiary font (Palatino 1-bit); buf is SCREEN_W wide (256). */
static void draw_text(uint16_t *buf, int x0, int y0, const char *str, uint16_t col) {
    if (!str || !*str) return;
    int text_w = bestiary_font_measure_utf8(str);
    dirty_rect(x0, y0, x0 + text_w + 1, y0 + bestiary_font_line_height());
    bestiary_font_draw_utf8(buf, x0, y0, str, col);
}

static void draw_text_centered(uint16_t *buf, int cx, int y0, const char *str, uint16_t col) {
    if (!str || !*str) return;
    draw_text(buf, cx - bestiary_font_measure_utf8(str) / 2, y0, str, col);
}

void menu_open_title(void) {
    s_state = MENU_TITLE;
    s_parent = MENU_TITLE;
    s_sel = 0;
    s_title_has_save = ENCOUNTERS_PROTO ? arpg_progress_has_save() : 0;
}

void menu_open_camp(void) {
    s_state = MENU_CAMP;
    s_parent = MENU_CAMP;
    s_sel = 0;
    s_camp_msg[0] = 0;
}

void menu_open_tree(void) {
    s_state = MENU_TREE;
    s_parent = MENU_CAMP;
    s_tree_sel = 1;
    s_tree_col = 0;
}

void menu_camp_message(const char *msg) {
    if (!msg) msg = "";
    strncpy(s_camp_msg, msg, sizeof(s_camp_msg) - 1);
    s_camp_msg[sizeof(s_camp_msg) - 1] = 0;
}

void menu_open_pause(void) {
    s_state = MENU_PAUSE;
    s_parent = MENU_PAUSE;
    s_sel = 0;
}

static void levelup_load_art(void) {
    for (int i = 0; i < 3; i++) lvcards_load(i, upgrades_offer_art_id(upgrades_offer(i)));
}

void menu_open_levelup(void) {
    s_state = MENU_LEVELUP;
    s_parent = MENU_NONE;
    s_sel = 0;
    s_pick = 0;
    s_lv_anim = 0;
    levelup_load_art();
}

int menu_levelup_pick(void) {
    return s_pick;
}

void menu_close(void) {
    if (s_state == MENU_LEVELUP) lvcards_free();
    s_state = MENU_NONE;
    s_sel = 0;
}

int menu_is_open(void) {
    return s_state != MENU_NONE;
}

MenuState menu_state(void) {
    return s_state;
}

/* Screen rectangle of a tree node (id 0 = the Maldicion box above the columns). */
static void tree_node_rect(int id, int *x, int *y, int *w, int *h) {
    if (id == 0) {
        *x = TREE_ROOT_X; *y = TREE_ROOT_Y; *w = TREE_ROOT_W; *h = TREE_ROOT_H;
        return;
    }
    int col = (id - 1) / 3, row = (id - 1) % 3;
    *x = s_tree_col_x[col];
    *y = TREE_ROW_Y0 + row * TREE_ROW_PITCH;
    *w = TREE_NODE_W;
    *h = TREE_NODE_H;
}

static void tree_select(int id) {
    s_tree_sel = id;
    if (id > 0) s_tree_col = (id - 1) / 3;
}

static void tree_buy_selected(void) {
    if (!arpg_tree_can_buy(s_tree_sel)) return;
    arpg_tree_buy(s_tree_sel);
    arpg_progress_save();
}

static MenuAction tree_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (touch_pressed) {
        /* Volver: top-left button of the header. */
        if (touch_x >= 6 && touch_x < 56 && touch_y >= 3 && touch_y < 17) {
            s_state = s_parent;
            s_sel = 0;
            return MENU_ACT_NONE;
        }
        for (int id = 0; id < ARPG_NODE_COUNT; id++) {
            int x, y, w, h;
            tree_node_rect(id, &x, &y, &w, &h);
            if (touch_x >= x && touch_x < x + w && touch_y >= y && touch_y < y + h) {
                if (id == s_tree_sel) tree_buy_selected();   /* tapping the selected node again buys it */
                else tree_select(id);
                return MENU_ACT_NONE;
            }
        }
    }

    int sel = s_tree_sel;
    if (keys_down & KEY_UP) {
        if (sel > 0) tree_select((sel - 1) % 3 > 0 ? sel - 1 : 0);
    }
    if (keys_down & KEY_DOWN) {
        if (sel == 0) tree_select(1 + s_tree_col * 3);
        else if ((sel - 1) % 3 < 2) tree_select(sel + 1);
    }
    if (keys_down & KEY_LEFT) {
        if (sel > 0 && (sel - 1) / 3 > 0) tree_select(sel - 3);
    }
    if (keys_down & KEY_RIGHT) {
        if (sel > 0 && (sel - 1) / 3 < TREE_COLS - 1) tree_select(sel + 3);
    }
    if (keys_down & KEY_A) tree_buy_selected();
    if (keys_down & KEY_B) {
        s_state = s_parent;
        s_sel = 0;
    }
    return MENU_ACT_NONE;
}

MenuAction menu_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (s_state == MENU_NONE) return MENU_ACT_NONE;

    if (s_state == MENU_TREE) return tree_update(keys_down, touch_pressed, touch_x, touch_y);

    if (s_state == MENU_LEVELUP) {
        /* D-pad LEFT/RIGHT + A, or tap a card (tap the selected one again to confirm). No cancel. */
        if (keys_down & KEY_SELECT) {
            upgrades_cycle_design_variant();
            levelup_load_art();
        }
        if (touch_pressed) {
            for (int i = 0; i < 3; i++) {
                int x0 = LV_CARD_X0 + i * (LV_CARD_W + LV_CARD_GAP);
                int y0 = LV_CARD_Y0 - (i == s_sel ? LV_LIFT : 0);
                if (touch_x >= x0 && touch_x < x0 + LV_CARD_W && touch_y >= y0 && touch_y < y0 + LV_CARD_H) {
                    if (i == s_sel) {
                        s_pick = i;
                        return MENU_ACT_LEVELUP_PICK;
                    }
                    s_sel = i;
                    break;
                }
            }
        }
        if (keys_down & KEY_LEFT) s_sel = (s_sel + 2) % 3;
        else if (keys_down & KEY_RIGHT) s_sel = (s_sel + 1) % 3;
        if (keys_down & KEY_A) {
            s_pick = s_sel;
            return MENU_ACT_LEVELUP_PICK;
        }
        return MENU_ACT_NONE;
    }

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

/* Darkens the whole bottom screen: opaque pixels to half brightness, transparent (hardware BG) ones dithered. */
static void dim_screen(uint16_t *buf) {
    const uint16_t dark = RGB15(2, 1, 2) | BIT(15);
    dirty_rect(0, 0, SCREEN_W, SCREEN_H);
    for (int y = 0; y < SCREEN_H; y++) {
        uint16_t *row = &buf[y * SCREEN_W];
        for (int x = 0; x < SCREEN_W; x++) {
            uint16_t px = row[x];
            if (px & BIT(15)) row[x] = (uint16_t)(((px & 0x7BDEu) >> 1) | BIT(15));
            else row[x] = dark;
        }
    }
}

/* Placeholder 16x16 icon shapes (one per shape id), all on the 2x grid around the centre. */
static int icon_in_shape(int shape, int x, int y) {
    if ((unsigned)x >= LV_ICON || (unsigned)y >= LV_ICON) return 0;
    int ax = 2 * x - 15, ay = 2 * y - 15;
    int px = ax < 0 ? -ax : ax, py = ay < 0 ? -ay : ay;
    switch (shape) {
    case 0:  return px + py <= 15;                              /* diamond */
    case 1:  return ax * ax + ay * ay <= 225;                   /* disc */
    case 2:  return px <= 11 && py <= 11;                       /* square */
    case 3:  return y >= 1 && y <= 14 && px <= y + 1;           /* triangle */
    case 4:  { int d = ax * ax + ay * ay; return d <= 225 && d >= 81; } /* ring */
    default: return px <= 5 || py <= 5;                         /* cross */
    }
}

static void draw_icon(uint16_t *buf, int x0, int y0, int shape, uint16_t col) {
    uint16_t edge = (uint16_t)(((col & 0x7BDEu) >> 1) | BIT(15));
    dirty_rect(x0, y0, x0 + LV_ICON, y0 + LV_ICON);
    for (int y = 0; y < LV_ICON; y++) {
        for (int x = 0; x < LV_ICON; x++) {
            if (!icon_in_shape(shape, x, y)) continue;
            int border = !icon_in_shape(shape, x - 1, y) || !icon_in_shape(shape, x + 1, y) ||
                         !icon_in_shape(shape, x, y - 1) || !icon_in_shape(shape, x, y + 1);
            int sx = x0 + x, sy = y0 + y;
            if ((unsigned)sx < SCREEN_W && (unsigned)sy < SCREEN_H)
                buf[sy * SCREEN_W + sx] = border ? edge : col;
        }
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

static void frame_rect(uint16_t *buf, int x0, int y0, int w, int h, uint16_t col) {
    for (int x = x0; x < x0 + w; x++) {
        if ((unsigned)x >= SCREEN_W) continue;
        if ((unsigned)y0 < SCREEN_H) buf[y0 * SCREEN_W + x] = col;
        if ((unsigned)(y0 + h - 1) < SCREEN_H) buf[(y0 + h - 1) * SCREEN_W + x] = col;
    }
    for (int y = y0; y < y0 + h; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        if ((unsigned)x0 < SCREEN_W) buf[y * SCREEN_W + x0] = col;
        if ((unsigned)(x0 + w - 1) < SCREEN_W) buf[y * SCREEN_W + x0 + w - 1] = col;
    }
}

/* Soft dithered glow around the selected card: checkerboard near the edge, sparse dots further out. */
static void draw_card_glow(uint16_t *buf, int x0, int y0, int w, int h, int pulse) {
    const uint16_t near_c = RGB15(12 + pulse * 2, 7 + pulse, 4 + pulse) | BIT(15);
    const uint16_t far_c = RGB15(7 + pulse, 4 + pulse / 2, 3) | BIT(15);
    const int R = 5;
    dirty_rect(x0 - R, y0 - R, x0 + w + R, y0 + h + R);
    for (int y = y0 - R; y < y0 + h + R; y++) {
        if ((unsigned)y >= SCREEN_H) continue;
        int dy = y < y0 ? y0 - y : (y >= y0 + h ? y - (y0 + h - 1) : 0);
        for (int x = x0 - R; x < x0 + w + R; x++) {
            if ((unsigned)x >= SCREEN_W) continue;
            int dx = x < x0 ? x0 - x : (x >= x0 + w ? x - (x0 + w - 1) : 0);
            int d = dx > dy ? dx : dy;
            if (d == 0) continue;
            if (d <= 2) { if (((x + y) & 1) == 0) buf[y * SCREEN_W + x] = near_c; }
            else if (((x & 1) == 0) && ((y & 1) == 0)) buf[y * SCREEN_W + x] = far_c;
        }
    }
}

/* Name below the art, centred; two lines (split at the best space) when it does not fit in one. */
static void draw_card_name(uint16_t *buf, int cx, int y, const char *name, uint16_t col) {
    const int max_w = LV_ART;
    int w = bestiary_font_measure_utf8(name);
    int n = (int)strlen(name);
    if (w <= max_w || n >= 40) {
        bestiary_font_draw_utf8(buf, cx - w / 2, y + 5, name, col);
        return;
    }
    char l1[40], l2[40];
    int best = -1, best_w = 9999;
    for (int i = 1; i < n; i++) {
        if (name[i] != ' ') continue;
        memcpy(l1, name, (size_t)i);
        l1[i] = 0;
        strcpy(l2, name + i + 1);
        int w1 = bestiary_font_measure_utf8(l1), w2 = bestiary_font_measure_utf8(l2);
        int m = w1 > w2 ? w1 : w2;
        if (m < best_w) { best_w = m; best = i; }
    }
    if (best < 0) {
        bestiary_font_draw_utf8(buf, cx - w / 2, y + 5, name, col);
        return;
    }
    memcpy(l1, name, (size_t)best);
    l1[best] = 0;
    strcpy(l2, name + best + 1);
    bestiary_font_draw_utf8(buf, cx - bestiary_font_measure_utf8(l1) / 2, y, l1, col);
    bestiary_font_draw_utf8(buf, cx - bestiary_font_measure_utf8(l2) / 2, y + 11, l2, col);
}

/* Heal card (no baked art): the sacred heart of the HUD at 2x on black. */
static void draw_cura_art(uint16_t *buf, int x0, int y0, int dim) {
    fill_rect(buf, x0, y0, LV_ART, LV_ART, 0x8000);
    int hx = x0 + (LV_ART - 2 * HUD_ICON_W) / 2, hy = y0 + (LV_ART - 2 * HUD_ICON_H) / 2;
    for (int gy = 0; gy < 2 * HUD_ICON_H; gy++) {
        for (int gx = 0; gx < 2 * HUD_ICON_W; gx++) {
            uint16_t c = g_hud_heart_full[(gy / 2) * HUD_ICON_W + gx / 2];
            if (!c) continue;
            if (dim) c = (uint16_t)(c - ((c >> 2) & 0x1CE7u));
            buf[(hy + gy) * SCREEN_W + hx + gx] = c;
        }
    }
}

static void render_levelup(uint16_t *buf) {
    const uint16_t gold = RGB15(27, 20, 9) | BIT(15);
    const uint16_t gold_dim = RGB15(15, 11, 6) | BIT(15);
    const uint16_t ivory = RGB15(30, 27, 20) | BIT(15);
    const uint16_t gray = RGB15(11, 10, 9) | BIT(15);
    const uint16_t black = 0x8000;
    const int relic_offer = upgrades_offer_is_relic();
    char title[40];

    dim_screen(buf);
    s_lv_anim++;
    const int frame = (s_lv_anim >> 2) & (LVC_FRAMES - 1);   /* 15 fps, 16-frame loop */
    int phase = (s_lv_anim >> 4) & 7;
    const int pulse = phase < 4 ? phase : 8 - phase;   /* 0..4, slow triangle */

    if (relic_offer) snprintf(title, sizeof(title), "Reliquia");
    else snprintf(title, sizeof(title), "Nivel %d", upgrades_offer_level());
    int tw = bestiary_font_measure_utf8(title);
    dirty_rect(0, 2, SCREEN_W, 17);
    bestiary_font_draw_utf8(buf, (SCREEN_W - tw) / 2, 3, title, relic_offer ? gold : MENU_COL_BODY);
    {
        char v[2] = { (char)('A' + g_design_variant), 0 };
        draw_text(buf, SCREEN_W - 9, 3, v, gray);   /* design variant, for the review round */
    }

    /* Selected card's glow first so the neighbours and the card itself paint over it. */
    draw_card_glow(buf, LV_CARD_X0 + s_sel * (LV_CARD_W + LV_CARD_GAP), LV_CARD_Y0 - LV_LIFT, LV_CARD_W, LV_CARD_H, pulse);

    for (int pass = 0; pass < 2; pass++) {
        for (int i = 0; i < 3; i++) {
            int active = (i == s_sel);
            if (active != pass) continue;
            const UpgradeOffer *o = upgrades_offer(i);
            int relic = (o->kind == UPG_KIND_RELIC);
            int x0 = LV_CARD_X0 + i * (LV_CARD_W + LV_CARD_GAP);
            int y0 = LV_CARD_Y0 - (active ? LV_LIFT : 0);
            uint16_t bdr = relic ? (active ? gold : gold_dim) : (active ? ivory : gray);

            fill_rect(buf, x0, y0, LV_CARD_W, LV_CARD_H, black);
            frame_rect(buf, x0, y0, LV_CARD_W, LV_CARD_H, bdr);
            if (relic && active) frame_rect(buf, x0 + 1, y0 + 1, LV_CARD_W - 2, LV_CARD_H - 2, gold_dim);

            int ax = x0 + 2, ay = y0 + 2;
            if (o->kind == UPG_KIND_CURA) draw_cura_art(buf, ax, ay, !active);
            else if (lvcards_loaded(i)) lvcards_draw(buf, i, ax, ay, frame, !active);
            else draw_icon(buf, ax + (LV_ART - LV_ICON) / 2, ay + (LV_ART - LV_ICON) / 2,
                           upgrades_offer_shape(o), upgrades_offer_color(o));

            char name[32];
            upgrades_offer_title(o, name, sizeof(name));
            draw_card_name(buf, x0 + LV_CARD_W / 2, y0 + LV_NAME_Y, name,
                           active ? ivory : (RGB15(17, 15, 12) | BIT(15)));
        }
    }

    /* Effect strip of the selected card. */
    const UpgradeOffer *sel = upgrades_offer(s_sel);
    fill_rect(buf, LV_STRIP_X, LV_STRIP_Y, LV_STRIP_W, LV_STRIP_H, black);
    frame_rect(buf, LV_STRIP_X, LV_STRIP_Y, LV_STRIP_W, LV_STRIP_H, sel->kind == UPG_KIND_RELIC ? gold_dim : gray);
    bestiary_font_draw_wrapped(buf, LV_STRIP_X + 8, LV_STRIP_Y + 6, LV_STRIP_W - 16, 12, upgrades_offer_text(sel),
                               MENU_COL_BODY);
}

/* Skill tree (DESIGN.md 7.3): header, Maldicion box, 4 branch columns (2 rayo on the left, 2 curses on the right),
   selected node frame, and a strip with the name, the description and the buy hint. */
static void tree_box(uint16_t *buf, int x0, int y0, int w, int h, uint16_t fill, uint16_t bdr) {
    fill_rect(buf, x0, y0, w, h, fill);
    frame_rect(buf, x0, y0, w, h, bdr);
}

/* Node name: one line centred when it fits, else two lines split at the best space (like draw_card_name). */
static void draw_node_name(uint16_t *buf, int x0, int y0, int w, int h, const char *name, uint16_t col) {
    const int lh = bestiary_font_line_height();
    const int cx = x0 + w / 2;
    char l1[32], l2[32];
    int n = (int)strlen(name);
    if (bestiary_font_measure_utf8(name) <= w - 4 || n >= 32) {
        draw_text_centered(buf, cx, y0 + (h - lh) / 2, name, col);
        return;
    }
    int best = -1, best_w = 9999;
    for (int i = 1; i < n; i++) {
        if (name[i] != ' ') continue;
        memcpy(l1, name, (size_t)i);
        l1[i] = 0;
        strcpy(l2, name + i + 1);
        int w1 = bestiary_font_measure_utf8(l1), w2 = bestiary_font_measure_utf8(l2);
        int m = w1 > w2 ? w1 : w2;
        if (m < best_w) { best_w = m; best = i; }
    }
    if (best < 0) {
        draw_text_centered(buf, cx, y0 + (h - lh) / 2, name, col);
        return;
    }
    memcpy(l1, name, (size_t)best);
    l1[best] = 0;
    strcpy(l2, name + best + 1);
    int top = y0 + (h - 2 * lh) / 2;
    draw_text_centered(buf, cx, top, l1, col);
    draw_text_centered(buf, cx, top + lh, l2, col);
}

static void render_tree(uint16_t *buf) {
    const uint16_t ivory = RGB15(30, 27, 20) | BIT(15);
    const uint16_t owned_fill = RGB15(12, 9, 4) | BIT(15);
    const uint16_t buy_bdr = RGB15(18, 16, 12) | BIT(15);
    const uint16_t buy_txt = RGB15(22, 20, 17) | BIT(15);
    const uint16_t lock_bdr = RGB15(6, 5, 5) | BIT(15);
    const uint16_t lock_txt = RGB15(9, 8, 7) | BIT(15);
    static const char *const branch_names[TREE_COLS] = { "Metralleta", "Quemadura", "Veneno", "Resurrec." };
    char line[40];

    fill_rect(buf, 0, 0, SCREEN_W, SCREEN_H, MENU_COL_INA_FILL);

    /* Header: Volver (left), title (centre), points (right). */
    tree_box(buf, 6, 3, 50, 14, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
    draw_text_centered(buf, 31, 3 + (14 - bestiary_font_line_height()) / 2, "Volver", MENU_COL_INA_TXT);
    draw_text_centered(buf, SCREEN_W / 2, 4, "Árbol", MENU_COL_HEADER);
    snprintf(line, sizeof(line), "Puntos: %d", (int)g_arpg.points);
    draw_text(buf, 250 - bestiary_font_measure_utf8(line), 4, line, MENU_COL_BODY);

    /* Labels: "Rayo" over the left half (its root box is to the right of it), branch names above each column. */
    draw_text_centered(buf, 66, TREE_ROOT_Y + 2, "Rayo", MENU_COL_HEADER);
    for (int c = 0; c < TREE_COLS; c++)
        draw_text_centered(buf, s_tree_col_x[c] + TREE_NODE_W / 2, TREE_BRANCH_Y, branch_names[c], MENU_COL_INA_TXT);

    for (int id = 0; id < ARPG_NODE_COUNT; id++) {
        int x, y, w, h;
        tree_node_rect(id, &x, &y, &w, &h);
        int owned = arpg_tree_has(id);
        int buyable = arpg_tree_can_buy(id);
        uint16_t fill = owned ? owned_fill : MENU_COL_INA_FILL;
        uint16_t bdr = owned ? MENU_COL_ACT_BDR : (buyable ? buy_bdr : lock_bdr);
        uint16_t txt = owned ? MENU_COL_ACT_TXT : (buyable ? buy_txt : lock_txt);
        tree_box(buf, x, y, w, h, fill, bdr);
        draw_node_name(buf, x, y, w, h, arpg_tree_name(id), txt);
    }

    /* Selected node: a ivory frame 2 px outside its box. */
    {
        int x, y, w, h;
        tree_node_rect(s_tree_sel, &x, &y, &w, &h);
        dirty_rect(x - 2, y - 2, x + w + 2, y + h + 2);
        frame_rect(buf, x - 2, y - 2, w + 4, h + 4, ivory);
    }

    /* Strip: name and buy state on the first line, description on the second. */
    fill_rect(buf, 6, TREE_STRIP_Y, 244, TREE_STRIP_H, MENU_COL_INA_FILL);
    frame_rect(buf, 6, TREE_STRIP_Y, 244, TREE_STRIP_H, MENU_COL_INA_BDR);
    {
        int s = s_tree_sel;
        const char *state = NULL;
        if (arpg_tree_has(s)) state = "Aprendido";
        else if (arpg_tree_can_buy(s)) state = "Pulsa A para aprender";
        else if (g_arpg.points <= 0) state = "Sin puntos";
        else state = "Requiere otro nodo";
        draw_text(buf, 12, TREE_STRIP_Y + 3, arpg_tree_name(s), MENU_COL_HEADER);
        draw_text(buf, 244 - bestiary_font_measure_utf8(state), TREE_STRIP_Y + 3, state,
                  arpg_tree_can_buy(s) ? MENU_COL_HEADER : MENU_COL_INA_TXT);
        draw_text(buf, 12, TREE_STRIP_Y + 17, arpg_tree_desc(s), MENU_COL_BODY);
    }
}

void menu_render_bottom(uint16_t *buf) {
    if (s_state == MENU_NONE || !buf) return;
    if (s_state == MENU_LEVELUP) {
        render_levelup(buf);
        return;
    }
    if (s_state == MENU_TREE) {
        render_tree(buf);
        return;
    }

    if (s_state == MENU_CAMP) {
        char line[32];
        const ArpgProgress *p = &g_arpg;
        draw_box(buf, 12, 6, 232, 90, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 14, "Campamento", MENU_COL_HEADER);
        snprintf(line, sizeof(line), "Nivel %d", (int)p->level);
        draw_text(buf, 26, 30, line, MENU_COL_BODY);
        snprintf(line, sizeof(line), "Exp %lu / %d", (unsigned long)p->xp, arpg_xp_needed(p->level));
        draw_text(buf, 26, 42, line, MENU_COL_BODY);
        snprintf(line, sizeof(line), "Puntos %d", (int)p->points);
        draw_text(buf, 26, 54, line, MENU_COL_BODY);
        snprintf(line, sizeof(line), "Piso más hondo %d", (int)p->deepest);
        draw_text(buf, 26, 66, line, MENU_COL_BODY);
        if (s_camp_msg[0]) draw_text_centered(buf, SCREEN_W / 2, 80, s_camp_msg, MENU_COL_HEADER);
    } else if (s_state == MENU_BESTIARY) {
        draw_box(buf, 38, 36, 180, 72, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 48, "Códice", MENU_COL_HEADER);
        draw_text_centered(buf, SCREEN_W / 2, 76, "Próximamente", MENU_COL_BODY);
    } else if (s_state == MENU_CONTROLS) {
        static const char *const lines[7] = {
            "Cruceta - moverse",
            "Lápiz - apuntar y cargar",
            "Start - pausa",
            "X - subir de nivel (prueba)",
            "Select - efectos A/B/C (prueba)",
            "L R B - invulnerable (prueba)",
            ""
        };
        draw_box(buf, 12, 10, 232, 116, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 18, "Controles", MENU_COL_HEADER);
        for (int i = 0; i < 6; i++) {
            draw_text(buf, 22, 36 + i * 13, lines[i], MENU_COL_BODY);
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
                           btns[i].y0 + (btns[i].h - bestiary_font_line_height()) / 2,
                           btns[i].label, txt);
    }
}
