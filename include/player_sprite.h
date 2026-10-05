#ifndef PLAYER_SPRITE_INCLUDED
#define PLAYER_SPRITE_INCLUDED

#include <nds.h>

#define PLAYER_SPRITE_W 64
#define PLAYER_SPRITE_H 64
#define PLAYER_SHADOW_W 96
#define PLAYER_SHADOW_H 96
#define PLAYER_NUM_DIRS 8
#define PLAYER_NUM_FRAMES 8

 // The ground origin is the shared lower anchor of every sprite canvas.
#define PLAYER_ANCHOR_X 32
#define PLAYER_ANCHOR_Y 32

extern const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_player_shadow_masks[PLAYER_NUM_DIRS][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_player_shadow_bounds[PLAYER_NUM_DIRS][4];

#endif // PLAYER_SPRITE_INCLUDED
