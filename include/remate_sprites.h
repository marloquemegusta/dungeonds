#ifndef REMATE_SPRITES_H
#define REMATE_SPRITES_H
// Generado por tools/generate_remate_sprites.py: no editar a mano.
#include <stdint.h>

#define REMATE_KIND_EXVOTO     0
#define REMATE_KIND_CIRENEO    1
#define REMATE_KIND_OJO        2
#define REMATE_KIND_MONAGUILLO 3
#define REMATE_KIND_BEBE       4
#define REMATE_NUM_KINDS       5
#define REMATE_NUM_DIRS      8

// Mayor numero de fotogramas de animacion de cualquier tipo (el Ojo, 38). Cada tipo declara los suyos en
// `RemateKindInfo.frames`; Exvoto y Cireneo usan 12. El bin de cada tipo lleva cabecera del tamano de sus frames.
#define REMATE_MAX_FRAMES    38
#define REMATE_SHADOW_CANVAS 80
#define REMATE_BIN_MAGIC     0x31544D52u
// Streaming desde NitroFS (remate.c): la celda lee el fotograma que toca a estos buffers estaticos en vez de cargar
// el bin entero. Son el peor fotograma de cualquier tipo/direccion (cuadrados a 1 KiB por el generador).
#define REMATE_HEADER_BYTES  2048
#define REMATE_PIX_BYTES     18432
#define REMATE_RUN_BYTES     1024
#define REMATE_MASK_BYTES    1024

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t has_remnant;
    uint8_t remnant_frame;   // indice del fotograma de restos dentro del bin
    uint8_t frames;          // fotogramas de animacion (sin el de restos)
    uint8_t ticks;           // frames de juego por fotograma de animacion
} RemateKindInfo;

typedef struct {
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
} RemateDirInfo;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];
extern const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS];
// Profundidad de cada capa de la celda por fotograma ([0] = heroe y enemigo en el agarre, [1] = restos sueltos), en px de mundo
// respecto a los pies finales del heroe. Solo se usan los primeros `frames` valores de cada fila.
extern const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2];
// Pies del heroe en el suelo (x, y) por fotograma, en px de mundo respecto al ancla (sus pies finales): el fotograma 0 es
// donde debe estar para empezar sin salto y el ultimo es (0,0). Lo usan la embestida previa y la camara (remate.c).
extern const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_MAX_FRAMES][2];

#endif
