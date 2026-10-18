#include "weapons.h"
#include "gameplay.h"
#include "los.h"
#include <stdio.h>
#include <string.h>

/* TUNABLE-PLACEHOLDER: Player Weapons Tuning Table (Fixed-Point 8.8) */
const WeaponTuning g_weapon_tuning[NUM_WEAPON_TYPES] = {
    [WEAPON_PISTOL] = {
        .name = "PISTOL",
        .fire_mode = FIRE_MODE_HITSCAN,
        .damage_per_hit = 15,          /* TUNABLE-PLACEHOLDER: base precision hitscan damage */
        .pellets = 1,                  /* TUNABLE-PLACEHOLDER: single precise tracer */
        .fire_cooldown = 18,           /* TUNABLE-PLACEHOLDER: low rate of fire (0.3s) */
        .max_ammo = 0,                 /* TUNABLE-PLACEHOLDER: 0 = infinite ammo fallback */
        .pickup_ammo_amount = 0,       /* TUNABLE-PLACEHOLDER: no pickups needed */
        .ammo_cost = 0,                /* TUNABLE-PLACEHOLDER: infinite fallback costs 0 */
        .projectile_speed = 0,         /* TUNABLE-PLACEHOLDER: instant hitscan */
        .projectile_range = 180,       /* TUNABLE-PLACEHOLDER: tracer range (world px) */
        .spread_angle = 0,             /* TUNABLE-PLACEHOLDER: pinpoint precision */
        .spinup_delay = 0,             /* TUNABLE-PLACEHOLDER: immediate response */
        .speed_penalty = 256,          /* TUNABLE-PLACEHOLDER: 1.0 (no movement penalty) */
        .explosion_radius = 0,         /* TUNABLE-PLACEHOLDER */
        .explosion_damage = 0          /* TUNABLE-PLACEHOLDER */
    },
    [WEAPON_SHOTGUN] = {
        .name = "SHOTGUN",
        .fire_mode = FIRE_MODE_PROJECTILE,
        .damage_per_hit = 8,           /* TUNABLE-PLACEHOLDER: 8 dmg * 5 pellets = 40 max */
        .pellets = 5,                  /* TUNABLE-PLACEHOLDER: 5 pellets spread */
        .fire_cooldown = 36,           /* TUNABLE-PLACEHOLDER: marked recoil & pump */
        .max_ammo = 50,                /* TUNABLE-PLACEHOLDER: medium capacity */
        .pickup_ammo_amount = 10,      /* TUNABLE-PLACEHOLDER: shells per box */
        .ammo_cost = 1,                /* TUNABLE-PLACEHOLDER: 1 shell per blast */
        .projectile_speed = 1536,      /* TUNABLE-PLACEHOLDER: 8.8 fixed: 6.0 px/frame */
        .projectile_range = 22,        /* TUNABLE-PLACEHOLDER: short range (~132 px max) */
        .spread_angle = 120,           /* TUNABLE-PLACEHOLDER: wide cone dispersion */
        .spinup_delay = 0,             /* TUNABLE-PLACEHOLDER: immediate blast */
        .speed_penalty = 256,          /* TUNABLE-PLACEHOLDER: 1.0 (no slowdown) */
        .explosion_radius = 0,         /* TUNABLE-PLACEHOLDER */
        .explosion_damage = 0          /* TUNABLE-PLACEHOLDER */
    },
    [WEAPON_GATLING] = {
        .name = "GATLING",
        .fire_mode = FIRE_MODE_HITSCAN,
        .damage_per_hit = 5,           /* TUNABLE-PLACEHOLDER: fast sustained damage */
        .pellets = 1,                  /* TUNABLE-PLACEHOLDER: continuous stream */
        .fire_cooldown = 4,            /* TUNABLE-PLACEHOLDER: rapid fire rate */
        .max_ammo = 200,               /* TUNABLE-PLACEHOLDER: high ammo capacity */
        .pickup_ammo_amount = 40,      /* TUNABLE-PLACEHOLDER: bullets per box */
        .ammo_cost = 1,                /* TUNABLE-PLACEHOLDER: 1 bullet per shot */
        .projectile_speed = 0,         /* TUNABLE-PLACEHOLDER: hitscan tracers */
        .projectile_range = 160,       /* TUNABLE-PLACEHOLDER: medium-long range */
        .spread_angle = 24,            /* TUNABLE-PLACEHOLDER: slight jitter/spread */
        .spinup_delay = 10,            /* TUNABLE-PLACEHOLDER: spin-up delay frames */
        .speed_penalty = 128,          /* TUNABLE-PLACEHOLDER: 8.8 fixed: 0.5 (50% speed) */
        .explosion_radius = 0,         /* TUNABLE-PLACEHOLDER */
        .explosion_damage = 0          /* TUNABLE-PLACEHOLDER */
    },
    [WEAPON_HEAVY] = {
        .name = "HEAVY",
        .fire_mode = FIRE_MODE_PROJECTILE,
        .damage_per_hit = 25,          /* TUNABLE-PLACEHOLDER: direct impact damage */
        .pellets = 1,                  /* TUNABLE-PLACEHOLDER: single rocket */
        .fire_cooldown = 55,           /* TUNABLE-PLACEHOLDER: slow reload */
        .max_ammo = 20,                /* TUNABLE-PLACEHOLDER: scarce heavy ammo */
        .pickup_ammo_amount = 5,       /* TUNABLE-PLACEHOLDER: rockets per box */
        .ammo_cost = 1,                /* TUNABLE-PLACEHOLDER: 1 rocket per shot */
        .projectile_speed = 1024,      /* TUNABLE-PLACEHOLDER: 8.8 fixed: 4.0 px/frame */
        .projectile_range = 60,        /* TUNABLE-PLACEHOLDER: long travel range */
        .spread_angle = 0,             /* TUNABLE-PLACEHOLDER: direct flight */
        .spinup_delay = 0,             /* TUNABLE-PLACEHOLDER: immediate launch */
        .speed_penalty = 256,          /* TUNABLE-PLACEHOLDER: 1.0 (no slowdown) */
        .explosion_radius = 32,        /* TUNABLE-PLACEHOLDER: 32px blast radius */
        .explosion_damage = 45         /* TUNABLE-PLACEHOLDER: area splash damage */
    }
};

static PlayerProjectile s_player_projectiles[MAX_PLAYER_PROJECTILES];
#define MAX_SPARKS 24
typedef struct {
    int active;
    fixed x, y;
    fixed vx, vy;
    int life;
    uint16_t color;
} WeaponSpark;

static WeaponTracer s_tracers[MAX_TRACERS];
static WeaponExplosion s_explosions[MAX_EXPLOSIONS];
static WeaponSpark s_sparks[MAX_SPARKS];
static int s_weapon_cooldown = 0;
static int s_gatling_spinup = 0;
static uint32_t s_weapon_tick = 0;

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
    s_gatling_spinup = 0;
    s_weapon_tick = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        s_player_projectiles[i].active = 0;
    }
    for (int i = 0; i < MAX_TRACERS; i++) {
        s_tracers[i].active = 0;
    }
    for (int i = 0; i < MAX_EXPLOSIONS; i++) {
        s_explosions[i].active = 0;
    }
    for (int i = 0; i < MAX_SPARKS; i++) {
        s_sparks[i].active = 0;
    }
}

void weapons_cycle(PlayerState *player, int delta) {
    if (!player) return;
    int next_w = (int)player->current_weapon + delta;
    if (next_w < 0) next_w = NUM_WEAPON_TYPES - 1;
    if (next_w >= NUM_WEAPON_TYPES) next_w = 0;
    player->current_weapon = (WeaponType)next_w;
    s_weapon_cooldown = 0;
    s_gatling_spinup = 0;
}

int weapons_can_fire(const PlayerState *player) {
    (void)player;
    return s_weapon_cooldown <= 0;
}

fixed weapons_get_speed_factor(const PlayerState *player, int is_firing_held) {
    if (!player) return 256;
    if (is_firing_held && player->current_weapon == WEAPON_GATLING) {
        return g_weapon_tuning[WEAPON_GATLING].speed_penalty;
    }
    return 256;
}

const char *weapons_get_name(WeaponType type) {
    if (type >= 0 && type < NUM_WEAPON_TYPES) {
        return g_weapon_tuning[type].name;
    }
    return "UNKNOWN";
}

int weapons_get_active_projectile_count(void) {
    int count = 0;
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        if (s_player_projectiles[i].active) count++;
    }
    return count;
}

static void spawn_sparks(fixed x, fixed y, uint16_t color) {
    static const int dirs[6][2] = {
        { 256, 128 }, { -256, 128 }, { 128, -256 }, { -128, -256 },
        { 0, 300 }, { 0, -300 }
    };
    for (int k = 0; k < 6; k++) {
        for (int i = 0; i < MAX_SPARKS; i++) {
            if (!s_sparks[i].active) {
                s_sparks[i].active = 1;
                s_sparks[i].x = x;
                s_sparks[i].y = y;
                s_sparks[i].vx = (fixed)dirs[k][0];
                s_sparks[i].vy = (fixed)dirs[k][1];
                s_sparks[i].life = 14;
                s_sparks[i].color = color;
                break;
            }
        }
    }
}

static void spawn_tracer(fixed start_x, fixed start_y, fixed end_x, fixed end_y, WeaponType weapon) {
    for (int i = 0; i < MAX_TRACERS; i++) {
        if (!s_tracers[i].active) {
            s_tracers[i].active = 1;
            s_tracers[i].weapon_type = weapon;
            s_tracers[i].start_x = start_x;
            s_tracers[i].start_y = start_y;
            s_tracers[i].end_x = end_x;
            s_tracers[i].end_y = end_y;
            s_tracers[i].life = (weapon == WEAPON_PISTOL) ? 4 : 2;
            return;
        }
    }
}

static void spawn_explosion(fixed x, fixed y, int radius, int damage,
                            Enemy *enemies, int max_enemies) {
    for (int i = 0; i < MAX_EXPLOSIONS; i++) {
        if (!s_explosions[i].active) {
            s_explosions[i].active = 1;
            s_explosions[i].x = x;
            s_explosions[i].y = y;
            s_explosions[i].radius = radius;
            s_explosions[i].life = 8;
            s_explosions[i].max_life = 8;
            break;
        }
    }

    int r2 = radius * radius;
    for (int i = 0; i < max_enemies; i++) {
        Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0) continue;
        int dx = TO_INT(e->x - x);
        int dy = TO_INT(e->y - y);
        if (dx * dx + dy * dy <= r2) {
            fixed push_x = (fixed)(dx << 8);
            fixed push_y = (fixed)(dy << 8);
            enemy_hit(e, damage, push_x, push_y);
        }
    }

    char msg[64];
    snprintf(msg, sizeof(msg), "ROCKET_EXPLOSION r=%d dmg=%d", radius, damage);
    nocashMessage(msg);
}

int weapons_fire(PlayerState *player, fixed player_x, fixed player_y,
                 int aim_screen_x, int aim_screen_y, int cam_x, int cam_y,
                 int is_firing_held, Enemy *enemies, int max_enemies) {
    (void)cam_x;
    (void)cam_y;
    if (!player || player->is_dead) return 0;

    const WeaponTuning *tuning = &g_weapon_tuning[player->current_weapon];

    // Gatling spinup handling
    if (player->current_weapon == WEAPON_GATLING) {
        if (is_firing_held) {
            s_gatling_spinup++;
            if (s_gatling_spinup < tuning->spinup_delay) {
                return 0; // Still spinning up
            }
        } else {
            s_gatling_spinup = 0;
            return 0;
        }
    } else {
        s_gatling_spinup = 0;
    }

    if (s_weapon_cooldown > 0) return 0;

    // Ammo check & infinite pistol fallback
    if (tuning->ammo_cost > 0) {
        if (player->ammo[player->current_weapon] < tuning->ammo_cost) {
            player->current_weapon = WEAPON_PISTOL;
            tuning = &g_weapon_tuning[WEAPON_PISTOL];
            s_gatling_spinup = 0;
        }
    }

    // Deduct ammo
    if (tuning->ammo_cost > 0) {
        player->ammo[player->current_weapon] -= tuning->ammo_cost;
        if (player->ammo[player->current_weapon] <= 0) {
            player->ammo[player->current_weapon] = 0;
            player->current_weapon = WEAPON_PISTOL; // Fallback when exhausted
        }
    }

    s_weapon_cooldown = tuning->fire_cooldown;
    s_weapon_tick++;

    // Calculate normalized 8.8 aim vector
    int px = TO_INT(player_x);
    int py = TO_INT(player_y);
    int dx = aim_screen_x - px;
    int dy = aim_screen_y - py;
    uint32_t len = int_sqrt((uint32_t)(dx * dx + dy * dy));
    if (len == 0) len = 1;
    fixed dir_x = (fixed)(((int64_t)dx << 8) / (int32_t)len);
    fixed dir_y = (fixed)(((int64_t)dy << 8) / (int32_t)len);
    fixed perp_x = -dir_y;
    fixed perp_y = dir_x;

    if (tuning->fire_mode == FIRE_MODE_HITSCAN) {
        // Hitscan trace
        fixed cur_dir_x = dir_x;
        fixed cur_dir_y = dir_y;
        if (tuning->spread_angle > 0) {
            int jitter = (int)(rng_next() % 51u) - 25; // -25..+25
            fixed offset = (fixed)(jitter * tuning->spread_angle) >> 5;
            cur_dir_x += (perp_x * offset) >> 8;
            cur_dir_y += (perp_y * offset) >> 8;
        }

        fixed cur_x = player_x;
        fixed cur_y = player_y;
        fixed step_x = (cur_dir_x * 2);
        fixed step_y = (cur_dir_y * 2);

        for (int d = 0; d < tuning->projectile_range; d += 2) {
            cur_x += step_x;
            cur_y += step_y;

            if (!bullet_position_is_free(cur_x, cur_y)) {
                break;
            }

            int hit_enemy = -1;
            for (int i = 0; i < max_enemies; i++) {
                Enemy *e = &enemies[i];
                if (!e->active || e->hp <= 0) continue;
                int edx = TO_INT(cur_x - e->x);
                int edy = TO_INT(cur_y - e->y);
                if (edx * edx + edy * edy <= 12 * 12) {
                    hit_enemy = i;
                    break;
                }
            }

            if (hit_enemy >= 0) {
                enemy_hit(&enemies[hit_enemy], tuning->damage_per_hit, cur_dir_x * 4, cur_dir_y * 4);
                break;
            }
        }

        spawn_tracer(player_x, player_y, cur_x, cur_y, player->current_weapon);
        uint16_t spark_col = (player->current_weapon == WEAPON_PISTOL) ?
            (RGB15(15, 31, 31) | BIT(15)) : (RGB15(31, 28, 8) | BIT(15));
        spawn_sparks(cur_x, cur_y, spark_col);
        spawn_sparks(player_x + ((cur_dir_x * 8) >> 8), player_y + ((cur_dir_y * 8) >> 8), spark_col);
    } else {
        // Projectile fire mode
        int pellets = tuning->pellets > 0 ? tuning->pellets : 1;
        for (int p_idx = 0; p_idx < pellets; p_idx++) {
            // Find free projectile slot
            int slot = -1;
            for (int s = 0; s < MAX_PLAYER_PROJECTILES; s++) {
                if (!s_player_projectiles[s].active) {
                    slot = s;
                    break;
                }
            }
            if (slot < 0) break;

            int spread_idx = (pellets > 1) ? (p_idx - (pellets / 2)) : 0;
            fixed spread_offset = (spread_idx * tuning->spread_angle) / 2;
            fixed vx = ((dir_x * tuning->projectile_speed) >> 8) + ((perp_x * spread_offset) >> 8);
            fixed vy = ((dir_y * tuning->projectile_speed) >> 8) + ((perp_y * spread_offset) >> 8);

            PlayerProjectile *proj = &s_player_projectiles[slot];
            proj->active = 1;
            proj->weapon_type = player->current_weapon;
            proj->x = player_x + (vx / 4);
            proj->y = player_y + (vy / 4);
            proj->vx = vx;
            proj->vy = vy;
            proj->life = tuning->projectile_range;
            proj->max_life = tuning->projectile_range;
            proj->damage = tuning->damage_per_hit;
            proj->is_explosive = (tuning->explosion_radius > 0);
            proj->explosion_radius = tuning->explosion_radius;
            proj->explosion_damage = tuning->explosion_damage;
            proj->hit_mask = 0;
            proj->seed = (uint8_t)(slot * 11 + p_idx * 7 + s_weapon_tick);
        }
    }

    char msg[64];
    snprintf(msg, sizeof(msg), "WEAPON_FIRE weapon=%s ammo=%d",
             tuning->name, player->ammo[player->current_weapon]);
    nocashMessage(msg);
    return 1;
}

void weapons_update(Enemy *enemies, int max_enemies, fixed player_x, fixed player_y) {
    (void)player_x;
    (void)player_y;
    if (s_weapon_cooldown > 0) s_weapon_cooldown--;

    for (int i = 0; i < MAX_TRACERS; i++) {
        if (!s_tracers[i].active) continue;
        s_tracers[i].life--;
        if (s_tracers[i].life <= 0) {
            s_tracers[i].active = 0;
        }
    }

    for (int i = 0; i < MAX_EXPLOSIONS; i++) {
        if (!s_explosions[i].active) continue;
        s_explosions[i].life--;
        if (s_explosions[i].life <= 0) {
            s_explosions[i].active = 0;
        }
    }

    for (int i = 0; i < MAX_SPARKS; i++) {
        if (!s_sparks[i].active) continue;
        s_sparks[i].x += s_sparks[i].vx;
        s_sparks[i].y += s_sparks[i].vy;
        s_sparks[i].life--;
        if (s_sparks[i].life <= 0) {
            s_sparks[i].active = 0;
        }
    }

    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;

        p->life--;
        if (p->life <= 0) {
            if (p->is_explosive) {
                spawn_explosion(p->x, p->y, p->explosion_radius, p->explosion_damage, enemies, max_enemies);
            }
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
            if (!bullet_position_is_free(nx, ny)) {
                blocked = 1;
                break;
            }
            p->x = nx;
            p->y = ny;
        }

        if (blocked) {
            if (p->is_explosive) {
                spawn_explosion(p->x, p->y, p->explosion_radius, p->explosion_damage, enemies, max_enemies);
            }
            p->active = 0;
            continue;
        }

        for (int e_idx = 0; e_idx < max_enemies; e_idx++) {
            Enemy *e = &enemies[e_idx];
            if (!e->active || e->hp <= 0 || (p->hit_mask & (1u << e_idx))) continue;
            int dx = TO_INT(p->x - e->x);
            int dy = TO_INT(p->y - e->y);
            if (dx * dx + dy * dy <= 12 * 12) {
                if (p->is_explosive) {
                    spawn_explosion(p->x, p->y, p->explosion_radius, p->explosion_damage, enemies, max_enemies);
                } else {
                    enemy_hit(e, p->damage, p->vx, p->vy);
                    p->hit_mask |= (uint16_t)(1u << e_idx);
                }
                p->active = 0;
                break;
            }
        }
    }
}

void weapons_render(uint16_t *buffer, int cam_x, int cam_y) {
    if (!buffer) return;

    // 1. Tracers
    for (int i = 0; i < MAX_TRACERS; i++) {
        WeaponTracer *t = &s_tracers[i];
        if (!t->active) continue;

        int x0 = TO_INT(t->start_x) - cam_x;
        int y0 = TO_INT(t->start_y) - cam_y;
        int x1 = TO_INT(t->end_x) - cam_x;
        int y1 = TO_INT(t->end_y) - cam_y;

        uint16_t color = (t->weapon_type == WEAPON_PISTOL) ?
            (RGB15(8, 28, 31) | BIT(15)) :  // Cyan tracer for pistol
            (RGB15(31, 28, 6) | BIT(15));   // Gold-yellow tracer for gatling

        int dx = x1 - x0;
        int dy = y1 - y0;
        int adx = abs_int(dx);
        int ady = abs_int(dy);
        int sx = dx < 0 ? -1 : 1;
        int sy = dy < 0 ? -1 : 1;
        int err = (adx > ady ? adx : -ady) / 2;

        int cur_x = x0, cur_y = y0;
        for (int step = 0; step < 160; step++) {
            if (cur_x >= 0 && cur_x < SCREEN_W && cur_y >= 0 && cur_y < SCREEN_H) {
                buffer[cur_y * SCREEN_W + cur_x] = color;
            }
            if (cur_x == x1 && cur_y == y1) break;
            int e2 = err;
            if (e2 > -adx) { err -= ady; cur_x += sx; }
            if (e2 < ady)  { err += adx; cur_y += sy; }
        }

        // Impact spark at end
        if (x1 >= 1 && x1 < SCREEN_W - 1 && y1 >= 1 && y1 < SCREEN_H - 1) {
            uint16_t spark = (RGB15(31, 31, 31) | BIT(15));
            buffer[y1 * SCREEN_W + x1] = spark;
            buffer[(y1 - 1) * SCREEN_W + x1] = color;
            buffer[(y1 + 1) * SCREEN_W + x1] = color;
            buffer[y1 * SCREEN_W + x1 - 1] = color;
            buffer[y1 * SCREEN_W + x1 + 1] = color;
        }
    }

    // 2. Projectiles
    for (int i = 0; i < MAX_PLAYER_PROJECTILES; i++) {
        PlayerProjectile *p = &s_player_projectiles[i];
        if (!p->active) continue;

        int sx = TO_INT(p->x) - cam_x;
        int sy = TO_INT(p->y) - cam_y;

        if (sx < 1 || sx >= SCREEN_W - 2 || sy < 1 || sy >= SCREEN_H - 2) continue;

        if (p->weapon_type == WEAPON_SHOTGUN) {
            uint16_t pellet = (RGB15(31, 26, 12) | BIT(15));
            uint16_t edge = (RGB15(24, 16, 4) | BIT(15));
            buffer[sy * SCREEN_W + sx] = pellet;
            buffer[sy * SCREEN_W + sx + 1] = edge;
            buffer[(sy + 1) * SCREEN_W + sx] = edge;
        } else if (p->weapon_type == WEAPON_HEAVY) {
            uint16_t tip = (RGB15(31, 31, 10) | BIT(15));
            uint16_t body = (RGB15(31, 6, 2) | BIT(15));
            uint16_t fin = (RGB15(16, 4, 1) | BIT(15));

            buffer[sy * SCREEN_W + sx] = tip;
            buffer[(sy - 1) * SCREEN_W + sx] = body;
            buffer[(sy + 1) * SCREEN_W + sx] = body;
            buffer[sy * SCREEN_W + sx - 1] = fin;
            buffer[sy * SCREEN_W + sx + 1] = fin;
        }
    }

    // 3. Explosions
    for (int i = 0; i < MAX_EXPLOSIONS; i++) {
        WeaponExplosion *e = &s_explosions[i];
        if (!e->active) continue;

        int ex = TO_INT(e->x) - cam_x;
        int ey = TO_INT(e->y) - cam_y;
        int progress = e->max_life - e->life;
        int cur_r = (e->radius * progress) / e->max_life;
        if (cur_r < 2) cur_r = 2;

        uint16_t blast_outer = (RGB15(31, 28, 4) | BIT(15));
        uint16_t blast_inner = (RGB15(31, 10, 0) | BIT(15));

        for (int dy = -cur_r; dy <= cur_r; dy += 2) {
            int py = ey + dy;
            if (py < 0 || py >= SCREEN_H) continue;
            int span = cur_r - abs_int(dy);
            int px1 = ex - span;
            int px2 = ex + span;
            if (px1 >= 0 && px1 < SCREEN_W) buffer[py * SCREEN_W + px1] = blast_outer;
            if (px2 >= 0 && px2 < SCREEN_W) buffer[py * SCREEN_W + px2] = blast_outer;
            if (span > 2) {
                int px_in1 = ex - span / 2;
                int px_in2 = ex + span / 2;
                if (px_in1 >= 0 && px_in1 < SCREEN_W) buffer[py * SCREEN_W + px_in1] = blast_inner;
                if (px_in2 >= 0 && px_in2 < SCREEN_W) buffer[py * SCREEN_W + px_in2] = blast_inner;
            }
        }
    }

    // 4. Sparks
    for (int i = 0; i < MAX_SPARKS; i++) {
        if (!s_sparks[i].active) continue;
        int sx = TO_INT(s_sparks[i].x) - cam_x;
        int sy = TO_INT(s_sparks[i].y) - cam_y;
        if (sx >= 1 && sx < SCREEN_W - 1 && sy >= 1 && sy < SCREEN_H - 1) {
            buffer[sy * SCREEN_W + sx] = s_sparks[i].color;
            buffer[(sy - 1) * SCREEN_W + sx] = s_sparks[i].color;
            buffer[sy * SCREEN_W + sx + 1] = s_sparks[i].color;
        }
    }
}
