#include "campanero_fx.h"
#include "game.h"
#include "collision.h"
#include "groundfx.h"
#include "glifo.h"
#include "sfx.h"
#include "cfxprof.h"
#include <nds/arm9/math.h>
#include <string.h>

// Campanero de Animas rings (DESIGN-ARPG.md section 9). A ring is a 2:1 ground ellipse (x radius r, y radius r/2) that grows from the
// bell. TOQUE (major): wide cracked band with a fading trail, hurts, stopped by tall pieces: at birth the distance to the first tall
// piece is measured once per angle bin and the ring is neither drawn nor harmful beyond it. TANIDO (minor): thin faint crack, ignores
// pieces, silences the glyphs it crosses (glifo_silence).
// The cut is marked: where the toque front meets a piece it rebounds (sparks + a short arc running back to the bell), and at the
// shadow edge the two loose ends of the front curl into the shadow with flickering sparks (the shadow itself is not drawn: the wave simply does not arrive there).
// Look: same language as the glyph crack (irregular 1 px fissure, light on the leading edge, motes rising, a trail that fades behind),
// in the desaturated enemy green ramp (bone-phosphor, verdigris, moss, smoke). tests/test_guardrails.py watches this file.
#define CFX_BONE  RGB15(23, 26, 19)
#define CFX_VERD  RGB15(14, 21, 15)
#define CFX_MOSS  RGB15(9, 14, 10)
#define CFX_SMOKE RGB15(7, 9, 8)
#define CFX_ASH   RGB15(15, 15, 13)   // tanido: dull bone grey, so it never reads as the green wave that hurts

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
    uint16_t blk[CFX_BINS];          // toque: ground distance at which a tall piece stops the bin (0xFFFF: not found yet / never)
    uint16_t mlo[CFX_BINS];          // toque: farthest distance already marched free along the bin ray
    uint16_t mto;                    // toque: distance every bin is marched to (grows each frame, always ahead of the ring)
} Ring;

static Ring s_ring[CFX_MAX];
static int s_sq_n;                       // pending sounds (see cfx_sfx_later)
#if CFX_PROF
volatile CfxProf g_cfxp;
#endif
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
    s_sq_n = 0;
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
// test that stops the Ojo's beam and shots) lies on the ray; refined by bisection below the march step. Incremental: every frame
// each bin is marched a few steps farther (CFX_MARCH_PER_FRAME), far ahead of the ring (which only reads blk at distances <= r),
// so the cost of the whole shadow is spread over ~27 frames instead of landing on the frame of the toll.
#define CFX_MARCH_PER_FRAME (4 * CFX_MARCH)
static Ring *s_dbg_ring;
// Sound queue: starting a sound (mmEffectEx) costs far more than any other single call of the fight (measured with scenarios/arpg_campanero_prof.json), so the boss never starts two in the same frame: the toll's strike, hum and the raised Exvotos' sounds are spaced.
#define CFX_SQ_MAX 8
static struct { int16_t id, x; int8_t wait; } s_sq[CFX_SQ_MAX];
void cfx_sfx_later(int sfx_id, int world_x, int delay) {
    if (s_sq_n >= CFX_SQ_MAX) return;
    s_sq[s_sq_n].id = (int16_t)sfx_id; s_sq[s_sq_n].x = (int16_t)world_x; s_sq[s_sq_n].wait = (int8_t)delay;
    s_sq_n++;
}
static void sq_step(void) {
    int played = 0;
    for (int i = 0; i < s_sq_n; ) {
        if (s_sq[i].wait > 0) s_sq[i].wait--;
        if (s_sq[i].wait <= 0 && !played) {
            played = 1;
            sfx_play(s_sq[i].id, s_sq[i].x);
            s_sq[i] = s_sq[--s_sq_n];
            continue;
        }
        i++;
    }
}

static void march_shadow(Ring *g) {
    if (g->mto >= CFX_R_MAX) return;
    CP_BEGIN(CP_MARCH);
    g->mto = (uint16_t)(g->mto + CFX_MARCH_PER_FRAME);
    const int to = g->mto < CFX_R_MAX ? g->mto : CFX_R_MAX;
    for (int b = 0; b < CFX_BINS; b++) {
        if (g->blk[b] != 0xFFFF) continue;
        const int ang = (b << CFX_BIN_SHIFT) + 1;       // bin centre
        const int c = COS_AT(ang), s = SIN_AT(ang);
        int lo = g->mlo[b], hi = 0;
        for (int d = lo + CFX_MARCH; d <= to; d += CFX_MARCH) {
            const int x = g->ox + ((d * c) >> 8), y = g->oy + ((d * s) >> 9);
            if (!bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) { hi = d; break; }
            lo = d;
        }
        if (!hi) { g->mlo[b] = (uint16_t)lo; continue; }
        while (hi - lo > 1) {
            const int m = (lo + hi) >> 1;
            const int x = g->ox + ((m * c) >> 8), y = g->oy + ((m * s) >> 9);
            if (bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) lo = m; else hi = m;
        }
        g->blk[b] = (uint16_t)lo;
        if (g == s_dbg_ring) g_cfx_dbg.blk[b] = (uint16_t)lo;
    }
    CP_END(CP_MARCH);
}

void cfx_emit(int kind, int ox, int oy) {
    CP_BEGIN(CP_EMIT);
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
    CP_BEGIN(CP_NZ);
    for (int b = 0; b < CFX_BINS; b++) g->nz[b] = (int8_t)((int)(((hash2((uint32_t)b, g->seed) >> 8) * (uint32_t)amp) >> 24) - amp / 2);
    CP_END(CP_NZ);
    if (kind == CFX_TOQUE) {
        for (int b = 0; b < CFX_BINS; b++) { g->blk[b] = 0xFFFF; g->mlo[b] = 0; g_cfx_dbg.blk[b] = 0xFFFF; }
        g->mto = 0;
        s_dbg_ring = g;
        g_cfx_dbg.ox = (int16_t)ox; g_cfx_dbg.oy = (int16_t)oy;
        cfx_sfx_later(SND_CFX_BONG, ox, 0);
        cfx_sfx_later(SND_CFX_BELL_LOW, ox, 2);
    } else {
        for (int b = 0; b < CFX_BINS; b++) g->blk[b] = 0xFFFF;
        cfx_sfx_later(SND_CFX_TANIDO, ox, 0);
    }
    CP_END(CP_EMIT);
}

void cfx_update(void) {
    CP_BEGIN(CP_UPDATE);
    { CP_BEGIN(CP_SFX); sq_step(); CP_END(CP_SFX); }
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
        if (g->kind == CFX_TOQUE) march_shadow(g);
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
    CP_END(CP_UPDATE);
}

int cfx_toque_hit(int x, int y) {
    CP_BEGIN(CP_HIT);
    for (int i = 0; i < CFX_MAX; i++) {
        const Ring *g = &s_ring[i];
        if (!g->active || g->kind != CFX_TOQUE) continue;
        const int dx = x - g->ox, dy2 = (y - g->oy) * 2;
        const int d = (int)sqrt32((unsigned)(dx * dx + dy2 * dy2));
        if (d < g->r - CFX_HIT_BAND || d > g->r + CFX_HIT_BAND) continue;
        if (d > (int)g->blk[angle256(dx, dy2) >> CFX_BIN_SHIFT]) continue;     // in the shadow of a tall piece
        CP_END(CP_HIT);
        return 1;
    }
    CP_END(CP_HIT);
    return 0;
}

// ---------------------------------------------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------------------------------------------
static uint16_t *r_buf;
static int r_camx, r_camy, r_cxs, r_cys;
static int8_t r_row[SCREEN_H];          // per screen row: -1 unknown, 0 clear, 1 a wall may hide something
#define CELL_W (SCREEN_W / 4 + 2)
#define CELL_H (SCREEN_H / 4 + 2)
static uint8_t r_cell[CELL_W * CELL_H]; // per 4x4 world cell on screen: 0 unknown, 1 free floor, 2 blocked (memo for the frame)
#define HCELL_W (SCREEN_W / 2 + 2)
#define HCELL_H (SCREEN_H / 2 + 2)
static uint8_t r_hid[HCELL_W * HCELL_H]; // per 2x2 world cell: 0 unknown, 1 visible, 2 hidden behind a wall (memo for the frame)
static uint16_t r_hgen[HCELL_H];             // frame stamp of each r_hid row: a row is cleared the first time a frame touches it (not 12 KB every frame)
static uint16_t s_gen;
static uint16_t r_dx0[SCREEN_H], r_dx1[SCREEN_H];   // painted span per row, flushed to dirty_row once at the end

__attribute__((target("arm"), optimize("O3"), noinline)) ITCM_CODE static void put_impl(int wx, int wy, uint16_t col) {
    CP_COUNT_INC(CP_PUT);
    const int sx = wx - r_camx, sy = wy - r_camy;
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    CP_COUNT_INC(CP_PUT_IN);
    uint8_t *cp = &r_cell[((sy + r_cys) >> 2) * CELL_W + ((sx + r_cxs) >> 2)];
    int ok = *cp;
    if (!ok) { CP_COUNT_INC(CP_GPIF); { CP_BEGIN_F(CP_TGPIF); ok = ground_point_is_free(wx, wy) ? 1 : 2; CP_END_F(CP_TGPIF); } *cp = (uint8_t)ok; }
    if (ok != 1) return;
    int h = r_row[sy];
    if (h < 0) { CP_COUNT_INC(CP_WSH); { CP_BEGIN_F(CP_TWSH); h = world_span_hidden(wy, r_camx, r_camx + SCREEN_W, wy) ? 1 : 0; CP_END_F(CP_TWSH); } r_row[sy] = (int8_t)h; }
    if (h) {
        const int hr = (sy + r_cys) >> 1;
        if (r_hgen[hr] != s_gen) { memset(&r_hid[hr * HCELL_W], 0, HCELL_W); r_hgen[hr] = s_gen; }
        uint8_t *hp = &r_hid[hr * HCELL_W + ((sx + r_cxs) >> 1)];
        int v = *hp;
        if (!v) { CP_COUNT_INC(CP_WPH); { CP_BEGIN_F(CP_TWPH); v = world_pixel_hidden(wx, wy, wy) ? 2 : 1; CP_END_F(CP_TWPH); } *hp = (uint8_t)v; }
        if (v == 2) return;
    }
    r_buf[sy * SCREEN_W + sx] = (uint16_t)(col | BIT(15));
    if (sx < (int)r_dx0[sy]) r_dx0[sy] = (uint16_t)sx;
    if (sx >= (int)r_dx1[sy]) r_dx1[sy] = (uint16_t)(sx + 1);
}

#if CFX_PROF && CFX_PROF_FINE
static inline void put(int wx, int wy, uint16_t col) { CP_BEGIN(CP_PUTT); put_impl(wx, wy, col); CP_END(CP_PUTT); }
#else
#define put put_impl
#endif

// Line; colb (when not 0xFFFF) is also drawn one pixel below every pixel of the line.
__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void put_line2(int x0, int y0, int x1, int y1, uint16_t col, uint16_t colb) {
    const int dx = x1 > x0 ? x1 - x0 : x0 - x1, dy = y1 > y0 ? y0 - y1 : y1 - y0;   // dy <= 0
    const int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (;;) {
        put(x0, y0, col);
        if (colb != 0xFFFF) put(x0, y0 + 1, colb);
        if (x0 == x1 && y0 == y1) break;
        const int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}
static inline void put_line(int x0, int y0, int x1, int y1, uint16_t col) { put_line2(x0, y0, x1, y1, col, 0xFFFF); }

static uint8_t s_noise[256];            // 0..15, replaces a hash per trail dot
static uint8_t s_noise_ok;

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

// Marked cut of the toque (stateless: r - blk is the clock of each rebound, the ring radius is the clock of the curled ends).
static inline int cut_blocked(const Ring *g, int b) { return (int)g->blk[b] < CFX_R_MAX && (int)g->blk[b] > 0; }

// One rebound per contiguous run of blocked bins: a solid crack hugging the piece's base and a splash of sparks thrown sideways and
// toward the camera from the middle of the run.
static void draw_rebound(const Ring *g, int b0, int b1, int run) {
    const int r = g->r;
    for (int i = b0 * 2 - 3; i < b1 * 2 + 4; i++) {                      // arc: the run plus ~6 px beyond both shadow edges
        int ba = i >> CFX_BIN_SHIFT, bb = (i + 1) >> CFX_BIN_SHIFT;
        ba = ba < b0 ? b0 : ba > b1 ? b1 : ba;
        bb = bb < b0 ? b0 : bb > b1 ? b1 : bb;
        const int ua = r - (int)g->blk[ba], ub = r - (int)g->blk[bb];
        if (ua < 0 || ub < 0 || ua >= 36 || ub >= 36) continue;
        const int da = ua >> 3, db = ub >> 3;                              // drifts back toward the bell, 0..4 px
        int xa, ya, xb, yb;
        ring_pt(g, (int)g->blk[ba] - 1 - da, i, &xa, &ya);
        ring_pt(g, (int)g->blk[bb] - 1 - db, i + 1, &xb, &yb);
        if (off_screen(xa, ya, xb, yb)) continue;
        put_line(xa, ya, xb, yb, ua < 16 ? CFX_BONE : CFX_VERD);
    }
    const int m = (b0 + b1) >> 1, bk = (int)g->blk[m], u = r - bk;
    if (u < 0 || u >= 36) return;
    const int age = (u * 85) >> 8;                                         // 0..11
    const int ang = m * 2 + 1;
    int px, py;
    ring_pt(g, bk - 1, ang, &px, &py);
    py += 8;                                                               // out of the piece's sprite footprint, toward the camera
    const int cx = -COS_AT(ang), cy = SIN_AT(ang) < 0 ? -SIN_AT(ang) : SIN_AT(ang);     // reflection, mirrored down-screen
    const int ac = angle256(cx, cy * 2);
    for (int j = 0; j < 12; j++) {
        const uint32_t h = hash2((uint32_t)(run * 16 + j), g->seed ^ 0x77u);
        const int a = ac + (int)(((h & 127u) * 85u) >> 7) - 42;             // fan of ~120 degrees
        const int t = age - (int)((h >> 20) & 3u);
        if (t < 0) continue;
        const int dist = ((t * (7 + (int)((h >> 8) & 3u))) >> 1) + 6;
        const uint16_t col = t < 4 ? CFX_BONE : t < 8 ? CFX_VERD : CFX_MOSS;
        for (int k = 0; k < 3; k++) {                                       // streak of 3 px, head first
            const int d = dist - k;
            if (d < 0) break;
            put(px + ((COS_AT(a) * d) >> 8), py + ((SIN_AT(a) * d) >> 8) + ((t * t) >> 5), col);
        }
    }
}

static void draw_cut(const Ring *g) {
    const int r = g->r;
    int run = 0;
    for (int b = 0; b < CFX_BINS; b++) {
        if (!cut_blocked(g, b)) continue;
        int e = b;
        while (e + 1 < CFX_BINS && cut_blocked(g, e + 1) && (int)g->blk[e + 1] - (int)g->blk[e] < 12 && (int)g->blk[e] - (int)g->blk[e + 1] < 12) e++;
        draw_rebound(g, b, e, run++);
        b = e;
    }
    // Curled ends: an open bin whose neighbour is already in shadow; the loose end of the front hooks into the shadow.
    for (int b = 0; b < CFX_BINS; b++) {
        if (r > (int)g->blk[b]) continue;
        for (int side = -1; side <= 1; side += 2) {
            const int nb = (b + side) & (CFX_BINS - 1);
            if (r <= (int)g->blk[nb]) continue;
            const int i = b * 2 + (side > 0 ? 1 : 0);
            int x, y;
            ring_pt(g, r + wobble(g, i), i, &x, &y);
            const int c = COS_AT(i), sn = SIN_AT(i);
            int tx = x, ty = y;
            for (int k = 1; k <= 8; k++) {                              // hook: 2 px thick, along the front into the shadow, curling back
                const int curl = (k * k) >> 2;
                tx = x + side * ((-sn * (k - 3)) >> 8) - ((c * curl) >> 8);          // starts 2 px before the cut, on open floor
                ty = y + side * ((c * (k - 3)) >> 9) - ((sn * curl) >> 9);
                put(tx, ty, k <= 2 ? CFX_BONE : k <= 5 ? CFX_VERD : CFX_BONE);
                put(tx, ty + 1, k <= 5 ? CFX_MOSS : CFX_VERD);
            }
            for (int f = 0; f < 4; f++) {                               // spark burst at the tip, new every frame
                const uint32_t h = hash2((uint32_t)(r * 7 + f), g->seed ^ (uint32_t)(b * 5 + 3));
                put(tx + (int)(h & 7u) - 3, ty + (int)((h >> 4) & 7u) - 4, (h & 0x100u) ? CFX_BONE : CFX_VERD);
            }
        }
    }
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
    // The ring has not reached the screen yet (nearest screen point farther than the ring plus the reach of sparks): nothing to draw.
    {
        const int nx = (g->ox < r_camx ? r_camx : g->ox > r_camx + SCREEN_W ? r_camx + SCREEN_W : g->ox) - g->ox;
        const int ny = ((g->oy < r_camy ? r_camy : g->oy > r_camy + SCREEN_H ? r_camy + SCREEN_H : g->oy) - g->oy) * 2;
        const int reach = r + 72;
        if (nx * nx + ny * ny > reach * reach) return;
    }
    CP_BEGIN(CP_PRE);
    // The front, sampled every 2/256 turn (the odd samples lie on the chord): point j is angle 2j, bin j. vis: within 24 px of the
    // screen, which also bounds the trail and the glow (they lie at most 22 px behind the front).
    int16_t fx[CFX_BINS + 1], fy[CFX_BINS + 1];
    uint8_t valid[CFX_BINS + 1], vis[CFX_BINS + 1];
    for (int j = 0; j < CFX_BINS; j++) {
        valid[j] = r <= (int)g->blk[j];
        vis[j] = 0;
        if (!valid[j]) continue;
        int x, y;
        ring_pt(g, r + wobble(g, j * 2), j * 2, &x, &y);
        fx[j] = (int16_t)x; fy[j] = (int16_t)y;
        vis[j] = (unsigned)(x - r_camx + 24) < SCREEN_W + 48 && (unsigned)(y - r_camy + 24) < SCREEN_H + 48;
    }
    valid[CFX_BINS] = valid[0]; vis[CFX_BINS] = vis[0]; fx[CFX_BINS] = fx[0]; fy[CFX_BINS] = fy[0];
    CP_END(CP_PRE);
    if (!toque) {                       // tanido (harmless): a thin dashed grey ring only, no trail, spurs or motes
        CP_BEGIN(CP_FRONT);
        for (int j = 1; j <= CFX_BINS; j++) {
            if (((j >> 2) & 1) || !(valid[j - 1] && valid[j]) || !(vis[j - 1] | vis[j])) continue;
            if (off_screen(fx[j - 1], fy[j - 1], fx[j], fy[j])) continue;
            put_line(fx[j - 1], fy[j - 1], fx[j], fy[j], CFX_ASH);
        }
        CP_END(CP_FRONT);
        return;
    }
    CP_BEGIN(CP_TRAIL);
    // Trail: dots on rings behind the front, sparser and darker the older they are (they stay where the front already crossed).
    {
        const int kmax = toque ? 22 : 12, kstep = toque ? 4 : 3;
        for (int k = toque ? 3 : 2; k <= kmax; k += kstep) {
            const int rad = r - k;
            if (rad <= 0) break;
            const int top = toque ? 18 : 6;
            const int dens = top - (k * top) / (kmax + 2);
            const uint16_t col = k < (toque ? 8 : 5) ? CFX_VERD : k < (toque ? 15 : 9) ? CFX_MOSS : CFX_SMOKE;
            const int nbase = k * 41 + g->seed;
            for (int j = 0; j < CFX_BINS; j++) {
                if (!vis[j]) continue;
                if ((int)s_noise[(j * 5 + nbase) & 255] >= dens) continue;
                if (rad > (int)g->blk[j]) continue;
                int x, y;
                ring_pt(g, rad + wobble(g, j * 2), j * 2, &x, &y);
                put(x, y, col);
            }
        }
    }
    CP_END(CP_TRAIL);
    CP_BEGIN(CP_FRONT);
    // Front: the fissure. Toque = two px wide and bone-bright; tanido = one px, faint, in dashes.
    for (int j = 1; j <= CFX_BINS; j++) {
        if (!(valid[j - 1] && valid[j]) || !(vis[j - 1] | vis[j])) continue;
        if (off_screen(fx[j - 1], fy[j - 1], fx[j], fy[j])) continue;
        if (toque) put_line2(fx[j - 1], fy[j - 1], fx[j], fy[j], CFX_BONE, CFX_VERD);
        else if (!((j >> 2) & 1)) put_line(fx[j - 1], fy[j - 1], fx[j], fy[j], (j & 1) ? CFX_MOSS : CFX_VERD);
    }
    CP_END(CP_FRONT);
    CP_BEGIN(CP_GLOW);
    // Glow band (toque): a solid bright band behind the front so the ring reads at any radius.
    if (toque) {
        for (int j = 1; j <= CFX_BINS; j++) {
            if (!(valid[j - 1] && valid[j]) || !(vis[j - 1] | vis[j])) continue;
            const int d = (j & 1) ? 4 : 2;                       // two bands folded into alternate segments
            const uint16_t col = d <= 2 ? CFX_VERD : CFX_MOSS;
            const int x0 = fx[j - 1] - ((COS_AT(j * 2 - 2) * d) >> 8), y0 = fy[j - 1] - ((SIN_AT(j * 2 - 2) * d) >> 9);
            const int x1 = fx[j] - ((COS_AT(j * 2) * d) >> 8), y1 = fy[j] - ((SIN_AT(j * 2) * d) >> 9);
            if (off_screen(x0, y0, x1, y1)) continue;
            put_line(x0, y0, x1, y1, col);
        }
    }
    CP_END(CP_GLOW);
    CP_BEGIN(CP_SPUR);
    // Spurs: short cracks that branch off the front into the trail.
    for (int i = 0; i < 256; i += 8) {
        const uint32_t h = hash2((uint32_t)i, g->seed ^ 0x5Au);
        if ((h & 3u) != 0u || r > (int)g->blk[i >> CFX_BIN_SHIFT] || !vis[i >> 1]) continue;
        const int len = (toque ? 4 : 2) + (int)((h >> 4) & 3u);
        const int side = (h & 0x100u) ? 1 : -1;
        const int x = fx[i >> 1], y = fy[i >> 1];
        for (int s = 1; s <= len; s++) put(x - ((COS_AT(i) * s) >> 8) + side * (s >> 1), y - ((SIN_AT(i) * s) >> 9), s < 3 ? CFX_VERD : CFX_MOSS);
    }
    CP_END(CP_SPUR);
    CP_BEGIN(CP_CUT);
    if (toque) draw_cut(g);
    CP_END(CP_CUT);
    CP_BEGIN(CP_MOTE);
    // Motes: born on the crack as the front passes, they rise and fade (stateless: the ring radius is the clock).
    {
        const int n = toque ? 32 : 14, life = toque ? 22 : 14;
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
    CP_END(CP_MOTE);
}

void cfx_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    int any = 0;
    for (int i = 0; i < CFX_MAX; i++) if (s_ring[i].active) { any = 1; break; }
    if (!any) return;
    CP_BEGIN(CP_RF);
    CP_COUNT_INC(CP_FRAMES);
#if CFX_PROF
    const uint32_t cp0[5] = { g_cfxp.n[CP_PUT], g_cfxp.n[CP_PUT_IN], g_cfxp.n[CP_GPIF], g_cfxp.n[CP_WSH], g_cfxp.n[CP_WPH] };
#endif
#if CFX_PROF
    { static uint32_t last; const uint32_t now = cpuGetTiming(); g_cfxp.t[CP_FRAMES] = now - last; last = now; }
#endif
    r_buf = buffer; r_camx = cam_x; r_camy = cam_y;
    if (!s_noise_ok) {
        for (int i = 0; i < 256; i++) s_noise[i] = (uint8_t)(hash2((uint32_t)i, 0x3Du) & 15u);
        s_noise_ok = 1;
    }
    CP_BEGIN(CP_MEMSET);
    memset(r_row, -1, sizeof(r_row));
    memset(r_cell, 0, sizeof(r_cell));
    if (++s_gen == 0) { memset(r_hgen, 0, sizeof(r_hgen)); s_gen = 1; }
    r_cxs = cam_x & 3; r_cys = cam_y & 3;
    for (int y = 0; y < SCREEN_H; y++) { r_dx0[y] = SCREEN_W; r_dx1[y] = 0; }
    CP_END(CP_MEMSET);
    for (int i = 0; i < CFX_MAX; i++)
        if (s_ring[i].active) draw_ring(&s_ring[i]);
    CP_BEGIN(CP_FLUSH);
    for (int y = 0; y < SCREEN_H; y++)
        if (r_dx0[y] < r_dx1[y]) dirty_row(y, r_dx0[y], r_dx1[y]);
    CP_END(CP_FLUSH);
    CP_END(CP_RF);
#if CFX_PROF
    { static const uint8_t ids[5] = { CP_PUT, CP_PUT_IN, CP_GPIF, CP_WSH, CP_WPH };
      for (int q = 0; q < 5; q++) { const uint32_t dd = g_cfxp.n[ids[q]] - cp0[q]; if (dd > g_cfxp.mx[ids[q]]) g_cfxp.mx[ids[q]] = dd; } }
#endif
}
