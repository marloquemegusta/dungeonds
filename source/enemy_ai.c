#include "enemy_ai.h"
#include "horde.h"
#include "enemy_laser.h"
#include "los.h"
#include "navfield.h"
#include "player_sprite.h"
#include "sandbox.h"
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
        if (!enemies[i].active) continue;
        int c = sep_cell(TO_INT(enemies[i].x) >> SEP_CELL_SHIFT, TO_INT(enemies[i].y) >> SEP_CELL_SHIFT);
        s_grid_next[i] = s_grid_head[c];
        s_grid_head[c] = (uint8_t)i;
    }
}

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
static void chase_step(Enemy *e, Enemy *enemies, int num_enemies, int idx, fixed speed,
                       int wx, int wy, int px, int py, int ground_dist_sq) {
    int target_x = px, target_y = py;
    int direct = (e->has_los & VIEW_DIRECT) && ground_dist_sq <= CHASE_DIRECT_RANGE * CHASE_DIRECT_RANGE;
    if (!direct) {
        int step_x, step_y;
        if (nav_next_step(wx, wy, &step_x, &step_y)) {
            target_x = step_x;
            target_y = step_y;
        }
    }

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

// Skeleton (DESIGN.md 6.9.1): the 0.3 charger AI, relentless melee pressure, no telegraph. FSM:
// CHASE -> ATTACK(cooldown) -> CHASE; * -> DEAD. Always active; no detection states.
static void update_skeleton(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                            fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_SKELETON];

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
        case ENEMY_STATE_ATTACK: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            if (--e->state_timer <= 0) e->state = ENEMY_STATE_CHASE;
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;

            // Bite when in melee range and nothing solid is in between.
            int melee_range = tuning->preferred_dist_max;
            if (ground_dist_sq <= melee_range * melee_range &&
                los_has_line_of_sight(wx, wy, px, py, 0) && line_is_walkable(wx, wy, px, py)) {
                player_take_hit(&g_player_state);
                e->state = ENEMY_STATE_ATTACK;
                e->state_timer = tuning->attack_cooldown;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                update_animation(e, 0);
                break;
            }

            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, CHASE_DIRECT_RANGE);
            chase_step(e, enemies, num_enemies, idx, tuning->speed, wx, wy, px, py, ground_dist_sq);
            break;
        }
    }
}

// Charger (DESIGN.md 6.9.1): lunge and dodge. FSM CHASE (slow approach) -> TELEGRAPH (still, blinks,
// locks the direction) -> CHARGE (straight line) -> RECOVER (still, vulnerable) -> CHASE.
// A wall or column in the way of the charge, or a shotgun hit during TELEGRAPH / CHARGE, leaves it STUNNED.
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
        case ENEMY_STATE_TELEGRAPH: {
            // 3-stage progressive crouch (walk[0] -> telegraph -> charge[0]) without blinking.
            e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
            int elapsed = tuning->telegraph_duration - e->state_timer;
            e->frame = (elapsed < 6) ? 0 : (elapsed < 20) ? 1 : 2;
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHARGE;
                e->state_timer = CHARGER_CHARGE_FRAMES;
                e->charge_hit = 0;
                e->frame = 0;
                e->anim_timer = 0;
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
                update_animation(e, 0);
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
                    player_take_hit(&g_player_state);          // one hit per charge; i-frames may absorb it
                    e->charge_hit = 1;
                }
            }
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_RECOVER;
                e->state_timer = CHARGER_RECOVER_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_RECOVER:
        case ENEMY_STATE_STUNNED: {
            update_animation(e, 0);
            if (--e->state_timer <= 0) e->state = ENEMY_STATE_CHASE;
            break;
        }

        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;
            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, CHARGER_ENGAGE_DIST);
            if ((e->has_los & VIEW_ENGAGE) && ground_dist_sq <= CHARGER_ENGAGE_DIST * CHARGER_ENGAGE_DIST &&
                aim_vector(wx, wy, px, py, &e->aim_dir_x, &e->aim_dir_y)) {
                e->state = ENEMY_STATE_TELEGRAPH;
                e->state_timer = tuning->telegraph_duration;
                e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
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
// Ojo del Tribunal (DESIGN.md 6.10, "Mirada colimada"), ENEMY_TYPE_SHOOTER. FSM
// CHASE (search) -> TRACK (40 frames: the band from the lantern follows the hero and narrows, the held head
// charges) -> LOCK (20 frames: the line is frozen where the hero was) -> SENTENCE (the head fires the beam
// from its mouth along the locked line, one hit) -> COOLDOWN -> CHASE.
// A wall or column cuts the sight and the beam (los_has_line_of_sight / ojo_ray_wall_dist). The rhythm is the
// old sniper's (aim, fix, fire); the hero is safe by leaving the line before SENTENCE or hiding behind a column.
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

// Fires the sentence: the beam leaves the mouth along the line to the locked point (ground metric), is cut at
// the first wall or column and hurts the hero once if he is on it (player_take_hit respects the i-frames).
static void ojo_fire(Enemy *e, fixed player_x, fixed player_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    int mxi = TO_INT(mx), myi = TO_INT(my);
    // Drawn direction: screen metric from the mouth to the locked chest point (as the old beam).
    int ax = e->aim_px - mxi;
    int ay = e->aim_py - myi + mh - OJO_TARGET_HEIGHT;
    int slen = (int)int_sqrt((uint32_t)(ax * ax + GROUND_DY2(ay)));
    if (slen < 1) { ax = 1; ay = 0; slen = 1; }
    e->aim_dir_x = div32(ax * 256, slen);
    e->aim_dir_y = div32(ay * 256, slen);
    // Hit line: true ground metric from the mouth to the locked point.
    int gx = e->aim_px - mxi;
    int gy2 = 2 * (e->aim_py - myi);
    int glen = (int)int_sqrt((uint32_t)(gx * gx + gy2 * gy2));
    if (glen < 1) { gx = 1; gy2 = 0; glen = 1; }
    int ux = div32(gx * 256, glen);                  // unit vector 8.8
    int uy = div32(gy2 * 256, glen);
    int cut = ojo_ray_wall_dist(mxi, myi, ux << 7, uy << 7, OJO_BEAM_MAX_LEN);
    e->beam_len = cut;
    int rx = TO_INT(player_x) - mxi;
    int ry2 = 2 * (TO_INT(player_y) - myi);
    int along = (rx * ux + ry2 * uy) >> 8;
    int cross = (rx * uy - ry2 * ux) >> 8;
    if (cross < 0) cross = -cross;
    if (along >= 0 && along <= cut && cross <= OJO_HIT_HALF_WIDTH) player_take_hit(&g_player_state);
}

// Advances the sentence gesture (SENTENCE and the start of COOLDOWN); 0 once it has played out.
static void ojo_gesture_tick(Enemy *e) {
    if (e->gesture <= 0) return;
    e->gesture++;
    if (e->gesture > OJO_GESTURE_FRAMES) e->gesture = 0;
}

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
            // Direction and point frozen: the dodge window.
            ojo_look_anim(e);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_SENTENCE;
                e->state_timer = OJO_BEAM_FRAMES;
                e->frame = 0;
                e->gesture = 1;
                ojo_fire(e, player_x, player_y);
            }
            break;
        }

        case ENEMY_STATE_SENTENCE: {
            ojo_gesture_tick(e);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_COOLDOWN;
                e->state_timer = tuning->attack_cooldown;
            }
            break;
        }

        case ENEMY_STATE_COOLDOWN: {
            update_animation(e, 0);
            ojo_gesture_tick(e);
            if (--e->state_timer <= 0) e->state = ENEMY_STATE_CHASE;
            break;
        }

        case ENEMY_STATE_POSITION:      // waiting for a free aiming slot
        case ENEMY_STATE_CHASE:
        default: {
            e->state = ENEMY_STATE_CHASE;
            e->gesture = 0;
            refresh_view(e, idx, wx, wy, px, py, ground_dist_sq, OJO_SIGHT_RANGE);   // walking flags (direct run)
            if (((s_ai_tick + idx) & 3) == 0 && ground_dist <= OJO_SIGHT_RANGE &&
                los_has_line_of_sight(wx, wy, px, py, 0))
                e->has_los |= VIEW_SIGHT;                                             // same cadence as the refresh above
            int sight = (e->has_los & VIEW_SIGHT) && ground_dist <= OJO_SIGHT_RANGE;
            // Far above the player in the strip it keeps walking instead of aiming (the horde keeps them near).
            int may_look = !(s_strip_mode && wy < py - HORDE_SHOOTER_TOP_LIMIT_PX);
            if (sight && may_look && ojos_looking(enemies, num_enemies) < OJO_MAX_LOOKING) {
                e->state = ENEMY_STATE_TRACK;
                e->state_timer = OJO_TRACK_FRAMES;
                e->frame = 0;
                e->anim_timer = 0;
                e->aim_px = px;
                e->aim_py = py;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
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

ITCM_CODE void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y) {
    if (!enemies || num_enemies <= 0) return;

    s_ai_tick++;
    if (!s_sep_ready) sep_init_table();
    sep_build_grid(enemies, num_enemies);

    for (int i = 0; i < num_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;

        if (e->hit_timer > 0) e->hit_timer--;

        // Staggered by a shotgun hit: shoved along the blast, no AI until it recovers.
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
            e->stun_timer--;
            move_with_slide(&e->x, &e->y, e->knock_vx, e->knock_vy);
            e->knock_vx = (e->knock_vx * 224) >> 8;
            e->knock_vy = (e->knock_vy * 224) >> 8;
            continue;
        }

        if (g_sandbox_freeze_ai) continue;                 // sandbox: stand still, no move and no attack

        if (e->state == ENEMY_STATE_DORMANT) continue;     // asleep: encounters.c wakes the whole pack

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

        if (e->type == ENEMY_TYPE_SKELETON) {
            update_skeleton(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_CHARGER) {
            update_charger(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_SHOOTER) {
            update_shooter(e, enemies, num_enemies, i, player_x, player_y);
        }
    }
    s_lod_mult = 1;
}
