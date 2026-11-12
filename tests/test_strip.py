import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class StripHostTest(unittest.TestCase):
    def test_strip_runtime_contracts(self):
        source = (ROOT / "source" / "strip.c").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(?:float|double|malloc)\b", source))
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "strip_host_test.exe"
            sources = [ROOT / "tests" / "host" / "strip_host_test.c",
                       ROOT / "tests" / "host" / "strip_fake_kit.c",
                       ROOT / "source" / "strip.c",
                       ROOT / "source" / "arena.c"]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror",
                 "-I", str(ROOT / "tests" / "host" / "stubs"), "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("STRIP_HOST_TEST=PASS", run.stdout)

    def test_rebase_preparation_matches_reference(self):
        # Four variants (reference, prepared, slow path, half prepared) must hash equal over 20
        # rebases; the harness also fails on a stage overflow or a rebase that does not shift.
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "strip_rebase_equiv.exe"
            sources = [ROOT / "tests" / "host" / "strip_rebase_equiv.c",
                       ROOT / "tests" / "host" / "strip_rebase_ref.c",
                       ROOT / "source" / "strip_kit.c"]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror",
                 "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("STRIP_REBASE_EQUIV=PASS", run.stdout)

    def test_navigation_survives_strip_rebases(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "strip_nav_host_test.exe"
            sources = [ROOT / "tests" / "host" / "strip_nav_host_test.c",
                       ROOT / "tests" / "host" / "strip_fake_kit.c",
                       ROOT / "source" / "strip.c",
                       ROOT / "source" / "arena.c",
                       ROOT / "source" / "navfield.c",
                       ROOT / "source" / "collision.c"]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror",
                 "-I", str(ROOT / "tests" / "host" / "stubs"), "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("STRIP_NAV_HOST_TEST=PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
