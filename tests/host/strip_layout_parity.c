// Host harness for tests/test_strip_layout_parity.py. It prints:
//   PLAN <block> <piece_id> <phase_col> <phase_row> <x_tile> <y_block>   one line per planned piece
//   MAP <tag> <row> v0 .. v63                                              window tiles (256 rows)
//   COL <tag> <row> v0 .. v127                                             window collision cells (512 rows)
// tag W0 is the window after strip_start(); W1 is the same window after one rebase.
#include <stdio.h>

#include "arena.h"
#include "strip.h"

// strip.c assigns g_arena in strip_start(); the dump path never installs an arena, so a single
// definition is enough to satisfy the link without pulling in arena.c.
const Arena *g_arena = 0;

#define PARITY_SEED 0xC0DE1234u

static void dump_piece(int32_t block, int piece_id, int phase_col, int phase_row,
                       int x_tile, int y_block) {
    printf("PLAN %d %d %d %d %d %d\n", (int)block, piece_id, phase_col, phase_row, x_tile, y_block);
}

static void print_window(const char *tag) {
    const uint16_t *map = strip_layout_map();
    const uint8_t *collision = strip_layout_collision();
    for (int row = 0; row < STRIP_WIN_H_PX / 8; row++) {
        printf("MAP %s %d", tag, row);
        for (int x = 0; x < 64; x++) printf(" %u", (unsigned)map[row * 64 + x]);
        printf("\n");
    }
    for (int row = 0; row < STRIP_WIN_H_PX / 4; row++) {
        printf("COL %s %d", tag, row);
        for (int x = 0; x < 128; x++) {
            unsigned value = ((unsigned)collision[row * 32 + (x >> 2)] >> ((x & 3) * 2)) & 3u;
            printf(" %u", value);
        }
        printf("\n");
    }
}

// Occlusion accessors exported by strip.c under STRIP_LAYOUT_DUMP (kept out of strip.h on purpose).
const DungeonOcclusionRun *strip_layout_occlusion(uint32_t *count);
const uint32_t *strip_layout_occlusion_row_start(void);

// Occlusion runs of the window in array order, then the row index (window_h + 1 entries).
static void print_occlusion(const char *tag) {
    uint32_t count = 0;
    const DungeonOcclusionRun *runs = strip_layout_occlusion(&count);
    printf("OCCN %s %u\n", tag, (unsigned)count);
    for (uint32_t i = 0; i < count; i++) {
        printf("OCC %s %u %u %u %u %d\n", tag, (unsigned)i, (unsigned)runs[i].x,
               (unsigned)runs[i].y, (unsigned)runs[i].length, (int)runs[i].depth);
    }
    const uint32_t *row_start = strip_layout_occlusion_row_start();
    for (int y = 0; y <= STRIP_WIN_H_PX; y++) printf("ROW %s %d %u\n", tag, y, (unsigned)row_start[y]);
}

int main(void) {
    g_strip_layout_dump = dump_piece;
    strip_layout_dump_blocks(PARITY_SEED, -16, 22);
    g_strip_layout_dump = 0;
    strip_start(PARITY_SEED);
    print_window("W0");
    print_occlusion("W0");
    if (strip_rebase_if_needed(STRIP_REBASE_TOP_PX - 1) != STRIP_SHIFT_PX) {
        printf("REBASE_FAILED\n");
        return 1;
    }
    print_window("W1");
    print_occlusion("W1");
    return 0;
}
