"""Contract of the arena map package (assets/sprites/arenas/<name>).

Checks the exported lab package against assets/arenas/arenas.json: image
sizes, collision.json vs collision.png, spawn and enemy points on walkable
ground, one connected walkable region, the walkable cells being exactly the
floor minus the blocks (so the decoration adds no collision), the silhouette
of the render and the occlusion depth data (so the decoration adds no
occlusion, and every wall and pillar does occlude where it should).
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
SIZE_W, SIZE_H = SPEC["image"]
CELL = 4
PPM = SPEC["pixels_per_metre"]
COS30 = math.cos(math.radians(30))
BODY_RX, BODY_RY = 6, 3      # body footprint ellipse on screen (6 ground px radius, 2:1)
VISUAL_TOL = 3               # silhouette of the render vs spec
FLOOR = SPEC["floor"]["rect"]
WALL_PX = SPEC["boundary_wall_height_m"] * COS30 * PPM
WALL_T_PX = 0.34 * PPM       # boundary wall thickness on screen (x)
SLAB_PX = 0.25 * COS30 * PPM


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


def expected_occluder_rects(arena):
    """Screen rectangles (x0, y0, x1, y1) that may hold occluding pixels: every block seen
    from its front edge up to its top, and the boundary walls. Anything else is spurious."""
    fx0, fy0, fx1, fy1 = FLOOR
    rects = [(fx0 - WALL_T_PX - 2, fy0 - WALL_PX - 9, fx1 + WALL_T_PX + 2, fy0 + 1),   # back wall
             (fx0 - WALL_T_PX - 2, fy0 - WALL_PX - 9, fx0 + 1, fy1 + 1),               # left wall
             (fx1 - 1, fy0 - WALL_PX - 9, fx1 + WALL_T_PX + 2, fy1 + 1)]               # right wall
    for b in arena["blocks"]:
        x0, y0, x1, y1 = b["rect"]
        h_px = b["height_m"] * COS30 * PPM
        rects.append((x0 - 8, y0 - h_px - 8, x1 + 8, y1 + 1))   # extended ends may reach into a neighbour
    return rects


class ArenaExportTest(unittest.TestCase):
    def arenas(self):
        return [(arena, *load_arena(arena)) for arena in SPEC["arenas"]]

    def test_spec_lists_the_dungeon(self):
        self.assertEqual([a["name"] for a in SPEC["arenas"]], ["dungeon_01"])
        self.assertEqual((SIZE_W, SIZE_H), (768, 768))
        self.assertEqual(FLOOR, [16, 120, 752, 752])

    def test_image_sizes_and_settings(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                self.assertEqual(world.shape, (SIZE_H, SIZE_W, 3))
                self.assertEqual(occ.shape, (SIZE_H, SIZE_W, 3))
                self.assertEqual(col_img.shape, (SIZE_H, SIZE_W))
                with Image.open(OUT / arena["name"] / "occlusion.png") as img:
                    self.assertEqual(img.size, (SIZE_W, SIZE_H))
                self.assertEqual((col_json["mapWidth"], col_json["mapHeight"]), (SIZE_W, SIZE_H))
                self.assertEqual((col_json["gridWidth"], col_json["gridHeight"]), (SIZE_W // CELL, SIZE_H // CELL))
                self.assertEqual(col_json["cellSize"], CELL)
                s = json.loads((OUT / arena["name"] / "map_settings.json").read_text(encoding="utf-8"))
                self.assertEqual((s["width"], s["height"]), (SIZE_W, SIZE_H))
                self.assertEqual(s["pixelsPerMeter"], PPM)
                self.assertAlmostEqual(s["orthoScaleMeters"], SIZE_W / PPM, places=3)
                self.assertEqual(s["cameraElevationDegrees"], 30)

    def test_collision_json_matches_png(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                grid = np.array(col_json["walkableGrid"], dtype=np.uint8)
                self.assertEqual(grid.shape, (SIZE_H // CELL, SIZE_W // CELL))
                from_png = (col_img >= 128).reshape(SIZE_H // CELL, CELL, SIZE_W // CELL, CELL)
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
        """The floor tiles, thresholds, bands and neon add no collision and no hole."""
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                grid = np.array(col_json["walkableGrid"], dtype=bool)
                fx0, fy0, fx1, fy1 = FLOOR
                expected = np.zeros_like(grid)
                gx = np.arange(SIZE_W // CELL) * CELL + CELL // 2
                gy = np.arange(SIZE_H // CELL) * CELL + CELL // 2
                in_floor = ((gy >= fy0) & (gy < fy1))[:, None] & ((gx >= fx0) & (gx < fx1))[None, :]
                expected |= in_floor
                for b in arena["blocks"]:
                    x0, y0, x1, y1 = b["rect"]
                    expected &= ~(((gy >= y0) & (gy < y1))[:, None] & ((gx >= x0) & (gx < x1))[None, :])
                diff = np.argwhere(grid != expected)
                self.assertEqual(len(diff), 0, f"cells differ from the spec, first (gx,gy): {diff[:5][:, ::-1].tolist()}")

    def test_silhouette_of_the_render(self):
        fx0, fy0, fx1, fy1 = FLOOR
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                solid = world.max(axis=2) >= 5
                ys, xs = np.nonzero(solid)
                got = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
                want = (fx0 - WALL_T_PX, fy0 - WALL_PX - 0.34 * 0.5 * PPM, fx1 + WALL_T_PX, fy1 + SLAB_PX)
                for g, w, name in zip(got, want, ("left", "top", "right", "bottom")):
                    self.assertLessEqual(abs(g - w), VISUAL_TOL, f"{name}: got {g}, want {w:.1f}")
                # the floor itself is drawn edge to edge
                self.assertTrue(solid[fy0:fy1, fx0:fx1].all(), "floor with void holes")

    def test_occlusion_depth_is_consistent_with_blocks(self):
        for arena, world, occ, col_img, col_json in self.arenas():
            with self.subTest(arena=arena["name"]):
                flag = occ[:, :, 2] >= 128
                ground = np.where(flag, occ[:, :, 0] * 256 + occ[:, :, 1], -1)
                void = world.max(axis=2) < 5
                self.assertEqual(int((flag & void).sum()), 0, "occluder over void")
                ys = np.arange(SIZE_H)[:, None]
                self.assertEqual(int((flag & (ground < ys)).sum()), 0, "ground contact above the pixel")
                occ_png = np.array(Image.open(OUT / arena["name"] / "occlusion.png").convert("L")) >= 128
                self.assertTrue(np.array_equal(occ_png, flag), "occlusion.png must mirror occlusion_depth.png")

                # no occluder outside the blocks and boundary walls (decoration must not occlude)
                allowed = np.zeros_like(flag)
                for x0, y0, x1, y1 in expected_occluder_rects(arena):
                    allowed[max(0, int(y0)):int(y1) + 1, max(0, int(x0)):int(x1) + 1] = True
                spurious = np.argwhere(flag & ~allowed)
                self.assertEqual(len(spurious), 0, f"spurious occluders, first (x,y): {spurious[:5][:, ::-1].tolist()}")

                for b in arena["blocks"]:
                    x0, y0, x1, y1 = b["rect"]
                    h_px = b["height_m"] * COS30 * PPM
                    xc = (x0 + x1) // 2
                    # the top face occludes and its ground contact lies inside the block footprint
                    y_top = int((y0 + y1) / 2 - h_px)
                    self.assertTrue(flag[y_top, xc], f"block {b['rect']}: top face at y={y_top} is not an occluder")
                    self.assertGreaterEqual(ground[y_top, xc], y0 - 3)
                    self.assertLessEqual(ground[y_top, xc], y1 + 2)
                    # the front face: ground contact at its base unless a block in front of it hides that pixel
                    probe = y1 - 12
                    hidden = any(o["rect"][0] <= xc < o["rect"][2] and o["rect"][3] > y1
                                 and o["rect"][1] - o["height_m"] * COS30 * PPM <= probe <= o["rect"][3]
                                 for o in arena["blocks"] if o is not b)
                    if not hidden:
                        self.assertTrue(flag[probe, xc], f"block {b['rect']}: front face not an occluder")
                        self.assertLessEqual(abs(int(ground[probe, xc]) - y1), 2, "front face ground contact")
                        # an actor standing behind the block (feet above its front edge) is hidden by
                        # its pixels, one standing in front of it (feet below) is not
                        self.assertLess(int(y0) - 6, ground[probe, xc])
                        self.assertGreater(y1 + 6, ground[probe, xc])


if __name__ == "__main__":
    unittest.main()
