#ifndef ENCOUNTERS_H
#define ENCOUNTERS_H

#include <stdint.h>
#include <stdbool.h>
#include "game.h"
#include "gameplay.h"

// ---------------------------------------------------------------------------
// 1. Encounter States & Tuning Tables
// ---------------------------------------------------------------------------

#define MAX_FLOOR_LEVELS 5

typedef enum {
    ENCOUNTER_STATE_IDLE = 0,
    ENCOUNTER_STATE_ACTIVE,
    ENCOUNTER_STATE_CLEARED
} EncounterState;

/* TUNABLE-PLACEHOLDER: Floor Progression Scaling Struct */
typedef struct {
    int floor_index;              /* TUNABLE-PLACEHOLDER: 0-based floor level */
    int enemy_count;              /* TUNABLE-PLACEHOLDER: total enemies spawned in wave */
    int charger_ratio;            /* TUNABLE-PLACEHOLDER: ratio / percent of chargers (0..100) */
    int guaranteed_health_drops;  /* TUNABLE-PLACEHOLDER: guaranteed health packs on wave clear */
    int guaranteed_ammo_drops;    /* TUNABLE-PLACEHOLDER: guaranteed ammo packs on wave clear */
} FloorDifficultyTuning;

extern const FloorDifficultyTuning g_floor_tuning[MAX_FLOOR_LEVELS];

// ---------------------------------------------------------------------------
// 2. Encounter Manager
// ---------------------------------------------------------------------------

typedef struct {
    int current_floor;            // 0-based floor difficulty level (0..MAX_FLOOR_LEVELS-1)
    int total_cleared_floors;     // Cumulative number of completed floors
    EncounterState wave_state;    // IDLE, ACTIVE, CLEARED
    int wave_index;               // Wave index
    int enemies_total;            // Total enemies spawned in this wave
    int enemies_remaining;        // Active alive enemies remaining
    int exit_open;                // 1 if exit transition is active/unlocked
    fixed exit_x;                 // Exit tile world coordinate (8.8 fixed)
    fixed exit_y;                 // Exit tile world coordinate (8.8 fixed)
    int exit_radius;              // Player activation distance to exit tile (px)
    fixed last_kill_x;            // Coordinate of last defeated enemy
    fixed last_kill_y;
} EncounterManager;

extern EncounterManager g_encounter_mgr;

/**
 * Initializes the encounter manager.
 */
void encounters_init(EncounterManager *mgr);

/**
 * Spawns a wave of enemies on valid walkable coordinates using world_point_has_floor
 * and position_is_free, according to the current floor's difficulty tuning.
 */
int encounters_spawn_wave(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                          fixed anchor_x, fixed anchor_y);

/**
 * Main per-frame update for encounters.
 * - Tracks alive enemies in current wave.
 * - Triggers wave clear on all enemies defeated: drops guaranteed health/ammo pickups,
 *   opens the exit transition tile.
 * - Advances to next floor when player steps on the active exit tile.
 */
void encounters_update(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                       PlayerState *player, fixed player_x, fixed player_y);

/**
 * Advances difficulty to next floor level and spawns the next wave.
 */
int encounters_advance_floor(EncounterManager *mgr, Enemy *enemies, int max_enemies,
                             fixed player_x, fixed player_y);

/**
 * Records enemy death position for drop placement.
 */
void encounters_record_kill(EncounterManager *mgr, fixed x, fixed y);

/**
 * Renders the exit portal / marker onto the screen buffer if the encounter is cleared.
 */
void encounters_render(const EncounterManager *mgr, uint16_t *buffer, int cam_x, int cam_y);

#endif // ENCOUNTERS_H
