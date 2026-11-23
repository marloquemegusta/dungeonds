#ifndef STREAM_CHAR_H
#define STREAM_CHAR_H

// Streamed character slots: sheets too big for the fixed RAM (TECHNICAL.md) stay in NitroFS and their frames are
// read on demand into one shared LRU cache. Slots today: the Párroco running (CHAR_EXVOTO_PARROCO_RUN, 48x48) and the
// four clips of the Súper Monja (CHAR_SMONJA_*, 56x56) and the four spider-form clips of the possessed Exvoto and
// Monaguillo (CHAR_EXVOTO_ARANA_*, CHAR_MONAGUILLO_ARANA_*; nitrofiles/arana/). The character_*_ptr accessors (player_sprite.h) call
// stream_char_ensure() for any slot >= CHAR_FIRST_STREAMED. Files are written by tools/generate_player_sprites_c.py.

#define STREAM_CACHE_SLOTS 16        // cached frames shared by all streamed slots (16 x 6 KB = 96 KB of RAM)
#define STREAM_SLOT_BYTES 6144       // >= the largest record of any file (5876 bytes today, the Súper Monja walk at 64 px; the generator prints it)

// Opens the files and wires the character tables of every streamed slot that loaded; sets g_parroco_run_ok and
// g_smonja_ok (1 only when all four of her clips loaded). Needs nitroFSInit (done by sfx_init).
void stream_char_init(void);

#endif
