import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class TideContractTests(unittest.TestCase):
    def test_tide_spring_curve_and_equilibrium(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "tide_host_test.exe"
            sources = [ROOT / "tests" / "host" / "tide_host_test.c"]
            build = subprocess.run(
                ["gcc", "-std=gnu11", "-O1", "-Wall", "-Werror",
                 "-I", str(ROOT / "tests" / "host" / "stubs"),
                 "-I", str(ROOT / "include"),
                 *map(str, sources), "-o", str(exe)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("TIDE_HOST_TEST=PASS", run.stdout)


if __name__ == "__main__":
    unittest.main()
