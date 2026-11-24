#include "sound_test.h"

#if SOUND_TEST

#include <string.h>
#include "collision.h"
#include "chars_pool.h"
#include "campanero_fx.h"
#include "dmg_numbers.h"
#include "sfx.h"

// Variante "prueba-sonidos": una escena por situacion de sonido. El heroe es invulnerable (lab_tuning.c) y los enemigos de las
// escenas llevan pack -1 (ni el despertar de encounters ni enc_untouchable() los tocan), como en remate_test.c.

int g_snd_scene = 0;

const char *const g_snd_scene_names[SND_SCENE_COUNT] = {
    "0 Mapa normal", "1 Remates", "2 Hechizos", "3 Ojos", "4 Cireneos", "5 Monja cura", "6 Monaguillos", "7 Campanero",
};

const char *const g_snd_scene_sounds[SND_SCENE_COUNT] = {
    "Puños, remate, Rayo, Glifo, golpes y muertes, orbes, cofres, puertas, subir nivel, clic y engarce del inventario.",
    "Puño aire, puño impacto, aviso de tambaleo, remate, muerte enemigo, orbe recogido.",
    "Rayo (carga y disparo), golpe enemigo, muerte enemigo, Glifo (grieta y detonación).",
    "Ojo carga, Ojo disparo, héroe herido, golpe enemigo.",
    "Cireneo carga, Cireneo muro, héroe herido, golpe enemigo.",
    "Monja cura (y los números verdes de curación).",
    "Monaguillo surge, golpe enemigo, muerte enemigo, héroe herido.",
    "Tañido (menor), toque (golpe y zumbido) y cristal del glifo apagado.",
};

const char *const g_snd_scene_todo[SND_SCENE_COUNT] = {
    "Juega normal. Para el mapa completo con todas las salas, reinicia la ROM: si vuelves aquí desde otra escena, las salas ya vistas quedan vacías.",
    "Pega con L a uno de la fila: queda tambaleando. Pulsa L otra vez para rematarlo y recoge el orbe. Reaparecen a los 2 s.",
    "Toca con el lápiz para lanzar el Rayo (mantén para cargar). Para el Glifo: mantén L, toca el Glifo del radial y toca el suelo junto a ellos.",
    "Quédate a tiro y espera: apuntan y disparan. Eres invulnerable pero el herido suena. Pega a uno con L para oír golpe y muerte.",
    "Espera a que embistan. Ponte con un muro justo detrás de ti para oír el choque contra el muro. Pega con L para golpe y muerte.",
    "No hay nada que hacer: cada 2 s la Monja cura a los Exvotos heridos (simulado: la oración real está desactivada en el juego).",
    "Cada 3 s surge uno del suelo (máx. 4). Pégales con L para oír golpe y muerte; te muerden pero eres invulnerable.",
    "La campana queda 70 px al norte: tañido cada 2 s y toque cada 7 s. Lanza un Glifo dentro del anillo para oír el cristal.",
};

#define ST_MAX_UNITS 8
#define ST_DELAY_FRAMES 120         // ~2 s tras caer antes de reaparecer en su sitio
#define ST_PACK (-1)
#define ST_MAX_HP 400
#define ST_HP_TOTTER 101            // un puñetazo (1..100) lo deja en <= 25 %: tambalea sin morir
#define ST_HP_HURT 150              // Monja cura: herido, a mitad de vida
#define ST_HEAL_PERIOD 120
#define ST_MONA_PERIOD 180
#define ST_MONA_CAP 4

typedef struct {
    uint8_t type;
    int16_t dx, dy;                 // respecto al heroe (norte = y negativo)
    int16_t hp;                     // 0 = vida completa del tipo
} Unit;

typedef struct {
    uint8_t n;
    uint8_t frozen;                 // la IA no mueve ni ataca (solo se tambalean al recibir golpes)
    uint32_t groups;                // bit por CG_* del arte que carga la escena
    Unit u[ST_MAX_UNITS];
} Scene;

#define G(x) (1u << (x))
// Sin las aranas: con ellas el pozo de arte se llena y la Super Monja (CG_SMONJA) no llega a cargarse (no se ve). Nadie cae en su aura de posesion.
#define ART_FAMILY (G(CG_OJO) | G(CG_CHARGER) | G(CG_EXVOTO) | G(CG_MONAGUILLO) | G(CG_PARROCO) | G(CG_SMONJA))

static const Scene s_scene[SND_SCENE_COUNT] = {
    [0] = { 0, 0, 0, { { 0 } } },
    [1] = { 7, 1, ART_FAMILY, {
        { ENEMY_TYPE_EXVOTO, -80, -60, ST_HP_TOTTER }, { ENEMY_TYPE_MONAGUILLO, -40, -60, ST_HP_TOTTER },
        { ENEMY_TYPE_BEBE, 0, -60, ST_HP_TOTTER }, { ENEMY_TYPE_PARROCO, 40, -60, ST_HP_TOTTER },
        { ENEMY_TYPE_MONJA, 80, -60, ST_HP_TOTTER },
        { ENEMY_TYPE_SHOOTER, -40, -100, ST_HP_TOTTER }, { ENEMY_TYPE_CHARGER, 40, -100, ST_HP_TOTTER } } },
    [2] = { 5, 1, G(CG_EXVOTO) | G(CG_PARROCO), {
        { ENEMY_TYPE_EXVOTO, -96, -70, ST_MAX_HP }, { ENEMY_TYPE_PARROCO, -48, -70, ST_MAX_HP },
        { ENEMY_TYPE_EXVOTO, 0, -70, ST_MAX_HP }, { ENEMY_TYPE_PARROCO, 48, -70, ST_MAX_HP },
        { ENEMY_TYPE_EXVOTO, 96, -70, ST_MAX_HP } } },
    [3] = { 2, 0, G(CG_OJO), {
        { ENEMY_TYPE_SHOOTER, -70, -80, 0 }, { ENEMY_TYPE_SHOOTER, 70, -80, 0 } } },
    [4] = { 2, 0, G(CG_CHARGER), {
        { ENEMY_TYPE_CHARGER, -60, -90, 0 }, { ENEMY_TYPE_CHARGER, 60, -90, 0 } } },
    // Monja (unidad 0) y tres Exvotos heridos a su alrededor; la curacion la hace este modulo (ver sound_test_update).
    [5] = { 4, 1, G(CG_EXVOTO) | G(CG_SMONJA) | G(CG_ARANA_EXVOTO), {
        { ENEMY_TYPE_MONJA, 0, -100, ST_MAX_HP }, { ENEMY_TYPE_EXVOTO, -50, -70, ST_HP_HURT },
        { ENEMY_TYPE_EXVOTO, 50, -70, ST_HP_HURT }, { ENEMY_TYPE_EXVOTO, 0, -55, ST_HP_HURT } } },
    [6] = { 0, 0, G(CG_MONAGUILLO), { { 0 } } },
    [7] = { 0, 0, 0, { { 0 } } },
};

static int s_applied;                  // escena montada
static int s_ready;                    // posiciones fijadas
static int16_t s_pos[ST_MAX_UNITS][2];
static int s_slot[ST_MAX_UNITS];
static int s_dead[ST_MAX_UNITS];
static int s_t;                        // frames desde que se monto la escena
static int s_mona_next;
static int16_t s_bell[2];

void sound_test_reset(void) {
    s_applied = 0;
    s_ready = 0;
    s_t = 0;
    for (int k = 0; k < ST_MAX_UNITS; k++) { s_slot[k] = -1; s_dead[k] = 0; }
}

void sound_test_shift_y(int dy_px) {
    for (int k = 0; k < ST_MAX_UNITS; k++) s_pos[k][1] = (int16_t)(s_pos[k][1] + dy_px);
    s_bell[1] = (int16_t)(s_bell[1] + dy_px);
}

int sound_test_freeze(void) { return s_applied > 0 && s_scene[s_applied].frozen; }

int sound_test_rooms_empty(void) { return g_snd_scene > 0 || s_applied > 0; }

// A free spot at the wanted offset, else pulled back towards the hero.
static void free_spot(int hx, int hy, int dx, int dy, int16_t *out) {
    int x = hx + dx, y = hy + dy;
    for (int t = 0; t < 6 && !position_is_free(TO_FIXED(x), TO_FIXED(y)); t++) {
        x = hx + dx * (5 - t) / 6;
        y = hy + dy * (5 - t) / 6;
    }
    out[0] = (int16_t)x;
    out[1] = (int16_t)y;
}

// Same fields as place_enemy() of encounters_act1.c: awake (CHASE); the Ojo also keeps its post (leash) where it stands.
static void place(Enemy *e, const Unit *u, int x, int y, int ordinal) {
    const EnemyType type = (EnemyType)u->type;
    memset(e, 0, sizeof(*e));
    e->x = TO_FIXED(x);
    e->y = TO_FIXED(y);
    e->active = 1;
    e->type = type;
    e->pack = ST_PACK;
    e->char_id = enemy_type_char_id(type);
    e->max_hp = u->hp > ST_HP_TOTTER ? ST_MAX_HP : (u->hp ? ST_MAX_HP : g_enemy_tuning[type].max_hp);
    e->hp = u->hp ? u->hp : e->max_hp;
    e->dir = (ordinal * 2) % 8;
    e->strafe_dir = (ordinal & 1) ? 1 : -1;
    e->state = ENEMY_STATE_CHASE;
    if (type == ENEMY_TYPE_SHOOTER) {
        e->home_flags = ENEMY_HOME_SET;
        *enemy_home_x(e) = x;
        *enemy_home_y(e) = y;
    }
}

static int free_slot(Enemy *enemies, int max_enemies) {
    for (int j = 0; j < max_enemies; j++)
        if (!enemies[j].active) return j;
    return -1;
}

static void apply_scene(Enemy *enemies, int max_enemies, int hx, int hy) {
    const Scene *sc = &s_scene[g_snd_scene];
    for (int j = 0; j < max_enemies; j++) enemies[j].active = 0;
    cfx_reset();
    if (g_snd_scene > 0) room_art_prepare(sc->groups, 0);   // a load hitch is fine in a test ROM
    s_applied = g_snd_scene;
    s_t = 0;
    s_mona_next = 0;
    for (int k = 0; k < ST_MAX_UNITS; k++) {
        s_slot[k] = -1;
        s_dead[k] = ST_DELAY_FRAMES;       // aparecen ya
        if (k < sc->n) free_spot(hx, hy, sc->u[k].dx, sc->u[k].dy, s_pos[k]);
    }
    free_spot(hx, hy, 0, -70, s_bell);     // la campana de la escena 7: fija desde que se entra
    s_ready = 1;
}

static int unit_alive(const Enemy *enemies, int k, const Scene *sc) {
    const int i = s_slot[k];
    return i >= 0 && enemies[i].active && enemies[i].hp > 0 && enemies[i].pack == ST_PACK && enemies[i].type == sc->u[k].type;
}

void sound_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y) {
    if (!s_ready || g_snd_scene != s_applied) apply_scene(enemies, max_enemies, hero_x, hero_y);
    if (s_applied == 0) return;
    const Scene *sc = &s_scene[s_applied];
    s_t++;

    for (int k = 0; k < sc->n; k++) {
        if (unit_alive(enemies, k, sc)) { s_dead[k] = 0; continue; }
        s_slot[k] = -1;
        if (s_dead[k] < ST_DELAY_FRAMES) { s_dead[k]++; continue; }
        const int j = free_slot(enemies, max_enemies);
        if (j < 0) continue;
        place(&enemies[j], &sc->u[k], s_pos[k][0], s_pos[k][1], k);
        s_slot[k] = j;
        s_dead[k] = 0;
    }

    if (s_applied == 4) {
        // A normal charge ends after ~170 px, short of any wall unless the hero stands right against it: here it
        // runs on until something stops it, so SND_CIRENEO_WALL is heard wherever the player stands.
        for (int k = 0; k < sc->n; k++)
            if (unit_alive(enemies, k, sc) && enemies[s_slot[k]].state == ENEMY_STATE_CHARGE) enemies[s_slot[k]].state_timer = 99;
    }

    if (s_applied == 5 && s_t % ST_HEAL_PERIOD == 0 && unit_alive(enemies, 0, sc)) {
        // Prayer of the Monja, simulated: the real one is off in the game (ARPG_MONJA_PRAYS 0), so SND_MONJA_HEAL never plays there.
        int hurt = 0;
        for (int k = 1; k < sc->n; k++) {
            if (!unit_alive(enemies, k, sc)) continue;
            Enemy *o = &enemies[s_slot[k]];
            if (o->hp >= o->max_hp) continue;
            int heal = o->max_hp * 25 / 100;
            o->hp += heal;
            if (o->hp > o->max_hp) o->hp = o->max_hp;
            dmg_numbers_spawn(o->x, o->y - TO_FIXED(16), heal, DMG_NUM_HEAL);
            hurt = 1;
        }
        if (hurt) sfx_play(SND_MONJA_HEAL, s_pos[0][0]);
        else for (int k = 1; k < sc->n; k++)                 // all healed: hurt them again for the next round
            if (unit_alive(enemies, k, sc)) enemies[s_slot[k]].hp = ST_HP_HURT;
    }

    if (s_applied == 6 && s_t % ST_MONA_PERIOD == 60) {
        static const int16_t ring[6][2] = { {-80, -30}, {80, -30}, {-60, 50}, {60, 50}, {0, -70}, {0, 70} };
        int live = 0;
        for (int j = 0; j < max_enemies; j++)
            if (enemies[j].active && enemies[j].hp > 0 && enemies[j].type == ENEMY_TYPE_MONAGUILLO) live++;
        const int j = live < ST_MONA_CAP ? free_slot(enemies, max_enemies) : -1;
        if (j >= 0) {
            for (int t = 0; t < 6; t++) {
                const int r = (s_mona_next + t) % 6;
                const int x = hero_x + ring[r][0], y = hero_y + ring[r][1];
                if (!position_is_free(TO_FIXED(x), TO_FIXED(y))) continue;
                Enemy *e = &enemies[j];
                memset(e, 0, sizeof(*e));
                e->x = TO_FIXED(x);
                e->y = TO_FIXED(y);
                e->type = ENEMY_TYPE_MONAGUILLO;
                e->char_id = CHAR_MONAGUILLO;
                e->hp = g_enemy_tuning[ENEMY_TYPE_MONAGUILLO].max_hp;
                e->max_hp = e->hp;
                e->dir = DIR_SOUTH;
                e->active = 1;
                e->state = ENEMY_STATE_EMERGE;
                e->state_timer = MONAGUILLO_EMERGE_FRAMES;
                e->strafe_dir = (r & 1) ? 1 : -1;
                e->pack = ST_PACK;
                sfx_play(SND_MONAGUILLO_EMERGE, x);
                s_mona_next = r + 1;
                break;
            }
        }
    }

    if (s_applied == 7) {
        if (s_t % 120 == 60) cfx_emit(CFX_TANIDO, s_bell[0], s_bell[1]);
        if (s_t % 420 == 200) cfx_emit(CFX_TOQUE, s_bell[0], s_bell[1]);
    }
}

#else
typedef int sound_test_disabled_translation_unit;
#endif
