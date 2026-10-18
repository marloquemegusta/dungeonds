import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

COLLISION_W = 192
COLLISION_H = 128
COLLISION_SCALE = 4


def los_has_line_of_sight(px0: int, py0: int, px1: int, py1: int, max_radius_px: int, coll: np.ndarray) -> bool:
    dx = px1 - px0
    dy = py1 - py0
    if max_radius_px > 0:
        if dx * dx + dy * dy > max_radius_px * max_radius_px:
            return False

    c0x = px0 // COLLISION_SCALE
    c0y = py0 // COLLISION_SCALE
    c1x = px1 // COLLISION_SCALE
    c1y = py1 // COLLISION_SCALE

    def get_flags(cx: int, cy: int) -> int:
        if cx < 0 or cx >= COLLISION_W or cy < 0 or cy >= COLLISION_H:
            return 3
        return int(coll[cy, cx])

    adx = c1x - c0x
    ady = c1y - c0y
    abs_dx = abs(adx)
    abs_dy = abs(ady)
    sx = -1 if adx < 0 else 1
    sy = -1 if ady < 0 else 1
    err = (abs_dx if abs_dx > abs_dy else -abs_dy) // 2

    x = c0x
    y = c0y
    while True:
        if x == c1x and y == c1y:
            return True
        if get_flags(x, y) == 3:
            return False

        e2 = err
        if e2 > -abs_dx:
            err -= abs_dy
            x += sx
        if e2 < abs_dy:
            err += abs_dx
            y += sy


class TestLineOfSightContract(unittest.TestCase):
    def setUp(self):
        self.grid = np.zeros((COLLISION_H, COLLISION_W), dtype=np.uint8)
        # Place a vertical wall from y=10 to y=30 at x=20
        self.grid[10:31, 20] = 3

    def test_clear_los_open_area(self):
        # Ray from (40, 40) to (60, 60) in open space (cells 10,10 to 15,15)
        self.assertTrue(los_has_line_of_sight(40, 40, 60, 60, 100, self.grid))

    def test_blocked_by_wall(self):
        # Ray crossing wall at cell x=20 (world px 80)
        # From cell (15, 20) -> px (60, 80) to cell (25, 20) -> px (100, 80)
        self.assertFalse(los_has_line_of_sight(60, 80, 100, 80, 100, self.grid))

    def test_range_limit(self):
        # Ray within clear area (py=16, cy=4) with distance = 50 px
        # radius limit = 40 px -> out of range (False)
        self.assertFalse(los_has_line_of_sight(40, 16, 90, 16, 40, self.grid))
        # radius limit = 60 px -> in range (True)
        self.assertTrue(los_has_line_of_sight(40, 16, 90, 16, 60, self.grid))

    def test_unconstrained_radius(self):
        # max_radius_px <= 0 means unconstrained -> in range (True)
        self.assertTrue(los_has_line_of_sight(40, 16, 90, 16, 0, self.grid))


if __name__ == "__main__":
    unittest.main()
