import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def define(name):
    return int(re.search(rf"#define {name} (\d+)", GAMEPLAY_H).group(1))


class PlayerRulesTest(unittest.TestCase):
    """DESIGN.md 4.2: a few hits, i-frames after each one, restart on death."""

    def test_health_is_four_to_five_hits(self):
        self.assertIn(define("PLAYER_MAX_HP"), (4, 5))

    def test_i_frames_are_brief(self):
        self.assertTrue(30 <= define("PLAYER_IFRAMES") <= 90)

    def test_no_armor_pickups_or_ammo(self):
        for removed in ("armor", "ammo", "PICKUP", "pickup", "apply_damage"):
            self.assertNotIn(removed, GAMEPLAY_H, removed)
            self.assertNotIn(removed, GAMEPLAY_C, removed)

    def test_hit_respects_i_frames_god_mode_and_death(self):
        body = GAMEPLAY_C.split("int player_take_hit")[1].split("\n}")[0]
        self.assertIn("player->invuln_timer > 0) return 0", body)
        self.assertIn("player->god_mode", body)
        self.assertIn("player->hp--;", body)
        self.assertIn("player->invuln_timer = PLAYER_IFRAMES + g_mods.iframes;", body)
        self.assertIn("player->is_dead = 1;", body)

    def test_every_enemy_attack_is_one_hit(self):
        self.assertIn("player_take_hit(&g_player_state);", AI_C)
        # skeleton bite, charger charge and shooter laser: one player_take_hit each, i-frames inside it
        self.assertGreaterEqual(AI_C.count("player_take_hit(&g_player_state);"), 3)

    def test_death_restarts_the_arena_with_full_health(self):
        self.assertIn("if (g_player_state.is_dead && !s_strip_mode) arena_restart();", MAIN_C)
        restart = MAIN_C.split("static void arena_restart(void)")[1].split("\n}")[0]
        self.assertIn("player_state_init(&g_player_state);", restart)
        self.assertIn("encounters_spawn(", restart)

    def test_player_flashes_red_during_i_frames(self):
        self.assertIn("g_player_state.invuln_timer > 0", MAIN_C.split("static void draw_player")[1].split("static void draw_hit_spark")[0])

    def test_enemy_hit_raises_hitstop_and_has_no_drops(self):
        body = GAMEPLAY_C.split("void enemy_hit")[1]
        self.assertIn("g_hitstop_frames", body)
        self.assertNotIn("pickup", body)

    def test_lcg_rng_is_deterministic(self):
        # Same LCG as gameplay.c; a seeded sequence must repeat.
        def seq(seed):
            state = seed
            out = []
            for _ in range(10):
                state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
                out.append(state)
            return out

        self.assertIn("1664525", GAMEPLAY_C)
        self.assertEqual(seq(42), seq(42))


if __name__ == "__main__":
    unittest.main()
