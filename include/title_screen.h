#ifndef TITLE_SCREEN_H
#define TITLE_SCREEN_H

#include <stdint.h>

/* Pantalla de título (DESIGN-ARPG.md §8): pantalla superior con el nombre y una vela.
 * full != 0 pinta todo; si no, solo repinta la llama (cada 4 frames). */
void title_top_render(uint16_t *buf, uint32_t frame, int full);

#endif
