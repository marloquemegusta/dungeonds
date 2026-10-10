import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.c"


class FloorCopyContractTest(unittest.TestCase):
    def test_world_floor_uses_cached_ram_and_dma_scanlines(self):
        source = SOURCE.read_text(encoding="utf-8")
        copy_row = source[source.index("static void copy_world_row("):source.index("static void render_screen")]

        self.assertIn("dmaCopyHalfWords(3, src, dst, SCREEN_W * sizeof(uint16_t))", copy_row)
        self.assertIn("s_dungeon_world_cache[wy * WORLD_W + wx]", source)
        self.assertIn("memcpy(s_dungeon_world_cache, g_dungeon_world_color", source)


if __name__ == "__main__":
    unittest.main()
