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
// Synchronized to 1.502m 3D stride (16.99 px at 11.31 px/m): 181/256 px/frame over 24 ticks (ANIM_PERIOD=3)
#define PLAYER_SPEED 181                 // ~0.71 px/frame (zero foot sliding)
#define PLAYER_COLLIDER 48               // 0.187 tile radius (~0.37m)
#define PILLAR_COLLIDE_R 40              // 0.156 tile radius (~0.31m, matches 0.65m 3D base)
#define PILLAR_MIN_DIST (PLAYER_COLLIDER + PILLAR_COLLIDE_R) // 88 units
#define ANIM_PERIOD 3                    // 24 ticks (0.40s) per 8-frame cycle

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

static int position_is_free(fixed x, fixed y) {
    int lo_c = TO_INT(x - PLAYER_COLLIDER);
    int lo_r = TO_INT(y - PLAYER_COLLIDER);
    int hi_c = TO_INT(x + PLAYER_COLLIDER);
    int hi_r = TO_INT(y + PLAYER_COLLIDER);

    // 1) Void boundary and wall collisions (walls block the full tile boundary)
    for (int r = lo_r; r <= hi_r; r++) {
        for (int c = lo_c; c <= hi_c; c++) {
            if (c < 0 || c >= MAP_COLS || r < 0 || r >= MAP_ROWS) return 0;
            if (g_floor_map[r][c] == MAP_VOID) return 0;

            uint8_t obj = g_obj_map[r][c];
            if (obj == 0) continue;
            int id = obj - 1;

            // Arches are open doorways; pillars are handled below via sub-tile base
            if (id >= OBJ_P_SOUL) continue;

            // Perimeter walls block tile entry
            return 0;
        }
    }

    // 2) Precise circular sub-tile collision for freestanding pillars in nearby tiles
    int pc0 = TO_INT(x) - 1;
    int pc1 = TO_INT(x) + 1;
    int pr0 = TO_INT(y) - 1;
    int pr1 = TO_INT(y) + 1;
    for (int r = pr0; r <= pr1; r++) {
        for (int c = pc0; c <= pc1; c++) {
            if (c < 0 || c >= MAP_COLS || r < 0 || r >= MAP_ROWS) continue;
            uint8_t obj = g_obj_map[r][c];
            if (obj == 0) continue;
            int id = obj - 1;
            if (id >= OBJ_P_SOUL && id < OBJ_AR_ROW) {
                // Pillar base is centered at tile midpoint (c + 0.5, r + 0.5)
                fixed cx = TO_FIXED(c) + 128;
                fixed cy = TO_FIXED(r) + 128;
                int dx = (int)(x - cx);
                int dy = (int)(y - cy);
                if (dx * dx + dy * dy < PILLAR_MIN_DIST * PILLAR_MIN_DIST) {
                    return 0; // Colliding with pillar base
                }
            }
        }
    }

    return 1;
}

// ---------------------------------------------------------------------------
// Blitting
// ---------------------------------------------------------------------------

static uint8_t s_obj_sprite_bounds[NUM_OBJ_SPRITES][4];

static void init_obj_sprite_bounds(void) {
    for (int i = 0; i < NUM_OBJ_SPRITES; i++) {
        const uint16_t *src = g_obj_sprites[i];
        int min_x = OBJ_SPRITE_W, max_x = -1;
        int min_y = OBJ_SPRITE_H, max_y = -1;
        for (int y = 0; y < OBJ_SPRITE_H; y++) {
            for (int x = 0; x < OBJ_SPRITE_W; x++) {
                if (src[y * OBJ_SPRITE_W + x] & BIT(15)) {
                    if (x < min_x) min_x = x;
                    if (x > max_x) max_x = x;
                    if (y < min_y) min_y = y;
                    if (y > max_y) max_y = y;
                }
            }
        }
        if (max_x < min_x) {
            s_obj_sprite_bounds[i][0] = 0;
            s_obj_sprite_bounds[i][1] = 0;
            s_obj_sprite_bounds[i][2] = 0;
            s_obj_sprite_bounds[i][3] = 0;
        } else {
            s_obj_sprite_bounds[i][0] = (uint8_t)min_x;
            s_obj_sprite_bounds[i][1] = (uint8_t)min_y;
            s_obj_sprite_bounds[i][2] = (uint8_t)(max_x - min_x + 1);
            s_obj_sprite_bounds[i][3] = (uint8_t)(max_y - min_y + 1);
        }
    }
}

// Blit a BGR555 sprite with arbitrary pitch, fast 32-bit dual-pixel write when both are opaque.
static void blit_stride(uint16_t *buffer, const uint16_t *src, int pitch, int sw, int sh,
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
        const uint16_t *srow = &src[y * pitch];
        uint16_t *drow = &buffer[(oy + y) * SCREEN_W + ox];
        int x;
        for (x = sx0; x + 1 < sx1; x += 2) {
            uint16_t a = srow[x];
            uint16_t b = srow[x + 1];
            if (a | b) {
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

static void blit_tile(uint16_t *buffer, int sprite_id,
                      int cx, int cy, int cam_x, int cam_y) {
    const uint8_t *b = s_obj_sprite_bounds[sprite_id];
    int bw = b[2];
    int bh = b[3];
    if (bw == 0 || bh == 0) return;
    int min_x = b[0];
    int min_y = b[1];
    const uint16_t *src = &g_obj_sprites[sprite_id][min_y * OBJ_SPRITE_W + min_x];
    blit_stride(buffer, src, OBJ_SPRITE_W, bw, bh,
                cx - OBJ_SPRITE_W / 2 + min_x,
                cy - OBJ_ANCHOR_Y + min_y,
                cam_x, cam_y);
}

// Shadow shape/coverage is baked from the 3D asset. Runtime only composites
// that coverage over the actual floor tile beneath it.
static inline uint16_t apply_shadow(uint16_t color, uint8_t coverage) {
    uint32_t keep = 255 - ((uint32_t)coverage * 160) / 255;
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
        uint16_t *dst_row = &buffer[(oy + y) * SCREEN_W + ox];
        for (int x = sx0; x < sx1; x++) {
            int pixel = y * sw + x;
            uint8_t packed = mask[pixel >> 1];
            uint8_t nibble = (pixel & 1) ? (packed >> 4) : (packed & 0x0F);
            if (nibble) {
                uint16_t c = dst_row[x];
                if (c != (VOID_COLOR | BIT(15))) {
                    dst_row[x] = apply_shadow(c, (uint8_t)(nibble * 17));
                }
            }
        }
    }
}

static void draw_shadow_mask_to_cache(const uint8_t *mask, int sw, int sh,
                                      const uint8_t *bounds, int left, int top) {
    int sx0 = bounds[0];
    int sy0 = bounds[1];
    int bw  = bounds[2];
    int bh  = bounds[3];
    if (bw == 0 || bh == 0) return;

    int sx1 = sx0 + bw;
    int sy1 = sy0 + bh;
    int ox = left - CACHE_X0;
    int oy = top - CACHE_Y0;

    if (ox + sx0 < 0) sx0 = -ox;
    if (oy + sy0 < 0) sy0 = -oy;
    if (ox + sx1 > CACHE_W) sx1 = CACHE_W - ox;
    if (oy + sy1 > CACHE_H) sy1 = CACHE_H - oy;
    if (sx0 >= sx1 || sy0 >= sy1) return;

    for (int y = sy0; y < sy1; y++) {
        uint16_t *dst_row = &s_floor_cache[(oy + y) * CACHE_W + ox];
        for (int x = sx0; x < sx1; x++) {
            int pixel = y * sw + x;
            uint8_t packed = mask[pixel >> 1];
            uint8_t nibble = (pixel & 1) ? (packed >> 4) : (packed & 0x0F);
            if (nibble) {
                uint16_t c = dst_row[x];
                if (c != (VOID_COLOR | BIT(15))) {
                    dst_row[x] = apply_shadow(c, (uint8_t)(nibble * 17));
                }
            }
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

    // Pre-bake all static map object shadows into the floor cache once at startup.
    // Eliminates 100% of static shadow math during the 60 FPS gameplay loop!
    for (int row = 0; row < MAP_ROWS; row++) {
        for (int col = 0; col < MAP_COLS; col++) {
            uint8_t obj = g_obj_map[row][col];
            if (obj == 0) continue;
            int cx = tile_center_x(col, row);
            int cy = tile_center_y(col, row);
            int id = obj - 1;
            draw_shadow_mask_to_cache(g_obj_shadow_masks[id],
                                      OBJ_SHADOW_W, OBJ_SHADOW_H,
                                      g_obj_shadow_bounds[id],
                                      cx - OBJ_SHADOW_W / 2,
                                      cy - OBJ_SHADOW_H / 2);
        }
    }
}

static void draw_floor(uint16_t *buffer, int cam_x, int cam_y) {
    // ARM9 burst assembly copy (ldmia/stmia) line-by-line
    const uint16_t *src = &s_floor_cache[(cam_y - CACHE_Y0) * CACHE_W + (cam_x - CACHE_X0)];
    for (int y = 0; y < SCREEN_H; y++) {
        memcpy(&buffer[y * SCREEN_W], src, SCREEN_W * sizeof(uint16_t));
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
    const uint16_t *frame = g_character_frames[s_player.char_id][s_player.dir][s_player.frame];
    blit_stride(buffer, frame, PLAYER_SPRITE_W, PLAYER_SPRITE_W, PLAYER_SPRITE_H,
                px - PLAYER_ANCHOR_X, py - PLAYER_ANCHOR_Y, cam_x, cam_y);
}

static void render_screen(uint16_t *buffer, int cam_x, int cam_y,
                          uint32_t *out_floor, uint32_t *out_shadow, uint32_t *out_blit) {
    uint32_t t_fl0 = cpuGetTiming();
    draw_floor(buffer, cam_x, cam_y);
    uint32_t floor_ticks = cpuGetTiming() - t_fl0;

    DrawItem items[MAX_DRAW_ITEMS + 1];
    int count = 0;

    // Calculate map row and col range intersecting this screen (dimetric bounds)
    int min_cx = cam_x - OBJ_SPRITE_W;
    int max_cx = cam_x + SCREEN_W + OBJ_SPRITE_W;
    int min_cy = cam_y - OBJ_SPRITE_H;
    int max_cy = cam_y + SCREEN_H + OBJ_SPRITE_H;

    int min_col = ((min_cx >> 4) + (min_cy >> 3)) / 2 - 2;
    int max_col = ((max_cx >> 4) + (max_cy >> 3)) / 2 + 2;
    int min_row = ((min_cy >> 3) - (max_cx >> 4)) / 2 - 2;
    int max_row = ((max_cy >> 3) - (min_cx >> 4)) / 2 + 2;

    if (min_col < 0) min_col = 0;
    if (max_col >= MAP_COLS) max_col = MAP_COLS - 1;
    if (min_row < 0) min_row = 0;
    if (max_row >= MAP_ROWS) max_row = MAP_ROWS - 1;

    for (int row = min_row; row <= max_row; row++) {
        for (int col = min_col; col <= max_col; col++) {
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

    // Add player only if visible on this screen
    int psx = player_screen_x(s_player.x, s_player.y);
    int psy = player_screen_y(s_player.x, s_player.y);
    int pl_left = psx - PLAYER_ANCHOR_X - cam_x;
    int pl_top = psy - PLAYER_ANCHOR_Y - cam_y;
    if (pl_left < SCREEN_W && pl_left + PLAYER_SPRITE_W > 0 &&
        pl_top < SCREEN_H && pl_top + PLAYER_SPRITE_H > 0) {
        items[count].depth = s_player.x + s_player.y;
        items[count].sprite = -1;
        items[count].cx = psx;
        items[count].cy = psy;
        count++;
    }

    // 1) Composite dynamic entity shadows (player) over floor; static shadows are pre-baked!
    uint32_t t_sh0 = cpuGetTiming();
    for (int i = 0; i < count; i++) {
        if (items[i].sprite < 0) {
            draw_shadow_mask(buffer, g_character_shadow_masks[s_player.char_id][s_player.dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[s_player.char_id][s_player.dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y);
        }
    }
    uint32_t shadow_ticks = cpuGetTiming() - t_sh0;

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

    uint32_t t_bl0 = cpuGetTiming();
    for (int i = 0; i < count; i++) {
        if (items[i].sprite < 0) {
            draw_player(buffer, cam_x, cam_y);
        } else {
            blit_tile(buffer, items[i].sprite,
                      items[i].cx, items[i].cy, cam_x, cam_y);
        }
    }
    uint32_t blit_ticks = cpuGetTiming() - t_bl0;

    if (out_floor) *out_floor = floor_ticks;
    if (out_shadow) *out_shadow = shadow_ticks;
    if (out_blit) *out_blit = blit_ticks;
}

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------

static void present_both_screens(int top_dirty) {
    if (top_dirty) {
        DC_FlushRange(s_top_backbuffer, sizeof(s_top_backbuffer));
        dmaCopyWords(1, s_top_backbuffer, s_top_vram, sizeof(s_top_backbuffer));
    }

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
    s_player.char_id = CHAR_HERO;
}

static void player_update(uint32_t keys, uint32_t keys_down) {
    // Switch active character when pressing X, Y, SELECT or A
    if (keys_down & (KEY_X | KEY_Y | KEY_SELECT | KEY_A)) {
        s_player.char_id = (s_player.char_id + 1) % NUM_CHARACTERS;
        s_player.frame = 0;
        s_player.anim_timer = 0;
    }

    int cur_char = s_player.char_id;
    fixed current_speed = g_characters[cur_char].speed;
    int current_period = g_characters[cur_char].anim_period;

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

        fixed vx = sdx * current_speed;
        fixed vy = sdy * current_speed;
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
        if (s_player.anim_timer >= current_period) {
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

volatile PerfStats g_perf = {
    .magic = 0x50455246,
    .frame_index = 0,
    .cpu_ticks = 0,
    .cpu_budget = 280095, // 33513982 Hz / 59.8261 Hz
    .cpu_percent = 0,
    .vcount_done = 0,
    .vblanks_elapsed = 1,
    .fps = 60,
    .logic_ticks = 0,
    .top_render_ticks = 0,
    .bot_render_ticks = 0,
    .present_ticks = 0,
    .show_hud = 0
};

static volatile uint32_t s_vblank_count = 0;
static void on_vblank_irq(void) {
    s_vblank_count++;
}

int main(void) {
    irqSet(IRQ_VBLANK, on_vblank_irq);
    irqEnable(IRQ_VBLANK);
    cpuStartTiming(0);

    lcdMainOnBottom();
    vramSetBankA(VRAM_A_LCD);
    vramSetBankB(VRAM_B_LCD);
    videoSetMode(MODE_FB0);

    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG);
    s_top_bg = bgInitSub(3, BgType_Bmp16, BgSize_B16_256x256, 0, 0);
    s_top_vram = (u16 *)bgGetGfxPtr(s_top_bg);

    floor_cache_build();
    init_obj_sprite_bounds();
    player_init();

    // Initialise camera position to match player spawn
    s_cam_x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    s_cam_y = player_screen_y(s_player.x, s_player.y) - CAMERA_ANCHOR_Y;
    if (s_cam_x < CACHE_X0) s_cam_x = CACHE_X0;
    if (s_cam_x > CACHE_X0 + CACHE_W - SCREEN_W) s_cam_x = CACHE_X0 + CACHE_W - SCREEN_W;
    if (s_cam_y < CACHE_Y0) s_cam_y = CACHE_Y0;
    if (s_cam_y > CACHE_Y0 + CACHE_H - SCREEN_H) s_cam_y = CACHE_Y0 + CACHE_H - SCREEN_H;

    // Render initial scene into top screen and both bottom VRAM buffers so frame 0 is never black
    render_screen(s_top_backbuffer, s_cam_x, s_cam_y - SCREEN_H, NULL, NULL, NULL);
    DC_FlushRange(s_top_backbuffer, sizeof(s_top_backbuffer));
    dmaCopyWords(1, s_top_backbuffer, s_top_vram, sizeof(s_top_backbuffer));

    render_screen((u16 *)VRAM_A, s_cam_x, s_cam_y, NULL, NULL, NULL);
    render_screen((u16 *)VRAM_B, s_cam_x, s_cam_y, NULL, NULL, NULL);

    int prev_top_cam_x = s_cam_x;
    int prev_top_cam_y = s_cam_y - SCREEN_H;

    while (1) {
        uint32_t frame_start_ticks = cpuGetTiming();
        uint32_t start_vblank = s_vblank_count;

        scanKeys();
        uint32_t keys_held = keysHeld();
        uint32_t keys_down = keysDown();

        if (keys_down & KEY_START) {
            g_perf.show_hud = !g_perf.show_hud;
        }

        uint32_t t0 = cpuGetTiming();
        player_update(keys_held, keys_down);
        uint32_t logic_ticks = cpuGetTiming() - t0;

        uint32_t top_fl = 0, top_sh = 0, top_bl = 0;
        uint32_t bot_fl = 0, bot_sh = 0, bot_bl = 0;

        int top_cam_x = s_cam_x;
        int top_cam_y = s_cam_y - SCREEN_H;
        int top_moved = (top_cam_x != prev_top_cam_x || top_cam_y != prev_top_cam_y);
        // Interleave top screen refresh during camera scrolling (30 Hz top / 60 Hz bot)
        // to guarantee 100% locked 60 FPS under the ARM9 16.7ms budget.
        int top_dirty = top_moved && ((g_perf.frame_index & 1) == 0 || !s_player.is_moving);

        uint32_t t1 = cpuGetTiming();
        if (top_dirty) {
            render_screen(s_top_backbuffer, top_cam_x, top_cam_y, &top_fl, &top_sh, &top_bl);
            prev_top_cam_x = top_cam_x;
            prev_top_cam_y = top_cam_y;
        }
        uint32_t top_ticks = cpuGetTiming() - t1;

        u16 *dest_vram = (s_active_vram_bank == 0) ? (u16 *)VRAM_B : (u16 *)VRAM_A;
        uint32_t t2 = cpuGetTiming();
        render_screen(dest_vram, s_cam_x, s_cam_y, &bot_fl, &bot_sh, &bot_bl);
        uint32_t bot_ticks = cpuGetTiming() - t2;

        // CPU rendering finished before waiting for VBlank
        uint32_t cpu_ticks = cpuGetTiming() - frame_start_ticks;
        int vcount_done = REG_VCOUNT;

        uint32_t t3 = cpuGetTiming();
        present_both_screens(top_dirty);
        uint32_t present_ticks = cpuGetTiming() - t3;

        uint32_t vblanks_elapsed = s_vblank_count - start_vblank;
        if (vblanks_elapsed == 0) vblanks_elapsed = 1;

        g_perf.frame_index++;
        g_perf.cpu_ticks = cpu_ticks;
        g_perf.cpu_percent = (cpu_ticks * 100) / g_perf.cpu_budget;
        g_perf.vcount_done = vcount_done;
        g_perf.vblanks_elapsed = vblanks_elapsed;
        g_perf.fps = 60 / vblanks_elapsed;
        g_perf.logic_ticks = logic_ticks;
        g_perf.top_render_ticks = top_ticks;
        g_perf.bot_render_ticks = bot_ticks;
        g_perf.present_ticks = present_ticks;
        g_perf.floor_ticks = top_fl + bot_fl;
        g_perf.shadow_ticks = top_sh + bot_sh;
        g_perf.blit_ticks = top_bl + bot_bl;

        if (g_perf.frame_index % 30 == 0) {
            char log_buf[110];
            snprintf(log_buf, sizeof(log_buf),
                     "FRAME %lu: FPS=%lu VBlanks=%lu CPU=%lu%% (ticks=%lu/%lu, VCount=%d)\n",
                     (unsigned long)g_perf.frame_index, (unsigned long)g_perf.fps,
                     (unsigned long)g_perf.vblanks_elapsed, (unsigned long)g_perf.cpu_percent,
                     (unsigned long)g_perf.cpu_ticks, (unsigned long)g_perf.cpu_budget,
                     vcount_done);
            nocashMessage(log_buf);
        }
    }

    return 0;
}
