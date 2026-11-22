#include "allies.h"
#include "arpg.h"
#include "arpg_tree.h"
#include "glifo.h"
#include "collision.h"
#include "enemy_ai.h"
#include "player_sprite.h"
#include "upgrades.h"
#if ENCOUNTERS_PROTO
#include "encounters_act1.h"
#endif
#include <nds.h>
#include <string.h>

uint8_t g_enemy_ally[MAX_GAMEPLAY_ENEMIES];
uint16_t g_ally_timer[MAX_GAMEPLAY_ENEMIES];

// Blasts are queued and run from allies_update, not inside the death hook: a blast from inside the hook would
// damage other enemies while the first death is still being processed.
#define ALLY_BLAST_QUEUE 4
static int s_blast_x[ALLY_BLAST_QUEUE], s_blast_y[ALLY_BLAST_QUEUE];
static int s_blast_count;

void allies_reset(void) {
    memset(g_enemy_ally, 0, sizeof(g_enemy_ally));
    memset(g_ally_timer, 0, sizeof(g_ally_timer));
    s_blast_count = 0;
}

int allies_is_ally(const Enemy *e, const Enemy *base) {
    int slot = (int)(e - base);
    return slot >= 0 && slot < MAX_GAMEPLAY_ENEMIES && g_enemy_ally[slot] != 0;
}

static int live_allies(const Enemy *enemies, int max_enemies) {
    int n = 0;
    for (int i = 0; i < max_enemies; i++)
        if (g_enemy_ally[i] && enemies[i].active && enemies[i].hp > 0) n++;
    return n;
}

static void ally_blast(int bx, int by, Enemy *enemies, int max_enemies) {
    const int r2 = ARPG_ALLY_BLAST_RADIUS * ARPG_ALLY_BLAST_RADIUS;
    for (int i = 0; i < max_enemies; i++) {
        if (g_enemy_ally[i]) continue;                       // allies never hurt allies
        Enemy *e = &enemies[i];
        if (!e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE) continue;
        int dx = TO_INT(e->x) - bx, dy = TO_INT(e->y) - by;
        if (dx * dx + GROUND_DY2(dy) > r2) continue;
        burn_apply(e, 2);
        enemy_hit(e, upgrades_fire_damage(ARPG_ALLY_BLAST_DAMAGE), 0, 0);
    }
}

void allies_on_enemy_death(Enemy *dead, Enemy *enemies, int max_enemies) {
    int slot = (int)(dead - enemies);
    if (slot < 0 || slot >= max_enemies || slot >= MAX_GAMEPLAY_ENEMIES) return;

    if (g_enemy_ally[slot]) {                                // an ally died: its flag goes, and node 12 blasts
        g_enemy_ally[slot] = 0;
        g_ally_timer[slot] = 0;
        if (arpg_tree_has(12) && s_blast_count < ALLY_BLAST_QUEUE) {
            s_blast_x[s_blast_count] = TO_INT(dead->x);
            s_blast_y[s_blast_count] = TO_INT(dead->y);
            s_blast_count++;
        }
        return;
    }

    if (!arpg_tree_has(10)) return;
    if (dead->type == ENEMY_TYPE_ABANDERADO) return;
    if (!glifo_point_in_zone(TO_INT(dead->x), TO_INT(dead->y))) return;
    int cap = arpg_tree_has(11) ? ARPG_ALLY_MAX_2 : ARPG_ALLY_MAX_1;
    if (live_allies(enemies, max_enemies) >= cap) return;

    int free_slot = -1;
    for (int s = 0; s < max_enemies; s++) {
        if (!enemies[s].active) { free_slot = s; break; }    // the dead one is still active here, so it is never reused
    }
    if (free_slot < 0) return;

    Enemy *a = &enemies[free_slot];
    memset(a, 0, sizeof(*a));
    a->x = dead->x;
    a->y = dead->y;
    a->active = 1;
    a->type = ENEMY_TYPE_EXVOTO;
    a->char_id = enemy_type_char_id(ENEMY_TYPE_EXVOTO);
    a->max_hp = ARPG_ALLY_HP;
    a->hp = ARPG_ALLY_HP;
    a->dir = dead->dir;
    a->strafe_dir = 1;
    a->state = ENEMY_STATE_CHASE;
    a->pack = -1;                                            // no encounter: never counted for a room, never blocks one
    g_enemy_ally[free_slot] = 1;
    g_ally_timer[free_slot] = (uint16_t)(arpg_tree_has(11) ? ARPG_ALLY_FRAMES_2 : ARPG_ALLY_FRAMES_1);
}

// Walk step with wall slide: X, then Y; each sweep stops at the first blocked point.
static int ally_move(fixed *x, fixed *y, fixed vx, fixed vy) {
    int moved = 0;
    fixed nx = *x, ny = *y;
    if (vx && sweep_position(&nx, &ny, vx, 0)) moved = 1;
    if (vy && sweep_position(&nx, &ny, 0, vy)) moved = 1;
    *x = nx;
    *y = ny;
    return moved;
}

static void ally_animate(Enemy *a, int moved) {
    int anim_period = g_characters[a->char_id].anim_period;
    if (anim_period <= 0) anim_period = 4;
    if (moved) {
        if (++a->anim_timer >= anim_period) {
            a->anim_timer = 0;
            a->frame = (a->frame + 1) % PLAYER_NUM_FRAMES;
        }
    } else {
        a->anim_timer = 0;
        a->frame = 0;
    }
}

void allies_update(Enemy *enemies, int max_enemies) {
    int blasts = s_blast_count;
    s_blast_count = 0;
    for (int b = 0; b < blasts; b++) ally_blast(s_blast_x[b], s_blast_y[b], enemies, max_enemies);

    const int range2 = ARPG_ALLY_RANGE * ARPG_ALLY_RANGE;
    for (int i = 0; i < max_enemies; i++) {
        if (!g_enemy_ally[i]) continue;
        Enemy *a = &enemies[i];
        if (!a->active || a->hp <= 0) { g_enemy_ally[i] = 0; g_ally_timer[i] = 0; continue; }

        if (g_ally_timer[i] > 0) g_ally_timer[i]--;
        if (g_ally_timer[i] == 0) { enemy_hit(a, 9999, 0, 0); continue; }   // time is up: it dies (and blasts with node 12)
        if (a->hit_timer > 0) a->hit_timer--;
        if (a->state_timer > 0) a->state_timer--;

        // Nearest living enemy that is not an ally and not held asleep by an encounter (the same rule as the hero's hits).
        Enemy *t = NULL;
        int best = 0x7fffffff;
        for (int j = 0; j < max_enemies; j++) {
            if (g_enemy_ally[j]) continue;
            Enemy *c = &enemies[j];
            if (!c->active || c->hp <= 0 || c->state == ENEMY_STATE_EMERGE || c->state == ENEMY_STATE_SUSPENDED) continue;
#if ENCOUNTERS_PROTO
            if (enc_untouchable(c)) continue;
#endif
            int dx = TO_INT(c->x - a->x), dy = TO_INT(c->y - a->y);
            int d2 = dx * dx + GROUND_DY2(dy);
            if (d2 < best) { best = d2; t = c; }
        }
        if (!t) { ally_animate(a, 0); continue; }                  // nothing to fight: stands still

        int dx = TO_INT(t->x - a->x), dy = TO_INT(t->y - a->y);
        int d2 = dx * dx + GROUND_DY2(dy);
        if (d2 > range2) {
            int dist = (int)sqrt32(d2);
            fixed speed = g_enemy_tuning[ENEMY_TYPE_EXVOTO].speed;
            fixed vx = (fixed)div32(dx * (int32_t)speed, (int32_t)dist);
            fixed vy = (fixed)div32(dy * (int32_t)speed, (int32_t)dist);
            int moved = ally_move(&a->x, &a->y, vx, vy);
            a->dir = enemy_dir_from_vector(TO_FIXED(dx), TO_FIXED(dy));
            ally_animate(a, moved);
        } else {
            a->dir = enemy_dir_from_vector(TO_FIXED(dx), TO_FIXED(dy));
            ally_animate(a, 0);
            if (a->state_timer == 0) {
                a->state_timer = ARPG_ALLY_ATTACK_FRAMES;
                enemy_hit(t, ARPG_ALLY_DAMAGE, 0, 0);
            }
        }
    }
}
