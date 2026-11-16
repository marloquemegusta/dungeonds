#include "gems.h"
#include "upgrades.h"
#include "collision.h"
#include "groundfx.h"

#define GEM_RECYCLE_BELOW_PX 400    // gems this far behind the hero are dropped

typedef struct { fixed x, y; uint8_t value; uint8_t active; uint8_t nox; int8_t mx, my; } Gem;   // mx, my: last magnet step (0 = not pulled); nox: evidence hook, no xp
static Gem s_gems[GEM_MAX_ACTIVE];
static uint32_t s_anim_tick = 0;

// XP per enemy type (DESIGN.md 6.12.10).
static int gem_value(EnemyType type) {
    switch (type) {
    case ENEMY_TYPE_ABANDERADO: return 15;
    case ENEMY_TYPE_CHARGER:
    case ENEMY_TYPE_SHOOTER:    return 3;
    default:                    return 1;   // exvoto, monaguillo
    }
}

void gems_init(void) {
    for (int i = 0; i < GEM_MAX_ACTIVE; i++) s_gems[i].active = 0;
    s_anim_tick = 0;
}

void gems_shift_y(int dy_px) {
    fixed shift = TO_FIXED(dy_px);
    for (int i = 0; i < GEM_MAX_ACTIVE; i++)
        if (s_gems[i].active) s_gems[i].y += shift;
}

volatile uint8_t g_gems_off = 0;

void gems_enemy_killed(const Enemy *enemy) {
    if (!enemy || g_gems_off) return;
    int value = gem_value(enemy->type);
    for (int i = 0; i < GEM_MAX_ACTIVE; i++) {
        if (s_gems[i].active) continue;
        s_gems[i].x = enemy->x;
        s_gems[i].y = enemy->y;
        s_gems[i].value = (uint8_t)value;
        s_gems[i].active = 1;
        s_gems[i].mx = s_gems[i].my = 0;
        s_gems[i].nox = 0;
        return;
    }
    upgrades_add_xp(value);     // pool full: no gem on the floor, the xp goes straight in
}

// Evidence hook for the design-variant scenarios (scenarios/abc_*.json): 1 = a row of gems (small, mid, big, mid,
// small) in front of the hero, out of reach; 2 = the same row inside the magnet radius (no xp when picked up);
// 3 = one mid gem inside the magnet radius that does give xp; 4 = occlusion staging (gems at fixed world points of the
// cathedral strip behind and in front of a column, a pew and a standing enemy, out of reach, no xp). Cleared at once.
volatile uint8_t g_abc_gems = 0;

void gems_update(fixed player_x, fixed player_y, fixed tide_y) {
    s_anim_tick++;
    if (g_abc_gems && g_abc_gems != 4) {
        static const int8_t dx_lut[5] = { -44, -22, 0, 22, 44 };
        static const uint8_t val_lut[5] = { 1, 3, 15, 3, 1 };
        int near = g_abc_gems >= 2, nox = g_abc_gems == 2, only = g_abc_gems == 3;
        g_abc_gems = 0;
        for (int k = 0; k < 5; k++) {
            if (only && k != 1) continue;
            for (int i = 0; i < GEM_MAX_ACTIVE; i++) {
                if (s_gems[i].active) continue;
                s_gems[i].x = player_x + TO_FIXED(near ? (k - 2) * 7 : dx_lut[k]);
                s_gems[i].y = player_y - TO_FIXED(near ? 8 + (k & 1) * 2 : 60 + (k & 1) * 12);
                s_gems[i].value = val_lut[k];
                s_gems[i].active = 1;
                s_gems[i].mx = s_gems[i].my = 0;
                s_gems[i].nox = (uint8_t)nox;
                break;
            }
        }
    }
    if (g_abc_gems == 4) {
        static const int16_t occ_lut[][2] = {      // world x, y (scenes/abc occlusion staging, hero at 200,1760)
            { 82, 1524 }, { 70, 1526 }, { 82, 1546 }, { 158, 1498 }, { 176, 1498 }, { 158, 1514 },
            { 240, 1734 }, { 240, 1748 },
        };
        g_abc_gems = 0;
        for (unsigned k = 0; k < sizeof(occ_lut) / sizeof(occ_lut[0]); k++)
            for (int i = 0; i < GEM_MAX_ACTIVE; i++) {
                if (s_gems[i].active) continue;
                s_gems[i].x = TO_FIXED(occ_lut[k][0]);
                s_gems[i].y = TO_FIXED(occ_lut[k][1]);
                s_gems[i].value = 3;
                s_gems[i].active = 1;
                s_gems[i].mx = s_gems[i].my = 0;
                s_gems[i].nox = 1;
                break;
            }
    }
    for (int i = 0; i < GEM_MAX_ACTIVE; i++) {
        Gem *g = &s_gems[i];
        if (!g->active) continue;
        if (g->y >= tide_y || g->y > player_y + TO_FIXED(GEM_RECYCLE_BELOW_PX)) { g->active = 0; continue; }
        int dx = TO_INT(player_x - g->x);
        int dy = TO_INT(player_y - g->y);
        int d2 = dx * dx + GROUND_DY2(dy);
        if (d2 <= GEM_PICKUP_RADIUS * GEM_PICKUP_RADIUS) {
            if (!g->nox) upgrades_add_xp(g->value);
            g->active = 0;
            continue;
        }
        if (d2 <= GEM_MAGNET_RADIUS * GEM_MAGNET_RADIUS) {
            // 2 ground px per frame on each axis (1 screen px vertically = 2 ground px).
            int sx = dx > 2 ? 2 : (dx < -2 ? -2 : dx);
            int sy = dy > 1 ? 1 : (dy < -1 ? -1 : dy);
            g->x += TO_FIXED(sx);
            g->y += TO_FIXED(sy);
            g->mx = (int8_t)sx;
            g->my = (int8_t)sy;
        } else {
            g->mx = g->my = 0;
        }
    }
}

// Diamond half-widths per row for the three sizes (3x5, 5x7, 7x9).
static const int8_t s_hw_small[5] = { 0, 1, 1, 1, 0 };
static const int8_t s_hw_mid[7]   = { 0, 1, 2, 2, 2, 1, 0 };
static const int8_t s_hw_big[9]   = { 0, 1, 2, 3, 3, 3, 2, 1, 0 };

typedef struct { uint16_t lit, body, dark; } GemTone;
// Muted amber / bone / old gold, in the spirit of FX_SH_* (DESIGN.md 6.10).
#define GC(r, g, b) (RGB15(r, g, b) | BIT(15))
static const GemTone s_tone_small = { GC(28, 23, 12), GC(24, 17, 6),  GC(14, 9, 3)  };
static const GemTone s_tone_mid   = { GC(29, 27, 21), GC(25, 23, 17), GC(16, 14, 11) };
static const GemTone s_tone_big   = { GC(30, 25, 13), GC(27, 19, 8),  GC(17, 10, 4)  };

// Teardrop half-widths per row (C, drops of molten wax / gold): pointed top, round belly.
static const int8_t s_td_small[6] = { 0, 1, 1, 2, 2, 1 };
static const int8_t s_td_mid[8]   = { 0, 1, 1, 2, 3, 3, 3, 2 };
static const int8_t s_td_big[10]  = { 0, 1, 1, 2, 3, 4, 4, 4, 3, 2 };

// Draw context of the gem being painted (set by gems_draw): walls in front hide it pixel by pixel.
static int s_occ, s_depth, s_cam_x, s_cam_y;

static inline void gem_put(uint16_t *buffer, int x, int y, uint16_t c) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    if (s_occ && world_pixel_hidden(x + s_cam_x, y + s_cam_y, s_depth)) return;
    buffer[y * SCREEN_W + x] = c;
}

static inline void gem_px(uint16_t *buffer, int x, int y, uint16_t c) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    gem_put(buffer, x, y, c);
    dirty_row(y, x, x + 1);
}

// Rosary bead (B): 3x3 round (r = 1) or 5x5 round (r = 2), lit top-left pixel, dark underside.
static void gem_bead(uint16_t *buffer, int cx, int cy, int r, const GemTone *tone) {
    static const int8_t hw1[3] = { 0, 1, 0 };
    static const int8_t hw2[5] = { 1, 2, 2, 2, 1 };
    const int8_t *hw = r == 1 ? hw1 : hw2;
    int n = 2 * r + 1;
    for (int row = 0; row < n; row++)
        for (int dx = -hw[row]; dx <= hw[row]; dx++) {
            uint16_t c = row == n - 1 || (row == n - 2 && dx == hw[row]) ? tone->dark
                       : (row == 0 && dx <= 0) || (row == 1 && dx == -hw[row]) ? tone->lit : tone->body;
            gem_px(buffer, cx + dx, cy - r + row, c);
        }
}

// Screen visibility of gem i for the painter's list in render_screen (main.c): its ground depth (world y).
int gems_item(int i, int cam_x, int cam_y, int *depth) {
    const Gem *g = &s_gems[i];
    if (!g->active) return 0;
    int cx = TO_INT(g->x) - cam_x;
    int cy = TO_INT(g->y) - cam_y;
    if (cx + 12 <= 0 || cx - 12 >= SCREEN_W || cy + 1 <= 0 || cy - 14 >= SCREEN_H) return 0;
    *depth = TO_INT(g->y);
    return 1;
}

void gems_draw(uint16_t *buffer, int i, int cam_x, int cam_y) {
    static const int8_t bob_lut[16] = { 0, 0, -1, -1, -1, -1, -1, 0, 0, 0, 1, 1, 1, 1, 1, 0 };
    const uint16_t shadow_col = RGB15(4, 3, 3) | BIT(15);
    const int variant = g_design_variant;
    // C glow pulse: a faint halo that breathes (1 px out, then 2 px out).
    const uint16_t halo_a = GC(15, 9, 4), halo_b = GC(10, 6, 3);
    const int pulse = (int)((s_anim_tick >> 4) & 1);

    {
        const Gem *g = &s_gems[i];
        const int8_t *hw;
        const GemTone *tone;
        int h;
        int size;                                    // 0 small, 1 mid, 2 big
        if (g->value >= 15)     { hw = s_hw_big;   h = 9; tone = &s_tone_big; size = 2; }
        else if (g->value >= 3) { hw = s_hw_mid;   h = 7; tone = &s_tone_mid; size = 1; }
        else                    { hw = s_hw_small; h = 5; tone = &s_tone_small; size = 0; }
        if (variant == 2) {
            if (size == 2)      { hw = s_td_big;   h = 10; }
            else if (size == 1) { hw = s_td_mid;   h = 8; }
            else                { hw = s_td_small; h = 6; }
        }

        int cx = TO_INT(g->x) - cam_x;
        int cy = TO_INT(g->y) - cam_y;
        int y0 = cy - h - 2 + bob_lut[((s_anim_tick >> 2) + (uint32_t)i) & 15];
        if (cx + 12 <= 0 || cx - 12 >= SCREEN_W || cy + 1 <= 0 || y0 >= SCREEN_H) return;
        s_cam_x = cam_x; s_cam_y = cam_y; s_depth = TO_INT(g->y);
        s_occ = 0;
        for (int r = y0 - 2; r <= cy + 1 && !s_occ; r++)
            if ((unsigned)r < SCREEN_H && world_span_hidden(r + cam_y, cx - 7 + cam_x, cx + 8 + cam_x, s_depth)) s_occ = 1;

        for (int sy = cy - 1; sy <= cy; sy++) {
            if ((unsigned)sy >= SCREEN_H) continue;
            int sw = variant == 1 ? (size > 0 ? 5 : 3) : 2;
            dirty_row(sy, cx - sw, cx + sw + 1);
            for (int sx = cx - sw; sx <= cx + sw; sx++)
                gem_put(buffer, sx, sy, shadow_col);
        }

        // Magnet trail: two dark beads (B) or three fading wax drops (C) behind a gem that is being pulled.
        if (variant != 0 && (g->mx | g->my)) {
            int n = variant == 1 ? 2 : 3;
            for (int k = 1; k <= n; k++) {
                int tx = cx - g->mx * 2 * k, ty = cy - 3 - g->my * k * 2;
                gem_px(buffer, tx, ty, variant == 1 ? tone->dark : (k == 1 ? tone->body : k == 2 ? tone->dark : halo_a));
            }
        }

        if (variant == 1) {
            // B: rosary beads. Small = one bead, mid = two on a thread, big = a decade of three (one over two).
            int by = y0 + (h >> 1);
            if (size == 0) {
                gem_bead(buffer, cx, by, 2, tone);
            } else if (size == 1) {
                gem_bead(buffer, cx - 3, by + 1, 2, tone);
                gem_bead(buffer, cx + 3, by + 1, 2, tone);
            } else {
                gem_bead(buffer, cx - 3, by + 2, 2, tone);
                gem_bead(buffer, cx + 3, by + 2, 2, tone);
                gem_bead(buffer, cx, by - 2, 2, tone);
            }
            return;
        }

        int mid = h >> 1;
        for (int r = 0; r < h; r++) {
            int sy = y0 + r;
            if ((unsigned)sy >= SCREEN_H) continue;
            int w = hw[r];
            dirty_row(sy, cx - w - 2, cx + w + 3);
            for (int dx = -w; dx <= w; dx++) {
                int sx = cx + dx;
                if ((unsigned)sx >= SCREEN_W) continue;
                uint16_t c;
                if (variant == 2) {
                    // Wax drop: lit left edge and a bright speck high on the belly, dark underside.
                    c = r == h - 1 ? tone->dark : (dx < 0 || (dx == 0 && r < mid)) ? tone->lit : tone->body;
                    if (r == mid && dx == -w && w > 0) c = GC(30, 27, 18);
                } else {
                    // Lit upper-left facet, darker lower half.
                    c = r > mid ? tone->dark : (dx < 0 || (dx == 0 && r < mid) ? tone->lit : tone->body);
                }
                gem_put(buffer, sx, sy, c);
            }
            if (variant == 2) {                                      // breathing glow: a dithered halo that swaps phase
                int on = ((r + pulse) & 1) != 0;
                gem_px(buffer, cx - w - 1, sy, on ? halo_a : halo_b);
                gem_px(buffer, cx + w + 1, sy, on ? halo_a : halo_b);
                if (on && w > 1) { gem_px(buffer, cx - w - 2, sy, halo_b); gem_px(buffer, cx + w + 2, sy, halo_b); }
                if (r == 0) gem_px(buffer, cx, sy - 1, pulse ? halo_a : halo_b);
            }
        }
    }
}
