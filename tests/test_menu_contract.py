import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MENU_H = (ROOT / "include" / "menu.h").read_text(encoding="utf-8")
MENU_C = (ROOT / "source" / "menu.c").read_text(encoding="utf-8")
SFX_H = (ROOT / "include" / "sfx.h").read_text(encoding="utf-8")
SFX_C = (ROOT / "source" / "sfx.c").read_text(encoding="utf-8")
MAIN_C = (ROOT / "source" / "main.c").read_text(encoding="utf-8")


class MenuContractTest(unittest.TestCase):
    def test_no_float_or_double_in_menu_and_sfx(self):
        for path_name, content in (
            ("include/menu.h", MENU_H),
            ("source/menu.c", MENU_C),
            ("include/sfx.h", SFX_H),
            ("source/sfx.c", SFX_C),
        ):
            self.assertNotIn("float", content, f"Forbidden float found in {path_name}")
            self.assertNotIn("double", content, f"Forbidden double found in {path_name}")

    def test_menu_c_defines_states_and_strings(self):
        for state in ("MENU_TITLE", "MENU_PAUSE", "MENU_BESTIARY", "MENU_CONTROLS"):
            self.assertIn(state, MENU_C, f"Expected {state} in source/menu.c")

        labels = [
            "NUEVA PARTIDA",
            "CONTINUAR",
            "REINICIAR",
            "BESTIARIO",
            "CONTROLES",
            "PROXIMAMENTE",
            "VOLVER",
        ]
        for label in labels:
            self.assertIn(f'"{label}"', MENU_C, f'Expected "{label}" in source/menu.c')

        control_lines = [
            "CRUCETA - MOVERSE",
            "LAPIZ - APUNTAR Y CARGAR",
            "START - PAUSA",
            "SELECT/Y - EFECTOS DEMO",
        ]
        for line in control_lines:
            self.assertIn(f'"{line}"', MENU_C, f'Expected "{line}" in source/menu.c')

    def test_main_c_boot_menu_open_title_guard(self):
        guard_match = re.search(r"#if\s+!\(SANDBOX\s*\|\|\s*STRESS_TEST\)(.*?)#", MAIN_C, re.DOTALL)
        self.assertIsNotNone(guard_match, "Expected #if !(SANDBOX || STRESS_TEST) block in source/main.c")
        self.assertIn("menu_open_title();", guard_match.group(1))

    def test_main_c_handles_start_for_pause_when_alive(self):
        self.assertRegex(MAIN_C, r"KEY_START\b[^;]*!g_player_state\.is_dead|!g_player_state\.is_dead[^;]*KEY_START")
        self.assertIn("menu_open_pause();", MAIN_C)

    def test_main_c_preserves_start_in_restart_keys(self):
        match = re.search(r"restart_keys\s*=\s*([^;]+);", MAIN_C)
        self.assertIsNotNone(match, "Expected restart_keys definition in source/main.c")
        self.assertIn("KEY_START", match.group(1))

    def test_main_c_freezes_simulate_when_menu_open(self):
        match = re.search(r"int\s+simulate\s*=\s*([^;]+);", MAIN_C)
        self.assertIsNotNone(match, "Expected simulate definition in source/main.c")
        self.assertIn("!menu_is_open()", match.group(1))

    def test_main_c_calls_sfx_set_bgm_paused(self):
        self.assertIn("sfx_set_bgm_paused(", MAIN_C)


if __name__ == "__main__":
    unittest.main()
