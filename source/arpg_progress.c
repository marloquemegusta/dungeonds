#include "arpg_progress.h"
#include "arpg.h"
#include <fat.h>
#include <stdio.h>
#include <string.h>

ArpgProgress g_arpg;

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

// round(25 * 1.45^(L-1)) for levels 1..20 (computed offline, hardcoded). Level 20 and up use the last value.
#define ARPG_XP_TABLE_LEN 20
static const int s_arpg_xp_needed[ARPG_XP_TABLE_LEN] = {
    25, 36, 53, 76, 111, 160, 232, 337, 489, 708,
    1027, 1489, 2160, 3131, 4540, 6584, 9546, 13842, 20071, 29103
};

void arpg_progress_reset(void) {
    memset(&g_arpg, 0, sizeof(g_arpg));
    g_arpg.magic = 0x41525047u;
    g_arpg.version = 5;
    g_arpg.level = 1;
    g_arpg.xp = 0;
    g_arpg.points = 0;
    g_arpg.tree = 0;
    g_arpg.deepest = 0;
    g_arpg.spell = 0;
    g_arpg.altars_lo = 0;
    g_arpg.altars_hi = 0;
    arpg_inv_new_game();          // Rayo equipado + 11 objetos de ejemplo (fase 2)
    g_arpg_level = g_arpg.level;
    arpg_unlock_for_tests();
}

int arpg_xp_needed(int level) {
    int idx = level - 1;
    if (idx < 0) idx = 0;
    if (idx >= ARPG_XP_TABLE_LEN) idx = ARPG_XP_TABLE_LEN - 1;
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
    switch (enemy_type) {
    case ENEMY_TYPE_EXVOTO:     return ARPG_XP_EXVOTO;
    case ENEMY_TYPE_MONAGUILLO: return ARPG_XP_MONAGUILLO;
    case ENEMY_TYPE_CHARGER:    return ARPG_XP_CIRENEO;
    case ENEMY_TYPE_SHOOTER:    return ARPG_XP_OJO;
    case ENEMY_TYPE_ABANDERADO: {
        int boss_index = (floor + 4) / 5;          // floor 5 -> 1, 10 -> 2, 15 -> 3
        if (boss_index < 1) boss_index = 1;
        if (boss_index - 1 >= 5) return ARPG_XP_BOSS_CAP;   // the shift would pass the cap anyway
        int xp = ARPG_XP_BOSS_BASE << (boss_index - 1);
        return xp > ARPG_XP_BOSS_CAP ? ARPG_XP_BOSS_CAP : xp;
    }
    default:                    return 0;
    }
}

void arpg_world_rest(void) {
    memset(g_arpg.dead_groups, 0, sizeof(g_arpg.dead_groups));
    g_arpg.boss_dead = 0;
}

/* ---- Save file (DESIGN.md 7.1: guardado en la tarjeta) ---- */

#define ARPG_SAVE_MAGIC   0x41525047u
#define ARPG_SAVE_VERSION 5
#if ARPG_ALL_UNLOCKED
#define ARPG_SAVE_NAME    "dungeonds_arpg_todo.sav"   // the test build never overwrites the player's save
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
static int arpg_fat_ready(void) {
    if (!s_arpg_fat_tried) {
        s_arpg_fat_tried = 1;
        s_arpg_fat_ok = fatInitDefault();
    }
    return s_arpg_fat_ok;
}

int arpg_progress_save(void) {
    if (!arpg_fat_ready()) return 0;
    for (int i = 0; i < 2; i++) {
        // libnds FAT only commits the file size on fclose, so write and close in one go.
        FILE *f = fopen(s_arpg_save_paths[i], "wb");
        if (!f) continue;
        int ok = fwrite(&g_arpg, sizeof(g_arpg), 1, f) == 1;
        if (fclose(f) != 0) ok = 0;
        if (ok) return 1;
    }
    return 0;
}

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
        memset(&tmp, 0, sizeof(tmp));          // a v4 file is shorter: the fields of v5 stay at zero
        size_t got = fread(&tmp, 1, sizeof(tmp), f);
        fclose(f);
        int old4 = got >= ARPG_SAVE_V4_SIZE && tmp.magic == ARPG_SAVE_MAGIC && tmp.version == 4;
        int ok = got == sizeof(tmp) || old4;
        if (old4) {                             // v4: same layout up to the inventory; the map fields start empty
            memset((uint8_t *)&tmp + ARPG_SAVE_V4_SIZE, 0, sizeof(tmp) - ARPG_SAVE_V4_SIZE);
            tmp.version = ARPG_SAVE_VERSION;
        }
        // v3 (mismo formato): se conserva todo y se le añaden el Tomo y las reliquias del Glifo que le falten.
        int old3 = got >= ARPG_SAVE_V4_SIZE && tmp.magic == ARPG_SAVE_MAGIC && tmp.version == 3 && tmp.level >= 1;
        if (old3) { tmp.version = ARPG_SAVE_VERSION; ok = 1; memset((uint8_t *)&tmp + ARPG_SAVE_V4_SIZE, 0, sizeof(tmp) - ARPG_SAVE_V4_SIZE); }
        if (ok && tmp.magic == ARPG_SAVE_MAGIC && tmp.version == ARPG_SAVE_VERSION && tmp.level >= 1) {
            g_arpg = tmp;
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
