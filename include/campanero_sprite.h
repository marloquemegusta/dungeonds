#ifndef CAMPANERO_SPRITE_H
#define CAMPANERO_SPRITE_H

#include <stdint.h>

// Fotogramas del Campanero de Animas leidos de NitroFS (nitro:/campanero/campanero.bin) de uno en uno:
// cinco clips x 8 dir x 8 fotogramas no caben en la EWRAM fija. Formato en tools/generate_campanero_bin.py.
#define CAMP_CLIP_IDLE   0
#define CAMP_CLIP_WALK   1
#define CAMP_CLIP_TOQUE  2
#define CAMP_CLIP_TANIDO 3
#define CAMP_CLIP_DEATH  4
#define CAMP_NUM_CLIPS   5

typedef struct {
    const uint8_t  *bounds;    // {x, y, w, h} dentro de la celda 60x60
    const uint16_t *pix;       // pixeles recortados (pitch par)
    const uint16_t *runs;      // bloque de tramos opacos
    const uint8_t  *sbounds;   // {x, y, w, h} de la sombra en el lienzo 80x80
    const uint8_t  *mask;      // mascara de sombra (nibbles)
} CampSprite;

// Devuelve 1 y rellena `out` (valido hasta la siguiente llamada con otro fotograma); 0 si no hay bin.
int campanero_sprite_get(int clip, int dir, int frame, CampSprite *out);
// Cierra el fichero (al salir de la sala) y descarta la cache.
void campanero_sprite_close(void);

#endif
