#ifndef PLAYER_SPRITE_INCLUDED
#define PLAYER_SPRITE_INCLUDED

#include <nds.h>

#define PLAYER_SPRITE_W 40
#define PLAYER_SPRITE_H 40
#define PLAYER_SHADOW_W 80
#define PLAYER_SHADOW_H 80
#define PLAYER_NUM_DIRS 8
#define PLAYER_NUM_FRAMES 8

// The ground origin is the shared lower anchor of every sprite canvas.
#define PLAYER_ANCHOR_X 20
#define PLAYER_ANCHOR_Y 35

#define NUM_CHARACTERS 3

enum {
    CHAR_HERO = 0,
    CHAR_CHARGER = 1,
    CHAR_NECRON = 2,
    CHAR_SKELETON = CHAR_NECRON // Backward compatibility alias
};

typedef struct {
    const char *name;
    int speed;        // 8.8 fixed point speed (px/frame)
    int anim_period;  // ticks per frame
} CharacterConfig;

extern const CharacterConfig g_characters[NUM_CHARACTERS];
extern const uint8_t g_character_ground_anchors[NUM_CHARACTERS][PLAYER_NUM_DIRS];

// Space Marine frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_player_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_player_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Charger enemy frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_charger_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_charger_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_charger_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Necron enemy frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_necron_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_necron_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_necron_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Fast indexed lookups:
extern const uint16_t (* const g_character_frames[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t (* const g_character_shadow_masks[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];

#endif // PLAYER_SPRITE_INCLUDED
