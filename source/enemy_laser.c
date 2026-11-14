#include "enemy_laser.h"
#include "enemy_ai.h"
#include "groundfx.h"
#include "arena.h"
#include <nds.h>

// Desaturated verdigris palette (DESIGN.md 6.10 "Efectos desaturados"): same role and peak brightness as the
// hero's FX_SH_* (ivory 29,25,19 ... deep 9,3,3), tinted green only by a few points; contrast by value.
#define OJO_FX_CORE   (RGB15(24, 27, 20) | BIT(15))   // pale bone-phosphor (peak)
#define OJO_FX_HI     (RGB15(16, 21, 14) | BIT(15))   // oxidized verdigris
#define OJO_FX_MID    (RGB15(10, 15, 9) | BIT(15))    // cathedral moss
#define OJO_FX_DIM    (RGB15(6, 10, 6) | BIT(15))     // spectral smoke
#define OJO_FX_DARK   (RGB15(3, 6, 4) | BIT(15))      // faint shadow

static uint32_t s_row_x0[SCREEN_H], s_row_x1[SCREEN_H];
static int s_fx_tick = 0;
static inline uint32_t int_sqrt(uint32_t n) { return (uint32_t)sqrt32((int)n); }

// Small integer sine table (16 steps, -128..128) for organic wave motion (fixed-point integer).
static const int8_t s_wave16[16] = {
    0, 49, 90, 118, 127, 118, 90, 49, 0, -49, -90, -118, -127, -118, -90, -49
};

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
    plot_occ_px(buffer, cx, cy, cam_x, cam_y, depth, age <= 1 ? OJO_FX_CORE : OJO_FX_HI);
    plot_occ_px(buffer, cx - spread, cy - 1, cam_x, cam_y, depth, OJO_FX_HI);
    plot_occ_px(buffer, cx + spread, cy + 1, cam_x, cam_y, depth, OJO_FX_HI);
    plot_occ_px(buffer, cx + 1, cy - spread, cam_x, cam_y, depth, OJO_FX_MID);
    plot_occ_px(buffer, cx - 1, cy + spread, cam_x, cam_y, depth, OJO_FX_MID);
    if (age <= 2) {
        plot_occ_px(buffer, cx, cy - spread - 1, cam_x, cam_y, depth, OJO_FX_DIM);
    }
}

__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void draw_laser(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    int ox = TO_INT(mx) - cam_x;
    int oy = TO_INT(my) - mh - cam_y;
    int dir_x = e->aim_dir_x;
    int dir_y = e->aim_dir_y;

    int len = e->beam_len;
    if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;
    if (len < 1) return;
    int ex = ox + ((dir_x * len) >> 8);
    int ey = oy + ((dir_y * len) >> 8);
    if ((ox < -8 && ex < -8) || (ox >= SCREEN_W + 8 && ex >= SCREEN_W + 8) ||
        (oy < -8 && ey < -8) || (oy >= SCREEN_H + 8 && ey >= SCREEN_H + 8)) return;

    int age = OJO_BEAM_FRAMES - e->state_timer;
    if (age < 0) age = 0;

    int m2 = dir_x * dir_x + dir_y * dir_y;
    int m = 1;
    while ((m + 1) * (m + 1) <= m2) m++;
    int perp_x = (-dir_y * 256) / m;
    int perp_y = (dir_x * 256) / m;

    for (int y = 0; y < SCREEN_H; y++) { s_row_x0[y] = SCREEN_W; s_row_x1[y] = 0; }

    int fx = (ox << 8) + 128;
    int fy = (oy << 8) + 128;
    const int base_y = TO_INT(e->y);

    for (int d = 1; d <= len; d++) {
        fx += dir_x;
        fy += dir_y;
        int px = fx >> 8;
        int py = fy >> 8;
        if (px < -4 || px >= SCREEN_W + 4 || py < -4 || py >= SCREEN_H + 4) continue;

        // Ground depth along the beam for proper wall/pillar occlusion.
        int depth = base_y + ((dir_y * d) >> 8);
        if (depth < base_y) depth = base_y;

        // Maleficio: tapered spectral ribbon with subtle wave + rising smoke wisps.
        int wave_idx = ((d >> 2) + age * 2) & 15;
        int w_off = (s_wave16[wave_idx] * (d < 24 ? 1 : 2)) >> 8;
        int cx = px + ((perp_x * w_off) >> 8);
        int cy = py + ((perp_y * w_off) >> 8);
        uint16_t core_col = (age <= 2) ? OJO_FX_CORE : (age <= 4 ? OJO_FX_HI : OJO_FX_MID);
        if ((age <= 4 || (d & 1) == 0) && (unsigned)cx < SCREEN_W && (unsigned)cy < SCREEN_H) {
            if (!world_pixel_hidden(cx + cam_x, cy + cam_y, depth)) {
                buffer[(cy << 8) + cx] = core_col;
                if (cx < (int)s_row_x0[cy]) s_row_x0[cy] = (uint32_t)cx;
                if (cx >= (int)s_row_x1[cy]) s_row_x1[cy] = (uint32_t)(cx + 1);
            }
        }
        // Thicker near the screaming mouth, tapering to 1 px toward the target.
        if (age <= 3 && d < (len >> 1)) {
            uint16_t rim = (d < (len >> 2)) ? OJO_FX_HI : OJO_FX_MID;
            for (int s = -1; s <= 1; s += 2) {
                if (((d + s + age) & 1) && d > 16) continue;
                int rx = cx + ((perp_x * s) >> 8);
                int ry = cy + ((perp_y * s) >> 8);
                if ((unsigned)rx < SCREEN_W && (unsigned)ry < SCREEN_H &&
                    !world_pixel_hidden(rx + cam_x, ry + cam_y, depth)) {
                    buffer[(ry << 8) + rx] = rim;
                    if (rx < (int)s_row_x0[ry]) s_row_x0[ry] = (uint32_t)rx;
                    if (rx >= (int)s_row_x1[ry]) s_row_x1[ry] = (uint32_t)(rx + 1);
                }
            }
        }
        // Trailing spectral smoke wisps peeling upward every ~10 px.
        if ((d % 10) == ((age * 3) % 10)) {
            int sy = cy - 1 - (age >> 1);
            if ((unsigned)cx < SCREEN_W && (unsigned)sy < SCREEN_H &&
                !world_pixel_hidden(cx + cam_x, sy + cam_y, depth)) {
                buffer[(sy << 8) + cx] = OJO_FX_DIM;
                if (cx < (int)s_row_x0[sy]) s_row_x0[sy] = (uint32_t)cx;
                if (cx >= (int)s_row_x1[sy]) s_row_x1[sy] = (uint32_t)(cx + 1);
            }
        }
    }
    for (int y = 0; y < SCREEN_H; y++)
        if (s_row_x1[y] > s_row_x0[y]) dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);

    // Chest impact ember burst (occluded by walls in front).
    if (age <= 3) {
        int end_depth = base_y + ((dir_y * len) >> 8);
        if (end_depth < base_y) end_depth = base_y;
        draw_ember_burst(buffer, ex, ey, cam_x, cam_y, end_depth, age);
    }
}

// ---------------------------------------------------------------------------
// 2) Collimating gaze band: lantern -> hero's chest (TRACK follows him, LOCK keeps the line frozen)
// ---------------------------------------------------------------------------
#define OJO_LANTERN_HEIGHT 30     // px above the Ojo's feet: the lantern at the top of the body
#define OJO_BAND_HALF 6           // px half-width of the band when it is first spotted

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

static inline void band_plot(uint16_t *buffer, int sx, int sy, uint16_t color) {
    if ((unsigned)sx >= SCREEN_W || (unsigned)sy >= SCREEN_H) return;
    buffer[(sy << 8) + sx] = color;
    if (sx < (int)s_row_x0[sy]) s_row_x0[sy] = (uint32_t)sx;
    if (sx >= (int)s_row_x1[sy]) s_row_x1[sy] = (uint32_t)(sx + 1);
}

// The band is a column of pixels across the line, wide + dithered at first and one bright pixel at the end
// (the hero sniper's collimation A1 in the Ojo's desaturated verdigris ramp). It stops at the first wall or
// column on the ground line and is hidden by walls in front of it. Bounded: at most OJO_BEAM_MAX_LEN steps of
// (2 * half + 1) pixels, one perpendicular and a handful of divisions per band.
__attribute__((target("arm"), optimize("O3"))) ITCM_CODE static void draw_gaze_band(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
    const int wx = TO_INT(e->x), wy = TO_INT(e->y);
    const int ox = wx - cam_x;
    const int oy = wy - OJO_LANTERN_HEIGHT - cam_y;
    const int ex = e->aim_px - cam_x;
    const int ey = e->aim_py - OJO_TARGET_HEIGHT - cam_y;
    const int dx = ex - ox, dy = ey - oy;
    int len0 = (int)int_sqrt((uint32_t)(dx * dx + dy * dy));
    if (len0 < 2) return;
    int len = len0;

    // Cut at the first wall or column along the true ground line (2:1 metric) toward the hero.
    const int gx = e->aim_px - wx, gy2 = 2 * (e->aim_py - wy);
    const int glen = (int)int_sqrt((uint32_t)(gx * gx + gy2 * gy2));
    if (glen >= 8) {
        int cut = ray_hit_dist(wx, wy, div32(gx << 15, glen), div32(gy2 << 15, glen), glen);
        if (cut < glen) len = div32(len0 * cut, glen);
    }
    if (len > OJO_BEAM_MAX_LEN) len = OJO_BEAM_MAX_LEN;
    if (len < 1) return;

    const int ux = div32(dx * 256, len0);               // unit direction, 8.8, on the screen
    const int uy = div32(dy * 256, len0);
    const int ex2 = ox + ((ux * len) >> 8), ey2 = oy + ((uy * len) >> 8);
    if ((ox < -8 && ex2 < -8) || (ox >= SCREEN_W + 8 && ex2 >= SCREEN_W + 8) ||
        (oy < -8 && ey2 < -8) || (oy >= SCREEN_H + 8 && ey2 >= SCREEN_H + 8)) return;
    const int dgy = div32((e->aim_py - wy) * 256, len0);  // ground y advanced per step, for the occlusion depth

    const int prog = ojo_aim_progress(e);
    const int w = (OJO_BAND_HALF * (256 - prog)) >> 8;    // 6 at the start, 0 on the last frame of the lock
    const uint16_t centre = prog >= 160 ? OJO_FX_CORE : OJO_FX_HI;
    const int tick = s_fx_tick;

    for (int y = 0; y < SCREEN_H; y++) { s_row_x0[y] = SCREEN_W; s_row_x1[y] = 0; }

    int fx = (ox << 8) + 128;
    int fy = (oy << 8) + 128;
    for (int d = 1; d <= len; d++) {
        fx += ux;
        fy += uy;
        const int px = fx >> 8, py = fy >> 8;
        if (px < -8 || px >= SCREEN_W + 8 || py < -8 || py >= SCREEN_H + 8) continue;
        const int depth = wy + ((dgy * d) >> 8);
        if ((unsigned)px < SCREEN_W && (unsigned)py < SCREEN_H && world_pixel_hidden(px + cam_x, py + cam_y, depth)) continue;

        if (w == 0) {                                   // armed: a 1 px line that blinks bone / verdigris
            band_plot(buffer, px, py, ((tick >> 1) & 1) ? OJO_FX_CORE : OJO_FX_HI);
            continue;
        }
        for (int o = -w; o <= w; o++) {
            const int x = px + ((-uy * o) >> 8);
            const int y = py + ((ux * o) >> 8);
            const int ao = o < 0 ? -o : o;
            if (o == 0) band_plot(buffer, x, y, centre);
            else if (ao == w) { if (((x * 3 + y * 5 + tick) & 3) == 0) band_plot(buffer, x, y, OJO_FX_DIM); }
            else if (ao * 2 >= w) { if (((x + y + tick) & 1) == 0) band_plot(buffer, x, y, OJO_FX_MID); }
            else band_plot(buffer, x, y, OJO_FX_HI);
        }
    }
    for (int y = 0; y < SCREEN_H; y++)
        if (s_row_x1[y] > s_row_x0[y]) dirty_row(y, (int)s_row_x0[y], (int)s_row_x1[y]);
}

// Every Ojo's band (TRACK, LOCK) or sentence beam (SENTENCE), under the actor sprites.
void enemy_lasers_render(uint16_t *buffer, const Enemy *enemies, int count, int cam_x, int cam_y) {
    if (!buffer || !enemies) return;
    s_fx_tick++;
    for (int i = 0; i < count; i++) {
        const Enemy *e = &enemies[i];
        if (!e->active || e->type != ENEMY_TYPE_SHOOTER) continue;
        if (e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK) draw_gaze_band(buffer, e, cam_x, cam_y);
        else if (e->state == ENEMY_STATE_SENTENCE) draw_laser(buffer, e, cam_x, cam_y);
    }
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
        if (age >= 0 && age <= 3) draw_ember_burst(buffer, cx, cy, cam_x, cam_y, depth, age);
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

