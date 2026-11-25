#ifndef STRIP_KIT_H
#define STRIP_KIT_H

#include <stdint.h>

// Cathedral strip art kit baked by tools/bake_cathedral_kit.py into source/strip_kit.c.
// source/strip.c stamps floor pieces into the RAM arena window at run time.
//
// Units: tiles are 8x8 px; collision cells are COLLISION_SCALE (4) px, 2 bits each with the
// same values as Arena.collision (0 free, 1 blocks bodies only, 2 low cover = blocks bodies, bullets pass, 3 blocks bodies and bullets).

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
    uint8_t x_cell, y_cell, length_cells; // blocked 4x4 ground cells relative to the stamp
} StripFootprintRun;

// Piece identity for the deterministic cathedral composer (source/strip.c). The baker emits it in
// every stamp; `--mode actual` emits STRIP_PIECE_NONE so the old random placement stays untouched.
// Keep these values in sync with PIECE_IDS in tools/bake_cathedral_kit.py (the parity test catches
// a mismatch: a wrong id makes the composer fail to find the stamp).
enum {
    STRIP_PIECE_NONE = 0,
    STRIP_PIECE_COLUMNA_ENTERA,
    STRIP_PIECE_BANCO_ENTERO,
    STRIP_PIECE_RELICARIO,
    STRIP_PIECE_VELA,
    STRIP_PIECE_LAPIDA_3X2_CRUZ,
    STRIP_PIECE_LAPIDA_3X2_CAB,
    STRIP_PIECE_LAPIDA_2X1_CRUZ,
    STRIP_PIECE_LAPIDA_2X1_CAB,
    STRIP_PIECE_BANCO_GRUPO4,
    STRIP_PIECE_SANTO,
    STRIP_PIECE_SACOS,
    STRIP_PIECE_VERJA,
    STRIP_PIECE_COLUMNA_ROTA,
    STRIP_PIECE_BANCO_GRUPO4_ROTO,
    STRIP_PIECE_SACOS_B,
    STRIP_PIECE_SACOS_REMATE,
    STRIP_PIECE_SACOS_REMATE_DER,
    STRIP_PIECE_ALAMBRE,
    STRIP_PIECE_SANTO_DER,
    STRIP_PIECE_BANCO_ROTO,
    STRIP_PIECE_BANCO_VOLCADO,
    STRIP_PIECE_CAPULLO,
    STRIP_PIECE_CEPO,
    STRIP_PIECE_LAPIDA_PIE,
    STRIP_PIECE_CANDELABRO_PIE,
    STRIP_PIECE_CALAVERAS_PILA,
    STRIP_PIECE_HUESOS_MONTON,
    STRIP_PIECE_RECLINATORIO,
    STRIP_PIECE_CATRE,
    STRIP_PIECE_BIOMBO,
    STRIP_PIECE_PALANGANA,
    STRIP_PIECE_OSARIO_ESTANTE,
    STRIP_PIECE_OSARIO_LADO,
    STRIP_PIECE_SARCOFAGO,
    STRIP_PIECE_BRASERO,
    STRIP_PIECE_COUNT
};

// Placeholders of the room furniture (salas ARPG). The kit does not bake them yet: the encounters
// composer falls back to an existing stamp (resolve_room_placeholder() in source/strip.c) while the
// identifiers stay stable, so the graphics can be swapped later without touching the room logic.
#define STRIP_PIECE_PUERTA 200          // upper door of every room, centred on its top line
#define STRIP_PIECE_COFRE_CERRADO 201   // chest, alternate rooms
#define STRIP_PIECE_COFRE_ABIERTO 202   // chest once opened
#define STRIP_PIECE_ALTAR 203           // travel altar, every third room
#define STRIP_PIECE_HUECO_IZQ 204       // occlusion of the south module of a left lateral opening (kit.hole_occ[0])
#define STRIP_PIECE_HUECO_DER 205       // same for the right one (kit.hole_occ[1])

typedef struct {
    uint8_t w_tiles, h_tiles;     // size of the tile block
    uint8_t phase_col, phase_row; // top-left tile coordinate modulo the 16x16 floor period
    uint8_t foot_anchor_y_px;     // local world Y of the footprint's lowest cell
    uint8_t foot_value;           // 0: decoration, 1: blocks bodies, 3: blocks bodies and bullets
    uint8_t piece_id;             // STRIP_PIECE_* (0 = none); fits the existing alignment padding
    const uint16_t *tiles;        // row-major tilemap entries; bits 10/11 are H/V flips, 0 keeps floor
    uint16_t num_foot_runs;
    const StripFootprintRun *foot_runs; // 4x4 ground-plane collision spans, one or more per row
    uint16_t num_depth_runs;
    const StripDepthRun *depth_runs; // relative runs; depth is added to the piece base world Y
} StripStamp;

typedef struct {
    const uint16_t *palette;      // 256 BGR555 entries, shared by floor and stamps
    const uint8_t (*tiles)[64];   // 8bpp tiles; id 0 is the blank tile
    uint16_t num_tiles;
    uint16_t map_h_tiles;         // vertical visual-map period, in tiles
    uint16_t floor_h_tiles;       // vertical period of the floor pattern, in tiles (divides 16)
    const uint16_t *floor_map;    // STRIP_W_TILES * map_h_tiles entries, including DS H/V flip bits
    const uint8_t *floor_collision; // STRIP_W_CELLS * (floor_h_tiles * 2) cells, packed like
                                    // Arena.collision (4 cells per byte, low bits first)
    uint8_t end_w_tiles, end_h_tiles; // back wall of a room: 32 x 19 tiles covering world x 128..384, base on its last row
    uint8_t hole_h_tiles;         // lateral opening (two modules removed): 3 x 33 tiles = 24 x 264 px, rows -24..239 from its first row (G0)
    const uint16_t *hole_map;     // the cut face (canto) of the north module, the void and the first rows of the south one; the right side is the H-flip
    const StripStamp *hole_occ;   // [0] left, [1] right: depth runs of the south module (no tiles) so the hero and the enemies hide behind it
    const uint16_t *end_map[2];   // [0] closed (all blind arches), [1] with the through arch in the centre; DS flip bits, 0 = the void
    uint8_t num_stamps;
    const StripStamp *stamps;
} StripKit;

extern const StripKit g_strip_kit;

#endif // STRIP_KIT_H
