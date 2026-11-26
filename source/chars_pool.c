#include "chars_pool.h"
#include "room_pool.h"
#include "room_light.h"
#include "campanero_sprite.h"
#include "gameplay.h"
#include <stdio.h>
#include <string.h>

volatile uint32_t g_pool_misses;
uint32_t g_chars_loaded;
static uint32_t s_failed;       // groups that did not fit: not retried until the next room (no file reads every frame)

const int8_t g_char_group[NUM_CHARACTERS] = {
    [CHAR_HERO] = -1,
    [CHAR_CHARGER] = CG_CHARGER,
    [CHAR_OJO] = CG_OJO,
    [CHAR_EXVOTO] = CG_EXVOTO,
    [CHAR_EXVOTO_PRAY_STAND] = CG_EXVOTO,
    [CHAR_EXVOTO_PRAY_KNEEL] = CG_EXVOTO,
    [CHAR_EXVOTO_STAND_UP] = CG_EXVOTO,
    [CHAR_ABANDERADO] = CG_ABANDERADO,
    [CHAR_MONAGUILLO] = CG_MONAGUILLO,
    [CHAR_HERO_CROUCH_WALK] = -1,
    [CHAR_EXVOTO_BEBE] = CG_EXVOTO,
    [CHAR_CAMPANERO] = -1,
    [CHAR_EXVOTO_PARROCO_RUN] = CG_PARROCO,
    [CHAR_SMONJA_WALK] = CG_SMONJA,
    [CHAR_SMONJA_PRAY_STAND] = CG_SMONJA,
    [CHAR_SMONJA_PRAY_KNEEL] = CG_SMONJA,
    [CHAR_SMONJA_STAND_UP] = CG_SMONJA,
    [CHAR_EXVOTO_ARANA_WALK] = CG_ARANA_EXVOTO,
    [CHAR_EXVOTO_ARANA_TRANS] = CG_ARANA_EXVOTO,
    [CHAR_MONAGUILLO_ARANA_WALK] = CG_ARANA_MONA,
    [CHAR_MONAGUILLO_ARANA_TRANS] = CG_ARANA_MONA,
};

// Bin of a clip: "CHR1", frames/runs/mask byte counts, then the three blocks each padded to 4 bytes.
#define CHR_MAGIC 0x31524843u
static inline uint32_t pad4(uint32_t n) { return (n + 3u) & ~3u; }

static void clip_publish(const CharClipDef *c, const uint16_t *fr, const uint16_t *rn, const uint8_t *mk) {
    *c->frames = fr;
    *c->runs = rn;
    if (c->masks) *c->masks = mk;
    if (c->char_id >= 0) {
        g_character_frames[c->char_id] = fr;
        g_character_runs[c->char_id] = rn;
        g_character_shadow_masks[c->char_id] = mk;
    }
}

// The clip of the room's light pack when it has one (room_light.h), else the day clip of nitrofiles/chars.
static FILE *clip_open(const CharClipDef *c) {
    FILE *f = room_light_open_clip(c->file);
    if (f) return f;
    char path[48];
    snprintf(path, sizeof(path), "nitro:/%s", c->file);
    return fopen(path, "rb");
}

static int clip_load(const CharClipDef *c) {
    if (!room_pool_fs_ready()) return 0;
    FILE *f = clip_open(c);
    if (!f) return 0;
    uint32_t head[4];
    if (fread(head, 4, 4, f) != 4 || head[0] != CHR_MAGIC) { fclose(f); return 0; }
    const uint32_t fr_b = pad4(head[1]), rn_b = pad4(head[2]), mk_b = pad4(head[3]);
    uint8_t *p = (uint8_t *)room_pool_alloc(fr_b + rn_b + mk_b);
    int ok = p && fread(p, 1, fr_b + rn_b + mk_b, f) == fr_b + rn_b + mk_b;
    fclose(f);
    if (!ok) return 0;
    clip_publish(c, (const uint16_t *)p, (const uint16_t *)(p + fr_b), p + fr_b + rn_b);
    return 1;
}

static void group_forget(int group) {
    for (int i = 0; i < g_char_clip_count; i++)
        if (g_char_clips[i].group == group) clip_publish(&g_char_clips[i], NULL, NULL, NULL);
    g_chars_loaded &= ~(1u << group);
}

int chars_load_group(int group) {
    if (group < 0 || group >= CG_COUNT) return 1;
    if ((g_chars_loaded >> group) & 1u) return 1;
    const uint32_t mark = room_pool_mark();
    for (int i = 0; i < g_char_clip_count; i++) {
        if (g_char_clips[i].group != group) continue;
        if (!clip_load(&g_char_clips[i])) {
            group_forget(group);
            room_pool_rewind(mark);      // the group is the last thing in the pool: nothing else moves
            return 0;
        }
    }
    g_chars_loaded |= 1u << group;
    return 1;
}

int chars_load_type(int enemy_type) {
    return chars_load_group(g_char_group[enemy_type_char_id((EnemyType)enemy_type)]);
}

void chars_unload_all(void) {
    for (int g = 0; g < CG_COUNT; g++) group_forget(g);
    g_chars_loaded = 0;
    s_failed = 0;
}

int chars_demand(int char_id) {
    const int g = g_char_group[char_id];
    if ((s_failed >> g) & 1u) return 0;
    g_pool_misses++;
    if (chars_load_group(g)) return 1;
    s_failed |= 1u << g;
    return 0;
}

uint32_t chars_group_bytes(int group) {
    uint32_t total = 0;
    for (int i = 0; i < g_char_clip_count; i++) {
        if (g_char_clips[i].group != group) continue;
        FILE *f = clip_open(&g_char_clips[i]);
        if (!f) continue;
        uint32_t head[4];
        if (fread(head, 4, 4, f) == 4 && head[0] == CHR_MAGIC) total += pad4(head[1]) + pad4(head[2]) + pad4(head[3]);
        fclose(f);
    }
    return total;
}

void room_art_prepare(uint32_t group_mask, int campanero) {
    campanero_sprite_unload();
    chars_unload_all();
    room_pool_reset();
    for (int g = 0; g < CG_COUNT; g++)
        if ((group_mask >> g) & 1u) chars_load_group(g);
    if (campanero) campanero_sprite_load();
}
