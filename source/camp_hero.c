#include "camp_hero.h"
#include <stdio.h>
#include <string.h>

#define CHRO_MAGIC 0x4F524843u
#define CHRO_DIRS 8
#define CHRO_FRAMES 8

typedef struct {
    uint8_t bounds[4];
    uint8_t sbounds[4];
    uint32_t off;
    uint16_t pix_bytes;
    uint16_t runs_bytes;
    uint16_t mask_bytes;
    uint16_t pad;
} ChroRec;

typedef struct {
    uint32_t magic;
    uint32_t nrec;
    uint8_t anchor[8];
    ChroRec rec[CHRO_DIRS * CHRO_FRAMES];
} ChroHeader;

static int s_az = -1;                      // current light azimuth (hysteresis state)
static FILE *s_file;
static int s_file_az = -1;                 // variant of the open file / loaded header (-1 = none)
static ChroHeader s_head __attribute__((aligned(4)));
static uint8_t s_buf[CAMP_HERO_REC_MAX] __attribute__((aligned(4)));
static int s_buf_az = -1, s_buf_dir = -1, s_buf_frame = -1;   // what s_buf holds
static CampHeroFrame s_out;

// Ground-plane axis of each azimuth in (right, down) units; the y of the world is doubled to leave the 2:1 view.
static const int8_t k_axis[8][2] = { {0, 1}, {-1, 1}, {-1, 0}, {-1, -1}, {0, -1}, {1, -1}, {1, 0}, {1, 1} };

void camp_hero_reset(void) { s_az = -1; }

int camp_hero_azimuth(int x, int y) {
    const int vx = x - CAMP_FIRE_X, vy = 2 * (y - CAMP_FIRE_Y);
    if (vx == 0 && vy == 0) return s_az < 0 ? 0 : s_az;
    if (s_az >= 0) {
        // Stay in the current sector while the hero is within atan(1/2) = 26.6 degrees of its axis (22.5 + 4 of margin):
        // angle <= 26.6 <=> 5 * dot^2 >= 4 * |v|^2 * |axis|^2, with dot > 0.
        const int ax = k_axis[s_az][0], ay = k_axis[s_az][1];
        const int dot = vx * ax + vy * ay;
        const int v2 = vx * vx + vy * vy, a2 = ax * ax + ay * ay;
        if (dot > 0 && 5 * dot * dot >= 4 * v2 * a2) return s_az;
    }
    // Plain 45-degree sectors: vertical when |vy| > 2.414 |vx|, horizontal when |vy| < 0.414 |vx|, else diagonal.
    const int absx = vx < 0 ? -vx : vx, absy = vy < 0 ? -vy : vy;
    int az;
    if (absy * 5 > absx * 12) az = vy > 0 ? 0 : 4;
    else if (absy * 12 < absx * 5) az = vx < 0 ? 2 : 6;
    else if (vy > 0) az = vx < 0 ? 1 : 7;
    else az = vx < 0 ? 3 : 5;
    s_az = az;
    return az;
}

void camp_hero_release(void) {
    if (s_file) { fclose(s_file); s_file = NULL; }
    s_file_az = -1;
    s_buf_az = -1;
}

static int load_variant(int az) {
    if (s_file_az == az && s_file) return 1;
    camp_hero_release();
    char path[40];
    snprintf(path, sizeof(path), "nitro:/camp/hero_a%d.bin", az);
    s_file = fopen(path, "rb");
    if (!s_file) return 0;
    if (fread(&s_head, 1, sizeof(s_head), s_file) != sizeof(s_head) ||
        s_head.magic != CHRO_MAGIC || s_head.nrec != CHRO_DIRS * CHRO_FRAMES) {
        camp_hero_release();
        return 0;
    }
    s_file_az = az;
    return 1;
}

const CampHeroFrame *camp_hero_frame(int x, int y, int dir, int frame) {
    const int az = camp_hero_azimuth(x, y);
    if ((unsigned)dir >= CHRO_DIRS || (unsigned)frame >= CHRO_FRAMES) return NULL;
    if (!load_variant(az)) return NULL;
    const ChroRec *r = &s_head.rec[dir * CHRO_FRAMES + frame];
    if (s_buf_az != az || s_buf_dir != dir || s_buf_frame != frame) {
        const uint32_t pr = ((uint32_t)r->pix_bytes + r->runs_bytes + 3u) & ~3u;
        const uint32_t total = pr + (((uint32_t)r->mask_bytes + 3u) & ~3u);
        s_buf_az = -1;
        if (total > sizeof(s_buf) || fseek(s_file, (long)r->off, SEEK_SET) != 0) return NULL;
        if (total && fread(s_buf, 1, total, s_file) != total) return NULL;
        s_buf_az = az; s_buf_dir = dir; s_buf_frame = frame;
    }
    const uint32_t pr = ((uint32_t)r->pix_bytes + r->runs_bytes + 3u) & ~3u;
    s_out.pix = (const uint16_t *)s_buf;
    s_out.runs = (const uint16_t *)(s_buf + r->pix_bytes);
    s_out.bounds = r->bounds;
    s_out.mask = s_buf + pr;
    s_out.sbounds = r->sbounds;
    s_out.anchor = s_head.anchor[dir];
    return &s_out;
}
