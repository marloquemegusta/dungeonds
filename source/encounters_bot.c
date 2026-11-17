#include "encounters_act1.h"

// Translation unit never empty (ISO C) when ENC_BOT=0.
typedef int encounters_bot_translation_unit_not_empty;

#if ENC_BOT && ENCOUNTERS_PROTO

// Autopilot of the variant "encuentros-bot" (tools/encuentros/BRIEF_bot.md). It plays the act as a careful player:
// dodge the Ojo line and the Cireneo lunge, keep away from the melee enemies, shoot the nearest awake enemy in
// sight (or the relicario of a corridor), then climb. It only replaces the buttons and the stylus; the game
// does not know. Test code: it runs in the headless scenarios, never in the shipping ROM.
//
// Geometry is done on the ground: x as is, y doubled (2:1 projection), so a world dy counts as 2 px.

#include "collision.h"
#include "weapons.h"
#include "modifiers.h"

#define GY(dy) (2 * (dy))
#define BOT_KEEP_AWAY 40            // ground px: a melee enemy this close makes the hero back off...
#define BOT_BACKED_OFF 64           // ...until it is this far (hysteresis)
#define BOT_START_CHARGE 56         // ground px: nearest melee enemy must be this far to start charging
#define BOT_CANCEL_CHARGE 24        // ground px: a melee enemy this close cancels a charge that is not ready
#define BOT_RANGE_MARGIN 12
#define BOT_STUCK_FRAMES 60
#define BOT_SIDESTEP_FRAMES 30
#define BOT_OJO_CLEAR 26            // ground px from the line the hero must stay
#define BOT_LANE_CLEAR 28

static const int8_t s_dir_x[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };       // 0 = north (up), clockwise
static const int8_t s_dir_y[8] = { -1, -1, 0, 1, 1, 1, 0, -1 };

static int s_last_dir = -1;                 // direction chosen last frame (hysteresis)
static int s_dodge_side;                    // +1 / -1: side taken while a dodge lasts, 0 none
static int s_dodge_hold;
static int s_stuck_ref_x, s_stuck_ref_y, s_stuck_timer;
static int s_side_timer, s_side_sign = 1;
static int s_wait_frames;                   // frames standing and waiting to start a charge
static int s_retreat;                       // 1 while backing off until the melee enemy is 64 px away

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

// Ground distance squared between two world points.
static int gd2(int dx, int dy) { return dx * dx + 4 * dy * dy; }

// Unit vector (length 256) of a ground vector; false when it is the zero vector.
static int unit256(int vx, int vy, int *ux, int *uy) {
    int len = isqrt_u((uint32_t)(vx * vx + vy * vy));
    if (len == 0) return 0;
    *ux = vx * 256 / len;
    *uy = vy * 256 / len;
    return 1;
}

static int is_free(int x, int y) { return position_is_free(TO_FIXED(x), TO_FIXED(y)); }

// Whether the hero can step from (hx, hy) in direction d for `len` ground px (two probes).
static int dir_free(int hx, int hy, int d, int len) {
    int ux, uy;
    unit256(s_dir_x[d] * 256, s_dir_y[d] * 256, &ux, &uy);
    for (int k = 1; k <= 2; k++) {
        int l = len * k / 2;
        if (!is_free(hx + ((ux * l) >> 8), hy + ((uy * l) >> 9))) return 0;
    }
    return 1;
}

// Picks the free direction closest to the wished ground vector. Returns the direction or -1 when boxed in.
static int steer(int hx, int hy, int wx, int wy) {
    int ux, uy;
    if (!unit256(wx, wy, &ux, &uy)) return -1;
    int best = -1, best_score = -100000;
    for (int d = 0; d < 8; d++) {
        int dx, dy;
        unit256(s_dir_x[d] * 256, s_dir_y[d] * 256, &dx, &dy);
        int score = (dx * ux + dy * uy) >> 8;                    // -256..256
        if (!dir_free(hx, hy, d, 16)) continue;
        if (!dir_free(hx, hy, d, 36)) score -= 90;               // a wall soon: worse
        if (d == s_last_dir) score += 40;                        // do not flicker
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

// "Awake" for the bot: not asleep, not rising out of a puddle. A praying Exvoto counts once its encounter has
// woken (the hero is inside it): before that the ray goes through it (enc_untouchable).
static int awake_state(const Enemy *e) {
    if (e->state == ENEMY_STATE_PRAY) return g_enc_stats.woken > e->pack;
    return e->state != ENEMY_STATE_DORMANT && e->state != ENEMY_STATE_EMERGE &&
           e->state != ENEMY_STATE_SUSPENDED && e->state != ENEMY_STATE_DEAD;
}

// Which side of a line (given by a ground unit direction) is closer to a bullet-blocking column within
// 48 px: +1 / -1, or 0 when there is none on either side.
static int column_side(int hx, int hy, int ux, int uy) {
    int px = -uy, py = ux;                    // perpendicular, ground metric
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
// Path finding for the advance rule: a coarse grid (8 ground px per cell) around the hero, filled with
// position_is_free, flooded from the goal. Greedy steering alone gets stuck behind the wires and the sacos.
// ---------------------------------------------------------------------------------------------------------

#define PF_W 28                  // cells across: world x 144..368
#define PF_X0 144
#define PF_CELL_X 8              // world px per cell horizontally
#define PF_CELL_Y 4              // world px per cell vertically (8 ground px)
#define PF_H 72
#define PF_ROWS_ABOVE 52         // the window starts this many rows above the hero when it is built
#define PF_INF 30000

static uint8_t s_pf_blocked[PF_W * PF_H];
static int16_t s_pf_dist[PF_W * PF_H];
static int16_t s_pf_queue[PF_W * PF_H];
static int s_pf_y0, s_pf_age = 1000;
static int s_flood_kind = -1, s_flood_cx, s_flood_cy, s_flood_age = 1000;

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

// Floods the distance field from the goal. goal_kind 0: the cell of (gx, gy); 1: every free cell of the top row.
static void pf_flood(int goal_kind, int gx, int gy) {
    for (int i = 0; i < PF_W * PF_H; i++) s_pf_dist[i] = PF_INF;
    int head = 0, tail = 0;
    if (goal_kind == 1) {
        for (int cx = 0; cx < PF_W; cx++) {
            if (s_pf_blocked[cx]) continue;
            s_pf_dist[cx] = 0;
            s_pf_queue[tail++] = (int16_t)cx;
        }
    } else {
        int cx, cy;
        pf_cell_of(gx, gy, &cx, &cy);
        // The goal is an enemy or a relicario standing on the floor: its own cell may count as blocked; start there anyway.
        s_pf_dist[cy * PF_W + cx] = 0;
        s_pf_queue[tail++] = (int16_t)(cy * PF_W + cx);
    }
    while (head < tail) {
        int cur = s_pf_queue[head++];
        int cx = cur % PF_W, cy = cur / PF_W;
        for (int d = 0; d < 8; d++) {
            int nx = cx + (int)s_dir_x[d], ny = cy + (int)s_dir_y[d];
            if (nx < 0 || ny < 0 || nx >= PF_W || ny >= PF_H) continue;
            int ni = ny * PF_W + nx;
            if (s_pf_blocked[ni] || s_pf_dist[ni] != PF_INF) continue;
            if ((s_dir_x[d] != 0 && s_dir_y[d] != 0) &&
                (s_pf_blocked[cy * PF_W + nx] || s_pf_blocked[ny * PF_W + cx])) continue;     // no corner cutting
            s_pf_dist[ni] = (int16_t)(s_pf_dist[cur] + 1);
            s_pf_queue[tail++] = (int16_t)ni;
        }
    }
}

// Ground vector towards the cell `steps` cells down the distance field from the hero; false when unreachable.
static int pf_next(int hx, int hy, int steps, int *wx, int *wy) {
    int cx, cy;
    pf_cell_of(hx, hy, &cx, &cy);
    int here = s_pf_dist[cy * PF_W + cx];
    int best_here = PF_INF;
    for (int d = 0; d < 8; d++) {                       // the hero's own cell may be flagged blocked: look at the neighbours
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

// Wished direction (ground vector) to reach a goal by the floor, or 0 if there is no path.
static int pf_direction(int hx, int hy, int goal_kind, int gx, int gy, int *wx, int *wy) {
    if (++s_pf_age > 24 || hy < s_pf_y0 + 2 * PF_CELL_Y || hy > s_pf_y0 + (PF_H - 4) * PF_CELL_Y) {
        pf_rebuild(hy);
        s_pf_age = 0;
    }
    // The flood is the costly part: redo it when the goal moves to another cell or every 8 frames.
    int gcx = 0, gcy = 0;
    if (goal_kind == 0) pf_cell_of(gx, gy, &gcx, &gcy);
    if (s_pf_age == 0 || goal_kind != s_flood_kind || gcx != s_flood_cx || gcy != s_flood_cy || ++s_flood_age >= 8) {
        pf_flood(goal_kind, gx, gy);
        s_flood_kind = goal_kind;
        s_flood_cx = gcx;
        s_flood_cy = gcy;
        s_flood_age = 0;
    }
    return pf_next(hx, hy, 3, wx, wy);
}

// ---------------------------------------------------------------------------------------------------------
// Reaction time: what the bot decides to dodge or back off from is the state of the enemies g_enc_debug.bot_reaction
// frames ago (a ring of snapshots). Aiming and the hero's own position are current.
// ---------------------------------------------------------------------------------------------------------

#define BOT_MAX_ENEMIES 32
#define BOT_HIST 32
typedef struct {
    int16_t x, y, adx, ady, apx, apy;     // enemy ground point, lunge direction, gaze point
    uint8_t state, type, live, track;     // track: frames the Ojo has been looking (TRACK, LOCK, SENTENCE)
} BotSnap;
static BotSnap s_hist[BOT_HIST][BOT_MAX_ENEMIES];
static uint8_t s_hist_head;
static uint8_t s_track_cnt[BOT_MAX_ENEMIES];
static uint32_t s_aim_roll = 1;
static uint8_t s_lunge_seen[BOT_MAX_ENEMIES], s_lunge_ignore[BOT_MAX_ENEMIES];   // clumsy profile: lunges not dodged
static int s_err_x, s_err_y;               // aiming error of the shot being charged

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

static int bot_rand(int amp) {            // -amp..amp, from the scenario seed
    s_aim_roll = s_aim_roll * 1664525u + 1013904223u + g_enc_debug.seed;
    if (amp <= 0) return 0;
    return (int)((s_aim_roll >> 16) % (uint32_t)(2 * amp + 1)) - amp;
}

void enc_bot_step(const EncBotView *v, Enemy *en, int n, EncBotInput *out) {
    volatile EncStats *st = &g_enc_stats;
    out->keys = 0;
    out->touch_down = 0;
    out->touch_x = 128;
    out->touch_y = 96;
    st->bot_rule = 0;
    if (g_player_state.is_dead || enc_victory() || st->result != 0) return;

    const int hx = v->hx, hy = v->hy;
    const int charging = weapons_aim_charging();
    const int progress = weapons_aim_progress();
    const int can_start = weapons_can_start_aim(&g_player_state);
    const int range = g_weapon_tuning[WEAPON_SNIPER].projectile_range + g_mods.sniper_range - BOT_RANGE_MARGIN;

    // ---- Scan -----------------------------------------------------------------------------------------
    int want_dx = 0, want_dy = 0, rule = 0;        // wished ground direction
    int dodge = 0;                                 // 1 = a rule forces movement (dodge)
    int melee_d2 = 0x7fffffff, melee_i = -1;
    int target_i = -1, target_d2 = 0x7fffffff;     // enemy to shoot
    int near_i = -1, near_d2 = 0x7fffffff;         // nearest awake enemy (shootable or not)
    int awake_count = 0;

    for (int i = 0; i < n; i++) {
        Enemy *e = &en[i];
        if (!e->active || e->hp <= 0) continue;
        int dx = e->x - TO_FIXED(hx), dy = e->y - TO_FIXED(hy);
        dx = TO_INT(dx);
        dy = TO_INT(dy);
        if (!awake_state(e)) continue;
        int d2 = gd2(dx, dy);
        if (awake_count == 0) { st->dbg_awake_state = (uint8_t)e->state; st->dbg_awake_type = (uint8_t)e->type; }
        awake_count++;
        if (d2 < near_d2) { near_d2 = d2; near_i = i; }
        if (d2 <= range * range && d2 < target_d2 &&
            bullet_line_is_free(hx, hy, TO_INT(e->x), TO_INT(e->y))) {
            target_d2 = d2;
            target_i = i;
        }
    }

    // What the enemies were doing `bot_reaction` frames ago: the rules that dodge and back off look at this.
    hist_push(en, n);
    const BotSnap *sn = hist_delayed(g_enc_debug.bot_reaction);
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES; i++) {
        if (!sn[i].live) continue;
        int st_ = sn[i].state;
        if (st_ == ENEMY_STATE_DORMANT || st_ == ENEMY_STATE_PRAY || st_ == ENEMY_STATE_EMERGE ||
            st_ == ENEMY_STATE_SUSPENDED || st_ == ENEMY_STATE_DEAD) continue;
        if (!(sn[i].type == ENEMY_TYPE_EXVOTO || sn[i].type == ENEMY_TYPE_MONAGUILLO ||
              sn[i].type == ENEMY_TYPE_CHARGER || sn[i].type == ENEMY_TYPE_ABANDERADO)) continue;
        int d2 = gd2(sn[i].x - hx, sn[i].y - hy);
        if (d2 < melee_d2) { melee_d2 = d2; melee_i = i; }
    }

    // ---- 1. Ojo: leave the line ---------------------------------------------------------------------
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES && !rule; i++) {
        if (!sn[i].live || sn[i].type != ENEMY_TYPE_SHOOTER) continue;
        if (sn[i].state != ENEMY_STATE_TRACK && sn[i].state != ENEMY_STATE_LOCK && sn[i].state != ENEMY_STATE_SENTENCE) continue;
        if (sn[i].track < g_enc_debug.bot_ojo_delay) continue;       // it has not noticed the gaze yet
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
        // Perpendicular to the line (ground metric): (uy, -ux) is the side of positive cross.
        want_dx = uy * s_dodge_side;
        want_dy = -ux * s_dodge_side;
        rule = 1;
        dodge = 1;
    }
    // ---- 2. Cireneo: leave the lunge lane ------------------------------------------------------------
    for (int i = 0; i < n && i < BOT_MAX_ENEMIES && !rule; i++) {
        if (!sn[i].live || sn[i].type != ENEMY_TYPE_CHARGER) continue;
        if (sn[i].state != ENEMY_STATE_TELEGRAPH && sn[i].state != ENEMY_STATE_CHARGE) { s_lunge_seen[i] = 0; continue; }
        if (!s_lunge_seen[i]) {           // a new lunge: the clumsy profile may not see it
            s_lunge_seen[i] = 1;
            s_lunge_ignore[i] = (uint8_t)(g_enc_debug.bot_miss_pct && (bot_rand(50) + 50) < g_enc_debug.bot_miss_pct);
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

    // ---- 3. Keep away from melee enemies -------------------------------------------------------------
    if (melee_i < 0 || melee_d2 >= BOT_BACKED_OFF * BOT_BACKED_OFF) s_retreat = 0;
    else if (melee_d2 < BOT_KEEP_AWAY * BOT_KEEP_AWAY) s_retreat = 1;
    int melee_close = s_retreat;
    if (!rule && melee_close) {
        want_dx = hx - sn[melee_i].x;
        want_dy = GY(hy - sn[melee_i].y);
        if (want_dx == 0 && want_dy == 0) want_dy = 1;
        rule = 3;
    }

    // ---- Relicario of the corridor: a target only when no enemy is awake ------------------------------
    int relic_x = 0, relic_y = 0, relic = 0;
    // The relicario comes first unless an awake enemy is already close (enemies that spawn awake walk down the
    // corridor towards the hero: the bot used to drop the relicario as soon as one appeared).
    relic = enc_relic_target(&relic_x, &relic_y);
    if (relic && awake_count > 0 && near_d2 <= 170 * 170) relic = 0;
    int relic_shootable = 0, relic_far = 0;
    if (relic) {
        int d2 = gd2(relic_x - hx, relic_y - hy);
        relic_far = d2 > range * range;
        // The relicario is a prop that may stop bullets itself: the line of sight is checked up to 14 ground px
        // short of it (the ray hits its body before it reaches the prop).
        int lx = relic_x, ly = relic_y, ux, uy;
        if (unit256(relic_x - hx, GY(relic_y - hy), &ux, &uy)) {
            lx = relic_x - ((ux * 14) >> 8);
            ly = relic_y - ((uy * 14) >> 9);
        }
        relic_shootable = d2 <= range * range && bullet_line_is_free(hx, hy, lx, ly);
    }

    st->dbg_awake = (uint8_t)awake_count;
    st->dbg_relic_x = (int16_t)(relic ? relic_x : 0);
    st->dbg_relic_y = (int16_t)(relic ? relic_y : 0);
    st->dbg_hero_x = (int16_t)hx;
    st->dbg_hero_y = (int16_t)hy;
    if (relic && st->relic_seen_frames < 0xFFFF) st->relic_seen_frames++;
    if (relic_shootable && st->relic_shootable_frames < 0xFFFF) st->relic_shootable_frames++;
    if (relic && !relic_shootable) {
        if (relic_far && st->relic_norange_frames < 0xFFFF) st->relic_norange_frames++;
        else if (!relic_far && st->relic_nolos_frames < 0xFFFF) st->relic_nolos_frames++;
    }

    // ---- 4. Shoot ---------------------------------------------------------------------------------------
    int aim_x = 0, aim_y = 0, have_target = 0;
    if (target_i >= 0) {
        aim_x = TO_INT(en[target_i].x);
        aim_y = TO_INT(en[target_i].y);
        have_target = 1;
    } else if (relic_shootable) {
        aim_x = relic_x;
        aim_y = relic_y;
        have_target = 1;
    }
    int touch = 0;
    if (!have_target || charging) s_wait_frames = 0;
    if (charging) {
        if (progress >= 256) {
            st->shots++;                  // released now: the shot goes
            if (st->boss_alive) st->boss_shots++;
            touch = 0;
            rule = rule ? rule : 4;
        } else if (dodge || (melee_i >= 0 && melee_d2 < BOT_CANCEL_CHARGE * BOT_CANCEL_CHARGE) || !have_target) {
            touch = 0;                    // cancel: the charge is lost
        } else {
            touch = 1;
            rule = 4;
            want_dx = want_dy = 0;
        }
    } else if (have_target && !dodge && can_start && !melee_close &&
               (melee_i < 0 || melee_d2 >= BOT_START_CHARGE * BOT_START_CHARGE || s_wait_frames >= 20)) {
        // (an enemy that keeps 40..56 px away without coming, e.g. behind a wire, is not a reason to wait for ever)
        touch = 1;
        rule = 4;
        want_dx = want_dy = 0;
    } else if (have_target && !dodge && !melee_close) {
        s_wait_frames++;
        rule = 4;                         // waiting for the cooldown (or for the melee enemies to stay away): stand
        want_dx = want_dy = 0;
    }

    if (touch && have_target) {
        if (!charging) {                  // a new shot: roll its aiming error once
            s_err_x = bot_rand(g_enc_debug.bot_aim_err);
            s_err_y = bot_rand(g_enc_debug.bot_aim_err / 2);
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

    // ---- 5. Advance -----------------------------------------------------------------------------------
    if (!rule) {
        rule = 5;
        if (!relic && awake_count > 0 && near_i >= 0) {
            // No shot (out of range or no line of sight): close in on the nearest awake enemy.
            const Enemy *e = &en[near_i];
            want_dx = TO_INT(e->x) - hx;
            want_dy = GY(TO_INT(e->y) - hy);
            if (near_d2 <= BOT_KEEP_AWAY * BOT_KEEP_AWAY) want_dx = want_dy = 0;   // already close: let it come
            else {
                int px, py;
                if (pf_direction(hx, hy, 0, TO_INT(e->x), TO_INT(e->y), &px, &py)) { want_dx = px; want_dy = py; }
            }
        } else if (relic) {
            want_dx = relic_x - hx;
            want_dy = GY(relic_y - hy);
            if (relic_shootable) want_dx = want_dy = 0;
            else {
                int px, py;
                if (pf_direction(hx, hy, 0, relic_x, relic_y, &px, &py)) { want_dx = px; want_dy = py; }
            }
        } else {
            want_dx = 0;
            want_dy = -256;               // clean or asleep ahead: climb (waking an encounter is the way in)
            int px, py;
            if (pf_direction(hx, hy, 1, 0, 0, &px, &py)) { want_dx = px; want_dy = py; }
        }
    }

    // ---- 6. Stuck ---------------------------------------------------------------------------------------
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
                st->stuck_events++;
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

    // ---- Execute the movement -------------------------------------------------------------------------
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
    st->bot_rule = (uint8_t)rule;
    st->dbg_awake_type = (uint8_t)((charging ? 1 : 0) | (can_start ? 2 : 0) | (have_target ? 4 : 0) | (touch ? 8 : 0) |
                                   (melee_close ? 16 : 0) | (relic ? 32 : 0) | (dodge ? 64 : 0) | (target_i >= 0 ? 128 : 0));
}

#endif // ENC_BOT && ENCOUNTERS_PROTO
