#include "punch.h"
#include "arpg_balance.h"
#include "collision.h"
#include "enemy_ai.h"
#include "weapons.h"
#include "allies.h"
#include "modifiers.h"
#include "upgrades.h"
#include "sfx.h"
#include "lab_tuning.h"
#if ENCOUNTERS_PROTO
#include "encounters_act1.h"
#endif
#include <stdio.h>

static uint8_t s_punch_bin_buf[PUNCH_MAX_BIN_BYTES] __attribute__((aligned(4)));
static int s_punch_loaded_move = -1;
static int s_punch_loaded_dir = -1;

static const char *move_name(int move) {
    return move == PUNCH_MOVE_A ? "punch_a" : move == PUNCH_MOVE_B ? "punch_b" : "gancho";
}

static int punch_load_bin(int move, int dir) {
    if (s_punch_loaded_move == move && s_punch_loaded_dir == dir) return 1;
    char path[48];
    snprintf(path, sizeof(path), "nitro:/punch/%s_d%d.bin", move_name(move), dir);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    size_t n = fread(s_punch_bin_buf, 1, sizeof(s_punch_bin_buf), f);
    fclose(f);
    if (n < sizeof(PunchBinHeader)) { s_punch_loaded_move = -1; return 0; }
    const PunchBinHeader *h = (const PunchBinHeader *)s_punch_bin_buf;
    if (h->magic != PUNCH_BIN_MAGIC || sizeof(PunchBinHeader) + h->pix_bytes + h->runs_bytes > n) {
        s_punch_loaded_move = -1;
        return 0;
    }
    s_punch_loaded_move = move;
    s_punch_loaded_dir = dir;
    return 1;
}

static int s_punch_active;
static int s_punch_move;
static int s_punch_dir;
static int s_punch_frame;
static int s_punch_t;
static int s_punch_chain;     // frames de ventana de encadenado que quedan
static int s_punch_target = -1;    // enemigo elegido al arrancar; el golpe lo cobra en el fotograma de impacto
static int s_punch_cone;           // 1 = andando (el objetivo debe seguir en el cono frontal), 0 = parado (soft-lock)
static int s_punch_applied;        // el impacto de este golpe ya se ha aplicado (una vez por golpe)
static int s_punch_queued;    // golpes guardados (0..2): cada L nuevo durante el golpe suma uno; se cobran cuando toca, sin cortar la animacion

int punch_active(void) { return s_punch_active; }
int punch_move(void) { return s_punch_move; }
int punch_dir(void) { return s_punch_dir; }
int punch_frame(void) { return s_punch_frame; }
int punch_chain_window(void) { return s_punch_chain; }

void punch_reset(void) {
    s_punch_active = 0;
    s_punch_chain = 0;
    s_punch_queued = 0;
    s_punch_target = -1;
    s_punch_applied = 1;
}

const uint16_t *punch_pixels(void) {
    if (!s_punch_active) return NULL;
    const PunchBinHeader *h = (const PunchBinHeader *)s_punch_bin_buf;
    return (const uint16_t *)(s_punch_bin_buf + sizeof(PunchBinHeader)) + h->pix_off[s_punch_frame];
}

const uint16_t *punch_runs(void) {
    if (!s_punch_active) return NULL;
    const PunchBinHeader *h = (const PunchBinHeader *)s_punch_bin_buf;
    return (const uint16_t *)(s_punch_bin_buf + sizeof(PunchBinHeader) + h->pix_bytes) + h->run_off[s_punch_frame];
}

const uint8_t *punch_bounds(void) {
    if (!s_punch_active) return NULL;
    const PunchBinHeader *h = (const PunchBinHeader *)s_punch_bin_buf;
    return h->bounds[s_punch_frame];
}

int punch_ground_anchor(void) { return g_punch_ground_anchor[s_punch_move][s_punch_dir]; }

// Nearest enemy this close, and whether it is reeling (<= 25 % life, gameplay.c): the hit goes to it.
// `cone` 0 = cualquier direccion (parado, soft-lock). 1 = solo en +-45 grados de `dir` (andando: el golpe
// va hacia donde el heroe camina, sin girarse hacia un enemigo que queda detras).
// Un enemigo puede recibir el golpe desde (hero_x, hero_y): activo, vivo, a tiro y, andando, en el cono frontal.
static int punch_can_hit(const Enemy *e, int i, int hx, int hy, int dir, int cone, int *d2out) {
    const int range = PUNCH_RANGE_V * (100 + g_mods.remate_range_bonus) / 100;
    if (g_enemy_ally[i] || !e->active || e->hp <= 0 || e->state == ENEMY_STATE_EMERGE) return 0;
#if ENCOUNTERS_PROTO
    if (enc_untouchable(e)) return 0;
#endif
    const int dx = TO_INT(e->x) - hx, dy = TO_INT(e->y) - hy;
    const int d2 = dx * dx + GROUND_DY2(dy);
    if (cone && d2 >= 16) {                              // a bocajarro (< 4 px) no se filtra por angulo
        int dd = (enemy_dir_from_vector(TO_FIXED(dx), TO_FIXED(dy)) - dir) & 7;
        if (dd > 4) dd = 8 - dd;
        if (dd > 1) return 0;                             // fuera del cono frontal de +-45 grados
    }
    if (d2 > range * range) return 0;
    *d2out = d2;
    return 1;
}

static int punch_target(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y,
                        int dir, int cone, int *ex, int *ey) {
    const int hx = TO_INT(hero_x), hy = TO_INT(hero_y);
    const int range = PUNCH_RANGE_V * (100 + g_mods.remate_range_bonus) / 100;
    int best = -1, best_d2 = range * range + 1;
    for (int i = 0; i < max_enemies; i++) {
        int d2;
        if (punch_can_hit(&enemies[i], i, hx, hy, dir, cone, &d2) && d2 < best_d2) { best_d2 = d2; best = i; }
    }
    if (best < 0) return -1;
    *ex = TO_INT(enemies[best].x);
    *ey = TO_INT(enemies[best].y);
    return best;
}

// Empuje hacia atras desde el heroe en la metrica de suelo 2:1.
static void punch_push_vec(const Enemy *e, fixed hero_x, fixed hero_y, fixed strength, fixed *px, fixed *py) {
    const int dx = TO_INT(e->x) - TO_INT(hero_x);
    const int dy = TO_INT(e->y) - TO_INT(hero_y);
    *px = dx < 0 ? -strength : (dx > 0 ? strength : 0);
    *py = dy < 0 ? -(strength >> 1) : (dy > 0 ? (strength >> 1) : 0);
}

// Aplica el golpe al enemigo `idx` ya elegido (el mismo que fijo la direccion): el efecto visible y el
// dano no pueden apuntar a enemigos distintos.
static void punch_apply(Enemy *enemies, int idx, fixed hero_x, fixed hero_y, int move) {
    if (idx < 0) return;
    Enemy *e = &enemies[idx];
    const int ex = TO_INT(e->x);
    const fixed push = (move == PUNCH_MOVE_HOOK) ? PUNCH_HOOK_PUSH_V : PUNCH_LIGHT_PUSH_V;
    const int base_dmg = (move == PUNCH_MOVE_HOOK) ? BAL(punch_hook, PUNCH_DAMAGE_HOOK)
                       : (move == PUNCH_MOVE_A)    ? BAL(punch_a, PUNCH_DAMAGE_A) : BAL(punch_b, PUNCH_DAMAGE_B);
    const int dmg = upgrades_punch_damage(base_dmg);
    fixed px = 0, py = 0;
    punch_push_vec(e, hero_x, hero_y, push, &px, &py);
    enemy_hit(e, dmg, px, py);
    // enemy_hit solo usa el empuje al morir: al que sobrevive se le da aqui el retroceso y un hit-stun corto
    // (DESIGN.md 7.2), que enemy_ai mueve con deslizamiento mientras dura.
    if (e->active && e->hp > 0) {
        e->knock_vx = px;
        e->knock_vy = py;
        if (e->stun_timer < PUNCH_HITSTUN_FRAMES) e->stun_timer = PUNCH_HITSTUN_FRAMES;
    }
    sfx_play_pitched(SND_PUNCH_HIT, ex, move == PUNCH_MOVE_HOOK ? 880 : 0);
    if (g_hitstop_frames < PUNCH_HITSTOP_V) g_hitstop_frames = PUNCH_HITSTOP_V;
    weapons_request_shake(1, PUNCH_SHAKE_V + (move == PUNCH_MOVE_HOOK ? 2 : 0));
}

int punch_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int move, int soft_lock) {
    if (s_punch_active || g_player_state.is_dead || move < 0 || move >= PUNCH_NUM_MOVES) return 0;
    const int face = hero_dir & 7;
    int ex = 0, ey = 0;
    const int idx = punch_target(enemies, max_enemies, hero_x, hero_y, face, !soft_lock, &ex, &ey);
    int dir = face;
    if (soft_lock && idx >= 0) {
        const int dx = ex - TO_INT(hero_x), dy = ey - TO_INT(hero_y);
        dir = dx * dx + GROUND_DY2(dy) < 16 ? face : enemy_dir_from_vector(TO_FIXED(dx), TO_FIXED(dy));
    }
    if (!punch_load_bin(move, dir)) return 0;
    s_punch_move = move;
    s_punch_dir = dir;
    s_punch_frame = PUNCH_START_V(move);          // salta la guardia quieta del principio del clip
    if (s_punch_frame > PUNCH_IMPACT_V(move)) s_punch_frame = PUNCH_IMPACT_V(move);
    if (s_punch_frame < 0) s_punch_frame = 0;
    s_punch_t = 0;
    s_punch_chain = 0;
    s_punch_target = idx;
    s_punch_cone = !soft_lock;
    s_punch_applied = 0;
    s_punch_active = 1;
    // Al arrancar solo suena el silbido: dano, sonido de golpe, paron y temblor llegan con el brazo
    // estirado (punch_impact_step, fotograma de impacto), no con el brazo aun recogido.
    sfx_play_pitched(SND_PUNCH_WHOOSH, TO_INT(hero_x), move == PUNCH_MOVE_HOOK ? 850 : 0);
    return 1;
}

// Fotograma de impacto: el brazo esta estirado. Se revalida el objetivo con la posicion actual del heroe
// (puede haber muerto, haberse ido o haber quedado fuera del alcance/cono); si no vale se busca otro y, si
// no hay ninguno, el golpe pasa al aire (solo el silbido). Una sola vez por golpe. El paron que pone
// punch_apply congela la simulacion entera (main.c), asi que la animacion se queda en este fotograma.
static void punch_impact_step(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y) {
    if (s_punch_applied || s_punch_frame < PUNCH_IMPACT_V(s_punch_move)) return;
    s_punch_applied = 1;
    const int hx = TO_INT(hero_x), hy = TO_INT(hero_y);
    int d2, idx = s_punch_target;
    if (idx < 0 || idx >= max_enemies || !punch_can_hit(&enemies[idx], idx, hx, hy, s_punch_dir, s_punch_cone, &d2)) {
        int ex, ey;
        idx = punch_target(enemies, max_enemies, hero_x, hero_y, s_punch_dir, s_punch_cone, &ex, &ey);
    }
    s_punch_target = -1;
    punch_apply(enemies, idx, hero_x, hero_y, s_punch_move);
}

// Cobra el golpe guardado (s_punch_queued): cierra el golpe en curso, que ya ha ensenado su impacto o ya
// termino, y saca el siguiente. Si no puede arrancar, el golpe anterior sigue su animacion.
static void punch_fire_queue(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int soft_lock) {
    s_punch_queued--;                       // se cobra uno; si queda otro, saldra tras el impacto de este
    const int was_active = s_punch_active;
    const int next = (s_punch_move >= PUNCH_MOVE_HOOK) ? PUNCH_MOVE_A : s_punch_move + 1;
    s_punch_active = 0;                     // punch_start rechaza un golpe en curso: cerrar el anterior
    if (!punch_start(enemies, max_enemies, hero_x, hero_y, hero_dir, next, soft_lock)) s_punch_active = was_active;
}

int punch_try_chain(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int soft_lock) {
    if (g_player_state.is_dead) return 0;
    int next;
    if (s_punch_active) {
        if (s_punch_move >= PUNCH_MOVE_HOOK) return 0;        // el gancho cierra el combo
        // Se guarda y se cobra en punch_update, sin cortar el golpe en curso. Caben tantos como golpes
        // le quedan al combo tras el actual (maximo 2): un tercer toque rapido no se funde con el segundo.
        const int room = PUNCH_MOVE_HOOK - s_punch_move;
        if (s_punch_queued < room) s_punch_queued++;
        return 1;
    } else if (s_punch_chain > 0) {
        next = (s_punch_move >= PUNCH_MOVE_HOOK) ? PUNCH_MOVE_A : s_punch_move + 1;
    } else {
        return 0;
    }
    return punch_start(enemies, max_enemies, hero_x, hero_y, hero_dir, next, soft_lock);
}

void punch_update(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir, int soft_lock) {
    if (!s_punch_active) {
        if (s_punch_chain > 0) s_punch_chain--;
        // Un L guardado mientras el golpe cerraba: arranca de inmediato.
        if (s_punch_queued > 0) punch_fire_queue(enemies, max_enemies, hero_x, hero_y, hero_dir, soft_lock);
        return;
    }
    if (++s_punch_t >= PUNCH_TICKS_V) {
        s_punch_t = 0;
        if (++s_punch_frame >= PUNCH_NUM_FRAMES) {
            s_punch_active = 0;
            s_punch_frame = PUNCH_NUM_FRAMES - 1;
            s_punch_chain = s_punch_move < PUNCH_MOVE_HOOK ? PUNCH_CHAIN_FRAMES_V : 0;
        }
    }
    if (s_punch_active) punch_impact_step(enemies, max_enemies, hero_x, hero_y);
    // El golpe guardado no corta la animacion en seco: se cobra cuando el golpe en curso ya ha ensenado su
    // impacto (la extension del brazo) y ademas PUNCH_FOLLOW_V fotogramas de seguimiento enteros, o en
    // cuanto la animacion termina. Asi el primer golpe del combo se ve siempre hasta el impacto.
    if (s_punch_queued > 0 && (!s_punch_active || s_punch_frame > PUNCH_IMPACT_V(s_punch_move) + PUNCH_FOLLOW_V))
        punch_fire_queue(enemies, max_enemies, hero_x, hero_y, hero_dir, soft_lock);
}
