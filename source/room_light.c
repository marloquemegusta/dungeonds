// Luz prerenderizada por sala: carga el paquete nitro:/arpg_luz/<luz>.bin en la pantalla de carga de la sala.
// Formato en TECHNICAL.md 5.7 y tools/arpg_light_pack.py (cabecera LMOD de la demo de ciclo del dia + trailer LEXT).
// Memoria: un solo paquete residente. Lo que ocupa RAM es el kit (paleta, tiles, suelo, muros, piezas: ~85 KB) y los
// sprites del heroe (arrays de source/player_sprite.c, que ya estaban en RAM); los clips de enemigo, los remates y los
// props se quedan en el cartucho y se leen por indice (el indice son ~3 KB).
#include "room_light.h"
#include "punch.h"
#include "strip_kit.h"
#include "hwshadow.h"
#include "room_pool.h"
#include <stdio.h>
#include <string.h>
#ifdef ARM9
#include <nds.h>
#endif

#define PACK_MAGIC 0x444F4D4Cu    // 'LMOD'
#define LEXT_MAGIC 0x5458454Cu    // 'LEXT'
#define MAX_TILES 1024        // tile store (BG1 limit): the pack's kit tiles + the free slots room_kit_load() fills with the room's own
#define MAX_STAMPS 64
#define MAX_STAMP_TILES 7424   // pack maximum 7248 (tools/room_light_slots.py)
#define MAX_ENTRIES 96
#define END_TILES 608             // 32 x 19
#define HOLE_TILES 99             // 3 x 33

typedef struct {
    uint32_t magic;
    uint16_t num_tiles;
    uint16_t stamp_count;
    uint32_t stamp_tiles;
    uint32_t slot_count;
} PackHead;

typedef struct {
    uint8_t w_tiles, h_tiles, foot_anchor_y_px, piece_id, phase_col, phase_row, pad0, pad1;
} StampMeta;

typedef struct {
    char name[24];
    uint32_t kind;
    uint32_t off;
    uint32_t len;
} Entry;

volatile RoomLightState g_room_light = { ROOM_LIGHT_NONE, 0, 0, 0, 0, 0, 0, 0 };

// Orden de las luces = orden de tools/arpg_light_rooms.json.
static const char *const k_light_ids[ROOM_LIGHT_COUNT] = {
    "nave_100", "nave_85", "nave_70", "nave_55", "galerias", "claustros",
    "enfermeria", "osario", "capillas", "prisionero", "monjarana", "cripta"
};
// Sala (ENC_ROOM_*, 0..15) -> indice de luz.
static const uint8_t k_room_light[16] = { 0, 1, 2, 3, 4, 4, 5, 5, 6, 7, 8, 8, 9, 8, 10, 11 };

// Kit residente (sustituye al de dia mientras hay luz de sala).
static uint16_t s_pal[256] __attribute__((aligned(4)));
static uint8_t s_tiles[MAX_TILES][64] __attribute__((aligned(4)));
static uint16_t s_floor[16 * 64] __attribute__((aligned(4)));
static uint16_t s_end[2][END_TILES] __attribute__((aligned(4)));
static uint16_t s_hole[HOLE_TILES] __attribute__((aligned(4)));
static uint16_t s_stamp_tiles[MAX_STAMP_TILES] __attribute__((aligned(4)));
static StripStamp s_stamps[MAX_STAMPS];

static Entry s_ent[MAX_ENTRIES];
static int s_n_ent;
static int s_light = -1;
static int s_day_saved;
static StripKit s_day_kit;

static void path_of(int light, char *out, size_t n) {
    snprintf(out, n, "nitro:/arpg_luz/%s.bin", k_light_ids[light]);
}

const char *room_light_id(void) {
    return s_light >= 0 ? k_light_ids[s_light] : "dia";
}

// Los nombres del trailer son 24 bytes: tools/arpg_light_pack.py abrevia exvoto_super_monja -> smonja si pasan de 23.
static void entry_name(const char *name, char *out) {
    char tmp[48];
    snprintf(tmp, sizeof(tmp), "%s", name);
    if (strlen(tmp) > 23 && strncmp(tmp, "exvoto_super_monja", 18) == 0) snprintf(tmp, sizeof(tmp), "smonja%s", name + 18);
    memset(out, 0, 24);
    size_t l = strlen(tmp);
    memcpy(out, tmp, l > 23 ? 23 : l);
}

// Tinte de suelo de cada luz (floor_tint * floor_gain de tools/arpg_light_rooms.json, x256): el mismo que tools/arpg_light_pack.py
// aplica a los remates. Los bins de punetazo (nitro:/punch) no viajan en el paquete: se tintan al leerlos.
static const uint16_t k_light_tint[ROOM_LIGHT_COUNT][3] = {
    { 215, 230, 256 }, { 194, 207, 230 }, { 170, 182, 202 }, { 148, 159, 177 }, { 184, 162, 129 }, { 358, 326, 269 },
    { 202, 174, 133 }, { 64, 77, 115 }, { 184, 151, 107 }, { 77, 106, 83 }, { 44, 61, 40 }, { 73, 54, 46 }
};

void room_light_tint_px(uint16_t *px, uint32_t count) {
    if (s_light < 0) return;
    const uint16_t *t = k_light_tint[s_light];
    for (uint32_t i = 0; i < count; i++) {
        const uint16_t v = px[i];
        if (!(v & 0x8000)) continue;
        uint32_t r = ((uint32_t)(v & 31) * t[0] + 128) >> 8;
        uint32_t g = ((uint32_t)((v >> 5) & 31) * t[1] + 128) >> 8;
        uint32_t b = ((uint32_t)((v >> 10) & 31) * t[2] + 128) >> 8;
        if (r > 31) r = 31;
        if (g > 31) g = 31;
        if (b > 31) b = 31;
        px[i] = (uint16_t)(0x8000 | (b << 10) | (g << 5) | r);
    }
}

FILE *room_light_open(uint32_t kind, const char *name, uint32_t *len) {
    if (s_light < 0) return NULL;
    char want[24];
    entry_name(name, want);
    for (int i = 0; i < s_n_ent; i++) {
        if (s_ent[i].kind != kind || memcmp(s_ent[i].name, want, 24) != 0) continue;
        char path[48];
        path_of(s_light, path, sizeof(path));
        FILE *f = fopen(path, "rb");
        if (!f) return NULL;
        if (fseek(f, (long)s_ent[i].off, SEEK_SET) != 0) { fclose(f); return NULL; }
        if (len) *len = s_ent[i].len;
        return f;
    }
    return NULL;
}

FILE *room_light_open_clip(const char *file) {
    const char *b = strrchr(file, '/');
    b = b ? b + 1 : file;
    char name[40];
    snprintf(name, sizeof(name), "%s", b);
    char *dot = strrchr(name, '.');
    if (dot) *dot = 0;
    return room_light_open(RL_CHR1, name, NULL);
}

static const StripStamp *day_stamp_for(int i, int piece_id) {
    const StripStamp *day = s_day_kit.stamps;
    const int n = s_day_kit.num_stamps;
    if (i < n && day[i].piece_id == piece_id) return &day[i];
    if (piece_id != 0)
        for (int k = 0; k < n; k++)
            if (day[k].piece_id == piece_id) return &day[k];
    return i < n ? &day[i] : NULL;
}

// Lee `n` bytes; 0 si falla.
static int rd(FILE *f, void *dst, size_t n) {
    return n == 0 || fread(dst, 1, n, f) == n;
}

static int load_pack(int light) {
    char path[48];
    path_of(light, path, sizeof(path));
    FILE *f = fopen(path, "rb");
    if (!f) { g_room_light.err = 100; return 0; }
    g_room_light.err = 0;
    int ok = 0;
    PackHead h;
    StampMeta meta[MAX_STAMPS];
    uint32_t stamp_n = 0;
    uint16_t nt = 0;
    int n_ent = 0;
    const size_t fmap_bytes = (size_t)STRIP_W_TILES * s_day_kit.map_h_tiles * sizeof(uint16_t);

    if (!rd(f, &h, sizeof(h)) || h.magic != PACK_MAGIC) { g_room_light.err = 1; goto done; }
    if (h.num_tiles == 0 || h.num_tiles > MAX_TILES || h.stamp_count == 0 || h.stamp_count > MAX_STAMPS ||
        h.stamp_tiles > MAX_STAMP_TILES || h.slot_count != g_room_light_slot_count || fmap_bytes != sizeof(s_floor)) { g_room_light.err = 2; goto done; }
    nt = h.num_tiles;
    stamp_n = h.stamp_tiles;

    // Kit: paleta, tiles, suelo, piezas.
    if (!rd(f, s_pal, sizeof(s_pal)) || !rd(f, s_tiles, (size_t)nt * 64) || !rd(f, s_floor, fmap_bytes)) { g_room_light.err = 3; goto done; }
    if (!rd(f, meta, sizeof(StampMeta) * h.stamp_count) || !rd(f, s_stamp_tiles, stamp_n * 2)) { g_room_light.err = 4; goto done; }

    // Validacion previa de los slots (longitudes) antes de tocar los sprites residentes.
    {
        const long slots_at = ftell(f);
        for (uint32_t i = 0; i < h.slot_count; i++) {
            uint32_t len;
            if (!rd(f, &len, 4) || len > g_room_light_slots[i].max_bytes) { g_room_light.err = 5; goto done; }
            if (fseek(f, (long)len, SEEK_CUR) != 0) { g_room_light.err = 6; goto done; }
        }
        // Trailer LEXT: indice y mapas de muro.
        uint32_t th[2];
        if (!rd(f, th, 8) || th[0] != LEXT_MAGIC || th[1] > MAX_ENTRIES) { g_room_light.err = 7; goto done; }
        n_ent = (int)th[1];
        for (int i = 0; i < n_ent; i++) {
            uint32_t eh[2];
            Entry *e = &s_ent[i];
            if (!rd(f, e->name, 24) || !rd(f, eh, 8)) { g_room_light.err = 8; goto done; }
            e->kind = eh[0];
            e->len = eh[1];
            e->off = (uint32_t)ftell(f);
            if (e->kind == RL_MAP) {
                uint16_t wh[2];
                if (!rd(f, wh, 4)) { g_room_light.err = 9; goto done; }
                const uint32_t cnt = (uint32_t)wh[0] * wh[1];
                uint16_t *dst = 0;
                if (memcmp(e->name, "end0", 5) == 0 && cnt == END_TILES) dst = s_end[0];
                else if (memcmp(e->name, "end1", 5) == 0 && cnt == END_TILES) dst = s_end[1];
                else if (memcmp(e->name, "hole", 5) == 0 && cnt == HOLE_TILES) dst = s_hole;
                if (!dst || !rd(f, dst, cnt * 2)) { g_room_light.err = 10; goto done; }
                if (fseek(f, (long)(e->off + e->len + ((4u - (e->len & 3u)) & 3u)), SEEK_SET) != 0) { g_room_light.err = 11; goto done; }
            } else if (fseek(f, (long)(e->len + ((4u - (e->len & 3u)) & 3u)), SEEK_CUR) != 0) {
                { g_room_light.err = 12; goto done; }
            }
        }
        // Sprites del heroe y tablas de enemigos, ya validados.
        if (fseek(f, slots_at, SEEK_SET) != 0) { g_room_light.err = 13; goto done; }
        for (uint32_t i = 0; i < h.slot_count; i++) {
            uint32_t len;
            if (!rd(f, &len, 4) || !rd(f, g_room_light_slots[i].dst, len)) { g_room_light.err = 14; goto done; }
        }
    }
    ok = 1;
done:
    fclose(f);
    if (!ok) return 0;

    // Publica el kit nuevo: piezas con la huella y la profundidad del kit de dia.
    uint32_t off = 0;
    for (uint32_t i = 0; i < h.stamp_count; i++) {
        const StripStamp *d = day_stamp_for((int)i, meta[i].piece_id);
        StripStamp *s = &s_stamps[i];
        if (d) *s = *d; else memset(s, 0, sizeof(*s));
        s->w_tiles = meta[i].w_tiles;
        s->h_tiles = meta[i].h_tiles;
        s->foot_anchor_y_px = meta[i].foot_anchor_y_px;
        s->piece_id = meta[i].piece_id;
        s->phase_col = meta[i].phase_col;
        s->phase_row = meta[i].phase_row;
        s->tiles = &s_stamp_tiles[off];
        off += (uint32_t)s->w_tiles * s->h_tiles;
    }
    g_strip_kit = s_day_kit;
    g_strip_kit.palette = s_pal;
    g_strip_kit.tiles = (const uint8_t (*)[64])s_tiles;
    g_strip_kit.num_tiles = nt;
    g_strip_kit.max_tiles = MAX_TILES;
    g_strip_kit.floor_map = s_floor;
    g_strip_kit.end_map[0] = s_end[0];
    g_strip_kit.end_map[1] = s_end[1];
    g_strip_kit.hole_map = s_hole;
    g_strip_kit.num_stamps = (uint8_t)h.stamp_count;
    g_strip_kit.stamps = s_stamps;
    s_n_ent = n_ent;

    // Las mascaras de sombra del heroe cambian en el sitio: la cache de sombras por hardware las vuelve a leer.
    for (uint32_t i = 0; i < h.slot_count; i++) {
        const uint8_t *lo = (const uint8_t *)g_room_light_slots[i].dst;
        hwshadow_invalidate_range(lo, lo + g_room_light_slots[i].max_bytes);
    }
    return 1;
}

// Arte de los fixtures (cofre cerrado, cofre abierto, altar) iluminado con la luz de la sala: <luz>_fix.bin, formato en
// tools/arpg_light_fix.py. Se lee directo sobre los pixeles de dia de include/enc_room_gfx.h (sin buffers). Si falta o
// no es valido se queda el arte que hubiera (el de dia hasta que cargue uno).
#define FIX_MAGIC 0x5849464Cu    // 'LFIX'
static void load_fix(int light) {
    char path[48];
    snprintf(path, sizeof(path), "nitro:/arpg_luz/%s_fix.bin", k_light_ids[light]);
    FILE *f = fopen(path, "rb");
    if (!f) return;
    uint32_t h[2];
    int16_t meta[3][4];
    if (rd(f, h, 8) && h[0] == FIX_MAGIC && h[1] == 3 && rd(f, meta, sizeof(meta))) {
        uint16_t *px = enc_room_gfx_begin(meta);
        if (px) {
            int total = 0;
            for (int i = 0; i < 3; i++) total += (int)(uint16_t)meta[i][1] * (uint16_t)meta[i][2];
            rd(f, px, (size_t)total * 2);
        }
    }
    fclose(f);
}

int room_light_load(int room) {
    if (room < 0 || room >= 16) return 0;
    const int light = k_room_light[room];
    g_room_light.room = (uint8_t)room;
    if (!s_day_saved) {
        s_day_saved = 1;
        s_day_kit = g_strip_kit;
    }
    if (light != s_light && !room_pool_fs_ready()) { g_room_light.ok = 0; return 0; }
    if (light == s_light) { g_room_light.ok = 1; return 1; }   // misma luz (p. ej. reinicio tras morir): nada que leer
#ifdef ARM9
    const uint32_t t0 = cpuGetTiming();
#endif
    // Si el paquete falta o no es valido se queda lo que hubiera: el arte de dia mientras no haya cargado ninguno.
    const int ok = load_pack(light);
    if (ok) load_fix(light);
    g_room_light.ok = (uint8_t)ok;
    if (!ok) return 0;
    s_light = light;
    punch_light_changed();   // los bins de punetazo en cache estaban tintados con la luz anterior
    g_room_light.id = (uint8_t)light;
    g_room_light.entries = (uint8_t)s_n_ent;
    g_room_light.loads++;
#ifdef ARM9
    g_room_light.load_ticks = cpuGetTiming() - t0;
#endif
    return 1;
}
