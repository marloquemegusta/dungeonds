#ifndef DIABLO_DUNGEON_H
#define DIABLO_DUNGEON_H

#include <nds.h>

#define WORLD_W 3200
#define WORLD_H 1920
#define COLLISION_W 800
#define COLLISION_H 480
#define COLLISION_SCALE 4
#define DUNGEON_OCCLUSION_SEGMENTS 4
#define COLLISION_BYTES ((COLLISION_W * COLLISION_H + 3) / 4)

#define SPAWN_PIXEL_X 1600
#define SPAWN_PIXEL_Y 960

extern const uint8_t g_dungeon_collision[COLLISION_BYTES];

#endif // DIABLO_DUNGEON_H
