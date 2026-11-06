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

    def test_tunable_defines_are_marked_in_headers(self):
        for name in ("horde.h", "tide.h", "pickups.h"):
            header = (ROOT / "include" / name).read_text(encoding="utf-8")
            for line in header.splitlines():
                if line.startswith("#define ") and re.search(r"\b(?:INTERVAL|FRAMES|CAP|CHANCE|GAP|PX|PERCENT|WIDTH|HEIGHT|ATTEMPTS|LIMIT|SIZE|RADIUS|BRIGHTNESS|SPEED|DENOMINATOR)\b", line):
                    self.assertIn("[TUNABLE-PLACEHOLDER]", line, (name, line))


if __name__ == "__main__":
    unittest.main()
