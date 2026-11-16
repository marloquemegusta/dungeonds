#ifndef LEVELUP_CARDS_H
#define LEVELUP_CARDS_H

#include <stdint.h>

// Level-up card art (DESIGN.md 6.12.8): 76x76, 16-frame loops captured from the game itself by
// tools/levelup_cards/capture_cards.py into nitro:/levelup/<id>.bin and loaded on demand for the 3 offered cards only
// (3 x ~91 KB, freed on close).
#define LVC_SIZE   76
#define LVC_FRAMES 16

// Loads the art of slot 0..2. art_id NULL (the heal) or a missing file leaves the slot empty (lvcards_loaded() == 0).
void lvcards_load(int slot, const char *art_id);
void lvcards_free(void);
int lvcards_loaded(int slot);

// Draws frame `frame` (0..15) with its top-left corner at (x, y). dim 0 = full colour, 1 = darker (unselected card).
void lvcards_draw(uint16_t *buf, int slot, int x, int y, int frame, int dim);

#endif // LEVELUP_CARDS_H
