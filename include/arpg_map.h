#ifndef ARPG_MAP_H
#define ARPG_MAP_H

#include <stdint.h>

// Overlay map of the zone (SELECT, ARPG build): isometric outline of the rooms already visited, painted over the upper screen
// without pausing the game. Only the contours are drawn (chalk lines on whatever is below), so nothing costs while it is closed.
void arpg_map_toggle(void);
int  arpg_map_is_open(void);
// Paints the map into the upper actor page (call right after render_screen of that page, with g_dirty_cur = its spans, so the
// next render_screen clears it). px, py: hero ground point in window px. frame: any increasing counter (blinks the hero).
// in_camp: the map is opened from the camp (no hero dot, no room becomes "seen").
// The map shows only the rooms already visited (and Nave 1, the way out of the camp), plus the mark of the current objective
// (arpg_campaign_objectives) floating where its room is even if it was never visited, and one mission line per objective.
void arpg_map_draw(uint16_t *page, int px, int py, int frame, int in_camp);

#endif
