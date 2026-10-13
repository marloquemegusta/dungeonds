#ifndef DUNGEON_OCCLUSION_H
#define DUNGEON_OCCLUSION_H

#include <stdint.h>
#include "diablo_dungeon.h"

typedef struct {
    uint16_t x;
    uint16_t y;
    uint16_t length;
    int16_t depth;
} DungeonOcclusionRun;

typedef struct {
    int16_t x;
    int16_t y;
} DungeonOcclusionSegmentOffset;

extern const DungeonOcclusionRun g_dungeon_occlusion_runs[];
extern const uint32_t g_dungeon_occlusion_run_count;
extern const DungeonOcclusionSegmentOffset g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS];

#endif
