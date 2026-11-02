"""Contract between the lab's map export, the baker and the NDS runtime.

world.png, collision.png and occlusion_depth.png must describe the same
geometry: occluders only where the render shows something, ground-contact
depths never above the pixel itself, and the baked runs/row index must be a
faithful encoding of occlusion_depth.png.
"""
from pathlib import Path
import re
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "assets/sprites/dungeon/isometric_shooter_bl"
WORLD_HEADER = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
WORLD_W = int(re.search(r"#define WORLD_W (\d+)", WORLD_HEADER).group(1))
WORLD_H = int(re.search(r"#define WORLD_H (\d+)", WORLD_HEADER).group(1))
SPAWN = (int(re.search(r"#define SPAWN_PIXEL_X (\d+)", WORLD_HEADER).group(1)),
         int(re.search(r"#define SPAWN_PIXEL_Y (\d+)", WORLD_HEADER).group(1)))


def load_rgb(name):
    return np.array(Image.open(MAP_DIR / name).convert("RGB"), dtype=np.int32)


def load_runs():
    source = (ROOT / "source/dungeon_occlusion.c").read_text(encoding="ascii")
    body = source.split("g_dungeon_occlusion_runs[]", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    runs = [tuple(map(int, m)) for m in re.findall(r"\{(\d+), (\d+), (\d+), (-?\d+)\}", body)]
    rows = source.split("g_dungeon_occlusion_row_start", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    row_start = [int(v) for v in re.findall(r"\d+", rows)]
    return runs, row_start


class MapExportCoherenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        world = load_rgb("world.png")
        occ = load_rgb("occlusion_depth.png")
        cls.void = world.max(axis=2) < 5
        cls.occluder = occ[:, :, 2] >= 128
        cls.ground_y = np.where(cls.occluder, occ[:, :, 0] * 256 + occ[:, :, 1], -1)
        cls.walkable = np.array(Image.open(MAP_DIR / "collision.png").convert("L")) >= 128
        cls.runs, cls.row_start = load_runs()

    def test_masks_share_the_render_resolution(self):
        self.assertEqual(self.void.shape, self.occluder.shape)
        self.assertEqual(self.void.shape, self.walkable.shape)

    def test_no_occluder_over_void(self):
        self.assertEqual(int((self.occluder & self.void).sum()), 0,
                         "occlusion must come from surfaces visible in world.png")

    def test_ground_contact_is_never_above_the_pixel(self):
        ys = np.arange(self.ground_y.shape[0])[:, None]
        self.assertEqual(int((self.occluder & (self.ground_y < ys)).sum()), 0)

    def test_walkable_floor_is_visible_and_contains_spawn(self):
        self.assertTrue(self.walkable[SPAWN[1], SPAWN[0]])
        # Cell-aligned grid edges may graze up to a few void pixels, never areas.
        self.assertLess(int((self.walkable & self.void).sum()), 64)

    def test_runs_encode_occlusion_depth_within_tolerance(self):
        rebuilt = np.full((WORLD_H, WORLD_W), -1, dtype=np.int32)
        for x, y, length, depth in self.runs:
            self.assertTrue(np.all(rebuilt[y, x:x + length] == -1), "runs must not overlap")
            rebuilt[y, x:x + length] = depth
        h, w = self.ground_y.shape
        covered = rebuilt[:h, :w] >= 0
        self.assertTrue(np.array_equal(covered, self.occluder))
        err = rebuilt[:h, :w][covered] - self.ground_y[covered]
        self.assertGreaterEqual(int(err.min()), 0, "runs store the deepest ground Y of the run")
        self.assertLessEqual(int(err.max()), 1)

    def test_row_index_matches_sorted_runs(self):
        self.assertEqual(len(self.row_start), WORLD_H + 1)
        self.assertEqual(self.row_start[-1], len(self.runs))
        for y in range(WORLD_H):
            row = self.runs[self.row_start[y]:self.row_start[y + 1]]
            self.assertTrue(all(r[1] == y for r in row))
            self.assertEqual([r[0] for r in row], sorted(r[0] for r in row))


if __name__ == "__main__":
    unittest.main()
