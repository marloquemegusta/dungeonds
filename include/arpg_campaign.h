#ifndef ARPG_CAMPAIGN_H
#define ARPG_CAMPAIGN_H
// Camp side of the demo campaign (DESIGN-ARPG.md 7 and the campaign notes): penance texts, rewards, what is lost
// on death or retreat, and the short notices the camp shows when the hero arrives.
#include <stdint.h>

// Destination room that enc_room_take_exit() returns when the hero walks out of the Nave 1 towards the camp.
// main.c then runs arpg_campaign_arrive_on_foot() and goes to the camp.
#define ARPG_EXIT_TO_CAMP 99

void arpg_campaign_descent_begin(void);   // leaving the camp: remember the bag and repopulate the cathedral
void arpg_campaign_on_death(int floor_extra);        // death: carried object lost, half of the loot of this descent lost, repopulate
void arpg_campaign_on_retreat(void);      // pause menu "volver al campamento": only the carried object is lost
void arpg_campaign_arrive_on_foot(void);  // back in the camp walking: delivers the carried objects and pays the rewards
void arpg_campaign_confess(void);         // confessional: queues the text of the next penance (or the closing line)

// Next pending camp notice (one line, fits the camp toast), or NULL. The camp loop shows one at a time.
const char *arpg_campaign_next_notice(void);
#endif
