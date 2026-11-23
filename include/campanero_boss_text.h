/* Presentation of El Campanero de Ánimas (DESIGN.md 6.13.7, DESIGN-ARPG.md 9). He has no voice: the "phrase" is what the
 * bell says; the sounds are bell tolls (tools/sfx/make_campanero_boss_sfx.py). Drop these into his BossDef. */
#ifndef CAMPANERO_BOSS_TEXT_H
#define CAMPANERO_BOSS_TEXT_H

#include "sfx.h"
#include "sfx_voice_len.h"

/* The name is drawn at x2 and the full "EL CAMPANERO DE ÁNIMAS" is 326 px (> 256): the name carries "EL CAMPANERO" and the
 * title the rest. */
#define CAMPANERO_BOSS_NAME "EL CAMPANERO"
#define CAMPANERO_BOSS_TITLE "de Ánimas, boca cosida, lengua de bronce"
#define CAMPANERO_BOSS_LINE_INTRO "«Doblan por ti.\nLos muertos ya vienen.»"
#define CAMPANERO_BOSS_LINE_DEFEAT "«Ya no doblan\npor nadie.»"
#define CAMPANERO_BOSS_SFX_INTRO SND_CAMPANERO_INTRO
#define CAMPANERO_BOSS_SFX_DEFEAT SND_CAMPANERO_DEFEAT
#define CAMPANERO_BOSS_VOICE_INTRO_FRAMES SFX_VOICE_VBLANKS_CAMPANERO_INTRO
#define CAMPANERO_BOSS_VOICE_DEFEAT_FRAMES SFX_VOICE_VBLANKS_CAMPANERO_DEFEAT

#endif
