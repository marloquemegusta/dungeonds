#ifndef ARPG_QUEST_H
#define ARPG_QUEST_H
// Campaign penances (mission objects). Contract shared by encounters and camp/progress.
#include <stdint.h>

enum {
    QUEST_TOMAS      = 0,   // Don Tomas: the choir list (Capilla del parroco)
    QUEST_MISA       = 1,   // optional: the chapel key (Galeria de la Misa)
    QUEST_LEONOR     = 2,   // Sor Leonor: her denunciation (Galeria de la monjarana)
    QUEST_ABANDERADO = 3,
    QUEST_COUNT      = 4
};

typedef struct {
    uint8_t delivered;  // bit per quest, permanent (saved)
    uint8_t carrying;   // bit per quest, picked up this run and not delivered yet
    uint8_t boss_tier;  // 1 while carrying an object, else 0
    uint8_t offered;    // next penance the voice has given (0..QUEST_COUNT)
} ArpgQuest;

extern ArpgQuest g_quest;

void arpg_quest_reset(void);
int  arpg_quest_delivered(int q);
int  arpg_quest_carrying(int q);
int  arpg_quest_has(int q);          // delivered or carrying
void arpg_quest_pick(int q);         // carrying |= bit; boss_tier = 1
void arpg_quest_drop_carried(void);  // death or retreat: carrying = 0; boss_tier = 0
int  arpg_quest_deliver_all(void);   // arrival on foot: carrying -> delivered; returns mask delivered now
int  arpg_quest_world_tier(void);    // popcount(delivered) + boss_tier
#endif
