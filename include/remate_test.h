#ifndef REMATE_TEST_H
#define REMATE_TEST_H

// Variante "arpg-remates" (ARPG_REMATE_TEST=1): las salas ARPG no se pueblan y, delante del heroe, hay una fila de
// Exvotos quietos (Monja de cera, Monaguillo, Bebe, Parroco, Super Monja) y, mas al norte, una segunda Super Monja con
// una Monja de cera y un Monaguillo poseidos. Un solo punetazo deja tambaleante a cada uno (listo para el remate con `L`)
// y, cuando uno muere, reaparece en su sitio a los ~2 s. Todo el modulo compila a nada en el resto.
#include "lab_tuning.h"
#include "game.h"
#include "gameplay.h"

#if ARPG_REMATE_TEST
void remate_test_reset(void);
// Una vez por frame simulado: coloca el montaje la primera vez y repone cada enemigo ~2 s despues de caer.
void remate_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y);
#endif

#endif
