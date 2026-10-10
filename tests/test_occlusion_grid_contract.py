from pathlib import Path
import random
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORLD = 512
BLOCK = 8
GRID = WORLD // BLOCK


def load_maps():
    source = (ROOT / "source/dungeon_occlusion.c").read_text(encoding="ascii")
    body = source.split("g_dungeon_occlusion_runs[]", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    runs = [tuple(map(int, match)) for match in re.findall(r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+)\s*\}", body)]
    depth = [[-1] * WORLD for _ in range(WORLD)]
    block_max = [[-1] * GRID for _ in range(GRID)]
    for x, y, length, value in runs:
        for px in range(x, x + length):
            depth[y][px] = value
        for bx in range(x // BLOCK, (x + length - 1) // BLOCK + 1):
            block_max[y // BLOCK][bx] = max(block_max[y // BLOCK][bx], value)
    return runs, depth, block_max


def may_block(block_max, x0, x1, y, actor_depth):
    if not 0 <= y < WORLD:
        return False
    x0 = max(0, x0)
    x1 = min(WORLD, x1)
    if x0 >= x1:
        return False
    return any(value > actor_depth for value in block_max[y // BLOCK][x0 // BLOCK:(x1 - 1) // BLOCK + 1])


class OcclusionGridContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs, cls.depth, cls.block_max = load_maps()

    def test_grid_never_misses_an_occluding_pixel(self):
        self.assertEqual(len(self.runs), 16908)
        rng = random.Random(0xD5)
        for _ in range(20000):
            y = rng.randrange(-8, WORLD + 8)
            x0 = rng.randrange(-8, WORLD + 8)
            x1 = x0 + rng.randrange(1, 80)
            actor_depth = rng.randrange(-1, WORLD + 1)
            exact = (0 <= y < WORLD and any(
                self.depth[y][x] > actor_depth
                for x in range(max(0, x0), min(WORLD, x1))))
            if exact:
                self.assertTrue(may_block(self.block_max, x0, x1, y, actor_depth))
            elif not may_block(self.block_max, x0, x1, y, actor_depth):
                continue

    def test_runtime_uses_conservative_gate_before_exact_depth_blit(self):
        source = (ROOT / "source/main.c").read_text(encoding="utf-8")
        self.assertIn("OCCLUSION_GRID_SHIFT 3", source)
        self.assertIn("occlusion_may_block_span(world_x0, world_x1, world_y, depth)", source)
        self.assertIn("depth_row[world_x] <= depth", source)


if __name__ == "__main__":
    unittest.main()
