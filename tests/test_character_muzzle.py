import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPRITES = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
HEADER = (ROOT / "include" / "player_sprite.h").read_text(encoding="utf-8")
CHAR_DIR = ROOT / "assets" / "sprites" / "characters"
# Order of the C tables (NUM_CHARACTERS): hero, charger, necron.
CHARACTERS = ["marine", "charger", "necron"]
ARMED = ["marine", "necron"]
TOLERANCE = 2


def settings(name):
    return json.loads((CHAR_DIR / name / "settings.json").read_text(encoding="utf-8"))


def c_muzzle_table():
    start = SPRITES.index("const int8_t g_character_muzzle[")
    body = SPRITES[SPRITES.index("=", start):SPRITES.index("};\n\n", start)]
    nums = [int(v) for v in re.findall(r"-?\d+", body)]
    assert len(nums) == 3 * 8 * 8 * len(CHARACTERS), len(nums)
    it = iter(nums)
    return [[[[next(it) for _ in range(3)] for _ in range(8)] for _ in range(8)] for _ in CHARACTERS]


class CharacterMuzzleTests(unittest.TestCase):
    def test_header_declares_table(self):
        self.assertIn(
            "extern const int8_t g_character_muzzle[NUM_CHARACTERS][PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3];",
            HEADER,
        )

    def test_armed_characters_have_valid_muzzles(self):
        for name in ARMED:
            with self.subTest(character=name):
                s = settings(name)
                muzzle = s["dirMuzzle"]
                self.assertEqual(len(muzzle), 8)
                ax, ay = s["anchor"]
                for d in range(8):
                    self.assertEqual(len(muzzle[d]), 8)
                    bx, by, bw, bh = s["dirBounds"][d]
                    for f in range(8):
                        gx, gy, h = muzzle[d][f]
                        for v in (gx, gy, h):
                            self.assertTrue(-128 <= v <= 127, (name, d, f, v))
                        self.assertTrue(8 <= h <= 40, (name, d, f, "h", h))
                        px, py = ax + gx, ay + gy - h
                        self.assertTrue(
                            bx - TOLERANCE <= px <= bx + bw - 1 + TOLERANCE
                            and by - TOLERANCE <= py <= by + bh - 1 + TOLERANCE,
                            (name, d, f, (px, py), s["dirBounds"][d]),
                        )

    def test_charger_has_no_muzzle(self):
        self.assertNotIn("dirMuzzle", settings("charger"))
        table = c_muzzle_table()[CHARACTERS.index("charger")]
        self.assertTrue(all(v == 0 for d in table for f in d for v in f))

    def test_c_table_matches_settings(self):
        table = c_muzzle_table()
        for name in ARMED:
            with self.subTest(character=name):
                self.assertEqual(table[CHARACTERS.index(name)], settings(name)["dirMuzzle"])


if __name__ == "__main__":
    unittest.main()
