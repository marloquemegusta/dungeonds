#ifndef STRIP_H
#define STRIP_H

#include <stdint.h>
#include "arena.h"

#define STRIP_WIN_H_PX 2048
#define STRIP_BAND_PX 128
#define STRIP_SHIFT_PX 768
#define STRIP_REBASE_TOP_PX 768
#define STRIP_PIXELS_PER_METER_100X 4042 // [TUNABLE-PLACEHOLDER] projected pixels per meter, hundredths (40.42)
// strip_prepare_step() builds the next rebase while player_y < STRIP_REBASE_TOP_PX + this margin.
#define STRIP_PREPARE_MARGIN_PX 512

void strip_start(uint32_t seed);
// One bounded unit of work toward the next rebase. Call once per frame, before strip_rebase_if_needed.
void strip_prepare_step(int player_y_px);
int strip_rebase_if_needed(int player_y_px);
// Staging of the next window for nav_stage_step(): while strip_stage_enter() returns 1 the Arena
// reads the final collision rows 0..191 of the next window (call strip_stage_leave() right after).
// strip_stage_id() changes whenever a preparation begins, so a staged result can be told stale.
uint32_t strip_stage_id(void);
int strip_stage_enter(void);
void strip_stage_leave(void);
int32_t strip_shift_total_px(void);
int strip_start_x(void);
int strip_start_y(void);
int strip_height_m(int player_y_px);
int strip_lane_center_px(int32_t band);
const Arena *strip_arena(void);

#if STRIP_LAYOUT_DUMP
// Host-only parity harness (tests/test_strip_layout_parity.py). The sink receives every planned piece
// of a block in emission order; strip_layout_dump_blocks() walks blocks without touching the arena.
// strip_layout_map() / strip_layout_collision() expose the window after strip_start() or a rebase.
extern void (*g_strip_layout_dump)(int32_t block, int piece_id, int phase_col, int phase_row,
                                   int x_tile, int y_block);
void strip_layout_dump_blocks(uint32_t seed, int32_t first_block, int num_blocks);
const uint16_t *strip_layout_map(void);
const uint8_t *strip_layout_collision(void);
#endif

#endif // STRIP_H
