#include "curse.h"
#include "groundfx.h"
#include "collision.h"
#include "arpg.h"
#include "arpg_tree.h"
#include "allies.h"
#include "placeholders_gfx.h"
#include "sfx.h"
#include <stddef.h>

// Curse look and arc (DESIGN.md 7.3). Colours are BGR555 without the alpha bit (gfx_* add it).
#define CURSE_CHEST_H 16        // [TUNABLE-PLACEHOLDER] the projectile leaves this high above the hero's feet
#define CURSE_ARC_H 20          // [TUNABLE-PLACEHOLDER] extra height of the arc at mid flight
#define CURSE_BLINK_FRAMES 60   // [TUNABLE-PLACEHOLDER] last frames of a zone: its ring blinks
#define CURSE_AIM_RING 10       // [TUNABLE-PLACEHOLDER] ground radius of the aim ring
#define CURSE_RING_DASH 3       // dashed ring: one dash every 3 outline pixels
#define CURSE_FILL RGB15(9, 6, 10)     // ashen violet, hatched
#define CURSE_RING RGB15(16, 11, 17)   // zone edge
#define CURSE_FILL_DIM RGB15(5, 3, 6)  // arming: same drawing, darker (DESIGN.md 7.3, tenue durante la espera)
#define CURSE_RING_DIM RGB15(9, 6, 10)
#define CURSE_AIM RGB15(20, 16, 20)    // aim ring

typedef struct {
    int active;
    fixed x, y;             // ground position (8.8)
    fixed step_x, step_y;   // ground step per frame (8.8)
    int tx, ty;             // landing point (world px)
    int frame;              // frames flown
} CurseShot;

typedef struct {
    int active;
    int cx, cy;             // centre (world px)
    int radius;             // ground radius
    int frames_left;        // live frames (slowing) left
    int arm_frames;         // frames left before the glifo acts (0 = slowing already)
    int tick_timer;         // frames until the next burn application (only with the tree node)
    int phase;              // hatch animation
} CurseZone;

static CurseShot s_shots[ARPG_CURSE_MAX];
static CurseZone s_zones[ARPG_CURSE_MAX];
static int s_aiming = 0;
static int s_aim_x = 0, s_aim_y = 0;     // clamped target while the stylus aims (world px)

static int curse_count(void) {
    int n = 0;
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        if (s_shots[i].active) n++;
        if (s_zones[i].active) n++;
    }
    return n;
}

static int zone_radius(void) { return arpg_tree_has(7) ? ARPG_CURSE_RADIUS_MIASMA : ARPG_CURSE_RADIUS; }
static int zone_frames(void) { return arpg_tree_has(7) ? ARPG_CURSE_FRAMES_MIASMA : ARPG_CURSE_FRAMES; }

// Ground metric: a point is inside a circle of ground radius r around (cx, cy).
static int ground_inside(int dx, int dy, int r) {
    return dx * dx + GROUND_DY2(dy) <= r * r;
}

// Height of the arc above the ground at flight frame f: a line from chest height down to the floor plus a parabola.
static int arc_height(int f) {
    const int F = ARPG_CURSE_FLIGHT;
    const int rem = F - f;
    return (CURSE_CHEST_H * rem) / F + (4 * CURSE_ARC_H * f * rem) / (F * F);
}

void curse_reset(void) {
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        s_shots[i].active = 0;
        s_zones[i].active = 0;
    }
    s_aiming = 0;
}

void curse_cancel_aim(void) { s_aiming = 0; }

void curse_shift_y(int dy_px) {
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        if (s_shots[i].active) {
            s_shots[i].y += TO_FIXED(dy_px);
            s_shots[i].ty += dy_px;
        }
        if (s_zones[i].active) s_zones[i].cy += dy_px;
    }
    if (s_aiming) s_aim_y += dy_px;
}

int curse_input(PlayerState *player, int touch_down, int touch_pressed, int touch_x, int touch_y, fixed hero_x, fixed hero_y) {
    (void)touch_pressed;
    const int hx = TO_INT(hero_x), hy = TO_INT(hero_y);

    if (touch_down) {
        // Target = the touched world point, clamped to ARPG_CURSE_RANGE from the hero (ground metric).
        int dx = touch_x - hx, dy = touch_y - hy;
        const int d2 = dx * dx + GROUND_DY2(dy);
        const int r2 = ARPG_CURSE_RANGE * ARPG_CURSE_RANGE;
        if (d2 > r2) {
            const int d = (int)sqrt32(d2);
            if (d > 0) {
                dx = dx * ARPG_CURSE_RANGE / d;
                dy = dy * ARPG_CURSE_RANGE / d;
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
    if (player->mana < ARPG_CURSE_COST || curse_count() >= ARPG_CURSE_MAX) return 0;
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        if (s_shots[i].active) continue;
        player->mana -= ARPG_CURSE_COST;
        const int F = ARPG_CURSE_FLIGHT;
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

void curse_update(Enemy *enemies, int max_enemies) {
    // Flight: a projectile that reaches its frame lands as a zone.
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        CurseShot *s = &s_shots[i];
        if (!s->active) continue;
        s->x += s->step_x;
        s->y += s->step_y;
        if (++s->frame < ARPG_CURSE_FLIGHT) continue;
        s->active = 0;
        for (int z = 0; z < ARPG_CURSE_MAX; z++) {
            if (s_zones[z].active) continue;
            s_zones[z].active = 1;
            s_zones[z].cx = s->tx;
            s_zones[z].cy = s->ty;
            s_zones[z].radius = zone_radius();
            s_zones[z].frames_left = zone_frames();
            s_zones[z].arm_frames = ARPG_CURSE_ARM_FRAMES;   // 0,5 s dibujado, mas tenue, antes de actuar
            s_zones[z].tick_timer = 0;                       // the first burn lands on the next update
            s_zones[z].phase = 0;
            break;
        }
    }

    // Glifo: while arming it only shows (darker, see render_floor). Once armed it slows the living enemies
    // inside. The burn is no longer base: only the tree node gives it (DESIGN.md 7.3).
    const int burns = arpg_tree_has(4) || arpg_tree_has(5) || arpg_tree_has(6);
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        CurseZone *z = &s_zones[i];
        if (!z->active) continue;
        if (z->arm_frames > 0) {
            if (--z->arm_frames == 0) sfx_play(SND_GLIFO_ACTIVATE, z->cx);
            z->phase++;
            continue;
        }
        if (burns && z->tick_timer <= 0) {
            for (int e = 0; e < max_enemies; e++) {
                Enemy *en = &enemies[e];
                if (g_enemy_ally[e] || !en->active || en->hp <= 0) continue;
                if (ground_inside(TO_INT(en->x) - z->cx, TO_INT(en->y) - z->cy, z->radius))
                    burn_apply(en, 1);
            }
            z->tick_timer = ARPG_CURSE_TICK;
        }
        if (z->tick_timer > 0) z->tick_timer--;
        z->phase++;
        if (--z->frames_left <= 0) z->active = 0;
    }
}

int curse_point_in_zone(int x, int y) {
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        const CurseZone *z = &s_zones[i];
        if (z->active && ground_inside(x - z->cx, y - z->cy, z->radius)) return 1;
    }
    return 0;
}

// % of speed a living glifo removes from a point (0 = outside or still arming).
int curse_slow_percent_at(int x, int y) {
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        const CurseZone *z = &s_zones[i];
        if (z->active && z->arm_frames <= 0 && ground_inside(x - z->cx, y - z->cy, z->radius))
            return ARPG_CURSE_SLOW_PCT;
    }
    return 0;
}

void curse_render_floor(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    GroundTarget g = { buffer, cam_x, cam_y };
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        const CurseZone *z = &s_zones[i];
        if (!z->active) continue;
        if (z->arm_frames > 0) {
            // Waiting to act: the same drawing, darker and without the hatched fill churn (DESIGN.md 7.3).
            gfx_ground_disc(&g, z->cx, z->cy, z->radius, CURSE_FILL_DIM, GFX_FILL_HATCH, z->phase >> 4);
            gfx_ground_ring(&g, z->cx, z->cy, z->radius, CURSE_RING_DIM, CURSE_RING_DASH);
            continue;
        }
        gfx_ground_disc(&g, z->cx, z->cy, z->radius, CURSE_FILL, GFX_FILL_HATCH, z->phase >> 3);
        // The last seconds: the edge blinks (off for 8 frames, on for 8 frames).
        if (z->frames_left > CURSE_BLINK_FRAMES || ((z->frames_left >> 3) & 1))
            gfx_ground_ring(&g, z->cx, z->cy, z->radius, CURSE_RING, CURSE_RING_DASH);
    }
    if (s_aiming) gfx_ground_ring(&g, s_aim_x, s_aim_y, CURSE_AIM_RING, CURSE_AIM, 0);
}

void curse_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    for (int i = 0; i < ARPG_CURSE_MAX; i++) {
        const CurseShot *s = &s_shots[i];
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
                const uint16_t p = g_ph_maldicion[row * PH_MALDICION_W + col];
                if (p == 0 || x < 0 || x >= SCREEN_W) continue;
                buffer[y * SCREEN_W + x] = p | BIT(15);
            }
        }
    }
}
