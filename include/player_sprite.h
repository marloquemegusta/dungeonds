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
#define OJO_LOOK_NUM_FRAMES 4       // breathing loop of the gaze (LOOK / CONDEMNED)
#define OJO_SENTENCE_NUM_FRAMES 6   // head-raising gesture when the beam is released
#define PLAYER_NUM_DIRS 8
#define PLAYER_NUM_FRAMES 8

// The ground origin row varies per character/direction: see g_character_ground_anchors.
#define PLAYER_ANCHOR_X 20

#define NUM_CHARACTERS 4

enum {
    CHAR_HERO = 0,
    CHAR_CHARGER = 1,
    CHAR_OJO = 2,       // El Ojo del Tribunal (ENEMY_TYPE_SHOOTER); the old necron assets are kept on disk but unused
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

// Space Marine / Hero frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped to bounds)
extern const uint16_t g_player_frames[];
extern const uint32_t g_player_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_player_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_player_shadow_masks[];
extern const uint32_t g_player_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_player_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Hero shot clip (CHAR_HERO only, DESIGN.md "Carga y disparo"): 8 dirs x 8 frames, f0 arms crossed,
// f7 collapsed. Drawn while the sniper charges (frame from the progress, backwards) and after a shot.
extern const uint16_t g_player_shot_frames[];
extern const uint32_t g_player_shot_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_player_shot_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_player_shot_shadow_masks[];
extern const uint32_t g_player_shot_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_player_shot_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
// Muzzle of the hero shot clip per [direction][frame] = { gx, gy, h }, same meaning as g_character_muzzle.
extern const int8_t g_hero_shot_muzzle[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3];

// Charger enemy frames & animated crisp 3D shadows (8 dirs x 8 frames, 60x60, shadow 80x80, cropped)
extern const uint16_t g_charger_frames[];
extern const uint32_t g_charger_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_charger_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_charger_shadow_masks[];
extern const uint32_t g_charger_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_charger_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Charger charge clip (Cireneo bent nearly parallel to the ground): 8 dirs x 4 frames at 60x60, cropped
extern const uint16_t g_charger_charge_frames[];
extern const uint32_t g_charger_charge_frame_offsets[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES];
extern const uint8_t g_charger_charge_frame_bounds[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][4];
extern const uint8_t g_charger_charge_shadow_masks[];
extern const uint32_t g_charger_charge_shadow_offsets[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES];
extern const uint8_t g_charger_charge_shadow_bounds[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES][4];

// Charger telegraph keyframe (Cireneo crouched with feet planted, bridging walk[0] -> charge[0]): 8 dirs x 1 frame at 60x60, cropped
extern const uint16_t g_charger_telegraph_frames[];
extern const uint32_t g_charger_telegraph_frame_offsets[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES];
extern const uint8_t g_charger_telegraph_frame_bounds[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES][4];

// Ojo del Tribunal frames & animated crisp 3D shadows (walk clip, 8 dirs x 8 frames, 40x40, cropped)
extern const uint16_t g_ojo_frames[];
extern const uint32_t g_ojo_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_ojo_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_ojo_shadow_masks[];
extern const uint32_t g_ojo_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_ojo_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Ojo look clip (4-frame breathing loop) and sentence clip (6-frame gesture): 8 dirs, 40x40, cropped.
// Their muzzles ({ gx, gy, h } like g_character_muzzle) follow the raised hand.
extern const uint16_t g_ojo_look_frames[];
extern const uint32_t g_ojo_look_frame_offsets[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES];
extern const uint8_t g_ojo_look_frame_bounds[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES][4];
extern const uint8_t g_ojo_look_shadow_masks[];
extern const uint32_t g_ojo_look_shadow_offsets[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES];
extern const uint8_t g_ojo_look_shadow_bounds[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES][4];
extern const int8_t g_ojo_look_muzzle[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES][3];
extern const uint16_t g_ojo_sentence_frames[];
extern const uint32_t g_ojo_sentence_frame_offsets[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES];
extern const uint8_t g_ojo_sentence_frame_bounds[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES][4];
extern const uint8_t g_ojo_sentence_shadow_masks[];
extern const uint32_t g_ojo_sentence_shadow_offsets[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES];
extern const uint8_t g_ojo_sentence_shadow_bounds[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES][4];
extern const int8_t g_ojo_sentence_muzzle[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES][3];

// Skeleton enemy frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_skeleton_frames[];
extern const uint32_t g_skeleton_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_skeleton_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_skeleton_shadow_masks[];
extern const uint32_t g_skeleton_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_skeleton_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Frame pixels are stored row by row with this pitch (the cropped width rounded up to even), so
// every row starts on a 32-bit boundary and the blit can read whole words.
static inline int sprite_pitch(int bw) { return (bw + 1) & ~1; }

// Opaque runs per sprite row (blit_stride). Each frame is a block of uint16: (bh + 1) row offsets in
// halfwords from the block start, then one run per entry = x | (len << 8) (x relative to the cropped
// frame). Row y owns the entries [rows[y], rows[y + 1]). Offsets index the *_runs array in halfwords.
extern const uint16_t g_player_runs[];
extern const uint32_t g_player_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_player_shot_runs[];
extern const uint32_t g_player_shot_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_charger_runs[];
extern const uint32_t g_charger_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_charger_charge_runs[];
extern const uint32_t g_charger_charge_run_offsets[PLAYER_NUM_DIRS][CHARGER_CHARGE_NUM_FRAMES];
extern const uint16_t g_charger_telegraph_runs[];
extern const uint32_t g_charger_telegraph_run_offsets[PLAYER_NUM_DIRS][CHARGER_TELEGRAPH_NUM_FRAMES];
extern const uint16_t g_ojo_runs[];
extern const uint32_t g_ojo_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_ojo_look_runs[];
extern const uint32_t g_ojo_look_run_offsets[PLAYER_NUM_DIRS][OJO_LOOK_NUM_FRAMES];
extern const uint16_t g_ojo_sentence_runs[];
extern const uint32_t g_ojo_sentence_run_offsets[PLAYER_NUM_DIRS][OJO_SENTENCE_NUM_FRAMES];
extern const uint16_t g_skeleton_runs[];
extern const uint32_t g_skeleton_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];

// Fast indexed lookups:
extern const uint16_t * const g_character_frames[NUM_CHARACTERS];
extern const uint32_t (* const g_character_frame_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];
extern const uint8_t (* const g_character_frame_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];
extern const uint8_t * const g_character_shadow_masks[NUM_CHARACTERS];
extern const uint32_t (* const g_character_shadow_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];
extern const uint8_t (* const g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];

static inline const uint16_t *character_frame_ptr(int char_id, int dir, int frame) {
    return g_character_frames[char_id] + g_character_frame_offsets[char_id][dir][frame];
}

extern const uint16_t * const g_character_runs[NUM_CHARACTERS];
extern const uint32_t (* const g_character_run_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];

static inline const uint16_t *character_runs_ptr(int char_id, int dir, int frame) {
    return g_character_runs[char_id] + g_character_run_offsets[char_id][dir][frame];
}

static inline const uint8_t *character_shadow_mask_ptr(int char_id, int dir, int frame) {
    return g_character_shadow_masks[char_id] + g_character_shadow_offsets[char_id][dir][frame];
}

#endif // PLAYER_SPRITE_INCLUDED
