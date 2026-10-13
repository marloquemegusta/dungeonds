#!/usr/bin/env python3
"""Bake the FBX RGB15 world bitmap into a 256-color 8bpp hardware BG."""
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
header_source = (ROOT / "include/diablo_dungeon.h").read_text(encoding="utf-8")
WIDTH = int(re.search(r"#define WORLD_W (\d+)", header_source).group(1))
HEIGHT = int(re.search(r"#define WORLD_H (\d+)", header_source).group(1))
TILE = 8
if WIDTH % TILE or HEIGHT % TILE:
    raise SystemExit("world dimensions must be multiples of 8 pixels")

if len(sys.argv) > 1:
    colors = np.fromfile(sys.argv[1], dtype="<u2")
else:
    source = (ROOT / "source/diablo_dungeon.c").read_text(encoding="utf-8")
    match = re.search(
        r"g_dungeon_world_color\[WORLD_W \* WORLD_H\].*?=\s*\{(.*?)\};",
        source,
        re.S,
    )
    if match is None:
        raise SystemExit("g_dungeon_world_color not found; pass a raw BGR555 source image")
    colors = np.array(
        [int(value, 16) for value in re.findall(r"0x[0-9a-fA-F]+", match.group(1))],
        dtype=np.uint16,
    )
if colors.size != WIDTH * HEIGHT:
    raise SystemExit(f"expected {WIDTH * HEIGHT} pixels, found {colors.size}")
colors = colors.reshape(HEIGHT, WIDTH)

# The source is a dungeon slab projected isometrically into a diamond.
# Preserve the canvas background as transparent void outside that slab; this same
# mask drives both the hardware floor and player collision.
from collections import deque

background_color = int(colors[0, 0])
corners = (colors[0, -1], colors[-1, 0], colors[-1, -1])
if any(int(color) != background_color for color in corners):
    raise SystemExit(f"{WIDTH}x{HEIGHT} source bake must have one flat color in all four corners")
background = colors == background_color
outside = np.zeros((HEIGHT, WIDTH), dtype=bool)
queue = deque()
for x in range(WIDTH):
    for y in (0, HEIGHT - 1):
        if background[y, x] and not outside[y, x]:
            outside[y, x] = True
            queue.append((y, x))
for y in range(HEIGHT):
    for x in (0, WIDTH - 1):
        if background[y, x] and not outside[y, x]:
            outside[y, x] = True
            queue.append((y, x))
while queue:
    py, px = queue.popleft()
    for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
        if 0 <= ny < HEIGHT and 0 <= nx < WIDTH and background[ny, nx] and not outside[ny, nx]:
            outside[ny, nx] = True
            queue.append((ny, nx))
colors = colors.copy()
colors[outside] = 0

rgb = np.stack(
    (((colors & 31) << 3), (((colors >> 5) & 31) << 3), (((colors >> 10) & 31) << 3)),
    axis=-1,
).astype(np.uint8)
quantized = Image.fromarray(rgb).quantize(colors=255, method=Image.Quantize.MEDIANCUT)
indices = np.asarray(quantized, dtype=np.uint8) + 1
indices[colors == 0] = 0  # text BG palette index 0 is transparent
palette_rgb = quantized.getpalette()[: 255 * 3]
palette_rgb.extend([0] * (255 * 3 - len(palette_rgb)))
palette = [0]
for i in range(255):
    r, g, b = (palette_rgb[i * 3 + c] >> 3 for c in range(3))
    palette.append(0x8000 | r | (g << 5) | (b << 10))

tiles = [bytes(TILE * TILE)]
tile_ids = {tiles[0]: 0}
map_width = WIDTH // TILE
map_height = HEIGHT // TILE
tilemap = np.empty((map_height, map_width), dtype=np.uint16)
for ty in range(map_height):
    for tx in range(map_width):
        tile = indices[ty * TILE : (ty + 1) * TILE, tx * TILE : (tx + 1) * TILE].tobytes()
        tile_id = tile_ids.get(tile)
        if tile_id is None:
            tile_id = len(tiles)
            tile_ids[tile] = tile_id
            tiles.append(tile)
        tilemap[ty, tx] = tile_id

tile_bytes = len(tiles) * TILE * TILE
map_bytes = tilemap.nbytes
# 0xFFFF is reserved by the runtime cache as BG_TILE_INVALID.
if len(tiles) > 0xFFFF:
    raise SystemExit(f"tile map exceeds its usable 16-bit tile-ID limit: {len(tiles)} unique tiles")

header = ROOT / "include/dungeon_bg_tiles.h"
header.write_text(
    """#ifndef DUNGEON_BG_TILES_H
#define DUNGEON_BG_TILES_H

#include <nds.h>

#define DUNGEON_BG_PALETTE_SIZE 256
#define DUNGEON_BG_NUM_TILES %d
#define DUNGEON_BG_MAP_WIDTH_TILES %d
#define DUNGEON_BG_MAP_HEIGHT_TILES %d

extern const uint16_t g_dungeon_bg_palette[DUNGEON_BG_PALETTE_SIZE];
extern const uint8_t g_dungeon_bg_tiles[DUNGEON_BG_NUM_TILES][64];
extern const uint16_t g_dungeon_bg_map[DUNGEON_BG_MAP_HEIGHT_TILES][DUNGEON_BG_MAP_WIDTH_TILES];

#endif
""" % (len(tiles), map_width, map_height),
    encoding="utf-8",
)

with (ROOT / "source/dungeon_bg_tiles.c").open("w", encoding="utf-8") as out:
    out.write('#include "dungeon_bg_tiles.h"\n\n')
    out.write("const uint16_t g_dungeon_bg_palette[256] __attribute__((aligned(4))) = {\n")
    for start in range(0, 256, 16):
        out.write("    " + ", ".join(f"0x{x:04X}" for x in palette[start : start + 16]) + ",\n")
    out.write("};\n\n")
    out.write(f"const uint8_t g_dungeon_bg_tiles[{len(tiles)}][64] __attribute__((aligned(4))) = {{\n")
    for tile_id, tile in enumerate(tiles):
        out.write("    {\n        ")
        out.write(", ".join(f"0x{pixel:02X}" for pixel in tile))
        out.write("\n    },\n")
    out.write("};\n\n")
    out.write(f"const uint16_t g_dungeon_bg_map[{map_height}][{map_width}] __attribute__((aligned(4))) = {{\n")
    for row in tilemap:
        out.write("    { " + ", ".join(str(int(x)) for x in row) + " },\n")
    out.write("};\n")

print(f"FBX_BG_TILES={len(tiles)} TILE_ATLAS_BYTES={tile_bytes} MAP={map_width}x{map_height} MAP_BYTES={map_bytes} STATIC_ASSET_BYTES={tile_bytes + map_bytes}")
