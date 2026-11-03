#ifndef NAVFIELD_H
#define NAVFIELD_H

#include "game.h"
#include "diablo_dungeon.h"

// Distance field over the walkable floor, from the player outwards (DESIGN.md 4.6).
// Enemies read it to walk around walls: from where they stand they step to the
// neighbouring node with the smallest distance.
//
// The grid is coarse (NAV_NODE_PX per node) and the breadth-first search runs a few
// hundred nodes per frame, building into a second buffer that is swapped in once
// complete, so enemies always read a finished field and the cost stays amortized.

#define NAV_NODE_PX 16                       // world px per node (4 collision cells)
#define NAV_W (WORLD_W / NAV_NODE_PX)
#define NAV_H (WORLD_H / NAV_NODE_PX)
#define NAV_UNREACHABLE 255

// Builds the walkable-node grid from the collision map. Call once per arena.
void nav_init(void);

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
