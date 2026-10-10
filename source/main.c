#include "game.h"
#include "dungeon_data.h"
#include "player_sprite.h"
#include "dungeon_bg_tiles.h"
#include "diablo_dungeon.h"
#include "dungeon_occlusion.h"

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
// Hardware Background Scrolling:
// The static floor, perimeter walls, and shadows are converted into 8bpp tiles.
// A 64x32 hardware ring map streams only newly exposed rows/columns during VBlank,
// while fine scroll remains in the BG registers; entities render on the bitmap BG.
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
static u16 *s_bot_vram = NULL;

// World tile origin currently loaded into each 64x32 hardware BG ring map.
static int s_top_map_tile_x = 0;
static int s_top_map_tile_y = 0;
static int s_bot_map_tile_x = 0;
static int s_bot_map_tile_y = 0;
static int s_top_map_ready = 0;
static int s_bot_map_ready = 0;

// Rendering buffers for top and bottom screens (cleared transparently for entities)
static uint16_t s_top_screen_buf[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));
static uint16_t s_bot_screen_buf[SCREEN_W * SCREEN_H] __attribute__((aligned(4)));

static Player s_player;
static int s_cam_x = 0;
static int s_cam_y = 0;
static int16_t s_occlusion_depth[WORLD_W * WORLD_H] __attribute__((aligned(4)));
static int s_draw_item_depth;

typedef struct {
    int32_t x, y;                 // raw 8.8 world pixels
    int32_t cam_x, cam_y;         // integer world pixels
    uint32_t input, moving, blocked_moves;
    uint32_t active_enemies, active_lances, frame_index;
} NavigationState;
volatile NavigationState g_nav_state;
static uint32_t s_blocked_moves = 0;

typedef struct {
    uint32_t calls, runs, pixels, ticks, frame_index;
} OcclusionStats;
volatile OcclusionStats g_occlusion_stats;

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
    int hp;
    int hit_timer;
} Enemy;

static Enemy s_enemies[MAX_ENEMIES];
static int abs_int(int v);

#define MAX_PROJECTILES 16
#define LANCE_PELLETS 5
#define LANCE_COOLDOWN 16
#define LANCE_SPEED 2048  // 8 projected pixels/frame in 8.8 fixed
#define LANCE_SPREAD 256  // max side ratio 256/1024 (~14-degree half cone)
#define LANCE_LIFETIME 40
#define LANCE_DAMAGE 10
typedef struct {
    fixed x;
    fixed y;
    fixed vx;
    fixed vy;
    uint16_t hit_mask;
    int life;
    int active;
    uint8_t seed;
} BoneLance;
static BoneLance s_lances[MAX_PROJECTILES];
static int s_lance_cooldown = 0;

#define MAX_BONE_PARTICLES 32
typedef struct {
    fixed x;
    fixed y;
    fixed vx;
    fixed vy;
    uint8_t life;
    uint8_t size;
    uint8_t tone;
    uint8_t active;
} BoneParticle;
static BoneParticle s_bone_particles[MAX_BONE_PARTICLES];
static uint8_t s_bone_effect_tick = 0;

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
    return (int)(x >> FIXED_SHIFT);
}

static inline int player_screen_y(fixed x, fixed y) {
    return (int)(y >> FIXED_SHIFT);
}

// ---------------------------------------------------------------------------
// Collision
// ---------------------------------------------------------------------------

static int position_is_free(fixed x, fixed y) {
    int wx = (int)(x >> FIXED_SHIFT);
    int wy = (int)(y >> FIXED_SHIFT);
    static const int offsets[9][2] = {
        {0, 0}, {-4, 0}, {4, 0}, {0, -3}, {0, 3},
        {-3, -2}, {-3, 2}, {3, -2}, {3, 2}
    };
    for (int i = 0; i < 9; i++) {
        int px = wx + offsets[i][0];
        int py = wy + offsets[i][1];
        if (px < 0 || px >= WORLD_W || py < 0 || py >= WORLD_H) return 0;
        int cx = px / COLLISION_SCALE;
        int cy = py / COLLISION_SCALE;
        if (cx < 0 || cx >= COLLISION_W || cy < 0 || cy >= COLLISION_H) return 0;
        if (g_dungeon_collision[cy * COLLISION_W + cx] != 0) return 0;
    }
    return 1;
}

// Sweep in <=1px increments so a frame cannot skip a thin blocked cell.
static int sweep_position(fixed *x, fixed *y, fixed dx, fixed dy) {
    fixed start_x = *x, start_y = *y;
    int ax = abs_int(dx), ay = abs_int(dy);
    int major = ax > ay ? ax : ay;
    int steps = (major + 255) / 256;
    if (steps < 1) steps = 1;
    for (int step = 1; step <= steps; step++) {
        fixed next_x = start_x + (fixed)(((int64_t)dx * step) / steps);
        fixed next_y = start_y + (fixed)(((int64_t)dy * step) / steps);
        if (!position_is_free(next_x, next_y)) return 0;
    }
    *x = start_x + dx;
    *y = start_y + dy;
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

static void build_occlusion_depth_map(void) {
    memset(s_occlusion_depth, 0xFF, sizeof(s_occlusion_depth));
    for (uint32_t i = 0; i < g_dungeon_occlusion_run_count; i++) {
        const DungeonOcclusionRun *run = &g_dungeon_occlusion_runs[i];
        if (run->y >= WORLD_H || run->x + run->length > WORLD_W) continue;
        int16_t *row = &s_occlusion_depth[(uint32_t)run->y * WORLD_W + run->x];
        for (uint32_t x = 0; x < run->length; x++) row[x] = run->depth;
    }
}

static inline int occlusion_blocks_pixel(int x, int y, int actor_depth) {
    if ((uint32_t)x >= WORLD_W || (uint32_t)y >= WORLD_H) return 0;
    return s_occlusion_depth[(uint32_t)y * WORLD_W + x] > actor_depth;
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

    for (int y = sy0; y < sy1; y++) {
        const uint16_t *srow = &src[y * pitch];
        uint16_t *drow = &buffer[(oy + y) * SCREEN_W + ox];
        int x = sx0;
        if (depth >= 0) {
            for (; x < sx1; x++) {
                uint16_t color = srow[x];
                if ((color & BIT(15)) &&
                    !occlusion_blocks_pixel(left + x, top + y, depth))
                    drow[x] = color;
            }
            continue;
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
                cam_x, cam_y, s_draw_item_depth);
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
                             int cam_x, int cam_y, const uint8_t *upper_mask) {
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
                int world_x = left + x, world_y = top + y;
                if (world_x < 0 || world_x >= WORLD_W || world_y < 0 || world_y >= WORLD_H) continue;
                uint32_t world_index = (uint32_t)world_y * WORLD_W + world_x;
                if (upper_mask[world_index >> 3] & (1u << (world_index & 7))) continue;
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

// Stream only newly exposed edges into the 64x32 BG ring map. This function
// runs in VBlank, so neither scanout nor fine-scroll sampling sees a half-updated map.
#define BG_RING_W 64
#define BG_RING_H 32

static int bg_ring_index(int tile, int size) {
    int index = tile % size;
    return index < 0 ? index + size : index;
}

// 512x256 text maps are two 32x32 screen blocks, not a linear 64-column array.
static int bg_map_index(int col, int row) {
    return (col >> 5) * 1024 + row * 32 + (col & 31);
}

static u16 bg_world_tile(int col, int row) {
    if (col < 0 || col >= DUNGEON_BG_MAP_WIDTH_TILES ||
        row < 0 || row >= DUNGEON_BG_MAP_HEIGHT_TILES) return 0;
    return g_dungeon_bg_map[row][col];
}

__attribute__((unused))
static void update_screen_hardware_bg(int is_sub, u16 *map_ptr, int cam_x, int cam_y) {
    int rel_x = cam_x - CACHE_X0;
    int rel_y = cam_y - CACHE_Y0;
    int tile_x = rel_x >> 3;
    int tile_y = rel_y >> 3;
    int ring_x = bg_ring_index(tile_x, BG_RING_W);
    int ring_y = bg_ring_index(tile_y, BG_RING_H);
    int fine_x = rel_x & 7;
    int fine_y = rel_y & 7;
    int *prev_x = is_sub ? &s_top_map_tile_x : &s_bot_map_tile_x;
    int *prev_y = is_sub ? &s_top_map_tile_y : &s_bot_map_tile_y;
    int *ready = is_sub ? &s_top_map_ready : &s_bot_map_ready;

    if (!*ready || tile_x - *prev_x >= BG_RING_W || tile_x - *prev_x <= -BG_RING_W ||
        tile_y - *prev_y >= BG_RING_H || tile_y - *prev_y <= -BG_RING_H) {
        for (int my = 0; my < BG_RING_H; my++) {
            int world_y = tile_y + bg_ring_index(my - ring_y, BG_RING_H);
            for (int mx = 0; mx < BG_RING_W; mx++) {
                int world_x = tile_x + bg_ring_index(mx - ring_x, BG_RING_W);
                map_ptr[bg_map_index(mx, my)] = bg_world_tile(world_x, world_y);
            }
        }
    } else {
        int dx = tile_x - *prev_x;
        int dy = tile_y - *prev_y;
        int step = dx < 0 ? -1 : 1;
        for (int x = dx < 0 ? *prev_x - 1 : *prev_x + 1; dx && (dx < 0 ? x >= tile_x : x <= tile_x); x += step) {
            int mx = bg_ring_index(x, BG_RING_W);
            for (int my = 0; my < BG_RING_H; my++) {
                int world_y = tile_y + bg_ring_index(my - ring_y, BG_RING_H);
                map_ptr[bg_map_index(mx, my)] = bg_world_tile(x, world_y);
            }
        }
        step = dy < 0 ? -1 : 1;
        for (int y = dy < 0 ? *prev_y - 1 : *prev_y + 1; dy && (dy < 0 ? y >= tile_y : y <= tile_y); y += step) {
            int my = bg_ring_index(y, BG_RING_H);
            for (int mx = 0; mx < BG_RING_W; mx++) {
                int world_x = tile_x + bg_ring_index(mx - ring_x, BG_RING_W);
                map_ptr[bg_map_index(mx, my)] = bg_world_tile(world_x, y);
            }
        }
    }

    *prev_x = tile_x;
    *prev_y = tile_y;
    *ready = 1;

    if (is_sub) {
        REG_BG1HOFS_SUB = (ring_x * 8 + fine_x) & 511;
        REG_BG1VOFS_SUB = (ring_y * 8 + fine_y) & 255;
    } else {
        REG_BG1HOFS = (ring_x * 8 + fine_x) & 511;
        REG_BG1VOFS = (ring_y * 8 + fine_y) & 255;
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
                px - PLAYER_ANCHOR_X + min_x, py - PLAYER_ANCHOR_Y + min_y,
                cam_x, cam_y, s_draw_item_depth);
}

static void draw_hit_spark(uint16_t *buffer, int x, int y, int cam_x, int cam_y, int phase) {
    uint16_t cyan = RGB15(9, 25, 31) | BIT(15);
    uint16_t ivory = RGB15(31, 28, 20) | BIT(15);
    for (int d = -3; d <= 3; d++) {
        int bx = x + d - cam_x, by = y - cam_y;
        if (bx >= 0 && bx < SCREEN_W && by >= 0 && by < SCREEN_H &&
            !occlusion_blocks_pixel(x + d, y, s_draw_item_depth))
            buffer[by * SCREEN_W + bx] = ((d + phase) & 1) ? cyan : ivory;
        bx = x - cam_x; by = y + d - cam_y;
        if (bx >= 0 && bx < SCREEN_W && by >= 0 && by < SCREEN_H &&
            !occlusion_blocks_pixel(x, y + d, s_draw_item_depth))
            buffer[by * SCREEN_W + bx] = ((d + phase) & 1) ? ivory : cyan;
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
                px - PLAYER_ANCHOR_X + min_x, py - PLAYER_ANCHOR_Y + min_y,
                cam_x, cam_y, s_draw_item_depth);
    if (e->hit_timer > 0)
        draw_hit_spark(buffer, px, py - 24, cam_x, cam_y, e->hit_timer);
}

static void bone_effect_pixel(uint16_t *buffer, int x, int y, int cam_x, int cam_y, uint16_t color) {
    int sx = x - cam_x, sy = y - cam_y;
    if (sx >= 0 && sx < SCREEN_W && sy >= 0 && sy < SCREEN_H &&
        !occlusion_blocks_pixel(x, y, s_draw_item_depth))
        buffer[sy * SCREEN_W + sx] = color;
}

static void draw_bone_lance(uint16_t *buffer, const BoneLance *lance, int cam_x, int cam_y) {
    int px = player_screen_x(lance->x, lance->y);
    int py = player_screen_y(lance->x, lance->y);
    int ax = lance->vx < 0 ? -lance->vx : lance->vx;
    int ay = lance->vy < 0 ? -lance->vy : lance->vy;
    int major = ax > ay ? ax : ay;
    if (major == 0) return;

    int ux = (int)(((int64_t)lance->vx * 256) / major);
    int uy = (int)(((int64_t)lance->vy * 256) / major);
    int length = 8 + (lance->seed & 3);
    int half = length / 2;
    uint16_t bone = RGB15(27, 23, 17) | BIT(15);
    uint16_t ivory = RGB15(31, 30, 25) | BIT(15);
    uint16_t warm = RGB15(30, 25, 17) | BIT(15);

    for (int i = 0; i < length; i++) {
        int along = i - half;
        int wobble = ((lance->seed + i * 5) % 7 == 0) ? (((lance->seed + i) & 1) ? 1 : -1) : 0;
        int x = px + ((ux * along - uy * wobble) >> 8);
        int y = py + ((uy * along + ux * wobble) >> 8);
        uint16_t color = i == length - 1 ? ivory :
                         i < 2 ? warm : ((i + lance->seed) % 4 == 0 ? ivory : bone);
        bone_effect_pixel(buffer, x, y, cam_x, cam_y, color);

        // A few broken barbs keep each splinter irregular without tracing its edge.
        if ((i == 1 && (lance->seed & 1)) ||
            (i == length - 3 && (lance->seed & 2))) {
            int side = ((lance->seed + i) & 1) ? 1 : -1;
            bone_effect_pixel(buffer, x + ((-uy * side) >> 8),
                              y + ((ux * side) >> 8), cam_x, cam_y, warm);
        }
        if (i == length - 2 && (lance->seed & 1)) {
            bone_effect_pixel(buffer, x + ((-uy) >> 8), y + (ux >> 8),
                              cam_x, cam_y, ivory);
        }
    }

    if (((s_bone_effect_tick + lance->seed) & 3) == 0) {
        int tx = px + ((ux * (half + 1)) >> 8);
        int ty = py + ((uy * (half + 1)) >> 8);
        bone_effect_pixel(buffer, tx, ty, cam_x, cam_y, warm);
    }
}

static void draw_bone_particle(uint16_t *buffer, const BoneParticle *p, int index, int cam_x, int cam_y) {
    static const uint16_t tones[2] = {
        RGB15(23, 22, 17) | BIT(15), RGB15(30, 27, 21) | BIT(15)
    };
    int x = p->x >> 8, y = p->y >> 8;
    int fade = p->life <= 2;
    uint16_t color = fade ? tones[0] : tones[p->tone % 2];
    bone_effect_pixel(buffer, x, y, cam_x, cam_y, color);
    if (p->size > 1 && p->life > 2)
        bone_effect_pixel(buffer, x + ((index & 1) ? 1 : 0), y + ((index & 1) ? 0 : 1),
                          cam_x, cam_y, tones[0]);
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
                buffer[sy * SCREEN_W + sx] = color;
        }
    }
}

static void render_screen(uint16_t *buffer, int cam_x, int cam_y,
                          uint32_t *out_floor, uint32_t *out_shadow, uint32_t *out_blit) {
    DrawItem items[MAX_DRAW_ITEMS + MAX_ENEMIES + MAX_PROJECTILES + MAX_DEATH_CHUNKS + MAX_BONE_PARTICLES + 1];
    int count = 0;

    // Background is rendered directly from pre-rendered 3D world bitmap

    // Add player only if visible on this screen
    int psx = player_screen_x(s_player.x, s_player.y);
    int psy = player_screen_y(s_player.x, s_player.y);
    int pl_left = psx - PLAYER_ANCHOR_X - cam_x;
    int pl_top = psy - PLAYER_ANCHOR_Y - cam_y;
    if (pl_left < SCREEN_W && pl_left + PLAYER_SPRITE_W > 0 &&
        pl_top < SCREEN_H && pl_top + PLAYER_SPRITE_H > 0) {
        if (count < MAX_DRAW_ITEMS) {
            items[count].depth = psy;
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
                items[count].depth = esy;
                items[count].sprite = -2 - e_idx;
                items[count].cx = esx;
                items[count].cy = esy;
                count++;
            }
        }
    }

    for (int p = 0; p < MAX_PROJECTILES; p++) {
        BoneLance *lance = &s_lances[p];
        if (!lance->active) continue;
        int px = player_screen_x(lance->x, lance->y);
        int py = player_screen_y(lance->x, lance->y);
        if (px + 8 < cam_x || px - 8 > cam_x + SCREEN_W ||
            py + 8 < cam_y || py - 8 > cam_y + SCREEN_H) continue;
        if (count < MAX_DRAW_ITEMS + MAX_ENEMIES + MAX_PROJECTILES + MAX_DEATH_CHUNKS) {
            items[count].depth = py;
            items[count].sprite = -2 - MAX_ENEMIES - p;
            items[count].cx = px;
            items[count].cy = py;
            count++;
        }
    }

    for (int i = 0; i < MAX_DEATH_CHUNKS; i++) {
        DeathChunk *chunk = &s_death_chunks[i];
        if (!chunk->active) continue;
        int px = player_screen_x(chunk->x, chunk->y);
        int py = player_screen_y(chunk->x, chunk->y) - (chunk->z >> FIXED_SHIFT);
        if (px + DEATH_CHUNK_SIZE < cam_x || px - DEATH_CHUNK_SIZE > cam_x + SCREEN_W ||
            py + DEATH_CHUNK_SIZE < cam_y || py - DEATH_CHUNK_SIZE > cam_y + SCREEN_H) continue;
        if (count < MAX_DRAW_ITEMS + MAX_ENEMIES + MAX_PROJECTILES + MAX_DEATH_CHUNKS) {
            items[count].depth = player_screen_y(chunk->x, chunk->y);
            items[count].sprite = -2 - MAX_ENEMIES - MAX_PROJECTILES - i;
            items[count].cx = px;
            items[count].cy = py;
            count++;
        }
    }

    for (int p = 0; p < MAX_BONE_PARTICLES; p++) {
        BoneParticle *particle = &s_bone_particles[p];
        if (!particle->active) continue;
        int px = player_screen_x(particle->x, particle->y);
        int py = player_screen_y(particle->x, particle->y);
        if (px < cam_x || px >= cam_x + SCREEN_W || py < cam_y || py >= cam_y + SCREEN_H) continue;
        items[count].depth = py;
        items[count].sprite = -2 - MAX_ENEMIES - MAX_PROJECTILES - MAX_DEATH_CHUNKS - p;
        items[count].cx = px;
        items[count].cy = py;
        count++;
    }

    // Blit pre-rendered 3D world background
    uint32_t floor_start_ticks = cpuGetTiming();
    for (int y = 0; y < SCREEN_H; y++) {
        int wy = cam_y + y;
        if (wy < 0 || wy >= WORLD_H) {
            memset(&buffer[y * SCREEN_W], 0, SCREEN_W * sizeof(uint16_t));
        } else {
            int wx = cam_x;
            if (wx < 0) wx = 0;
            if (wx + SCREEN_W > WORLD_W) wx = WORLD_W - SCREEN_W;
            const uint16_t *src = &g_dungeon_world_color[wy * WORLD_W + wx];
            dmaCopyHalfWords(3, src, &buffer[y * SCREEN_W], SCREEN_W * sizeof(uint16_t));
        }
    }

    if (out_floor) *out_floor = cpuGetTiming() - floor_start_ticks;

    // 1) Composite dynamic entity shadows (player & enemies)
    uint32_t t_sh0 = cpuGetTiming();
    for (int i = 0; i < count; i++) {
        if (items[i].sprite == -1) {
            draw_shadow_mask(buffer, g_character_shadow_masks[s_player.char_id][s_player.dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[s_player.char_id][s_player.dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y, g_dungeon_upper_mask);
        } else if (items[i].sprite <= -2 &&
                   items[i].sprite > -2 - MAX_ENEMIES) {
            int e_idx = -2 - items[i].sprite;
            const Enemy *e = &s_enemies[e_idx];
            draw_shadow_mask(buffer, g_character_shadow_masks[e->char_id][e->dir],
                             PLAYER_SHADOW_W, PLAYER_SHADOW_H,
                             g_character_shadow_bounds[e->char_id][e->dir],
                             items[i].cx - PLAYER_SHADOW_W / 2,
                             items[i].cy - PLAYER_SHADOW_H / 2, cam_x, cam_y, g_dungeon_upper_mask);
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
        s_draw_item_depth = items[i].depth;
        int sp = items[i].sprite;
        if (sp >= 0) {
            blit_tile(buffer, sp, items[i].cx, items[i].cy, cam_x, cam_y);
        } else if (sp == -1) {
            draw_player(buffer, cam_x, cam_y);
        } else if (sp <= -2 - MAX_ENEMIES - MAX_PROJECTILES - MAX_DEATH_CHUNKS) {
            int particle_idx = -2 - MAX_ENEMIES - MAX_PROJECTILES - MAX_DEATH_CHUNKS - sp;
            draw_bone_particle(buffer, &s_bone_particles[particle_idx], particle_idx, cam_x, cam_y);
        } else if (sp <= -2 - MAX_ENEMIES - MAX_PROJECTILES) {
            int chunk_idx = -2 - MAX_ENEMIES - MAX_PROJECTILES - sp;
            draw_death_chunk(buffer, &s_death_chunks[chunk_idx], cam_x, cam_y);
        } else if (sp <= -2 - MAX_ENEMIES) {
            draw_bone_lance(buffer, &s_lances[-2 - MAX_ENEMIES - sp], cam_x, cam_y);
        } else {
            draw_enemy(buffer, &s_enemies[-2 - sp], cam_x, cam_y);
        }
    }
    uint32_t blit_ticks = cpuGetTiming() - t_bl0;

    if (out_shadow) *out_shadow = shadow_ticks;
    if (out_blit) *out_blit = blit_ticks;
}

static const char s_fps_chars[] = " FPS:C0123456789";
static const uint8_t s_fps_font[][7] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00}, // space
    {0x1F,0x10,0x10,0x1E,0x10,0x10,0x10}, // F
    {0x1E,0x11,0x11,0x1E,0x10,0x10,0x10}, // P
    {0x0F,0x10,0x10,0x0E,0x01,0x01,0x1E}, // S
    {0x00,0x04,0x04,0x00,0x04,0x04,0x00}, // :
    {0x0E,0x11,0x10,0x10,0x10,0x11,0x0E}, // C
    {0x0E,0x11,0x13,0x15,0x19,0x11,0x0E}, // 0
    {0x04,0x0C,0x04,0x04,0x04,0x04,0x0E}, // 1
    {0x0E,0x11,0x01,0x02,0x04,0x08,0x1F}, // 2
    {0x1E,0x01,0x01,0x0E,0x01,0x01,0x1E}, // 3
    {0x02,0x06,0x0A,0x12,0x1F,0x02,0x02}, // 4
    {0x1F,0x10,0x10,0x1E,0x01,0x01,0x1E}, // 5
    {0x0E,0x10,0x10,0x1E,0x11,0x11,0x0E}, // 6
    {0x1F,0x01,0x02,0x04,0x08,0x08,0x08}, // 7
    {0x0E,0x11,0x11,0x0E,0x11,0x11,0x0E}, // 8
    {0x0E,0x11,0x11,0x0F,0x01,0x01,0x0E}  // 9
};

static void draw_fps_hud(uint16_t *buffer) {
    char label[24];
    unsigned long cpu_ms = (unsigned long)(g_perf.cpu_ticks / 33514u);
    unsigned long present_ms = (unsigned long)(g_perf.present_ticks / 33514u);
    if (cpu_ms > 99) cpu_ms = 99;
    if (present_ms > 99) present_ms = 99;
    snprintf(label, sizeof(label), "FPS:%2lu C:%02lu P:%02lu",
             (unsigned long)g_perf.fps, cpu_ms, present_ms);
    const int left = 4, top = 4, pad = 2, char_w = 6, glyph_w = 5, glyph_h = 7;
    int text_w = (int)strlen(label) * char_w - 1;
    int box_w = text_w + pad * 2;
    int box_h = glyph_h + pad * 2;
    uint16_t panel = RGB15(1, 2, 1) | BIT(15);
    uint16_t border = RGB15(0, 16, 0) | BIT(15);
    uint16_t ink = RGB15(18, 31, 18) | BIT(15);

    for (int y = 0; y < box_h; y++) {
        for (int x = 0; x < box_w; x++) {
            int edge = x == 0 || y == 0 || x == box_w - 1 || y == box_h - 1;
            buffer[(top + y) * SCREEN_W + left + x] = edge ? border : panel;
        }
    }

    for (int i = 0; label[i]; i++) {
        int glyph = 0;
        while (s_fps_chars[glyph] && s_fps_chars[glyph] != label[i]) glyph++;
        if (!s_fps_chars[glyph]) continue;
        const uint8_t *rows = s_fps_font[glyph];
        for (int y = 0; y < glyph_h; y++) {
            for (int x = 0; x < glyph_w; x++) {
                if (rows[y] & (1u << (glyph_w - 1 - x)))
                    buffer[(top + pad + y) * SCREEN_W + left + pad + i * char_w + x] = ink;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------

static uint32_t present_both_screens(int top_cam_x, int top_cam_y,
                                      int bot_cam_x, int bot_cam_y) {
    (void)top_cam_x; (void)top_cam_y; (void)bot_cam_x; (void)bot_cam_y;
    swiWaitForVBlank();
    dmaCopyWords(3, s_top_screen_buf, s_top_vram, SCREEN_W * SCREEN_H * 2);
    dmaCopyWords(3, s_bot_screen_buf, s_bot_vram, SCREEN_W * SCREEN_H * 2);
    return 0;
}

// ---------------------------------------------------------------------------
// Enemies
// ---------------------------------------------------------------------------

static void enemies_init(void) {
    // Find free pixel-space points around the player; a blocked map may yield fewer enemies.
    static const int dir_cycle[8] = { DIR_SOUTH, DIR_SOUTHWEST, DIR_WEST, DIR_NORTHWEST,
                                      DIR_NORTH, DIR_NORTHEAST, DIR_EAST, DIR_SOUTHEAST };
    int spawned = 0;
    for (int i = 0; i < MAX_ENEMIES; i++) {
        Enemy *e = &s_enemies[i];
        e->active = 0;
        e->dir = dir_cycle[i & 7];
        e->frame = 0;
        e->anim_timer = 0;
        e->char_id = (i == 4 || i == 5) ? CHAR_CHARGER : CHAR_SKELETON;
        e->step_count = 0;
        e->step_limit = 60 + i * 15;
        e->hp = e->char_id == CHAR_CHARGER ? 90 : 40;
        e->hit_timer = 0;

        int found = 0;
        for (int radius = 64; radius <= 192 && !found; radius += 32) {
            for (int dy = -radius; dy <= radius && !found; dy += 32) {
                for (int dx = -radius; dx <= radius && !found; dx += 32) {
                    if (abs_int(dx) != radius && abs_int(dy) != radius) continue;
                    fixed x = TO_FIXED(SPAWN_PIXEL_X + dx);
                    fixed y = TO_FIXED(SPAWN_PIXEL_Y + dy);
                    if (!position_is_free(x, y)) continue;
                    int clear = 1;
                    for (int j = 0; j < MAX_ENEMIES; j++) {
                        if (!s_enemies[j].active) continue;
                        int ex = player_screen_x(x, y) - player_screen_x(s_enemies[j].x, s_enemies[j].y);
                        int ey = player_screen_y(x, y) - player_screen_y(s_enemies[j].x, s_enemies[j].y);
                        if (ex * ex + ey * ey < 48 * 48) { clear = 0; break; }
                    }
                    if (!clear) continue;
                    e->x = x;
                    e->y = y;
                    e->active = 1;
                    e->frame = (spawned * 3) % PLAYER_NUM_FRAMES;
                    spawned++;
                    found = 1;
                }
            }
        }
    }
}

static int abs_int(int v) { return v < 0 ? -v : v; }

static int lance_dir_from_screen(int dx, int dy) {
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

static void lance_fire(int aim_x, int aim_y, int touch_aim) {
    if (s_lance_cooldown > 0) return;
    int slots[LANCE_PELLETS], free_count = 0;
    for (int i = 0; i < MAX_PROJECTILES && free_count < LANCE_PELLETS; i++) {
        if (!s_lances[i].active) slots[free_count++] = i;
    }
    if (free_count < LANCE_PELLETS) return;

    int px = player_screen_x(s_player.x, s_player.y);
    int py = player_screen_y(s_player.x, s_player.y);
    int dir = lance_dir_from_screen(aim_x - px, aim_y - py);
    static const int dir_dx[8] = { 0, -1, -1, -1, 0, 1, 1, 1 };
    static const int dir_dy[8] = { 1, 1, 0, -1, -1, -1, 0, 1 };
    int sx = dir_dx[dir], sy = dir_dy[dir];
    fixed forward_x = sx * LANCE_SPEED;
    fixed forward_y = sy * LANCE_SPEED;
    if (sx && sy) {
        forward_x = (forward_x * 181) >> 8;
        forward_y = (forward_y * 181) >> 8;
    }

    for (int pellet = 0; pellet < LANCE_PELLETS; pellet++) {
        fixed spread = (pellet - (LANCE_PELLETS / 2)) * (LANCE_SPREAD / 2);
        fixed vx = forward_x - ((forward_y * spread) >> 10);
        fixed vy = forward_y + ((forward_x * spread) >> 10);
        BoneLance *lance = &s_lances[slots[pellet]];
        lance->x = s_player.x + vx / 4;
        lance->y = s_player.y + vy / 4;
        lance->vx = vx;
        lance->vy = vy;
        lance->hit_mask = 0;
        lance->seed = (uint8_t)(slots[pellet] * 11 + pellet * 6 + s_bone_effect_tick);
        lance->life = LANCE_LIFETIME;
        lance->active = 1;
    }
    s_lance_cooldown = LANCE_COOLDOWN;
    s_player.dir = dir;
    char msg[48];
    snprintf(msg, sizeof(msg), "BONE_SHOTGUN_FIRE pellets=%d touch=%d", LANCE_PELLETS, touch_aim);
    nocashMessage(msg);
}

static uint8_t s_bone_particle_cursor = 0;

static void emit_bone_particle(const BoneLance *lance, int slot) {
    uint32_t age = (uint32_t)(LANCE_LIFETIME - lance->life);
    uint32_t hash = (uint32_t)(slot + 1) * 0x45d9f3bu ^ (age + lance->seed) * 0x27d4eb2du;
    hash ^= hash >> 16;
    int ax = lance->vx < 0 ? -lance->vx : lance->vx;
    int ay = lance->vy < 0 ? -lance->vy : lance->vy;
    int major = ax > ay ? ax : ay;
    if (major == 0) return;

    int jitter = (int)(hash & 0x1ffu) - 256;
    fixed px = (fixed)player_screen_x(lance->x, lance->y) * 256;
    fixed py = (fixed)player_screen_y(lance->x, lance->y) * 256;
    fixed perp_x = (fixed)(((int64_t)-lance->vy * 256) / major);
    fixed perp_y = (fixed)(((int64_t)lance->vx * 256) / major);
    unsigned index = s_bone_particle_cursor++ & (MAX_BONE_PARTICLES - 1);
    BoneParticle *p = &s_bone_particles[index];
    p->x = px;
    p->y = py;
    p->vx = -lance->vx / 3 + (perp_x * jitter >> 8);
    p->vy = -lance->vy / 3 + (perp_y * jitter >> 8);
    p->life = (uint8_t)(4 + ((hash >> 19) & 3u));
    p->size = (uint8_t)(1 + ((hash >> 12) & 1u));
    p->tone = (uint8_t)((hash >> 7) % 2u);
    p->active = 1;
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
        int offset_y = sy + DEATH_CHUNK_SIZE / 2 - PLAYER_ANCHOR_Y;
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

static void bone_particles_update(void) {
    for (int i = 0; i < MAX_BONE_PARTICLES; i++) {
        BoneParticle *p = &s_bone_particles[i];
        if (!p->active) continue;
        p->x += p->vx;
        p->y += p->vy;
        if (--p->life == 0) p->active = 0;
    }
}

static void lances_update(void) {
    s_bone_effect_tick++;
    bone_particles_update();
    death_chunks_update();
    if (s_lance_cooldown > 0) s_lance_cooldown--;
    for (int p = 0; p < MAX_PROJECTILES; p++) {
        BoneLance *lance = &s_lances[p];
        if (!lance->active) continue;
        fixed start_x = lance->x, start_y = lance->y;
        int major = abs_int(lance->vx) > abs_int(lance->vy) ? abs_int(lance->vx) : abs_int(lance->vy);
        int steps = (major + 511) / 512; // sample every 2 px to prevent crossing a 4 px wall cell
        if (steps < 1) steps = 1;
        int blocked = 0;
        for (int step = 1; step <= steps; step++) {
            fixed next_x = start_x + (fixed)(((int64_t)lance->vx * step) / steps);
            fixed next_y = start_y + (fixed)(((int64_t)lance->vy * step) / steps);
            if (!position_is_free(next_x, next_y)) {
                blocked = 1;
                break;
            }
            lance->x = next_x;
            lance->y = next_y;
        }
        lance->life--;
        if (blocked || lance->life <= 0) {
            lance->active = 0;
            continue;
        }
        uint32_t particle_roll = (uint32_t)s_bone_effect_tick * (lance->seed * 2u + 11u) + (uint32_t)p * 37u;
        particle_roll ^= particle_roll >> 3;
        if (particle_roll % 5u < 2u) emit_bone_particle(lance, p);
        int lx = player_screen_x(lance->x, lance->y);
        int ly = player_screen_y(lance->x, lance->y);
        for (int i = 0; i < MAX_ENEMIES; i++) {
            Enemy *e = &s_enemies[i];
            if (!e->active || (lance->hit_mask & (1u << i))) continue;
            int dx = lx - player_screen_x(e->x, e->y);
            int dy = ly - player_screen_y(e->x, e->y);
            if (dx * dx + dy * dy > 100) continue;
            e->hp -= LANCE_DAMAGE;
            e->hit_timer = 8;
            lance->hit_mask |= (uint16_t)(1u << i);
            char msg[64];
            if (e->hp <= 0) {
                death_chunks_spawn(e, lance->vx, lance->vy);
                e->active = 0;
                snprintf(msg, sizeof(msg), "BONE_LANCE_KILL enemy=%d", i);
            } else {
                snprintf(msg, sizeof(msg), "BONE_LANCE_HIT enemy=%d hp=%d", i, e->hp);
            }
            nocashMessage(msg);
        }
    }
}

static int nearest_enemy_screen(int *out_x, int *out_y) {
    int px = player_screen_x(s_player.x, s_player.y);
    int py = player_screen_y(s_player.x, s_player.y);
    int nearest = -1, best = 0x7FFFFFFF;
    for (int i = 0; i < MAX_ENEMIES; i++) {
        if (!s_enemies[i].active) continue;
        int ex = player_screen_x(s_enemies[i].x, s_enemies[i].y);
        int ey = player_screen_y(s_enemies[i].x, s_enemies[i].y);
        int distance = abs_int(ex - px) + abs_int(ey - py);
        if (distance < best) { best = distance; nearest = i; }
    }
    if (nearest >= 0) {
        *out_x = player_screen_x(s_enemies[nearest].x, s_enemies[nearest].y);
        *out_y = player_screen_y(s_enemies[nearest].x, s_enemies[nearest].y);
    }
    return nearest;
}

static void enemies_update(void) {
    // Screen-space direction vectors (sdx, sdy) for DIR_SOUTH .. DIR_SOUTHEAST
    static const int dir_dx[8] = { 0, -1, -1, -1,  0,  1, 1, 1 };
    static const int dir_dy[8] = { 1,  1,  0, -1, -1, -1, 0, 1 };

    for (int i = 0; i < MAX_ENEMIES; i++) {
        Enemy *e = &s_enemies[i];
        if (!e->active) continue;
        if (e->hit_timer > 0) e->hit_timer--;

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

        fixed next_x = e->x, next_y = e->y;

        if (sweep_position(&next_x, &next_y, vx, vy)) {
            e->x = next_x;
            e->y = next_y;
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
    s_player.x = TO_FIXED(SPAWN_PIXEL_X);
    s_player.y = TO_FIXED(SPAWN_PIXEL_Y);
    s_player.dir = DIR_SOUTH;
    s_player.frame = 0;
    s_player.is_moving = 0;
    s_player.anim_timer = 0;
    s_player.char_id = CHAR_HERO;

    enemies_init();
}

static void player_update(uint32_t keys, uint32_t keys_down, int touch_x, int touch_y, int touch_down) {
    // Keep X/Y/SELECT for the existing character preview controls; A now casts Bone Lance.
    if (keys_down & (KEY_X | KEY_Y | KEY_SELECT)) {
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

    // Camera: centered on player, clamped to world bounds
    int target_x = player_screen_x(s_player.x, s_player.y) - SCREEN_W / 2;
    int target_y = player_screen_y(s_player.x, s_player.y) - SCREEN_H / 2;

    if (target_x < 0) target_x = 0;
    if (target_x > WORLD_W - SCREEN_W) target_x = WORLD_W - SCREEN_W;
    if (target_y < 0) target_y = 0;
    if (target_y > WORLD_H - SCREEN_H) target_y = WORLD_H - SCREEN_H;

    s_cam_x = target_x;
    s_cam_y = target_y;

    int aim_x = player_screen_x(s_player.x, s_player.y);
    int aim_y = player_screen_y(s_player.x, s_player.y) - 16;
    if (touch_down) {
        aim_x = touch_x + s_cam_x;
        aim_y = touch_y + s_cam_y;
    } else if (keys & KEY_A) {
        if (nearest_enemy_screen(&aim_x, &aim_y) < 0) {
            static const int aim_dx[8] = { 0, -1, -1, -1, 0, 1, 1, 1 };
            static const int aim_dy[8] = { 1, 1, 0, -1, -1, -1, 0, 1 };
            aim_x += aim_dx[s_player.dir] * 32;
            aim_y += aim_dy[s_player.dir] * 32;
        }
    }
    if (touch_down || (keys & KEY_A)) lance_fire(aim_x, aim_y, touch_down);
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

    // Pointer to Bottom BG2 VRAM in CPU address space:
    s_bot_vram = (u16 *)0x06020000;

    // Load Background Palette to Main and Sub engines
    dmaCopyWords(3, g_dungeon_bg_palette, BG_PALETTE, DUNGEON_BG_PALETTE_SIZE * 2);
    dmaCopyWords(3, g_dungeon_bg_palette, BG_PALETTE_SUB, DUNGEON_BG_PALETTE_SIZE * 2);

    // Initialize Main BG1 (Hardware Tiled Floor)
    // tileBase 0 = 0x06000000 (28 KB tiles), mapBase 16 = 0x06008000 (4 KB map)
    int bot_hw_bg = bgInit(1, BgType_Text8bpp, BgSize_T_512x256, 16, 0);
    bgSetPriority(bot_hw_bg, 3); // Lowest priority (drawn behind entities)
    s_bot_map_ptr = bgGetMapPtr(bot_hw_bg);
    u16 *bot_tile_ptr = bgGetGfxPtr(bot_hw_bg);
    dmaCopyWords(3, g_dungeon_bg_tiles, bot_tile_ptr, sizeof(g_dungeon_bg_tiles));

    // Initialize Main BG2 (16-bit Bitmap for Entities & dynamic shadows at mapBase 8 = 0x06020000)
    s_bot_bg = bgInit(2, BgType_Bmp16, BgSize_B16_256x256, 8, 0);
    bgSetPriority(s_bot_bg, 0); // High priority (drawn on top of BG1)

    // Sub Engine (Top Screen): Mode 5
    // VRAM_C (128 KB) at 0x06200000 cleanly split:
    // BG1 Text8bpp: tileBase 0 (28 KB), mapBase 14 (0x06207000, 4 KB)
    // BG2 Bmp16:    mapBase 2 (0x06208000, 256x192x2 = 96 KB)
    videoSetModeSub(MODE_5_2D);
    vramSetBankC(VRAM_C_SUB_BG_0x06200000); // 128 KB for Sub BG (contains both BG1 and BG2)

    // Initialize Sub BG1 (Hardware Tiled Floor)
    int top_hw_bg = bgInitSub(1, BgType_Text8bpp, BgSize_T_512x256, 14, 0);
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
    s_cam_y = player_screen_y(s_player.x, s_player.y) - SCREEN_H / 2;
    if (s_cam_x < 0) s_cam_x = 0;
    if (s_cam_x > WORLD_W - SCREEN_W) s_cam_x = WORLD_W - SCREEN_W;
    if (s_cam_y < 0) s_cam_y = 0;
    if (s_cam_y > WORLD_H - SCREEN_H) s_cam_y = WORLD_H - SCREEN_H;

    build_occlusion_depth_map();
    render_screen(s_top_screen_buf, s_cam_x, s_cam_y - SCREEN_H, NULL, NULL, NULL);
    dmaCopyWords(3, s_top_screen_buf, s_top_vram, SCREEN_W * SCREEN_H * 2);

    render_screen(s_bot_screen_buf, s_cam_x, s_cam_y, NULL, NULL, NULL);
    dmaCopyWords(3, s_bot_screen_buf, s_bot_vram, SCREEN_W * SCREEN_H * 2);

    while (1) {
        uint32_t frame_start_ticks = cpuGetTiming();
        uint32_t start_vblank = s_vblank_count;

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
        player_update(keys_held, keys_down, touch.px, touch.py, touch_down);
        enemies_update();
        lances_update();
        uint32_t logic_ticks = cpuGetTiming() - t0;

        uint32_t top_floor = 0, top_sh = 0, top_bl = 0;
        uint32_t bot_floor = 0, bot_sh = 0, bot_bl = 0;

        int top_cam_x = s_cam_x;
        int top_cam_y = s_cam_y - SCREEN_H;

        // Render entities and dynamic shadows for top screen
        uint32_t t1 = cpuGetTiming();
        render_screen(s_top_screen_buf, top_cam_x, top_cam_y, &top_floor, &top_sh, &top_bl);
        draw_fps_hud(s_top_screen_buf);
        uint32_t top_ticks = cpuGetTiming() - t1;

        // Render entities and dynamic shadows for bottom screen
        uint32_t t2 = cpuGetTiming();
        render_screen(s_bot_screen_buf, s_cam_x, s_cam_y, &bot_floor, &bot_sh, &bot_bl);
        uint32_t bot_ticks = cpuGetTiming() - t2;

        // CPU rendering finished before waiting for VBlank
        uint32_t cpu_ticks = cpuGetTiming() - frame_start_ticks;
        int vcount_done = REG_VCOUNT;

        uint32_t t3 = cpuGetTiming();
        uint32_t bg_ticks = present_both_screens(top_cam_x, top_cam_y, s_cam_x, s_cam_y);
        uint32_t present_ticks = cpuGetTiming() - t3;

        uint32_t vblanks_elapsed = s_vblank_count - start_vblank;
        if (vblanks_elapsed == 0) vblanks_elapsed = 1;

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

        uint32_t enemies = 0, lances = 0;
        for (int i = 0; i < MAX_ENEMIES; i++) enemies += s_enemies[i].active != 0;
        for (int i = 0; i < MAX_PROJECTILES; i++) lances += s_lances[i].active != 0;
        g_nav_state.x = s_player.x;
        g_nav_state.y = s_player.y;
        g_nav_state.cam_x = s_cam_x;
        g_nav_state.cam_y = s_cam_y;
        g_nav_state.input = keys_held & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
        g_nav_state.moving = s_player.is_moving;
        g_nav_state.blocked_moves = s_blocked_moves;
        g_nav_state.active_enemies = enemies;
        g_nav_state.active_lances = lances;
        g_nav_state.frame_index = g_perf.frame_index;
        if ((g_perf.frame_index % 15) == 0) {
            char nav_buf[120];
            snprintf(nav_buf, sizeof(nav_buf), "NAV frame=%lu x=%ld y=%ld cam=%lu,%lu in=%lu move=%lu blocked=%lu enemies=%lu lances=%lu\\n",
                     (unsigned long)g_nav_state.frame_index, (long)g_nav_state.x, (long)g_nav_state.y,
                     (unsigned long)g_nav_state.cam_x, (unsigned long)g_nav_state.cam_y,
                     (unsigned long)g_nav_state.input, (unsigned long)g_nav_state.moving,
                     (unsigned long)g_nav_state.blocked_moves, (unsigned long)g_nav_state.active_enemies,
                     (unsigned long)g_nav_state.active_lances);
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
    }

    return 0;
}
