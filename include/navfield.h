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
#define NAV_MAX_W 80                         // largest arena (px / NAV_NODE_PX) the buffers hold (1280 px dungeon)
#define NAV_MAX_H 80
#define NAV_UNREACHABLE 0xFFFF               // distances are uint16: corridors are long
// The search stops this many steps from the player: farther nodes stay unreachable, which keeps
// the per-frame cost bounded on the 80x80 grid (enemies that far away are dormant or out of the fight).
#ifndef NAV_MAX_DEPTH            // the host test builds with a huge value to check connectivity
#define NAV_MAX_DEPTH 96
#endif

// Builds the walkable-node grid from the active arena. Call whenever the arena changes.
void nav_init(void);

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
