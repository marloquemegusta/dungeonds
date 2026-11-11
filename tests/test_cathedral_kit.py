import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CathedralKitContractTest(unittest.TestCase):
    def test_48px_walls_are_blocked_in_baker_and_runtime(self):
        baker = (ROOT / "tools/bake_cathedral_kit.py").read_text(encoding="utf-8")
        runtime = (ROOT / "source/strip.c").read_text(encoding="utf-8")
        self.assertIn("collision[:, :12] = 3", baker)
        self.assertIn("collision[:, 116:] = 3", baker)
        self.assertIn("#define STRIP_WALL_TILES 6", runtime)
        self.assertIn("#define STRIP_WALL_CELLS (STRIP_WALL_TILES * 2)", runtime)
        self.assertIn("STRIP_WALL_CELLS + x, 3", runtime)

    def test_baked_tile_and_window_budgets_and_sources(self):
        generated = (ROOT / "source/strip_kit.c").read_text(encoding="utf-8")
        metrics = re.search(r"floor=(\d+), props=(\d+), shared=(\d+), tiles=(\d+), worst_window=(\d+), worst_occlusion_window=(\d+)", generated)
        self.assertIsNotNone(metrics, "generated source must record palette and window metrics")
        floor_n, props_n, shared_n, tile_n, worst_n, worst_occ = map(int, metrics.groups())
        self.assertGreater(floor_n, 0)
        self.assertGreater(props_n, 0)
        self.assertLessEqual(shared_n, 256)
        self.assertLessEqual(tile_n, 1024)
        self.assertLess(worst_n, 440)
        self.assertLess(worst_occ, 32768)
        self.assertIn("from floor assets/environment/cathedral/floor/", generated)
        self.assertIn("assets/environment/cathedral/props/render", generated)

    def test_strip_runtime_has_no_floating_point_types(self):
        source = (ROOT / "source/strip.c").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(?:float|double)\b", source))

    def test_phase_slots_guard_invalid_x_and_tall_y_phases(self):
        baker = (ROOT / "tools/bake_cathedral_kit.py").read_text(encoding="utf-8")
        runtime = (ROOT / "source/strip.c").read_text(encoding="utf-8")
        # Python spec: the stamp must fit between the wall columns and inside its band.
        self.assertIn('if x < 6 or x + s["w"] > 58', baker)
        self.assertIn('if y_local < 0 or y_local + s["h"] > 16', baker)
        self.assertIn("pc, pr = x & 15, y & 15", baker)
        # Runtime: same x range and tall-y/band guards, and the (phase_col, phase_row) slots.
        self.assertIn("x_tile < STRIP_WALL_TILES", runtime)
        self.assertIn("x_tile + (int)stamp->w_tiles > STRIP_W_TILES - STRIP_WALL_TILES", runtime)
        self.assertIn("y_local < 0 || y_local + (int)stamp->h_tiles > STRIP_BAND_TILES", runtime)
        self.assertIn("(uint8_t)(x_tile & 15)", runtime)
        self.assertIn("(uint8_t)(y_tile & 15)", runtime)

    def test_props_option_defaults_to_the_selected_assets_and_single_phase_tombstones(self):
        baker = (ROOT / "tools/bake_cathedral_kit.py").read_text(encoding="utf-8")
        generated = (ROOT / "source/strip_kit.c").read_text(encoding="utf-8")
        defaults = ("banco_roto", "banco_volcado", "columna", "relicario", "santo", "vela",
                    "lapida_cruz_h", "lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v",
                    "lapida_cruz2_h", "lapida_cruz2_v", "lapida_caballero2_h", "lapida_caballero2_v",
                    "banco_entero", "sacos", "columna_entera")
        self.assertIn("DEFAULT_PROPS = (", baker)
        for name in defaults:
            self.assertIn(f'"{name}"', baker)
        self.assertIn('SINGLE_PHASE_PREFIXES = ("lapida_",)', baker)
        self.assertIn('p.add_argument("--props"', baker)
        self.assertIn("skipped", baker)
        # catedral mode bakes only the (piece, phase) pairs the determinist composer can place:
        # the old random set plus banco_entero, sacos and columna_entera.
        baked = ("banco_roto", "banco_volcado", "columna", "banco_entero", "sacos",
                 "columna_entera", "relicario", "santo", "vela", "lapida_cruz_h")
        for name in baked:
            self.assertIn(f"// {name}", generated)
        # Tombstones stay single-phase: only the one the plan uses is baked.
        for other in ("lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v",
                      "lapida_cruz2_h", "lapida_cruz2_v", "lapida_caballero2_h",
                      "lapida_caballero2_v"):
            self.assertNotIn(f"// {other}", generated)

    def test_tile_flip_bits_survive_top_cache_and_cpu_compositor(self):
        main = (ROOT / "source/main.c").read_text(encoding="utf-8")
        self.assertIn("entry & 0x0400u", main)
        self.assertIn("entry & 0x0800u", main)
        self.assertIn("tile_entry & 0x0c00u", main)


if __name__ == "__main__":
    unittest.main()
