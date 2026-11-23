#include "dmg_numbers.h"
#include <nds.h>

#define DMG_NUM_MAX 24
#define DMG_LIFE_ARC 33
#define DMG_LIFE_DOT 30

// Fixed-point 8.8 kinematics (FIXED_SHIFT = 8 -> 1 px = 256).
#define DMG_ARC_VY0  (-307) // -1.2 px/frame
#define DMG_ARC_GRAV 12     // ~0.047 px/frame^2
#define DMG_DOT_VY   (-128) // -0.5 px/frame

typedef struct {
    fixed x, y;
    fixed vx, vy;
    int value;
    uint8_t kind;
    uint8_t age;
    uint8_t life;
    uint8_t active;
} DmgNum;

static DmgNum s_nums[DMG_NUM_MAX];
static int s_next_slot = 0;
static uint32_t s_rng = 0x51A7BEEFu;
static fixed s_player_x = 0;
static fixed s_player_y = 0;

// 3x5 1-bit glyphs: 3 bits per row (MSB=left), 5 rows. Index 10 = '+'.
static const uint8_t s_glyphs[11][5] = {
    {7, 5, 5, 5, 7}, // 0
    {2, 6, 2, 2, 7}, // 1
    {7, 1, 7, 4, 7}, // 2
    {7, 1, 7, 1, 7}, // 3
    {5, 5, 7, 1, 1}, // 4
    {7, 4, 7, 1, 7}, // 5
    {7, 4, 7, 5, 7}, // 6
    {7, 1, 1, 2, 2}, // 7
    {7, 5, 7, 5, 7}, // 8
    {7, 5, 7, 1, 7}, // 9
    {0, 2, 7, 2, 0}, // +
};

void dmg_numbers_reset(void) {
    for (int i = 0; i < DMG_NUM_MAX; i++) s_nums[i].active = 0;
    s_next_slot = 0;
}

void dmg_numbers_set_player_pos(fixed x, fixed y) {
    s_player_x = x;
    s_player_y = y;
}

static fixed next_spread_vx(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    // Spread in +-0.125..0.25 px/frame (32..63 in 8.8 fixed point)
    int mag = (int)((s_rng >> 16) & 31) + 32;
    return (s_rng & 0x80000000u) ? (fixed)mag : (fixed)(-mag);
}

static void spawn_internal(fixed world_x, fixed world_y, int value, DmgNumKind kind) {
    DmgNum *n = &s_nums[s_next_slot];
    s_next_slot = (s_next_slot + 1) % DMG_NUM_MAX;

    n->x = world_x;
    n->y = world_y;
    n->value = value;
    n->kind = (uint8_t)kind;
    n->age = 0;
    n->active = 1;

    if (kind == DMG_NUM_DOT) {
        n->vx = 0;
        n->vy = DMG_DOT_VY;
        n->life = DMG_LIFE_DOT;
    } else {
        n->vx = next_spread_vx();
        n->vy = DMG_ARC_VY0;
        n->life = DMG_LIFE_ARC;
    }
}

void dmg_numbers_spawn(fixed world_x, fixed world_y, int value, DmgNumKind kind) {
    if (value <= 0) return;
    spawn_internal(world_x, world_y, value, kind);
}

// Shows an explicit "0" (immune target); dmg_numbers_spawn skips non-positive values.
void dmg_numbers_spawn_zero(fixed world_x, fixed world_y) {
    spawn_internal(world_x, world_y, 0, DMG_NUM_NORMAL);
}

void dmg_numbers_spawn_player(int value, DmgNumKind kind) {
    dmg_numbers_spawn(s_player_x, s_player_y - TO_FIXED(18), value, kind);
}

void dmg_numbers_update(void) {
    for (int i = 0; i < DMG_NUM_MAX; i++) {
        DmgNum *n = &s_nums[i];
        if (!n->active) continue;
        n->age++;
        if (n->age >= n->life) {
            n->active = 0;
            continue;
        }
        n->x += n->vx;
        n->y += n->vy;
        if (n->kind != DMG_NUM_DOT) n->vy += DMG_ARC_GRAV;
    }
}

static uint16_t kind_color(uint8_t kind, int fade_step) {
    int r, g, b;
    switch (kind) {
        case DMG_NUM_DOT:    r = 22; g = 18; b = 23; break;
        case DMG_NUM_PLAYER: r = 25; g = 10; b = 10; break;
        case DMG_NUM_HEAL:   r = 14; g = 21; b = 15; break;
        case DMG_NUM_MANA:   r = 14; g = 19; b = 25; break;
        default:             r = 28; g = 26; b = 23; break;
    }
    if (fade_step == 1) { r = (r * 3) >> 2; g = (g * 3) >> 2; b = (b * 3) >> 2; }
    else if (fade_step >= 2) { r >>= 1; g >>= 1; b >>= 1; }
    return (uint16_t)(RGB15(r, g, b) | BIT(15));
}

static void draw_glyph(uint16_t *buffer, int x0, int y0, int glyph_idx, uint16_t fg, uint16_t out, int fade) {
    const uint8_t *rows = s_glyphs[glyph_idx];
    // Skip heavy outline in the final fade step so it dissolves softly.
    if (fade < 2) {
        for (int r = 0; r < 5; r++) {
            uint8_t bits = rows[r];
            for (int c = 0; c < 3; c++) {
                if (!(bits & (4 >> c))) continue;
                int px = x0 + c, py = y0 + r;
                for (int oy = -1; oy <= 1; oy++) {
                    int sy = py + oy;
                    if (sy < 0 || sy >= SCREEN_H) continue;
                    for (int ox = -1; ox <= 1; ox++) {
                        int sx = px + ox;
                        if (sx >= 0 && sx < SCREEN_W) buffer[sy * SCREEN_W + sx] = out;
                    }
                }
            }
        }
    }
    for (int r = 0; r < 5; r++) {
        uint8_t bits = rows[r];
        int sy = y0 + r;
        if (sy < 0 || sy >= SCREEN_H) continue;
        for (int c = 0; c < 3; c++) {
            if (!(bits & (4 >> c))) continue;
            int sx = x0 + c;
            if (sx >= 0 && sx < SCREEN_W) {
                // Checkerboard dissolve in the final fade step
                if (fade >= 2 && ((sx + sy) & 1)) continue;
                buffer[sy * SCREEN_W + sx] = fg;
            }
        }
    }
}

void dmg_numbers_draw(uint16_t *buffer, int cam_x, int cam_y) {
    const uint16_t outline = RGB15(2, 1, 1) | BIT(15);
    for (int i = 0; i < DMG_NUM_MAX; i++) {
        const DmgNum *n = &s_nums[i];
        if (!n->active) continue;

        int sx = TO_INT(n->x) - cam_x;
        int sy = TO_INT(n->y) - cam_y;
        if (sy < -8 || sy >= SCREEN_H + 8 || sx < -24 || sx >= SCREEN_W + 24) continue;

        int rem = (int)n->life - (int)n->age;
        int fade = (rem <= 5) ? 2 : (rem <= 11 ? 1 : 0);
        uint16_t fg = kind_color(n->kind, fade);

        uint8_t idx[8];
        int len = 0;
        int v = n->value;
        if (v > 9999) v = 9999;
        uint8_t rev[6];
        int rlen = 0;
        do {
            rev[rlen++] = (uint8_t)(v % 10);
            v /= 10;
        } while (v > 0 && rlen < 6);
        if (n->kind == DMG_NUM_HEAL || n->kind == DMG_NUM_MANA) idx[len++] = 10; // '+'
        while (rlen > 0) idx[len++] = rev[--rlen];

        int total_w = len * 4 - 1;
        int x0 = sx - (total_w >> 1);
        int y0 = sy - 2;

        // Mark dirty spans including 1-px outline
        int d_x0 = x0 - 1;
        int d_x1 = x0 + total_w + 1;
        if (d_x0 < 0) d_x0 = 0;
        if (d_x1 > SCREEN_W) d_x1 = SCREEN_W;
        if (d_x0 < d_x1) {
            for (int r = -1; r <= 5; r++) dirty_row(y0 + r, d_x0, d_x1);
        }

        for (int k = 0; k < len; k++) {
            draw_glyph(buffer, x0 + k * 4, y0, idx[k], fg, outline, fade);
        }
    }
}
