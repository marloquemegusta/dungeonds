from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HordeContractTests(unittest.TestCase):
    def test_runtime_modules_have_no_floating_point_types(self):
        for name in ("horde.c", "tide.c", "pickups.c"):
            source = (ROOT / "source" / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\b(?:float|double)\b", source), name)

    def test_recycling_does_not_call_death_hook(self):
        source = (ROOT / "source" / "horde.c").read_text(encoding="utf-8")
        self.assertIn("e->active = 0", source)
        self.assertNotIn("enemy_hit(", source)
        self.assertNotIn("death_hook", source)

    def test_tide_uses_hardware_window_without_pixel_fill_loop(self):
        source = (ROOT / "source" / "tide.c").read_text(encoding="utf-8")
        self.assertIn("REG_WIN0V", source)
        self.assertIn("REG_WIN0V_SUB", source)
        self.assertIn("REG_BLDCNT", source)
        self.assertNotIn("for (int y = line; y < SCREEN_H; y++)", source)

    def test_horde_mix_is_skeleton_charger_shooter_with_a_charger_cap(self):
        header = (ROOT / "include" / "horde.h").read_text(encoding="utf-8")
        skeleton = int(re.search(r"#define HORDE_SKELETON_PERCENT (\d+)", header).group(1))
        charger = int(re.search(r"#define HORDE_CHARGER_PERCENT (\d+)", header).group(1))
        self.assertEqual((skeleton, charger, 100 - skeleton - charger), (60, 15, 25))
        self.assertIn("#define HORDE_CHARGER_MAX_ALIVE 3", header)
        source = (ROOT / "source" / "horde.c").read_text(encoding="utf-8")
        self.assertIn("s_chargers_alive < HORDE_CHARGER_MAX_ALIVE ? ENEMY_TYPE_CHARGER : ENEMY_TYPE_SKELETON", source)
        self.assertIn("e->char_id = enemy_type_char_id(e->type);", source)

    def test_tunable_defines_are_marked_in_headers(self):
        for name in ("horde.h", "tide.h", "pickups.h"):
            header = (ROOT / "include" / name).read_text(encoding="utf-8")
            for line in header.splitlines():
                if line.startswith("#define ") and re.search(r"\b(?:INTERVAL|FRAMES|CAP|CHANCE|GAP|PX|PERCENT|WIDTH|HEIGHT|ATTEMPTS|LIMIT|SIZE|RADIUS|BRIGHTNESS|SPEED|DENOMINATOR)\b", line):
                    self.assertIn("[TUNABLE-PLACEHOLDER]", line, (name, line))


if __name__ == "__main__":
    unittest.main()
