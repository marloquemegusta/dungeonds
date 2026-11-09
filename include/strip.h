#ifndef STRIP_H
#define STRIP_H

#include <stdint.h>
#include "arena.h"

#define STRIP_WIN_H_PX 2048
#define STRIP_BAND_PX 128
#define STRIP_SHIFT_PX 512
#define STRIP_REBASE_TOP_PX 768
#define STRIP_PIXELS_PER_METER_100X 4042 // [TUNABLE-PLACEHOLDER] projected pixels per meter, hundredths (40.42)

void strip_start(uint32_t seed);
int strip_rebase_if_needed(int player_y_px);
int32_t strip_shift_total_px(void);
int strip_start_x(void);
int strip_start_y(void);
int strip_height_m(int player_y_px);
int strip_lane_center_px(int32_t band);
const Arena *strip_arena(void);

#if LAPIDA_DEBUG
// Debug-only ("lapidas" build variant): scenario-poked marine world position (x, y); -1 = off.
extern int32_t g_strip_debug_pos[2];
#endif

#endif // STRIP_H
