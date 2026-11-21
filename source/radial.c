#include "radial.h"
#include "game.h"
#include "arpg_inv.h"
#include "arpg_progress.h"
#include "arpg_hud_gfx.h"

// Hasta tres hechizos equipados (DESIGN.md 7.4): el activo más dos alternativos. El anillo
// existente ya tenía disposición para 1, 2 y 3 entradas, así que solo cambia de dónde salen.
#define RADIAL_MAX ARPG_INV_SPELLS
#define RADIAL_CELL_W HUD_VIRIL_RAYO_W
#define RADIAL_CELL_H HUD_VIRIL_RAYO_H

// The icon the radial grows from: exact spot draw_run_hud uses for the active viril.
#define RADIAL_ANCHOR_X 203
#define RADIAL_ANCHOR_Y (SCREEN_H - HUD_VIRIL_RAYO_H + HUD_VIRIL_RAYO_H / 2)

static int s_open = 0;
static int s_count = 0;
static int s_spells[RADIAL_MAX];

// Alternatives sit on a ring around the active icon (the anchor): every entry is at the same
// centre-to-centre distance (~36 px) from it, fanned over the quarter up-left so they never reach
// the Reliquary (bottom-right) or the Caliz (bottom-left). Indexed by the number of entries.
static const int8_t s_ring_dx[4][3] = { {0,0,0}, {-25,0,0}, {-13,-33,0}, {0,-25,-36} };
static const int8_t s_ring_dy[4][3] = { {0,0,0}, {-25,0,0}, {-33,-13,0}, {-36,-25,0} };

// The entries are every equipped spell except the active one, rebuilt on demand (picking one swaps it).
static int build_entries(void) {
    int avail[RADIAL_MAX], n = 0, m = 0;
    for (int i = 0; i < ARPG_INV_SPELLS; i++) {
        int sp = arpg_inv_equipped_spell(i);
        if (sp < 0) continue;
        int dup = 0;
        for (int k = 0; k < n; k++) if (avail[k] == sp) dup = 1;
        if (!dup) avail[n++] = sp;
    }
    for (int i = 0; i < n; i++)
        if (avail[i] != (int)g_arpg.spell) s_spells[m++] = avail[i];
    s_count = m;
    return m;
}

static const uint16_t *spell_icon(int spell) {
    if (spell == ARPG_SPELL_GLIFO) return g_hud_viril_glifo;
    if (spell == ARPG_SPELL_LEVANTAR) return g_hud_viril_levantar;
    return g_hud_viril_rayo;
}

static void entry_rect(int i, int *x0, int *y0) {
    int cx = RADIAL_ANCHOR_X + s_ring_dx[s_count][i];
    int cy = RADIAL_ANCHOR_Y + s_ring_dy[s_count][i];
    int x = cx - RADIAL_CELL_W / 2;
    int y = cy - RADIAL_CELL_H / 2;
    if (x > SCREEN_W - RADIAL_CELL_W) x = SCREEN_W - RADIAL_CELL_W;
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    *x0 = x;
    *y0 = y;
}

int radial_is_open(void) {
    return s_open;
}

int radial_begin(void) {
    s_open = (build_entries() >= 1) ? 1 : 0;      // nothing to pick with a single spell
    return s_open;
}

void radial_close(void) {
    s_open = 0;
}

int radial_touch(int tx, int ty) {
    if (!s_open) return -1;
    build_entries();
    for (int i = 0; i < s_count; i++) {
        int x0, y0;
        entry_rect(i, &x0, &y0);
        if (tx >= x0 && tx < x0 + RADIAL_CELL_W && ty >= y0 && ty < y0 + RADIAL_CELL_H)
            return s_spells[i];
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

static void outline_rect(uint16_t *buffer, int x0, int y0, int w, int h, uint16_t color) {
    if (w <= 0 || h <= 0) return;
    int x1 = x0 + w, y1 = y0 + h;
    for (int x = x0; x < x1; x++) {
        int sx = x;
        if (sx < 0 || sx >= SCREEN_W) continue;
        if (y0 >= 0 && y0 < SCREEN_H) { dirty_row(y0, sx, sx + 1); buffer[y0 * SCREEN_W + sx] = color; }
        if (y1 - 1 >= 0 && y1 - 1 < SCREEN_H) { dirty_row(y1 - 1, sx, sx + 1); buffer[(y1 - 1) * SCREEN_W + sx] = color; }
    }
    for (int y = y0; y < y1; y++) {
        int sy = y;
        if (sy < 0 || sy >= SCREEN_H) continue;
        if (x0 >= 0 && x0 < SCREEN_W) { dirty_row(sy, x0, x0 + 1); buffer[sy * SCREEN_W + x0] = color; }
        if (x1 - 1 >= 0 && x1 - 1 < SCREEN_W) { dirty_row(sy, x1 - 1, x1); buffer[sy * SCREEN_W + x1 - 1] = color; }
    }
}

// Same blit rule as draw_hud_sprite in main.c: zero pixels are transparent.
static void blit_icon(uint16_t *buffer, int x0, int y0, const uint16_t *sprite) {
    for (int y = 0; y < RADIAL_CELL_H; y++) {
        int sy = y0 + y;
        if (sy < 0 || sy >= SCREEN_H) continue;
        int d0 = x0 < 0 ? 0 : x0;
        int d1 = (x0 + RADIAL_CELL_W) > SCREEN_W ? SCREEN_W : (x0 + RADIAL_CELL_W);
        if (d0 < d1) dirty_row(sy, d0, d1);
        const uint16_t *row = &sprite[y * RADIAL_CELL_W];
        for (int x = 0; x < RADIAL_CELL_W; x++) {
            int sx = x0 + x;
            if (sx >= 0 && sx < SCREEN_W && row[x] != 0) buffer[sy * SCREEN_W + sx] = row[x];
        }
    }
}

void radial_render(uint16_t *buffer) {
    if (!s_open) return;
    build_entries();

    const uint16_t edge = RGB15(22, 18, 11) | BIT(15);     // desaturated warm ring around the active icon

    // No backing box: the entries float over the room. The active icon stays at the centre, outlined.
    for (int i = 0; i < s_count; i++) {
        int x0, y0;
        entry_rect(i, &x0, &y0);
        blit_icon(buffer, x0, y0, spell_icon(s_spells[i]));
    }
    int ax = RADIAL_ANCHOR_X - RADIAL_CELL_W / 2, ay = SCREEN_H - RADIAL_CELL_H;
    outline_rect(buffer, ax - 1, ay - 1, RADIAL_CELL_W + 2, RADIAL_CELL_H + 2, edge);
}
