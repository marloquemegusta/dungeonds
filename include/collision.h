#ifndef COLLISION_MODULE_H
#define COLLISION_MODULE_H

#include "game.h"

// The map is a 2:1 dimetric projection (30 deg elevation): one ground unit along
// screen Y covers half the pixels of one along X. Simulation distances and speeds
// are isotropic on the ground; GROUND_DY2(dy) is (2*dy)^2, the screen dy squared
// in ground units.
#define GROUND_Y_SHIFT 1
#define GROUND_DY2(dy) ((dy) * (dy) * 4)

// Body footprint test (a circle on the ground) against the baked collision grid.
int position_is_free(fixed x, fixed y);
// Point test for projectiles: only grid value 3 stops them (value 2, low cover, lets them pass over).
int bullet_position_is_free(fixed x, fixed y);
// Moves (x, y) by (dx, dy) in <=1 px steps; returns 0 and leaves it unchanged if blocked.
int sweep_position(fixed *x, fixed *y, fixed dx, fixed dy);

// True when a body can walk the straight line between two world points: samples the body
// footprint every few px (endpoints excluded). Line of sight alone misses low walls.
int line_is_walkable(int x0, int y0, int x1, int y1);

// True when nothing that stops bullets lies on the straight line (endpoints excluded).
int bullet_line_is_free(int x0, int y0, int x1, int y1);

// Low cover (grid value 2): true when a cell of value 2 lies within `reach` px of the body footprint at ground
// point (wx, wy), in world px (same units as position_is_free).
int low_cover_near(int wx, int wy, int reach);
// Low cover on the side the input (ix, iy: -1, 0 or 1 per axis, screen space) pushes toward, within the same reach.
int low_cover_toward(int wx, int wy, int reach, int ix, int iy);
// Bench test start: the low-cover cell nearest (from_x, from_y) with a free ground point just below it that hugs it
// within `reach`. Returns 1 and writes the point (world px, feet), or 0 when the arena has no such spot.
int low_cover_find_spot(int from_x, int from_y, int reach, int *out_x, int *out_y);
// True when the segment between two world points crosses a low-cover cell (endpoints excluded).
int line_crosses_low_cover(int x0, int y0, int x1, int y1);

#endif // COLLISION_MODULE_H
