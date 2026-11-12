import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
SPRITES = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
HEADER = (ROOT / "include" / "player_sprite.h").read_text(encoding="utf-8")
WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
WEAPONS_H = (ROOT / "include" / "weapons.h").read_text(encoding="utf-8")
SHOT_DIR = ROOT / "assets" / "sprites" / "characters" / "corazon_disparo"


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("unterminated " + signature)


def clip_section():
    start = MAIN.index("#define SHOT_FRAME_TICKS")
    end = MAIN.index("static void draw_player(")
    return MAIN[start:end]


def shot_muzzle_table():
    start = SPRITES.index("const int8_t g_hero_shot_muzzle[")
    body = SPRITES[SPRITES.index("=", start):SPRITES.index("};", start)]
    nums = [int(v) for v in re.findall(r"-?\d+", body)]
    assert len(nums) == 3 * 8 * 8, len(nums)
    it = iter(nums)
    return [[[next(it) for _ in range(3)] for _ in range(8)] for _ in range(8)]


class HeroShotClipContractTests(unittest.TestCase):
    def test_header_declares_shot_clip(self):
        self.assertIn("extern const uint16_t g_player_shot_frames[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SPRITE_W * PLAYER_SPRITE_H];", HEADER)
        self.assertIn("extern const uint8_t g_player_shot_shadow_masks[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][PLAYER_SHADOW_W * PLAYER_SHADOW_H / 2];", HEADER)
        self.assertIn("extern const uint8_t g_player_shot_shadow_bounds[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][4];", HEADER)
        self.assertIn("extern const int8_t g_hero_shot_muzzle[PLAYER_NUM_DIRS][PLAYER_NUM_FRAMES][3];", HEADER)

    def test_generated_tables_exist_once(self):
        for name in ["g_player_shot_frames", "g_player_shot_shadow_masks", "g_player_shot_shadow_bounds", "g_hero_shot_muzzle"]:
            with self.subTest(table=name):
                self.assertEqual(len(re.findall(r"\b%s\[" % name, SPRITES)), 1)

    def test_no_float_in_clip_code(self):
        section = clip_section()
        self.assertNotRegex(section, r"\b(float|double)\b")
        self.assertNotRegex(function_body(WEAPONS_C, "int weapons_aim_progress(void)"), r"\b(float|double)\b")

    def test_charge_mapping_has_no_divide(self):
        body = function_body(MAIN, "static int hero_charge_frame(void)")
        self.assertIn("SHOT_LAST_FRAME - ((prog * SHOT_LAST_FRAME) >> 8)", body)
        self.assertNotIn("/", body)
        self.assertNotIn("%", body)

    def test_recovery_runs_three_game_frames_per_clip_frame(self):
        self.assertIn("#define SHOT_FRAME_TICKS 3", MAIN)
        body = function_body(MAIN, "static void shot_clip_step(void)")
        self.assertIn("SHOT_FRAME_TICKS", body)
        self.assertNotIn("/", body)
        self.assertIn("s_shot_frame = 0;", MAIN)
        self.assertIn("s_shot_active = 0;", body)

    def test_shot_starts_only_for_sniper_and_only_hero_uses_clip(self):
        self.assertIn("(result & WEAPON_RESULT_FIRED) && g_player_state.current_weapon == WEAPON_SNIPER", MAIN)
        body = function_body(MAIN, "static int hero_clip_frame(void)")
        self.assertIn("s_player.char_id != CHAR_HERO", body)

    def test_charging_uses_the_weapon_state_getters(self):
        self.assertIn("int weapons_aim_charging(void)", WEAPONS_C)
        self.assertIn("int weapons_aim_progress(void)", WEAPONS_C)
        self.assertIn("int weapons_aim_charging(void);", WEAPONS_H)
        self.assertIn("int weapons_aim_progress(void);", WEAPONS_H)

    def test_draw_and_shadow_use_the_clip_when_shown(self):
        self.assertIn("&g_player_shot_frames[s_player.dir][clip][", MAIN)
        self.assertIn("g_player_shot_shadow_masks[s_player.dir][clip]", MAIN)
        self.assertIn("g_player_shot_shadow_bounds[s_player.dir][clip]", MAIN)
        self.assertIn("s_hero_shot_frame_bounds[s_player.dir][clip]", MAIN)

    def test_muzzle_follows_the_shown_clip_frame(self):
        body = function_body(MAIN, "static void player_muzzle(fixed *mx, fixed *my, int *mh)")
        self.assertIn("g_hero_shot_muzzle[s_player.dir][s_hero_clip_frame]", body)
        self.assertIn("g_character_muzzle[", body)
        self.assertLess(MAIN.index("s_hero_clip_frame = hero_clip_frame();"), MAIN.index("player_muzzle(&in.muzzle_x"))

    def test_moving_cuts_the_recovery(self):
        self.assertIn("s_shot_active = 0;      // walking during the recovery cuts the shot clip", MAIN)

    def test_enemies_do_not_use_the_clip(self):
        draw_enemy = function_body(MAIN, "static void draw_enemy(")
        self.assertNotIn("shot", draw_enemy)
        self.assertNotIn("s_hero_clip_frame", draw_enemy)

    def test_generated_muzzle_matches_disparo_settings(self):
        settings = json.loads((SHOT_DIR / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(shot_muzzle_table(), settings["dirMuzzle"])

    def test_shot_ground_line_is_shifted_onto_the_walk(self):
        # The lab put the shot's feet 1 px lower than the walk (34 vs 33); the generator shifts the
        # shot sprites up by that difference so one ground anchor table serves both clips.
        walk = json.loads((ROOT / "assets" / "sprites" / "characters" / "corazon" / "settings.json").read_text(encoding="utf-8"))
        shot = json.loads((SHOT_DIR / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(walk["anchor"][0], shot["anchor"][0])
        self.assertEqual(walk["frameSize"], shot["frameSize"])
        for d in range(8):
            self.assertEqual(walk["dirGroundAnchors"][d] - shot["dirGroundAnchors"][d], -1)
        gen = (ROOT / "tools" / "generate_player_sprites_c.py").read_text(encoding="utf-8")
        self.assertIn("shot_shift = [walk_anchors[d] - shot_anchors[d] for d in range(8)]", gen)

if __name__ == "__main__":
    unittest.main()
