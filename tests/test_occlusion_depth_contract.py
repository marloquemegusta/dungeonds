"""Synthetic painter contract plus checks on the real generated FBX mask."""
from pathlib import Path
import re
import unittest

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORLD_HEADER = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
WORLD_W = int(re.search(r"#define WORLD_W (\d+)", WORLD_HEADER).group(1))
WORLD_H = int(re.search(r"#define WORLD_H (\d+)", WORLD_HEADER).group(1))


def compose_wall_actor(base, wall_depth, actor_depth, wall_color, actor_color):
    """Small software example of the depth ordering used by the runtime painter."""
    frame = list(base)
    if wall_depth <= actor_depth:
        frame[1] = wall_color
        frame[2] = wall_color
        frame[2] = actor_color
    else:
        frame[2] = actor_color
        frame[1] = wall_color
        frame[2] = wall_color
    return frame


class OcclusionDepthContractTest(unittest.TestCase):
    def test_actor_depth_relative_to_same_wall(self):
        base = ["floor"] * 4
        self.assertEqual(compose_wall_actor(base, 20, 10, "wall", "actor")[2], "wall")
        self.assertEqual(compose_wall_actor(base, 20, 30, "wall", "actor")[2], "actor")
        self.assertEqual(compose_wall_actor(base, 20, 30, "wall", "actor")[0], "floor")

    def test_visible_floor_sample_stays_out_of_upper_mask(self):
        legacy_path = ROOT / "assets/diablo_test/dungeon_color.png"
        if not legacy_path.exists():
            self.skipTest("assets/diablo_test legacy files not present")
        color = Image.open(legacy_path).convert("RGB")
        mask = Image.open(ROOT / "assets/diablo_test/dungeon_upper_mask.png").convert("L")
        self.assertEqual(color.size, (512, 512))
        self.assertEqual(mask.size, (512, 512))
        # (218,236) is a visible stone-floor pixel in the rendered color bake,
        # selected from the central room beside the barrel, not from collision data.
        floor_rgb = color.getpixel((218, 236))
        self.assertGreater(floor_rgb[0], floor_rgb[1])
        self.assertGreater(floor_rgb[1], floor_rgb[2])
        self.assertGreater(sum(floor_rgb), 100)
        self.assertEqual(mask.getpixel((218, 236)), 0, "visible floor must remain outside upper-geometry mask")
        image = mask
        white = sum(value > 127 for value in image.getdata())
        self.assertGreater(white, 1000, "upper wall/arch mask unexpectedly empty")
        self.assertLess(white, 512 * 512 // 2, "upper mask swallowed most floor pixels")

    def test_generated_depth_runs_are_nonempty_and_world_bounded(self):
        source = (ROOT / "source/dungeon_occlusion.c").read_text(encoding="ascii")
        self.assertIn("g_dungeon_occlusion_run_count =", source)
        run_count = int(re.search(r"g_dungeon_occlusion_run_count = (\d+)u?;", source).group(1))
        self.assertGreater(run_count, 0)
        self.assertLess(run_count, 5000, "canonical sector mask should be instanced, not duplicated per sector")
        self.assertIn("g_dungeon_occlusion_segments[DUNGEON_OCCLUSION_SEGMENTS]", source)
        self.assertNotIn("g_dungeon_upper_mask", source)
        runtime = (ROOT / "source/main.c").read_text(encoding="utf-8")
        self.assertIn("s_occlusion_depth", runtime)
        self.assertIn("build_occlusion_depth_map(s_cam_x, s_cam_y);", runtime)


if __name__ == "__main__":
    unittest.main()

