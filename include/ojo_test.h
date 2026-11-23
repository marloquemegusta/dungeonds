#ifndef OJO_TEST_H
#define OJO_TEST_H

// Variante "arpg-ojo" (ARPG_OJO_TEST=1): las salas ARPG no se pueblan y, delante del heroe, vive UN Ojo del Tribunal
// despierto con columnas en la sala para probar la sentencia (coberturas). Todo el modulo compila a nada en el resto.
#include "lab_tuning.h"
#include "game.h"
#include "gameplay.h"

#if ARPG_OJO_TEST
// Lectura de depuracion (escenarios): [0..1] heroe x,y; [2..3] Ojo x,y; [4..7] caja de la columna elegida x0,y0,x1,y1;
// [12..43] hasta 8 cajas de columna x0,y0,x1,y1; [8] columnas halladas; [9] 1 si hay linea de tiro limpia Ojo-heroe al colocarlo.
extern volatile int g_ojo_test_dbg[48];
void ojo_test_reset(void);
// Una vez por frame simulado: si el Ojo ha muerto, lo repone en su sitio a los ~2 s.
void ojo_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y);
#endif

#endif
