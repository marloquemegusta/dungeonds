#ifndef REMATE_SPRITES_H
#define REMATE_SPRITES_H
// Generado por tools/generate_remate_sprites.py: no editar a mano.
#include <stdint.h>

#define REMATE_KIND_EXVOTO   0
#define REMATE_KIND_CIRENEO  1
#define REMATE_NUM_KINDS     2
#define REMATE_NUM_DIRS      8

#define REMATE_NUM_FRAMES    12
#define REMATE_SHADOW_CANVAS 80
#define REMATE_BIN_MAGIC     0x54414D52u
#define REMATE_MAX_BIN_BYTES 86608

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t has_remnant;
    uint8_t remnant_frame;
} RemateKindInfo;

typedef struct {
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
} RemateDirInfo;

typedef struct {
    uint32_t magic;
    uint32_t pix_bytes;
    uint32_t runs_bytes;
    uint32_t mask_bytes;
    uint8_t  f_bounds[REMATE_NUM_FRAMES + 1][4];
    uint32_t f_pix_off[REMATE_NUM_FRAMES + 1];
    uint32_t f_run_off[REMATE_NUM_FRAMES + 1];
    uint8_t  s_bounds[REMATE_NUM_FRAMES][4];
    uint32_t s_mask_off[REMATE_NUM_FRAMES];
    uint8_t  d_bounds[REMATE_NUM_FRAMES + 1][4];     // capa B: restos sueltos del fotograma (0 = ninguno)
    uint32_t d_pix_off[REMATE_NUM_FRAMES + 1];
    uint32_t d_run_off[REMATE_NUM_FRAMES + 1];
} RemateBinHeader;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];
extern const RemateDirInfo g_remate_dir_info[REMATE_NUM_KINDS][REMATE_NUM_DIRS];
// Profundidad de cada capa de la celda por fotograma ([0] = heroe y enemigo en el agarre, [1] = restos sueltos), en px de mundo
// respecto a los pies finales del heroe: [0] la mas cercana entre los pies del heroe y el enemigo, [1] la fila mas baja de los restos (pack_dir_bin en el generador).
extern const int8_t g_remate_depth[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2];
// Pies del heroe en el suelo (x, y) por fotograma, en px de mundo respecto al ancla (sus pies finales): el fotograma 0 es
// donde debe estar para empezar sin salto y el 11 es (0,0). Lo usan la embestida previa y la camara (remate.c).
extern const int8_t g_remate_hero_off[REMATE_NUM_KINDS][REMATE_NUM_DIRS][REMATE_NUM_FRAMES][2];

#endif
