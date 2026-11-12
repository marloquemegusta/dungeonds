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
#define STRIP_WALL_TILES 6
#define STRIP_WALL_CELLS (STRIP_WALL_TILES * 2)
#define STRIP_OCCLUSION_CAPACITY 32768
#define STRIP_START_CLEAR_BANDS 4
// Compositor v2 (DESIGN.md 6.9.1b): block = 2 screens of 24 tile rows = 3 bands of 16 rows.
#define STRIP_BLOCK_TILES 48
#define STRIP_SCREEN_TILES 24
#define STRIP_BLOCK_MAX_PIECES 48
#define STRIP_PLAN_NONE 0x7fffffff
// Piece categories, in emission order (keep in sync with _emit_order() in tools/bake_cathedral_kit.py).
#define PLAN_CAT_LAP 0
#define PLAN_CAT_STRUCT 1
#define PLAN_CAT_VEL 2
// Deterministic cathedral composer salts (keep in sync with tools/bake_cathedral_kit.py).
#define S_SCREEN_TYPE 0x243F6A88u
#define S_BENCH_LX 0x85A308D3u
#define S_BENCH_LY 0x13198A2Eu
#define S_BENCH_RY 0x03707344u
#define S_VELA_N 0xA4093822u
#define S_VELA_PICK 0x299F31D0u
#define S_REL_VN 0x082EFA98u
#define S_REL_PICK 0xEC4E6C89u
#define S_LAP_N 0x452821E6u
#define S_LAP_POS 0x38D01377u
#define S_LAP_VAR 0xBE5466CFu
#define S_LAP_GRP 0x34E90C6Cu
#define S_LAP_GLEN 0xC0AC29B7u
#define S_LAP_GPOS 0xC97C50DDu
#define S_LAP_GVAR 0x3F84D5B5u
// Incremental rebase (strip_prepare_step). A rebase shifts STRIP_SHIFT_PX and builds 6 bands;
// runs of the active window with y below STRIP_KEEP_MAX_Y survive the shift.
#define STRIP_PREP_STAGE_BANDS (STRIP_SHIFT_PX / STRIP_BAND_PX)
#define STRIP_KEEP_MAX_Y (STRIP_WIN_H_PX - STRIP_SHIFT_PX)
#define STRIP_STAGE_RUNS_MAX 8192      // new runs of one rebase (about 5500 measured): 64 KB
#define STRIP_PREP_CHUNK_RUNS 512      // runs per count / scatter / insertion call
#define STRIP_PREP_COPY_RUNS 2048      // surviving runs copied per call

typedef struct {
    const StripStamp *stamp;
    int x, y;          // block tiles (y is the block row, 0..47)
    uint8_t piece_id;
    uint8_t cat;       // PLAN_CAT_*
} PlanItem;

// Where a band is written: the live window, or the preparation stage. Both use the window's row
// numbering, so a stage is the top rows of the window (map rows 0..95, collision rows 0..191).
typedef struct {
    uint16_t *map;                 // row 0 of the destination tilemap
    uint8_t *collision;            // row 0 of the destination collision (packed, 4 cells per byte)
    DungeonOcclusionRun *runs;     // destination occlusion runs
    uint32_t *run_count;
    uint32_t run_limit;            // runs beyond this are dropped (the STRIP_OCCLUSION_CAPACITY rule)
    uint32_t *run_dropped;         // drops are counted here; NULL for the live window
} BandSink;

// Active window (what the Arena exposes) and its reserve. strip_prepare_step() fills the reserve;
// the commit swaps the pointers, so a reader never sees a half-built index.
static uint16_t s_map[STRIP_W_TILES * STRIP_MAP_H_TILES];
static uint8_t s_collision[(STRIP_COLLISION_W * STRIP_COLLISION_H) / 4];
static uint32_t s_occlusion_row_start[STRIP_WIN_H_PX + 1];
static DungeonOcclusionRun s_occlusion_runs[STRIP_OCCLUSION_CAPACITY];
static uint32_t s_occlusion_count;
// Scratch of the row bucket sort, and the reserve run array of the next window: 32768 * 8 B = 256 KB.
static DungeonOcclusionRun s_occlusion_scratch[STRIP_OCCLUSION_CAPACITY];
static DungeonOcclusionRun *s_runs_active = s_occlusion_runs;
static DungeonOcclusionRun *s_runs_reserve = s_occlusion_scratch;
static uint32_t *s_row_active = s_occlusion_row_start;
static uint32_t s_stage_row_start[STRIP_WIN_H_PX + 1];                    // reserve row index
static uint32_t *s_row_reserve = s_stage_row_start;
static uint16_t s_stage_map[STRIP_MAP_SHIFT_ROWS * STRIP_W_TILES];        // 6 bands x 16 rows
static uint8_t s_stage_collision[STRIP_COLLISION_SHIFT_ROWS * STRIP_COLLISION_ROW_BYTES]; // 6 x 32 rows
static DungeonOcclusionRun s_stage_new_runs[STRIP_STAGE_RUNS_MAX];        // new runs, emission order
static uint32_t s_stage_new_count;
static uint32_t s_stage_dropped;                                          // must stay 0 (host checks it)
static uint32_t s_stage_peak;                                             // largest new-run count seen
static BandSink s_stage_sink;
static const uint16_t s_fallback_palette[256];
static const uint8_t s_fallback_tile[1][64];
static int32_t s_next_band;
static int32_t s_shift_total_px;
static uint32_t s_seed;
static int s_kit_valid;
static int32_t s_plan_block = STRIP_PLAN_NONE;   // block whose plan sits in s_plan
static PlanItem s_plan[STRIP_BLOCK_MAX_PIECES];
static int s_plan_n;
#define STRIP_INITIAL_BANDS (STRIP_MAP_H_TILES / STRIP_BAND_TILES)
enum {
    PREP_IDLE, PREP_BANDS, PREP_PLAN, PREP_COUNT, PREP_PREFIX, PREP_PLACE, PREP_INSERT,
    PREP_COPY, PREP_INDEX, PREP_READY
};
static int s_prep_phase = PREP_IDLE;
static uint32_t s_prep_cursor;         // next band / run / kept run of the current phase
static uint32_t s_prep_kept;           // surviving runs of the active window
static uint32_t s_prep_new;            // new runs (placed first in the reserve)
static uint32_t s_prep_steps;          // units run by the current preparation
static uint32_t s_prep_steps_last;     // units of the last commit (host measurement)
static int32_t s_prep_plan_block;      // block whose plan is being built (PREP_PLAN)
static uint32_t s_prep_plan_unit;      // next plan_unit() part of that block
static int s_prep_plan_n;              // pieces accepted so far for that block

#if STRIP_LAYOUT_DUMP
// Host-only parity hook (tests/test_strip_layout_parity.py): called for every planned piece, in
// emission order. strip_layout_dump_blocks() walks blocks without touching the arena.
void (*g_strip_layout_dump)(int32_t block, int piece_id, int phase_col, int phase_row,
                            int x_tile, int y_block);
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

// Hash of (screen index, salt, sub): the same bits as _pick() in tools/bake_cathedral_kit.py.
static uint32_t plan_pick(int32_t sidx, uint32_t salt, uint32_t sub) {
    return band_hash(sidx, salt ^ (sub * 0x85ebca6bu));
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

// Overlap test on the tiles a stamp actually writes (tile != 0), exactly like the Python plan:
// empty shadow-canvas margins stay free and may overlap a neighbour. Rows below the block are
// dropped on both sides (a columna's last shadow row belongs to the next block and is clipped).
static int stamp_tiles_overlap(const StripStamp *a, int ax, int ay,
                               const StripStamp *b, int bx, int by) {
    int x0 = ax > bx ? ax : bx;
    int y0 = ay > by ? ay : by;
    int ax1 = ax + (int)a->w_tiles, bx1 = bx + (int)b->w_tiles;
    int ay1 = ay + (int)a->h_tiles, by1 = by + (int)b->h_tiles;
    int x1 = ax1 < bx1 ? ax1 : bx1;
    int y1 = ay1 < by1 ? ay1 : by1;
    if (y1 > STRIP_BLOCK_TILES) y1 = STRIP_BLOCK_TILES;
    for (int y = y0; y < y1; y++) {
        for (int x = x0; x < x1; x++) {
            uint16_t ta = a->tiles[(y - ay) * (int)a->w_tiles + (x - ax)];
            uint16_t tb = b->tiles[(y - by) * (int)b->w_tiles + (x - bx)];
            if ((ta & 0x3ffu) != 0u && (tb & 0x3ffu) != 0u) return 1;
        }
    }
    return 0;
}

static int piece_is_lapida(uint8_t piece_id) {
    return piece_id >= STRIP_PIECE_LAPIDA_3X2_CRUZ && piece_id <= STRIP_PIECE_LAPIDA_2X1_CAB;
}

// The composer asks for a (piece, phase_col, phase_row) triple derived from its tile position,
// never for a raw index, so the kit can be rebaked without renumbering anything here.
// A lapida is baked at two phases, (0, 2) and (2, 3) (the damero inverted). Its stamp at (pc, pr)
// fits tile (x, y) when (x - pc) is a multiple of 4 and (y - pr) of 2: the joints of the floor
// then follow the damero rule (DESIGN.md 6.9.1b). A position no phase fits gets no stamp.
// `& 3` and `& 1` give the positive residue for negative differences too (two's complement).
static const StripStamp *stamp_for_lapida(uint8_t piece_id, int x_tile, int y_tile) {
    for (int i = 0; i < (int)g_strip_kit.num_stamps; i++) {
        const StripStamp *stamp = &g_strip_kit.stamps[i];
        if (stamp->piece_id != piece_id) continue;
        if (((x_tile - (int)stamp->phase_col) & 3) == 0 && ((y_tile - (int)stamp->phase_row) & 1) == 0)
            return stamp;
    }
    return 0;
}

static const StripStamp *find_stamp(uint8_t piece_id, int x_tile, int y_tile) {
    if (piece_is_lapida(piece_id)) return stamp_for_lapida(piece_id, x_tile, y_tile);
    uint8_t pc = (uint8_t)(x_tile & 15);
    uint8_t pr = (uint8_t)(y_tile & 15);
    for (int i = 0; i < (int)g_strip_kit.num_stamps; i++) {
        const StripStamp *stamp = &g_strip_kit.stamps[i];
        if (stamp->piece_id != piece_id) continue;
        if (stamp->phase_col == pc && stamp->phase_row == pr) return stamp;
    }
    return 0;
}

// Accept a piece on the block when it fits the walls, the rows and the tiles of what is already
// accepted (same rule as _try_place() in the baker). `clip`: rows below the block may be dropped.
static int plan_try(PlanItem *acc, int *n, uint8_t cat, uint8_t piece_id,
                    int x_tile, int y_tile, int row_lo, int row_hi, int clip) {
    const StripStamp *stamp = find_stamp(piece_id, x_tile, y_tile);
    if (!stamp) return 0;
    if (x_tile < STRIP_WALL_TILES ||
        x_tile + (int)stamp->w_tiles > STRIP_W_TILES - STRIP_WALL_TILES) return 0;
    if (y_tile < row_lo || y_tile >= row_hi) return 0;
    if (y_tile + (int)stamp->h_tiles > row_hi && !clip) return 0;
    for (int i = 0; i < *n; i++) {
        if (stamp_tiles_overlap(stamp, x_tile, y_tile, acc[i].stamp, acc[i].x, acc[i].y)) return 0;
    }
    if (*n >= STRIP_BLOCK_MAX_PIECES) return 0;
    acc[*n].stamp = stamp;
    acc[*n].x = x_tile;
    acc[*n].y = y_tile;
    acc[*n].piece_id = piece_id;
    acc[*n].cat = cat;
    (*n)++;
    return 1;
}

// Vela candidates of one screen (y outer, x inner) whose baked phase exists.
static int vela_cands(int *cx, int *cy, int x_lo, int x_hi, int top) {
    int count = 0;
    for (int y = top; y <= top + STRIP_SCREEN_TILES - 4; y++) {
        for (int x = x_lo; x <= x_hi; x++) {
            if (x < STRIP_WALL_TILES || x + 4 > STRIP_W_TILES - STRIP_WALL_TILES) continue;
            if (!find_stamp(STRIP_PIECE_VELA, x, y)) continue;
            cx[count] = x;
            cy[count] = y;
            count++;
        }
    }
    return count;
}

static void pick_velas(PlanItem *acc, int *n, int32_t sidx, uint32_t salt, uint32_t sub0,
                       const int *cx, const int *cy, int ncand, int want, int row_lo, int row_hi) {
    if (ncand == 0) return;
    int placed = 0;
    for (int a = 0; a < 4 * want; a++) {
        if (placed == want) break;
        uint32_t pick = plan_pick(sidx, salt, sub0 + (uint32_t)a) % (uint32_t)ncand;
        if (plan_try(acc, n, PLAN_CAT_VEL, STRIP_PIECE_VELA, cx[pick], cy[pick],
                     row_lo, row_hi, 0)) placed++;
    }
}

// One part of the plan of a block, in the computation order of plan_block(). The parts are
// PLAN_UNITS calls: 0..1 structure of each screen (two columns, then a relicario or two benches),
// 2..3 lapidas of each screen (checked against the structure, so they never sit under a bench or
// a relicario), 4..9 velas of each screen (side 0, side 1, then the relicario's velas). The
// preparation runs the parts over several calls; plan_block() runs them all. Mirrors _block_records()
// in the baker.
#define PLAN_UNITS 10
static void plan_unit(int32_t block, PlanItem *acc, int *n_io, int unit) {
    int n = *n_io;
    int kinds[2];
    static int cx[160], cy[160];
    for (int s = 0; s < 2; s++) kinds[s] = (int)(plan_pick(2 * block + s, S_SCREEN_TYPE, 0) & 1u);
    if (unit < 2) {
        int s = unit;
        int32_t sidx = 2 * block + s;
        int top = s * STRIP_SCREEN_TILES;
        plan_try(acc, &n, PLAN_CAT_STRUCT, STRIP_PIECE_COLUMNA_ENTERA, 7, top + 9, 0, STRIP_BLOCK_TILES, 1);
        plan_try(acc, &n, PLAN_CAT_STRUCT, STRIP_PIECE_COLUMNA_ENTERA, 51, top + 9, 0, STRIP_BLOCK_TILES, 1);
        if (kinds[s]) {
            plan_try(acc, &n, PLAN_CAT_STRUCT, STRIP_PIECE_RELICARIO, 28, top + 9, 0, STRIP_BLOCK_TILES, 0);
        } else {
            int lx = (plan_pick(sidx, S_BENCH_LX, 0) & 1u) ? 16 : 19;
            int ly = top + ((plan_pick(sidx, S_BENCH_LY, 0) & 1u) ? 8 : 0);
            int ry = top + ((plan_pick(sidx, S_BENCH_RY, 0) & 1u) ? 8 : 0);
            plan_try(acc, &n, PLAN_CAT_STRUCT, STRIP_PIECE_BANCO_GRUPO4, lx, ly, 0, STRIP_BLOCK_TILES, 0);
            plan_try(acc, &n, PLAN_CAT_STRUCT, STRIP_PIECE_BANCO_GRUPO4, 35, ry, 0, STRIP_BLOCK_TILES, 0);
        }
    } else if (unit < 4) {
        int s = unit - 2;
        int32_t sidx = 2 * block + s;
        int top = s * STRIP_SCREEN_TILES;
        int row_hi = top + STRIP_SCREEN_TILES;
        static const uint8_t lapida_ids[4] = { STRIP_PIECE_LAPIDA_3X2_CRUZ, STRIP_PIECE_LAPIDA_3X2_CAB,
                                               STRIP_PIECE_LAPIDA_2X1_CRUZ, STRIP_PIECE_LAPIDA_2X1_CAB };
        int nsingle = (int)(plan_pick(sidx, S_LAP_N, 0) % 3u);
        for (int i = 0; i < nsingle; i++) {
            int y = top + (int)(plan_pick(sidx, S_LAP_POS, (uint32_t)i) % 13u);
            int x0 = 7 + ((((2 * y) & 3) + 1) & 3);
            int n_pos = (41 - x0) / 4 + 1;
            int x = x0 + 4 * (int)(plan_pick(sidx, S_LAP_POS, 16u + (uint32_t)i) % (uint32_t)n_pos);
            plan_try(acc, &n, PLAN_CAT_LAP, lapida_ids[plan_pick(sidx, S_LAP_VAR, (uint32_t)i) % 4u],
                     x, y, top, row_hi, 0);
        }
        if (plan_pick(sidx, S_LAP_GRP, 0) % 100u < 20u) {
            int len = 4 + (int)(plan_pick(sidx, S_LAP_GLEN, 0) % 5u);
            int y0 = top + (len - 1) + (int)(plan_pick(sidx, S_LAP_GPOS, 0) % (uint32_t)(14 - len));
            int x0b = 7 + ((((2 * y0) & 3) + 1) & 3);
            int x_last_max = 41 - 2 * (len - 1);
            if (x0b <= x_last_max) {
                int n_pos = (x_last_max - x0b) / 4 + 1;
                int x0 = x0b + 4 * (int)(plan_pick(sidx, S_LAP_GPOS, 32u) % (uint32_t)n_pos);
                uint8_t id = (plan_pick(sidx, S_LAP_GVAR, 0) % 2u) ? STRIP_PIECE_LAPIDA_2X1_CAB
                                                                   : STRIP_PIECE_LAPIDA_2X1_CRUZ;
                for (int i = 0; i < len; i++)
                    plan_try(acc, &n, PLAN_CAT_LAP, id, x0 + 2 * i, y0 - i, top, row_hi, 0);
            }
        }
    } else {
        int s = (unit - 4) / 3;
        int part = (unit - 4) % 3;
        int32_t sidx = 2 * block + s;
        int top = s * STRIP_SCREEN_TILES;
        int row_hi = top + STRIP_SCREEN_TILES;
        if (part < 2) {
            int cx0 = part ? 51 : 7;
            int want = 1 + (int)(plan_pick(sidx, S_VELA_N, (uint32_t)part) % 2u);
            int ncand = vela_cands(cx, cy, cx0 - 3, cx0 + 3, top);
            pick_velas(acc, &n, sidx, S_VELA_PICK, (uint32_t)part * 16u, cx, cy, ncand, want, top, row_hi);
        } else if (kinds[s]) {
            int want = 3 + (int)(plan_pick(sidx, S_REL_VN, 0) % 3u);
            int ncand = vela_cands(cx, cy, 28 - 5, 28 + 5, top);
            pick_velas(acc, &n, sidx, S_REL_PICK, 0, cx, cy, ncand, want, top, row_hi);
        }
    }
    *n_io = n;
}

// Accepted pieces of one block: all parts of plan_unit() in order.
static int plan_block(int32_t block, PlanItem *acc) {
    int n = 0;
    for (int unit = 0; unit < PLAN_UNITS; unit++) plan_unit(block, acc, &n, unit);
    return n;
}

// Band -> block and row offset of the band inside the block. Same map as band_block() in the baker.
static void band_to_block(int32_t band, int32_t *block, int32_t *off) {
    if (band < 16) {
        *block = band / 3;
        *off = (band % 3) * STRIP_BAND_TILES;
        return;
    }
    int32_t b = band - 16;
    int32_t g = b / 6;
    int32_t k = b % 6;
    *block = -2 * (g + 1) + k / 3;
    *off = (k % 3) * STRIP_BAND_TILES;
}

static void packed_set_cell(uint8_t *collision, unsigned cell_y, unsigned cell_x, unsigned value) {
    if (cell_x > 0 && cell_x < STRIP_COLLISION_W - 1u)
        packed_collision_set(collision, cell_y * STRIP_COLLISION_W + cell_x, value);
}

// Write the part of a planned piece that falls inside the band whose first block row is `off`:
// its tiles, its footprint cells and its occlusion runs. Rows outside the band are dropped.
static void stamp_place_band(const BandSink *sink, const PlanItem *it, int32_t off,
                             int map_row, int collision_row) {
    const StripStamp *stamp = it->stamp;
    int rel = it->y - (int)off;                       // piece top row, band-local
    for (unsigned sy = 0; sy < stamp->h_tiles; sy++) {
        int ly = rel + (int)sy;
        if (ly < 0 || ly >= STRIP_BAND_TILES) continue;
        unsigned dst = (unsigned)(map_row + ly) * STRIP_W_TILES + (unsigned)it->x;
        unsigned src = sy * stamp->w_tiles;
        for (unsigned sx = 0; sx < stamp->w_tiles; sx++) {
            uint16_t tile = stamp->tiles[src + sx];
            if (tile != 0) sink->map[dst + sx] = tile;
        }
    }
    for (unsigned ri = 0; ri < stamp->num_foot_runs; ri++) {
        const StripFootprintRun *run = &stamp->foot_runs[ri];
        int cell_local = rel * 2 + (int)run->y_cell;  // cell row inside the band
        if (cell_local < 0 || cell_local >= STRIP_BAND_CELLS) continue;
        unsigned cell_y = (unsigned)collision_row + (unsigned)cell_local;
        if (cell_y >= STRIP_COLLISION_H - 1u) continue;
        unsigned first_cell = (unsigned)it->x * 2u + run->x_cell;
        for (unsigned cx = 0; cx < run->length_cells; cx++)
            packed_set_cell(sink->collision, cell_y, first_cell + cx, stamp->foot_value);
    }
    for (unsigned ri = 0; ri < stamp->num_depth_runs; ri++) {
        const StripDepthRun *run = &stamp->depth_runs[ri];
        int row_local = rel * 8 + (int)run->y_px;      // window pixel row inside the band
        if (row_local < 0 || row_local >= STRIP_BAND_TILES * 8 || !run->length) continue;
        unsigned rx = (unsigned)(it->x * 8 + run->x_px);
        if (rx >= STRIP_W_PX) continue;
        if (*sink->run_count >= sink->run_limit) {
            if (sink->run_dropped) (*sink->run_dropped)++;
            continue;
        }
        int base_px = map_row * 8 + rel * 8;
        DungeonOcclusionRun *dst = &sink->runs[(*sink->run_count)++];
        dst->x = (uint16_t)rx;
        dst->y = (uint16_t)(map_row * 8 + row_local);
        dst->length = (uint16_t)((rx + run->length > STRIP_W_PX) ? STRIP_W_PX - rx : run->length);
        dst->depth = (int16_t)(base_px + stamp->foot_anchor_y_px + run->depth_delta);
    }
}

// Sink for the parity harness: every planned piece of a block, in emission order.
#if STRIP_LAYOUT_DUMP
static void dump_block_plan(int32_t block, const PlanItem *acc, int n) {
    for (int cat = 0; cat < 3; cat++) {
        for (int i = 0; i < n; i++) {
            if (acc[i].cat != cat || !g_strip_layout_dump) continue;
            g_strip_layout_dump(block, acc[i].piece_id, acc[i].stamp->phase_col,
                                acc[i].stamp->phase_row, acc[i].x, acc[i].y);
        }
    }
}
#endif

static void stamp_band(const BandSink *sink, int32_t band, int map_row, int collision_row) {
#if defined(PROPS_SHOWCASE) && PROPS_SHOWCASE
    // Showcase build: strip_start() places one fixed exemplar of each physical prop instead.
    return;
#endif
    if ((band >= STRIP_INITIAL_BANDS - STRIP_START_CLEAR_BANDS && band < STRIP_INITIAL_BANDS) ||
        g_strip_kit.num_stamps == 0 ||
        g_strip_kit.stamps == 0 || g_strip_kit.floor_h_tiles == 0) return;
    int32_t block, off;
    band_to_block(band, &block, &off);
    // The three bands of a block share one plan: compute it once, when the first band asks.
    // The cache key is the block, and the plan is a pure function of (seed, block), so the
    // preparation may fill it for the bands it builds ahead.
    if (block != s_plan_block) {
        s_plan_n = plan_block(block, s_plan);
        s_plan_block = block;
    }
    for (int cat = 0; cat < 3; cat++) {
        for (int i = 0; i < s_plan_n; i++) {
            if (s_plan[i].cat == cat) stamp_place_band(sink, &s_plan[i], off, map_row, collision_row);
        }
    }
}

#if STRIP_LAYOUT_DUMP
// Host-only parity harness hook: the plan of `num_blocks` blocks from `first_block`, dumped in
// emission order. Pure function of (seed, block): no arena, no band state.
void strip_layout_dump_blocks(uint32_t seed, int32_t first_block, int num_blocks) {
    s_seed = seed;
    for (int i = 0; i < num_blocks; i++) {
        PlanItem acc[STRIP_BLOCK_MAX_PIECES];
        int n = plan_block(first_block + i, acc);
        dump_block_plan(first_block + i, acc, n);
    }
    s_plan_block = STRIP_PLAN_NONE;
}

const uint16_t *strip_layout_map(void) { return s_map; }
const uint8_t *strip_layout_collision(void) { return s_collision; }
const DungeonOcclusionRun *strip_layout_occlusion(uint32_t *count) {
    *count = s_occlusion_count;
    return s_runs_active;
}
const uint32_t *strip_layout_occlusion_row_start(void) { return s_row_active; }
#endif

// One band: the floor copy of its rows plus its stamps, written into `sink` (window row numbering).
static void generate_band(const BandSink *sink, int32_t band, int map_row, int collision_row) {
    const unsigned map_period = g_strip_kit.map_h_tiles;
    const unsigned collision_period = (unsigned)g_strip_kit.floor_h_tiles * 2u;
    unsigned map_phase = (unsigned)((uint32_t)band * STRIP_BAND_TILES) % map_period;
    unsigned collision_phase = (unsigned)((uint32_t)band * STRIP_BAND_CELLS) % collision_period;

    for (unsigned row = 0; row < STRIP_BAND_TILES; row++) {
        const uint16_t *src = g_strip_kit.floor_map + map_phase * STRIP_W_TILES;
        uint16_t *dst = sink->map + (unsigned)(map_row + (int)row) * STRIP_W_TILES;
        memcpy(dst, src, STRIP_MAP_ROW_BYTES);
        map_phase++;
        if (map_phase == map_period) map_phase = 0;
    }
    for (unsigned row = 0; row < STRIP_BAND_CELLS; row++) {
        const uint8_t *src = g_strip_kit.floor_collision + collision_phase * STRIP_COLLISION_ROW_BYTES;
        uint8_t *dst = sink->collision + (unsigned)(collision_row + (int)row) * STRIP_COLLISION_ROW_BYTES;
        memcpy(dst, src, STRIP_COLLISION_ROW_BYTES);
        collision_phase++;
        if (collision_phase == collision_period) collision_phase = 0;
    }

    stamp_band(sink, band, map_row, collision_row);
}

// Hard edges (DESIGN.md 6.9.1b): the wall columns of collision rows [0, row_end) and the whole
// bottom row. A commit passes only the rows it rewrote: the others already carry their walls.
static void enforce_hard_edges(unsigned row_end) {
    for (unsigned row = 0; row < row_end; row++) {
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

// Row of a run, clamped to the tail bucket STRIP_WIN_H_PX (runs outside the window never occur).
static uint32_t occlusion_bucket(uint16_t y) {
    return y < STRIP_WIN_H_PX ? y : STRIP_WIN_H_PX;
}

// Stable (y, x) order: true when `a` must come after `b`.
static int occlusion_after(const DungeonOcclusionRun *a, const DungeonOcclusionRun *b) {
    return a->y > b->y || (a->y == b->y && a->x > b->x);
}

// Orders s_occlusion_runs by (y, x) in O(n + rows) for the bucket pass plus an insertion sort
// per row, stable for equal (y, x). s_occlusion_row_start[y] ends as the first index of row y.
// Used by strip_start() only: a rebase never sorts everything, it merges (see prep_* below).
static void rebuild_occlusion_index(void) {
    uint32_t *start = s_occlusion_row_start;
    const uint32_t n = s_occlusion_count;
    memset(start, 0, sizeof(s_occlusion_row_start));
    // Count per row into start[row + 1]; the tail bucket is not counted, it fills the rest.
    for (uint32_t i = 0; i < n; i++) {
        uint32_t b = occlusion_bucket(s_occlusion_runs[i].y);
        if (b < STRIP_WIN_H_PX) start[b + 1]++;
    }
    // Prefix sums: start[y] = number of runs in rows < y. Tail starts at start[STRIP_WIN_H_PX].
    for (uint32_t y = 1; y <= STRIP_WIN_H_PX; y++) start[y] += start[y - 1];
    // Place in input order (stable), using start[row] as the cursor of each row.
    for (uint32_t i = 0; i < n; i++) {
        uint32_t b = occlusion_bucket(s_occlusion_runs[i].y);
        s_occlusion_scratch[start[b]++] = s_occlusion_runs[i];
    }
    // The cursors now hold the end of each row: shift them back one slot to get the row starts.
    for (uint32_t y = STRIP_WIN_H_PX; y > 0; y--) start[y] = start[y - 1];
    start[0] = 0;
    // Insertion sort by x inside each row. Rows hold a handful of runs, and the input is already
    // nearly ordered, so each run moves only a few places. Strict '>' keeps equal keys in order.
    for (uint32_t i = 1; i < n; i++) {
        DungeonOcclusionRun cur = s_occlusion_scratch[i];
        uint32_t lo = start[occlusion_bucket(cur.y)];
        uint32_t j = i;
        while (j > lo && occlusion_after(&s_occlusion_scratch[j - 1], &cur)) {
            s_occlusion_scratch[j] = s_occlusion_scratch[j - 1];
            j--;
        }
        s_occlusion_scratch[j] = cur;
    }
    for (uint32_t i = 0; i < n; i++) s_occlusion_runs[i] = s_occlusion_scratch[i];
}

// ---- Incremental preparation of the next rebase (strip_prepare_step) ----------------------------
//
// A rebase depends only on the current window, s_seed and s_next_band, so the window it will
// produce can be built ahead in the reserve buffers, one bounded unit of work per call:
//   BANDS   6 calls   generate band b into s_stage_map / s_stage_collision (window rows 0..95 and
//                     0..191) and its runs, in emission order, into s_stage_new_runs.
//   PLAN    10 calls  per block, before its first band (two blocks per rebase): plan_unit() parts.
//   COUNT   chunks    per-row counts of the new runs (STRIP_PREP_CHUNK_RUNS per call).
//   PREFIX  1 call    prefix sums over the 768 new rows.
//   PLACE   chunks    stable scatter of the new runs into the reserve array; then the cursors
//                     are shifted back into row starts.
//   INSERT  chunks    insertion sort by x inside each row (the loop of rebuild_occlusion_index).
//   COPY    chunks    the surviving runs (a prefix of the active array, sorted by y) shifted by
//                     +768 in y and depth, after the new ones (STRIP_PREP_COPY_RUNS per call).
//   INDEX   1 call    row starts of the reserve: rows 0..767 from the scatter, rows 768..2048 are
//                     nn + the active row starts of y - 768.
//   READY             the commit is a few copies and pointer swaps (commit_prepared).
// The active window does not change until the commit, so the preparation never needs to be
// redone. strip_start() drops it (phase IDLE). A rebase that finds the preparation unfinished runs
// the remaining units in the same call: the same result, with the full cost in one frame.

static void prep_begin(void) {
    s_prep_kept = s_row_active[STRIP_KEEP_MAX_Y];      // runs of the active window that survive
    uint32_t room = STRIP_OCCLUSION_CAPACITY - s_prep_kept;
    s_stage_new_count = 0;
    s_stage_sink.map = s_stage_map;
    s_stage_sink.collision = s_stage_collision;
    s_stage_sink.runs = s_stage_new_runs;
    s_stage_sink.run_count = &s_stage_new_count;
    s_stage_sink.run_limit = room < STRIP_STAGE_RUNS_MAX ? room : STRIP_STAGE_RUNS_MAX;
    s_stage_sink.run_dropped = &s_stage_dropped;
    memset(s_row_reserve, 0, (STRIP_SHIFT_PX + 1u) * sizeof(uint32_t));
    s_prep_new = 0;
    s_prep_cursor = 0;
    s_prep_steps = 0;
    s_prep_phase = PREP_BANDS;
}

// The plan of a block is built by PLAN_UNITS calls of plan_unit() before the first band that needs
// it, so no call computes a whole plan (about 8 us on the host).
static void prep_plan(void) {
    plan_unit(s_prep_plan_block, s_plan, &s_prep_plan_n, (int)s_prep_plan_unit);
    if (++s_prep_plan_unit == PLAN_UNITS) {
        s_plan_n = s_prep_plan_n;
        s_plan_block = s_prep_plan_block;   // the cache now holds this block's plan
        s_prep_phase = PREP_BANDS;
    }
}

static void prep_band(void) {
    uint32_t b = s_prep_cursor;
    int32_t block, off;
    band_to_block(s_next_band + (int32_t)b, &block, &off);
    if (block != s_plan_block) {
        s_prep_plan_block = block;
        s_prep_plan_unit = 0;
        s_prep_plan_n = 0;
        s_prep_phase = PREP_PLAN;
        return;
    }
    generate_band(&s_stage_sink, s_next_band + (int32_t)b,
                  (int)(b * STRIP_BAND_TILES), (int)(b * STRIP_BAND_CELLS));
    if (++s_prep_cursor == STRIP_PREP_STAGE_BANDS) {
        s_prep_cursor = 0;
        s_prep_phase = PREP_COUNT;
    }
}

static void prep_count(void) {
    uint32_t end = s_prep_cursor + STRIP_PREP_CHUNK_RUNS;
    if (end > s_stage_new_count) end = s_stage_new_count;
    for (uint32_t i = s_prep_cursor; i < end; i++) s_row_reserve[s_stage_new_runs[i].y + 1u]++;
    s_prep_cursor = end;
    if (end == s_stage_new_count) {
        s_prep_cursor = 0;
        s_prep_phase = PREP_PREFIX;
    }
}

static void prep_prefix(void) {
    for (uint32_t y = 1; y <= STRIP_SHIFT_PX; y++) s_row_reserve[y] += s_row_reserve[y - 1];
    if (s_stage_new_count > s_stage_peak) s_stage_peak = s_stage_new_count;
    s_prep_phase = PREP_PLACE;
}

static void prep_place(void) {
    uint32_t end = s_prep_cursor + STRIP_PREP_CHUNK_RUNS;
    if (end > s_stage_new_count) end = s_stage_new_count;
    for (uint32_t i = s_prep_cursor; i < end; i++) {
        const DungeonOcclusionRun *run = &s_stage_new_runs[i];
        s_runs_reserve[s_row_reserve[run->y]++] = *run;
    }
    s_prep_cursor = end;
    if (end == s_stage_new_count) {
        // The cursors now hold the end of each row: shift them back one slot to get the row starts.
        for (uint32_t y = STRIP_SHIFT_PX; y > 0; y--) s_row_reserve[y] = s_row_reserve[y - 1];
        s_row_reserve[0] = 0;
        s_prep_new = s_stage_new_count;
        s_prep_cursor = 0;
        s_prep_phase = PREP_INSERT;
    }
}

static void prep_insert(void) {
    const uint32_t n = s_prep_new;
    uint32_t i = s_prep_cursor < 1u ? 1u : s_prep_cursor;
    uint32_t end = i + STRIP_PREP_CHUNK_RUNS;
    if (end > n) end = n;
    DungeonOcclusionRun *a = s_runs_reserve;
    for (; i < end; i++) {
        DungeonOcclusionRun cur = a[i];
        uint32_t lo = s_row_reserve[occlusion_bucket(cur.y)];
        uint32_t j = i;
        while (j > lo && occlusion_after(&a[j - 1], &cur)) {
            a[j] = a[j - 1];
            j--;
        }
        a[j] = cur;
    }
    s_prep_cursor = end;
    if (end >= n) {
        s_prep_cursor = 0;
        s_prep_phase = PREP_COPY;
    }
}

static void prep_copy(void) {
    uint32_t end = s_prep_cursor + STRIP_PREP_COPY_RUNS;
    if (end > s_prep_kept) end = s_prep_kept;
    const DungeonOcclusionRun *src = s_runs_active;
    DungeonOcclusionRun *dst = s_runs_reserve + s_prep_new;
    for (uint32_t k = s_prep_cursor; k < end; k++) {
        DungeonOcclusionRun run = src[k];
        run.y = (uint16_t)(run.y + STRIP_SHIFT_PX);
        run.depth += STRIP_SHIFT_PX;
        dst[k] = run;
    }
    s_prep_cursor = end;
    if (end == s_prep_kept) {
        s_prep_cursor = 0;
        s_prep_phase = PREP_INDEX;
    }
}

static void prep_index(void) {
    for (uint32_t y = STRIP_SHIFT_PX; y <= STRIP_WIN_H_PX; y++)
        s_row_reserve[y] = s_prep_new + s_row_active[y - STRIP_SHIFT_PX];
    s_prep_phase = PREP_READY;
}

// One unit of preparation work (the IDLE unit only starts the preparation).
static void prep_unit(void) {
    s_prep_steps++;
    switch (s_prep_phase) {
    case PREP_IDLE:   prep_begin(); break;
    case PREP_BANDS:  prep_band(); break;
    case PREP_PLAN:   prep_plan(); break;
    case PREP_COUNT:  prep_count(); break;
    case PREP_PREFIX: prep_prefix(); break;
    case PREP_PLACE:  prep_place(); break;
    case PREP_INSERT: prep_insert(); break;
    case PREP_COPY:   prep_copy(); break;
    case PREP_INDEX:  prep_index(); break;
    default:          break;
    }
}

// Commit of a READY preparation: the window moves up by STRIP_SHIFT_PX. The map and collision
// rows move with two memmove; the six new bands come from the stage; the run arrays and row
// indexes swap roles, so the Arena reads the new window from its next call on.
static int commit_prepared(void) {
    memmove(s_map + STRIP_MAP_SHIFT_ROWS * STRIP_W_TILES,
            s_map,
            (STRIP_MAP_H_TILES - STRIP_MAP_SHIFT_ROWS) * STRIP_MAP_ROW_BYTES);
    memmove(s_collision + STRIP_COLLISION_SHIFT_ROWS * STRIP_COLLISION_ROW_BYTES,
            s_collision,
            (STRIP_COLLISION_H - STRIP_COLLISION_SHIFT_ROWS) * STRIP_COLLISION_ROW_BYTES);
    memcpy(s_map, s_stage_map, sizeof(s_stage_map));
    memcpy(s_collision, s_stage_collision, sizeof(s_stage_collision));

    DungeonOcclusionRun *runs = s_runs_active;
    s_runs_active = s_runs_reserve;
    s_runs_reserve = runs;
    uint32_t *rows = s_row_active;
    s_row_active = s_row_reserve;
    s_row_reserve = rows;
    s_occlusion_count = s_prep_new + s_prep_kept;
    s_arena.occlusion_runs = s_runs_active;
    s_arena.occlusion_row_start = s_row_active;

    enforce_hard_edges(STRIP_COLLISION_SHIFT_ROWS);
    s_next_band += STRIP_PREP_STAGE_BANDS;
    s_shift_total_px += STRIP_SHIFT_PX;
    s_prep_steps_last = s_prep_steps;
    s_prep_phase = PREP_IDLE;
    return STRIP_SHIFT_PX;
}

// Live window: where strip_start() writes its bands.
static BandSink live_sink(void) {
    BandSink sink = { s_map, s_collision, s_occlusion_runs, &s_occlusion_count,
                      STRIP_OCCLUSION_CAPACITY, 0 };
    return sink;
}

void strip_start(uint32_t seed) {
    s_seed = seed;
    s_next_band = 0;
    s_shift_total_px = 0;
    s_occlusion_count = 0;
    s_plan_block = STRIP_PLAN_NONE;
    s_prep_phase = PREP_IDLE;
    s_runs_active = s_occlusion_runs;
    s_runs_reserve = s_occlusion_scratch;
    s_row_active = s_occlusion_row_start;
    s_row_reserve = s_stage_row_start;
    s_arena.occlusion_runs = s_occlusion_runs;
    s_arena.occlusion_row_start = s_occlusion_row_start;
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
        enforce_hard_edges(STRIP_COLLISION_H);
        return;
    }
    s_kit_valid = 1;

    BandSink sink = live_sink();
    for (int band = 0; band < STRIP_MAP_H_TILES / STRIP_BAND_TILES; band++) {
        generate_band(&sink, band, band * STRIP_BAND_TILES, band * STRIP_BAND_CELLS);
        s_next_band = band + 1;
    }
    rebuild_occlusion_index();
    enforce_hard_edges(STRIP_COLLISION_H);
    s_arena.num_tiles = g_strip_kit.num_tiles;
    s_arena.palette = g_strip_kit.palette;
    s_arena.tiles = g_strip_kit.tiles;
}

void strip_prepare_step(int player_y_px) {
    if (g_arena != &s_arena || !s_kit_valid || s_prep_phase == PREP_READY) return;
    if (player_y_px >= STRIP_REBASE_TOP_PX + STRIP_PREPARE_MARGIN_PX) return;
    prep_unit();
}

int strip_rebase_if_needed(int player_y_px) {
    if (g_arena != &s_arena || !s_kit_valid || player_y_px >= STRIP_REBASE_TOP_PX) return 0;
    // Units the preparation has not reached yet run now: same result, the full cost in this call.
    while (s_prep_phase != PREP_READY) prep_unit();
    return commit_prepared();
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
