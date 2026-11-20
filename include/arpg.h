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
#define ARPG_DMG_BEBE 8             // [TUNABLE-PLACEHOLDER] swarm tier: weak individually, dangerous in numbers
#define ARPG_DMG_PARROCO 25         // [TUNABLE-PLACEHOLDER] tank tier: hits harder than the Exvoto (15)
#define ARPG_DMG_PARROCO_PUSH 96    // [TUNABLE-PLACEHOLDER] 8.8 fixed shove (0,375 px/frame) the Párroco's blow gives the hero
#define ARPG_DMG_PARROCO_PUSH_FRAMES 10 // [TUNABLE-PLACEHOLDER] frames the hero keeps being pushed after a Párroco blow
#define ARPG_DMG_MONJA 10           // [TUNABLE-PLACEHOLDER] support tier: her blow is weak when cornered
#define ARPG_DMG_CIRENEO 25         // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_CHARGER
#define ARPG_DMG_OJO 30             // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_SHOOTER
#define ARPG_DMG_ABANDERADO 25      // [TUNABLE-PLACEHOLDER]
#define ARPG_DMG_DEFAULT 20         // [TUNABLE-PLACEHOLDER] any other source

// Exvoto tiers (v3, walkthroughs/arpg-predemo §10).
#define ARPG_BEBE_SPEED_BONUS_PCT 23    // [TUNABLE-PLACEHOLDER] % faster than the Exvoto (130 -> ~160 in 8.8)
#define ARPG_PARROCO_HP_X 4             // [TUNABLE-PLACEHOLDER] life multiplier over the Exvoto base
#define ARPG_MONJA_HP_X 2               // [TUNABLE-PLACEHOLDER] life multiplier over the Exvoto base
// Monja: stays behind praying and heals the Exvotos around her while she prays.
#define ARPG_MONJA_PRAY_RADIUS 48       // [TUNABLE-PLACEHOLDER] ground px: Exvotos inside this circle are healed
#define ARPG_MONJA_HEAL_PCT 2           // [TUNABLE-PLACEHOLDER] % of the target's max life restored per second
#define ARPG_MONJA_HEAL_PERIOD 60       // [TUNABLE-PLACEHOLDER] frames between heals (60 = once a second at 60 FPS)
#define ARPG_MONJA_PRAY_MIN 30          // [TUNABLE-PLACEHOLDER] frames she keeps praying before moving again
#define ARPG_MONJA_PRAY_MAX 90          // [TUNABLE-PLACEHOLDER] frames praying; then she re-anchors behind the group

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

// Glifo (antes Maldicion, DESIGN.md 7.3): a second spell thrown to the stylus point. It arms for a moment and
// then, for a few seconds, slows the enemies standing inside. The burn is no longer part of it: only a tree node
// gives it (DESIGN.md 7.3).
#define ARPG_CURSE_COST 30          // [TUNABLE-PLACEHOLDER] mana per throw
#define ARPG_CURSE_RADIUS 40        // [TUNABLE-PLACEHOLDER] ground px of the zone
#define ARPG_CURSE_RADIUS_MIASMA 56 // [TUNABLE-PLACEHOLDER] ground px with Miasma (tree node 7)
#define ARPG_CURSE_FRAMES 240       // [TUNABLE-PLACEHOLDER] zone lifetime (4 s at 60 FPS)
#define ARPG_CURSE_FRAMES_MIASMA 360 // [TUNABLE-PLACEHOLDER] zone lifetime with Miasma
#define ARPG_CURSE_ARM_FRAMES 30    // [TUNABLE-PLACEHOLDER] the glifo is drawn, darker, this long before it acts (0,5 s)
#define ARPG_CURSE_SLOW_PCT 40      // [TUNABLE-PLACEHOLDER] % of speed removed from enemies inside a live glifo
#define ARPG_CURSE_TICK 30          // [TUNABLE-PLACEHOLDER] frames between burn applications (only with the node)
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

// Rooms (salas ARPG): doors, lateral openings, chests and altars, and the group population.
#define ARPG_ROOM_DOOR_TRIGGER_PX 22      // [TUNABLE-PLACEHOLDER] hero this close to a room's top line, centred, crosses the door
#define ARPG_ROOM_DOOR_HALF_W_PX 26       // [TUNABLE-PLACEHOLDER] half width of the door gap, ground px
#define ARPG_ROOM_DOOR_ART_W_PX 64        // [TUNABLE-PLACEHOLDER] baked door sprite width (shadow canvas of the render)
#define ARPG_ROOM_FOOT_OFFSET_PX 40       // [TUNABLE-PLACEHOLDER] where the hero lands above the foot of the next room
#define ARPG_ROOM_HOLE_W_PX 24            // [TUNABLE-PLACEHOLDER] lateral opening width (3 tiles)
#define ARPG_ROOM_HOLE_H_PX 24            // [TUNABLE-PLACEHOLDER] lateral opening height (3 tiles)
#define ARPG_ROOM_HOLE_Y_PX 168           // [TUNABLE-PLACEHOLDER] top of the lateral opening, from the room's top line
#define ARPG_ROOM_SPAWN_AHEAD_PX 640      // [TUNABLE-PLACEHOLDER] a room's group is placed this far before the hero reaches it
#define ARPG_ROOM_DESPAWN_BEHIND_PX 760   // [TUNABLE-PLACEHOLDER] enemies this far below the hero are recycled
#define ARPG_ROOM_GROUP_MIN 4             // [TUNABLE-PLACEHOLDER] smallest group of a room
#define ARPG_ROOM_GROUP_MAX 12            // [TUNABLE-PLACEHOLDER] largest group of a room
#define ARPG_ROOM_MAX_AWAKE 2             // [TUNABLE-PLACEHOLDER] groups awake at once around the hero
// Difficulty ramp of the opening rooms (rooms are 1-based, thresholds are the 0-based room index).
#define ARPG_MINION_MIN_ROOM 2            // [TUNABLE-PLACEHOLDER] room index from which an Ojo/Cireneo may appear at all (room 3)
#define ARPG_MINION_ROOM_FREQ 3           // [TUNABLE-PLACEHOLDER] 1 in this many rooms carries a single Ojo/Cireneo (until the full mix)
#define ARPG_MINION_MAX_PER_GROUP 2       // [TUNABLE-PLACEHOLDER] cap of Ojos/Cireneos per group from the full-mix room on
#define ARPG_TIER_MIN_ROOM 4              // [TUNABLE-PLACEHOLDER] room index from which Párroco and Monja join the mix (room 5)
#define ARPG_TIER_CAP_PER_GROUP 1         // [TUNABLE-PLACEHOLDER] max of each (Párroco, Monja) per group until the full mix
#define ARPG_FULL_MIX_ROOM 7              // [TUNABLE-PLACEHOLDER] room index of the full mix and the Ojo/Cireneo cap (room 8)
#define ARPG_ROOM_CHEST_REACH_PX 24       // [TUNABLE-PLACEHOLDER] chest opens when the hero is this close
#define ARPG_ROOM_ALTAR_REACH_PX 28       // [TUNABLE-PLACEHOLDER] altar is touched when the hero is this close
#define ARPG_ROOM_CHEST_XP 6              // [TUNABLE-PLACEHOLDER] xp of a chest at room 1; grows a little per room

// Hero level (starts at 1; later phases change it).
extern int g_arpg_level;

// Damage the hero takes from one hit by an enemy of this EnemyType.
int arpg_enemy_damage(int enemy_type);

// L held past ARPG_L_HOLD_FRAMES: switches Rayo <-> Maldicion once the curse is unlocked.
void arpg_on_l_hold(void);

// Adds mana back slowly (one point every ARPG_MANA_REGEN_FRAMES). Call once per simulated frame.
void player_regen_mana(PlayerState *player);

#endif
