import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.c"


class FloorBackgroundContractTest(unittest.TestCase):
    def test_floor_uses_hardware_ring_map_streaming(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("static void update_screen_hardware_bg", source)
        self.assertIn("bg_world_tile(world_x, world_y)", source)
        self.assertIn("memcpy(tile_vram + (uint32_t)slot * 64", source)
        self.assertIn("REG_BG1HOFS =", source)
        self.assertIn("int top_cam_y = s_cam_y - SCREEN_H;", source)
        self.assertIn("DC_FlushRange(s_bot_screen_buf, sizeof(s_bot_screen_buf));", source)
        self.assertNotIn("s_dungeon_world_cache", source)


if __name__ == "__main__":
    unittest.main()
