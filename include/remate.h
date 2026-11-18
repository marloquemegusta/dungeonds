#ifndef REMATE_H
#define REMATE_H

#include "gameplay.h"
#include "remate_sprites.h"

// Remates (DESIGN.md 6.13.8): un golpe que no mata deja al Exvoto o al Cireneo TAMBALEANDOSE (WOBBLE);
// con L el heroe ejecuta el remate (animacion combinada de remate_sprites.h), el enemigo muere sin su
// efecto estandar de muerte y el rayo del heroe queda cargado al instante.
#define REMATE_WOBBLE_FRAMES 60     // [TUNABLE-PLACEHOLDER] frames que tambalea tras un golpe que no mata
#define REMATE_RANGE 48             // [TUNABLE-PLACEHOLDER] alcance de L (px de suelo)
#define REMATE_TICKS 4              // [TUNABLE-PLACEHOLDER] frames de juego por fotograma de la animacion (12 fotogramas)
#define REMATE_REMNANT_FRAMES 30    // [TUNABLE-PLACEHOLDER] vida de las mitades en el suelo (~0,5 s); los ultimos 12 parpadean
#define REMATE_REMNANT_BLINK 12     // [TUNABLE-PLACEHOLDER]

void remate_reset(void);
// L: empieza el remate del enemigo tambaleante mas cercano a <= REMATE_RANGE. Devuelve 1 si empezo.
int remate_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y);
// Una vez por frame simulado (aunque no haya remate: avanza el resto). Al terminar mueve al heroe al sitio final.
void remate_update(Enemy *enemies, int max_enemies, fixed *hero_x, fixed *hero_y, int *hero_dir);
int remate_active(void);
int remate_kind(void);
// Fotograma de la animacion (0..11) y variante (0 = tal cual, 1 = espejada).
int remate_frame(void);
int remate_mirror(void);
// Ancla de la celda (pies finales del heroe, px de mundo).
void remate_origin(int *x, int *y);
// Mitades en el suelo: 1 si hay, con tipo, ancla y variante; *visible = 0 en los parpadeos apagados.
int remate_remnant(int *kind, int *x, int *y, int *mirror, int *visible);
// 1 mientras enemy_hit mata al rematado: el gancho de muerte se salta el derretido o desmembramiento.
int remate_killing(void);
void remate_shift_y(int dy_px);

#endif
