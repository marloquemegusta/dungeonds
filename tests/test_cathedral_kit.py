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
        # Python spec: the stamp must fit between the wall columns and inside its block rows
        # (compositor v2: a columna may drop its last shadow row at the block edge, see _try_place).
        self.assertIn('if x < 6 or x + s["w"] > 58', baker)
        self.assertIn('y < lo or y >= hi', baker)
        self.assertIn("pc, pr = x & 15, y & 15", baker)
        # Runtime: same x range and row guards, and the (phase_col, phase_row) slots.
        self.assertIn("x_tile < STRIP_WALL_TILES", runtime)
        self.assertIn("x_tile + (int)stamp->w_tiles > STRIP_W_TILES - STRIP_WALL_TILES", runtime)
        self.assertIn("y_tile < row_lo || y_tile >= row_hi", runtime)
        self.assertIn("(uint8_t)(x_tile & 15)", runtime)
        self.assertIn("(uint8_t)(y_tile & 15)", runtime)

    def test_props_option_defaults_and_single_phase_lapidas(self):
        baker = (ROOT / "tools/bake_cathedral_kit.py").read_text(encoding="utf-8")
        generated = (ROOT / "source/strip_kit.c").read_text(encoding="utf-8")
        defaults = ("columna_entera", "banco_entero", "relicario", "vela",
                    "lapida_3x2_cruz", "lapida_3x2_cab", "lapida_2x1_cruz", "lapida_2x1_cab",
                    "banco_grupo4")
        self.assertIn("DEFAULT_PROPS = (", baker)
        for name in defaults:
            self.assertIn(f'"{name}"', baker)
        self.assertIn("LAPIDA_PHASE = (0, 2)", baker)
        self.assertIn('p.add_argument("--props"', baker)
        self.assertIn("skipped", baker)
        # catedral mode bakes only the (piece, phase) pairs the deterministic composer can use.
        # banco_entero is only the source of banco_grupo4, so it is not a stamp of its own.
        baked = ("columna_entera", "relicario", "vela", "banco_grupo4",
                 "lapida_3x2_cruz", "lapida_3x2_cab", "lapida_2x1_cruz", "lapida_2x1_cab")
        for name in baked:
            self.assertIn(f"// {name}\n", generated)
        self.assertNotIn("// banco_entero\n", generated)
        # Retired pieces are no longer baked (their PNG stay in assets/).
        for other in ("banco_roto", "banco_volcado", "columna", "santo", "sacos",
                      "lapida_cruz_h", "lapida_cruz_v", "lapida_caballero_h", "lapida_caballero_v",
                      "lapida_cruz2_h", "lapida_cruz2_v", "lapida_caballero2_h", "lapida_caballero2_v"):
            self.assertNotIn(f"// {other}\n", generated)

    def test_wall_map_and_lapidas_v5_are_wired_without_the_old_code(self):
        baker = (ROOT / "tools/bake_cathedral_kit.py").read_text(encoding="utf-8")
        generated = (ROOT / "source/strip_kit.c").read_text(encoding="utf-8")
        self.assertIn("def make_wall_map(", baker)
        self.assertIn("muro_izq_128.png", baker)
        self.assertIn("WALL_BACKDROP_RGB = (0x1c, 0x19, 0x20)", baker)
        self.assertIn("row[63 - tx] = entry ^ 0x400", baker)
        self.assertIn('lapidas_meta.json', baker)
        for old in ("make_cathedral_map", "lapida_tone", "LAPIDA_PAD", "CLUSTER_MARGIN",
                    "diamond_mask", "JOINT_RGB"):
            self.assertNotIn(old, baker)
        self.assertIn(".map_h_tiles = 16,", generated)

    def test_piece_ids_match_header_enum_in_order(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import bake_cathedral_kit as baker
        header = (ROOT / "include/strip_kit.h").read_text(encoding="utf-8")
        block = header[header.index("enum {"):header.index("};", header.index("enum {"))]
        names = [n.split("=")[0].strip().rstrip(",") for n in block.splitlines()[1:] if n.strip()]
        self.assertEqual(names[0], "STRIP_PIECE_NONE")
        self.assertEqual(names[-1], "STRIP_PIECE_COUNT")
        for i, enum_name in enumerate(names[1:-1], start=1):
            piece = enum_name[len("STRIP_PIECE_"):].lower()
            self.assertEqual(baker.PIECE_IDS[next(k for k in baker.PIECE_IDS if k.upper() == piece.upper())], i, enum_name)
        self.assertEqual(len(baker.PIECE_IDS), len(names) - 2)

    def test_tile_flip_bits_survive_top_cache_and_cpu_compositor(self):
        main = (ROOT / "source/main.c").read_text(encoding="utf-8")
        self.assertIn("entry & 0x0400u", main)
        self.assertIn("entry & 0x0800u", main)
        self.assertIn("tile_entry & 0x0c00u", main)


if __name__ == "__main__":
    unittest.main()
