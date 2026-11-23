#include "stream_char.h"
#include "player_sprite.h"
#include "hwshadow.h"
#include <stdio.h>
#include <string.h>

// File layout (tools/generate_player_sprites_c.py, write_streamed_bin): header, records[64], frame bounds, shadow
// bounds, data. A record is { pixels (u16), runs (u16), shadow mask (u8) }, each part padded to 4 bytes.
#define SC_MAGIC 0x4E555250u          // 'PRUN'
#define SC_FRAMES (PLAYER_NUM_DIRS * PLAYER_NUM_FRAMES)
#define SC_SLOTS (NUM_CHARACTERS - CHAR_FIRST_STREAMED)

typedef struct {
    uint32_t magic, frames, max_record, spare[5];
} ScHeader;

typedef struct {
    uint32_t off;
    uint16_t pix, runs, shadow, spare;      // sizes in bytes, unpadded
} ScRec;

typedef struct {
    FILE *file;
    ScRec rec[SC_FRAMES];
    uint8_t frame_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
    uint8_t shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];
    // Where each (dir, frame) sits inside s_cache while it is loaded: element offsets from s_cache, read by the
    // character_*_ptr accessors through the character tables (pixels and runs in halfwords, shadow in bytes).
    uint32_t pix_off[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
    uint32_t run_off[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
    uint32_t shadow_off[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES];
    int8_t cache_slot[SC_FRAMES];           // cache slot holding the frame, -1 = not loaded
} ScChar;

static const char *const s_path[SC_SLOTS] = {
    "nitro:/parroco/run.bin",
    "nitro:/smonja/walk.bin",
    "nitro:/smonja/pray_stand.bin",
    "nitro:/smonja/pray_kneel.bin",
    "nitro:/smonja/stand_up.bin",
    "nitro:/arana/exvoto_walk.bin",
    "nitro:/arana/exvoto_trans.bin",
    "nitro:/arana/monaguillo_walk.bin",
    "nitro:/arana/monaguillo_trans.bin",
};

int g_parroco_run_ok = 0;
int g_smonja_ok = 0;
int g_arana_ok = 0;

static ScChar s_char[SC_SLOTS];
static uint8_t s_cache[STREAM_CACHE_SLOTS * STREAM_SLOT_BYTES] __attribute__((aligned(4)));
static int16_t s_owner[STREAM_CACHE_SLOTS];     // (slot index << 6 | frame key) in the cache slot, -1 = free
static uint32_t s_used[STREAM_CACHE_SLOTS];     // last use (s_clock), for the LRU replacement
static uint32_t s_clock;

static inline uint32_t pad4(uint32_t n) { return (n + 3u) & ~3u; }

static int load_one(int i) {
    ScChar *c = &s_char[i];
    c->file = fopen(s_path[i], "rb");
    if (!c->file) return 0;
    ScHeader h;
    if (fread(&h, 1, sizeof(h), c->file) != sizeof(h) || h.magic != SC_MAGIC || h.frames != SC_FRAMES ||
        h.max_record > STREAM_SLOT_BYTES ||
        fread(c->rec, 1, sizeof(c->rec), c->file) != sizeof(c->rec) ||
        fread(c->frame_bounds, 1, sizeof(c->frame_bounds), c->file) != sizeof(c->frame_bounds) ||
        fread(c->shadow_bounds, 1, sizeof(c->shadow_bounds), c->file) != sizeof(c->shadow_bounds)) {
        fclose(c->file);
        c->file = NULL;
        return 0;
    }
    memset(c->cache_slot, -1, sizeof(c->cache_slot));
    const int id = CHAR_FIRST_STREAMED + i;
    g_character_frames[id] = (const uint16_t *)s_cache;
    g_character_frame_offsets[id] = (const uint32_t (*)[PLAYER_NUM_FRAMES])c->pix_off;
    g_character_frame_bounds[id] = (const uint8_t (*)[PLAYER_NUM_FRAMES][4])c->frame_bounds;
    g_character_runs[id] = (const uint16_t *)s_cache;
    g_character_run_offsets[id] = (const uint32_t (*)[PLAYER_NUM_FRAMES])c->run_off;
    g_character_shadow_masks[id] = s_cache;
    g_character_shadow_offsets[id] = (const uint32_t (*)[PLAYER_NUM_FRAMES])c->shadow_off;
    g_character_shadow_bounds[id] = (const uint8_t (*)[PLAYER_NUM_FRAMES][4])c->shadow_bounds;
    return 1;
}

void stream_char_init(void) {
    memset(s_owner, -1, sizeof(s_owner));
    int ok[SC_SLOTS];
    for (int i = 0; i < SC_SLOTS; i++) ok[i] = load_one(i);
    g_parroco_run_ok = ok[CHAR_EXVOTO_PARROCO_RUN - CHAR_FIRST_STREAMED];
    g_smonja_ok = 1;
    for (int id = CHAR_SMONJA_WALK; id <= CHAR_SMONJA_STAND_UP; id++) g_smonja_ok &= ok[id - CHAR_FIRST_STREAMED];
    g_arana_ok = 1;
    for (int id = CHAR_EXVOTO_ARANA_WALK; id <= CHAR_MONAGUILLO_ARANA_TRANS; id++) g_arana_ok &= ok[id - CHAR_FIRST_STREAMED];
}

void stream_char_ensure(int char_id, int dir, int frame) {
    ScChar *c = &s_char[char_id - CHAR_FIRST_STREAMED];
    if (!c->file) return;
    const int key = ((dir & 7) << 3) | (frame & 7);
    s_clock++;
    int slot = c->cache_slot[key];
    if (slot >= 0) {
        s_used[slot] = s_clock;
        return;
    }
    // Miss: a free slot, else the least recently used one.
    slot = 0;
    for (int i = 0; i < STREAM_CACHE_SLOTS; i++) {
        if (s_owner[i] < 0) { slot = i; break; }
        if (s_used[i] < s_used[slot]) slot = i;
    }
    if (s_owner[slot] >= 0) {
        const int o = s_owner[slot];
        ScChar *oc = &s_char[o >> 6];
        oc->cache_slot[o & 63] = -1;
#if HW_SHADOWS
        // The hardware shadows cache their OBJ tiles keyed by the mask's address: this address is about to hold
        // another frame, so its tiles must be rebuilt instead of reused (stale tiles = wrong or missing shadow).
        hwshadow_invalidate(s_cache + oc->shadow_off[(o >> 3) & 7][o & 7]);
#endif
    }
    const ScRec *r = &c->rec[key];
    const uint32_t pix_n = pad4(r->pix), runs_n = pad4(r->runs), sh_n = pad4(r->shadow);
    uint8_t *base = s_cache + slot * STREAM_SLOT_BYTES;
    const uint32_t cache_off = (uint32_t)(base - s_cache);
    c->pix_off[dir & 7][frame & 7] = cache_off >> 1;
    c->run_off[dir & 7][frame & 7] = (cache_off + pix_n) >> 1;
    c->shadow_off[dir & 7][frame & 7] = cache_off + pix_n + runs_n;
    const uint32_t total = pix_n + runs_n + sh_n;
    if (total > 0 && total <= STREAM_SLOT_BYTES && fseek(c->file, (long)r->off, SEEK_SET) == 0)
        fread(base, 1, total, c->file);
    c->cache_slot[key] = (int8_t)slot;
    s_owner[slot] = (int16_t)(((char_id - CHAR_FIRST_STREAMED) << 6) | key);
    s_used[slot] = s_clock;
}
