import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from run_scenario import check_state_assertion, map_symbol_address


class ScenarioStateAssertionsTest(unittest.TestCase):
    def test_resolves_linker_map_bss_symbol(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "game.map"
            path.write_text(" .bss.other 0x02001000 0x4\n"
                            " .bss.g_nav_state\n"
                            "                0x02001004 0x28 build/main.o\n")
            self.assertEqual(map_symbol_address(path, "g_nav_state"), 0x02001004)

    def test_checks_actual_position_delta(self):
        samples = {"spawn": {"x": 1000}, "walk": {"x": 1800}}
        result = check_state_assertion(samples, {
            "from": "spawn", "to": "walk", "field": "x", "min_abs_delta": 512,
        })
        self.assertTrue(result["passed"])
        self.assertEqual(result["delta"], 800)

    def test_checks_wall_stop_with_bounded_delta(self):
        samples = {"at_wall": {"x": 4200}, "after_hold": {"x": 4200}}
        result = check_state_assertion(samples, {
            "from": "at_wall", "to": "after_hold", "field": "x", "max_abs_delta": 0,
        })
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
