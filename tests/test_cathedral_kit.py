import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


class CathedralKitContractTest(unittest.TestCase):
    def test_baked_tile_and_window_budgets(self):
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

    def test_generated_kit_stamps_are_exactly_the_baker_pieces(self):
        # The kit now serves only the encounter rooms (DESIGN.md 6.13.6): it bakes the pieces and
        # phases the plants, the corridor and the rastrillo ask for, not every PIECE_IDS entry.
        # banco_entero is only the source of banco_grupo4 / banco_grupo4_roto.
        import bake_cathedral_kit as baker
        generated = (ROOT / "source/strip_kit.c").read_text(encoding="utf-8")
        baked = set(re.findall(r"\},\s*//\s*(\w+)\s*$", generated, re.M))
        self.assertEqual(baked, set(baker.catedral_phase_map()))

    def test_piece_ids_match_header_enum_in_order(self):
        import bake_cathedral_kit as baker
        # The enum names the room role; the art folder (PIECE_IDS key) keeps its own name.
        aliases = {"columna_rota": "columna"}
        header = (ROOT / "include/strip_kit.h").read_text(encoding="utf-8")
        block = header[header.index("enum {"):header.index("};", header.index("enum {"))]
        names = [n.split("=")[0].strip().rstrip(",") for n in block.splitlines()[1:] if n.strip()]
        self.assertEqual(names[0], "STRIP_PIECE_NONE")
        self.assertEqual(names[-1], "STRIP_PIECE_COUNT")
        for i, enum_name in enumerate(names[1:-1], start=1):
            piece = enum_name[len("STRIP_PIECE_"):].lower()
            piece = aliases.get(piece, piece)
            self.assertEqual(baker.PIECE_IDS[next(k for k in baker.PIECE_IDS if k.upper() == piece.upper())], i, enum_name)
        self.assertEqual(len(baker.PIECE_IDS), len(names) - 2)


if __name__ == "__main__":
    unittest.main()
