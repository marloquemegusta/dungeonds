import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = ["-I", str(ROOT / "tests" / "host" / "stubs")]
HOST = ROOT / "tests" / "host"
SRC = ROOT / "source"

# Se compilan y ejecutan a la vez en setUpClass (strip_rebase_equiv tarda ~9 s).
# nombre -> (fuentes, usa stubs, marca de PASS)
PROGRAMS = {
    "strip_host_test": ([HOST / "strip_host_test.c", HOST / "strip_fake_kit.c", SRC / "strip.c", SRC / "arena.c"],
                        True, "STRIP_HOST_TEST=PASS"),
    "strip_rebase_equiv": ([HOST / "strip_rebase_equiv.c", HOST / "strip_rebase_ref.c", SRC / "strip_kit.c"],
                           False, "STRIP_REBASE_EQUIV=PASS"),
    "strip_nav_host_test": ([HOST / "strip_nav_host_test.c", HOST / "strip_fake_kit.c", SRC / "strip.c",
                             SRC / "arena.c", SRC / "navfield.c", SRC / "collision.c"],
                            True, "STRIP_NAV_HOST_TEST=PASS"),
}


@unittest.skipUnless(shutil.which("gcc"), "needs a host C compiler")
class StripHostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.exes = {}

        def build(name):
            sources, stubs, _ = PROGRAMS[name]
            exe = Path(cls._tmp.name) / (name + ".exe")
            res = subprocess.run(["gcc", "-std=gnu11", "-O2", "-Wall", "-Werror", *(STUBS if stubs else []),
                                  "-I", str(ROOT / "include"), *map(str, sources), "-o", str(exe)],
                                 capture_output=True, text=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True) if res.returncode == 0 else None
            return name, res, run

        with ThreadPoolExecutor(max_workers=len(PROGRAMS)) as pool:
            cls.results = {n: (b, r) for n, b, r in pool.map(build, PROGRAMS)}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _run(self, name):
        build, run = self.results[name]
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn(PROGRAMS[name][2], run.stdout)

    def test_strip_runtime_contracts(self):
        self._run("strip_host_test")

    def test_rebase_preparation_matches_reference(self):
        # Cuatro variantes (referencia, preparada, camino lento, media preparada) deben dar el mismo hash.
        self._run("strip_rebase_equiv")

    def test_navigation_survives_strip_rebases(self):
        self._run("strip_nav_host_test")


if __name__ == "__main__":
    unittest.main()
