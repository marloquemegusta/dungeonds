#ifndef STRIP_REBASE_REF_H
#define STRIP_REBASE_REF_H

#include <stdint.h>
#include "arena.h"

// Reference copy of the strip rebase (tests/host/strip_rebase_ref.c): state view for the
// equivalence harness. Read-only, host only.
typedef struct {
    const uint16_t *map;
    const uint8_t *collision;
    const DungeonOcclusionRun *runs;
    uint32_t run_count;
    const uint32_t *row_start;
    int32_t next_band;
    int32_t shift_total_px;
} StripStateView;

void ref_strip_start(uint32_t seed);
int ref_strip_rebase_if_needed(int player_y_px);
const Arena *ref_strip_arena(void);
void ref_strip_state_view(StripStateView *view);

#endif // STRIP_REBASE_REF_H
