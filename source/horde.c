#include "horde.h"
#include "collision.h"
#include "player_sprite.h"

static uint32_t s_rng;
static uint32_t s_run_frames;
static int s_spawn_timer;
static int s_interval;
static int s_interval_ramp;
static int s_cap;
static int s_cap_ramp;
static int s_cap_ramp_timer;

static uint32_t horde_random(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    return s_rng;
}

void horde_init(uint32_t seed) {
    s_rng = seed ? seed : 1u;
    s_run_frames = 0;
    s_interval = HORDE_INITIAL_INTERVAL;
    s_spawn_timer = s_interval;
    s_interval_ramp = HORDE_RAMP_STEP_FRAMES;
    s_cap = HORDE_INITIAL_CAP;
    s_cap_ramp = HORDE_CAP_RAMP_FRAMES / (HORDE_MAX_CAP - HORDE_INITIAL_CAP);
    s_cap_ramp_timer = s_cap_ramp;
}

static int spawn_enemy(Enemy *e, int upper_screen_y, int clustered, int center_x, int center_y,
                       int *spawn_x, int *spawn_y) {
    int x = HORDE_SPAWN_X_MIN;
    int y = upper_screen_y - HORDE_SPAWN_GAP_MIN;
    for (int attempt = 0; attempt < HORDE_SPAWN_ATTEMPTS; attempt++) {
        if (clustered) {
            x = center_x - HORDE_CLUSTER_HALF_WIDTH_PX +
                (int)(horde_random() % (HORDE_CLUSTER_HALF_WIDTH_PX * 2 + 1));
            y = center_y - HORDE_CLUSTER_HALF_HEIGHT_PX +
                (int)(horde_random() % (HORDE_CLUSTER_HALF_HEIGHT_PX * 2 + 1));
        } else {
            x = HORDE_SPAWN_X_MIN + (int)(horde_random() % (HORDE_SPAWN_X_MAX - HORDE_SPAWN_X_MIN + 1));
            y = upper_screen_y - HORDE_SPAWN_GAP_MIN -
                (int)(horde_random() % (HORDE_SPAWN_GAP_MAX - HORDE_SPAWN_GAP_MIN + 1));
        }
        if (clustered) {
            if (x < HORDE_SPAWN_X_MIN) x = HORDE_SPAWN_X_MIN;
            if (x > HORDE_SPAWN_X_MAX) x = HORDE_SPAWN_X_MAX;
            if (y > upper_screen_y - HORDE_SPAWN_GAP_MIN) y = upper_screen_y - HORDE_SPAWN_GAP_MIN;
            if (y < upper_screen_y - HORDE_SPAWN_GAP_MAX) y = upper_screen_y - HORDE_SPAWN_GAP_MAX;
        }
        if (position_is_free(TO_FIXED(x), TO_FIXED(y))) break;
    }
    if (!position_is_free(TO_FIXED(x), TO_FIXED(y))) return 0;
    *spawn_x = x;
    *spawn_y = y;
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->type = (horde_random() % 100u) < HORDE_CHARGER_PERCENT ? ENEMY_TYPE_CHARGER : ENEMY_TYPE_SHOOTER;
    e->char_id = e->type == ENEMY_TYPE_CHARGER ? CHAR_CHARGER : CHAR_NECRON;
    e->hp = g_enemy_tuning[e->type].max_hp;
    e->max_hp = e->hp;
    e->dir = DIR_SOUTH;
    e->frame = 0;
    e->anim_timer = 0;
    e->active = 1;
    e->state = e->type == ENEMY_TYPE_CHARGER ? ENEMY_STATE_CHASE : ENEMY_STATE_POSITION;
    e->state_timer = 0;
    e->burst_shots_left = 0;
    e->burst_interval_timer = 0;
    e->hit_timer = 0;
    e->stun_timer = 0;
    e->knock_vx = 0;
    e->knock_vy = 0;
    e->strafe_dir = (horde_random() & 1u) ? 1 : -1;
    e->pack = -1;
    e->has_los = 0;
    return 1;
}

void horde_update(Enemy *enemies, int count, fixed player_y,
                  int upper_screen_y, fixed tide_y) {
    if (!enemies || count <= 0) return;
    s_run_frames++;
    if (s_interval > HORDE_MIN_INTERVAL && --s_interval_ramp <= 0) {
        s_interval--;
        s_interval_ramp = HORDE_RAMP_STEP_FRAMES;
    }
    if (s_cap < HORDE_MAX_CAP && --s_cap_ramp_timer <= 0) {
        s_cap++;
        s_cap_ramp_timer = s_cap_ramp;
    }

    int alive = 0;
    for (int i = 0; i < count; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;
        if (e->y > player_y + TO_FIXED(HORDE_RECYCLE_BEHIND_PX) || e->y >= tide_y) e->active = 0;
        else alive++;
    }

    if (--s_spawn_timer > 0 || alive >= s_cap) return;
    int wanted = 1;
    if ((int)(horde_random() % 100u) < HORDE_SPAWN_GROUP_CHANCE)
        wanted = HORDE_SPAWN_GROUP_MIN + (int)(horde_random() % (HORDE_SPAWN_GROUP_MAX - HORDE_SPAWN_GROUP_MIN + 1));
    int cluster_x = 0, cluster_y = 0;
    for (int n = 0; n < wanted && alive < s_cap; n++) {
        for (int i = 0; i < count; i++) {
            if (enemies[i].active) continue;
            if (spawn_enemy(&enemies[i], upper_screen_y, n != 0, cluster_x, cluster_y,
                            &cluster_x, &cluster_y)) alive++;
            else if (n == 0) {
                s_spawn_timer = s_interval;
                return;
            }
            break;
        }
    }
    s_spawn_timer = s_interval;
}

uint32_t horde_run_frames(void) { return s_run_frames; }
