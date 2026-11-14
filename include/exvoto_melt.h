#ifndef EXVOTO_MELT_H
#define EXVOTO_MELT_H

#include <stdint.h>
#include "game.h"
#include "groundfx.h"
#include "gameplay.h"

// Death of an Exvoto (DESIGN.md 6.10, "se derrite"): no 3D animation. The sprite sinks into the floor for
// EXVOTO_MELT_SINK_FRAMES while a wax puddle (2:1 ellipse, light with a dark rim, desaturated) spreads under
// it; the puddle then lasts EXVOTO_MELT_POOL_FRAMES in all, fades out (dithered, then shrinking) and does
// nothing. The pool is small and fixed: the cost per frame is bounded by EXVOTO_MELT_MAX discs per screen.
#define EXVOTO_MELT_MAX 8              // [TUNABLE-PLACEHOLDER] melting Exvotos at once (the oldest is replaced)
#define EXVOTO_MELT_SINK_FRAMES 20     // [TUNABLE-PLACEHOLDER] frames the sprite takes to sink away
#define EXVOTO_MELT_POOL_FRAMES 90     // [TUNABLE-PLACEHOLDER] frames the puddle lasts, fade included
#define EXVOTO_MELT_FADE_START 55      // [TUNABLE-PLACEHOLDER] age at which the puddle starts to fade (dither, then shrink)
#define EXVOTO_MELT_SHRINK_START 72    // [TUNABLE-PLACEHOLDER] age at which the faded puddle starts to shrink
#define EXVOTO_MELT_RADIUS 13          // [TUNABLE-PLACEHOLDER] ground radius px of the full puddle

typedef struct {
    fixed x, y;            // feet, world fixed point
    int age;               // frames since the death; < 0 = free slot
    int char_id, dir, frame;   // the sprite it was drawn with when it died
    uint32_t seed;         // deterministic shape/texture variation per puddle
} ExvotoMelt;

void exvoto_melt_reset(void);
// Starts the melt of a dying Exvoto (called from the death hook).
void exvoto_melt_spawn(const Enemy *e);
// One simulated frame.
void exvoto_melt_update(void);
// World moved down by dy_px (strip rebase).
void exvoto_melt_shift_y(int dy_px);
// Slot i if it is still sinking (age < EXVOTO_MELT_SINK_FRAMES), else NULL: what the sprite pass draws.
const ExvotoMelt *exvoto_melt_sinking(int i);
// Rows of the sprite already under the floor: 0..bh.
int exvoto_melt_hidden_rows(const ExvotoMelt *m, int bh);
// Floor pass: draws every live puddle (before the shadows and sprites).
void exvoto_melt_render_floor(const GroundTarget *g);

#endif // EXVOTO_MELT_H
