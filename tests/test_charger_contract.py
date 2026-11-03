import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
SPRITE_C = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
ENCOUNTERS_C = (ROOT / "source" / "encounters.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def charger_function():
    return AI_C.split("static void update_charger")[1].split("static void update_shooter")[0]


class ChargerContractTest(unittest.TestCase):
    """DESIGN.md 4.4: relentless melee pressure. FSM CHASE -> ATTACK(cooldown) -> CHASE."""

    def test_fsm_has_only_chase_and_attack(self):
        body = charger_function()
        self.assertIn("case ENEMY_STATE_ATTACK:", body)
        self.assertIn("case ENEMY_STATE_CHASE:", body)
        for removed in ("ENEMY_STATE_IDLE", "ENEMY_STATE_ALERT", "ENEMY_STATE_SEARCH", "last_seen", "los_lost"):
            self.assertNotIn(removed, body, removed)

    def test_speed_is_about_ninety_percent_of_the_hero(self):
        hero = int(re.search(r'\{ "Space Marine Hero", (\d+),', SPRITE_C).group(1))
        charger = int(re.search(r"ENEMY_TYPE_CHARGER\] = \{.*?\.speed = (\d+)", GAMEPLAY_C, re.S).group(1))
        self.assertTrue(0.85 <= charger / hero <= 0.95, f"{charger}/{hero}")

    def test_no_telegraph_and_bite_has_cooldown(self):
        body = charger_function()
        self.assertIn("e->state_timer = tuning->attack_cooldown;", body)
        self.assertNotIn("TELEGRAPH", body)
        cooldown = int(re.search(r"ENEMY_TYPE_CHARGER\] = \{.*?\.attack_cooldown = (\d+)", GAMEPLAY_C, re.S).group(1))
        self.assertLessEqual(cooldown, 40)       # "cooldown corto"

    def test_bite_needs_a_clear_line_not_just_distance(self):
        body = charger_function()
        bite = body.split("// Bite")[1].split("// Straight")[0]
        self.assertIn("los_has_line_of_sight(wx, wy, px, py, 0)", bite)
        self.assertIn("line_is_walkable(wx, wy, px, py)", bite)   # low walls do not block line of sight

    def test_it_walks_down_the_navigation_field(self):
        body = charger_function()
        self.assertIn("nav_next_step(wx, wy, &step_x, &step_y)", body)
        self.assertIn("nav_update(NAV_BUDGET_PER_FRAME);", MAIN_C)
        self.assertIn("nav_set_goal(TO_INT(s_player.x), TO_INT(s_player.y));", MAIN_C)

    def test_enemies_are_active_from_the_start(self):
        # Closed arena (DESIGN.md 4.6): no detection, all enemies act as soon as the wave spawns.
        self.assertIn("e->state = (type == ENEMY_TYPE_CHARGER) ? ENEMY_STATE_CHASE", ENCOUNTERS_C)


if __name__ == "__main__":
    unittest.main()
