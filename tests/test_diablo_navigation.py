import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import numpy as np

from diablo_navigation import (choose_spawn, largest_walkable_component, project_camera_plane_to_ground,
                               spawn_is_clear, classify_vertical_hits, WALKABLE, OBSTACLE, VOID)


class DiabloNavigationTests(unittest.TestCase):
    def test_low_door_arch_clears_at_requested_height_and_support_tolerance(self):
        # Measured vertical hits at the arch soffit: floor at 0.0828 and lintel at 0.1356–0.1477.
        hits = [0.1664, 0.1614, 0.1477, 0.1356, 0.0828, 0.0099]
        self.assertEqual(classify_vertical_hits(hits), WALKABLE)
        self.assertEqual(classify_vertical_hits(hits, support_tolerance=0.008), VOID)
        self.assertEqual(classify_vertical_hits(hits, player_height=0.08), OBSTACLE)

    def test_unmatched_floor_crossing_below_feet_does_not_block(self):
        self.assertEqual(classify_vertical_hits([0.07655, 0.07449, 0.00988]), WALKABLE)
        self.assertEqual(classify_vertical_hits([0.07950, 0.07488, 0.01051]), WALKABLE)
        self.assertEqual(classify_vertical_hits([0.17, 0.12, 0.07301]), OBSTACLE)
        self.assertEqual(classify_vertical_hits([0.17, 0.15, 0.13, 0.12, 0.07301]), OBSTACLE)

    def test_reported_room_points_are_clear_for_player_footprint(self):
        import re
        source_path = Path(__file__).resolve().parents[1] / "source" / "diablo_dungeon.c"
        source = source_path.read_text(encoding="utf-8")
        header = (Path(__file__).resolve().parents[1] / "include" / "diablo_dungeon.h").read_text(encoding="utf-8")
        payload = re.search(r"g_dungeon_collision[^=]*=\s*\{([^}]+)\}", source).group(1)
        packed = np.fromiter((int(value, 0) for value in re.findall(r"0x[0-9A-Fa-f]+|\b\d+\b", payload)), dtype=np.uint8)
        width = int(re.search(r"#define COLLISION_W (\d+)", header).group(1))
        height = int(re.search(r"#define COLLISION_H (\d+)", header).group(1))
        scale = int(re.search(r"#define COLLISION_SCALE (\d+)", header).group(1))
        spawn_x = int(re.search(r"#define SPAWN_PIXEL_X (\d+)", header).group(1))
        spawn_y = int(re.search(r"#define SPAWN_PIXEL_Y (\d+)", header).group(1))
        indices = np.arange(width * height, dtype=np.uint32)
        values = (packed[indices >> 2] >> ((indices & 3) * 2)) & 3
        grid = values.reshape((height, width))
        offsets = ((0, 0), (-16, 0), (16, 0), (0, -12), (0, 12), (-12, -8), (-12, 8), (12, -8), (12, 8))
        for dx, dy in offsets:
            with self.subTest(offset=(dx, dy)):
                cx = (spawn_x + dx) // scale
                cy = (spawn_y + dy) // scale
                self.assertEqual(grid[cy, cx] & 0x01, 0)

    def test_vertical_intervals_respect_hero_height_and_support(self):
        floor, height = 0.07301, 0.09
        self.assertEqual(classify_vertical_hits([floor, 0.0], floor, height), WALKABLE)
        self.assertEqual(classify_vertical_hits([0.197, floor, floor, 0.0], floor, height), OBSTACLE)
        self.assertEqual(classify_vertical_hits([0.197, 0.17, floor, 0.0], floor, height), WALKABLE)
        self.assertEqual(classify_vertical_hits([0.10, 0.09, floor, 0.0], floor, height), OBSTACLE)
        self.assertEqual(classify_vertical_hits([0.197, floor, 0.0], floor, height), OBSTACLE)
        self.assertEqual(classify_vertical_hits([], floor, height), VOID)

    def test_camera_pixel_ray_intersects_z0(self):
        from math import cos, radians, sin
        el, az = radians(30), radians(45)
        forward = (-cos(el) * cos(az), cos(el) * sin(az), -sin(el))
        right = (forward[1], -forward[0], 0.0)
        right_len = sum(v * v for v in right) ** 0.5
        right = tuple(v / right_len for v in right)
        up = (right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2], right[0] * forward[1] - right[1] * forward[0])
        p = project_camera_plane_to_ground((0, 0, 0.05), right, up, forward, 0, 0)
        self.assertAlmostEqual(p[0], -0.06123724357, places=7)
        self.assertAlmostEqual(p[1], 0.06123724357, places=7)
        self.assertAlmostEqual(p[2], 0.0, places=7)

    def test_spawn_is_clear_and_in_largest_connected_region(self):
        grid = np.full((18, 24), 2, dtype=np.uint8)
        grid[2:15, 2:20] = 0
        grid[8, 10] = 1
        grid[1:5, 21:24] = 0  # smaller disconnected pocket
        x, y, component, sizes = choose_spawn(grid)
        labels, _ = largest_walkable_component(grid)
        self.assertEqual(component, int(np.argmax(sizes)))
        self.assertEqual(labels[y, x], component)
        self.assertTrue(spawn_is_clear(grid, x, y))
        self.assertEqual(sizes[component], 13 * 18 - 1)

    def test_no_clear_spawn_fails_in_narrow_corridor(self):
        grid = np.full((8, 12), 2, dtype=np.uint8)
        grid[3, 1:11] = 0
        with self.assertRaisesRegex(ValueError, "no 1-cell clearance spawn"):
            choose_spawn(grid)

    def test_components_use_four_way_connectivity(self):
        grid = np.full((3, 3), 2, dtype=np.uint8)
        grid[0, 0] = grid[1, 1] = 0
        _, sizes = largest_walkable_component(grid)
        self.assertEqual(sorted(sizes), [1, 1])


if __name__ == "__main__":
    unittest.main()





