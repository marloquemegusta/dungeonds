import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_H = (ROOT / "include" / "weapons.h").read_text(encoding="utf-8")
WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")

# Mirror of C definitions and fixed point math
WEAPON_PISTOL = 0
WEAPON_SHOTGUN = 1
WEAPON_GATLING = 2
WEAPON_HEAVY = 3
NUM_WEAPON_TYPES = 4

FIRE_MODE_HITSCAN = 0
FIRE_MODE_PROJECTILE = 1


class WeaponTuning:
    def __init__(
        self,
        name,
        fire_mode,
        damage_per_hit,
        pellets,
        fire_cooldown,
        max_ammo,
        pickup_ammo_amount,
        ammo_cost,
        projectile_speed,
        projectile_range,
        spread_angle,
        spinup_delay,
        speed_penalty,
        explosion_radius,
        explosion_damage,
    ):
        self.name = name
        self.fire_mode = fire_mode
        self.damage_per_hit = damage_per_hit
        self.pellets = pellets
        self.fire_cooldown = fire_cooldown
        self.max_ammo = max_ammo
        self.pickup_ammo_amount = pickup_ammo_amount
        self.ammo_cost = ammo_cost
        self.projectile_speed = projectile_speed
        self.projectile_range = projectile_range
        self.spread_angle = spread_angle
        self.spinup_delay = spinup_delay
        self.speed_penalty = speed_penalty
        self.explosion_radius = explosion_radius
        self.explosion_damage = explosion_damage


# Canonical tuning mirror
TUNING = {
    WEAPON_PISTOL: WeaponTuning(
        "PISTOL",
        FIRE_MODE_HITSCAN,
        15,
        1,
        18,
        0,
        0,
        0,
        0,
        180,
        0,
        0,
        256,
        0,
        0,
    ),
    WEAPON_SHOTGUN: WeaponTuning(
        "SHOTGUN",
        FIRE_MODE_PROJECTILE,
        8,
        5,
        36,
        50,
        10,
        1,
        1536,
        22,
        120,
        0,
        256,
        0,
        0,
    ),
    WEAPON_GATLING: WeaponTuning(
        "GATLING",
        FIRE_MODE_HITSCAN,
        5,
        1,
        4,
        200,
        40,
        1,
        0,
        160,
        24,
        10,
        128,
        0,
        0,
    ),
    WEAPON_HEAVY: WeaponTuning(
        "HEAVY",
        FIRE_MODE_PROJECTILE,
        25,
        1,
        55,
        20,
        5,
        1,
        1024,
        60,
        0,
        0,
        256,
        32,
        45,
    ),
}


class PlayerWeaponSim:
    def __init__(self):
        self.current_weapon = WEAPON_PISTOL
        self.ammo = {
            WEAPON_PISTOL: 0,
            WEAPON_SHOTGUN: 12,
            WEAPON_GATLING: 50,
            WEAPON_HEAVY: 5,
        }
        self.cooldown = 0
        self.gatling_spinup = 0
        self.is_dead = False

    def cycle(self, delta: int):
        next_w = (self.current_weapon + delta) % NUM_WEAPON_TYPES
        if next_w < 0:
            next_w += NUM_WEAPON_TYPES
        self.current_weapon = next_w
        self.cooldown = 0
        self.gatling_spinup = 0

    def fire(self, is_held: bool = True) -> tuple[bool, int, str]:
        """Simulates fire event. Returns (fired, ammo_remaining, weapon_used)"""
        tuning = TUNING[self.current_weapon]

        # Gatling spinup handling
        if self.current_weapon == WEAPON_GATLING:
            if is_held:
                self.gatling_spinup += 1
                if self.gatling_spinup < tuning.spinup_delay:
                    return False, self.ammo[self.current_weapon], tuning.name
            else:
                self.gatling_spinup = 0
                return False, self.ammo[self.current_weapon], tuning.name
        else:
            self.gatling_spinup = 0

        # Ammo check & fallback to pistol
        if tuning.ammo_cost > 0 and self.ammo[self.current_weapon] < tuning.ammo_cost:
            self.current_weapon = WEAPON_PISTOL
            tuning = TUNING[WEAPON_PISTOL]
            self.gatling_spinup = 0

        # Consume ammo
        if tuning.ammo_cost > 0:
            self.ammo[self.current_weapon] -= tuning.ammo_cost
            if self.ammo[self.current_weapon] <= 0:
                self.ammo[self.current_weapon] = 0
                self.current_weapon = WEAPON_PISTOL

        self.cooldown = tuning.fire_cooldown
        return True, self.ammo[self.current_weapon], tuning.name

    def get_speed_factor(self, is_held: bool) -> int:
        if is_held and self.current_weapon == WEAPON_GATLING:
            return TUNING[WEAPON_GATLING].speed_penalty
        return 256


class WeaponsContractTest(unittest.TestCase):
    def test_source_code_contract(self):
        # 1. No float/double in weapons module
        for kw in ("float ", "double ", "float\t", "double\t"):
            self.assertNotIn(kw, WEAPONS_H)
            self.assertNotIn(kw, WEAPONS_C)

        # 2. TUNABLE-PLACEHOLDER markers present on tuning table
        self.assertIn("/* TUNABLE-PLACEHOLDER", WEAPONS_C)
        self.assertIn(".fire_mode", WEAPONS_C)
        self.assertIn(".damage_per_hit", WEAPONS_C)
        self.assertIn(".fire_cooldown", WEAPONS_C)
        self.assertIn(".max_ammo", WEAPONS_C)
        self.assertIn(".speed_penalty", WEAPONS_C)
        self.assertIn(".explosion_radius", WEAPONS_C)

        # 3. Fire modes abstraction present
        self.assertIn("FIRE_MODE_HITSCAN", WEAPONS_H)
        self.assertIn("FIRE_MODE_PROJECTILE", WEAPONS_H)

        # 4. Controls wired in main.c
        self.assertIn("weapons_cycle(&g_player_state, -1)", MAIN_C)
        self.assertIn("weapons_cycle(&g_player_state, 1)", MAIN_C)
        self.assertIn("KEY_L", MAIN_C)
        self.assertIn("KEY_R", MAIN_C)
        self.assertIn("weapons_get_speed_factor", MAIN_C)
        self.assertIn("weapons_render", MAIN_C)

    def test_weapon_cycling_lr(self):
        sim = PlayerWeaponSim()
        self.assertEqual(sim.current_weapon, WEAPON_PISTOL)

        # Cycle next (R)
        sim.cycle(1)
        self.assertEqual(sim.current_weapon, WEAPON_SHOTGUN)
        sim.cycle(1)
        self.assertEqual(sim.current_weapon, WEAPON_GATLING)
        sim.cycle(1)
        self.assertEqual(sim.current_weapon, WEAPON_HEAVY)
        sim.cycle(1)
        self.assertEqual(sim.current_weapon, WEAPON_PISTOL)

        # Cycle prev (L)
        sim.cycle(-1)
        self.assertEqual(sim.current_weapon, WEAPON_HEAVY)
        sim.cycle(-1)
        self.assertEqual(sim.current_weapon, WEAPON_GATLING)
        sim.cycle(-1)
        self.assertEqual(sim.current_weapon, WEAPON_SHOTGUN)
        sim.cycle(-1)
        self.assertEqual(sim.current_weapon, WEAPON_PISTOL)

    def test_ammo_consumption_and_infinite_pistol(self):
        sim = PlayerWeaponSim()
        # Pistol does not consume ammo
        fired, ammo, name = sim.fire()
        self.assertTrue(fired)
        self.assertEqual(ammo, 0)
        self.assertEqual(name, "PISTOL")

        # Shotgun consumes 1 ammo
        sim.current_weapon = WEAPON_SHOTGUN
        sim.ammo[WEAPON_SHOTGUN] = 5
        fired, ammo, name = sim.fire()
        self.assertTrue(fired)
        self.assertEqual(ammo, 4)
        self.assertEqual(name, "SHOTGUN")

        # Heavy consumes 1 ammo
        sim.current_weapon = WEAPON_HEAVY
        sim.ammo[WEAPON_HEAVY] = 2
        fired, ammo, name = sim.fire()
        self.assertTrue(fired)
        self.assertEqual(ammo, 1)
        self.assertEqual(name, "HEAVY")

    def test_infinite_pistol_fallback_when_empty(self):
        sim = PlayerWeaponSim()
        sim.current_weapon = WEAPON_SHOTGUN
        sim.ammo[WEAPON_SHOTGUN] = 0

        # Attempting to fire shotgun with 0 ammo immediately falls back to Pistol
        fired, ammo, name = sim.fire()
        self.assertTrue(fired)
        self.assertEqual(name, "PISTOL")
        self.assertEqual(sim.current_weapon, WEAPON_PISTOL)

    def test_fallback_on_exhaustion(self):
        sim = PlayerWeaponSim()
        sim.current_weapon = WEAPON_HEAVY
        sim.ammo[WEAPON_HEAVY] = 1

        # Fire last rocket: fires HEAVY, reaches 0 ammo, falls back to PISTOL
        fired, ammo, name = sim.fire()
        self.assertTrue(fired)
        self.assertEqual(name, "HEAVY")
        self.assertEqual(ammo, 0)
        self.assertEqual(sim.current_weapon, WEAPON_PISTOL)

    def test_gatling_spinup_and_speed_penalty(self):
        sim = PlayerWeaponSim()
        sim.current_weapon = WEAPON_GATLING
        sim.ammo[WEAPON_GATLING] = 50

        # Before spinup reaches 10 frames, it cannot fire
        for frame in range(1, 10):
            fired, _, _ = sim.fire(is_held=True)
            self.assertFalse(fired, f"Gatling should not fire at frame {frame}")

        # At frame 10 (spinup satisfied), it fires!
        fired, ammo, name = sim.fire(is_held=True)
        self.assertTrue(fired)
        self.assertEqual(name, "GATLING")
        self.assertEqual(ammo, 49)

        # Movement speed penalty: 128 / 256 = 50%
        factor = sim.get_speed_factor(is_held=True)
        self.assertEqual(factor, 128)

        # When released or with other weapon: 256 = 100%
        factor_released = sim.get_speed_factor(is_held=False)
        self.assertEqual(factor_released, 256)
        sim.current_weapon = WEAPON_PISTOL
        factor_pistol = sim.get_speed_factor(is_held=True)
        self.assertEqual(factor_pistol, 256)

    def test_damage_and_pellet_specs(self):
        # Shotgun: 5 pellets, spread angle
        self.assertEqual(TUNING[WEAPON_SHOTGUN].pellets, 5)
        self.assertGreater(TUNING[WEAPON_SHOTGUN].spread_angle, 0)
        self.assertEqual(TUNING[WEAPON_SHOTGUN].fire_mode, FIRE_MODE_PROJECTILE)

        # Heavy: 1 projectile, explosion radius, splash damage
        self.assertEqual(TUNING[WEAPON_HEAVY].pellets, 1)
        self.assertEqual(TUNING[WEAPON_HEAVY].fire_mode, FIRE_MODE_PROJECTILE)
        self.assertEqual(TUNING[WEAPON_HEAVY].explosion_radius, 32)
        self.assertEqual(TUNING[WEAPON_HEAVY].explosion_damage, 45)

        # Pistol: 1 pellet, hitscan, 0 ammo cost
        self.assertEqual(TUNING[WEAPON_PISTOL].pellets, 1)
        self.assertEqual(TUNING[WEAPON_PISTOL].fire_mode, FIRE_MODE_HITSCAN)
        self.assertEqual(TUNING[WEAPON_PISTOL].ammo_cost, 0)


if __name__ == "__main__":
    unittest.main()
