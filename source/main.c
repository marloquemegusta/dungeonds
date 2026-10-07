#include "game.h"
#include "dungeon_data.h"
#include "player_sprite.h"
#include "dungeon_bg_tiles.h"

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
// Hardware Background Scrolling (Option 1):
// The static floor, perimeter walls, and static shadows are converted into
// 8bpp tiles streamed to the NDS 2D Background Engine. Each frame, only a 32x24
// tilemap window is streamed to VRAM (~1.5 KB via ARM burst/DMA), reducing
// floor rendering time from 7.2 ms down to ~0.05 ms.
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

// World-sized floor cache bounds (origin = world pixel (CACHE_X0, CACHE_Y0))
#define CACHE_X0 (-((MAP_ROWS - 1) * TILE_HALF_W) - TILE_HALF_W)
#define CACHE_Y0 (-OBJ_SPRITE_H)
#define CACHE_W  ((((MAP_COLS - 1) * TILE_HALF_W) + TILE_HALF_W) - CACHE_X0)
#define CACHE_H  (((((MAP_COLS - 1) + (MAP_ROWS - 1)) * TILE_HALF_H) + TILE_HALF_H) - CACHE_Y0)

// Hardware BG IDs and pointers
static int s_top_bg = 0;
static int s_bot_bg = 0;
static u16 *s_top_map_ptr = NULL;
static u16 *s_bot_map_ptr = NULL;
static u16 *s_top_vram = NULL;
static u16 *s_bot_vram_buf0 = NULL;
static u16 *s_bot_vram_buf1 = NULL;
static int s_active_vram_bank = 0;

// Dual-buffered rendering buffers for top and bottom screens (cleared transparently for entities)
static uint16_t s_top_screen_buf[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));
static uint16_t s_bot_screen_buf[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));

static Player s_player;
static int s_cam_x = 0;
static int s_cam_y = 0;

#define MAX_ENEMIES 10
typedef struct {
    fixed x;
    fixed y;
    int dir;
    int frame;
    int anim_timer;
    int char_id;
    int active;
    int step_count;
    int step_limit;
} Enemy;

static Enemy s_enemies[MAX_ENEMIES];

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
                // Pillar base is centered at tile projection origin (c, r)
                fixed cx = TO_FIXED(c);
                fixed cy = TO_FIXED(r);
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
static uint8_t s_char_frame_bounds[NUM_CHARACTERS][PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];

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

    for (int c = 0; c < NUM_CHARACTERS; c++) {
        for (int d = 0; d < PLAYER_NUM_DIRS; d++) {
            for (int f = 0; f < PLAYER_NUM_FRAMES; f++) {
                const uint16_t *src = g_character_frames[c][d][f];
                int min_x = PLAYER_SPRITE_W, max_x = -1;
                int min_y = PLAYER_SPRITE_H, max_y = -1;
                for (int y = 0; y < PLAYER_SPRITE_H; y++) {
                    for (int x = 0; x < PLAYER_SPRITE_W; x++) {
                        if (src[y * PLAYER_SPRITE_W + x] & BIT(15)) {
                            if (x < min_x) min_x = x;
                            if (x > max_x) max_x = x;
                            if (y < min_y) min_y = y;
                            if (y > max_y) max_y = y;
                        }
                    }
                }
                if (max_x < min_x) {
                    s_char_frame_bounds[c][d][f][0] = 0;
                    s_char_frame_bounds[c][d][f][1] = 0;
                    s_char_frame_bounds[c][d][f][2] = 0;
                    s_char_frame_bounds[c][d][f][3] = 0;
                } else {
                    s_char_frame_bounds[c][d][f][0] = (uint8_t)min_x;
                    s_char_frame_bounds[c][d][f][1] = (uint8_t)min_y;
                    s_char_frame_bounds[c][d][f][2] = (uint8_t)(max_x - min_x + 1);
                    s_char_frame_bounds[c][d][f][3] = (uint8_t)(max_y - min_y + 1);
                }
            }
        }
    }
}

// Blit a BGR555 sprite with arbitrary pitch, fast 32-bit dual-pixel write when both are opaque.
__attribute__((target("arm"), noinline))
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
        int x = sx0;

        // Align drow + x to 32-bit (4-byte) boundary if needed
        if (((uintptr_t)&drow[x] & 2) && x < sx1) {
            uint16_t a = srow[x];
            if (a & BIT(15)) drow[x] = a;
            x++;
        }

        uint32_t *d32 = (uint32_t *)&drow[x];
        for (; x + 1 < sx1; x += 2, d32++) {
            uint16_t a = srow[x];
            uint16_t b = srow[x + 1];
            uint32_t test = (a | b);
            if (!test) continue;
            if ((a & BIT(15)) && (b & BIT(15))) {
                *d32 = (uint32_t)a | ((uint32_t)b << 16);
            } else if (a & BIT(15)) {
                drow[x] = a;
            } else if (b & BIT(15)) {
                drow[x + 1] = b;
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

// Shadow shape/coverage is baked from the 3D asset.
static inline uint16_t apply_shadow(uint16_t color, uint8_t coverage) {
    uint32_t keep = 255 - ((uint32_t)coverage * 160) / 255;
    uint32_t r = ((color & 0x1F) * keep) / 255;
    uint32_t g = (((color >> 5) & 0x1F) * keep) / 255;
    uint32_t b = (((color >> 10) & 0x1F) * keep) / 255;
    return (uint16_t)(r | (g << 5) | (b << 10) | BIT(15));
}

// Fast bitwise approximation: 50% shadow darkening using RGB channel masks in 1 cycle!
static inline uint16_t apply_shadow_fast(uint16_t color) {
    // (color & 0x7BDE) >> 1 darkens 15-bit RGB by exactly 50% without channel crosstalk
    return ((color & 0x7BDE) >> 1) | BIT(15);
}

__attribute__((target("arm"), noinline))
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
        int row_offset = y * sw;
        for (int x = sx0; x < sx1; x++) {
            int pixel = row_offset + x;
            uint8_t packed = mask[pixel >> 1];
            uint8_t nibble = (pixel & 1) ? (packed >> 4) : (packed & 0x0F);
            if (nibble >= 4) {
                uint16_t c = dst_row[x];
                if (c != (VOID_COLOR | BIT(15))) {
                    dst_row[x] = apply_shadow_fast(c);
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Hardware Background Tilemap Streaming
// ---------------------------------------------------------------------------

// Stream the 32x25 tilemap window into the 32x32 hardware text background map,
// and configure sub-tile fine scrolling directly via hardware scroll registers.
// Window copy size: 32 cols x 25 rows = 800 entries (1600 bytes) ~20-30 us.
static void update_screen_hardware_bg(int is_sub, u16 *map_ptr, int cam_x, int cam_y) {
    int rel_x = cam_x - CACHE_X0;
    int rel_y = cam_y - CACHE_Y0;

    int tile_x = rel_x >> 3;
    int tile_y = rel_y >> 3;
    int fine_x = rel_x & 7;
    int fine_y = rel_y & 7;

    if (is_sub) {
        REG_BG1HOFS_SUB = fine_x;
        REG_BG1VOFS_SUB = fine_y;
    } else {
        REG_BG1HOFS = fine_x;
        REG_BG1VOFS = fine_y;
    }

    int rows_to_copy = 25;
    for (int ty = 0; ty < rows_to_copy; ty++) {
        int my = tile_y + ty;
        u16 *dst_row = &map_ptr[ty * 32];
        if (my >= 0 && my < DUNGEON_BG_MAP_HEIGHT_TILES) {
            const u16 *src_map_row = g_dungeon_bg_map[my];
            for (int tx = 0; tx < 32; tx++) {
                int mx = tile_x + tx;
                if (mx >= 0 && mx < DUNGEON_BG_MAP_WIDTH_TILES) {
                    dst_row[tx] = src_map_row[mx];
                } else {
                    dst_row[tx] = 0;
                }
            }
        } else {
            for (int tx = 0; tx < 32; tx++) {
                dst_row[tx] = 0;
            }
        }
    }
}


// ---------------------------------------------------------------------------
// Composition
// ---------------------------------------------------------------------------

static void draw_player(uint16_t *buffer, int cam_x, int cam_y) {
    int px = player_screen_x(s_player.x, s_player.y);
    int py = player_screen_y(s_player.x, s_player.y);

    const uint8_t *b = s_char_frame_bounds[s_player.char_id][s_player.dir][s_player.frame];
    int bw = b[2];
    int bh = b[3];
    if (bw == 0 || bh == 0) return;
    int min_x = b[0];
    int min_y = b[1];

    const uint16_t *frame = &g_character_frames[s_player.char_id][s_player.dir][s_player.frame][min_y * PLAYER_SPRITE_W + min_x];
    blit_stride(buffer, frame, PLAYER_SPRITE_W, bw, bh,
                px - PLAYER_ANCHOR_X + min_x, py - PLAYER_ANCHOR_Y + min_y, cam_x, cam_y);
}

static void draw_enemy(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
    int px = player_screen_x(e->x, e->y);
    int py = player_screen_y(e->x, e->y);

    const uint8_t *b = s_char_frame_bounds[e->char_id][e->dir][e->frame];
    int bw = b[2];
    int bh = b[3];
    if (bw == 0 || bh == 0) return;
    int min_x = b[0];
    int min_y = b[1];

    const uint16_t *frame = &g_character_frames[e->char_id][e->dir][e->frame][min_y * PLAYER_SPRITE_W + min_x];
    blit_stride(buffer, frame, PLAYER_SPRITE_W, bw, bh,
                px - PLAYER_ANCHOR_X + min_x, py - PLAYER_ANCHOR_Y + min_y, cam_x, cam_y);
}

static void render_screen(uint16_t *buffer, int cam_x, int cam_y,
                          uint32_t *out_floor, uint32_t *out_shadow, uint32_t *out_blit) {
    if (out_floor) *out_floor = 0; // Hardware background handles floor scrolling in ~0.03 ms!

    DrawItem items[MAX_DRAW_ITEMS + 1];
    int count = 0;

    // Only freestanding pillars (obj > 24) need depth-sorted sprite rendering.
    // Perimeter walls (obj <= 24) are pre-baked into the hardware background!
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
            if (obj <= 24) continue; // Skip empty tiles and perimeter walls (already in hardware BG)

            int cx = tile_center_x(col, row);
            int cy = tile_center_y(col, row);
            int left = cx - OBJ_SPRITE_W / 2 - cam_x;
            int top = cy - OBJ_SPRITE_H / 2 - cam_y;
            if (left >= SCREEN_W || left + OBJ_SPRITE_W <= 0) continue;
            if (top >= SCREEN_H || top + OBJ_SPRITE_H <= 0) continue;
            if (count >= MAX_DRAW_ITEMS) break;

            items[count].depth = (col + row) << 8;
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
        if (count < MAX_DRAW_ITEMS) {
            items[count].depth = s_player.x + s_player.y;
            items[count].sprite = -1;
            items[count].cx = psx;
            items[count].cy = psy;
            count++;
        }
    }

    // Add enemies only if visible on this screen
    for (int e_idx = 0; e_idx < MAX_ENEMIES; e_idx++) {
        if (!s_enemies[e_idx].active) continue;
        int esx = player_screen_x(s_enemies[e_idx].x, s_enemies[e_idx].y);
        int esy = player_screen_y(s_enemies[e_idx].x, s_enemies[e_idx].y);
        int e_left = esx - PLAYER_ANCHOR_X - cam_x;
        int e_top = esy - PLAYER_ANCHOR_Y - cam_y;
        if (e_left < SCREEN_W && e_left + PLAYER_SPRITE_W > 0 &&
            e_top < SCREEN_H && e_top + PLAYER_SPRITE_H > 0) {
            if (count < MAX_DRAW_ITEMS) {
                items[count].depth = s_enemies[e_idx].x + s_enemies[e_idx].y;
                items[count].sprite = -2 - e_idx;
                items[count].cx = esx;
                items[count].cy = esy;
                count++;
            }
        }
    }

    // Clear buffer (0 = transparent pixel) so hardware BG shows underneath
    dmaFillWords(0, buffer, SCREEN_W * SCREEN_H * 2);

    // 1) Composite dynamic entity shadows (player & enemies)
    uint32_t t_sh0 = cpuGetTiming();
    for (int i = 0; i < count; i++) {
        if (items[i].sprite == -1) {
            draw_shadow_mask(buffer, g_character_shadow_masks[s_player.char_id][s_player.dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[s_player.char_id][s_player.dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y);
        } else if (items[i].sprite <= -2) {
            int e_idx = -2 - items[i].sprite;
            const Enemy *e = &s_enemies[e_idx];
            draw_shadow_mask(buffer, g_character_shadow_masks[e->char_id][e->dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[e->char_id][e->dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y);
        }
    }
    uint32_t shadow_ticks = cpuGetTiming() - t_sh0;

    // 2) Sprites back-to-front (painter's algorithm)
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
        int sp = items[i].sprite;
        if (sp >= 0) {
            blit_tile(buffer, sp, items[i].cx, items[i].cy, cam_x, cam_y);
        } else if (sp == -1) {
            draw_player(buffer, cam_x, cam_y);
        } else {
            draw_enemy(buffer, &s_enemies[-2 - sp], cam_x, cam_y);
        }
    }
    uint32_t blit_ticks = cpuGetTiming() - t_bl0;

    if (out_shadow) *out_shadow = shadow_ticks;
    if (out_blit) *out_blit = blit_ticks;
}

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------

static void present_both_screens(void) {
    // Top screen copy: dmaCopyWords to s_top_vram
    dmaCopyWords(3, s_top_screen_buf, s_top_vram, SCREEN_W * SCREEN_H * 2);

    swiWaitForVBlank();

    // Bottom screen page-flip: switch mapBase between 8 (VRAM_A) and 16 (VRAM_B)
    if (s_active_vram_bank == 0) {
        bgSetMapBase(s_bot_bg, 16); // Display VRAM_B (slot 2 = 0x06040000)
        s_active_vram_bank = 1;
    } else {
        bgSetMapBase(s_bot_bg, 8);  // Display VRAM_A (slot 1 = 0x06020000)
        s_active_vram_bank = 0;
    }
}

// ---------------------------------------------------------------------------
// Enemies
// ---------------------------------------------------------------------------

static void enemies_init(void) {
    // Spawn 10 enemies in the central room around player (col 18, row 18)
    // 8 Skeletons patrolling, 2 Chargers roaming
    static const struct {
        int dcol, drow, char_id, dir;
    } spawn_defs[MAX_ENEMIES] = {
        { -2, -1, CHAR_SKELETON, DIR_SOUTHEAST },
        {  2, -1, CHAR_SKELETON, DIR_SOUTHWEST },
        { -1,  2, CHAR_SKELETON, DIR_NORTHWEST },
        {  1,  2, CHAR_SKELETON, DIR_NORTHEAST },
        { -2, -2, CHAR_CHARGER,  DIR_EAST },
        {  2, -2, CHAR_CHARGER,  DIR_WEST },
        { -3,  0, CHAR_SKELETON, DIR_EAST },
        {  3,  0, CHAR_SKELETON, DIR_WEST },
        {  0, -2, CHAR_SKELETON, DIR_SOUTH },
        {  0,  2, CHAR_SKELETON, DIR_NORTH }
    };

    fixed center_col = TO_FIXED(MAP_COLS / 2 - 1);
    fixed center_row = TO_FIXED(MAP_ROWS / 2 - 1);

    for (int i = 0; i < MAX_ENEMIES; i++) {
        s_enemies[i].x = center_col + TO_FIXED(spawn_defs[i].dcol);
        s_enemies[i].y = center_row + TO_FIXED(spawn_defs[i].drow);
        s_enemies[i].dir = spawn_defs[i].dir;
        s_enemies[i].frame = (i * 3) % PLAYER_NUM_FRAMES;
        s_enemies[i].anim_timer = 0;
        s_enemies[i].char_id = spawn_defs[i].char_id;
        s_enemies[i].active = 1;
        s_enemies[i].step_count = 0;
        s_enemies[i].step_limit = 60 + (i * 15);
    }
}

static void enemies_update(void) {
    // Screen-space direction vectors (sdx, sdy) for DIR_SOUTH .. DIR_SOUTHEAST
    static const int dir_dx[8] = { 0, -1, -1, -1,  0,  1, 1, 1 };
    static const int dir_dy[8] = { 1,  1,  0, -1, -1, -1, 0, 1 };

    for (int i = 0; i < MAX_ENEMIES; i++) {
        Enemy *e = &s_enemies[i];
        if (!e->active) continue;

        fixed spd = g_characters[e->char_id].speed;
        int anim_period = g_characters[e->char_id].anim_period;

        int sdx = dir_dx[e->dir];
        int sdy = dir_dy[e->dir];
        fixed vx = sdx * spd;
        fixed vy = sdy * spd;
        if (sdx != 0 && sdy != 0) {
            vx = (vx * 181) >> 8;
            vy = (vy * 181) >> 8;
        }

        fixed dcol = (vx + (vy << 1)) / (TILE_HALF_W * 2);
        fixed drow = ((vy << 1) - vx) / (TILE_HALF_W * 2);

        if (position_is_free(e->x + dcol, e->y + drow)) {
            e->x += dcol;
            e->y += drow;
        } else {
            // Pick next direction on collision
            e->dir = (e->dir + 3) & 7;
            e->step_count = 0;
        }

        e->step_count++;
        if (e->step_count >= e->step_limit) {
            e->step_count = 0;
            e->dir = (e->dir + 1 + (i & 3)) & 7;
        }

        e->anim_timer++;
        if (e->anim_timer >= anim_period) {
            e->anim_timer = 0;
            e->frame = (e->frame + 1) % PLAYER_NUM_FRAMES;
        }
    }
}

// ---------------------------------------------------------------------------
// Player
// ---------------------------------------------------------------------------

static void player_init(void) {
    s_player.x = TO_FIXED(MAP_COLS / 2 - 1); // tile centre (col, row)
    s_player.y = TO_FIXED(MAP_ROWS / 2 - 1);
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
    s_player.char_id = CHAR_HERO;

    enemies_init();
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
            vx = (vx * 181) >> 8;
            vy = (vy * 181) >> 8;
        }

        // Screen space -> tile space (inverse of the dimetric projection)
        // sx = vx / TILE_HALF_W, sy = vy / TILE_HALF_H
        // dcol = (sx + sy) / 2 = (vx + 2*vy) / 32
        // drow = (sy - sx) / 2 = (2*vy - vx) / 32
        fixed dcol = (vx + (vy << 1)) / (TILE_HALF_W * 2);
        fixed drow = ((vy << 1) - vx) / (TILE_HALF_W * 2);

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

    // Main Engine (Bottom Screen): Mode 5
    // Pure standard mapping without DISPCNT offsets (zero-shift):
    // Slot 0 (0x06000000 .. 0x06020000, 128 KB): VRAM_D for BG1 Text8bpp (tileBase 0, mapBase 16 = 0x06008000)
    // Slot 1 (0x06020000 .. 0x06040000, 128 KB): VRAM_A for BG2 Bmp16 Buffer 0 (mapBase 8 = 0x06020000)
    // Slot 2 (0x06040000 .. 0x06060000, 128 KB): VRAM_B for BG2 Bmp16 Buffer 1 (mapBase 16 = 0x06040000)
    videoSetMode(MODE_5_2D);
    vramSetBankD(VRAM_D_MAIN_BG_0x06000000); // 128 KB for BG1 Text8bpp in slot 0
    vramSetBankA(VRAM_A_MAIN_BG_0x06020000); // 128 KB for BG2 Bmp16 buffer 0 in slot 1
    vramSetBankB(VRAM_B_MAIN_BG_0x06040000); // 128 KB for BG2 Bmp16 buffer 1 in slot 2

    // Pointers to the two double-buffered VRAM surfaces in CPU address space:
    s_bot_vram_buf0 = (u16 *)0x06020000;
    s_bot_vram_buf1 = (u16 *)0x06040000;

    // Load Background Palette to Main and Sub engines
    dmaCopyWords(3, g_dungeon_bg_palette, BG_PALETTE, DUNGEON_BG_PALETTE_SIZE * 2);
    dmaCopyWords(3, g_dungeon_bg_palette, BG_PALETTE_SUB, DUNGEON_BG_PALETTE_SIZE * 2);

    // Initialize Main BG1 (Hardware Tiled Floor)
    // tileBase 0 = 0x06000000 (30 KB tiles), mapBase 16 = 0x06008000 (2 KB map)
    int bot_hw_bg = bgInit(1, BgType_Text8bpp, BgSize_T_256x256, 16, 0);
    bgSetPriority(bot_hw_bg, 3); // Lowest priority (drawn behind entities)
    s_bot_map_ptr = bgGetMapPtr(bot_hw_bg);
    u16 *bot_tile_ptr = bgGetGfxPtr(bot_hw_bg);
    dmaCopyWords(3, g_dungeon_bg_tiles, bot_tile_ptr, sizeof(g_dungeon_bg_tiles));

    // Initialize Main BG2 (Double-buffered 16-bit Bitmap for Entities & dynamic shadows)
    // Initially displays Buffer 0 (mapBase 8 = 0x06020000)
    s_bot_bg = bgInit(2, BgType_Bmp16, BgSize_B16_256x256, 8, 0);
    bgSetPriority(s_bot_bg, 0); // High priority (drawn on top of BG1)
    s_active_vram_bank = 0;

    // Sub Engine (Top Screen): Mode 5
    // VRAM_C (128 KB) at 0x06200000 cleanly split:
    // BG1 Text8bpp: tileBase 0 (0x06200000, 480 tiles * 64B = 30 KB), mapBase 15 (0x06207800, 2 KB)
    // BG2 Bmp16:    mapBase 2 (0x06208000, 256x192x2 = 96 KB)
    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG_0x06200000); // 128 KB for Sub BG (contains both BG1 and BG2)

    // Initialize Sub BG1 (Hardware Tiled Floor)
    int top_hw_bg = bgInitSub(1, BgType_Text8bpp, BgSize_T_256x256, 15, 0);
    bgSetPriority(top_hw_bg, 3);
    s_top_map_ptr = bgGetMapPtr(top_hw_bg);
    u16 *top_tile_ptr = bgGetGfxPtr(top_hw_bg);
    dmaCopyWords(3, g_dungeon_bg_tiles, top_tile_ptr, sizeof(g_dungeon_bg_tiles));

    // Initialize Sub BG2 (16-bit Bitmap for Entities & dynamic shadows at mapBase 2 = 0x06208000)
    s_top_bg = bgInitSub(2, BgType_Bmp16, BgSize_B16_256x256, 2, 0);
    bgSetPriority(s_top_bg, 0);
    s_top_vram = (u16 *)bgGetGfxPtr(s_top_bg);

    init_obj_sprite_bounds();
    player_init();

    // Initialise camera position to match player spawn
    s_cam_x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    s_cam_y = player_screen_y(s_player.x, s_player.y) - CAMERA_ANCHOR_Y;
    if (s_cam_x < CACHE_X0) s_cam_x = CACHE_X0;
    if (s_cam_x > CACHE_X0 + CACHE_W - SCREEN_W) s_cam_x = CACHE_X0 + CACHE_W - SCREEN_W;
    if (s_cam_y < CACHE_Y0) s_cam_y = CACHE_Y0;
    if (s_cam_y > CACHE_Y0 + CACHE_H - SCREEN_H) s_cam_y = CACHE_Y0 + CACHE_H - SCREEN_H;

    // Initial hardware BG and entity render
    update_screen_hardware_bg(1, s_top_map_ptr, s_cam_x, s_cam_y - SCREEN_H);
    update_screen_hardware_bg(0, s_bot_map_ptr, s_cam_x, s_cam_y);
    render_screen(s_top_screen_buf, s_cam_x, s_cam_y - SCREEN_H, NULL, NULL, NULL);
    dmaCopyWords(3, s_top_screen_buf, s_top_vram, SCREEN_W * SCREEN_H * 2);

    render_screen(s_bot_screen_buf, s_cam_x, s_cam_y, NULL, NULL, NULL);
    dmaCopyWords(3, s_bot_screen_buf, s_bot_vram_buf0, SCREEN_W * SCREEN_H * 2);

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
        enemies_update();
        uint32_t logic_ticks = cpuGetTiming() - t0;

        uint32_t top_fl = 0, top_sh = 0, top_bl = 0;
        uint32_t bot_fl = 0, bot_sh = 0, bot_bl = 0;

        int top_cam_x = s_cam_x;
        int top_cam_y = s_cam_y - SCREEN_H;

        // Stream 32x25 tilemaps and set hardware scroll registers (~25-30 us)
        uint32_t t_bg_stream = cpuGetTiming();
        update_screen_hardware_bg(1, s_top_map_ptr, top_cam_x, top_cam_y);
        update_screen_hardware_bg(0, s_bot_map_ptr, s_cam_x, s_cam_y);
        top_fl = cpuGetTiming() - t_bg_stream;

        // Render entities and dynamic shadows for top screen
        uint32_t t1 = cpuGetTiming();
        render_screen(s_top_screen_buf, top_cam_x, top_cam_y, NULL, &top_sh, &top_bl);
        uint32_t top_ticks = cpuGetTiming() - t1;

        // Render entities and dynamic shadows for bottom screen
        uint32_t t2 = cpuGetTiming();
        render_screen(s_bot_screen_buf, s_cam_x, s_cam_y, NULL, &bot_sh, &bot_bl);
        // Copy directly into back-buffer VRAM surface (in CPU address space)
        u16 *back_vram = (s_active_vram_bank == 0) ? s_bot_vram_buf1 : s_bot_vram_buf0;
        dmaCopyWords(3, s_bot_screen_buf, back_vram, SCREEN_W * SCREEN_H * 2);
        uint32_t bot_ticks = cpuGetTiming() - t2;

        // CPU rendering finished before waiting for VBlank
        uint32_t cpu_ticks = cpuGetTiming() - frame_start_ticks;
        int vcount_done = REG_VCOUNT;

        uint32_t t3 = cpuGetTiming();
        present_both_screens();
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
