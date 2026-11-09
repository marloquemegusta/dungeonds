#ifndef STRIP_KIT_H
#define STRIP_KIT_H

#include <stdint.h>

// Cathedral strip art kit baked by tools/bake_cathedral_kit.py into source/strip_kit.c.
// source/strip.c stamps floor pieces into the RAM arena window at run time.
//
// Units: tiles are 8x8 px; collision cells are COLLISION_SCALE (4) px, 2 bits each with the
// same values as Arena.collision (0 free, 1 blocks bodies only, 3 blocks bodies and bullets).

#define STRIP_W_PX 512                       // world width, 2 screens (DESIGN.md 6.0)
#define STRIP_W_TILES (STRIP_W_PX / 8)       // 64
#define STRIP_W_CELLS (STRIP_W_PX / 4)       // 128

typedef struct {
    uint8_t x_px;
    uint8_t y_px;
    uint8_t length;
    int16_t depth_delta;
} StripDepthRun;

typedef struct {
    uint8_t w_tiles, h_tiles;     // size of the tile block
    uint8_t phase_col, phase_row; // top-left tile coordinate modulo the 16x16 floor period
    uint8_t foot_x, foot_y;       // collision footprint, in cells relative to the block's top-left
    uint8_t foot_w, foot_h;
    uint8_t foot_value;           // 0: decoration, 1: blocks bodies, 3: blocks bodies and bullets
    const uint16_t *tiles;        // row-major tilemap entries; bits 10/11 are H/V flips, 0 keeps floor
    uint16_t num_depth_runs;
    const StripDepthRun *depth_runs; // relative runs; depth is added to the piece base world Y
} StripStamp;

typedef struct {
    const uint16_t *palette;      // 256 BGR555 entries, shared by floor and stamps
    const uint8_t (*tiles)[64];   // 8bpp tiles; id 0 is the blank tile
    uint16_t num_tiles;
    uint16_t floor_h_tiles;       // vertical period of the floor pattern, in tiles (divides 16)
    const uint16_t *floor_map;    // STRIP_W_TILES * floor_h_tiles entries, including DS H/V flip bits
    const uint8_t *floor_collision; // STRIP_W_CELLS * (floor_h_tiles * 2) cells, packed like
                                    // Arena.collision (4 cells per byte, low bits first)
    uint8_t num_stamps;
    const StripStamp *stamps;
} StripKit;

extern const StripKit g_strip_kit;

#endif // STRIP_KIT_H
