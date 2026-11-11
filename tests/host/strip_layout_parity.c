// Host harness for tests/test_strip_layout_parity.py: dumps every placement the C cathedral
// composer makes, one per line as "band piece_id phase_col phase_row x_tile y_tile".
#include <stdio.h>

#include "arena.h"
#include "strip.h"

// strip.c assigns g_arena in strip_start(); the dump path never installs an arena, so a single
// definition is enough to satisfy the link without pulling in arena.c.
const Arena *g_arena = 0;

static void dump_placement(int32_t band, int piece_id, int phase_col, int phase_row,
                           int x_tile, int y_tile) {
    printf("%d %d %d %d %d %d\n", (int)band, piece_id, phase_col, phase_row, x_tile, y_tile);
}

int main(void) {
    g_strip_layout_dump = dump_placement;
    strip_layout_dump_bands(0xC0DE1234u, 64);
    return 0;
}
