#ifndef DUNGEON_OCCLUSION_H
#define DUNGEON_OCCLUSION_H

#include <stdint.h>
#include "diablo_dungeon.h"

#define DUNGEON_OCCLUSION_MASK_BYTES ((WORLD_W * WORLD_H + 7) / 8)
#define DUNGEON_OCCLUSION_MASK_TEST(index) \
    (g_dungeon_upper_mask[(index) >> 3] & (1u << ((index) & 7)))

typedef struct {
    uint16_t x;
    uint16_t y;
    uint16_t length;
    int16_t depth;
} DungeonOcclusionRun;

extern const DungeonOcclusionRun g_dungeon_occlusion_runs[];
extern const uint32_t g_dungeon_occlusion_run_count;
extern const uint8_t g_dungeon_upper_mask[DUNGEON_OCCLUSION_MASK_BYTES];

#endif
