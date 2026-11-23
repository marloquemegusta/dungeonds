#ifndef EXVOTO_TEST_H
#define EXVOTO_TEST_H

// Variante "arpg-exvotos" (ARPG_EXVOTO_TEST=1): las salas ARPG no se pueblan y, delante del heroe, vive un
// encuentro de prueba de los Exvotos de escalon 3 (Super Monja, Monjas de cera, Monaguillos, Parroco, Bebe).
// Todo el modulo compila a nada en el resto.
#include "lab_tuning.h"
#include "game.h"
#include "gameplay.h"

#if ARPG_EXVOTO_TEST
void exvoto_test_reset(void);
// Una vez por frame simulado: cuando no queda vivo ninguno del encuentro, lo recoloca tras ~2 s.
void exvoto_test_update(Enemy *enemies, int max_enemies, int hero_x, int hero_y);
#endif

#endif
