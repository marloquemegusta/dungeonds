#include "game.h"
#include "dungeon_data.h"
#include "player_sprite.h"

// ---------------------------------------------------------------------------
// DungeonDS - dimetric dungeon renderer
//
// The world is a MAP_COLS x MAP_ROWS tile grid. A tile (col,row) centre maps to
// world pixel coordinates:
//      sx = (col - row) * (FLOOR_TILE_W / 2)
//      sy = (col + row) * (FLOOR_TILE_H / 2)
// FLOOR_TILE_H comes from the baked view preset (tools/ds_look.py): it is
// 16 px at 30 deg elevation (classic 2:1) and 28 px at 60 deg. Sprites are
// pre-baked with the matching orthographic camera, so a sprite's centre is its
// ground anchor point on the tile.
//
// The static floor is pre-composited once into a world-sized cache; each frame
// only the visible window is copied out, which keeps the ARM9 well inside its
// 60 FPS budget. Both screens show a continuous vertical slice of the world:
// the bottom screen is centred on the player and the top screen reveals the
// area above it.
// ---------------------------------------------------------------------------

#define VOID_COLOR RGB15(0, 0, 0)

// Screen-space movement speed (px/frame, 8.8 fixed) and collider radius
#define PLAYER_SPEED (TO_FIXED(1) + 128) // 1.5 px/frame
#define PLAYER_COLLIDER 96               // 0.375 tile radius
#define ANIM_PERIOD 5

// Camera vertical anchor: where the player's feet sit on the bottom screen.
// Above centre, so the top screen is filled by the dungeon rather than the void.
#define CAMERA_ANCHOR_Y 88

// Upper bound on objects drawn per screen (walls + pillars in view).
#define MAX_DRAW_ITEMS 128

// World-sized floor cache (origin = world pixel (CACHE_X0, CACHE_Y0))
#define CACHE_X0 (-((MAP_ROWS - 1) * TILE_HALF_W) - TILE_HALF_W)
#define CACHE_Y0 (-OBJ_SPRITE_H)
#define CACHE_W  ((((MAP_COLS - 1) * TILE_HALF_W) + TILE_HALF_W) - CACHE_X0)
#define CACHE_H  (((((MAP_COLS - 1) + (MAP_ROWS - 1)) * TILE_HALF_H) + TILE_HALF_H) - CACHE_Y0)

static uint16_t s_floor_cache[CACHE_W * CACHE_H] __attribute__((aligned(4)));
static uint16_t s_bot_backbuffer[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));
static uint16_t s_top_backbuffer[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));

static u16 *s_top_vram = NULL;
static int s_top_bg = 0;
static int s_active_vram_bank = 0;

static Player s_player;
static int s_cam_x = 0;
static int s_cam_y = 0;

typedef struct {
    int depth;     // 8.8 fixed depth key (col+row in tile units)
    int sprite;    // object id, -1 = player
    int cx;        // world pixel centre X
    int cy;        // world pixel centre Y (ground point)
} DrawItem;

// ---------------------------------------------------------------------------
// Projection helpers
// ---------------------------------------------------------------------------

static inline int tile_center_x(int col, int row) {
    return (col - row) * TILE_HALF_W;
}

static inline int tile_center_y(int col, int row) {
    return (col + row) * TILE_HALF_H;
}

static inline int player_screen_x(fixed x, fixed y) {
    return (int)(((x - y) * TILE_HALF_W) >> FIXED_SHIFT);
}

static inline int player_screen_y(fixed x, fixed y) {
    return (int)(((x + y) * TILE_HALF_H) >> FIXED_SHIFT);
}

// ---------------------------------------------------------------------------
// Collision
// ---------------------------------------------------------------------------

static int tile_walkable(int col, int row) {
    if (col < 0 || col >= MAP_COLS || row < 0 || row >= MAP_ROWS) return 0;
    if (g_floor_map[row][col] == MAP_VOID) return 0;
    uint8_t obj = g_obj_map[row][col];
    if (obj == 0) return 1;
    int id = obj - 1;
    // Arches are open doorways you can walk through.
    return (id == OBJ_AR_ROW || id == OBJ_AR_COL);
}

static int position_is_free(fixed x, fixed y) {
    int lo_c = TO_INT(x - PLAYER_COLLIDER);
    int lo_r = TO_INT(y - PLAYER_COLLIDER);
    int hi_c = TO_INT(x + PLAYER_COLLIDER);
    int hi_r = TO_INT(y + PLAYER_COLLIDER);
    if (!tile_walkable(lo_c, lo_r)) return 0;
    if (!tile_walkable(hi_c, lo_r)) return 0;
    if (!tile_walkable(lo_c, hi_r)) return 0;
    if (!tile_walkable(hi_c, hi_r)) return 0;
    return 1;
}

// ---------------------------------------------------------------------------
// Blitting
// ---------------------------------------------------------------------------

// Blit a BGR555 sprite (bit 15 = opaque) relative to a world position.
static void blit(uint16_t *buffer, const uint16_t *src, int sw, int sh,
                 int left, int top, int cam_x, int cam_y) {
    int ox = left - cam_x;
    int oy = top - cam_y;

    int sy0 = 0, sy1 = sh;
    if (oy < 0) sy0 = -oy;
    if (oy + sh > SCREEN_H) sy1 = SCREEN_H - oy;
    if (sy0 >= sy1) return;

    int sx0 = 0, sx1 = sw;
    int clip_x = (ox < 0) || (ox + sw > SCREEN_W);
    if (clip_x) {
        if (ox < 0) sx0 = -ox;
        if (ox + sw > SCREEN_W) sx1 = SCREEN_W - ox;
        if (sx0 >= sx1) return;
    }

    for (int y = sy0; y < sy1; y++) {
        const uint16_t *srow = &src[y * sw];
        uint16_t *drow = &buffer[(oy + y) * SCREEN_W + ox];
        int x;
        for (x = sx0; x + 1 < sx1; x += 2) {
            uint16_t a = srow[x];
            uint16_t b = srow[x + 1];
            if (a | b) { // both transparent only when the pair is zero
                if (a & BIT(15)) drow[x] = a;
                if (b & BIT(15)) drow[x + 1] = b;
            }
        }
        if (x < sx1) {
            uint16_t a = srow[x];
            if (a & BIT(15)) drow[x] = a;
        }
    }
}

static void blit_tile(uint16_t *buffer, const uint16_t *src, int w, int h,
                      int cx, int cy, int cam_x, int cam_y) {
    blit(buffer, src, w, h, cx - w / 2, cy - OBJ_ANCHOR_Y, cam_x, cam_y);
}

// Shadow shape/coverage is baked from the 3D asset. Runtime only composites
// that coverage over the actual floor tile beneath it.
static inline uint16_t apply_shadow(uint16_t color, uint8_t coverage) {
    uint32_t keep = 255 - ((uint32_t)coverage * 160) / 255; // max ~63% darkening
    uint32_t r = ((color & 0x1F) * keep) / 255;
    uint32_t g = (((color >> 5) & 0x1F) * keep) / 255;
    uint32_t b = (((color >> 10) & 0x1F) * keep) / 255;
    return (uint16_t)(r | (g << 5) | (b << 10) | BIT(15));
}

static void draw_shadow_mask(uint16_t *buffer, const uint8_t *mask, int sw, int sh,
                             const uint8_t *bounds, int left, int top,
                             int cam_x, int cam_y) {
    int ox = left - cam_x;
    int oy = top - cam_y;
    int sx0 = bounds[0];
    int sy0 = bounds[1];
    int sx1 = sx0 + bounds[2];
    int sy1 = sy0 + bounds[3];
    if (ox + sx0 < 0) sx0 = -ox;
    if (oy + sy0 < 0) sy0 = -oy;
    if (ox + sx1 > SCREEN_W) sx1 = SCREEN_W - ox;
    if (oy + sy1 > SCREEN_H) sy1 = SCREEN_H - oy;
    if (sx0 >= sx1 || sy0 >= sy1) return;

    for (int y = sy0; y < sy1; y++) {
        for (int x = sx0; x < sx1; x++) {
            int pixel = y * sw + x;
            uint8_t packed = mask[pixel >> 1];
            uint8_t coverage = (uint8_t)(((pixel & 1) ? packed >> 4 : packed & 0x0F) * 17);
            uint16_t *dst = &buffer[(oy + y) * SCREEN_W + ox + x];
            if (coverage && *dst != (VOID_COLOR | BIT(15)))
                *dst = apply_shadow(*dst, coverage);
        }
    }
}

// ---------------------------------------------------------------------------
// Floor cache
// ---------------------------------------------------------------------------

static void floor_cache_build(void) {
    for (int i = 0; i < CACHE_W * CACHE_H; i++) {
        s_floor_cache[i] = VOID_COLOR | BIT(15);
    }
    for (int row = 0; row < MAP_ROWS; row++) {
        for (int col = 0; col < MAP_COLS; col++) {
            uint8_t t = g_floor_map[row][col];
            if (t == MAP_VOID) continue;

            const uint16_t *src = g_floor_tiles[t];
            int left = tile_center_x(col, row) - CACHE_X0 - FLOOR_TILE_W / 2;
            int top = tile_center_y(col, row) - CACHE_Y0 - FLOOR_TILE_H / 2;

            // Diamond tiles are copied through a nearest-neighbour expansion so
            // no gap appears between adjacent tiles; overlaps are harmless.
            for (int sy = 0; sy < FLOOR_TILE_H; sy++) {
                int dy = top + sy;
                if (dy < 0 || dy >= CACHE_H) continue;
                const uint16_t *srow = &src[sy * FLOOR_TILE_W];
                uint16_t *drow = &s_floor_cache[dy * CACHE_W];
                for (int sx = 0; sx < FLOOR_TILE_W; sx++) {
                    int dx = left + sx;
                    if (dx < 0 || dx >= CACHE_W) continue;
                    uint16_t c = srow[sx];
                    if (c & BIT(15)) drow[dx] = c;
                }
            }
        }
    }
}

static void draw_floor(uint16_t *buffer, int cam_x, int cam_y) {
    // The camera is clamped to the cache, so this window copy never clips.
    const uint16_t *src = &s_floor_cache[(cam_y - CACHE_Y0) * CACHE_W + (cam_x - CACHE_X0)];
    for (int y = 0; y < SCREEN_H; y++) {
        uint16_t *drow = &buffer[y * SCREEN_W];
        for (int x = 0; x < SCREEN_W; x++) drow[x] = src[x];
        src += CACHE_W;
    }
}

// ---------------------------------------------------------------------------
// Composition
// ---------------------------------------------------------------------------

static void draw_player(uint16_t *buffer, int cam_x, int cam_y) {
    int px = player_screen_x(s_player.x, s_player.y);
    int py = player_screen_y(s_player.x, s_player.y);

    // The ground origin is the centre of each cell (PLAYER_ANCHOR_*).
    const uint16_t *frame = g_player_frames[s_player.dir][s_player.frame];
    blit(buffer, frame, PLAYER_SPRITE_W, PLAYER_SPRITE_H,
         px - PLAYER_ANCHOR_X, py - PLAYER_ANCHOR_Y, cam_x, cam_y);
}

static void render_screen(uint16_t *buffer, int cam_x, int cam_y) {
    draw_floor(buffer, cam_x, cam_y);

    DrawItem items[MAX_DRAW_ITEMS + 1];
    int count = 0;

    for (int row = 0; row < MAP_ROWS; row++) {
        for (int col = 0; col < MAP_COLS; col++) {
            uint8_t obj = g_obj_map[row][col];
            if (obj == 0) continue;

            int cx = tile_center_x(col, row);
            int cy = tile_center_y(col, row);
            int left = cx - OBJ_SPRITE_W / 2 - cam_x;
            int top = cy - OBJ_SPRITE_H / 2 - cam_y;
            if (left >= SCREEN_W || left + OBJ_SPRITE_W <= 0) continue;
            if (top >= SCREEN_H || top + OBJ_SPRITE_H <= 0) continue;
            if (count >= MAX_DRAW_ITEMS) break;

            items[count].depth = (col + row + 1) << 8;
            items[count].sprite = obj - 1;
            items[count].cx = cx;
            items[count].cy = cy;
            count++;
        }
    }

    int psx = player_screen_x(s_player.x, s_player.y);
    int psy = player_screen_y(s_player.x, s_player.y);
    items[count].depth = s_player.x + s_player.y;
    items[count].sprite = -1;
    items[count].cx = psx;
    items[count].cy = psy;
    count++;

    // 1) Composite the baked 3D shadow masks over the floor; sprites then cover them.
    for (int i = 0; i < count; i++) {
        if (items[i].sprite < 0) {
            draw_shadow_mask(buffer, g_player_shadow_masks[s_player.dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_player_shadow_bounds[s_player.dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y);
        } else {
            draw_shadow_mask(buffer, g_obj_shadow_masks[items[i].sprite],
                             OBJ_SHADOW_W, OBJ_SHADOW_H,
                             g_obj_shadow_bounds[items[i].sprite],
                             items[i].cx - OBJ_SHADOW_W / 2,
                             items[i].cy - OBJ_SHADOW_H / 2, cam_x, cam_y);
        }
    }

    // 2) Sprites back-to-front (painter's algorithm, near objects last).
    for (int i = 1; i < count; i++) {
        DrawItem key = items[i];
        int j = i - 1;
        while (j >= 0 && items[j].depth > key.depth) {
            items[j + 1] = items[j];
            j--;
        }
        items[j + 1] = key;
    }

    for (int i = 0; i < count; i++) {
        if (items[i].sprite < 0) {
            draw_player(buffer, cam_x, cam_y);
        } else {
            blit_tile(buffer, g_obj_sprites[items[i].sprite],
                      OBJ_SPRITE_W, OBJ_SPRITE_H,
                      items[i].cx, items[i].cy, cam_x, cam_y);
        }
    }
}

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------

static void present_both_screens(void) {
    DC_FlushRange(s_top_backbuffer, sizeof(s_top_backbuffer));
    dmaCopyWords(1, s_top_backbuffer, s_top_vram, sizeof(s_top_backbuffer));

    u16 *dest_vram = (s_active_vram_bank == 0) ? (u16 *)VRAM_B : (u16 *)VRAM_A;
    DC_FlushRange(s_bot_backbuffer, sizeof(s_bot_backbuffer));
    dmaCopyWords(2, s_bot_backbuffer, dest_vram, sizeof(s_bot_backbuffer));

    swiWaitForVBlank();

    if (s_active_vram_bank == 0) {
        videoSetMode(MODE_FB1);
        s_active_vram_bank = 1;
    } else {
        videoSetMode(MODE_FB0);
        s_active_vram_bank = 0;
    }
}

// ---------------------------------------------------------------------------
// Player
// ---------------------------------------------------------------------------

static void player_init(void) {
    s_player.x = TO_FIXED(MAP_COLS / 2 - 1) + 128; // tile centre
    s_player.y = TO_FIXED(MAP_ROWS / 2 - 1) + 128;
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
}

static void player_update(uint32_t keys) {
    int sdx = 0, sdy = 0; // screen-space input axes
    if (keys & KEY_UP) sdy -= 1;
    if (keys & KEY_DOWN) sdy += 1;
    if (keys & KEY_LEFT) sdx -= 1;
    if (keys & KEY_RIGHT) sdx += 1;

    if (sdx != 0 || sdy != 0) {
        s_player.is_moving = 1;

        if (sdy > 0 && sdx == 0) s_player.dir = DIR_SOUTH;
        else if (sdy > 0 && sdx < 0) s_player.dir = DIR_SOUTHWEST;
        else if (sdy == 0 && sdx < 0) s_player.dir = DIR_WEST;
        else if (sdy < 0 && sdx < 0) s_player.dir = DIR_NORTHWEST;
        else if (sdy < 0 && sdx == 0) s_player.dir = DIR_NORTH;
        else if (sdy < 0 && sdx > 0) s_player.dir = DIR_NORTHEAST;
        else if (sdy == 0 && sdx > 0) s_player.dir = DIR_EAST;
        else s_player.dir = DIR_SOUTHEAST;

        fixed vx = sdx * PLAYER_SPEED;
        fixed vy = sdy * PLAYER_SPEED;
        if (sdx != 0 && sdy != 0) { // normalise diagonals
            vx = vx * 181 / 256;
            vy = vy * 181 / 256;
        }

        // Screen space -> tile space (inverse of the dimetric projection)
        fixed sx = vx / TILE_HALF_W;
        fixed sy = vy / TILE_HALF_H;
        fixed dcol = (sx + sy) >> 1;
        fixed drow = (sy - sx) >> 1;

        if (position_is_free(s_player.x + dcol, s_player.y + drow)) {
            s_player.x += dcol;
            s_player.y += drow;
        } else if (position_is_free(s_player.x + dcol, s_player.y)) {
            s_player.x += dcol;
        } else if (position_is_free(s_player.x, s_player.y + drow)) {
            s_player.y += drow;
        }

        s_player.anim_timer++;
        if (s_player.anim_timer >= ANIM_PERIOD) {
            s_player.anim_timer = 0;
            s_player.frame = (s_player.frame + 1) % PLAYER_NUM_FRAMES;
        }
    } else {
        s_player.is_moving = 0;
        s_player.frame = 0;
        s_player.anim_timer = 0;
    }

    // Camera: the feet sit CAMERA_ANCHOR_Y below the top of the bottom screen;
    // the top screen then shows the dungeon above. Clamped to the floor cache.
    int target_x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    int target_y = player_screen_y(s_player.x, s_player.y) - CAMERA_ANCHOR_Y;

    if (target_x < CACHE_X0) target_x = CACHE_X0;
    if (target_x > CACHE_X0 + CACHE_W - SCREEN_W) target_x = CACHE_X0 + CACHE_W - SCREEN_W;
    if (target_y < CACHE_Y0) target_y = CACHE_Y0;
    if (target_y > CACHE_Y0 + CACHE_H - SCREEN_H) target_y = CACHE_Y0 + CACHE_H - SCREEN_H;

    s_cam_x = target_x;
    s_cam_y = target_y;
}

int main(void) {
    lcdMainOnBottom();
    vramSetBankA(VRAM_A_LCD);
    vramSetBankB(VRAM_B_LCD);
    videoSetMode(MODE_FB0);

    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG);
    s_top_bg = bgInitSub(3, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    s_top_vram = (u16 *)bgGetGfxPtr(s_top_bg);

    floor_cache_build();
    player_init();

    while (1) {
        scanKeys();
        uint32_t keys_held = keysHeld();

        player_update(keys_held);

        render_screen(s_top_backbuffer, s_cam_x, s_cam_y - SCREEN_H);
        render_screen(s_bot_backbuffer, s_cam_x, s_cam_y);

        present_both_screens();
    }

    return 0;
}
