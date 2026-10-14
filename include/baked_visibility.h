#ifndef BAKED_VISIBILITY_H
#define BAKED_VISIBILITY_H

#include <nds.h>

#define BAKED_VIS_MAP_W 96
#define BAKED_VIS_MAP_H 64
#define BAKED_VIS_RADIUS 12
#define BAKED_VIS_BOX_SIZE 25
#define BAKED_VIS_BOX_BYTES 79
#define BAKED_VIS_NUM_WALKABLE 1614

extern const int16_t g_baked_walkable_index[BAKED_VIS_MAP_H][BAKED_VIS_MAP_W];
extern const uint8_t g_baked_vis_masks[BAKED_VIS_NUM_WALKABLE][BAKED_VIS_BOX_BYTES];

#endif // BAKED_VISIBILITY_H
