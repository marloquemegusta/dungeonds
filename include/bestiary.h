#ifndef BESTIARY_H
#define BESTIARY_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t active;
    uint32_t entry_index;
    uint32_t frame_count;
    uint32_t trigger;
} BestiaryDebugState;

extern volatile BestiaryDebugState g_bestiary_debug;

/* Runs the bestiary UI loop until the user exits with 'B' or touch 'Volver'.
 * top_page: 256x192 16bpp framebuffer for the top screen (sub engine bitmap).
 * bot_page_a: 256x192 16bpp framebuffer for lower screen page A (e.g. page 8).
 * bot_page_b: 256x192 16bpp framebuffer for lower screen page B (e.g. page 24).
 * bot_active_page_idx: pointer to currently active lower page index (8 or 24).
 * vblank_flip_fn: function called to wait for VBlank and flip lower screen page,
 *                 or NULL to use swiWaitForVBlank directly.
 */
void bestiary_run(uint16_t *top_page, uint16_t *bot_page_a, uint16_t *bot_page_b,
                  int *bot_active_page_idx, void (*vblank_flip_fn)(void));

#ifdef __cplusplus
}
#endif

#endif /* BESTIARY_H */
