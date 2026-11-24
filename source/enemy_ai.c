#include "campanero_sprite.h"
#include "enemy_ai.h"
#include "lab_tuning.h"
#include "sound_test.h"
#include "horde.h"
#include "enemy_laser.h"
#include "groundfx.h"
#include "los.h"
#include "collision.h"
#include "navfield.h"
#include "player_sprite.h"
#include "chars_pool.h"
#include "sandbox.h"
#include "arpg.h"
#include "dmg_numbers.h"
#include "allies.h"
#include "glifo.h"
#include "sfx.h"
#include "campanero_fx.h"
#include "cfxprof.h"
#if ENCOUNTERS_PROTO
#include "boss.h"
#include "encounters_act1.h"
#endif
#if ENCOUNTERS_PROTO
#include "weapons.h"
#endif
#include <nds.h>
#include <string.h>

static uint32_t s_ai_tick = 0;
static int s_strip_mode;

void enemy_ai_set_strip_mode(int enabled) { s_strip_mode = enabled != 0; }

// Hardware divider and square root of the ARM9 (the C operators / and the old bit loop are software routines).
static inline uint32_t int_sqrt(uint32_t n) { return (uint32_t)sqrt32((int)n); }

// Level of detail: enemies outside the two screens (plus a margin) think every 2nd frame and move twice as far.
static int s_view_valid = 0;
static int s_view_l, s_view_t, s_view_r, s_view_b;   // world px, margin included
static int s_offscreen = 0;                          // this enemy is outside the window (any state)
static int s_lod_mult = 1;                           // 2 on the frame an off-screen enemy runs its AI

void enemy_ai_set_view(int cam_x, int cam_top_y, int cam_bottom_y) {
    s_view_valid = 1;
    s_view_l = cam_x - ENEMY_AI_VIEW_MARGIN;
    s_view_r = cam_x + 256 + ENEMY_AI_VIEW_MARGIN;
    s_view_t = cam_top_y - ENEMY_AI_VIEW_MARGIN;
    s_view_b = cam_bottom_y + ENEMY_AI_VIEW_MARGIN;
}

static inline int dir_from_vector(fixed dx, fixed dy) {
    int sdx = TO_INT(dx);
    int sdy = TO_INT(dy);
    int ax = sdx < 0 ? -sdx : sdx;
    int ay = sdy < 0 ? -sdy : sdy;
    if (ax * 2 < ay) sdx = 0;
    else if (ay * 2 < ax) sdy = 0;
    else {
        sdx = sdx < 0 ? -1 : 1;
        sdy = sdy < 0 ? -1 : 1;
    }
    if (sdx == 0) return sdy >= 0 ? DIR_SOUTH : DIR_NORTH;
    if (sdy == 0) return sdx < 0 ? DIR_WEST : DIR_EAST;
    if (sdx < 0) return sdy > 0 ? DIR_SOUTHWEST : DIR_NORTHWEST;
    return sdy < 0 ? DIR_NORTHEAST : DIR_SOUTHEAST;
}

int enemy_dir_from_vector(fixed dx, fixed dy) { return dir_from_vector(dx, dy); }

ITCM_CODE static int move_with_slide(fixed *x, fixed *y, fixed vx, fixed vy) {
    if (vx == 0 && vy == 0) return 0;

    fixed next_x = *x;
    fixed next_y = *y;
    if (sweep_position(&next_x, &next_y, vx, vy)) {
        *x = next_x;
        *y = next_y;
        return 1;
    }

    // Slide along X
    next_x = *x;
    next_y = *y;
    if (vx != 0 && sweep_position(&next_x, &next_y, vx, 0)) {
        *x = next_x;
        return 1;
    }

    // Slide along Y
    next_x = *x;
    next_y = *y;
    if (vy != 0 && sweep_position(&next_x, &next_y, 0, vy)) {
        *y = next_y;
        return 1;
    }

    return 0;
}

// Separation: a uniform grid of SEP_CELL_PX cells (>= the 16 px radius) rebuilt once per frame, so an enemy only
// looks at the 3x3 cells around it. Cells wrap (hash) and every candidate is re-checked with its real distance.
#define SEP_CELL_SHIFT 4
#define SEP_GRID_BITS 5
#define SEP_GRID_DIM (1 << SEP_GRID_BITS)
#define SEP_NONE 0xFF
static uint8_t s_grid_head[SEP_GRID_DIM * SEP_GRID_DIM];
static uint8_t s_grid_next[MAX_GAMEPLAY_ENEMIES];
static uint16_t s_sep_scale[256];                    // 8.8 of 128 / sqrt(d2) for d2 in 1..255 (0.5 px/frame impulse)
static int s_sep_ready = 0;

static inline int sep_cell(int cx, int cy) {
    return ((cy & (SEP_GRID_DIM - 1)) << SEP_GRID_BITS) | (cx & (SEP_GRID_DIM - 1));
}

static void sep_init_table(void) {
    for (int d2 = 1; d2 < 256; d2++) {
        uint32_t d16 = int_sqrt((uint32_t)d2 << 8);   // 16 * sqrt(d2)
        s_sep_scale[d2] = (uint16_t)div32(524288, (int32_t)d16);
    }
    s_sep_ready = 1;
}

ITCM_CODE static void sep_build_grid(const Enemy *enemies, int num_enemies) {
    memset(s_grid_head, SEP_NONE, sizeof(s_grid_head));
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
    for (int i = 0; i < num_enemies; i++) {
        if (!enemies[i].active || enemies[i].state == ENEMY_STATE_SUSPENDED) continue;   // a suspended victim does not push
        int c = sep_cell(TO_INT(enemies[i].x) >> SEP_CELL_SHIFT, TO_INT(enemies[i].y) >> SEP_CELL_SHIFT);
        s_grid_next[i] = s_grid_head[c];
        s_grid_head[c] = (uint8_t)i;
    }
}

static int s_sep_skip_guard;            // 1 while an Ojo repositions: it does not push against the garrison
ITCM_CODE static void apply_separation(Enemy *enemies, int num_enemies, int current_idx, fixed *vx, fixed *vy) {
    (void)num_enemies;
    Enemy *e = &enemies[current_idx];
    int cx = TO_INT(e->x) >> SEP_CELL_SHIFT;
    int cy = TO_INT(e->y) >> SEP_CELL_SHIFT;
    int32_t rep_vx = 0;
    int32_t rep_vy = 0;

    for (int gy = cy - 1; gy <= cy + 1; gy++) {
        for (int gx = cx - 1; gx <= cx + 1; gx++) {
            for (int j = s_grid_head[sep_cell(gx, gy)]; j != SEP_NONE; j = s_grid_next[j]) {
                if (j == current_idx || !enemies[j].active) continue;
                if (s_sep_skip_guard && (enemies[j].home_flags & ENEMY_HOME_GUARD)) continue;
                int32_t edx = TO_INT(e->x - enemies[j].x);
                int32_t edy = TO_INT(e->y - enemies[j].y);
                int32_t d2 = edx * edx + edy * edy;
                // Separation radius: 16 pixels (256 sq px)
                if (d2 > 0 && d2 < 256) {
                    int32_t k = s_sep_scale[d2];
                    rep_vx += (edx * k) / 256;      // constant divisor: shifts
                    rep_vy += (edy * k) / 256;
                }
            }
        }
    }

    *vx = (*vx + (fixed)rep_vx) * s_lod_mult;
    *vy = (*vy + (fixed)rep_vy) * s_lod_mult;
}

static void update_animation(Enemy *e, int moved) {
    int anim_period = g_characters[e->char_id].anim_period;
    if (anim_period <= 0) anim_period = 4;

    if (moved) {
        e->anim_timer++;
        if (e->anim_timer >= anim_period) {
            e->anim_timer = 0;
            e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES;
        }
    } else {
        e->anim_timer = 0;
        e->frame = 0;
    }
}

// Super Monja haste: while one prays, the Exvoto family inside her radius walks ARPG_MONJA_HASTE_PCT % faster.
// Rebuilt every frame in enemy_ai_update (haste_refresh); attacks and cooldowns are not touched. No visual yet
// (pending a design decision, DESIGN-ARPG).
// Also the speed of the Exvotos possessed by a Súper Monja (possession_update).
static uint8_t s_haste[MAX_GAMEPLAY_ENEMIES];
static const Enemy *s_haste_base;
static inline fixed haste_speed(const Enemy *e, fixed speed) {
    int i = (int)(e - s_haste_base);
    if (i >= 0 && i < MAX_GAMEPLAY_ENEMIES && s_haste[i]) return speed + (speed * ARPG_MONJA_HASTE_PCT) / 100;
    return speed;
}

#define VIEW_DIRECT 4                 // e->has_los bits: close, in view and walkable: run straight at the player
#define VIEW_ENGAGE 8                 //                  charger: within CHARGER_ENGAGE_DIST, in view and walkable
#define VIEW_SIGHT 16                 //                  Ojo: line of sight (walls and columns cut it) within OJO_SIGHT_RANGE

#define CHASE_DIRECT_RANGE 48         // ground px: closer than this (with a clear view) it runs straight at the player

// Unit direction (8.8, ground metric) from (ox, oy) to (tx, ty), same convention as the player's
// weapons: dir_x^2 + (2 dir_y)^2 = 256^2. Returns 0 (leaving *dx, *dy) when both points coincide.
static int aim_vector(int ox, int oy, int tx, int ty, int *dx, int *dy) {
    int ax = tx - ox;
    int ay = ty - oy;
    int len = (int)int_sqrt((uint32_t)(ax * ax + GROUND_DY2(ay)));
    if (len < 1) return 0;
    *dx = div32(ax * 256, len);
    *dy = div32(ay * 256, len);
    return 1;
}

// Walks toward the player: straight when close with a clear walkable line (cached in VIEW_DIRECT),
// otherwise down the distance field (it walks around walls); with no field value, straight.
// Shared by the skeleton and the charger's approach.
#if ENCOUNTERS_PROTO
static int s_chase_bias_x, s_chase_bias_y;    // v2: lateral offset of the walking target (world px), set by the Exvoto and cleared here
#endif
static void chase_step(Enemy *e, Enemy *enemies, int num_enemies, int idx, fixed speed,
                       int wx, int wy, int px, int py, int ground_dist_sq) {
    speed = burn_slow(e, haste_speed(e, speed));   // Quemado frena (DESIGN.md 6.12.2); Super Monja acelera
    int target_x = px, target_y = py;
    int direct = (e->has_los & VIEW_DIRECT) && ground_dist_sq <= CHASE_DIRECT_RANGE * CHASE_DIRECT_RANGE;
    if (!direct) {
        int step_x, step_y;
        if (nav_next_step(wx, wy, &step_x, &step_y)) {
            target_x = step_x;
            target_y = step_y;
        }
    }

#if ENCOUNTERS_PROTO
    target_x += s_chase_bias_x;
    target_y += s_chase_bias_y;
    s_chase_bias_x = s_chase_bias_y = 0;
#endif
    int t_dx = target_x - wx;
    int t_dy = target_y - wy;
    uint32_t t_dist = int_sqrt((uint32_t)(t_dx * t_dx + GROUND_DY2(t_dy)));
    fixed vx = 0, vy = 0;
    if (t_dist > 0) {
        vx = (fixed)div32(t_dx * (int32_t)speed, (int32_t)t_dist);
        vy = (fixed)div32(t_dy * (int32_t)speed, (int32_t)t_dist);
    }

    apply_separation(enemies, num_enemies, idx, &vx, &vy);
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    e->dir = dir_from_vector(TO_FIXED(t_dx), TO_FIXED(t_dy));   // velocity is sub-pixel: use the step vector
    update_animation(e, moved);
}

// Cached for a few frames: line of sight plus a walkable line for the body, within engage_dist.
static void refresh_view(Enemy *e, int idx, int wx, int wy, int px, int py, int ground_dist_sq, int engage_dist) {
    if (((s_ai_tick + idx) & 3) != 0) return;

    int clear = 0;
    if (ground_dist_sq <= engage_dist * engage_dist)
        clear = los_has_line_of_sight(wx, wy, px, py, 0) && line_is_walkable(wx, wy, px, py);
    e->has_los = 0;
    if (clear && ground_dist_sq <= CHASE_DIRECT_RANGE * CHASE_DIRECT_RANGE) e->has_los |= VIEW_DIRECT;
    if (clear) e->has_los |= VIEW_ENGAGE;
}

// ---- Exvoto & Monaguillo praying / emerging / melee (DESIGN.md 6.10) -------------------------------------
// The pose of a praying Exvoto is a character slot of its own (player_sprite.h): the enemy swaps char_id.

// Pose slot and first frame of a praying Exvoto: on its feet or on its knees.
void enemy_exvoto_start_praying(Enemy *e, int kneel, int dir) {
    e->state = ENEMY_STATE_PRAY;
    e->kneel = kneel != 0;
    e->char_id = exvoto_pose_char(e->type, e->kneel ? EXVOTO_POSE_PRAY_KNEEL : EXVOTO_POSE_PRAY_STAND);
    e->dir = dir;
    e->frame = 0;
    e->anim_timer = 0;
    e->state_timer = 0;
}

// Slot of the moving pose once an Exvoto-family enemy is up: the Exvoto walk, or the Párroco's own run sheet.
static inline int exvoto_up_char(const Enemy *e) {
    return (e->type == ENEMY_TYPE_PARROCO || e->type == ENEMY_TYPE_MONJA) ? enemy_type_char_id(e->type) : CHAR_EXVOTO;
}

// Wakes one praying Exvoto: the kneeling ones rise first (still), the standing ones walk at once.
static void exvoto_wake_one(Enemy *e) {
    e->home_flags &= (uint8_t)~ENEMY_HOME_GUARD;       // a nun of the chapel stops being a praying post
    e->anim_timer = 0;
    e->frame = 0;
    if (e->kneel) {
        e->state = ENEMY_STATE_RISE;
        e->state_timer = EXVOTO_RISE_FRAMES;
        e->char_id = exvoto_pose_char(e->type, EXVOTO_POSE_STAND_UP);
    } else {
        e->state = ENEMY_STATE_CHASE;
        e->char_id = exvoto_up_char(e);
    }
}

// Wakes enemies[idx] and, in chain, every praying Exvoto within EXVOTO_CHAIN_WAKE_RADIUS (ground metric)
// of one that has just woken, so a procession starts at once. Runs only on a wake event; the work list
// is bounded by the pool.
static void exvoto_wake_chain(Enemy *enemies, int num_enemies, int idx) {
    uint8_t queue[MAX_GAMEPLAY_ENEMIES];
    int head = 0, tail = 0;
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
    exvoto_wake_one(&enemies[idx]);
    queue[tail++] = (uint8_t)idx;
    while (head < tail) {
        const Enemy *w = &enemies[queue[head++]];
        for (int j = 0; j < num_enemies; j++) {
            Enemy *p = &enemies[j];
            if (!p->active || p->type != ENEMY_TYPE_EXVOTO || p->state != ENEMY_STATE_PRAY) continue;
            int dx = TO_INT(p->x - w->x);
            int dy = TO_INT(p->y - w->y);
            if (dx * dx + GROUND_DY2(dy) <= EXVOTO_CHAIN_WAKE_RADIUS * EXVOTO_CHAIN_WAKE_RADIUS) {
                exvoto_wake_one(p);
                queue[tail++] = (uint8_t)j;       // each Exvoto is queued once: it leaves PRAY when woken
            }
        }
    }
}

// Exvoto & Monaguillo (DESIGN.md 6.10): relentless melee pressure, no telegraph.
// Exvoto: PRAY -> (RISE) -> CHASE <-> ATTACK; * -> DEAD.
// Monaguillo: EMERGE (~0.5 s, invulnerable, still) -> CHASE <-> ATTACK; * -> DEAD.
#if ENCOUNTERS_PROTO
// ---- v2: the Exvoto dodges the hero's ray and does not walk straight (DESIGN.md 6.13.6) ----------------------
// While the hero charges the ray the aiming line is a straight line from his muzzle. An awake Exvoto within
// EXVOTO_DODGE_HALF px of it (ground), ahead of the hero and farther than EXVOTO_DODGE_MIN_DIST from him, reacts after
// EXVOTO_DODGE_REACT frames and steps sideways for EXVOTO_DODGE_STEP frames, to its own side of the line (sign of the
// cross product), so a row opens one to each side. Then EXVOTO_DODGE_COOL frames before it can dodge again.
// One dot and one cross product per Exvoto and frame, in fixed point, only while charging. State lives in fields
// the Exvoto does not use: aim_px (reaction timer), aim_py (step timer), beam_mx (cooldown), beam_my (side).
#define EXVOTO_DODGE_HALF 14
#define EXVOTO_DODGE_MIN_DIST 24
#define EXVOTO_DODGE_REACT 12
#define EXVOTO_DODGE_STEP 20
#define EXVOTO_DODGE_COOL 45
#define EXVOTO_DODGE_SPEED_NUM 5      // the sidestep runs at 5/2 of the walking speed
#define EX_REACT(e) ((e)->aim_px)
#define EX_STEP(e) ((e)->aim_py)
#define EX_COOL(e) ((e)->beam_mx)
#define EX_SIDE(e) ((e)->beam_my)

// Returns 1 when the Exvoto spent the frame dodging (it does not also walk or bite).
static int exvoto_dodge(Enemy *e, int wx, int wy, int ground_dist_sq, fixed speed) {
    if (EX_COOL(e) > 0) EX_COOL(e)--;
    int mx = 0, my = 0, gx = 0, gy = 0;
    const int line = weapons_aim_line(&mx, &my, &gx, &gy);
    int rx = wx - mx, ry = 2 * (wy - my);
    int along = (rx * gx + ry * gy) >> 8;
    int cross = (rx * gy - ry * gx) >> 8;
    if (EX_STEP(e) > 0) {
        // The hero fired or let go of the aim: drop the sidestep at once and resume the chase this same frame.
        if (!line) {
            EX_STEP(e) = 0;
            EX_COOL(e) = EXVOTO_DODGE_COOL;
            return 0;
        }
        // Sidestep: perpendicular to the line, towards the Exvoto's own side.
        int s = EX_SIDE(e);
        int sp = haste_speed(e, speed) * EXVOTO_DODGE_SPEED_NUM / 2;
        fixed vx = (fixed)((gy * s * sp) >> 8);
        fixed vy = (fixed)((-gx * s * sp) >> 9);   // ground y -> world y
        int moved = move_with_slide(&e->x, &e->y, vx, vy);
        e->dir = dir_from_vector(vx, vy * 2);
        update_animation(e, moved);
        if (--EX_STEP(e) <= 0) EX_COOL(e) = EXVOTO_DODGE_COOL;
        return 1;
    }
    int threatened = line && along > 0 && cross < EXVOTO_DODGE_HALF && cross > -EXVOTO_DODGE_HALF &&
                     ground_dist_sq >= EXVOTO_DODGE_MIN_DIST * EXVOTO_DODGE_MIN_DIST && EX_COOL(e) <= 0;
    if (!threatened) {
        EX_REACT(e) = 0;
        return 0;
    }
    if (EX_REACT(e) == 0) {
        EX_REACT(e) = EXVOTO_DODGE_REACT;
        EX_SIDE(e) = cross > 0 ? 1 : cross < 0 ? -1 : (e->strafe_dir >= 0 ? 1 : -1);
    }
    if (--EX_REACT(e) <= 0) {
        EX_REACT(e) = 0;
        EX_STEP(e) = EXVOTO_DODGE_STEP;
    }
    return 0;
}

// Each Exvoto walks with a slow lateral weave of its own (a triangle wave with a phase per enemy), so a column of them
// does not arrive in a straight line. Fades to nothing close to the hero.
static void exvoto_weave(const Enemy *e, int idx, int dx, int dy) {
    int dy2 = 2 * dy;
    int m = dx < 0 ? -dx : dx;
    int a = dy2 < 0 ? -dy2 : dy2;
    if (a > m) m = a;
    if (m <= 32) return;                              // within ~32 ground px: straight at the hero
    int ph = (int)((s_ai_tick * 2 + (uint32_t)idx * 77u) & 255u);
    int tri = (ph < 128 ? ph : 256 - ph) - 64;         // -64..64
    int amp = (e->strafe_dir >= 0 ? 1 : -1) * tri;     // the strafe sign gives each Exvoto its own phase direction
    int fade = m >= 96 ? 64 : m - 32;                  // 0 at 32 px, 64 (=100 % in /64) from 96 px out
    int off = div32(amp * 24 * fade, 4096);            // up to +-24 px, eased out as the Exvoto closes in
    s_chase_bias_x = div32(-dy2 * off, m);
    s_chase_bias_y = div32(dx * off, m) / 2;
}
#endif

// Bodyguard (DESIGN-ARPG s5, Monaguillo and Parroco): while the hero charges the Ray, the guard runs to the point of the
// line hero -> nearest ally (the Súper Monja first, else the ally nearest the hero; never the Bebé or another guard) that is ARPG_GUARD_DIST ground px from the hero, and waits there
// facing him. Returns 1 when it spent the frame on that (no walk, no bite); 0 when there is nothing to guard.
static int bodyguard_step(Enemy *e, Enemy *enemies, int num_enemies, int idx, int px, int py, fixed speed) {
    if (!weapons_aim_charging()) return 0;
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
    int best = -1, best_d = 0, best_monja = 0;
    for (int j = 0; j < num_enemies; j++) {
        const Enemy *o = &enemies[j];
        if (j == idx || !o->active || o->hp <= 0 || g_enemy_ally[j]) continue;
        if (o->type == ENEMY_TYPE_PARROCO || o->type == ENEMY_TYPE_MONAGUILLO) continue;      // other bodyguards are not guarded
        if (o->type == ENEMY_TYPE_BEBE) continue;      // the Bebé is filler, not worth guarding
        if (o->state == ENEMY_STATE_DORMANT || o->state == ENEMY_STATE_DEAD || o->state == ENEMY_STATE_EMERGE) continue;
        const int ox = TO_INT(o->x) - px, oy = TO_INT(o->y) - py;
        const int d = ox * ox + GROUND_DY2(oy);
        const int mj = o->type == ENEMY_TYPE_MONJA;
        if (best < 0 || (mj && !best_monja) || (mj == best_monja && d < best_d)) { best = j; best_d = d; best_monja = mj; }
    }
    if (best < 0) return 0;
    const int tx = TO_INT(enemies[best].x) - px, ty = TO_INT(enemies[best].y) - py;
    const int len = (int)int_sqrt((uint32_t)best_d);
    if (len < 2 * 8) return 0;
    int gd = len / 2 < ARPG_GUARD_DIST ? len / 2 : ARPG_GUARD_DIST;
    const int gx = px + div32(tx * gd, len), gy = py + div32(ty * gd, len);     // the guard post on the line
    const int wx = TO_INT(e->x), wy = TO_INT(e->y);
    const int ex = gx - wx, ey = gy - wy;
    const int d2 = ex * ex + GROUND_DY2(ey);
    e->dir = dir_from_vector(TO_FIXED(px) - e->x, TO_FIXED(py) - e->y);
    if (d2 <= 3 * 3) { update_animation(e, 0); return 1; }
    int ux, uy;
    if (!aim_vector(wx, wy, gx, gy, &ux, &uy)) { update_animation(e, 0); return 1; }
    const int sp = (int)burn_slow(e, haste_speed(e, speed)) * ARPG_GUARD_SPEED_X;
    fixed vx = (fixed)((ux * sp) >> 8);
    fixed vy = (fixed)((uy * sp) >> 8);
    if (d2 < 256 && vx * vx + 4 * vy * vy > d2 * 65536) { vx = TO_FIXED(ex); vy = TO_FIXED(ey); }                   // do not overshoot the post
    const int moved = move_with_slide(&e->x, &e->y, vx, vy);
    e->dir = dir_from_vector(vx, vy * 2);
    update_animation(e, moved);
    return 1;
}

#if ENCOUNTERS_PROTO
// Monja de cera praying at her post (ENEMY_HOME_GUARD + PRAY, Capilla del parroco): once a second she heals ARPG_EXVOTO_HEAL_PCT %
// of the life of the Exvoto family within ARPG_EXVOTO_HEAL_RADIUS ground px (green numbers, like the Monja's heal).
static void exvoto_pray_heal(Enemy *e, Enemy *enemies, int num_enemies, int idx) {
    if (++e->state_timer % ARPG_MONJA_HEAL_PERIOD != (idx % ARPG_MONJA_HEAL_PERIOD)) return;
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
    int healed_any = 0;
    for (int j = 0; j < num_enemies; j++) {
        Enemy *o = &enemies[j];
        if (j == idx || !o->active || o->hp <= 0 || o->hp >= o->max_hp || g_enemy_ally[j]) continue;
        if (o->type != ENEMY_TYPE_BEBE && o->type != ENEMY_TYPE_EXVOTO && o->type != ENEMY_TYPE_PARROCO &&
            o->type != ENEMY_TYPE_MONAGUILLO) continue;
        int dx = TO_INT(o->x - e->x);
        int dy = TO_INT(o->y - e->y);
        if (dx * dx + GROUND_DY2(dy) > ARPG_EXVOTO_HEAL_RADIUS * ARPG_EXVOTO_HEAL_RADIUS) continue;
        int heal = o->max_hp * ARPG_EXVOTO_HEAL_PCT / 100;
        if (heal < 1) heal = 1;
        o->hp += heal;
        if (o->hp > o->max_hp) o->hp = o->max_hp;
        dmg_numbers_spawn(o->x, o->y - TO_FIXED(16), heal, DMG_NUM_HEAL);
        healed_any = 1;
    }
    if (healed_any) sfx_play(SND_MONJA_HEAL, TO_INT(e->x));
}
#endif

static void update_exvoto(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                          fixed player_x, fixed player_y, const EnemyTuning *tuning) {
    if (e->type == ENEMY_TYPE_PARROCO && e->gesture > 0) e->gesture--;      // wax-white flash timer (set when the Ray breaks on it)
    if (e->state == ENEMY_STATE_EMERGE) {
        e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
        if (--e->state_timer <= 0) {
            e->state = ENEMY_STATE_CHASE;
            e->state_timer = 0;
        }
        return;
    }

    if (g_player_state.is_dead) {
        update_animation(e, 0);
        return;
    }

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);
    int dx = px - wx;
    int dy = py - wy;
    int ground_dist_sq = dx * dx + GROUND_DY2(dy);

    switch (e->state) {
        case ENEMY_STATE_PRAY: {
#if ENCOUNTERS_PROTO
            if (e->home_flags & ENEMY_HOME_GUARD) {
                // Praying nun of the chapel: a hit does not wake her, only the hero on top of her (a stagger from a hit neither).
                if (ground_dist_sq <= EXVOTO_CHAIN_WAKE_RADIUS * EXVOTO_CHAIN_WAKE_RADIUS) {
                    exvoto_wake_chain(enemies, num_enemies, idx);
                    break;
                }
                exvoto_pray_heal(e, enemies, num_enemies, idx);
                int period = g_characters[e->char_id].anim_period;
                if (++e->anim_timer >= period) {
                    e->anim_timer = 0;
                    e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES;
                }
                break;
            }
#endif
            if (ground_dist_sq <= EXVOTO_WAKE_RADIUS * EXVOTO_WAKE_RADIUS || e->hit_timer > 0) {
                exvoto_wake_chain(enemies, num_enemies, idx);
                break;
            }
            // Loop of the pose clip, no movement.
            int anim_period = g_characters[e->char_id].anim_period;
            if (++e->anim_timer >= anim_period) {
                e->anim_timer = 0;
                e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_WOBBLE:
            // Reeling after a hit that did not kill: still, no dodge, no bite; glows (main.c). Recovers wounded.
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHASE;
                e->state_timer = 0;
            }
            break;

        case ENEMY_STATE_RISE: {
            // stand_up clip: 8 frames over EXVOTO_RISE_FRAMES, still. Ends on the first walk frame.
            int anim_period = g_characters[e->char_id].anim_period;
            if (++e->anim_timer >= anim_period) {
                e->anim_timer = 0;
                if (e->frame < PLAYER_NUM_FRAMES - 1) e->frame++;
            }
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHASE;
                e->char_id = exvoto_up_char(e);
                e->frame = 0;
                e->anim_timer = 0;
            }
            break;
        }

        case ENEMY_STATE_ATTACK: {
            if ((e->type == ENEMY_TYPE_PARROCO || e->type == ENEMY_TYPE_MONAGUILLO) && weapons_aim_charging()) {
                e->state = ENEMY_STATE_CHASE;      // a guard leaves the bite cooldown to cover the hero's Ray charge
                if (bodyguard_step(e, enemies, num_enemies, idx, px, py, tuning->speed)) break;
            }
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            if (--e->state_timer <= 0) e->state = ENEMY_STATE_CHASE;
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;

            // Hit-stun: brief stagger while hit_timer > 0; no bite, advance or dodge this frame.
            if (e->hit_timer > 0) {
                update_animation(e, 0);
                break;
            }

            // Bodyguards (Monaguillo, Párroco): while the hero charges the Ray they run to stand in the line of fire (before the bite: covering beats biting).
            if ((e->type == ENEMY_TYPE_PARROCO || e->type == ENEMY_TYPE_MONAGUILLO) &&
                bodyguard_step(e, enemies, num_enemies, idx, px, py, tuning->speed)) break;

            // Bite when in melee range and nothing solid is in between.
            int melee_range = tuning->preferred_dist_max;
            if (ground_dist_sq <= melee_range * melee_range &&
                los_has_line_of_sight(wx, wy, px, py, 0) && line_is_walkable(wx, wy, px, py)) {
                player_take_damage(&g_player_state, arpg_enemy_damage_of(e));
                e->state = ENEMY_STATE_ATTACK;
                e->state_timer = tuning->attack_cooldown;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                update_animation(e, 0);
                break;
            }

            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, CHASE_DIRECT_RANGE);
#if ENCOUNTERS_PROTO
            if (e->type == ENEMY_TYPE_EXVOTO || e->type == ENEMY_TYPE_PARROCO) {
                if (e->type == ENEMY_TYPE_EXVOTO && exvoto_dodge(e, wx, wy, ground_dist_sq, tuning->speed)) break;
                exvoto_weave(e, idx, dx, dy);
            }
#endif
            chase_step(e, enemies, num_enemies, idx, tuning->speed, wx, wy, px, py, ground_dist_sq);
            break;
        }
    }
}

// Charger (DESIGN.md 6.9.1): lunge and dodge. FSM CHASE (slow approach) -> TELEGRAPH (still, blinks,
// locks the direction) -> CHARGE (straight line) -> RECOVER (still, vulnerable) -> CHASE.
// A wall or column in the way of the charge, or a ray hit during TELEGRAPH / CHARGE, leaves it STUNNED.
static void update_charger(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                           fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_CHARGER];

    if (g_player_state.is_dead) {
        update_animation(e, 0);
        return;
    }

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);
    int dx = px - wx;
    int dy = py - wy;
    int ground_dist_sq = dx * dx + GROUND_DY2(dy);

    switch (e->state) {
        case ENEMY_STATE_WOBBLE:
            // Reeling after a hit that did not kill: still, glows (main.c). Recovers wounded.
            update_animation(e, 0);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHASE;
                e->state_timer = 0;
            }
            break;

        case ENEMY_STATE_TELEGRAPH: {
            // 3-stage progressive crouch (walk[0] -> telegraph -> charge[0]) without blinking.
            e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
            int elapsed = tuning->telegraph_duration - e->state_timer;
            e->frame = (elapsed < 10) ? 0 : (elapsed < 28) ? 1 : 2;
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHARGE;
                e->state_timer = CHARGER_CHARGE_FRAMES;
                e->charge_hit = 0;
                e->frame = 0;
                e->anim_timer = 0;
                sfx_play(SND_CIRENEO_CHARGE, TO_INT(e->x));
            }
            break;
        }

        case ENEMY_STATE_CHARGE: {
            fixed vx = (e->aim_dir_x * tuning->charge_speed) >> 8;
            fixed vy = (e->aim_dir_y * tuning->charge_speed) >> 8;
            e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
            if (!sweep_position(&e->x, &e->y, vx, vy)) {       // no sliding: a wall or column stops it dead
                e->state = ENEMY_STATE_STUNNED;
                e->state_timer = CHARGER_STUN_WALL_FRAMES;
                e->charge_hit = CHARGER_JAMMED;                // jam in three beats; the clip frame comes from the timer below
                e->frame = 0;
                e->anim_timer = 0;
                sfx_play(SND_CIRENEO_WALL, TO_INT(e->x));
                break;
            }
            // 4-frame charge clip at 4 ticks/frame (16 frames/stride -> ~40 px at charge_speed 650)
            if (++e->anim_timer >= 4) {
                e->anim_timer = 0;
                e->frame = (e->frame + 1) & 3;
            }
            if (!e->charge_hit) {
                int hx = TO_INT(player_x - e->x);
                int hy = TO_INT(player_y - e->y);
                if (hx * hx + GROUND_DY2(hy) <= CHARGER_HIT_RADIUS * CHARGER_HIT_RADIUS) {
                    player_take_damage(&g_player_state, arpg_enemy_damage_of(e));          // one hit per charge; i-frames may absorb it
                    e->charge_hit = 1;
                }
            }
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_RECOVER;
                e->state_timer = CHARGER_RECOVER_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_STUNNED:
            if (e->charge_hit == CHARGER_JAMMED) {
                // Wall jam: impact (frames 0-1), struggle (frames 2/3 alternating shake), release (5 pull, 6 back-step).
                // Still facing the wall; the whole jam is vulnerable and finishable (state stays STUNNED).
                e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
                int elapsed = CHARGER_STUN_WALL_FRAMES - e->state_timer;
                if (elapsed < CHARGER_JAM_IMPACT_FRAMES) {
                    e->frame = elapsed < 4 ? 0 : 1;
                } else if (e->state_timer > CHARGER_JAM_RELEASE_FRAMES) {
                    if (e->frame < 2 || e->frame > 3) { e->frame = 2; e->anim_timer = 0; }
                    if (++e->anim_timer >= CHARGER_JAM_STRUGGLE_TICKS) { e->anim_timer = 0; e->frame = e->frame == 3 ? 2 : 3; }
                } else if (e->state_timer > CHARGER_JAM_BACKSTEP_FRAMES) {
                    e->frame = 5;
                } else {
                    e->frame = 6;
                    sweep_position(&e->x, &e->y, -((e->aim_dir_x * CHARGER_JAM_BACKSTEP_SPEED) >> 8),
                                   -((e->aim_dir_y * CHARGER_JAM_BACKSTEP_SPEED) >> 8));
                }
                if (--e->state_timer <= 0) {
                    e->state = ENEMY_STATE_CHASE;
                    e->charge_hit = 0;
                    e->frame = 0;
                    e->anim_timer = 0;
                }
                break;
            }
            // fallthrough: stunned by a ray hit keeps the still frame
        case ENEMY_STATE_RECOVER: {
            update_animation(e, 0);
            if (--e->state_timer <= 0) e->state = ENEMY_STATE_CHASE;
            break;
        }

        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;
            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, CHARGER_ENGAGE_DIST);
#if ENCOUNTERS_PROTO
            // v2: it charges only when it has the hero lined up (heading within one 45-degree sector of him),
            // up to 160 px away, with a clear view. It also telegraphs point blank so the player can dodge.
            if ((e->has_los & VIEW_ENGAGE) && ground_dist_sq <= CHARGER_ENGAGE_DIST * CHARGER_ENGAGE_DIST &&
                ((dir_from_vector(player_x - e->x, player_y - e->y) - e->dir + 9) & 7) <= 2 &&
                aim_vector(wx, wy, px, py, &e->aim_dir_x, &e->aim_dir_y)) {
#else
            if ((e->has_los & VIEW_ENGAGE) && ground_dist_sq <= CHARGER_ENGAGE_DIST * CHARGER_ENGAGE_DIST &&
                aim_vector(wx, wy, px, py, &e->aim_dir_x, &e->aim_dir_y)) {
#endif
                e->state = ENEMY_STATE_TELEGRAPH;
                e->state_timer = tuning->telegraph_duration;
                e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
                e->charge_hit = 0;
                e->frame = 0;
                e->anim_timer = 0;
                break;
            }
            chase_step(e, enemies, num_enemies, idx, tuning->speed, wx, wy, px, py, ground_dist_sq);
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Ojo del Tribunal (DESIGN.md 6.10, "sentencia escrita en el suelo"), ENEMY_TYPE_SHOOTER. FSM
// CHASE (search) -> TRACK (40 frames: a crack on the ground grows from its feet to the hero and follows him)
// -> LOCK (20 frames: the crack freezes and extends to the first wall or column; a light runs along it opening
// each eye, the countdown) -> SENTENCE (the whole line bursts at once into spectral flames; the head opens its
// mouth and fires nothing; the damage is that strip of ground, from the feet to the wall) -> COOLDOWN (scar) -> CHASE.
// A wall or column cuts the sight and the line (los_has_line_of_sight / ojo_ray_wall_dist). The hero is safe by
// leaving the line before SENTENCE or hiding behind a column.
// ---------------------------------------------------------------------------

void enemy_muzzle(const Enemy *e, fixed *mx, fixed *my, int *mh) {
    int clip = ojo_clip(e);
    const int8_t *m = clip == CLIP_OJO_SENTENCE ? g_ojo_sentence_muzzle[e->dir][ojo_clip_frame(e, clip)]
                    : clip == CLIP_OJO_LOOK     ? g_ojo_look_muzzle[e->dir][ojo_clip_frame(e, clip)]
                                                : g_character_muzzle[e->char_id][e->dir][e->frame];
    int gx = m[0], gy = m[1], gh = m[2];
    *mx = e->x + TO_FIXED(gx);
    *my = e->y + TO_FIXED(gy);
    *mh = gh;
}

// Ojos that are tracking, locked or sentencing: they hold an aiming slot.
static int ojos_looking(const Enemy *enemies, int num_enemies) {
    int n = 0;
    for (int i = 0; i < num_enemies; i++) {
        const Enemy *o = &enemies[i];
        if (o->active && (o->state == ENEMY_STATE_TRACK || o->state == ENEMY_STATE_LOCK ||
                          o->state == ENEMY_STATE_SENTENCE))
            n++;
    }
    return n;
}

// Look loop (breathing) while it aims, instead of the walk frames.
static void ojo_look_anim(Enemy *e) {
    if (++e->anim_timer >= OJO_LOOK_PERIOD) {
        e->anim_timer = 0;
        e->frame = (e->frame + 1) & (OJO_LOOK_NUM_FRAMES - 1);
    }
}

// A crouched hero is covered when the line from the shooter to him crosses low cover (DESIGN.md 6.9). One rule for the damage
// (ojo_beam_hurts) and for the Ojo's decision to hold its fire (ojo_hero_covered), so it never spends a beam on a bench.
static int ojo_cover_shields(int ox, int oy, int px, int py) {
    return g_hero_crouched && line_crosses_low_cover(ox, oy, px, py);
}

// Would the sentence that the Ojo pronounces now be cancelled by low cover? The line starts at its feet (the crack on the floor).
static int ojo_hero_covered(Enemy *e, fixed player_x, fixed player_y) {
    if (!g_hero_crouched) return 0;
    return ojo_cover_shields(TO_INT(e->x), TO_INT(e->y), TO_INT(player_x), TO_INT(player_y));
}

// The damage line is a temporary wall: while the sentence hurts (impact + flare) a hero within OJO_HIT_HALF_WIDTH ground px of
// the crack, from the Ojo's feet to the first wall or column in the direction fixed in LOCK, takes a hit (player_take_hit's
// i-frames cap it at one). The same line is what enemy_laser.c paints. Once per frame per Ojo.
static void ojo_beam_hurts(const Enemy *e, fixed player_x, fixed player_y) {
    int rx = TO_INT(player_x) - e->beam_mx;
    int ry2 = 2 * (TO_INT(player_y) - e->beam_my);
    int along = (rx * e->beam_ux + ry2 * e->beam_uy) >> 8;
    int cross = (rx * e->beam_uy - ry2 * e->beam_ux) >> 8;
    if (cross < 0) cross = -cross;
    if (along >= 0 && along <= e->beam_len && cross <= OJO_HIT_HALF_WIDTH) {
        // Low cover (DESIGN.md 6.9): a crouched hero is safe when the line from the Ojo's feet to him crosses a bench or
        // sacks before reaching him. The crack is still drawn over the cover; only the hit is cancelled.
        if (ojo_cover_shields(e->beam_mx, e->beam_my, TO_INT(player_x), TO_INT(player_y))) return;
        player_take_damage(&g_player_state, arpg_enemy_damage_of(e));
    }
}

// Pronounces the sentence: the whole crack from the Ojo's feet along the ground line to the locked point (ground metric)
// and on to the first wall or column hurts the hero once if he is on it (player_take_hit respects the i-frames).
static void ojo_fire(Enemy *e, fixed player_x, fixed player_y) {
    const int wx = TO_INT(e->x), wy = TO_INT(e->y);
    // Screen direction of the line (kept for the bots that read aim_dir).
    int ax = e->aim_px - wx;
    int ay = e->aim_py - wy;
    int slen = (int)int_sqrt((uint32_t)(ax * ax + ay * ay));
    if (slen < 1) { ax = 1; ay = 0; slen = 1; }
    e->aim_dir_x = div32(ax * 256, slen);
    e->aim_dir_y = div32(ay * 256, slen);
    // Hit line: true ground metric from the feet to the locked point, extended to the first wall or column.
    int gx = e->aim_px - wx;
    int gy2 = 2 * (e->aim_py - wy);
    int glen = (int)int_sqrt((uint32_t)(gx * gx + gy2 * gy2));
    if (glen < 1) { gx = 1; gy2 = 0; glen = 1; }
    int ux = div32(gx * 256, glen);                  // unit vector 8.8
    int uy = div32(gy2 * 256, glen);
    e->beam_len = ojo_ray_wall_dist(wx, wy, ux << 7, uy << 7, OJO_BEAM_MAX_LEN);
    e->beam_mx = wx;
    e->beam_my = wy;
    e->beam_ux = ux;
    e->beam_uy = uy;
    ojo_beam_hurts(e, player_x, player_y);
}

// Advances the sentence gesture (SENTENCE and the start of COOLDOWN); 0 once it has played out.
static void ojo_gesture_tick(Enemy *e) {
    if (e->gesture <= 0) return;
    e->gesture++;
    if (e->gesture > OJO_GESTURE_FRAMES) e->gesture = e->state == ENEMY_STATE_SENTENCE ? OJO_GESTURE_FRAMES : 0;   // held while the beam lasts
}

// The Ojo's leash grows while it hunts: ojo_leash_q (units of OJO_LEASH_Q_PX) lives in the Exvoto's `kneel` byte, which an Ojo never uses.
#define ojo_leash_q(e) ((e)->kneel)
#define OJO_LEASH_Q_PX 8
#define OJO_LEASH_Q_MAX 96                // 768 px: the whole room
#define OJO_POST_LEASH 20                 // ground px an Ojo may leave its post while a Campanero lives
static int s_post_fixed;                  // 1 while a Campanero lives (set once per enemy_ai_update)
#define OJO_LEASH_Q_FRAMES 5              // one unit per 5 frames = 96 px per second without sight of the hero

// The hero is in the sights again: the leash returns to its base, but wide enough to keep the Ojo where it stands (it does not go back).
static void ojo_leash_settle(Enemy *e) {
    if (ojo_leash_q(e) == 0) return;
    const int lx = TO_INT(e->x) - *enemy_home_x(e);
    const int ly = TO_INT(e->y) - *enemy_home_y(e);
    const int d = (int)int_sqrt((uint32_t)(lx * lx + GROUND_DY2(ly)));
    int q = d > OJO_LEASH_DIST ? (d - OJO_LEASH_DIST + OJO_LEASH_Q_PX - 1) / OJO_LEASH_Q_PX : 0;
    const int dn = TO_INT(e->y) - *enemy_home_y(e) - OJO_LEASH_DOWN_PX;       // also keep the row it stands on
    if (dn > 0 && (dn * 2 + OJO_LEASH_Q_PX - 1) / OJO_LEASH_Q_PX > q) q = (dn * 2 + OJO_LEASH_Q_PX - 1) / OJO_LEASH_Q_PX;
    ojo_leash_q(e) = (uint8_t)q;
}

// Hero velocity (ground px per frame, 8.8), smoothed: the Ojo aims where he will be, not where he is.
static int s_hero_prev_x, s_hero_prev_y, s_hero_vx, s_hero_vy, s_hero_prev_ok;
static void hero_velocity_update(int px, int py) {
    if (s_hero_prev_ok) {
        const int dx = px - s_hero_prev_x, dy = py - s_hero_prev_y;
        if (dx > 8 || dx < -8 || dy > 8 || dy < -8) { s_hero_vx = s_hero_vy = 0; }     // a strip rebase or a teleport, not walking
        else {
            s_hero_vx = (s_hero_vx * 3 + dx * 256) >> 2;
            s_hero_vy = (s_hero_vy * 3 + dy * 256) >> 2;
        }
    }
    s_hero_prev_x = px; s_hero_prev_y = py; s_hero_prev_ok = 1;
}

// The Ojo keeps the hero in view (DESIGN.md 6.13.9). While it is not aiming (CHASE with no sight), every OJO_PURSUE_TICKS frames it picks
// the nearest walkable point from which it sees the hero where he is now AND where he will be in OJO_PURSUE_LOOKAHEAD frames at his
// current velocity (if none sees both: the nearest that sees him now), and walks there at full speed. The point is kept until reached or
// until it loses sight of the hero. The search is a grid around the Ojo scanned ring by ring, inside a leash around its post that grows
// with the time without sight (ojo_leash_q) and never lower than OJO_LEASH_DOWN_PX (also growing) below it. aim_px / aim_py hold the
// target here (aim_px 0 = none).
static void ojo_reposition(Enemy *e, Enemy *enemies, int num_enemies, int idx, int wx, int wy, int px, int py,
                           fixed player_x, fixed player_y, const EnemyTuning *tuning) {
    if (e->state == ENEMY_STATE_CHASE) {        // (in COOLDOWN state_timer is the cooldown clock)
        if (e->state_timer < 100000) e->state_timer++;
        const int q = e->state_timer / OJO_LEASH_Q_FRAMES;
        if (q > ojo_leash_q(e)) ojo_leash_q(e) = (uint8_t)(q > OJO_LEASH_Q_MAX ? OJO_LEASH_Q_MAX : q);
    }
    const int tick8 = ((s_ai_tick + idx) & (OJO_PURSUE_TICKS - 1)) == 0;
    if (e->aim_px != 0 && tick8 && !los_has_line_of_sight(e->aim_px, e->aim_py, px, py, 0)) e->aim_px = 0;
    if (e->aim_px == 0 && tick8) {
        const int hx = *enemy_home_x(e);
        const int hy = *enemy_home_y(e);
        // Campanero fight: the Ojo keeps his post (a short leash that never grows), so the shelter column leaves the hero in his line.
        const int leash = s_post_fixed ? OJO_POST_LEASH : OJO_LEASH_DIST + ojo_leash_q(e) * OJO_LEASH_Q_PX;
        const int maxy = s_post_fixed ? hy + OJO_POST_LEASH : hy + OJO_LEASH_DOWN_PX + ojo_leash_q(e) * (OJO_LEASH_Q_PX / 2);
        const int colpx = leash / OJO_SEARCH_COLS > OJO_SEARCH_COL_PX ? leash / OJO_SEARCH_COLS : OJO_SEARCH_COL_PX;
        const int rowpx = leash / (2 * OJO_SEARCH_ROWS) > OJO_SEARCH_ROW_PX ? leash / (2 * OJO_SEARCH_ROWS) : OJO_SEARCH_ROW_PX;
        int fx = px + ((s_hero_vx * OJO_PURSUE_LOOKAHEAD) >> 8);        // where the hero will be (limited to a short stride)
        int fy = py + ((s_hero_vy * OJO_PURSUE_LOOKAHEAD) >> 8);
        if (fx > px + 48) fx = px + 48; else if (fx < px - 48) fx = px - 48;
        if (fy > py + 32) fy = py + 32; else if (fy < py - 32) fy = py - 32;
        const int moving = fx != px || fy != py;
        int best_both = 0x7fffffff, best_now = 0x7fffffff;
        int bx = 0, by = 0, nx = 0, ny = 0, ring_now = 0;
        for (int ring = 1; ring <= OJO_SEARCH_COLS && best_both == 0x7fffffff; ring++) {
            if (best_now != 0x7fffffff && ring > ring_now + 2) break;     // a point that sees him now is good enough if no better one is near
            const int rmax = ring < OJO_SEARCH_ROWS ? ring : OJO_SEARCH_ROWS;
            for (int ry = -rmax; ry <= rmax; ry++) {
                const int cy = wy + ry * rowpx;
                if (cy > maxy) continue;
                const int ay = ry < 0 ? -ry : ry;
                for (int rx = -ring; rx <= ring; rx++) {
                    const int ax = rx < 0 ? -rx : rx;
                    if (ax != ring && ay != ring) continue;          // only the cells of this ring
                    const int cx = wx + rx * colpx;
                    const int lx = cx - hx;
                    const int ly = cy - hy;
                    if (lx * lx + GROUND_DY2(ly) > leash * leash) continue;
                    const int ddx = cx - wx;
                    const int d2 = ddx * ddx + GROUND_DY2(cy - wy);
                    if (d2 >= best_both && d2 >= best_now) continue;
                    if (!line_is_walkable(wx, wy, cx, cy) || !los_has_line_of_sight(cx, cy, px, py, 0)) continue;
                    if (moving ? los_has_line_of_sight(cx, cy, fx, fy, 0) : 1) {
                        if (d2 < best_both) { best_both = d2; bx = cx; by = cy; }
                    } else if (d2 < best_now) {
                        if (best_now == 0x7fffffff) ring_now = ring;
                        best_now = d2; nx = cx; ny = cy;
                    }
                }
            }
        }
        if (best_both != 0x7fffffff) { e->aim_px = bx; e->aim_py = by; }
        else if (best_now != 0x7fffffff) { e->aim_px = nx; e->aim_py = ny; }
    }
    if (e->aim_px == 0) {                                    // no opening inside the leash: it stays put
        e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
        update_animation(e, 0);
        return;
    }
    const int tdx = e->aim_px - wx;
    const int tdy = e->aim_py - wy;
    const int tdist = (int)int_sqrt((uint32_t)(tdx * tdx + GROUND_DY2(tdy)));
    if (tdist <= 2) {
        e->aim_px = 0;
        update_animation(e, 0);
        return;
    }
    fixed speed = burn_slow(e, haste_speed(e, (tuning->speed * OJO_REPOSITION_SPEED_PCT) / 100));
    fixed vx = (fixed)div32(tdx * (int32_t)speed, tdist);
    fixed vy = (fixed)div32(tdy * (int32_t)speed, tdist);
    s_sep_skip_guard = 1;
    apply_separation(enemies, num_enemies, idx, &vx, &vy);
    s_sep_skip_guard = 0;
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    if (!moved) e->aim_px = 0;
    e->dir = dir_from_vector(TO_FIXED(tdx), TO_FIXED(tdy));
    update_animation(e, moved);
}

#if OJO_PURSUE_IN_COOLDOWN
// Between shots the Ojo also keeps the hero in view: every OJO_PURSUE_TICKS it checks the line to him now and to where he will be, and
// walks (ojo_reposition) while either is missing. The verdict is kept in has_los bit 32 between checks.
#define VIEW_PURSUE 32
static int ojo_wants_to_move(Enemy *e, int idx, int wx, int wy, int px, int py) {
    if (((s_ai_tick + idx) & (OJO_PURSUE_TICKS - 1)) == 0) {
        int fx = px + ((s_hero_vx * OJO_PURSUE_LOOKAHEAD) >> 8);
        int fy = py + ((s_hero_vy * OJO_PURSUE_LOOKAHEAD) >> 8);
        if (fx > px + 48) fx = px + 48; else if (fx < px - 48) fx = px - 48;
        if (fy > py + 32) fy = py + 32; else if (fy < py - 32) fy = py - 32;
        int need = !los_has_line_of_sight(wx, wy, px, py, 0);
        if (!need && (fx != px || fy != py)) need = !los_has_line_of_sight(wx, wy, fx, fy, 0);
        if (need) e->has_los |= VIEW_PURSUE; else { e->has_los &= ~VIEW_PURSUE; e->aim_px = 0; }
    }
    return (e->has_los & VIEW_PURSUE) != 0;
}
#endif

static void update_shooter(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                           fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_SHOOTER];

    if (g_player_state.is_dead) {
        if (e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK) e->state = ENEMY_STATE_CHASE;
        update_animation(e, 0);
        return;
    }

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);
    int dx = px - wx;
    int dy = py - wy;
    int ground_dist_sq = dx * dx + GROUND_DY2(dy);
    int ground_dist = (int)int_sqrt((uint32_t)ground_dist_sq);

    switch (e->state) {
        case ENEMY_STATE_TRACK: {
            if (ojo_hero_covered(e, player_x, player_y)) {
                // Hero behind low cover: no beam against a bench. The cycle waits at its start (eyes on him); when he is exposed the
                // whole TRACK -> LOCK -> SENTENCE runs with its normal times. Covering again mid-cycle sends it back here.
                if (ground_dist <= OJO_SIGHT_RANGE + OJO_RANGE_MARGIN && los_has_line_of_sight(wx, wy, px, py, 0)) {
                    e->aim_px = px;
                    e->aim_py = py;
                    e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                }
                ojo_look_anim(e);
                e->state_timer = OJO_TRACK_FRAMES;
                break;
            }
            // Stands still facing the hero; the band follows him while it has a clear line within range,
            // otherwise it keeps its last point (a column or wall cuts the gaze, not the clock).
            if (ground_dist <= OJO_SIGHT_RANGE + OJO_RANGE_MARGIN && los_has_line_of_sight(wx, wy, px, py, 0)) {
                e->aim_px = px;
                e->aim_py = py;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            }
            ojo_look_anim(e);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_LOCK;
                e->state_timer = OJO_LOCK_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_LOCK: {
            if (ojo_hero_covered(e, player_x, player_y)) {      // covered again mid-cycle: back to the start of the aim
                e->state = ENEMY_STATE_TRACK;
                e->state_timer = OJO_TRACK_FRAMES;
                ojo_look_anim(e);
                break;
            }
            // Direction and point frozen: the dodge window.
            ojo_look_anim(e);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_SENTENCE;
                e->state_timer = OJO_BEAM_FRAMES;
                e->frame = 0;
                e->gesture = 1;
                ojo_fire(e, player_x, player_y);
                sfx_play(SND_OJO_FIRE, TO_INT(e->x));
            }
            break;
        }

        case ENEMY_STATE_SENTENCE: {
            ojo_gesture_tick(e);
            if (OJO_BEAM_FRAMES - e->state_timer < OJO_BEAM_HIT_FRAMES) ojo_beam_hurts(e, player_x, player_y);   // impact + flare, not dissipation
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_COOLDOWN;
                e->state_timer = tuning->attack_cooldown;
            }
            break;
        }

        case ENEMY_STATE_COOLDOWN: {
            ojo_gesture_tick(e);
#if OJO_PURSUE_IN_COOLDOWN
            if ((e->home_flags & ENEMY_HOME_SET) && e->gesture == 0 && ojo_wants_to_move(e, idx, wx, wy, px, py)) {
                ojo_reposition(e, enemies, num_enemies, idx, wx, wy, px, py, player_x, player_y, tuning);
            } else {
                e->aim_px = 0;
                update_animation(e, 0);
            }
#else
            update_animation(e, 0);
#endif
            if (--e->state_timer <= 0) { e->state = ENEMY_STATE_CHASE; e->aim_px = 0; }
            break;
        }

        case ENEMY_STATE_WOBBLE:
            // Reeling after a hit that did not kill: the aim cycle stops (no tracking, no sentence) and it just
            // trembles with the warm pulse of main.c. From here L starts the finisher (remate.c, kind Ojo).
            e->gesture = 0;
            e->aim_px = 0;
            if (--e->state_timer <= 0) { e->state = ENEMY_STATE_CHASE; e->state_timer = 0; }
            break;

        case ENEMY_STATE_POSITION:      // waiting for a free aiming slot
        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;
            e->gesture = 0;
            const int homed = (e->home_flags & ENEMY_HOME_SET) != 0;       // encounter rooms: it holds a post, it does not hunt
            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, OJO_SIGHT_RANGE);   // walking flags (direct run)
            if (((s_ai_tick + idx) & 3) == 0 && ground_dist <= OJO_SIGHT_RANGE &&
                los_has_line_of_sight(wx, wy, px, py, 0))
                e->has_los |= VIEW_SIGHT;                                             // same cadence as the refresh above
            int sight = (e->has_los & VIEW_SIGHT) && ground_dist <= OJO_SIGHT_RANGE;
            // Horde: far above the player in the strip it keeps walking instead of aiming (the horde keeps them near).
            int may_look = homed || !(s_strip_mode && wy < py - HORDE_SHOOTER_TOP_LIMIT_PX);
            if (sight && may_look && ojos_looking(enemies, num_enemies) < OJO_MAX_LOOKING) {
                if (homed) ojo_leash_settle(e);
                e->state = ENEMY_STATE_TRACK;
                e->state_timer = OJO_TRACK_FRAMES;
                e->frame = 0;
                e->anim_timer = 0;
                e->aim_px = px;
                e->aim_py = py;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                sfx_play(SND_OJO_CHARGE, TO_INT(e->x));
            } else if (homed) {
                if (sight) {                                // no free aiming slot: it waits at its post, watching
                    ojo_leash_settle(e);
                    e->state = ENEMY_STATE_POSITION;
                    e->state_timer = 0;
                    e->aim_px = 0;
                    e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                    update_animation(e, 0);
                } else {
                    ojo_reposition(e, enemies, num_enemies, idx, wx, wy, px, py, player_x, player_y, tuning);
                }
            } else if (sight && ground_dist <= OJO_WAIT_DIST) {
                e->state = ENEMY_STATE_POSITION;        // no free slot: waits where it is
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                update_animation(e, 0);
            } else {
                chase_step(e, enemies, num_enemies, idx, tuning->speed, wx, wy, px, py, ground_dist_sq);
                // Search: sweep head/facing slowly left and right while walking; no light, no mark.
                static const int8_t s_search_sweep[4] = { 0, 1, 0, -1 };
                int sweep = s_search_sweep[((s_ai_tick + idx * 17) >> 5) & 3];
                e->dir = (e->dir + sweep) & 7;
            }
            break;
        }
    }
}

// Garrison (DESIGN.md 6.13.9): an Exvoto or Cireneo that wakes with the room but holds its post, watching the hero, until the hero
// comes within GUARD_RELEASE_DIST of the post, it is hurt, or the Ojos it guards (posts within GUARD_OJO_BOND_DIST) are all dead.
static void guard_release(Enemy *e) {
    e->home_flags &= ENEMY_TIER2;                              // the post goes, the tier stays
    e->aim_px = e->aim_py = e->beam_mx = e->beam_my = 0;      // the post lived in aim_px / aim_py: give the fields back clean
    e->state = ENEMY_STATE_CHASE;
    e->state_timer = 0;
}

static void update_guard(Enemy *e, Enemy *enemies, int num_enemies, int idx, fixed player_x, fixed player_y) {
    if (g_player_state.is_dead) {
        update_animation(e, 0);
        return;
    }
    const int hx = *enemy_home_x(e);
    const int hy = *enemy_home_y(e);
    const int dx = TO_INT(player_x) - hx;
    const int dy = TO_INT(player_y) - hy;
    if (e->hp < e->max_hp || e->hit_timer > 0 || dx * dx + GROUND_DY2(dy) <= GUARD_RELEASE_DIST * GUARD_RELEASE_DIST) {
        guard_release(e);
        return;
    }
    if (((s_ai_tick + idx) & 7) == 0) {                      // the guarded Ojos: still alive?
        int bonded = 0;
        for (int j = 0; j < num_enemies && !bonded; j++) {
            Enemy *o = &enemies[j];
            if (!o->active || o->hp <= 0 || o->type != ENEMY_TYPE_SHOOTER || o->pack != e->pack || !(o->home_flags & ENEMY_HOME_SET)) continue;
            int ox = *enemy_home_x(o) - hx;
            int oy = *enemy_home_y(o) - hy;
            if (ox * ox + GROUND_DY2(oy) <= GUARD_OJO_BOND_DIST * GUARD_OJO_BOND_DIST) bonded = 1;
        }
        if (!bonded) {
            guard_release(e);
            return;
        }
    }
    e->dir = dir_from_vector(player_x - e->x, player_y - e->y);    // watches the hero
    update_animation(e, 0);
}

// ---------------------------------------------------------------------------
// Monja (v3 tier): support. She stays behind, praying (the Exvoto pray slot), and while she prays the troops
// around her (other tiers and Exvotos, not herself) recover a little life per second, shown with the existing
// green heal numbers (dmg_numbers DMG_NUM_HEAL). She is a guard: she does not chase, she only bites back when the
// hero comes right into her. `home_flags` carries the post; her prayer clock lives in `state_timer`.
// ---------------------------------------------------------------------------
#if ENCOUNTERS_PROTO
static int monja_heals_ally(const Enemy *m, const Enemy *o) {
    if (!o->active || o->hp <= 0) return 0;
    if (o == m) return 0;                                     // she never heals herself
    if (o->type != ENEMY_TYPE_BEBE && o->type != ENEMY_TYPE_EXVOTO && o->type != ENEMY_TYPE_PARROCO &&
        o->type != ENEMY_TYPE_MONAGUILLO && o->type != ENEMY_TYPE_MONJA &&
        o->type != ENEMY_TYPE_CAMPANERO) return 0;   // the Exvoto family and the Campanero (DESIGN-ARPG.md 9)
    int dx = TO_INT(o->x - m->x);
    int dy = TO_INT(o->y - m->y);
    return dx * dx + GROUND_DY2(dy) <= ARPG_MONJA_PRAY_RADIUS * ARPG_MONJA_PRAY_RADIUS;
}

// Marks (s_haste) every ally inside the radius of a praying Super Monja. Called once per frame.
static void haste_refresh(Enemy *enemies, int num_enemies) {
    s_haste_base = enemies;
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
    memset(s_haste, 0, sizeof(s_haste));
    for (int i = 0; i < num_enemies; i++) {
        const Enemy *m = &enemies[i];
        if (!m->active || m->hp <= 0 || m->type != ENEMY_TYPE_MONJA || m->state != ENEMY_STATE_PRAY || g_enemy_ally[i]) continue;
        for (int j = 0; j < num_enemies; j++)
            if (!g_enemy_ally[j] && monja_heals_ally(m, &enemies[j])) s_haste[j] = 1;
    }
}

static void monja_pray(Enemy *e, Enemy *enemies, int num_enemies) {
    e->state_timer++;
    // Clip loop of the standing prayer (the Exvoto pray slot).
    int anim_period = g_characters[e->char_id].anim_period;
    if (++e->anim_timer >= anim_period) {
        e->anim_timer = 0;
        e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES;
    }
    if (e->state_timer % ARPG_MONJA_HEAL_PERIOD != 0) return;
    int healed_any = 0;
    for (int j = 0; j < num_enemies; j++) {
        Enemy *o = &enemies[j];
        if (!monja_heals_ally(e, o) || o->hp >= o->max_hp) continue;
        int heal = o->max_hp * ARPG_MONJA_HEAL_PCT / 100;
        if (heal < 1) heal = 1;
        o->hp += heal;
        if (o->hp > o->max_hp) o->hp = o->max_hp;
        dmg_numbers_spawn(o->x, o->y - TO_FIXED(16), heal, DMG_NUM_HEAL);   // green sage number over the healed one
        healed_any = 1;
    }
    if (healed_any) sfx_play(SND_MONJA_HEAL, TO_INT(e->x));
}

// One step of the Super Monja's movement: the "monjarana" scuttle. Short, very fast bursts (frames 0-5 of the walk
// sheet spread over the burst, no skating) toward the goal (the hero's nav field when approaching, straight away from
// him when fleeing), each one deflected 45-90 degrees alternating sides (zigzag, 1 in ARPG_MONJA_BACKSTEP_ONE_IN a
// short sideways step back), separated by dead stops on the pause frames (6/7). A burst that hits a wall is cut.
// Per-enemy state lives in fields the Monja does not otherwise use: beam_len = phase (0 burst, 1 pause), gesture =
// frames left in the phase, beam_mx = burst length, aim_dir_x/y = burst direction (8.8 unit, ground metric),
// beam_ux = next deflection side. monja_scuttle_reset() starts it from a pause of 0 frames.
static void monja_scuttle_reset(Enemy *e) {
    e->beam_len = 1;
    e->gesture = 0;
    e->beam_ux = ((rng_next() >> 16) & 1u) ? 1 : -1;
    e->beam_my = 0;                                           // Super Monja mode: 0 scuttle, 1 warn, 2 charge, 3 recover
    e->beam_uy = rng_range(ARPG_SMONJA_CHARGE_CD_MIN, ARPG_SMONJA_CHARGE_CD_MAX);   // frames to the next charge
    e->kneel = 0;                                             // 1 = kiting (fast escape bursts, no pauses)
    e->charge_hit = 0;
}

static void monja_walk(Enemy *e, Enemy *enemies, int num_enemies, int idx, int wx, int wy, int px, int py,
                       int walk, fixed speed) {
    (void)speed;
    if (e->beam_len == 1) {                                   // pause (or about to start a burst)
        if (e->gesture > 0) {
            e->gesture--;
            e->frame = 6 + ((e->gesture & 2) ? 1 : 0);
            e->anim_timer = 0;
            return;
        }
        // New burst: aim at the goal, then deflect.
        int tx = px, ty = py;
        if (walk == 0) {                                      // orbit: tangent to the circle around the hero (ground metric)
            tx = wx - ((py - wy) * 2) * e->strafe_dir;
            ty = wy + ((px - wx) * e->strafe_dir) / 2;
        } else if (walk > 0) {
            int sx, sy;
            if (nav_next_step(wx, wy, &sx, &sy)) { tx = sx; ty = sy; }
        } else {
            tx = wx - (px - wx);
            ty = wy - (py - wy);
        }
        int ux, uy;
        if (!aim_vector(wx, wy, tx, ty, &ux, &uy)) { ux = 0; uy = 256 / 2; }
        static const int16_t k_cos[4] = { 222, 181, 128, 66 };     // 30, 45, 60, 75 degrees (8.8)
        static const int16_t k_sin[4] = { 128, 181, 222, 247 };
        int ci = (int)((rng_next() >> 16) & 3u);   // high bits: the LCG low bits cycle
        int c = k_cos[ci], sn = k_sin[ci];
        int len = rng_range(ARPG_MONJA_BURST_MIN, ARPG_MONJA_BURST_MAX);
        if (rng_range(0, ARPG_MONJA_BACKSTEP_ONE_IN - 1) == 0) {   // small sideways step back
            c = -181; sn = 181;
            len = ARPG_MONJA_BURST_MIN;
        }
        int side = e->beam_ux;
        int gy = uy * 2;                                       // ground-space vector
        int rx = (ux * c - side * sn * gy) >> 8;
        int ry = (side * sn * ux + c * gy) >> 8;               // still ground-space
        e->aim_dir_x = rx;
        e->aim_dir_y = ry / 2;                                 // back to the (dx, dy) world convention
        e->beam_ux = -side;
        e->beam_mx = len;
        e->gesture = len;
        e->beam_len = 0;
    }
    // Burst frame: fast, direction fixed for the whole burst.
    fixed spd = burn_slow(e, haste_speed(e, e->kneel ? ARPG_SMONJA_KITE_SPEED : ARPG_MONJA_BURST_SPEED));
    fixed vx = (fixed)((e->aim_dir_x * (int32_t)spd) >> 8);
    fixed vy = (fixed)((e->aim_dir_y * (int32_t)spd) >> 8);
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    e->dir = dir_from_vector(vx, vy * 2);
    int elapsed = e->beam_mx - e->gesture;                     // 0 .. len-1
    e->frame = div32(elapsed * 6, e->beam_mx);                 // frames 0-5 spread over the burst
    e->anim_timer = 0;
    (void)enemies; (void)num_enemies; (void)idx;
    if (!moved || --e->gesture <= 0) {                         // blocked by a wall, or the burst is over: stop dead
        e->beam_len = 1;
        e->gesture = e->kneel ? 0 : rng_range(ARPG_MONJA_PAUSE_MIN, ARPG_MONJA_PAUSE_MAX);
        e->frame = 6;
    }
}

// Where she goes when she has nothing else to do: the prayer (ARPG_MONJA_PRAYS) or the scuttling approach.
static void monja_rest(Enemy *e) {
    e->state_timer = 0;
    e->frame = 0; e->anim_timer = 0;
#if ARPG_MONJA_PRAYS
    e->state = ENEMY_STATE_PRAY;
    e->char_id = exvoto_pose_char(e->type, EXVOTO_POSE_PRAY_STAND);
#else
    e->state = ENEMY_STATE_POSITION;
    if (e->strafe_dir == 0) e->strafe_dir = 1;
    e->char_id = enemy_type_char_id(ENEMY_TYPE_MONJA);
    monja_scuttle_reset(e);
#endif
}

#if !ARPG_MONJA_PRAYS
// Super Monja (DESIGN-ARPG s5): circles the hero at mid distance with the scuttle, kites when he gets to punching
// range, and every few seconds warns (still, trembling), charges in a straight line and stops (vulnerable).
// Mode in beam_my (0 scuttle, 1 warn, 2 charge, 3 recover, 4 bounce), mode clock in state_timer, charge direction in
// aim_dir_x/y. Moving backwards facing the hero (bounce, kite) plays the walk in reverse so she does not skate.
#define SM_SCUTTLE 0
#define SM_WARN 1
#define SM_CHARGE 2
#define SM_RECOVER 3
#define SM_BOUNCE 4

// One step straight along the unit vector (ux, uy) (8.8, ground metric) at `speed`, facing the hero, walk played backwards.
static int smonja_back_step(Enemy *e, int ux, int uy, int speed, fixed player_x, fixed player_y) {
    fixed vx = (fixed)((ux * speed) >> 8);
    fixed vy = (fixed)((uy * speed) >> 8);
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
    e->anim_timer++;
    e->frame = 5 - ((e->anim_timer / 2) % 6);
    return moved;
}
// The Super Monja is the only Exvoto that dodges the Glifo: while a glifo has not detonated yet and she is inside its
// ellipse (or about to be), she dashes outwards with a zigzag until she is clear. Cancels any warn / charge in progress.
static int smonja_glifo_dodge(Enemy *e, int wx, int wy, fixed player_x, fixed player_y) {
    (void)player_x; (void)player_y;
    const int side = e->strafe_dir >= 0 ? 1 : -1;
    int ux, uy;
    const int fl = glifo_flee_dir(wx, wy, ARPG_SMONJA_GLIFO_MARGIN, ((e->anim_timer >> 3) & 1) ? -side : side, &ux, &uy);
    if (!fl) return 0;
    if (fl == 2) {                                           // the crack has just opened under her: a stop dead, then she runs
        if (e->beam_my == SM_WARN && e->knock_vx) { e->x -= TO_FIXED(e->knock_vx); e->knock_vx = 0; }
        e->beam_my = SM_SCUTTLE;
        e->frame = 6; e->anim_timer = 0;
        return 1;
    }
    if (e->beam_my == SM_WARN && e->knock_vx) { e->x -= TO_FIXED(e->knock_vx); e->knock_vx = 0; }   // undo the warning shake
    e->beam_my = SM_SCUTTLE;
    e->kneel = 0;
    fixed vx = (fixed)((ux * ARPG_SMONJA_GLIFO_SPEED) >> 8);
    fixed vy = (fixed)((uy * ARPG_SMONJA_GLIFO_SPEED) >> 8);
    move_with_slide(&e->x, &e->y, vx, vy);
    e->dir = dir_from_vector(vx, vy * 2);
    e->anim_timer++;
    e->frame = (e->anim_timer / 2) % 6;                       // the walk, sped up
    return 1;
}
static void smonja_update(Enemy *e, Enemy *enemies, int num_enemies, int idx, int wx, int wy, int px, int py,
                          int ground_dist_sq, fixed player_x, fixed player_y) {
    switch (e->beam_my) {
        case SM_WARN: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            e->frame = 6; e->anim_timer = 0;
            int t = ARPG_SMONJA_WARN_FRAMES - e->state_timer;
            if ((t & 1) == 0) {                               // 1 px shake of the sprite position, +1 / -1 every 2 frames
                int off = (t & 2) ? -1 : 1;
                e->x += TO_FIXED(off - e->knock_vx);
                e->knock_vx = off;
            }
            if (--e->state_timer <= 0) {
                e->x -= TO_FIXED(e->knock_vx);                // back to the true position
                e->knock_vx = 0;
                int ux, uy;
                if (!aim_vector(wx, wy, px, py, &ux, &uy)) { ux = 0; uy = 128; }
                e->aim_dir_x = ux; e->aim_dir_y = uy;        // where the hero was when the charge began
                e->beam_my = SM_CHARGE;
                e->state_timer = ARPG_SMONJA_CHARGE_FRAMES;
                e->charge_hit = 0;
                e->frame = 0;
            }
            return;
        }
        case SM_CHARGE: {
            if (ground_dist_sq > ARPG_SMONJA_CHARGE_LOCK_DIST * ARPG_SMONJA_CHARGE_LOCK_DIST) {   // she tracks the hero until close
                int tx, ty;
                if (aim_vector(wx, wy, px, py, &tx, &ty)) {
                    int mx = (e->aim_dir_x * ((1 << ARPG_SMONJA_CHARGE_STEER) - 1) + tx) >> ARPG_SMONJA_CHARGE_STEER;
                    int my = (e->aim_dir_y * ((1 << ARPG_SMONJA_CHARGE_STEER) - 1) + ty) >> ARPG_SMONJA_CHARGE_STEER;
                    int len = (int)int_sqrt((uint32_t)(mx * mx + GROUND_DY2(my)));
                    if (len > 0) { e->aim_dir_x = div32(mx * 256, len); e->aim_dir_y = div32(my * 256, len); }
                }
            }
            fixed vx = (fixed)((e->aim_dir_x * ARPG_SMONJA_CHARGE_SPEED) >> 8);
            fixed vy = (fixed)((e->aim_dir_y * ARPG_SMONJA_CHARGE_SPEED) >> 8);
            int moved = move_with_slide(&e->x, &e->y, vx, vy);
            e->dir = dir_from_vector(vx, vy * 2);
            e->frame = ((ARPG_SMONJA_CHARGE_FRAMES - e->state_timer) / 2) % 6;   // the walk, sped up (frames 0-5)
            e->anim_timer = 0;
            int hit = ground_dist_sq <= ARPG_SMONJA_HIT_RADIUS * ARPG_SMONJA_HIT_RADIUS;
            if (hit && !e->charge_hit) {
                e->charge_hit = 1;                            // the headbutt: one hit per charge, and she stops dead
                player_take_damage(&g_player_state, ARPG_SMONJA_CHARGE_DAMAGE);
            }
            if (hit || !moved || --e->state_timer <= 0) {
                e->beam_my = SM_RECOVER;
                e->state_timer = ARPG_SMONJA_RECOVER_FRAMES;
                e->frame = 6;
            }
            return;
        }
        case SM_RECOVER:
            e->frame = 6; e->anim_timer = 0;
            if (--e->state_timer <= 0) {
                e->beam_my = SM_BOUNCE;                       // after the short pause: straight back, away from the hero
                e->state_timer = ARPG_SMONJA_BOUNCE_FRAMES;
            }
            return;
        case SM_BOUNCE: {
            smonja_back_step(e, -e->aim_dir_x, -e->aim_dir_y, ARPG_SMONJA_BOUNCE_SPEED, player_x, player_y);
            if (ground_dist_sq >= ARPG_SMONJA_BOUNCE_DIST * ARPG_SMONJA_BOUNCE_DIST || --e->state_timer <= 0) {
                int side = -e->strafe_dir;
                monja_scuttle_reset(e);                       // new cooldown, back to circling
                e->strafe_dir = side;
            }
            return;
        }
        default: break;
    }
    // Scuttle: countdown to the next charge (only starts when the hero is within reach).
    if (e->beam_uy > 0) e->beam_uy--;
    if (e->beam_uy <= 0 && !e->kneel && ground_dist_sq <= ARPG_SMONJA_CHARGE_MAX_DIST * ARPG_SMONJA_CHARGE_MAX_DIST) {
        e->beam_my = SM_WARN;
        e->state_timer = ARPG_SMONJA_WARN_FRAMES;
        e->knock_vx = 0;
        return;
    }
    // Kite: at punching range she backs off fast, facing the hero, without pauses, until she is out of reach.
    if (ground_dist_sq <= ARPG_SMONJA_KITE_DIST * ARPG_SMONJA_KITE_DIST) e->kneel = 1;
    else if (ground_dist_sq >= ARPG_SMONJA_RING_NEAR * ARPG_SMONJA_RING_NEAR) e->kneel = 0;
    if (e->kneel) {
        int ux, uy;
        if (!aim_vector(px, py, wx, wy, &ux, &uy)) { ux = 0; uy = 128; }
        smonja_back_step(e, ux, uy, ARPG_SMONJA_KITE_SPEED, player_x, player_y);
        e->beam_len = 1; e->gesture = 0;                      // the next scuttle burst starts at once
        return;
    }
    int walk = ground_dist_sq < ARPG_SMONJA_RING_NEAR * ARPG_SMONJA_RING_NEAR ? -1
             : ground_dist_sq > ARPG_SMONJA_RING_FAR * ARPG_SMONJA_RING_FAR ? 1 : 0;
    monja_walk(e, enemies, num_enemies, idx, wx, wy, px, py, walk, 0);
}
#endif

static void update_monja(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                         fixed player_x, fixed player_y, const EnemyTuning *tuning) {
    if (e->state == ENEMY_STATE_EMERGE) {
        e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
        if (--e->state_timer <= 0) monja_rest(e);
        return;
    }
    if (g_player_state.is_dead) { update_animation(e, 0); return; }

    int wx = TO_INT(e->x), wy = TO_INT(e->y);
    int px = TO_INT(player_x), py = TO_INT(player_y);
    int dx = px - wx, dy = py - wy;
    int ground_dist_sq = dx * dx + GROUND_DY2(dy);

    // Hit-stun: while hit_timer > 0 (and not reeling in WOBBLE), do not enter ATTACK or deal damage.
    if (e->hit_timer > 0 && e->state != ENEMY_STATE_WOBBLE) {
        update_animation(e, 0);
        return;
    }

#if ARPG_MONJA_PRAYS
    // Hurt or with the hero right on top of her: she drops the prayer and fights back like a weak Exvoto.
    if (e->state != ENEMY_STATE_ATTACK && e->state != ENEMY_STATE_WOBBLE &&
        (e->hit_timer > 0 || ground_dist_sq <= (tuning->preferred_dist_max + 8) * (tuning->preferred_dist_max + 8))) {
        e->state = ENEMY_STATE_ATTACK;
        e->state_timer = tuning->attack_cooldown;
        e->char_id = enemy_type_char_id(ENEMY_TYPE_MONJA);
    }
#endif

#if !ARPG_MONJA_PRAYS
    // No prayer (see smonja_update). The heal / haste / placement code stays, disconnected, for another enemy.
    if (e->state == ENEMY_STATE_PRAY || e->state == ENEMY_STATE_DORMANT) monja_rest(e);
    if (e->state == ENEMY_STATE_POSITION && smonja_glifo_dodge(e, wx, wy, player_x, player_y)) return;
    if (e->state == ENEMY_STATE_POSITION) {
        smonja_update(e, enemies, num_enemies, idx, wx, wy, px, py, ground_dist_sq, player_x, player_y);
        return;
    }
#else
    // Placement: she keeps a middle distance behind her group. Too close -> walks away; too far -> walks closer;
    // in between (hysteresis) she stops and prays. Only while not brawling or reeling.
    if (e->state == ENEMY_STATE_PRAY || e->state == ENEMY_STATE_POSITION) {
        int walk = 0;                                         // -1 = away from the hero, +1 = towards him
        if (e->state == ENEMY_STATE_POSITION) {
            walk = e->strafe_dir;
            if (walk < 0 && ground_dist_sq >= ARPG_MONJA_KEEP_FLEE_STOP * ARPG_MONJA_KEEP_FLEE_STOP) walk = 0;
            if (walk > 0 && ground_dist_sq <= ARPG_MONJA_KEEP_FAR_STOP * ARPG_MONJA_KEEP_FAR_STOP) walk = 0;
        } else if (ground_dist_sq < ARPG_MONJA_KEEP_FLEE * ARPG_MONJA_KEEP_FLEE) walk = -1;
        else if (ground_dist_sq > ARPG_MONJA_KEEP_FAR * ARPG_MONJA_KEEP_FAR) walk = 1;
        if (walk != 0) {
            if (e->state != ENEMY_STATE_POSITION) {
                e->state = ENEMY_STATE_POSITION;
                e->char_id = enemy_type_char_id(ENEMY_TYPE_MONJA);
                monja_scuttle_reset(e);
                e->frame = 0; e->anim_timer = 0;
            }
            e->strafe_dir = walk;
            monja_walk(e, enemies, num_enemies, idx, wx, wy, px, py, walk, tuning->speed);
            return;
        }
        if (e->state == ENEMY_STATE_POSITION) {               // arrived: back to the prayer
            e->state = ENEMY_STATE_PRAY;
            e->state_timer = 0;
            e->char_id = exvoto_pose_char(e->type, EXVOTO_POSE_PRAY_STAND);
            e->frame = 0; e->anim_timer = 0;
        }
    }

#endif
    switch (e->state) {
        case ENEMY_STATE_WOBBLE:
            if (--e->state_timer <= 0) monja_rest(e);
            break;
        case ENEMY_STATE_ATTACK: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            if (e->state_timer == tuning->attack_cooldown && ground_dist_sq <= tuning->preferred_dist_max * tuning->preferred_dist_max)
                player_take_damage(&g_player_state, arpg_enemy_damage_of(e));
            if (--e->state_timer <= 0) {
                // Back to praying (the support pose) if she is safe again, otherwise keep brawling.
                if (ground_dist_sq > (tuning->preferred_dist_max + 8) * (tuning->preferred_dist_max + 8) && e->hit_timer == 0) {
                    monja_rest(e);
                } else {
                    e->state_timer = tuning->attack_cooldown;
                }
            }
            update_animation(e, 0);
            break;
        }
        case ENEMY_STATE_PRAY:
        default: {
#if !ARPG_MONJA_PRAYS
            monja_rest(e);
            break;
#endif
            e->state = ENEMY_STATE_PRAY;
            e->char_id = exvoto_pose_char(e->type, EXVOTO_POSE_PRAY_STAND);
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);   // she faces the hero while praying
            monja_pray(e, enemies, num_enemies);
            break;
        }
    }
    (void)idx;
}
#endif  // ENCOUNTERS_PROTO

// ---------------------------------------------------------------------------
// El Abanderado (jefe, version minima) & cream puddles (DESIGN.md 6.10)
// ---------------------------------------------------------------------------
#define MAX_PUDDLES 8
#define PUDDLE_DURATION 36    // ~0.6 s total: opens, monaguillos emerge (30 f), dries out

typedef struct {
    int x, y;
    int timer;
    int active;
} CreamPuddle;

static CreamPuddle s_puddles[MAX_PUDDLES];

void enemy_puddles_init(void) {
    memset(s_puddles, 0, sizeof(s_puddles));
}

void enemy_puddles_shift_y(int dy_px) {
    for (int i = 0; i < MAX_PUDDLES; i++)
        if (s_puddles[i].active) s_puddles[i].y += dy_px;
}

void enemy_puddles_update(void) {
    for (int i = 0; i < MAX_PUDDLES; i++) {
        if (!s_puddles[i].active) continue;
        if (++s_puddles[i].timer >= PUDDLE_DURATION) s_puddles[i].active = 0;
    }
}

void enemy_puddles_render(uint16_t *buffer, int cam_x, int cam_y) {
    GroundTarget g = { buffer, cam_x, cam_y };
    const uint16_t cream_fill = RGB15(23, 21, 16); // desaturated warm cream
    const uint16_t cream_edge = RGB15(17, 15, 11);
    for (int i = 0; i < MAX_PUDDLES; i++) {
        const CreamPuddle *p = &s_puddles[i];
        if (!p->active) continue;
        int t = p->timer;
        int r = 14;
        if (t < 8) r = 4 + ((t * 10) >> 3);
        else if (t > PUDDLE_DURATION - 8) r = (((PUDDLE_DURATION - t) * 14) >> 3);
        if (r < 2) continue;
        gfx_ground_disc(&g, p->x, p->y, r, cream_fill, GFX_FILL_SOLID, 0);
        gfx_ground_ring(&g, p->x, p->y, r, cream_edge, 0);
    }
}

static int count_live_monaguillos(const Enemy *enemies, int num_enemies) {
    int n = 0;
    for (int i = 0; i < num_enemies; i++) {
        if (enemies[i].active && enemies[i].type == ENEMY_TYPE_MONAGUILLO) n++;
    }
    return n;
}

static void spawn_monaguillo_at(Enemy *slot, int x, int y) {
    memset(slot, 0, sizeof(*slot));
    slot->x = TO_FIXED(x);
    slot->y = TO_FIXED(y);
    slot->type = ENEMY_TYPE_MONAGUILLO;
    slot->char_id = CHAR_MONAGUILLO;
    slot->hp = g_enemy_tuning[ENEMY_TYPE_MONAGUILLO].max_hp;
    slot->max_hp = slot->hp;
    slot->dir = DIR_SOUTH;
    slot->active = 1;
    slot->state = ENEMY_STATE_EMERGE;
    slot->state_timer = MONAGUILLO_EMERGE_FRAMES;
    slot->strafe_dir = (rng_next() & 1u) ? 1 : -1;
    slot->pack = -1;
    sfx_play(SND_MONAGUILLO_EMERGE, x);
}

int g_abanderado_max_mona = 8;           // cap of live monaguillos of the Abanderado (encounters_act1.c sets it per boss)

static void spawn_cream_puddle(Enemy *enemies, int num_enemies, int mx, int my) {
    for (int i = 0; i < MAX_PUDDLES; i++) {
        if (!s_puddles[i].active) {
            s_puddles[i].x = mx;
            s_puddles[i].y = my;
            s_puddles[i].timer = 0;
            s_puddles[i].active = 1;
            break;
        }
    }
    static const int8_t dx_off[2] = { -8, 8 };
    int live = count_live_monaguillos(enemies, num_enemies);
    for (int k = 0; k < 2 && live < g_abanderado_max_mona; k++) {
        int sx = mx + dx_off[k];
        int sy = my;
        if (!position_is_free(TO_FIXED(sx), TO_FIXED(sy))) { sx = mx; sy = my; }
        if (!position_is_free(TO_FIXED(sx), TO_FIXED(sy))) continue;
        for (int i = 0; i < num_enemies; i++) {
            if (!enemies[i].active) {
                spawn_monaguillo_at(&enemies[i], sx, sy);
                live++;
                break;
            }
        }
    }
}

static void pick_abanderado_patrol_target(Enemy *e, int px, int py) {
    int min_x = s_view_valid ? s_view_l + ENEMY_AI_VIEW_MARGIN + 24 : px - 100;
    int max_x = s_view_valid ? s_view_r - ENEMY_AI_VIEW_MARGIN - 24 : px + 100;
    int min_y = s_view_valid ? s_view_t + ENEMY_AI_VIEW_MARGIN + 24 : py - 140;
    int max_y = s_view_valid ? s_view_b - ENEMY_AI_VIEW_MARGIN - 24 : py + 40;
    if (min_x > max_x) { min_x = px - 40; max_x = px + 40; }
    if (min_y > max_y) { min_y = py - 60; max_y = py + 20; }
    for (int attempt = 0; attempt < 8; attempt++) {
        int tx = rng_range(min_x, max_x);
        int ty = rng_range(min_y, max_y);
        if (position_is_free(TO_FIXED(tx), TO_FIXED(ty))) {
            e->aim_px = tx;
            e->aim_py = ty;
            e->state_timer = 150;
            return;
        }
    }
    e->aim_px = px;
    e->aim_py = py - 48;
    e->state_timer = 60;
}

static void update_abanderado(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                              fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_ABANDERADO];
    (void)idx;
    if (g_player_state.is_dead) {
        update_animation(e, 0);
        return;
    }

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);
    int dx = px - wx;
    int dy = py - wy;
    int ground_dist_sq = dx * dx + GROUND_DY2(dy);
    int sight_r = (e->state == ENEMY_STATE_POINT)
        ? (ABANDERADO_SIGHT_RANGE + ABANDERADO_SIGHT_MARGIN)
        : ABANDERADO_SIGHT_RANGE;
    int in_sight = (ground_dist_sq <= sight_r * sight_r) && los_has_line_of_sight(wx, wy, px, py, 0);

    if (e->state == ENEMY_STATE_POINT) {
        e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
        if (e->gesture < ABANDERADO_POINT_NUM_FRAMES * ABANDERADO_POINT_PERIOD) e->gesture++;
        if (in_sight) {
            e->beam_mx = 0; // lose_sight_timer
        } else if (++e->beam_mx >= ABANDERADO_LOSE_SIGHT_FRAMES) {
            e->state = ENEMY_STATE_CHASE;
            e->gesture = 0;
            e->state_timer = 0;
            return;
        }
        if (--e->beam_len <= 0) { // summon_timer
            e->beam_len = ABANDERADO_SUMMON_FRAMES;
            if (count_live_monaguillos(enemies, num_enemies) < g_abanderado_max_mona) {
                int mx = (wx + px) >> 1;
                int my = (wy + py) >> 1;
                if (!position_is_free(TO_FIXED(mx), TO_FIXED(my))) {
                    mx = div32(wx + px * 2, 3);
                    my = div32(wy + py * 2, 3);
                }
                if (!position_is_free(TO_FIXED(mx), TO_FIXED(my))) {
                    mx = wx;
                    my = wy;
                }
                spawn_cream_puddle(enemies, num_enemies, mx, my);
            }
        }
        return;
    }

    // Patrol state (ENEMY_STATE_CHASE)
    e->state = ENEMY_STATE_CHASE;
    e->gesture = 0;
    if (in_sight) {
        e->state = ENEMY_STATE_POINT;
        e->gesture = 1;
        e->beam_mx = 0;
        if (e->beam_len <= 0 || e->beam_len > 30) e->beam_len = 30;
        e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
        return;
    }

    int band_top = s_view_valid ? s_view_t + ENEMY_AI_VIEW_MARGIN : py - 180;
    int band_bot = s_view_valid ? s_view_b - ENEMY_AI_VIEW_MARGIN : py + 80;
    if (e->state_timer <= 0 || e->aim_py < band_top || e->aim_py > band_bot) {
        pick_abanderado_patrol_target(e, px, py);
    } else {
        e->state_timer--;
    }

    int tdx = e->aim_px - wx;
    int tdy = e->aim_py - wy;
    uint32_t tdist = int_sqrt((uint32_t)(tdx * tdx + GROUND_DY2(tdy)));
    if (tdist <= 12) {
        e->state_timer = 0;
        update_animation(e, 0);
        return;
    }
    fixed spd = burn_slow(e, (wy > band_bot) ? (tuning->speed * 2) : tuning->speed);
    fixed vx = (fixed)div32(tdx * (int32_t)spd, (int32_t)tdist);
    fixed vy = (fixed)div32(tdy * (int32_t)spd, (int32_t)tdist);
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    if (!moved) e->state_timer = 0;
    e->dir = dir_from_vector(TO_FIXED(tdx), TO_FIXED(tdy));
    update_animation(e, moved);
}

// ---- Possession by the Súper Monja's aura (DESIGN-ARPG s5, "Aura de posesión") ---------------------------------
// The Exvoto (Monja de cera) and the Monaguillo awake inside the radius of a living Súper Monja turn into spiders: the
// transition clip (still, ~0.4 s), then the scuttling walk with haste (s_haste). Outside the radius (+ hysteresis) or
// without a Súper Monja they get up with the transition played backwards. They keep their own AI (the Exvoto walks and
// bites, never prays; the Monaguillo as ever). No extra Enemy fields: the phase is the clip in char_id (spider walk /
// transition), the transition's frame is `frame` and `kneel` (unused once awake) = 1 while it plays backwards (getting up).
static inline int possess_candidate(const Enemy *e) {
    if (!e->active) return 0;
    if (e->type == ENEMY_TYPE_EXVOTO) return (g_chars_loaded >> CG_ARANA_EXVOTO) & 1u;   // the spider forms are in the pool only
    if (e->type == ENEMY_TYPE_MONAGUILLO) return (g_chars_loaded >> CG_ARANA_MONA) & 1u; // in rooms with a Súper Monja
    return 0;
}
static inline int possess_walk_char(const Enemy *e) {
    return e->type == ENEMY_TYPE_MONAGUILLO ? CHAR_MONAGUILLO_ARANA_WALK : CHAR_EXVOTO_ARANA_WALK;
}
static inline int possess_trans_char(const Enemy *e) {
    return e->type == ENEMY_TYPE_MONAGUILLO ? CHAR_MONAGUILLO_ARANA_TRANS : CHAR_EXVOTO_ARANA_TRANS;
}
// 0 = normal, 1 = transition playing, 2 = spider walk.
static inline int possess_phase(const Enemy *e) {
    if (!possess_candidate(e)) return 0;
    if (e->char_id == possess_trans_char(e)) return 1;
    if (e->char_id == possess_walk_char(e)) return 2;
    return 0;
}
static inline int possess_awake(const Enemy *e) {
    return e->state == ENEMY_STATE_CHASE || e->state == ENEMY_STATE_ATTACK || e->state == ENEMY_STATE_WOBBLE;
}
static void possess_release(Enemy *e) {
    e->char_id = enemy_type_char_id(e->type);
    e->frame = 0;
    e->anim_timer = 0;
    e->kneel = 0;
}

// Once a frame, before the AI: starts, reverses and ends the possessions and marks the hasted ones (s_haste).
static void possession_update(Enemy *enemies, int num_enemies) {
    if (num_enemies > MAX_GAMEPLAY_ENEMIES) num_enemies = MAX_GAMEPLAY_ENEMIES;
#if !ENCOUNTERS_PROTO
    s_haste_base = enemies;
    memset(s_haste, 0, sizeof(s_haste));
#endif
    if (!(g_chars_loaded & ((1u << CG_ARANA_EXVOTO) | (1u << CG_ARANA_MONA)))) return;
    uint8_t monja[MAX_GAMEPLAY_ENEMIES];
    int nm = 0;
    for (int i = 0; i < num_enemies; i++) {
        const Enemy *m = &enemies[i];
        if (m->active && m->type == ENEMY_TYPE_MONJA && m->hp > 0 && !g_enemy_ally[i] &&
            m->state != ENEMY_STATE_DEAD && m->state != ENEMY_STATE_DORMANT && m->state != ENEMY_STATE_SUSPENDED &&
            m->state != ENEMY_STATE_REMATE)
            monja[nm++] = (uint8_t)i;
    }
    for (int i = 0; i < num_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!possess_candidate(e) || g_enemy_ally[i]) continue;
        const int ph = possess_phase(e);
        if (e->state == ENEMY_STATE_DEAD) continue;               // it dies in the form it had
        if (!possess_awake(e)) {                                  // praying, guarding, finisher, suspended...: back to normal at once
            if (ph) possess_release(e);
            continue;
        }
        if (e->state == ENEMY_STATE_WOBBLE) {                     // reeling (ready for the finisher): it stands up at once and
            if (ph) possess_release(e);                           // stays on its feet, so the finisher is its normal one;
            continue;                                             // no spider again until the reel ends
        }
        int d2 = 0x7FFFFFFF;
        for (int k = 0; k < nm; k++) {
            const int dx = TO_INT(e->x - enemies[monja[k]].x);
            const int dy = TO_INT(e->y - enemies[monja[k]].y);
            const int q = dx * dx + GROUND_DY2(dy);
            if (q < d2) d2 = q;
        }
        const int in = d2 <= ARPG_SMONJA_POSSESS_RADIUS * ARPG_SMONJA_POSSESS_RADIUS;
        const int out = d2 > (ARPG_SMONJA_POSSESS_RADIUS + ARPG_SMONJA_POSSESS_HYST) * (ARPG_SMONJA_POSSESS_RADIUS + ARPG_SMONJA_POSSESS_HYST);
        if (ph == 0) {
            if (in && e->char_id == enemy_type_char_id(e->type)) {   // lie down
                e->char_id = possess_trans_char(e);
                e->frame = 0; e->anim_timer = 0; e->kneel = 0;
            }
        } else if (ph == 2) {
            if (out) {                                              // get up: the transition backwards from its last frame
                e->char_id = possess_trans_char(e);
                e->frame = PLAYER_NUM_FRAMES - 1; e->anim_timer = 0; e->kneel = 1;
            } else {
                s_haste[i] = 1;
            }
        } else {                                                    // mid-transition: change of mind, same frame
            if (!e->kneel && out) e->kneel = 1;
            else if (e->kneel && in) e->kneel = 0;
        }
    }
}

// One frame of the transition clip, still (forwards = lying down, backwards = getting up). Returns 1 while it plays.
static int possession_step(Enemy *e) {
    if (e->state == ENEMY_STATE_WOBBLE) return 0;                // reeling: update_exvoto counts it down; the frame holds
    int period = g_characters[e->char_id].anim_period;
    if (period <= 0) period = 3;
    if (++e->anim_timer < period) return 1;
    e->anim_timer = 0;
    if (e->kneel) {
        if (e->frame > 0) e->frame--;
        else possess_release(e);                                 // up again: the normal walk
    } else if (e->frame < PLAYER_NUM_FRAMES - 1) {
        e->frame++;
    } else {
        e->char_id = possess_walk_char(e);                       // spider: the scuttling walk
        e->frame = 0;
    }
    return 1;
}
// ---------------------------------------------------------------------------
// El Campanero de Animas (jefe ARPG, DESIGN-ARPG.md 9). One instance. Its clocks live in fields no other type uses here:
//   beam_len = minor-toll clock, state_timer = major-toll clock (start to start), beam_mx = telegraph left,
//   gesture = second toll pending (phase II), beam_my = window left (cannot move or toll).
// The rings themselves (growth, shadows, glyph silencing, sounds) belong to campanero_fx.c.
// ---------------------------------------------------------------------------
#if ENCOUNTERS_PROTO
#define CAMP_TANIDO_FRAMES 60       // [TUNABLE-PLACEHOLDER] minor toll every second, all phases
#define CAMP_TELEGRAPH_FRAMES 36    // [TUNABLE-PLACEHOLDER] the bell is lifted (0.6 s)
#define CAMP_WINDOW_FRAMES 60       // [TUNABLE-PLACEHOLDER] after a major toll he cannot move or toll for 1 s
#define CAMP_DOUBLE_GAP 30          // [TUNABLE-PLACEHOLDER] phase II: second toll this long after the first
#define CAMP_EXVOTOS_PER_TOQUE 2
#define CAMP_EXVOTO_CAP 6
#define CAMP_CONTACT_R 14           // ground px
static const uint16_t s_camp_period[3] = { 210, 240, 180 };    // major toll start to start: 3.5 s, 4.0 s, 3.0 s

volatile struct {                   // read by scenarios (symbol g_campanero_dbg)
    uint16_t toques, tanidos, hero_hits, raised;
    uint8_t phase, telegraph, window, pad;
    uint16_t ring_frames;           // frames the major ring's front was on the hero (hit or not: i-frames can hide the hit)
} g_campanero_dbg;

static void camp_raise_exvotos(Enemy *boss, Enemy *enemies, int num_enemies) {
    CP_BEGIN(CP_RAISE);
    int live = 0;
    for (int i = 0; i < num_enemies; i++)
        if (enemies[i].active && enemies[i].hp > 0 && enemies[i].type == ENEMY_TYPE_EXVOTO) live++;
    for (int k = 0; k < CAMP_EXVOTOS_PER_TOQUE && live < CAMP_EXVOTO_CAP; k++) {
        int sx = 0, sy = 0, ok = 0;
        CP_BEGIN(CP_SPOT);
        for (int attempt = 0; attempt < 6 && !ok; attempt++) {      // beside a column or at a random floor spot
            enc_camp_spot(rng_next(), &sx, &sy);
            ok = position_is_free(TO_FIXED(sx), TO_FIXED(sy));
        }
        CP_END(CP_SPOT);
        if (!ok) continue;
        int slot = -1;
        for (int i = 0; i < num_enemies; i++) if (!enemies[i].active) { slot = i; break; }
        if (slot < 0) { CP_END(CP_RAISE); return; }
        Enemy *x = &enemies[slot];
        memset(x, 0, sizeof(*x));
        x->x = TO_FIXED(sx);
        x->y = TO_FIXED(sy);
        x->type = ENEMY_TYPE_EXVOTO;
        x->char_id = CHAR_EXVOTO;
        x->max_hp = g_enemy_tuning[ENEMY_TYPE_EXVOTO].max_hp;
        x->hp = x->max_hp;
        x->dir = DIR_SOUTH;
        x->active = 1;
        x->state = ENEMY_STATE_EMERGE;                 // rises from the floor: still and untouchable for half a second
        x->state_timer = MONAGUILLO_EMERGE_FRAMES;
        x->strafe_dir = (rng_next() & 1u) ? 1 : -1;
        x->pack = boss->pack;                          // dies with the boss
        live++;
        g_campanero_dbg.raised++;
        cfx_sfx_later(SND_MONAGUILLO_EMERGE, sx, 4 + 3 * k);          // spaced from the toll's own sounds (campanero_fx.c)
    }
    CP_END(CP_RAISE);
}

static void camp_toque(Enemy *e, Enemy *enemies, int num_enemies) {
    cfx_emit(CFX_TOQUE, TO_INT(e->x), TO_INT(e->y));
    g_campanero_dbg.toques++;
    camp_raise_exvotos(e, enemies, num_enemies);
}

static void update_campanero(Enemy *e, Enemy *enemies, int num_enemies, int idx, fixed player_x, fixed player_y) {
    const int ph = boss_phase();
    g_campanero_dbg.phase = (uint8_t)ph;
    if (g_player_state.is_dead) { update_animation(e, 0); return; }
    const int wx = TO_INT(e->x), wy = TO_INT(e->y);
    const int px = TO_INT(player_x), py = TO_INT(player_y);
    const int dx = px - wx, dy = py - wy;
    const int dist_sq = dx * dx + GROUND_DY2(dy);

    // The major toll's front hurts the hero (through the normal path: i-frames respected).
    if (cfx_toque_hit(px, py)) {
        g_campanero_dbg.ring_frames++;
        if (player_take_damage(&g_player_state, ARPG_DMG_CAMPANERO_TOQUE)) g_campanero_dbg.hero_hits++;
    }
    // Contact (the bell and the man).
    if (dist_sq <= CAMP_CONTACT_R * CAMP_CONTACT_R) player_take_damage(&g_player_state, arpg_enemy_damage_of(e));

    // Minor toll: always, every second, whatever he is doing.
    if (++e->beam_len >= CAMP_TANIDO_FRAMES) {
        e->beam_len = 0;
        cfx_emit(CFX_TANIDO, wx, wy);
        g_campanero_dbg.tanidos++;
    }

    int moved = 0;
    if (e->state_timer < 30000) e->state_timer++;
    if (e->beam_mx > 0) {                                   // the bell goes up
        if (--e->beam_mx == 0) {
            camp_toque(e, enemies, num_enemies);
            if (ph == 2) e->gesture = CAMP_DOUBLE_GAP; else e->beam_my = CAMP_WINDOW_FRAMES;
        }
    } else if (e->gesture > 0) {                            // phase II: the second toll
        if (--e->gesture == 0) {
            camp_toque(e, enemies, num_enemies);
            e->beam_my = CAMP_WINDOW_FRAMES;
        }
    } else if (e->beam_my > 0) {                            // the bell still hums: he cannot move or toll
        e->beam_my--;
    } else if (e->state_timer >= s_camp_period[ph >= 1 && ph <= 3 ? ph - 1 : 0]) {
        e->state_timer = 0;
        e->beam_mx = CAMP_TELEGRAPH_FRAMES;
        sfx_play(SND_CFX_LIFT, wx);                          // lab_creak: the bell is lifted
    } else if (ph >= 3) {                                   // phase III: he walks to the hero dragging the bell
        if (dist_sq > CAMP_CONTACT_R * CAMP_CONTACT_R) {
            const fixed x0 = e->x, y0 = e->y;
            chase_step(e, enemies, num_enemies, idx, g_enemy_tuning[ENEMY_TYPE_EXVOTO].speed, wx, wy, px, py, dist_sq);
            moved = (e->x != x0 || e->y != y0);
        }
    }
    e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
    {   // Clip and frame (source/campanero_sprite.c): the raise is the telegraph, the strike opens the window
        int clip, fr;
        if (e->beam_mx > 0) {
            clip = CAMP_CLIP_TOQUE; fr = ((CAMP_TELEGRAPH_FRAMES - e->beam_mx) * 6) / CAMP_TELEGRAPH_FRAMES;
        } else if (e->gesture > 0) {                        // phase II: strike, then raise again for the second toll
            clip = CAMP_CLIP_TOQUE;
            fr = e->gesture > CAMP_DOUBLE_GAP - 4 ? 6 : ((CAMP_DOUBLE_GAP - e->gesture) * 6) / CAMP_DOUBLE_GAP;
        } else if (e->beam_my > 0) {
            clip = CAMP_CLIP_TOQUE; fr = (CAMP_WINDOW_FRAMES - e->beam_my) < 4 ? 6 : 7;
        } else if (e->beam_len < 16) {                      // minor toll: the bell swings for 16 frames
            clip = CAMP_CLIP_TANIDO; fr = e->beam_len >> 1;
        } else if (moved) {
            clip = CAMP_CLIP_WALK; fr = (int)((s_ai_tick / 6u) & 7u);
        } else {
            clip = CAMP_CLIP_IDLE; fr = (int)((s_ai_tick / 8u) & 7u);
        }
        e->kneel = (uint8_t)clip;
        e->frame = (uint8_t)fr;
    }
    g_campanero_dbg.telegraph = (uint8_t)e->beam_mx;
    g_campanero_dbg.window = (uint8_t)e->beam_my;
}
#endif  // ENCOUNTERS_PROTO

ITCM_CODE void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y) {
    if (!enemies || num_enemies <= 0) return;

    s_ai_tick++;
#if ENCOUNTERS_PROTO
    haste_refresh(enemies, num_enemies);
#endif
    possession_update(enemies, num_enemies);
    s_post_fixed = 0;
    for (int i = 0; i < num_enemies; i++)
        if (enemies[i].active && enemies[i].hp > 0 && enemies[i].type == ENEMY_TYPE_CAMPANERO) { s_post_fixed = 1; break; }
    hero_velocity_update(TO_INT(player_x), TO_INT(player_y));
    enemy_puddles_update();
    if (!s_sep_ready) sep_init_table();
    sep_build_grid(enemies, num_enemies);

    for (int i = 0; i < num_enemies; i++) {
        Enemy *e = &enemies[i];
        if (g_enemy_ally[i]) continue;                                   // ARPG: allies walk and fight in allies_update (allies.c)
        if (!e->active || e->state == ENEMY_STATE_SUSPENDED) continue;   // Viatico: inert until enemy_suspend_update ends it

        if (e->hit_timer > 0) e->hit_timer--;
        if (e->state == ENEMY_STATE_REMATE) continue;       // the finisher animation owns it (remate.c)

        // Staggered by a ray hit: shoved along the blast, no AI until it recovers.
        if (e->stun_timer > 0) {
            if (e->type == ENEMY_TYPE_SHOOTER &&
                (e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK ||
                 e->state == ENEMY_STATE_SENTENCE)) {
                e->state = ENEMY_STATE_CHASE;        // a shove breaks the aim (and annuls a pending sentence)
                e->state_timer = 0;
                e->gesture = 0;
            } else if (e->type == ENEMY_TYPE_CHARGER &&
                       (e->state == ENEMY_STATE_TELEGRAPH || e->state == ENEMY_STATE_CHARGE)) {
                e->state = ENEMY_STATE_STUNNED;      // interrupted lunge: dazed after the stagger
                e->state_timer = CHARGER_STUN_HIT_FRAMES;
            }
            if (e->type == ENEMY_TYPE_EXVOTO && e->state == ENEMY_STATE_PRAY && !(e->home_flags & ENEMY_HOME_GUARD))
                exvoto_wake_chain(enemies, num_enemies, i);   // hurt but alive: it wakes (and the others with it)
            e->stun_timer--;
            move_with_slide(&e->x, &e->y, e->knock_vx, e->knock_vy);
            e->knock_vx = (e->knock_vx * 224) >> 8;
            e->knock_vy = (e->knock_vy * 224) >> 8;
            continue;
        }

        if (g_sandbox_freeze_ai) continue;                 // sandbox: stand still, no move and no attack
#if ARPG_REMATE_TEST
        if (possess_phase(e) == 1 && possession_step(e)) continue;   // remate room: frozen, but the possessed still lie down
        continue;                                          // no walking, no attack, no guard, no dodge: they only reel from hits
#endif
#if SOUND_TEST
        if (sound_test_freeze()) continue;                 // prueba-sonidos: scenes 1, 2 and 5 hold their enemies still (they only reel from hits)
#endif
#if ARPG_BOXEO
        if (g_lab_saco_still) continue;                    // boxeo: the dummy only reels from hits
#endif

        if (e->state == ENEMY_STATE_DORMANT) continue;     // asleep: encounters.c wakes the whole pack
        if (e->state == ENEMY_STATE_GUARD) {               // garrison: holds its post until released
#if ENCOUNTERS_PROTO
            if (e->type == ENEMY_TYPE_MONJA) {             // the Monja tier prays (and heals) instead of just watching
                update_monja(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_MONJA]);
                continue;
            }
#endif
            update_guard(e, enemies, num_enemies, i, player_x, player_y);
            continue;
        }

        // Possessed and lying down (or getting up): still, no AI, no bite until the transition ends.
        if (possess_phase(e) == 1 && possession_step(e)) continue;

        // Level of detail: off-screen enemies that are only walking (CHASE / POSITION) think every 2nd frame,
        // staggered by index, and cover twice the distance on that frame.
        s_lod_mult = 1;
        s_offscreen = 0;
        if (s_view_valid) {
            int wx = TO_INT(e->x);
            int wy = TO_INT(e->y);
            s_offscreen = wx < s_view_l || wx >= s_view_r || wy < s_view_t || wy >= s_view_b;
            if (s_offscreen && (e->state == ENEMY_STATE_CHASE || e->state == ENEMY_STATE_POSITION)) {
                if ((s_ai_tick + (uint32_t)i) & 1) continue;
                s_lod_mult = 2;
            }
        }

        if (e->type == ENEMY_TYPE_EXVOTO) {
            update_exvoto(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_EXVOTO]);
        } else if (e->type == ENEMY_TYPE_MONAGUILLO) {
            update_exvoto(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_MONAGUILLO]);
#if ENCOUNTERS_PROTO
        } else if (e->type == ENEMY_TYPE_BEBE) {
            update_exvoto(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_BEBE]);
        } else if (e->type == ENEMY_TYPE_PARROCO) {
            update_exvoto(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_PARROCO]);
        } else if (e->type == ENEMY_TYPE_MONJA) {
            update_monja(e, enemies, num_enemies, i, player_x, player_y, &g_enemy_tuning[ENEMY_TYPE_MONJA]);
#endif
        } else if (e->type == ENEMY_TYPE_CAMPANERO) {
#if ENCOUNTERS_PROTO
            { CP_BEGIN(CP_CAMP);
            update_campanero(e, enemies, num_enemies, i, player_x, player_y);
            CP_END(CP_CAMP); }
#endif
        } else if (e->type == ENEMY_TYPE_ABANDERADO) {
            update_abanderado(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_CHARGER) {
            update_charger(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_SHOOTER) {
            update_shooter(e, enemies, num_enemies, i, player_x, player_y);
        }
    }
    s_lod_mult = 1;
}
