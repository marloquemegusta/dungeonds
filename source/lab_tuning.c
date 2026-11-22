#include "lab_tuning.h"

#if ARPG_LAB

#include <nds.h>
#include <stdio.h>
#include <string.h>
#include "game.h"
#include "bestiary_font.h"

int g_lab_sfx_var[SND_COUNT];
int g_lab_god = 0;

static const char *const s_variant_labels[LABV_COUNT] = {
#define X(n, label, mm) [LABV_##n] = label,
    LAB_VARIANTS(X)
#undef X
};

/* Candidates of each event, in menu order (variant k of the event is v[k-1]; variant 0 is always the original). */
typedef struct { uint8_t n; int8_t v[4]; } EventVariants;
static const EventVariants s_ev[SND_COUNT] = {
    [SND_PUNCH_WHOOSH]      = { 3, { LABV_CLOTH1, LABV_CLOTH4, LABV_KNIFE } },
    [SND_PUNCH_HIT]         = { 4, { LABV_PUNCH_M0, LABV_PUNCH_M2, LABV_PUNCH_H0, LABV_PUNCH_H3 } },
    [SND_CIRENEO_WALL]      = { 3, { LABV_WOOD_HEAVY, LABV_MINING0, LABV_GENERIC_LIGHT } },
    [SND_BOSS_PHASE]        = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_WOBBLE_CUE]        = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_MONAGUILLO_EMERGE] = { 2, { LABV_MINING2, LABV_STEP_STONE } },
    [SND_PICKUP_ORB]        = { 3, { LABV_GLASS1, LABV_GLASS4, LABV_CONFIRM1 } },
    [SND_CHEST_OPEN]        = { 3, { LABV_CREAK, LABV_LATCH, LABV_DOOR_OPEN1 } },
    [SND_DOOR_OPEN]         = { 2, { LABV_DOOR_OPEN2, LABV_DOOR_CLOSE } },
    [SND_UI_CLICK]          = { 3, { LABV_CLICK, LABV_SELECT, LABV_TICK } },
    [SND_RELIC_SOCKET]      = { 3, { LABV_DROP, LABV_METAL_CLICK, LABV_PLATE } },
    [SND_LEVEL_UP]          = { 2, { LABV_CONFIRM2, LABV_MAXIMIZE } },
};

int lab_sfx_candidate(int ev) {
    if (ev < 0 || ev >= SND_COUNT) return -1;
    int k = g_lab_sfx_var[ev];
    if (k <= 0 || k > s_ev[ev].n) return -1;
    return s_ev[ev].v[k - 1];
}

#define SFXROW(page, label, id) { page, label, &g_lab_sfx_var[id], 0, 0, 1, LAB_KIND_SFX_VARIANT }

#define PG_A "Sonidos: combate"
#define PG_B "Sonidos: mundo y menús"
#define PG_C "Sonidos: sin variantes"

/* THE TABLE: add a line to register a tunable (see lab_tuning.h). Events with candidates come first. */
static const LabEntry s_entries[] = {
    SFXROW(PG_A, "Puño aire", SND_PUNCH_WHOOSH),
    SFXROW(PG_A, "Puño impacto", SND_PUNCH_HIT),
    SFXROW(PG_A, "Cireneo muro", SND_CIRENEO_WALL),
    SFXROW(PG_A, "Aviso tambaleo", SND_WOBBLE_CUE),
    SFXROW(PG_A, "Fase jefe", SND_BOSS_PHASE),
    SFXROW(PG_A, "Monaguillo surge", SND_MONAGUILLO_EMERGE),

    SFXROW(PG_B, "Orbe recogido", SND_PICKUP_ORB),
    SFXROW(PG_B, "Abrir cofre", SND_CHEST_OPEN),
    SFXROW(PG_B, "Abrir puerta", SND_DOOR_OPEN),
    SFXROW(PG_B, "Clic menú", SND_UI_CLICK),
    SFXROW(PG_B, "Engarce reliquia", SND_RELIC_SOCKET),
    SFXROW(PG_B, "Subir nivel", SND_LEVEL_UP),

    SFXROW(PG_C, "Hechizo disparo", SND_HEART_FIRE),
    SFXROW(PG_C, "Hechizo carga", SND_HEART_CHARGE),
    SFXROW(PG_C, "Golpe enemigo", SND_ENEMY_HIT),
    SFXROW(PG_C, "Muerte enemigo", SND_ENEMY_DEATH),
    SFXROW(PG_C, "Héroe herido", SND_PLAYER_HURT),
    SFXROW(PG_C, "Remate", SND_REMATE_EXEC),
    SFXROW(PG_C, "Glifo lanzar", SND_GLIFO_CAST),
    SFXROW(PG_C, "Glifo activar", SND_GLIFO_ACTIVATE),
    SFXROW(PG_C, "Ojo carga", SND_OJO_CHARGE),
    SFXROW(PG_C, "Ojo disparo", SND_OJO_FIRE),
    SFXROW(PG_C, "Cireneo carga", SND_CIRENEO_CHARGE),
    SFXROW(PG_C, "Monja cura", SND_MONJA_HEAL),
    SFXROW(PG_C, "Abanderado voz", SND_ABANDERADO_INTRO),
    SFXROW(PG_C, "Abanderado fin", SND_ABANDERADO_DEFEAT),

    { "Pruebas", "Invulnerable", &g_lab_god, 0, 1, 1, LAB_KIND_INT },
};
#define N_ENTRIES ((int)(sizeof(s_entries) / sizeof(s_entries[0])))


#define VISIBLE_ROWS 10
#define ROW_H 13
#define ROW_Y0 22

static int s_open = 0;
static int s_page = 0;          /* index of the current page */
static int s_sel = 0;           /* row inside the page */
static int s_scroll = 0;
static int s_hold_dir = 0, s_hold_frames = 0;

void lab_tuning_init(void) {
    for (int i = 0; i < SND_COUNT; i++) g_lab_sfx_var[i] = 0;
}

int lab_tuning_is_open(void) { return s_open; }

/* The k-th distinct page title in order of appearance (NULL past the last). */
static const char *page_title(int k) {
    int seen = -1;
    for (int i = 0; i < N_ENTRIES; i++) {
        int first = 1;
        for (int j = 0; j < i; j++) {
            if (strcmp(s_entries[j].page, s_entries[i].page) == 0) { first = 0; break; }
        }
        if (first && ++seen == k) return s_entries[i].page;
    }
    return NULL;
}

static int page_count(void) {
    int n = 0;
    while (page_title(n)) n++;
    return n;
}

/* Entry index of row `row` in the current page, or -1. */
static int page_entry(int row) {
    const char *t = page_title(s_page);
    int r = 0;
    for (int i = 0; i < N_ENTRIES; i++) {
        if (strcmp(s_entries[i].page, t) != 0) continue;
        if (r++ == row) return i;
    }
    return -1;
}

static int page_rows(void) {
    int n = 0;
    while (page_entry(n) >= 0) n++;
    return n;
}

static int sfx_event(const LabEntry *e) { return (int)(e->value - g_lab_sfx_var); }

static void change(const LabEntry *e, int dir) {
    int v = *e->value;
    if (e->kind == LAB_KIND_SFX_VARIANT) {
        int n = s_ev[sfx_event(e)].n;
        if (n == 0) return;
        v += dir;
        if (v < 0) v = n;
        if (v > n) v = 0;
        *e->value = v;
        sfx_lab_prepare(sfx_event(e));
        return;
    }
    v += dir * e->step;
    if (v < e->min) v = e->min;
    if (v > e->max) v = e->max;
    *e->value = v;
}

static void set_page(int p) {
    int n = page_count();
    s_page = (p % n + n) % n;
    s_sel = 0;
    s_scroll = 0;
}

int lab_tuning_update(uint32_t keys_down, uint32_t keys_held) {
    const int chord = (keys_held & KEY_L) && (keys_held & KEY_R);      /* L+R+SELECT is the bestiary / crash combo */
    if (!s_open) {
        if ((keys_down & KEY_SELECT) && !chord) {
            s_open = 1;
            s_hold_dir = 0;
            sfx_set_bgm_paused(1);
            return 1;
        }
        return 0;
    }
    if (keys_down & (KEY_B | KEY_SELECT)) {
        s_open = 0;
        sfx_set_bgm_paused(0);
        return 1;           /* this frame the closing key is still swallowed */
    }
    int rows = page_rows();
    if (keys_down & KEY_UP) s_sel = (s_sel + rows - 1) % rows;
    if (keys_down & KEY_DOWN) s_sel = (s_sel + 1) % rows;
    if (keys_down & KEY_L) set_page(s_page - 1);
    if (keys_down & KEY_R) set_page(s_page + 1);
    rows = page_rows();
    if (s_sel < s_scroll) s_scroll = s_sel;
    if (s_sel >= s_scroll + VISIBLE_ROWS) s_scroll = s_sel - VISIBLE_ROWS + 1;

    int ei = page_entry(s_sel);
    if (ei >= 0) {
        const LabEntry *e = &s_entries[ei];
        int dir = 0;
        if (keys_down & KEY_LEFT) { dir = -1; s_hold_dir = -1; s_hold_frames = 0; }
        else if (keys_down & KEY_RIGHT) { dir = 1; s_hold_dir = 1; s_hold_frames = 0; }
        else if ((s_hold_dir < 0 && (keys_held & KEY_LEFT)) || (s_hold_dir > 0 && (keys_held & KEY_RIGHT))) {
            if (++s_hold_frames >= 20 && (s_hold_frames & 3) == 0 && e->kind == LAB_KIND_INT) dir = s_hold_dir;
        } else {
            s_hold_dir = 0;
        }
        if (dir) change(e, dir);
        if ((keys_down & KEY_A) && e->kind == LAB_KIND_SFX_VARIANT) sfx_lab_preview(sfx_event(e));
    }
    return 1;
}

#define COL_PANEL (RGB15(2, 1, 3) | BIT(15))
#define COL_BORDER (RGB15(10, 9, 8) | BIT(15))
#define COL_SEL (RGB15(9, 3, 3) | BIT(15))
#define COL_TXT (RGB15(26, 24, 20) | BIT(15))
#define COL_DIM (RGB15(15, 14, 13) | BIT(15))
#define COL_GOLD (RGB15(31, 27, 12) | BIT(15))

static void fill(uint16_t *buf, int x0, int y0, int x1, int y1, uint16_t col) {
    dirty_rect(x0, y0, x1, y1);
    for (int y = y0; y < y1; y++) {
        uint16_t *row = &buf[y * SCREEN_W];
        for (int x = x0; x < x1; x++) row[x] = col;
    }
}

static void text(uint16_t *buf, int x, int y, const char *s, uint16_t col) {
    bestiary_font_draw_utf8(buf, x, y, s, col);
}

static void text_right(uint16_t *buf, int xr, int y, const char *s, uint16_t col) {
    text(buf, xr - bestiary_font_measure_utf8(s), y, s, col);
}

void lab_tuning_render(uint16_t *buf) {
    if (!s_open || !buf) return;
    fill(buf, 4, 2, SCREEN_W - 4, SCREEN_H - 2, COL_BORDER);
    fill(buf, 5, 3, SCREEN_W - 5, SCREEN_H - 3, COL_PANEL);

    char head[64];
    if (page_rows() > VISIBLE_ROWS) snprintf(head, sizeof(head), "fila %d/%d  pág %d/%d", s_sel + 1, page_rows(), s_page + 1, page_count());
    else snprintf(head, sizeof(head), "pág %d/%d", s_page + 1, page_count());
    text(buf, 10, 5, page_title(s_page), COL_GOLD);
    text_right(buf, SCREEN_W - 10, 5, head, COL_DIM);

    int rows = page_rows();
    for (int v = 0; v < VISIBLE_ROWS; v++) {
        int row = s_scroll + v;
        if (row >= rows) break;
        const LabEntry *e = &s_entries[page_entry(row)];
        int y = ROW_Y0 + v * ROW_H;
        int sel = (row == s_sel);
        if (sel) fill(buf, 7, y - 1, SCREEN_W - 7, y + ROW_H - 1, COL_SEL);
        int dim_row = (e->kind == LAB_KIND_SFX_VARIANT && s_ev[sfx_event(e)].n == 0);
        text(buf, 12, y, e->label, sel ? COL_GOLD : (dim_row ? COL_DIM : COL_TXT));
        char val[40];
        int dim = 0;
        if (e->kind == LAB_KIND_SFX_VARIANT) {
            int ev = sfx_event(e), k = *e->value;
            dim = (s_ev[ev].n == 0);
            snprintf(val, sizeof(val), "%s%s", k ? "* " : "", k ? s_variant_labels[s_ev[ev].v[k - 1]] : "Original");
        } else {
            snprintf(val, sizeof(val), "%d", *e->value);
        }
        text_right(buf, SCREEN_W - 12, y, val, sel ? COL_GOLD : (dim ? COL_DIM : COL_TXT));
    }

    text(buf, 10, 154, "Cruz: fila y variante     A: probar", COL_DIM);
    text(buf, 10, 166, "L/R: página     B o SELECT: cerrar", COL_DIM);
    text(buf, 10, 178, "* = variante distinta del original", COL_DIM);
}

#else
typedef int lab_tuning_disabled_translation_unit;
#endif
