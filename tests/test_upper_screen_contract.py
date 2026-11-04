import re
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")

SUB_VRAM_BYTES = 128 * 1024          # bank C
PAGE_BYTES = 256 * 192 * 2           # one 16 bpp actor page
VIEW_W, VIEW_H = 33, 25              # tiles streamed for one screen (BG_VIEW_W/H)


def define(text, name):
    return int(re.search(rf"#define {name} (\d+)", text).group(1))


def arena_tile_maps():
    """(name, tile map as a numpy array) for every baked arena (source/arena_*.c)."""
    maps = []
    for path in sorted((ROOT / "source").glob("arena_*.c")):
        text = path.read_text(encoding="utf-8")
        width = int(re.search(r"\.map_w = (\d+)", text).group(1))
        height = int(re.search(r"\.map_h = (\d+)", text).group(1))
        body = text.split("s_map[")[1].split("{", 1)[1].split("};")[0]
        values = [int(v) for v in re.findall(r"\d+", body)]
        maps.append((path.name, np.array(values[:width * height], dtype=np.int32).reshape(height, width)))
    return maps


class UpperScreenContractTest(unittest.TestCase):
    """Both screens draw the same layers: floor tiles plus a 16 bpp actor page."""

    def test_both_screens_run_the_same_compositor(self):
        self.assertIn("render_screen(s_top_page, s_dirty_top, view_x, view_y - SCREEN_H", MAIN_C)
        self.assertIn("render_screen(bot_page_ptr(s_bot_back_page), s_dirty[s_bot_back_page == 24], view_x, view_y", MAIN_C)
        self.assertIn("update_player_see_through();", MAIN_C)
        # The see-through state belongs to the player, not to whichever screen is drawn.
        render = MAIN_C.split("static void render_screen")[1].split("static const char s_fps_chars")[0]
        self.assertNotIn("s_player_see_through = 0;", render)

    def test_sub_vram_layout_fits_bank_c(self):
        capacity = define(MAIN_C, "TOP_TILE_CACHE_CAPACITY")
        tiles = capacity * 64
        map_base = int(re.search(r"bgInitSub\(0, BgType_Text8bpp, BgSize_T_512x256, (\d+), 0\)", MAIN_C).group(1)) * 2048
        page_base = int(re.search(r"bgInitSub\(2, BgType_Bmp16, BgSize_B16_256x256, (\d+), 0\)", MAIN_C).group(1)) * 16384
        self.assertLessEqual(tiles, map_base)                 # tile slots end before the map
        self.assertLessEqual(map_base + 4096, page_base)      # the 512x256 map (4 KiB) ends before the page
        self.assertLessEqual(page_base + PAGE_BYTES, SUB_VRAM_BYTES)

    def test_every_screen_window_of_every_arena_fits_the_upper_tile_slots(self):
        capacity = define(MAIN_C, "TOP_TILE_CACHE_CAPACITY")
        maps = arena_tile_maps()
        self.assertTrue(maps, "no baked arenas")
        for name, tile_map in maps:
            worst = 0
            for y in range(0, max(1, tile_map.shape[0] - VIEW_H + 1)):
                for x in range(0, max(1, tile_map.shape[1] - VIEW_W + 1)):
                    worst = max(worst, len(np.unique(tile_map[y:y + VIEW_H, x:x + VIEW_W])))
            # Slot 0 is the blank tile; a few slots of slack cover the ring while it scrolls.
            self.assertLessEqual(worst, capacity - 8, f"{name}: worst window needs {worst} tiles")

    def test_the_tile_cache_arrays_hold_every_arena(self):
        most = max(int(re.search(r"\.num_tiles = (\d+)", p.read_text(encoding="utf-8")).group(1))
                   for p in (ROOT / "source").glob("arena_*.c"))
        self.assertLessEqual(most, define(MAIN_C, "BG_MAX_TILES"))

if __name__ == "__main__":
    unittest.main()
