#include "arpg_progress.h"
#include "arpg.h"
#include "arpg_quest.h"
#include "arpg_log.h"
#include <fat.h>
#include <stdio.h>
#include <string.h>

ArpgProgress g_arpg;

#define ARPG_SAVE_VERSION 8      // v8: quest bits in the old reserved bytes (a v7 file loads as is, with no penance delivered). v7: 16 rooms + camp stash. v6 (12 rooms + stash) keeps its stash; v3-v6 keep level, xp, inventory, tips and spell; the map progress restarts

// Test build (variant arpg-todo, project.json): every save and every fresh start has level 10 and every relic and tome equipped.
#ifndef ARPG_ALL_UNLOCKED
#define ARPG_ALL_UNLOCKED 0
#endif

static void arpg_unlock_for_tests(void) {
#if ARPG_ALL_UNLOCKED
    g_arpg.level = 10;
    g_arpg.points = 0;
    arpg_inv_unlock_all();
    g_arpg_level = g_arpg.level;
#endif
}

// Curve x2 (DESIGN-ARPG.md 7, campaign): level 1 asks 60 and every level the double of the previous one, 60 * 2^(L-1) for
// levels 1..20 (the last is 31457280, still inside int32). Level 20 and up use the last value.
#define ARPG_XP_TABLE_LEN 20
static const int s_arpg_xp_needed[ARPG_XP_TABLE_LEN] = {
    60, 120, 240, 480, 960, 1920, 3840, 7680, 15360, 30720,
    61440, 122880, 245760, 491520, 983040, 1966080, 3932160, 7864320, 15728640, 31457280
};

void arpg_progress_reset(void) {
    memset(&g_arpg, 0, sizeof(g_arpg));
    g_arpg.magic = 0x41525047u;
    g_arpg.version = ARPG_SAVE_VERSION;
    g_arpg.level = 1;
    g_arpg.xp = 0;
    g_arpg.points = 0;
    g_arpg.tips = 0;
    g_arpg.deepest = 0;
    g_arpg.spell = 0;
    g_arpg.altars_lo = 0;
    g_arpg.altars_hi = 0;
    arpg_quest_reset();
    arpg_inv_new_game();          // Rayo equipado, bolsa vacía
    g_arpg_level = g_arpg.level;
    arpg_unlock_for_tests();
}

int arpg_xp_needed(int level) {
    int idx = level - 1;
    if (idx < 0) idx = 0;
    if (idx >= ARPG_XP_TABLE_LEN) idx = ARPG_XP_TABLE_LEN - 1;
#if ARPG_BOT
    if (g_bal.xp_curve_pm) {                 // balance loop: 25 * f^(L-1) in integer maths, f per mille
        int v = 25 << 8;
        for (int i = 0; i < idx; i++) v = (int)(((int64_t)v * g_bal.xp_curve_pm) / 1000);
        return (v + 128) >> 8;
    }
#endif
    return s_arpg_xp_needed[idx];
}

void arpg_add_xp(int amount) {
    if (amount > 0) g_arpg.xp += (uint32_t)amount;
}

int arpg_sleep(void) {
    int gained = 0;
    while (g_arpg.xp >= (uint32_t)arpg_xp_needed(g_arpg.level)) {
        g_arpg.xp -= (uint32_t)arpg_xp_needed(g_arpg.level);
        g_arpg.level++;
        gained++;
    }
    g_arpg_level = g_arpg.level;
    return gained;
}

int arpg_enemy_xp(int enemy_type, int floor) {
    int base;
    switch (enemy_type) {
    case ENEMY_TYPE_BEBE:       base = BAL_AT(xp, enemy_type, ARPG_XP_BEBE); break;
    case ENEMY_TYPE_MONAGUILLO: base = BAL_AT(xp, enemy_type, ARPG_XP_MONAGUILLO); break;
    case ENEMY_TYPE_EXVOTO:     base = BAL_AT(xp, enemy_type, ARPG_XP_EXVOTO); break;
    case ENEMY_TYPE_PARROCO:    base = BAL_AT(xp, enemy_type, ARPG_XP_PARROCO); break;
    case ENEMY_TYPE_SHOOTER:    base = BAL_AT(xp, enemy_type, ARPG_XP_OJO); break;
    case ENEMY_TYPE_CHARGER:    base = BAL_AT(xp, enemy_type, ARPG_XP_CIRENEO); break;
    case ENEMY_TYPE_MONJA:      base = BAL_AT(xp, enemy_type, ARPG_XP_MONJA); break;
    case ENEMY_TYPE_CAMPANERO:      // a boss like the Abanderado of the Cripta
        return ARPG_XP_BOSS;
    case ENEMY_TYPE_ABANDERADO:     // fixed per fight: the Abanderado of the Cripta
        return BAL_AT(xp, enemy_type, ARPG_XP_BOSS);
    default:                    return 0;
    }
    const int lvl = floor < 1 ? 1 : floor;
    (void)lvl;                      // flat per enemy: no scaling by room level (DESIGN-ARPG.md 10)
    return base;
}

void arpg_world_rest(void) {
    memset(g_arpg.dead_groups, 0, sizeof(g_arpg.dead_groups));
    g_arpg.boss_dead = 0;
}

/* ---- Save file (DESIGN.md 7.1: guardado en la tarjeta) ---- */

#define ARPG_SAVE_MAGIC   0x41525047u
#if ARPG_ALL_UNLOCKED
#define ARPG_SAVE_NAME    "dungeonds_arpg_todo.sav"   // the test build never overwrites the player's save
#elif MINIROM
#define ARPG_SAVE_NAME    "dungeonds_arpg_mini.sav"    // a mini ROM never overwrites the player's save
#else
#define ARPG_SAVE_NAME    "dungeonds_arpg.sav"
#endif

// v1 layout (no inventory): read old saves and migrate them keeping level and xp.
typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t level;
    uint32_t xp;
    uint16_t points;
    uint16_t tree;
    uint16_t deepest;
    uint16_t spell;
    uint32_t altars_lo;
    uint32_t altars_hi;
} ArpgProgressV1;

static const char *const s_arpg_save_paths[2] = { "fat:/" ARPG_SAVE_NAME, "sd:/" ARPG_SAVE_NAME };
static int s_arpg_fat_tried = 0;
static int s_arpg_fat_ok = 0;

// Mounts the card once; the first save/load/has_save call does it. Without a card every call is a no-op.
int arpg_fat_ready(void) {
    if (!s_arpg_fat_tried) {
        s_arpg_fat_tried = 1;
        s_arpg_fat_ok = fatInitDefault();
    }
    return s_arpg_fat_ok;
}

static int progress_save(int flush_log) {
    if (!arpg_fat_ready()) return 0;
    g_arpg.quest_delivered = g_quest.delivered;     // carrying and boss_tier are not saved: they are 0 after loading
    g_arpg.quest_offered = g_quest.offered;
    for (int i = 0; i < 2; i++) {
        // libnds FAT only commits the file size on fclose, so write and close in one go.
        FILE *f = fopen(s_arpg_save_paths[i], "wb");
        if (!f) continue;
        int ok = fwrite(&g_arpg, sizeof(g_arpg), 1, f) == 1;
        if (fclose(f) != 0) ok = 0;
        if (ok) { if (flush_log) arpg_log_flush(); return 1; }
    }
    if (flush_log) arpg_log_flush();
    return 0;
}

int arpg_progress_save(void) { return progress_save(1); }
int arpg_progress_save_quiet(void) { return progress_save(0); }

// Reads `size` bytes of an old v1 save and rebuilds a v2 progress with a fresh inventory.
static int arpg_load_v1(FILE *f) {
    ArpgProgressV1 old;
    if (fread(&old, sizeof(old), 1, f) != 1) return 0;
    if (old.magic != ARPG_SAVE_MAGIC || old.level < 1) return 0;
    memset(&g_arpg, 0, sizeof(g_arpg));
    g_arpg.magic = ARPG_SAVE_MAGIC;
    g_arpg.version = ARPG_SAVE_VERSION;
    g_arpg.level = old.level;
    g_arpg.xp = old.xp;
    g_arpg.deepest = old.deepest;
    g_arpg.spell = old.spell;
    g_arpg.altars_lo = old.altars_lo;
    g_arpg.altars_hi = old.altars_hi;
    arpg_inv_new_game();          // the old tree is gone: fresh bag, level and xp kept
    arpg_quest_reset();
    g_arpg_level = g_arpg.level;
    arpg_unlock_for_tests();
    return 1;
}

int arpg_progress_load(void) {
    if (!arpg_fat_ready()) return 0;
    for (int i = 0; i < 2; i++) {
        FILE *f = fopen(s_arpg_save_paths[i], "rb");
        if (!f) continue;
        uint32_t magic = 0;
        uint16_t version = 0;
        int head = fread(&magic, sizeof(magic), 1, f) == 1 && fread(&version, sizeof(version), 1, f) == 1;
        if (head && magic == ARPG_SAVE_MAGIC && version == 1) {
            rewind(f);
            int ok = arpg_load_v1(f);
            fclose(f);
            return ok;
        }
        rewind(f);
        ArpgProgress tmp;
        memset(&tmp, 0, sizeof(tmp));          // an older file is shorter: the fields of the map stay at zero
        size_t got = fread(&tmp, 1, sizeof(tmp), f);
        fclose(f);
        int ok = got == sizeof(tmp);
        // v3-v6: the prefix up to the map fields is identical. Room ids changed in v7 (12 -> 16 rooms), so the map
        // progress (chests, altars, bosses, key, rooms seen, last altar) restarts; level, xp, bag, tips and spell stay.
        // v6 (dead_groups[12]) also carried the camp stash, 4 bytes earlier than now: it is moved, not lost.
        const int old_map = got >= ARPG_SAVE_V4_SIZE && tmp.magic == ARPG_SAVE_MAGIC && tmp.version >= 3 && tmp.version <= 6 && tmp.level >= 1;
        const int old3 = old_map && tmp.version == 3;
        if (old_map) {
            ok = 1;
            if (tmp.version == 6 && got >= ARPG_SAVE_V6_STASH_OFS + sizeof(tmp.stash))
                memmove(tmp.stash, (const uint8_t *)&tmp + ARPG_SAVE_V6_STASH_OFS, sizeof(tmp.stash));
            else
                memset(tmp.stash, 0, sizeof(tmp.stash));
            memset((uint8_t *)&tmp + ARPG_SAVE_V4_SIZE, 0, ARPG_SAVE_V5_SIZE - ARPG_SAVE_V4_SIZE);
            tmp.altars_lo = 0;                  // altars are room ids too
            tmp.altars_hi = 0;
            tmp.deepest = 0;
            tmp.version = ARPG_SAVE_VERSION;
        }
        if (ok && tmp.magic == ARPG_SAVE_MAGIC && tmp.version == 7 && tmp.level >= 1) {
            // v7 -> v8: same layout. The old key (key_have) is ignored: no penance is delivered.
            tmp.quest_delivered = 0;
            tmp.quest_offered = 0;
            tmp.version = ARPG_SAVE_VERSION;
        }
        if (ok && tmp.magic == ARPG_SAVE_MAGIC && tmp.version == ARPG_SAVE_VERSION && tmp.level >= 1) {
            g_arpg = tmp;
            g_quest.delivered = (uint8_t)(g_arpg.quest_delivered & ((1u << QUEST_COUNT) - 1u));
            g_quest.carrying = 0;
            g_quest.boss_tier = 0;
            g_quest.offered = g_arpg.quest_offered > QUEST_COUNT ? QUEST_COUNT : g_arpg.quest_offered;
            arpg_inv_sanitize();
            if (old3) arpg_inv_migrate_glifo();
            g_arpg_level = g_arpg.level;
            arpg_unlock_for_tests();
            return 1;
        }
        return 0;   // the file is there but not ours or damaged: do not read the other device
    }
    return 0;
}

int arpg_progress_has_save(void) {
    if (!arpg_fat_ready()) return 0;
    for (int i = 0; i < 2; i++) {
        FILE *f = fopen(s_arpg_save_paths[i], "rb");
        if (f) {
            fclose(f);
            return 1;
        }
    }
    return 0;
}

int arpg_tip_take(int bit) {
    if (g_arpg.tips & bit) return 0;
    g_arpg.tips = (uint16_t)(g_arpg.tips | bit);
    return 1;
}
