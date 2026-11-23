#include "hwshadow.h"

#if HW_SHADOWS

#include <nds.h>
#include "game.h"
#include "verja_gfx.h"

int g_hw_shadows_on = 1;

// ---------------------------------------------------------------------------
// OBJ VRAM and OAM budget
//   Main engine: bank E at 0x06400000. Tile indices are 10 bits in 1D_32 mapping, so only the
//     first 1024 tiles (32 KiB) of the 64 KiB bank are addressable.
//   Sub engine: bank I at 0x06600000, 512 tiles (16 KiB, the whole bank).
//   OAM: 128 entries per engine. A shadow takes 1-4 entries (see the plan below).
// Tiles are 4 bpp (32 bytes). Mask bit set (masks are 1 bpp, LSB first) becomes colour index 1: any non-zero index makes
// the OBJ-window pixel opaque, the palette is irrelevant.
// ---------------------------------------------------------------------------

#define POOL_TILES_MAIN 1024
#define POOL_TILES_SUB 512
#define VERJA_TILES 128          // two 64x64 4bpp OBJs (0..63 left 64px, 64..127 right 40px), reserved at pool start
#define MAX_ENTRIES 96
#define OAM_LIMIT 128
#define PLAN_MAX_PARTS 8
#define OBJ_PENALTY_TILES 3     // an extra OAM entry is worth this many tiles when planning

typedef struct { uint8_t w, h, shape, size; } HwObjShape;   // w, h in tiles
static const HwObjShape k_shapes[12] = {
    {1, 1, 0, 0}, {2, 2, 0, 1}, {4, 4, 0, 2}, {8, 8, 0, 3},   // square 8, 16, 32, 64
    {2, 1, 1, 0}, {4, 1, 1, 1}, {4, 2, 1, 2}, {8, 4, 1, 3},   // wide 16x8, 32x8, 32x16, 64x32
    {1, 2, 2, 0}, {1, 4, 2, 1}, {2, 4, 2, 2}, {4, 8, 2, 3},   // tall 8x16, 8x32, 16x32, 32x64
};

// A shadow of w x h tiles is covered by a few OBJs of small total area (a 34x35 px mask would
// need one 64x64 OBJ = 64 tiles; split it takes about 25). Computed once at boot by a tiny DP.
typedef struct { uint8_t tx, ty, shape, toff; } PlanPart;   // tile offset in the shadow, OBJ shape, first tile in its block
typedef struct { uint8_t n; uint8_t tiles; PlanPart p[PLAN_MAX_PARTS]; } Plan;
static Plan s_plan[11][11];                                  // [h][w], 1..10 (hasta 80 px)
static int16_t s_cost[11][11];
static int8_t s_choice[11][11]; // 0..11 single OBJ of that shape, 100+c vertical split at c, 120+r horizontal at r
#define RETIRED_MASK ((const uint8_t *)(uintptr_t)1)

static int plan_cost(int w, int h) {
    if (s_cost[h][w]) return s_cost[h][w];
    int best = 0x7fff, choice = -1;
    for (int s = 0; s < 12; s++) {
        if (k_shapes[s].w < w || k_shapes[s].h < h) continue;
        int c = k_shapes[s].w * k_shapes[s].h + OBJ_PENALTY_TILES;
        if (c < best) { best = c; choice = s; }
    }
    for (int c = 1; c < w; c++) {
        int v = plan_cost(c, h) + plan_cost(w - c, h);
        if (v < best) { best = v; choice = 100 + c; }
    }
    for (int r = 1; r < h; r++) {
        int v = plan_cost(w, r) + plan_cost(w, h - r);
        if (v < best) { best = v; choice = 120 + r; }
    }
    s_cost[h][w] = (int16_t)best;
    s_choice[h][w] = (int8_t)choice;
    return best;
}

static void plan_emit(Plan *plan, int w, int h, int x0, int y0) {
    int choice = s_choice[h][w];
    if (choice < 100) {
        if (plan->n < PLAN_MAX_PARTS) {
            PlanPart *p = &plan->p[plan->n++];
            p->tx = (uint8_t)x0;
            p->ty = (uint8_t)y0;
            p->shape = (uint8_t)choice;
            p->toff = plan->tiles;
        }
        plan->tiles = (uint8_t)(plan->tiles + k_shapes[choice].w * k_shapes[choice].h);
    } else if (choice < 120) {
        int c = choice - 100;
        plan_emit(plan, c, h, x0, y0);
        plan_emit(plan, w - c, h, x0 + c, y0);
    } else {
        int r = choice - 120;
        plan_emit(plan, w, r, x0, y0);
        plan_emit(plan, w, h - r, x0, y0 + r);
    }
}

typedef struct {
    const uint8_t *mask;      // key: the baked mask in ROM (shared by every actor showing that frame)
    uint32_t last_build;
    uint16_t tile;            // first tile of its block in the pool
    uint8_t ht, wt;           // mask bounds in tiles (selects the plan)
} Entry;

typedef struct {
    OamState *oam;
    volatile uint32_t *vram;
    uint8_t *occ;             // 1 byte per pool tile
    int pool;
    Entry e[MAX_ENTRIES];
    uint32_t build;           // list being built
    uint32_t committed;       // list on screen: its tiles must not be overwritten
    int count, prev_count;    // OAM entries used by the building / committed list
} Engine;

static uint8_t s_occ_main[POOL_TILES_MAIN];
static uint8_t s_occ_sub[POOL_TILES_SUB];
static Engine s_eng[2];
static int s_verja_lift[2] = { -1, -1 };

// Uploads the 104x56 verja sprite shifted up by `lift_px` (0..55) into the first 128 4bpp tiles
// of `g->vram`, clearing the bottom `lift_px + 8` rows so the gate is clipped at its top edge.
static void verja_upload_tiles(Engine *g, int lift_px) {
    for (int blk = 0; blk < 2; blk++) {
        int x0 = blk * 64;
        volatile uint32_t *dst = g->vram + blk * 64 * 8;
        for (int ty = 0; ty < 8; ty++) {
            for (int tx = 0; tx < 8; tx++) {
                for (int r = 0; r < 8; r++) {
                    int sy = lift_px + ty * 8 + r;
                    uint32_t word = 0;
                    if (sy >= 0 && sy < VERJA_H) {
                        for (int px = 0; px < 8; px++) {
                            int sx = x0 + tx * 8 + px;
                            if (sx < VERJA_W) {
                                uint32_t c = g_verja_pixels[sy][sx];
                                if (c) word |= (c & 0xFu) << (px * 4);
                            }
                        }
                    }
                    dst[(ty * 8 + tx) * 8 + r] = word;
                }
            }
        }
    }
}

void hwshadow_add_verja(int sub, int x, int y, int lift_px, int in_front) {
    if (lift_px < 0) lift_px = 0;
    if (lift_px >= VERJA_H) return;
    if (y + (VERJA_H - lift_px) <= 0 || y >= SCREEN_H) return;
    Engine *g = &s_eng[sub];
    if (s_verja_lift[sub] != lift_px) {
        verja_upload_tiles(g, lift_px);
        s_verja_lift[sub] = lift_px;
    }
    static const int k_xoff[4] = { 0, 64, VERJA_W, VERJA_W + 64 };
    static const uint16_t k_tile[4] = { 0, 64, 0, 64 };
    const uint16_t prio = ATTR2_PRIORITY(in_front ? 0 : 1);
    for (int i = 0; i < 4; i++) {
        if (g->count >= OAM_LIMIT) return;
        int px = x + k_xoff[i];
        if (px >= SCREEN_W || px + 64 <= 0) continue;
        uint16_t *a = (uint16_t *)g->oam->oamMemory[g->count++].attribute;
        a[0] = (uint16_t)((y & 0xFF) | ATTR0_NORMAL | ATTR0_TYPE_NORMAL | ATTR0_COLOR_16);
        a[1] = (uint16_t)((px & 0x1FF) | ATTR1_SIZE_64);
        a[2] = (uint16_t)(k_tile[i] | prio);
    }
}

static void entry_free(Engine *g, Entry *en) {
    const Plan *pl = &s_plan[en->ht][en->wt];
    for (int i = 0; i < pl->tiles; i++) g->occ[en->tile + i] = 0;
    en->mask = NULL;
}

// Frees the least recently used entry that is neither in the list being built nor on screen.
static int evict_lru(Engine *g) {
    int best = -1;
    uint32_t best_build = 0xffffffffu;
    for (int i = 0; i < MAX_ENTRIES; i++) {
        Entry *en = &g->e[i];
        if (!en->mask || en->last_build == g->build || en->last_build == g->committed) continue;
        if (en->last_build < best_build) { best_build = en->last_build; best = i; }
    }
    if (best < 0) return 0;
    entry_free(g, &g->e[best]);
    return 1;
}

static int find_free_run(const Engine *g, int n) {
    int run = 0;
    for (int i = 0; i < g->pool; i++) {
        if (g->occ[i]) run = 0;
        else if (++run == n) return i - n + 1;
    }
    return -1;
}

// 4 bpp 8x8 tile layout (1D mapping), tiles of one OBJ row-major. VRAM takes 16/32-bit writes
// only, so every tile row (8 pixels) is composed in a register and stored as one word.
__attribute__((target("arm"), optimize("O3"), noinline))
ITCM_CODE static void convert_part(volatile uint32_t *dst, const uint8_t *mask, int bw, int bh,
                         int px0, int py0, int tw, int th) {
    for (int ty = 0; ty < th; ty++) {
        for (int tx = 0; tx < tw; tx++) {
            for (int r = 0; r < 8; r++) {
                int y = py0 + ty * 8 + r;
                uint32_t word = 0;
                if (y < bh) {
                    int xs = px0 + tx * 8;
                    int xe = xs + 8 < bw ? xs + 8 : bw;
                    int n = y * bw + xs;
                    for (int x = xs; x < xe; x++, n++) {
                        if ((mask[n >> 3] >> (n & 7)) & 1) word |= 1u << ((x - xs) * 4);
                    }
                }
                dst[(ty * tw + tx) * 8 + r] = word;
            }
        }
    }
}

static Entry *entry_make(Engine *g, const uint8_t *mask, const uint8_t *bounds) {
    int bw = bounds[2], bh = bounds[3];
    int wt = (bw + 7) >> 3, ht = (bh + 7) >> 3;
    const Plan *pl = &s_plan[ht][wt];
    int slot = -1;
    for (;;) {
        for (int i = 0; i < MAX_ENTRIES; i++) if (!g->e[i].mask) { slot = i; break; }
        if (slot >= 0) break;
        if (!evict_lru(g)) return NULL;
    }
    int tile;
    while ((tile = find_free_run(g, pl->tiles)) < 0) {
        if (!evict_lru(g)) return NULL;
    }
    Entry *en = &g->e[slot];
    en->mask = mask;
    en->tile = (uint16_t)tile;
    en->wt = (uint8_t)wt;
    en->ht = (uint8_t)ht;
    for (int i = 0; i < pl->tiles; i++) g->occ[tile + i] = 1;
    for (int i = 0; i < pl->n; i++) {
        const HwObjShape *sh = &k_shapes[pl->p[i].shape];
        convert_part(g->vram + (tile + pl->p[i].toff) * 8, mask, bw, bh,
                     pl->p[i].tx * 8, pl->p[i].ty * 8, sh->w, sh->h);
    }
    return en;
}

void hwshadow_begin(int sub) {
    Engine *g = &s_eng[sub];
    g->build++;
    g->count = 0;
    for (int i = 0; i < MAX_ENTRIES; i++) {
        if (g->e[i].mask == RETIRED_MASK && g->e[i].last_build != g->committed) {
            entry_free(g, &g->e[i]);
        }
    }
}

void hwshadow_invalidate(const uint8_t *mask) {
    if (!mask) return;
    hwshadow_invalidate_range(mask, mask + 1);
}

// Every entry whose mask lies in [lo, hi): the room pool empties (its addresses will hold other masks) or a mask
// buffer is overwritten.
void hwshadow_invalidate_range(const void *lo, const void *hi) {
    const uintptr_t a = (uintptr_t)lo, b = (uintptr_t)hi;
    for (int sub = 0; sub < 2; sub++) {
        Engine *g = &s_eng[sub];
        for (int i = 0; i < MAX_ENTRIES; i++) {
            Entry *en = &g->e[i];
            const uintptr_t m = (uintptr_t)en->mask;
            if (m < a || m >= b || en->mask == RETIRED_MASK) continue;
            if (en->last_build != g->build && en->last_build != g->committed)
                entry_free(g, en);
            else
                en->mask = RETIRED_MASK;
        }
    }
}

__attribute__((target("arm"), optimize("O3"), noinline))
ITCM_CODE void hwshadow_add(int sub, const uint8_t *mask, const uint8_t *bounds, int ox, int oy) {
    Engine *g = &s_eng[sub];
    int bw = bounds[2], bh = bounds[3];
    if (bw == 0 || bh == 0 || bw > 80 || bh > 80) return;
    int x0 = ox + bounds[0], y0 = oy + bounds[1];
    if (x0 >= SCREEN_W || y0 >= SCREEN_H || x0 + bw <= 0 || y0 + bh <= 0) return;
    const Plan *pl = &s_plan[(bh + 7) >> 3][(bw + 7) >> 3];
    if (g->count + pl->n > OAM_LIMIT) return;               // out of OAM: this shadow is skipped

    Entry *en = NULL;
    for (int i = 0; i < MAX_ENTRIES; i++) if (g->e[i].mask == mask) { en = &g->e[i]; break; }
    if (!en) en = entry_make(g, mask, bounds);
    if (!en) return;                                         // out of VRAM: skipped, never stalls
    en->last_build = g->build;

    for (int i = 0; i < pl->n; i++) {
        const PlanPart *p = &pl->p[i];
        const HwObjShape *sh = &k_shapes[p->shape];
        int px = x0 + p->tx * 8, py = y0 + p->ty * 8;
        if (px >= SCREEN_W || py >= SCREEN_H || px + sh->w * 8 <= 0 || py + sh->h * 8 <= 0) continue;
        uint16_t *a = (uint16_t *)g->oam->oamMemory[g->count++].attribute;
        a[0] = (uint16_t)((py & 0xFF) | ATTR0_NORMAL | ATTR0_TYPE_WINDOWED | ATTR0_COLOR_16 | (sh->shape << 14));
        a[1] = (uint16_t)((px & 0x1FF) | (sh->size << 14));
        a[2] = (uint16_t)(en->tile + p->toff);
    }
}

// Sync with the sprites: the lists are built while each screen is rendered and committed inside
// VBlank at the moment that screen's bitmap becomes visible (main: with the page flip in
// present_vblank_begin; sub: right after the single-buffered top page has been redrawn). OBJ
// tiles of the list on screen are never overwritten (see evict_lru), so building the next list
// during active display cannot disturb the current frame.
ITCM_CODE void hwshadow_commit(int sub) {
    Engine *g = &s_eng[sub];
    if (!g_hw_shadows_on) g->count = 0;
    for (int i = g->count; i < g->prev_count; i++) g->oam->oamMemory[i].attribute[0] = ATTR0_DISABLED;
    g->prev_count = g->count;
    oamUpdate(g->oam);
    g->committed = g->build;
}

// ---------------------------------------------------------------------------
// Window and blend
//   outside windows : every layer, no effect
//   OBJ window      : BG layers + effect -> BLDCNT darkens only the floor layer (main BG1 / sub BG0)
// ---------------------------------------------------------------------------

#define BLD_FADE_BLACK (3 << 6)
#define WINOUT_SHADOW 0x3F1F   // outside: BG0-3+OBJ, no effect | OBJ window: all + effect

void hwshadow_init(void) {
    s_eng[0] = (Engine){ .oam = &oamMain, .vram = (volatile uint32_t *)0x06400000, .occ = s_occ_main, .pool = POOL_TILES_MAIN };
    s_eng[1] = (Engine){ .oam = &oamSub, .vram = (volatile uint32_t *)0x06600000, .occ = s_occ_sub, .pool = POOL_TILES_SUB };
    vramSetBankE(VRAM_E_MAIN_SPRITE);
    vramSetBankI(VRAM_I_SUB_SPRITE);
    oamInit(&oamMain, SpriteMapping_1D_32, false);
    oamInit(&oamSub, SpriteMapping_1D_32, false);
    oamEnable(&oamMain);
    oamEnable(&oamSub);
    for (int i = 0; i < VERJA_TILES; i++) {
        s_occ_main[i] = 1;
        s_occ_sub[i] = 1;
    }
    for (int i = 0; i < 16; i++) {
        SPRITE_PALETTE[i] = g_verja_palette[i];
        SPRITE_PALETTE_SUB[i] = g_verja_palette[i];
    }
    verja_upload_tiles(&s_eng[0], 0);
    verja_upload_tiles(&s_eng[1], 0);
    s_verja_lift[0] = 0;
    s_verja_lift[1] = 0;
    for (int h = 1; h <= 10; h++)
        for (int w = 1; w <= 10; w++) {
            plan_cost(w, h);
            s_plan[h][w] = (Plan){0};
            plan_emit(&s_plan[h][w], w, h, 0, 0);
        }
}

void hwshadow_screen_regs(int sub) {
    vu16 *bldcnt = sub ? &REG_BLDCNT_SUB : &REG_BLDCNT;
    vu16 *bldy = sub ? &REG_BLDY_SUB : &REG_BLDY;
    vu16 *winout = sub ? &REG_WINOUT_SUB : &REG_WINOUT;
    vu32 *dispcnt = sub ? &REG_DISPCNT_SUB : &REG_DISPCNT;

    *winout = WINOUT_SHADOW;
    *dispcnt = (*dispcnt & ~DISPLAY_WIN0_ON) | DISPLAY_SPR_WIN_ON | DISPLAY_SPR_ACTIVE;
    *bldcnt = (uint16_t)((sub ? BIT(0) : BIT(1)) | BLD_FADE_BLACK);
    *bldy = HW_SHADOW_BLDY;
}

void hwshadow_regs_off(void) {
    REG_DISPCNT &= ~DISPLAY_SPR_WIN_ON;
    REG_DISPCNT_SUB &= ~DISPLAY_SPR_WIN_ON;
}

#endif
