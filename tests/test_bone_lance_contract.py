from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


class BoneLanceContract(unittest.TestCase):
    def test_procedural_shard_uses_no_baked_sprite_or_outline(self):
        self.assertNotIn("bone_lance_sprite.h", MAIN)
        self.assertNotIn("g_bone_lance_frames", MAIN)
        self.assertNotIn("s_lance_frame_bounds", MAIN)
        draw = MAIN.split("static void draw_bone_lance(", 1)[1].split("static void draw_bone_particles", 1)[0]
        self.assertIn("int length = 8 + (lance->seed & 3)", draw)
        self.assertIn("bone_effect_pixel(buffer", draw)
        self.assertNotIn("blit_stride", draw)
        self.assertIn("#define MAX_BONE_PARTICLES 32", MAIN)
        self.assertIn("emit_bone_particle(lance, p)", MAIN)
        self.assertIn("if (--p->life == 0) p->active = 0", MAIN)

    def test_pellet_volley_and_enemy_numbers(self):
        damage = int(re.search(r"#define LANCE_DAMAGE (\d+)", MAIN).group(1))
        pellets = int(re.search(r"#define LANCE_PELLETS (\d+)", MAIN).group(1))
        skeleton_hp = int(re.search(r"char_id == CHAR_CHARGER \? (\d+) : (\d+)", MAIN).group(2))
        charger_hp = int(re.search(r"char_id == CHAR_CHARGER \? (\d+) : (\d+)", MAIN).group(1))
        self.assertEqual((damage, pellets, skeleton_hp, charger_hp), (10, 5, 40, 90))
        self.assertRegex(MAIN, r"for \(int pellet = 0; pellet < LANCE_PELLETS; pellet\+\+")
        self.assertIn("slots[pellet] * 11 + pellet * 6", MAIN)
        seeds = [(pellet * 11 + pellet * 6) & 3 for pellet in range(5)]
        self.assertEqual(len(set(seeds)), 4)

    def test_both_ds_aim_paths_are_wired_to_lance_fire(self):
        self.assertIn("if (touch_down || (keys & KEY_A)) lance_fire", MAIN)
        self.assertIn("touchRead(&touch);", MAIN)
        self.assertIn("nearest_enemy_screen(&aim_x, &aim_y)", MAIN)

    def test_skeleton_death_plays_once_and_keeps_the_final_pile(self):
        sprite_header = (ROOT / "include" / "player_sprite.h").read_text(encoding="utf-8")
        sprite_source = (ROOT / "source" / "player_sprite.c").read_text(encoding="utf-8")
        converter = (ROOT / "tools" / "convert_iso_to_c.py").read_text(encoding="utf-8")
        self.assertIn("g_skeleton_death_frames", sprite_header)
        self.assertIn("g_skeleton_death_frames", sprite_source)
        self.assertIn("skeleton_death_{args.preset}.png", converter)
        self.assertIn("e->death_frame = 0", MAIN)
        self.assertIn("e->death_frame < PLAYER_NUM_FRAMES - 1", MAIN)
        self.assertIn("if (e->death_frame >= 0)", MAIN)
        self.assertIn("draw_enemy(buffer, e, cam_x, cam_y)", MAIN)


if __name__ == "__main__":
    unittest.main()
