#ifndef PLAYER_SPRITE_INCLUDED
#define PLAYER_SPRITE_INCLUDED

#include <nds.h>

#define PLAYER_SPRITE_W 40
#define PLAYER_SPRITE_H 40
#define PLAYER_SHADOW_W 80
#define PLAYER_SHADOW_H 80
#define CHARGER_SPRITE_W 60
#define CHARGER_SPRITE_H 60
#define CHARGER_SHADOW_W 80
#define CHARGER_SHADOW_H 80
#define CHARGER_CHARGE_NUM_FRAMES 4
#define CHARGER_TELEGRAPH_NUM_FRAMES 1
#define PLAYER_NUM_DIRS 8
#define PLAYER_NUM_FRAMES 8

// The ground origin row varies per character/direction: see g_character_ground_anchors.
#define PLAYER_ANCHOR_X 20

#define NUM_CHARACTERS 4

enum {
    CHAR_HERO = 0,
    CHAR_CHARGER = 1,
    CHAR_NECRON = 2,
    CHAR_SKELETON = 3
};

typedef struct {
    const char *name;
    int speed;        // 8.8 fixed point speed (px/frame)
    int anim_period;  // ticks per frame
    uint8_t sprite_w;
    uint8_t sprite_h;
    uint8_t shadow_w;
    uint8_t shadow_h;
} CharacterConfig;

extern const CharacterConfig g_characters[NUM_CHARACTERS];
extern const uint8_t g_character_ground_anchors[NUM_CHARACTERS][PLAYER_NUM_DIRS];
// Weapon muzzle per [character][direction][frame] = { gx, gy, h }: sprite pixels relative to the
// ground anchor; a shot is drawn at feet + (gx, gy - h). All zeros for characters without weapon.
extern const int8_t g_character_muzzle[NUM_CHARACTERS][PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3];

// Space Marine frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_player_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_player_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_player_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Hero shot clip (CHAR_HERO only, DESIGN.md "Carga y disparo"): 8 dirs x 8 frames, f0 arms crossed,
// f7 collapsed. Drawn while the sniper charges (frame from the progress, backwards) and after a shot.
extern const uint16_t g_player_shot_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_player_shot_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_player_shot_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
// Muzzle of the hero shot clip per [direction][frame] = { gx, gy, h }, same meaning as g_character_muzzle.
extern const int8_t g_hero_shot_muzzle[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3];

// Charger enemy frames & animated crisp 3D shadows (8 dirs x 8 frames, 60x60, shadow 80x80)
extern const uint16_t g_charger_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][CHARGER_SPRITE_W * CHARGER_SPRITE_H];
extern const uint8_t g_charger_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][CHARGER_SHADOW_W * CHARGER_SHADOW_H / 2];
extern const uint8_t g_charger_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Charger charge clip (Cireneo bent nearly parallel to the ground): 8 dirs x 4 frames at 60x60
extern const uint16_t g_charger_charge_frames[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][CHARGER_SPRITE_W * CHARGER_SPRITE_H];
extern const uint8_t g_charger_charge_shadow_masks[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][CHARGER_SHADOW_W * CHARGER_SHADOW_H / 2];
extern const uint8_t g_charger_charge_shadow_bounds[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][4];

// Charger telegraph keyframe (Cireneo crouched with feet planted, bridging walk[0] -> charge[0]): 8 dirs x 1 frame at 60x60
extern const uint16_t g_charger_telegraph_frames[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES][CHARGER_SPRITE_W * CHARGER_SPRITE_H];

// Necron enemy frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_necron_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_necron_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_necron_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Skeleton enemy frames & animated crisp 3D shadows (8 dirs x 8 frames)
extern const uint16_t g_skeleton_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];
extern const uint8_t g_skeleton_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];
extern const uint8_t g_skeleton_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Fast indexed lookups:
extern const uint16_t * const g_character_frames[NUM_CHARACTERS];
extern const uint8_t * const g_character_shadow_masks[NUM_CHARACTERS];
extern const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];

static inline const uint16_t *character_frame_ptr(int char_id, int dir, int frame) {
    int stride = (int)g_characters[char_id].sprite_w * (int)g_characters[char_id].sprite_h;
    return g_character_frames[char_id] + (dir * PLAYER_NUM_FRAMES + frame) * stride;
}

static inline const uint8_t *character_shadow_mask_ptr(int char_id, int dir, int frame) {
    int stride = ((int)g_characters[char_id].shadow_w * (int)g_characters[char_id].shadow_h) / 2;
    return g_character_shadow_masks[char_id] + (dir * PLAYER_NUM_FRAMES + frame) * stride;
}

#endif // PLAYER_SPRITE_INCLUDED
