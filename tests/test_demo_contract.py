import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class DemoContractTest(unittest.TestCase):
    def test_hero_starts_with_laser_in_the_demo_rom(self):
        src = read("source/gameplay.c")
        init = src[src.index("void player_state_init"):src.index("int player_take_hit")]
        m = re.search(r"#if TEST_WEAPON_CYCLE\s*(.*?)#else\s*(.*?)#endif", init, re.S)
        self.assertIsNotNone(m)
        self.assertIn("WEAPON_SHOTGUN", m.group(1))
        self.assertIn("WEAPON_SNIPER", m.group(2))

    def test_weapon_cycle_only_in_test_variants(self):
        main = read("source/main.c")
        m = re.search(r"#if TEST_WEAPON_CYCLE\s*[^\n]*\n\s*if \(keys_down & KEY_L\) \{\s*weapons_cycle", main)
        self.assertIsNotNone(m)
        self.assertEqual(main.count("weapons_cycle("), 1)
        flag = re.search(r"#if ([^\n]*)\n#define TEST_WEAPON_CYCLE 1", read("include/gameplay.h")).group(1)
        for name in ("SANDBOX", "PLAYGROUND", "STRESS_TEST", "GODRAYS_PROTO"):
            self.assertIn(name, flag)

    def test_strip_hud_draws_hearts_while_alive(self):
        main = read("source/main.c")
        hud = main[main.index("static void draw_run_hud"):main.index("// Presentation")]
        strip = hud[:hud.index("// Hit points, right-aligned")]
        dead = strip.index("is_dead")
        hearts = strip.index("g_hud_heart_full")
        self.assertGreater(hearts, dead)
        self.assertIn("g_hud_heart_empty", strip)
        self.assertIn("max_hp", strip)
        self.assertIn("SCREEN_W - 6", strip)
        # the death screen returns before the hearts
        self.assertIn("return;", strip[dead:hearts])

    def test_hud_icon_data_exists_without_float(self):
        for rel in ("source/hud_icons_gfx.c", "include/hud_icons_gfx.h",
                    "assets/sprites/hud/heart_full.png", "assets/sprites/hud/heart_empty.png"):
            self.assertTrue((ROOT / rel).exists(), rel)
        text = read("source/hud_icons_gfx.c") + read("include/hud_icons_gfx.h")
        self.assertIsNone(re.search(r"\b(float|double)\b", text))
        main = read("source/main.c")
        icon = main[main.index("static void hud_icon"):main.index("static void draw_run_hud")]
        self.assertIsNone(re.search(r"\b(float|double)\b|[/%] ", icon))
        self.assertIn("if (c)", icon)

    def test_heal_pickups_render_levitating_sacred_heart(self):
        pickups = read("source/pickups.c")
        self.assertIn("g_hud_heart_full", pickups)
        self.assertIn("bob_lut", pickups)
        self.assertIsNone(re.search(r"\b(float|double)\b", pickups))


if __name__ == "__main__":
    unittest.main()
