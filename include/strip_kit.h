#ifndef STRIP_KIT_H
#define STRIP_KIT_H

#include <stdint.h>

// Art kit of the vertical strip (DESIGN.md 6.0): the v0.2 dungeon pieces (one neon accent,
// side walls, low pillars) baked by tools/bake_strip_kit.py into source/strip_kit.c.
// source/strip.c stamps these pieces into the RAM arena window at run time.
//
// Units: tiles are 8x8 px; collision cells are COLLISION_SCALE (4) px, 2 bits each with the
// same values as Arena.collision (0 free, 1 blocks bodies only, 3 blocks bodies and bullets).

#define STRIP_W_PX 512                       // world width, 2 screens (DESIGN.md 6.0)
#define STRIP_W_TILES (STRIP_W_PX / 8)       // 64
#define STRIP_W_CELLS (STRIP_W_PX / 4)       // 128

typedef struct {
    uint8_t w_tiles, h_tiles;     // size of the tile block
    uint8_t phase_row;            // the block's top row must satisfy row % floor_h_tiles == phase_row
    uint8_t foot_x, foot_y;       // collision footprint, in cells relative to the block's top-left
    uint8_t foot_w, foot_h;
    uint8_t foot_value;           // collision value written in the footprint (1: low pillar)
    const uint16_t *tiles;        // w_tiles * h_tiles ids, row-major; 0 = keep the floor tile below
} StripStamp;

typedef struct {
    const uint16_t *palette;      // 256 BGR555 entries, shared by floor and stamps
    const uint8_t (*tiles)[64];   // 8bpp tiles; id 0 is the blank tile
    uint16_t num_tiles;
    uint16_t floor_h_tiles;       // vertical period of the floor pattern, in tiles (divides 16)
    const uint16_t *floor_map;    // STRIP_W_TILES * floor_h_tiles ids, side walls included
    const uint8_t *floor_collision; // STRIP_W_CELLS * (floor_h_tiles * 2) cells, packed like
                                    // Arena.collision (4 cells per byte, low bits first)
    uint8_t num_stamps;
    const StripStamp *stamps;
} StripKit;

extern const StripKit g_strip_kit;

#endif // STRIP_KIT_H
