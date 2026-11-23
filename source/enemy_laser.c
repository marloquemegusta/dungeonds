#include "enemy_laser.h"
#include "enemy_ai.h"
#include "groundfx.h"
#include "arena.h"
#include <nds.h>

// Desaturated bone-phosphor palette of the sentence written on the floor (DESIGN.md 6.10 "Efectos desaturados"), five levels
// from dim (0) to peak (4); contrast by value, tint green by a few points. s_dark: the pupils and the dithered halo.
static const uint16_t s_ramp[5] = { RGB15(4, 8, 6) | BIT(15), RGB15(8, 14, 10) | BIT(15), RGB15(13, 20, 14) | BIT(15),
                                    RGB15(19, 25, 19) | BIT(15), RGB15(25, 29, 23) | BIT(15) };
static const uint16_t s_dark = RGB15(2, 4, 3) | BIT(15);

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
// The sentence written on the floor (DESIGN.md 6.10), look "fosforo del farol". The Ojo no longer shoots a beam: from its
// feet it engraves a crack along the ground, with almond eyes along it, and the whole line blows up at once.
//   TRACK     the lantern flashes (a ring that opens); the tip of the crack advances to the hero (~14 frames) and the line
//             follows him: 1 px core, as far as the hero.
//   LOCK      the line is frozen in its direction and runs on to the first wall or column (the reach of the damage), 2 px
//             core; a light runs from the Ojo to the end opening the eyes (the countdown); the last 10 frames it pulses.
//   SENTENCE  the whole line blows up from the floor (impact 3 frames, burning 20, dissipating 8) while the head in its hand
//             flashes at the mouth; nothing is fired. The damage (enemy_ai.c ojo_fire) is this same line, feet to wall.
//   scar      the crack stays and goes out in ~1 s (it outlives the sentence, into the cooldown).
// ---------------------------------------------------------------------------
#define OJO_LANTERN_HEIGHT 30     // px above the Ojo feet: the lantern at the top of the body
#define OJO_LOCK_BLINK_FRAMES 10  // last frames of LOCK in which the line pulses
#define OJO_TIP_FRAMES 14         // frames the tip of the crack takes to reach the hero
#define OJO_FLASH_FRAMES 8        // frames of the lantern flash when it sees the hero
#define OJO_SCAR_START OJO_BEAM_HIT_FRAMES   // age at which the crack begins to go out (the flames are dissipating)
#define OJO_SCAR_FRAMES 68        // the last pixel of the crack is out this many frames later
#define OJO_SCAR_END (OJO_SCAR_START + OJO_SCAR_FRAMES)
#define OJO_OFF_CAP 6             // perpendicular offset tables cover -6..6
#define OJO_EYE_PERIOD 14         // an eye every 14 steps of the line, at the steps d with d mod 14 == OJO_EYE_MARK
#define OJO_EYE_MARK 7
#define OJO_DRAW_SECTION ITCM_CODE   // the drawing loop lives in the fast memory

// Pseudo-noise by distance along the line, so the drawing is stable while the line turns: a slow random walk of the crack
// sideways offset and 0..7 values for heights and gaps.
static const int8_t s_walk[64] = {
    0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, -1, -1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, -1, -1, -1, -1, -1, -1,
    0, 0, 0, 1, 1, 1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1,
};
static const uint8_t s_hh[64] = {
    3, 3, 2, 3, 6, 7, 1, 6, 0, 1, 1, 0, 4, 3, 6, 4, 6, 7, 4, 2, 1, 2, 3, 7, 1, 4, 3, 3, 0, 1, 4, 6,
    7, 3, 0, 0, 2, 4, 5, 2, 1, 5, 2, 7, 5, 2, 0, 0, 7, 5, 4, 0, 0, 1, 7, 1, 4, 5, 2, 1, 1, 7, 5, 0,
};
// Unit circle in 32 directions (8.8): cos(k * 11.25 deg); sin(k) = cos(k - 8).
static const int16_t s_cos32[32] = { 256, 251, 237, 213, 181, 142, 98, 50, 0, -50, -98, -142, -181, -213, -237, -251, -256, -251, -237, -213, -181, -142, -98, -50, 0, 50, 98, 142, 181, 213, 237, 251 };

// ---------------------------------------------------------------------------
// Each active line (TRACK, LOCK, SENTENCE, scar) is prepared ONCE per frame (enemy_lasers_begin) into a "strip": the origin
// (the Ojo feet on the screen), the 8.8 step, the perpendicular offsets and the ground depth of every step
// (depth(d) = depth0 + (dgy * d >> 8): the ground y under that point of the line, which for a floor line is its own y).
// The painter loop in main.c calls enemy_lasers_draw_before(depth) before each sorted actor: it paints the not-yet-painted
// steps whose ground depth is smaller (further away) than the actor, so the actor covers them, and the rest (nearer) are
// painted after it, over it. Depth is monotonic along a line, so the steps of a depth window are one contiguous interval
// and every step is painted exactly once; row bounds accumulate across the partial passes and are flushed once at the end.
// ---------------------------------------------------------------------------
enum { PH_TRACK = 0, PH_LOCK, PH_BLAST, PH_SCAR };
#define OJO_MAX_STRIPS 6          // at most OJO_MAX_LOOKING (2) Ojos aim or shoot at once, plus the scars still going out

typedef struct {
    int ox, oy;               // screen origin px (the Ojo feet)
    int ux, uy;               // 8.8 screen step per d
    int lo, hi;               // steps still to paint: [lo, hi]
    int depth0, dgy;          // ground depth of step 0 and its 8.8 advance per step
    int ph;                   // phase
    int a;                    // TRACK / LOCK: frames since the phase began; BLAST / SCAR: frames since the sentence fell
    int cd;                   // LOCK: step reached by the charge (front of the light / last eye opened)
    int pulse;                // LOCK, last frames: 1 bright, 2 dim, 0 none
    int off_x[2 * OJO_OFF_CAP + 1], off_y[2 * OJO_OFF_CAP + 1];
} OjoStrip;

// Geometry of a line on the ground: the Ojo feet, the locked point, the screen length to the locked point (len0) and the
// screen length of the line itself (len): in TRACK it ends at the first wall before the hero, from LOCK on it runs to the
// first wall or column, which is the reach of the damage. The line of every Ojo slot is kept (LOCK to scar).
typedef struct { int ok, wx, wy, ax, ay, len0, len; } OjoGeo;

static OjoStrip s_strip[OJO_MAX_STRIPS];
static int s_strip_n;
static int s_strip_cam_x, s_strip_cam_y;
static OjoGeo s_geo[MAX_GAMEPLAY_ENEMIES];

static inline void strip_plot(uint16_t *buffer, int x, int y, uint16_t color) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    buffer[(y << 8) + x] = color;
    if (x < (int)s_row_x0[y]) s_row_x0[y] = (uint32_t)x;
    if (x >= (int)s_row_x1[y]) s_row_x1[y] = (uint32_t)(x + 1);
}

// Is the floor pixel (sx, sy) of the screen covered by a wall or column in front of ground depth `depth`?
static inline int hid_at(int sx, int sy, int depth) {
    return (unsigned)sx < SCREEN_W && (unsigned)sy < SCREEN_H &&
           world_pixel_hidden(sx + s_strip_cam_x, sy + s_strip_cam_y, depth);
}

// Fills the perpendicular offsets of a strip (one square root and two divisions per line), rounded to the nearest pixel.
static void strip_offsets(OjoStrip *S, int dir_x, int dir_y) {
    int m = (int)sqrt32(dir_x * dir_x + dir_y * dir_y);
    if (m < 1) m = 1;
    const int perp_x = div32(-dir_y * 256, m);
    const int perp_y = div32(dir_x * 256, m);
    for (int o = -OJO_OFF_CAP; o <= OJO_OFF_CAP; o++) {
        S->off_x[o + OJO_OFF_CAP] = (perp_x * o + 128) >> 8;
        S->off_y[o + OJO_OFF_CAP] = (perp_y * o + 128) >> 8;
    }
}

// Ground line from the Ojo feet (wx, wy) toward the point (ax, ay), cut at the first wall or column (true ground metric,
// 2:1). `ext` 0: it stops at the point (TRACK); 1: it runs on to the first wall or column (LOCK on), exactly the line that
// ojo_fire in enemy_ai.c measures for the damage (same origin, same unit vector, same march).
static int line_geo(OjoGeo *G, int wx, int wy, int ax, int ay, int ext) {
    G->ok = 0;
    const int dx = ax - wx, dy = ay - wy;
    const int len0 = (int)int_sqrt((uint32_t)(dx * dx + dy * dy));
    if (len0 < 2) return 0;
    const int gy2 = 2 * dy;
    const int glen = (int)int_sqrt((uint32_t)(dx * dx + gy2 * gy2));
    if (glen < 1) return 0;
    const int ux = div32(dx * 256, glen), uy = div32(gy2 * 256, glen);
    const int cut = ray_hit_dist(wx, wy, ux << 7, uy << 7, ext ? OJO_BEAM_MAX_LEN : glen);
    int len = cut >= glen && !ext ? len0 : div32(len0 * cut, glen);
    if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;
    if (len < 1) return 0;
    G->wx = wx; G->wy = wy; G->ax = ax; G->ay = ay; G->len0 = len0; G->len = len;
    G->ok = 1;
    return 1;
}

static int strip_prepare_line(OjoStrip *S, const OjoGeo *G, int ph, int a, int timer, int cam_x, int cam_y) {
    const int ox = G->wx - cam_x, oy = G->wy - cam_y;
    const int ux = div32((G->ax - G->wx) * 256, G->len0);
    const int uy = div32((G->ay - G->wy) * 256, G->len0);
    const int len = G->len;
    const int ex = ox + ((ux * len) >> 8), ey = oy + ((uy * len) >> 8);
    if ((ox < -8 && ex < -8) || (ox >= SCREEN_W + 8 && ex >= SCREEN_W + 8) ||
        (oy < -8 && ey < -8) || (oy >= SCREEN_H + 24 && ey >= SCREEN_H + 24)) return 0;
    S->ox = ox;
    S->oy = oy;
    S->ux = ux;
    S->uy = uy;
    S->lo = 1;
    S->hi = len;
    S->ph = ph;
    S->a = a;
    S->cd = 0;
    S->pulse = 0;
    if (ph == PH_TRACK) {                    // the tip advances toward the hero in OJO_TIP_FRAMES
        const int tip = a >= OJO_TIP_FRAMES ? len : (len * (a + 1) * 4681) >> 16;   // 4681 = 65536 / 14
        S->hi = tip < 1 ? 1 : tip;
    } else if (ph == PH_LOCK) {              // the light runs from the Ojo to the end of the line over the whole lock
        S->cd = (len * (a + 1) * 3277) >> 16;                                         // 3277 = 65536 / 20
        if (timer <= OJO_LOCK_BLINK_FRAMES) S->pulse = ((timer >> 1) & 1) ? 1 : 2;
    }
    strip_offsets(S, ux, uy);
    S->depth0 = G->wy;
    S->dgy = div32((G->ay - G->wy) * 256, G->len0);
    return 1;
}

// One column of the detonation rising from the floor pixel (cx, cy): height, then colours foot / middle / tip by level.
// The base pixel and the top pixel are tested against walls; if they agree the column is painted or skipped whole, if not
// (a wall edge crosses it) every pixel is tested.
static inline void blast_column(uint16_t *buffer, int cx, int cy, int h, int depth, int hid0, int lf, int lm, int lt) {
    if (h < 1) return;
    const int hidt = hid_at(cx, cy - h, depth);
    if (hid0 && hidt) return;
    const int mixed = hid0 != hidt;
    for (int i = 0; i < h; i++) {
        const int y = cy - 1 - i;
        if (mixed && hid_at(cx, y, depth)) continue;
        const int lvl = i * 3 < h ? lf : (i * 3 < 2 * h ? lm : lt);
        strip_plot(buffer, cx, y, s_ramp[lvl]);
    }
}

static inline void hline(uint16_t *buffer, int x0, int x1, int y, uint16_t col) {
    for (int x = x0; x <= x1; x++) strip_plot(buffer, x, y, col);
}

// The eye, 7x3 almond: es 0 closed (a 7 px slit), else open (dark inside with a bright pupil). Rare: not in ITCM.
__attribute__((noinline)) static void eye7(uint16_t *buffer, int px, int py, int es, int el) {
    const uint16_t ring = s_ramp[el];
    if (es == 0) { hline(buffer, px - 3, px + 3, py, ring); return; }
    hline(buffer, px - 2, px + 2, py - 1, ring);
    hline(buffer, px - 2, px + 2, py + 1, ring);
    strip_plot(buffer, px - 3, py, ring); strip_plot(buffer, px + 3, py, ring);
    hline(buffer, px - 2, px - 1, py, s_dark); hline(buffer, px + 1, px + 2, py, s_dark);
    strip_plot(buffer, px, py, s_ramp[4]);
}

// Paints steps d0..d1 of a line, each exactly once. The hot loop: ITCM when it fits (see the ITCM note in the report).
__attribute__((target("arm"), optimize("O2"))) OJO_DRAW_SECTION static void draw_line(uint16_t *buffer, const OjoStrip *S, int d0, int d1) {
    const int ux = S->ux, uy = S->uy, ph = S->ph, a = S->a, cd = S->cd, pulse = S->pulse, hi = S->hi;
    const int impact = ph == PH_BLAST && a < OJO_BEAM_IMPACT_FRAMES;
    const int fa = a - OJO_BEAM_HIT_FRAMES;                  // >= 0: dissipating (BLAST) or the scar first frames
    const int t_scar = a - OJO_SCAR_START;                   // frames since the crack began to go out (< 0: not yet)
    int fc = d0 + OJO_EYE_PERIOD - OJO_EYE_MARK;             // eye counter: 0 on the steps that carry an eye
    fc -= OJO_EYE_PERIOD * div32(fc, OJO_EYE_PERIOD);
    int fx = (S->ox << 8) + 128 + ux * d0;
    int fy = (S->oy << 8) + 128 + uy * d0;
    for (int d = d0; d <= d1; d++, fx += ux, fy += uy) {
        const int f0 = fc;
        if (++fc == OJO_EYE_PERIOD) fc = 0;
        const int px = fx >> 8, py = fy >> 8;
        if (px < -8 || px >= SCREEN_W + 8 || py < -32 || py >= SCREEN_H + 24) continue;
        const int depth = S->depth0 + ((S->dgy * d) >> 8);
        const int hid0 = hid_at(px, py, depth);
        const int g = s_hh[d & 63];

        // Level of the crack at this step, or dead (the scar goes out step by step, at its own time).
        int lvl, alive = 1, es = 0;
        if (ph == PH_TRACK) {
            lvl = g == 7 ? 1 : (g == 0 ? 3 : 2);
            if (d + 3 > hi) lvl = d == hi ? 4 : 3;           // the leading tip
        } else if (ph == PH_LOCK) {
            lvl = g == 7 ? 1 : (g == 0 ? 3 : 2);
            if (d <= cd) { lvl = 4; es = 2; }                // the light has reached this step (and opened this eye)
            if (pulse == 1) lvl = 4;
        } else {
            if (ph == PH_BLAST && t_scar < 0) { lvl = impact ? 4 : (3 + (((d + a) & 3) == 0)); es = 2; }
            else {
                const int te = 40 + (s_hh[(d * 7 + 3) & 63] << 2);       // this step goes out 40..68 frames after the scar began
                const int rem = te - t_scar;
                if (rem <= 0) { alive = 0; lvl = 0; }
                else lvl = rem > 30 ? 3 : (rem > 18 ? 2 : (rem > 8 ? 1 : 0));
                es = lvl >= 3 ? 2 : 0;
            }
        }

        const int o = s_walk[d & 63];
        const int cx = px + S->off_x[o + OJO_OFF_CAP];
        const int cy = py + S->off_y[o + OJO_OFF_CAP];
        if (alive && !hid0) {
            strip_plot(buffer, cx, cy, s_ramp[lvl]);
            if (ph != PH_TRACK && lvl >= 2)                    // 2 px core from the lock on (1 px while it follows)
                strip_plot(buffer, cx + S->off_x[1 + OJO_OFF_CAP], cy + S->off_y[1 + OJO_OFF_CAP], s_ramp[lvl]);
            if (impact) {                                      // the floor flashes wider for 3 frames
                strip_plot(buffer, cx - S->off_x[1 + OJO_OFF_CAP], cy - S->off_y[1 + OJO_OFF_CAP], s_ramp[3]);
                strip_plot(buffer, cx + S->off_x[2 + OJO_OFF_CAP], cy + S->off_y[2 + OJO_OFF_CAP], s_ramp[3]);
            }
            if (f0 == 0) eye7(buffer, px, py, es, lvl < 4 ? lvl + 1 : 4);     // the eye of this step, lit like the crack
        }

        // SENTENCE: the whole line blows up at once, a column of spectral flame per step.
        if (ph == PH_BLAST) {
            int ha, lf, lm, lt;
            if (impact) { ha = 11; lf = 4; lm = 3; lt = 2; }
            else if (fa < 0) { ha = 8 + ((a >> 1) & 1); lf = 3; lm = 2; lt = 1; }
            else { ha = 8 - fa; lf = 2; lm = 1; lt = 0; }
            int h = ha + g - 2;                                // flames with gaps
            if (((d + a) & 7) == 0) h = 1;
            if (fa >= 4 && (((d >> 1) + a) & 1)) h = 0;
            blast_column(buffer, cx, cy, h, depth, hid0, lf, lm, lt);
            if (!impact && h > 1 && (((d * 13 + a * 3) & 15) == 2) && !hid0)      // motes
                strip_plot(buffer, cx, cy - h - 2 - ((a * 3 + d) & 7), s_ramp[3]);
        }
    }
}

// Prepares every Ojo line (TRACK, LOCK, SENTENCE and the scar of the last sentence) once per frame, for one screen.
void enemy_lasers_begin(const Enemy *enemies, int count, int cam_x, int cam_y) {
    s_strip_n = 0;
    if (!enemies) return;
    s_fx_tick++;
    s_strip_cam_x = cam_x;
    s_strip_cam_y = cam_y;
    const int cool = g_enemy_tuning[ENEMY_TYPE_SHOOTER].attack_cooldown;
    for (int i = 0; i < count && s_strip_n < OJO_MAX_STRIPS; i++) {
        const Enemy *e = &enemies[i];
        const int slot = i < MAX_GAMEPLAY_ENEMIES;
        if (!e->active || e->type != ENEMY_TYPE_SHOOTER) {
            if (slot) s_geo[i].ok = 0;
            continue;
        }
        const int wx = TO_INT(e->x), wy = TO_INT(e->y);
        OjoGeo tmp;
        const OjoGeo *G = 0;
        int ph = -1, a = 0;
        if (e->state == ENEMY_STATE_TRACK) {
            if (slot) s_geo[i].ok = 0;                                // LOCK measures the line to the wall afresh
            if (line_geo(&tmp, wx, wy, e->aim_px, e->aim_py, 0)) { G = &tmp; ph = PH_TRACK; a = OJO_TRACK_FRAMES - e->state_timer; }
        } else if (e->state == ENEMY_STATE_LOCK || e->state == ENEMY_STATE_SENTENCE) {
            if (slot) {                                               // the fixed line, feet to wall: measured once per lock
                OjoGeo *K = &s_geo[i];
                if (!K->ok || K->wx != wx || K->wy != wy || K->ax != e->aim_px || K->ay != e->aim_py)
                    line_geo(K, wx, wy, e->aim_px, e->aim_py, 1);
                if (K->ok) G = K;
            } else if (line_geo(&tmp, wx, wy, e->aim_px, e->aim_py, 1)) G = &tmp;
            if (e->state == ENEMY_STATE_LOCK) { ph = PH_LOCK; a = OJO_LOCK_FRAMES - e->state_timer; }
            else { ph = PH_BLAST; a = OJO_BEAM_FRAMES - e->state_timer; }
        } else if (e->state == ENEMY_STATE_COOLDOWN && slot && s_geo[i].ok) {
            a = OJO_BEAM_FRAMES + cool - e->state_timer;
            if (a < OJO_SCAR_END) { G = &s_geo[i]; ph = PH_SCAR; }
        }
        if (!G) continue;
        if (a < 0) a = 0;
        if (strip_prepare_line(&s_strip[s_strip_n], G, ph, a, e->state_timer, cam_x, cam_y)) s_strip_n++;
    }
    if (s_strip_n > 0)
        for (int y = 0; y < SCREEN_H; y++) { s_row_x0[y] = SCREEN_W; s_row_x1[y] = 0; }
}

// Paints, for every prepared strip, the steps still unpainted whose ground depth is smaller than `depth` (further from
// the camera than an actor standing at that depth). The painter loop calls it before each sorted actor.
void enemy_lasers_draw_before(uint16_t *buffer, int depth) {
    for (int i = 0; i < s_strip_n; i++) {
        OjoStrip *S = &s_strip[i];
        if (S->lo > S->hi) continue;
        const int k = depth - S->depth0;
        if (S->dgy > 0) {                          // depth grows with the step: steps d <= maxd are further than `depth`
            const int maxd = k <= 0 ? 0 : div32(256 * k + S->dgy - 1, S->dgy) - 1;
            const int b = maxd < S->hi ? maxd : S->hi;
            if (S->lo <= b) { draw_line(buffer, S, S->lo, b); S->lo = b + 1; }
        } else if (S->dgy == 0) {                  // the whole line is at one depth
            if (k > 0) { draw_line(buffer, S, S->lo, S->hi); S->lo = S->hi + 1; }
        } else {                                   // it runs away from the camera: the far end is the first to be covered
            const int mind = k > 0 ? 1 : div32(256 * -k, -S->dgy) + 1;
            const int a = mind > S->lo ? mind : S->lo;
            if (a <= S->hi) { draw_line(buffer, S, a, S->hi); S->hi = a - 1; }
        }
    }
}

// After the last actor: paints what is left (the steps in front of everybody), then marks the touched rows once.
void enemy_lasers_end(uint16_t *buffer) {
    if (s_strip_n <= 0) return;
    for (int i = 0; i < s_strip_n; i++) {
        OjoStrip *S = &s_strip[i];
        if (S->lo <= S->hi) { draw_line(buffer, S, S->lo, S->hi); S->lo = S->hi + 1; }
    }
    for (int y = 0; y < SCREEN_H; y++)
        if (s_row_x1[y] > s_row_x0[y]) dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);
    s_strip_n = 0;
}

// ---------------------------------------------------------------------------
// The lantern (top of the body) and the mouth of the hand-held head, drawn over the Ojo sprite.
//   searching (CHASE, POSITION, COOLDOWN): the lantern flickers faintly, 1-3 pixels, slowly.
//   TRACK: an 8-frame flash ("he has seen you"): a bright core and a halo ring that opens 2 to 9 px; then a steady glow.
//   LOCK: steady, pulsing with the line at the end. SENTENCE: a short flash on the mouth of the head (nothing is fired).
// ---------------------------------------------------------------------------
static void lantern_ring(uint16_t *buffer, int lx, int ly, int cam_x, int cam_y, int depth, int r, uint16_t col) {
    for (int k = 0; k < 32; k++) {
        const int x = lx + ((s_cos32[k] * r + 128) >> 8);
        const int y = ly + ((s_cos32[(k + 24) & 31] * r + 128) >> 8);
        plot_occ_px(buffer, x, y, cam_x, cam_y, depth, col);
    }
}

static void draw_lantern(uint16_t *buffer, const Enemy *e, int idx, int cam_x, int cam_y, int depth) {
    const uint16_t *ramp = s_ramp;
    const int lx = TO_INT(e->x) - cam_x;
    const int ly = TO_INT(e->y) - OJO_LANTERN_HEIGHT - cam_y;
    if (e->state == ENEMY_STATE_TRACK) {
        const int age = OJO_TRACK_FRAMES - e->state_timer;
        if (age < OJO_FLASH_FRAMES) {
            const int r = 3 + age + (age >> 1);                     // the ring opens from 3 to 13 px
            const int lv = age < 2 ? 4 : (age < 4 ? 3 : (age < 6 ? 2 : 1));
            if (age < 4)                                            // a dithered pale disc under the ring while it is young
                for (int dy = -5; dy <= 5; dy++)
                    for (int dx = -5; dx <= 5; dx++)
                        if (dx * dx + dy * dy <= 25 && ((dx + dy) & 1) == 0)
                            plot_occ_px(buffer, lx + dx, ly + dy, cam_x, cam_y, depth, ramp[age < 2 ? 3 : 2]);
            lantern_ring(buffer, lx, ly, cam_x, cam_y, depth, r, ramp[lv]);
            lantern_ring(buffer, lx, ly, cam_x, cam_y, depth, r - 1, ramp[lv > 1 ? lv - 1 : 1]);
            if (age < 6) {                                          // a 3x3 core with long arms, shrinking
                for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                        plot_occ_px(buffer, lx + dx, ly + dy, cam_x, cam_y, depth, ramp[(dx | dy) == 0 ? 4 : 3]);
                const int arm = age < 3 ? 5 : 3;
                for (int k = 2; k <= arm; k++) {
                    plot_occ_px(buffer, lx - k, ly, cam_x, cam_y, depth, ramp[4 - (k >> 1)]);
                    plot_occ_px(buffer, lx + k, ly, cam_x, cam_y, depth, ramp[4 - (k >> 1)]);
                    plot_occ_px(buffer, lx, ly - k, cam_x, cam_y, depth, ramp[4 - (k >> 1)]);
                    plot_occ_px(buffer, lx, ly + k, cam_x, cam_y, depth, ramp[4 - (k >> 1)]);
                }
            } else {
                plot_occ_px(buffer, lx, ly, cam_x, cam_y, depth, ramp[3]);
            }
        } else {                                                    // steady glow: a small plus
            plot_occ_px(buffer, lx, ly, cam_x, cam_y, depth, ramp[3]);
            plot_occ_px(buffer, lx - 1, ly, cam_x, cam_y, depth, ramp[2]);
            plot_occ_px(buffer, lx + 1, ly, cam_x, cam_y, depth, ramp[2]);
            plot_occ_px(buffer, lx, ly - 1, cam_x, cam_y, depth, ramp[2]);
            plot_occ_px(buffer, lx, ly + 1, cam_x, cam_y, depth, ramp[2]);
        }
    } else if (e->state == ENEMY_STATE_LOCK) {
        const int on = e->state_timer > OJO_LOCK_BLINK_FRAMES || ((e->state_timer >> 1) & 1);
        plot_occ_px(buffer, lx, ly, cam_x, cam_y, depth, ramp[on ? 4 : 3]);
        plot_occ_px(buffer, lx - 1, ly, cam_x, cam_y, depth, ramp[on ? 3 : 2]);
        plot_occ_px(buffer, lx + 1, ly, cam_x, cam_y, depth, ramp[on ? 3 : 2]);
        plot_occ_px(buffer, lx, ly - 1, cam_x, cam_y, depth, ramp[on ? 3 : 2]);
        plot_occ_px(buffer, lx, ly + 1, cam_x, cam_y, depth, ramp[on ? 3 : 2]);
    } else if (e->state == ENEMY_STATE_CHASE || e->state == ENEMY_STATE_POSITION || e->state == ENEMY_STATE_COOLDOWN) {
        const int ph = ((s_fx_tick >> 3) + idx * 5) & 7;            // slow: ~8 frames per step
        if (ph < 5) plot_occ_px(buffer, lx, ly, cam_x, cam_y, depth, ramp[1]);
        if (ph == 1 || ph == 2 || ph == 5) plot_occ_px(buffer, lx, ly - 1, cam_x, cam_y, depth, ramp[2]);
        if (ph == 3 || ph == 4) plot_occ_px(buffer, lx + 1, ly, cam_x, cam_y, depth, ramp[1]);
    }
}

void enemy_ojo_mouth_glow_render(uint16_t *buffer, const Enemy *e, int idx, int cam_x, int cam_y, int depth) {
    if (!buffer || !e) return;
    const uint16_t *ramp = s_ramp;
    if (e->state != ENEMY_STATE_SENTENCE) { draw_lantern(buffer, e, idx, cam_x, cam_y, depth); return; }

    const int age = OJO_BEAM_FRAMES - e->state_timer;
    if (age < 0 || age >= 8) return;                                // a short flash, then the mouth is just a mouth
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    const int cx = TO_INT(mx) - cam_x;
    const int cy = TO_INT(my) - mh - cam_y;
    if (age < OJO_BEAM_IMPACT_FRAMES) {                              // 3x3 flash with arms
        for (int dy = -1; dy <= 1; dy++)
            for (int dx = -1; dx <= 1; dx++)
                plot_occ_px(buffer, cx + dx, cy + dy, cam_x, cam_y, depth, ramp[(dx | dy) == 0 ? 4 : 3]);
        plot_occ_px(buffer, cx - 3, cy, cam_x, cam_y, depth, ramp[2]);
        plot_occ_px(buffer, cx + 3, cy, cam_x, cam_y, depth, ramp[2]);
        plot_occ_px(buffer, cx, cy - 3, cam_x, cam_y, depth, ramp[2]);
        plot_occ_px(buffer, cx, cy + 3, cam_x, cam_y, depth, ramp[1]);
        plot_occ_px(buffer, cx - 2, cy - 2, cam_x, cam_y, depth, ramp[1]);
        plot_occ_px(buffer, cx + 2, cy - 2, cam_x, cam_y, depth, ramp[1]);
    } else {                                                         // fading cross
        const int l = age < 5 ? 3 : 2;
        plot_occ_px(buffer, cx, cy, cam_x, cam_y, depth, ramp[l]);
        plot_occ_px(buffer, cx - 1, cy, cam_x, cam_y, depth, ramp[l - 1]);
        plot_occ_px(buffer, cx + 1, cy, cam_x, cam_y, depth, ramp[l - 1]);
        plot_occ_px(buffer, cx, cy - 1, cam_x, cam_y, depth, ramp[l - 1]);
        plot_occ_px(buffer, cx, cy + 1, cam_x, cam_y, depth, ramp[l - 2]);
    }
}
