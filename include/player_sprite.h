#ifndef PLAYER_SPRITE_INCLUDED
#define PLAYER_SPRITE_INCLUDED

#include <nds.h>

#define PLAYER_SPRITE_W 40
#define PLAYER_SPRITE_H 40
// Hero shot clip (charge / shoot, arms spread in a cross): its own, bigger cell at the same world scale as the
// walk. Drawn centred on the feet like every sprite (x - W / 2); its ground row is g_player_shot_ground_anchors.
#define HERO_SHOT_SPRITE_W 48
#define HERO_SHOT_SPRITE_H 48
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
#define ABANDERADO_POINT_NUM_FRAMES 8 // head raised + staff tilted forward
#define PLAYER_NUM_DIRS 8
#define PLAYER_NUM_FRAMES 8

// The ground origin row varies per character/direction: see g_character_ground_anchors.
#define PLAYER_ANCHOR_X 20

#define NUM_CHARACTERS 21

enum {
    CHAR_HERO = 0,
    CHAR_CHARGER = 1,
    CHAR_OJO = 2,               // El Ojo del Tribunal (ENEMY_TYPE_SHOOTER); the old necron assets are kept on disk but unused
    CHAR_EXVOTO = 3,            // wax nun walking (the horde mass; replaces the skeleton, DESIGN.md 6.10)
    // Exvoto clips: one slot each, the enemy swaps char_id with its pose (same 40x40 cell as the walk).
    CHAR_EXVOTO_PRAY_STAND = 4, // praying on her feet (loop)
    CHAR_EXVOTO_PRAY_KNEEL = 5, // praying on her knees (loop)
    CHAR_EXVOTO_STAND_UP = 6,   // kneeling -> standing, ends where the walk starts
    CHAR_ABANDERADO = 7,
    CHAR_MONAGUILLO = 8,
    // Hero crouched (cobertura baja, DESIGN.md 6.9): the player swaps char_id between CHAR_HERO and this slot.
    CHAR_HERO_CROUCH_WALK = 9,  // crouched walking, 8 frames, 40x40 cell; the still pose is one fixed frame of it
    // Exvoto tiers (v3, walkthroughs/arpg-predemo §10): the Bebé has its own baked sheet; the Párroco runs with
    // its own sheet streamed from NitroFS (see CHAR_EXVOTO_PARROCO_RUN); the praying/rising poses of the Párroco
    // still borrow CHAR_EXVOTO / CHAR_EXVOTO_PRAY_STAND (his sheets do not fit in EWRAM, TECHNICAL.md).
    CHAR_EXVOTO_BEBE = 10,      // Exvoto Bebé walking (swarm tier), 8 frames, 40x40 cell
    // El Campanero de Ánimas (jefe ARPG): slot sin píxeles en la EWRAM; sus 5 clips (60x60) se leen de NitroFS
    // (source/campanero_sprite.c) y el clip actual va en Enemy.kneel. No es un slot de stream_char: va antes de CHAR_FIRST_STREAMED.
    CHAR_CAMPANERO = 11,
    // Párroco running (Mixamo Running on exvoto_parroco), 8 frames, 48x48 cell. Its pixels, runs and shadow masks are
    // NOT in this file's tables: they live in nitrofiles/parroco/run.bin and source/stream_char.c keeps a small
    // cache of frames; the character_*_ptr accessors below load a frame on demand for the streamed slots (>= CHAR_FIRST_STREAMED).
    CHAR_EXVOTO_PARROCO_RUN = 12,
    CHAR_FIRST_STREAMED = CHAR_EXVOTO_PARROCO_RUN,
    // Súper Monja (ENEMY_TYPE_MONJA, Tripo 9713149f), 56x56 cell, her own four clips, also streamed (nitrofiles/smonja/).
    CHAR_SMONJA_WALK = 13,
    CHAR_SMONJA_PRAY_STAND = 14,
    CHAR_SMONJA_PRAY_KNEEL = 15,
    CHAR_SMONJA_STAND_UP = 16,
    // Spider form of the Exvoto and the Monaguillo under the Súper Monja's aura (nitrofiles/arana/): walk (burst + pause) and the
    // lying-down transition (played backwards to get up). Cells 40x40 (Exvoto) and 48x48 (Monaguillo).
    CHAR_EXVOTO_ARANA_WALK = 17,
    CHAR_EXVOTO_ARANA_TRANS = 18,
    CHAR_MONAGUILLO_ARANA_WALK = 19,
    CHAR_MONAGUILLO_ARANA_TRANS = 20
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

// Hero frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped to bounds)
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
// Ground anchor (feet row inside the HERO_SHOT_SPRITE cell) per direction; the walk's is g_character_ground_anchors.
extern const uint8_t g_player_shot_ground_anchors[PLAYER_NUM_DIRS];
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

// Exvoto walk (andar rezando) frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_exvoto_frames[];
extern const uint32_t g_exvoto_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_exvoto_shadow_masks[];
extern const uint32_t g_exvoto_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Exvoto praying standing frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_exvoto_pray_stand_frames[];
extern const uint32_t g_exvoto_pray_stand_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_pray_stand_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_exvoto_pray_stand_shadow_masks[];
extern const uint32_t g_exvoto_pray_stand_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_pray_stand_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Exvoto praying kneeling frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_exvoto_pray_kneel_frames[];
extern const uint32_t g_exvoto_pray_kneel_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_pray_kneel_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_exvoto_pray_kneel_shadow_masks[];
extern const uint32_t g_exvoto_pray_kneel_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_pray_kneel_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Exvoto standing up frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_exvoto_stand_up_frames[];
extern const uint32_t g_exvoto_stand_up_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_stand_up_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_exvoto_stand_up_shadow_masks[];
extern const uint32_t g_exvoto_stand_up_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_stand_up_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Exvoto Bebé walk (swarm tier) frames & animated crisp 3D shadows (8 dirs x 8 frames, cropped)
extern const uint16_t g_exvoto_bebe_frames[];
extern const uint32_t g_exvoto_bebe_frame_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_bebe_frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
extern const uint8_t g_exvoto_bebe_shadow_masks[];
extern const uint32_t g_exvoto_bebe_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint8_t g_exvoto_bebe_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

// Abanderado point clip (CHAR_ABANDERADO, 60x60, 8 dirs x 8 frames, cropped)
extern const uint16_t g_abanderado_point_frames[];
extern const uint32_t g_abanderado_point_frame_offsets[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES];
extern const uint8_t g_abanderado_point_frame_bounds[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES][4];
extern const uint8_t g_abanderado_point_shadow_masks[];
extern const uint32_t g_abanderado_point_shadow_offsets[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES];
extern const uint8_t g_abanderado_point_shadow_bounds[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES][4];

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
extern const uint16_t g_exvoto_runs[];
extern const uint32_t g_exvoto_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_exvoto_pray_stand_runs[];
extern const uint32_t g_exvoto_pray_stand_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_exvoto_pray_kneel_runs[];
extern const uint32_t g_exvoto_pray_kneel_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_exvoto_stand_up_runs[];
extern const uint32_t g_exvoto_stand_up_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_exvoto_bebe_runs[];
extern const uint32_t g_exvoto_bebe_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_abanderado_runs[];
extern const uint32_t g_abanderado_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
extern const uint16_t g_abanderado_point_runs[];
extern const uint32_t g_abanderado_point_run_offsets[PLAYER_NUM_DIRS][ABANDERADO_POINT_NUM_FRAMES];
extern const uint16_t g_monaguillo_runs[];
extern const uint32_t g_monaguillo_run_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];

// Fast indexed lookups:
// The tables are writable only because the streamed slots (>= CHAR_FIRST_STREAMED) fill its entries at runtime.
extern const uint16_t * g_character_frames[NUM_CHARACTERS];
extern const uint32_t (* g_character_frame_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];
extern const uint8_t (* g_character_frame_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];
extern const uint8_t * g_character_shadow_masks[NUM_CHARACTERS];
extern const uint32_t (* g_character_shadow_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];
extern const uint8_t (* g_character_shadow_bounds[NUM_CHARACTERS])[PLAYER_NUM_FRAMES][4];

// Streamed slots (source/stream_char.c): makes sure the frame is in the RAM cache before its pointers are used.
extern int g_parroco_run_ok;    // 1 once run.bin has been read; 0 = enemy_type_char_id falls back to the Exvoto sheet
extern int g_arana_ok;          // 1 once the four spider-form files (nitrofiles/arana/) have been read; 0 = no possession
extern int g_smonja_ok;         // 1 once the four Súper Monja files have been read; 0 = the Monja falls back to the Exvoto sheets
void stream_char_ensure(int char_id, int dir, int frame);

static inline const uint16_t *character_frame_ptr(int char_id, int dir, int frame) {
    if (__builtin_expect(char_id >= CHAR_FIRST_STREAMED, 0)) stream_char_ensure(char_id, dir, frame);
    return g_character_frames[char_id] + g_character_frame_offsets[char_id][dir][frame];
}

extern const uint16_t * g_character_runs[NUM_CHARACTERS];
extern const uint32_t (* g_character_run_offsets[NUM_CHARACTERS])[PLAYER_NUM_FRAMES];

static inline const uint16_t *character_runs_ptr(int char_id, int dir, int frame) {
    if (__builtin_expect(char_id >= CHAR_FIRST_STREAMED, 0)) stream_char_ensure(char_id, dir, frame);
    return g_character_runs[char_id] + g_character_run_offsets[char_id][dir][frame];
}

static inline const uint8_t *character_shadow_mask_ptr(int char_id, int dir, int frame) {
    if (__builtin_expect(char_id >= CHAR_FIRST_STREAMED, 0)) stream_char_ensure(char_id, dir, frame);
    return g_character_shadow_masks[char_id] + g_character_shadow_offsets[char_id][dir][frame];
}

#endif // PLAYER_SPRITE_INCLUDED
