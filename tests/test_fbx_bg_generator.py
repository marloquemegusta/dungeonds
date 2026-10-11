import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate_fbx_bg_tiles.py"


class FbxBackgroundGeneratorTest(unittest.TestCase):
    def test_generator_reserves_runtime_invalid_tile_id(self):
        source = GENERATOR.read_text(encoding="utf-8")
        self.assertRegex(source, r"if len\(tiles\) > 0xFFFF:")
        self.assertIn("0xFFFF is reserved by the runtime cache as BG_TILE_INVALID", source)

    def test_768px_world_with_over_1024_unique_tiles(self):
        width = height = 768
        tile_columns = width // 8
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "tools").mkdir()
            (project / "include").mkdir()
            (project / "source").mkdir()
            (project / "tools" / GENERATOR.name).write_bytes(GENERATOR.read_bytes())
            (project / "include" / "diablo_dungeon.h").write_text(
                f"#define WORLD_W {width}\n#define WORLD_H {height}\n",
                encoding="utf-8",
            )

            source_path = project / "source" / "diablo_dungeon.c"
            with source_path.open("w", encoding="utf-8") as source:
                source.write("const uint16_t g_dungeon_world_color[WORLD_W * WORLD_H] = {\n")
                for y in range(height):
                    tile_y, in_tile_y = divmod(y, 8)
                    row_values = []
                    for tile_x in range(tile_columns):
                        tile_id = tile_y * tile_columns + tile_x
                        bit_offset = in_tile_y * 8
                        pixels = [
                            "0x001F" if tile_id & (1 << (bit_offset + bit)) else "0x0000"
                            for bit in range(8)
                        ]
                        row_values.extend(pixels)
                    source.write(", ".join(row_values) + ",\n")
                source.write("};\n")

            result = subprocess.run(
                [sys.executable, str(project / "tools" / GENERATOR.name)],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            self.assertIn("FBX_BG_TILES=9216", result.stdout)
            self.assertIn("TILE_ATLAS_BYTES=589824", result.stdout)
            self.assertIn("MAP=96x96 MAP_BYTES=18432", result.stdout)
            self.assertIn("STATIC_ASSET_BYTES=608256", result.stdout)
            generated_header = (project / "include" / "dungeon_bg_tiles.h").read_text(
                encoding="utf-8"
            )
            self.assertRegex(generated_header, r"#define DUNGEON_BG_MAP_WIDTH_TILES 96")
            self.assertRegex(generated_header, r"#define DUNGEON_BG_MAP_HEIGHT_TILES 96")

    def test_generator_rejects_reserved_ffff_id(self):
        width = height = 2048
        tile_columns = width // 8

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "tools").mkdir()
            (project / "include").mkdir()
            (project / "source").mkdir()
            (project / "tools" / GENERATOR.name).write_bytes(GENERATOR.read_bytes())
            (project / "include" / "diablo_dungeon.h").write_text(
                f"#define WORLD_W {width}\\n#define WORLD_H {height}\\n",
                encoding="utf-8",
            )

            source_path = project / "source" / "diablo_dungeon.c"
            with source_path.open("w", encoding="utf-8") as source:
                source.write("const uint16_t g_dungeon_world_color[WORLD_W * WORLD_H] = {\\n")
                for y in range(height):
                    tile_y, in_tile_y = divmod(y, 8)
                    bit_offset = in_tile_y * 8
                    row_values = []
                    for tile_x in range(tile_columns):
                        tile_id = tile_y * tile_columns + tile_x
                        pixels = [
                            "0x001F" if bit_offset + bit < 16 and
                            tile_id & (1 << (bit_offset + bit)) else "0x0000"
                            for bit in range(8)
                        ]
                        row_values.extend(pixels)
                    source.write(", ".join(row_values) + ",\\n")
                source.write("};\\n")

            result = subprocess.run(
                [sys.executable, str(project / "tools" / GENERATOR.name)],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("usable 16-bit tile-ID limit: 65536", result.stderr)
            self.assertFalse((project / "include" / "dungeon_bg_tiles.h").exists())


if __name__ == "__main__":
    unittest.main()
