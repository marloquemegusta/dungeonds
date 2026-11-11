"""Parity between the C cathedral composer (source/strip.c) and the Python spec (catedral_plan).

The C kit is regrown with --mode catedral, so `source/strip_kit.c` is the same stamp table the ROM
uses. This test parses that table, asks the Python spec for its plan, and checks that a host build
of strip.c emits exactly the same (band, piece, phase, x, y) list. It also re-checks the layout
invariants on the plan (corridors, footprint share, no overlap) and the no-float contract.
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

STAMP_ROW = re.compile(
    r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*"
    r"(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*\},\s*//\s*(\w+)")


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


def parse_stamps(source):
    stamps = []
    for row in STAMP_ROW.finditer(source):
        (w, h, pc, pr, _anchor, _value, piece_id,
         tiles_ptr, foot_n, foot_ptr, _depth_n, _depth_ptr, name) = row.groups()
        w, h, pc, pr, piece_id, foot_n = map(int, (w, h, pc, pr, piece_id, foot_n))
        values = [int(v) for v in re.findall(r"\d+", array_body(source, tiles_ptr))]
        if len(values) != w * h:
            raise AssertionError(f"{name}: tile array has {len(values)} entries, expected {w * h}")
        tiles = [values[r * w:(r + 1) * w] for r in range(h)]
        foot_runs = []
        if foot_n:
            foot_runs = [tuple(map(int, m.groups())) for m in re.finditer(
                r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}", array_body(source, foot_ptr))]
            if len(foot_runs) != foot_n:
                raise AssertionError(f"{name}: foot array has {len(foot_runs)} runs, expected {foot_n}")
        stamps.append({"name": name, "piece_id": piece_id, "w": w, "h": h,
                       "phase_col": pc, "phase_row": pr, "tiles": tiles, "foot_runs": foot_runs})
    return stamps


def plan_tuples(plan, stamps):
    return [(e["band"], stamps[e["idx"]]["piece_id"], stamps[e["idx"]]["phase_col"],
             stamps[e["idx"]]["phase_row"], e["x"], e["y"])
            for e in plan if e["idx"] is not None]


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class StripLayoutParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.exists():
            raise unittest.SkipTest("source/strip_kit.c has not been baked")
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.stamps = parse_stamps(cls.source)
        cls.bake = load_bake()
        cls.plan = cls.bake.catedral_plan(cls.stamps, seed=0xC0DE1234, n_bands=64)

    def c_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "strip_layout_parity.exe"
            sources = [ROOT / "tests" / "host" / "strip_layout_parity.c",
                       ROOT / "source" / "strip.c", SOURCE]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror", "-DSTRIP_LAYOUT_DUMP=1",
                 "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
        rows = []
        for line in run.stdout.splitlines():
            parts = line.split()
            if len(parts) == 6:
                rows.append(tuple(int(v) for v in parts))
        return rows

    def test_c_matches_python_plan(self):
        self.assertGreater(len(self.stamps), 10)
        expected = plan_tuples(self.plan, self.stamps)
        self.assertGreater(len(expected), 100)
        self.assertEqual(self.c_layout(), expected)

    def test_layout_invariants(self):
        rows = self.bake.catedral_metrics(self.plan, self.stamps, bands=64)
        for row in rows:
            self.assertGreaterEqual(row["central"], 48, row)
            self.assertGreaterEqual(row["lateral"], 48, row)
        total_foot = sum(n * 16 for e in self.plan if e["idx"] is not None
                         for _x, _y, n in self.stamps[e["idx"]]["foot_runs"])
        share = 100.0 * total_foot / (416 * 64 * 128)
        self.assertLessEqual(share, 15.0, f"footprint share {share:.2f}% > 15%")

        by_band = {}
        for e in self.plan:
            if e["idx"] is None:
                continue
            band = e["band"]
            mask = self.bake._stamp_nz(self.stamps[e["idx"]])
            for ox, oy, om in by_band.setdefault(band, []):
                self.assertFalse(self.bake._masks_overlap(e["x"], e["y"] - band * 16, mask,
                                                          ox, oy, om),
                                 f"overlap in band {band} near x={e['x']}")
            by_band[band].append((e["x"], e["y"] - band * 16, mask))

    def test_composer_has_no_floating_point(self):
        source = STRIP_C.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(?:float|double)\b", source))
        self.assertIsNone(re.search(r"\b(?:float|double)\b", self.source))


class BenchGroupPlanTest(unittest.TestCase):
    """The bench plan places one glued 4-6 bench group per row and tramo, staggered and inside
    its own tramo (DESIGN.md, "Seccion de bancadas"). Runs on the baked kit; no host gcc needed."""

    @classmethod
    def setUpClass(cls):
        if not SOURCE.exists():
            raise unittest.SkipTest("source/strip_kit.c has not been baked")
        cls.stamps = parse_stamps(SOURCE.read_text(encoding="utf-8"))
        cls.bake = load_bake()
        cls.plan = cls.bake.catedral_plan(cls.stamps, seed=0xC0DE1234, n_bands=64)

    def bench_groups(self):
        groups = {}
        for e in self.plan:
            if e["idx"] is None:
                continue
            stamp = self.stamps[e["idx"]]
            if stamp["name"] not in ("banco_entero", "banco_roto"):
                continue
            self.assertIn(e["x"], (19, 35))
            self.assertEqual(stamp["phase_col"], 3)
            tramo = e["band"] >> 1
            row = 0 if e["x"] == 19 else 1
            slot = (e["band"] - tramo * 2) * 4 + (e["y"] - e["band"] * 16) // 4
            groups.setdefault((tramo, row), []).append(slot)
        return groups

    def test_one_glued_group_per_row_and_tramo(self):
        groups = self.bench_groups()
        self.assertGreater(len(groups), 10)
        for (tramo, row), slots in groups.items():
            slots.sort()
            self.assertIn(len(slots), (4, 5, 6), (tramo, row, slots))
            self.assertEqual(slots, list(range(slots[0], slots[0] + len(slots))),
                             f"tramo {tramo} row {row} has a hole: {slots}")
            self.assertGreaterEqual(slots[0], 0)
            self.assertLessEqual(slots[-1], 7)
            self.assertIn((tramo, 1 - row), groups, "both bench rows exist in a bancada tramo")

    def test_rows_stagger_when_they_would_share_the_same_slots(self):
        groups = self.bench_groups()
        for tramo in {t for t, _ in groups}:
            left, right = groups.get((tramo, 0)), groups.get((tramo, 1))
            if left and right and len(left) == len(right):
                self.assertNotEqual(left[0], right[0],
                                    f"tramo {tramo}: both groups start at {left[0]}")


if __name__ == "__main__":
    unittest.main()
