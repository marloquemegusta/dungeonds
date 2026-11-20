#ifndef ARPG_H
#define ARPG_H

// Pre-demo ARPG prototype (DESIGN.md section 7). Every number here is a [TUNABLE-PLACEHOLDER].

#include "gameplay.h"

// Hero life is in points (not hearts): base plus per level.
#define ARPG_HP_BASE 100            // [TUNABLE-PLACEHOLDER] life at level 1
#define ARPG_HP_PER_LEVEL 10        // [TUNABLE-PLACEHOLDER] life gained per level
// Mana: spent by spells, regenerated slowly.
#define ARPG_MANA_BASE 60           // [TUNABLE-PLACEHOLDER] mana at level 1
#define ARPG_MANA_PER_LEVEL 5       // [TUNABLE-PLACEHOLDER] mana gained per level
#define ARPG_MANA_REGEN_FRAMES 30   // [TUNABLE-PLACEHOLDER] 1 mana every N frames

// Damage the hero takes per hit, by enemy type.
#define ARPG_DMG_EXVOTO 15          // [TUNABLE-PLACEHOLDER]
#define ARPG_DMG_MONAGUILLO 10      // [TUNABLE-PLACEHOLDER]
#define ARPG_DMG_CIRENEO 25         // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_CHARGER
#define ARPG_DMG_OJO 30             // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_SHOOTER
#define ARPG_DMG_ABANDERADO 25      // [TUNABLE-PLACEHOLDER]
#define ARPG_DMG_DEFAULT 20         // [TUNABLE-PLACEHOLDER] any other source

// Life restored by one heal pickup (what an old one-heart heal now gives).
#define ARPG_HEAL_PICKUP 20         // [TUNABLE-PLACEHOLDER]

// Sacred ray: mana per shot and damage per hit (was 150).
#define ARPG_RAY_COST 15            // [TUNABLE-PLACEHOLDER] mana per shot
#define ARPG_RAY_DAMAGE 100         // [TUNABLE-PLACEHOLDER] damage per ray hit

// Punch: short tap of L when there is no reeling enemy to finish.
#define ARPG_PUNCH_DAMAGE 50        // [TUNABLE-PLACEHOLDER]
#define ARPG_PUNCH_RANGE 28         // [TUNABLE-PLACEHOLDER] ground px
#define ARPG_PUNCH_COOLDOWN 24      // [TUNABLE-PLACEHOLDER] frames between punches
#define ARPG_L_HOLD_FRAMES 15       // [TUNABLE-PLACEHOLDER] an L press held this long is a hold, not a tap

// Remate drops: chance in percent and amount restored by each orb.
#define ARPG_REMATE_HP_CHANCE 60    // [TUNABLE-PLACEHOLDER] %
#define ARPG_REMATE_HP 20           // [TUNABLE-PLACEHOLDER] life per health orb
#define ARPG_REMATE_MANA_CHANCE 75  // [TUNABLE-PLACEHOLDER] %
#define ARPG_REMATE_MANA 25         // [TUNABLE-PLACEHOLDER] mana per mana orb
#define ARPG_PICKUP_MAGNET 36       // [TUNABLE-PLACEHOLDER] ground px: orbs this close fly to the hero

// Experience runes (DESIGN.md 7): what a death is worth, and how far a rune is pulled to the hero.
#define ARPG_XP_EXVOTO 4            // [TUNABLE-PLACEHOLDER] xp per Exvoto
#define ARPG_XP_MONAGUILLO 1        // [TUNABLE-PLACEHOLDER] xp per Monaguillo
#define ARPG_XP_CIRENEO 10          // [TUNABLE-PLACEHOLDER] xp per Cireneo (ENEMY_TYPE_CHARGER)
#define ARPG_XP_OJO 8               // [TUNABLE-PLACEHOLDER] xp per Ojo del Tribunal (ENEMY_TYPE_SHOOTER)
#define ARPG_XP_BOSS_BASE 100       // [TUNABLE-PLACEHOLDER] Abanderado xp at boss 1; doubles per boss
#define ARPG_XP_BOSS_CAP 1600       // [TUNABLE-PLACEHOLDER] Abanderado xp ceiling
#define ARPG_RUNE_MAGNET 64         // [TUNABLE-PLACEHOLDER] ground px: runes this close fly to the hero (orbs: ARPG_PICKUP_MAGNET)
#define ARPG_BOSS_RUNES 6           // [TUNABLE-PLACEHOLDER] runes an Abanderado drops, splitting its xp
#define ARPG_BOSS_RUNE_SPREAD 12    // [TUNABLE-PLACEHOLDER] ground px from the boss to each rune

// Curse (Maldicion, DESIGN.md 7.3): a second spell thrown to the stylus point, leaves a burning zone on the floor.
#define ARPG_CURSE_COST 30          // [TUNABLE-PLACEHOLDER] mana per throw
#define ARPG_CURSE_RADIUS 40        // [TUNABLE-PLACEHOLDER] ground px of the zone
#define ARPG_CURSE_RADIUS_MIASMA 56 // [TUNABLE-PLACEHOLDER] ground px with Miasma (tree node 7)
#define ARPG_CURSE_FRAMES 240       // [TUNABLE-PLACEHOLDER] zone lifetime
#define ARPG_CURSE_FRAMES_MIASMA 360 // [TUNABLE-PLACEHOLDER] zone lifetime with Miasma
#define ARPG_CURSE_TICK 30          // [TUNABLE-PLACEHOLDER] frames between burn applications
#define ARPG_CURSE_RANGE 140        // [TUNABLE-PLACEHOLDER] max throw distance, ground px
#define ARPG_CURSE_FLIGHT 20        // [TUNABLE-PLACEHOLDER] frames in the air
#define ARPG_CURSE_MAX 3            // [TUNABLE-PLACEHOLDER] curses (flying or lying) at once

// Resurreccion (DESIGN.md 7.3): an Exvoto that dies inside a curse zone rises as an ally for a while.
#define ARPG_ALLY_MAX_1 2           // [TUNABLE-PLACEHOLDER] live allies (tree node 10)
#define ARPG_ALLY_MAX_2 4           // [TUNABLE-PLACEHOLDER] live allies with node 11
#define ARPG_ALLY_FRAMES_1 300      // [TUNABLE-PLACEHOLDER] ally lifetime
#define ARPG_ALLY_FRAMES_2 480      // [TUNABLE-PLACEHOLDER] ally lifetime with node 11
#define ARPG_ALLY_HP 200            // [TUNABLE-PLACEHOLDER] ally life
#define ARPG_ALLY_DAMAGE 40         // [TUNABLE-PLACEHOLDER] damage per ally blow
#define ARPG_ALLY_ATTACK_FRAMES 45  // [TUNABLE-PLACEHOLDER] frames between ally blows
#define ARPG_ALLY_RANGE 20          // [TUNABLE-PLACEHOLDER] ground px: melee reach
#define ARPG_ALLY_BLAST_DAMAGE 120  // [TUNABLE-PLACEHOLDER] fire damage of the blast when an ally dies (node 12)
#define ARPG_ALLY_BLAST_RADIUS 40   // [TUNABLE-PLACEHOLDER] ground px of that blast

// Depth (DESIGN.md 7.1): enemies get tougher with the floor (stage k, 0-based); bosses also by their number n (0 = floor 5).
#define ARPG_DEPTH_HP_PCT 12        // [TUNABLE-PLACEHOLDER] % of life added per floor
#define ARPG_DEPTH_PCT(k) (100 + ARPG_DEPTH_HP_PCT * (k))
#define ARPG_BOSS_HP_PCT(n) ((n) == 0 ? 100 : (n) == 1 ? 160 : 220 + 40 * ((n) - 2))   // [TUNABLE-PLACEHOLDER] % of life by boss number

// Hero level (starts at 1; later phases change it).
extern int g_arpg_level;

// Damage the hero takes from one hit by an enemy of this EnemyType.
int arpg_enemy_damage(int enemy_type);

// L held past ARPG_L_HOLD_FRAMES: switches Rayo <-> Maldicion once the curse is unlocked.
void arpg_on_l_hold(void);

// Adds mana back slowly (one point every ARPG_MANA_REGEN_FRAMES). Call once per simulated frame.
void player_regen_mana(PlayerState *player);

#endif
