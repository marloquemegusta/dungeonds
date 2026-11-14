#ifndef GROUNDFX_H
#define GROUNDFX_H

#include <stdint.h>
#include "game.h"

// Ground-plane effects (DESIGN.md 4.9). PERSPECTIVE RULE: ground distance is sqrt(dx^2 + 4*dy^2)
// (GROUND_DY2 in collision.h), so a circle of ground radius R is an ELLIPSE of half-width R and
// half-height R/2 on screen. Every shape here takes ground coordinates (world px of the feet) and
// a ground radius, and derives the 2:1 ellipse itself, so callers cannot draw a screen-space circle.
//
// Two passes per screen (render_screen in main.c):
//   floor pass  - before the shadows and sprites: decals painted on the floor, under the actors;
//   light pass  - after the sprites: lights actors that stand in a beam.
// Both write BGR555 | BIT(15) into the actor page, call dirty_row() for every span they write, clip
// to the screen and skip pixels hidden by a wall in front (world_pixel_hidden, depth = world y).

typedef struct {
    uint16_t *buffer;    // actor page of the screen being drawn
    int cam_x, cam_y;    // camera of that screen
} GroundTarget;

// Wall test used by the decals: non-zero when a wall run hides the pixel (main.c).
int world_pixel_hidden(int x, int y, int depth);
// Non-zero when a wall run hides any pixel of world row y in [x0, x1) (one lookup per span).
int world_span_hidden(int y, int x0, int x1, int depth);

// Fill patterns for gfx_ground_disc. `phase` slides the pattern (animation), any integer.
enum { GFX_FILL_SOLID = 0, GFX_FILL_CHECKER, GFX_FILL_HATCH };

// One pixel at ground point (wx, wy). `color` is BGR555 without the alpha bit.
void gfx_ground_px(const GroundTarget *g, int wx, int wy, uint16_t color);

// One-pixel line between two world points (already in the 2:1 world: a ground vector must have its y
// halved by the caller). `dash` as in gfx_ground_ring. At most max(|dx|, |dy|) + 1 pixels.
void gfx_ground_line(const GroundTarget *g, int x0, int y0, int x1, int y1, uint16_t color, int dash);

// One-pixel ellipse outline. `dash`: 0 = continuous, otherwise draw an arc step only when
// (step / dash) is even (step = one outline pixel along the perimeter).
void gfx_ground_ring(const GroundTarget *g, int cx, int cy, int radius, uint16_t color, int dash);

// Ellipse outline limited to the angular window [a0, a1) in 1/32 turns (0 = east, 8 = south in
// screen terms), `thickness` rings deep (inwards). Used for shock arcs and gapped shock rings.
void gfx_ground_arc(const GroundTarget *g, int cx, int cy, int radius, int a0, int a1,
                    uint16_t color, int thickness);

// Filled ellipse. HATCH draws diagonal stripes that follow the iso ground (stripe period 4 px).
void gfx_ground_disc(const GroundTarget *g, int cx, int cy, int radius, uint16_t color,
                     int pattern, int phase);

// Lights the opaque pixels (actors) inside a beam: a cylinder of ground radius `radius` standing
// on ground point (cx, cy), `height` px tall. Each colour channel gains `level` (0..31, saturating)
// and the red channel gains `red_boost` more. Pixels equal to `skip_a` or `skip_b` (the decals
// drawn by the floor pass, BGR555 | BIT(15)) are left alone. Transparent pixels are never touched.
void gfx_light_column(const GroundTarget *g, int cx, int cy, int radius, int height,
                      int level, int red_boost, uint16_t skip_a, uint16_t skip_b);

#endif // GROUNDFX_H
