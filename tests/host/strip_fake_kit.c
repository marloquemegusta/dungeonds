#include "arena.h"
#include "strip_kit.h"

static const uint16_t s_palette[256] = {0};
static const uint8_t s_tiles[4][64] = {{0}};
static uint16_t s_floor_map[STRIP_W_TILES * 4];
static uint8_t s_floor_collision[STRIP_W_CELLS * 8 / 4];
static const uint16_t s_stamp_tiles_a[4] = {3, 3, 3, 3};
static const uint16_t s_stamp_tiles_b[4] = {2, 3, 3, 2};
static const StripFootprintRun s_stamp_foot_a[2] = {{0, 0, 4}, {0, 1, 4}};
static const StripFootprintRun s_stamp_foot_b[2] = {{0, 0, 4}, {0, 1, 4}};
// Synthetic stamps tagged as the two left-hand colonnade variants, on the phases the composer
// asks for. They sit at x_tile 8 (px 64..80), far from the x=256 center lane the nav test walks,
// and their per-band state depends on the seed, so the seed-difference assertions still hold.
static const StripStamp s_stamps[2] = {
    {2, 2, 8, 0, 4, 1, STRIP_PIECE_COLUMNA_ENTERA, s_stamp_tiles_a, 2, s_stamp_foot_a, 0, 0},
    {2, 2, 8, 8, 4, 1, STRIP_PIECE_COLUMNA, s_stamp_tiles_b, 2, s_stamp_foot_b, 0, 0}
};

const StripKit g_strip_kit = {
    .palette = s_palette,
    .tiles = s_tiles,
    .num_tiles = 4,
    .map_h_tiles = 4,
    .floor_h_tiles = 4,
    .floor_map = s_floor_map,
    .floor_collision = s_floor_collision,
    .num_stamps = 2,
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
