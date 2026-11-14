#include "enemy_laser.h"
#include "enemy_ai.h"
#include "groundfx.h"
#include "arena.h"
#include <nds.h>

// Desaturated verdigris palette (DESIGN.md 6.10 "Efectos desaturados"): same role and peak brightness as the
// hero's FX_SH_* (ivory 29,25,19 ... deep 9,3,3), tinted green only by a few points; contrast by value.
#define OJO_FX_CORE   (RGB15(24, 27, 20) | BIT(15))   // pale bone-phosphor (gaze peak)
#define OJO_FX_HI     (RGB15(16, 21, 14) | BIT(15))   // oxidized verdigris
#define OJO_FX_MID    (RGB15(10, 15, 9) | BIT(15))    // cathedral moss
#define OJO_FX_DIM    (RGB15(6, 10, 6) | BIT(15))     // spectral smoke
// The shot (SENTENCE) is cold desaturated ice blue ("hielo espectral"), apart from the green gaze/charge.
#define OJO_SHOT_FLASH (RGB15(28, 29, 30) | BIT(15))  // core and muzzle flash
#define OJO_SHOT_BODY  (RGB15(21, 26, 28) | BIT(15))
#define OJO_SHOT_EDGE  (RGB15(12, 19, 23) | BIT(15))
#define OJO_SHOT_FADE  (RGB15(8, 13, 17) | BIT(15))
#define OJO_FX_DARK   (RGB15(3, 6, 4) | BIT(15))      // faint shadow

static uint32_t s_row_x0[SCREEN_H], s_row_x1[SCREEN_H];
static int s_fx_tick = 0;
static inline uint32_t int_sqrt(uint32_t n) { return (uint32_t)sqrt32((int)n); }

static inline uint8_t cone_coll_flags(int cx, int cy) {
    if ((uint32_t)cx >= g_arena->collision_w || (uint32_t)cy >= g_arena->collision_h) return 3;
    uint32_t index = (uint32_t)cy * g_arena->collision_w + (uint32_t)cx;
    return (g_arena->collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

// Marches along true-ground unit vector (vx, vy) (1.15) from (fx_base, fy_base) in 4px steps,
// stopping at the first wall/pillar cell (flags == 3) or max_len.
static int ray_hit_dist(int fx_base, int fy_base, int vx, int vy, int max_len) {
    for (int r = 8; r <= max_len; r += 4) {
        int wx = fx_base + ((vx * r) >> 15);
        int wy = fy_base + ((vy * r) >> 16);
        if (cone_coll_flags(wx >> 2, wy >> 2) == 3) return r;
    }
    return max_len;
}

// Ground distance (px) from (fx, fy) along the true-ground unit vector (vx, vy) (1.15) to the first wall or column.
int ojo_ray_wall_dist(int fx, int fy, int vx, int vy, int max_len) {
    return ray_hit_dist(fx, fy, vx, vy, max_len);
}

static inline void plot_occ_px(uint16_t *buffer, int sx, int sy, int cam_x, int cam_y, int depth, uint16_t color) {
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    if (world_pixel_hidden(sx + cam_x, sy + cam_y, depth)) return;
    buffer[(sy << 8) + sx] = color;
    dirty_row(sy, sx, sx + 1);
}

// ---------------------------------------------------------------------------
// 1) Sentence curse / spectral stream (ENEMY_STATE_SENTENCE)
// ---------------------------------------------------------------------------
static void draw_ember_burst(uint16_t *buffer, int cx, int cy, int cam_x, int cam_y, int depth, int age) {
    int spread = 1 + age;
    plot_occ_px(buffer, cx, cy, cam_x, cam_y, depth, age <= 1 ? OJO_SHOT_BODY : OJO_SHOT_EDGE);
    plot_occ_px(buffer, cx - spread, cy - 1, cam_x, cam_y, depth, OJO_SHOT_EDGE);
    plot_occ_px(buffer, cx + spread, cy + 1, cam_x, cam_y, depth, OJO_SHOT_EDGE);
    plot_occ_px(buffer, cx + 1, cy - spread, cam_x, cam_y, depth, OJO_SHOT_FADE);
    plot_occ_px(buffer, cx - 1, cy + spread, cam_x, cam_y, depth, OJO_SHOT_FADE);
    if (age <= 2) {
        plot_occ_px(buffer, cx, cy - spread - 1, cam_x, cam_y, depth, OJO_SHOT_FADE);
    }
}

// Muzzle flash on the mouth: big for the whole impact + flare (it pulses a little), then the small burst.
static void draw_muzzle_flash(uint16_t *buffer, int cx, int cy, int cam_x, int cam_y, int depth, int age) {
    if (age < OJO_BEAM_HIT_FRAMES) {
        const int big = age < OJO_BEAM_IMPACT_FRAMES || (age & 2);      // a 3x3 flash, with a ring that pulses
        for (int dy = -1; dy <= 1; dy++)
            for (int dx = -1; dx <= 1; dx++)
                plot_occ_px(buffer, cx + dx, cy + dy, cam_x, cam_y, depth,
                            (dx | dy) == 0 ? OJO_SHOT_FLASH : OJO_SHOT_BODY);
        const int r = big ? 3 : 2;
        plot_occ_px(buffer, cx - r, cy, cam_x, cam_y, depth, OJO_SHOT_EDGE);
        plot_occ_px(buffer, cx + r, cy, cam_x, cam_y, depth, OJO_SHOT_EDGE);
        plot_occ_px(buffer, cx, cy - r, cam_x, cam_y, depth, OJO_SHOT_EDGE);
        plot_occ_px(buffer, cx, cy + r, cam_x, cam_y, depth, OJO_SHOT_FADE);
        if (big) {
            plot_occ_px(buffer, cx - 2, cy - 2, cam_x, cam_y, depth, OJO_SHOT_FADE);
            plot_occ_px(buffer, cx + 2, cy - 2, cam_x, cam_y, depth, OJO_SHOT_FADE);
        }
        return;
    }
    draw_ember_burst(buffer, cx, cy, cam_x, cam_y, depth, age - OJO_BEAM_HIT_FRAMES);
}

// Pseudo-noise of the flame edge (integer table, no rand): 2..4 quarters of the full edge, indexed by (step >> 2) + frame.
static const uint8_t s_flame[16] = { 3, 4, 2, 3, 4, 3, 2, 4, 3, 2, 4, 3, 3, 2, 4, 3 };
#define OJO_FLAME_HALF_CAP 5      // px: widest half-width of the flame incl. tongues
#define OJO_OFF_CAP 6             // perpendicular offset tables cover -6..6 (the band's widest half-width is 6)
#define OJO_LANTERN_HEIGHT 30     // px above the Ojo's feet: the lantern at the top of the body
#define OJO_LOCK_BLINK_FRAMES 10  // last frames of LOCK in which the line blinks
#define OJO_BAND_HALF 6           // px half-width of the band when it is first spotted

// ---------------------------------------------------------------------------
// 2) Gaze bands and sentence beams, painted in depth order with the actors.
//
// Each active band (TRACK, LOCK) or beam (SENTENCE) is prepared ONCE per frame (enemy_lasers_begin) into a "strip":
// the origin, the 8.8 step, the perpendicular offsets, the colours and the ground depth of every step
// (depth(d) = depth0 + (dgy * d >> 8): the ground y under that point of the line, interpolated from the mouth or
// lantern to the hero's feet and kept going beyond him). The painter loop in main.c calls
// enemy_lasers_draw_before(depth) before each sorted actor: it paints the not-yet-painted steps whose ground depth is
// smaller (further away) than the actor's, so the actor covers them, and the rest (nearer) are painted after it,
// over it. Depth is monotonic along a line, so the steps of a depth window are one contiguous interval and every
// step is painted exactly once; row bounds accumulate across the partial passes and are flushed once at the end.
// ---------------------------------------------------------------------------
enum { STRIP_BEAM = 1, STRIP_BAND = 2 };
#define OJO_MAX_STRIPS 4          // at most OJO_MAX_LOOKING (2) Ojos aim or shoot at once; headroom for a band and a beam each

typedef struct {
    const Enemy *e;
    int kind;
    int ox, oy;               // screen origin px
    int ux, uy;               // 8.8 screen step per d
    int lo, hi;               // steps still to paint: [lo, hi]
    int depth0, dgy;          // ground depth of step 0 and its 8.8 advance per step
    // beam
    int age, impact, dissipate, fa, maxw, rise, wisp_k, wisp_mul, wisp_phase;
    uint16_t core_col, flank_col;
    int ex, ey, end_depth, burst_done, burst_age;      // the impact burst at the end of the beam
    // band
    int w, tick;
    uint16_t centre;
    int off_x[2 * OJO_OFF_CAP + 1], off_y[2 * OJO_OFF_CAP + 1];
} OjoStrip;

static OjoStrip s_strip[OJO_MAX_STRIPS];
static int s_strip_n;
static int s_strip_cam_x, s_strip_cam_y;

static inline void strip_plot(uint16_t *buffer, int x, int y, uint16_t color) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    buffer[(y << 8) + x] = color;
    if (x < (int)s_row_x0[y]) s_row_x0[y] = (uint32_t)x;
    if (x >= (int)s_row_x1[y]) s_row_x1[y] = (uint32_t)(x + 1);
}

// Fills the perpendicular offsets of a strip (one square root and two divisions per beam or band).
static void strip_offsets(OjoStrip *S, int dir_x, int dir_y) {
    int m = (int)sqrt32(dir_x * dir_x + dir_y * dir_y);
    if (m < 1) m = 1;
    const int perp_x = div32(-dir_y * 256, m);
    const int perp_y = div32(dir_x * 256, m);
    for (int o = -OJO_OFF_CAP; o <= OJO_OFF_CAP; o++) {
        S->off_x[o + OJO_OFF_CAP] = (perp_x * o) >> 8;
        S->off_y[o + OJO_OFF_CAP] = (perp_y * o) >> 8;
    }
}

// 0..256 progress of the whole aim (TRACK then LOCK); the band narrows and the mouth charges with it.
static int ojo_aim_progress(const Enemy *e) {
    int elapsed;
    if (e->state == ENEMY_STATE_TRACK) elapsed = OJO_TRACK_FRAMES - e->state_timer;
    else if (e->state == ENEMY_STATE_LOCK) elapsed = OJO_TRACK_FRAMES + OJO_LOCK_FRAMES - e->state_timer;
    else return 0;
    if (elapsed < 0) elapsed = 0;
    if (elapsed > OJO_AIM_FRAMES) elapsed = OJO_AIM_FRAMES;
    return div32(elapsed * 256, OJO_AIM_FRAMES);       // one division per Ojo per frame
}

// Prepares the sentence beam "llamarada espectral" (DESIGN.md 6.10): a STRAIGHT core exactly on the damage line with flame
// edges whose width varies along the beam and per frame, tongues that escape sideways and ice wisps. IMPACT (3 frames):
// widest and brightest. FLARE (20): wide, burning edges. DISSIPATE (8): narrows, breaks into segments, leaves wisps.
static int strip_prepare_beam(OjoStrip *S, const Enemy *e, int cam_x, int cam_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    const int mxi = TO_INT(mx), myi = TO_INT(my);
    const int ox = mxi - cam_x;
    const int oy = myi - mh - cam_y;
    const int dir_x = e->aim_dir_x;
    const int dir_y = e->aim_dir_y;

    int len = e->beam_len;
    if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;
    if (len < 1) return 0;
    const int ex = ox + ((dir_x * len) >> 8);
    const int ey = oy + ((dir_y * len) >> 8);
    if ((ox < -8 && ex < -8) || (ox >= SCREEN_W + 8 && ex >= SCREEN_W + 8) ||
        (oy < -8 && ey < -8) || (oy >= SCREEN_H + 8 && ey >= SCREEN_H + 8)) return 0;

    int age = OJO_BEAM_FRAMES - e->state_timer;
    if (age < 0) age = 0;
    S->e = e;
    S->kind = STRIP_BEAM;
    S->ox = ox;
    S->oy = oy;
    S->ux = dir_x;
    S->uy = dir_y;
    S->lo = 1;
    S->hi = len;
    S->age = age;
    S->impact = age < OJO_BEAM_IMPACT_FRAMES;
    S->fa = age - OJO_BEAM_HIT_FRAMES;                 // >= 0: dissipating, frames since it began
    S->dissipate = S->fa >= 0;
    // Widest half-width of the flame edge: 3 px (7 px beam) on impact and flare, narrowing while it dissipates.
    S->maxw = !S->dissipate ? 3 : (S->fa < 3 ? 3 : (S->fa < 6 ? 2 : 1));
    S->core_col = S->impact ? OJO_SHOT_FLASH : (S->dissipate ? OJO_SHOT_EDGE : OJO_SHOT_BODY);
    S->flank_col = S->impact ? OJO_SHOT_BODY : OJO_SHOT_EDGE;     // the 1 px each side of the core
    S->rise = S->dissipate ? 2 + S->fa : 2 + ((age >> 1) & 3);
    // Wisps every 13 px (9 while dissipating): (d + phase) mod K == 0 without a division, see beam_range.
    S->wisp_k = S->dissipate ? 9 : 13;
    S->wisp_mul = S->dissipate ? 7282 : 5042;          // ~ 65536 / K
    S->wisp_phase = (age * 5) & 7;
    strip_offsets(S, dir_x, dir_y);

    // Ground depth: from the mouth's ground y to the locked point's (the hero's feet), extrapolated beyond it.
    const int ay = e->aim_py - myi + mh - OJO_TARGET_HEIGHT;
    const int axw = e->aim_px - mxi;
    int slen = (int)int_sqrt((uint32_t)(axw * axw + GROUND_DY2(ay)));
    if (slen < 1) slen = 1;
    S->depth0 = myi;
    S->dgy = div32((e->aim_py - myi) * 256, slen);
    S->ex = ex;
    S->ey = ey;
    S->end_depth = S->depth0 + ((S->dgy * len) >> 8);
    S->burst_done = S->dissipate;                      // the chest burst lasts through impact and flare
    S->burst_age = S->impact ? age : 1 + (age & 1);
    return 1;
}

// Paints beam steps d0..d1 (each exactly once): offsets are precomputed per beam; occlusion is tested at the centre of
// each step against walls and columns with that step's own ground depth; one pass of at most OJO_BEAM_MAX_LEN steps.
__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void draw_laser(uint16_t *buffer, const OjoStrip *S, int d0, int d1) {
    const int cam_x = s_strip_cam_x, cam_y = s_strip_cam_y;
    const int ux = S->ux, uy = S->uy;
    const int impact = S->impact, dissipate = S->dissipate, fa = S->fa, maxw = S->maxw, age = S->age;
    int fx = (S->ox << 8) + 128 + ux * d0;
    int fy = (S->oy << 8) + 128 + uy * d0;
    for (int d = d0; d <= d1; d++, fx += ux, fy += uy) {
        const int px = fx >> 8;
        const int py = fy >> 8;
        if (px < -8 || px >= SCREEN_W + 8 || py < -8 || py >= SCREEN_H + 8) continue;
        const int depth = S->depth0 + ((S->dgy * d) >> 8);
        if ((unsigned)px < SCREEN_W && (unsigned)py < SCREEN_H && world_pixel_hidden(px + cam_x, py + cam_y, depth)) continue;

        // Dissipating: the beam breaks into segments that grow apart.
        if (fa >= 2 && ((((d >> 3) + fa) & 3) == 0)) continue;

        // Flame half-widths of both sides at this step and frame, plus an occasional tongue escaping sideways.
        const int idx = ((d >> 2) + age * 3) & 15;
        int hl = impact ? maxw : (maxw * s_flame[idx] + 2) >> 2;
        int hr = impact ? maxw : (maxw * s_flame[(idx + 5) & 15] + 2) >> 2;
        if (!impact && !dissipate) {
            const int t = (d * 7 + age * 13) & 31;
            if (t == 0) hl += 2;
            else if (t == 11) hr += 1 + (d & 1);
        }
        for (int o = -hl; o <= hr; o++) {
            const int ao = o < 0 ? -o : o;
            const int side_w = o < 0 ? hl : hr;
            uint16_t col;
            if (o == 0) col = S->core_col;
            else if (ao == 1) col = S->flank_col;
            else col = ao == side_w ? OJO_SHOT_FADE : OJO_SHOT_EDGE;
            strip_plot(buffer, px + S->off_x[o + OJO_OFF_CAP], py + S->off_y[o + OJO_OFF_CAP], col);
        }
        // Ice wisp peeling off the edge and rising (heritage of the Maleficio smoke), by step so it is order independent.
        const int dd = d + S->wisp_phase;
        if (dd - S->wisp_k * ((dd * S->wisp_mul) >> 16) == 0) {
            const int wo = (d & 4) ? hr + 1 : -(hl + 1);
            const int wc = wo > OJO_FLAME_HALF_CAP ? OJO_FLAME_HALF_CAP : (wo < -OJO_FLAME_HALF_CAP ? -OJO_FLAME_HALF_CAP : wo);
            const int x = px + S->off_x[wc + OJO_OFF_CAP];
            const int y = py + S->off_y[wc + OJO_OFF_CAP] - S->rise;
            strip_plot(buffer, x, y, OJO_SHOT_EDGE);
            strip_plot(buffer, x, y - 1, OJO_SHOT_FADE);
        }
    }
}

// Prepares the gaze band lantern -> hero's chest (TRACK follows him, LOCK keeps the line frozen). It stops at the first wall
// or column on the ground line. Wide + dithered at first, one bright pixel at the end (the hero sniper's collimation A1).
static int strip_prepare_band(OjoStrip *S, const Enemy *e, int cam_x, int cam_y) {
    // Last frames of the lock: the thin line blinks (2 frames on, 2 off) as the "fires now" warning.
    if (e->state == ENEMY_STATE_LOCK && e->state_timer <= OJO_LOCK_BLINK_FRAMES && ((e->state_timer >> 1) & 1)) return 0;
    const int wx = TO_INT(e->x), wy = TO_INT(e->y);
    const int ox = wx - cam_x;
    const int oy = wy - OJO_LANTERN_HEIGHT - cam_y;
    const int ex = e->aim_px - cam_x;
    const int ey = e->aim_py - OJO_TARGET_HEIGHT - cam_y;
    const int dx = ex - ox, dy = ey - oy;
    const int len0 = (int)int_sqrt((uint32_t)(dx * dx + dy * dy));
    if (len0 < 2) return 0;
    int len = len0;

    // Cut at the first wall or column along the true ground line (2:1 metric) toward the hero.
    const int gx = e->aim_px - wx, gy2 = 2 * (e->aim_py - wy);
    const int glen = (int)int_sqrt((uint32_t)(gx * gx + gy2 * gy2));
    if (glen >= 8) {
        int cut = ray_hit_dist(wx, wy, div32(gx << 15, glen), div32(gy2 << 15, glen), glen);
        if (cut < glen) len = div32(len0 * cut, glen);
    }
    if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;
    if (len < 1) return 0;

    const int ux = div32(dx * 256, len0);               // unit direction, 8.8, on the screen
    const int uy = div32(dy * 256, len0);
    const int ex2 = ox + ((ux * len) >> 8), ey2 = oy + ((uy * len) >> 8);
    if ((ox < -8 && ex2 < -8) || (ox >= SCREEN_W + 8 && ex2 >= SCREEN_W + 8) ||
        (oy < -8 && ey2 < -8) || (oy >= SCREEN_H + 8 && ey2 >= SCREEN_H + 8)) return 0;

    const int prog = ojo_aim_progress(e);
    S->e = e;
    S->kind = STRIP_BAND;
    S->ox = ox;
    S->oy = oy;
    S->ux = ux;
    S->uy = uy;
    S->lo = 1;
    S->hi = len;
    S->w = (OJO_BAND_HALF * (256 - prog)) >> 8;        // 6 at the start, 0 on the last frame of the lock
    S->centre = prog >= 160 ? OJO_FX_CORE : OJO_FX_HI;
    S->tick = s_fx_tick;
    strip_offsets(S, ux, uy);
    // Ground depth: from the Ojo's feet to the hero's feet, extrapolated beyond him (it is cut at the first wall anyway).
    S->depth0 = wy;
    S->dgy = div32((e->aim_py - wy) * 256, len0);
    return 1;
}

__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void draw_gaze_band(uint16_t *buffer, const OjoStrip *S, int d0, int d1) {
    const int cam_x = s_strip_cam_x, cam_y = s_strip_cam_y;
    const int ux = S->ux, uy = S->uy, w = S->w, tick = S->tick;
    int fx = (S->ox << 8) + 128 + ux * d0;
    int fy = (S->oy << 8) + 128 + uy * d0;
    for (int d = d0; d <= d1; d++, fx += ux, fy += uy) {
        const int px = fx >> 8, py = fy >> 8;
        if (px < -8 || px >= SCREEN_W + 8 || py < -8 || py >= SCREEN_H + 8) continue;
        const int depth = S->depth0 + ((S->dgy * d) >> 8);
        if ((unsigned)px < SCREEN_W && (unsigned)py < SCREEN_H && world_pixel_hidden(px + cam_x, py + cam_y, depth)) continue;

        if (w == 0) {                                   // armed: a steady 1 px muted line (it blinks in the last lock frames)
            strip_plot(buffer, px, py, OJO_FX_HI);
            continue;
        }
        for (int o = -w; o <= w; o++) {
            const int x = px + S->off_x[o + OJO_OFF_CAP];
            const int y = py + S->off_y[o + OJO_OFF_CAP];
            const int ao = o < 0 ? -o : o;
            if (o == 0) strip_plot(buffer, x, y, S->centre);
            else if (ao == w) { if (((x * 3 + y * 5 + tick) & 3) == 0) strip_plot(buffer, x, y, OJO_FX_DIM); }
            else if (ao * 2 >= w) { if (((x + y + tick) & 1) == 0) strip_plot(buffer, x, y, OJO_FX_MID); }
            else strip_plot(buffer, x, y, OJO_FX_HI);
        }
    }
}

static void strip_paint(uint16_t *buffer, const OjoStrip *S, int d0, int d1) {
    if (S->kind == STRIP_BEAM) draw_laser(buffer, S, d0, d1);
    else draw_gaze_band(buffer, S, d0, d1);
}

// Prepares every Ojo's band (TRACK, LOCK) and sentence beam (SENTENCE) once per frame, for one screen.
void enemy_lasers_begin(const Enemy *enemies, int count, int cam_x, int cam_y) {
    s_strip_n = 0;
    if (!enemies) return;
    s_fx_tick++;
    s_strip_cam_x = cam_x;
    s_strip_cam_y = cam_y;
    for (int i = 0; i < count && s_strip_n < OJO_MAX_STRIPS; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->type != ENEMY_TYPE_SHOOTER) continue;
        OjoStrip *S = &s_strip[s_strip_n];
        int ok = 0;
        if (e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK) ok = strip_prepare_band(S, e, cam_x, cam_y);
        else if (e->state == ENEMY_STATE_SENTENCE) ok = strip_prepare_beam(S, e, cam_x, cam_y);
        if (ok) s_strip_n++;
    }
    if (s_strip_n > 0)
        for (int y = 0; y < SCREEN_H; y++) { s_row_x0[y] = SCREEN_W; s_row_x1[y] = 0; }
}

// Paints, for every prepared strip, the steps still unpainted whose ground depth is smaller than `depth` (further from
// the camera than an actor standing at that depth). The painter loop calls it before each sorted actor.
void enemy_lasers_draw_before(uint16_t *buffer, int depth) {
    for (int i = 0; i < s_strip_n; i++) {
        OjoStrip *S = &s_strip[i];
        if (S->lo <= S->hi) {
            const int k = depth - S->depth0;
            if (S->dgy > 0) {                          // depth grows with the step: steps d <= maxd are further than `depth`
                const int maxd = k <= 0 ? 0 : div32(256 * k + S->dgy - 1, S->dgy) - 1;
                const int b = maxd < S->hi ? maxd : S->hi;
                if (S->lo <= b) { strip_paint(buffer, S, S->lo, b); S->lo = b + 1; }
            } else if (S->dgy == 0) {                  // the whole line is at one depth
                if (k > 0) { strip_paint(buffer, S, S->lo, S->hi); S->lo = S->hi + 1; }
            } else {                                   // it runs away from the camera: the far end is the first to be covered
                const int mind = k > 0 ? 1 : div32(256 * -k, -S->dgy) + 1;
                const int a = mind > S->lo ? mind : S->lo;
                if (a <= S->hi) { strip_paint(buffer, S, a, S->hi); S->hi = a - 1; }
            }
        }
        if (S->kind == STRIP_BEAM && !S->burst_done && S->end_depth < depth) {
            draw_ember_burst(buffer, S->ex, S->ey, s_strip_cam_x, s_strip_cam_y, S->end_depth, S->burst_age);
            S->burst_done = 1;
        }
    }
}

// After the last actor: paints what is left (the steps in front of everybody), then marks the touched rows once.
void enemy_lasers_end(uint16_t *buffer) {
    if (s_strip_n <= 0) return;
    for (int i = 0; i < s_strip_n; i++) {
        OjoStrip *S = &s_strip[i];
        if (S->lo <= S->hi) { strip_paint(buffer, S, S->lo, S->hi); S->lo = S->hi + 1; }
        if (S->kind == STRIP_BEAM && !S->burst_done) {
            draw_ember_burst(buffer, S->ex, S->ey, s_strip_cam_x, s_strip_cam_y, S->end_depth, S->burst_age);
            S->burst_done = 1;
        }
    }
    for (int y = 0; y < SCREEN_H; y++)
        if (s_row_x1[y] > s_row_x0[y]) dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);
    s_strip_n = 0;
}

// ---------------------------------------------------------------------------
// 3) Mouth charge aura on the hand-held head (and muzzle burst on fire)
// ---------------------------------------------------------------------------
void enemy_ojo_mouth_glow_render(uint16_t *buffer, const Enemy *e, int idx, int cam_x, int cam_y, int depth) {
    if (!buffer || !e) return;
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    const int cx = TO_INT(mx) - cam_x;
    const int cy = TO_INT(my) - mh - cam_y;

    if (e->state == ENEMY_STATE_SENTENCE) {
        int age = OJO_BEAM_FRAMES - e->state_timer;
        if (age >= 0 && age < OJO_BEAM_FRAMES) draw_muzzle_flash(buffer, cx, cy, cam_x, cam_y, depth, age);
        return;
    }

    (void)idx;
    // The charge follows this Ojo's own aim (TRACK + LOCK = 60 frames): dark at first, very bright at the shot.
    const int prog = ojo_aim_progress(e);
    if (prog <= 0) return;

    const int tick = s_fx_tick;

    // Pulsing core + shimmering organic halo + rising embers.
    int pulse = (tick >> 2) & 1;
    uint16_t core = (prog >= 192) ? OJO_FX_CORE : (prog >= 96 ? OJO_FX_HI : OJO_FX_MID);
    plot_occ_px(buffer, cx, cy, cam_x, cam_y, depth, core);

    if (prog >= 48) {
        uint16_t ring1 = (prog >= 180) ? OJO_FX_HI : OJO_FX_MID;
        static const int8_t nx[4] = { -1, 1, 0, 0 };
        static const int8_t ny[4] = { 0, 0, -1, 1 };
        for (int i = 0; i < 4; i++) {
            if (prog < 120 && ((i + pulse) & 1)) continue;
            plot_occ_px(buffer, cx + nx[i], cy + ny[i], cam_x, cam_y, depth, ring1);
        }
    }
    if (prog >= 110) {
        uint16_t ring2 = (prog >= 210) ? OJO_FX_MID : OJO_FX_DIM;
        static const int8_t ox[8] = { -1, 1, -1, 1, -2, 2, 0, 0 };
        static const int8_t oy[8] = { -1, -1, 1, 1, 0, 0, -2, 2 };
        for (int i = 0; i < 8; i++) {
            if (((i + (tick >> 1)) & 1) && prog < 220) continue;
            plot_occ_px(buffer, cx + ox[i], cy + oy[i], cam_x, cam_y, depth, ring2);
        }
    }
    if (prog >= 150) {
        for (int w = 0; w < 3; w++) {
            int phase = (tick + w * 7) % 18;
            int dy = -(1 + (phase / 3));
            int dx = (w - 1) + (((phase >> 2) & 1) ? 0 : (w == 0 ? -1 : 1));
            uint16_t col = (phase < 6) ? OJO_FX_HI : (phase < 12 ? OJO_FX_MID : OJO_FX_DIM);
            plot_occ_px(buffer, cx + dx, cy + dy, cam_x, cam_y, depth, col);
        }
    }
}

