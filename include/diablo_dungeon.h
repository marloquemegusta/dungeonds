#ifndef DIABLO_DUNGEON_H
#define DIABLO_DUNGEON_H

#include <nds.h>

#define WORLD_W 512
#define WORLD_H 512
#define COLLISION_W 128
#define COLLISION_H 128
#define COLLISION_SCALE 4

#define SPAWN_PIXEL_X 250
#define SPAWN_PIXEL_Y 266

extern const uint16_t g_dungeon_world_color[WORLD_W * WORLD_H];
extern const uint8_t g_dungeon_collision[COLLISION_H * COLLISION_W];

#endif // DIABLO_DUNGEON_H
