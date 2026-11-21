#include "camp_floor_light.h"
#include "camp_arena_data.h"
#include <nds.h>

#define FLICKER_FRAMES_SHIFT 2          // a step lasts 4 frames
#define FLICKER_SEQ_LEN 16

// Irregular fire pulse over the baked steps (0 = palette as baked, 1 = dim, 2 = bright, 3 = soft dim).
static const uint8_t k_seq[FLICKER_SEQ_LEN] = { 0, 2, 0, 1, 3, 2, 0, 0, 1, 3, 0, 2, 2, 0, 3, 1 };

static int s_step = -1;

void camp_floor_light_reset(void) {
    s_step = -1;
}

void camp_floor_light_tick(int frame) {
    int step = k_seq[(frame >> FLICKER_FRAMES_SHIFT) & (FLICKER_SEQ_LEN - 1)];
    if (step >= CAMP_LIGHT_FLICKER_STEPS) step = 0;
    if (step == s_step) return;
    s_step = step;
    const uint16_t *src = g_camp_flicker[step];
    const uint32_t bytes = CAMP_LIGHT_WARM_COUNT * 2;
    dmaCopyHalfWords(3, src, BG_PALETTE + CAMP_LIGHT_WARM_FIRST, bytes);
    dmaCopyHalfWords(3, src, BG_PALETTE_SUB + CAMP_LIGHT_WARM_FIRST, bytes);
}
