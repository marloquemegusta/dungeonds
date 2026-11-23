#ifndef CHARS_POOL_H
#define CHARS_POOL_H

#include <stdint.h>
#include "player_sprite.h"

// Enemy art of the room (see room_pool.h). The frames, runs and shadow masks of every enemy clip are NitroFS bins
// (nitrofiles/chars/<clip>.bin, tools/generate_player_sprites_c.py); a loading screen empties the room pool and loads
// only the groups the room can show. Until a group is loaded its pointers are NULL: draw code asks chars_ready() first.
//
// Groups (CG_*): Exvoto (walk, praying clips, Bebe: also Parroco and Monja), Ojo (walk, look, sentence), Cargador
// (walk, charge, telegraph), Abanderado (walk, point), Monaguillo.

extern volatile uint32_t g_pool_misses;     // groups that had to be loaded outside the room load (a stutter): 0 is the goal
extern uint32_t g_chars_loaded;             // bit per CG_* group now in the pool
extern const int8_t g_char_group[NUM_CHARACTERS];   // CG_* of each CHAR_*, -1 = resident art (hero, Campanero)

// Loads a group into the pool (1 = ready). All or nothing: when it does not fit, nothing of it stays.
int chars_load_group(int group);
// The same by enemy type (EnemyType, gameplay.h); types without streamed art are always ready.
int chars_load_type(int enemy_type);
// Forgets every group (pointers to NULL). room_pool_reset() must follow (room_art_prepare does both).
void chars_unload_all(void);
// Bytes the files of a group take in the pool (for budgeting).
uint32_t chars_group_bytes(int group);

int chars_demand(int char_id);              // slow path of chars_ready: counts a miss and loads the group now

// 1 when the art of this character can be read now. Loads it on the spot when the room did not (a miss, g_pool_misses);
// 0 when it does not fit: the caller must not draw it (never dereference the pointers then).
static inline int chars_ready(int char_id) {
    const int g = g_char_group[char_id];
    if (g < 0 || ((g_chars_loaded >> g) & 1u)) return 1;
    return chars_demand(char_id);
}

// Loading screen: empties the pool and loads the groups in `group_mask` (bit per CG_*) and, if asked, the Campanero
// (campanero_sprite.h). Enemies first, so the Campanero takes what is left (whole file, or the streaming fallback).
void room_art_prepare(uint32_t group_mask, int campanero);

#endif
