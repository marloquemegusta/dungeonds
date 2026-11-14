"""Parity between the C cathedral composer (source/strip.c, compositor v2) and the Python spec
(tools/bake_cathedral_kit.py: catedral_block_plan, band_block).

The C kit is regrown with --mode catedral, so `source/strip_kit.c` is the same stamp table the ROM
uses. A host build of strip.c with -DSTRIP_LAYOUT_DUMP=1 prints:
  * the plan of blocks -16..5, piece by piece, in emission order;
  * the window (tiles and collision cells) after strip_start() and after one rebase.
The test rebuilds the same window from the Python plan and compares every cell. It also checks the
layout invariants of DESIGN.md 6.9.1b on 40 blocks, and the no-float contract of the composer.
"""
import importlib.util
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/strip_kit.c"
STRIP_C = ROOT / "source/strip.c"
HARNESS = ROOT / "tests" / "host" / "strip_layout_parity.c"
SEED = 0xC0DE1234
PLAN_BLOCKS = range(-16, 6)
BLOCK_ROWS = 48
CLEAR_BLOCKS = (4, 5)

STAMP_ROW = re.compile(
    r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*"
    r"(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*\},\s*//\s*(\w+)")
VALUE = re.compile(r"0x[0-9A-Fa-f]+|\d+")


def load_bake():
    spec = importlib.util.spec_from_file_location("bake_cathedral_kit",
                                                  ROOT / "tools/bake_cathedral_kit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def array_body(source, ptr):
    match = re.search(rf"static const [A-Za-z0-9_]+ {re.escape(ptr)}\[[^\]]+\][^=]*=\s*\{{(.*?)\n\}};",
                      source, re.S)
    if not match:
        raise AssertionError(f"generated array {ptr} not found")
    return match.group(1)


def values(body):
    return [int(v, 0) for v in VALUE.findall(body)]


def parse_stamps(source):
    stamps = []
    for row in STAMP_ROW.finditer(source):
        (w, h, pc, pr, _anchor, value, piece_id,
         tiles_ptr, foot_n, foot_ptr, _depth_n, _depth_ptr, name) = row.groups()
        w, h, pc, pr, piece_id, foot_n, value = map(int, (w, h, pc, pr, piece_id, foot_n, value))
        flat = values(array_body(source, tiles_ptr))
        if len(flat) != w * h:
            raise AssertionError(f"{name}: tile array has {len(flat)} entries, expected {w * h}")
        tiles = [flat[r * w:(r + 1) * w] for r in range(h)]
        foot_runs = []
        if foot_n:
            foot_runs = [tuple(map(int, m.groups())) for m in re.finditer(
                r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", array_body(source, foot_ptr))]
            if len(foot_runs) != foot_n:
                raise AssertionError(f"{name}: foot array has {len(foot_runs)} runs, expected {foot_n}")
        stamps.append({"name": name, "piece_id": piece_id, "w": w, "h": h, "value": value,
                       "phase_col": pc, "phase_row": pr, "tiles": tiles, "foot_runs": foot_runs})
    return stamps


def stamp_of(stamps, piece_id, pc, pr):
    return next(s for s in stamps if s["piece_id"] == piece_id and s["phase_col"] == pc
                and s["phase_row"] == pr)


def block_world(bake, stamps, source_floor, top_block, blocks):
    """Window rows and collision cells rebuilt from the block plan. Block b starts at window row
    48 * (b - top_block); the floor repeats every 16 tile rows and 32 cell rows."""
    floor_map, floor_cells = source_floor
    tiles = [[floor_map[r % 16][c] for c in range(64)] for r in range(256)]
    cells = [[floor_cells[(r % 32) * 128 + c] for c in range(128)] for r in range(512)]
    for block in blocks:
        if block in CLEAR_BLOCKS:
            continue
        top = BLOCK_ROWS * (block - top_block)
        for piece_id, pc, pr, x, y in bake.catedral_block_plan(stamps, SEED, block):
            stamp = stamp_of(stamps, piece_id, pc, pr)
            for sy in range(stamp["h"]):
                if y + sy >= BLOCK_ROWS or not 0 <= top + y + sy < 256:
                    continue
                for sx in range(stamp["w"]):
                    if stamp["tiles"][sy][sx]:
                        tiles[top + y + sy][x + sx] = stamp["tiles"][sy][sx]
            for fx, fy, n in stamp["foot_runs"]:
                if 2 * y + fy >= 2 * BLOCK_ROWS:
                    continue
                row = 2 * (top + y) + fy
                if row >= 512 - 1:
                    continue
                for k in range(n):
                    cx = 2 * x + fx + k
                    if 0 < cx < 127:
                        cells[row][cx] = stamp["value"]
    for row in cells:
        for c in range(12):
            row[c] = 3
            row[127 - c] = 3
    cells[511] = [3] * 128
    return tiles, cells


def c_window(output, tag):
    tiles = [None] * 256
    cells = [None] * 512
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] != tag or parts[0] not in ("MAP", "COL"):
            continue
        row = int(parts[2])
        vals = [int(v) for v in parts[3:]]
        if parts[0] == "MAP":
            tiles[row] = vals
        else:
            cells[row] = vals
    return tiles, cells


def c_occlusion(output, tag):
    """(index, x, y, length, depth) of every occlusion run of the window, in array order."""
    count = None
    runs = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "OCCN" and parts[1] == tag:
            count = int(parts[2])
        elif len(parts) == 7 and parts[0] == "OCC" and parts[1] == tag:
            runs.append(tuple(int(v) for v in parts[2:]))
    if count is None or count != len(runs):
        raise AssertionError(f"{tag}: OCCN says {count}, dumped {len(runs)} runs")
    return runs


def c_row_start(output, tag):
    rows = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "ROW" and parts[1] == tag:
            rows[int(parts[2])] = int(parts[3])
    return [rows[y] for y in range(2049)]


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class CompositorV2ParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.exists():
            raise unittest.SkipTest("source/strip_kit.c has not been baked")
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.stamps = parse_stamps(cls.source)
        cls.bake = load_bake()
        cls.floor = (
            [values(array_body(cls.source, "s_floor_map"))[r * 64:(r + 1) * 64] for r in range(16)],
            values(array_body(cls.source, "s_floor_collision")),
        )
        cls.floor_cells = [0] * (32 * 128)
        packed = cls.floor[1]
        for r in range(32):
            for c in range(128):
                cls.floor_cells[r * 128 + c] = (packed[r * 32 + (c >> 2)] >> ((c & 3) * 2)) & 3
        cls.floor = (cls.floor[0], cls.floor_cells)
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "strip_layout_parity.exe"
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror", "-DSTRIP_LAYOUT_DUMP=1",
                 "-I", str(ROOT / "include"), str(HARNESS), str(STRIP_C), str(SOURCE),
                 "-o", str(exe)],
                capture_output=True, text=True)
            if build.returncode:
                raise AssertionError(build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            if run.returncode:
                raise AssertionError(run.stdout + run.stderr)
        cls.output = run.stdout

    def test_plan_matches_python_block_by_block(self):
        c_plan = {}
        for line in self.output.splitlines():
            parts = line.split()
            if parts and parts[0] == "PLAN":
                block, *rest = map(int, parts[1:])
                c_plan.setdefault(block, []).append(tuple(rest))
        self.assertEqual(sorted(c_plan), list(PLAN_BLOCKS))
        for block in PLAN_BLOCKS:
            expected = self.bake.catedral_block_plan(self.stamps, SEED, block)
            self.assertEqual(c_plan[block], list(expected), f"block {block}")
        self.assertGreater(sum(len(v) for v in c_plan.values()), 200)

    def test_window_tiles_and_collision_match_the_block_world(self):
        for tag, top in (("W0", 0), ("W1", -2)):
            with self.subTest(window=tag):
                tiles, cells = block_world(self.bake, self.stamps, self.floor, top,
                                           range(top, top + 6))
                c_tiles, c_cells = c_window(self.output, tag)
                bad_tiles = [r for r in range(256) if c_tiles[r] != tiles[r]]
                bad_cells = [r for r in range(512) if c_cells[r] != cells[r]]
                self.assertEqual(bad_tiles, [], f"{tag}: tile rows differ")
                self.assertEqual(bad_cells, [], f"{tag}: collision rows differ")

    def test_occlusion_runs_are_sorted_by_row_then_x_with_a_consistent_row_index(self):
        for tag in ("W0", "W1"):
            with self.subTest(window=tag):
                runs = c_occlusion(self.output, tag)
                self.assertGreater(len(runs), 1000)
                self.assertEqual([r[0] for r in runs], list(range(len(runs))))
                keys = [(r[2], r[1]) for r in runs]
                self.assertEqual(keys, sorted(keys), "runs not ordered by (y, x)")
                # row_start[y] = number of runs in rows < y, with the tail row clamped to 2048.
                counts = [0] * 2049
                for y, _x in keys:
                    counts[min(y, 2048)] += 1
                expected, total = [], 0
                for y in range(2049):
                    expected.append(total)
                    total += counts[y]
                self.assertEqual(c_row_start(self.output, tag), expected)


class CompositorV2InvariantsTest(unittest.TestCase):
    """DESIGN.md 6.9.1b, compositor v2: checked on the Python spec over 40 blocks."""

    @classmethod
    def setUpClass(cls):
        if not SOURCE.exists():
            raise unittest.SkipTest("source/strip_kit.c has not been baked")
        cls.stamps = parse_stamps(SOURCE.read_text(encoding="utf-8"))
        cls.bake = load_bake()
        cls.blocks = range(-17, 23)
        cls.records = {b: cls.bake._block_records(cls.stamps, SEED, b) for b in cls.blocks}

    def test_two_columns_per_screen(self):
        for block, acc in self.records.items():
            for s in (0, 1):
                top = s * 24
                cols = sorted(r["x"] for r in acc if r["cat"] == "struct"
                              and r["name"] == "columna_entera" and r["y"] == top + 9)
                self.assertEqual(cols, [7, 51], f"block {block} screen {s}")

    def test_bancadas_have_two_benches_and_a_central_aisle_of_64_to_88_px(self):
        checked = 0
        for block, acc in self.records.items():
            entries = [{"block": block, "name": self.stamps[r["idx"]]["name"], "idx": r["idx"],
                        "x": r["x"], "y": r["y"]} for r in acc]
            for s in (0, 1):
                top = s * 24
                benches = [r for r in acc if r["cat"] == "struct" and r["name"] == "banco_grupo4"
                           and top <= r["y"] < top + 24]
                if not benches:
                    continue
                checked += 1
                self.assertEqual(len(benches), 2, f"block {block} screen {s}")
                aisle = self.bake._screen_central_min(entries, self.stamps, block, s)
                self.assertGreaterEqual(aisle, 64, f"block {block} screen {s}")
                self.assertLessEqual(aisle, 88, f"block {block} screen {s}")
        self.assertGreater(checked, 20)

    def test_no_lapida_under_a_bench_or_a_relicario(self):
        for block, acc in self.records.items():
            solid = [r for r in acc if r["cat"] == "struct" and r["name"] in ("banco_grupo4", "relicario", "santo")]
            for lap in (r for r in acc if r["cat"] == "lap"):
                for other in solid:
                    self.assertFalse(self.bake._masks_overlap(lap["x"], lap["y"], lap["nz"],
                                                              other["x"], other["y"], other["nz"]),
                                     f"block {block}: {lap['name']} under {other['name']}")

    def test_no_piece_outside_the_usable_floor(self):
        for block, acc in self.records.items():
            for r in acc:
                w = self.stamps[r["idx"]]["w"]
                self.assertGreaterEqual(r["x"] * 8, 48, f"block {block} {r['name']}")
                self.assertLessEqual((r["x"] + w) * 8, 464, f"block {block} {r['name']}")

    def test_pieces_never_overlap_inside_a_block(self):
        for block, acc in self.records.items():
            for i, a in enumerate(acc):
                for b in acc[i + 1:]:
                    self.assertFalse(self.bake._masks_overlap(a["x"], a["y"], a["nz"],
                                                              b["x"], b["y"], b["nz"]),
                                     f"block {block}: {a['name']} and {b['name']} overlap")

    def test_footprint_share_and_piece_cap(self):
        plan = self.bake.catedral_plan(self.stamps, SEED, 64)
        rows = self.bake.catedral_metrics_v2(plan, self.stamps, window=4)
        for row in rows:
            self.assertLessEqual(row["footprint_pct"], 15.0, row)
        for block in self.blocks:
            self.assertLessEqual(len(self.records[block]), self.bake.BLOCK_MAX_PIECES, block)

    def test_lapida_stamp_phase_fits_the_damero_rule(self):
        """Every planned lapida carries the (pc, pr) that fits its tile: (x - pc) % 4 == 0 and
        (y - pr) % 2 == 0. Both baked phases, (0, 2) and (2, 3), must be used by the plan."""
        used = set()
        lapida_ids = {5, 6, 7, 8}
        for block in PLAN_BLOCKS:
            for piece_id, pc, pr, x, y in self.bake.catedral_block_plan(self.stamps, SEED, block):
                if piece_id not in lapida_ids:
                    continue
                self.assertEqual((x - pc) % 4, 0, f"block {block}: lapida at x={x} with pc={pc}")
                self.assertEqual((y - pr) % 2, 0, f"block {block}: lapida at y={y} with pr={pr}")
                used.add((pc, pr))
        self.assertEqual(used, {(0, 2), (2, 3)})

    def test_lapida_lookup_rejects_positions_no_phase_fits(self):
        lookup = self.bake._stamp_lookup
        self.assertIsNone(lookup(self.stamps, "lapida_3x2_cruz", 8, 1))
        self.assertIsNone(lookup(self.stamps, "lapida_3x2_cruz", 9, 2))
        hit = lookup(self.stamps, "lapida_3x2_cruz", 10, 1)
        self.assertEqual((self.stamps[hit]["phase_col"], self.stamps[hit]["phase_row"]), (2, 3))
        hit = lookup(self.stamps, "lapida_3x2_cruz", 8, 2)
        self.assertEqual((self.stamps[hit]["phase_col"], self.stamps[hit]["phase_row"]), (0, 2))

    def test_band_map_is_contiguous_and_top_down(self):
        self.assertEqual([self.bake.band_block(b) for b in range(3)], [(0, 0), (0, 16), (0, 32)])
        self.assertEqual([self.bake.band_block(b) for b in range(16, 22)],
                         [(-2, 0), (-2, 16), (-2, 32), (-1, 0), (-1, 16), (-1, 32)])
        for g in range(8):
            blocks = [self.bake.band_block(16 + 6 * g + k)[0] for k in range(6)]
            self.assertEqual(blocks, [-2 * (g + 1)] * 3 + [-2 * (g + 1) + 1] * 3)

    def test_composer_has_no_floating_point(self):
        source = STRIP_C.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(?:float|double)\b", source))
        self.assertIsNone(re.search(r"\b(?:float|double)\b", SOURCE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
