#ifndef ARPG_BALANCE_H
#define ARPG_BALANCE_H

// Knob panel of the ARPG balance (variant "arpg-bot" only): the main [TUNABLE-PLACEHOLDER] numbers of arpg.h can be overridden
// at run time through ONE volatile struct (symbol g_bal) that the balance tool (tools/arpg_balance.py) or a scenario writes by
// memory offset before play. Every field is an OVERRIDE: 0 = "use the game's own value", so with nothing written the bot
// variant plays exactly the numbers of the shipping build. Outside the bot variant BAL()/BAL_AT() are the plain constant:
// no struct, no cost, no behaviour change.

#include <stdint.h>
#include <stddef.h>
#include "game.h"

#if ARPG_BOT

#define ARPG_BAL_TYPES 10          // indexed by EnemyType (include/gameplay.h): 0 none, 1 Cireneo, 2 Ojo, 3 Exvoto, 4 Abanderado, 5 Monaguillo, 6 Bebe, 7 Parroco, 8 Monja, 9 Campanero

typedef struct {
    uint16_t hp_pct[ARPG_BAL_TYPES];        // 0   life multiplier per enemy type, % (applied on top of the tuning table; 0 = 100)
    uint16_t dmg[ARPG_BAL_TYPES];           // 20  damage of one hit to the hero, per enemy type (0 = the game's value)
    uint16_t xp[ARPG_BAL_TYPES];            // 40  base xp per kill, per enemy type (Abanderado: xp of the boss)
    uint16_t hero_hp_base;                  // 60  life at level 1
    uint16_t hero_hp_level;                 // 62  life per level above 1
    uint16_t hero_mana_base;                // 64
    uint16_t hero_mana_level;               // 66
    uint16_t ray_cost;                      // 68  mana per ray shot
    uint16_t ray_damage;                    // 70  damage per ray hit
    uint16_t punch_a;                       // 72  jab
    uint16_t punch_b;                       // 74  cross
    uint16_t punch_hook;                    // 76  hook
    uint16_t remate_hp_chance;              // 78  % chance of the remate health orb
    uint16_t remate_hp;                     // 80  life of that orb
    uint16_t remate_mana_chance;            // 82  % chance of the remate mana orb
    uint16_t remate_mana;                   // 84  mana of that orb
    uint16_t xp_curve_pm;                   // 86  xp curve factor per level, per mille (the table is 25 * 1.45^(L-1))
    uint16_t group_pct;                     // 88  density of the groups of a room, % of its roster (up to 200 adds copies)
    uint16_t mana_regen_frames;             // 90  frames per mana point
    uint16_t boss_hp_pct0;                  // 92  % of life of the Cripta boss
    uint16_t heal_pickup;                   // 94  life of a heal (chest orb, Viatico, pack cleared)
    uint16_t tier2_hp_pct;                  // 96  % of life of the tier 2 Ojo/Cireneo
    uint16_t tier2_dmg_pct;                 // 98  % of damage of the tier 2 Ojo/Cireneo
    uint16_t pad[6];                        // 100
} ArpgBalance;
_Static_assert(sizeof(ArpgBalance) == 112 && offsetof(ArpgBalance, dmg) == 20 && offsetof(ArpgBalance, xp) == 40 &&
               offsetof(ArpgBalance, hero_hp_base) == 60 && offsetof(ArpgBalance, ray_cost) == 68 &&
               offsetof(ArpgBalance, punch_a) == 72 && offsetof(ArpgBalance, remate_hp_chance) == 78 &&
               offsetof(ArpgBalance, xp_curve_pm) == 86 && offsetof(ArpgBalance, mana_regen_frames) == 90 &&
               offsetof(ArpgBalance, boss_hp_pct0) == 92 && offsetof(ArpgBalance, heal_pickup) == 94,
               "ArpgBalance layout is written by tools/arpg_balance.py by offset");
extern volatile ArpgBalance g_bal;

#define BAL(field, def)        (g_bal.field ? (int)g_bal.field : (int)(def))
#define BAL_AT(field, i, def)  ((i) >= 0 && (i) < ARPG_BAL_TYPES && g_bal.field[i] ? (int)g_bal.field[i] : (int)(def))

#else

#define BAL(field, def)        (def)
#define BAL_AT(field, i, def)  (def)

#endif
#endif
