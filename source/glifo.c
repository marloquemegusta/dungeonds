#include "glifo.h"
#include "glifo_rune_data.h"
#include "groundfx.h"
#include "collision.h"
#include "arpg.h"
#include "arpg_inv.h"
#include "allies.h"
#include "punch.h"
#include "sfx.h"
#include <nds/arm9/math.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

// Glifo look and arc (DESIGN.md 7.5-7.7). Colours are BGR555 without the alpha bit (put adds it).
// Desaturated palette, same values as FX_SH_* in weapons.c (tests/test_guardrails.py watches this file).
#define GL_IVORY   RGB15(29, 25, 19)
#define GL_GOLD    RGB15(27, 20, 11)
#define GL_AMBER   RGB15(24, 15, 7)
#define GL_EMBER   RGB15(20, 9, 5)
#define GL_DEEP    RGB15(9, 3, 3)
#define GL_ASH_B   RGB15(10, 9, 8)
#define GL_ASH_C   RGB15(6, 5, 5)
#define GL_SMOKE_M RGB15(18, 16, 14)

// Aim preview colours: the overlay layer has no floor to read, so the faint mix is baked: ~3/8 ivory over the mean floor tone
// (90, 86, 78) of the cathedral = (143, 129, 106) -> RGB15(18, 16, 13); the branch pixels a step dimmer, like in the seal.
#define GL_PV_LINE RGB15(18, 16, 13)
#define GL_PV_DIM  RGB15(16, 14, 11)

#define GLIFO_FLASH_FRAMES 12   // [TUNABLE-PLACEHOLDER] detonation flash before the crack closes
#define GLIFO_TONGUES 6         // Zarza: flame tongues alive at once
#define GLIFO_TONGUE_PERIOD 20  // Zarza: frames of one tongue
#define GLIFO_BASE_R 40         // ground radius the baked rune was made for

// The hero's prayer (DESIGN.md 7.7): the clip is nitrofiles/punch/pray_d<dir>.bin (same format as the punch clips). The
// seal appears at the touched point on the frame the hands close.
#define GLIFO_PRAY_FRAMES 8     // frames of the clip (corazon_pray)
#define GLIFO_PRAY_TICKS 4      // [TUNABLE-PLACEHOLDER] game frames per clip frame: the hands close at tick 5*4 = 20 (0,33 s)
#define GLIFO_PRAY_CLOSE 5      // clip frame in which the hands close (tools/characters/build_corazon.py PRAY_CLOSE_FRAME)
#define GLIFO_PRAY_BIN_BYTES 10240

typedef struct {
    int active;
    int cx, cy;             // centre (world px)
    int radius;             // ground radius (Radio line applied)
    int sc;                 // radius / base radius, 8.8: scales the baked rune
    int t;                  // frames since the cycle began
    int t_open, t_det, t_end;   // apertura ends, detonation, cycle ends
    int tick;               // frames until the next Zarza layer
    uint8_t aura;           // GLIFO_AURA_* bits
    uint8_t reopen;         // Doble Sello: reopens once, free, when this cycle ends
    uint8_t seed;
    uint8_t det_sound;          // the detonation sound already played (Doble Sello: once per glifo)
    int xh;                     // half-width (px) of the rows the rune can touch
    int npx;                    // pixels of this zone's scaled mask (s_px[zone])
} GlifoZone;   // scenarios read active/aura at fixed offsets (tools/glifo_rune/gen_scenarios.py): new fields go last

static GlifoZone s_zones[ARPG_GLIFO_MAX];
// Prayer in progress.
static int s_pray_active = 0, s_pray_frame = 0, s_pray_t = 0, s_pray_dir = 0;
static int s_pray_tx = 0, s_pray_ty = 0;                 // where the seal will appear (world px)
static uint8_t s_pray_buf[GLIFO_PRAY_BIN_BYTES] __attribute__((aligned(4)));
static int s_pray_loaded_dir = -1;
static int s_aiming = 0;
static int s_aim_x = 0, s_aim_y = 0;     // clamped target while the stylus aims (world px)
static uint8_t s_next_aura = 0;

static int glifo_count(void) {
    int n = 0;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++)
        if (s_zones[i].active) n++;
    return n + (s_pray_active ? 1 : 0);
}

// Ground metric: a point is inside a circle of ground radius r around (cx, cy).
static int ground_inside(int dx, int dy, int r) {
    return dx * dx + GROUND_DY2(dy) <= r * r;
}

static inline int scl(int v, int sc) { return (v * sc + (v < 0 ? -128 : 128)) / 256; }

static int throw_cost(void) {
    int c = ARPG_GLIFO_COST * (100 - arpg_inv_glifo_line(ARPG_LINE_COST)) / 100;
    return c < ARPG_GLIFO_COST_MIN ? ARPG_GLIFO_COST_MIN : c;
}

static int pray_load_bin(int dir) {
    if (s_pray_loaded_dir == dir) return 1;
    char path[40];
    snprintf(path, sizeof(path), "nitro:/punch/pray_d%d.bin", dir);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    size_t n = fread(s_pray_buf, 1, sizeof(s_pray_buf), f);
    fclose(f);
    s_pray_loaded_dir = -1;
    if (n < sizeof(PunchBinHeader)) return 0;
    const PunchBinHeader *h = (const PunchBinHeader *)s_pray_buf;
    if (h->magic != PUNCH_BIN_MAGIC || sizeof(PunchBinHeader) + h->pix_bytes + h->runs_bytes > n) return 0;
    s_pray_loaded_dir = dir;
    return 1;
}

void glifo_reset(void) {
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) s_zones[i].active = 0;
    s_aiming = 0;
    s_pray_active = 0;
}

void glifo_cancel_aim(void) { s_aiming = 0; }

void glifo_shift_y(int dy_px) {
    for (int i = 0; i < ARPG_GLIFO_MAX; i++)
        if (s_zones[i].active) s_zones[i].cy += dy_px;
    if (s_aiming) s_aim_y += dy_px;
    if (s_pray_active) s_pray_ty += dy_px;
}

int glifo_busy(void) { return s_pray_active; }

int glifo_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y, int hero_dir) {
    (void)hero_x; (void)hero_y;
    (void)touch_pressed;
    if (s_pray_active) {                                  // praying: the hero walks freely and the clip follows his facing
        s_aiming = 0;
        const int d = hero_dir & 7;
        if (d != s_pray_dir && pray_load_bin(d)) s_pray_dir = d;
        return 0;
    }

    if (touch_down) {
        // Target = exactly the touched world point (no range limit).
        s_aim_x = touch_x;
        s_aim_y = touch_y;
        s_aiming = 1;
        return 1;
    }

    if (!s_aiming) return 0;
    s_aiming = 0;

    // Solo suelo: on a wall, pillar or obstacle nothing happens (no prayer, no mana).
    if (!ground_point_is_free(s_aim_x, s_aim_y)) return 0;

    // Release: the hero prays if there is mana and a free slot; the mana is paid now (the prayer is a commitment).
    const int cost = throw_cost();
    if (player->mana < cost || glifo_count() >= ARPG_GLIFO_MAX) return 0;
    player->mana -= cost;
    s_pray_tx = s_aim_x;
    s_pray_ty = s_aim_y;
    s_pray_dir = hero_dir & 7;
    s_pray_frame = 0;
    s_pray_t = 0;
    s_pray_active = 1;
    if (!pray_load_bin(s_pray_dir)) s_pray_frame = GLIFO_PRAY_CLOSE;   // no clip (should not happen): the seal appears at once
    return 1;
}

const uint16_t *glifo_pray_pixels(void) {
    if (!s_pray_active || s_pray_loaded_dir != s_pray_dir) return NULL;
    const PunchBinHeader *h = (const PunchBinHeader *)s_pray_buf;
    return (const uint16_t *)(s_pray_buf + sizeof(PunchBinHeader)) + h->pix_off[s_pray_frame];
}

const uint16_t *glifo_pray_runs(void) {
    if (!s_pray_active || s_pray_loaded_dir != s_pray_dir) return NULL;
    const PunchBinHeader *h = (const PunchBinHeader *)s_pray_buf;
    return (const uint16_t *)(s_pray_buf + sizeof(PunchBinHeader) + h->pix_bytes) + h->run_off[s_pray_frame];
}

const uint8_t *glifo_pray_bounds(void) {
    if (!s_pray_active || s_pray_loaded_dir != s_pray_dir) return NULL;
    return ((const PunchBinHeader *)s_pray_buf)->bounds[s_pray_frame];
}

int glifo_pray_dir(void) { return s_pray_dir; }
int glifo_pray_frame(void) { return s_pray_frame; }
int glifo_pray_anchor(void) { return g_pray_ground_anchor[s_pray_dir]; }

// ---------------------------------------------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------------------------------------------

// Cycle timings: the Espera line shortens apertura + espera (never below ARPG_GLIFO_WAIT_MIN_PCT).
static void zone_start(GlifoZone *z) {
    int k = 100 - arpg_inv_glifo_line(ARPG_LINE_WAIT);
    if (k < ARPG_GLIFO_WAIT_MIN_PCT) k = ARPG_GLIFO_WAIT_MIN_PCT;
    int open = ARPG_GLIFO_OPEN_FRAMES * k / 100;
    int wait = ARPG_GLIFO_WAIT_FRAMES * k / 100;
    if (open < 1) open = 1;
    if (wait < 1) wait = 1;
    z->t = 0;
    z->t_open = open;
    z->t_det = open + wait;
    z->t_end = z->t_det + GLIFO_FLASH_FRAMES + ARPG_GLIFO_CLOSE_FRAMES;
    z->tick = 0;
}

static int enemy_in_zone(const Enemy *en, int e, const GlifoZone *z) {
    if (g_enemy_ally[e] || !en->active || en->hp <= 0) return 0;
    return ground_inside(TO_INT(en->x) - z->cx, TO_INT(en->y) - z->cy, z->radius);
}

// Redil: a fixed pull toward the centre, added to the enemy's own movement, that never overshoots the centre and
// respects the walls (slides X, then Y).
static void redil_pull(Enemy *en, const GlifoZone *z) {
    switch (en->state) {
    case ENEMY_STATE_EMERGE: case ENEMY_STATE_REMATE: case ENEMY_STATE_SUSPENDED:
    case ENEMY_STATE_DEAD: case ENEMY_STATE_DORMANT:
        return;
    default: break;
    }
    const int dxf = TO_FIXED(z->cx) - en->x;
    const int dyf = TO_FIXED(z->cy) - en->y;
    const int dist = (int)sqrt32((unsigned)(dxf * dxf + 4 * dyf * dyf));   // ground distance, 8.8
    int vx, vy;
    if (dist <= ARPG_GLIFO_REDIL_SPEED) {
        vx = dxf;
        vy = dyf;
    } else {
        vx = div32(dxf * ARPG_GLIFO_REDIL_SPEED, dist);
        vy = div32(dyf * ARPG_GLIFO_REDIL_SPEED, dist);
    }
    if (vx) sweep_position(&en->x, &en->y, vx, 0);
    if (vy) sweep_position(&en->x, &en->y, 0, vy);
}

static void zone_detonate(GlifoZone *z, Enemy *enemies, int max_enemies) {
    const int dmg = ARPG_GLIFO_DAMAGE * (100 + arpg_inv_glifo_line(ARPG_LINE_DAMAGE)) / 100;
    for (int e = 0; e < max_enemies; e++) {
        Enemy *en = &enemies[e];
        if (!enemy_in_zone(en, e, z)) continue;
        if (z->aura & GLIFO_AURA_ZARZA) burn_apply(en, ARPG_GLIFO_ZARZA_DET);   // before the hit: Martirio sees the layers
        enemy_hit(en, dmg, 0, 0);
    }
}

// Mask scaled to the zone's real radius (computed once when the seal appears). The baked rune is a list of 1 px
// crack pixels for radius 40; scaled by sc (8.8, 1.0..2.0) each pixel covers a w x h footprint of destination pixels.
// Drawing the footprint's centre alone would leave holes, so the pixel gets an L: its row across the footprint and its
// column. That keeps the crack 1 px thin and continuous (its length grows with the radius, its width does not).
// Extra pixels inherit the opening order and the closing order, brightness and branch bit of their source pixel.
#define GL_PX_MAX 2400          // 788 source pixels x up to 3 (centre + two arms); duplicates are removed
#define GL_EX 96                // dedupe bitmap: dx in [-96, 96), dy in [-64, 64)
#define GL_EY 64
#define PV_ZONE ARPG_GLIFO_MAX       // scratch slot of s_px / s_floor for the aim preview
static GlifoPx s_px[ARPG_GLIFO_MAX + 1][GL_PX_MAX];
// Floor mask of each zone (the rune is only drawn on walkable floor): one byte per 4 px collision cell, filled
// once when the seal appears. Cells cover dx in [-96, 96] and dy in [-64, 64) around the centre.
#define FL_W 50
#define FL_H 34
static uint8_t s_floor[ARPG_GLIFO_MAX + 1][FL_W * FL_H];
static int s_fl_bx[ARPG_GLIFO_MAX + 1], s_fl_by[ARPG_GLIFO_MAX + 1];
static const uint8_t *r_floor;
static int r_flx, r_fly;
static void zone_build_floor(int zi, const GlifoZone *z) {
    const int bx = (z->cx - 96) >> 2, by = (z->cy - 64) >> 2;
    s_fl_bx[zi] = bx; s_fl_by[zi] = by;
    for (int j = 0; j < FL_H; j++)
        for (int i = 0; i < FL_W; i++)
            s_floor[zi][j * FL_W + i] = (uint8_t)ground_point_is_free((bx + i) * 4 + 2, (by + j) * 4 + 2);
}
static uint8_t s_seen[(2 * GL_EX) * (2 * GL_EY) / 8];

static inline int fx(int v, int sc) { return ((2 * v - 1) * sc + 256) >> 9; }    // first destination column of cell v
static inline int seen_bit(int x, int y) {
    if ((unsigned)(x + GL_EX) >= (unsigned)(2 * GL_EX) || (unsigned)(y + GL_EY) >= (unsigned)(2 * GL_EY)) return -1;
    return (y + GL_EY) * (2 * GL_EX) + (x + GL_EX);
}
static int seen_test_set(int x, int y) {          // 1 if it was already set (or out of range); sets it otherwise
    const int b = seen_bit(x, y);
    if (b < 0) return 1;
    const uint8_t m = (uint8_t)(1u << (b & 7));
    if (s_seen[b >> 3] & m) return 1;
    s_seen[b >> 3] |= m;
    return 0;
}

static void zone_build_mask(int zi, GlifoZone *z) {
    const int redil = (z->aura & GLIFO_AURA_REDIL) != 0;
    const GlifoPx *src = redil ? g_glifo_twist : g_glifo_base;
    const int n = redil ? GLIFO_TWIST_N : GLIFO_BASE_N;
    const int sc = z->sc;
    GlifoPx *out = s_px[zi];
    int m = 0;
    memset(s_seen, 0, sizeof(s_seen));
    for (int i = 0; i < n; i++) (void)seen_test_set(scl(src[i].dx, sc), scl(src[i].dy, sc));   // the centres are never displaced
    for (int i = 0; i < n && m < GL_PX_MAX; i++) {
        const GlifoPx *q = &src[i];
        const int cx = scl(q->dx, sc), cy = scl(q->dy, sc);
        out[m++] = (GlifoPx){ (int8_t)cx, (int8_t)cy, q->order, q->close, q->flags };
        const int x0 = fx(q->dx, sc), x1 = fx(q->dx + 1, sc) - 1;
        const int y0 = fx(q->dy, sc), y1 = fx(q->dy + 1, sc) - 1;
        const uint8_t fl = (uint8_t)(q->flags & ~(GLIFO_FL_SHARD | GLIFO_FL_FLARE));
        for (int x = x0; x <= x1 && m < GL_PX_MAX; x++)
            if (x != cx && !seen_test_set(x, cy)) out[m++] = (GlifoPx){ (int8_t)x, (int8_t)cy, q->order, q->close, fl };
        for (int y = y0; y <= y1 && m < GL_PX_MAX; y++)
            if (y != cy && !seen_test_set(cx, y)) out[m++] = (GlifoPx){ (int8_t)cx, (int8_t)y, q->order, q->close, fl };
    }
    z->npx = m;
}

// The seal appears at the prayer's point with the auras equipped at that moment.
static void zone_spawn(int tx, int ty) {
    for (int zi = 0; zi < ARPG_GLIFO_MAX; zi++) {
        GlifoZone *z = &s_zones[zi];
        if (z->active) continue;
        z->active = 1;
        z->cx = tx;
        z->cy = ty;
        int r = ARPG_GLIFO_RADIUS * (100 + arpg_inv_glifo_line(ARPG_LINE_RADIUS)) / 100;
        if (r > ARPG_GLIFO_RADIUS_MAX) r = ARPG_GLIFO_RADIUS_MAX;
        z->radius = r;
        z->sc = r * 256 / GLIFO_BASE_R;
        z->xh = ((44 * z->sc) >> 8) + 3;
        z->aura = (uint8_t)((arpg_inv_has_mechanic(ARPG_MECH_REDIL) ? GLIFO_AURA_REDIL : 0) |
                            (arpg_inv_has_mechanic(ARPG_MECH_ZARZA) ? GLIFO_AURA_ZARZA : 0));
        z->reopen = (uint8_t)(arpg_inv_has_mechanic(ARPG_MECH_DOBLE_SELLO) ? 1 : 0);
        z->det_sound = 0;
        z->seed = (uint8_t)(s_next_aura++ * 37u + 11u);
        zone_build_mask(zi, z);
        zone_build_floor(zi, z);
        zone_start(z);
        sfx_play(SND_GLIFO_CRACK, z->cx);
        break;
    }
}

void glifo_update(Enemy *enemies, int max_enemies) {
    // Prayer: the hands close on frame GLIFO_PRAY_CLOSE and the seal appears at the touched point.
    if (s_pray_active) {
        if (s_pray_t == 0 && s_pray_frame == GLIFO_PRAY_CLOSE) zone_spawn(s_pray_tx, s_pray_ty);
        if (++s_pray_t >= GLIFO_PRAY_TICKS) {
            s_pray_t = 0;
            if (++s_pray_frame >= GLIFO_PRAY_FRAMES) s_pray_active = 0;
        }
    }

    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        GlifoZone *z = &s_zones[i];
        if (!z->active) continue;
        const int t = z->t;
        if (t >= z->t_open && t < z->t_det) {
            if ((z->aura & GLIFO_AURA_REDIL) || (z->aura & GLIFO_AURA_ZARZA)) {
                const int zarza_tick = (z->aura & GLIFO_AURA_ZARZA) && z->tick <= 0;
                for (int e = 0; e < max_enemies; e++) {
                    Enemy *en = &enemies[e];
                    if (!enemy_in_zone(en, e, z)) continue;
                    if (zarza_tick) burn_apply(en, 1);
                    if (z->aura & GLIFO_AURA_REDIL) redil_pull(en, z);
                }
                if (zarza_tick) z->tick = ARPG_GLIFO_ZARZA_TICK;
                z->tick--;
            }
        } else if (t == z->t_det) {
            zone_detonate(z, enemies, max_enemies);
            if (!z->det_sound) { z->det_sound = 1; sfx_play(SND_GLIFO_DETONATE, z->cx); }   // once per glifo, even with Doble Sello
        }
        if (++z->t >= z->t_end) {
            if (z->reopen) {            // Doble Sello: once, free, same spot and same auras
                z->reopen = 0;
                zone_start(z);
            } else {
                z->active = 0;
            }
        }
    }
}

int glifo_point_in_zone(int x, int y) {
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        const GlifoZone *z = &s_zones[i];
        if (z->active && ground_inside(x - z->cx, y - z->cy, z->radius)) return 1;
    }
    return 0;
}

// ---------------------------------------------------------------------------------------------------------------
// Render (DESIGN.md 7.7, variant A). Layers: [Redil: vortex under] -> crack (base or twisted mask) -> [Zarza tongues].
// ---------------------------------------------------------------------------------------------------------------

#ifndef GLEXP
#define GLEXP 0
#endif
#define ROWS 128                // rows kept in the occlusion cache (dy + 64): the rune reaches 42 px at radius 80 plus flames
#define ROW_OFF 64

static uint16_t *r_buf;
static int r_camx, r_camy, r_cx, r_cy, r_xh;     // r_xh: half-width queried for the occlusion of a row
static int8_t r_hid[ROWS];      // per row: -1 unknown, 0 clear, 1 a wall may hide something

static void put_rel(int dx, int dy, uint16_t col) {
    const int wy = r_cy + dy, sy = wy - r_camy;
    const int wx = r_cx + dx, sx = wx - r_camx;
    if ((unsigned)sy >= SCREEN_H || (unsigned)sx >= SCREEN_W) return;
    const int ri = dy + ROW_OFF;
    if ((unsigned)ri >= ROWS) return;
    {   // only on walkable floor (cell mask of the zone)
        const unsigned fi = (unsigned)((wx >> 2) - r_flx), fj = (unsigned)((wy >> 2) - r_fly);
        if (fi >= FL_W || fj >= FL_H || !r_floor[fj * FL_W + fi]) return;
    }
    int h = r_hid[ri];
    if (h < 0) {
        h = world_span_hidden(wy, r_cx - r_xh, r_cx + r_xh + 1, wy) ? 1 : 0;
        r_hid[ri] = (int8_t)h;
    }
    if (h && world_pixel_hidden(wx, wy, wy)) return;
    r_buf[sy * SCREEN_W + sx] = (uint16_t)(col | BIT(15));
}

static uint16_t core_color(int v) {
    return v >= 200 ? GL_IVORY : v >= 140 ? GL_GOLD : v >= 90 ? GL_AMBER : GL_EMBER;
}

static const uint8_t k_breath[16] = { 18, 25, 31, 35, 36, 35, 31, 25, 18, 11, 5, 1, 0, 1, 5, 11 };
static const int k_bright[3] = { 128, 256, 287 };     // brightness classes of the baked pixels

static uint32_t hash2(uint32_t a, uint32_t b) {
    uint32_t v = a * 73856093u ^ b * 19349663u;
    v = (v ^ (v >> 13)) * 1274126177u;
    return v ^ (v >> 16);
}

// A flame tongue rising from (dx, dy): gold at the foot, amber, ember at the tip, a wisp of smoke above.
static void draw_tongue(int dx, int dy, int h, int hot) {
    for (int i = 0; i < h; i++) {
        const uint16_t c = (i * 3 < h) ? (hot ? GL_IVORY : GL_GOLD) : (i * 3 < h * 2) ? GL_AMBER : GL_EMBER;
        put_rel(dx, dy - 1 - i, c);
    }
    if (h >= 3) put_rel(dx, dy - 1 - h, GL_SMOKE_M);
}

// The well and its arms scale with the rune: each baked pixel fills its whole footprint (nearest-neighbour upscale).
static void put_cell(int dx, int dy, int sc, uint16_t col) {
    if (sc == 256) { put_rel(dx, dy, col); return; }
    const int x0 = fx(dx, sc), x1 = fx(dx + 1, sc), y0 = fx(dy, sc), y1 = fx(dy + 1, sc);
    for (int y = y0; y < y1; y++)
        for (int x = x0; x < x1; x++) put_rel(x, y, col);
}

static void draw_vortex(int T, const GlifoZone *z, int lim) {
    const int fr = (T >> 1) & 7;
    const int sc = z->sc;
    for (int i = 0; i < GLIFO_VX_BASE_N; i++) {
        const GlifoVx *p = &g_glifo_vx_base[i];
        if (p->rr > lim) break;
        put_cell(p->dx, p->dy, sc, p->col == 0 ? GL_DEEP : p->col == 1 ? GL_ASH_C : GL_ASH_B);
    }
    for (int i = 0; i < GLIFO_VX_ARM_N; i++) {
        const GlifoVx *p = &g_glifo_vx_arm[fr][i];
        if (p->rr > lim || p->rr == 255) continue;
        put_cell(p->dx, p->dy, sc, p->col == 3 ? GL_IVORY : p->col == 4 ? GL_GOLD : GL_AMBER);
    }
}

static void draw_zone(const GlifoZone *z, int zi) {
    const int T = z->t;
    const int sc = z->sc;
    const int redil = (z->aura & GLIFO_AURA_REDIL) != 0;
    const GlifoPx *mask = s_px[zi];           // the rune already scaled to this zone's radius
    const int n = z->npx;
    const int phase_close = T >= z->t_det + GLIFO_FLASH_FRAMES;
    const int flash = T >= z->t_det && !phase_close;
    int p = 255, cprog = -1, f = 256;           // reveal progress, close progress, fade
    if (T < z->t_open) {
        p = div32(T * 255, z->t_open);
        f = 160 + ((p * 96) >> 8);
    } else if (T < z->t_det) {
        f = 220 + k_breath[(T >> 2) & 15];
    } else if (flash) {
        f = 300;
    } else {
        cprog = ((T - z->t_det - GLIFO_FLASH_FRAMES) * 17) >> 1;   // 0..255 over ARPG_GLIFO_CLOSE_FRAMES = 30
        if (cprog > 255) cprog = 255;
        f = 256 - (cprog >> 1);
    }

    // Layer 1 (Redil transformation): the light well under the whirl.
    if (redil && T >= z->t_open) {
        int lim = 255;
        if (T < z->t_open + 10) lim = (T - z->t_open + 1) * 26;
        if (phase_close) lim = 255 - cprog;
        if (lim > 0) draw_vortex(T, z, lim);
    }

    // Layer 0: the crack (sorted by opening order: stop at the first pixel not yet opened).
    for (int i = 0; i < n; i++) {
        const GlifoPx *q = &mask[i];
        if (q->order > p) break;
        if (cprog >= 0 && q->close <= cprog) continue;          // closes outside-in
        int v = (k_bright[q->flags & 3] * f) >> 8;
        if (T < z->t_open && q->order + 14 > p) v = 256;         // the leading edge of the opening is bright
        if (flash) v = 300;
        if (q->flags & GLIFO_FL_BRANCH) v = (v * 3) >> 2;
        const int dx = q->dx, dy = q->dy;
        if (q->flags & GLIFO_FL_SHARD) {                         // a raised stone chip beside the crack
            put_rel(dx + 1, dy, GL_ASH_C);
            put_rel(dx, dy - 1, GL_SMOKE_M);
        }
        put_rel(dx, dy, core_color(v));
    }

    // Redil motes: sparks that spiral inward along the whirl during the wait.
    if (redil && T >= z->t_open && T < z->t_det) {
        for (int a = 0; a < 3; a++) {
            for (int m = 0; m < 2; m++) {
                int idx = ((T >> 1) + m * 12 + a * 5) % 24;
                put_rel(scl(g_glifo_spiral[a][idx][0], sc), scl(g_glifo_spiral[a][idx][1], sc), GL_GOLD);
                if (idx > 0)
                    put_rel(scl(g_glifo_spiral[a][idx - 1][0], sc), scl(g_glifo_spiral[a][idx - 1][1], sc), GL_AMBER);
            }
        }
    }

    // Layer 2 (Zarza, additive over the active mask): tongues born on the crack, and a blaze along it on detonation.
    if (z->aura & GLIFO_AURA_ZARZA) {
        const int8_t (*emit)[2] = redil ? g_glifo_emit_twist : g_glifo_emit_base;
        if (T >= z->t_open && T < z->t_det) {
            for (int s = 0; s < GLIFO_TONGUES; s++) {
                const int tt = T + s * 3;
                const int cyc = tt / GLIFO_TONGUE_PERIOD;
                const int age = tt - cyc * GLIFO_TONGUE_PERIOD;
                const int pt = (int)(hash2((uint32_t)cyc * 8u + (uint32_t)s, z->seed) % GLIFO_EMIT_N);
                draw_tongue(scl(emit[pt][0], sc), scl(emit[pt][1], sc), g_glifo_flame_h[(age * 16) / GLIFO_TONGUE_PERIOD], 0);
            }
        } else if (flash) {
            const int age = T - z->t_det;
            const int h = g_glifo_flame_h[(age * 43) >> 5] + 2;
            for (int i = 0; i < n; i++) {
                const GlifoPx *q = &mask[i];
                if (q->flags & GLIFO_FL_FLARE) draw_tongue(q->dx, q->dy, h, 1);
            }
        }
    }

    // Detonation: a ring of light leaves the centre.
    if (flash) {
        const int age = T - z->t_det;
        const int rr = z->radius * (4 + age) / (4 + GLIFO_FLASH_FRAMES);
        const uint16_t rc = age < 6 ? GL_IVORY : GL_GOLD;
        // One-pixel ellipse (half-width rr, half-height rr/2), clipped to the floor by put_rel.
        for (int x = -rr; x <= rr; x++) {
            const int y = sqrt32(rr * rr - x * x) >> 1;
            put_rel(x, y, rc);
            if (y) put_rel(x, -y, rc);
        }
        for (int y = -(rr >> 1); y <= (rr >> 1); y++) {
            const int x = sqrt32(rr * rr - 4 * y * y);
            put_rel(x, y, rc);
            if (x) put_rel(-x, y, rc);
        }
    }
}

// Aim preview (DESIGN.md 7 Glifo): the whole rune, static and faint, at the touched point. The scaled mask is rebuilt only
// when the radius or the auras change (not while the stylus moves); the floor cells it touches are re-queried only when the
// aim point enters another 4 px cell (about 250 lookups, not the full window).
static int s_pv_valid = 0, s_pv_cellx, s_pv_celly, s_pv_sc = -1, s_pv_aura = -1, s_pv_ex, s_pv_ey;
static GlifoZone s_pv;

static void preview_draw(int cam_x, int cam_y) {
    if (!ground_point_is_free(s_aim_x, s_aim_y)) return;
    int r = ARPG_GLIFO_RADIUS * (100 + arpg_inv_glifo_line(ARPG_LINE_RADIUS)) / 100;
    if (r > ARPG_GLIFO_RADIUS_MAX) r = ARPG_GLIFO_RADIUS_MAX;
    const int aura = (arpg_inv_has_mechanic(ARPG_MECH_REDIL) ? GLIFO_AURA_REDIL : 0);
    const int sc = r * 256 / GLIFO_BASE_R;
    if (sc != s_pv_sc || aura != s_pv_aura) {
        s_pv.sc = sc; s_pv.aura = (uint8_t)aura; s_pv.radius = r;
        zone_build_mask(PV_ZONE, &s_pv);
        s_pv.xh = ((44 * sc) >> 8) + 3;
        int ex = 0, ey = 0;
        for (int i = 0; i < s_pv.npx; i++) {
            const int ax = s_px[PV_ZONE][i].dx < 0 ? -s_px[PV_ZONE][i].dx : s_px[PV_ZONE][i].dx;
            const int ay = s_px[PV_ZONE][i].dy < 0 ? -s_px[PV_ZONE][i].dy : s_px[PV_ZONE][i].dy;
            if (ax > ex) ex = ax;
            if (ay > ey) ey = ay;
        }
        s_pv_ex = ex; s_pv_ey = ey;
        s_pv_sc = sc; s_pv_aura = aura; s_pv_valid = 0;
    }
    s_pv.cx = s_aim_x; s_pv.cy = s_aim_y;
    if (s_pv.xh < 0 || s_pv.xh > 96) return;
    const int cellx = s_aim_x >> 2, celly = s_aim_y >> 2;
    if (!s_pv_valid || cellx != s_pv_cellx || celly != s_pv_celly) {
        const int bx = (s_aim_x - 96) >> 2, by = (s_aim_y - 64) >> 2;
        s_fl_bx[PV_ZONE] = bx; s_fl_by[PV_ZONE] = by;
        const int i0 = ((s_aim_x - s_pv_ex) >> 2) - bx, i1 = ((s_aim_x + s_pv_ex) >> 2) - bx;
        const int j0 = ((s_aim_y - s_pv_ey) >> 2) - by, j1 = ((s_aim_y + s_pv_ey) >> 2) - by;
        for (int j = j0; j <= j1 && j < FL_H; j++)
            for (int i = i0; i <= i1 && i < FL_W; i++)
                if (i >= 0 && j >= 0) s_floor[PV_ZONE][j * FL_W + i] = (uint8_t)ground_point_is_free((bx + i) * 4 + 2, (by + j) * 4 + 2);
        s_pv_cellx = cellx; s_pv_celly = celly; s_pv_valid = 1;
    }
    r_cx = s_pv.cx; r_cy = s_pv.cy; r_xh = s_pv.xh;
    r_floor = s_floor[PV_ZONE]; r_flx = s_fl_bx[PV_ZONE]; r_fly = s_fl_by[PV_ZONE];
    for (int k = 0; k < ROWS; k++) r_hid[k] = -1;
    const int sx = r_cx - cam_x;
    for (int dy = -ROW_OFF; dy < ROWS - ROW_OFF; dy++) {
        const int row = r_cy + dy - cam_y;
        if ((unsigned)row < SCREEN_H) dirty_row(row, sx - s_pv.xh, sx + s_pv.xh + 1);
    }
    const GlifoPx *mask = s_px[PV_ZONE];
    for (int i = 0; i < s_pv.npx; i++) {
        const GlifoPx *q = &mask[i];
        put_rel(q->dx, q->dy, (q->flags & GLIFO_FL_BRANCH) ? GL_PV_DIM : GL_PV_LINE);
    }
}

void glifo_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    r_buf = buffer; r_camx = cam_x; r_camy = cam_y;
    if (s_aiming) preview_draw(cam_x, cam_y);
    else s_pv_valid = 0;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        const GlifoZone *z = &s_zones[i];
        if (!z->active) continue;
        // Skip a rune that lies wholly off screen (its widest reach is the radius plus the flames and the well).
        const int sx = z->cx - cam_x, sy = z->cy - cam_y;
        if (sx + z->xh < 0 || sx - z->xh >= SCREEN_W || sy + ROW_OFF < 0 || sy - ROW_OFF >= SCREEN_H) continue;
        r_cx = z->cx; r_cy = z->cy; r_xh = z->xh;
        r_floor = s_floor[i]; r_flx = s_fl_bx[i]; r_fly = s_fl_by[i];
        for (int r = 0; r < ROWS; r++) r_hid[r] = -1;
        for (int dy = -ROW_OFF; dy < ROWS - ROW_OFF; dy++) {
            const int row = r_cy + dy - cam_y;
#if GLEXP != 2
            if ((unsigned)row < SCREEN_H) dirty_row(row, sx - z->xh, sx + z->xh + 1);
#endif
        }
#if GLEXP != 1
        draw_zone(z, i);
#endif
    }
}
