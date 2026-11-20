#ifndef ARPG_PROGRESS_H
#define ARPG_PROGRESS_H

// Persistent ARPG progression (DESIGN.md section 7). All state lives in g_arpg so a later phase can save it in one block.
#include <stdint.h>

typedef struct {
    uint32_t magic;      // set by arpg_progress_reset to 0x41525047 ("ARPG")
    uint16_t version;    // 1
    uint16_t level;      // starts at 1
    uint32_t xp;         // banked xp not yet converted into levels
    uint16_t points;     // unspent skill points
    uint16_t tree;       // bitmask of bought skill-tree nodes (used later)
    uint16_t deepest;    // deepest floor reached (used later)
    uint16_t spell;      // active spell (used later)
    uint32_t altars_lo;  // bit a = travel altar (room index / 3) touched, altars 0..31
    uint32_t altars_hi;  // altars 32..63
} ArpgProgress;

extern ArpgProgress g_arpg;

void arpg_progress_reset(void);          // level 1, everything else 0
int  arpg_xp_needed(int level);          // xp to go from `level` to level+1
void arpg_add_xp(int amount);            // just adds to g_arpg.xp (no level up here)
int  arpg_sleep(void);                   // converts banked xp into levels, returns levels gained; also sets g_arpg_level
int  arpg_enemy_xp(int enemy_type, int floor); // xp a kill is worth

// Save file on the SD card (fat:/dungeonds_arpg.sav, falling back to sd:/). Silent no-op when there is no card.
int  arpg_progress_save(void);           // writes g_arpg; returns 1 on success
int  arpg_progress_load(void);           // reads a valid save (magic and version match) into g_arpg; returns 1 if it did
int  arpg_progress_has_save(void);       // 1 if a save file exists on the card

#endif
