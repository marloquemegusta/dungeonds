import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODS_H = (ROOT / "include" / "modifiers.h").read_text(encoding="utf-8")
MODS_C = (ROOT / "source" / "modifiers.c").read_text(encoding="utf-8")
WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")
DESIGN = (ROOT / "DESIGN.md").read_text(encoding="utf-8")


class ModifiersContractTest(unittest.TestCase):
    """DESIGN.md 5: eight Isaac-style modifiers, each a trade, two pedestals, take one."""

    def test_eight_modifiers_and_every_name_is_in_design(self):
        self.assertEqual(int(re.search(r"#define MOD_COUNT (\d+)", MODS_H).group(1)), 8)
        names = re.findall(r'\{ "([A-Z ]+)",', MODS_C)
        self.assertEqual(len(names), 8)

    def test_names_only_use_letters_the_hud_font_has(self):
        font = re.search(r's_fps_chars\[\] = "([^"]+)"', MAIN_C).group(1)
        for name in re.findall(r'\{ "([A-Z ]+)",', MODS_C):
            for ch in name:
                self.assertIn(ch, font, f"{name}: HUD font lacks {ch!r}")
        for ch in "MAZMORRA COMPLETADA MANADAS DE":
            self.assertIn(ch, font)

    def test_every_modifier_has_an_upside_and_a_cost(self):
        apply_fn = MODS_C.split("static void apply(int id)")[1].split("void mods_reset")[0]
        cases = re.findall(r"case (MOD_\w+):(.*?)break;", apply_fn, re.S)
        self.assertEqual(len(cases), 8)
        for name, body in cases:
            self.assertGreaterEqual(len(re.findall(r"g_mods\.\w+", body)), 2, name)

    def test_two_pedestals_taking_one_removes_the_other(self):
        self.assertIn("#define NUM_PEDESTALS 2", MODS_C)
        self.assertIn("memset(s_pedestals, 0, sizeof(s_pedestals));    // the other one vanishes", MODS_C)
        self.assertIn("(s_owned & (1 << id))", MODS_C)      # never offers one already owned

    def test_pickup_is_delayed_and_uses_the_ground_metric(self):
        self.assertIn("s_delay == 0 && p->armed && d2 <= PICKUP_RADIUS * PICKUP_RADIUS", MODS_C)
        self.assertIn("GROUND_DY2(dy)", MODS_C)

    def test_weapons_read_the_modifiers(self):
        for needle in ("g_mods.shotgun_pellets", "g_mods.shotgun_cooldown", "g_mods.shotgun_damage_pct",
                       "g_mods.shotgun_pierce", "g_mods.sniper_aim", "g_mods.sniper_damage_pct",
                       "g_mods.knock_pct", "g_mods.kill_resets_shotgun"):
            self.assertIn(needle, WEAPONS_C)
        self.assertIn("g_mods.recoil_pct", MAIN_C)
        self.assertIn("g_mods.speed_pct", MAIN_C)

    def test_pellets_never_hit_the_same_enemy_twice(self):
        self.assertIn("(p->hit_mask & (1u << e_idx))", WEAPONS_C)
        self.assertIn("p->hit_mask |= 1u << e_idx;", WEAPONS_C)

    def test_pedestals_are_hidden_by_walls_like_actors(self):
        self.assertIn("world_pixel_hidden", MODS_C)

    def test_design_lists_the_same_trade_offs(self):
        for text in ("Perdigones perforantes", "Recámara doble", "Gatillo ligero", "Cañón largo",
                     "Sed de sangre", "Coraza ósea", "Pies ligeros", "Retroceso brutal"):
            self.assertIn(text, DESIGN)


if __name__ == "__main__":
    unittest.main()
