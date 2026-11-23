#include "campanero_sprite.h"
#include "campanero_sprite_dims.h"
#include "hwshadow.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
    uint8_t  bounds[4];
    uint8_t  sbounds[4];
    uint32_t offset;
    uint16_t pix_hw, runs_hw, mask_bytes, pad;
    uint32_t pad2;                  // el registro del bin mide 24 bytes
} CampRec;

static FILE *s_f;
static int s_tried;
static CampRec s_tab[CAMP_NUM_RECORDS] __attribute__((aligned(4)));
static uint8_t s_pix[CAMP_PIX_MAX_BYTES] __attribute__((aligned(4)));
static uint8_t s_runs[CAMP_RUNS_MAX_BYTES] __attribute__((aligned(4)));
static uint8_t s_mask[CAMP_MASK_MAX_BYTES] __attribute__((aligned(4)));
static int s_cur = -1;
#if CAMP_PRELOAD
static uint8_t *s_blob;             // prueba: el bin entero en RAM al abrirlo (sin lecturas de la ROM durante el combate)
static uint32_t s_blob_len;
static void rd(void *dst, uint32_t off, uint32_t n) {
    if (s_blob) { if (off + n <= s_blob_len) memcpy(dst, s_blob + off, n); return; }
    fseek(s_f, (long)off, SEEK_SET); fread(dst, 1, n, s_f);
}
#else
static void rd(void *dst, uint32_t off, uint32_t n) { fseek(s_f, (long)off, SEEK_SET); fread(dst, 1, n, s_f); }
#endif

_Static_assert(sizeof(CampRec) == 24, "CampRec = registro de campanero.bin");

static int open_bin(void) {
    if (s_f) return 1;
    if (s_tried) return 0;
    s_tried = 1;
    FILE *f = fopen("nitro:/campanero/campanero.bin", "rb");
    if (!f) return 0;
    uint32_t head[2];
    if (fread(head, 4, 2, f) != 2 || head[0] != 0x504D4143u || head[1] != CAMP_NUM_RECORDS ||
        fread(s_tab, sizeof(CampRec), CAMP_NUM_RECORDS, f) != CAMP_NUM_RECORDS) {
        fclose(f);
        return 0;
    }
    s_f = f;
#if CAMP_PRELOAD
    fseek(f, 0, SEEK_END);
    s_blob_len = (uint32_t)ftell(f);
    s_blob = (uint8_t *)malloc(s_blob_len);
    if (s_blob) { fseek(f, 0, SEEK_SET); if (fread(s_blob, 1, s_blob_len, f) != s_blob_len) { free(s_blob); s_blob = NULL; } }
#endif
    return 1;
}

void campanero_sprite_close(void) {
    if (s_f) { fclose(s_f); s_f = NULL; }
#if CAMP_PRELOAD
    free(s_blob); s_blob = NULL;
#endif
    s_tried = 0;
    s_cur = -1;
#if HW_SHADOWS
    hwshadow_invalidate(s_mask);
#endif
}

int campanero_sprite_get(int clip, int dir, int frame, CampSprite *out) {
    if (clip < 0 || clip >= CAMP_NUM_CLIPS || dir < 0 || dir > 7 || frame < 0 || frame > 7) return 0;
    if (!open_bin()) return 0;
    const int idx = (clip * 8 + dir) * 8 + frame;
    const CampRec *r = &s_tab[idx];
    if (idx != s_cur) {
        uint32_t off = r->offset;
        const uint32_t pix_b = (uint32_t)r->pix_hw * 2u, runs_b = (uint32_t)r->runs_hw * 2u;
        if (pix_b) rd(s_pix, off, pix_b);
        off = (off + pix_b + 3u) & ~3u;
        if (runs_b) rd(s_runs, off, runs_b);
        off = (off + runs_b + 3u) & ~3u;
        if (r->mask_bytes) rd(s_mask, off, r->mask_bytes);
#if HW_SHADOWS
        hwshadow_invalidate(s_mask);
#endif
        s_cur = idx;
    }
    out->bounds = r->bounds;
    out->pix = (const uint16_t *)s_pix;
    out->runs = (const uint16_t *)s_runs;
    out->sbounds = r->sbounds;
    out->mask = s_mask;
    return 1;
}
