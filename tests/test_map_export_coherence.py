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
LEGACY_DIR = ROOT / "assets/sprites/dungeon/isometric_shooter_bl"


def package_dir(stem):
    """Lab package of a baked arena: source/arena_<stem>.c <- assets/sprites/arenas/<stem>/."""
    if stem == "legacy":
        return LEGACY_DIR
    return ROOT / "assets/sprites/arenas" / stem


def baked_arenas():
    return [p.stem[len("arena_"):] for p in sorted((ROOT / "source").glob("arena_*.c"))]


def load_rgb(directory, name):
    return np.array(Image.open(directory / name).convert("RGB"), dtype=np.int32)


def load_arena_source(stem):
    source = (ROOT / "source" / f"arena_{stem}.c").read_text(encoding="utf-8")
    field = lambda name: int(re.search(rf"\.{name} = (\d+)", source).group(1))
    body = source.split("s_occlusion_runs[]", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    runs = [tuple(map(int, m)) for m in re.findall(r"\{(\d+), (\d+), (\d+), (-?\d+)\}", body)]
    rows = source.split("s_occlusion_row_start", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    row_start = [int(v) for v in re.findall(r"\d+", rows)]
    return field("world_w"), field("world_h"), (field("player_x"), field("player_y")), runs, row_start


class MapExportCoherenceTest(unittest.TestCase):
    def check_arena(self, stem):
        directory = package_dir(stem)
        world_w, world_h, spawn, runs, row_start = load_arena_source(stem)
        world = load_rgb(directory, "world.png")
        occ = load_rgb(directory, "occlusion_depth.png")
        void = world.max(axis=2) < 5
        occluder = occ[:, :, 2] >= 128
        ground_y = np.where(occluder, occ[:, :, 0] * 256 + occ[:, :, 1], -1)
        walkable = np.array(Image.open(directory / "collision.png").convert("L")) >= 128

        # The masks share the render resolution.
        self.assertEqual(void.shape, occluder.shape)
        self.assertEqual(void.shape, walkable.shape)
        # Occlusion must come from surfaces visible in world.png.
        self.assertEqual(int((occluder & void).sum()), 0)
        # Ground contact is never above the pixel itself.
        ys = np.arange(ground_y.shape[0])[:, None]
        self.assertEqual(int((occluder & (ground_y < ys)).sum()), 0)
        # The walkable floor is visible and contains the start; grid edges may graze a few void pixels.
        self.assertTrue(walkable[spawn[1], spawn[0]])
        self.assertLess(int((walkable & void).sum()), 64)
        # The baked runs encode occlusion_depth.png within tolerance and never overlap.
        rebuilt = np.full((world_h, world_w), -1, dtype=np.int32)
        for x, y, length, depth in runs:
            self.assertTrue(np.all(rebuilt[y, x:x + length] == -1), "runs must not overlap")
            rebuilt[y, x:x + length] = depth
        h, w = ground_y.shape
        covered = rebuilt[:h, :w] >= 0
        self.assertTrue(np.array_equal(covered, occluder))
        if covered.any():
            err = rebuilt[:h, :w][covered] - ground_y[covered]
            self.assertGreaterEqual(int(err.min()), 0, "runs store the deepest ground Y of the run")
            self.assertLessEqual(int(err.max()), 1)
        # The row index matches the sorted runs.
        self.assertEqual(len(row_start), world_h + 1)
        self.assertEqual(row_start[-1], len(runs))
        for y in range(world_h):
            row = runs[row_start[y]:row_start[y + 1]]
            self.assertTrue(all(r[1] == y for r in row))
            self.assertEqual([r[0] for r in row], sorted(r[0] for r in row))

    def test_every_baked_arena_is_coherent_with_its_lab_package(self):
        stems = baked_arenas()
        self.assertTrue(stems, "no baked arenas")
        for stem in stems:
            with self.subTest(arena=stem):
                self.check_arena(stem)


if __name__ == "__main__":
    unittest.main()
