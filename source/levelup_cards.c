#include "levelup_cards.h"
#include "game.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <nds.h>

#define LVC_MAGIC 0x4C44   /* indices comprimidos con LZ10 (BIOS) */

typedef struct {
    uint16_t magic;
    uint8_t frames;
    uint8_t size;
    uint16_t palette[256];
} LvcHeader;   // 516 bytes, followed by frames * size * size palette indices

typedef struct {
    uint16_t palette[256];
    uint8_t pixels[LVC_FRAMES * LVC_SIZE * LVC_SIZE];
    int loaded;
} LvcSlot;

static LvcSlot *s_slots[3];

static LvcSlot *slot_get(int slot) {
    if ((unsigned)slot >= 3u) return NULL;
    if (!s_slots[slot]) s_slots[slot] = (LvcSlot *)malloc(sizeof(LvcSlot));
    return s_slots[slot];
}

void lvcards_load(int slot, const char *art_id) {
    LvcSlot *s = slot_get(slot);
    if (!s) return;
    s->loaded = 0;
    if (!art_id) return;
    char path[64];
    snprintf(path, sizeof(path), "nitro:/levelup/%s.bin", art_id);
    FILE *f = fopen(path, "rb");
    if (!f) return;
    LvcHeader hdr;
    if (fread(&hdr, sizeof(hdr), 1, f) == 1 && hdr.magic == LVC_MAGIC && hdr.frames == LVC_FRAMES &&
        hdr.size == LVC_SIZE && fseek(f, 0, SEEK_END) == 0) {
        long total = ftell(f);
        size_t csize = total > (long)sizeof(hdr) ? (size_t)total - sizeof(hdr) : 0;
        uint32_t *tmp = csize ? (uint32_t *)malloc((csize + 3) & ~(size_t)3) : NULL;
        if (tmp && fseek(f, (long)sizeof(hdr), SEEK_SET) == 0 && fread(tmp, 1, csize, f) == csize &&
            (tmp[0] & 0xFF) == 0x10 && (tmp[0] >> 8) == sizeof(s->pixels)) {
            swiDecompressLZSSWram(tmp, s->pixels);
            memcpy(s->palette, hdr.palette, sizeof(s->palette));
            s->loaded = 1;
        }
        free(tmp);
    }
    fclose(f);
}

void lvcards_free(void) {
    for (int i = 0; i < 3; i++) {
        free(s_slots[i]);
        s_slots[i] = NULL;
    }
}

int lvcards_loaded(int slot) {
    return (unsigned)slot < 3u && s_slots[slot] && s_slots[slot]->loaded;
}

void lvcards_draw(uint16_t *buf, int slot, int x, int y, int frame, int dim) {
    if (!lvcards_loaded(slot) || !buf) return;
    const LvcSlot *s = s_slots[slot];
    uint16_t pal[256];
    for (int i = 0; i < 256; i++) {
        uint16_t c = s->palette[i];
        // Unselected cards: 3/4 brightness per channel.
        pal[i] = dim ? (uint16_t)(c - ((c >> 2) & 0x1CE7u)) : c;
    }
    const uint8_t *src = &s->pixels[(frame & (LVC_FRAMES - 1)) * LVC_SIZE * LVC_SIZE];
    for (int j = 0; j < LVC_SIZE; j++) {
        int sy = y + j;
        if ((unsigned)sy >= SCREEN_H) continue;
        dirty_row(sy, x, x + LVC_SIZE);
        uint16_t *row = &buf[sy * SCREEN_W];
        for (int i = 0; i < LVC_SIZE; i++) {
            int sx = x + i;
            if ((unsigned)sx < SCREEN_W) row[sx] = pal[src[j * LVC_SIZE + i]];
        }
    }
}
