#ifndef REMATE_SPRITES_H
#define REMATE_SPRITES_H
// Generado por tools/generate_remate_sprites.py: no editar a mano.
#include <stdint.h>

#define REMATE_KIND_EXVOTO   0
#define REMATE_KIND_CIRENEO  1
#define REMATE_NUM_KINDS     2

#define REMATE_NUM_FRAMES    12
#define REMATE_SHADOW_CANVAS 80

typedef struct {
    uint8_t cell_w;
    uint8_t cell_h;
    uint8_t anchor_x;
    uint8_t anchor_y;
    int8_t  enemy_dx;
    int8_t  enemy_dy;
    int8_t  shadow_ox;
    int8_t  shadow_oy;
    uint8_t has_remnant;
    uint8_t remnant_frame;
} RemateKindInfo;

extern const RemateKindInfo g_remate_kind_info[REMATE_NUM_KINDS];

extern const uint8_t g_remate_frame_bounds[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1][4];
extern const uint32_t g_remate_frame_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1];
extern const uint32_t g_remate_run_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES + 1];

extern const uint8_t g_remate_shadow_bounds[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES][4];
extern const uint32_t g_remate_shadow_offsets[REMATE_NUM_KINDS][2][REMATE_NUM_FRAMES];

extern const uint16_t g_remate_pixels[];
extern const uint16_t g_remate_runs[];
extern const uint8_t g_remate_shadow_masks[];

#endif
