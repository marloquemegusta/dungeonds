#include "room_kit.h"
#include "room_pool.h"
#include "strip_kit.h"
#include <stdio.h>
#include <string.h>

// File layout (little endian, blocks padded to 4 bytes): see RoomTiles in tools/bake_cathedral_kit.py.
typedef struct {
    uint32_t magic;
    uint16_t version, flags, base_tiles, n_tiles, n_stamps, n_map, n_foot, n_depth, n_pal, reserved;
} RmkHeader;                                   // 24 bytes

typedef struct {
    uint8_t w, h, phase_col, phase_row, foot_anchor_y, foot_value, piece_id, zero;
    uint16_t map_off, foot_off, num_foot, depth_off, num_depth, zero2;
} RmkStamp;                                    // 20 bytes

_Static_assert(sizeof(RmkHeader) == 24 && sizeof(RmkStamp) == 20, "RMK1 records");
_Static_assert(sizeof(StripFootprintRun) == 3 && sizeof(StripDepthRun) == 6, "RMK1 runs");

static inline uint32_t pad4(uint32_t n) { return (n + 3u) & ~3u; }

static const uint16_t *s_palette;
static int s_tiles;
static uint32_t s_bytes;

const uint16_t *room_kit_palette(void) { return s_palette; }
int room_kit_tiles(void) { return s_tiles; }
uint32_t room_kit_bytes(void) { return s_bytes; }

int room_kit_load(int room) {
    s_palette = 0;
    s_tiles = 0;
    s_bytes = 0;
    strip_set_room_stamps(0, 0, 0);
    if (room < 0 || room > 99 || !room_pool_fs_ready()) return 0;
    char path[32];
    snprintf(path, sizeof(path), "nitro:/rooms/sala_%02d.rmk", room);
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    const long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    const uint32_t mark = room_pool_mark();
    uint8_t *blob = size >= (long)sizeof(RmkHeader) ? (uint8_t *)room_pool_alloc((uint32_t)size) : 0;
    if (!blob || fread(blob, 1, (size_t)size, f) != (size_t)size) { fclose(f); room_pool_rewind(mark); return 0; }
    fclose(f);

    const RmkHeader *h = (const RmkHeader *)blob;
    const uint32_t pal_bytes = pad4((uint32_t)h->n_pal * 2u);
    const uint32_t tiles_off = (uint32_t)sizeof(RmkHeader) + (((h->flags & 1u) && h->n_pal) ? pal_bytes : 0u);
    const uint32_t stamps_off = tiles_off + (uint32_t)h->n_tiles * 64u;
    const uint32_t map_off = stamps_off + (uint32_t)h->n_stamps * (uint32_t)sizeof(RmkStamp);
    const uint32_t foot_off = map_off + pad4((uint32_t)h->n_map * 2u);
    const uint32_t depth_off = foot_off + pad4((uint32_t)h->n_foot * 3u);
    const uint32_t end_off = depth_off + pad4((uint32_t)h->n_depth * 6u);
    if (h->magic != RMK_MAGIC || h->version != 1 || end_off != (uint32_t)size ||
        h->base_tiles != g_strip_kit.num_tiles || (uint32_t)h->base_tiles + h->n_tiles > g_strip_kit.max_tiles) {
        room_pool_rewind(mark);
        return 0;
    }
    StripStamp *stamps = h->n_stamps ? (StripStamp *)room_pool_alloc((uint32_t)h->n_stamps * (uint32_t)sizeof(StripStamp)) : 0;
    if (h->n_stamps && !stamps) { room_pool_rewind(mark); return 0; }

    // Tiles: the free slots of the kit's tile store (the loader of the BG tile cache reads them on demand).
    uint8_t (*store)[64] = (uint8_t (*)[64])g_strip_kit.tiles;
    memcpy(store[h->base_tiles], blob + tiles_off, (size_t)h->n_tiles * 64u);

    const RmkStamp *rs = (const RmkStamp *)(blob + stamps_off);
    for (int i = 0; i < h->n_stamps; i++) {
        StripStamp *st = &stamps[i];
        st->w_tiles = rs[i].w;
        st->h_tiles = rs[i].h;
        st->phase_col = rs[i].phase_col;
        st->phase_row = rs[i].phase_row;
        st->foot_anchor_y_px = rs[i].foot_anchor_y;
        st->foot_value = rs[i].foot_value;
        st->piece_id = rs[i].piece_id;
        st->tiles = (const uint16_t *)(blob + map_off) + rs[i].map_off;
        st->num_foot_runs = rs[i].num_foot;
        st->foot_runs = (const StripFootprintRun *)(blob + foot_off) + rs[i].foot_off;
        st->num_depth_runs = rs[i].num_depth;
        st->depth_runs = (const StripDepthRun *)(blob + depth_off) + rs[i].depth_off;
    }
    if ((h->flags & 1u) && h->n_pal) s_palette = (const uint16_t *)(blob + sizeof(RmkHeader));
    s_tiles = h->n_tiles;
    s_bytes = (uint32_t)size;
    strip_set_room_stamps(stamps, h->n_stamps, h->n_tiles);
    return h->n_stamps;
}
