#include "campanero_sprite.h"
#include "campanero_sprite_dims.h"
#include "room_pool.h"
#include "chars_pool.h"
#include "hwshadow.h"
#include <stdio.h>
#include <string.h>
#if CAMP_LZ_BODY
#include <nds.h>        // decompress(..., LZ77): BIOS LZ77 a memoria principal
#endif

// CAMP_LZ_BODY (campanero_sprite.h, 0 por defecto): los pixeles de los clips que el generador comprimio (--lz) se guardan LZ77
// (formato BIOS) y se descomprimen al cambiar de fotograma a un buffer de CAMP_PIX_MAX_BYTES. Cada registro lleva su
// bandera, asi que la eleccion es por clip. Con la flag a 0 el bin tiene que estar sin comprimir (CAMP_BIN_HAS_LZ = 0).
#if !CAMP_LZ_BODY && CAMP_BIN_HAS_LZ
#error "campanero.bin lleva clips comprimidos: compilar con CAMP_LZ_BODY=1 o regenerar sin --lz"
#endif

typedef struct {
    uint8_t  bounds[4];
    uint8_t  sbounds[4];
    uint32_t offset;
    uint16_t pix_hw, runs_hw, mask_bytes, flags;
    uint32_t lz_bytes;              // con CAMP_REC_LZ: bytes de los pixeles comprimidos en el bin (pix_hw es el tamano descomprimido)
} CampRec;

#define CAMP_REC_LZ 1u

_Static_assert(sizeof(CampRec) == 24, "CampRec = registro de campanero.bin");

#define CAMP_MAGIC 0x504D4143u

// Estado de la sala: ST_NONE (sin cargar), ST_BLOB (todo el bin en el deposito de sala) o ST_STREAM (respaldo: tabla y
// una cache de CAMP_SLOTS fotogramas en el deposito, rellenada desde el cartucho). La cache es de mapeo directo por
// numero de fotograma: cada hueco tiene punteros propios y estables, asi la cache de sombras por hardware (clave: puntero
// de la mascara) sigue acertando como en ST_BLOB y solo se invalida el hueco que cambia de fotograma.
enum { ST_NONE = 0, ST_BLOB, ST_STREAM, ST_FAILED };
static int s_camp_state;
static FILE *s_f;
static const CampRec *s_tab;        // en el bin cargado (ST_BLOB) o en el deposito (ST_STREAM)
static const uint8_t *s_blob;
#define CAMP_SLOTS 8
typedef struct { uint8_t *pix, *runs, *mask; int tag; } CampSlot;
static CampSlot s_slot[CAMP_SLOTS];
#if CAMP_LZ_BODY
static uint8_t *s_lzout;            // pixeles descomprimidos del fotograma comprimido en uso (ST_BLOB y ST_STREAM)
static uint8_t *s_lzin;             // solo ST_STREAM: bytes comprimidos leidos del cartucho
static int s_lz_cur = -1;
#endif

static void close_file(void) {
    if (s_f) { fclose(s_f); s_f = NULL; }
}

void campanero_sprite_unload(void) {
    close_file();
    s_camp_state = ST_NONE;
    s_tab = NULL;
    s_blob = NULL;
    memset(s_slot, 0, sizeof(s_slot));
#if CAMP_LZ_BODY
    s_lzout = s_lzin = NULL;
    s_lz_cur = -1;
#endif
}

int campanero_sprite_loaded(void) { return s_camp_state == ST_BLOB || s_camp_state == ST_STREAM; }
int campanero_sprite_is_blob(void) { return s_camp_state == ST_BLOB; }

static int load_stream(FILE *f) {
    // Respaldo: no cabe el bin entero. Tabla + cache de fotogramas desde el deposito.
    const uint32_t mark = room_pool_mark();
    CampRec *tab = (CampRec *)room_pool_alloc(sizeof(CampRec) * CAMP_NUM_RECORDS);
    CampSlot slot[CAMP_SLOTS];
    int slots_ok = 1;
    for (int i = 0; i < CAMP_SLOTS; i++) {
        slot[i].pix = (uint8_t *)room_pool_alloc(CAMP_PIX_MAX_BYTES);
        slot[i].runs = (uint8_t *)room_pool_alloc(CAMP_RUNS_MAX_BYTES);
        slot[i].mask = (uint8_t *)room_pool_alloc(CAMP_MASK_MAX_BYTES);
        slot[i].tag = -1;
        if (!slot[i].pix || !slot[i].runs || !slot[i].mask) slots_ok = 0;
    }
    uint32_t head[2];
#if CAMP_LZ_BODY
    uint8_t *lzin = CAMP_BIN_HAS_LZ ? (uint8_t *)room_pool_alloc(CAMP_LZ_MAX_BYTES) : (uint8_t *)slot[0].pix;
    if (tab && slots_ok && lzin) {
#else
    if (tab && slots_ok) {
#endif
        fseek(f, 0, SEEK_SET);
        if (fread(head, 4, 2, f) == 2 && head[0] == CAMP_MAGIC && head[1] == CAMP_NUM_RECORDS &&
            fread(tab, sizeof(CampRec), CAMP_NUM_RECORDS, f) == CAMP_NUM_RECORDS) {
            s_f = f;
            s_tab = tab;
            memcpy(s_slot, slot, sizeof(s_slot));
#if CAMP_LZ_BODY
            s_lzin = lzin;
#endif
            s_camp_state = ST_STREAM;
            return 1;
        }
    }
    room_pool_rewind(mark);
    fclose(f);
    s_camp_state = ST_FAILED;
    return 0;
}

int campanero_sprite_load(void) {
    if (campanero_sprite_loaded()) return 1;
    campanero_sprite_unload();
    if (!room_pool_fs_ready()) { s_camp_state = ST_FAILED; return 0; }
    FILE *f = fopen("nitro:/campanero/campanero.bin", "rb");
    if (!f) { s_camp_state = ST_FAILED; return 0; }
    const uint32_t mark = room_pool_mark();
    uint8_t *blob = (uint8_t *)room_pool_alloc(CAMP_FILE_BYTES);
#if CAMP_LZ_BODY
    uint8_t *lzout = (blob && CAMP_BIN_HAS_LZ) ? (uint8_t *)room_pool_alloc(CAMP_PIX_MAX_BYTES) : blob;
    if (!lzout) blob = NULL;
#endif
    if (blob) {
        fseek(f, 0, SEEK_SET);
        const uint32_t *head = (const uint32_t *)blob;
        if (fread(blob, 1, CAMP_FILE_BYTES, f) == CAMP_FILE_BYTES && head[0] == CAMP_MAGIC && head[1] == CAMP_NUM_RECORDS) {
            fclose(f);
#if CAMP_LZ_BODY
            s_lzout = lzout;
#endif
            s_blob = blob;
            s_tab = (const CampRec *)(blob + 8);
            s_camp_state = ST_BLOB;
            return 1;
        }
        // Lectura corta: no deberia pasar; se libera el hueco y se cae al respaldo.
        room_pool_rewind(mark);
    }
    return load_stream(f);
}

int campanero_sprite_get(int clip, int dir, int frame, CampSprite *out) {
    if (clip < 0 || clip >= CAMP_NUM_CLIPS || dir < 0 || dir > 7 || frame < 0 || frame > 7) return 0;
    if (!campanero_sprite_loaded()) {
        // Red de seguridad: la sala no lo preparo (variante sin encuentros). Cuenta como fallo.
        if (s_camp_state == ST_FAILED) return 0;
        g_pool_misses++;
        if (!campanero_sprite_load()) return 0;
    }
    const int idx = (clip * 8 + dir) * 8 + frame;
    const CampRec *r = &s_tab[idx];
    if (s_camp_state == ST_BLOB) {
        // Todo en memoria: los punteros no cambian entre fotogramas, la cache de sombras sigue valida.
        const uint32_t pix_b = (r->flags & CAMP_REC_LZ) ? r->lz_bytes : (uint32_t)r->pix_hw * 2u;
        const uint32_t runs_b = (uint32_t)r->runs_hw * 2u;
        const uint32_t off_runs = (r->offset + pix_b + 3u) & ~3u;
        const uint32_t off_mask = (off_runs + runs_b + 3u) & ~3u;
        out->bounds = r->bounds;
#if CAMP_LZ_BODY
        if (r->flags & CAMP_REC_LZ) {
            // Clip comprimido: se descomprime solo al cambiar de fotograma (el buffer es unico).
            if (idx != s_lz_cur) { decompress(s_blob + r->offset, s_lzout, LZ77); s_lz_cur = idx; }
            out->pix = (const uint16_t *)s_lzout;
        } else
#endif
        out->pix = (const uint16_t *)(s_blob + r->offset);
        out->runs = (const uint16_t *)(s_blob + off_runs);
        out->sbounds = r->sbounds;
        out->mask = s_blob + off_mask;
        return 1;
    }
    CampSlot *sl = &s_slot[frame];
    if (idx != sl->tag) {
        uint32_t off = r->offset;
        const uint32_t pix_b = (r->flags & CAMP_REC_LZ) ? r->lz_bytes : (uint32_t)r->pix_hw * 2u;
        const uint32_t runs_b = (uint32_t)r->runs_hw * 2u;
        fseek(s_f, (long)off, SEEK_SET);
#if CAMP_LZ_BODY
        if (r->flags & CAMP_REC_LZ) {
            fread(s_lzin, 1, pix_b, s_f);
            decompress(s_lzin, sl->pix, LZ77);
        } else
#endif
        if (pix_b) fread(sl->pix, 1, pix_b, s_f);
        off = (off + pix_b + 3u) & ~3u;
        fseek(s_f, (long)off, SEEK_SET);
        if (runs_b) fread(sl->runs, 1, runs_b, s_f);
        off = (off + runs_b + 3u) & ~3u;
        if (r->mask_bytes) {
            fseek(s_f, (long)off, SEEK_SET);
            fread(sl->mask, 1, r->mask_bytes, s_f);
        }
#if HW_SHADOWS
        hwshadow_invalidate(sl->mask);
#endif
        sl->tag = idx;
    }
    out->bounds = r->bounds;
    out->pix = (const uint16_t *)sl->pix;
    out->runs = (const uint16_t *)sl->runs;
    out->sbounds = r->sbounds;
    out->mask = sl->mask;
    return 1;
}
