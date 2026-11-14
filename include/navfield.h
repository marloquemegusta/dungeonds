#ifndef NAVFIELD_H
#define NAVFIELD_H

#include "game.h"
#include "arena.h"

// Distance field over the walkable floor, from the player outwards (DESIGN.md 4.6).
// Enemies read it to walk around walls: from where they stand they step to the
// neighbouring node with the smallest distance.
//
// The grid is coarse (NAV_NODE_PX per node) and the breadth-first search runs a few
// hundred nodes per frame, building into a second buffer that is swapped in once
// complete, so enemies always read a finished field and the cost stays amortized.

#define NAV_NODE_PX 16                       // world px per node (4 collision cells)
#define NAV_MAX_W 48                         // keeps the widest v0.2 arena supported
#define NAV_MAX_H 128                        // 2048 px window / 16 px per node
#define NAV_UNREACHABLE 255

// Builds the walkable-node grid from the active arena. Call whenever the arena changes.
void nav_init(void);

// Rebuilds the walkable grid incrementally after the active arena data shifts.
// nav_update spends its node budget on this grid first, then on the distance search.
void nav_refresh_begin(int goal_px, int goal_py);
// stage_id: the id the rows were staged under by nav_stage_step (0 = none); a match skips the
// per-node walkability work of the shift frame.
void nav_shift_down(int rows, int goal_px, int goal_py, uint32_t stage_id);
// Computes ahead, `budget` nodes per call, the walkable flags of the `rows` top node rows that the
// next nav_shift_down(rows, ...) will need. The caller points the arena at the window those rows
// belong to (strip_stage_enter) and passes the stage id; a changed id restarts. Returns 1 when done.
int nav_stage_step(int rows, int budget, uint32_t stage_id);

// Grid size of the active arena, in nodes.
int nav_width(void);
int nav_height(void);

// Sets the goal (world px) used when the next search starts. Cheap; call every frame.
void nav_set_goal(int goal_px, int goal_py);

// Advances the search by up to `budget` node expansions; swaps the field in when done.
void nav_update(int budget);

// Runs a whole search at once (arena start and host tests).
void nav_rebuild_now(void);

// Steps to the goal from the node under (px, py), or NAV_UNREACHABLE.
int nav_distance(int px, int py);

// Centre (world px) of the neighbouring node an enemy at (px, py) should walk to next.
// Returns 0 when it has no better neighbour (at the goal, or unreachable).
int nav_next_step(int px, int py, int *target_px, int *target_py);

// Number of walkable nodes (for tests and diagnostics).
int nav_walkable_count(void);

#endif // NAVFIELD_H
