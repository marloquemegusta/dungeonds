#ifndef DUNGEON_OCCLUSION_H
#define DUNGEON_OCCLUSION_H

#include <nds.h>
#include "diablo_dungeon.h"

// Horizontal run of occluding pixels; depth is the world Y of the floor point
// under the visible surface (an actor whose feet are above it is hidden).
typedef struct {
    uint16_t x;
    uint16_t y;
    uint16_t length;
    int16_t depth;
} DungeonOcclusionRun;

extern const DungeonOcclusionRun g_dungeon_occlusion_runs[];
extern const uint32_t g_dungeon_occlusion_run_count;
extern const uint32_t g_dungeon_occlusion_row_start[WORLD_H + 1];

#endif // DUNGEON_OCCLUSION_H
