#include "game.h"
#include "player_sprite.h"
#include "arena.h"
#include "los.h"
#include "gameplay.h"
#include "enemy_ai.h"
#include "navfield.h"
#include "projectiles.h"
#include "weapons.h"
#include "grenade.h"
#include "sandbox.h"
#include "encounters.h"
#include "modifiers.h"
#include "crashlog.h"
#include "perfprof.h"
#include <string.h>

// ---------------------------------------------------------------------------
// DungeonDS - dimetric dungeon renderer
//
// World space is the baked FBX dungeon: world pixel coordinates are the
// projected 2:1 dimetric image (see include/arena.h). Sprites are
// pre-baked with the matching orthographic camera, so a sprite's centre is its
// ground anchor point on the floor.
//
// Hardware Background Scrolling:
// The static floor, perimeter walls, and shadows are converted into 8bpp tiles.
// The 64x32 map streams only the 33x25 tiles covering the viewport and fine-scroll
// overlap during VBlank; entities render on the bitmap BG.
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

// Upper bound on objects drawn per screen (walls + pillars in view).
#define MAX_DRAW_ITEMS 128
#define BG_RING_W 64
#define BG_RING_H 32
#define BG_VIEW_W (SCREEN_W / 8 + 1)
#define BG_VIEW_H (SCREEN_H / 8 + 1)

// Hardware BG IDs and pointers
static int s_bot_bg = 0;
static u16 *s_top_map_ptr = NULL;
static uint16_t *s_top_page = NULL;    // upper-screen 16 bpp actor page (single buffered)
static u16 *s_bot_map_ptr = NULL;
static int s_bot_active_page = 8;
static int s_bot_back_page = 24;

// World tile origin currently loaded into each 64x32 hardware BG map.
static int s_top_map_tile_x = 0;
static int s_top_map_tile_y = 0;
static int s_bot_map_tile_x = 0;
static int s_bot_map_tile_y = 0;
static int s_top_map_ready = 0;
static int s_bot_map_ready = 0;

// Actors, shadows and the HUD are painted straight into the hidden VRAM page of
// the BG2 bitmap (0x0000 = transparent). Each page remembers, per row, the span
// that was painted into it so reusing it only clears what was drawn two frames ago.
#define DIRTY_VERIFY 0 // 1 = after the span clear scan the whole page and count leftovers in g_perf.dirty_leaks
static DirtySpan s_dirty[2][SCREEN_H];
static DirtySpan s_dirty_top[SCREEN_H];
DirtySpan *g_dirty_cur = s_dirty[0];

static inline uint16_t *bot_page_ptr(int page) {
    return (uint16_t *)(0x06000000 + (uintptr_t)page * 0x4000);
}

#define BG_TILE_CACHE_CAPACITY 1024     // lower screen: 64 KiB of tile slots in bank D
#define TOP_TILE_CACHE_CAPACITY 448     // upper screen: 28 KiB in bank C (the baker keeps every window within it)
#define BG_TILE_INVALID 0xFFFF
#define BG_MAX_TILES 1024               // most distinct tiles of any arena (checked by tests/test_upper_screen_contract.py)
typedef struct {
    uint16_t slot_for_tile[BG_MAX_TILES];
    uint16_t slot_refs[BG_TILE_CACHE_CAPACITY];
    uint16_t world_tile_for_cell[BG_RING_W * BG_RING_H];
    uint16_t capacity;
    uint8_t overflow;
} BgTileCache;
static BgTileCache s_top_bg_tile_cache;
static BgTileCache s_bot_bg_tile_cache;
static uint8_t *s_top_bg_tiles_vram;
static uint8_t *s_bot_bg_tiles_vram;

static Player s_player;
static int s_cam_x = 0;
static int s_cam_y = 0;
static int s_player_see_through;
static int s_draw_item_depth;
static int s_draw_item_is_player;
static uint32_t s_frame_index = 0;

typedef struct {
    int32_t x, y;                 // raw 8.8 world pixels
    int32_t cam_x, cam_y;         // integer world pixels
    uint32_t input, moving, blocked_moves;
    uint32_t active_enemies, active_projectiles, frame_index;
} NavigationState;
volatile NavigationState g_nav_state;
static uint32_t s_blocked_moves = 0;
static uint32_t s_keys_down_latch = 0;

typedef struct {
    uint32_t calls, runs, pixels, ticks, frame_index;
} OcclusionStats;
volatile OcclusionStats g_occlusion_stats;

#define MAX_ENEMIES MAX_GAMEPLAY_ENEMIES

Enemy g_enemies[MAX_ENEMIES];     // not static: headless scenarios read it by symbol (the arena data also has an s_enemies)
static int abs_int(int v);

#define MAX_DEATH_CHUNKS 48
#define DEATH_CHUNK_SIZE 4
typedef struct {
    fixed x, y;       // world tile position, 8.8 fixed
    fixed vx, vy;     // world tile velocity per frame, 8.8 fixed
    fixed z, vz;      // screen-space height/velocity in pixels, 8.8 fixed
    uint16_t pixels[DEATH_CHUNK_SIZE * DEATH_CHUNK_SIZE];
    uint8_t life;
    uint8_t active;
} DeathChunk;
static DeathChunk s_death_chunks[MAX_DEATH_CHUNKS];
static uint32_t s_death_chunk_seed;

typedef struct {
    int depth;     // ground world Y in pixels
    int ref;       // -1 = player, -2 - i = enemy i, -2 - MAX_ENEMIES - i = death chunk i
    int cx;        // world pixel centre X
    int cy;        // world pixel centre Y (ground point)
} DrawItem;

// ---------------------------------------------------------------------------
// Projection helpers
// ---------------------------------------------------------------------------

static inline int player_screen_x(fixed x, fixed y) {
    return (int)(x >> FIXED_SHIFT);
}

static inline int player_screen_y(fixed x, fixed y) {
    return (int)(y >> FIXED_SHIFT);
}

// ---------------------------------------------------------------------------
// Blitting
// ---------------------------------------------------------------------------

static uint8_t s_char_frame_bounds[NUM_CHARACTERS][PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
static uint8_t s_char_ground_anchor[NUM_CHARACTERS][PLAYER_NUM_DIRS];

static void init_char_sprite_data(void) {
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
            s_char_ground_anchor[c][d] = g_character_ground_anchors[c][d];
        }
    }

}

// Runs of one world row are sorted by x; find the first that may reach cam_x.
// Runs never overlap, so the one ending past cam_x starts at or before any later one.
static inline uint32_t find_first_occlusion_run_in_row(int row, int cam_x) {
    uint32_t low = g_arena->occlusion_row_start[row];
    uint32_t high = g_arena->occlusion_row_start[row + 1];
    while (low < high) {
        uint32_t mid = (low + high) >> 1;
        const DungeonOcclusionRun *run = &g_arena->occlusion_runs[mid];
        if ((int)run->x + (int)run->length <= cam_x) {
            low = mid + 1;
        } else {
            high = mid;
        }
    }
    return low;
}
static inline uint8_t world_collision_flags_rt(int cx, int cy) {
    uint32_t index = (uint32_t)cy * g_arena->collision_w + (uint32_t)cx;
    return (g_arena->collision[index >> 2] >> ((index & 3) * 2)) & 0x03;
}

// Occlusion queries read the static baked runs directly (sorted by y then x, never
// overlapping inside a row, pixel exact). A run hides an actor whose depth is lower.
static inline int occlusion_blocks_pixel(int x, int y, int actor_depth) {
    if ((uint32_t)y >= g_arena->world_h) return 0;
    uint32_t i = find_first_occlusion_run_in_row(y, x);
    if (i >= g_arena->occlusion_row_start[y + 1]) return 0;
    const DungeonOcclusionRun *r = &g_arena->occlusion_runs[i];
    return (int)r->x <= x && (int)r->depth > actor_depth;
}

// Used by the enemy bolts (projectiles.c) so walls hide them like they hide actors.
int world_pixel_hidden(int x, int y, int depth) {
    return occlusion_blocks_pixel(x, y, depth);
}

// First run of world row y reaching x0 whose x < x1 and depth > actor_depth.
// Returns row_end when nothing in [x0, x1) can hide the actor.
static inline uint32_t find_hiding_run(int y, int x0, int x1, int actor_depth, uint32_t *row_end) {
    uint32_t re = g_arena->occlusion_row_start[y + 1];
    *row_end = re;
    for (uint32_t k = find_first_occlusion_run_in_row(y, x0); k < re; k++) {
        const DungeonOcclusionRun *r = &g_arena->occlusion_runs[k];
        if ((int)r->x >= x1) break;
        if ((int)r->depth > actor_depth) return k;
    }
    return re;
}

// Used by the ground decals (groundfx.c): non-zero when some wall run hides any pixel of world row y
// in [x0, x1) from an object of this depth. One lookup per span instead of one per pixel.
int world_span_hidden(int y, int x0, int x1, int depth) {
    if ((uint32_t)y >= g_arena->world_h) return 0;
    uint32_t row_end;
    return find_hiding_run(y, x0, x1, depth, &row_end) < row_end;
}

static inline void blit_px_range(uint16_t *drow, const uint16_t *srow, int a, int b) {
    for (; a < b; a++) {
        uint16_t c = srow[a];
        if (c & BIT(15)) drow[a] = c;
    }
}

// Blit a BGR555 sprite with arbitrary pitch, clipping opaque pixels against baked depth.
__attribute__((target("arm"), noinline))
static void blit_stride(uint16_t *buffer, const uint16_t *src, int pitch, int sw, int sh,
                        int left, int top, int cam_x, int cam_y, int depth) {
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

    int see_through = (s_draw_item_is_player || s_player_see_through) && (s_frame_index & 1);
    for (int y = sy0; y < sy1; y++) {
        const uint16_t *srow = &src[y * pitch];
        uint16_t *drow = &buffer[(oy + y) * SCREEN_W + ox];
        int x = sx0;
        int world_y = top + y;
        int world_x0 = left + sx0;
        int world_x1 = left + sx1;
        dirty_row(oy + y, ox + sx0, ox + sx1);
        if (depth >= 0 && !see_through && (uint32_t)world_y < g_arena->world_h) {
            uint32_t re;
            uint32_t k = find_hiding_run(world_y, world_x0, world_x1, depth, &re);
            if (k < re) {
                // Paint the stretches between hiding runs; pixels inside them stay hidden.
                int cur = sx0;
                for (; k < re; k++) {
                    const DungeonOcclusionRun *r = &g_arena->occlusion_runs[k];
                    int rx0 = (int)r->x - left;
                    if (rx0 >= sx1) break;
                    if ((int)r->depth <= depth) continue;
                    if (rx0 > cur) blit_px_range(drow, srow, cur, rx0);
                    int rx1 = rx0 + (int)r->length;
                    if (rx1 > cur) cur = rx1;
                    if (cur >= sx1) break;
                }
                if (cur < sx1) blit_px_range(drow, srow, cur, sx1);
                continue;
            }
        }

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

static inline uint16_t world_floor_color(int x, int y) {
    if ((uint32_t)x >= g_arena->world_w || (uint32_t)y >= g_arena->world_h) return VOID_COLOR | BIT(15);
    uint16_t tile_id = g_arena->map[(y >> 3) * g_arena->map_w + (x >> 3)];
    if (tile_id >= g_arena->num_tiles) return VOID_COLOR | BIT(15);
    uint8_t palette_index = g_arena->tiles[tile_id][(y & 7) * 8 + (x & 7)];
    if (palette_index == 0) return VOID_COLOR | BIT(15);
    return g_arena->palette[palette_index];
}

__attribute__((target("arm"), noinline))
static void draw_shadow_mask(uint16_t *buffer, const uint8_t *mask, int sw, int sh,
                             const uint8_t *bounds, int left, int top,
                             int cam_x, int cam_y, int depth) {
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
        int world_y = top + y;
        dirty_row(oy + y, ox + sx0, ox + sx1);
        // rn walks the runs of this row left to right; null when nothing can hide the shadow.
        const DungeonOcclusionRun *rn = NULL, *rend = NULL;
        if (!(s_draw_item_is_player && s_player_see_through) && (uint32_t)world_y < g_arena->world_h) {
            uint32_t re;
            if (find_hiding_run(world_y, left + sx0, left + sx1, depth, &re) < re) {
                rn = &g_arena->occlusion_runs[find_first_occlusion_run_in_row(world_y, left + sx0)];
                rend = &g_arena->occlusion_runs[re];
            }
        }
        for (int x = sx0; x < sx1; x++) {
            int pixel = row_offset + x;
            uint8_t packed = mask[pixel >> 1];
            uint8_t nibble = (pixel & 1) ? (packed >> 4) : (packed & 0x0F);
            if (nibble > 0) {
                int world_x = left + x;
                if (world_x < 0 || world_x >= g_arena->world_w || world_y < 0 || world_y >= g_arena->world_h) continue;
                if (rn) {
                    while (rn < rend && (int)rn->x + (int)rn->length <= world_x) rn++;
                    if (rn < rend && (int)rn->x <= world_x && (int)rn->depth > depth) continue;
                }
                uint16_t c = dst_row[x] ? dst_row[x] : world_floor_color(world_x, world_y);
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

// Stream only newly exposed edges into the 64x32 BG ring map. This function
// runs in VBlank, so neither scanout nor fine-scroll sampling sees a half-updated map.
static int bg_ring_index(int tile, int size) {
    int index = tile % size;
    return index < 0 ? index + size : index;
}

// 512x256 text maps are two 32x32 screen blocks, not a linear 64-column array.
static int bg_map_index(int col, int row) {
    return (col >> 5) * 1024 + row * 32 + (col & 31);
}

static u16 bg_world_tile(int col, int row) {
    if (col < 0 || col >= g_arena->map_w || row < 0 || row >= g_arena->map_h) return 0;
    return g_arena->map[row * g_arena->map_w + col];
}

static void init_bg_tile_cache(BgTileCache *cache, uint16_t capacity, uint8_t *tile_vram) {
    cache->capacity = capacity;
    memset(tile_vram, 0, 64);              // slot 0 is the blank tile
    for (uint32_t i = 0; i < BG_MAX_TILES; i++) cache->slot_for_tile[i] = BG_TILE_INVALID;
    for (uint32_t i = 0; i < BG_RING_W * BG_RING_H; i++) cache->world_tile_for_cell[i] = BG_TILE_INVALID;
    memset(cache->slot_refs, 0, sizeof(cache->slot_refs));
    cache->slot_for_tile[0] = 0;
    cache->slot_refs[0] = BG_TILE_INVALID;
    cache->overflow = 0;
}

static uint16_t acquire_bg_tile(BgTileCache *cache, uint16_t tile_id, uint8_t *tile_vram) {
    if (tile_id == 0) return 0;
    if (tile_id >= g_arena->num_tiles) {
        cache->overflow = 1;
        return 0;
    }
    uint16_t slot = cache->slot_for_tile[tile_id];
    if (slot != BG_TILE_INVALID) {
        cache->slot_refs[slot]++;
        return slot;
    }
    for (slot = 1; slot < cache->capacity; slot++) {
        if (cache->slot_refs[slot] == 0) break;
    }
    if (slot == cache->capacity) {
        cache->overflow = 1;
        return 0;
    }
    memcpy(tile_vram + (uint32_t)slot * 64, g_arena->tiles[tile_id], 64);
    cache->slot_for_tile[tile_id] = slot;
    cache->slot_refs[slot] = 1;
    return slot;
}

static void release_bg_tile(BgTileCache *cache, uint16_t tile_id) {
    if (tile_id == 0 || tile_id == BG_TILE_INVALID || tile_id >= BG_MAX_TILES) return;
    uint16_t slot = cache->slot_for_tile[tile_id];
    if (slot == BG_TILE_INVALID || slot == 0) return;
    if (--cache->slot_refs[slot] == 0) cache->slot_for_tile[tile_id] = BG_TILE_INVALID;
}

// Palette of the active arena into both engines (each arena has its own 255 colours).
static void apply_arena_palette(void) {
    dmaCopyWords(3, g_arena->palette, BG_PALETTE, 256 * 2);
    dmaCopyWords(3, g_arena->palette, BG_PALETTE_SUB, 256 * 2);
}

static void update_screen_hardware_bg(int is_sub, u16 *map_ptr, int cam_x, int cam_y) {
    int rel_x = cam_x;
    int rel_y = cam_y;
    int tile_x = rel_x >> 3;
    int tile_y = rel_y >> 3;
    int ring_x = bg_ring_index(tile_x, BG_RING_W);
    int ring_y = bg_ring_index(tile_y, BG_RING_H);
    int fine_x = rel_x & 7;
    int fine_y = rel_y & 7;
    BgTileCache *cache = is_sub ? &s_top_bg_tile_cache : &s_bot_bg_tile_cache;
    uint8_t *tile_vram = is_sub ? s_top_bg_tiles_vram : s_bot_bg_tiles_vram;
    int *prev_x = is_sub ? &s_top_map_tile_x : &s_bot_map_tile_x;
    int *prev_y = is_sub ? &s_top_map_tile_y : &s_bot_map_tile_y;
    int *ready = is_sub ? &s_top_map_ready : &s_bot_map_ready;

    if (!*ready || tile_x != *prev_x || tile_y != *prev_y) {
        for (int my = 0; my < BG_RING_H; my++) {
            int rel_y = bg_ring_index(my - ring_y, BG_RING_H);
            int world_y = tile_y + rel_y;
            for (int mx = 0; mx < BG_RING_W; mx++) {
                int rel_x = bg_ring_index(mx - ring_x, BG_RING_W);
                int world_x = tile_x + rel_x;
                uint32_t cell = my * BG_RING_W + mx;
                uint16_t tile_id = 0;
                if (rel_x < BG_VIEW_W && rel_y < BG_VIEW_H) {
                    tile_id = bg_world_tile(world_x, world_y);
                }
                if (cache->world_tile_for_cell[cell] != tile_id) {
                    release_bg_tile(cache, cache->world_tile_for_cell[cell]);
                    uint16_t slot = acquire_bg_tile(cache, tile_id, tile_vram);
                    cache->world_tile_for_cell[cell] = tile_id;
                    map_ptr[bg_map_index(mx, my)] = slot;
                }
            }
        }
        *prev_x = tile_x;
        *prev_y = tile_y;
        *ready = 1;
    }

    if (is_sub) {
        REG_BG0HOFS_SUB = (ring_x * 8 + fine_x) & 511;
        REG_BG0VOFS_SUB = (ring_y * 8 + fine_y) & 255;
    } else {
        REG_BG1HOFS = (ring_x * 8 + fine_x) & 511;
        REG_BG1VOFS = (ring_y * 8 + fine_y) & 255;
    }
}


// ---------------------------------------------------------------------------
// Composition
// ---------------------------------------------------------------------------

// While the player is see-through, mark where hidden wall footprints meet the
// floor: the collision grid edge, drawn only over occluder surfaces (floor already shows it).
#define WALL_BASE_COLOR (RGB15(3, 3, 6) | BIT(15))
// A wall-base pixel is drawn only where some occluder run covers it (depth -1 hides nothing less).
static inline void wall_base_px(uint16_t *buffer, int cam_x, int cam_y, int wx, int wy) {
    int sx = wx - cam_x, sy = wy - cam_y;
    if ((uint32_t)sx >= SCREEN_W || (uint32_t)sy >= SCREEN_H) return;
    if (!occlusion_blocks_pixel(wx, wy, -1)) return;
    buffer[sy * SCREEN_W + sx] = WALL_BASE_COLOR;
    dirty_row(sy, sx, sx + 1);
}

// Four consecutive pixels of one world row with a single run lookup.
static inline void wall_base_hrow(uint16_t *buffer, int cam_x, int cam_y, int wx, int wy) {
    int sy = wy - cam_y;
    if ((uint32_t)wy >= g_arena->world_h || (uint32_t)sy >= SCREEN_H) return;
    uint32_t i = find_first_occlusion_run_in_row(wy, wx);
    uint32_t re = g_arena->occlusion_row_start[wy + 1];
    for (int k = 0; k < COLLISION_SCALE; k++) {
        int x = wx + k;
        int sx = x - cam_x;
        while (i < re && (int)g_arena->occlusion_runs[i].x + (int)g_arena->occlusion_runs[i].length <= x) i++;
        if (i >= re) break;
        if ((int)g_arena->occlusion_runs[i].x > x || (uint32_t)sx >= SCREEN_W) continue;
        buffer[sy * SCREEN_W + sx] = WALL_BASE_COLOR;
        dirty_row(sy, sx, sx + 1);
    }
}
__attribute__((target("arm"), optimize("O3"), noinline))
static void draw_hidden_wall_base(uint16_t *buffer, int cam_x, int cam_y, int psx, int psy) {
    enum { BOX_CELLS_W = 14, BOX_CELLS_H = 10 };
    int cx0 = (psx - 28) / COLLISION_SCALE;
    int cy0 = (psy - 20) / COLLISION_SCALE;
    if (cx0 < 1) cx0 = 1;
    if (cy0 < 1) cy0 = 1;
    if (cx0 + BOX_CELLS_W > g_arena->collision_w - 1) cx0 = g_arena->collision_w - 1 - BOX_CELLS_W;
    if (cy0 + BOX_CELLS_H > g_arena->collision_h - 1) cy0 = g_arena->collision_h - 1 - BOX_CELLS_H;

    // Blocked bit of the three rows around the current one, read once per row.
    uint8_t rows[3][BOX_CELLS_W + 2];
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < BOX_CELLS_W + 2; c++)
            rows[r][c] = world_collision_flags_rt(cx0 - 1 + c, cy0 - 1 + r) & 0x01;

    for (int j = 0; j < BOX_CELLS_H; j++) {
        for (int i = 0; i < BOX_CELLS_W; i++) {
            if (!rows[1][i + 1]) continue;
            int wx = (cx0 + i) * COLLISION_SCALE, wy = (cy0 + j) * COLLISION_SCALE;
            int lx = wx - cam_x, ly = wy - cam_y;
            if ((uint32_t)lx >= SCREEN_W || (uint32_t)ly >= SCREEN_H) continue;
            int up = !rows[0][i + 1], dn = !rows[2][i + 1];
            int lf = !rows[1][i], rt = !rows[1][i + 2];
            if (up) wall_base_hrow(buffer, cam_x, cam_y, wx, wy);
            if (dn) wall_base_hrow(buffer, cam_x, cam_y, wx, wy + 3);
            for (int k = 0; k < COLLISION_SCALE; k++) {
                if (lf) wall_base_px(buffer, cam_x, cam_y, wx, wy + k);
                if (rt) wall_base_px(buffer, cam_x, cam_y, wx + 3, wy + k);
            }
        }
    }
}

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
    int pitch = PLAYER_SPRITE_W;
    if (g_player_state.invuln_timer > 0 && ((g_player_state.invuln_timer >> 2) & 1)) {
        // Hit feedback: red flash while the i-frames run.
        static uint16_t s_tint[PLAYER_SPRITE_W * PLAYER_SPRITE_H];
        for (int y = 0; y < bh; y++) {
            for (int x = 0; x < bw; x++) {
                uint16_t c = frame[y * PLAYER_SPRITE_W + x];
                if (c & BIT(15)) {
                    int red = (c & 31) + 14, green = ((c >> 5) & 31) >> 1, blue = ((c >> 10) & 31) >> 1;
                    if (red > 31) red = 31;
                    c = (uint16_t)(red | (green << 5) | (blue << 10) | BIT(15));
                }
                s_tint[y * bw + x] = c;
            }
        }
        frame = s_tint;
        pitch = bw;
    }
    blit_stride(buffer, frame, pitch, bw, bh,
                px - PLAYER_ANCHOR_X + min_x, py - s_char_ground_anchor[s_player.char_id][s_player.dir] + min_y,
                cam_x, cam_y, s_draw_item_depth);
}

static void draw_hit_spark(uint16_t *buffer, int x, int y, int cam_x, int cam_y, int phase) {
    uint16_t cyan = RGB15(9, 25, 31) | BIT(15);
    uint16_t ivory = RGB15(31, 28, 20) | BIT(15);
    for (int d = -3; d <= 3; d++) {
        int bx = x + d - cam_x, by = y - cam_y;
        if (bx >= 0 && bx < SCREEN_W && by >= 0 && by < SCREEN_H &&
            !occlusion_blocks_pixel(x + d, y, s_draw_item_depth))
        { buffer[by * SCREEN_W + bx] = ((d + phase) & 1) ? cyan : ivory; dirty_row(by, bx, bx + 1); }
        bx = x - cam_x; by = y + d - cam_y;
        if (bx >= 0 && bx < SCREEN_W && by >= 0 && by < SCREEN_H &&
            !occlusion_blocks_pixel(x, y + d, s_draw_item_depth))
        { buffer[by * SCREEN_W + bx] = ((d + phase) & 1) ? ivory : cyan; dirty_row(by, bx, bx + 1); }
    }
}

// Shooter telegraph (DESIGN.md 4.5): the weapon glows at its muzzle before a burst, pulsing
// faster and bigger as the shot gets closer. Same muzzle table as the player.
static void bone_effect_pixel(uint16_t *buffer, int x, int y, int cam_x, int cam_y, uint16_t color);
static void draw_telegraph_flash(uint16_t *buffer, const Enemy *e, int cam_x, int cam_y) {
    const int8_t *m = g_character_muzzle[e->char_id][e->dir][e->frame];
    int x = TO_INT(e->x) + m[0];
    int y = TO_INT(e->y) + m[1] - m[2];
    int left = e->state_timer;                      // frames until the burst
    int big = left < 8;
    uint16_t core = RGB15(24, 31, 20) | BIT(15);
    uint16_t glow = RGB15(2, 29, 6) | BIT(15);
    if ((left & (big ? 1 : 2)) == 0) return;        // blink
    bone_effect_pixel(buffer, x, y, cam_x, cam_y, core);
    bone_effect_pixel(buffer, x - 1, y, cam_x, cam_y, glow);
    bone_effect_pixel(buffer, x + 1, y, cam_x, cam_y, glow);
    bone_effect_pixel(buffer, x, y - 1, cam_x, cam_y, glow);
    bone_effect_pixel(buffer, x, y + 1, cam_x, cam_y, glow);
    if (big) {
        bone_effect_pixel(buffer, x - 2, y, cam_x, cam_y, glow);
        bone_effect_pixel(buffer, x + 2, y, cam_x, cam_y, glow);
        bone_effect_pixel(buffer, x, y - 2, cam_x, cam_y, glow);
        bone_effect_pixel(buffer, x, y + 2, cam_x, cam_y, glow);
    }
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
                px - PLAYER_ANCHOR_X + min_x, py - s_char_ground_anchor[e->char_id][e->dir] + min_y,
                cam_x, cam_y, s_draw_item_depth);
    if (e->hit_timer > 0)
        draw_hit_spark(buffer, px, py - 24, cam_x, cam_y, e->hit_timer);
    if (e->state == ENEMY_STATE_TELEGRAPH)
        draw_telegraph_flash(buffer, e, cam_x, cam_y);
}

static void bone_effect_pixel(uint16_t *buffer, int x, int y, int cam_x, int cam_y, uint16_t color) {
    int sx = x - cam_x, sy = y - cam_y;
    if (sx >= 0 && sx < SCREEN_W && sy >= 0 && sy < SCREEN_H &&
        !occlusion_blocks_pixel(x, y, s_draw_item_depth))
        { buffer[sy * SCREEN_W + sx] = color; dirty_row(sy, sx, sx + 1); }
}

static void draw_death_chunk(uint16_t *buffer, const DeathChunk *chunk, int cam_x, int cam_y) {
    int cx = player_screen_x(chunk->x, chunk->y);
    int ground_y = player_screen_y(chunk->x, chunk->y);
    bone_effect_pixel(buffer, cx, ground_y + 2, cam_x, cam_y, RGB15(2, 2, 2) | BIT(15));
    int cy = ground_y - (chunk->z >> FIXED_SHIFT);
    int left = cx - DEATH_CHUNK_SIZE / 2 - cam_x;
    int top = cy - DEATH_CHUNK_SIZE / 2 - cam_y;
    if (left >= SCREEN_W || left + DEATH_CHUNK_SIZE <= 0 ||
        top >= SCREEN_H || top + DEATH_CHUNK_SIZE <= 0) return;

    for (int y = 0; y < DEATH_CHUNK_SIZE; y++) {
        int sy = top + y;
        if (sy < 0 || sy >= SCREEN_H) continue;
        for (int x = 0; x < DEATH_CHUNK_SIZE; x++) {
            int sx = left + x;
            uint16_t color = chunk->pixels[y * DEATH_CHUNK_SIZE + x];
            if (sx >= 0 && sx < SCREEN_W && (color & BIT(15)) &&
                !occlusion_blocks_pixel(cx - DEATH_CHUNK_SIZE / 2 + x,
                                        cy - DEATH_CHUNK_SIZE / 2 + y,
                                        s_draw_item_depth))
                { buffer[sy * SCREEN_W + sx] = color; dirty_row(sy, sx, sx + 1); }
        }
    }
}
// Zero the rows' painted spans (32-bit stores: VRAM ignores 8-bit writes) and forget them.
// Spans widen to even pixels; pixels outside a span are already zero.
__attribute__((target("arm"), optimize("O3,no-tree-loop-distribute-patterns"), noinline))
static void clear_dirty_spans(uint16_t *page, DirtySpan *spans) {
    for (int y = 0; y < SCREEN_H; y++) {
        int x0 = spans[y].x0, x1 = spans[y].x1;
        if (x0 >= x1) continue;
        spans[y].x0 = SCREEN_W;
        spans[y].x1 = 0;
        x0 &= ~1;
        x1 = (x1 + 1) & ~1;
        volatile uint32_t *p = (volatile uint32_t *)&page[y * SCREEN_W + x0];
        for (int n = (x1 - x0) >> 1; n > 0; n--) *p++ = 0;
    }
#if DIRTY_VERIFY
    const uint32_t *w = (const uint32_t *)page;
    uint32_t leaks = 0;
    for (int i = 0; i < SCREEN_W * SCREEN_H / 2; i++) {
        uint32_t v = w[i];
        leaks += ((v & 0xFFFFu) != 0) + ((v >> 16) != 0);
    }
    g_perf.dirty_leaks += leaks;
#endif
}

// Whether the player stands behind a wall (the actors are then drawn see-through, on both
// screens). Computed once per frame from the player alone.
static void update_player_see_through(void) {
    int cx = player_screen_x(s_player.x, s_player.y);
    int cy = player_screen_y(s_player.x, s_player.y);
    s_player_see_through = 0;
    for (int k = 8; k <= 24; k += 8) {
        if (occlusion_blocks_pixel(cx, cy - k, cy)) {
            s_player_see_through = 1;
            break;
        }
    }
}

static void render_screen(uint16_t *buffer, DirtySpan *spans, int cam_x, int cam_y,
                          uint32_t *out_floor, uint32_t *out_shadow, uint32_t *out_blit) {
    DrawItem items[MAX_DRAW_ITEMS + MAX_ENEMIES + MAX_DEATH_CHUNKS + 1];
    int count = 0;

    // The static floor is in BG1; this buffer contains only dynamic layers.

    // Add player only if visible on this screen
    int psx = player_screen_x(s_player.x, s_player.y);
    int psy = player_screen_y(s_player.x, s_player.y);
    int pl_left = psx - PLAYER_ANCHOR_X - cam_x;
    // Cull on the feet row: the exported ground anchor varies per character
    // and direction, so the sprite top lies within one canvas height above it.
    int pl_feet = psy - cam_y;
    if (pl_left < SCREEN_W && pl_left + PLAYER_SPRITE_W > 0 &&
        pl_feet - PLAYER_SPRITE_H < SCREEN_H && pl_feet + PLAYER_SPRITE_H > 0) {
        if (count < MAX_DRAW_ITEMS) {
            items[count].depth = psy;
            items[count].ref = -1;
            items[count].cx = psx;
            items[count].cy = psy;
            count++;
        }
    }

    // Add enemies only if visible on this screen
    for (int e_idx = 0; e_idx < MAX_ENEMIES; e_idx++) {
        if (!g_enemies[e_idx].active) continue;
        int esx = player_screen_x(g_enemies[e_idx].x, g_enemies[e_idx].y);
        int esy = player_screen_y(g_enemies[e_idx].x, g_enemies[e_idx].y);
        int e_left = esx - PLAYER_ANCHOR_X - cam_x;
        int e_feet = esy - cam_y;
        if (e_left < SCREEN_W && e_left + PLAYER_SPRITE_W > 0 &&
            e_feet - PLAYER_SPRITE_H < SCREEN_H && e_feet + PLAYER_SPRITE_H > 0) {
            if (count < MAX_DRAW_ITEMS) {
                items[count].depth = esy;
                items[count].ref = -2 - e_idx;
                items[count].cx = esx;
                items[count].cy = esy;
                count++;
            }
        }
    }

    for (int i = 0; i < MAX_DEATH_CHUNKS; i++) {
        DeathChunk *chunk = &s_death_chunks[i];
        if (!chunk->active) continue;
        int px = player_screen_x(chunk->x, chunk->y);
        int py = player_screen_y(chunk->x, chunk->y) - (chunk->z >> FIXED_SHIFT);
        if (px + DEATH_CHUNK_SIZE < cam_x || px - DEATH_CHUNK_SIZE > cam_x + SCREEN_W ||
            py + DEATH_CHUNK_SIZE < cam_y || py - DEATH_CHUNK_SIZE > cam_y + SCREEN_H) continue;
        if (count < MAX_DRAW_ITEMS + MAX_ENEMIES + MAX_DEATH_CHUNKS) {
            items[count].depth = player_screen_y(chunk->x, chunk->y);
            items[count].ref = -2 - MAX_ENEMIES - i;
            items[count].cx = px;
            items[count].cy = py;
            count++;
        }
    }

    // The static FBX bake is now a hardware BG; keep this bitmap layer transparent
    // (0x0000 = transparent in 16-bit direct bitmap mode) and render only dynamic
    // actors, shadows, particles, and the HUD into it.
    PP_T0(pp_clear);
    uint32_t floor_start_ticks = cpuGetTiming();
    clear_dirty_spans(buffer, spans);
    g_dirty_cur = spans;
    if (out_floor) *out_floor = cpuGetTiming() - floor_start_ticks;
    PP_ADD(PP_CLEAR, pp_clear);

    // 0) Ground decals of the weapons (aim marker, warning zones, shock rings): under everything.
    weapons_render_floor(buffer, cam_x, cam_y);

    // 1) Composite dynamic entity shadows (player & enemies, animated per frame)
    uint32_t t_sh0 = cpuGetTiming();
    PP_T0(pp_shadow);
    for (int i = 0; i < count; i++) {
        s_draw_item_is_player = (items[i].ref == -1);
        if (items[i].ref == -1) {
            draw_shadow_mask(buffer, g_character_shadow_masks[s_player.char_id][s_player.dir][s_player.frame],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[s_player.char_id][s_player.dir][s_player.frame],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y, items[i].depth);
        } else if (items[i].ref <= -2 &&
                   items[i].ref > -2 - MAX_ENEMIES) {
            int e_idx = -2 - items[i].ref;
            const Enemy *e = &g_enemies[e_idx];
            draw_shadow_mask(buffer, g_character_shadow_masks[e->char_id][e->dir][e->frame],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[e->char_id][e->dir][e->frame],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y, items[i].depth);
        }
    }
    PP_ADD(PP_SHADOW, pp_shadow);
    if (s_player_see_through) {
        PP_T0(pp_wall);
        for (int i = 0; i < count; i++)
            if (items[i].ref == -1)
                draw_hidden_wall_base(buffer, cam_x, cam_y, items[i].cx, items[i].cy);
        PP_ADD(PP_WALLBASE, pp_wall);
    }
    uint32_t shadow_ticks = cpuGetTiming() - t_sh0;

    // 2) Sprites back-to-front (painter's algorithm)
    PP_T0(pp_sort);
    for (int i = 1; i < count; i++) {
        DrawItem key = items[i];
        int j = i - 1;
        while (j >= 0 && items[j].depth > key.depth) {
            items[j + 1] = items[j];
            j--;
        }
        items[j + 1] = key;
    }

    PP_ADD(PP_SORT, pp_sort);
    uint32_t t_bl0 = cpuGetTiming();
    PP_T0(pp_blit);
    for (int i = 0; i < count; i++) {
        s_draw_item_depth = items[i].depth;
        int sp = items[i].ref;
        CRASH_MARK(CL_DRAW_ITEM, sp, items[i].depth);
        s_draw_item_is_player = (sp == -1);
        if (sp == -1) {
            draw_player(buffer, cam_x, cam_y);
        } else if (sp <= -2 - MAX_ENEMIES) {
            int chunk_idx = -2 - MAX_ENEMIES - sp;
            draw_death_chunk(buffer, &s_death_chunks[chunk_idx], cam_x, cam_y);
        } else {
            draw_enemy(buffer, &g_enemies[-2 - sp], cam_x, cam_y);
        }
    }
    PP_ADD(PP_BLIT, pp_blit);
    weapons_render_light(buffer, cam_x, cam_y);     // beams light the sprites drawn above
    PP_T0(pp_proj);
    enemy_projectiles_render(buffer, cam_x, cam_y);
    weapons_render(buffer, cam_x, cam_y);
    mods_render(buffer, cam_x, cam_y);
    PP_ADD(PP_PROJ, pp_proj);
    uint32_t blit_ticks = cpuGetTiming() - t_bl0;

    if (out_shadow) *out_shadow = shadow_ticks;
    if (out_blit) *out_blit = blit_ticks;
}

static const char s_fps_chars[] = " FPS:CBL0123456789HARMDEWNITOGUVY.ZJ";
static const uint8_t s_fps_font[][7] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00}, // space
    {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10}, // F
    {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10}, // P
    {0x0F,0x10,0x10,0x0E,0x01,0x01,0x1E}, // S
    {0x00,0x04,0x04,0x00,0x04,0x04,0x00}, // :
    {0x0E,0x11,0x10,0x10,0x10,0x11,0x0E}, // C
    {0x1E,0x11,0x11,0x1E,0x11,0x11,0x1E}, // B
    {0x10,0x10,0x10,0x10,0x10,0x10,0x1F}, // L
    {0x0E,0x11,0x13,0x15,0x19,0x11,0x0E}, // 0
    {0x04,0x0C,0x04,0x04,0x04,0x04,0x0E}, // 1
    {0x0E,0x11,0x01,0x02,0x04,0x08,0x1F}, // 2
    {0x1E,0x01,0x01,0x0E,0x01,0x01,0x1E}, // 3
    {0x02,0x06,0x0A,0x12,0x1F,0x02,0x02}, // 4
    {0x1F,0x10,0x10,0x1E,0x01,0x01,0x1E}, // 5
    {0x0E,0x10,0x10,0x1E,0x11,0x11,0x0E}, // 6
    {0x1F,0x01,0x02,0x04,0x08,0x08,0x08}, // 7
    {0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E}, // 8
    {0x0E,0x11,0x11,0x0F,0x01,0x01,0x0E}, // 9
    {0x11,0x11,0x11,0x1F,0x11,0x11,0x11}, // H
    {0x0E,0x11,0x11,0x1F,0x11,0x11,0x11}, // A
    {0x1E,0x11,0x11,0x1E,0x14,0x12,0x11}, // R
    {0x11,0x1B,0x15,0x11,0x11,0x11,0x11}, // M
    {0x1E,0x11,0x11,0x11,0x11,0x11,0x1E}, // D
    {0x1F,0x10,0x10,0x1E,0x10,0x10,0x1F}, // E
    {0x11,0x11,0x11,0x15,0x15,0x1B,0x11}, // W
    {0x11,0x19,0x15,0x13,0x11,0x11,0x11}, // N
    {0x1F,0x04,0x04,0x04,0x04,0x04,0x1F}, // I
    {0x1F,0x04,0x04,0x04,0x04,0x04,0x04}, // T
    {0x0E,0x11,0x11,0x11,0x11,0x11,0x0E}, // O
    {0x0E,0x11,0x10,0x17,0x11,0x11,0x0F}, // G
    {0x11,0x11,0x11,0x11,0x11,0x11,0x0E}, // U
    {0x11,0x11,0x11,0x11,0x11,0x0A,0x04}, // V
    {0x11,0x11,0x0A,0x04,0x04,0x04,0x04}, // Y
    {0x00,0x00,0x00,0x00,0x00,0x0C,0x0C}, // .
    {0x1F,0x01,0x02,0x04,0x08,0x10,0x1F}, // Z
    {0x07,0x02,0x02,0x02,0x02,0x12,0x0C}  // J
};

#define HUD_LINES 4 // PERF_PROFILE reuses lines 1-2 (top stages) to keep the HUD as cheap as the original

static void draw_fps_hud(uint16_t *buffer) {
    char labels[HUD_LINES][32];
    unsigned long cpu_ms = (unsigned long)(g_perf.cpu_ticks / 33514u);
    unsigned long present_ms = (unsigned long)(g_perf.present_ticks / 33514u);
    unsigned long floor_ms = (unsigned long)(g_perf.floor_ticks / 33514u);
    unsigned long shadow_ms = (unsigned long)(g_perf.shadow_ticks / 33514u);
    unsigned long blit_ms = (unsigned long)(g_perf.blit_ticks / 33514u);
    unsigned long logic_ms = (unsigned long)(g_perf.logic_ticks / 33514u);
    if (cpu_ms > 99) cpu_ms = 99;
    if (present_ms > 99) present_ms = 99;
    if (floor_ms > 99) floor_ms = 99;
    if (shadow_ms > 99) shadow_ms = 99;
    if (blit_ms > 99) blit_ms = 99;
    if (logic_ms > 99) logic_ms = 99;
#if PERF_PROFILE
    snprintf(labels[0], sizeof(labels[0]), "FPS:%lu.%lu C:%02lu P:%02lu",
             (unsigned long)(perfprof_fps10() / 10), (unsigned long)(perfprof_fps10() % 10), cpu_ms, present_ms);
    perfprof_hud_line(0, labels[1], sizeof(labels[1]));
#else
    snprintf(labels[0], sizeof(labels[0]), "FPS:%2lu C:%02lu P:%02lu",
             (unsigned long)g_perf.fps, cpu_ms, present_ms);
#endif
#if PERF_PROFILE
    (void)floor_ms; (void)shadow_ms; (void)blit_ms; (void)logic_ms;
#else
    snprintf(labels[1], sizeof(labels[1]), "F:%02lu S:%02lu B:%02lu L:%02lu",
             floor_ms, shadow_ms, blit_ms, logic_ms);
#endif
    if (g_player_state.is_dead) {
        snprintf(labels[2], sizeof(labels[2]), "HP:DEAD");
    } else {
        snprintf(labels[2], sizeof(labels[2]), "HP:%d",
                 g_player_state.hp);
    }
    snprintf(labels[3], sizeof(labels[3]), "WPN:%s FX:%c%c",
             weapons_get_name(g_player_state.current_weapon), weapons_fx_style_letter(),
             weapons_aura_style_letter());

    const int left = 4, top = 4, pad = 2, char_w = 6, glyph_w = 5, glyph_h = 7, line_gap = 2;
    int first_w = (int)strlen(labels[0]) * char_w - 1;
    int second_w = (int)strlen(labels[1]) * char_w - 1;
    int third_w = (int)strlen(labels[2]) * char_w - 1;
    int fourth_w = (int)strlen(labels[3]) * char_w - 1;
    int text_w = first_w > second_w ? first_w : second_w;
    if (third_w > text_w) text_w = third_w;
    if (fourth_w > text_w) text_w = fourth_w;
    int box_w = text_w + pad * 2;
    int box_h = glyph_h * HUD_LINES + line_gap * (HUD_LINES - 1) + pad * 2;
    uint16_t panel = RGB15(1, 2, 1) | BIT(15);
    uint16_t border = RGB15(0, 16, 0) | BIT(15);
    uint16_t ink = RGB15(18, 31, 18) | BIT(15);

    for (int y = 0; y < box_h; y++) {
        dirty_row(top + y, left, left + box_w);
        for (int x = 0; x < box_w; x++) {
            int edge = x == 0 || y == 0 || x == box_w - 1 || y == box_h - 1;
            buffer[(top + y) * SCREEN_W + left + x] = edge ? border : panel;
        }
    }

    for (int line = 0; line < HUD_LINES; line++) {
        for (int i = 0; labels[line][i]; i++) {
            int glyph = 0;
            while (s_fps_chars[glyph] && s_fps_chars[glyph] != labels[line][i]) glyph++;
            if (!s_fps_chars[glyph]) continue;
            const uint8_t *rows = s_fps_font[glyph];
            int line_y = top + pad + line * (glyph_h + line_gap);
            for (int y = 0; y < glyph_h; y++) {
                for (int x = 0; x < glyph_w; x++) {
                    if (rows[y] & (1u << (glyph_w - 1 - x)))
                        buffer[(line_y + y) * SCREEN_W + left + pad + i * char_w + x] = ink;
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Run HUD (DESIGN.md 5): always on, bottom screen only. Hit points, modifiers taken, packs
// cleared, the name of the modifier under the player and the "dungeon completed" banner.
// ---------------------------------------------------------------------------

static int hud_glyph_index(char c) {
    for (int i = 0; s_fps_chars[i]; i++)
        if (s_fps_chars[i] == c) return i;
    return -1;
}

static int hud_text_width(const char *s) { return (int)strlen(s) * 6 - 1; }

static void hud_px(uint16_t *buffer, int x, int y, uint16_t c) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) return;
    buffer[y * SCREEN_W + x] = c;
}

static void hud_text(uint16_t *buffer, int x, int y, const char *s, uint16_t ink) {
    const uint16_t shadow = RGB15(1, 1, 2) | BIT(15);
    int w = hud_text_width(s);
    for (int row = 0; row < 9; row++) dirty_row(y + row, x, x + w + 2);
    for (int i = 0; s[i]; i++) {
        int g = hud_glyph_index(s[i]);
        if (g < 0 || s[i] == ' ') continue;
        const uint8_t *rows = s_fps_font[g];
        for (int gy = 0; gy < 7; gy++)
            for (int gx = 0; gx < 5; gx++)
                if (rows[gy] & (1u << (4 - gx))) {
                    hud_px(buffer, x + i * 6 + gx + 1, y + gy + 1, shadow);
                    hud_px(buffer, x + i * 6 + gx, y + gy, ink);
                }
    }
}

static void hud_square(uint16_t *buffer, int x, int y, int size, uint16_t fill, uint16_t edge) {
    for (int dy = 0; dy < size; dy++) {
        dirty_row(y + dy, x, x + size);
        for (int dx = 0; dx < size; dx++)
            hud_px(buffer, x + dx, y + dy, (dx == 0 || dy == 0 || dx == size - 1 || dy == size - 1) ? edge : fill);
    }
}

static void draw_run_hud(uint16_t *buffer) {
    const uint16_t ink = RGB15(31, 31, 31) | BIT(15);
    const uint16_t dark = RGB15(5, 1, 1) | BIT(15);
    const uint16_t red = RGB15(31, 5, 6) | BIT(15);
    const uint16_t edge = RGB15(31, 24, 24) | BIT(15);

    // Hit points, right-aligned at the top.
    int max_hp = g_player_state.max_hp;
    int x0 = SCREEN_W - 6 - max_hp * 8;
    for (int i = 0; i < max_hp; i++)
        hud_square(buffer, x0 + i * 8, 6, 7, i < g_player_state.hp ? red : dark, edge);

    // Modifiers taken, one coloured square each, under the hit points.
    int mask = mods_owned_mask(), n = 0;
    for (int id = 0; id < MOD_COUNT; id++) {
        if (!(mask & (1 << id))) continue;
        hud_square(buffer, SCREEN_W - 6 - 6 - n * 8, 17, 6, mods_color(id), RGB15(2, 2, 3) | BIT(15));
        n++;
    }

    // Packs cleared, bottom left.
    char line[24];
    snprintf(line, sizeof(line), "MANADAS %d DE %d", g_encounter_mgr.packs_cleared, g_encounter_mgr.packs_total);
    hud_text(buffer, 6, SCREEN_H - 14, line, ink);

    // Modifier name: the pedestal the player is near, or the one just taken.
    const char *name = mods_hud_text();
    if (name) hud_text(buffer, (SCREEN_W - hud_text_width(name)) / 2, SCREEN_H - 32, name, RGB15(31, 28, 8) | BIT(15));

    if (g_encounter_mgr.state == ENCOUNTER_STATE_CLEARED) {
        const char *msg = "MAZMORRA COMPLETADA";
        hud_text(buffer, (SCREEN_W - hud_text_width(msg)) / 2, 84, msg, RGB15(31, 28, 8) | BIT(15));
    }
}

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------

static uint32_t present_both_screens(int top_cam_x, int top_cam_y,
                                      int bot_cam_x, int bot_cam_y) {
    PP_T0(pp_vw);
    swiWaitForVBlank();
    PP_ADD(PP_VWAIT, pp_vw);
    PP_T0(pp_bs);
    update_screen_hardware_bg(1, s_top_map_ptr, top_cam_x, top_cam_y);
    PP_ADD(PP_BGSUB, pp_bs);
    PP_T0(pp_bb);
    update_screen_hardware_bg(0, s_bot_map_ptr, bot_cam_x, bot_cam_y);
    PP_ADD(PP_BGBOT, pp_bb);
    bgSetMapBase(s_bot_bg, s_bot_back_page);
    int old_page = s_bot_active_page;
    s_bot_active_page = s_bot_back_page;
    s_bot_back_page = old_page;
    return 0;
}

// ---------------------------------------------------------------------------
// Enemies
// ---------------------------------------------------------------------------

static void enemies_init(void) {
    enemy_projectiles_init();
    encounters_init(&g_encounter_mgr);
    encounters_spawn(&g_encounter_mgr, g_enemies, MAX_ENEMIES);
}

static int abs_int(int v) { return v < 0 ? -v : v; }

static int aim_dir_from_screen(int dx, int dy) {
    int ax = abs_int(dx), ay = abs_int(dy);
    if (ax * 2 < ay) dx = 0;
    else if (ay * 2 < ax) dy = 0;
    else {
        dx = dx < 0 ? -1 : 1;
        dy = dy < 0 ? -1 : 1;
    }
    if (dx == 0) return dy >= 0 ? 0 : 4;
    if (dy == 0) return dx < 0 ? 2 : 6;
    if (dx < 0) return dy > 0 ? 1 : 3;
    return dy < 0 ? 5 : 7;
}

static void death_chunks_spawn(const Enemy *e, fixed hit_vx, fixed hit_vy) {
    const uint8_t *bounds = s_char_frame_bounds[e->char_id][e->dir][e->frame];
    int min_x = bounds[0], min_y = bounds[1];
    int width = bounds[2], height = bounds[3];
    if (width == 0 || height == 0) return;
    const uint16_t *frame = g_character_frames[e->char_id][e->dir][e->frame];

    for (int piece = 0; piece < 6; piece++) {
        int column = piece & 1;
        int row = piece >> 1;
        int sx = min_x + ((2 * column + 1) * width) / 4 - DEATH_CHUNK_SIZE / 2;
        int sy = min_y + ((row + 1) * height) / 4 - DEATH_CHUNK_SIZE / 2;
        int max_x = min_x + width - DEATH_CHUNK_SIZE;
        int max_y = min_y + height - DEATH_CHUNK_SIZE;
        if (max_x < min_x) max_x = min_x;
        if (max_y < min_y) max_y = min_y;
        if (max_x > PLAYER_SPRITE_W - DEATH_CHUNK_SIZE) max_x = PLAYER_SPRITE_W - DEATH_CHUNK_SIZE;
        if (max_y > PLAYER_SPRITE_H - DEATH_CHUNK_SIZE) max_y = PLAYER_SPRITE_H - DEATH_CHUNK_SIZE;
        if (sx < min_x) sx = min_x;
        if (sy < min_y) sy = min_y;
        if (sx > max_x) sx = max_x;
        if (sy > max_y) sy = max_y;

        uint32_t seed = s_death_chunk_seed++;
        DeathChunk *chunk = &s_death_chunks[seed % MAX_DEATH_CHUNKS];
        int opaque = 0;
        for (int y = 0; y < DEATH_CHUNK_SIZE; y++) {
            for (int x = 0; x < DEATH_CHUNK_SIZE; x++) {
                uint16_t color = frame[(sy + y) * PLAYER_SPRITE_W + sx + x];
                chunk->pixels[y * DEATH_CHUNK_SIZE + x] = color;
                opaque |= (color & BIT(15)) != 0;
            }
        }
        if (!opaque) {
            chunk->active = 0;
            continue;
        }

        uint32_t hash = seed * 0x45d9f3bu + (uint32_t)piece * 0x27d4eb2du;
        hash ^= hash >> 16;
        int offset_x = sx + DEATH_CHUNK_SIZE / 2 - PLAYER_ANCHOR_X;
        int offset_y = sy + DEATH_CHUNK_SIZE / 2 - s_char_ground_anchor[e->char_id][e->dir];
        fixed screen_x = offset_x * (1 << FIXED_SHIFT);
        fixed screen_y = offset_y * (1 << FIXED_SHIFT);
        chunk->x = e->x + screen_x;
        chunk->y = e->y + screen_y;

        fixed impulse_x = hit_vx / 16 + (int)(hash & 0x3ffu) - 512;
        fixed impulse_y = hit_vy / 16 + (int)((hash >> 10) & 0x3ffu) - 512;
        chunk->vx = impulse_x;
        chunk->vy = impulse_y;
        chunk->z = (fixed)(1 + ((hash >> 20) & 3u)) << FIXED_SHIFT;
        chunk->vz = (fixed)(512 + ((hash >> 18) & 255u));
        chunk->life = (uint8_t)(28 + ((hash >> 24) & 7u));
        chunk->active = 1;
    }
}

// Registered with enemy_set_death_hook(); enemy_hit() (gameplay.c) calls it on a kill.
static void on_enemy_death(const Enemy *e, fixed hit_vx, fixed hit_vy) {
    CRASH_MARK(CL_DEATH_CHUNKS, e->char_id, e->dir);
    death_chunks_spawn(e, hit_vx, hit_vy);
    weapons_notify_kill();
    CRASH_MARK(CL_DEATH_HOOK_DONE, 0, 0);
}

static void death_chunks_update(void) {
    for (int i = 0; i < MAX_DEATH_CHUNKS; i++) {
        DeathChunk *chunk = &s_death_chunks[i];
        if (!chunk->active) continue;
        chunk->x += chunk->vx;
        chunk->y += chunk->vy;
        if (chunk->z > 0 || chunk->vz > 0) {
            chunk->z += chunk->vz;
            chunk->vz -= 48;
            if (chunk->z <= 0) {
                chunk->z = 0;
                chunk->vz = 0;
            }
        } else {
            chunk->vx = (chunk->vx * 3) / 4;
            chunk->vy = (chunk->vy * 3) / 4;
        }
        if (--chunk->life == 0) chunk->active = 0;
    }
}

static void weapons_and_effects_update(void) {
    grenade_set_player_pos(s_player.x, s_player.y);
    weapons_update(g_enemies, MAX_ENEMIES);
    death_chunks_update();
}

#define NAV_BUDGET_PER_FRAME 300   // BFS node expansions per frame (a full field takes ~10 frames; measure with PERF_PROFILE)

static fixed s_prev_player_x = 0;
static fixed s_prev_player_y = 0;
static int s_first_frame = 1;     // set again by arena_restart so the lead does not see a teleport

static void enemies_update(void) {
    if (s_first_frame) {
        s_prev_player_x = s_player.x;
        s_prev_player_y = s_player.y;
        s_first_frame = 0;
    }
    fixed pvx = s_player.x - s_prev_player_x;
    fixed pvy = s_player.y - s_prev_player_y;
    s_prev_player_x = s_player.x;
    s_prev_player_y = s_player.y;

    nav_set_goal(TO_INT(s_player.x), TO_INT(s_player.y));
    nav_update(NAV_BUDGET_PER_FRAME);
    enemy_ai_update(g_enemies, MAX_ENEMIES, s_player.x, s_player.y, pvx, pvy);
    enemy_projectiles_update(s_player.x, s_player.y);
    encounters_update(&g_encounter_mgr, g_enemies, MAX_ENEMIES, s_player.x, s_player.y);
    mods_update(s_player.x, s_player.y);
}

// ---------------------------------------------------------------------------
// Player
// ---------------------------------------------------------------------------

static void player_init(void) {
    s_player.x = TO_FIXED(g_arena->player_x);
    s_player.y = TO_FIXED(g_arena->player_y);
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
    s_player.char_id = CHAR_HERO;

    mods_reset();
    player_state_init(&g_player_state);
    weapons_init();

    enemies_init();
}

// Stylus edges are tracked every presented frame (hitstop included) and latched
// until the simulation consumes them, so a short tap is never lost.
static int s_prev_touch_down = 0;
static int s_latch_pressed = 0;
static int s_latch_released = 0;
static int s_last_touch_x = 0;
static int s_last_touch_y = 0;
static int s_rooted = 0;          // the sniper is aiming: the player stands still

#define AIM_CHEST_H 16            // height used to pick the facing direction from the stylus

static void touch_track(int touch_down, int touch_x, int touch_y) {
    if (touch_down && !s_prev_touch_down) s_latch_pressed = 1;
    if (!touch_down && s_prev_touch_down) s_latch_released = 1;
    s_prev_touch_down = touch_down;
    if (touch_down) {
        s_last_touch_x = touch_x;
        s_last_touch_y = touch_y;
    }
}

// Muzzle of the weapon for the current direction and frame: the lab exports it as
// an offset from the ground anchor plus a height above the ground.
static void player_muzzle(fixed *mx, fixed *my, int *mh) {
    const int8_t *m = g_character_muzzle[s_player.char_id][s_player.dir][s_player.frame];
    *mx = s_player.x + TO_FIXED(m[0]);
    *my = s_player.y + TO_FIXED(m[1]);
    *mh = m[2];
}

// The camera follows the player but stays inside the arena: horizontally the view never leaves
// the floor image, and vertically the player stays on the touch screen (the upper screen shows
// the strip above it) with at most half a screen of void beyond the arena edge.
static void update_camera(void) {
    int x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    int y = player_screen_y(s_player.x, s_player.y) - SCREEN_H / 2;
    int max_x = g_arena->world_w - SCREEN_W;
    if (max_x <= 0) x = max_x / 2;
    else if (x < 0) x = 0;
    else if (x > max_x) x = max_x;
    int min_y = SCREEN_H / 2;
    int max_y = g_arena->world_h - SCREEN_H / 2;
    if (y < min_y) y = min_y;
    if (y > max_y) y = max_y;
    s_cam_x = x;
    s_cam_y = y;
}

static void player_update(uint32_t keys, uint32_t keys_down) {
    if (g_player_state.invuln_timer > 0) g_player_state.invuln_timer--;

    if (g_player_state.is_dead) {
        s_player.is_moving = 0;
        s_player.frame = 0;
        return;
    }

    // Debug god mode for headless walk scenarios: hold L+R and press B.
    if ((keys & (KEY_L | KEY_R)) == (KEY_L | KEY_R) && (keys_down & KEY_B)) {
        g_player_state.god_mode = !g_player_state.god_mode;
    }

    // Debug for headless scenarios: hold L+R and press X to kill the pack nearest to the player
    // (through enemy_hit, so death effects, the pack reward and the run end all run for real).
    if ((keys & (KEY_L | KEY_R)) == (KEY_L | KEY_R) && (keys_down & KEY_X)) {
        int best = -1, best_d2 = 0x7fffffff;
        for (int i = 0; i < MAX_ENEMIES; i++) {
            if (!g_enemies[i].active || g_enemies[i].hp <= 0) continue;
            int dx = TO_INT(g_enemies[i].x - s_player.x), dy = TO_INT(g_enemies[i].y - s_player.y);
            int d2 = dx * dx + GROUND_DY2(dy);
            if (d2 < best_d2) { best_d2 = d2; best = i; }
        }
        if (best >= 0) {
            int pack = g_enemies[best].pack;
            for (int i = 0; i < MAX_ENEMIES; i++)
                if (g_enemies[i].active && g_enemies[i].hp > 0 && g_enemies[i].pack == pack)
                    enemy_hit(&g_enemies[i], 9999, 0, 0);
        }
    }

    // L is the only button of the test: it switches weapon (and cancels a sniper aim).
    if (keys_down & KEY_L) {
        weapons_cycle(&g_player_state);
    }
    // Playground ROM: R puts the parked dummies back (no-op in every other build).
    if (keys_down & KEY_R) sandbox_respawn();
    // DESIGN.md 4.9 (debug): SELECT cycles the weapon-effects style A/B/C for the comparison.
    if (keys_down & KEY_SELECT) {
        g_fx_style = (g_fx_style + 1) % FX_STYLE_COUNT;
    }
    // DESIGN.md 4.9 (debug): Y cycles the sniper charge aura look K -> C -> V for the comparison.
    if (keys_down & KEY_Y) {
        g_aura_style = (g_aura_style + 1) % AURA_STYLE_COUNT;
    }

    int pressed = s_latch_pressed;
    int released = s_latch_released;
    int touch_down = s_prev_touch_down;
    s_latch_pressed = 0;
    if (pressed && released) {
        // Tap shorter than the hitstop: deliver the press now and the release next frame.
        released = 0;
        touch_down = 1;
    } else {
        s_latch_released = 0;
    }

    int cur_char = s_player.char_id;
    fixed current_speed = g_characters[cur_char].speed * g_mods.speed_pct / 100;
    int current_period = g_characters[cur_char].anim_period;

    if (pressed && weapons_can_start_aim(&g_player_state)) s_rooted = 1;

    int sdx = 0, sdy = 0; // screen-space input axes
    if (!s_rooted) {
        if (keys & KEY_UP) sdy -= 1;
        if (keys & KEY_DOWN) sdy += 1;
        if (keys & KEY_LEFT) sdx -= 1;
        if (keys & KEY_RIGHT) sdx += 1;
    }

    if (sdx != 0 || sdy != 0) {
        // While the stylus aims, the character faces the target and strafes.
        if (!touch_down) {
            if (sdy > 0 && sdx == 0) s_player.dir = DIR_SOUTH;
            else if (sdy > 0 && sdx < 0) s_player.dir = DIR_SOUTHWEST;
            else if (sdy == 0 && sdx < 0) s_player.dir = DIR_WEST;
            else if (sdy < 0 && sdx < 0) s_player.dir = DIR_NORTHWEST;
            else if (sdy < 0 && sdx == 0) s_player.dir = DIR_NORTH;
            else if (sdy < 0 && sdx > 0) s_player.dir = DIR_NORTHEAST;
            else if (sdy == 0 && sdx > 0) s_player.dir = DIR_EAST;
            else s_player.dir = DIR_SOUTHEAST;
        }

        fixed vx = sdx * current_speed;
        fixed vy = sdy * current_speed;
        if (sdx != 0 && sdy != 0) { // normalise diagonals on the ground plane
            vx = (vx * 181) >> 8;
            vy = (vy * 181) >> 8;
        }
        vy >>= GROUND_Y_SHIFT; // equal ground speed on both axes under 2:1

        int moved = 0;
        fixed next_x = s_player.x, next_y = s_player.y;
        if (sweep_position(&next_x, &next_y, vx, vy)) {
            moved = next_x != s_player.x || next_y != s_player.y;
        } else {
            next_x = s_player.x;
            next_y = s_player.y;
            if (sweep_position(&next_x, &next_y, vx, 0)) {
                moved = next_x != s_player.x;
            } else {
                next_x = s_player.x;
                next_y = s_player.y;
                if (sweep_position(&next_x, &next_y, 0, vy))
                    moved = next_y != s_player.y;
            }
        }
        if (moved) {
            s_player.x = next_x;
            s_player.y = next_y;
        }
        s_player.is_moving = moved;
        if (!moved) s_blocked_moves++;
        if (moved) {
            s_player.anim_timer++;
            if (s_player.anim_timer >= current_period) {
                s_player.anim_timer = 0;
                s_player.frame = (s_player.frame + 1) % PLAYER_NUM_FRAMES;
            }
        } else {
            s_player.frame = 0;
            s_player.anim_timer = 0;
        }
    } else {
        s_player.is_moving = 0;
        s_player.frame = 0;
        s_player.anim_timer = 0;
    }

    update_camera();

    // Stylus: aim and fire. The character turns towards the touched point first so the
    // muzzle used for the shot belongs to the direction it is facing.
    WeaponInput in;
    in.touch_down = touch_down;
    in.touch_pressed = pressed;
    in.touch_released = released;
    // The frame on screen is drawn shifted by the shake: map the touch onto what is shown.
    int shake_x, shake_y;
    weapons_shake_offset(&shake_x, &shake_y);
    in.touch_x = s_last_touch_x + s_cam_x + shake_x;
    in.touch_y = s_last_touch_y + s_cam_y + shake_y;
    in.player_x = s_player.x;
    in.player_y = s_player.y;
    if (touch_down) {
        s_player.dir = aim_dir_from_screen(in.touch_x - player_screen_x(s_player.x, s_player.y),
                                           in.touch_y - (player_screen_y(s_player.x, s_player.y) - AIM_CHEST_H));
    }
    player_muzzle(&in.muzzle_x, &in.muzzle_y, &in.muzzle_h);

    int result = weapons_input(&g_player_state, &in, g_enemies, MAX_ENEMIES);
    s_rooted = (result & WEAPON_RESULT_ROOTED) != 0;
    if (result & WEAPON_RESULT_FIRED) {
        // Recoil: a short kick opposite to the shot.
        fixed dir_x, dir_y;
        weapons_last_shot_dir(&dir_x, &dir_y);
        const WeaponTuning *tuning = &g_weapon_tuning[g_player_state.current_weapon];
        fixed recoil = tuning->recoil * g_mods.recoil_pct / 100;
        fixed kx = s_player.x - ((dir_x * recoil) >> 8);
        fixed ky = s_player.y - ((dir_y * recoil) >> 8);
        if (position_is_free(kx, ky)) {
            s_player.x = kx;
            s_player.y = ky;
        }
    }
}

// Death restarts the current arena at once: full health, the wave respawned.
static void arena_restart(void) {
    int god = g_player_state.god_mode;
    s_player.x = TO_FIXED(g_arena->player_x);
    s_player.y = TO_FIXED(g_arena->player_y);
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
    mods_reset();                    // a new run: modifiers are lost (DESIGN.md 5)
    player_state_init(&g_player_state);
    g_player_state.god_mode = god;
    weapons_init();
    nav_set_goal(g_arena->player_x, g_arena->player_y);
    nav_rebuild_now();
    s_rooted = 0;
    s_first_frame = 1;
    s_latch_pressed = 0;
    s_latch_released = 0;
    s_keys_down_latch = 0;
    update_camera();                 // the fade-in shows the new arena before the player moves
    g_hitstop_frames = 0;
    memset(s_death_chunks, 0, sizeof(s_death_chunks));
    encounters_spawn(&g_encounter_mgr, g_enemies, MAX_ENEMIES);
}

// Switches to another arena: its palette, floor tiles and navigation field, then starts it.
static void arena_enter(int index) {
    arena_select(index);
    g_encounter_mgr.arena = ((index % g_num_arenas) + g_num_arenas) % g_num_arenas;
    apply_arena_palette();
    init_bg_tile_cache(&s_top_bg_tile_cache, TOP_TILE_CACHE_CAPACITY, s_top_bg_tiles_vram);
    init_bg_tile_cache(&s_bot_bg_tile_cache, BG_TILE_CACHE_CAPACITY, s_bot_bg_tiles_vram);
    s_top_map_ready = 0;
    s_bot_map_ready = 0;
    nav_init();
    arena_restart();
}

// Fade to black, load the next arena at full black, fade back in (the simulation is frozen).
enum { TRANSITION_NONE = 0, TRANSITION_OUT, TRANSITION_IN };
#define FADE_STEP 2                     // brightness levels per frame (16 = black): 8 frames each way
static int s_transition = TRANSITION_NONE;
static int s_fade_level = 0;

static void transition_update(void) {
    if (s_transition == TRANSITION_NONE) {
        if (g_encounter_mgr.advance) s_transition = TRANSITION_OUT;
        return;
    }
    if (s_transition == TRANSITION_OUT) {
        s_fade_level += FADE_STEP;
        if (s_fade_level >= 16) {
            s_fade_level = 16;
            setBrightness(3, -16);           // fully black before the palette and tiles change
            arena_enter(encounters_next_arena(&g_encounter_mgr));
            s_transition = TRANSITION_IN;
        }
    } else {
        s_fade_level -= FADE_STEP;
        if (s_fade_level <= 0) {
            s_fade_level = 0;
            s_transition = TRANSITION_NONE;
        }
    }
    setBrightness(3, -s_fade_level);
}

volatile PerfStats g_perf = {
    .magic = 0x50455246,
    .frame_index = 0,
    .cpu_ticks = 0,
    .cpu_budget = 560190, // 33513982 Hz / 59.8261 Hz
    .cpu_percent = 0,
    .vcount_done = 0,
    .vblanks_elapsed = 1,
    .fps = 60,
    .logic_ticks = 0,
    .top_render_ticks = 0,
    .bot_render_ticks = 0,
    .present_ticks = 0,
    .show_hud = PLAYGROUND,       // the playground ROM shows the weapon / style label from the start
    .dirty_leaks = 0
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

    // Main engine: streamed FBX 8bpp floor in D, dynamic 16bpp actors in A.
    videoSetMode(MODE_5_2D);
    vramSetBankD(VRAM_D_MAIN_BG_0x06000000);
    vramSetBankA(VRAM_A_MAIN_BG_0x06020000);
    vramSetBankB(VRAM_B_MAIN_BG_0x06060000);

    // Load Background Palette to Main and Sub engines
    arena_select(0);
    apply_arena_palette();

    // BG1 map lives at 0x06000000; 1024 streamed tile slots start at +64 KiB.
    int bot_hw_bg = bgInit(1, BgType_Text8bpp, BgSize_T_512x256, 0, 4);
    bgSetPriority(bot_hw_bg, 3); // Lowest priority (drawn behind entities)
    bgShow(bot_hw_bg);
    BG_PALETTE[0] = RGB15(0, 0, 0);
    s_bot_map_ptr = bgGetMapPtr(bot_hw_bg);
    s_bot_bg_tiles_vram = (uint8_t *)bgGetGfxPtr(bot_hw_bg);

    // Initialize Main BG2 (16-bit Bitmap for Entities & dynamic shadows at mapBase 8 = 0x06020000)
    {
        uint32_t zero = 0;
        swiFastCopy(&zero, bot_page_ptr(8), COPY_MODE_FILL | (SCREEN_W * SCREEN_H * 2 / 4));
        swiFastCopy(&zero, bot_page_ptr(24), COPY_MODE_FILL | (SCREEN_W * SCREEN_H * 2 / 4));
    }
    s_bot_bg = bgInit(2, BgType_Bmp16, BgSize_B16_256x256, 8, 0);
    bgSetPriority(s_bot_bg, 0); // High priority (drawn on top of BG1)

    // Sub engine: same layers as the main one (floor tiles + a 16 bpp actor bitmap), so both
    // screens draw the same things. Bank C (128 KiB): tile slots 0-28 KiB, floor map 28-32 KiB,
    // actor page 32-128 KiB (256x192 at 16 bpp = 96 KiB).
    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG_0x06200000); // 128 KB for the upper floor tiles and map

    int top_hw_bg = bgInitSub(0, BgType_Text8bpp, BgSize_T_512x256, 14, 0);
    bgSetPriority(top_hw_bg, 1);
    bgShow(top_hw_bg);
    s_top_map_ptr = bgGetMapPtr(top_hw_bg);
    s_top_bg_tiles_vram = (uint8_t *)bgGetGfxPtr(top_hw_bg);

    int top_bmp_bg = bgInitSub(2, BgType_Bmp16, BgSize_B16_256x256, 2, 0);
    bgSetPriority(top_bmp_bg, 0);
    s_top_page = (uint16_t *)bgGetGfxPtr(top_bmp_bg);
    {
        uint32_t zero = 0;
        swiFastCopy(&zero, s_top_page, COPY_MODE_FILL | (SCREEN_W * SCREEN_H * 2 / 4));
    }


    init_char_sprite_data();
    CRASH_INIT();
    PP_INIT();
    enemy_set_death_hook(on_enemy_death);
    nav_init();
    nav_set_goal(g_arena->player_x, g_arena->player_y);
    nav_rebuild_now();
    player_init();

    // Initialise camera position to match player spawn
    s_cam_x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    s_cam_y = player_screen_y(s_player.x, s_player.y) - SCREEN_H / 2;

    init_bg_tile_cache(&s_top_bg_tile_cache, TOP_TILE_CACHE_CAPACITY, s_top_bg_tiles_vram);
    init_bg_tile_cache(&s_bot_bg_tile_cache, BG_TILE_CACHE_CAPACITY, s_bot_bg_tiles_vram);
    update_screen_hardware_bg(1, s_top_map_ptr, s_cam_x, s_cam_y - SCREEN_H);

    update_player_see_through();
    render_screen(s_top_page, s_dirty_top, s_cam_x, s_cam_y - SCREEN_H, NULL, NULL, NULL);
    render_screen(bot_page_ptr(s_bot_active_page), s_dirty[s_bot_active_page == 24], s_cam_x, s_cam_y, NULL, NULL, NULL);
    draw_run_hud(bot_page_ptr(s_bot_active_page));
    draw_fps_hud(bot_page_ptr(s_bot_active_page));
    update_screen_hardware_bg(0, s_bot_map_ptr, s_cam_x, s_cam_y);

    while (1) {
        uint32_t frame_start_ticks = cpuGetTiming();
        uint32_t start_vblank = s_vblank_count;
        s_frame_index++;

        scanKeys();
        uint32_t keys_held = keysHeld();
        uint32_t keys_down = keysDown();
        touchPosition touch;
        touchRead(&touch);
        int touch_down = (keys_held & KEY_TOUCH) && touch.px < SCREEN_W && touch.py < SCREEN_H;

        if (keys_down & KEY_START) {
            g_perf.show_hud = !g_perf.show_hud;
        }

        uint32_t t0 = cpuGetTiming();
        touch_track(touch_down, touch.px, touch.py);
        s_keys_down_latch |= keys_down;
        transition_update();
        int simulate = g_hitstop_frames <= 0 && s_transition == TRANSITION_NONE;
        if (!simulate) g_hitstop_frames--;
        if (simulate) {
            sandbox_update(g_enemies, MAX_ENEMIES, &s_player.x, &s_player.y);
            player_update(keys_held, s_keys_down_latch);
            s_keys_down_latch = 0;
        }
        PP_ADD(PP_PLAYER, t0);
        CRASH_FRAME(s_frame_index);
        CRASH_MARK(CL_FRAME_START, s_frame_index, 0);
        CRASH_POLL();
        CRASH_MARK(CL_OCCLUSION_DONE, 0, 0);
        PP_T0(pp_en);
        if (simulate) enemies_update();
        PP_ADD(PP_ENEMIES, pp_en);
        CRASH_MARK(CL_ENEMIES_DONE, 0, 0);
        PP_T0(pp_wp);
        if (simulate) weapons_and_effects_update();
        if (g_player_state.is_dead) arena_restart();
        PP_ADD(PP_WEAPONS, pp_wp);
        CRASH_MARK(CL_WEAPONS_DONE, 0, 0);
        uint32_t logic_ticks = cpuGetTiming() - t0;

        uint32_t top_floor = 0, top_sh = 0, top_bl = 0;
        uint32_t bot_floor = 0, bot_sh = 0, bot_bl = 0;

        int shake_x, shake_y;
        weapons_shake_offset(&shake_x, &shake_y);
        int view_x = s_cam_x + shake_x;
        int view_y = s_cam_y + shake_y;
        int top_cam_x = view_x;
        int top_cam_y = view_y - SCREEN_H;

        uint32_t top_ticks = 0;
        // Both screens draw the same layers. The upper page is single buffered: it is drawn
        // first, right after the logic, while the frame is still in or near VBlank.
        update_player_see_through();
        uint32_t t_top = cpuGetTiming();
        render_screen(s_top_page, s_dirty_top, view_x, view_y - SCREEN_H, &top_floor, &top_sh, &top_bl);
        top_ticks = cpuGetTiming() - t_top;

        // The lower screen adds the HUD on top of the same layers.
        uint32_t t2 = cpuGetTiming();
        CRASH_MARK(CL_RENDER_START, 0, 0);
        render_screen(bot_page_ptr(s_bot_back_page), s_dirty[s_bot_back_page == 24], view_x, view_y, &bot_floor, &bot_sh, &bot_bl);
        CRASH_MARK(CL_RENDER_DONE, 0, 0);
        PP_T0(pp_hud);
        draw_run_hud(bot_page_ptr(s_bot_back_page));
        if (g_perf.show_hud != 0) {
            draw_fps_hud(bot_page_ptr(s_bot_back_page));
        }
        PP_ADD(PP_HUD, pp_hud);
        uint32_t bot_ticks = cpuGetTiming() - t2;

        // CPU rendering finished before waiting for VBlank
        uint32_t cpu_ticks = cpuGetTiming() - frame_start_ticks;
        PP_SET(PP_CPU, cpu_ticks);
        int vcount_done = REG_VCOUNT;

        uint32_t t3 = cpuGetTiming();
        uint32_t bg_ticks = present_both_screens(top_cam_x, top_cam_y, view_x, view_y);
        uint32_t present_ticks = cpuGetTiming() - t3;

        uint32_t vblanks_elapsed = s_vblank_count - start_vblank;
        if (vblanks_elapsed == 0) vblanks_elapsed = 1;
#if PERF_PROFILE
        PP_SET(PP_FRAME, cpuGetTiming() - frame_start_ticks);
        perfprof_frame_end(s_frame_index, vblanks_elapsed, s_vblank_count, s_bot_active_page, s_player_see_through);
#endif

        g_perf.frame_index++;
        uint32_t total_cpu_ticks = cpu_ticks + bg_ticks;
        g_perf.cpu_ticks = total_cpu_ticks;
        g_perf.cpu_percent = (total_cpu_ticks * 100) / g_perf.cpu_budget;
        g_perf.vcount_done = vcount_done;
        g_perf.vblanks_elapsed = vblanks_elapsed;
        g_perf.fps = 60 / vblanks_elapsed;
        g_perf.logic_ticks = logic_ticks;
        g_perf.top_render_ticks = top_ticks;
        g_perf.bot_render_ticks = bot_ticks;
        g_perf.present_ticks = present_ticks;
        g_perf.floor_ticks = top_floor + bot_floor;
        g_perf.shadow_ticks = top_sh + bot_sh;
        g_perf.blit_ticks = top_bl + bot_bl;

        uint32_t enemies = 0, projectiles = 0;
        for (int i = 0; i < MAX_ENEMIES; i++) enemies += g_enemies[i].active != 0;
        projectiles += weapons_get_active_projectile_count();
        g_nav_state.x = s_player.x;
        g_nav_state.y = s_player.y;
        g_nav_state.cam_x = s_cam_x;
        g_nav_state.cam_y = s_cam_y;
        g_nav_state.input = keys_held & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
        g_nav_state.moving = s_player.is_moving;
        g_nav_state.blocked_moves = s_blocked_moves;
        g_nav_state.active_enemies = enemies;
        g_nav_state.active_projectiles = projectiles;
        g_nav_state.frame_index = g_perf.frame_index;
#ifdef DEBUG
        if ((g_perf.frame_index % 15) == 0) {
            char nav_buf[120];
            snprintf(nav_buf, sizeof(nav_buf), "NAV frame=%lu x=%ld y=%ld cam=%lu,%lu in=%lu move=%lu blocked=%lu enemies=%lu projectiles=%lu\\n",
                     (unsigned long)g_nav_state.frame_index, (long)g_nav_state.x, (long)g_nav_state.y,
                     (unsigned long)g_nav_state.cam_x, (unsigned long)g_nav_state.cam_y,
                     (unsigned long)g_nav_state.input, (unsigned long)g_nav_state.moving,
                     (unsigned long)g_nav_state.blocked_moves, (unsigned long)g_nav_state.active_enemies,
                     (unsigned long)g_nav_state.active_projectiles);
            nocashMessage(nav_buf);
        }

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
#endif
    }

    return 0;
}
