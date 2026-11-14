import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
NAV = (ROOT / "source" / "navfield.c").read_text(encoding="utf-8")
COLL = (ROOT / "source" / "collision.c").read_text(encoding="utf-8")
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


def function_body(src, signature):
    start = src.index(signature)
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1]
    raise AssertionError(signature)


class AiPerfContract(unittest.TestCase):
    def test_separation_uses_a_bounded_grid_and_no_software_math(self):
        self.assertRegex(AI, r"static uint8_t s_grid_head\[")
        self.assertRegex(AI, r"static uint8_t s_grid_next\[MAX_GAMEPLAY_ENEMIES\]")
        self.assertIn("SEP_CELL_SHIFT 4", AI)               # cell >= the 16 px separation radius
        body = function_body(AI, "static void apply_separation")
        self.assertIn("s_grid_head[", body)
        self.assertNotIn("int_sqrt", body)
        self.assertNotRegex(body, r"for \(int j = 0; j < num_enemies")   # no O(n^2) scan
        self.assertNotRegex(body, r"\) / \(int32_t\)")                  # no division by a variable
        self.assertNotIn("malloc", AI)

    def test_hardware_sqrt_and_divide_in_the_ai_path(self):
        self.assertIn("sqrt32(", AI)
        self.assertIn("div32(", AI)
        self.assertNotIn("bit >>= 2", AI)                   # the old software sqrt loop is gone
        self.assertNotRegex(AI, r"\(t_dx \* \(int32_t\)speed\) /")
        self.assertNotRegex(AI, r"/ len;")

    def test_no_float_in_ai_or_nav(self):
        for src in (AI, NAV):
            self.assertNotRegex(src, r"(float|double)")

    def test_level_of_detail_is_staggered_and_scaled(self):
        self.assertIn("enemy_ai_set_view", AI)
        self.assertRegex(AI, r"\(s_ai_tick \+ \(uint32_t\)i\) & 1")
        self.assertIn("s_lod_mult = 2", AI)
        self.assertIn("* s_lod_mult", AI)
        self.assertEqual(MAIN.count("enemy_ai_set_view("), 2)   # arena and strip update paths

    def test_navigation_caches_and_skips_redundant_searches(self):
        self.assertIn("s_step_cache", NAV)
        self.assertIn("s_dirty", NAV)
        self.assertIn("s_searched_goal", NAV)

    def test_line_samplers_do_not_divide_per_sample(self):
        body = function_body(COLL, "int line_is_walkable")
        self.assertNotRegex(body, r"\* i / steps")
        body = function_body(COLL, "int bullet_line_is_free")
        self.assertNotRegex(body, r"\* i / steps")


if __name__ == "__main__":
    unittest.main()
