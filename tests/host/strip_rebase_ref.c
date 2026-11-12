/*
 * REFERENCIA del rebase de la tira ANTES de la preparacion incremental (host only).
 * Copia literal de source/strip.c previa al cambio; solo sirve al arnés de equivalencia
 * (tests/host/strip_rebase_equiv.c) y al perfil (tests/host/strip_rebase_profile.c).
 * Los simbolos publicos se renombran con prefijo ref_ para convivir con source/strip.c
 * en el mismo ejecutable. No se compila en la ROM.
 */
#define strip_start ref_strip_start
#define strip_rebase_if_needed ref_strip_rebase_if_needed
#define strip_shift_total_px ref_strip_shift_total_px
#define strip_start_x ref_strip_start_x
#define strip_start_y ref_strip_start_y
#define strip_height_m ref_strip_height_m
#define strip_lane_center_px ref_strip_lane_center_px
#define strip_arena ref_strip_arena
#include "strip_rebase_ref.h"
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

typedef struct {
    const StripStamp *stamp;
    int x, y;          // block tiles (y is the block row, 0..47)
    uint8_t piece_id;
    uint8_t cat;       // PLAN_CAT_*
} PlanItem;

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
static int32_t s_plan_block = STRIP_PLAN_NONE;   // block whose plan sits in s_plan
static PlanItem s_plan[STRIP_BLOCK_MAX_PIECES];
static int s_plan_n;
#define STRIP_INITIAL_BANDS (STRIP_MAP_H_TILES / STRIP_BAND_TILES)

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

// Accepted pieces of one block. Computation order: structure (per screen: two columns, then a
// relicario or two benches), lapidas (checked against the structure, so they never sit under a bench
// or a relicario) and velas last. Mirrors _block_records() in the baker.
static int plan_block(int32_t block, PlanItem *acc) {
    int n = 0;
    int kinds[2];
    static int cx[160], cy[160];
    for (int s = 0; s < 2; s++) kinds[s] = (int)(plan_pick(2 * block + s, S_SCREEN_TYPE, 0) & 1u);
    for (int s = 0; s < 2; s++) {
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
    }
    static const uint8_t lapida_ids[4] = { STRIP_PIECE_LAPIDA_3X2_CRUZ, STRIP_PIECE_LAPIDA_3X2_CAB,
                                           STRIP_PIECE_LAPIDA_2X1_CRUZ, STRIP_PIECE_LAPIDA_2X1_CAB };
    for (int s = 0; s < 2; s++) {
        int32_t sidx = 2 * block + s;
        int top = s * STRIP_SCREEN_TILES;
        int row_hi = top + STRIP_SCREEN_TILES;
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
    }
    for (int s = 0; s < 2; s++) {
        int32_t sidx = 2 * block + s;
        int top = s * STRIP_SCREEN_TILES;
        int row_hi = top + STRIP_SCREEN_TILES;
        for (int side = 0; side < 2; side++) {
            int cx0 = side ? 51 : 7;
            int want = 1 + (int)(plan_pick(sidx, S_VELA_N, (uint32_t)side) % 2u);
            int ncand = vela_cands(cx, cy, cx0 - 3, cx0 + 3, top);
            pick_velas(acc, &n, sidx, S_VELA_PICK, (uint32_t)side * 16u, cx, cy, ncand, want, top, row_hi);
        }
        if (kinds[s]) {
            int want = 3 + (int)(plan_pick(sidx, S_REL_VN, 0) % 3u);
            int ncand = vela_cands(cx, cy, 28 - 5, 28 + 5, top);
            pick_velas(acc, &n, sidx, S_REL_PICK, 0, cx, cy, ncand, want, top, row_hi);
        }
    }
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

static void packed_set_cell(unsigned cell_y, unsigned cell_x, unsigned value) {
    if (cell_x > 0 && cell_x < STRIP_COLLISION_W - 1u)
        packed_collision_set(s_collision, cell_y * STRIP_COLLISION_W + cell_x, value);
}

// Write the part of a planned piece that falls inside the band whose first block row is `off`:
// its tiles, its footprint cells and its occlusion runs. Rows outside the band are dropped.
static void stamp_place_band(const PlanItem *it, int32_t off, int map_row, int collision_row) {
    const StripStamp *stamp = it->stamp;
    int rel = it->y - (int)off;                       // piece top row, band-local
    for (unsigned sy = 0; sy < stamp->h_tiles; sy++) {
        int ly = rel + (int)sy;
        if (ly < 0 || ly >= STRIP_BAND_TILES) continue;
        unsigned dst = (unsigned)(map_row + ly) * STRIP_W_TILES + (unsigned)it->x;
        unsigned src = sy * stamp->w_tiles;
        for (unsigned sx = 0; sx < stamp->w_tiles; sx++) {
            uint16_t tile = stamp->tiles[src + sx];
            if (tile != 0) s_map[dst + sx] = tile;
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
            packed_set_cell(cell_y, first_cell + cx, stamp->foot_value);
    }
    for (unsigned ri = 0; ri < stamp->num_depth_runs; ri++) {
        const StripDepthRun *run = &stamp->depth_runs[ri];
        int row_local = rel * 8 + (int)run->y_px;      // window pixel row inside the band
        if (row_local < 0 || row_local >= STRIP_BAND_TILES * 8 || !run->length) continue;
        unsigned rx = (unsigned)(it->x * 8 + run->x_px);
        if (rx >= STRIP_W_PX) continue;
        if (s_occlusion_count >= STRIP_OCCLUSION_CAPACITY) continue;
        int base_px = map_row * 8 + rel * 8;
        DungeonOcclusionRun *dst = &s_occlusion_runs[s_occlusion_count++];
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

static void stamp_band(int32_t band, int map_row, int collision_row) {
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
    if (block != s_plan_block) {
        s_plan_n = plan_block(block, s_plan);
        s_plan_block = block;
    }
    for (int cat = 0; cat < 3; cat++) {
        for (int i = 0; i < s_plan_n; i++) {
            if (s_plan[i].cat == cat) stamp_place_band(&s_plan[i], off, map_row, collision_row);
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
    return s_occlusion_runs;
}
const uint32_t *strip_layout_occlusion_row_start(void) { return s_occlusion_row_start; }
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

// Scratch for the row bucket sort: 32768 * 8 B = 256 KB of static RAM, only touched by rebuilds.
static DungeonOcclusionRun s_occlusion_scratch[STRIP_OCCLUSION_CAPACITY];

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

void strip_start(uint32_t seed) {
    s_seed = seed;
    s_next_band = 0;
    s_shift_total_px = 0;
    s_occlusion_count = 0;
    s_plan_block = STRIP_PLAN_NONE;
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

void ref_strip_state_view(StripStateView *view) {
    view->map = s_map;
    view->collision = s_collision;
    view->runs = s_occlusion_runs;
    view->run_count = s_occlusion_count;
    view->row_start = s_occlusion_row_start;
    view->next_band = s_next_band;
    view->shift_total_px = s_shift_total_px;
}
