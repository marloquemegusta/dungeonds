from pathlib import Path
import re
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "assets" / "effects" / "bone_lance" / "bone_lance_e30.png"
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
BAKER = (ROOT / "tools" / "bake_bone_lance.py").read_text(encoding="utf-8")


class BoneLanceContract(unittest.TestCase):
    def test_bake_has_eight_small_readable_screen_directions(self):
        self.assertTrue(SHEET.is_file())
        with Image.open(SHEET) as sheet:
            sheet = sheet.convert("RGBA")
            self.assertEqual(sheet.size, (64, 64 * 8))
            boxes = []
            for direction in range(8):
                frame = sheet.crop((0, direction * 64, 64, (direction + 1) * 64))
                box = frame.getchannel("A").getbbox()
                self.assertIsNotNone(box, f"empty direction {direction}")
                boxes.append((box[2] - box[0], box[3] - box[1]))
            self.assertLessEqual(max(max(size) for size in boxes), 12)
            for direction in (0, 4):
                self.assertGreater(boxes[direction][1], boxes[direction][0])
            for direction in (2, 6):
                self.assertGreater(boxes[direction][0], boxes[direction][1])

    def test_bone_pellet_is_under_one_meter_and_volley_is_clear(self):
        scale = float(re.search(r"root\.scale = \(([^,]+),", BAKER).group(1))
        shaft_length_m = 2.05 * scale
        damage = int(re.search(r"#define LANCE_DAMAGE (\d+)", MAIN).group(1))
        pellets = int(re.search(r"#define LANCE_PELLETS (\d+)", MAIN).group(1))
        skeleton_hp = int(re.search(r"char_id == CHAR_CHARGER \? (\d+) : (\d+)", MAIN).group(2))
        charger_hp = int(re.search(r"char_id == CHAR_CHARGER \? (\d+) : (\d+)", MAIN).group(1))
        self.assertLessEqual(shaft_length_m, 1.0)
        self.assertEqual((damage, pellets, skeleton_hp, charger_hp), (10, 5, 40, 90))
        self.assertEqual((skeleton_hp + damage * pellets - 1) // (damage * pellets), 1)
        self.assertEqual((charger_hp + damage * pellets - 1) // (damage * pellets), 2)
        self.assertRegex(MAIN, r"for \(int pellet = 0; pellet < LANCE_PELLETS; pellet\+\+\)")

    def test_both_ds_aim_paths_are_wired_to_lance_fire(self):
        self.assertIn("if (touch_down || (keys & KEY_A)) lance_fire", MAIN)
        self.assertIn("touchRead(&touch);", MAIN)
        self.assertIn("nearest_enemy_screen(&aim_x, &aim_y)", MAIN)


if __name__ == "__main__":
    unittest.main()
