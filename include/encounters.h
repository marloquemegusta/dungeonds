#ifndef ENCOUNTERS_H
#define ENCOUNTERS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "gameplay.h"

// DESIGN.md 5: the dungeon is full of dormant packs. A pack wakes as a whole when the player
// comes close to any of its members (or when one of them is hurt); clearing a pack heals one
// hit and offers two modifiers; clearing every pack completes the run.

#define MAX_PACKS 12
#define PACK_WAKE_RADIUS 220            // ground px (metric dx^2 + 4 dy^2) from any dormant member
#define RUN_COMPLETE_FRAMES 180         // "dungeon completed" banner before the next run

typedef enum {
    ENCOUNTER_STATE_ACTIVE = 0,
    ENCOUNTER_STATE_CLEARED         // every pack dead: banner, then the run restarts
} EncounterState;

typedef struct {
    int arena;                    // index of the arena being played (into g_arenas)
    int total_cleared;            // runs completed since the game started
    EncounterState state;
    int enemies_total;            // enemies spawned in this run
    int enemies_remaining;        // alive enemies
    int packs_total;              // packs with at least one enemy
    int packs_cleared;
    int clear_timer;              // frames left in the completion banner
    int advance;                  // 1 when the banner is over: main starts a new run
    uint8_t pack_alive[MAX_PACKS];
    uint8_t pack_awake[MAX_PACKS];
    int16_t kill_x[MAX_PACKS];    // where each pack's latest member died
    int16_t kill_y[MAX_PACKS];
} EncounterManager;

extern EncounterManager g_encounter_mgr;

void encounters_init(EncounterManager *mgr);

// Spawns every enemy of the active arena (g_arena) asleep and starts the run.
int encounters_spawn(EncounterManager *mgr, Enemy *enemies, int max_enemies);

// Wakes packs, detects cleared packs (heal + modifier offer) and the end of the run.
void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies, fixed player_x, fixed player_y);

// Index of the arena that follows the current one.
int encounters_next_arena(const EncounterManager *mgr);

// Records where an enemy of `pack` died.
void encounters_record_kill(EncounterManager *mgr, int pack, fixed x, fixed y);

#endif // ENCOUNTERS_H
