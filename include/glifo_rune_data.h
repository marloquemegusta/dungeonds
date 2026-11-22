// GENERADO por tools/glifo_rune/bake_glifo_rune.py: no editar a mano.
// Runa A «Sello litúrgico» del Glifo (DESIGN.md 7.7) a radio de suelo 40 (elipse 80x40), relativa al centro.
// Capas: base (siempre) + transformación Redil (misma geometría en remolino) + capa aditiva Zarza (emisores).
#ifndef GLIFO_RUNE_DATA_H
#define GLIFO_RUNE_DATA_H
#include <stdint.h>

// Un píxel de la grieta, ordenados por `order` (orden de apertura 0..255).
// close: orden de cierre (0 = el de fuera, 255 = el del centro).
// flags: bits 0-1 brillo (0 = 0,5; 1 = 1; 2 = 1,12); GLIFO_FL_BRANCH astilla corta; GLIFO_FL_SHARD esquirla de piedra
// levantada; GLIFO_FL_FLARE el píxel arde en la llamarada de la Zarza al detonar.
typedef struct { int8_t dx, dy; uint8_t order, close, flags; } GlifoPx;
#define GLIFO_FL_BRANCH 4
#define GLIFO_FL_SHARD 8
#define GLIFO_FL_FLARE 16

// Pozo de luz del Redil. col: 0 hondo, 1 borde, 2 brillo bajo, 3 marfil, 4 oro, 5 ámbar. rr: 0..245 (200 = borde).
typedef struct { int8_t dx, dy; uint8_t col, rr; } GlifoVx;

#define GLIFO_EMIT_N 32
#define GLIFO_BASE_N 698
#define GLIFO_TWIST_N 788
#define GLIFO_VX_BASE_N 116
#define GLIFO_VX_FRAMES 8
#define GLIFO_VX_ARM_N 39

extern const GlifoPx g_glifo_base[GLIFO_BASE_N];       // Sello solo (y con Zarza)
extern const GlifoPx g_glifo_twist[GLIFO_TWIST_N];     // la misma runa retorcida por el Redil
extern const int8_t g_glifo_emit_base[GLIFO_EMIT_N][2];   // emisores de lenguas de la Zarza sobre cada máscara
extern const int8_t g_glifo_emit_twist[GLIFO_EMIT_N][2];
extern const GlifoVx g_glifo_vx_base[GLIFO_VX_BASE_N];
extern const GlifoVx g_glifo_vx_arm[GLIFO_VX_FRAMES][GLIFO_VX_ARM_N];   // relleno con rr = 255
extern const int8_t g_glifo_spiral[3][24][2];          // ruta de las motas del Redil: brazo, punto, (dx, dy)
extern const uint8_t g_glifo_flame_h[16];              // altura de la lengua de llama por edad

#endif
