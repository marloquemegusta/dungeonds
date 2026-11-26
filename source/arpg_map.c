#include "arpg_map.h"
#include "game.h"
#include "encounters_act1.h"
#include "arpg_progress.h"

#if ENCOUNTERS_PROTO

// Overlay map (DESIGN.md / diseno_juego_final.md, "Mapa"). Integer only. The rooms live in map units (enc_map_room); the plane is
// turned 45 degrees and squashed 2:1: sx = (X + Y) * K, sy = (Y - X) * K / 2, so the way up the cathedral climbs to the right.
#define MAP_K_MAX 80              // /256: zoom when only a room or two are known; it shrinks to fit the revealed rooms
#define MAP_FIT_W 232             // px the revealed rooms may span
#define MAP_FIT_H 164

// Muted chalk on dark (no pure primaries): BGR555 | alpha.
#define COL(r, g, b) ((uint16_t)(BIT(15) | ((b) << 10) | ((g) << 5) | (r)))
#define C_ROOM_NOW   COL(30, 28, 21)
#define C_ROOM       COL(19, 17, 13)
#define C_DOOR       COL(14, 12, 9)
#define C_ALTAR      COL(24, 18, 9)
#define C_ALTAR_LAST COL(29, 23, 11)
#define C_CHEST      COL(21, 15, 8)
#define C_CHEST_OPEN COL(11, 9, 6)
#define C_HERO       COL(31, 31, 27)
#define C_HALO       COL(2, 2, 3)
#define C_HERO_DIM   COL(22, 20, 15)

static int s_open;
static uint16_t *s_page;

void arpg_map_toggle(void) { s_open ^= 1; }
int arpg_map_is_open(void) { return s_open; }

static int s_k = 11, s_uc, s_vc;     // zoom (/256) and centre of the revealed rooms in (X+Y, Y-X) units

static inline int proj_x(int x, int y) { return 128 + (((x + y - s_uc) * s_k) >> 8); }
static inline int proj_y(int x, int y) { return 96 - (((y - x - s_vc) * s_k) >> 9); }

// Fits the zoom and the centre to the revealed rooms (plus the stubs of their doors).
static void fit_view(void) {
    int umin = 1 << 20, umax = -(1 << 20), vmin = 1 << 20, vmax = -(1 << 20);
    for (int r = 0; r < ENC_ROOM_COUNT; r++) {
        if (!((g_arpg.rooms_seen >> r) & 1)) continue;
        EncMapRoom m;
        enc_map_room(r, &m);
        const int x0 = m.x - 60, x1 = m.x + m.w + 60, y0 = m.y - 60, y1 = m.y + m.h + 60;
        const int us[2] = { x0 + y0, x1 + y1 }, vs[2] = { y0 - x1, y1 - x0 };
        if (us[0] < umin) umin = us[0];
        if (us[1] > umax) umax = us[1];
        if (vs[0] < vmin) vmin = vs[0];
        if (vs[1] > vmax) vmax = vs[1];
    }
    if (umax < umin) { umin = umax = vmin = vmax = 0; }
    s_uc = (umin + umax) / 2;
    s_vc = (vmin + vmax) / 2;
    int k = MAP_K_MAX;
    if (umax > umin) { const int ku = MAP_FIT_W * 256 / (umax - umin); if (ku < k) k = ku; }
    if (vmax > vmin) { const int kv = MAP_FIT_H * 512 / (vmax - vmin); if (kv < k) k = kv; }
    s_k = k;
}

// Two passes over the whole drawing: pass 0 paints a dark border, pass 1 the 2 px chalk line on top, so it reads on any floor.
static int s_pass;
static int16_t s_rx0[SCREEN_H], s_rx1[SCREEN_H];

static inline void put(int x, int y, uint16_t c) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    s_page[y * SCREEN_W + x] = c;
    if (x < s_rx0[y]) s_rx0[y] = (int16_t)x;
    if (x + 1 > s_rx1[y]) s_rx1[y] = (int16_t)(x + 1);
}

static inline void plot(int x, int y, uint16_t c) {
    if (s_pass == 0) {
        put(x - 1, y, C_HALO); put(x + 1, y, C_HALO); put(x, y - 1, C_HALO); put(x, y + 2, C_HALO);
    } else {
        put(x, y, c); put(x, y + 1, c);
    }
}

static void line(int x0, int y0, int x1, int y1, uint16_t c, int dotted) {
    int dx = x1 > x0 ? x1 - x0 : x0 - x1, sx = x0 < x1 ? 1 : -1;
    int dy = y1 > y0 ? y0 - y1 : y1 - y0, sy = y0 < y1 ? 1 : -1;     // -|dy|
    int err = dx + dy, n = 0;
    for (;;) {
        if (!dotted || (n & 1) == 0) plot(x0, y0, c);
        n++;
        if (x0 == x1 && y0 == y1) break;
        int e2 = err << 1;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// Segment between two map points.
static void seg(int ax, int ay, int bx, int by, uint16_t c, int dotted) {
    line(proj_x(ax, ay), proj_y(ax, ay), proj_x(bx, by), proj_y(bx, by), c, dotted);
}

static void dot3(int mx, int my, uint16_t c, int filled) {
    const int sx = proj_x(mx, my), sy = proj_y(mx, my);
    plot(sx, sy, c);
    if (!filled) return;
    plot(sx - 1, sy, c); plot(sx + 1, sy, c); plot(sx, sy - 1, c); plot(sx, sy + 1, c);
}

static void draw_room(int room, int is_now) {
    EncMapRoom m;
    enc_map_room(room, &m);
    const uint16_t col = is_now ? C_ROOM_NOW : C_ROOM;
    const int x0 = m.x, x1 = m.x + m.w, y0 = m.y, y1 = m.y + m.h;
    // Lateral walls with a gap where the opening is; the upper wall with a gap for the door; the foot wall is solid.
    int gl_lo = 0, gl_hi = 0, gr_lo = 0, gr_hi = 0, gu = 0;
    for (int i = 0; i < m.n_doors; i++) {
        const EncMapDoor *d = &m.door[i];
        if (d->side == 0) { gl_lo = d->cy - 128; gl_hi = d->cy + 128; }
        else if (d->side == 1) { gr_lo = d->cy - 128; gr_hi = d->cy + 128; }
        else gu = 1;
    }
    seg(x0, y0, x1, y0, col, 0);
    if (gl_hi > gl_lo) { seg(x0, y0, x0, gl_lo, col, 0); seg(x0, gl_hi, x0, y1, col, 0); } else seg(x0, y0, x0, y1, col, 0);
    if (gr_hi > gr_lo) { seg(x1, y0, x1, gr_lo, col, 0); seg(x1, gr_hi, x1, y1, col, 0); } else seg(x1, y0, x1, y1, col, 0);
    if (gu) { const int mx = (x0 + x1) / 2; seg(x0, y1, mx - 40, y1, col, 0); seg(mx + 40, y1, x1, y1, col, 0); }
    else seg(x0, y1, x1, y1, col, 0);
    // Doors toward rooms not seen yet: a short dotted stub out of the opening.
    for (int i = 0; i < m.n_doors; i++) {
        const EncMapDoor *d = &m.door[i];
        if ((g_arpg.rooms_seen >> d->dest) & 1) continue;
        if (d->side == 0) seg(d->cx, d->cy, d->cx - 140, d->cy, C_DOOR, 0);
        else if (d->side == 1) seg(d->cx, d->cy, d->cx + 140, d->cy, C_DOOR, 0);
        else seg(d->cx, d->cy, d->cx, d->cy + 140, C_DOOR, 0);
    }
    if (m.altar) dot3(m.altar_x, m.altar_y, g_arpg.last_altar == room ? C_ALTAR_LAST : C_ALTAR, 1);
    if (m.chest) {
        if ((g_arpg.chests_open >> room) & 1) dot3(m.chest_x, m.chest_y, C_CHEST_OPEN, 0);
        else dot3(m.chest_x, m.chest_y, C_CHEST, 1);
    }
}

void arpg_map_draw(uint16_t *page, int px, int py, int frame) {
    s_page = page;
    int hx, hy;
    const int now = enc_map_hero(px, py, &hx, &hy);
    g_arpg.rooms_seen |= (uint16_t)(1u << now);
    fit_view();
    for (int y = 0; y < SCREEN_H; y++) { s_rx0[y] = SCREEN_W; s_rx1[y] = 0; }
    for (s_pass = 0; s_pass < 2; s_pass++) {
        for (int r = 0; r < ENC_ROOM_COUNT; r++)
            if (r != now && ((g_arpg.rooms_seen >> r) & 1)) draw_room(r, 0);
        draw_room(now, 1);
        dot3(hx, hy, (frame & 16) ? C_HERO_DIM : C_HERO, 1);
    }
    for (int y = 0; y < SCREEN_H; y++) dirty_row(y, s_rx0[y], s_rx1[y]);
}

#else
void arpg_map_toggle(void) {}
int arpg_map_is_open(void) { return 0; }
void arpg_map_draw(uint16_t *page, int px, int py, int frame) { (void)page; (void)px; (void)py; (void)frame; }
#endif
