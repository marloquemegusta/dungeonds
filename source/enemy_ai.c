#include "enemy_ai.h"
#include "horde.h"
#include "los.h"
#include "navfield.h"
#include "player_sprite.h"
#include "sandbox.h"
#include <string.h>

static uint32_t s_ai_tick = 0;
static int s_strip_mode;

void enemy_ai_set_strip_mode(int enabled) { s_strip_mode = enabled != 0; }

static inline uint32_t int_sqrt(uint32_t n) {
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

static int move_with_slide(fixed *x, fixed *y, fixed vx, fixed vy) {
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

static void apply_separation(Enemy *enemies, int num_enemies, int current_idx, fixed *vx, fixed *vy) {
    Enemy *e = &enemies[current_idx];
    fixed rep_vx = 0;
    fixed rep_vy = 0;

    for (int j = 0; j < num_enemies; j++) {
        if (j == current_idx || !enemies[j].active) continue;
        int32_t edx = TO_INT(e->x - enemies[j].x);
        int32_t edy = TO_INT(e->y - enemies[j].y);
        int32_t d2 = edx * edx + edy * edy;

        // Separation radius: 16 pixels (256 sq px)
        if (d2 > 0 && d2 < 256) {
            uint32_t d = int_sqrt((uint32_t)d2);
            if (d > 0) {
                // Repel with 0.5 px/frame impulse
                rep_vx += (fixed)((edx * 128) / (int32_t)d);
                rep_vy += (fixed)((edy * 128) / (int32_t)d);
            }
        }
    }

    *vx += rep_vx;
    *vy += rep_vy;
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

#define VIEW_BULLET 1                 // e->has_los bits: a bullet can fly from here to the player
#define VIEW_WALKABLE 2               //                  a body can walk it
#define VIEW_DIRECT 4                 //                  close, in view and walkable: run straight at the player
#define VIEW_ENGAGE 8                 //                  charger: within CHARGER_ENGAGE_DIST, in view and walkable

#define CHASE_DIRECT_RANGE 48         // ground px: closer than this (with a clear view) it runs straight at the player

// Unit direction (8.8, ground metric) from (ox, oy) to (tx, ty), same convention as the player's
// weapons: dir_x^2 + (2 dir_y)^2 = 256^2. Returns 0 (leaving *dx, *dy) when both points coincide.
static int aim_vector(int ox, int oy, int tx, int ty, int *dx, int *dy) {
    int ax = tx - ox;
    int ay = ty - oy;
    int len = (int)int_sqrt((uint32_t)(ax * ax + GROUND_DY2(ay)));
    if (len < 1) return 0;
    *dx = (ax * 256) / len;
    *dy = (ay * 256) / len;
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
        vx = (fixed)((t_dx * (int32_t)speed) / (int32_t)t_dist);
        vy = (fixed)((t_dy * (int32_t)speed) / (int32_t)t_dist);
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
            // Standing still; the renderer blinks the sprite. The direction was locked on entry.
            e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
            update_animation(e, 0);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHARGE;
                e->state_timer = CHARGER_CHARGE_FRAMES;
                e->charge_hit = 0;
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
                update_animation(e, 0);
                break;
            }
            chase_step(e, enemies, num_enemies, idx, tuning->speed, wx, wy, px, py, ground_dist_sq);
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Necron shooter (DESIGN.md 6.9.1): zone control with a laser the player must leave. FSM
// POSITION -> LASER_AIM (line follows) -> LASER_FIX (locked, wider) -> LASER_FIRE -> COOLDOWN -> POSITION.
// ---------------------------------------------------------------------------

#define SHOOTER_FIRE_MARGIN 24        // ground px beyond the band's far edge from which it already charges

void enemy_muzzle(const Enemy *e, fixed *mx, fixed *my, int *mh) {
    const int8_t *m = g_character_muzzle[e->char_id][e->dir][e->frame];
    *mx = e->x + TO_FIXED(m[0]);
    *my = e->y + TO_FIXED(m[1]);
    *mh = m[2];
}

// Walks the distance band: back off when the player is too close, close in (straight if the
// body can walk it, else down the navigation field) when too far or out of view, and strafe
// sideways in between. Used while positioning and while cooling down.
static void shooter_reposition(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                               int px, int py, int ground_dist) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_SHOOTER];
    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int dx = px - wx;
    int dy = py - wy;
    int move_x, move_y;
    int strafing = 0;

    if (ground_dist < tuning->preferred_dist_min) {
        move_x = -dx;
        move_y = -dy;
    } else if (ground_dist > tuning->preferred_dist_max || !(e->has_los & VIEW_BULLET)) {
        move_x = dx;
        move_y = dy;
        if (!(e->has_los & VIEW_WALKABLE)) {
            int step_x, step_y;
            if (nav_next_step(wx, wy, &step_x, &step_y)) {
                move_x = step_x - wx;
                move_y = step_y - wy;
            }
        }
    } else {
        // Sideways on the ground: perpendicular to (dx, 2*dy), which is (-2*dy, dx/2) on screen.
        if (e->strafe_dir == 0) e->strafe_dir = 1;
        move_x = -2 * dy * e->strafe_dir;
        move_y = (dx * e->strafe_dir) / 2;
        strafing = 1;
    }

    uint32_t m_dist = int_sqrt((uint32_t)(move_x * move_x + GROUND_DY2(move_y)));
    fixed vx = 0, vy = 0;
    if (m_dist > 0) {
        vx = (fixed)((move_x * (int32_t)tuning->speed) / (int32_t)m_dist);
        vy = (fixed)((move_y * (int32_t)tuning->speed) / (int32_t)m_dist);
    }
    apply_separation(enemies, num_enemies, idx, &vx, &vy);
    int moved = move_with_slide(&e->x, &e->y, vx, vy);
    if (strafing && !moved) e->strafe_dir = -e->strafe_dir;

    // Face the player while aiming-ready (backing off or strafing); face the way it walks when
    // it is closing in or going around a wall, so it does not slide sideways looking at the player.
    if (moved && !strafing && ground_dist >= tuning->preferred_dist_min)
        e->dir = dir_from_vector(TO_FIXED(move_x), TO_FIXED(move_y));
    else
        e->dir = dir_from_vector(px - e->x, py - e->y);
    update_animation(e, moved);
}

// Points the laser from the muzzle at the player's feet; keeps the old line when they coincide.
static void shooter_aim(Enemy *e, fixed player_x, fixed player_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    aim_vector(TO_INT(mx), TO_INT(my), TO_INT(player_x), TO_INT(player_y), &e->aim_dir_x, &e->aim_dir_y);
}

// 1 when the player stands in the beam: ahead of the muzzle, within SHOOTER_LASER_LENGTH along the line
// and SHOOTER_LASER_HALF_WIDTH across it (ground metric). Columns do not stop it.
static int laser_covers(const Enemy *e, fixed player_x, fixed player_y) {
    fixed mx, my;
    int mh;
    enemy_muzzle(e, &mx, &my, &mh);
    int dx = TO_INT(player_x - mx);
    int dy = TO_INT(player_y - my);
    int along = (dx * e->aim_dir_x + 4 * dy * e->aim_dir_y) >> 8;
    int across = (2 * (dy * e->aim_dir_x - dx * e->aim_dir_y)) >> 8;
    if (across < 0) across = -across;
    return along >= 0 && along <= SHOOTER_LASER_LENGTH && across <= SHOOTER_LASER_HALF_WIDTH;
}

static int lasers_charging(const Enemy *enemies, int num_enemies) {
    int n = 0;
    for (int i = 0; i < num_enemies; i++) {
        if (enemies[i].active && (enemies[i].state == ENEMY_STATE_LASER_AIM || enemies[i].state == ENEMY_STATE_LASER_FIX))
            n++;
    }
    return n;
}

static void update_shooter(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                           fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_SHOOTER];

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
    int ground_dist = (int)int_sqrt((uint32_t)(dx * dx + GROUND_DY2(dy)));
    if (((s_ai_tick + idx) & 3) == 0) {
        e->has_los = (bullet_line_is_free(wx, wy, px, py) ? VIEW_BULLET : 0) |
                     (line_is_walkable(wx, wy, px, py) ? VIEW_WALKABLE : 0);
    }
    if (s_strip_mode && wy < py - HORDE_SHOOTER_TOP_LIMIT_PX) {
        e->state = ENEMY_STATE_POSITION;
        e->state_timer = 0;
        shooter_reposition(e, enemies, num_enemies, idx, px, py, ground_dist);
        return;
    }

    switch (e->state) {
        case ENEMY_STATE_LASER_AIM: {
            // Thin line that follows the player; the shooter stands still.
            // The muzzle moves with the facing, so aim, face the line, then aim again from the new muzzle:
            // the beam origin (fixed from now on) and the locked direction then agree.
            shooter_aim(e, player_x, player_y);
            e->dir = dir_from_vector(TO_FIXED(e->aim_dir_x), TO_FIXED(e->aim_dir_y));
            shooter_aim(e, player_x, player_y);
            update_animation(e, 0);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_LASER_FIX;
                e->state_timer = SHOOTER_LASER_FIX_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_LASER_FIX: {
            // Locked and wider: the player has to leave the line. The facing stays, so the muzzle stays.
            update_animation(e, 0);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_LASER_FIRE;
                e->state_timer = SHOOTER_LASER_FIRE_FRAMES;
            }
            break;
        }

        case ENEMY_STATE_LASER_FIRE: {
            update_animation(e, 0);
            if (laser_covers(e, player_x, player_y)) player_take_hit(&g_player_state);   // i-frames absorb repeats
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_COOLDOWN;
                e->state_timer = tuning->attack_cooldown;
            }
            break;
        }

        case ENEMY_STATE_COOLDOWN: {
            shooter_reposition(e, enemies, num_enemies, idx, px, py, ground_dist);
            if (--e->state_timer <= 0) {
                e->state = ENEMY_STATE_POSITION;
                e->state_timer = 0;
            }
            break;
        }

        case ENEMY_STATE_POSITION:
        default: {
            e->state = ENEMY_STATE_POSITION;
            shooter_reposition(e, enemies, num_enemies, idx, px, py, ground_dist);
            e->state_timer++;
            // Charge the laser once it has settled, has a clear line, is not out of reach and a laser
            // slot is free (otherwise it keeps waiting in its band).
            if (e->state_timer >= tuning->position_duration && (e->has_los & VIEW_BULLET) &&
                ground_dist <= tuning->preferred_dist_max + SHOOTER_FIRE_MARGIN &&
                lasers_charging(enemies, num_enemies) < SHOOTER_MAX_CHARGING) {
                e->state = ENEMY_STATE_LASER_AIM;
                e->state_timer = SHOOTER_LASER_TRACK_FRAMES;
                e->frame = 0;                        // standing pose, so the beam leaves the muzzle
                e->anim_timer = 0;
                shooter_aim(e, player_x, player_y);
            }
            break;
        }
    }
}

void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y) {
    if (!enemies || num_enemies <= 0) return;

    s_ai_tick++;

    for (int i = 0; i < num_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;

        if (e->hit_timer > 0) e->hit_timer--;

        // Staggered by a shotgun hit: shoved along the blast, no AI until it recovers.
        if (e->stun_timer > 0) {
            if (e->type == ENEMY_TYPE_SHOOTER &&
                (e->state == ENEMY_STATE_LASER_AIM || e->state == ENEMY_STATE_LASER_FIX ||
                 e->state == ENEMY_STATE_LASER_FIRE)) {
                e->state = ENEMY_STATE_POSITION;     // a shove spoils the shot
                e->state_timer = 0;
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

        if (e->type == ENEMY_TYPE_SKELETON) {
            update_skeleton(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_CHARGER) {
            update_charger(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_SHOOTER) {
            update_shooter(e, enemies, num_enemies, i, player_x, player_y);
        }
    }
}
