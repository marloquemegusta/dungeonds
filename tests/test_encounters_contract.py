import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCOUNTERS_H = (ROOT / "include" / "encounters.h").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")

# Constants mirroring C definitions
MAX_FLOOR_LEVELS = 5
MAX_GAMEPLAY_ENEMIES = 10

ENCOUNTER_STATE_IDLE = 0
ENCOUNTER_STATE_ACTIVE = 1
ENCOUNTER_STATE_CLEARED = 2

ENEMY_TYPE_NONE = 0
ENEMY_TYPE_CHARGER = 1
ENEMY_TYPE_SHOOTER = 2

PICKUP_HEALTH = 1
PICKUP_ARMOR = 2
PICKUP_AMMO_SHOTGUN = 3
PICKUP_AMMO_GATLING = 4
PICKUP_AMMO_HEAVY = 5


class FloorDifficultyTuning:
    def __init__(self, floor_index, enemy_count, charger_ratio, health_drops, ammo_drops):
        self.floor_index = floor_index
        self.enemy_count = enemy_count
        self.charger_ratio = charger_ratio
        self.health_drops = health_drops
        self.ammo_drops = ammo_drops


def parse_floor_tuning():
    pattern = re.compile(
        r"\[(\d+)\]\s*=\s*\{[^}]*?\.floor_index\s*=\s*(\d+)[^}]*?\.enemy_count\s*=\s*(\d+)[^}]*?\.charger_ratio\s*=\s*(\d+)[^}]*?\.guaranteed_health_drops\s*=\s*(\d+)[^}]*?\.guaranteed_ammo_drops\s*=\s*(\d+)",
        re.DOTALL
    )
    matches = pattern.findall(ENCOUNTERS_C)
    tuning = {}
    for idx_str, f_idx, count, ratio, hp_d, am_d in matches:
        idx = int(idx_str)
        tuning[idx] = FloorDifficultyTuning(
            floor_index=int(f_idx),
            enemy_count=int(count),
            charger_ratio=int(ratio),
            health_drops=int(hp_d),
            ammo_drops=int(am_d)
        )
    return tuning


class MockEncounterManager:
    def __init__(self, tuning_table):
        self.tuning_table = tuning_table
        self.current_floor = 0
        self.total_cleared_floors = 0
        self.wave_state = ENCOUNTER_STATE_IDLE
        self.wave_index = 0
        self.enemies_total = 0
        self.enemies_remaining = 0
        self.exit_open = 0
        self.exit_x = 380 << 8
        self.exit_y = (227 - 64) << 8
        self.exit_radius = 24
        self.last_kill_x = 0
        self.last_kill_y = 0
        self.enemies = []
        self.spawned_pickups = []

    def spawn_wave(self, anchor_x=380 << 8, anchor_y=227 << 8):
        tuning = self.tuning_table[self.current_floor]
        target_count = min(tuning.enemy_count, MAX_GAMEPLAY_ENEMIES)
        num_chargers = (target_count * tuning.charger_ratio + 50) // 100
        if num_chargers < 1 and tuning.charger_ratio > 0 and target_count > 0:
            num_chargers = 1
        if num_chargers > target_count:
            num_chargers = target_count
        num_shooters = target_count - num_chargers

        self.enemies = []
        for i in range(target_count):
            e_type = ENEMY_TYPE_CHARGER if i < num_chargers else ENEMY_TYPE_SHOOTER
            self.enemies.append({
                "id": i,
                "type": e_type,
                "active": 1,
                "hp": 60 if e_type == ENEMY_TYPE_CHARGER else 20,
                "x": anchor_x + ((i + 1) * 32 << 8),
                "y": anchor_y + ((i + 1) * 32 << 8),
            })

        self.enemies_total = len(self.enemies)
        self.enemies_remaining = len(self.enemies)
        self.wave_state = ENCOUNTER_STATE_ACTIVE
        self.exit_open = 0
        self.wave_index += 1
        return len(self.enemies)

    def record_kill(self, x, y):
        self.last_kill_x = x
        self.last_kill_y = y

    def update(self, player_x, player_y):
        if self.wave_state == ENCOUNTER_STATE_ACTIVE:
            alive_count = sum(1 for e in self.enemies if e["active"] and e["hp"] > 0)
            self.enemies_remaining = alive_count
            if alive_count == 0:
                self.wave_state = ENCOUNTER_STATE_CLEARED
                self.exit_open = 1
                tuning = self.tuning_table[self.current_floor]
                # Drop guaranteed health pickups
                for _ in range(tuning.health_drops):
                    self.spawned_pickups.append({"type": PICKUP_HEALTH, "amount": 25})
                # Drop guaranteed ammo pickups
                ammo_cycle = [PICKUP_AMMO_SHOTGUN, PICKUP_AMMO_GATLING, PICKUP_AMMO_HEAVY]
                for a in range(tuning.ammo_drops):
                    self.spawned_pickups.append({"type": ammo_cycle[a % 3], "amount": 10})
        elif self.wave_state == ENCOUNTER_STATE_CLEARED and self.exit_open:
            pdx = (player_x - self.exit_x) >> 8
            pdy = (player_y - self.exit_y) >> 8
            if pdx * pdx + pdy * pdy <= self.exit_radius * self.exit_radius:
                self.advance_floor(player_x, player_y)

    def advance_floor(self, player_x, player_y):
        self.total_cleared_floors += 1
        if self.current_floor < MAX_FLOOR_LEVELS - 1:
            self.current_floor += 1
        else:
            self.current_floor = MAX_FLOOR_LEVELS - 1
        self.exit_open = 0
        return self.spawn_wave(player_x, player_y)


class TestEncountersContract(unittest.TestCase):
    def test_encounters_header_contract(self):
        """Validates that encounters.h declares types, structs, and function prototypes."""
        self.assertIn("ENCOUNTER_STATE_IDLE", ENCOUNTERS_H)
        self.assertIn("ENCOUNTER_STATE_ACTIVE", ENCOUNTERS_H)
        self.assertIn("ENCOUNTER_STATE_CLEARED", ENCOUNTERS_H)
        self.assertIn("typedef struct", ENCOUNTERS_H)
        self.assertIn("FloorDifficultyTuning", ENCOUNTERS_H)
        self.assertIn("EncounterManager", ENCOUNTERS_H)
        self.assertIn("encounters_init", ENCOUNTERS_H)
        self.assertIn("encounters_spawn_wave", ENCOUNTERS_H)
        self.assertIn("encounters_update", ENCOUNTERS_H)
        self.assertIn("encounters_advance_floor", ENCOUNTERS_H)
        self.assertIn("encounters_record_kill", ENCOUNTERS_H)
        self.assertIn("encounters_render", ENCOUNTERS_H)

    def test_tunable_placeholder_annotations(self):
        """Verifies that tunable tables have canonical TUNABLE-PLACEHOLDER markers."""
        self.assertIn("/* TUNABLE-PLACEHOLDER: Floor Progression Scaling Table */", ENCOUNTERS_C)
        self.assertIn("/* TUNABLE-PLACEHOLDER: Floor Progression Scaling Struct */", ENCOUNTERS_H)
        matches = re.findall(r"/\*\s*TUNABLE-PLACEHOLDER:[^*]+\*/", ENCOUNTERS_C)
        self.assertGreaterEqual(len(matches), 5, "Floor progression parameters must be parameterized")

    def test_floor_progression_scaling_tuning(self):
        """Verifies parametric scaling across floors: enemy count and charger ratio increase."""
        tuning = parse_floor_tuning()
        self.assertEqual(len(tuning), MAX_FLOOR_LEVELS)

        prev_count = 0
        prev_ratio = 0
        for floor_idx in range(MAX_FLOOR_LEVELS):
            self.assertIn(floor_idx, tuning)
            t = tuning[floor_idx]
            self.assertGreater(t.enemy_count, 0)
            self.assertLessEqual(t.enemy_count, MAX_GAMEPLAY_ENEMIES, "Wave enemy count must fit in pool (<= 10)")
            self.assertGreaterEqual(t.enemy_count, prev_count, "Enemy count must scale monotonically")
            self.assertGreaterEqual(t.charger_ratio, prev_ratio, "Charger ratio must scale or remain high")
            self.assertGreaterEqual(t.health_drops, 1, "Must drop at least 1 guaranteed health pickup")
            self.assertGreaterEqual(t.ammo_drops, 1, "Must drop at least 1 guaranteed ammo pickup")
            prev_count = t.enemy_count
            prev_ratio = t.charger_ratio

        # Verify Floor 1 intro vs Floor 5 stress
        self.assertEqual(tuning[0].enemy_count, 3)
        self.assertEqual(tuning[4].enemy_count, 10, "Floor 5 must exercise maximum enemy stress (10 enemies)")
        self.assertGreater(tuning[4].charger_ratio, tuning[0].charger_ratio)

    def test_wave_spawning_composition_per_floor(self):
        """Verifies mixed group composition of Chargers and Shooters for all floors."""
        tuning = parse_floor_tuning()
        mgr = MockEncounterManager(tuning)

        expected_mix = [
            (3, 1, 2),  # Floor 1: 3 total, 1 charger, 2 shooters
            (5, 2, 3),  # Floor 2: 5 total, 2 chargers, 3 shooters
            (7, 3, 4),  # Floor 3: 7 total, 3 chargers, 4 shooters
            (8, 4, 4),  # Floor 4: 8 total, 4 chargers, 4 shooters
            (10, 6, 4), # Floor 5: 10 total, 6 chargers, 4 shooters
        ]

        for floor_idx, (exp_total, exp_chargers, exp_shooters) in enumerate(expected_mix):
            mgr.current_floor = floor_idx
            spawned = mgr.spawn_wave()
            self.assertEqual(spawned, exp_total)
            self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_ACTIVE)
            self.assertEqual(mgr.exit_open, 0)
            chargers = sum(1 for e in mgr.enemies if e["type"] == ENEMY_TYPE_CHARGER)
            shooters = sum(1 for e in mgr.enemies if e["type"] == ENEMY_TYPE_SHOOTER)
            self.assertEqual(chargers, exp_chargers)
            self.assertEqual(shooters, exp_shooters)

    def test_wave_clear_trigger_and_reward_drops(self):
        """Verifies wave clear triggers when all enemies are defeated, dropping guaranteed rewards."""
        tuning = parse_floor_tuning()
        mgr = MockEncounterManager(tuning)
        mgr.current_floor = 0
        mgr.spawn_wave()

        # Enemies alive -> wave remains ACTIVE
        mgr.update(380 << 8, 227 << 8)
        self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_ACTIVE)
        self.assertEqual(mgr.exit_open, 0)
        self.assertEqual(len(mgr.spawned_pickups), 0)

        # Defeat 2 out of 3 enemies -> still ACTIVE
        mgr.enemies[0]["hp"] = 0
        mgr.enemies[0]["active"] = 0
        mgr.enemies[1]["hp"] = 0
        mgr.enemies[1]["active"] = 0
        mgr.update(380 << 8, 227 << 8)
        self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_ACTIVE)
        self.assertEqual(mgr.enemies_remaining, 1)
        self.assertEqual(mgr.exit_open, 0)

        # Defeat final enemy -> CLEARED, exit opens, guaranteed pickups drop
        mgr.enemies[2]["hp"] = 0
        mgr.enemies[2]["active"] = 0
        mgr.update(380 << 8, 227 << 8)
        self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_CLEARED)
        self.assertEqual(mgr.enemies_remaining, 0)
        self.assertEqual(mgr.exit_open, 1)

        # Check guaranteed drops on Floor 1 (1 health, 2 ammo)
        health_drops = sum(1 for p in mgr.spawned_pickups if p["type"] == PICKUP_HEALTH)
        ammo_drops = sum(1 for p in mgr.spawned_pickups if p["type"] in (PICKUP_AMMO_SHOTGUN, PICKUP_AMMO_GATLING, PICKUP_AMMO_HEAVY))
        self.assertEqual(health_drops, tuning[0].health_drops)
        self.assertEqual(ammo_drops, tuning[0].ammo_drops)

    def test_floor_progression_exit_transition(self):
        """Verifies stepping on the exit tile advances floor and starts next scaled wave."""
        tuning = parse_floor_tuning()
        mgr = MockEncounterManager(tuning)
        mgr.current_floor = 0
        mgr.spawn_wave()

        # Defeat all enemies
        for e in mgr.enemies:
            e["hp"] = 0
            e["active"] = 0
        mgr.update(380 << 8, 227 << 8)
        self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_CLEARED)
        self.assertEqual(mgr.exit_open, 1)

        # Player far from exit -> does not advance
        player_x = 380 << 8
        player_y = 227 << 8
        mgr.update(player_x, player_y)
        self.assertEqual(mgr.current_floor, 0)
        self.assertEqual(mgr.total_cleared_floors, 0)

        # Player steps onto exit tile -> advances to floor 1 (Floor 2 in display)
        exit_player_x = mgr.exit_x
        exit_player_y = mgr.exit_y
        mgr.update(exit_player_x, exit_player_y)
        self.assertEqual(mgr.current_floor, 1)
        self.assertEqual(mgr.total_cleared_floors, 1)
        self.assertEqual(mgr.wave_state, ENCOUNTER_STATE_ACTIVE)
        self.assertEqual(mgr.exit_open, 0)
        self.assertEqual(mgr.enemies_total, tuning[1].enemy_count)

    def test_main_c_hooks_encounters_subsystem(self):
        """Verifies main.c integrates encounters_init, encounters_update, and encounters_render."""
        self.assertIn('#include "encounters.h"', MAIN_C)
        self.assertIn("encounters_init(&g_encounter_mgr)", MAIN_C)
        self.assertIn("encounters_spawn_wave(&g_encounter_mgr", MAIN_C)
        self.assertIn("encounters_update(&g_encounter_mgr", MAIN_C)
        self.assertIn("encounters_render(&g_encounter_mgr", MAIN_C)
        self.assertIn("encounters_record_kill(&g_encounter_mgr", MAIN_C)


if __name__ == "__main__":
    unittest.main()
