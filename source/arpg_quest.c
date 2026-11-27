#include "arpg_quest.h"

ArpgQuest g_quest;

void arpg_quest_reset(void) { g_quest.delivered = 0; g_quest.carrying = 0; g_quest.boss_tier = 0; g_quest.offered = 0; }
int  arpg_quest_delivered(int q) { return (g_quest.delivered >> q) & 1; }
int  arpg_quest_carrying(int q) { return (g_quest.carrying >> q) & 1; }
int  arpg_quest_has(int q) { return ((g_quest.delivered | g_quest.carrying) >> q) & 1; }
void arpg_quest_pick(int q) { g_quest.carrying |= (uint8_t)(1u << q); g_quest.boss_tier = 1; }
void arpg_quest_drop_carried(void) { g_quest.carrying = 0; g_quest.boss_tier = 0; }
int  arpg_quest_deliver_all(void) {
    int now = g_quest.carrying & ~g_quest.delivered;
    g_quest.delivered |= g_quest.carrying;
    g_quest.carrying = 0;
    g_quest.boss_tier = 0;
    return now;
}
int  arpg_quest_world_tier(void) {
    int n = 0;
    for (int q = 0; q < QUEST_COUNT; q++) n += (g_quest.delivered >> q) & 1;
    return n + g_quest.boss_tier;
}
