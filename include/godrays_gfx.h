#ifndef GODRAYS_GFX_H
#define GODRAYS_GFX_H
#include <stdint.h>
typedef struct { uint8_t ray, width, height; int16_t x, y; uint16_t tile_offset; } GodrayPiece;
typedef struct { uint16_t first_piece, piece_count; } GodrayRange;
#define GODRAY_RAY_COUNT 2
#define GODRAY_PIECE_COUNT 88
#define GODRAY_TILE_BYTES 11328
#define GODRAY_DUST_OFFSET 11264
extern const uint8_t g_godray_tiles[GODRAY_TILE_BYTES];
extern const uint16_t g_godray_palettes[48];
extern const GodrayPiece g_godray_pieces[GODRAY_PIECE_COUNT];
extern const GodrayRange g_godray_ranges[GODRAY_RAY_COUNT];
#endif

