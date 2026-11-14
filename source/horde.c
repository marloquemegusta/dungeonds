#include "horde.h"
#include "collision.h"
#include "player_sprite.h"
#include "strip.h"
#include "enemy_ai.h"
#include <nds/ndstypes.h>

static uint32_t s_rng;
static uint32_t s_run_frames;
static int s_spawn_timer;
static int s_interval;
static int s_interval_ramp;
static int s_cap;
static int s_cap_ramp;
static int s_cap_ramp_timer;
static int s_chargers_alive;      // recounted every update, bumped on each charger spawn

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

// 2:1 ellipse table, 32 steps (unit circle x256): step 0 = east, step 8 = south on screen.
static const int16_t s_ring_cos[32] = {
    256, 251, 237, 213, 181, 142, 98, 50, 0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50, 0, 50, 98, 142, 181, 213, 237, 251
};
static const int16_t s_ring_sin[32] = {
    0, 50, 98, 142, 181, 213, 237, 251, 256, 251, 237, 213, 181, 142, 98, 50,
    0, -50, -98, -142, -181, -213, -237, -251, -256, -251, -237, -213, -181, -142, -98, -50
};

// The devout piece the Exvotos of the current spawn burst pray to (DESIGN.md 6.10): picked by the first
// Exvoto of the burst, shared by the rest up to HORDE_EXVOTO_GROUP_MAX.
static StripDevout s_group_piece;
static int s_group_piece_valid;
static int s_group_seated;

// A praying Exvoto already stands at this piece (the piece is claimed by an earlier group).
static int piece_is_claimed(const StripDevout *d, const Enemy *enemies, int count) {
    int r = (d->hw > d->hh ? d->hw : d->hh) + HORDE_EXVOTO_CLAIM_RADIUS_PX;
    for (int i = 0; i < count; i++) {
        const Enemy *o = &enemies[i];
        if (!o->active || o->type != ENEMY_TYPE_EXVOTO || o->state != ENEMY_STATE_PRAY) continue;
        int dx = TO_INT(o->x) - d->x;
        int dy = TO_INT(o->y) - d->y;
        if (dx * dx + GROUND_DY2(dy) <= r * r) return 1;
    }
    return 0;
}

// Picks a free devout piece in the spawn strip for a new burst of Exvotos; 0 when there is none.
static int pick_devout_piece(const Enemy *enemies, int count, int upper_screen_y) {
    StripDevout found[HORDE_DEVOUT_CANDIDATES];
    int n = strip_devout_in_band(upper_screen_y - HORDE_SPAWN_GAP_MAX, upper_screen_y - HORDE_SPAWN_GAP_MIN,
                                 found, HORDE_DEVOUT_CANDIDATES);
    int free_idx[HORDE_DEVOUT_CANDIDATES];
    int free_n = 0;
    for (int i = 0; i < n; i++) {
        if (found[i].x < HORDE_SPAWN_X_MIN || found[i].x > HORDE_SPAWN_X_MAX) continue;
        if (piece_is_claimed(&found[i], enemies, count)) continue;
        free_idx[free_n++] = i;
    }
    if (free_n == 0) return 0;
    s_group_piece = found[free_idx[horde_random() % (uint32_t)free_n]];
    s_group_piece_valid = 1;
    s_group_seated = 0;
    return 1;
}

// Seats an Exvoto right outside the footprint of the burst's devout piece (the body is a circle of radius 6 on the
// ground, so the nearest free spot is 7 px beside the footprint or 4 screen rows in front of it; a second cell
// further is the other option), on a free cell, facing the piece. Candidate angles start on the south side (towards the hero) and alternate left and
// right, so a group of up to HORDE_EXVOTO_GROUP_MAX spreads in an arc. Returns 0 when it does not fit.
static int seat_exvoto(Enemy *e, const Enemy *enemies, int count, int upper_screen_y,
                       int *spawn_x, int *spawn_y) {
    if (!s_group_piece_valid && !pick_devout_piece(enemies, count, upper_screen_y)) return 0;
    if (s_group_seated >= HORDE_EXVOTO_GROUP_MAX) return 0;
    const StripDevout *d = &s_group_piece;
    int extra = 4 * (int)(horde_random() & 1u);               // 0 or 1 more collision cell of 4 px
    int rx = d->hw + HORDE_EXVOTO_SIDE_PX + extra;
    int ry = d->hh + HORDE_EXVOTO_FRONT_PX + (extra >> 1);
    for (int k = 0; k < 32; k++) {
        int off = (k + 1) >> 1;                               // 0, 1, 1, 2, 2, ...
        int step = (8 + ((k & 1) ? off : -off) * 2) & 31;     // 22.5 degrees apart, alternating sides
        int x = d->x + ((rx * s_ring_cos[step]) >> 8);
        int y = d->y + ((ry * s_ring_sin[step]) >> 8);
        // The front of the piece (south half) is a straight row just outside the footprint: an Exvoto beside the
        // piece but above its base would stand behind the piece's own occlusion and vanish.
        if (s_ring_sin[step] > 0 && y < d->y + d->hh + HORDE_EXVOTO_FRONT_PX) y = d->y + d->hh + HORDE_EXVOTO_FRONT_PX;
        if (x < HORDE_SPAWN_X_MIN || x > HORDE_SPAWN_X_MAX) continue;
        if (y > upper_screen_y - HORDE_SPAWN_GAP_MIN) continue;   // never seat them in view
        if (!position_is_free(TO_FIXED(x), TO_FIXED(y))) continue;
        int crowded = 0;
        for (int i = 0; i < count && !crowded; i++) {
            const Enemy *o = &enemies[i];
            if (!o->active || o == e) continue;
            int dx = TO_INT(o->x) - x;
            int dy = TO_INT(o->y) - y;
            crowded = dx * dx + GROUND_DY2(dy) < HORDE_EXVOTO_SPACING_PX * HORDE_EXVOTO_SPACING_PX;
        }
        if (crowded) continue;
        e->x = TO_FIXED(x);
        e->y = TO_FIXED(y);
        e->dir = enemy_dir_from_vector(TO_FIXED(d->x - x), TO_FIXED(d->y - y));
        *spawn_x = x;
        *spawn_y = y;
        s_group_seated++;
        return 1;
    }
    return 0;
}

static int spawn_enemy(Enemy *e, Enemy *enemies, int count, int upper_screen_y, int clustered,
                       int center_x, int center_y, int *spawn_x, int *spawn_y) {
    memset(e, 0, sizeof(*e));
    uint32_t roll = horde_random() % 100u;
    if (roll < HORDE_EXVOTO_PERCENT) e->type = ENEMY_TYPE_EXVOTO;
    else if (roll < HORDE_EXVOTO_PERCENT + HORDE_CHARGER_PERCENT)
        e->type = s_chargers_alive < HORDE_CHARGER_MAX_ALIVE ? ENEMY_TYPE_CHARGER : ENEMY_TYPE_EXVOTO;
    else e->type = ENEMY_TYPE_SHOOTER;

    // An Exvoto prays in front of a devout piece of the strip; with none free it spawns awake and walking.
    int seated = e->type == ENEMY_TYPE_EXVOTO &&
                 seat_exvoto(e, enemies, count, upper_screen_y, spawn_x, spawn_y);
    if (!seated) {
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
        e->x = TO_FIXED(x);
        e->y = TO_FIXED(y);
        e->dir = DIR_SOUTH;
    }
    if (e->type == ENEMY_TYPE_CHARGER) s_chargers_alive++;
    e->char_id = enemy_type_char_id(e->type);
    e->hp = g_enemy_tuning[e->type].max_hp;
#if STRESS_TEST
    e->hp = 1;                // measurement build: any hit kills
#endif
    e->max_hp = e->hp;
    e->frame = 0;
    e->anim_timer = 0;
    e->active = 1;
    e->state = ENEMY_INITIAL_STATE(e->type);
    e->state_timer = 0;
    e->charge_hit = 0;
    e->hit_timer = 0;
    e->stun_timer = 0;
    e->knock_vx = 0;
    e->knock_vy = 0;
    e->strafe_dir = (horde_random() & 1u) ? 1 : -1;
    e->pack = -1;
    e->has_los = 0;
    if (seated)
        enemy_exvoto_start_praying(e, (int)(horde_random() % 100u) < EXVOTO_KNEEL_PERCENT, e->dir);
    return 1;
}

ITCM_CODE void horde_update(Enemy *enemies, int count, fixed player_y,
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
    s_chargers_alive = 0;
    for (int i = 0; i < count; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;
        if (e->y > player_y + TO_FIXED(HORDE_RECYCLE_BEHIND_PX) || e->y >= tide_y) e->active = 0;
        else {
            alive++;
            if (e->type == ENEMY_TYPE_CHARGER) s_chargers_alive++;
        }
    }

    if (--s_spawn_timer > 0 || alive >= s_cap) return;
    int wanted = 1;
    if ((int)(horde_random() % 100u) < HORDE_SPAWN_GROUP_CHANCE)
        wanted = HORDE_SPAWN_GROUP_MIN + (int)(horde_random() % (HORDE_SPAWN_GROUP_MAX - HORDE_SPAWN_GROUP_MIN + 1));
    int cluster_x = 0, cluster_y = 0;
    s_group_piece_valid = 0;
    for (int n = 0; n < wanted && alive < s_cap; n++) {
        for (int i = 0; i < count; i++) {
            if (enemies[i].active) continue;
            if (spawn_enemy(&enemies[i], enemies, count, upper_screen_y, n != 0, cluster_x, cluster_y,
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
