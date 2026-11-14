import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return text[brace:i + 1]
    raise AssertionError("unbalanced braces after " + signature)


class HwShadowsContractTest(unittest.TestCase):
    def test_flag_exists_defaults_on_and_godrays_forces_software(self):
        header = read("include/hwshadow.h")
        self.assertRegex(header, r"#ifndef HW_SHADOWS\s*\n#define HW_SHADOWS 1")
        self.assertRegex(header, r"#if defined\(GODRAYS_PROTO\) && GODRAYS_PROTO\s*\n#undef HW_SHADOWS\s*\n#define HW_SHADOWS 0")
        self.assertIn("#define HW_SHADOW_BLDY 8", header)

    def test_obj_window_with_floor_only_brightness_decrease(self):
        src = strip_comments(read("source/hwshadow.c"))
        self.assertIn("ATTR0_TYPE_WINDOWED", src)               # shadow OBJs are window sprites
        self.assertIn("DISPLAY_SPR_WIN_ON", src)
        self.assertIn("DISPLAY_SPR_ACTIVE", src)
        self.assertIn("#define BLD_FADE_BLACK (3 << 6)", src)    # BLDCNT mode 3: brightness decrease
        # first target = floor layer only: main floor is BG1, sub floor is BG0, BG2 (actors) is never a target
        self.assertIn("(sub ? BIT(0) : BIT(1)) | BLD_FADE_BLACK", src)
        self.assertNotRegex(src, r"BIT\(2\)\s*\|\s*BLD_FADE_BLACK")
        self.assertIn("*bldy = HW_SHADOW_BLDY", src)
        # OBJ window region gets the colour effect, outside does not
        self.assertIn("#define WINOUT_SHADOW 0x3F1F", src)

    def test_oam_window_vram_banks_and_budget(self):
        src = strip_comments(read("source/hwshadow.c"))
        self.assertIn("VRAM_E_MAIN_SPRITE", src)
        self.assertIn("VRAM_I_SUB_SPRITE", src)
        self.assertIn("#define POOL_TILES_MAIN 1024", src)       # 10-bit tile index in 1D_32 mapping
        self.assertIn("#define POOL_TILES_SUB 512", src)         # bank I is only 16 KiB
        self.assertIn("#define OAM_LIMIT 128", src)
        self.assertIn("evict_lru", src)                          # LRU cache keyed by mask pointer
        self.assertIn("g->count + pl->n > OAM_LIMIT", src)       # out of OAM: skip, never crash

    def test_tide_split_per_scanline(self):
        src = strip_comments(read("source/hwshadow.c"))
        self.assertIn("IRQ_VCOUNT", src)
        self.assertIn("SetYtrigger", src)
        self.assertIn("DISP_IN_HBLANK", src)
        self.assertIn("TIDE_BRIGHTNESS", src)
        self.assertIn("#define BLD_TIDE (0x3f | BLD_FADE_BLACK)", src)   # tide: every layer, as in tide.c
        tide = read("source/tide.c")
        self.assertIn("int tide_window_top(int camera_y)", tide)
        self.assertIn("*bldcnt = 0x3f | (3 << 6);", tide)       # the software-shadow tide path keeps its look

    def test_no_float_or_double_in_new_code(self):
        for rel in ("source/hwshadow.c", "include/hwshadow.h"):
            self.assertIsNone(re.search(r"\b(float|double)\b", strip_comments(read(rel))), rel)
        tide_top = function_body(read("source/tide.c"), "int tide_window_top(int camera_y)")
        self.assertIsNone(re.search(r"\b(float|double)\b", tide_top))

    def test_main_integration_and_software_path_still_present(self):
        main = read("source/main.c")
        self.assertIn("static void draw_shadow_mask(", main)
        self.assertIn("draw_shadow_mask(buffer, sel.mask, sel.bounds", main)
        self.assertIn("static int shadow_select(", main)
        render = function_body(main, "static void render_screen(")
        self.assertIn("hwshadow_begin(sub_screen)", render)
        # a foot point hidden by baked occlusion hides the whole shadow
        self.assertRegex(render, r"!occlusion_blocks_pixel\(items\[i\]\.cx, items\[i\]\.cy, items\[i\]\.depth\)\)\s*\n\s*hwshadow_add")
        self.assertIn("PP_ADD(PP_SHADOW, pp_shadow)", render)
        present = function_body(main, "static void present_vblank_begin(void)")
        self.assertIn("hwshadow_commit(0)", present)              # main OAM with the page flip
        self.assertLess(present.index("bgSetMapBase"), present.index("hwshadow_commit(0)"))
        loop = main[main.index("int main(void)"):]
        self.assertIn("hwshadow_commit(1)", loop)                # sub OAM after the top page redraw
        self.assertLess(loop.index("render_screen(s_top_page, s_dirty_top, view_x"), loop.index("hwshadow_commit(1)"))
        self.assertIn("hwshadow_init();", loop)
        self.assertIn("tide_window_top(", main)
        self.assertIn("hwshadow_regs_off();", main)               # software choice: the tide module alone

    def test_stress_variants_and_toggle(self):
        project = json.loads(read(".ds-game-dev/project.json"))
        self.assertEqual(project["variants"]["stress"]["defines"], ["STRESS_TEST=1"])
        self.assertEqual(project["variants"]["stress-perf"]["defines"], ["STRESS_TEST=1", "PERF_PROFILE=1"])
        self.assertIn("python.exe tests/test_hw_shadows_contract.py", project["hostTests"])
        gameplay = read("include/gameplay.h")
        self.assertRegex(gameplay, r"#if STRESS_TEST\s*\n#define MAX_GAMEPLAY_ENEMIES 64")
        horde = read("include/horde.h")
        self.assertRegex(horde, r"#if STRESS_TEST[\s\S]*#define HORDE_MAX_CAP 48")
        self.assertRegex(read("source/horde.c"), r"#if STRESS_TEST\s*\n\s*e->hp = 1;")
        main = read("source/main.c")
        self.assertRegex(main, r"#if STRESS_TEST\s*\n\s*g_player_state\.god_mode = 1;")
        self.assertRegex(main, r"#if STRESS_TEST && HW_SHADOWS\s*\n[^\n]*\n\s*if \(\(keys & \(KEY_L \| KEY_R\)\) == \(KEY_L \| KEY_R\) && \(keys_down & KEY_A\)\)")
        self.assertIn('" SH %s", g_hw_shadows_on ? "HW" : "SW"', main)

    def test_default_build_has_no_stress_code(self):
        self.assertRegex(read("include/gameplay.h"), r"#ifndef STRESS_TEST\s*\n#define STRESS_TEST 0")
        self.assertIn("#define MAX_GAMEPLAY_ENEMIES 24", read("include/gameplay.h"))


if __name__ == "__main__":
    unittest.main()
