#ifndef LAB_TUNING_H
#define LAB_TUNING_H

/*
 * Lab tuning menu (variant "arpg-lab", define ARPG_LAB=1). SELECT opens it on the bottom screen and pauses the game.
 * D-pad up/down: row. Left/right: change the value (held: repeats). A: test (a sound plays). L/R: page. B/SELECT: close.
 * In every other build this whole module compiles to nothing.
 *
 * HOW TO ADD A TUNABLE (3 steps):
 *   1. In lab_tuning.c define the variable with its default:   int g_lab_remate_range = 40;
 *      and declare it here:                                    extern int g_lab_remate_range;
 *   2. Register one line in s_entries[] (lab_tuning.c):
 *        { "Remates", "Alcance", &g_lab_remate_range, 8, 120, 4, LAB_KIND_INT },
 *      (page, label, variable, min, max, step, kind). Entries with the same page text share a page.
 *   3. In the game code read the variable instead of the constant (inside #if ARPG_LAB, or via a macro that falls
 *      back to the constant). Changes apply live, the menu has no other plumbing.
 * Sounds are LAB_KIND_SFX_VARIANT rows: one per event (SfxId). Variant 0 is the event's own baked sound ("Original");
 * the others are candidate files assets/sfx/baked/lab_*.wav. To add a candidate: drop lab_<slug>.wav in that folder,
 * add one X(...) line to LAB_VARIANTS below and list it for its event in s_ev[] (lab_tuning.c).
 */

#include <stdint.h>

#ifndef ARPG_LAB
#define ARPG_LAB 0
#endif

#if ARPG_LAB
#include "sfx.h"

/* Candidate sound variants: X(name, menu label, soundbank id SFX_LAB_<NAME>). Ids are only expanded in sfx.c. */
#define LAB_VARIANTS(X)     X(CLOTH1, "Tela rápida 1", SFX_LAB_CLOTH1) X(CLOTH4, "Tela rápida 4", SFX_LAB_CLOTH4)     X(KNIFE, "Corte/aire seco", SFX_LAB_KNIFE)     X(PUNCH_M0, "Puñetazo medio 0", SFX_LAB_PUNCH_M0) X(PUNCH_M2, "Puñetazo medio 2", SFX_LAB_PUNCH_M2)     X(PUNCH_H0, "Puñetazo pesado 0", SFX_LAB_PUNCH_H0) X(PUNCH_H3, "Puñetazo pesado 3", SFX_LAB_PUNCH_H3)     X(WOOD_HEAVY, "Madera pesada", SFX_LAB_WOOD_HEAVY) X(MINING0, "Piedra/roca", SFX_LAB_MINING0)     X(GENERIC_LIGHT, "Golpe seco", SFX_LAB_GENERIC_LIGHT)     X(BELL_H0, "Campana grave 0", SFX_LAB_BELL_H0) X(BELL_H2, "Campana grave 2", SFX_LAB_BELL_H2)     X(BONG, "Bong corto", SFX_LAB_BONG)     X(MINING2, "Tierra/piedra", SFX_LAB_MINING2) X(STEP_STONE, "Paso piedra", SFX_LAB_STEP_STONE)     X(GLASS1, "Cristal 1", SFX_LAB_GLASS1) X(GLASS4, "Cristal 4", SFX_LAB_GLASS4)     X(CONFIRM1, "Confirmación suave", SFX_LAB_CONFIRM1)     X(CREAK, "Chirrido cofre", SFX_LAB_CREAK) X(LATCH, "Pestillo metálico", SFX_LAB_LATCH)     X(DOOR_OPEN1, "Apertura madera", SFX_LAB_DOOR_OPEN1)     X(DOOR_OPEN2, "Puerta pesada", SFX_LAB_DOOR_OPEN2) X(DOOR_CLOSE, "Cierre puerta", SFX_LAB_DOOR_CLOSE)     X(CLICK, "Click", SFX_LAB_CLICK) X(SELECT, "Select", SFX_LAB_SELECT) X(TICK, "Tick", SFX_LAB_TICK)     X(DROP, "Encaje seco", SFX_LAB_DROP) X(METAL_CLICK, "Click metálico", SFX_LAB_METAL_CLICK)     X(PLATE, "Placa/piedra", SFX_LAB_PLATE)     X(CONFIRM2, "Acorde confirmación", SFX_LAB_CONFIRM2) X(MAXIMIZE, "Ascenso", SFX_LAB_MAXIMIZE)

enum {
#define X(n, label, mm) LABV_##n,
    LAB_VARIANTS(X)
#undef X
    LABV_COUNT
};

typedef enum { LAB_KIND_INT = 0, LAB_KIND_SFX_VARIANT } LabKind;

typedef struct {
    const char *page;       /* page title (entries with the same text are shown together) */
    const char *label;      /* short row label, Spanish */
    int *value;
    int min, max, step;     /* LAB_KIND_SFX_VARIANT ignores them (0..number of variants of its event, wraps) */
    LabKind kind;
} LabEntry;

extern int g_lab_sfx_var[SND_COUNT];    /* per event: 0 = Original, 1.. = that event's candidates in order */
extern int g_lab_god;                   /* 1 = the hero cannot die (applied each frame by main.c) */
/* The candidate (LABV_*) the event currently plays, or -1 for its original sound. */
int lab_sfx_candidate(int ev);

void lab_tuning_init(void);
/* Feed the frame's keys. Returns 1 while the menu is open (the game must not simulate nor see the keys). */
int lab_tuning_update(uint32_t keys_down, uint32_t keys_held);
int lab_tuning_is_open(void);
void lab_tuning_render(uint16_t *bottom_page);   /* draws over the bottom screen page; no-op when closed */

/* sfx.c: plays the event with its current variant, ignoring cooldown (the A preview); prepare loads the variant. */
void sfx_lab_preview(int ev);
void sfx_lab_prepare(int ev);
#endif

#endif /* LAB_TUNING_H */
