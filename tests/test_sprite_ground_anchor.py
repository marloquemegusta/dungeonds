import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
SPRITES = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
ANCHOR_Y = 28
WIDTH = 40
HEIGHT = 40
SHADOW_W = 80
SHADOW_H = 80
MASK_BYTES = (SHADOW_W * SHADOW_H) // 2


def pixel_values(symbol):
    marker = f"const uint16_t {symbol}["
    start = SPRITES.index(marker)
    opening = SPRITES.index("{", SPRITES.index("=", start))
    depth = 0
    for end in range(opening, len(SPRITES)):
        if SPRITES[end] == "{":
            depth += 1
        elif SPRITES[end] == "}":
            depth -= 1
            if depth == 0:
                break
    return [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{4})", SPRITES[opening:end + 1])]


class SpriteGroundAnchorTests(unittest.TestCase):
    def test_charger_frames_extend_below_shared_anchor(self):
        values = pixel_values("g_charger_frames")
        self.assertEqual(len(values), 8 * 8 * WIDTH * HEIGHT)
        lowest = 0
        for frame_index in range(8 * 8):
            frame = values[frame_index * WIDTH * HEIGHT:(frame_index + 1) * WIDTH * HEIGHT]
            opaque_rows = [y for y in range(HEIGHT)
                           if any(pixel & 0x8000 for pixel in frame[y * WIDTH:(y + 1) * WIDTH])]
            self.assertTrue(opaque_rows)
            lowest = max(lowest, max(opaque_rows))
        self.assertGreaterEqual(lowest - ANCHOR_Y, 4)

    def test_player_and_enemy_frames_use_exported_ground_anchor(self):
        for function in ("draw_player", "draw_enemy"):
            start = MAIN.index(f"static void {function}(")
            end = MAIN.index("\n}", start) + 2
            body = MAIN[start:end]
            self.assertIn("py - s_char_ground_anchor[", body)
            self.assertNotIn("sprite_max_y", body)

    def test_shadow_masks_and_bounds_dimensions(self):
        for prefix in ("g_player", "g_charger", "g_necron"):
            mask_decl = f"const uint8_t {prefix}_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2]"
            self.assertIn(mask_decl, SPRITES)
            bounds_decl = f"const uint8_t {prefix}_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4]"
            self.assertIn(bounds_decl, SPRITES)

        anchor_decl = "const uint8_t g_character_ground_anchors[NUM_CHARACTERS][PLAYER_NUM_DIRS]"
        self.assertIn(anchor_decl, SPRITES)


if __name__ == "__main__":
    unittest.main()
