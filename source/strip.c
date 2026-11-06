#include "strip.h"
#include "strip_kit.h"

#include <string.h>

#define STRIP_MAP_H_TILES (STRIP_WIN_H_PX / 8)
#define STRIP_COLLISION_W (STRIP_W_CELLS)
#define STRIP_COLLISION_H (STRIP_WIN_H_PX / COLLISION_SCALE)
#define STRIP_BAND_TILES (STRIP_BAND_PX / 8)
#define STRIP_BAND_CELLS (STRIP_BAND_PX / COLLISION_SCALE)
#define STRIP_MAP_SHIFT_ROWS (STRIP_SHIFT_PX / 8)
#define STRIP_COLLISION_SHIFT_ROWS (STRIP_SHIFT_PX / COLLISION_SCALE)
#define STRIP_MAP_ROW_BYTES (STRIP_W_TILES * sizeof(uint16_t))
#define STRIP_COLLISION_ROW_BYTES (STRIP_COLLISION_W / 4)
#define STRIP_MAX_STAMPS_PER_BAND 3
#define STRIP_START_CLEAR_BANDS 3
#define STRIP_LANE_HALF_WIDTH_PX 32

static uint16_t s_map[STRIP_W_TILES * STRIP_MAP_H_TILES];
static uint8_t s_collision[(STRIP_COLLISION_W * STRIP_COLLISION_H) / 4];
static uint32_t s_occlusion_row_start[STRIP_WIN_H_PX + 1];
static const uint16_t s_fallback_palette[256];
static const uint8_t s_fallback_tile[1][64];
static int32_t s_next_band;
static int32_t s_shift_total_px;
static uint32_t s_seed;
static int s_kit_valid;
#define STRIP_INITIAL_BANDS (STRIP_MAP_H_TILES / STRIP_BAND_TILES)

static Arena s_arena = {
    .name = "vertical strip",
    .world_w = STRIP_W_PX,
    .world_h = STRIP_WIN_H_PX,
    .collision_w = STRIP_COLLISION_W,
    .collision_h = STRIP_COLLISION_H,
    .map_w = STRIP_W_TILES,
    .map_h = STRIP_MAP_H_TILES,
    .num_tiles = 0,
    .player_x = STRIP_W_PX / 2,
    .player_y = STRIP_WIN_H_PX - 256,
    .num_enemies = 0,
    .collision = s_collision,
    .palette = 0,
    .tiles = 0,
    .map = s_map,
    .occlusion_runs = 0,
    .occlusion_row_start = s_occlusion_row_start,
    .enemies = 0
};

static uint32_t hash32(uint32_t value) {
    value ^= value >> 16;
    value *= 0x7feb352du;
    value ^= value >> 15;
    value *= 0x846ca68bu;
    value ^= value >> 16;
    return value;
}

static uint32_t band_hash(int32_t band, uint32_t salt) {
    return hash32(s_seed ^ ((uint32_t)band * 0x9e3779b9u) ^ salt);
}

// Hash-selected anchor points every four bands are linearly interpolated. Their
// x range is only 32 px, so neighboring lane centers differ by at most 8 px;
// the 64 px-wide reserved corridor therefore overlaps safely across every seam.
int strip_lane_center_px(int32_t band) {
    int32_t anchor = band >> 2;
    int step = (int)(band & 3);
    int a = (int)(band_hash(anchor, 0x51ed270bu) & 7u) - 3;
    int b = (int)(band_hash(anchor + 1, 0x51ed270bu) & 7u) - 3;
    int delta = b - a;
    int interpolated = a + (delta * step) / 4;
    return (STRIP_W_PX / 2) + interpolated * 4;
}

static void packed_collision_set(uint8_t *data, unsigned index, unsigned value) {
    unsigned shift = (index & 3u) << 1;
    uint8_t mask = (uint8_t)(3u << shift);
    data[index >> 2] = (uint8_t)((data[index >> 2] & (uint8_t)~mask) | ((value & 3u) << shift));
}

static int rects_overlap(int ax, int ay, int aw, int ah,
                         int bx, int by, int bw, int bh) {
    return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

static int stamp_overlaps_lane(const StripStamp *stamp, int x_tile, int y_tile,
                               int lane_x) {
    int left = x_tile * 8;
    int right = left + (int)stamp->w_tiles * 8;
    int lane_left = lane_x - STRIP_LANE_HALF_WIDTH_PX;
    int lane_right = lane_x + STRIP_LANE_HALF_WIDTH_PX;
    if (left < lane_right && lane_left < right) return 1;

    int foot_left = (x_tile * 2) + stamp->foot_x;
    int foot_right = foot_left + stamp->foot_w;
    int lane_cell_left = (lane_left + COLLISION_SCALE - 1) / COLLISION_SCALE;
    int lane_cell_right = lane_right / COLLISION_SCALE;
    return foot_left < lane_cell_right && lane_cell_left < foot_right;
}

static int stamp_can_be_placed(const StripStamp *stamp, int x_tile, int y_tile,
                               int lane_x, const int placed_x[],
                               const int placed_y[], const StripStamp *placed[],
                               int placed_count) {
    int w = stamp->w_tiles;
    int h = stamp->h_tiles;
    if (w == 0 || h == 0 || x_tile < 1 || x_tile + w >= STRIP_W_TILES - 1 ||
        y_tile < 0 || y_tile + h > STRIP_BAND_TILES) return 0;
    if (stamp->foot_w == 0 || stamp->foot_h == 0 || stamp->foot_value > 3 ||
        (unsigned)stamp->foot_x + stamp->foot_w > (unsigned)w * 2u ||
        (unsigned)stamp->foot_y + stamp->foot_h > (unsigned)h * 2u) return 0;
    if (stamp_overlaps_lane(stamp, x_tile, y_tile, lane_x)) return 0;
    for (int i = 0; i < placed_count; i++) {
        if (rects_overlap(x_tile, y_tile, w, h,
                          placed_x[i], placed_y[i],
                          placed[i]->w_tiles, placed[i]->h_tiles)) return 0;
    }
    return 1;
}

static void stamp_band(int32_t band, int map_row, int collision_row) {
    if ((band >= STRIP_INITIAL_BANDS - STRIP_START_CLEAR_BANDS && band < STRIP_INITIAL_BANDS) ||
        g_strip_kit.num_stamps == 0 ||
        g_strip_kit.stamps == 0 || g_strip_kit.floor_h_tiles == 0) return;

    int lane_x = strip_lane_center_px(band);
    int placed_x[STRIP_MAX_STAMPS_PER_BAND];
    int placed_y[STRIP_MAX_STAMPS_PER_BAND];
    const StripStamp *placed[STRIP_MAX_STAMPS_PER_BAND];
    int placed_count = 0;
    unsigned wanted = band_hash(band, 0x68bc21ebu) & 3u;

    for (unsigned n = 0; n < wanted; n++) {
        uint32_t random = band_hash(band, 0x02e5be93u + n * 0x9e3779b9u);
        const StripStamp *stamp = &g_strip_kit.stamps[random % g_strip_kit.num_stamps];
        int period = g_strip_kit.floor_h_tiles;
        int first_y = stamp->phase_row;
        if (first_y >= period) continue;
        int y_slots = ((int)STRIP_BAND_TILES - (int)stamp->h_tiles - first_y) / period + 1;
        int x_slots = (int)STRIP_W_TILES - (int)stamp->w_tiles - 2;
        if (y_slots <= 0 || x_slots <= 0) continue;

        for (int attempt = 0; attempt < 16; attempt++) {
            uint32_t probe = hash32(random + (uint32_t)attempt * 0x85ebca6bu);
            int x_tile = 1 + (int)(probe % (unsigned)x_slots);
            int y_tile = first_y + (int)((probe >> 16) % (unsigned)y_slots) * period;
            if (!stamp_can_be_placed(stamp, x_tile, y_tile, lane_x,
                                     placed_x, placed_y, placed, placed_count)) continue;

            for (unsigned sy = 0; sy < stamp->h_tiles; sy++) {
                unsigned dst = (unsigned)(map_row + y_tile + (int)sy) * STRIP_W_TILES + (unsigned)x_tile;
                unsigned src = sy * stamp->w_tiles;
                for (unsigned sx = 0; sx < stamp->w_tiles; sx++) {
                    uint16_t tile = stamp->tiles[src + sx];
                    if (tile != 0) s_map[dst + sx] = tile;
                }
            }
            for (unsigned cy = 0; cy < stamp->foot_h; cy++) {
                for (unsigned cx = 0; cx < stamp->foot_w; cx++) {
                    unsigned cell_x = (unsigned)x_tile * 2u + stamp->foot_x + cx;
                    unsigned cell_y = (unsigned)collision_row + (unsigned)y_tile * 2u + stamp->foot_y + cy;
                    if (cell_x > 0 && cell_x < STRIP_COLLISION_W - 1u &&
                        cell_y < STRIP_COLLISION_H - 1u) {
                        packed_collision_set(s_collision, cell_y * STRIP_COLLISION_W + cell_x,
                                             stamp->foot_value);
                    }
                }
            }
            placed_x[placed_count] = x_tile;
            placed_y[placed_count] = y_tile;
            placed[placed_count] = stamp;
            placed_count++;
            break;
        }
    }
}

static void generate_band(int32_t band, int map_row, int collision_row) {
    const unsigned floor_period = g_strip_kit.floor_h_tiles;
    const unsigned collision_period = floor_period * 2u;
    // Window and band origins are period aligned (floor_h_tiles divides 16).
    unsigned map_phase = 0;
    unsigned collision_phase = 0;

    for (unsigned row = 0; row < STRIP_BAND_TILES; row++) {
        const uint16_t *src = g_strip_kit.floor_map + map_phase * STRIP_W_TILES;
        uint16_t *dst = s_map + (unsigned)(map_row + (int)row) * STRIP_W_TILES;
        memcpy(dst, src, STRIP_MAP_ROW_BYTES);
        map_phase++;
        if (map_phase == floor_period) map_phase = 0;
    }
    for (unsigned row = 0; row < STRIP_BAND_CELLS; row++) {
        const uint8_t *src = g_strip_kit.floor_collision + collision_phase * STRIP_COLLISION_ROW_BYTES;
        uint8_t *dst = s_collision + (unsigned)(collision_row + (int)row) * STRIP_COLLISION_ROW_BYTES;
        memcpy(dst, src, STRIP_COLLISION_ROW_BYTES);
        collision_phase++;
        if (collision_phase == collision_period) collision_phase = 0;
    }

    stamp_band(band, map_row, collision_row);
}

static void enforce_hard_edges(void) {
    for (unsigned row = 0; row < STRIP_COLLISION_H; row++) {
        unsigned base = row * STRIP_COLLISION_W;
        packed_collision_set(s_collision, base, 3);
        packed_collision_set(s_collision, base + STRIP_COLLISION_W - 1u, 3);
    }
    unsigned bottom = (STRIP_COLLISION_H - 1u) * STRIP_COLLISION_W;
    for (unsigned x = 0; x < STRIP_COLLISION_W; x++)
        packed_collision_set(s_collision, bottom + x, 3);
}

void strip_start(uint32_t seed) {
    s_seed = seed;
    s_next_band = 0;
    s_shift_total_px = 0;
    g_arena = &s_arena;
    s_kit_valid = 0;
    if (g_strip_kit.floor_h_tiles == 0 || g_strip_kit.floor_h_tiles > STRIP_BAND_TILES ||
        !g_strip_kit.floor_map || !g_strip_kit.floor_collision || !g_strip_kit.palette ||
        !g_strip_kit.tiles) {
        memset(s_map, 0, sizeof(s_map));
        memset(s_collision, 0, sizeof(s_collision));
        memset(s_occlusion_row_start, 0, sizeof(s_occlusion_row_start));
        s_arena.num_tiles = 1;
        s_arena.palette = s_fallback_palette;
        s_arena.tiles = s_fallback_tile;
        enforce_hard_edges();
        return;
    }
    s_kit_valid = 1;

    for (int band = 0; band < STRIP_MAP_H_TILES / STRIP_BAND_TILES; band++) {
        generate_band(band, band * STRIP_BAND_TILES, band * STRIP_BAND_CELLS);
        s_next_band = band + 1;
    }
    enforce_hard_edges();
    s_arena.num_tiles = g_strip_kit.num_tiles;
    s_arena.palette = g_strip_kit.palette;
    s_arena.tiles = g_strip_kit.tiles;
}

int strip_rebase_if_needed(int player_y_px) {
    if (g_arena != &s_arena || !s_kit_valid || player_y_px >= STRIP_REBASE_TOP_PX) return 0;

    memmove(s_map + STRIP_MAP_SHIFT_ROWS * STRIP_W_TILES,
            s_map,
            (STRIP_MAP_H_TILES - STRIP_MAP_SHIFT_ROWS) * STRIP_MAP_ROW_BYTES);
    memmove(s_collision + STRIP_COLLISION_SHIFT_ROWS * STRIP_COLLISION_ROW_BYTES,
            s_collision,
            (STRIP_COLLISION_H - STRIP_COLLISION_SHIFT_ROWS) * STRIP_COLLISION_ROW_BYTES);
    for (int band = 0; band < STRIP_SHIFT_PX / STRIP_BAND_PX; band++) {
        generate_band(s_next_band, band * STRIP_BAND_TILES, band * STRIP_BAND_CELLS);
        s_next_band++;
    }
    enforce_hard_edges();
    s_shift_total_px += STRIP_SHIFT_PX;
    return STRIP_SHIFT_PX;
}

int32_t strip_shift_total_px(void) { return s_shift_total_px; }
int strip_start_x(void) { return STRIP_W_PX / 2; }
int strip_start_y(void) { return STRIP_WIN_H_PX - 256; }
int strip_height_m(int player_y_px) {
    int32_t height_px = strip_start_y() + strip_shift_total_px() - player_y_px;
    if (height_px <= 0) return 0;
    return (int)(((height_px / STRIP_PIXELS_PER_METER_100X) * 100) +
                 ((height_px % STRIP_PIXELS_PER_METER_100X) * 100) / STRIP_PIXELS_PER_METER_100X);
}
const Arena *strip_arena(void) { return &s_arena; }
