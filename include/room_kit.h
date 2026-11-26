#ifndef ROOM_KIT_H
#define ROOM_KIT_H

#include <stdint.h>

// Per-room art of the cathedral (salas ARPG). The base kit (source/strip_kit.c: floor, walls, doors, the corridor props and the
// lapidas) is always resident; the props that only one room uses live in nitrofiles/rooms/sala_NN.rmk, baked by
// tools/bake_cathedral_kit.py (format in the comment of `RoomTiles` there and in TECHNICAL.md 3.3.1). The loading screen
// calls room_kit_load() once the room pool holds the room's enemy art: the tiles go to the free slots of the kit's tile store and
// the stamps to the room pool, and the composer finds them next to the kit's own (strip_set_room_stamps).
//
// The file also has a slot for a palette of its own (flag bit 0, n_pal x BGR555): room_kit_palette() returns it, or NULL. Nothing
// applies it yet; the per-room light will.

#define RMK_MAGIC 0x314b4d52u   // "RMK1"

// Loads sala_NN.rmk (room index 0..15). Returns the number of stamps (0 if the room has no file, it does not fit or is invalid:
// the room then shows only the base kit). Call after room_art_prepare() and before the strip is composed.
int room_kit_load(int room);

// Room palette of the loaded file (256 BGR555 entries) or NULL.
const uint16_t *room_kit_palette(void);

// Figures for the budget table: tiles taken, bytes read from the file.
int room_kit_tiles(void);
uint32_t room_kit_bytes(void);

#endif
