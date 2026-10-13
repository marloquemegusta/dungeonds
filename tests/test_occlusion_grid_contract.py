from pathlib import Path
import random
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORLD_HEADER = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
WORLD_W = int(re.search(r"#define WORLD_W (\d+)", WORLD_HEADER).group(1))
WORLD_H = int(re.search(r"#define WORLD_H (\d+)", WORLD_HEADER).group(1))
BLOCK = 8
SCREEN_W = 256
SCREEN_H = 192
GRID_W = (SCREEN_W + BLOCK - 1) // BLOCK
GRID_H = (SCREEN_H + BLOCK - 1) // BLOCK
DEPTH_W = (SCREEN_W + 1) // 2
DEPTH_H = (SCREEN_H + 1) // 2


def load_maps(cam_x, cam_y):
    source = (ROOT / "source/dungeon_occlusion.c").read_text(encoding="ascii")
    body = source.split("g_dungeon_occlusion_runs[]", 1)[1].split("= {", 1)[1].split("};", 1)[0]
    runs = [tuple(map(int, match)) for match in re.findall(r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(-?\d+)\s*\}", body)]
    depth = [[-1] * SCREEN_W for _ in range(SCREEN_H)]
    block_max = [[-1] * GRID_W for _ in range(GRID_H)]
    depth_coarse = [[-1] * DEPTH_W for _ in range(DEPTH_H)]
    for x, y, length, value in runs:
        local_y = y - cam_y
        if not 0 <= local_y < SCREEN_H:
            continue
        x0, x1 = max(x, cam_x), min(x + length, cam_x + SCREEN_W)
        for world_x in range(x0, x1):
            px = world_x - cam_x
            depth[local_y][px] = value
            coarse = depth_coarse[local_y // 2]
            if value > coarse[px // 2]:
                coarse[px // 2] = value
        for bx in range((x0 - cam_x) // BLOCK, (x1 - 1 - cam_x) // BLOCK + 1):
            if x0 < x1:
                block_max[local_y // BLOCK][bx] = max(block_max[local_y // BLOCK][bx], value)
    return runs, depth, block_max, depth_coarse


def may_block(block_max, x0, x1, y, actor_depth):
    if not 0 <= y < SCREEN_H:
        return False
    x0 = max(0, x0)
    x1 = min(SCREEN_W, x1)
    if x0 >= x1:
        return False
    return any(value > actor_depth for value in block_max[y // BLOCK][x0 // BLOCK:(x1 - 1) // BLOCK + 1])


class OcclusionGridContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cam_x = WORLD_W // 2 - SCREEN_W // 2
        cls.cam_y = WORLD_H // 2 - SCREEN_H // 2
        cls.runs, cls.depth, cls.block_max, cls.depth_coarse = load_maps(cls.cam_x, cls.cam_y)

    def test_grid_never_misses_an_occluding_pixel(self):
        self.assertGreater(len(self.runs), 0)
        rng = random.Random(0xD5)
        for _ in range(20000):
            y = rng.randrange(-8, SCREEN_H + 8)
            x0 = rng.randrange(-8, SCREEN_W + 8)
            x1 = x0 + rng.randrange(1, 80)
            actor_depth = rng.randrange(-1, max(WORLD_W, WORLD_H) + 1)
            exact = (0 <= y < SCREEN_H and any(
                self.depth[y][x] > actor_depth
                for x in range(max(0, x0), min(SCREEN_W, x1))))
            if exact:
                self.assertTrue(may_block(self.block_max, x0, x1, y, actor_depth))
            elif not may_block(self.block_max, x0, x1, y, actor_depth):
                continue

    def test_two_by_two_depth_cells_never_drop_frontmost_occlusion(self):
        rng = random.Random(0x2D)
        for _ in range(20000):
            x = rng.randrange(SCREEN_W)
            y = rng.randrange(SCREEN_H)
            actor_depth = rng.randrange(-1, max(WORLD_W, WORLD_H) + 1)
            if self.depth[y][x] > actor_depth:
                self.assertGreater(self.depth_coarse[y // 2][x // 2], actor_depth)

    def test_runtime_uses_conservative_gate_before_exact_depth_blit(self):
        source = (ROOT / "source/main.c").read_text(encoding="utf-8")
        self.assertIn("OCCLUSION_GRID_SHIFT 3", source)
        self.assertIn("OCCLUSION_DEPTH_SHIFT 1", source)
        self.assertIn("OCCLUSION_GRID_W ((SCREEN_W", source)
        self.assertIn("int local_y = y - s_occlusion_cam_y;", source)
        self.assertIn("occlusion_may_block_span(world_x0, world_x1, world_y, depth)", source)
        self.assertIn("depth_y * OCCLUSION_DEPTH_W + depth_x", source)


if __name__ == "__main__":
    unittest.main()
