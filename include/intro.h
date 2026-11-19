#ifndef INTRO_H
#define INTRO_H

#include <stdint.h>

/* Secuencia de 5 tarjetas de introduccion (DESIGN.md 6.3). Bloquea hasta que
 * el jugador pulsa EMPEZAR/SALTAR/START. Mismos parametros que bestiary_run. */
void intro_run(uint16_t *top_page, uint16_t *bot_page_a, uint16_t *bot_page_b,
               int *bot_active_page_idx, void (*vblank_flip_fn)(void));

#endif /* INTRO_H */
