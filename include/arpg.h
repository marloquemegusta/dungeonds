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
#define ARPG_GUARD_DIST 70          // [TUNABLE-PLACEHOLDER] ground px from the hero where a bodyguard (Monaguillo, PÃ¡rroco) stands in the line of fire
#define ARPG_GUARD_SPEED_X 3        // [TUNABLE-PLACEHOLDER] a bodyguard runs to the line at this multiple of its walking speed
#define ARPG_PARROCO_FLASH_FRAMES 5 // [TUNABLE-PLACEHOLDER] frames the PÃ¡rroco's body flashes wax-white when the ray breaks on it
#define ARPG_SMONJA_GLIFO_SPEED 768 // [TUNABLE-PLACEHOLDER] 8.8 ground px/frame of the SÃºper Monja's dash out of a glifo (3 px/frame)
#define ARPG_SMONJA_GLIFO_REACT 10  // [TUNABLE-PLACEHOLDER] frames she stays still after the glifo lands, before dashing out
#define ARPG_SMONJA_GLIFO_MARGIN 14 // [TUNABLE-PLACEHOLDER] ground px past the glifo's edge she keeps running to
#define ARPG_DMG_MONJA 10           // [TUNABLE-PLACEHOLDER] support tier: her blow is weak when cornered
#define ARPG_DMG_CIRENEO 25         // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_CHARGER
#define ARPG_DMG_OJO 30             // [TUNABLE-PLACEHOLDER] ENEMY_TYPE_SHOOTER
#define ARPG_DMG_ABANDERADO 25      // [TUNABLE-PLACEHOLDER]
#define ARPG_DMG_DEFAULT 20         // [TUNABLE-PLACEHOLDER] any other source

// Exvoto tiers (v3, walkthroughs/arpg-predemo Â§10).
#define ARPG_BEBE_SPEED_BONUS_PCT 23    // [TUNABLE-PLACEHOLDER] % faster than the Exvoto (130 -> ~160 in 8.8)
#define ARPG_PARROCO_HP_X 4             // [TUNABLE-PLACEHOLDER] life multiplier over the Exvoto base
#define ARPG_MONJA_HP_X 2               // [TUNABLE-PLACEHOLDER] life multiplier over the Exvoto base
// Super Monja (ENEMY_TYPE_MONJA): stays behind her group praying; while she prays the Exvoto family around her
// (not herself) recovers life and walks faster.
#define ARPG_MONJA_PRAY_RADIUS 64       // [TUNABLE-PLACEHOLDER] ground px: allies inside this circle are healed and hasted
#define ARPG_MONJA_HEAL_PCT 5           // [TUNABLE-PLACEHOLDER] % of the target's max life restored per second
#define ARPG_MONJA_HEAL_PERIOD 60       // [TUNABLE-PLACEHOLDER] frames between heals (60 = once a second at 60 FPS)
#define ARPG_MONJA_HASTE_PCT 50         // [TUNABLE-PLACEHOLDER] % faster walking for allies in the radius (attacks unchanged); also the possessed spiders
// Possession (DESIGN-ARPG s5, "Aura de posesiÃ³n"): the Exvoto and the Monaguillo inside a living SÃºper Monja's radius turn
// into spiders (transition, then the scuttling walk, hasted) and get up again (transition played backwards) when they leave.
#define ARPG_SMONJA_POSSESS_RADIUS 96   // [TUNABLE-PLACEHOLDER] ground px (dy counts double): they are possessed inside this circle
#define ARPG_SMONJA_POSSESS_HYST 16     // [TUNABLE-PLACEHOLDER] ground px: they are released only beyond RADIUS + this (no flicker at the edge)
#define ARPG_MONJA_KEEP_FLEE 60         // [TUNABLE-PLACEHOLDER] ground px: hero closer than this makes her walk away
#define ARPG_MONJA_KEEP_FLEE_STOP 90    // [TUNABLE-PLACEHOLDER] ground px: she stops fleeing (and prays) from this distance
#define ARPG_MONJA_KEEP_FAR 115         // [TUNABLE-PLACEHOLDER] ground px: hero farther than this makes her walk closer
#define ARPG_MONJA_KEEP_FAR_STOP 100    // [TUNABLE-PLACEHOLDER] ground px: she stops approaching (and prays) from this distance
#define ARPG_MONJA_PRAYS 0              // 1 = the old prayer (heal + haste + placement); 0 = Super Monja: circles, kites and charges (ARPG_SMONJA_*)
// Super Monja (DESIGN-ARPG s5): circles at mid distance, kites at punching range, charges now and then.
#define ARPG_SMONJA_RING_NEAR 80        // [TUNABLE-PLACEHOLDER] ground px: closer than this (but outside KITE) she backs off
#define ARPG_SMONJA_RING_FAR 120        // [TUNABLE-PLACEHOLDER] ground px: farther than this she closes in; between, she orbits
#define ARPG_SMONJA_KITE_DIST 40        // [TUNABLE-PLACEHOLDER] ground px: punching range, she backs off at once (until RING_NEAR)
#define ARPG_SMONJA_KITE_SPEED 512      // [TUNABLE-PLACEHOLDER] 8.8 ground px/frame of the backward retreat (2 px/frame; the hero walks ~0.7)
#define ARPG_SMONJA_CHARGE_CD_MIN 120   // [TUNABLE-PLACEHOLDER] frames between charges (min, 2 s)
#define ARPG_SMONJA_CHARGE_CD_MAX 180   // [TUNABLE-PLACEHOLDER] frames between charges (max, 3 s)
#define ARPG_SMONJA_CHARGE_MAX_DIST 200 // [TUNABLE-PLACEHOLDER] ground px: she only warns when the hero is within this
#define ARPG_SMONJA_WARN_FRAMES 30      // [TUNABLE-PLACEHOLDER] still and trembling before the charge (0.5 s)
#define ARPG_SMONJA_CHARGE_SPEED 768    // [TUNABLE-PLACEHOLDER] 8.8 ground px/frame of the charge (3 px/frame)
#define ARPG_SMONJA_CHARGE_FRAMES 48    // [TUNABLE-PLACEHOLDER] max frames of the charge (~144 ground px) if it touches nothing
#define ARPG_SMONJA_HIT_RADIUS 16       // [TUNABLE-PLACEHOLDER] ground px: the headbutt lands (and the charge stops) inside this
#define ARPG_SMONJA_CHARGE_DAMAGE 20    // [TUNABLE-PLACEHOLDER] damage of the charge
#define ARPG_SMONJA_RECOVER_FRAMES 9    // [TUNABLE-PLACEHOLDER] still after the headbutt / end of the charge: her weak moment
#define ARPG_SMONJA_BOUNCE_SPEED 640    // [TUNABLE-PLACEHOLDER] 8.8 ground px/frame of the bounce back (2.5 px/frame)
#define ARPG_SMONJA_BOUNCE_DIST 90      // [TUNABLE-PLACEHOLDER] ground px from the hero where the bounce ends (ring distance)
#define ARPG_SMONJA_BOUNCE_FRAMES 40    // [TUNABLE-PLACEHOLDER] max frames of the bounce (wall or far hero cut it)
// Monjarana scuttle (her walk when she repositions): fast bursts and dead stops, zigzag.
#define ARPG_MONJA_BURST_MIN 6          // [TUNABLE-PLACEHOLDER] game frames of one burst (min)
#define ARPG_MONJA_BURST_MAX 12         // [TUNABLE-PLACEHOLDER] game frames of one burst (max)
#define ARPG_MONJA_BURST_SPEED 384      // [TUNABLE-PLACEHOLDER] 8.8 ground px/frame during a burst (384 = 1.5 px/frame)
#define ARPG_MONJA_PAUSE_MIN 4          // [TUNABLE-PLACEHOLDER] frames standing still between bursts (min)
#define ARPG_MONJA_PAUSE_MAX 14         // [TUNABLE-PLACEHOLDER] frames standing still between bursts (max)
#define ARPG_MONJA_BACKSTEP_ONE_IN 5    // [TUNABLE-PLACEHOLDER] 1 burst in N is a small sideways step back

// Life restored by one heal pickup (what an old one-heart heal now gives).
#define ARPG_HEAL_PICKUP 20         // [TUNABLE-PLACEHOLDER]

// Sacred ray: mana per shot and damage per hit (was 150).
#define ARPG_RAY_COST 15            // [TUNABLE-PLACEHOLDER] mana per shot
#define ARPG_RAY_DAMAGE 100         // [TUNABLE-PLACEHOLDER] damage per ray hit

// Punch: short tap of L when there is no reeling enemy to finish.
#define ARPG_PUNCH_DAMAGE 50        // [TUNABLE-PLACEHOLDER]
#define ARPG_PUNCH_RANGE 28         // [TUNABLE-PLACEHOLDER] ground px
#define ARPG_PUNCH_COOLDOWN 24      // [TUNABLE-PLACEHOLDER] frames between punches
#define ARPG_L_HOLD_FRAMES 5        // [TUNABLE-PLACEHOLDER] an L press held this long is a hold, not a tap (opens the radial)

// Remate drops: chance in percent and amount restored by each orb.
#define ARPG_REMATE_HP_CHANCE 60    // [TUNABLE-PLACEHOLDER] %
#define ARPG_REMATE_HP 20           // [TUNABLE-PLACEHOLDER] life per health orb
#define ARPG_REMATE_MANA_CHANCE 75  // [TUNABLE-PLACEHOLDER] %
#define ARPG_REMATE_MANA 25         // [TUNABLE-PLACEHOLDER] mana per mana orb
#define ARPG_PICKUP_MAGNET 36       // [TUNABLE-PLACEHOLDER] ground px: orbs this close fly to the hero

// Experience (DESIGN-ARPG.md Â§1): what a death is worth, granted directly on the kill.
#define ARPG_XP_EXVOTO 4            // [TUNABLE-PLACEHOLDER] xp per Exvoto
#define ARPG_XP_MONAGUILLO 1        // [TUNABLE-PLACEHOLDER] xp per Monaguillo
#define ARPG_XP_CIRENEO 10          // [TUNABLE-PLACEHOLDER] xp per Cireneo (ENEMY_TYPE_CHARGER)
#define ARPG_XP_OJO 8               // [TUNABLE-PLACEHOLDER] xp per Ojo del Tribunal (ENEMY_TYPE_SHOOTER)
#define ARPG_XP_BOSS_BASE 100       // [TUNABLE-PLACEHOLDER] Abanderado xp at boss 1; doubles per boss
#define ARPG_XP_BOSS_CAP 1600       // [TUNABLE-PLACEHOLDER] Abanderado xp ceiling

// Glifo (DESIGN.md 7.5-7.7): hechizo de suelo lanzado al punto del lapiz. Ciclo: apertura (la grieta se abre, sin efecto),
// espera (actuan las auras) y detonacion (un golpe a todo el que este dentro), luego cierre. Auras componibles
// (bits de GlifoAura en include/glifo.h): Redil arrastra al centro y Zarza quema.
#define ARPG_GLIFO_COST 30          // [TUNABLE-PLACEHOLDER] mana per throw
#define ARPG_GLIFO_COST_MIN 10      // [TUNABLE-PLACEHOLDER] floor of the cost with the "Coste" line
#define ARPG_GLIFO_RADIUS 40        // [TUNABLE-PLACEHOLDER] ground px of the zone
#define ARPG_GLIFO_RADIUS_MAX 80    // [TUNABLE-PLACEHOLDER] cap with the Radio line (2x: the baked rune scales up to here)
#define ARPG_GLIFO_OPEN_FRAMES 30   // [TUNABLE-PLACEHOLDER] apertura: the crack opens, no effect (0,5 s)
#define ARPG_GLIFO_WAIT_FRAMES 90   // [TUNABLE-PLACEHOLDER] espera: the auras act (1,5 s)
#define ARPG_GLIFO_CLOSE_FRAMES 30  // [TUNABLE-PLACEHOLDER] cierre: the crack closes, outside-in (0,5 s)
#define ARPG_GLIFO_WAIT_MIN_PCT 40  // [TUNABLE-PLACEHOLDER] apertura+espera never go below this % of base
#define ARPG_GLIFO_DAMAGE 80        // [TUNABLE-PLACEHOLDER] single detonation hit
#define ARPG_GLIFO_REDIL_SPEED 120  // [TUNABLE-PLACEHOLDER] pull toward the centre, 8.8 px/frame (~28 px/s)
#define ARPG_GLIFO_ZARZA_TICK 30    // [TUNABLE-PLACEHOLDER] frames between Quemado layers during the wait
#define ARPG_GLIFO_ZARZA_DET 2      // [TUNABLE-PLACEHOLDER] Quemado layers on detonation
#define ARPG_GLIFO_MAX 3            // [TUNABLE-PLACEHOLDER] glifos (flying or lying) at once

// Resurreccion (DESIGN.md 7.3): an Exvoto that dies inside a Glifo rises as an ally for a while.
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

// Room level (zone map, DESIGN.md 7.1): no auto-scaling; the life of an enemy depends on the FIXED level of its room (k = level - 1).
// Bosses and minibosses also by their number n (0 = Cripta, 1 = Galeria del elite).
#define ARPG_DEPTH_HP_PCT 12        // [TUNABLE-PLACEHOLDER] % of life added per room level above 1
#define ARPG_DEPTH_PCT(k) (100 + ARPG_DEPTH_HP_PCT * (k))
#define ARPG_BOSS_HP_PCT(n) ((n) == 0 ? 100 : (n) == 1 ? 160 : 220 + 40 * ((n) - 2))   // [TUNABLE-PLACEHOLDER] % of life by boss number

// Rooms (salas ARPG): doors, lateral openings, chests and altars, and the group population.
#define ARPG_ROOM_DOOR_TRIGGER_PX 22      // [TUNABLE-PLACEHOLDER] hero this close to a room's top line, centred, crosses the door
#define ARPG_ROOM_DOOR_HALF_W_PX 13       // [TUNABLE-PLACEHOLDER] half width of the through arch of the back wall (mouth of 26 px), ground px
#define ARPG_ROOM_FOOT_OFFSET_PX 40       // [TUNABLE-PLACEHOLDER] where the hero lands above the foot of the next room
#define ARPG_ROOM_HOLE_W_PX 24            // [TUNABLE-PLACEHOLDER] lateral opening width (3 tiles)
#define ARPG_ROOM_HOLE_H_PX 256           // [TUNABLE-PLACEHOLDER] lateral opening height: two modules of the wall (128 px each), on the ground
#define ARPG_ROOM_HOLE_Y_PX 96            // [TUNABLE-PLACEHOLDER] top of a lateral opening, from the block top (a module joint of the wall art)
#define ARPG_ROOM_HOLE_ARRIVE_PX 80       // [TUNABLE-PLACEHOLDER] where the hero lands, from the top of the opening (inside its visible part)
#define ARPG_ROOM_SPAWN_AHEAD_PX 640      // [TUNABLE-PLACEHOLDER] a room's group is placed this far before the hero reaches it
#define ARPG_ROOM_DESPAWN_BEHIND_PX 760   // [TUNABLE-PLACEHOLDER] enemies this far below the hero are recycled
#define ARPG_ROOM_GROUP_MIN 4             // [TUNABLE-PLACEHOLDER] smallest group of a room
#define ARPG_ROOM_GROUP_MAX 12            // [TUNABLE-PLACEHOLDER] largest group of a room
#define ARPG_ROOM_MAX_AWAKE 2             // [TUNABLE-PLACEHOLDER] groups awake at once around the hero
// Difficulty ramp of the opening rooms (rooms are 1-based, thresholds are the 0-based room index).
#define ARPG_MINION_MIN_ROOM 2            // [TUNABLE-PLACEHOLDER] room index from which an Ojo/Cireneo may appear at all (room 3)
#define ARPG_MINION_ROOM_FREQ 3           // [TUNABLE-PLACEHOLDER] 1 in this many rooms carries a single Ojo/Cireneo (until the full mix)
#define ARPG_MINION_MAX_PER_GROUP 2       // [TUNABLE-PLACEHOLDER] cap of Ojos/Cireneos per group from the full-mix room on
#define ARPG_TIER_MIN_ROOM 4              // [TUNABLE-PLACEHOLDER] room index from which PÃ¡rroco and Monja join the mix (room 5)
#define ARPG_TIER_CAP_PER_GROUP 1         // [TUNABLE-PLACEHOLDER] max of each (PÃ¡rroco, Monja) per group until the full mix
#define ARPG_FULL_MIX_ROOM 7              // [TUNABLE-PLACEHOLDER] room index of the full mix and the Ojo/Cireneo cap (room 8)
// Tier 2 of the Ojo and the Cireneo (same enemy type; no visual or mechanical change yet, only life and damage).
#define ARPG_TIER2_HP_PCT 200             // [TUNABLE-PLACEHOLDER] % of the life of tier 1
#define ARPG_TIER2_DAMAGE_PCT 150         // [TUNABLE-PLACEHOLDER] % of the damage of tier 1
#define ARPG_MISA_HP_PCT 200              // [TUNABLE-PLACEHOLDER] % of life of every enemy of the miniboss "la Misa"
#define ARPG_ROOM_CHEST_REACH_PX 24       // [TUNABLE-PLACEHOLDER] chest opens when the hero is this close
#define ARPG_ROOM_ALTAR_REACH_PX 28       // [TUNABLE-PLACEHOLDER] altar is touched when the hero is this close
#define ARPG_ROOM_CHEST_XP 6              // [TUNABLE-PLACEHOLDER] xp of a chest at room 1; grows a little per room

// Hero level (starts at 1; later phases change it).
extern int g_arpg_level;

// Damage the hero takes from one hit by an enemy of this EnemyType.
int arpg_enemy_damage(int enemy_type);
// Same for a live enemy: adds the damage of its tier (ENEMY_TIER2).
int arpg_enemy_damage_of(const Enemy *e);

// L held past ARPG_L_HOLD_FRAMES: switches Rayo <-> Glifo once the Glifo tome is equipped.
void arpg_on_l_hold(void);

// Adds mana back slowly (one point every ARPG_MANA_REGEN_FRAMES). Call once per simulated frame.
void player_regen_mana(PlayerState *player);

#endif
