#ifndef RADIAL_H
#define RADIAL_H

// Spell radial menu (L held). It opens out of the active-spell viril at the bottom of the touch
// screen and the stylus picks one of the available spells. The game never pauses; while it is
// open the stylus is consumed here and never reaches the weapons or the curse.

#include <stdint.h>

int  radial_is_open(void);
// Opens the radial around the bottom HUD icon. Returns 1 if it opened (two or more spells
// available), 0 if there is nothing to choose (a single spell) so the caller does nothing.
int  radial_begin(void);
void radial_close(void);
// Hit-tests the stylus point against the entries. Returns the chosen spell id (ARPG_SPELL_*:
// 0 Rayo, 1 Glifo, 2 Levantar), or -1 when the point is outside every entry (the radial stays open).
int  radial_touch(int tx, int ty);
// Draws the dark frame and the entries over the bottom page. Cost is zero while closed.
void radial_render(uint16_t *buffer);

#endif
