#include "arpg_quest.h"
#include "arpg_bot.h"

// Translation unit never empty (ISO C) when ARPG_BOT=0.
typedef int arpg_bot_translation_unit_not_empty;

#if ARPG_BOT && ENCOUNTERS_PROTO

// Autopilot of the variant "arpg-bot". It plays the cathedral of the ARPG like a human of a given skill: it dodges the
// Ojo gaze and the Cireneo lunge (late, or not at all, when clumsy), shoots the ray at what is worth its mana, punches
// what comes close, finishes the reeling enemies with L and climbs through the upper doors. It only replaces the
// buttons and the stylus; the game does not know. Geometry is done on the ground: x as is, y doubled (2:1 projection).
// Adapted from source/encounters_bot.c (the autopilot of the old roguelike mode, which stays as it is).

#include "collision.h"
#include "weapons.h"
#include "modifiers.h"
#include "encounters_act1.h"
#include "remate.h"
#include "pickups.h"
#include "arpg.h"
#include "arpg_progress.h"
#include "camp.h"
#include "menu.h"

#define GY(dy) (2 * (dy))
#define BOT_RAY_MIN_DIST 56         // ground px: a melee enemy this close makes the hero punch instead of charging the ray
#define BOT_CANCEL_CHARGE 24        // ground px: a melee enemy this close cancels a charge that is not ready
#define BOT_RETREAT_NEAR 48         // ground px: below the panic threshold the hero backs off from a melee enemy this close...
#define BOT_RETREAT_FAR 72          // ...until it is this far
#define BOT_PUNCH_REACH 28          // ground px: enemies this close are punched (the game reach is 34)
#define BOT_RANGE_MARGIN 12
#define BOT_STUCK_FRAMES 60
#define BOT_SIDESTEP_FRAMES 30
#define BOT_OJO_CLEAR 26
#define BOT_LANE_CLEAR 28
#define BOT_PASSIVE_ENGAGE 150      // ground px: guards and praying enemies only count as targets this close
#define BOT_GIVE_UP_FRAMES 1500     // frames in a room without a kill before it drops the hunt and goes for the door
#define BOT_ORB_RANGE 150           // ground px: orbs this close are collected when nothing threatens
#define BOT_DEFAULT_TIMEOUT 36000
#define BOT_VISIT_CAP 10800         // frames in one visit to a room before it stops for chests and heads for the door

volatile ArpgBotDebug g_arpg_bot_debug = { .profile = 0, .applied = 0xFF, .seed = 1 };
volatile ArpgBotStats g_arpg_bot_stats;

static const int8_t s_dir_x[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };       // 0 = north (up), clockwise
static const int8_t s_dir_y[8] = { -1, -1, 0, 1, 1, 1, 0, -1 };

static int s_last_dir = -1;
static int s_dodge_side, s_dodge_hold;
static int s_stuck_ref_x, s_stuck_ref_y, s_stuck_timer;
static int s_side_timer, s_side_sign = 1;
static int s_retreat;
static int s_wait_frames;

static int isqrt_u(uint32_t v) {
    uint32_t r = 0, bit = 1u << 30;
    while (bit > v) bit >>= 2;
    while (bit) {
        if (v >= r + bit) { v -= r + bit; r = (r >> 1) + bit; }
        else r >>= 1;
        bit >>= 2;
    }
    return (int)r;
}
static int iabs(int v) { return v < 0 ? -v : v; }
static int gd2(int dx, int dy) { return dx * dx + 4 * dy * dy; }

static int unit256(int vx, int vy, int *ux, int *uy) {
    int len = isqrt_u((uint32_t)(vx * vx + vy * vy));
    if (len == 0) return 0;
    *ux = vx * 256 / len;
    *uy = vy * 256 / len;
    return 1;
}

// Mouths of the lateral doors of a nave: the bot never walks into them (it has no business in the side rooms; kiting or
// dodging towards a mouth used to drag it into the Capilla del parroco again and again). Refreshed every frame.
static int s_nside, s_side_l[3], s_side_y0[3], s_side_y1[3], s_side_x[3];

static int is_free(int x, int y) {
    for (int i = 0; i < s_nside; i++) {
        if (y >= s_side_y0[i] && y <= s_side_y1[i] && (s_side_l[i] ? x <= s_side_x[i] : x >= s_side_x[i])) return 0;
    }
    return position_is_free(TO_FIXED(x), TO_FIXED(y));
}

static int dir_free(int hx, int hy, int d, int len) {
    int ux = 0, uy = 0;
    unit256(s_dir_x[d] * 256, s_dir_y[d] * 256, &ux, &uy);
    for (int k = 1; k <= 2; k++) {
        int l = len * k / 2;
        if (!is_free(hx + ((ux * l) >> 8), hy + ((uy * l) >> 9))) return 0;
    }
    return 1;
}

static int steer(int hx, int hy, int wx, int wy) {
    int ux, uy;
    if (!unit256(wx, wy, &ux, &uy)) return -1;
    int best = -1, best_score = -100000;
    for (int d = 0; d < 8; d++) {
        int dx = 0, dy = 0;
        unit256(s_dir_x[d] * 256, s_dir_y[d] * 256, &dx, &dy);
        int score = (dx * ux + dy * uy) >> 8;
        if (!dir_free(hx, hy, d, 16)) continue;
        if (!dir_free(hx, hy, d, 36)) score -= 90;
        if (d == s_last_dir) score += 40;
        if (score > best_score) { best_score = score; best = d; }
    }
    return best;
}

static uint32_t keys_of(int d) {
    uint32_t k = 0;
    if (s_dir_y[d] < 0) k |= KEY_UP;
    if (s_dir_y[d] > 0) k |= KEY_DOWN;
    if (s_dir_x[d] < 0) k |= KEY_LEFT;
    if (s_dir_x[d] > 0) k |= KEY_RIGHT;
    return k;
}

// Walkable straight line (a wall between two actors blocks it): 6 samples along the segment.
static int walk_line_free(int x0, int y0, int x1, int y1) {
    for (int k = 1; k <= 6; k++) {
        if (!is_free(x0 + (x1 - x0) * k / 7, y0 + (y1 - y0) * k / 7)) return 0;
    }
    return 1;
}

static int column_side(int hx, int hy, int ux, int uy) {
    int px = -uy, py = ux;
    for (int dist = 8; dist <= 48; dist += 8) {
        for (int s = 1; s >= -1; s -= 2) {
            int x = hx + ((px * dist * s) >> 8);
            int y = hy + ((py * dist * s) >> 9);
            if (!bullet_position_is_free(TO_FIXED(x), TO_FIXED(y))) return s;
        }
    }
    return 0;
}

// ---------------------------------------------------------------------------------------------------------
// Path finding: a coarse grid (8 ground px per cell) around the hero, flooded from the goal.
// ---------------------------------------------------------------------------------------------------------
#define PF_W 28                  // cells across: world x 144..368 (the floor of a room is 152..360)
#define PF_X0 144
#define PF_CELL_X 8
#define PF_CELL_Y 4
#define PF_H 72
#define PF_ROWS_ABOVE 52
#define PF_INF 30000

static uint8_t s_pf_blocked[PF_W * PF_H];
static int16_t s_pf_dist[PF_W * PF_H];
static int16_t s_pf_queue[PF_W * PF_H];
static int s_pf_y0, s_pf_age = 1000;
static int s_flood_cx = -1, s_flood_cy = -1, s_flood_age = 1000;

static int pf_cell_free(int cx, int cy) {
    return is_free(PF_X0 + cx * PF_CELL_X + PF_CELL_X / 2, s_pf_y0 + cy * PF_CELL_Y + PF_CELL_Y / 2);
}

static void pf_rebuild(int hy) {
    s_pf_y0 = hy - PF_ROWS_ABOVE * PF_CELL_Y;
    for (int cy = 0; cy < PF_H; cy++)
        for (int cx = 0; cx < PF_W; cx++) s_pf_blocked[cy * PF_W + cx] = (uint8_t)!pf_cell_free(cx, cy);
}

static void pf_cell_of(int wx, int wy, int *cx, int *cy) {
    int x = (wx - PF_X0) / PF_CELL_X, y = (wy - s_pf_y0) / PF_CELL_Y;
    if (wx < PF_X0) x = 0;
    if (wy < s_pf_y0) y = 0;
    if (x >= PF_W) x = PF_W - 1;
    if (y >= PF_H) y = PF_H - 1;
    *cx = x;
    *cy = y;
}

// Starts the flood at the cell of (gx, gy), or at the free cell nearest to it when that one is blocked (a goal clamped to the
// top of the window may fall inside a wall).
static void pf_flood(int gx, int gy) {
    for (int i = 0; i < PF_W * PF_H; i++) s_pf_dist[i] = PF_INF;
    int cx, cy;
    pf_cell_of(gx, gy, &cx, &cy);
    if (s_pf_blocked[cy * PF_W + cx]) {
        int found = 0;
        for (int r = 1; r <= 8 && !found; r++) {
            for (int dy = 0; dy <= r && !found; dy++) {
                for (int dx = -r; dx <= r && !found; dx++) {
                    int nx = cx + dx, ny = cy + dy;
                    if (nx < 0 || nx >= PF_W || ny < 0 || ny >= PF_H) continue;
                    if (!s_pf_blocked[ny * PF_W + nx]) { cx = nx; cy = ny; found = 1; }
                }
            }
        }
    }
    int head = 0, tail = 0;
    s_pf_dist[cy * PF_W + cx] = 0;
    s_pf_queue[tail++] = (int16_t)(cy * PF_W + cx);
    while (head < tail) {
        int cur = s_pf_queue[head++];
        int ccx = cur % PF_W, ccy = cur / PF_W;
        for (int d = 0; d < 8; d++) {
            int nx = ccx + (int)s_dir_x[d], ny = ccy + (int)s_dir_y[d];
            if (nx < 0 || ny < 0 || nx >= PF_W || ny >= PF_H) continue;
            int ni = ny * PF_W + nx;
            if (s_pf_blocked[ni] || s_pf_dist[ni] != PF_INF) continue;
            if ((s_dir_x[d] != 0 && s_dir_y[d] != 0) &&
                (s_pf_blocked[ccy * PF_W + nx] || s_pf_blocked[ny * PF_W + ccx])) continue;
            s_pf_dist[ni] = (int16_t)(s_pf_dist[cur] + 1);
            s_pf_queue[tail++] = (int16_t)ni;
        }
    }
}

static int pf_next(int hx, int hy, int steps, int *wx, int *wy) {
    int cx, cy;
    pf_cell_of(hx, hy, &cx, &cy);
    int here = s_pf_dist[cy * PF_W + cx];
    int best_here = PF_INF;
    for (int d = 0; d < 8; d++) {
        int nx = cx + (int)s_dir_x[d], ny = cy + (int)s_dir_y[d];
        if (nx < 0 || ny < 0 || nx >= PF_W || ny >= PF_H) continue;
        if (s_pf_dist[ny * PF_W + nx] < best_here) best_here = s_pf_dist[ny * PF_W + nx];
    }
    if (here == PF_INF && best_here == PF_INF) return 0;
    for (int k = 0; k < steps; k++) {
        int bd = -1, bv = s_pf_dist[cy * PF_W + cx];
        for (int d = 0; d < 8; d++) {
            int nx = cx + (int)s_dir_x[d], ny = cy + (int)s_dir_y[d];
            if (nx < 0 || ny < 0 || nx >= PF_W || ny >= PF_H) continue;
            int v = s_pf_dist[ny * PF_W + nx];
            if (v < bv || (bd < 0 && v < PF_INF && bv == PF_INF)) { bv = v; bd = d; }
        }
        if (bd < 0) break;
        cx += s_dir_x[bd];
        cy += s_dir_y[bd];
    }
    int tx = PF_X0 + cx * PF_CELL_X + PF_CELL_X / 2;
    int ty = s_pf_y0 + cy * PF_CELL_Y + PF_CELL_Y / 2;
    *wx = tx - hx;
    *wy = GY(ty - hy);
    return (*wx != 0 || *wy != 0);
}

// Wished ground vector to reach (gx, gy) by the floor; 0 when there is no path.
static int pf_direction(int hx, int hy, int gx, int gy, int *wx, int *wy) {
    if (++s_pf_age > 24 || hy < s_pf_y0 + 2 * PF_CELL_Y || hy > s_pf_y0 + (PF_H - 4) * PF_CELL_Y) {
        pf_rebuild(hy);
        s_pf_age = 0;
    }
    int gcx, gcy;
    pf_cell_of(gx, gy, &gcx, &gcy);
    if (s_pf_age == 0 || gcx != s_flood_cx || gcy != s_flood_cy || ++s_flood_age >= 8) {
        pf_flood(gx, gy);
        s_flood_cx = gcx;
        s_flood_cy = gcy;
        s_flood_age = 0;
    }
    return pf_next(hx, hy, 3, wx, wy);
}

// ---------------------------------------------------------------------------------------------------------
// Reaction time: dodging and backing off look at the enemies as they were `reaction` frames ago.
// ---------------------------------------------------------------------------------------------------------
#define BOT_MAX_ENEMIES 32
#define BOT_HIST 64
typedef struct {
    int16_t x, y, adx, ady, apx, apy;
    uint8_t state, type, live, track;
} BotSnap;
static BotSnap s_hist[BOT_HIST][BOT_MAX_ENEMIES];
static uint8_t s_hist_head;
static uint8_t s_track_cnt[BOT_MAX_ENEMIES];
static uint32_t s_roll = 1;
static uint8_t s_lunge_seen[BOT_MAX_ENEMIES], s_lunge_ignore[BOT_MAX_ENEMIES];
static int s_err_x, s_err_y;

static void hist_clear(void) {
    for (int h = 0; h < BOT_HIST; h++)
        for (int i = 0; i < BOT_MAX_ENEMIES; i++) s_hist[h][i].live = 0;
    for (int i = 0; i < BOT_MAX_ENEMIES; i++) { s_track_cnt[i] = 0; s_lunge_seen[i] = 0; s_lunge_ignore[i] = 0; }
}

static void hist_push(const Enemy *en, int n) {
    s_hist_head = (uint8_t)((s_hist_head + 1) & (BOT_HIST - 1));
    BotSnap *h = s_hist[s_hist_head];
    for (int i = 0; i < BOT_MAX_ENEMIES; i++) {
        if (i >= n || !en[i].active || en[i].hp <= 0) { h[i].live = 0; s_track_cnt[i] = 0; continue; }
        const Enemy *e = &en[i];
        int looking = e->state == ENEMY_STATE_TRACK || e->state == ENEMY_STATE_LOCK || e->state == ENEMY_STATE_SENTENCE;
        if (looking) { if (s_track_cnt[i] < 255) s_track_cnt[i]++; } else s_track_cnt[i] = 0;
        h[i].x = (int16_t)TO_INT(e->x);
        h[i].y = (int16_t)TO_INT(e->y);
        h[i].adx = (int16_t)e->aim_dir_x;
        h[i].ady = (int16_t)e->aim_dir_y;
        h[i].apx = (int16_t)e->aim_px;
        h[i].apy = (int16_t)e->aim_py;
        h[i].state = (uint8_t)e->state;
        h[i].type = (uint8_t)e->type;
        h[i].live = 1;
        h[i].track = s_track_cnt[i];
    }
}

static const BotSnap *hist_delayed(int frames) {
    if (frames > BOT_HIST - 1) frames = BOT_HIST - 1;
    return s_hist[(s_hist_head - frames) & (BOT_HIST - 1)];
}

static int bot_rand(int amp) {            // -amp..amp
    s_roll = s_roll * 1664525u + 1013904223u + g_arpg_bot_debug.seed;
    if (amp <= 0) return 0;
    return (int)((s_roll >> 16) % (uint32_t)(2 * amp + 1)) - amp;
}
static int bot_pct(void) { return (bot_rand(50) + 50); }   // 0..100

static void apply_profile(void) {
    volatile ArpgBotDebug *d = &g_arpg_bot_debug;
    if (d->applied == d->profile) return;
    d->applied = d->profile;
    switch (d->profile) {
    case 1:  d->reaction = 30; d->aim_err = 12; d->miss_pct = 25; d->remate_miss_pct = 35; d->panic_pct = 15; d->punch_jitter = 10; d->ojo_delay = 30;
             d->retreat_pct = 20; d->kite_dist = 0;  d->mana_reserve = 15; break;
    case 2:  d->reaction = 8;  d->aim_err = 3;  d->miss_pct = 2;  d->remate_miss_pct = 3;  d->panic_pct = 40; d->punch_jitter = 1;  d->ojo_delay = 8;
             d->retreat_pct = 35; d->kite_dist = 84; d->mana_reserve = 0;  break;
    case 3:  break;
    default: d->reaction = 18; d->aim_err = 7;  d->miss_pct = 10; d->remate_miss_pct = 12; d->panic_pct = 30; d->punch_jitter = 4;  d->ojo_delay = 20;
             d->retreat_pct = 30; d->kite_dist = 56; d->mana_reserve = 0;  break;
    }
}

// ---------------------------------------------------------------------------------------------------------
// Bookkeeping that survives between frames
// ---------------------------------------------------------------------------------------------------------
static int s_room_prev = -1;
static int s_hp_prev, s_mana_prev;
static uint8_t s_alive_prev[BOT_MAX_ENEMIES];
static uint8_t s_wob_age[BOT_MAX_ENEMIES], s_wob_forget[BOT_MAX_ENEMIES];
static int s_remate_prev;
static int s_last_hit_type;                 // type of the enemy that probably gave the last blow
static int s_no_kill_frames;                // frames in this room since the last kill
static int s_no_hit_frames;                 // frames in this room since the hero last lost life
static int s_give_up;                       // 1 = the hunt is dropped for this room
static int s_l_hold, s_l_gap;               // L pulse: frames still held, frames of pause

static int is_melee_type(int t) {
    return t == ENEMY_TYPE_EXVOTO || t == ENEMY_TYPE_BEBE || t == ENEMY_TYPE_PARROCO || t == ENEMY_TYPE_MONAGUILLO ||
           t == ENEMY_TYPE_CHARGER || t == ENEMY_TYPE_ABANDERADO;
}

static int passive_state(int st) { return st == ENEMY_STATE_GUARD || st == ENEMY_STATE_PRAY; }

// Awake and worth fighting: not asleep, not rising out of a puddle, not being finished, not already reeling (that is a remate).
static int threat_state(int st) {
    return st != ENEMY_STATE_DORMANT && st != ENEMY_STATE_EMERGE && st != ENEMY_STATE_SUSPENDED && st != ENEMY_STATE_DEAD &&
           st != ENEMY_STATE_WOBBLE && st != ENEMY_STATE_REMATE;
}

static void blame_hit(const Enemy *en, int n, int hx, int hy) {
    int best = -1, best_d2 = 0x7fffffff, type = 0;
    for (int i = 0; i < n; i++) {                                  // a blow in melee: the nearest biting enemy
        const Enemy *e = &en[i];
        if (!e->active || e->hp <= 0 || e->state != ENEMY_STATE_ATTACK) continue;
        int d2 = gd2(TO_INT(e->x) - hx, TO_INT(e->y) - hy);
        if (d2 < best_d2) { best_d2 = d2; best = i; }
    }
    if (best >= 0 && best_d2 <= 60 * 60) { s_last_hit_type = en[best].type; return; }
    for (int i = 0; i < n; i++) {                                  // else a beam or a lunge in progress
        const Enemy *e = &en[i];
        if (!e->active || e->hp <= 0) continue;
        if (e->state == ENEMY_STATE_SENTENCE) type = ENEMY_TYPE_SHOOTER;
        else if (e->state == ENEMY_STATE_CHARGE && type == 0) type = ENEMY_TYPE_CHARGER;
    }
    if (type) { s_last_hit_type = type; return; }
    best = -1; best_d2 = 0x7fffffff;                               // else the nearest awake enemy
    for (int i = 0; i < n; i++) {
        const Enemy *e = &en[i];
        if (!e->active || e->hp <= 0 || !threat_state(e->state)) continue;
        int d2 = gd2(TO_INT(e->x) - hx, TO_INT(e->y) - hy);
        if (d2 < best_d2) { best_d2 = d2; best = i; }
    }
    if (best >= 0) s_last_hit_type = en[best].type;
}

static void finish(volatile ArpgBotStats *st, int result) {
    if (st->result == 0) st->result = (uint8_t)result;
}

// ---------------------------------------------------------------------------------------------------------
// Campaign: bajadas (cathedral runs) between visits to the camp.
// ---------------------------------------------------------------------------------------------------------
enum { PH_IDLE = 0, PH_DUNGEON, PH_PAUSE, PH_DEATH, PH_CAMP_BED, PH_CAMP_DOOR };
#define CAMP_SPAWN_WAIT 6
#define BOT_DEFAULT_BAJADAS 60
static int s_phase, s_started, s_t, s_menu_t, s_sleep_wait;
static uint32_t s_b_dungeon0, s_b_screens0;
static uint16_t s_b_dmg0;
static int s_b_deep, s_scr_max, s_prev_level, s_settle;
static int s_wp;                                      // camp walk: waypoint index
static int s_kite, s_kite_frames, s_kite_rest, s_kite_ref_x, s_kite_ref_y, s_kite_ref_t;
static int s_altar_frames, s_entry_x, s_entry_y;

// Scripted route of zone 1 (how a person would walk it). Each step: in room `room`, take door `door` (index in the room table of
// encounters_act1.c) to `dest`. kind E = excursion into a side room (its next step is the way back), F = forward, R = way back.
// Nave 1 -> Galeria del cofre -> back -> Claustro bajo -> Galeria del secreto -> back -> up to Claustro alto -> Nave 2 ->
// Enfermeria -> Capilla del parroco (key) -> back -> up to Osario -> Galeria de la Misa -> back -> Nave 3 ->
// Galeria de bajada -> back -> Nave 4 -> Capilla con llave -> back -> Galeria de la monjarana -> back -> Cripta.
typedef struct { uint8_t room, door, dest, kind; } BotStep;
enum { K_E = 0, K_F = 1, K_R = 2 };
static const BotStep s_script[] = {
    { 0, 0, 4, K_E },   { 4, 0, 0, K_R },
    { 0, 1, 6, K_F },
    { 6, 1, 5, K_E },   { 5, 0, 6, K_R },
    { 6, 2, 7, K_F },   { 7, 0, 1, K_F },
    { 1, 0, 8, K_F },
    { 8, 1, 10, K_E },  { 10, 0, 8, K_R },
    { 8, 2, 9, K_F },
    { 9, 1, 11, K_E },  { 11, 0, 9, K_R },
    { 9, 0, 2, K_F },
    { 2, 1, 12, K_E },  { 12, 0, 2, K_R },
    { 2, 2, 3, K_F },
    { 3, 0, 13, K_E },  { 13, 0, 3, K_R },
    { 3, 1, 14, K_E },  { 14, 0, 3, K_R },
    { 3, 2, 15, K_F },
};
#define BOT_SCRIPT_LEN ((int)(sizeof(s_script) / sizeof(s_script[0])))

static uint16_t s_cleared_ever;                       // rooms left with nothing alive, in this run (the "already cleared" rooms)
static uint16_t s_b_visited;                          // rooms entered in this bajada
static uint8_t s_fail[ARPG_BOT_ROOMS];                // bajadas ended (death, retreat) in each room since the last level up
static int s_visit_first, s_last_alive, s_visit_frames;

// Door of the current room the script says to take, -1 = none. An excursion is skipped when its room is already cleared, was
// entered in this bajada, beat the hero twice, needs the key it does not have, or its door does not lead where the script says.
static int script_door(const ArpgBotRoom *ri, int cur, int count) {
    for (int i = 0; i < BOT_SCRIPT_LEN; i++) {
        const BotStep *t = &s_script[i];
        if (t->room != cur) continue;
        if (t->door >= ri->n_door || ri->door_dest[t->door] != t->dest) {         // the table does not match the real door: log and skip
            if (count && g_arpg_bot_stats.script_skips < 0xFFFF) g_arpg_bot_stats.script_skips++;
            continue;
        }
        if (t->kind == K_E) {
            if (((s_cleared_ever >> t->dest) & 1) || ((s_b_visited >> t->dest) & 1) || s_fail[t->dest] >= 2) continue;
            if (t->dest == 13 && !arpg_quest_has(QUEST_MISA)) {                               // the chapel with the reja: no key, no way in
                if (count && g_arpg_bot_stats.script_skips < 0xFFFF) g_arpg_bot_stats.script_skips++;
                continue;
            }
        }
        return t->door;
    }
    return -1;
}

static int rank_of(int room) { return room == ENC_ROOM_CRIPTA ? 5 : (room >= 0 && room <= 3) ? room + 1 : 0; }

static void start_bajada(void) {
    volatile ArpgBotStats *st = &g_arpg_bot_stats;
    const int b = st->bajadas;
    if (b < ARPG_BOT_BAJADAS) st->b_level[b] = (uint8_t)g_arpg.level;
    if (st->bajadas < 255) st->bajadas++;
    s_b_dungeon0 = st->dungeon_frames;
    s_b_screens0 = st->screens;
    s_b_dmg0 = st->damage_total;
    s_b_deep = 0;
    s_b_visited = 0;
    s_room_prev = -1;
    s_phase = PH_DUNGEON;
    s_settle = CAMP_SPAWN_WAIT;
    s_l_hold = 0;
    s_l_gap = 0;
    s_altar_frames = 0;
}

static void end_bajada(int cause) {
    volatile ArpgBotStats *st = &g_arpg_bot_stats;
    const int b = (int)st->bajadas - 1;
    if ((cause == 1 || cause == 2) && st->room < ARPG_BOT_ROOMS && s_fail[st->room] < 255) s_fail[st->room]++;
    if (b < 0 || b >= ARPG_BOT_BAJADAS) return;
    st->b_frames[b] = st->dungeon_frames - s_b_dungeon0;
    st->b_damage[b] = (uint16_t)(st->damage_total - s_b_dmg0);
    st->b_deep[b] = (uint8_t)s_b_deep;
    st->b_cause[b] = (uint8_t)cause;
    const uint32_t sc = st->screens - s_b_screens0;
    st->b_screens[b] = (uint8_t)(sc > 255 ? 255 : sc);
}

static void start_run(void) {
    volatile ArpgBotDebug *d = &g_arpg_bot_debug;
    volatile ArpgBotStats *st = &g_arpg_bot_stats;
    for (unsigned i = 0; i < sizeof(ArpgBotStats); i++) ((volatile uint8_t *)st)[i] = 0;
    st->death_room = 0xFF;
    const int lvl = d->start_level > 1 ? d->start_level : 1;
    g_arpg.level = (uint16_t)lvl;                      // the life and mana of that level are set by the restart (player_state_init)
    g_arpg.xp = 0;
    g_arpg_level = lvl;
    g_arpg.last_altar = 0;
    g_arpg.altars_lo = g_arpg.altars_hi = 0;
    g_arpg.chests_open = 0;
    g_arpg.boss_dead = g_arpg.boss_ever = 0;
    for (int i = 0; i < 12; i++) g_arpg.dead_groups[i] = 0;
    g_enc_debug.restart = 1;                           // the game restarts the run at the top of the next frame
    s_prev_level = lvl;
    s_cleared_ever = 0;
    for (int i = 0; i < ARPG_BOT_ROOMS; i++) s_fail[i] = 0;
    s_started = 1;
    s_roll = 1;
    s_kite = 0; s_kite_frames = 0; s_kite_rest = 0;
    start_bajada();
    s_settle = 8;
}

// Waypoints of the camp errands (world px of the camp room, ground point): the bed by the bonfire; the door at the top.
static const int16_t s_wp_bed[][2] = { { 196, 346 } };
static const int16_t s_wp_door[][2] = { { 164, 330 }, { 164, 240 }, { 136, 150 }, { 128, 107 } };

// Walks the waypoints (the last one is the prop); presses A (every 4 frames) once the prop is in reach.
// Returns 1 on the frames in which A is pressed.
static int camp_errand(const ArpgBotView *v, ArpgBotInput *out, const int16_t (*wps)[2], int nwp, int act) {
    const int hx = v->hx, hy = v->hy;
    if (camp_focus_act() == act) {
        if (s_t % 4 == 0) { out->keys |= KEY_A; return 1; }
        return 0;
    }
    if (s_wp >= nwp) s_wp = nwp - 1;
    int dx = wps[s_wp][0] - hx, dy = GY(wps[s_wp][1] - hy);
    if (s_wp < nwp - 1 && dx * dx + dy * dy < 24 * 24) {
        s_wp++;
        dx = wps[s_wp][0] - hx;
        dy = GY(wps[s_wp][1] - hy);
    }
    int d = steer(hx, hy, dx, dy);
    if (d >= 0) { out->keys |= keys_of(d); s_last_dir = d; } else s_last_dir = -1;
    // Blocked by a prop: slide sideways for a while.
    if (iabs(hx - s_stuck_ref_x) + 2 * iabs(hy - s_stuck_ref_y) >= 8) {
        s_stuck_timer = 0;
        s_stuck_ref_x = hx;
        s_stuck_ref_y = hy;
    } else if (++s_stuck_timer >= 40) {
        s_side_timer = 20;
        s_side_sign = -s_side_sign;
        s_stuck_timer = 0;
    }
    if (s_side_timer > 0) {
        s_side_timer--;
        int ux, uy;
        out->keys &= ~(uint32_t)(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
        if (unit256(dx, dy, &ux, &uy)) {
            int sd = steer(hx, hy, uy * s_side_sign, -ux * s_side_sign);
            if (sd >= 0) out->keys |= keys_of(sd);
        }
    }
    return 0;
}

static void dungeon_step(const ArpgBotView *v, Enemy *en, int n, ArpgBotInput *out);

void arpg_bot_step(const ArpgBotView *v, Enemy *en, int n, ArpgBotInput *out) {
    volatile ArpgBotDebug *d = &g_arpg_bot_debug;
    volatile ArpgBotStats *st = &g_arpg_bot_stats;
    out->keys = 0;
    out->touch_down = 0;
    out->touch_x = 128;
    out->touch_y = 96;
    apply_profile();
    if (d->god) g_player_state.god_mode = 1;
    if (!d->go) { s_started = 0; s_phase = PH_IDLE; return; }
    if (!s_started) { start_run(); return; }
    if (st->result != 0) { st->rule = 0; return; }

    st->frames++;
    st->phase = (uint8_t)s_phase;
    const uint32_t timeout = d->mode == 1 ? (d->campaign_frames ? d->campaign_frames : 324000u)
                                          : (d->timeout_frames ? d->timeout_frames : (uint32_t)BOT_DEFAULT_TIMEOUT);
    if (st->frames >= timeout) {
        if (s_phase == PH_DUNGEON) end_bajada(4);
        finish(st, 3);
        return;
    }
    if ((int)g_arpg.level != s_prev_level) {            // levels come on sleep only
        for (int lv = s_prev_level + 1; lv <= (int)g_arpg.level; lv++)
            if (lv >= 2 && lv <= 9) st->level_minute[lv - 2] = (uint16_t)(st->frames / 60);   // game second
        s_prev_level = g_arpg.level;
        for (int i = 0; i < ARPG_BOT_ROOMS; i++) s_fail[i] = 0;   // stronger now: the rooms that beat it are worth another try
    }
    st->level = (uint8_t)g_arpg.level;
    if (st->level > st->max_level) st->max_level = st->level;
    if (s_settle > 0) { s_settle--; return; }           // a restart or the door fade: nothing to read yet

    const int in_camp = camp_active();
    if (in_camp && (s_phase == PH_PAUSE || s_phase == PH_DEATH)) {
        s_phase = PH_CAMP_BED;
        s_wp = 0; s_t = 0; s_sleep_wait = 0;
        s_stuck_timer = 0; s_stuck_ref_x = v->hx; s_stuck_ref_y = v->hy; s_side_timer = 0;
    } else if (in_camp && s_phase == PH_DUNGEON) {      // the camp at the start of the run (no intro skipped): out by the door
        s_phase = PH_CAMP_DOOR;
        s_wp = 0; s_t = 0;
        s_stuck_timer = 0; s_stuck_ref_x = v->hx; s_stuck_ref_y = v->hy; s_side_timer = 0;
    } else if (!in_camp && (s_phase == PH_CAMP_BED || s_phase == PH_CAMP_DOOR)) {
        start_bajada();                                  // out of the door: the next bajada begins at the last altar
        return;
    }

    switch (s_phase) {
    case PH_DUNGEON:
        dungeon_step(v, en, n, out);
        return;
    case PH_PAUSE:                                       // the real pause menu: START, down, down, A ("Volver al campamento")
        st->rule = 14;
        st->camp_frames++;
        if (!menu_is_open()) {
            s_menu_t = 0;
            if (++s_t % 10 == 1) out->keys |= KEY_START;
        } else if (menu_state() == MENU_PAUSE) {
            const int t = s_menu_t++;
            if (t == 10 || t == 16) out->keys |= KEY_DOWN;
            else if (t == 24) out->keys |= KEY_A;
            else if (t > 70) { out->keys |= KEY_B; s_menu_t = 0; }   // it did not take: close the pause and try again
        }
        return;
    case PH_DEATH:
        st->rule = 0;
        st->camp_frames++;
        s_t++;
        if (s_t > 80 && (s_t / 3) % 2 == 0) out->keys |= KEY_A;       // the death screen takes any key once armed
        return;
    case PH_CAMP_BED:
    case PH_CAMP_DOOR:
        st->rule = 13;
        st->camp_frames++;
        s_t++;
        if (s_phase == PH_CAMP_BED) {
            if (s_sleep_wait > 0) {                     // the toast of the sleep is on screen; then out by the door
                if (--s_sleep_wait == 0) { s_phase = PH_CAMP_DOOR; s_wp = 0; s_stuck_timer = 0; s_side_timer = 0; }
                return;
            }
            if (camp_errand(v, out, s_wp_bed, 1, CAMP_ACT_SLEEP)) s_sleep_wait = 50;
        } else {
            const int cap = d->max_bajadas ? d->max_bajadas : BOT_DEFAULT_BAJADAS;     // stats keep the first 16 bajadas only
            if (st->bajadas >= cap) { finish(st, 4); return; }
            camp_errand(v, out, s_wp_door, 4, CAMP_ACT_DOOR);
        }
        return;
    default:
        return;
    }
}

// The cathedral: fights, doors, altars; decides when to go back to the camp.
static void dungeon_step(const ArpgBotView *v, Enemy *en, int n, ArpgBotInput *out) {
    volatile ArpgBotStats *st = &g_arpg_bot_stats;
    st->dungeon_frames++;
    if (g_arpg_bot_debug.god) g_player_state.god_mode = 1;

    const int hx = v->hx, hy = v->hy;
    const int room = enc_room_current();
    const int hp = g_player_state.hp, maxhp = g_player_state.max_hp;
    const int mana = g_player_state.mana;
    const int goal_room = g_arpg_bot_debug.goal_room;
    const int mode = g_arpg_bot_debug.mode;
    const int rr = room < ARPG_BOT_ROOMS ? room : 0;
    ArpgBotRoom ri;
    arpg_bot_room(&ri);
    const int explore = mode != 0 && goal_room == 0 && room != ENC_ROOM_CRIPTA;
    const int tdoor = explore ? script_door(&ri, room, 0) : -1;       // the door the script says to take
    const int tside = tdoor >= 0 ? ri.door_side_k[tdoor] : -1;
    s_nside = 0;                                        // the mouths of the side doors are off limits (kiting dragged it in), except the one it takes
    for (int i = 0; i < ri.n_side; i++) {
        if (explore && tdoor >= 0 ? i == tside : (!ri.has_up)) continue;
        s_side_l[s_nside] = ri.side_left[i]; s_side_y0[s_nside] = ri.side_y0[i]; s_side_y1[s_nside] = ri.side_y1[i]; s_side_x[s_nside] = ri.side_edge_x[i];
        s_nside++;
    }

    // ---- Bookkeeping ----------------------------------------------------------------------------------
    int room_changed = 0;
    if (room != s_room_prev) {
        if (s_room_prev >= 0) {
            const int pr = s_room_prev < ARPG_BOT_ROOMS ? s_room_prev : 0;
            st->room_hp_exit[pr] = (uint8_t)(hp > 255 ? 255 : hp);
            st->rooms_cleared++;
            if (s_last_alive == 0) s_cleared_ever |= (uint16_t)(1u << pr);
        }
        room_changed = 1;
        s_room_prev = room;
        st->visited |= (uint16_t)(1u << rr);
        st->rooms_seen |= (uint16_t)(1u << rr);
        s_visit_first = !((s_cleared_ever >> rr) & 1);
        s_visit_frames = 0;
        s_b_visited |= (uint16_t)(1u << rr);
        if (explore) (void)script_door(&ri, room, 1);                    // counts the steps it has to skip
        hist_clear();
        for (int i = 0; i < BOT_MAX_ENEMIES; i++) { s_alive_prev[i] = 0; s_wob_age[i] = 0; s_wob_forget[i] = 0; }
        s_no_kill_frames = 0;
        s_no_hit_frames = 0;
        s_give_up = 0;
        s_retreat = 0;
        s_pf_age = 1000;
        s_flood_age = 1000;
        s_hp_prev = hp;
        s_mana_prev = mana;
        s_kite = 0; s_kite_frames = 0; s_kite_rest = 0;
        s_altar_frames = 0;
        s_entry_x = hx;                                 // where it came in (a side room is left by the same side)
        s_entry_y = hy;
        s_scr_max = 0;                                  // the first screen of the room counts at once
        st->screens++;
        if (st->room_screens[rr] < 255) st->room_screens[rr]++;
        if (rank_of(room) > s_b_deep) s_b_deep = rank_of(room);
    }
    {   // screens crossed: one per 192 px of room walked
        int scr = (ri.foot_y - hy) / 192;
        if (scr < 0) scr = 0;
        while (s_scr_max < scr) {
            s_scr_max++;
            st->screens++;
            if (st->room_screens[rr] < 255) st->room_screens[rr]++;
        }
    }
    st->room = (uint8_t)room;
    if (s_visit_first) st->first_visit_frames++; else st->repeat_frames++;
    if (s_visit_frames < 1000000) s_visit_frames++;
    {
        int alive = 0;
        for (int i = 0; i < n; i++) if (en[i].active && en[i].hp > 0) alive++;
        s_last_alive = alive;
    }
    if (st->room_frames[rr] < 0xFFFF) st->room_frames[rr]++;
    st->room_frames32[rr]++;
    st->hp = (uint8_t)(hp > 255 ? 255 : hp);
    st->max_hp = (uint8_t)(maxhp > 255 ? 255 : maxhp);
    st->mana = (uint8_t)(mana > 255 ? 255 : mana);
    st->xp = (uint16_t)g_arpg.xp;
    st->hero_x = (int16_t)hx;
    st->hero_y = (int16_t)hy;
    st->goal_x = st->goal_y = 0;
    if (st->hp_min == 0 || st->hp < st->hp_min) st->hp_min = st->hp ? st->hp : st->hp_min;
    if (mana < BAL(ray_cost, ARPG_RAY_COST) && st->mana_empty_frames < 0xFFFF) st->mana_empty_frames++;

    if (s_no_hit_frames < 0xFFFF) s_no_hit_frames++;
    if (hp < s_hp_prev) {                                          // a blow
        s_no_hit_frames = 0;
        const int lost = s_hp_prev - hp;
        blame_hit(en, n, hx, hy);
        st->damage_total = (uint16_t)(st->damage_total + lost);
        st->hits++;
        if (st->room_damage[rr] + lost < 0xFFFF) st->room_damage[rr] = (uint16_t)(st->room_damage[rr] + lost);
        if (s_last_hit_type >= 0 && s_last_hit_type < 9) st->dmg_type[s_last_hit_type] = (uint16_t)(st->dmg_type[s_last_hit_type] + lost);
    } else if (hp >= s_hp_prev + 10 && !room_changed) {
        st->orbs++;
    }
    if (mana >= s_mana_prev + 5 && !room_changed) st->orbs++;
    if (mana < s_mana_prev && !room_changed) st->mana_spent += (uint32_t)(s_mana_prev - mana);
    s_hp_prev = hp;
    s_mana_prev = mana;

    if (g_player_state.is_dead) {
        st->death_room = (uint8_t)room;
        st->killer = (uint8_t)s_last_hit_type;
        st->rule = 0;
        if (room == ENC_ROOM_CRIPTA) st->boss_result = 2;
        end_bajada(1);
        if (mode == 1) { s_phase = PH_DEATH; s_t = 0; }
        else finish(st, 2);
        return;
    }
    if (goal_room) {
        if (room == goal_room) { end_bajada(3); finish(st, 1); return; }
    } else if ((g_arpg.boss_dead >> ENC_ROOM_CRIPTA) & 1) {         // the boss of the Cripta is dead: the zone is done
        st->boss_result = 1;
        end_bajada(3);
        finish(st, 1);
        return;
    }
    // Back to the camp when hurt and no orb of life is around (the real pause menu: "Volver al campamento").
    // Not in the Cripta: the boss is fought to the end.
    if ((mode == 1 || mode == 2) && g_arpg_bot_debug.retreat_pct > 0 && room != ENC_ROOM_CRIPTA &&
        hp * 100 < g_arpg_bot_debug.retreat_pct * maxhp && !remate_active() && !remate_approaching()) {
        int ox, oy;
        const int od = pickups_nearest(PICKUP_KIND_HEALTH, hx, hy, &ox, &oy);
        if (od < 0 || od >= BOT_ORB_RANGE * BOT_ORB_RANGE) {
            end_bajada(2);
            if (mode == 2) { finish(st, 5); return; }
            s_phase = PH_PAUSE;
            s_t = 0;
            s_menu_t = 0;
            st->rule = 14;
            return;
        }
    }

    // ---- Kills and reeling enemies ---------------------------------------------------------------------
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES; i++) {
        const Enemy *e = &en[i];
        const int alive = e->active && e->hp > 0;
        if (s_alive_prev[i] && !alive && e->hp <= 0 && !room_changed) {
            if (st->kills < 0xFFFF) st->kills++;
            if (st->room_kills[rr] < 255) st->room_kills[rr]++;
            s_no_kill_frames = 0;
        }
        s_alive_prev[i] = (uint8_t)alive;
        const int wob = alive && e->state == ENEMY_STATE_WOBBLE;
        if (wob) {
            if (s_wob_age[i] == 0) s_wob_forget[i] = (uint8_t)(bot_pct() < g_arpg_bot_debug.remate_miss_pct);
            if (s_wob_age[i] < 255) s_wob_age[i]++;
        } else if (s_wob_age[i] > 0) {
            if (!(alive && e->state == ENEMY_STATE_REMATE) && st->remates_missed < 0xFFFF) st->remates_missed++;
            s_wob_age[i] = 0;
        }
    }
    {
        const int rem = remate_active() || remate_approaching();
        if (rem && !s_remate_prev && st->remates_done < 0xFFFF) st->remates_done++;
        s_remate_prev = rem;
        if (rem) {                                                 // the game owns the hero meanwhile
            st->rule = 8;
            s_l_hold = 0;
            s_l_gap = 4;
            return;
        }
    }
    if (s_no_kill_frames < 0xFFFF) s_no_kill_frames++;

    // ---- Scan -------------------------------------------------------------------------------------------
    const int charging = weapons_aim_charging();
    const int progress = weapons_aim_progress();
    const int can_start = weapons_can_start_aim(&g_player_state);
    const int range = g_weapon_tuning[WEAPON_SNIPER].projectile_range + g_mods.sniper_range - BOT_RANGE_MARGIN;
    const int can_ray = mana >= BAL(ray_cost, ARPG_RAY_COST);

    int want_dx = 0, want_dy = 0, rule = 0;
    int dodge = 0;
    int near_i = -1, near_d2 = 0x7fffffff;           // nearest threat to fight (awake, or passive and close)
    int melee_now_d2 = 0x7fffffff;                   // nearest melee threat, current state
    int target_i = -1, target_score = -1;            // ray target
    int awake_count = 0;
    int wob_i = -1, wob_d2 = 0x7fffffff;             // nearest reeling enemy the bot has noticed

    for (int i = 0; i < n; i++) {
        Enemy *e = &en[i];
        if (!e->active || e->hp <= 0) continue;
        const int dx = TO_INT(e->x) - hx, dy = TO_INT(e->y) - hy;
        const int d2 = gd2(dx, dy);
        if (e->state == ENEMY_STATE_WOBBLE) {
            const int noticed = (!s_wob_forget[i] && s_wob_age[i] >= g_arpg_bot_debug.reaction) || s_wob_age[i] >= 120;
            if (noticed && d2 < wob_d2) { wob_d2 = d2; wob_i = i; }
            continue;
        }
        if (!threat_state(e->state) || enc_untouchable(e)) continue;
        const int passive = passive_state(e->state);
        if (passive && d2 > BOT_PASSIVE_ENGAGE * BOT_PASSIVE_ENGAGE) continue;
        if (!passive) awake_count++;
        // The boss is the point of its room: the escort (Ojos, Monaguillos) comes back for ever, so the hero goes for the boss.
        const int d2_pick = e->type == ENEMY_TYPE_ABANDERADO ? d2 / 16 : d2;
        if (d2_pick < near_d2) { near_d2 = d2_pick; near_i = i; }
        if (!passive && is_melee_type(e->type) && d2 < melee_now_d2) melee_now_d2 = d2;
        if (d2 <= range * range && bullet_line_is_free(hx, hy, TO_INT(e->x), TO_INT(e->y))) {
            int score = 1000000 - d2;
            if (e->type == ENEMY_TYPE_SHOOTER) score += 2000000;
            else if (e->type == ENEMY_TYPE_CHARGER) score += 1000000;
            else if (e->type == ENEMY_TYPE_ABANDERADO) score += 4000000;
            if (score > target_score) { target_score = score; target_i = i; }
        }
    }

    hist_push(en, n);
    const BotSnap *sn = hist_delayed(g_arpg_bot_debug.reaction);
    int melee_d2 = 0x7fffffff, melee_i = -1;
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES; i++) {
        if (!sn[i].live) continue;
        const int s_ = sn[i].state;
        if (!threat_state(s_) || passive_state(s_)) continue;
        if (!is_melee_type(sn[i].type)) continue;
        int d2 = gd2(sn[i].x - hx, sn[i].y - hy);
        if (d2 < melee_d2) { melee_d2 = d2; melee_i = i; }
    }
    st->awake = (uint8_t)(awake_count > 255 ? 255 : awake_count);
    st->near_type = near_i >= 0 ? (uint8_t)en[near_i].type : 0;
    st->near_state = near_i >= 0 ? (uint8_t)en[near_i].state : 0;
    {
        int alive = 0;
        for (int i = 0; i < n; i++) if (en[i].active && en[i].hp > 0) alive++;
        if (alive > st->max_alive) st->max_alive = (uint8_t)(alive > 255 ? 255 : alive);
        if (awake_count > st->max_awake) st->max_awake = (uint8_t)(awake_count > 255 ? 255 : awake_count);
    }

    // ---- 1. Ojo: leave the gaze line ----------------------------------------------------------------------
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES && !rule; i++) {
        if (!sn[i].live || sn[i].type != ENEMY_TYPE_SHOOTER) continue;
        if (sn[i].state != ENEMY_STATE_TRACK && sn[i].state != ENEMY_STATE_LOCK && sn[i].state != ENEMY_STATE_SENTENCE) continue;
        if (sn[i].track < g_arpg_bot_debug.ojo_delay) continue;
        int ex = sn[i].x, ey = sn[i].y;
        int gx = sn[i].apx - ex, gy = GY(sn[i].apy - ey);
        int ux, uy;
        if (!unit256(gx, gy, &ux, &uy)) continue;
        int rx = hx - ex, ry = GY(hy - ey);
        int along = (rx * ux + ry * uy) >> 8;
        int cross = (rx * uy - ry * ux) >> 8;
        if (along < -10 || along > 220 || iabs(cross) >= BOT_OJO_CLEAR) continue;
        if (s_dodge_hold <= 0 || s_dodge_side == 0) {
            int cs = column_side(hx, hy, ux, uy);
            s_dodge_side = cs ? cs : (cross >= 0 ? 1 : -1);
            s_dodge_hold = 12;
        }
        want_dx = uy * s_dodge_side;
        want_dy = -ux * s_dodge_side;
        rule = 1;
        dodge = 1;
    }
    // ---- 2. Cireneo: leave the lunge lane -----------------------------------------------------------------
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES && !rule; i++) {
        if (!sn[i].live || sn[i].type != ENEMY_TYPE_CHARGER) continue;
        if (sn[i].state != ENEMY_STATE_TELEGRAPH && sn[i].state != ENEMY_STATE_CHARGE) { s_lunge_seen[i] = 0; continue; }
        if (!s_lunge_seen[i]) {
            s_lunge_seen[i] = 1;
            s_lunge_ignore[i] = (uint8_t)(g_arpg_bot_debug.miss_pct && bot_pct() < g_arpg_bot_debug.miss_pct);
        }
        if (s_lunge_ignore[i]) continue;
        int ex = sn[i].x, ey = sn[i].y;
        int rx = hx - ex, ry = GY(hy - ey);
        int ux = sn[i].adx, uy = sn[i].ady;
        int along = (rx * ux + ry * uy) >> 8;
        int cross = (rx * uy - ry * ux) >> 8;
        if (along < -12 || along > 330 || iabs(cross) >= BOT_LANE_CLEAR) continue;
        if (s_dodge_hold <= 0 || s_dodge_side == 0) {
            s_dodge_side = cross >= 0 ? 1 : -1;
            s_dodge_hold = 12;
        }
        want_dx = uy * s_dodge_side;
        want_dy = -ux * s_dodge_side;
        rule = 2;
        dodge = 1;
    }
    if (s_dodge_hold > 0) s_dodge_hold--;
    if (!rule && s_dodge_hold <= 0) s_dodge_side = 0;

    // ---- 3. Panic: low life, back off from melee enemies (towards a health orb when there is one) -----------
    const int low = hp * 100 < g_arpg_bot_debug.panic_pct * maxhp;
    if (melee_i < 0 || melee_d2 >= BOT_RETREAT_FAR * BOT_RETREAT_FAR) s_retreat = 0;
    else if (low && melee_d2 < BOT_RETREAT_NEAR * BOT_RETREAT_NEAR) s_retreat = 1;
    if (!low) s_retreat = 0;
    int melee_close = 0;
    if (!rule && s_retreat) {
        int ox, oy;
        int od = pickups_nearest(PICKUP_KIND_HEALTH, hx, hy, &ox, &oy);
        if (od >= 0 && od < 220 * 220 && gd2(ox - hx, oy - hy) < melee_d2 + 1) {
            want_dx = ox - hx;
            want_dy = GY(oy - hy);
            st->goal_x = (int16_t)ox;
            st->goal_y = (int16_t)oy;
            rule = 9;
        } else {
            want_dx = hx - sn[melee_i].x;
            want_dy = GY(hy - sn[melee_i].y);
            if (want_dx == 0 && want_dy == 0) want_dy = 1;
            rule = 3;
        }
        melee_close = 1;
    }

    // ---- 11. Kite: do not let a group of melee enemies surround the hero; back off from their centre while there is room ----
    {
        const int kd = g_arpg_bot_debug.kite_dist;
        int nc = 0, sx = 0, sy = 0, nearest = 0x7fffffff;
        if (kd > 0) {
            for (int i = 0; i < n && i < BOT_MAX_ENEMIES; i++) {
                if (!sn[i].live || !threat_state(sn[i].state) || passive_state(sn[i].state) || !is_melee_type(sn[i].type)) continue;
                const int d2 = gd2(sn[i].x - hx, sn[i].y - hy);
                if (d2 > kd * kd) continue;
                if (!walk_line_free(hx, hy, sn[i].x, sn[i].y)) continue;     // a wall between them: it cannot reach the hero
                nc++;
                sx += sn[i].x;
                sy += sn[i].y;
                if (d2 < nearest) nearest = d2;
            }
        }
        if (s_kite_rest > 0) s_kite_rest--;
        const int want_kite = kd > 0 && !rule && !s_retreat && s_kite_rest == 0 && (nc >= 2 || (nc == 1 && hp * 100 < 50 * maxhp));
        if (want_kite) {
            int ax = hx - sx / nc, ay = GY(hy - sy / nc);
            if (ax == 0 && ay == 0) ay = 1;
            if (!s_kite) { s_kite = 1; s_kite_ref_x = hx; s_kite_ref_y = hy; s_kite_ref_t = 0; }
            s_kite_frames++;
            if (++s_kite_ref_t >= 20) {                        // not getting anywhere (a wall behind it): cornered, so it fights
                if (iabs(hx - s_kite_ref_x) + 2 * iabs(hy - s_kite_ref_y) < 6) s_kite_frames = 240;
                s_kite_ref_x = hx; s_kite_ref_y = hy; s_kite_ref_t = 0;
            }
            if (s_kite_frames >= 240) { s_kite = 0; s_kite_frames = 0; s_kite_rest = 180; }
            else if (steer(hx, hy, ax, ay) >= 0) { want_dx = ax; want_dy = ay; rule = 11; melee_close = 0; }
        } else if (s_kite && !want_kite) {
            s_kite = 0;
            if (s_kite_frames > 0) s_kite_frames -= s_kite_frames > 8 ? 8 : s_kite_frames;
        }
    }

    // ---- 8. Remate: tap L on a reeling enemy within reach (the game picks the nearest one itself) ------------
    int tap_l = 0;
    if (!dodge && !melee_close && wob_i >= 0) {
        if (wob_d2 <= REMATE_RANGE * REMATE_RANGE) {
            tap_l = 1;
            rule = 8;
            want_dx = want_dy = 0;
        } else if (wob_d2 <= 260 * 260 && !rule) {
            want_dx = TO_INT(en[wob_i].x) - hx;
            want_dy = GY(TO_INT(en[wob_i].y) - hy);
            rule = 8;
        }
    }

    // ---- 4. Ray ------------------------------------------------------------------------------------------------
    int touch = 0, have_target = 0, aim_x = 0, aim_y = 0;
    if (target_i >= 0) {
        const int tt = en[target_i].type;
        // The ray is for what hurts from afar; the rest only above the mana reserve kept for them.
        const int worth = tt == ENEMY_TYPE_SHOOTER || tt == ENEMY_TYPE_CHARGER || mana >= BAL(ray_cost, ARPG_RAY_COST) + g_arpg_bot_debug.mana_reserve;
        if (worth && (can_ray || charging)) {
            aim_x = TO_INT(en[target_i].x);
            aim_y = TO_INT(en[target_i].y);
            have_target = 1;
        }
    }
    const int nearest_melee_d2 = melee_now_d2;
    if (!have_target || charging) s_wait_frames = 0;
    if (charging) {
        if (progress >= 256) {
            st->shots++;
            touch = 0;                                   // released now: the shot goes
            rule = rule ? rule : 4;
        } else if (dodge || tap_l || (nearest_melee_d2 < BOT_CANCEL_CHARGE * BOT_CANCEL_CHARGE) || !have_target || melee_close) {
            touch = 0;                                   // cancelled: the charge is lost
        } else {
            touch = 1;
            rule = 4;
            want_dx = want_dy = 0;
        }
    } else if (have_target && !dodge && !tap_l && can_start && !melee_close &&
               (nearest_melee_d2 >= BOT_RAY_MIN_DIST * BOT_RAY_MIN_DIST || s_wait_frames >= 20)) {
        touch = 1;
        rule = 4;
        want_dx = want_dy = 0;
    }

    if (touch && have_target) {
        if (!charging) {
            s_err_x = bot_rand(g_arpg_bot_debug.aim_err);
            s_err_y = bot_rand(g_arpg_bot_debug.aim_err / 2);
        }
        aim_x += s_err_x;
        aim_y += s_err_y;
        int ax = aim_x - v->muzzle_x, ay = aim_y - v->muzzle_y;
        int len = isqrt_u((uint32_t)(ax * ax + 4 * ay * ay));
        if (len < 8) len = 8;
        int ox = ax * 60 / len, oy = ay * 60 / len;
        int tx = v->muzzle_x + ox - v->cam_x - v->shake_x;
        int ty = v->muzzle_y + oy - v->muzzle_h - v->cam_y - v->shake_y;
        if (tx < 1) tx = 1;
        if (tx > 254) tx = 254;
        if (ty < 1) ty = 1;
        if (ty > 190) ty = 190;
        out->touch_down = 1;
        out->touch_x = tx;
        out->touch_y = ty;
    }

    // ---- 7. Melee: close in on the nearest threat and punch it -----------------------------------------------
    if (!rule && !dodge && near_i >= 0 && !s_give_up) {
        const Enemy *e = &en[near_i];
        const int dx = TO_INT(e->x) - hx, dy = TO_INT(e->y) - hy;
        const int d = isqrt_u((uint32_t)gd2(dx, dy));
        if (d <= BOT_PUNCH_REACH) {
            tap_l = 1;
            want_dx = want_dy = 0;
            rule = 7;
        } else if (d <= 90 || (!target_i && !have_target)) {
            // Close (or nothing to shoot): walk in, punching on the way when the enemy is already in reach.
            int px, py;
            want_dx = dx;
            want_dy = GY(dy);
            if (d > 40 && pf_direction(hx, hy, TO_INT(e->x), TO_INT(e->y), &px, &py)) { want_dx = px; want_dy = py; }
            rule = 7;
        }
    } else if (!rule && !dodge && !touch && tap_l == 0 && near_i >= 0 && s_give_up) {
        // The hunt is dropped: only what is already in reach gets punched.
        const Enemy *e = &en[near_i];
        if (gd2(TO_INT(e->x) - hx, TO_INT(e->y) - hy) <= BOT_PUNCH_REACH * BOT_PUNCH_REACH) tap_l = 1;
    }
    if (tap_l && rule == 7 && !(wob_i >= 0 && wob_d2 <= REMATE_RANGE * REMATE_RANGE)) { /* a punch */ }

    // ---- 9. Orbs: only when nothing threatens (chest orbs; the remate orbs are low priority) -------------------
    if (!rule && awake_count == 0 && !touch) {
        int ox, oy, od;
        if (hp + 10 <= maxhp && (od = pickups_nearest(PICKUP_KIND_HEALTH, hx, hy, &ox, &oy)) >= 0 && od < BOT_ORB_RANGE * BOT_ORB_RANGE) {
            want_dx = ox - hx; want_dy = GY(oy - hy); rule = 9;
        } else if (mana + 12 <= g_player_state.max_mana && (od = pickups_nearest(PICKUP_KIND_MANA, hx, hy, &ox, &oy)) >= 0 && od < BOT_ORB_RANGE * BOT_ORB_RANGE) {
            want_dx = ox - hx; want_dy = GY(oy - hy); rule = 9;
        }
    }

    // ---- 5. Advance: hunt what is awake, else go for the way out --------------------------------------------------
    if (!s_give_up && s_no_kill_frames >= BOT_GIVE_UP_FRAMES && awake_count > 0 &&
        (melee_now_d2 > 80 * 80 || s_no_hit_frames >= 900)) {      // (an enemy that stays close but never bites is stuck behind a prop)
        s_give_up = 1;                                           // the hunt leads nowhere: leave it
        if (st->give_ups < 0xFFFF) st->give_ups++;
    }
    if (!rule) {
        rule = 5;
        int gx = 0, gy = 0, have_goal = 0;
        if (near_i >= 0 && !s_give_up && awake_count > 0) {
            gx = TO_INT(en[near_i].x);
            gy = TO_INT(en[near_i].y);
            have_goal = 1;
        } else if (ri.altar && awake_count == 0 && (int)g_arpg.last_altar != room && s_altar_frames < 900) {
            gx = ri.altar_x;                                      // light the altar: the next bajada enters here
            gy = ri.altar_y;
            have_goal = 1;
            rule = 12;
            s_altar_frames++;
        } else if (tdoor >= 0 && ri.chest && !ri.chest_open && !s_give_up && s_visit_frames < BOT_VISIT_CAP) {
            gx = ri.chest_x;
            gy = ri.chest_y;
            have_goal = 1;
        } else if (tdoor >= 0) {
            gx = ri.door_gx[tdoor];
            gy = ri.door_gy[tdoor];
            have_goal = 1;
            if (s_give_up || s_visit_frames >= BOT_VISIT_CAP) rule = 10;
        } else if (ri.has_up) {
            gx = ri.up_x;
            gy = ri.up_y;
            have_goal = 1;
            if (s_give_up) rule = 10;
        } else if (ri.chest && !ri.chest_open) {
            gx = ri.chest_x;
            gy = ri.chest_y;
            have_goal = 1;
        } else if (room == ENC_ROOM_CRIPTA && awake_count == 0) {   // the boss sleeps until the hero steps up past the foot of the room
            gx = 256;
            gy = ri.foot_y - 70;
            have_goal = 1;
        } else if (room != ENC_ROOM_CRIPTA) {                     // a side room with nothing left to do: back out by the side it came in
            gx = s_entry_x < 256 ? 140 : 372;
            gy = s_entry_y;
            have_goal = 1;
        }
        if (have_goal) {
            st->goal_x = (int16_t)gx;
            st->goal_y = (int16_t)gy;
            int px, py;
            want_dx = gx - hx;
            want_dy = GY(gy - hy);
            if (pf_direction(hx, hy, gx, gy, &px, &py)) { want_dx = px; want_dy = py; }
        }
    }

    // ---- 6. Stuck ------------------------------------------------------------------------------------------------
    int moving_intent = (want_dx != 0 || want_dy != 0);
    if (!moving_intent || touch) {
        s_stuck_timer = 0;
        s_stuck_ref_x = hx;
        s_stuck_ref_y = hy;
    } else {
        s_stuck_timer++;
        if (s_stuck_timer >= BOT_STUCK_FRAMES && s_side_timer <= 0) {
            if (iabs(hx - s_stuck_ref_x) + 2 * iabs(hy - s_stuck_ref_y) < 8) {
                s_side_timer = BOT_SIDESTEP_FRAMES;
                s_side_sign = -s_side_sign;
                if (st->stuck_events < 0xFFFF) st->stuck_events++;
            }
            s_stuck_timer = 0;
            s_stuck_ref_x = hx;
            s_stuck_ref_y = hy;
        }
    }
    if (s_side_timer > 0 && !dodge) {
        s_side_timer--;
        int ux, uy;
        if (unit256(want_dx, want_dy, &ux, &uy)) { want_dx = uy * s_side_sign; want_dy = -ux * s_side_sign; }
        else { want_dx = 256 * s_side_sign; want_dy = 0; }
        rule = 6;
    }

    // ---- L pulses: two frames down, then a pause (a held L past a few frames would open the spell radial) -------
    if (s_l_hold > 0) {
        out->keys |= KEY_L;
        if (--s_l_hold == 0) s_l_gap = 9 + (bot_rand(g_arpg_bot_debug.punch_jitter) + g_arpg_bot_debug.punch_jitter) / 2;
    } else if (s_l_gap > 0) {
        s_l_gap--;
    } else if (tap_l && !touch) {
        out->keys |= KEY_L;
        s_l_hold = 1;
        if (rule != 8 && st->punches < 0xFFFF) st->punches++;
    }

    // ---- Execute the movement ---------------------------------------------------------------------------------------
    if (!touch && (want_dx != 0 || want_dy != 0)) {
        int d = steer(hx, hy, want_dx, want_dy);
        if (d >= 0) {
            out->keys |= keys_of(d);
            s_last_dir = d;
        } else {
            s_last_dir = -1;
        }
    } else {
        s_last_dir = -1;
    }
    st->rule = (uint8_t)rule;
}

#endif // ARPG_BOT && ENCOUNTERS_PROTO
