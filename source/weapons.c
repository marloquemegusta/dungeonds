#include "weapons.h"
#include "gameplay.h"

/* TUNABLE-PLACEHOLDER: Player Weapons Tuning Table (Fixed-Point 8.8).
 * Goal hits to kill (DESIGN.md 4.3): shotgun point blank 1 shooter / 2-3 charger,
 * sniper 1 shooter / 2 charger. */
const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES] = {
    [WEAPON_SHOTGUN] = {
        .name = "SHOTGUN",
        .damage_per_hit = 8,        /* 8 dmg * 5 pellets = 40 point blank */
        .pellets = 5,
        .fire_cooldown = 36,        /* marked pump between shots */
        .projectile_speed = 1536,   /* 6.0 px/frame */
        .projectile_range = 22,     /* ~132 px: lethal close, weak far */
        .spread_angle = 120,
        .aim_min_frames = 0,
        .knockback = 640,           /* 2.5 px/frame shove */
        .stun_frames = 10,
        .recoil = 512,              /* 2 px kick back */
        .shake_amp = 2,
        .shake_frames = 6
    },
    [WEAPON_SNIPER] = {
        .name = "SNIPER",
        .damage_per_hit = 30,       /* shooter 20 hp: 1 hit, charger 60 hp: 2 hits */
        .pellets = 1,
        .fire_cooldown = 40,
        .projectile_speed = 0,
        .projectile_range = 320,    /* ray length in ground px */
        .spread_angle = 0,
        .aim_min_frames = 24,       /* ~0.4 s before the shot is armed */
        .knockback = 0,
        .stun_frames = 0,
        .recoil = 0,
        .shake_amp = 3,
        .shake_frames = 8
    }
};

#define ENEMY_HIT_RADIUS 11          // ground px
#define SNIPER_CANCEL_RADIUS 12      // screen px around the player's body
#define MIN_AIM_DISTANCE 4           // ground px; closer than this there is no direction

#define MAX_SPARKS 40
#define SPARK_LIFE_MIN 6

typedef struct {
    int active;
    fixed x, y;           // 8.8 screen-space world position (height already applied)
    fixed vx, vy;
    int life, max_life;
} WeaponSpark;

typedef struct {
    int life;
    int x, y;             // muzzle in world px (height applied)
    int dir_x, dir_y;     // 8.8 screen direction of the shot
} MuzzleFlash;

typedef struct {
    int life;
    int x0, y0, x1, y1;   // world px, height applied
} SniperTrail;

enum { AIM_IDLE = 0, AIM_AIMING, AIM_READY, AIM_CANCELLED };

static PlayerProjectile s_player_projectiles[MAX_PLAYER_PROJECTILES];
static WeaponSpark s_sparks[MAX_SPARKS];
static MuzzleFlash s_flash;
static SniperTrail s_trail;
static int s_weapon_cooldown = 0;
static int s_aim_state = AIM_IDLE;
static int s_aim_timer = 0;
static fixed s_aim_dir_x = 0, s_aim_dir_y = 256;
static fixed s_aim_muzzle_x = 0, s_aim_muzzle_y = 0;
static int s_aim_muzzle_h = 0;
static int s_aim_len = 0;         // ground px the laser reaches before a wall
static fixed s_last_dir_x = 0, s_last_dir_y = 0;
static int s_shake_timer = 0, s_shake_frames = 1, s_shake_amp = 0;
static uint32_t s_shake_tick = 0;

static inline int abs_int(int v) {
    return v < 0 ? -v : v;
}

static uint32_t int_sqrt(uint32_t n) {
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

void weapons_init(void) {
    s_weapon_cooldown = 0;
    s_aim_state = AIM_IDLE;
    s_aim_timer = 0;
    s_last_dir_x = s_last_dir_y = 0;
    s_shake_timer = 0;
    s_flash.life = 0;
    s_trail.life = 0;
    s_aim_len = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) s_player_projectiles[i].active = 0;
    for (int i = 0; i < MAX_SPARKS; i++) s_sparks[i].active = 0;
}

void weapons_cycle(PlayerState *player) {
    if (!player) return;
    player->current_weapon = (WeaponType)((player->current_weapon + 1) % NUM_WEAPON_TYPES);
    s_aim_state = AIM_IDLE;
    s_aim_timer = 0;
}

const char *weapons_get_name(WeaponType type) {
    if (type >= 0 && type < NUM_WEAPON_TYPES) return g_weapon_tuning[type].name;
    return "UNKNOWN";
}

int weapons_get_active_projectile_count(void) {
    int count = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        if (s_player_projectiles[i].active) count++;
    }
    return count;
}

void weapons_last_shot_dir(fixed *dir_x, fixed *dir_y) {
    *dir_x = s_last_dir_x;
    *dir_y = s_last_dir_y;
}

void weapons_shake_offset(int *dx, int *dy) {
    *dx = 0;
    *dy = 0;
    if (s_shake_timer <= 0) return;
    int amp = (s_shake_amp * s_shake_timer) / s_shake_frames;
    if (amp < 1) amp = 1;
    // Deterministic zig-zag so scenarios stay reproducible.
    *dx = (s_shake_tick & 1) ? amp : -amp;
    *dy = (s_shake_tick & 2) ? (amp + 1) / 2 : -((amp + 1) / 2);
}

// ---------------------------------------------------------------------------
// Effects: procedural strokes, no sprites (DESIGN.md 4.7)
// ---------------------------------------------------------------------------

// Sparks leave the impact point opposite to the shot, with a sideways spread.
static void spawn_impact(int x, int y, fixed back_x, fixed back_y, int count) {
    for (int k = 0; k < count; k++) {
        for (int i = 0; i < MAX_SPARKS; i++) {
            if (s_sparks[i].active) continue;
            int speed = 320 + (int)(rng_next() % 400u);                  // 1.25..2.8 px/frame
            int side = (int)(rng_next() % 641u) - 320;                   // +-1.25 px/frame
            s_sparks[i].active = 1;
            s_sparks[i].x = TO_FIXED(x);
            s_sparks[i].y = TO_FIXED(y);
            s_sparks[i].vx = ((back_x * speed) >> 8) + ((-back_y * side) >> 8);
            s_sparks[i].vy = ((back_y * speed) >> 8) + ((back_x * side) >> 8) - 64;
            s_sparks[i].max_life = SPARK_LIFE_MIN + (int)(rng_next() % 5u);
            s_sparks[i].life = s_sparks[i].max_life;
            break;
        }
    }
}

static void spawn_flash(const WeaponInput *in, fixed dir_x, fixed dir_y) {
    s_flash.life = 3;
    s_flash.x = TO_INT(in->muzzle_x);
    s_flash.y = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_flash.dir_x = dir_x;
    s_flash.dir_y = dir_y;
}

static void request_shake(const WeaponTuning *tuning) {
    s_shake_amp = tuning->shake_amp;
    s_shake_frames = tuning->shake_frames > 0 ? tuning->shake_frames : 1;
    s_shake_timer = s_shake_frames;
}

// ---------------------------------------------------------------------------
// Aiming
// ---------------------------------------------------------------------------

// The stylus touches a pixel of the screen. Shots fly at muzzle height, so the
// touched pixel is read as a point at that height: its ground point lies
// `muzzle_h` pixels below it. Returns 0 when the touch is on top of the muzzle.
static int compute_aim(const WeaponInput *in, fixed *dir_x, fixed *dir_y) {
    int ax = in->touch_x - TO_INT(in->muzzle_x);
    int ay = (in->touch_y + in->muzzle_h) - TO_INT(in->muzzle_y);
    uint32_t len = int_sqrt((uint32_t)(ax * ax + GROUND_DY2(ay)));
    if ((int)len < MIN_AIM_DISTANCE) return 0;
    *dir_x = (fixed)((ax * 256) / (int)len);
    *dir_y = (fixed)((ay * 256) / (int)len);
    return 1;
}

// ---------------------------------------------------------------------------
// Firing
// ---------------------------------------------------------------------------

static void shove_enemy(Enemy *e, const WeaponTuning *tuning, fixed dir_x, fixed dir_y) {
    if (!e->active || e->hp <= 0 || tuning->knockback <= 0) return;
    e->knock_vx = (dir_x * tuning->knockback) >> 8;
    e->knock_vy = (dir_y * tuning->knockback) >> 8;
    e->stun_timer = tuning->stun_frames;
}

// The muzzle hangs off the feet; against a wall it can land inside the bullet-blocking
// cells. Then the shot starts at the player's ground point (the flash stays at the muzzle).
static void shot_origin(const WeaponInput *in, fixed *x, fixed *y) {
    if (bullet_position_is_free(in->muzzle_x, in->muzzle_y)) {
        *x = in->muzzle_x;
        *y = in->muzzle_y;
    } else {
        *x = in->player_x;
        *y = in->player_y;
    }
}

// Length in ground px a straight shot from the muzzle travels before a wall (0..range).
static int ray_length(const WeaponInput *in, fixed dir_x, fixed dir_y, int range) {
    fixed x, y;
    shot_origin(in, &x, &y);
    int d = 0;
    for (; d < range; d += 2) {
        x += dir_x * 2;
        y += dir_y * 2;
        if (!bullet_position_is_free(x, y)) break;
    }
    return d;
}

static void fire_shotgun(const WeaponTuning *tuning, const WeaponInput *in, fixed dir_x, fixed dir_y) {
    fixed origin_x, origin_y;
    shot_origin(in, &origin_x, &origin_y);
    fixed perp_x = -dir_y;
    fixed perp_y = dir_x;
    int pellets = tuning->pellets > 0 ? tuning->pellets : 1;
    for (int p_idx = 0; p_idx < pellets; p_idx++) {
        int slot = -1;
        for (int s = 0; s < MAX_PLAYER_PROJECTILES; s++) {
            if (!s_player_projectiles[s].active) { slot = s; break; }
        }
        if (slot < 0) break;

        int spread_idx = (pellets > 1) ? (p_idx - (pellets / 2)) : 0;
        fixed jitter = (fixed)rng_range(-(int)tuning->spread_angle / 4, (int)tuning->spread_angle / 4);
        fixed spread_offset = (spread_idx * tuning->spread_angle) / 2 + jitter;
        PlayerProjectile *proj = &s_player_projectiles[slot];
        proj->active = 1;
        proj->weapon_type = WEAPON_SHOTGUN;
        proj->x = origin_x;
        proj->y = origin_y;
        proj->vx = ((dir_x * tuning->projectile_speed) >> 8) + ((perp_x * spread_offset) >> 8);
        proj->vy = ((dir_y * tuning->projectile_speed) >> 8) + ((perp_y * spread_offset) >> 8);
        proj->height = in->muzzle_h;
        proj->life = tuning->projectile_range;
        proj->max_life = tuning->projectile_range;
        proj->damage = tuning->damage_per_hit;
    }
}

// Piercing ray: damages every enemy on the line once and stops at the first wall.
static void fire_sniper(const WeaponTuning *tuning, const WeaponInput *in, fixed dir_x, fixed dir_y,
                        Enemy *enemies, int max_enemies) {
    fixed cur_x, cur_y;
    shot_origin(in, &cur_x, &cur_y);
    fixed step_x = dir_x * 2;
    fixed step_y = dir_y * 2;
    uint32_t hit_mask = 0;
    int end_blocked = 0;

    for (int d = 0; d < tuning->projectile_range; d += 2) {
        fixed nx = cur_x + step_x;
        fixed ny = cur_y + step_y;
        if (!bullet_position_is_free(nx, ny)) { end_blocked = 1; break; }
        cur_x = nx;
        cur_y = ny;

        for (int i = 0; i < max_enemies; i++) {
            Enemy *e = &enemies[i];
            if (!e->active || e->hp <= 0 || (hit_mask & (1u << i))) continue;
            int edx = TO_INT(cur_x - e->x);
            int edy = TO_INT(cur_y - e->y);
            if (edx * edx + GROUND_DY2(edy) <= ENEMY_HIT_RADIUS * ENEMY_HIT_RADIUS) {
                hit_mask |= 1u << i;
                spawn_impact(TO_INT(cur_x), TO_INT(cur_y) - in->muzzle_h, -dir_x, -dir_y, 4);
                enemy_hit(e, tuning->damage_per_hit, dir_x * 4, dir_y * 4);
                shove_enemy(e, tuning, dir_x, dir_y);
            }
        }
    }

    s_trail.life = 6;
    s_trail.x0 = TO_INT(in->muzzle_x);
    s_trail.y0 = TO_INT(in->muzzle_y) - in->muzzle_h;
    s_trail.x1 = TO_INT(cur_x);
    s_trail.y1 = TO_INT(cur_y) - in->muzzle_h;
    if (end_blocked) {
        spawn_impact(s_trail.x1, s_trail.y1, -dir_x, -dir_y, 6);
    }
}

static int fire_weapon(PlayerState *player, const WeaponInput *in, fixed dir_x, fixed dir_y,
                       Enemy *enemies, int max_enemies) {
    const WeaponTuning *tuning = &g_weapon_tuning[player->current_weapon];
    s_weapon_cooldown = tuning->fire_cooldown;
    s_last_dir_x = dir_x;
    s_last_dir_y = dir_y;
    if (player->current_weapon == WEAPON_SHOTGUN) {
        fire_shotgun(tuning, in, dir_x, dir_y);
    } else {
        fire_sniper(tuning, in, dir_x, dir_y, enemies, max_enemies);
    }
    spawn_flash(in, dir_x, dir_y);
    request_shake(tuning);
    return WEAPON_RESULT_FIRED;
}

int weapons_can_start_aim(const PlayerState *player) {
    return player->current_weapon == WEAPON_SNIPER && s_weapon_cooldown <= 0 && s_aim_state == AIM_IDLE;
}

int weapons_input(PlayerState *player, const WeaponInput *in, Enemy *enemies, int max_enemies) {
    if (!player || !in || player->is_dead) {
        s_aim_state = AIM_IDLE;
        return 0;
    }

    fixed dir_x = 0, dir_y = 0;
    int has_aim = in->touch_down ? compute_aim(in, &dir_x, &dir_y) : 0;

    if (player->current_weapon == WEAPON_SHOTGUN) {
        // One shot per touch: holding the stylus does not repeat.
        if (in->touch_pressed && has_aim && s_weapon_cooldown <= 0) {
            return fire_weapon(player, in, dir_x, dir_y, enemies, max_enemies);
        }
        return 0;
    }

    // Sniper: touch to aim (the player stops), release to fire once armed.
    int result = 0;
    if (s_aim_state == AIM_IDLE) {
        if (in->touch_pressed && s_weapon_cooldown <= 0) {
            s_aim_state = AIM_AIMING;
            s_aim_timer = 0;
        }
    }
    if (s_aim_state == AIM_IDLE) return 0;

    if (!in->touch_down) {
        if (s_aim_state == AIM_READY) {
            result = fire_weapon(player, in, s_aim_dir_x, s_aim_dir_y, enemies, max_enemies);
        }
        s_aim_state = AIM_IDLE;
        return result;
    }

    if (s_aim_state == AIM_CANCELLED) return 0;

    // Dragging the stylus back onto the character cancels the shot.
    int bx = in->touch_x - TO_INT(in->player_x);
    int by = in->touch_y - (TO_INT(in->player_y) - in->muzzle_h);
    if (bx * bx + by * by <= SNIPER_CANCEL_RADIUS * SNIPER_CANCEL_RADIUS) {
        s_aim_state = AIM_CANCELLED;
        return 0;
    }

    if (has_aim) {
        s_aim_dir_x = dir_x;
        s_aim_dir_y = dir_y;
    }
    s_aim_muzzle_x = in->muzzle_x;
    s_aim_muzzle_y = in->muzzle_y;
    s_aim_muzzle_h = in->muzzle_h;
    s_aim_len = ray_length(in, s_aim_dir_x, s_aim_dir_y, g_weapon_tuning[WEAPON_SNIPER].projectile_range);
    s_aim_timer++;
    if (s_aim_timer >= g_weapon_tuning[WEAPON_SNIPER].aim_min_frames) s_aim_state = AIM_READY;
    return WEAPON_RESULT_ROOTED;
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

void weapons_update(Enemy *enemies, int max_enemies) {
    if (s_weapon_cooldown > 0) s_weapon_cooldown--;
    if (s_flash.life > 0) s_flash.life--;
    if (s_trail.life > 0) s_trail.life--;
    if (s_shake_timer > 0) { s_shake_timer--; s_shake_tick++; }

    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        s->x += s->vx;
        s->y += s->vy;
        s->vy += 32;                      // light gravity
        if (--s->life <= 0) s->active = 0;
    }

    const WeaponTuning *shotgun = &g_weapon_tuning[WEAPON_SHOTGUN];
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;

        if (--p->life <= 0) {
            p->active = 0;
            continue;
        }

        int major = abs_int(p->vx) > abs_int(p->vy) ? abs_int(p->vx) : abs_int(p->vy);
        int steps = (major + 511) / 512;
        if (steps < 1) steps = 1;
        int blocked = 0;
        for (int s = 1; s <= steps; s++) {
            fixed nx = p->x + (p->vx / steps);
            fixed ny = p->y + (p->vy / steps);
            if (!bullet_position_is_free(nx, ny)) { blocked = 1; break; }
            p->x = nx;
            p->y = ny;
        }
        if (blocked) {
            spawn_impact(TO_INT(p->x), TO_INT(p->y) - p->height, -p->vx / 8, -p->vy / 8, 3);
            p->active = 0;
            continue;
        }

        for (int e_idx = 0; e_idx < max_enemies; e_idx++) {
            Enemy *e = &enemies[e_idx];
            if (!e->active || e->hp <= 0) continue;
            int dx = TO_INT(p->x - e->x);
            int dy = TO_INT(p->y - e->y);
            if (dx * dx + GROUND_DY2(dy) > ENEMY_HIT_RADIUS * ENEMY_HIT_RADIUS) continue;

            // Damage falls off from 100% at the muzzle to 25% at the end of the range.
            int damage = (p->damage * (64 + (192 * p->life) / p->max_life)) >> 8;
            if (damage < 1) damage = 1;
            spawn_impact(TO_INT(p->x), TO_INT(p->y) - p->height, -p->vx / 8, -p->vy / 8, 3);
            enemy_hit(e, damage, p->vx, p->vy);
            fixed len_dir_x = p->vx * 256 / shotgun->projectile_speed;
            fixed len_dir_y = p->vy * 256 / shotgun->projectile_speed;
            shove_enemy(e, shotgun, len_dir_x, len_dir_y);
            p->active = 0;
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Rendering: procedural strokes. render_screen() calls weapons_render() once per screen,
// so the aim laser, pellets, trail, flash and sparks show on both of them.
// ---------------------------------------------------------------------------

enum {
    FX_CORE = 0, FX_HOT, FX_COOL,                  // muzzle flash
    FX_AIM, FX_AIM_READY,                          // sniper laser
    FX_TRAIL_A, FX_TRAIL_B, FX_TRAIL_C,            // sniper trail, bright to dim
    FX_PELLET_HEAD,
    FX_SPARK_A, FX_SPARK_B, FX_SPARK_C,            // impact sparks, hot to cold
    FX_NUM_COLORS
};

static const uint16_t s_fx_rgb[FX_NUM_COLORS] = {
    RGB15(31, 31, 24), RGB15(31, 24, 6), RGB15(28, 12, 2),
    RGB15(31, 8, 6), RGB15(20, 31, 31),
    RGB15(31, 31, 31), RGB15(18, 28, 31), RGB15(8, 16, 26),
    RGB15(31, 30, 20),
    RGB15(31, 30, 18), RGB15(31, 18, 3), RGB15(20, 5, 2)
};

typedef struct {
    uint16_t *p16;        // screen page (BGR555 with the alpha bit)
} FxTarget;

static inline void put_px(const FxTarget *t, int x, int y, int color) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    t->p16[y * SCREEN_W + x] = s_fx_rgb[color] | BIT(15);
    dirty_row(y, x, x + 1);
}

// Draws a one-pixel Bresenham line in screen space.
static void draw_line(const FxTarget *t, int x0, int y0, int x1, int y1, int color) {
    // Nothing of the line can reach this screen: skip the walk.
    if ((x0 < 0 && x1 < 0) || (x0 >= SCREEN_W && x1 >= SCREEN_W) ||
        (y0 < 0 && y1 < 0) || (y0 >= SCREEN_H && y1 >= SCREEN_H)) return;
    int dx = abs_int(x1 - x0), dy = abs_int(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = (dx > dy ? dx : -dy) / 2;
    for (;;) {
        put_px(t, x0, y0, color);
        if (x0 == x1 && y0 == y1) break;
        int e2 = err;
        if (e2 > -dx) { err -= dy; x0 += sx; }
        if (e2 < dy) { err += dx; y0 += sy; }
    }
}

static void render_aim_line(const FxTarget *t, int cam_x, int cam_y) {
    if (s_aim_state != AIM_AIMING && s_aim_state != AIM_READY) return;
    int ready = s_aim_state == AIM_READY;
    int color = ready ? FX_AIM_READY : FX_AIM;
    int last_x = TO_INT(s_aim_muzzle_x) - cam_x;
    int last_y = TO_INT(s_aim_muzzle_y) - s_aim_muzzle_h - cam_y;
    for (int d = 2; d <= s_aim_len; d += 2) {
        int px = TO_INT(s_aim_muzzle_x + s_aim_dir_x * d) - cam_x;
        int py = TO_INT(s_aim_muzzle_y + s_aim_dir_y * d) - s_aim_muzzle_h - cam_y;
        // Dashed while aiming, solid once the shot is armed.
        if (ready || (((d - 2) >> 2) & 1) == 0) draw_line(t, last_x, last_y, px, py, color);
        last_x = px;
        last_y = py;
    }
}

static void render_flash(const FxTarget *t, int cam_x, int cam_y) {
    if (s_flash.life <= 0) return;
    int x = s_flash.x - cam_x, y = s_flash.y - cam_y;
    int reach = 2 + s_flash.life * 2;                 // 8, 6, 4 px as it fades
    for (int k = 1; k <= reach; k++) {
        int px = x + ((s_flash.dir_x * k) >> 8);
        int py = y + ((s_flash.dir_y * k) >> 8);
        put_px(t, px, py, k * 2 > reach ? FX_COOL : FX_HOT);
    }
    put_px(t, x, y, FX_CORE);
    put_px(t, x - 1, y, FX_HOT);
    put_px(t, x + 1, y, FX_HOT);
    put_px(t, x, y - 1, FX_HOT);
    put_px(t, x, y + 1, FX_HOT);
}

static void render_fx(const FxTarget *t, int cam_x, int cam_y) {
    render_aim_line(t, cam_x, cam_y);

    // Sniper trail: a long bright stroke that fades in a few frames.
    if (s_trail.life > 0) {
        int color = s_trail.life > 4 ? FX_TRAIL_A : s_trail.life > 2 ? FX_TRAIL_B : FX_TRAIL_C;
        draw_line(t, s_trail.x0 - cam_x, s_trail.y0 - cam_y,
                  s_trail.x1 - cam_x, s_trail.y1 - cam_y, color);
    }

    // Pellets: short streak behind a bright head.
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;
        int hx = TO_INT(p->x) - cam_x;
        int hy = TO_INT(p->y) - p->height - cam_y;
        int tx = hx - (p->vx >> 8) * 2 / 3;
        int ty = hy - (p->vy >> 8) * 2 / 3;
        draw_line(t, tx, ty, hx, hy, FX_COOL);
        put_px(t, hx, hy, FX_PELLET_HEAD);
    }

    render_flash(t, cam_x, cam_y);

    // Impact sparks: two-pixel strokes along their velocity, cooling as they die.
    for (int i = 0; i < MAX_SPARKS; i++) {
        WeaponSpark *s = &s_sparks[i];
        if (!s->active) continue;
        int age = (s->life * 3) / s->max_life;        // 2 young .. 0 old
        int color = age >= 2 ? FX_SPARK_A : age == 1 ? FX_SPARK_B : FX_SPARK_C;
        int hx = TO_INT(s->x) - cam_x, hy = TO_INT(s->y) - cam_y;
        put_px(t, hx, hy, color);
        put_px(t, hx - (s->vx > 96) + (s->vx < -96), hy - (s->vy > 96) + (s->vy < -96), color);
    }
}

void weapons_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;
    FxTarget target = { buffer };
    render_fx(&target, cam_x, cam_y);
}
