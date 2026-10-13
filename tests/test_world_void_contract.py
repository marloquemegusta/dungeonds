import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "source/main.c").read_text(encoding="utf-8")
BG_SOURCE = (ROOT / "source/dungeon_bg_tiles.c").read_text(encoding="utf-8")
BG_HEADER = (ROOT / "include/dungeon_bg_tiles.h").read_text(encoding="utf-8")
WORLD_HEADER = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
WORLD_W = int(re.search(r"#define WORLD_W (\d+)", WORLD_HEADER).group(1))
WORLD_H = int(re.search(r"#define WORLD_H (\d+)", WORLD_HEADER).group(1))
MAP_W = int(re.search(r"#define DUNGEON_BG_MAP_WIDTH_TILES (\d+)", BG_HEADER).group(1))
MAP_H = int(re.search(r"#define DUNGEON_BG_MAP_HEIGHT_TILES (\d+)", BG_HEADER).group(1))


def read_bg_map():
    body = re.search(r"g_dungeon_bg_map[^=]*=\s*\{(.*?)\};", BG_SOURCE, re.S).group(1)
    values = [int(value) for value in re.findall(r"\b\d+\b", body)]
    return [values[row * MAP_W : (row + 1) * MAP_W] for row in range(MAP_H)]


def read_bg_tiles():
    body = re.search(r"g_dungeon_bg_tiles[^=]*=\s*\{(.*?)\};", BG_SOURCE, re.S).group(1)
    return [
        [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]+)", tile)]
        for tile in re.findall(r"\{([^{}]+)\}", body)
    ]


class WorldVoidContractTest(unittest.TestCase):
    def test_isometric_square_keeps_void_outside_its_diamond_edge(self):
        tile_map = read_bg_map()
        tiles = read_bg_tiles()

        def is_floor(x, y):
            tile_id = tile_map[y >> 3][x >> 3]
            return tiles[tile_id][(y & 7) * 8 + (x & 7)] != 0

        for point in ((0, 0), (WORLD_W - 1, 0), (0, WORLD_H - 1), (WORLD_W - 1, WORLD_H - 1),
                      (0, WORLD_H // 2), (WORLD_W - 1, WORLD_H // 2),
                      (WORLD_W // 2, 0), (WORLD_W // 2, WORLD_H - 1)):
            with self.subTest(point=point):
                self.assertFalse(is_floor(*point))
        for point in ((WORLD_W // 2, WORLD_H // 2),
                      (WORLD_W // 2, WORLD_H // 2 - 224),
                      (WORLD_W // 2, WORLD_H // 2 + 224),
                      (WORLD_W // 2 - 448, WORLD_H // 2),
                      (WORLD_W // 2 + 448, WORLD_H // 2)):
            with self.subTest(point=point):
                self.assertTrue(is_floor(*point))

        generator = (ROOT / "tools/generate_fbx_bg_tiles.py").read_text(encoding="utf-8")
        self.assertIn("background_color = int(colors[0, 0])", generator)
        self.assertIn("colors[outside] = 0", generator)
        self.assertNotIn("repeated_floor", generator)
        self.assertIn("uint16_t tile_id = g_dungeon_bg_map[py >> 3][px >> 3];", MAIN)
        self.assertIn("g_dungeon_bg_tiles[tile_id][(py & 7) * 8 + (px & 7)] != 0", MAIN)
        self.assertIn("if (!world_point_has_floor(px, py)) return 0;", MAIN)

    def test_collision_and_occlusion_masks_match_repeated_prop_transforms(self):
        assembler = (ROOT / "tools/assemble_wh40k_full_sector.py").read_text(encoding="utf-8")
        self.assertIn("bm_sector.from_mesh(p.data)", assembler)
        self.assertIn("sector_bvh = BVHTree.FromBMesh(bm_sector)", assembler)
        self.assertIn("matrix=p.matrix_world, verts=new_verts", assembler)
        self.assertIn("collision_bvh = BVHTree.FromBMesh(bm_collision)", assembler)
        self.assertIn("delta.dot(cam_right) * WORLD_W / ORTHO_SCALE", assembler)
        self.assertIn("-delta.dot(cam_up) * WORLD_H / view_h", assembler)
        self.assertIn("walk_samples = tuple((dx, dy) for dy in range(-2, 2) for dx in range(-2, 2))", assembler)
        self.assertIn("collision_bvh.ray_cast(", assembler)
        self.assertIn("SIDEWALK_Z + 25.0)),", assembler)
        self.assertIn("Vector((0.0, 0.0, -1.0)), 24.95)", assembler)
        self.assertIn("hit_co.z > SIDEWALK_Z + 0.01", assembler)
        self.assertIn("hit_high = (hit_hi_co is not None", assembler)
        self.assertIn("hit_co, _, _, _ = sector_bvh.ray_cast", assembler)
        self.assertIn("segment_x = g_dungeon_occlusion_segments[segment].x", MAIN)
        self.assertIn("run_depth = (int)run->depth + segment_y;", MAIN)
        self.assertIn("{0, 0}, {-6, 0}, {6, 0}, {0, -6}, {0, 6}", MAIN)

    def test_world_expansion_preserves_the_original_pixel_scale(self):
        assembler = (ROOT / "tools/assemble_wh40k_full_sector.py").read_text(encoding="utf-8")
        ortho = float(re.search(r"ORTHO_SCALE = ([0-9.]+)", assembler).group(1))
        width = int(re.search(r"WORLD_W = (\d+)", assembler).group(1))
        segments = int(re.search(r"MAP_SEGMENTS = (\d+)", assembler).group(1))
        self.assertEqual(ortho / width, 30.0 / 512.0)
        self.assertEqual(segments, 4)
        self.assertIn("range(-2, -2 + MAP_SEGMENTS * 5)", assembler)
        self.assertIn("segment * 50.0 - 75.0", assembler)
        self.assertGreater(WORLD_W, 512)
        self.assertGreater(WORLD_H, 512)

    def test_repeated_sector_collisions_exist_in_all_four_world_bands(self):
        source = (ROOT / "source/diablo_dungeon.c").read_text(encoding="utf-8")
        header = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
        payload = re.search(r"g_dungeon_collision[^=]*=\s*\{([^}]+)\}", source).group(1)
        packed = [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})", payload)]
        width = int(re.search(r"#define COLLISION_W (\d+)", header).group(1))
        height = int(re.search(r"#define COLLISION_H (\d+)", header).group(1))
        for band in range(4):
            y0, y1 = band * height // 4, (band + 1) * height // 4
            blocked = 0
            for cy in range(y0, y1):
                for cx in range(16, width - 16):
                    index = cy * width + cx
                    flags = (packed[index >> 2] >> ((index & 3) * 2)) & 3
                    blocked += (flags & 1) != 0
            with self.subTest(band=band):
                self.assertGreater(blocked, 100)

    def test_upper_screen_is_the_world_strip_above_lower_screen(self):
        self.assertIn("int top_cam_y = s_cam_y - SCREEN_H;", MAIN)

    def test_camera_tracks_player_into_black_void_at_world_edge(self):
        self.assertIn("int target_y = player_screen_y(s_player.x, s_player.y) - SCREEN_H / 2;", MAIN)
        self.assertNotIn("if (target_y < 0) target_y = 0;", MAIN)

    def test_dma_reads_flushed_actor_buffer(self):
        self.assertIn("s_bot_screen_buf[SCREEN_W * SCREEN_H] __attribute__((aligned(32)))", MAIN)
        self.assertGreaterEqual(MAIN.count("DC_FlushRange(s_bot_screen_buf, sizeof(s_bot_screen_buf));"), 2)


if __name__ == "__main__":
    unittest.main()
