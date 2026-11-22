#include "glifo.h"
#include "glifo_rune_data.h"
#include "groundfx.h"
#include "collision.h"
#include "arpg.h"
#include "arpg_inv.h"
#include "allies.h"
#include "placeholders_gfx.h"
#include "sfx.h"
#include <stddef.h>

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
#define GL_AIM     RGB15(20, 16, 20)

#define GLIFO_CHEST_H 16        // [TUNABLE-PLACEHOLDER] the projectile leaves this high above the hero's feet
#define GLIFO_ARC_H 20          // [TUNABLE-PLACEHOLDER] extra height of the arc at mid flight
#define GLIFO_AIM_RING 10       // [TUNABLE-PLACEHOLDER] ground radius of the aim ring
#define GLIFO_FLASH_FRAMES 12   // [TUNABLE-PLACEHOLDER] detonation flash before the crack closes
#define GLIFO_TONGUES 6         // Zarza: flame tongues alive at once
#define GLIFO_TONGUE_PERIOD 20  // Zarza: frames of one tongue
#define GLIFO_BASE_R 40         // ground radius the baked rune was made for

typedef struct {
    int active;
    fixed x, y;             // ground position (8.8)
    fixed step_x, step_y;   // ground step per frame (8.8)
    int tx, ty;             // landing point (world px)
    int frame;              // frames flown
} GlifoShot;

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
} GlifoZone;

static GlifoShot s_shots[ARPG_GLIFO_MAX];
static GlifoZone s_zones[ARPG_GLIFO_MAX];
static int s_aiming = 0;
static int s_aim_x = 0, s_aim_y = 0;     // clamped target while the stylus aims (world px)
static uint8_t s_next_aura = 0;

static int glifo_count(void) {
    int n = 0;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        if (s_shots[i].active) n++;
        if (s_zones[i].active) n++;
    }
    return n;
}

// Ground metric: a point is inside a circle of ground radius r around (cx, cy).
static int ground_inside(int dx, int dy, int r) {
    return dx * dx + GROUND_DY2(dy) <= r * r;
}

static int throw_cost(void) {
    int c = ARPG_GLIFO_COST * (100 - arpg_inv_glifo_line(ARPG_LINE_COST)) / 100;
    return c < ARPG_GLIFO_COST_MIN ? ARPG_GLIFO_COST_MIN : c;
}

// Height of the arc above the ground at flight frame f: a line from chest height down to the floor plus a parabola.
static int arc_height(int f) {
    const int F = ARPG_GLIFO_FLIGHT;
    const int rem = F - f;
    return (GLIFO_CHEST_H * rem) / F + (4 * GLIFO_ARC_H * f * rem) / (F * F);
}

void glifo_reset(void) {
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        s_shots[i].active = 0;
        s_zones[i].active = 0;
    }
    s_aiming = 0;
}

void glifo_cancel_aim(void) { s_aiming = 0; }

void glifo_shift_y(int dy_px) {
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        if (s_shots[i].active) {
            s_shots[i].y += TO_FIXED(dy_px);
            s_shots[i].ty += dy_px;
        }
        if (s_zones[i].active) s_zones[i].cy += dy_px;
    }
    if (s_aiming) s_aim_y += dy_px;
}

int glifo_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y) {
    (void)touch_pressed;
    const int hx = TO_INT(hero_x), hy = TO_INT(hero_y);

    if (touch_down) {
        // Target = the touched world point, clamped to ARPG_GLIFO_RANGE from the hero (ground metric).
        int dx = touch_x - hx, dy = touch_y - hy;
        const int d2 = dx * dx + GROUND_DY2(dy);
        const int r2 = ARPG_GLIFO_RANGE * ARPG_GLIFO_RANGE;
        if (d2 > r2) {
            const int d = (int)sqrt32(d2);
            if (d > 0) {
                dx = dx * ARPG_GLIFO_RANGE / d;
                dy = dy * ARPG_GLIFO_RANGE / d;
            }
        }
        s_aim_x = hx + dx;
        s_aim_y = hy + dy;
        s_aiming = 1;
        return 1;
    }

    if (!s_aiming) return 0;
    s_aiming = 0;

    // Release: throw if there is mana and a free slot.
    const int cost = throw_cost();
    if (player->mana < cost || glifo_count() >= ARPG_GLIFO_MAX) return 0;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        if (s_shots[i].active) continue;
        player->mana -= cost;
        const int F = ARPG_GLIFO_FLIGHT;
        s_shots[i].active = 1;
        s_shots[i].x = hero_x;
        s_shots[i].y = hero_y;
        s_shots[i].step_x = (fixed)((s_aim_x - hx) * 256 / F);
        s_shots[i].step_y = (fixed)((s_aim_y - hy) * 256 / F);
        s_shots[i].tx = s_aim_x;
        s_shots[i].ty = s_aim_y;
        s_shots[i].frame = 0;
        sfx_play(SND_GLIFO_CAST, hx);
        break;
    }
    return 0;
}

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

void glifo_update(Enemy *enemies, int max_enemies) {
    // Flight: a projectile that reaches its frame lands as a rune with the auras equipped at the throw.
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        GlifoShot *s = &s_shots[i];
        if (!s->active) continue;
        s->x += s->step_x;
        s->y += s->step_y;
        if (++s->frame < ARPG_GLIFO_FLIGHT) continue;
        s->active = 0;
        for (int zi = 0; zi < ARPG_GLIFO_MAX; zi++) {
            GlifoZone *z = &s_zones[zi];
            if (z->active) continue;
            z->active = 1;
            z->cx = s->tx;
            z->cy = s->ty;
            z->radius = ARPG_GLIFO_RADIUS * (100 + arpg_inv_glifo_line(ARPG_LINE_RADIUS)) / 100;
            z->sc = z->radius * 256 / GLIFO_BASE_R;
            z->aura = (uint8_t)((arpg_inv_has_mechanic(ARPG_MECH_REDIL) ? GLIFO_AURA_REDIL : 0) |
                                (arpg_inv_has_mechanic(ARPG_MECH_ZARZA) ? GLIFO_AURA_ZARZA : 0));
            z->reopen = (uint8_t)(arpg_inv_has_mechanic(ARPG_MECH_DOBLE_SELLO) ? 1 : 0);
            z->seed = (uint8_t)(s_next_aura++ * 37u + 11u);
            zone_start(z);
            break;
        }
    }

    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        GlifoZone *z = &s_zones[i];
        if (!z->active) continue;
        const int t = z->t;
        if (t == z->t_open) sfx_play(SND_GLIFO_ACTIVATE, z->cx);
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

#define ROWS 96                 // rows below/above the centre kept in the occlusion cache (dy + 48)
#define ROW_OFF 48
#define X_HALF 76               // half-width queried for the occlusion of a row

static uint16_t *r_buf;
static int r_camx, r_camy, r_cx, r_cy;
static int8_t r_hid[ROWS];      // per row: -1 unknown, 0 clear, 1 a wall may hide something

static void put_rel(int dx, int dy, uint16_t col) {
    const int wy = r_cy + dy, sy = wy - r_camy;
    const int wx = r_cx + dx, sx = wx - r_camx;
    if ((unsigned)sy >= SCREEN_H || (unsigned)sx >= SCREEN_W) return;
    const int ri = dy + ROW_OFF;
    if ((unsigned)ri >= ROWS) return;
    int h = r_hid[ri];
    if (h < 0) {
        h = world_span_hidden(wy, r_cx - X_HALF, r_cx + X_HALF + 1, wy) ? 1 : 0;
        r_hid[ri] = (int8_t)h;
    }
    if (h && world_pixel_hidden(wx, wy, wy)) return;
    r_buf[sy * SCREEN_W + sx] = (uint16_t)(col | BIT(15));
}

static inline int scl(int v, int sc) { return (v * sc + (v < 0 ? -128 : 128)) / 256; }

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

static void draw_vortex(int T, const GlifoZone *z, int lim) {
    const int fr = (T >> 1) & 7;
    for (int i = 0; i < GLIFO_VX_BASE_N; i++) {
        const GlifoVx *p = &g_glifo_vx_base[i];
        if (p->rr > lim) break;
        put_rel(p->dx, p->dy, p->col == 0 ? GL_DEEP : p->col == 1 ? GL_ASH_C : GL_ASH_B);
    }
    for (int i = 0; i < GLIFO_VX_ARM_N; i++) {
        const GlifoVx *p = &g_glifo_vx_arm[fr][i];
        if (p->rr > lim || p->rr == 255) continue;
        put_rel(p->dx, p->dy, p->col == 3 ? GL_IVORY : p->col == 4 ? GL_GOLD : GL_AMBER);
    }
    (void)z;
}

static void draw_zone(const GlifoZone *z) {
    const int T = z->t;
    const int sc = z->sc;
    const int redil = (z->aura & GLIFO_AURA_REDIL) != 0;
    const GlifoPx *mask = redil ? g_glifo_twist : g_glifo_base;
    const int n = redil ? GLIFO_TWIST_N : GLIFO_BASE_N;
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
        const int dx = scl(q->dx, sc), dy = scl(q->dy, sc);
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
                if (q->flags & GLIFO_FL_FLARE) draw_tongue(scl(q->dx, sc), scl(q->dy, sc), h, 1);
            }
        }
    }

    // Detonation: a ring of light leaves the centre.
    if (flash) {
        GroundTarget g = { r_buf, r_camx, r_camy };
        const int age = T - z->t_det;
        const int rr = z->radius * (4 + age) / (4 + GLIFO_FLASH_FRAMES);
        gfx_ground_ring(&g, z->cx, z->cy, rr, age < 6 ? GL_IVORY : GL_GOLD, 0);
    }
}

void glifo_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    GroundTarget g = { buffer, cam_x, cam_y };
    r_buf = buffer; r_camx = cam_x; r_camy = cam_y;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        const GlifoZone *z = &s_zones[i];
        if (!z->active) continue;
        // Skip a rune that lies wholly off screen (its widest reach is the radius plus the flames and the well).
        const int sx = z->cx - cam_x, sy = z->cy - cam_y;
        if (sx + X_HALF < 0 || sx - X_HALF >= SCREEN_W || sy + 40 < 0 || sy - 40 >= SCREEN_H) continue;
        r_cx = z->cx; r_cy = z->cy;
        for (int r = 0; r < ROWS; r++) r_hid[r] = -1;
        for (int dy = -ROW_OFF; dy < ROWS - ROW_OFF; dy++) {
            const int row = r_cy + dy - cam_y;
            if ((unsigned)row < SCREEN_H) dirty_row(row, sx - X_HALF, sx + X_HALF + 1);
        }
        draw_zone(z);
    }
    if (s_aiming) gfx_ground_ring(&g, s_aim_x, s_aim_y, GLIFO_AIM_RING, GL_AIM, 0);
}

void glifo_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    for (int i = 0; i < ARPG_GLIFO_MAX; i++) {
        const GlifoShot *s = &s_shots[i];
        if (!s->active) continue;
        const int h = arc_height(s->frame);
        const int x0 = TO_INT(s->x) - cam_x - PH_MALDICION_W / 2;
        const int y0 = TO_INT(s->y) - cam_y - h - PH_MALDICION_H / 2;
        for (int row = 0; row < PH_MALDICION_H; row++) {
            const int y = y0 + row;
            if (y < 0 || y >= SCREEN_H) continue;
            dirty_row(y, x0, x0 + PH_MALDICION_W);
            for (int col = 0; col < PH_MALDICION_W; col++) {
                const int x = x0 + col;
                const uint16_t px = g_ph_maldicion[row * PH_MALDICION_W + col];
                if (px == 0 || x < 0 || x >= SCREEN_W) continue;
                buffer[y * SCREEN_W + x] = px | BIT(15);
            }
        }
    }
}
