#include "groundfx.h"

// Ground-plane effects (DESIGN.md 4.9). Integer only: no float, no libm, no division in pixel loops.
// Ground coordinates are world px; the screen point is (wx - cam_x, wy - cam_y). A ground circle of
// radius R is the ellipse x^2 + 4*y^2 = R^2 (half-width R, half-height R/2), see groundfx.h.

// 2:1 ellipse table, 32 steps (unit circle x256). Step 0 = east, step 8 = south on screen.
// Same values as the table in weapons.c, kept local so the two files stay independent.
static const int s_gfx_cos[32] = {
    256, 251, 237, 213, 181, 142, 98, 50, 0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50, 0, 50, 98, 142, 181, 213, 237, 251
};
static const int s_gfx_sin[32] = {
    0, 50, 98, 142, 181, 213, 237, 251, 256, 251, 237, 213, 181, 142, 98, 50,
    0, -50, -98, -142, -181, -213, -237, -251, -256, -251, -237, -213, -181, -142, -98, -50
};

// Integer square root (digit by digit, no division).
static int gfx_isqrt(int n) {
    if (n <= 0) return 0;
    uint32_t v = (uint32_t)n;
    uint32_t root = 0;
    uint32_t bit = 1u << 30;
    while (bit > v) bit >>= 2;
    while (bit != 0) {
        if (v >= root + bit) {
            v -= root + bit;
            root = (root >> 1) + bit;
        } else {
            root >>= 1;
        }
        bit >>= 2;
    }
    return (int)root;
}

// One decal pixel at screen point (sx, sy). Hidden by a wall in front: nothing is written.
// Depth of a floor pixel is its world y.
static void decal_put(const GroundTarget *g, int sx, int sy, uint16_t color) {
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    int wx = sx + g->cam_x;
    int wy = sy + g->cam_y;
    if (world_pixel_hidden(wx, wy, wy)) return;
    g->buffer[sy * SCREEN_W + sx] = (uint16_t)(color | BIT(15));
    dirty_row(sy, sx, sx + 1);
}

void gfx_ground_px(const GroundTarget *g, int wx, int wy, uint16_t color) {
    if (!g) return;
    decal_put(g, wx - g->cam_x, wy - g->cam_y, color);
}

// Dash state along the outline walk: `on` toggles every `dash` pixels (dash 0 = always on).
typedef struct {
    int dash;
    int run;
    int on;
} DashState;

static void dash_plot(const GroundTarget *g, int x, int y, uint16_t color, DashState *ds) {
    if (ds->on) gfx_ground_px(g, x, y, color);
    if (ds->dash > 0 && ++ds->run >= ds->dash) {
        ds->run = 0;
        ds->on = !ds->on;
    }
}

// Bresenham line in world space (Zingl form, error term with negative dy). When skip_first is set
// the start pixel is the end of the previous segment, which was already counted and drawn.
static void ground_line(const GroundTarget *g, int x0, int y0, int x1, int y1,
                        uint16_t color, DashState *ds, int skip_first) {
    int dx = x1 > x0 ? x1 - x0 : x0 - x1;
    int dy = -(y1 > y0 ? y1 - y0 : y0 - y1);
    int sx = x0 < x1 ? 1 : -1;
    int sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    int first = 1;
    for (;;) {
        if (!(first && skip_first)) dash_plot(g, x0, y0, color, ds);
        first = 0;
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// Walks the ellipse of radius r (32 chords, each joined by a line) and draws the chords whose
// start step lies in the window [a0, a0 + span) of 1/32 turns. span 32 = whole outline.
static void ring_walk(const GroundTarget *g, int cx, int cy, int r, uint16_t color,
                      int dash, int a0, int span) {
    if (r <= 0 || span <= 0) return;
    int px[32], py[32];
    for (int k = 0; k < 32; k++) {
        px[k] = cx + ((r * s_gfx_cos[k]) >> 8);
        py[k] = cy + ((r * s_gfx_sin[k]) >> 9);     // 2:1: vertical semi-axis r/2
    }
    DashState ds = { dash, 0, 1 };
    for (int k = 0; k < 32; k++) {
        if (((k - a0) & 31) >= span) continue;
        int prev_in = ((k - 1 - a0) & 31) < span;   // previous chord drew our start pixel
        int k1 = (k + 1) & 31;
        ground_line(g, px[k], py[k], px[k1], py[k1], color, &ds, prev_in);
    }
}

void gfx_ground_ring(const GroundTarget *g, int cx, int cy, int radius, uint16_t color, int dash) {
    if (!g) return;
    ring_walk(g, cx, cy, radius, color, dash, 0, 32);
}

void gfx_ground_arc(const GroundTarget *g, int cx, int cy, int radius, int a0, int a1,
                    uint16_t color, int thickness) {
    if (!g || radius <= 0 || thickness <= 0) return;
    int span = a1 - a0;
    if (span < 0) span += 32;
    if (span > 32) span = 32;
    a0 &= 31;
    for (int t = 0; t < thickness; t++) {
        int r = radius - t;                          // rings step inwards
        if (r <= 0) break;
        ring_walk(g, cx, cy, r, color, 0, a0, span);
    }
}

// Fast row fill, used when no wall hides any pixel of the span. Writes `val` on the pixels of
// [sx0, sx1] (inclusive) that the pattern keeps. wx0 is the world x of sx0. The pattern phase is
// carried in a counter (no % or / per pixel): CHECKER flips a parity bit, HATCH steps a 2-bit phase.
__attribute__((target("arm"), optimize("O3"), noinline))
static void disc_fill_row(uint16_t *row, int sx0, int sx1, uint16_t val,
                          int pattern, int wx0, int wy, int phase) {
    if (pattern == GFX_FILL_CHECKER) {
        int par = (wx0 + wy + phase) & 1;            // drawn when parity is 0
        for (int sx = sx0; sx <= sx1; sx++) {
            if (!par) row[sx] = val;
            par ^= 1;
        }
    } else if (pattern == GFX_FILL_HATCH) {
        int ph = (wx0 - wy + phase) & 3;             // drawn when phase is 0 or 1
        for (int sx = sx0; sx <= sx1; sx++) {
            if (ph < 2) row[sx] = val;
            ph = (ph + 1) & 3;
        }
    } else {
        for (int sx = sx0; sx <= sx1; sx++) row[sx] = val;
    }
}

// Slow row fill: the wall test is done per pixel. Only used on rows where a wall may hide something.
__attribute__((target("arm"), optimize("O3"), noinline))
static void disc_fill_row_walled(uint16_t *row, int sx0, int sx1, uint16_t val,
                                 int pattern, int cam_x, int wy, int phase) {
    for (int sx = sx0; sx <= sx1; sx++) {
        int wx = sx + cam_x;
        if (pattern == GFX_FILL_CHECKER && ((wx + wy + phase) & 1)) continue;
        if (pattern == GFX_FILL_HATCH && ((wx - wy + phase) & 3) >= 2) continue;
        if (world_pixel_hidden(wx, wy, wy)) continue;
        row[sx] = val;
    }
}

// Filled 2:1 ellipse. One span per row. The wall test is one world_span_hidden() query per row:
// a clear row takes the fast fill, a row with a wall in it takes the per-pixel path.
void gfx_ground_disc(const GroundTarget *g, int cx, int cy, int radius, uint16_t color,
                     int pattern, int phase) {
    if (!g || radius <= 0) return;
    int hh = radius >> 1;
    int r2 = radius * radius;
    uint16_t val = (uint16_t)(color | BIT(15));
    for (int dy = -hh; dy <= hh; dy++) {
        int wy = cy + dy;
        int sy = wy - g->cam_y;
        if ((unsigned)sy >= SCREEN_H) continue;
        int hw = gfx_isqrt(r2 - 4 * dy * dy);
        int sx0 = (cx - hw) - g->cam_x;
        int sx1 = (cx + hw) - g->cam_x;
        if (sx0 < 0) sx0 = 0;
        if (sx1 > SCREEN_W - 1) sx1 = SCREEN_W - 1;
        if (sx0 > sx1) continue;
        uint16_t *row = g->buffer + sy * SCREEN_W;
        if (world_span_hidden(wy, sx0 + g->cam_x, sx1 + g->cam_x + 1, wy)) {
            disc_fill_row_walled(row, sx0, sx1, val, pattern, g->cam_x, wy, phase);
        } else {
            disc_fill_row(row, sx0, sx1, val, pattern, sx0 + g->cam_x, wy, phase);
        }
        dirty_row(sy, sx0, sx1 + 1);
    }
}

// Light tables for one call: each entry is the channel already saturated and moved to its bit
// position, so a pixel is lit with three lookups and two ORs. Index = the 5-bit channel value.
typedef struct {
    uint16_t r[32];
    uint16_t g[32];
    uint16_t b[32];
} LightLut;

static void light_lut_build(LightLut *t, int level, int red_boost) {
    for (int c = 0; c < 32; c++) {
        int r = c + level + red_boost;
        if (r > 31) r = 31;
        int v = c + level;
        if (v > 31) v = 31;
        t->r[c] = (uint16_t)r;
        t->g[c] = (uint16_t)(v << 5);
        t->b[c] = (uint16_t)(v << 10);
    }
}

// Lights the opaque pixels of one row span [sx0, sx1] (inclusive). Transparent pixels and the
// two skip colours are left as they are.
__attribute__((target("arm"), optimize("O3"), noinline))
static void light_row(uint16_t *row, int sx0, int sx1, const LightLut *t,
                      uint16_t skip_a, uint16_t skip_b) {
    for (int sx = sx0; sx <= sx1; sx++) {
        uint16_t p = row[sx];
        if (!(p & BIT(15))) continue;
        if (p == skip_a || p == skip_b) continue;
        row[sx] = (uint16_t)(BIT(15) | t->r[p & 31] | t->g[(p >> 5) & 31] | t->b[(p >> 10) & 31]);
    }
}

// Beam: the body spans rows [cy - height, cy] at full radius; the caps are the lower half of the
// ellipse under cy and the upper half of the ellipse at cy - height. Only opaque actor pixels are
// lifted; floor decals (skip_a / skip_b) and transparent pixels are left alone. No wall test here.
// Opaque pixels always lie inside the row's dirty span, so each row is clipped to it.
void gfx_light_column(const GroundTarget *g, int cx, int cy, int radius, int height,
                      int level, int red_boost, uint16_t skip_a, uint16_t skip_b) {
    if (!g || radius <= 0) return;
    if (height < 0) height = 0;
    if (level < 0) level = 0;
    if (level > 31) level = 31;
    if (red_boost < 0) red_boost = 0;
    if (red_boost > 31) red_boost = 31;

    LightLut lut;
    light_lut_build(&lut, level, red_boost);

    int hh = radius >> 1;
    int r2 = radius * radius;
    int top = cy - height;
    for (int wy = top - hh; wy <= cy + hh; wy++) {
        int sy = wy - g->cam_y;
        if ((unsigned)sy >= SCREEN_H) continue;
        const DirtySpan *ds = &g_dirty_cur[sy];
        if (ds->x0 >= ds->x1) continue;              // nothing painted on this row
        int hw;
        if (wy < top) {
            int dy = wy - top;                       // upper cap, dy in [-hh, -1]
            hw = gfx_isqrt(r2 - 4 * dy * dy);
        } else if (wy <= cy) {
            hw = radius;                             // body
        } else {
            int dy = wy - cy;                        // lower cap, dy in [1, hh]
            hw = gfx_isqrt(r2 - 4 * dy * dy);
        }
        int sx0 = (cx - hw) - g->cam_x;
        int sx1 = (cx + hw) - g->cam_x;
        if (sx0 < 0) sx0 = 0;
        if (sx1 > SCREEN_W - 1) sx1 = SCREEN_W - 1;
        if (sx0 < (int)ds->x0) sx0 = (int)ds->x0;
        if (sx1 > (int)ds->x1 - 1) sx1 = (int)ds->x1 - 1;
        if (sx0 > sx1) continue;
        light_row(g->buffer + sy * SCREEN_W, sx0, sx1, &lut, skip_a, skip_b);
    }
}
