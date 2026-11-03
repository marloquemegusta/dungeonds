#ifndef ENCOUNTERS_H
#define ENCOUNTERS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "gameplay.h"

// One encounter per arena (DESIGN.md 4.6): when the arena starts all its enemies spawn at the
// points listed in the arena data and act at once. When the last one dies there is a short
// pause and then the game moves to the next arena (the first one again after the last).

#define ENCOUNTER_CLEAR_PAUSE_FRAMES 30     // half a second between the last kill and the next arena

typedef enum {
    ENCOUNTER_STATE_ACTIVE = 0,
    ENCOUNTER_STATE_CLEARED
} EncounterState;

typedef struct {
    int arena;                    // index of the arena being played (into g_arenas)
    int total_cleared;            // arenas cleared since the game started
    EncounterState state;
    int enemies_total;            // enemies spawned in this arena
    int enemies_remaining;        // alive enemies
    int clear_timer;              // frames left in the pause after the last kill
    int advance;                  // 1 when the pause is over: main loads the next arena
} EncounterManager;

extern EncounterManager g_encounter_mgr;

void encounters_init(EncounterManager *mgr);

// Spawns the enemies of the active arena (g_arena) and starts the encounter.
int encounters_spawn(EncounterManager *mgr, Enemy *enemies, int max_enemies);

// Counts the living enemies; on the last kill starts the pause, and raises `advance` when it ends.
void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies);

// Index of the arena that follows the current one.
int encounters_next_arena(const EncounterManager *mgr);

// Records where an enemy died (kept for effects).
void encounters_record_kill(EncounterManager *mgr, fixed x, fixed y);

#endif // ENCOUNTERS_H
