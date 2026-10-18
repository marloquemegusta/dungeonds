#include "enemy_ai.h"
#include "los.h"
#include "projectiles.h"
#include "player_sprite.h"
#include <string.h>

void enemy_ai_init(void) {
    // Subsystem init if needed
}

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

static void update_charger(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                           fixed player_x, fixed player_y) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_CHARGER];
    int player_dead = g_player_state.is_dead;

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);

    int has_los = !player_dead && los_has_line_of_sight(wx, wy, px, py, tuning->los_range);

    if (e->hit_timer > 0) {
        if (e->state == ENEMY_STATE_IDLE || e->state == ENEMY_STATE_SEARCH) {
            e->state = ENEMY_STATE_ALERT;
            e->state_timer = tuning->alert_duration;
            e->last_seen_x = player_x;
            e->last_seen_y = player_y;
            e->los_lost_timer = 0;
        }
    }

    switch (e->state) {
        case ENEMY_STATE_IDLE: {
            if (has_los) {
                e->state = ENEMY_STATE_ALERT;
                e->state_timer = tuning->alert_duration;
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
            }
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_ALERT: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            e->state_timer--;
            if (e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHASE;
            }
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_CHASE: {
            if (player_dead) {
                e->state = ENEMY_STATE_IDLE;
                update_animation(e, 0);
                break;
            }

            if (has_los) {
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
            } else {
                e->los_lost_timer++;
                if (e->los_lost_timer >= tuning->los_lost_limit) {
                    e->state = ENEMY_STATE_SEARCH;
                    e->state_timer = tuning->search_duration;
                    update_animation(e, 0);
                    break;
                }
            }

            // Check melee contact range to player
            int32_t p_dx = px - wx;
            int32_t p_dy = py - wy;
            int32_t p_dist_sq = p_dx * p_dx + p_dy * p_dy;

            int melee_range = tuning->preferred_dist_max > 0 ? tuning->preferred_dist_max : 16;
            if (p_dist_sq <= melee_range * melee_range) {
                player_apply_damage(&g_player_state, tuning->contact_damage);
                e->state = ENEMY_STATE_ATTACK;
                e->state_timer = tuning->attack_cooldown;
                e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
                update_animation(e, 0);
                break;
            }

            // Move towards player (or last seen pos if no LOS)
            fixed target_x = has_los ? player_x : e->last_seen_x;
            fixed target_y = has_los ? player_y : e->last_seen_y;

            int32_t t_dx = TO_INT(target_x - e->x);
            int32_t t_dy = TO_INT(target_y - e->y);
            uint32_t t_dist = int_sqrt((uint32_t)(t_dx * t_dx + t_dy * t_dy));

            fixed vx = 0, vy = 0;
            if (t_dist > 0) {
                vx = (fixed)((t_dx * (int32_t)tuning->speed) / (int32_t)t_dist);
                vy = (fixed)((t_dy * (int32_t)tuning->speed) / (int32_t)t_dist);
            }

            apply_separation(enemies, num_enemies, idx, &vx, &vy);
            int moved = move_with_slide(&e->x, &e->y, vx, vy);
            e->dir = dir_from_vector(vx, vy);
            update_animation(e, moved);
            break;
        }

        case ENEMY_STATE_ATTACK: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            e->state_timer--;
            if (e->state_timer <= 0) {
                e->state = ENEMY_STATE_CHASE;
            }
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_SEARCH: {
            if (has_los) {
                e->state = ENEMY_STATE_ALERT;
                e->state_timer = tuning->alert_duration / 2;
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
                update_animation(e, 0);
                break;
            }

            int32_t s_dx = TO_INT(e->last_seen_x - e->x);
            int32_t s_dy = TO_INT(e->last_seen_y - e->y);
            uint32_t s_dist = int_sqrt((uint32_t)(s_dx * s_dx + s_dy * s_dy));

            e->state_timer--;
            if (s_dist <= 8 || e->state_timer <= 0) {
                e->state = ENEMY_STATE_IDLE;
                update_animation(e, 0);
                break;
            }

            fixed vx = (fixed)((s_dx * (int32_t)tuning->speed) / (int32_t)s_dist);
            fixed vy = (fixed)((s_dy * (int32_t)tuning->speed) / (int32_t)s_dist);
            apply_separation(enemies, num_enemies, idx, &vx, &vy);
            int moved = move_with_slide(&e->x, &e->y, vx, vy);
            e->dir = dir_from_vector(vx, vy);
            update_animation(e, moved);
            break;
        }

        default:
            break;
    }
}

static void update_shooter(Enemy *e, Enemy *enemies, int num_enemies, int idx,
                           fixed player_x, fixed player_y, fixed player_vx, fixed player_vy) {
    const EnemyTuning *tuning = &g_enemy_tuning[ENEMY_TYPE_SHOOTER];
    int player_dead = g_player_state.is_dead;

    int wx = TO_INT(e->x);
    int wy = TO_INT(e->y);
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);

    int has_los = !player_dead && los_has_line_of_sight(wx, wy, px, py, tuning->los_range);

    if (e->hit_timer > 0) {
        if (e->state == ENEMY_STATE_IDLE || e->state == ENEMY_STATE_SEARCH) {
            e->state = ENEMY_STATE_ALERT;
            e->state_timer = tuning->alert_duration;
            e->last_seen_x = player_x;
            e->last_seen_y = player_y;
            e->los_lost_timer = 0;
        }
    }

    switch (e->state) {
        case ENEMY_STATE_IDLE: {
            if (has_los) {
                e->state = ENEMY_STATE_ALERT;
                e->state_timer = tuning->alert_duration;
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
            }
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_ALERT: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            e->state_timer--;
            if (e->state_timer <= 0) {
                e->state = ENEMY_STATE_POSITION;
                e->state_timer = tuning->position_duration;
            }
            update_animation(e, 0);
            break;
        }

        case ENEMY_STATE_POSITION: {
            if (player_dead) {
                e->state = ENEMY_STATE_IDLE;
                update_animation(e, 0);
                break;
            }

            if (has_los) {
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
            } else {
                e->los_lost_timer++;
                if (e->los_lost_timer >= tuning->los_lost_limit) {
                    e->state = ENEMY_STATE_SEARCH;
                    e->state_timer = tuning->search_duration;
                    update_animation(e, 0);
                    break;
                }
            }

            int32_t p_dx = px - wx;
            int32_t p_dy = py - wy;
            uint32_t p_dist = int_sqrt((uint32_t)(p_dx * p_dx + p_dy * p_dy));

            fixed move_dx = 0;
            fixed move_dy = 0;

            if (p_dist < (uint32_t)tuning->preferred_dist_min) {
                // Too close: retreat away from player
                move_dx = -p_dx;
                move_dy = -p_dy;
            } else if (p_dist > (uint32_t)tuning->preferred_dist_max) {
                // Too far: advance towards player
                move_dx = p_dx;
                move_dy = p_dy;
            } else {
                // In distance band: strafe laterally
                if (e->strafe_dir == 0) e->strafe_dir = 1;
                move_dx = -p_dy * e->strafe_dir;
                move_dy =  p_dx * e->strafe_dir;
            }

            uint32_t m_dist = int_sqrt((uint32_t)(move_dx * move_dx + move_dy * move_dy));
            fixed vx = 0, vy = 0;
            if (m_dist > 0) {
                vx = (fixed)((move_dx * (int32_t)tuning->speed) / (int32_t)m_dist);
                vy = (fixed)((move_dy * (int32_t)tuning->speed) / (int32_t)m_dist);
            }

            apply_separation(enemies, num_enemies, idx, &vx, &vy);
            int moved = move_with_slide(&e->x, &e->y, vx, vy);
            if (!moved && p_dist >= (uint32_t)tuning->preferred_dist_min && p_dist <= (uint32_t)tuning->preferred_dist_max) {
                // If strafe hit a wall, reverse strafe direction
                e->strafe_dir = -e->strafe_dir;
            }

            // Shooter continuously faces player while positioning
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            update_animation(e, moved);

            e->state_timer--;
            if (e->state_timer <= 0 && e->los_lost_timer == 0) {
                e->state = ENEMY_STATE_AIM;
                e->state_timer = tuning->aim_duration;
            }
            break;
        }

        case ENEMY_STATE_AIM: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            update_animation(e, 0);

            e->state_timer--;
            if (e->state_timer <= 0) {
                e->state = ENEMY_STATE_BURST;
                e->burst_shots_left = tuning->burst_count;
                e->burst_interval_timer = 0;
            }
            break;
        }

        case ENEMY_STATE_BURST: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            update_animation(e, 0);

            if (e->burst_interval_timer <= 0 && e->burst_shots_left > 0) {
                // Predict target position with lead
                int32_t p_dx = px - wx;
                int32_t p_dy = py - wy;
                uint32_t p_dist = int_sqrt((uint32_t)(p_dx * p_dx + p_dy * p_dy));

                fixed proj_spd = tuning->projectile_speed > 0 ? tuning->projectile_speed : 384;
                int32_t travel_frames = (int32_t)((p_dist * 256) / (uint32_t)proj_spd);
                if (travel_frames > 20) travel_frames = 20;
                if (travel_frames < 0) travel_frames = 0;

                fixed target_px = player_x + ((player_vx * travel_frames) >> 8);
                fixed target_py = player_y + ((player_vy * travel_frames) >> 8);

                int32_t t_dx = TO_INT(target_px - e->x);
                int32_t t_dy = TO_INT(target_py - e->y);
                uint32_t t_dist = int_sqrt((uint32_t)(t_dx * t_dx + t_dy * t_dy));

                if (t_dist > 0) {
                    fixed pvx = (fixed)((t_dx * (int32_t)proj_spd) / (int32_t)t_dist);
                    fixed pvy = (fixed)((t_dy * (int32_t)proj_spd) / (int32_t)t_dist);
                    enemy_projectile_spawn_linear(e->x, e->y, pvx, pvy, tuning->projectile_damage, 120);
                }

                e->burst_shots_left--;
                e->burst_interval_timer = tuning->burst_interval;
            } else {
                e->burst_interval_timer--;
            }

            if (e->burst_shots_left <= 0) {
                e->state = ENEMY_STATE_COOLDOWN;
                e->state_timer = tuning->attack_cooldown;
            }
            break;
        }

        case ENEMY_STATE_COOLDOWN: {
            e->dir = dir_from_vector(player_x - e->x, player_y - e->y);
            update_animation(e, 0);

            e->state_timer--;
            if (e->state_timer <= 0) {
                e->state = ENEMY_STATE_POSITION;
                e->state_timer = tuning->position_duration;
            }
            break;
        }

        case ENEMY_STATE_SEARCH: {
            if (has_los) {
                e->state = ENEMY_STATE_ALERT;
                e->state_timer = tuning->alert_duration / 2;
                e->last_seen_x = player_x;
                e->last_seen_y = player_y;
                e->los_lost_timer = 0;
                update_animation(e, 0);
                break;
            }

            int32_t s_dx = TO_INT(e->last_seen_x - e->x);
            int32_t s_dy = TO_INT(e->last_seen_y - e->y);
            uint32_t s_dist = int_sqrt((uint32_t)(s_dx * s_dx + s_dy * s_dy));

            e->state_timer--;
            if (s_dist <= 8 || e->state_timer <= 0) {
                e->state = ENEMY_STATE_IDLE;
                update_animation(e, 0);
                break;
            }

            fixed vx = (fixed)((s_dx * (int32_t)tuning->speed) / (int32_t)s_dist);
            fixed vy = (fixed)((s_dy * (int32_t)tuning->speed) / (int32_t)s_dist);
            apply_separation(enemies, num_enemies, idx, &vx, &vy);
            int moved = move_with_slide(&e->x, &e->y, vx, vy);
            e->dir = dir_from_vector(vx, vy);
            update_animation(e, moved);
            break;
        }

        default:
            break;
    }
}

void enemy_ai_update(Enemy *enemies, int num_enemies, fixed player_x, fixed player_y, fixed player_vx, fixed player_vy) {
    if (!enemies || num_enemies <= 0) return;

    for (int i = 0; i < num_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;

        if (e->hit_timer > 0) e->hit_timer--;

        if (e->type == ENEMY_TYPE_CHARGER) {
            update_charger(e, enemies, num_enemies, i, player_x, player_y);
        } else if (e->type == ENEMY_TYPE_SHOOTER) {
            update_shooter(e, enemies, num_enemies, i, player_x, player_y, player_vx, player_vy);
        }
    }
}
