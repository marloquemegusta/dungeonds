#ifndef DIABLO_DUNGEON_H
#define DIABLO_DUNGEON_H

#include <nds.h>

#define WORLD_W 768
#define WORLD_H 512
#define COLLISION_W 192
#define COLLISION_H 128
#define COLLISION_SCALE 4
#define DUNGEON_OCCLUSION_SEGMENTS 1
#define COLLISION_BYTES 6144

#define SPAWN_PIXEL_X 361
#define SPAWN_PIXEL_Y 233

extern const uint8_t g_dungeon_collision[COLLISION_BYTES];

#endif // DIABLO_DUNGEON_H
