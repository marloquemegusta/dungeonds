import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (symbol stem, number of frames per direction)
SETS = [
    ("player", 8),
    ("charger", 8),
    ("ojo", 8),
    ("skeleton", 8),
    ("charger_charge", 4),
    ("charger_telegraph", 1),
    ("player_shot", 8),
]


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


def array_body(text, name):
    m = re.search(r"\b" + re.escape(name) + r"\[[^=;{]*=\s*\{", text)
    assert m, name
    end = text.index("\n};", m.end())
    return text[m.end():end]


def ints(body, base=10):
    if base == 16:
        return [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]+", body)]
    return [int(v) for v in re.findall(r"\d+", body)]


class BlitRunsContractTest(unittest.TestCase):
    def test_generator_emits_runs_for_every_sprite_set(self):
        gen = read("tools/generate_player_sprites_c.py")
        self.assertIn("def emit_runs(", gen)
        self.assertIn("pixels_all.append(0)", gen)           # even row pitch
        c = read("source/player_sprite.c")
        for stem, _ in SETS:
            self.assertRegex(c, r"const uint16_t g_%s_runs\[\]" % stem)
            self.assertRegex(c, r"const uint32_t g_%s_run_offsets\[PLAYER_NUM_DIRS\]" % stem)
        self.assertIn("g_character_runs[NUM_CHARACTERS]", c)
        self.assertIn("g_character_run_offsets[NUM_CHARACTERS]", c)
        header = read("include/player_sprite.h")
        self.assertIn("sprite_pitch(int bw)", header)
        self.assertIn("character_runs_ptr", header)

    def test_runs_are_exactly_the_opaque_runs_of_every_frame(self):
        c = read("source/player_sprite.c")
        for stem, nframes in SETS:
            pixels = ints(array_body(c, "g_%s_frames" % stem), 16)
            offs = ints(array_body(c, "g_%s_frame_offsets" % stem))
            bounds = ints(array_body(c, "g_%s_frame_bounds" % stem))
            runs = ints(array_body(c, "g_%s_runs" % stem))
            roffs = ints(array_body(c, "g_%s_run_offsets" % stem))
            self.assertEqual(len(offs), 8 * nframes, stem)
            self.assertEqual(len(roffs), 8 * nframes, stem)
            self.assertEqual(len(bounds), 8 * nframes * 4, stem)
            for f in range(8 * nframes):
                bw, bh = bounds[f * 4 + 2], bounds[f * 4 + 3]
                if bw == 0 or bh == 0:
                    continue
                pitch = (bw + 1) & ~1
                base, rb = offs[f], roffs[f]
                self.assertEqual(rb % 2, 0, "run block must be word aligned")
                for y in range(bh):
                    row = pixels[base + y * pitch:base + y * pitch + bw]
                    expected = []
                    x = 0
                    while x < bw:
                        if row[x] & 0x8000:
                            x0 = x
                            while x < bw and row[x] & 0x8000:
                                x += 1
                            expected.append(x0 | ((x - x0) << 8))
                        else:
                            x += 1
                    r0, r1 = runs[rb + y], runs[rb + y + 1]
                    self.assertEqual(runs[rb + r0:rb + r1], expected, "%s frame %d row %d" % (stem, f, y))
                if bw & 1:
                    for y in range(bh):
                        self.assertEqual(pixels[base + y * pitch + bw], 0, "pad pixel must be transparent")

    def test_rom_growth_of_the_run_tables_stays_modest(self):
        c = read("source/player_sprite.c")
        total = 0
        for stem, _ in SETS:
            total += 2 * len(ints(array_body(c, "g_%s_runs" % stem)))
            total += 4 * len(ints(array_body(c, "g_%s_run_offsets" % stem)))
        self.assertLess(total, 150 * 1024)

    def test_blit_walks_runs_without_a_per_pixel_opacity_test(self):
        main = read("source/main.c")
        code = strip_comments(main)
        blit = function_body(code, "static void blit_stride(")
        self.assertNotIn("BIT(15)", blit)
        self.assertNotIn("0x8000", blit)
        self.assertIn("blit_runs_span(", blit)
        self.assertIn("runs[y]", blit)
        for name in ("copy_run", "blit_runs_span"):
            body = function_body(code, "static inline void %s(" % name)
            self.assertNotIn("BIT(15)", body)
        # Hot loops: ARM mode + O3, no float, no C division or modulo.
        start = code.index("static inline void copy_run(")
        hot = code[code.rindex("__attribute__", 0, start):code.index("static inline uint16_t apply_shadow(")]
        self.assertEqual(hot.count('target("arm")'), 3)
        self.assertEqual(hot.count('optimize("O3")'), 3)
        self.assertNotRegex(hot, r"\bfloat\b|\bdouble\b")
        self.assertNotRegex(hot, r"[^/*]/[^/*]")
        self.assertNotIn("%", hot)

    def test_blit_never_writes_bytes_to_vram(self):
        code = strip_comments(read("source/main.c"))
        copy = function_body(code, "static inline void copy_run(")
        self.assertNotRegex(copy, r"uint8_t|char\b")

    def test_dirty_span_still_covers_every_painted_row(self):
        code = strip_comments(read("source/main.c"))
        blit = function_body(code, "static void blit_stride(")
        # The painted span (first run start .. last run end, clipped) widens the row's dirty span
        # before anything is written, and rows without runs paint nothing.
        self.assertIn("dspan->x0", blit)
        self.assertIn("dspan->x1", blit)
        self.assertLess(blit.index("dspan->x1"), blit.index("blit_runs_span("))
        self.assertIn("if (rr == rend) continue;", blit)

    def test_callers_pass_the_runs_of_the_frame_they_draw(self):
        code = strip_comments(read("source/main.c"))
        player = function_body(code, "static void draw_player(")
        enemy = function_body(code, "static void draw_enemy(")
        self.assertIn("g_player_shot_runs", player)
        self.assertIn("character_runs_ptr", player)
        self.assertIn("blit_stride(buffer, frame, runs,", player)
        for tag in ("g_charger_telegraph_runs", "g_charger_charge_runs", "character_runs_ptr"):
            self.assertIn(tag, enemy)
        self.assertIn("blit_stride(buffer, frame, runs,", enemy)
        self.assertIn("sprite_pitch(bw)", player)
        self.assertIn("sprite_pitch(bw)", enemy)
        self.assertIn("sprite_pitch(width)", code)       # death chunks read the padded frame

    def test_hot_per_frame_functions_are_placed_in_itcm(self):
        # ITCM (zero-wait instruction TCM) holds the per-frame hot path; the attribute must sit on
        # the definition itself, not on a comment or a call site.
        hot = {
            "source/main.c": ["static void blit_stride(", "static void zero_words_burst(",
                              "static void clear_dirty_spans(", "static void render_screen(",
                              "static void draw_shadow_mask("],
            "source/hwshadow.c": ["void hwshadow_add(", "void hwshadow_commit(", "static void convert_part("],
            "source/enemy_ai.c": ["void enemy_ai_update(", "static int move_with_slide(",
                                  "static void apply_separation(", "static void sep_build_grid("],
            "source/navfield.c": ["void nav_update(", "int nav_next_step("],
            "source/horde.c": ["void horde_update("],
            "source/collision.c": ["int position_is_free(", "int line_is_walkable(",
                                   "int bullet_line_is_free("],
        }
        for rel, signatures in hot.items():
            code = strip_comments(read(rel))
            for sig in signatures:
                self.assertIn(sig, code, sig)
                start = code.index(sig)
                head = code[max(0, code.rfind(";", 0, start), code.rfind("}", 0, start)):start]
                self.assertIn("ITCM_CODE", head, "%s in %s is not in ITCM" % (sig, rel))
        # The ITCM macro comes from libnds; the files that use it must include its header.
        self.assertIn("<nds/ndstypes.h>", read("source/collision.c"))
        self.assertIn("<nds/ndstypes.h>", read("source/navfield.c"))
        self.assertIn("<nds/ndstypes.h>", read("source/horde.c"))


if __name__ == "__main__":
    unittest.main()
