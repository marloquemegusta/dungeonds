#ifndef CAMPANERO_SPRITE_H
#define CAMPANERO_SPRITE_H

#include <stdint.h>

// 1 = los clips que tools/generate_campanero_bin.py --lz comprimio se descomprimen en ejecucion (por fotograma, al cambiar).
// Desactivado: el bin de serie va sin comprimir y esta flag no se activa en ninguna variante (se prueba con -DCAMP_LZ_BODY=1).
#ifndef CAMP_LZ_BODY
#define CAMP_LZ_BODY 0
#endif

// Fotogramas del Campanero de Animas (nitro:/campanero/campanero.bin, formato en tools/generate_campanero_bin.py).
// Al cargar la sala del jefe el bin entero se lee al deposito de sala (room_pool.h) y los fotogramas se sirven de
// memoria; si no cabe, respaldo: se leen de uno en uno del cartucho a buffers pequenos del deposito.
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
    const uint8_t  *mask;      // mascara de sombra (1 bpp, LSB primero)
} CampSprite;

// Devuelve 1 y rellena `out` (valido hasta la siguiente llamada con otro fotograma); 0 si no hay bin.
int campanero_sprite_get(int clip, int dir, int frame, CampSprite *out);
// Carga el Campanero en el deposito de sala (1 = listo). Llamar tras cargar los enemigos: se queda con lo que sobra.
int campanero_sprite_load(void);
// Lo olvida (el deposito se vacia con room_pool_reset): cierra el fichero del respaldo.
void campanero_sprite_unload(void);
int campanero_sprite_loaded(void);
int campanero_sprite_is_blob(void);     // 1 = bin entero en memoria (sin lecturas en combate)

#endif
