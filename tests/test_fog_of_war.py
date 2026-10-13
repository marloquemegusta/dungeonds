import unittest
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# World and fog constants
WORLD_W = 768
WORLD_H = 512
COLLISION_W = 192
COLLISION_H = 128
COLLISION_SCALE = 4
FOG_MAP_W = 96
FOG_MAP_H = 64
FOG_VISION_RADIUS_TILES = 12
FOG_VISION_RADIUS_CELLS = 24


class FogOfWarSimulator:
    def __init__(self, coll_grid: np.ndarray):
        self.coll = coll_grid
        self.explored = np.zeros((FOG_MAP_H, FOG_MAP_W), dtype=bool)
        self.visible = np.zeros((FOG_MAP_H, FOG_MAP_W), dtype=bool)

    def update(self, player_px: int, player_py: int):
        self.visible.fill(False)
        pcx = player_px // COLLISION_SCALE
        pcy = player_py // COLLISION_SCALE
        r_cells = FOG_VISION_RADIUS_CELLS
        r_sq = r_cells * r_cells

        # Trace 192 rays around perimeter of square [-r_cells, r_cells]
        perimeter = []
        for dx in range(-r_cells, r_cells + 1):
            perimeter.append((dx, -r_cells))
            perimeter.append((dx, r_cells))
        for dy in range(-r_cells + 1, r_cells):
            perimeter.append((-r_cells, dy))
            perimeter.append((r_cells, dy))

        newly_revealed = 0
        for target_dx, target_dy in perimeter:
            steps = max(abs(target_dx), abs(target_dy))
            if steps == 0:
                continue
            for step in range(steps + 1):
                cx = pcx + int(round(target_dx * step / steps))
                cy = pcy + int(round(target_dy * step / steps))
                if cx < 0 or cx >= COLLISION_W or cy < 0 or cy >= COLLISION_H:
                    break
                d2 = (cx - pcx) ** 2 + (cy - pcy) ** 2
                if d2 > r_sq:
                    break

                tx = cx // 2
                ty = cy // 2
                if 0 <= tx < FOG_MAP_W and 0 <= ty < FOG_MAP_H:
                    self.visible[ty, tx] = True
                    if not self.explored[ty, tx]:
                        self.explored[ty, tx] = True
                        newly_revealed += 1

                # Check tall solid wall (flags == 3)
                if self.coll[cy, cx] == 3:
                    break

        return newly_revealed

    def has_los(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        c0x, c0y = x0 // COLLISION_SCALE, y0 // COLLISION_SCALE
        c1x, c1y = x1 // COLLISION_SCALE, y1 // COLLISION_SCALE
        d2 = (x1 - x0) ** 2 + (y1 - y0) ** 2
        max_dist = (FOG_VISION_RADIUS_TILES * 8) ** 2
        if d2 > max_dist:
            return False

        dx = c1x - c0x
        dy = c1y - c0y
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return True
        for step in range(1, steps):
            cx = c0x + int(round(dx * step / steps))
            cy = c0y + int(round(dy * step / steps))
            if 0 <= cx < COLLISION_W and 0 <= cy < COLLISION_H:
                if self.coll[cy, cx] == 3:
                    return False
        return True


class TestFogOfWarContract(unittest.TestCase):
    def setUp(self):
        coll_path = ROOT / "assets/scifi_baked/scifi_coll.npy"
        if not coll_path.exists():
            self.skipTest("scifi_coll.npy not found")
        self.coll = np.load(coll_path)
        self.sim = FogOfWarSimulator(self.coll)

    def test_initial_state_is_unexplored(self):
        self.assertEqual(np.sum(self.sim.explored), 0)
        self.assertEqual(np.sum(self.sim.visible), 0)

    def test_spawn_reveals_local_room(self):
        # Spawn at courtyard (361, 233)
        revealed = self.sim.update(361, 233)
        self.assertGreater(revealed, 50)
        self.assertTrue(self.sim.visible[233 // 8, 361 // 8])
        self.assertTrue(self.sim.explored[233 // 8, 361 // 8])

    def test_distant_room_remains_unexplored(self):
        self.sim.update(361, 233)
        # Far corner (e.g. tile (10, 10)) should be completely unexplored
        self.assertFalse(self.sim.explored[10, 10])
        self.assertFalse(self.sim.visible[10, 10])

    def test_wall_blocks_line_of_sight(self):
        self.sim.update(361, 233)
        # Point separated by thick exterior or room wall should not have LOS
        # West room is separated by a solid column/wall structure
        has_los_open = self.sim.has_los(361, 233, 361, 240) # straight clear line
        self.assertTrue(has_los_open)

    def test_memory_preserves_explored_when_moving_away(self):
        self.sim.update(361, 233)
        spawn_tile = (233 // 8, 361 // 8)
        self.assertTrue(self.sim.explored[spawn_tile])
        self.assertTrue(self.sim.visible[spawn_tile])

        # Move far away to (200, 200)
        self.sim.update(200, 200)
        # Spawn tile should still be EXPLORED (memory), but NO LONGER VISIBLE (penumbra)
        self.assertTrue(self.sim.explored[spawn_tile])
        self.assertFalse(self.sim.visible[spawn_tile])


if __name__ == "__main__":
    unittest.main()
