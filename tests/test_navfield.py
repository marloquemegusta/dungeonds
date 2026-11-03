import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class NavFieldHostTest(unittest.TestCase):
    """Compiles the real collision + navigation code on the host and runs it on every baked arena."""

    def test_distance_field_over_the_baked_arenas(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "nav_host_test.exe"
            sources = [
                ROOT / "tests" / "host" / "nav_host_test.c",
                ROOT / "source" / "collision.c",
                ROOT / "source" / "navfield.c",
                ROOT / "source" / "los.c",
                ROOT / "source" / "arena.c",
                ROOT / "source" / "arenas.c",
                *sorted((ROOT / "source").glob("arena_*.c")),
            ]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror", "-I", str(ROOT / "tests" / "host" / "stubs"),
                 "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertIn("NAV_HOST_TEST=PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
