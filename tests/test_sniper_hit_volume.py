"""The sniper ray must hit wherever the stylus is on the enemy sprite (fix/sniper-hit-side)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_sprite_ground_anchor import exported_anchors, pixel_values  # noqa: E402

WEAPONS_C = (ROOT / "source" / "weapons.c").read_text(encoding="utf-8")
HIT_H = (ROOT / "include" / "hitvolume.h").read_text(encoding="utf-8")
CHARACTERS = {"charger": ("g_charger_frames", 1), "shooter": ("g_necron_frames", 2)}
MUZZLE_HEIGHTS = (14, 18, 22)


def hit_grid(height):
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "grid.exe"
        subprocess.run(["gcc", "-O1", "-Wall", "-Werror", "-I", str(ROOT / "include"),
                        str(ROOT / "tests" / "host" / "hitvolume_grid.c"), "-o", str(exe)], check=True)
        out = subprocess.run([str(exe), str(height)], check=True, capture_output=True, text=True).stdout
    grid = {}
    for line in out.splitlines():
        px, up, old, new, _ = map(int, line.split())
        grid[(px, up)] = (old, new)
    return grid


def opaque_pixels(symbol, char_id):
    """{direction: set of (dx, up) opaque offsets from the feet anchor, over the 8 frames}."""
    values = pixel_values(symbol)
    anchors = exported_anchors()[char_id]
    result = {}
    for d in range(8):
        pts = set()
        for f in range(8):
            frame = values[(d * 8 + f) * 1600:(d * 8 + f + 1) * 1600]
            for y in range(40):
                for x in range(40):
                    if frame[y * 40 + x] & 0x8000:
                        pts.add((x - 20, anchors[d] - y))
        result[d] = pts
    return result


def coverage(grid, pts, which):
    inside = sum(1 for p in pts if p in grid and grid[p][which])
    return inside / len(pts)


class SniperHitVolumeTests(unittest.TestCase):
    def test_new_volume_covers_the_sprite_old_one_did_not(self):
        for h in MUZZLE_HEIGHTS:
            grid = hit_grid(h)
            for name, (symbol, cid) in CHARACTERS.items():
                for d, pts in opaque_pixels(symbol, cid).items():
                    old, new = coverage(grid, pts, 0), coverage(grid, pts, 1)
                    self.assertGreaterEqual(new, 0.80, f"{name} dir{d} h{h}: new {new:.2f}")
                    self.assertGreater(new, old + 0.4, f"{name} dir{d} h{h}: old {old:.2f} new {new:.2f}")

    def test_volume_does_not_swallow_far_misses(self):
        grid = hit_grid(18)
        for far in ((-24, 20), (24, 20), (0, 40), (0, -8), (-24, 0), (24, 0)):
            self.assertEqual(grid[far][1], 0, f"stylus {far} must miss")

    def test_sweep_from_both_sides_on_a_south_facing_enemy(self):
        # The stylus sweeps the sprite height at the centre column and at +-10 px (the sides).
        grid = hit_grid(18)
        for px in (-10, 0, 10):
            hits = sum(grid[(px, up)][1] for up in range(0, 31))
            self.assertGreaterEqual(hits, 24, f"column {px}: {hits}/31 rows hit")

    def test_ray_uses_body_volume_and_no_float(self):
        # The sniper ray (fire_sniper) is the only caller since the C reticle (DESIGN.md 6.10) went away.
        self.assertGreaterEqual(WEAPONS_C.count("body_hit_test("), 1)
        self.assertNotIn("float", HIT_H)
        self.assertNotIn("double", HIT_H)


if __name__ == "__main__":
    unittest.main()
