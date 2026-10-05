#ifndef GAME_H
#define GAME_H

#include <nds.h>
#include <stdio.h>
#include <string.h>

#define SCREEN_W 256
#define SCREEN_H 192

// Fixed point 8.8 (no FPU on the Nintendo DS)
typedef int32_t fixed;
#define FIXED_SHIFT 8
#define TO_FIXED(x) ((fixed)((x) << FIXED_SHIFT))
#define TO_INT(x)   ((int)((x) >> FIXED_SHIFT))

// Half-tile helpers for the 2:1 dimetric projection.
#define TILE_HALF_W 16
#define TILE_HALF_H 8

// Direction constants (8 directions matching sprite rows)
// 0: South, 1: SW, 2: West, 3: NW, 4: North, 5: NE, 6: East, 7: SE
enum {
    DIR_SOUTH = 0,
    DIR_SOUTHWEST = 1,
    DIR_WEST = 2,
    DIR_NORTHWEST = 3,
    DIR_NORTH = 4,
    DIR_NORTHEAST = 5,
    DIR_EAST = 6,
    DIR_SOUTHEAST = 7
};

typedef struct {
    fixed x;       // 8.8 fixed point tile-space X (tile centre = int + 0.5)
    fixed y;       // 8.8 fixed point tile-space Y
    int dir;       // 0..7
    int frame;     // 0..7
    int is_moving;
    int anim_timer;
} Player;

#endif // GAME_H
