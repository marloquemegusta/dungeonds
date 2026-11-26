#include "lab_tuning.h"

#if ARPG_LAB

#include <nds.h>
#include <stdio.h>
#include <string.h>
#include "game.h"
#include "bestiary_font.h"
#include "punch.h"
#include "boxeo.h"
#if SOUND_TEST
#include "sound_test.h"
#endif

int g_lab_sfx_var[SND_COUNT];
int g_lab_god = (ARPG_BOXEO && !ARPG_BOXEO_MELEE && !ARPG_BOXEO_DUELO) || SOUND_TEST;       /* boxeo / sound test: the hero starts invulnerable */
int g_lab_punch_ticks = PUNCH_TICKS;
int g_lab_punch_chain = PUNCH_CHAIN_FRAMES;
int g_lab_punch_walk_pct = PUNCH_WALK_SPEED_PCT;
int g_lab_punch_range = PUNCH_RANGE;
int g_lab_punch_impact[3] = { PUNCH_IMPACT_A, PUNCH_IMPACT_B, PUNCH_IMPACT_HOOK };
int g_lab_punch_follow = PUNCH_FOLLOW;
int g_lab_punch_split = PUNCH_WALK_SPLIT;
int g_lab_punch_start[3] = { PUNCH_START_A, PUNCH_START_B, PUNCH_START_HOOK };
int g_lab_punch_light_push = PUNCH_LIGHT_PUSH;
int g_lab_punch_hook_push = PUNCH_HOOK_PUSH;
int g_lab_punch_hitstop = PUNCH_HITSTOP_FRAMES;
int g_lab_punch_shake = PUNCH_SHAKE_LIGHT;
#if ARPG_BOXEO
int g_lab_saco_still = !ARPG_BOXEO_MELEE && !ARPG_BOXEO_DUELO;
int g_lab_saco_type = 0;
#endif

static const char *const s_variant_labels[LABV_COUNT] = {
#define X(n, label, mm) [LABV_##n] = label,
    LAB_VARIANTS(X)
#undef X
};

/* Candidates of each event, in menu order (variant k of the event is v[k-1]; variant 0 is always the original). */
typedef struct { uint8_t n; int8_t v[4]; } EventVariants;
static const EventVariants s_ev[SND_COUNT] = {
    [SND_PUNCH_WHOOSH]      = { 3, { LABV_CLOTH1, LABV_CLOTH4, LABV_KNIFE } },
    [SND_PUNCH_HIT]         = { 4, { LABV_PUNCH_M0, LABV_PUNCH_M2, LABV_PUNCH_H0, LABV_PUNCH_H3 } },
    [SND_CIRENEO_WALL]      = { 3, { LABV_WOOD_HEAVY, LABV_MINING0, LABV_GENERIC_LIGHT } },
    [SND_BOSS_PHASE]        = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_WOBBLE_CUE]        = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
#if SOUND_TEST
#else
    [SND_MONAGUILLO_EMERGE] = { 2, { LABV_MINING2, LABV_STEP_STONE } },
    [SND_PICKUP_ORB]        = { 3, { LABV_GLASS1, LABV_GLASS4, LABV_CONFIRM1 } },
#endif
    [SND_CHEST_OPEN]        = { 3, { LABV_CREAK, LABV_LATCH, LABV_DOOR_OPEN1 } },
    [SND_DOOR_OPEN]         = { 2, { LABV_DOOR_OPEN2, LABV_DOOR_CLOSE } },
    [SND_UI_CLICK]          = { 3, { LABV_CLICK, LABV_SELECT, LABV_TICK } },
    [SND_RELIC_SOCKET]      = { 3, { LABV_DROP, LABV_METAL_CLICK, LABV_PLATE } },
    [SND_LEVEL_UP]          = { 2, { LABV_CONFIRM2, LABV_MAXIMIZE } },
#if SOUND_TEST
    [SND_CFX_TANIDO]        = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_CFX_BONG]          = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_CFX_BELL_LOW]      = { 3, { LABV_BELL_H0, LABV_BELL_H2, LABV_BONG } },
    [SND_CFX_GLASS_A]       = { 3, { LABV_GLASS1, LABV_GLASS4, LABV_CONFIRM1 } },
    [SND_CFX_GLASS_B]       = { 3, { LABV_GLASS1, LABV_GLASS4, LABV_CONFIRM1 } },
#endif
};

int lab_sfx_candidate(int ev) {
    if (ev < 0 || ev >= SND_COUNT) return -1;
    int k = g_lab_sfx_var[ev];
    if (k <= 0 || k > s_ev[ev].n) return -1;
    return s_ev[ev].v[k - 1];
}

#define SFXROW(page, label, id) { page, label, &g_lab_sfx_var[id], 0, 0, 1, LAB_KIND_SFX_VARIANT }

#if SOUND_TEST
#define PG_ESC "Escenas"
#define PG_HERO "Sonidos: Héroe"
#define PG_ENE "Sonidos: Enemigos"
#define PG_BOSS "Sonidos: Campanero y jefes"
#define PG_WORLD "Sonidos: Mundo y menús"
#define PG_FREE "Banco gratuito (Kenney)"

static int s_cand_dummy;

/* Exact file name (assets/sfx/baked, no extension) each event plays when its row is on "Original". lab_* = free bank
 * (Kenney CC0), the rest are generated (ElevenLabs). Keep in step with s_mm_ids in sfx.c. */
static const char *const s_snd_file[SND_COUNT] = {
    [SND_HEART_CHARGE] = "heart_charge", [SND_HEART_FIRE] = "heart_fire", [SND_ENEMY_HIT] = "enemy_hit",
    [SND_ENEMY_DEATH] = "enemy_death", [SND_PLAYER_HURT] = "player_hurt",
    [SND_ABANDERADO_INTRO] = "abanderado_intro", [SND_ABANDERADO_DEFEAT] = "abanderado_derrota",
    [SND_PUNCH_WHOOSH] = "punch_whoosh", [SND_PUNCH_HIT] = "punch_hit", [SND_REMATE_CERA] = "remate_cera", [SND_REMATE_VIGA] = "remate_viga", [SND_REMATE_OJO] = "remate_ojo", [SND_REMATE_DERRETIR] = "remate_derretir", [SND_REMATE_TIRON] = "remate_tiron", [SND_REMATE_CAIDA] = "remate_caida", [SND_REMATE_FORCEJEO] = "remate_forcejeo", [SND_REMATE_MANO] = "remate_mano",
    [SND_WOBBLE_CUE] = "wobble_cue", [SND_GLIFO_CRACK] = "glifo_grieta", [SND_GLIFO_DETONATE] = "glifo_detonacion", [SND_CFX_LIFT] = "lab_creak",
    [SND_OJO_CHARGE] = "ojo_charge", [SND_OJO_FIRE] = "ojo_fire", [SND_CIRENEO_CHARGE] = "cireneo_charge",
    [SND_CIRENEO_WALL] = "cireneo_wall", [SND_MONJA_HEAL] = "monja_heal", [SND_MONAGUILLO_EMERGE] = "monaguillo_emerge",
    [SND_BOSS_PHASE] = "boss_phase", [SND_PICKUP_ORB] = "pickup_orb", [SND_CHEST_OPEN] = "chest_open",
    [SND_DOOR_OPEN] = "door_open", [SND_UI_CLICK] = "ui_click", [SND_RELIC_SOCKET] = "relic_socket",
    [SND_LEVEL_UP] = "level_up", [SND_CFX_TANIDO] = "lab_bell_h2", [SND_CFX_BONG] = "lab_bong",
    [SND_CFX_BELL_LOW] = "lab_bell_h0", [SND_CFX_GLASS_A] = "lab_glass1", [SND_CFX_GLASS_B] = "lab_glass4",
    [SND_CAMPANERO_INTRO] = "campanero_intro", [SND_CAMPANERO_DEFEAT] = "campanero_derrota",
};

static const char *const s_labv_file[LABV_COUNT] = {
    [LABV_CLOTH1] = "lab_cloth1", [LABV_CLOTH4] = "lab_cloth4", [LABV_KNIFE] = "lab_knife",
    [LABV_PUNCH_M0] = "lab_punch_m0", [LABV_PUNCH_M2] = "lab_punch_m2", [LABV_PUNCH_H0] = "lab_punch_h0",
    [LABV_PUNCH_H3] = "lab_punch_h3", [LABV_WOOD_HEAVY] = "lab_wood_heavy", [LABV_MINING0] = "lab_mining0",
    [LABV_GENERIC_LIGHT] = "lab_generic_light", [LABV_BELL_H0] = "lab_bell_h0", [LABV_BELL_H2] = "lab_bell_h2",
    [LABV_BONG] = "lab_bong", [LABV_MINING2] = "lab_mining2", [LABV_STEP_STONE] = "lab_step_stone",
    [LABV_GLASS1] = "lab_glass1", [LABV_GLASS4] = "lab_glass4", [LABV_CONFIRM1] = "lab_confirm1",
    [LABV_CREAK] = "lab_creak", [LABV_LATCH] = "lab_latch", [LABV_DOOR_OPEN1] = "lab_door_open1",
    [LABV_DOOR_OPEN2] = "lab_door_open2", [LABV_DOOR_CLOSE] = "lab_door_close", [LABV_CLICK] = "lab_click",
    [LABV_SELECT] = "lab_select", [LABV_TICK] = "lab_tick", [LABV_DROP] = "lab_drop",
    [LABV_METAL_CLICK] = "lab_metal_click", [LABV_PLATE] = "lab_plate", [LABV_CONFIRM2] = "lab_confirm2",
    [LABV_MAXIMIZE] = "lab_maximize",
#if SOUND_TEST
#endif
};

#define CANDROW(n, label, mm) { PG_FREE, "", &s_cand_dummy, LABV_##n, 0, 1, LAB_KIND_CANDIDATE },
#else
#define PG_A "Sonidos: combate"
#define PG_B "Sonidos: mundo y menús"
#define PG_C "Sonidos: sin variantes"
#endif

/* THE TABLE: add a line to register a tunable (see lab_tuning.h). Events with candidates come first. */
static const LabEntry s_entries[] = {
#if SOUND_TEST
    { PG_ESC, "Escena", &g_snd_scene, 0, SND_SCENE_COUNT - 1, 1, LAB_KIND_INT, g_snd_scene_names },
    { PG_ESC, "Invulnerable", &g_lab_god, 0, 1, 1, LAB_KIND_INT },

    SFXROW(PG_HERO, "Puño aire", SND_PUNCH_WHOOSH),
    SFXROW(PG_HERO, "Puño impacto", SND_PUNCH_HIT),
    SFXROW(PG_HERO, "Aviso tambaleo", SND_WOBBLE_CUE),
    SFXROW(PG_HERO, "Exvoto/Mon./Bebé: cera", SND_REMATE_CERA),
    SFXROW(PG_HERO, "S.Monja: tirón", SND_REMATE_TIRON),
    SFXROW(PG_HERO, "S.Monja: caída", SND_REMATE_CAIDA),
    SFXROW(PG_HERO, "Cireneo: viga", SND_REMATE_VIGA),
    SFXROW(PG_HERO, "Ojo: forcejeo", SND_REMATE_FORCEJEO),
    SFXROW(PG_HERO, "Ojo: vuelco", SND_REMATE_OJO),
    SFXROW(PG_HERO, "Párroco: mano", SND_REMATE_MANO),
    SFXROW(PG_HERO, "Párroco: derrite", SND_REMATE_DERRETIR),
    SFXROW(PG_HERO, "Rayo carga", SND_HEART_CHARGE),
    SFXROW(PG_HERO, "Rayo disparo", SND_HEART_FIRE),
    SFXROW(PG_HERO, "Glifo grieta", SND_GLIFO_CRACK),
    SFXROW(PG_HERO, "Glifo detonación", SND_GLIFO_DETONATE),
    SFXROW(PG_HERO, "Héroe herido", SND_PLAYER_HURT),

    SFXROW(PG_ENE, "Golpe enemigo", SND_ENEMY_HIT),
    SFXROW(PG_ENE, "Muerte enemigo", SND_ENEMY_DEATH),
    SFXROW(PG_ENE, "Ojo carga", SND_OJO_CHARGE),
    SFXROW(PG_ENE, "Ojo disparo", SND_OJO_FIRE),
    SFXROW(PG_ENE, "Cireneo carga", SND_CIRENEO_CHARGE),
    SFXROW(PG_ENE, "Cireneo muro", SND_CIRENEO_WALL),
    SFXROW(PG_ENE, "Monja cura", SND_MONJA_HEAL),
    SFXROW(PG_ENE, "Monaguillo surge", SND_MONAGUILLO_EMERGE),

    SFXROW(PG_BOSS, "Tañido (menor)", SND_CFX_TANIDO),
    SFXROW(PG_BOSS, "Toque: golpe", SND_CFX_BONG),
    SFXROW(PG_BOSS, "Toque: zumbido", SND_CFX_BELL_LOW),
    SFXROW(PG_BOSS, "Cristal glifo A", SND_CFX_GLASS_A),
    SFXROW(PG_BOSS, "Cristal glifo B", SND_CFX_GLASS_B),
    SFXROW(PG_BOSS, "Fase jefe", SND_BOSS_PHASE),
    SFXROW(PG_BOSS, "Abanderado intro", SND_ABANDERADO_INTRO),
    SFXROW(PG_BOSS, "Abanderado fin", SND_ABANDERADO_DEFEAT),
    SFXROW(PG_BOSS, "Campanero intro", SND_CAMPANERO_INTRO),
    SFXROW(PG_BOSS, "Campanero fin", SND_CAMPANERO_DEFEAT),

    SFXROW(PG_WORLD, "Orbe recogido", SND_PICKUP_ORB),
    SFXROW(PG_WORLD, "Abrir cofre", SND_CHEST_OPEN),
    SFXROW(PG_WORLD, "Abrir puerta", SND_DOOR_OPEN),
    SFXROW(PG_WORLD, "Clic menú", SND_UI_CLICK),
    SFXROW(PG_WORLD, "Engarce reliquia", SND_RELIC_SOCKET),
    SFXROW(PG_WORLD, "Subir nivel", SND_LEVEL_UP),

    LAB_VARIANTS(CANDROW)
#else
    SFXROW(PG_A, "Puño aire", SND_PUNCH_WHOOSH),
    SFXROW(PG_A, "Puño impacto", SND_PUNCH_HIT),
    SFXROW(PG_A, "Cireneo muro", SND_CIRENEO_WALL),
    SFXROW(PG_A, "Aviso tambaleo", SND_WOBBLE_CUE),
    SFXROW(PG_A, "Fase jefe", SND_BOSS_PHASE),
    SFXROW(PG_A, "Monaguillo surge", SND_MONAGUILLO_EMERGE),

    SFXROW(PG_B, "Orbe recogido", SND_PICKUP_ORB),
    SFXROW(PG_B, "Abrir cofre", SND_CHEST_OPEN),
    SFXROW(PG_B, "Abrir puerta", SND_DOOR_OPEN),
    SFXROW(PG_B, "Clic menú", SND_UI_CLICK),
    SFXROW(PG_B, "Engarce reliquia", SND_RELIC_SOCKET),
    SFXROW(PG_B, "Subir nivel", SND_LEVEL_UP),

    SFXROW(PG_C, "Hechizo disparo", SND_HEART_FIRE),
    SFXROW(PG_C, "Hechizo carga", SND_HEART_CHARGE),
    SFXROW(PG_C, "Golpe enemigo", SND_ENEMY_HIT),
    SFXROW(PG_C, "Muerte enemigo", SND_ENEMY_DEATH),
    SFXROW(PG_C, "Héroe herido", SND_PLAYER_HURT),
    SFXROW(PG_C, "Exvoto/Mon./Bebé: cera", SND_REMATE_CERA),
    SFXROW(PG_C, "S.Monja: tirón", SND_REMATE_TIRON),
    SFXROW(PG_C, "S.Monja: caída", SND_REMATE_CAIDA),
    SFXROW(PG_C, "Cireneo: viga", SND_REMATE_VIGA),
    SFXROW(PG_C, "Ojo: forcejeo", SND_REMATE_FORCEJEO),
    SFXROW(PG_C, "Ojo: vuelco", SND_REMATE_OJO),
    SFXROW(PG_C, "Párroco: mano", SND_REMATE_MANO),
    SFXROW(PG_C, "Párroco: derrite", SND_REMATE_DERRETIR),
    SFXROW(PG_C, "Glifo grieta", SND_GLIFO_CRACK),
    SFXROW(PG_C, "Glifo detonación", SND_GLIFO_DETONATE),
    SFXROW(PG_C, "Ojo carga", SND_OJO_CHARGE),
    SFXROW(PG_C, "Ojo disparo", SND_OJO_FIRE),
    SFXROW(PG_C, "Cireneo carga", SND_CIRENEO_CHARGE),
    SFXROW(PG_C, "Monja cura", SND_MONJA_HEAL),
    SFXROW(PG_C, "Abanderado voz", SND_ABANDERADO_INTRO),
    SFXROW(PG_C, "Abanderado fin", SND_ABANDERADO_DEFEAT),

    { "Puñetazo", "Velocidad (frames/foto)", &g_lab_punch_ticks, 1, 6, 1, LAB_KIND_INT },
    { "Puñetazo", "Ventana combo", &g_lab_punch_chain, 0, 40, 2, LAB_KIND_INT },
    { "Puñetazo", "Andar pegando %", &g_lab_punch_walk_pct, 0, 100, 5, LAB_KIND_INT },
    { "Puñetazo", "Impacto directo", &g_lab_punch_impact[0], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Impacto cruzado", &g_lab_punch_impact[1], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Impacto gancho", &g_lab_punch_impact[2], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Inicio directo", &g_lab_punch_start[0], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Inicio cruzado", &g_lab_punch_start[1], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Inicio gancho", &g_lab_punch_start[2], 0, 7, 1, LAB_KIND_INT },
    { "Puñetazo", "Corte cintura", &g_lab_punch_split, 4, 24, 1, LAB_KIND_INT },
    { "Puñetazo", "Seguimiento (fotos)", &g_lab_punch_follow, 0, 3, 1, LAB_KIND_INT },
    { "Puñetazo", "Empuje ligero", &g_lab_punch_light_push, 0, 512, 16, LAB_KIND_INT },
    { "Puñetazo", "Empuje gancho", &g_lab_punch_hook_push, 0, 512, 16, LAB_KIND_INT },
    { "Puñetazo", "Parón al golpear", &g_lab_punch_hitstop, 0, 10, 1, LAB_KIND_INT },
    { "Puñetazo", "Temblor (gancho +2)", &g_lab_punch_shake, 0, 8, 1, LAB_KIND_INT },
    { "Puñetazo", "Alcance", &g_lab_punch_range, 16, 64, 2, LAB_KIND_INT },

    { "Pruebas", "Invulnerable", &g_lab_god, 0, 1, 1, LAB_KIND_INT },
#endif
#if ARPG_BOXEO
    { "Pruebas", "Saco quieto", &g_lab_saco_still, 0, 1, 1, LAB_KIND_INT },
    { "Pruebas", "Saco tipo", &g_lab_saco_type, 0, BOXEO_TYPE_COUNT - 1, 1, LAB_KIND_INT, g_boxeo_type_names },
#endif
};
#define N_ENTRIES ((int)(sizeof(s_entries) / sizeof(s_entries[0])))


#define VISIBLE_ROWS 10
#define ROW_H 13
#define ROW_Y0 22

static int s_open = 0;
static int s_page = 0;          /* index of the current page */
static int s_sel = 0;           /* row inside the page */
static int s_scroll = 0;
static int s_hold_dir = 0, s_hold_frames = 0;

void lab_tuning_init(void) {
    for (int i = 0; i < SND_COUNT; i++) g_lab_sfx_var[i] = 0;
}

int lab_tuning_is_open(void) { return s_open; }

/* The k-th distinct page title in order of appearance (NULL past the last). */
static const char *page_title(int k) {
    int seen = -1;
    for (int i = 0; i < N_ENTRIES; i++) {
        int first = 1;
        for (int j = 0; j < i; j++) {
            if (strcmp(s_entries[j].page, s_entries[i].page) == 0) { first = 0; break; }
        }
        if (first && ++seen == k) return s_entries[i].page;
    }
    return NULL;
}

static int page_count(void) {
    int n = 0;
    while (page_title(n)) n++;
    return n;
}

/* Entry index of row `row` in the current page, or -1. */
static int page_entry(int row) {
    const char *t = page_title(s_page);
    int r = 0;
    for (int i = 0; i < N_ENTRIES; i++) {
        if (strcmp(s_entries[i].page, t) != 0) continue;
        if (r++ == row) return i;
    }
    return -1;
}

static int page_rows(void) {
    int n = 0;
    while (page_entry(n) >= 0) n++;
    return n;
}

static int sfx_event(const LabEntry *e) { return (int)(e->value - g_lab_sfx_var); }

static void change(const LabEntry *e, int dir) {
    int v = *e->value;
    if (e->kind == LAB_KIND_CANDIDATE) return;
    if (e->kind == LAB_KIND_SFX_VARIANT) {
        int n = s_ev[sfx_event(e)].n;
        if (n == 0) return;
        v += dir;
        if (v < 0) v = n;
        if (v > n) v = 0;
        *e->value = v;
        sfx_lab_prepare(sfx_event(e));
        return;
    }
    v += dir * e->step;
    if (v < e->min) v = e->min;
    if (v > e->max) v = e->max;
    *e->value = v;
}

static void set_page(int p) {
    int n = page_count();
    s_page = (p % n + n) % n;
    s_sel = 0;
    s_scroll = 0;
}

int lab_tuning_update(uint32_t keys_down, uint32_t keys_held) {
    const int chord = (keys_held & KEY_L) && (keys_held & KEY_R);      /* L+R+SELECT is the bestiary / crash combo */
    if (!s_open) {
        if ((keys_down & KEY_SELECT) && !chord) {
            s_open = 1;
            s_hold_dir = 0;
            sfx_set_bgm_paused(1);
            return 1;
        }
        return 0;
    }
    if (keys_down & (KEY_B | KEY_SELECT)) {
        s_open = 0;
        sfx_set_bgm_paused(0);
        return 1;           /* this frame the closing key is still swallowed */
    }
    int rows = page_rows();
    if (keys_down & KEY_UP) s_sel = (s_sel + rows - 1) % rows;
    if (keys_down & KEY_DOWN) s_sel = (s_sel + 1) % rows;
    if (keys_down & KEY_L) set_page(s_page - 1);
    if (keys_down & KEY_R) set_page(s_page + 1);
    rows = page_rows();
    if (s_sel < s_scroll) s_scroll = s_sel;
    if (s_sel >= s_scroll + VISIBLE_ROWS) s_scroll = s_sel - VISIBLE_ROWS + 1;

    int ei = page_entry(s_sel);
    if (ei >= 0) {
        const LabEntry *e = &s_entries[ei];
        int dir = 0;
        if (keys_down & KEY_LEFT) { dir = -1; s_hold_dir = -1; s_hold_frames = 0; }
        else if (keys_down & KEY_RIGHT) { dir = 1; s_hold_dir = 1; s_hold_frames = 0; }
        else if ((s_hold_dir < 0 && (keys_held & KEY_LEFT)) || (s_hold_dir > 0 && (keys_held & KEY_RIGHT))) {
            if (++s_hold_frames >= 20 && (s_hold_frames & 3) == 0 && e->kind == LAB_KIND_INT) dir = s_hold_dir;
        } else {
            s_hold_dir = 0;
        }
        if (dir) change(e, dir);
        if ((keys_down & KEY_A) && e->kind == LAB_KIND_SFX_VARIANT) sfx_lab_preview(sfx_event(e));
        if ((keys_down & KEY_A) && e->kind == LAB_KIND_CANDIDATE) sfx_lab_play_candidate(e->min);
    }
    return 1;
}

#define COL_PANEL (RGB15(2, 1, 3) | BIT(15))
#define COL_BORDER (RGB15(10, 9, 8) | BIT(15))
#define COL_SEL (RGB15(9, 3, 3) | BIT(15))
#define COL_TXT (RGB15(26, 24, 20) | BIT(15))
#define COL_DIM (RGB15(15, 14, 13) | BIT(15))
#define COL_GOLD (RGB15(31, 27, 12) | BIT(15))

static void fill(uint16_t *buf, int x0, int y0, int x1, int y1, uint16_t col) {
    dirty_rect(x0, y0, x1, y1);
    for (int y = y0; y < y1; y++) {
        uint16_t *row = &buf[y * SCREEN_W];
        for (int x = x0; x < x1; x++) row[x] = col;
    }
}

static void text(uint16_t *buf, int x, int y, const char *s, uint16_t col) {
    bestiary_font_draw_utf8(buf, x, y, s, col);
}

static void text_right(uint16_t *buf, int xr, int y, const char *s, uint16_t col) {
    text(buf, xr - bestiary_font_measure_utf8(s), y, s, col);
}

void lab_tuning_render(uint16_t *buf) {
    if (!s_open || !buf) return;
    fill(buf, 4, 2, SCREEN_W - 4, SCREEN_H - 2, COL_BORDER);
    fill(buf, 5, 3, SCREEN_W - 5, SCREEN_H - 3, COL_PANEL);

    char head[64];
    if (page_rows() > VISIBLE_ROWS) snprintf(head, sizeof(head), "fila %d/%d  pág %d/%d", s_sel + 1, page_rows(), s_page + 1, page_count());
    else snprintf(head, sizeof(head), "pág %d/%d", s_page + 1, page_count());
    text(buf, 10, 5, page_title(s_page), COL_GOLD);
    text_right(buf, SCREEN_W - 10, 5, head, COL_DIM);

    int rows = page_rows();
    for (int v = 0; v < VISIBLE_ROWS; v++) {
        int row = s_scroll + v;
        if (row >= rows) break;
        const LabEntry *e = &s_entries[page_entry(row)];
        int y = ROW_Y0 + v * ROW_H;
        int sel = (row == s_sel);
        if (sel) fill(buf, 7, y - 1, SCREEN_W - 7, y + ROW_H - 1, COL_SEL);
#if SOUND_TEST
        text(buf, 12, y, e->kind == LAB_KIND_CANDIDATE ? s_labv_file[e->min] : e->label, sel ? COL_GOLD : COL_TXT);
#else
        int dim_row = (e->kind == LAB_KIND_SFX_VARIANT && s_ev[sfx_event(e)].n == 0);
        text(buf, 12, y, e->label, sel ? COL_GOLD : (dim_row ? COL_DIM : COL_TXT));
#endif
        char val[48];
        val[0] = 0;
        int dim = 0;
        if (e->kind == LAB_KIND_CANDIDATE) {
#if SOUND_TEST
            snprintf(val, sizeof(val), "%s", s_variant_labels[e->min]);
#endif
        } else if (e->kind == LAB_KIND_SFX_VARIANT) {
            int ev = sfx_event(e), k = *e->value;
            dim = (s_ev[ev].n == 0);
#if SOUND_TEST
            {   /* the exact file the row plays now, with its origin: K = free bank (Kenney), IA = generated (ElevenLabs) */
                const char *file = k ? s_labv_file[s_ev[ev].v[k - 1]] : s_snd_file[ev];
                if (k && strncmp(file, "cand_", 5) == 0)   /* round-2 candidate: its label already says A/B/C and the origin */
                    snprintf(val, sizeof(val), "* %s", s_variant_labels[s_ev[ev].v[k - 1]]);
                else
                    snprintf(val, sizeof(val), "%s%s%s", k ? "* " : "", strncmp(file, "lab_", 4) == 0 ? "K·" : "IA·", file);
                dim = 0;
            }
#else
            snprintf(val, sizeof(val), "%s%s", k ? "* " : "", k ? s_variant_labels[s_ev[ev].v[k - 1]] : "Original");
#endif
        } else if (e->names) {
            snprintf(val, sizeof(val), "%s", e->names[*e->value]);
        } else {
            snprintf(val, sizeof(val), "%d", *e->value);
        }
        text_right(buf, SCREEN_W - 12, y, val, sel ? COL_GOLD : (dim ? COL_DIM : COL_TXT));
    }

#if SOUND_TEST
    if (strcmp(page_title(s_page), PG_ESC) == 0) {
        text(buf, 10, 52, "Suenan en esta escena:", COL_GOLD);
        bestiary_font_draw_wrapped(buf, 10, 63, SCREEN_W - 20, 10, g_snd_scene_sounds[g_snd_scene], COL_TXT);
        text(buf, 10, 99, "Qué hacer:", COL_GOLD);
        bestiary_font_draw_wrapped(buf, 10, 110, SCREEN_W - 20, 10, g_snd_scene_todo[g_snd_scene], COL_TXT);
    }
#endif
    text(buf, 10, 154, "Cruz: fila y variante     A: probar", COL_DIM);
    text(buf, 10, 166, "L/R: página     B o SELECT: cerrar", COL_DIM);
    text(buf, 10, 178, "* = variante distinta del original", COL_DIM);
}

#else
typedef int lab_tuning_disabled_translation_unit;
#endif
