#ifndef DIABLO_DUNGEON_H
#define DIABLO_DUNGEON_H

#include <nds.h>

#define WORLD_W 1536
#define WORLD_H 864
#define COLLISION_W 384
#define COLLISION_H 216
#define COLLISION_SCALE 4
#define DUNGEON_OCCLUSION_SEGMENTS 1
#define COLLISION_BYTES 20736

#define SPAWN_PIXEL_X 705
#define SPAWN_PIXEL_Y 515

extern const uint8_t g_dungeon_collision[COLLISION_BYTES];

#endif // DIABLO_DUNGEON_H
