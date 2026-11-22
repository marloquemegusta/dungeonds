#ifndef ARPG_PROGRESS_H
#define ARPG_PROGRESS_H

// Persistent ARPG progression (DESIGN.md section 7). All state lives in g_arpg so a later phase can save it in one block.
#include <stdint.h>
#include <stddef.h>
#include "arpg_inv.h"

typedef struct {
    uint32_t magic;      // set by arpg_progress_reset to 0x41525047 ("ARPG")
    uint16_t version;    // 5 (v4: sin mapa; v1: inventario nuevo; v3: se conserva y se le añade el Glifo)
    uint16_t level;      // starts at 1
    uint32_t xp;         // banked xp not yet converted into levels
    uint16_t points;     // retired with the skill tree; kept so the save layout (and scenarios) do not move
    uint16_t tree;       // retired with the skill tree; arpg_tree_has() reads the inventory now
    uint16_t deepest;    // deepest floor reached (used later)
    uint16_t spell;      // active spell (used later)
    uint32_t altars_lo;  // bit a = travel altar (room index / 3) touched, altars 0..31
    uint32_t altars_hi;  // altars 32..63
    ArpgInventory inv;   // reliquias, tomos, engarces y cera (DESIGN.md 7.4)
    // v5 (mapa de la zona 1, 12 salas): fields appended at the end, never reordered. Bit r = room r (0..11).
    uint16_t chests_open;    // chests opened (never refilled)
    uint16_t boss_ever;      // bosses and minibosses beaten at least once (kept forever)
    uint16_t boss_dead;      // bosses and minibosses dead since the last sleep (they come back when sleeping)
    uint8_t  last_altar;     // room id of the last altar touched (the camp door leads there); 0 = Nave 1
    uint8_t  key_have;       // the key of the zone (no logic yet)
    uint8_t  dead_groups[12];// per room: bit b = group of block b dead since the last sleep
    uint8_t  reserved[4];
} ArpgProgress;
#define ARPG_SAVE_V4_SIZE offsetof(ArpgProgress, chests_open)

extern ArpgProgress g_arpg;

void arpg_progress_reset(void);          // level 1, fresh inventory (sample items)
int  arpg_xp_needed(int level);          // xp to go from `level` to level+1
void arpg_add_xp(int amount);            // just adds to g_arpg.xp (no level up here)
int  arpg_sleep(void);                   // converts banked xp into levels, returns levels gained; also sets g_arpg_level
int  arpg_enemy_xp(int enemy_type, int floor); // xp a kill is worth (floor = fixed level of the room)
void arpg_world_rest(void);              // sleeping: groups and bosses killed come back; chests, altars and "beaten once" stay

// Save file on the SD card (fat:/dungeonds_arpg.sav, falling back to sd:/). Silent no-op when there is no card.
int  arpg_progress_save(void);           // writes g_arpg; returns 1 on success
int  arpg_progress_load(void);           // reads a valid save (magic match) into g_arpg; returns 1 if it did
int  arpg_progress_has_save(void);       // 1 if a save file exists on the card

#endif
