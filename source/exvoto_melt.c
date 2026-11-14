#include "exvoto_melt.h"
#include <nds.h>
#include <string.h>

// Integer only (no float, no division in pixel loops). Colours are BGR555 without the alpha bit; the
// groundfx primitives add it, clip to the screen and skip the pixels a wall in front hides.
#define MELT_FILL RGB15(24, 22, 18)      // pale wax, desaturated
#define MELT_MID  RGB15(19, 17, 14)      // cooler/darker wax pooling
#define MELT_HIGH RGB15(27, 25, 21)      // subtle tallow sheen
#define MELT_RIM  RGB15(9, 8, 7)         // dark rim

static ExvotoMelt s_melt[EXVOTO_MELT_MAX];
static int s_melt_next;                  // slot replaced when the pool is full (round robin)

static uint32_t melt_hash(uint32_t x) {
    x ^= x >> 16;
    x *= 0x85ebca6bu;
    x ^= x >> 13;
    x *= 0xc2b2ae35u;
    return x ^ (x >> 16);
}

void exvoto_melt_reset(void) {
    for (int i = 0; i < EXVOTO_MELT_MAX; i++) s_melt[i].age = -1;
    s_melt_next = 0;
}

void exvoto_melt_spawn(const Enemy *e) {
    int slot = -1;
    for (int i = 0; i < EXVOTO_MELT_MAX; i++) {
        if (s_melt[i].age < 0) { slot = i; break; }
    }
    if (slot < 0) {
        slot = s_melt_next;
        s_melt_next = (s_melt_next + 1) % EXVOTO_MELT_MAX;
    }
    ExvotoMelt *m = &s_melt[slot];
    m->x = e->x;
    m->y = e->y;
    m->age = 0;
    m->char_id = e->char_id;
    m->dir = e->dir;
    m->frame = e->frame;
    m->seed = melt_hash((uint32_t)e->x ^ ((uint32_t)e->y << 7) ^ ((uint32_t)e->dir << 19) ^ (uint32_t)slot);
}

void exvoto_melt_update(void) {
    for (int i = 0; i < EXVOTO_MELT_MAX; i++) {
        ExvotoMelt *m = &s_melt[i];
        if (m->age < 0) continue;
        if (++m->age >= EXVOTO_MELT_POOL_FRAMES) m->age = -1;
    }
}

void exvoto_melt_shift_y(int dy_px) {
    fixed shift = TO_FIXED(dy_px);
    for (int i = 0; i < EXVOTO_MELT_MAX; i++)
        if (s_melt[i].age >= 0) s_melt[i].y += shift;
}

const ExvotoMelt *exvoto_melt_sinking(int i) {
    if (i < 0 || i >= EXVOTO_MELT_MAX) return 0;
    const ExvotoMelt *m = &s_melt[i];
    return (m->age >= 0 && m->age < EXVOTO_MELT_SINK_FRAMES) ? m : 0;
}

int exvoto_melt_hidden_rows(const ExvotoMelt *m, int bh) {
    return (bh * m->age) / EXVOTO_MELT_SINK_FRAMES;       // constant divisor, a handful of calls per frame
}

void exvoto_melt_render_floor(const GroundTarget *g) {
    // 4 asymmetric lobe directions in 2:1 ground metric (dx, dy) + 1 central core.
    static const int8_t lobe_dx[4] = { 1, -1, 1, -1 };
    static const int8_t lobe_dy[4] = { -1, -1, 1, 1 };

    for (int i = 0; i < EXVOTO_MELT_MAX; i++) {
        const ExvotoMelt *m = &s_melt[i];
        if (m->age < 0) continue;
        int cx = TO_INT(m->x), cy = TO_INT(m->y);
        // Cheap reject: lobes can extend a few px beyond EXVOTO_MELT_RADIUS.
        const int margin = EXVOTO_MELT_RADIUS + 8;
        int sx = cx - g->cam_x, sy = cy - g->cam_y;
        if (sx < -margin || sx > SCREEN_W + margin ||
            sy < -margin || sy > SCREEN_H + margin) continue;

        int r = EXVOTO_MELT_RADIUS;
        if (m->age < EXVOTO_MELT_SINK_FRAMES)             // spreads while the body sinks
            r = 4 + ((EXVOTO_MELT_RADIUS - 4) * m->age) / EXVOTO_MELT_SINK_FRAMES;
        int pattern = GFX_FILL_SOLID;
        if (m->age >= EXVOTO_MELT_FADE_START) pattern = GFX_FILL_CHECKER;
        if (m->age >= EXVOTO_MELT_SHRINK_START)
            r = EXVOTO_MELT_RADIUS -
                ((EXVOTO_MELT_RADIUS / 2) * (m->age - EXVOTO_MELT_SHRINK_START)) /
                (EXVOTO_MELT_POOL_FRAMES - EXVOTO_MELT_SHRINK_START);
        if (r < 3) continue;

        // Deterministic lobe offsets/radii scaled to current radius r (no float).
        uint32_t s = m->seed;
        int lx[5], ly[5], lr[5];
        lx[0] = cx;
        ly[0] = cy;
        lr[0] = (r * 3) >> 2;
        if (lr[0] < 3) lr[0] = 3;
        for (int k = 0; k < 4; k++) {
            int rot = (int)((s >> (k * 3)) & 3u);
            int idx = (k + rot) & 3;
            int dist = 2 + (int)((s >> (12 + k * 2)) & 3u);          // 2..5 at full size
            int ox = lobe_dx[idx] * ((dist * r) / EXVOTO_MELT_RADIUS);
            int oy = lobe_dy[idx] * (((dist + 1) * r) / (EXVOTO_MELT_RADIUS * 2));
            if (ox == 0) ox = lobe_dx[idx];
            lx[k + 1] = cx + ox;
            ly[k + 1] = cy + oy;
            int lrad = (r * (5 + (int)((s >> (20 + k * 2)) & 3u))) / 10;  // 0.5r..0.8r
            lr[k + 1] = lrad < 2 ? 2 : lrad;
        }

        // Dark 1-px rim underneath the irregular silhouette when solid.
        if (pattern == GFX_FILL_SOLID) {
            for (int k = 0; k < 5; k++)
                gfx_ground_disc(g, lx[k], ly[k], lr[k] + 1, MELT_RIM, GFX_FILL_SOLID, 0);
        }
        // Main pale wax body.
        for (int k = 0; k < 5; k++)
            gfx_ground_disc(g, lx[k], ly[k], lr[k], MELT_FILL, pattern, 0);

        // Internal wax texture: cooler pool + tallow highlight + stray droplets near the edge.
        if (pattern == GFX_FILL_SOLID && r >= 6) {
            int mx = lx[1] + ((lx[0] - lx[1]) >> 1);
            int my = ly[1] + ((ly[0] - ly[1]) >> 1);
            gfx_ground_disc(g, mx, my, (r * 5) / 10, MELT_MID, GFX_FILL_HATCH, (int)(s & 3u));
            int hx = lx[2] + ((lx[0] - lx[2]) >> 1);
            int hy = ly[2] + ((ly[0] - ly[2]) >> 1);
            gfx_ground_disc(g, hx, hy, (r * 3) / 10, MELT_HIGH, GFX_FILL_CHECKER, 0);

            for (int d = 0; d < 3; d++) {
                int dir = (int)((s >> (24 + d * 2)) & 3u);
                int dx = lobe_dx[dir] * (r + 1 + (d & 1));
                int dy = lobe_dy[dir] * ((r >> 1) + 1);
                gfx_ground_px(g, cx + dx, cy + dy, MELT_RIM);
                gfx_ground_px(g, cx + dx - lobe_dx[dir], cy + dy, MELT_FILL);
            }
        }
    }
}
