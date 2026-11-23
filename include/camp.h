#ifndef CAMP_H
#define CAMP_H

#include <stdint.h>
#include "game.h"
#include "arena.h"

// The camp scene only exists in the ARPG build (ENCOUNTERS_PROTO); other variants keep the old flow.
#define CAMP_SCENE (ENCOUNTERS_PROTO)

// The camp is its own playable room (DESIGN.md: the claustro). One screen wide and two screens tall,
// shown whole across both DS screens. The floor is the cathedral floor recoloured (paler, colder,
// greenish stone), the walls are the cathedral walls; the props are drawn as software sprites
// over that floor (the strip kit is full, so nothing is baked into it).

#define CAMP_CAM_Y 192          // fixed camera: top screen shows rows 0..192, bottom 192..384
#define CAMP_START_X 128        // hero appears beside the bonfire (its name shows at once)
#define CAMP_START_Y 322

// Action a prop triggers when the hero is next to it and touches it (or presses A).
enum { CAMP_ACT_NONE = 0, CAMP_ACT_SLEEP, CAMP_ACT_INVENTORY, CAMP_ACT_CODEX, CAMP_ACT_DOOR };

#if CAMP_SCENE
const Arena *camp_arena(void);   // the static camp room (built once on first call)
void camp_unload_gfx(void);      // frees camp graphics when leaving for the dungeon
int  camp_active(void);
void camp_set_active(int on);

// Movement, prop focus and interaction. Returns a CAMP_ACT_* to be handled by the caller.
int camp_update(Player *p, uint32_t keys_held, uint32_t keys_down, int touch_pressed, int touch_x, int touch_y);

// A short line shown in the middle of the camp (e.g. the result of sleeping).
void camp_toast(const char *msg);

// Render hooks called from render_screen.
void camp_render_floor(uint16_t *buffer, int cam_x, int cam_y);   // bonfire glow, under the actors
void camp_clear_page(uint16_t *page, DirtySpan *spans, int cam_x, int cam_y);  // clears the dirty spans, keeping the wall frame
void camp_invalidate_pages(void);                                 // a page was wiped: re-prime the wall frame
void camp_render_overlay(uint16_t *buffer, int cam_x, int cam_y); // prop name + hint + toast
int  camp_items_count(int cam_x, int cam_y);                      // props visible on this screen
int  camp_item_depth(int index);
void camp_item_draw(int index, uint16_t *buffer, int cam_x, int cam_y, int depth);

// Baked ground shadow of a visible prop, on its own canvas (1 bpp). Fills the mask pointer,
// its bounds {0, 0, w, h} and the canvas top-left in world pixels. Returns 0 when the piece has none.
int  camp_item_shadow(int index, const uint8_t **mask, uint8_t *bounds, int *left, int *top);
#else
// Not the ARPG build: the camp scene never runs (keeps call sites simple).
static inline int camp_active(void) { return 0; }
static inline void camp_set_active(int on) { (void)on; }
static inline void camp_invalidate_pages(void) {}
#endif

#endif // CAMP_H
