#include "strip.h"
#include "strip_kit.h"

#include <string.h>
#include <stdlib.h>

#define STRIP_MAP_H_TILES (STRIP_WIN_H_PX / 8)
#define STRIP_COLLISION_W (STRIP_W_CELLS)
#define STRIP_COLLISION_H (STRIP_WIN_H_PX / COLLISION_SCALE)
#define STRIP_BAND_TILES (STRIP_BAND_PX / 8)
#define STRIP_BAND_CELLS (STRIP_BAND_PX / COLLISION_SCALE)
#define STRIP_MAP_SHIFT_ROWS (STRIP_SHIFT_PX / 8)
#define STRIP_COLLISION_SHIFT_ROWS (STRIP_SHIFT_PX / COLLISION_SCALE)
#define STRIP_MAP_ROW_BYTES (STRIP_W_TILES * sizeof(uint16_t))
#define STRIP_COLLISION_ROW_BYTES (STRIP_COLLISION_W / 4)
#define STRIP_COMPOSE_MAX_STAMPS 12
#define STRIP_WALL_TILES 6
#define STRIP_WALL_CELLS (STRIP_WALL_TILES * 2)
#define STRIP_OCCLUSION_CAPACITY 32768
#define STRIP_START_CLEAR_BANDS 3
// Deterministic cathedral composer salts (keep in sync with tools/bake_cathedral_kit.py).
#define S_COL_L 0x1a2b3c4du
#define S_COL_R 0x5e6f7a8bu
#define S_BANK_TYPE 0x2f9e1b77u
#define S_BANK_LEN 0x9be2f431u
#define S_BANK_START 0x5bd1e995u
#define S_BARRICADE 0x73c1d0a5u
#define S_DECOR 0x41c64e6du
#define COL_ENTERA 0
#define COL_ROTA 1
#define COL_CAIDA 2

static uint16_t s_map[STRIP_W_TILES * STRIP_MAP_H_TILES];
static uint8_t s_collision[(STRIP_COLLISION_W * STRIP_COLLISION_H) / 4];
static uint32_t s_occlusion_row_start[STRIP_WIN_H_PX + 1];
static DungeonOcclusionRun s_occlusion_runs[STRIP_OCCLUSION_CAPACITY];
static uint32_t s_occlusion_count;
static const uint16_t s_fallback_palette[256];
static const uint8_t s_fallback_tile[1][64];
static int32_t s_next_band;
static int32_t s_shift_total_px;
static uint32_t s_seed;
static int s_kit_valid;
#define STRIP_INITIAL_BANDS (STRIP_MAP_H_TILES / STRIP_BAND_TILES)

#if LAPIDA_DEBUG
int32_t g_strip_debug_pos[2] = { -1, -1 };
#endif

#if STRIP_LAYOUT_DUMP
// Host-only parity hook (tests/test_strip_layout_parity.py): called for every placement.
void (*g_strip_layout_dump)(int32_t band, int piece_id, int phase_col, int phase_row,
                            int x_tile, int y_tile);
#endif

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
    .occlusion_runs = s_occlusion_runs,
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

// Copy the stamp's non-empty tiles, write its footprint into the collision map and append its
// occlusion runs. Returns nothing: the caller decides whether it fits (see compose_place).
static void stamp_place(const StripStamp *stamp, int x_tile, int y_tile,
                        int map_row, int collision_row) {
    for (unsigned sy = 0; sy < stamp->h_tiles; sy++) {
        unsigned dst = (unsigned)(map_row + y_tile + (int)sy) * STRIP_W_TILES + (unsigned)x_tile;
        unsigned src = sy * stamp->w_tiles;
        for (unsigned sx = 0; sx < stamp->w_tiles; sx++) {
            uint16_t tile = stamp->tiles[src + sx];
            if (tile != 0) s_map[dst + sx] = tile;
        }
    }
    for (unsigned ri = 0; ri < stamp->num_foot_runs; ri++) {
        const StripFootprintRun *run = &stamp->foot_runs[ri];
        unsigned cell_y = (unsigned)collision_row + (unsigned)y_tile * 2u + run->y_cell;
        if (cell_y >= STRIP_COLLISION_H - 1u) continue;
        unsigned first_cell = (unsigned)x_tile * 2u + run->x_cell;
        for (unsigned cx = 0; cx < run->length_cells; cx++) {
            unsigned cell_x = first_cell + cx;
            if (cell_x > 0 && cell_x < STRIP_COLLISION_W - 1u) {
                packed_collision_set(s_collision, cell_y * STRIP_COLLISION_W + cell_x,
                                     stamp->foot_value);
            }
        }
    }
    for (unsigned ri = 0; ri < stamp->num_depth_runs; ri++) {
        const StripDepthRun *run = &stamp->depth_runs[ri];
        unsigned ry = (unsigned)(map_row * 8 + y_tile * 8 + run->y_px);
        unsigned rx = (unsigned)(x_tile * 8 + run->x_px);
        if (ry >= STRIP_WIN_H_PX || rx >= STRIP_W_PX || !run->length) continue;
        DungeonOcclusionRun *dst = &s_occlusion_runs[s_occlusion_count++];
        dst->x = (uint16_t)rx;
        dst->y = (uint16_t)ry;
        dst->length = (uint16_t)((rx + run->length > STRIP_W_PX) ? STRIP_W_PX - rx : run->length);
        dst->depth = (int16_t)(map_row * 8 + y_tile * 8 + stamp->foot_anchor_y_px + run->depth_delta);
    }
}

// Overlap test on the tiles a stamp actually writes (tile != 0), exactly like the Python plan:
// empty shadow-canvas margins stay free and may overlap a neighbour.
static int stamp_tiles_overlap(const StripStamp *a, int ax, int ay,
                               const StripStamp *b, int bx, int by) {
    int x0 = ax > bx ? ax : bx;
    int y0 = ay > by ? ay : by;
    int ax1 = ax + (int)a->w_tiles, bx1 = bx + (int)b->w_tiles;
    int ay1 = ay + (int)a->h_tiles, by1 = by + (int)b->h_tiles;
    int x1 = ax1 < bx1 ? ax1 : bx1;
    int y1 = ay1 < by1 ? ay1 : by1;
    for (int y = y0; y < y1; y++) {
        for (int x = x0; x < x1; x++) {
            uint16_t ta = a->tiles[(y - ay) * (int)a->w_tiles + (x - ax)];
            uint16_t tb = b->tiles[(y - by) * (int)b->w_tiles + (x - bx)];
            if ((ta & 0x3ffu) != 0u && (tb & 0x3ffu) != 0u) return 1;
        }
    }
    return 0;
}

// The composer asks for a (piece, phase_col, phase_row) triple derived from its tile position,
// never for a raw index, so the kit can be rebaked without renumbering anything here.
static const StripStamp *find_stamp(uint8_t piece_id, int x_tile, int y_tile) {
    uint8_t pc = (uint8_t)(x_tile & 15);
    uint8_t pr = (uint8_t)(y_tile & 15);
    for (int i = 0; i < (int)g_strip_kit.num_stamps; i++) {
        const StripStamp *stamp = &g_strip_kit.stamps[i];
        if (stamp->piece_id == piece_id && stamp->phase_col == pc && stamp->phase_row == pr)
            return stamp;
    }
    return 0;
}

static int column_state(int32_t band, uint32_t salt) {
    uint32_t r = band_hash(band, salt) % 100u;
    if (r < 55u) return COL_ENTERA;
    if (r < 85u) return COL_ROTA;
    return COL_CAIDA;
}

// A raw hole right after another raw hole becomes a broken stump: two holes never sit back to
// back on the same row (same rule as _effective_column_state in the Python spec).
static int effective_column_state(int32_t band, uint32_t salt) {
    int state = column_state(band, salt);
    if (state == COL_CAIDA && column_state(band - 1, salt) == COL_CAIDA) return COL_ROTA;
    return state;
}

static int compose_place(int32_t band, int map_row, int collision_row,
                         uint8_t piece_id, int x_tile, int y_local,
                         int placed_x[], int placed_y[], const StripStamp *placed[],
                         int *placed_count) {
    int y_tile = (int32_t)band * STRIP_BAND_TILES + y_local;
    const StripStamp *stamp = find_stamp(piece_id, x_tile, y_tile);
    if (!stamp) return 0;
    if (x_tile < STRIP_WALL_TILES ||
        x_tile + (int)stamp->w_tiles > STRIP_W_TILES - STRIP_WALL_TILES) return 0;
    if (y_local < 0 || y_local + (int)stamp->h_tiles > STRIP_BAND_TILES) return 0;
    for (int i = 0; i < *placed_count; i++) {
        if (stamp_tiles_overlap(stamp, x_tile, y_local,
                                placed[i], placed_x[i], placed_y[i])) return 0;
    }
    if (s_occlusion_count + stamp->num_depth_runs > STRIP_OCCLUSION_CAPACITY) return 0;
    stamp_place(stamp, x_tile, y_local, map_row, collision_row);
    placed_x[*placed_count] = x_tile;
    placed_y[*placed_count] = y_local;
    placed[*placed_count] = stamp;
    (*placed_count)++;
#if STRIP_LAYOUT_DUMP
    if (g_strip_layout_dump)
        g_strip_layout_dump(band, piece_id, stamp->phase_col, stamp->phase_row, x_tile, y_tile);
#endif
    return 1;
}

// Deterministic cathedral floor plan (DESIGN.md, "Compositor de la catedral"). The band number
// decides what goes where; hashes only pick variants. No state between bands: identical to
// catedral_plan() in tools/bake_cathedral_kit.py, including placement order.
static void catedral_band(int32_t band, int map_row, int collision_row) {
    int placed_x[STRIP_COMPOSE_MAX_STAMPS];
    int placed_y[STRIP_COMPOSE_MAX_STAMPS];
    const StripStamp *placed[STRIP_COMPOSE_MAX_STAMPS];
    int placed_count = 0;
    int tramo = band >> 1;
    int pos = tramo & 3;
    int ciclo = tramo >> 2;
    int left_state = effective_column_state(band, S_COL_L);
    int right_state = effective_column_state(band, S_COL_R);

    if (pos != 3) {
        const int xs[2] = { 8, 48 };   // inner faces of the two columna_entera rows
        const int states[2] = { left_state, right_state };
        for (int side = 0; side < 2; side++) {
            if (states[side] == COL_ENTERA)
                compose_place(band, map_row, collision_row, STRIP_PIECE_COLUMNA_ENTERA,
                              xs[side], 0, placed_x, placed_y, placed, &placed_count);
            else if (states[side] == COL_ROTA)
                compose_place(band, map_row, collision_row, STRIP_PIECE_COLUMNA,
                              xs[side], 8, placed_x, placed_y, placed, &placed_count);
        }
    }

    if (pos == 0 || pos == 1) {
        // One glued group of 4-6 benches per row and tramo (8 slots of 32 px = 2 bands x 4).
        // Length is hashed per (tramo, row) 25/50/25 for 4/5/6 and the start inside
        // [0, 8 - length]; when both rows land on exactly the same slots the right row moves one
        // valid start so the rows stagger. Same rule as bench_groups() in the baker.
        static const int bench_x[2] = { 19, 35 };
        int len[2], start[2];
        for (int row_i = 0; row_i < 2; row_i++) {
            int row_key = (tramo << 1) + row_i;
            uint32_t r = band_hash(row_key, S_BANK_LEN) % 100u;
            len[row_i] = r < 25u ? 4 : (r >= 75u ? 6 : 5);
            start[row_i] = (int)(band_hash(row_key, S_BANK_START)
                                 % (uint32_t)(8 - len[row_i] + 1));
        }
        if (len[0] == len[1] && start[0] == start[1])
            start[1] = (start[1] + 1) % (8 - len[1] + 1);
        int sub = band & 1;
        for (int row_i = 0; row_i < 2; row_i++) {
            for (int slot = start[row_i]; slot < start[row_i] + len[row_i]; slot++) {
                if ((slot >> 2) != sub) continue;
                uint32_t salt = S_BANK_TYPE ^ (((uint32_t)row_i * 0x9e3779b9u)
                                               ^ ((uint32_t)slot * 0x85ebca6bu));
                uint8_t pid = (band_hash(band, salt) % 100u < 25u)
                                  ? STRIP_PIECE_BANCO_ROTO : STRIP_PIECE_BANCO_ENTERO;
                compose_place(band, map_row, collision_row, pid, bench_x[row_i],
                              (slot & 3) * 4, placed_x, placed_y, placed, &placed_count);
            }
        }
    } else if (pos == 2) {
        if (band_hash(ciclo, S_BARRICADE) % 3u == 0u) {
            // Cleared tramo: 0-2 candles / a flat tomb (no collision) in the open nave.
            uint32_t h = band_hash(band, S_DECOR);
            uint32_t count = h % 3u;
            if (count >= 1u) {
                if ((h >> 4) & 1u)
                    compose_place(band, map_row, collision_row, STRIP_PIECE_LAPIDA_CRUZ_H,
                                  16, 0, placed_x, placed_y, placed, &placed_count);
                else
                    compose_place(band, map_row, collision_row, STRIP_PIECE_VELA,
                                  40, 0, placed_x, placed_y, placed, &placed_count);
            }
            if (count >= 2u)
                compose_place(band, map_row, collision_row, STRIP_PIECE_VELA,
                              40, 8, placed_x, placed_y, placed, &placed_count);
        } else {
            // Barricade: sacks staggered in y; on odd cycles the line leans right when the right
            // column is down, which alternates the open side.
            int shift = ((ciclo & 1) && right_state == COL_CAIDA) ? 8 : 0;
            const int xs[3] = { 16 + shift, 24 + shift, 32 + shift };
            if (band & 1) {
                compose_place(band, map_row, collision_row, STRIP_PIECE_SACOS,
                              xs[1], 0, placed_x, placed_y, placed, &placed_count);
                compose_place(band, map_row, collision_row, STRIP_PIECE_SACOS,
                              xs[2], 8, placed_x, placed_y, placed, &placed_count);
                compose_place(band, map_row, collision_row, STRIP_PIECE_BANCO_VOLCADO,
                              16, 8, placed_x, placed_y, placed, &placed_count);
            } else {
                compose_place(band, map_row, collision_row, STRIP_PIECE_SACOS,
                              xs[0], 0, placed_x, placed_y, placed, &placed_count);
                compose_place(band, map_row, collision_row, STRIP_PIECE_SACOS,
                              xs[1], 8, placed_x, placed_y, placed, &placed_count);
                compose_place(band, map_row, collision_row, STRIP_PIECE_SACOS,
                              xs[2], 0, placed_x, placed_y, placed, &placed_count);
            }
        }
    } else {
        // Crucero: open arena. Symmetric saints, candles and one lateral reliquary.
        compose_place(band, map_row, collision_row, STRIP_PIECE_SANTO, 16, 0,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_SANTO, 40, 0,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_VELA, 8, 0,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_VELA, 24, 0,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_VELA, 32, 8,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_VELA, 48, 0,
                      placed_x, placed_y, placed, &placed_count);
        compose_place(band, map_row, collision_row, STRIP_PIECE_RELICARIO,
                      (ciclo & 1) ? 48 : 8, 8, placed_x, placed_y, placed, &placed_count);
    }
}

static void stamp_band(int32_t band, int map_row, int collision_row) {
#if LAPIDA_DEBUG
    // "lapidas" variant: bands 11..15 host the forced showcase lapidas (see strip_debug_lapidas).
    if (band >= 11 && band <= 15) return;
#endif
#if defined(PROPS_SHOWCASE) && PROPS_SHOWCASE
    // Showcase build: strip_start() places one fixed exemplar of each physical prop instead.
    return;
#endif
    if ((band >= STRIP_INITIAL_BANDS - STRIP_START_CLEAR_BANDS && band < STRIP_INITIAL_BANDS) ||
        g_strip_kit.num_stamps == 0 ||
        g_strip_kit.stamps == 0 || g_strip_kit.floor_h_tiles == 0) return;
    catedral_band(band, map_row, collision_row);
}

#if STRIP_LAYOUT_DUMP
// Host-only parity harness hook: walk `num_bands` bands like strip_start() would, dumping every
// successful placement. s_occlusion_count resets per band because the plan has no cross-band state.
void strip_layout_dump_bands(uint32_t seed, int num_bands) {
    s_seed = seed;
    for (int band = 0; band < num_bands; band++) {
        s_occlusion_count = 0;
        stamp_band(band, 0, 0);
    }
}
#endif

static void generate_band(int32_t band, int map_row, int collision_row) {
    const unsigned map_period = g_strip_kit.map_h_tiles;
    const unsigned collision_period = (unsigned)g_strip_kit.floor_h_tiles * 2u;
    unsigned map_phase = (unsigned)((uint32_t)band * STRIP_BAND_TILES) % map_period;
    unsigned collision_phase = (unsigned)((uint32_t)band * STRIP_BAND_CELLS) % collision_period;

    for (unsigned row = 0; row < STRIP_BAND_TILES; row++) {
        const uint16_t *src = g_strip_kit.floor_map + map_phase * STRIP_W_TILES;
        uint16_t *dst = s_map + (unsigned)(map_row + (int)row) * STRIP_W_TILES;
        memcpy(dst, src, STRIP_MAP_ROW_BYTES);
        map_phase++;
        if (map_phase == map_period) map_phase = 0;
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
        for (unsigned x = 0; x < STRIP_WALL_CELLS; x++) {
            packed_collision_set(s_collision, base + x, 3);
            packed_collision_set(s_collision, base + STRIP_COLLISION_W - STRIP_WALL_CELLS + x, 3);
        }
    }
    unsigned bottom = (STRIP_COLLISION_H - 1u) * STRIP_COLLISION_W;
    for (unsigned x = 0; x < STRIP_COLLISION_W; x++)
        packed_collision_set(s_collision, bottom + x, 3);
}

static int occlusion_compare(const void *a, const void *b) {
    const DungeonOcclusionRun *ra = (const DungeonOcclusionRun *)a;
    const DungeonOcclusionRun *rb = (const DungeonOcclusionRun *)b;
    if (ra->y != rb->y) return (int)ra->y - (int)rb->y;
    return (int)ra->x - (int)rb->x;
}

static void rebuild_occlusion_index(void) {
    qsort(s_occlusion_runs, s_occlusion_count, sizeof(s_occlusion_runs[0]), occlusion_compare);
    uint32_t i = 0;
    for (unsigned y = 0; y <= STRIP_WIN_H_PX; y++) {
        while (i < s_occlusion_count && s_occlusion_runs[i].y < y) i++;
        s_occlusion_row_start[y] = i;
    }
}

#if LAPIDA_DEBUG
// Debug-only showcase ("lapidas" build variant): every lapida stamp in the kit is painted at a
// fixed band so it is on screen deterministically. The catedral kit bakes only one gravestone
// variant (lapida_cruz_h), so this variant shows that single piece; the other lapida stamps only
// exist in the old `--mode actual` kit.
static void strip_debug_blit_lapida(int band, int stamp_index) {
    const StripStamp *stamp = &g_strip_kit.stamps[stamp_index];
    int x_tile = 16;                          // floor phase 0 in x
    int y_tile = band * STRIP_BAND_TILES;     // floor phase 0 in y
    int w = (int)stamp->w_tiles;
    int h = (int)stamp->h_tiles;
    for (int sy = 0; sy < h; sy++) {
        for (int sx = 0; sx < w; sx++) {
            uint16_t tile = stamp->tiles[sy * w + sx];
            if (tile) s_map[(unsigned)(y_tile + sy) * STRIP_W_TILES + x_tile + sx] = tile;
        }
    }
}
static void strip_debug_lapidas(void) {
    int band = 11;
    for (int i = 0; i < (int)g_strip_kit.num_stamps && band <= 15; i++) {
        uint8_t id = g_strip_kit.stamps[i].piece_id;
        if (id < STRIP_PIECE_LAPIDA_CRUZ_H || id >= STRIP_PIECE_COUNT) continue;
        strip_debug_blit_lapida(band, i);
        band++;
    }
}
#endif

void strip_start(uint32_t seed) {
    s_seed = seed;
    s_next_band = 0;
    s_shift_total_px = 0;
    s_occlusion_count = 0;
    g_arena = &s_arena;
    s_kit_valid = 0;
    if (g_strip_kit.map_h_tiles == 0 || g_strip_kit.map_h_tiles > STRIP_MAP_H_TILES ||
        ((STRIP_BAND_TILES % g_strip_kit.map_h_tiles) != 0 &&
         (g_strip_kit.map_h_tiles % STRIP_BAND_TILES) != 0) ||
        g_strip_kit.floor_h_tiles == 0 || g_strip_kit.floor_h_tiles > STRIP_BAND_TILES ||
        !g_strip_kit.floor_map || !g_strip_kit.floor_collision || !g_strip_kit.palette ||
        !g_strip_kit.tiles) {
        memset(s_map, 0, sizeof(s_map));
        memset(s_collision, 0, sizeof(s_collision));
        memset(s_occlusion_row_start, 0, sizeof(s_occlusion_row_start));
        s_arena.occlusion_runs = 0;
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
#if LAPIDA_DEBUG
    strip_debug_lapidas();
#endif
    rebuild_occlusion_index();
    s_arena.occlusion_runs = s_occlusion_runs;
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
    uint32_t kept_runs = 0;
    for (uint32_t i = 0; i < s_occlusion_count; i++) {
        unsigned shifted_y = (unsigned)s_occlusion_runs[i].y + STRIP_SHIFT_PX;
        if (shifted_y >= STRIP_WIN_H_PX) continue;
        s_occlusion_runs[i].y = (uint16_t)shifted_y;
        s_occlusion_runs[i].depth += STRIP_SHIFT_PX;
        s_occlusion_runs[kept_runs++] = s_occlusion_runs[i];
    }
    s_occlusion_count = kept_runs;
    for (int band = 0; band < STRIP_SHIFT_PX / STRIP_BAND_PX; band++) {
        generate_band(s_next_band, band * STRIP_BAND_TILES, band * STRIP_BAND_CELLS);
        s_next_band++;
    }
    rebuild_occlusion_index();
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
