import re
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "source" / "main.c"


class FpsHudContractTest(unittest.TestCase):
    def test_hud_displays_cpu_breakdown_fields_and_matching_glyphs(self):
        source = SOURCE.read_text(encoding="utf-8")
        chars = re.search(r's_fps_chars\[\]\s*=\s*"([^"]+)"', source).group(1)
        font = re.search(r's_fps_font\[\]\[7\]\s*=\s*\{(.*?)\n\};', source, re.S).group(1)
        glyphs = re.findall(r"//\s*(space|[A-Z]|:|[0-9])\s*$", font, re.M)
        hud = source[source.index("static void draw_fps_hud"):source.index("// Presentation")]

        self.assertEqual(len(chars), len(glyphs))
        self.assertEqual(chars, "".join(" " if glyph == "space" else glyph for glyph in glyphs))
        self.assertIn('"F:%02lu S:%02lu B:%02lu L:%02lu"', hud)
        for field in ("floor_ticks", "shadow_ticks", "blit_ticks", "logic_ticks"):
            self.assertIn(f"g_perf.{field}", hud)


if __name__ == "__main__":
    unittest.main()
