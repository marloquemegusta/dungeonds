import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMEPLAY_H = (ROOT / "include" / "gameplay.h").read_text(encoding="utf-8")
GAMEPLAY_C = (ROOT / "source" / "gameplay.c").read_text(encoding="utf-8")
ENEMY_AI_C = (ROOT / "source" / "enemy_ai.c").read_text(encoding="utf-8")
HORDE_C = (ROOT / "source" / "horde.c").read_text(encoding="utf-8")
PICKUPS_C = (ROOT / "source" / "pickups.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


class AbanderadoContractTest(unittest.TestCase):
    def test_tuning_and_constants_match_design(self):
        self.assertIn("ABANDERADO_SPAWN_FRAMES 7200", GAMEPLAY_H)
        self.assertIn("ABANDERADO_MAX_MONAGUILLOS 8", GAMEPLAY_H)
        self.assertIn("MONAGUILLO_EMERGE_FRAMES 30", GAMEPLAY_H)
        self.assertIn(".max_hp = 1200", GAMEPLAY_C)

    def test_monaguillo_is_invulnerable_while_emerging(self):
        hit_fn = GAMEPLAY_C.split("void enemy_hit(")[1].split("\n}")[0]
        self.assertIn("ENEMY_STATE_EMERGE", hit_fn)

    def test_abanderado_forces_healing_cross_drop(self):
        fn = PICKUPS_C.split("void pickups_enemy_killed(")[1].split("\n}")[0]
        self.assertIn("ENEMY_TYPE_ABANDERADO", fn)

    def test_puddle_and_bar_colors_are_desaturated(self):
        puddle_fn = ENEMY_AI_C.split("void enemy_puddles_render(")[1].split("\n}")[0]
        rgb_calls = re.findall(r"RGB15\((\d+),\s*(\d+),\s*(\d+)\)", puddle_fn)
        self.assertTrue(rgb_calls)
        for r, g, b in rgb_calls:
            self.assertLess(max(int(r), int(g), int(b)), 28)

    def test_no_float_in_abanderado_code(self):
        for src in (ENEMY_AI_C, HORDE_C, PICKUPS_C):
            self.assertNotRegex(src, r"\b(float|double)\b")

    def test_main_renders_puddles_point_clip_and_bar(self):
        self.assertIn("enemy_puddles_render(", MAIN_C)
        self.assertIn("CLIP_ABANDERADO_POINT", MAIN_C)
        self.assertIn("ENEMY_TYPE_ABANDERADO", MAIN_C)


if __name__ == "__main__":
    unittest.main()
