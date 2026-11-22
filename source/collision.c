#include "collision.h"
#include "arena.h"
#include <nds/ndstypes.h>

// Extra ground rectangles (room fixtures). They only count while the arena that registered them is
// the current one, so leaving the rooms drops them without any explicit reset.
#define COLLISION_EXTRA_MAX 8
typedef struct { int x0, y0, x1, y1; } ExtraBlock;
static ExtraBlock s_extra[COLLISION_EXTRA_MAX];
static int s_extra_n = 0;
static const Arena *s_extra_arena = 0;

void collision_extra_begin(void) {
    s_extra_n = 0;
    s_extra_arena = g_arena;
}

void collision_extra_add(int x0, int y0, int x1, int y1) {
    if (s_extra_n >= COLLISION_EXTRA_MAX) return;
    s_extra[s_extra_n].x0 = x0; s_extra[s_extra_n].y0 = y0;
    s_extra[s_extra_n].x1 = x1; s_extra[s_extra_n].y1 = y1;
    s_extra_n++;
}

// ---------------------------------------------------------------------------
// World Collision
//
// The baked grid is the only walkability source: the lab exports floor that is
// reachable and free of any geometry inside the body slab, so dark render
// pixels never act as invisible walls.
// ---------------------------------------------------------------------------

static inline uint8_t world_collision_flags(int cx, int cy) {
    uint32_t index = (uint32_t)cy * g_arena->collision_w + (uint32_t)cx;
    return (g_arena->collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

// The body footprint is a circle on the ground (radius 6), which the 2:1
// projection turns into an ellipse of 6 x 3 screen pixels.
ITCM_CODE int position_is_free(fixed x, fixed y) {
    int wx = (int)(x >> FIXED_SHIFT);
    int wy = (int)(y >> FIXED_SHIFT);
    const int radius = 6;
    const int radius_y = radius >> GROUND_Y_SHIFT;
    if (wx - radius < 0 || wy - radius_y < 0) return 0;

    int cell_x0 = (wx - radius) / COLLISION_SCALE;
    int cell_x1 = (wx + radius) / COLLISION_SCALE;
    int cell_y0 = (wy - radius_y) / COLLISION_SCALE;
    int cell_y1 = (wy + radius_y) / COLLISION_SCALE;
    const int radius_sq = radius * radius;
    for (int cy = cell_y0; cy <= cell_y1; cy++) {
        for (int cx = cell_x0; cx <= cell_x1; cx++) {
            if (cx < 0 || cx >= g_arena->collision_w || cy < 0 || cy >= g_arena->collision_h) return 0;
            if (world_collision_flags(cx, cy) == 0) continue;     // 1, 2 (low cover) and 3 all stop bodies
            int left = cx * COLLISION_SCALE;
            int top = cy * COLLISION_SCALE;
            int nearest_x = wx < left ? left : (wx > left + COLLISION_SCALE - 1 ? left + COLLISION_SCALE - 1 : wx);
            int nearest_y = wy < top ? top : (wy > top + COLLISION_SCALE - 1 ? top + COLLISION_SCALE - 1 : wy);
            int dx = wx - nearest_x;
            int dy = wy - nearest_y;
            if (dx * dx + GROUND_DY2(dy) <= radius_sq) return 0;
        }
    }
    if (s_extra_arena == g_arena) {
        for (int i = 0; i < s_extra_n; i++) {
            int nx = wx < s_extra[i].x0 ? s_extra[i].x0 : (wx > s_extra[i].x1 ? s_extra[i].x1 : wx);
            int ny = wy < s_extra[i].y0 ? s_extra[i].y0 : (wy > s_extra[i].y1 ? s_extra[i].y1 : wy);
            int dx = wx - nx;
            int dy = wy - ny;
            if (dx * dx + GROUND_DY2(dy) <= radius_sq) return 0;
        }
    }
    return 1;
}

int bullet_position_is_free(fixed x, fixed y) {
    int px = (int)(x >> FIXED_SHIFT);
    int py = (int)(y >> FIXED_SHIFT);
    if (px < 0 || py < 0) return 0;
    int cx = px / COLLISION_SCALE;
    int cy = py / COLLISION_SCALE;
    if (cx < 0 || cx >= g_arena->collision_w || cy < 0 || cy >= g_arena->collision_h) return 0;
    return world_collision_flags(cx, cy) != 3;        // only 3 stops bullets: 2 (low cover) lets them pass over
}

// Sweep in <=1px increments so a frame cannot skip a thin blocked cell.
// Incremental 32-bit interpolation: next = start + trunc(d * step / steps) is
// evaluated as q * step + floor(|r| * step / steps) (q = d / steps, r = d % steps),
// carrying the fractional part with a Bresenham accumulator. No division per
// step and no int64 (software on ARM9).
int sweep_position(fixed *x, fixed *y, fixed dx, fixed dy) {
    fixed start_x = *x, start_y = *y;
    int ax = dx < 0 ? -dx : dx;
    int ay = dy < 0 ? -dy : dy;
    int major = ax > ay ? ax : ay;
    int steps = (major + 255) / 256;
    if (steps < 1) steps = 1;

    fixed qx = dx / steps, qy = dy / steps;
    int rx = (dx % steps) < 0 ? -(dx % steps) : (dx % steps);
    int ry = (dy % steps) < 0 ? -(dy % steps) : (dy % steps);
    int sgn_x = dx < 0 ? -1 : 1, sgn_y = dy < 0 ? -1 : 1;
    int acc_x = 0, acc_y = 0;
    fixed off_x = 0, off_y = 0;
    for (int step = 1; step <= steps; step++) {
        off_x += qx;
        off_y += qy;
        acc_x += rx;
        if (acc_x >= steps) { acc_x -= steps; off_x += sgn_x; }
        acc_y += ry;
        if (acc_y >= steps) { acc_y -= steps; off_y += sgn_y; }
        if (!position_is_free(start_x + off_x, start_y + off_y)) return 0;
    }
    *x = start_x + dx;
    *y = start_y + dy;
    return 1;
}

// Samples x0 + dx * i / steps (C truncation toward zero) without a division per sample: one divide
// up front, then the remainder is carried (software division is slow on the ARM9).
typedef struct {
    int origin, sign, q, r, steps, acc, extra;
} LineStepper;

static inline void line_stepper_init(LineStepper *s, int origin, int delta, int steps) {
    int a = delta < 0 ? -delta : delta;
    s->origin = origin;
    s->sign = delta < 0 ? -1 : 1;
    s->q = a / steps;
    s->r = a % steps;
    s->steps = steps;
    s->acc = 0;
    s->extra = 0;
}

// Value for sample i; call with i = 1, 2, 3, ... in order.
static inline int line_stepper_next(LineStepper *s, int i) {
    s->acc += s->r;
    if (s->acc >= s->steps) {
        s->acc -= s->steps;
        s->extra++;
    }
    return s->origin + s->sign * (s->q * i + s->extra);
}

ITCM_CODE int line_is_walkable(int x0, int y0, int x1, int y1) {
    int dx = x1 - x0, dy = y1 - y0;
    int adx = dx < 0 ? -dx : dx;
    int ady = (dy < 0 ? -dy : dy) << GROUND_Y_SHIFT;          // ground units
    int steps = ((adx > ady ? adx : ady) >> 2) + 1;           // a sample every ~4 ground px
    LineStepper sx, sy;
    line_stepper_init(&sx, x0, dx, steps);
    line_stepper_init(&sy, y0, dy, steps);
    for (int i = 1; i < steps; i++) {
        int x = line_stepper_next(&sx, i);
        int y = line_stepper_next(&sy, i);
        if (!position_is_free(TO_FIXED(x), TO_FIXED(y))) return 0;
    }
    return 1;
}

ITCM_CODE int bullet_line_is_free(int x0, int y0, int x1, int y1) {
    int dx = x1 - x0, dy = y1 - y0;
    int adx = dx < 0 ? -dx : dx;
    int ady = dy < 0 ? -dy : dy;
    int steps = ((adx > ady ? adx : ady) >> 2) + 1;           // a sample every ~4 px
    LineStepper sx, sy;
    line_stepper_init(&sx, x0, dx, steps);
    line_stepper_init(&sy, y0, dy, steps);
    for (int i = 1; i < steps; i++) {
        int x = line_stepper_next(&sx, i);
        int y = line_stepper_next(&sy, i);
        if (!bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) return 0;
    }
    return 1;
}

// Low cover (value 2, DESIGN.md 6.9 "Agacharse tras coberturas bajas"): is there a cell of value 2 within
// `reach` px of the ground point (wx, wy)? The footprint is the same 2:1 ellipse as position_is_free, so
// reach = 4 means "hugging" it. Only the few cells around the hero are sampled.
ITCM_CODE int low_cover_near(int wx, int wy, int reach) {
    const int rx = 6 + reach;
    const int ry = rx >> GROUND_Y_SHIFT;
    int cell_x0 = (wx - rx) / COLLISION_SCALE;
    int cell_x1 = (wx + rx) / COLLISION_SCALE;
    int cell_y0 = (wy - ry) / COLLISION_SCALE;
    int cell_y1 = (wy + ry) / COLLISION_SCALE;
    if (cell_x0 < 0) cell_x0 = 0;
    if (cell_y0 < 0) cell_y0 = 0;
    if (cell_x1 >= g_arena->collision_w) cell_x1 = g_arena->collision_w - 1;
    if (cell_y1 >= g_arena->collision_h) cell_y1 = g_arena->collision_h - 1;
    const int rsq = rx * rx;
    for (int cy = cell_y0; cy <= cell_y1; cy++) {
        for (int cx = cell_x0; cx <= cell_x1; cx++) {
            if (world_collision_flags(cx, cy) != 2) continue;
            int left = cx * COLLISION_SCALE;
            int top = cy * COLLISION_SCALE;
            int nearest_x = wx < left ? left : (wx > left + COLLISION_SCALE - 1 ? left + COLLISION_SCALE - 1 : wx);
            int nearest_y = wy < top ? top : (wy > top + COLLISION_SCALE - 1 ? top + COLLISION_SCALE - 1 : wy);
            int dx = wx - nearest_x;
            int dy = wy - nearest_y;
            if (dx * dx + GROUND_DY2(dy) <= rsq) return 1;
        }
    }
    return 0;
}

// Is the cell under ground point (wx, wy) low cover (value 2)? Points off the arena count as free.
static int low_cover_at(int wx, int wy) {
    if (wx < 0 || wy < 0) return 0;
    const int cx = wx / COLLISION_SCALE;
    const int cy = wy / COLLISION_SCALE;
    if (cx >= g_arena->collision_w || cy >= g_arena->collision_h) return 0;
    return world_collision_flags(cx, cy) == 2;
}

// Bench test start (see collision.h). Scans the whole arena once at boot: the nearest low-cover cell, then the first
// ground point under it (k px below its bottom edge) that is free and hugs it.
int low_cover_find_spot(int from_x, int from_y, int reach, int *out_x, int *out_y) {
    int best_d = -1;
    int bx = 0, by = 0;
    for (int cy = 0; cy < g_arena->collision_h; cy++) {
        for (int cx = 0; cx < g_arena->collision_w; cx++) {
            if (world_collision_flags(cx, cy) != 2) continue;
            const int x = cx * COLLISION_SCALE + COLLISION_SCALE / 2;
            const int bottom = (cy + 1) * COLLISION_SCALE;
            const int dx = x - from_x, dy = bottom - from_y;
            const int d = dx * dx + dy * dy;
            if (best_d >= 0 && d >= best_d) continue;
            for (int k = 1; k <= 16; k++) {
                const int py = bottom + k;
                if (!position_is_free(TO_FIXED(x), TO_FIXED(py))) continue;
                if (!low_cover_near(x, py, reach)) continue;
                best_d = d;
                bx = x;
                by = py;
                break;
            }
        }
    }
    if (best_d < 0) return 0;
    *out_x = bx;
    *out_y = by;
    return 1;
}

// Low cover the hero is pushing toward (DESIGN.md 6.13.6): the same `reach` ellipse as low_cover_near, sampled on the
// edge of that ellipse on each axis the input (ix, iy, screen space, -1..1) points along. Cover on the side he pushes
// toward answers; cover he only walks past (parallel to him) does not, so he stays standing.
ITCM_CODE int low_cover_toward(int wx, int wy, int reach, int ix, int iy) {
    const int rx = 6 + reach;
    const int ry = rx >> GROUND_Y_SHIFT;
    if (ix > 0 && low_cover_at(wx + rx, wy)) return 1;
    if (ix < 0 && low_cover_at(wx - rx, wy)) return 1;
    if (iy > 0 && low_cover_at(wx, wy + ry)) return 1;
    if (iy < 0 && low_cover_at(wx, wy - ry)) return 1;
    return 0;
}

// Does the straight segment (x0,y0) -> (x1,y1), in ground px, cross a low-cover cell (value 2) strictly between
// its ends? Samples every ~4 px like bullet_line_is_free; the end cells are skipped so the shooter's own cell and
// the hero's (which touches the cover) never count.
ITCM_CODE int line_crosses_low_cover(int x0, int y0, int x1, int y1) {
    int dx = x1 - x0, dy = y1 - y0;
    int adx = dx < 0 ? -dx : dx;
    int ady = dy < 0 ? -dy : dy;
    int steps = ((adx > ady ? adx : ady) >> 1) + 1;
    LineStepper sx, sy;
    line_stepper_init(&sx, x0, dx, steps);
    line_stepper_init(&sy, y0, dy, steps);
    for (int i = 1; i < steps; i++) {
        int cx = line_stepper_next(&sx, i) / COLLISION_SCALE;
        int cy = line_stepper_next(&sy, i) / COLLISION_SCALE;
        if (cx < 0 || cx >= g_arena->collision_w || cy < 0 || cy >= g_arena->collision_h) continue;
        if (world_collision_flags(cx, cy) == 2) return 1;
    }
    return 0;
}
