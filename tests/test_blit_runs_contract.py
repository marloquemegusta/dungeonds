import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_sprite_ground_anchor import streamed_block  # noqa: E402

# (symbol stem, number of frames per direction)
SETS = [
    ("player", 8),
    ("charger", 8),
    ("ojo", 8),
    ("exvoto", 8),
    ("exvoto_pray_stand", 8),
    ("exvoto_pray_kneel", 8),
    ("exvoto_stand_up", 8),
    ("charger_charge", 4),
    ("charger_telegraph", 1),
    ("player_shot", 8),
]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def array_body(text, name):
    m = re.search(r"\b" + re.escape(name) + r"\[[^=;{]*=\s*\{", text)
    assert m, name
    end = text.index("\n};", m.end())
    return text[m.end():end]


def ints(body, base=10):
    if base == 16:
        return [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]+", body)]
    return [int(v) for v in re.findall(r"\d+", body)]


class BlitRunsContractTest(unittest.TestCase):
    def test_runs_are_exactly_the_opaque_runs_of_every_frame(self):
        c = read("source/player_sprite.c")
        for stem, nframes in SETS:
            pixels = streamed_block(stem, "frames") or ints(array_body(c, "g_%s_frames" % stem), 16)
            offs = ints(array_body(c, "g_%s_frame_offsets" % stem))
            bounds = ints(array_body(c, "g_%s_frame_bounds" % stem))
            runs = streamed_block(stem, "runs") or ints(array_body(c, "g_%s_runs" % stem))
            roffs = ints(array_body(c, "g_%s_run_offsets" % stem))
            self.assertEqual(len(offs), 8 * nframes, stem)
            self.assertEqual(len(roffs), 8 * nframes, stem)
            self.assertEqual(len(bounds), 8 * nframes * 4, stem)
            for f in range(8 * nframes):
                bw, bh = bounds[f * 4 + 2], bounds[f * 4 + 3]
                if bw == 0 or bh == 0:
                    continue
                pitch = (bw + 1) & ~1
                base, rb = offs[f], roffs[f]
                self.assertEqual(rb % 2, 0, "run block must be word aligned")
                for y in range(bh):
                    row = pixels[base + y * pitch:base + y * pitch + bw]
                    expected = []
                    x = 0
                    while x < bw:
                        if row[x] & 0x8000:
                            x0 = x
                            while x < bw and row[x] & 0x8000:
                                x += 1
                            expected.append(x0 | ((x - x0) << 8))
                        else:
                            x += 1
                    r0, r1 = runs[rb + y], runs[rb + y + 1]
                    self.assertEqual(runs[rb + r0:rb + r1], expected, "%s frame %d row %d" % (stem, f, y))
                if bw & 1:
                    for y in range(bh):
                        self.assertEqual(pixels[base + y * pitch + bw], 0, "pad pixel must be transparent")

    def test_rom_growth_of_the_run_tables_stays_modest(self):
        c = read("source/player_sprite.c")
        total = 0
        for stem, _ in SETS:
            total += 2 * len(streamed_block(stem, "runs") or ints(array_body(c, "g_%s_runs" % stem)))
            total += 4 * len(ints(array_body(c, "g_%s_run_offsets" % stem)))
        self.assertLess(total, 150 * 1024)


if __name__ == "__main__":
    unittest.main()
