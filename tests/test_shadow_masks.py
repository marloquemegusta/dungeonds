from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from shadow_masks import read_shadow_coverage, shadow_coverage


OBJECT_BASES = (
    "WR_crypt", "WC_crypt", "WR_buttress", "WC_buttress",
    "WR_ossuary", "WC_ossuary", "P_soul", "P_broken", "AR_row", "AR_col",
)
ROTATIONS = (0, 90, 180, 270)
PLAYER_SHADOW = ROOT / "assets" / "characters" / "monster" / "player_e30_shadow.png"


class ShadowMaskContract(unittest.TestCase):
    def assert_coverage(self, path, expected_size):
        self.assertTrue(path.is_file(), f"missing shadow bake: {path}")
        with Image.open(path) as image:
            image = image.convert("RGBA")
            self.assertEqual(image.size, (128, 128), str(path))
            source = read_shadow_coverage(path, (128, 128))
            offset = (128 - expected_size[0]) // 2
            coverage = [source[(offset + y) * 128 + offset + x]
                        for y in range(expected_size[1])
                        for x in range(expected_size[0])]
            self.assertGreater(max(coverage), 16, f"empty shadow mask: {path}")
            self.assertEqual(min(coverage), 0, f"mask has no transparent area: {path}")
            self.assertLess(coverage.count(255), len(coverage) // 2)

    def test_every_object_orientation_has_a_3d_mask(self):
        folder = ROOT / "assets" / "dungeon_e30"
        for base in OBJECT_BASES:
            for rotation in ROTATIONS:
                name = f"{base}_r{rotation:03d}_shadow.png"
                with self.subTest(asset=name):
                    self.assert_coverage(folder / name, (128, 128))

    @unittest.skipUnless(PLAYER_SHADOW.is_file(), "player shadow bake not generated yet")
    def test_player_has_one_3d_mask_per_facing(self):
        path = PLAYER_SHADOW
        with Image.open(path) as sheet:
            sheet = sheet.convert("RGBA")
            self.assertEqual(sheet.size, (8 * 96, 96))
            for direction in range(8):
                with self.subTest(direction=direction):
                    crop = sheet.crop((direction * 96, 0, (direction + 1) * 96, 96))
                    cell = shadow_coverage(crop, f"player facing {direction}")
                    self.assertGreater(max(cell), 16)
                    self.assertEqual(min(cell), 0)


if __name__ == "__main__":
    unittest.main()
