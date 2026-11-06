// Grenade (DESIGN.md 4.9): arc thrown from the muzzle, fuse, blast damage and the three
// warning variants of g_fx_style (A ring, B bouncing sprite, C danger zone with a laser from space).
// Three passes: grenade_render_floor (ground decals, groundfx, under shadows and sprites),
// grenade_render (sprites with volume, C laser beam) and grenade_render_light (C light column,
// after the sprites). Integer and 8.8 fixed point only. Everything is drawn straight into the
// BGR555 page; every written span calls dirty_row().

#include "grenade.h"
#include "collision.h"

// ---------------------------------------------------------------------------
// Constants. Design numbers live in grenade.h and DESIGN.md 4.9.
// ---------------------------------------------------------------------------

#define GR_ARC_PEAK 28              // NOTE: peak height of the throw arc (px); DESIGN.md gives no number
#define GR_CANCEL_R 12              // stylus over the character: screen px around the body
#define GR_MARK_ARM 3               // half length of the aim cross (ground px)
#define GR_B_BOUNCE1_LEN 8          // NOTE: B bounce durations (frames) and peaks (px), DESIGN.md 4.9 gives the heights only
#define GR_B_BOUNCE1_PEAK 8
#define GR_B_BOUNCE2_LEN 6
#define GR_B_BOUNCE2_PEAK 3
#define GR_C_FALL_FRAMES 12         // C: the laser is visible during the last 12 frames of the fuse
#define GR_C_FALL_STEP 5            // C: px the laser tip descends per frame (60 px above the ground down to 0)
#define GR_C_RAMP (GRENADE_FUSE_FRAMES - GR_C_FALL_FRAMES)  // C: light ramp ends when the laser starts (78 frames)
#define GR_C_LIGHT_LO 2             // C: light column level at the start of the fuse
#define GR_C_LIGHT_HI 12            // C: light column level at the laser start (kept until the blast)
#define GR_C_LIGHT_RED 10           // C: extra red at the maximum
#define GR_C_LIGHT_H 80             // C: height of the light column (px)
// C zone: two decal colours for the hatch (BGR555 | BIT(15), the same values skip the light pass)
#define GR_C_DECAL_A (RGB15(10, 2, 2) | BIT(15))
#define GR_C_DECAL_B (RGB15(5, 1, 1) | BIT(15))
#define GR_SHOCK_FRAMES 8           // shock ring grows to the blast radius in 8 frames
#define GR_FLASH_FRAMES 2
#define GR_BLAST_SLOTS 2            // explosions cannot overlap more than this (grenades are 60 frames apart)
#define GR_GFX_MAX 32               // one shared budget for lobes, debris and smoke (AGENTS.md / task budget)
#define GR_DISK_R 12                // largest filled disk (lobes up to 11 px, smoke up to 11 px)
#define GR_LOS_STEP_SHIFT 2         // line of sight sampled every 4 ground px
#define GR_GRAVITY 40               // 8.8 px/frame^2 for debris
#define GR_SMOKE_RISE 128           // 8.8 px/frame
#define GR_SMOKE_LIFE 40
#define GR_HITSTOP 3
#define GR_RING_GAP 5               // gapped shock ring: 5 of every 8 segments drawn (~65 %)
#define GR_DEBRIS_N 14
#define GR_SMOKE_MIN 4
#define GR_SMOKE_MAX 5
#define GR_LOBE_MIN 7
#define GR_LOBE_MAX 9

#define GR_FX(v) ((fixed)(v) * 256)  // int to 8.8 without shifting negative values

// Colours (BGR555 with the alpha bit). Fire ramp first: white, yellow, orange, red, dark red, grey.
enum {
    K_WHITE = 0, K_YELLOW, K_ORANGE, K_RED, K_DARKRED, K_GREY,
    K_BONE,
    K_SMOKE_A, K_SMOKE_B,
    K_MARK, K_MARK_CROSS,
    K_RING_A,
    K_FAINT,
    K_BODY, K_LIGHT, K_SHADOW, K_SPRITE_RED, K_SPRITE_DARK,
    K_RING_C, K_BEAM_EDGE,
    K_NUM
};

static const uint16_t s_col[K_NUM] = {
    [K_WHITE]       = RGB15(31, 31, 29) | BIT(15),
    [K_YELLOW]      = RGB15(31, 26, 6) | BIT(15),
    [K_ORANGE]      = RGB15(30, 13, 3) | BIT(15),
    [K_RED]         = RGB15(22, 4, 2) | BIT(15),
    [K_DARKRED]     = RGB15(7, 1, 1) | BIT(15),
    [K_GREY]        = RGB15(10, 10, 11) | BIT(15),
    [K_BONE]        = RGB15(27, 26, 21) | BIT(15),
    [K_SMOKE_A]     = RGB15(14, 14, 15) | BIT(15),
    [K_SMOKE_B]     = RGB15(7, 7, 8) | BIT(15),
    [K_MARK]        = RGB15(16, 22, 24) | BIT(15),
    [K_MARK_CROSS]  = RGB15(31, 31, 31) | BIT(15),
    [K_RING_A]      = RGB15(28, 17, 4) | BIT(15),
    [K_FAINT]       = RGB15(8, 10, 11) | BIT(15),
    [K_BODY]        = RGB15(6, 8, 6) | BIT(15),
    [K_LIGHT]       = RGB15(31, 31, 20) | BIT(15),
    [K_SHADOW]      = RGB15(1, 1, 2) | BIT(15),
    [K_SPRITE_RED]  = RGB15(31, 3, 2) | BIT(15),
    [K_SPRITE_DARK] = RGB15(9, 2, 1) | BIT(15),
    [K_RING_C]      = RGB15(31, 10, 8) | BIT(15),
    [K_BEAM_EDGE]   = RGB15(31, 14, 12) | BIT(15),
};

enum { G_IDLE = 0, G_AIMING };
enum { PK_NONE = 0, PK_LOBE, PK_DEBRIS, PK_SMOKE };

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

typedef struct {
    int active;
    int age;                    // frames since the throw
    fixed cur_x, cur_y;         // ground position now (8.8)
    fixed step_x, step_y;       // ground motion per frame during the flight (8.8)
    fixed tx, ty;               // landing point = blast centre (8.8)
    int start_h;                // muzzle height at the throw (px)
} Grenade;

typedef struct {
    int active;
    int age;
    fixed cx, cy;
    int seed;                   // phase of the gapped shock ring
} Blast;

typedef struct {
    int kind;                   // PK_*
    int size;                   // lobe / smoke radius (px)
    int delay;                  // frames before it appears
    int age;                    // frames since it appeared
    int life;
    int peak;                   // lobe: height it rises to (px)
    fixed cx, cy;               // blast centre (ground)
    fixed ox, oy, oh;           // offset from the centre (ground) and height (8.8)
    fixed vx, vy, vh;           // velocity (8.8 per frame)
} Particle;

static Grenade s_gren[GRENADE_MAX_ACTIVE];
static Blast s_blast[GR_BLAST_SLOTS];
static Particle s_fx[GR_GFX_MAX];
static int s_state = G_IDLE;
static int s_cancelled = 0;
static int s_aim_valid = 0;
static fixed s_aim_x = 0, s_aim_y = 0;          // clipped landing point of the aim (8.8)
static fixed s_player_x = 0, s_player_y = 0;    // last ground position seen by grenade_input()
static int s_cooldown = 0;

// Precomputed tables (filled by grenade_init, read-only afterwards).
static uint8_t s_disk_hw[GR_DISK_R + 1][GR_DISK_R + 1];     // half width of a filled disk, [radius][|dy|]
static uint8_t s_arc[GRENADE_FLIGHT_FRAMES + 1];            // height of the throw arc (px)

// ---------------------------------------------------------------------------
// Integer helpers
// ---------------------------------------------------------------------------

static int gr_iabs(int v) {
    return v < 0 ? -v : v;
}

static int gr_sgn(int v) {
    return v > 0 ? 1 : (v < 0 ? -1 : 0);
}

static uint32_t gr_isqrt(uint32_t n) {
    if (n == 0) return 0;
    uint32_t root = 0;
    uint32_t bit = 1u << 30;
    while (bit > n) bit >>= 2;
    while (bit != 0) {
        if (n >= root + bit) {
            n -= root + bit;
            root = (root >> 1) + bit;
        } else {
            root >>= 1;
        }
        bit >>= 2;
    }
    return root;
}

// ---------------------------------------------------------------------------
// Drawing primitives (direct BGR555 writes; render never changes game state)
// ---------------------------------------------------------------------------

static void gr_plot(uint16_t *buf, int x, int y, int k) {
    if ((unsigned)x >= SCREEN_W || (unsigned)y >= SCREEN_H) return;
    buf[y * SCREEN_W + x] = s_col[k];
    dirty_row(y, x, x + 1);
}

// Horizontal span [x0, x1) clipped to the screen.
static void gr_span(uint16_t *buf, int y, int x0, int x1, int k) {
    if ((unsigned)y >= SCREEN_H) return;
    if (x0 < 0) x0 = 0;
    if (x1 > SCREEN_W) x1 = SCREEN_W;
    if (x0 >= x1) return;
    uint16_t c = s_col[k];
    uint16_t *row = buf + y * SCREEN_W;
    for (int x = x0; x < x1; x++) row[x] = c;
    dirty_row(y, x0, x1);
}

// Solid screen disk.
static void gr_disk(uint16_t *buf, int cx, int cy, int r, int k) {
    if (r < 0) return;
    if (r > GR_DISK_R) r = GR_DISK_R;
    for (int dy = -r; dy <= r; dy++) {
        int hw = s_disk_hw[r][gr_iabs(dy)];
        gr_span(buf, cy + dy, cx - hw, cx + hw + 1, k);
    }
}

// Smoke puff: grey inside, checkerboard along the rim.
static void gr_puff(uint16_t *buf, int cx, int cy, int r) {
    if (r < 0) return;
    if (r > GR_DISK_R) r = GR_DISK_R;
    for (int dy = -r; dy <= r; dy++) {
        int hw = s_disk_hw[r][gr_iabs(dy)];
        int y = cy + dy;
        for (int x = cx - hw; x <= cx + hw; x++) {
            int edge = (x == cx - hw) || (x == cx + hw) || (dy == -r) || (dy == r);
            int k = K_SMOKE_A;
            if (edge && ((x ^ y) & 1)) k = K_SMOKE_B;
            gr_plot(buf, x, y, k);
        }
    }
}

// One-pixel Bresenham line (integer only).
static void gr_line(uint16_t *buf, int x0, int y0, int x1, int y1, int k) {
    int dx = gr_iabs(x1 - x0);
    int dy = -gr_iabs(y1 - y0);
    int sx = x0 < x1 ? 1 : -1;
    int sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (;;) {
        gr_plot(buf, x0, y0, k);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// Blast flash: white star with ten rays of uneven length, two frames.
static void gr_flash(uint16_t *buf, int cx, int cy, int age) {
    static const int RX[10] = { 16, 13, 5, -5, -13, -16, -13, -5, 5, 13 };
    static const int RY[10] = { 0, 9, 15, 15, 9, 0, -9, -15, -15, -9 };
    static const int LEN[10] = { 14, 8, 11, 7, 13, 14, 8, 11, 7, 13 };
    int color = age == 0 ? K_WHITE : K_YELLOW;
    gr_plot(buf, cx, cy, K_WHITE);
    for (int k = 0; k < 10; k++) {
        if (age > 0 && (k & 1)) continue;   // second frame: half the rays
        int ex = cx + ((RX[k] * LEN[k]) >> 4);
        int ey = cy + ((RY[k] * LEN[k]) >> 4);
        gr_line(buf, cx, cy, ex, ey, color);
    }
}

// ---------------------------------------------------------------------------
// Flight
// ---------------------------------------------------------------------------

static int gr_flight_height(const Grenade *g) {
    int a = g->age < GRENADE_FLIGHT_FRAMES ? g->age : GRENADE_FLIGHT_FRAMES;
    return s_arc[a] + (g->start_h * (GRENADE_FLIGHT_FRAMES - a)) / GRENADE_FLIGHT_FRAMES;
}

// Variant B only: flight, then two bounces on the ground (render-only, the blast time does not change).
static int gr_b_height(const Grenade *g) {
    int a = g->age;
    if (a <= GRENADE_FLIGHT_FRAMES) return gr_flight_height(g);
    a -= GRENADE_FLIGHT_FRAMES;
    if (a < GR_B_BOUNCE1_LEN) {
        return (4 * GR_B_BOUNCE1_PEAK * a * (GR_B_BOUNCE1_LEN - a)) / (GR_B_BOUNCE1_LEN * GR_B_BOUNCE1_LEN);
    }
    a -= GR_B_BOUNCE1_LEN;
    if (a < GR_B_BOUNCE2_LEN) {
        return (4 * GR_B_BOUNCE2_PEAK * a * (GR_B_BOUNCE2_LEN - a)) / (GR_B_BOUNCE2_LEN * GR_B_BOUNCE2_LEN);
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Aiming and throwing
// ---------------------------------------------------------------------------

static int gr_count_active(void) {
    int n = 0;
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        if (s_gren[i].active) n++;
    }
    return n;
}

// Landing point under the stylus: capped at the throw range, then cut at the last
// free point of the straight line from the player (2 px steps).
static void gr_compute_aim(const WeaponInput *in) {
    fixed px = in->player_x;
    fixed py = in->player_y;
    int dx = in->touch_x - TO_INT(px);
    int dy = in->touch_y - TO_INT(py);
    int range = g_weapon_tuning[WEAPON_GRENADE].projectile_range;
    int d = (int)gr_isqrt((uint32_t)(dx * dx + GROUND_DY2(dy)));
    if (d > range && d > 0) {
        dx = dx * range / d;        // NOTE: division only while aiming (one per frame), not in render
        dy = dy * range / d;
    }
    fixed tx = px + GR_FX(dx);
    fixed ty = py + GR_FX(dy);

    int len = gr_iabs(dx) > gr_iabs(dy) ? gr_iabs(dx) : gr_iabs(dy);
    int n = len >> 1;
    fixed lx = px;
    fixed ly = py;
    if (n > 0) {
        fixed stepx = (tx - px) / n;
        fixed stepy = (ty - py) / n;
        for (int i = 1; i <= n; i++) {
            fixed x = px + stepx * i;
            fixed y = py + stepy * i;
            if (!bullet_position_is_free(x, y)) break;
            lx = x;
            ly = y;
        }
    }
    s_aim_x = lx;
    s_aim_y = ly;
    s_aim_valid = 1;
}

static void gr_throw(const WeaponInput *in) {
    Grenade *g = NULL;
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        if (!s_gren[i].active) { g = &s_gren[i]; break; }
    }
    if (!g) return;
    g->active = 1;
    g->age = 0;
    g->cur_x = in->muzzle_x;
    g->cur_y = in->muzzle_y;
    g->tx = s_aim_x;
    g->ty = s_aim_y;
    g->step_x = (g->tx - g->cur_x) / GRENADE_FLIGHT_FRAMES;
    g->step_y = (g->ty - g->cur_y) / GRENADE_FLIGHT_FRAMES;
    g->start_h = in->muzzle_h;
    s_cooldown = g_weapon_tuning[WEAPON_GRENADE].fire_cooldown;
}

void grenade_init(void) {
    memset(s_gren, 0, sizeof s_gren);
    memset(s_blast, 0, sizeof s_blast);
    memset(s_fx, 0, sizeof s_fx);
    s_state = G_IDLE;
    s_cancelled = 0;
    s_aim_valid = 0;
    s_aim_x = 0;
    s_aim_y = 0;
    s_player_x = 0;
    s_player_y = 0;
    s_cooldown = 0;

    for (int r = 0; r <= GR_DISK_R; r++) {
        for (int d = 0; d <= GR_DISK_R; d++) {
            s_disk_hw[r][d] = d <= r ? (uint8_t)gr_isqrt((uint32_t)(r * r - d * d)) : 0;
        }
    }
    for (int a = 0; a <= GRENADE_FLIGHT_FRAMES; a++) {
        s_arc[a] = (uint8_t)((4 * GR_ARC_PEAK * a * (GRENADE_FLIGHT_FRAMES - a)) /
                             (GRENADE_FLIGHT_FRAMES * GRENADE_FLIGHT_FRAMES));
    }
}

void grenade_shift_y(int dy_px) {
    fixed shift = TO_FIXED(dy_px);
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++)
        if (s_gren[i].active) { s_gren[i].cur_y += shift; s_gren[i].ty += shift; }
    for (int i = 0; i < GR_BLAST_SLOTS; i++)
        if (s_blast[i].active) s_blast[i].cy += shift;
    for (int i = 0; i < GR_GFX_MAX; i++)
        if (s_fx[i].kind != PK_NONE) s_fx[i].cy += shift;
    if (s_aim_valid) s_aim_y += shift;
    s_player_y += shift;
}

void grenade_set_player_pos(fixed x, fixed y) {
    s_player_x = x;
    s_player_y = y;
}

void grenade_cancel(void) {
    s_state = G_IDLE;
    s_cancelled = 0;
    s_aim_valid = 0;
}

int grenade_input(PlayerState *player, const WeaponInput *in) {
    if (!player || !in) return 0;
    // Remembered for the blast (grenade_update has no player position); see the report.
    s_player_x = in->player_x;
    s_player_y = in->player_y;

    if (s_state == G_IDLE) {
        if (!in->touch_pressed || s_cooldown > 0 || gr_count_active() >= GRENADE_MAX_ACTIVE) return 0;
        s_state = G_AIMING;
        s_cancelled = 0;
        s_aim_valid = 0;
    }

    // G_AIMING
    if (!in->touch_down) {
        int fired = 0;
        if (!s_cancelled && s_aim_valid) {
            gr_throw(in);
            fired = 1;
        }
        s_state = G_IDLE;
        s_cancelled = 0;
        s_aim_valid = 0;
        return fired ? WEAPON_RESULT_FIRED : 0;
    }

    if (s_cancelled) return 0;

    // Dragging the stylus over the character cancels the throw (no rooting).
    int bx = in->touch_x - TO_INT(in->player_x);
    int by = in->touch_y - (TO_INT(in->player_y) - in->muzzle_h);
    if (bx * bx + by * by <= GR_CANCEL_R * GR_CANCEL_R) {
        s_cancelled = 1;
        s_aim_valid = 0;
        return 0;
    }
    gr_compute_aim(in);
    return 0;
}

// ---------------------------------------------------------------------------
// Blast
// ---------------------------------------------------------------------------

// True when no bullet-blocking cell lies between the two ground points (sampled every 4 px).
static int gr_clear_line(fixed x0, fixed y0, fixed x1, fixed y1) {
    int len = gr_iabs(TO_INT(x1 - x0));
    int ly = gr_iabs(TO_INT(y1 - y0));
    if (ly > len) len = ly;
    int n = len >> GR_LOS_STEP_SHIFT;
    if (n < 2) return 1;
    fixed sx = (x1 - x0) / n;
    fixed sy = (y1 - y0) / n;
    for (int i = 1; i < n; i++) {
        if (!bullet_position_is_free(x0 + sx * i, y0 + sy * i)) return 0;
    }
    return 1;
}

static Particle *gr_alloc_particle(void) {
    for (int i = 0; i < GR_GFX_MAX; i++) {
        if (s_fx[i].kind == PK_NONE) return &s_fx[i];
    }
    return NULL;   // pool full: the effect is dropped, the blast still happens
}

static void gr_spawn_blast(fixed cx, fixed cy) {
    for (int i = 0; i < GR_BLAST_SLOTS; i++) {
        if (s_blast[i].active) continue;
        s_blast[i].active = 1;
        s_blast[i].age = 0;
        s_blast[i].cx = cx;
        s_blast[i].cy = cy;
        s_blast[i].seed = rng_range(0, 7);
        break;
    }

    // Fireball: a cluster of lobes, rising while it grows.
    int lobes = rng_range(GR_LOBE_MIN, GR_LOBE_MAX);
    for (int i = 0; i < lobes; i++) {
        Particle *p = gr_alloc_particle();
        if (!p) break;
        p->kind = PK_LOBE;
        p->size = rng_range(7, 12);
        p->delay = rng_range(0, 4);
        p->age = 0;
        p->life = rng_range(15, 19);
        p->peak = rng_range(10, 18);
        p->cx = cx;
        p->cy = cy;
        p->ox = GR_FX(rng_range(-28, 28));
        p->oy = GR_FX(rng_range(-14, 14));
        p->oh = 0;
        p->vx = 0;
        p->vy = 0;
        p->vh = 0;
    }

    // Debris and embers, with gravity.
    for (int i = 0; i < GR_DEBRIS_N; i++) {
        Particle *p = gr_alloc_particle();
        if (!p) break;
        p->kind = PK_DEBRIS;
        p->size = 0;
        p->delay = 0;
        p->age = 0;
        p->life = rng_range(18, 26);
        p->peak = 0;
        p->cx = cx;
        p->cy = cy;
        p->ox = 0;
        p->oy = 0;
        p->oh = 0;
        p->vx = rng_range(-640, 640);
        p->vy = rng_range(-640, 640);
        p->vh = rng_range(200, 520);
    }

    // Smoke puffs that rise slowly.
    int puffs = rng_range(GR_SMOKE_MIN, GR_SMOKE_MAX);
    for (int i = 0; i < puffs; i++) {
        Particle *p = gr_alloc_particle();
        if (!p) break;
        p->kind = PK_SMOKE;
        p->size = rng_range(4, 6);
        p->delay = rng_range(0, 6);
        p->age = 0;
        p->life = GR_SMOKE_LIFE;
        p->peak = 0;
        p->cx = cx;
        p->cy = cy;
        p->ox = GR_FX(rng_range(-14, 14));
        p->oy = GR_FX(rng_range(-7, 7));
        p->oh = GR_FX(4);
        p->vx = rng_range(-40, 40);
        p->vy = rng_range(-20, 20);
        p->vh = 0;
    }
}

static void gr_explode(Grenade *g, Enemy *enemies, int max_enemies, PlayerState *player) {
    fixed cx = g->tx;
    fixed cy = g->ty;
    int icx = TO_INT(cx);
    int icy = TO_INT(cy);
    int R = GRENADE_RADIUS;
    int R2 = R * R;
    const WeaponTuning *t = &g_weapon_tuning[WEAPON_GRENADE];

    if (enemies) {
        for (int i = 0; i < max_enemies; i++) {
            Enemy *e = &enemies[i];
            if (!e->active || e->hp <= 0) continue;
            int dx = TO_INT(e->x) - icx;
            int dy = TO_INT(e->y) - icy;
            int d2 = dx * dx + GROUND_DY2(dy);
            if (d2 > R2) continue;
            if (!gr_clear_line(cx, cy, e->x, e->y)) continue;

            int d = (int)gr_isqrt((uint32_t)d2);
            int dmg = GRENADE_DAMAGE_RIM + (t->damage_per_hit - GRENADE_DAMAGE_RIM) * (R - d) / R;
            if (dmg < 1) dmg = 1;

            fixed dir_x = 0;
            fixed dir_y = 0;
            if (d > 0) {
                dir_x = dx * 256 / d;
                dir_y = dy * 256 / d;
            }
            fixed mag = t->knockback * (R - d) / R;      // 8.8 px/frame, strongest at the centre
            fixed kx = (dir_x * mag) >> 8;
            fixed ky = (dir_y * mag) >> 8;

            enemy_hit(e, dmg, kx, ky);
            if (e->hp > 0) {
                e->knock_vx = kx;
                e->knock_vy = ky;
                e->stun_timer = t->stun_frames;
            }
        }
    }

    // Friendly fire: the player takes one hit if inside the radius with a clear line.
    if (player && !player->is_dead) {
        int pdx = TO_INT(s_player_x) - icx;
        int pdy = TO_INT(s_player_y) - icy;
        if (pdx * pdx + GROUND_DY2(pdy) <= R2 && gr_clear_line(cx, cy, s_player_x, s_player_y)) {
            player_take_hit(player);
        }
    }

    weapons_request_shake(t->shake_amp, t->shake_frames);
    if (g_hitstop_frames < GR_HITSTOP) g_hitstop_frames = GR_HITSTOP;
    gr_spawn_blast(cx, cy);
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

void grenade_update(Enemy *enemies, int max_enemies, PlayerState *player) {
    if (s_cooldown > 0) s_cooldown--;

    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        Grenade *g = &s_gren[i];
        if (!g->active) continue;
        g->age++;
        if (g->age < GRENADE_FLIGHT_FRAMES) {
            g->cur_x += g->step_x;
            g->cur_y += g->step_y;
        } else if (g->age == GRENADE_FLIGHT_FRAMES) {
            g->cur_x = g->tx;
            g->cur_y = g->ty;
        }
        if (g->age >= GRENADE_FUSE_FRAMES) {
            gr_explode(g, enemies, max_enemies, player);
            g->active = 0;
        }
    }

    for (int i = 0; i < GR_BLAST_SLOTS; i++) {
        if (!s_blast[i].active) continue;
        s_blast[i].age++;
        if (s_blast[i].age >= GR_SHOCK_FRAMES) s_blast[i].active = 0;
    }

    for (int i = 0; i < GR_GFX_MAX; i++) {
        Particle *p = &s_fx[i];
        if (p->kind == PK_NONE) continue;
        if (p->delay > 0) {
            p->delay--;
            continue;
        }
        p->age++;
        if (p->age >= p->life) {
            p->kind = PK_NONE;
            continue;
        }
        switch (p->kind) {
        case PK_LOBE: {
            int rise = p->age < 6 ? p->age : 6;
            p->oh = GR_FX(p->peak * rise / 6);
            break;
        }
        case PK_DEBRIS:
            p->ox += p->vx;
            p->oy += p->vy;
            p->oh += p->vh;
            p->vh -= GR_GRAVITY;
            if (p->oh <= 0) {
                p->oh = 0;
                p->vh = 0;
                p->vx = (p->vx * 3) >> 2;
                p->vy = (p->vy * 3) >> 2;
            }
            break;
        case PK_SMOKE:
            p->ox += p->vx;
            p->oy += p->vy;
            p->oh += GR_SMOKE_RISE;
            break;
        default:
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Rendering. Read-only with respect to the game state. Ground coordinates go to groundfx
// (world px of the feet, the camera is in the GroundTarget); screen coordinates only for the
// volumetric sprites and the C laser.
// ---------------------------------------------------------------------------

// Floor pass: everything that lies on the ground. Drawn under shadows and sprites.
void grenade_render_floor(const GroundTarget *gt) {
    if (!gt || !gt->buffer) return;
    int style = g_fx_style;

    // Aim marker: dotted ground ellipse of the grenade radius with a small cross on the ground.
    if (s_state == G_AIMING && !s_cancelled && s_aim_valid) {
        int mx = TO_INT(s_aim_x);
        int my = TO_INT(s_aim_y);
        gfx_ground_ring(gt, mx, my, GRENADE_RADIUS, s_col[K_MARK], 2);
        for (int i = -GR_MARK_ARM; i <= GR_MARK_ARM; i++) {
            gfx_ground_px(gt, mx + i, my, s_col[K_MARK_CROSS]);
            gfx_ground_px(gt, mx, my + i, s_col[K_MARK_CROSS]);
        }
    }

    // Warning on the ground, per variant.
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        const Grenade *gn = &s_gren[i];
        if (!gn->active) continue;
        int tx = TO_INT(gn->tx);
        int ty = TO_INT(gn->ty);
        if (style == 0) {
            // A: ring that shrinks towards the centre during the fuse.
            int r = (GRENADE_RADIUS * (GRENADE_FUSE_FRAMES - gn->age)) / GRENADE_FUSE_FRAMES;
            if (r > 0) gfx_ground_ring(gt, tx, ty, r, s_col[K_RING_A], 0);
        } else if (style == 1) {
            // B: faint dotted circle of the radius, and the small soft shadow under the bouncing grenade.
            gfx_ground_ring(gt, tx, ty, GRENADE_RADIUS, s_col[K_FAINT], 2);
            gfx_ground_disc(gt, TO_INT(gn->cur_x), TO_INT(gn->cur_y), 3, s_col[K_SHADOW], GFX_FILL_CHECKER, 0);
        } else {
            // C: hatched danger zone in two dark reds, with a bright rim. The hatch slides between
            // two phases (soft blink); the zone is never switched off.
            int ph = (gn->age >> 3) & 1;
            gfx_ground_disc(gt, tx, ty, GRENADE_RADIUS, GR_C_DECAL_A, GFX_FILL_HATCH, ph);
            gfx_ground_disc(gt, tx, ty, GRENADE_RADIUS, GR_C_DECAL_B, GFX_FILL_HATCH, ph + 2);
            gfx_ground_ring(gt, tx, ty, GRENADE_RADIUS, s_col[K_RING_C], 0);
        }
    }

    // Shock wave: pale, gapped ring growing to the blast radius (5 of 8 segments drawn).
    for (int i = 0; i < GR_BLAST_SLOTS; i++) {
        const Blast *b = &s_blast[i];
        if (!b->active) continue;
        int cx = TO_INT(b->cx);
        int cy = TO_INT(b->cy);
        int a = (GRENADE_RADIUS * (b->age + 1)) / GR_SHOCK_FRAMES;
        for (int sg = 0; sg < 8; sg++) {
            if (((sg + b->seed) & 7) >= GR_RING_GAP) continue;
            gfx_ground_arc(gt, cx, cy, a, 4 * sg, 4 * sg + 4, s_col[K_BONE], 1);
        }
    }
}

// Sprites pass: objects with volume, drawn over the actors. Ground decals live in the floor pass.
void grenade_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    int style = g_fx_style;

    // Smoke at the back.
    for (int i = 0; i < GR_GFX_MAX; i++) {
        const Particle *p = &s_fx[i];
        if (p->kind != PK_SMOKE || p->delay > 0) continue;
        int sx = TO_INT(p->cx + p->ox) - cam_x;
        int sy = TO_INT(p->cy + p->oy - p->oh) - cam_y;
        gr_puff(buffer, sx, sy, p->size + (p->age >> 3));
    }

    // Debris: short strokes along the velocity, orange to grey.
    for (int i = 0; i < GR_GFX_MAX; i++) {
        const Particle *p = &s_fx[i];
        if (p->kind != PK_DEBRIS) continue;
        int sx = TO_INT(p->cx + p->ox) - cam_x;
        int sy = TO_INT(p->cy + p->oy - p->oh) - cam_y;
        int f = (p->age * 3) / p->life;
        int k = f == 0 ? K_ORANGE : (f == 1 ? K_RED : K_GREY);
        gr_line(buffer, sx - gr_sgn(p->vx), sy - gr_sgn(p->vy), sx, sy, k);
    }

    // Fireball lobes: two tones, the core shifted up and to the left.
    for (int i = 0; i < GR_GFX_MAX; i++) {
        const Particle *p = &s_fx[i];
        if (p->kind != PK_LOBE || p->delay > 0) continue;
        int sx = TO_INT(p->cx + p->ox) - cam_x;
        int sy = TO_INT(p->cy + p->oy - p->oh) - cam_y;
        int f = (p->age * 6) / p->life;
        if (f > 5) f = 5;
        int body = f < 5 ? f + 1 : 5;   // colder body
        int core = f;                   // hotter core
        int rad = p->size;
        if (p->age < 3) rad = (p->size * (p->age + 2)) / 5;
        if (p->age > 10) rad -= (p->age - 10) / 2;
        if (rad < 1) rad = 1;
        gr_disk(buffer, sx, sy, rad, body);
        gr_disk(buffer, sx - rad / 3, sy - rad / 3, rad / 2, core);
    }

    // Blast flash on top of the fireball.
    for (int i = 0; i < GR_BLAST_SLOTS; i++) {
        const Blast *b = &s_blast[i];
        if (!b->active || b->age >= GR_FLASH_FRAMES) continue;
        int cx = TO_INT(b->cx) - cam_x;
        int cy = TO_INT(b->cy) - cam_y - 6;
        gr_flash(buffer, cx, cy, b->age);
    }

    // The grenades themselves.
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        const Grenade *g = &s_gren[i];
        if (!g->active) continue;
        int sx = TO_INT(g->cur_x) - cam_x;
        int sy = TO_INT(g->cur_y) - cam_y;
        if (style == 0) {
            // A: bright point on the arc while in flight.
            if (g->age <= GRENADE_FLIGHT_FRAMES) {
                int hy = sy - gr_flight_height(g);
                gr_plot(buffer, sx, hy, K_LIGHT);
                gr_plot(buffer, sx + 1, hy, K_LIGHT);
                gr_plot(buffer, sx, hy + 1, K_LIGHT);
                gr_plot(buffer, sx + 1, hy + 1, K_LIGHT);
            }
        } else if (style == 1) {
            // B: 4x4 sprite that bounces; the red light blinks faster and faster.
            int hy = sy - gr_b_height(g);
            int lit = ((g->age * g->age) >> 9) & 1;
            for (int y = hy - 2; y < hy + 2; y++) {
                gr_span(buffer, y, sx - 2, sx + 2, K_BODY);
            }
            int lk = lit ? K_SPRITE_RED : K_SPRITE_DARK;
            gr_plot(buffer, sx - 1, hy - 1, lk);
            gr_plot(buffer, sx, hy - 1, lk);
            gr_plot(buffer, sx - 1, hy, lk);
            gr_plot(buffer, sx, hy, lk);
        } else {
            // C: laser from the top of the screen onto the target during the last frames. The tip
            // descends GR_C_FALL_STEP px per frame and touches the ground on the last drawn frame.
            if (g->age >= GRENADE_FUSE_FRAMES - GR_C_FALL_FRAMES) {
                int tx = TO_INT(g->tx) - cam_x;
                int ty = TO_INT(g->ty) - cam_y;
                int tip = ty - GR_C_FALL_STEP * (GRENADE_FUSE_FRAMES - 1 - g->age);
                int ybot = tip < SCREEN_H ? tip : SCREEN_H - 1;
                for (int y = 0; y <= ybot; y++) {
                    gr_plot(buffer, tx, y, K_WHITE);        // 2 px beam: white core ...
                    gr_plot(buffer, tx + 1, y, K_BEAM_EDGE); // ... light red edge
                }
                gr_span(buffer, tip, tx - 1, tx + 3, K_WHITE);  // falling head
            }
        }
    }
}

// Light pass: after the sprites. Variant C only: the column over the zone lights the actors inside.
void grenade_render_light(const GroundTarget *gt) {
    if (!gt || !gt->buffer || g_fx_style != 2) return;
    for (int i = 0; i < GRENADE_MAX_ACTIVE; i++) {
        const Grenade *g = &s_gren[i];
        if (!g->active || g->age >= GRENADE_FUSE_FRAMES) continue;
        int ramp = g->age < GR_C_RAMP ? g->age : GR_C_RAMP;
        int level = GR_C_LIGHT_LO + ((GR_C_LIGHT_HI - GR_C_LIGHT_LO) * ramp) / GR_C_RAMP;
        int red = (GR_C_LIGHT_RED * ramp) / GR_C_RAMP;
        gfx_light_column(gt, TO_INT(g->tx), TO_INT(g->ty), GRENADE_RADIUS, GR_C_LIGHT_H,
                         level, red, GR_C_DECAL_A, GR_C_DECAL_B);
    }
}
