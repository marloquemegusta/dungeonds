#ifndef BOXEO_H
#define BOXEO_H

// Variante "arpg-boxeo" (ARPG_BOXEO=1): la sala ARPG inicial no tiene mas enemigo que el "saco", un enemigo de
// vida infinita colocado delante del heroe para ajustar el punetazo. Todo el modulo compila a nada en el resto.
#include "lab_tuning.h"
#include "game.h"
#include "gameplay.h"

#define BOXEO_TYPE_COUNT 7      // tipos que recorre la fila "Saco tipo" del menu (boxeo.c: s_types)

#if ARPG_BOXEO
extern const char *const g_boxeo_type_names[BOXEO_TYPE_COUNT];
void boxeo_reset(void);
// Una vez por frame simulado: coloca el saco si falta, le devuelve la vida y lo trae de vuelta a su sitio.
void boxeo_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y);
#endif

#endif
