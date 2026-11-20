#ifndef ALLIES_H
#define ALLIES_H

// Resurreccion (DESIGN.md 7.3): Exvotos that die inside a curse zone rise as allies. An ally lives in g_enemies like any
// enemy (same slot, same drawing), but its flag lives here, indexed by slot, so struct Enemy keeps its layout.
#include <stdint.h>
#include "gameplay.h"

extern uint8_t g_enemy_ally[MAX_GAMEPLAY_ENEMIES];   // 1 = this slot is an ally
extern uint16_t g_ally_timer[MAX_GAMEPLAY_ENEMIES];  // frames left before the ally dies

void allies_reset(void);                                        // clears every ally (new run / arena restart)
int allies_is_ally(const Enemy *e, const Enemy *base);           // 1 if e points at an ally slot of base[]
// Called from the death hook (main.c). `dead` is still active here. A dead ally blasts (node 12). A dead enemy inside a
// curse zone rises as an ally into a free slot (node 10), while there is room for it.
void allies_on_enemy_death(Enemy *dead, Enemy *enemies, int max_enemies);
// Once per simulated frame, after enemy_ai_update: walks each ally to the nearest living enemy, hits it, runs the timers.
void allies_update(Enemy *enemies, int max_enemies);

#endif
