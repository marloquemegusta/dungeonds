"""Contract of the v0.1 arena map packages (assets/sprites/arenas/arena_0N).

Checks the exported lab packages against assets/arenas/arenas.json: image
sizes, collision.json vs collision.png, spawn and enemy points on walkable
ground, one connected walkable region, footprints in world.png and in the
collision grid, and the occlusion depth data around every block.
"""
import json
import math
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "assets/arenas/arenas.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets/sprites/arenas"
SIZE = 384
CELL = 4
PPM = SPEC["pixels_per_metre"]
COS30 = math.cos(math.radians(30))
BODY_RX, BODY_RY = 6, 3      # body footprint ellipse on screen (6 ground px radius, 2:1)
VISUAL_TOL = 3               # world.png footprints vs spec
FLOOR = SPEC["floor"]["rect"]


def load_arena(arena):
    d = OUT / arena["name"]
    world = np.array(Image.open(d / "world.png").convert("RGB"), dtype=np.int32)
    occ = np.array(Image.open(d / "occlusion_depth.png").convert("RGB"), dtype=np.int32)
    col_img = np.array(Image.open(d / "collision.png").convert("L"))
    col_json = json.loads((d / "collision.json").read_text(encoding="utf-8"))
    return world, occ, col_img, col_json


def cells_under_ellipse(x, y):
    """Collision cells touched by the body ellipse (centre = feet at x, y)."""
    cells = set()
    for k in range(32):
        a = 2 * math.pi * k / 32
        cells.add((int(math.floor(x + BODY_RX * math.cos(a))) // CELL,
                   int(math.floor(y + BODY_RY * math.sin(a))) // CELL))
    cells.add((int(x) // CELL, int(y) // CELL))
    return cells


def components(walk):
    seen = np.zeros_like(walk, dtype=bool)
    count = 0
    for sy, sx in zip(*np.nonzero(walk)):
        if seen[sy, sx]:
            continue
        count += 1
        stack = [(sy, sx)]
        seen[sy, sx] = True
        while stack:
            y, x = stack.pop()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < walk.shape[0] and 0 <= nx < walk.shape[1] and walk[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
    return count


def first_change(world, start, step, fixed, axis, tol=8):
    """Walk from `start` along `axis` ('x' or 'y') until the colour changes."""
    ref = world[fixed, start] if axis == "x" else world[start, fixed]
    pos = start
    while 0 < pos < SIZE - 1:
        px = world[fixed, pos] if axis == "x" else world[pos, fixed]
        if np.abs(px - ref).max() > tol:
            return pos
        pos += step
    return pos


class ArenaExportTest(unittest.TestCase):
    def arenas(self):
        loaded = []
        for arena in SPEC["arenas"]:
            loaded.append((arena, *load_arena(arena)))
        return loaded

    def test_spec_lists_four_arenas(self):
        self.assertEqual([a["name"] for a in SPEC["arenas"]], [f"arena_0{i}" for i in range(1, 5)])

    def test_image_sizes_and_settings(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                self.assertEqual(world.shape, (SIZE, SIZE, 3))
                self.assertEqual(occ.shape, (SIZE, SIZE, 3))
                self.assertEqual(col_img.shape, (SIZE, SIZE))
                with Image.open(OUT / arena["name"] / "occlusion.png") as img:
                    self.assertEqual(img.size, (SIZE, SIZE))
                self.assertEqual((col_json["mapWidth"], col_json["mapHeight"]), (SIZE, SIZE))
                self.assertEqual((col_json["gridWidth"], col_json["gridHeight"]), (SIZE // CELL, SIZE // CELL))
                self.assertEqual(col_json["cellSize"], CELL)
                s = json.loads((OUT / arena["name"] / "map_settings.json").read_text(encoding="utf-8"))
                self.assertEqual((s["width"], s["height"]), (SIZE, SIZE))
                self.assertEqual(s["pixelsPerMeter"], PPM)
                self.assertAlmostEqual(s["orthoScaleMeters"], SIZE / PPM, places=3)
                self.assertEqual(s["cameraElevationDegrees"], 30)

    def test_collision_json_matches_png(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                grid = np.array(col_json["walkableGrid"], dtype=np.uint8)
                self.assertEqual(grid.shape, (SIZE // CELL, SIZE // CELL))
                from_png = (col_img >= 128).reshape(SIZE // CELL, CELL, SIZE // CELL, CELL)
                self.assertTrue(np.all(from_png.all(axis=(1, 3)) == from_png.any(axis=(1, 3))),
                                "collision.png must be made of whole 4 px cells")
                self.assertTrue(np.array_equal(from_png.all(axis=(1, 3)), grid.astype(bool)))

    def test_spawn_and_enemies_are_walkable(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                grid = np.array(col_json["walkableGrid"], dtype=bool)
                points = [("player_start", arena["player_start"])] + \
                    [(f"{e['type']}@{e['at']}", e["at"]) for e in arena["enemies"]]
                for label, (x, y) in points:
                    for cx, cy in cells_under_ellipse(x, y):
                        self.assertTrue(grid[cy, cx], f"{label}: body cell ({cx},{cy}) is blocked")

    def test_walkable_region_is_connected(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                self.assertEqual(components(np.array(col_json["walkableGrid"], dtype=bool)), 1)

    def test_walkable_area_is_floor_minus_blocks(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                grid = np.array(col_json["walkableGrid"], dtype=bool)
                fx0, fy0, fx1, fy1 = FLOOR
                for gy in range(SIZE // CELL):
                    for gx in range(SIZE // CELL):
                        cx, cy = gx * CELL + CELL // 2, gy * CELL + CELL // 2
                        in_floor = fx0 <= cx < fx1 and fy0 <= cy < fy1
                        in_block = any(b["rect"][0] <= cx < b["rect"][2] and b["rect"][1] <= cy < b["rect"][3]
                                       for b in arena["blocks"])
                        self.assertEqual(bool(grid[gy, gx]), in_floor and not in_block, f"cell {gx},{gy}")

    def test_floor_footprint_in_world(self):
        fx0, fy0, fx1, fy1 = FLOOR
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                front = first_change(world, 330, 1, 40, "y")           # slab edge below the floor
                back = first_change(world, 200, -1, 40, "y") + 1       # back wall face above it
                left = first_change(world, 100, -1, 330, "x") + 1
                right = first_change(world, 300, 1, 330, "x")
                self.assertLessEqual(abs(front - fy1), VISUAL_TOL, "front edge")
                self.assertLessEqual(abs(back - fy0), VISUAL_TOL, "back edge")
                self.assertLessEqual(abs(left - fx0), VISUAL_TOL, "left edge")
                self.assertLessEqual(abs(right - fx1), VISUAL_TOL, "right edge")

    def test_block_footprints_in_world_and_collision(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                walk = col_img >= 128
                for b in arena["blocks"]:
                    x0, y0, x1, y1 = b["rect"]
                    h_px = b["height_m"] * COS30 * PPM
                    top = y0 - h_px
                    xc = (x0 + x1) // 2
                    front_ref = world[y1 - 4, xc]
                    top_ref = world[int(top) + 3, xc]
                    m = (np.abs(world - front_ref).max(axis=2) <= 6) | (np.abs(world - top_ref).max(axis=2) <= 6)
                    win = np.zeros_like(m)
                    wy0 = max(0, int(top) - 3)
                    win[wy0:y1 + 4, max(0, x0 - 6):x1 + 7] = True
                    ys, xs = np.nonzero(m & win)
                    got = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
                    want = (x0, top, x1, y1)
                    for g, w, name in zip(got, want, ("left", "top", "right", "bottom")):
                        self.assertLessEqual(abs(g - w), VISUAL_TOL, f"{b['rect']} {name}: got {g}, want {w:.1f}")
                    # collision footprint: blocked bbox in a window around the rect
                    sub = ~walk[y0 - 12:y1 + 12, x0 - 12:x1 + 12]
                    sub[:max(0, 120 - (y0 - 12)), :] = False   # ignore the back wall rows
                    yy, xx = np.nonzero(sub)
                    cgot = (xx.min() + x0 - 12, yy.min() + y0 - 12, xx.max() + x0 - 11, yy.max() + y0 - 11)
                    for g, w, name in zip(cgot, b["rect"], ("left", "top", "right", "bottom")):
                        self.assertLessEqual(abs(g - w), CELL, f"collision {b['rect']} {name}: got {g}, want {w}")

    def test_occlusion_depth_is_consistent_with_blocks(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                flag = occ[:, :, 2] >= 128
                ground = np.where(flag, occ[:, :, 0] * 256 + occ[:, :, 1], -1)
                void = world.max(axis=2) < 5
                self.assertEqual(int((flag & void).sum()), 0, "occluder over void")
                ys = np.arange(SIZE)[:, None]
                self.assertEqual(int((flag & (ground < ys)).sum()), 0, "ground contact above the pixel")
                occ_png = np.array(Image.open(OUT / arena["name"] / "occlusion.png").convert("L")) >= 128
                self.assertTrue(np.array_equal(occ_png, flag), "occlusion.png must mirror occlusion_depth.png")
                for b in arena["blocks"]:
                    x0, y0, x1, y1 = b["rect"]
                    h_px = b["height_m"] * COS30 * PPM
                    xc = (x0 + x1) // 2
                    top = int(y0 - h_px)
                    # the whole visible column of the block occludes, ground contact within its footprint depth
                    for y in range(top + 3, y1 - 10):   # the lowest 0.25 m is below the lab occluder height
                        self.assertTrue(flag[y, xc], f"block {b['rect']} pixel y={y} not an occluder")
                        self.assertGreaterEqual(ground[y, xc], y0 - 3)
                        self.assertLessEqual(ground[y, xc], y1 + 2)
                    self.assertLessEqual(abs(int(ground[y1 - 12, xc]) - y1), 2, "front face ground contact")
                    # an actor standing behind the block (feet above its front edge) is hidden by its pixels,
                    # one standing in front of it (feet below) is not
                    self.assertLess(int(y0) - 6, ground[y1 - 12, xc])
                    self.assertGreater(y1 + 6, ground[y1 - 12, xc])
                    # open floor beside the block (nothing above it) does not occlude
                self.assertFalse(flag[y1 - 12, x1 + 12] and not any(
                    o["rect"][0] <= x1 + 12 < o["rect"][2] and o["rect"][1] - 80 <= y1 - 12 < o["rect"][3]
                    for o in arena["blocks"]), f"block {b['rect']}: occluder on open floor beside it")


if __name__ == "__main__":
    unittest.main()
