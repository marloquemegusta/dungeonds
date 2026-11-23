#include "menu.h"
#include "game.h"
#include "upgrades.h"
#include "bestiary_font.h"
#include "levelup_cards.h"
#include "hud_icons_gfx.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "inventory.h"
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
static int s_pause_in_camp = 0;        /* pause opened from the camp scene: no "back to the camp" button */

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
    /* Title and pause buttons are filled at run time: the title drops "Continuar" when there is no save,
       the pause drops "Volver al campamento" when it was opened from the camp itself. */
    static MenuButton title_btns[4];
    static const char *const title_labels[4] = { "Continuar", "Nueva partida", "Códice", "Controles" };
    static MenuButton pause_btns[5];
    static const MenuButton bestiary_btns[] = {
        { BTN_X0, 128, BTN_W, BTN_H, "Volver" },
    };
    static const MenuButton controls_btns[] = {
        { BTN_X0, 142, BTN_W, BTN_H, "Volver" },
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
    case MENU_PAUSE: {
        static const char *const pause_labels_camp[3] = { "Continuar", "Códice", "Controles" };
#if ENCOUNTERS_PROTO
        /* Inventario (DESIGN.md 7.4): the dungeon pause opens the bag; in the camp it is the chest. */
        static const char *const pause_labels_dungeon[5] = { "Continuar", "Inventario", "Volver al campamento", "Códice", "Controles" };
#else
        static const char *const pause_labels_dungeon[4] = { "Continuar", "Reiniciar", "Códice", "Controles" };
#endif
        const char *const *labels = s_pause_in_camp ? pause_labels_camp : pause_labels_dungeon;
        int n = s_pause_in_camp ? 3 : (ENCOUNTERS_PROTO ? 5 : 4);
        /* The camp pause (3 buttons) is centred; the dungeon one (5) is packed above the HUD (bottom ~40 px). */
        int packed = (n == 5);
        int y0 = packed ? 12 : 42, pitch = packed ? 27 : BTN_PITCH;
        for (int i = 0; i < n; i++)
            pause_btns[i] = (MenuButton){ BTN_X0, y0 + i * pitch, BTN_W, BTN_H, labels[i] };
        *out_btns = pause_btns;
        return n;
    }
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

    case MENU_PAUSE: {
        /* Same order as the labels in get_buttons(): the camp pause has no "back to the camp" button. */
        int k = idx;
        if (k == 0) {
            s_state = MENU_NONE;
            return MENU_ACT_RESUME;
        }
#if ENCOUNTERS_PROTO
        if (!s_pause_in_camp && k == 1) {
            s_parent = MENU_PAUSE;      /* closing the inventory returns to the pause */
            s_state = MENU_INVENTORY;
            inventory_open();
            return MENU_ACT_NONE;
        }
#endif
        if (!s_pause_in_camp) {
            int camp_k = ENCOUNTERS_PROTO ? 2 : 1;
            if (k == camp_k) {
                s_state = MENU_NONE;
#if ENCOUNTERS_PROTO
                return MENU_ACT_TO_CAMP;
#else
                return MENU_ACT_START_NEW;
#endif
            }
            k -= ENCOUNTERS_PROTO ? 2 : 1;
        }
        if (k == 1) {
            s_parent = MENU_PAUSE;
            s_state = MENU_BESTIARY;
            s_sel = 0;
        } else if (k == 2) {
            s_parent = MENU_PAUSE;
            s_state = MENU_CONTROLS;
            s_sel = 0;
        }
        return MENU_ACT_NONE;
    }

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

void menu_open_inventory(int mode) {
    s_state = MENU_INVENTORY;
    s_parent = MENU_NONE;   /* Volver/B closes straight back to the camp scene */
    inventory_open_mode(mode);
}

void menu_open_codex(void) {
    s_state = MENU_BESTIARY;
    s_parent = MENU_NONE;   /* the viewer closes straight back to the camp scene */
    s_sel = 0;
}

void menu_open_pause(int from_camp) {
    s_state = MENU_PAUSE;
    s_parent = MENU_PAUSE;
    s_pause_in_camp = from_camp != 0;
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

MenuAction menu_update(uint32_t keys_down, int touch_pressed, int touch_x, int touch_y) {
    if (s_state == MENU_NONE) return MENU_ACT_NONE;

    if (s_state == MENU_INVENTORY) {
        if (inventory_update(keys_down, touch_pressed, touch_x, touch_y)) {
            s_state = s_parent;
            s_sel = 0;
        }
        return MENU_ACT_NONE;
    }

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

void menu_render_bottom(uint16_t *buf) {
    if (s_state == MENU_NONE || !buf) return;
    if (s_state == MENU_LEVELUP) {
        render_levelup(buf);
        return;
    }
    if (s_state == MENU_INVENTORY) {
        inventory_render(buf);
        return;
    }

    if (s_state == MENU_TITLE) {
        /* Mismo fondo casi negro que la pantalla de arriba (title_screen.c): sin suelo de catedral. */
        const uint16_t bg = RGB15(1, 1, 2) | BIT(15);
        dirty_rect(0, 0, SCREEN_W, SCREEN_H);
        for (int i = 0; i < SCREEN_W * SCREEN_H; i++) buf[i] = bg;
    }
    if (s_state == MENU_BESTIARY) {
        draw_box(buf, 38, 36, 180, 72, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 48, "Códice", MENU_COL_HEADER);
        draw_text_centered(buf, SCREEN_W / 2, 76, "Próximamente", MENU_COL_BODY);
    } else if (s_state == MENU_CONTROLS) {
        /* Two blocks with a heading: key column in the header colour, description in the body colour. */
        static const char *const dungeon_keys[6] = { "Cruceta", "Lápiz", "L", "Mantén L", "SELECT", "START" };
        static const char *const dungeon_text[6] = {
            "Mover", "Lanzar el hechizo (gasta maná)", "Puñetazo; remata al que se tambalea",
            "Elegir hechizo (toca uno)", "Mapa", "Pausa"
        };
        static const char *const camp_keys[2] = { "A", "START" };
        static const char *const camp_text[2] = { "Usar (jergón, arcón, atril, puerta)", "Pausa" };
        const int key_x = 16, text_x = 72, step = 10;
        draw_box(buf, 6, 4, 244, 130, MENU_COL_INA_FILL, MENU_COL_INA_BDR);
        draw_text_centered(buf, SCREEN_W / 2, 7, "Controles", MENU_COL_HEADER);
        int y = 21;
        draw_text(buf, key_x - 4, y, "En la catedral", MENU_COL_HEADER);
        y += step + 1;
        for (int i = 0; i < 6; i++, y += step) {
            draw_text(buf, key_x, y, dungeon_keys[i], MENU_COL_HEADER);
            draw_text(buf, text_x, y, dungeon_text[i], MENU_COL_BODY);
        }
        y += 5;
        draw_text(buf, key_x - 4, y, "En el campamento", MENU_COL_HEADER);
        y += step + 1;
        for (int i = 0; i < 2; i++, y += step) {
            draw_text(buf, key_x, y, camp_keys[i], MENU_COL_HEADER);
            draw_text(buf, text_x, y, camp_text[i], MENU_COL_BODY);
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
