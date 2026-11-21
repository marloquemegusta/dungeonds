#ifndef CAMP_FLOOR_LIGHT_H
#define CAMP_FLOOR_LIGHT_H

// Bonfire flicker of the baked camp floor (DESIGN.md 7.5). The floor/wall light is baked in bands by
// tools/camp/bake_camp_arena.py; the warm bands are one contiguous block of palette entries, and this
// rewrites that block (both engines) with one of CAMP_LIGHT_FLICKER_STEPS pre-baked brightness variants.
// No float: the step sequence is a small table indexed by the frame counter.

// Forget the current step. Call after apply_arena_palette() loads the camp palette (enter_camp_scene).
void camp_floor_light_reset(void);

// Call once per frame in the camp loop with any increasing counter (vblank count). It only touches the
// palette when the step changes (about every 4 frames).
void camp_floor_light_tick(int frame);

#endif
