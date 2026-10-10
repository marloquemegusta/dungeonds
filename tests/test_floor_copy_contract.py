import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.c"


class FloorCopyContractTest(unittest.TestCase):
    def test_scanline_copy_has_aligned_and_safe_halfword_paths(self):
        source = SOURCE.read_text(encoding="utf-8")
        aligned = source[source.index("static void copy_world_row_aligned"):source.index("static void copy_world_row_halfword_aligned")]
        unaligned = source[source.index("static void copy_world_row_halfword_aligned"):source.index("static void render_screen")]

        self.assertIn('"ldmia %1!, {r3, r4, r5, r6, r7, r8, r9, r10}', aligned)
        self.assertIn("mov r2, #16", aligned)  # 16 * 8 words = 256 pixels
        self.assertIn("ldrh r3, [%1], #2", unaligned)
        self.assertIn("ldrh r4, [%1], #2", unaligned)
        self.assertIn("mov r2, #128", unaligned)
        self.assertIn("if ((uintptr_t)src & 2)", source)
        self.assertIn("s_dungeon_world_cache[wy * WORLD_W + wx]", source)
        self.assertIn("memcpy(s_dungeon_world_cache, g_dungeon_world_color", source)
        self.assertNotIn("dmaCopyHalfWords(3, src", source)


if __name__ == "__main__":
    unittest.main()
