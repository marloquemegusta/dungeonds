#ifndef SANDBOX_H
#define SANDBOX_H

#include <stdint.h>
#include "game.h"
#include "gameplay.h"

#ifndef SANDBOX
#define SANDBOX 0
#endif
// PLAYGROUND=1 (build variant "playground", needs SANDBOX=1): a playable test ROM. At boot the sandbox
// applies a built-in layout (player in the south hall, parked dummies around it, god mode), dead
// dummies come back by themselves, R puts every dummy back at once and SELECT cycles the effects
// style. No scenario needed.
#ifndef PLAYGROUND
#define PLAYGROUND 0
#endif
#ifndef CATHEDRAL_PLAYGROUND
#define CATHEDRAL_PLAYGROUND 0
#endif

// Scenario sandbox (build variant "sandbox", -DSANDBOX=1; never in the shipping ROM).
// A headless scenario fills g_sandbox with `poke` steps and finally increments `seq`; the game
// applies the request on the next simulated frame and copies `seq` into `ack` (the scenario
// waits on `ack`). This places the player, picks the weapon and effects style and spawns parked
// enemies, so a scenario can stage exactly the situation it wants to show.
//
// Layout (offsets are part of the contract, asserted in sandbox.c and the host test):
//   0 seq u32 | 4 ack u32 | 8 player_x s16 | 10 player_y s16 | 12 weapon u8 | 13 style u8
//   14 enemy_count u8 | 15 flags u8 | 16 enemies[16] (6 bytes each: type u8, flags u8, x s16, y s16)
#define SANDBOX_MAX_ENEMIES 16
#define SANDBOX_FLAG_CLEAR     1   // remove every existing enemy (and effects) before spawning
#define SANDBOX_FLAG_FREEZE_AI 2   // enemies keep their place (hits still hurt, shove and kill)
#define SANDBOX_FLAG_GOD       4   // the player ignores damage
// Sniper charge aura look (g_aura_style, AURA_STYLE_*) in flag bits 3-4: 8 = bit 0, 16 = bit 1.
// 0 = K (default), 1 = C, 2 = V.
#define SANDBOX_FLAG_AURA_SHIFT 3
#define SANDBOX_FLAG_AURA_MASK  (3 << SANDBOX_FLAG_AURA_SHIFT)

#define SANDBOX_ENEMY_NONE    0
#define SANDBOX_ENEMY_CHARGER 1
#define SANDBOX_ENEMY_SHOOTER 2
#define SANDBOX_ENEMY_SKELETON 3
#define SANDBOX_ENEMY_FLAG_ASLEEP 1   // spawn dormant instead of awake

typedef struct {
    uint8_t type;      // SANDBOX_ENEMY_*
    uint8_t flags;     // SANDBOX_ENEMY_FLAG_*
    int16_t x;         // ground position, world px (feet)
    int16_t y;
} SandboxEnemy;

typedef struct {
    uint32_t seq;
    uint32_t ack;
    int16_t player_x;
    int16_t player_y;
    uint8_t weapon;    // WeaponType
    uint8_t style;     // g_fx_style (0 = A, 1 = B, 2 = C)
    uint8_t enemy_count;
    uint8_t flags;     // SANDBOX_FLAG_*
    SandboxEnemy enemies[SANDBOX_MAX_ENEMIES];
} SandboxMailbox;

#if SANDBOX
// Playground only: R. Puts every dummy back at its spawn point with full health.
void sandbox_respawn(void);
extern SandboxMailbox g_sandbox;
extern int g_sandbox_freeze_ai;          // read by enemy_ai_update()
// Applies a pending request; call once per simulated frame before the player update.
void sandbox_update(Enemy *enemies, int max_enemies, fixed *player_x, fixed *player_y);
#else
#define g_sandbox_freeze_ai 0
static inline void sandbox_respawn(void) {}
static inline void sandbox_update(Enemy *enemies, int max_enemies, fixed *player_x, fixed *player_y) {
    (void)enemies; (void)max_enemies; (void)player_x; (void)player_y;
}
#endif

#endif // SANDBOX_H
