#ifndef REMATE_H
#define REMATE_H

#include "gameplay.h"
#include "remate_sprites.h"

// Remates (DESIGN.md 6.13.8): un golpe que no mata deja al enemigo TAMBALEANDOSE (WOBBLE); con L el heroe ejecuta
// el remate (animacion combinada de remate_sprites.h), el enemigo muere sin su efecto estandar de muerte y el rayo
// del heroe queda cargado al instante. Cada tipo (Exvoto, Cireneo, Ojo) trae sus fotogramas y ticks de juego en
// g_remate_kind_info: el Exvoto y el Cireneo duran 12x6 = 72 frames (~1,2 s); el Ojo, 38x4 = 152 (~2,5 s).
#define REMATE_WOBBLE_FRAMES 180    // [TUNABLE-PLACEHOLDER] frames que tambalea tras un golpe que no mata (~3 s)
#define REMATE_RANGE 96             // [TUNABLE-PLACEHOLDER] alcance de L (px de suelo)
#define REMATE_POST_INVULN_FRAMES 60 // [TUNABLE-PLACEHOLDER] invulnerabilidad tras acabar el remate (~1 s) para reposicionarse
#define REMATE_REMNANT_FRAMES 60    // [TUNABLE-PLACEHOLDER] vida de los restos en el suelo (~1,0 s); los ultimos 18 parpadean
#define REMATE_REMNANT_BLINK 18     // [TUNABLE-PLACEHOLDER]
#define REMATE_DASH_SPEED 4         // [TUNABLE-PLACEHOLDER] px de suelo por frame de la embestida previa (mas rapido que andar)
#define REMATE_DASH_MAX_FRAMES 20   // [TUNABLE-PLACEHOLDER] tope de la embestida (~0,3 s); si no llega, salta al punto de inicio

void remate_reset(void);
// L: empieza el remate del enemigo tambaleante (Exvoto, Cireneo u Ojo) mas cercano a <= REMATE_RANGE. Devuelve 1 si empezo.
int remate_start(Enemy *enemies, int max_enemies, fixed hero_x, fixed hero_y, int hero_dir);
// Una vez por frame simulado (aunque no haya remate: avanza el resto). Al terminar mueve al heroe al sitio final.
void remate_update(Enemy *enemies, int max_enemies, fixed *hero_x, fixed *hero_y, int *hero_dir);
// 1 mientras suena la celda combinada (dibujo del heroe y el enemigo fundidos en una).
int remate_active(void);
// 1 durante la embestida previa: el heroe corre al punto de inicio de la celda con su animacion de andar normal.
int remate_approaching(void);
// Frames restantes de invulnerabilidad post-remate (separada de invuln_timer de daño).
int remate_invuln(void);
int remate_kind(void);
// Fotograma de la animacion del tipo activo (0..frames-1) y direccion (0..7, DIR_SOUTH..DIR_SOUTHEAST).
int remate_frame(void);
int remate_dir(void);
// Ancla de la celda (pies finales del heroe, px de mundo).
void remate_origin(int *x, int *y);
// Restos en el suelo: 1 si hay, con tipo, ancla y direccion; *visible = 0 en los parpadeos apagados.
int remate_remnant(int *kind, int *x, int *y, int *dir, int *visible);
// 1 mientras enemy_hit mata al rematado: el gancho de muerte se salta el derretido o desmembramiento.
int remate_killing(void);
void remate_shift_y(int dy_px);

// Datos binarios del remate activo. Cada tipo tiene su numero de fotogramas, asi que la cabecera del bin es variable:
// remate.c la interpreta y va leyendo de NitroFS el fotograma que toca a buffers estaticos (streaming). Estas funciones
// devuelven punteros al fotograma ya cargado.
const uint16_t *remate_layer_pixels(int layer);
const uint16_t *remate_layer_runs(int layer);
const uint8_t *remate_shadow_mask(void);
// Capa `layer` (0 = heroe/enemigo en el agarre, 1 = restos sueltos) del fotograma f.
const uint8_t *remate_layer_bounds(int layer, int f);
// Sombra horneada del fotograma f (mascara 4bpp + bounds dentro del lienzo).
const uint8_t *remate_shadow_bounds(int f);

#endif
