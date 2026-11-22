#include "campanero_fx.h"
#include "game.h"
#include "collision.h"
#include "groundfx.h"
#include "glifo.h"
#include "sfx.h"
#include <nds/arm9/math.h>
#include <string.h>

// Campanero de Animas rings (DESIGN-ARPG.md section 9). A ring is a 2:1 ground ellipse (x radius r, y radius r/2) that grows from the
// bell. TOQUE (major): wide cracked band with a fading trail, hurts, stopped by tall pieces: at birth the distance to the first tall
// piece is measured once per angle bin and the ring is neither drawn nor harmful beyond it. TANIDO (minor): thin faint crack, ignores
// pieces, silences the glyphs it crosses (glifo_silence).
// Look: same language as the glyph crack (irregular 1 px fissure, light on the leading edge, motes rising, a trail that fades behind),
// in the desaturated enemy green ramp (bone-phosphor, verdigris, moss, smoke). tests/test_guardrails.py watches this file.
#define CFX_BONE  RGB15(23, 26, 19)
#define CFX_VERD  RGB15(14, 21, 15)
#define CFX_MOSS  RGB15(9, 14, 10)
#define CFX_SMOKE RGB15(7, 9, 8)

#define CFX_MAX 6
#define CFX_BINS 128                 // angle bins of the shadow (ring samples are 256 per turn: 2 per bin)
#define CFX_BIN_SHIFT 1
#define CFX_R_MAX 640                // ground px: reaches the far end of the 2-screen room (boss near the top)
#define CFX_SPEED_TANIDO 4
#define CFX_SPEED_TOQUE 3
#define CFX_MARCH 6                  // px between tall-piece tests along a bin ray
#define CFX_HIT_BAND 4               // toque: +-px (ellipse metric) around the front that hurt

typedef struct {
    uint8_t active, kind, seed;
    int ox, oy;
    int r, rprev;
    int8_t nz[CFX_BINS];             // crack wobble: value noise along the ring, -3..3 px
    uint16_t blk[CFX_BINS];          // toque: ground distance at which a tall piece stops the bin
} Ring;

static Ring s_ring[CFX_MAX];
volatile struct { int16_t ox, oy; uint16_t silenced; uint16_t blk[CFX_BINS]; } g_cfx_dbg;   // last major toll's shadow (read by scenarios)
#if CFX_TEST
// Test bell (variant cfx-test): a fixed floor point of the first strip window (nave 1), between two statue pairs (tall pieces at
// world (223, 1100) (303, 1100) to its north and (172, 1216) (332, 1216) to its south): a toque casts a shadow behind each statue.
#define CFX_TEST_X 263
#define CFX_TEST_Y 1135
static int s_test_t, s_test_dy;
#endif

// cos(i / 256 turn) * 256; sin(i) = cos(i - 64).
static const int16_t k_cos[256] = {
    256, 256, 256, 255, 255, 254, 253, 252, 251, 250, 248, 247, 245, 243, 241, 239, 237, 234, 231, 229, 226, 223, 220, 216, 213, 209,
    206, 202, 198, 194, 190, 185, 181, 177, 172, 167, 162, 157, 152, 147, 142, 137, 132, 126, 121, 115, 109, 104, 98, 92, 86, 80, 74,
    68, 62, 56, 50, 44, 38, 31, 25, 19, 13, 6, 0, -6, -13, -19, -25, -31, -38, -44, -50, -56, -62, -68, -74, -80, -86, -92, -98, -104,
    -109, -115, -121, -126, -132, -137, -142, -147, -152, -157, -162, -167, -172, -177, -181, -185, -190, -194, -198, -202, -206, -209,
    -213, -216, -220, -223, -226, -229, -231, -234, -237, -239, -241, -243, -245, -247, -248, -250, -251, -252, -253, -254, -255, -255,
    -256, -256, -256, -256, -256, -255, -255, -254, -253, -252, -251, -250, -248, -247, -245, -243, -241, -239, -237, -234, -231, -229,
    -226, -223, -220, -216, -213, -209, -206, -202, -198, -194, -190, -185, -181, -177, -172, -167, -162, -157, -152, -147, -142, -137,
    -132, -126, -121, -115, -109, -104, -98, -92, -86, -80, -74, -68, -62, -56, -50, -44, -38, -31, -25, -19, -13, -6, 0, 6, 13, 19,
    25, 31, 38, 44, 50, 56, 62, 68, 74, 80, 86, 92, 98, 104, 109, 115, 121, 126, 132, 137, 142, 147, 152, 157, 162, 167, 172, 177, 181,
    185, 190, 194, 198, 202, 206, 209, 213, 216, 220, 223, 226, 229, 231, 234, 237, 239, 241, 243, 245, 247, 248, 250, 251, 252, 253,
    254, 255, 255, 256, 256
};
static const uint8_t k_atan[33] = { 0, 1, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 25, 26, 27, 28,
                                    29, 29, 30, 31, 31, 32 };      // atan(q / 32) in 1/256 turns
#define COS_AT(i) k_cos[(i) & 255]
#define SIN_AT(i) k_cos[((i) + 192) & 255]

static uint32_t hash2(uint32_t a, uint32_t b) {
    uint32_t v = a * 73856093u ^ b * 19349663u;
    v = (v ^ (v >> 13)) * 1274126177u;
    return v ^ (v >> 16);
}

// Angle (1/256 turn) of a GROUND vector (screen y already doubled): the inverse of COS_AT / SIN_AT.
static int angle256(int gx, int gy) {
    const int ax = gx < 0 ? -gx : gx, ay = gy < 0 ? -gy : gy;
    if (!ax && !ay) return 0;
    int a;
    if (ay <= ax) a = k_atan[div32(ay * 32 + (ax >> 1), ax)];
    else a = 64 - k_atan[div32(ax * 32 + (ay >> 1), ay)];
    if (gx < 0) a = 128 - a;
    if (gy < 0) a = 256 - a;
    return a & 255;
}

void cfx_reset(void) {
    for (int i = 0; i < CFX_MAX; i++) s_ring[i].active = 0;
#if CFX_TEST
    s_test_t = 0;
    s_test_dy = 0;
#endif
}

void cfx_shift_y(int dy_px) {
#if CFX_TEST
    s_test_dy += dy_px;
#endif
    for (int i = 0; i < CFX_MAX; i++)
        if (s_ring[i].active) s_ring[i].oy += dy_px;
}

// Toque shadow: per bin, the first ground distance where a tall piece (collision value 3: walls, columns, statues, the same
// test that stops the Ojo's beam and shots) lies on the ray; refined by bisection below the march step.
static void build_shadow(Ring *g) {
    for (int b = 0; b < CFX_BINS; b++) {
        const int ang = (b << CFX_BIN_SHIFT) + 1;       // bin centre
        const int c = COS_AT(ang), s = SIN_AT(ang);
        int lo = 0, hi = 0;
        for (int d = CFX_MARCH; d <= CFX_R_MAX; d += CFX_MARCH) {
            const int x = g->ox + ((d * c) >> 8), y = g->oy + ((d * s) >> 9);
            if (!bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) { hi = d; break; }
            lo = d;
        }
        if (!hi) { g->blk[b] = 0xFFFF; continue; }
        while (hi - lo > 1) {
            const int m = (lo + hi) >> 1;
            const int x = g->ox + ((m * c) >> 8), y = g->oy + ((m * s) >> 9);
            if (bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) lo = m; else hi = m;
        }
        g->blk[b] = (uint16_t)lo;
    }
}

void cfx_emit(int kind, int ox, int oy) {
    int slot = 0, far = -1;
    for (int i = 0; i < CFX_MAX; i++) {                 // free slot, else the oldest ring
        if (!s_ring[i].active) { slot = i; break; }
        if (s_ring[i].r > far) { far = s_ring[i].r; slot = i; }
    }
    Ring *g = &s_ring[slot];
    static uint8_t s_seed = 17;
    s_seed = (uint8_t)(s_seed * 41u + 7u);
    g->active = 1;
    g->kind = (uint8_t)kind;
    g->seed = s_seed;
    g->ox = ox; g->oy = oy;
    g->r = 0; g->rprev = 0;
    const int amp = kind == CFX_TOQUE ? 7 : 5;
    for (int b = 0; b < CFX_BINS; b++) g->nz[b] = (int8_t)((int)(hash2((uint32_t)b, g->seed) % (uint32_t)amp) - amp / 2);
    if (kind == CFX_TOQUE) {
        build_shadow(g);
        g_cfx_dbg.ox = (int16_t)ox; g_cfx_dbg.oy = (int16_t)oy;
        for (int b = 0; b < CFX_BINS; b++) g_cfx_dbg.blk[b] = g->blk[b];
        sfx_play(SND_CFX_BONG, ox);
        sfx_play(SND_CFX_BELL_LOW, ox);
    } else {
        for (int b = 0; b < CFX_BINS; b++) g->blk[b] = 0xFFFF;
        sfx_play(SND_CFX_TANIDO, ox);
    }
}

void cfx_update(void) {
#if CFX_TEST
    {   // test hook: a bell standing at a fixed floor point
        const int t = s_test_t++;
        if (t % 60 == 30) cfx_emit(CFX_TANIDO, CFX_TEST_X, CFX_TEST_Y + s_test_dy);
        if (t % 210 == 100) cfx_emit(CFX_TOQUE, CFX_TEST_X, CFX_TEST_Y + s_test_dy);
    }
#endif
    for (int i = 0; i < CFX_MAX; i++) {
        Ring *g = &s_ring[i];
        if (!g->active) continue;
        g->rprev = g->r;
        g->r += g->kind == CFX_TOQUE ? CFX_SPEED_TOQUE : CFX_SPEED_TANIDO;
        if (g->r >= CFX_R_MAX) { g->active = 0; continue; }
        if (g->kind != CFX_TANIDO) continue;
        // The wave reaches a glyph when its front touches the rune's near edge (the silencing sweep starts there).
        for (int z = 0, n = glifo_zone_count(); z < n; z++) {
            int cx, cy, rad;
            if (!glifo_silenceable(z, &cx, &cy, &rad)) continue;
            const int dx = cx - g->ox, dy2 = (cy - g->oy) * 2;
            const int d = (int)sqrt32((unsigned)(dx * dx + dy2 * dy2));
            if (g->r >= d - rad && g->rprev < d + rad) { glifo_silence(z, g->ox, g->oy); g_cfx_dbg.silenced++; }
        }
    }
}

int cfx_toque_hit(int x, int y) {
    for (int i = 0; i < CFX_MAX; i++) {
        const Ring *g = &s_ring[i];
        if (!g->active || g->kind != CFX_TOQUE) continue;
        const int dx = x - g->ox, dy2 = (y - g->oy) * 2;
        const int d = (int)sqrt32((unsigned)(dx * dx + dy2 * dy2));
        if (d < g->r - CFX_HIT_BAND || d > g->r + CFX_HIT_BAND) continue;
        if (d > (int)g->blk[angle256(dx, dy2) >> CFX_BIN_SHIFT]) continue;     // in the shadow of a tall piece
        return 1;
    }
    return 0;
}

// ---------------------------------------------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------------------------------------------
static uint16_t *r_buf;
static int r_camx, r_camy;
static int8_t r_row[SCREEN_H];          // per screen row: -1 unknown, 0 clear, 1 a wall may hide something
static int r_cell = -1, r_cell_ok;      // memo of the last collision cell tested

static inline void put(int wx, int wy, uint16_t col) {
    const int sx = wx - r_camx, sy = wy - r_camy;
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    const int cell = (wy >> 2) * 4096 + (wx >> 2);
    if (cell != r_cell) { r_cell = cell; r_cell_ok = ground_point_is_free(wx, wy); }
    if (!r_cell_ok) return;
    int h = r_row[sy];
    if (h < 0) { h = world_span_hidden(wy, r_camx, r_camx + SCREEN_W, wy) ? 1 : 0; r_row[sy] = (int8_t)h; }
    if (h && world_pixel_hidden(wx, wy, wy)) return;
    r_buf[sy * SCREEN_W + sx] = (uint16_t)(col | BIT(15));
    dirty_row(sy, sx, sx + 1);
}

static void put_line(int x0, int y0, int x1, int y1, uint16_t col) {
    const int dx = x1 > x0 ? x1 - x0 : x0 - x1, dy = y1 > y0 ? y0 - y1 : y1 - y0;   // dy <= 0
    const int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (;;) {
        put(x0, y0, col);
        if (x0 == x1 && y0 == y1) break;
        const int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// Crack wobble at sample i (0..255): value noise between two neighbouring bins.
static inline int wobble(const Ring *g, int i) {
    const int b = (i >> CFX_BIN_SHIFT) & (CFX_BINS - 1), f = i & 1;
    return f ? (g->nz[b] + g->nz[(b + 1) & (CFX_BINS - 1)]) >> 1 : g->nz[b];
}

static inline void ring_pt(const Ring *g, int rad, int i, int *x, int *y) {
    *x = g->ox + ((rad * COS_AT(i)) >> 8);
    *y = g->oy + ((rad * SIN_AT(i)) >> 9);
}

static inline int off_screen(int x0, int y0, int x1, int y1) {
    const int a = x0 - r_camx, b = y0 - r_camy, c = x1 - r_camx, d = y1 - r_camy;
    return (a < 0 && c < 0) || (a >= SCREEN_W && c >= SCREEN_W) || (b < 0 && d < 0) || (b >= SCREEN_H && d >= SCREEN_H);
}

static void draw_ring(const Ring *g) {
    const int toque = g->kind == CFX_TOQUE;
    const int r = g->r;
    // The whole screen lies behind the trail: nothing to draw.
    {
        const int reach = r - 72;
        if (reach > 0) {
            int inside = 1;
            for (int c = 0; c < 4 && inside; c++) {
                const int dx = r_camx + ((c & 1) ? SCREEN_W : 0) - g->ox, dy2 = (r_camy + ((c & 2) ? SCREEN_H : 0) - g->oy) * 2;
                if (dx * dx + dy2 * dy2 >= reach * reach) inside = 0;
            }
            if (inside) return;
        }
    }
    // Trail: dots on rings behind the front, sparser and darker the older they are (they stay where the front already crossed).
    {
        const int kmax = toque ? 22 : 12, kstep = toque ? 2 : 3;
        for (int k = toque ? 3 : 2; k <= kmax; k += kstep) {
            const int rad = r - k;
            if (rad <= 0) break;
            const int top = toque ? 12 : 6;
            const int dens = top - (k * top) / (kmax + 2);
            const uint16_t col = k < (toque ? 8 : 5) ? CFX_VERD : k < (toque ? 15 : 9) ? CFX_MOSS : CFX_SMOKE;
            for (int i = 0; i < 256; i += 2) {
                if ((int)(hash2((uint32_t)i * 3u + (uint32_t)k, g->seed) & 15u) >= dens) continue;
                if (rad > (int)g->blk[i >> CFX_BIN_SHIFT]) continue;
                int x, y;
                ring_pt(g, rad + wobble(g, i), i, &x, &y);
                put(x, y, col);
            }
        }
    }
    // Front: the fissure. Toque = two px wide and bone-bright; tanido = one px, faint, in dashes.
    {
        int px0 = 0, py0 = 0, have = 0;
        for (int i = 0; i <= 256; i++) {
            const int ii = i & 255;
            if (r > (int)g->blk[ii >> CFX_BIN_SHIFT]) { have = 0; continue; }
            int x, y;
            ring_pt(g, r + wobble(g, ii), ii, &x, &y);
            if (have && !off_screen(px0, py0, x, y)) {
                if (toque) {
                    put_line(px0, py0, x, y, CFX_BONE);
                    put_line(px0, py0 + 1, x, y + 1, CFX_VERD);
                } else if (!((ii >> 3) & 1)) {
                    put_line(px0, py0, x, y, ((ii >> 1) & 1) ? CFX_MOSS : CFX_VERD);
                }
            }
            px0 = x; py0 = y; have = 1;
        }
    }
    // Spurs: short cracks that branch off the front into the trail.
    for (int i = 0; i < 256; i += 8) {
        const uint32_t h = hash2((uint32_t)i, g->seed ^ 0x5Au);
        if ((h & 3u) != 0u || r > (int)g->blk[i >> CFX_BIN_SHIFT]) continue;
        const int len = (toque ? 4 : 2) + (int)((h >> 4) & 3u);
        const int side = (h & 0x100u) ? 1 : -1;
        int x, y;
        ring_pt(g, r + wobble(g, i), i, &x, &y);
        for (int s = 1; s <= len; s++) put(x - ((COS_AT(i) * s) >> 8) + side * (s >> 1), y - ((SIN_AT(i) * s) >> 9), s < 3 ? CFX_VERD : CFX_MOSS);
    }
    // Motes: born on the crack as the front passes, they rise and fade (stateless: the ring radius is the clock).
    {
        const int n = toque ? 64 : 14, life = toque ? 22 : 14;
        for (int m = 0; m < n; m++) {
            const uint32_t h = hash2((uint32_t)m, g->seed ^ 0xA5u);
            const int rb = (int)((((h >> 8) & 0xFFFFu) * CFX_R_MAX) >> 16);       // radius at which this mote is born
            if (rb > r) continue;
            const int age = toque ? (((r - rb) * 85) >> 8) : ((r - rb) >> 2);
            if (age >= life) continue;
            const int ang = (int)(h & 255u);
            if (rb > (int)g->blk[ang >> CFX_BIN_SHIFT]) continue;
            int x, y;
            ring_pt(g, rb + wobble(g, ang), ang, &x, &y);
            x += COS_AT(age * 9 + m * 31) >> 8;
            y -= (age * 3) >> 2;
            const uint16_t col = age < life / 4 ? CFX_BONE : age < life / 2 ? CFX_VERD : age < life * 3 / 4 ? CFX_MOSS : CFX_SMOKE;
            put(x, y, col);
            if (toque && age < life / 3) put(x, y - 1, CFX_VERD);
        }
    }
}

void cfx_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    int any = 0;
    for (int i = 0; i < CFX_MAX; i++) if (s_ring[i].active) { any = 1; break; }
    if (!any) return;
    r_buf = buffer; r_camx = cam_x; r_camy = cam_y;
    memset(r_row, -1, sizeof(r_row));
    r_cell = -1;
    for (int i = 0; i < CFX_MAX; i++)
        if (s_ring[i].active) draw_ring(&s_ring[i]);
}
