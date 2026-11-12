#include "arena.h"
#include "strip_kit.h"

static const uint16_t s_palette[256] = {0};
static const uint8_t s_tiles[4][64] = {{0}};
static uint16_t s_floor_map[STRIP_W_TILES * 4];
static uint8_t s_floor_collision[STRIP_W_CELLS * 8 / 4];
static const uint16_t s_stamp_tiles_col[4] = {3, 3, 3, 3};
static const uint16_t s_stamp_tiles_rel[4] = {2, 2, 2, 2};
static const uint16_t s_stamp_tiles_bank[16] = {3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3};
static const StripFootprintRun s_stamp_foot_col[2] = {{0, 0, 4}, {0, 1, 4}};
static const StripFootprintRun s_stamp_foot_bank[4] = {{0, 0, 8}, {0, 1, 8}, {0, 2, 8}, {0, 3, 8}};
// Synthetic stamps at the phases the composer asks for (strip.c plan_block): columns at x_tile 7 and
// 51 on rows 9 and 1 (phases (7,9), (7,1), (3,9), (3,1)); relicario at x_tile 28 (phase col 12);
// benches at x_tile 16/19 and 35 (phase cols 0 and 3) on rows 0 and 8. Sizes are small so they
// stay clear of the x=256 center lane (tile 32) that the nav test walks. Bench and relicario
// choices depend on the seed, so different seeds still produce different content.
static const StripStamp s_stamps[] = {
    {2, 2, 7, 9, 4, 1, STRIP_PIECE_COLUMNA_ENTERA, s_stamp_tiles_col, 2, s_stamp_foot_col, 0, 0},
    {2, 2, 7, 1, 4, 1, STRIP_PIECE_COLUMNA_ENTERA, s_stamp_tiles_col, 2, s_stamp_foot_col, 0, 0},
    {2, 2, 3, 9, 4, 1, STRIP_PIECE_COLUMNA_ENTERA, s_stamp_tiles_col, 2, s_stamp_foot_col, 0, 0},
    {2, 2, 3, 1, 4, 1, STRIP_PIECE_COLUMNA_ENTERA, s_stamp_tiles_col, 2, s_stamp_foot_col, 0, 0},
    {2, 2, 12, 9, 2, 3, STRIP_PIECE_RELICARIO, s_stamp_tiles_rel, 0, 0, 0, 0},
    {2, 2, 12, 1, 2, 3, STRIP_PIECE_RELICARIO, s_stamp_tiles_rel, 0, 0, 0, 0},
    {4, 4, 0, 0, 4, 1, STRIP_PIECE_BANCO_GRUPO4, s_stamp_tiles_bank, 4, s_stamp_foot_bank, 0, 0},
    {4, 4, 0, 8, 4, 1, STRIP_PIECE_BANCO_GRUPO4, s_stamp_tiles_bank, 4, s_stamp_foot_bank, 0, 0},
    {4, 4, 3, 0, 4, 1, STRIP_PIECE_BANCO_GRUPO4, s_stamp_tiles_bank, 4, s_stamp_foot_bank, 0, 0},
    {4, 4, 3, 8, 4, 1, STRIP_PIECE_BANCO_GRUPO4, s_stamp_tiles_bank, 4, s_stamp_foot_bank, 0, 0}
};

const StripKit g_strip_kit = {
    .palette = s_palette,
    .tiles = s_tiles,
    .num_tiles = 4,
    .map_h_tiles = 4,
    .floor_h_tiles = 4,
    .floor_map = s_floor_map,
    .floor_collision = s_floor_collision,
    .num_stamps = 10,
    .stamps = s_stamps
};

const Arena *const g_arenas[] = {0};
const int g_num_arenas = 0;

// Initialize the synthetic periodic floor before host tests start.
__attribute__((constructor)) static void init_fake_floor(void) {
    for (unsigned row = 0; row < 4; row++) {
        for (unsigned x = 0; x < STRIP_W_TILES; x++)
            s_floor_map[row * STRIP_W_TILES + x] = (uint16_t)((x == 0 || x == STRIP_W_TILES - 1) ? 1 : 2);
    }
    for (unsigned row = 0; row < 8; row++) {
        for (unsigned x = 0; x < STRIP_W_CELLS; x++) {
            unsigned index = row * STRIP_W_CELLS + x;
            unsigned value = (x == 0 || x == STRIP_W_CELLS - 1) ? 3 : 0;
            s_floor_collision[index >> 2] |= (uint8_t)(value << ((index & 3u) * 2u));
        }
    }
}
