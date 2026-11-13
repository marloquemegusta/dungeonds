import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
SPRITES = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
WIDTH = 40
HEIGHT = 40
SHADOW_W = 80
SHADOW_H = 80
MASK_BYTES = (SHADOW_W * SHADOW_H) // 2


def exported_anchors():
    """Single source of truth: the per-character, per-direction anchors exported with the sprites."""
    start = SPRITES.index("const uint8_t g_character_ground_anchors[")
    end = SPRITES.index("};", start)
    rows = re.findall(r"\{([^{}]+)\}", SPRITES[SPRITES.index("=", start):end])
    return [[int(v) for v in row.split(",")] for row in rows]


def _brace_block(symbol_decl):
    start = SPRITES.index(symbol_decl)
    opening = SPRITES.index("{", SPRITES.index("=", start))
    depth = 0
    for end in range(opening, len(SPRITES)):
        if SPRITES[end] == "{":
            depth += 1
        elif SPRITES[end] == "}":
            depth -= 1
            if depth == 0:
                return SPRITES[opening:end + 1]
    raise AssertionError("unterminated " + symbol_decl)


def pixel_values(symbol):
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{4})", _brace_block(f"const uint16_t {symbol}["))]


def frame_offsets(symbol):
    return [int(v) for v in re.findall(r"\d+", _brace_block(f"const uint32_t {symbol}["))]


def frame_bounds(symbol):
    rows = re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", _brace_block(f"const uint8_t {symbol}["))
    return [tuple(int(x) for x in r) for r in rows]


class SpriteGroundAnchorTests(unittest.TestCase):
    def test_charger_frames_extend_below_shared_anchor(self):
        values = pixel_values("g_charger_frames")
        offsets = frame_offsets("g_charger_frame_offsets")
        bounds = frame_bounds("g_charger_frame_bounds")
        self.assertEqual(len(offsets), 8 * 8)
        self.assertEqual(len(bounds), 8 * 8)
        lowest = 0
        for frame_index in range(8 * 8):
            off = offsets[frame_index]
            _bx, by, bw, bh = bounds[frame_index]
            frame = values[off:off + bw * bh]
            opaque_rows = [by + y for y in range(bh)
                           if any(pixel & 0x8000 for pixel in frame[y * bw:(y + 1) * bw])]
            self.assertTrue(opaque_rows)
            lowest = max(lowest, max(opaque_rows))
        anchor = max(exported_anchors()[1])
        self.assertGreaterEqual(lowest - anchor, 0)

    def test_player_and_enemy_frames_use_exported_ground_anchor(self):
        for function in ("draw_player", "draw_enemy"):
            start = MAIN.index(f"static void {function}(")
            end = MAIN.index("\n}", start) + 2
            body = MAIN[start:end]
            self.assertIn("py - s_char_ground_anchor[", body)
            self.assertNotIn("sprite_max_y", body)

    def test_no_hardcoded_anchor_constant(self):
        header = (ROOT / "include" / "player_sprite.h").read_text(encoding="utf-8")
        self.assertNotIn("PLAYER_ANCHOR_Y", header)
        self.assertNotIn("PLAYER_ANCHOR_Y", MAIN)
        anchors = exported_anchors()
        self.assertEqual(len(anchors), 4)
        self.assertTrue(all(len(row) == 8 for row in anchors))

    def test_shadow_masks_and_bounds_dimensions(self):
        prefixes = ("g_player", "g_charger", "g_necron", "g_skeleton")
        for prefix in prefixes:
            mask_decl = f"const uint8_t {prefix}_shadow_masks[]"
            self.assertIn(mask_decl, SPRITES)
            off_decl = f"const uint32_t {prefix}_shadow_offsets[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES]"
            self.assertIn(off_decl, SPRITES)
            bounds_decl = f"const uint8_t {prefix}_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4]"
            self.assertIn(bounds_decl, SPRITES)

        anchor_decl = "const uint8_t g_character_ground_anchors[NUM_CHARACTERS][PLAYER_NUM_DIRS]"
        self.assertIn(anchor_decl, SPRITES)


if __name__ == "__main__":
    unittest.main()
