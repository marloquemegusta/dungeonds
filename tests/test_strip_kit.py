import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/strip_kit.c"
SPEC = ROOT / "assets/arenas/arenas.json"


def values(source, name):
    match = re.search(rf"{name}\[[^]]+\][^=]*=\s*\{{(.*?)\}};", source, re.S)
    if not match:
        raise AssertionError(f"missing generated array {name}")
    return [int(value, 0) for value in re.findall(r"0x[0-9A-Fa-f]+|\b\d+\b", match.group(1))]


class StripKitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC.read_text(encoding="utf-8"))
        cls.arena = next(a for a in cls.spec["kits"] if a["name"] == "strip_kit")

    def test_art_spec_contract(self):
        self.assertIn(self.spec["strip_kit"]["floor_h_tiles"], (2, 4, 8, 16))
        self.assertEqual(self.arena["image"][0], 512)
        self.assertEqual(self.arena["boundaries"], ["left", "right"])
        self.assertEqual(len(self.arena["zones"]), 1)
        self.assertEqual(self.arena["zones"][0]["accent"], "cyan")
        self.assertEqual(self.arena["zones"][0]["pattern"], "rows")
        self.assertEqual(len(self.arena["blocks"]), 3)
        for block in self.arena["blocks"]:
            self.assertEqual(block["kind"], "pillar")
            self.assertEqual(block["height_m"], 0.5)

    def test_generated_kit_contract(self):
        if not SOURCE.exists():
            self.skipTest("strip_kit.c awaits the headless lab package")
        source = SOURCE.read_text(encoding="utf-8")
        period_match = re.search(r"\.floor_h_tiles\s*=\s*(\d+)", source)
        tile_match = re.search(r"\.num_tiles\s*=\s*(\d+)", source)
        self.assertIsNotNone(period_match)
        self.assertIsNotNone(tile_match)
        period = int(period_match.group(1))
        num_tiles = int(tile_match.group(1))
        self.assertIn(period, (2, 4, 8, 16))
        self.assertEqual(16 % period, 0)
        self.assertLessEqual(num_tiles, 1024)  # real BG1 cap: bank D, 1024 tile slots

        floor_map = values(source, "s_floor_map")
        self.assertEqual(len(floor_map), 64 * period)
        self.assertTrue(all(0 <= (tile & 0x3FF) < num_tiles for tile in floor_map))  # bits 10/11 are H/V flips
        collision = values(source, "s_floor_collision")
        unpacked = [((byte >> shift) & 3) for byte in collision for shift in (0, 2, 4, 6)]
        rows = period * 2
        self.assertEqual(len(unpacked), 128 * rows)
        for y in range(rows):
            row = unpacked[y * 128:(y + 1) * 128]
            self.assertEqual(row[:12], [3] * 12)   # side walls: 6 tiles = 12 cells
            self.assertEqual(row[-12:], [3] * 12)
            self.assertTrue(all(value == 0 for value in row[12:-12]))

        stamp_rows = re.findall(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,"
            r"\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,"
            r"\s*s_stamp_\d+_tiles\s*,\s*\d+\s*,\s*[\w]+\s*\}", source)
        self.assertGreaterEqual(len(stamp_rows), 2)
        self.assertEqual(len(re.findall(r"\.num_stamps\s*=\s*\d+", source)), 1)
        for w, h, phase_col, phase_row, foot_x, foot_y, foot_w, foot_h, foot_value in stamp_rows:
            w, h, foot_x, foot_y, foot_w, foot_h, foot_value = map(
                int, (w, h, foot_x, foot_y, foot_w, foot_h, foot_value))
            self.assertLessEqual(int(phase_col), 15)
            self.assertLessEqual(int(phase_row), 15)
            self.assertIn(foot_value, (0, 1, 3))
            if foot_value:
                self.assertGreater(foot_w, 0)
                self.assertGreater(foot_h, 0)
            self.assertLessEqual(foot_x + foot_w, w * 2)
            self.assertLessEqual(foot_y + foot_h, h * 2)
        for name in re.findall(r"s_stamp_\d+_tiles", source):
            self.assertTrue(all((tile & 0x3FF) < num_tiles for tile in values(source, name)))


if __name__ == "__main__":
    unittest.main()
