#!/usr/bin/env python3
"""Bake the vertical strip's repeating floor and low pillar stamps from a lab package.

Usage: python tools/bake_strip_kit.py [--package assets/sprites/arenas/strip_kit]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "assets/arenas/arenas.json"
DEFAULT_PACKAGE = ROOT / "assets/sprites/arenas/strip_kit"
OUTPUT = ROOT / "source/strip_kit.c"
TILE = 8
CELL = 4


def load_images(package):
    world = np.array(Image.open(package / "world.png").convert("RGB"))
    collision = np.array(Image.open(package / "collision.png").convert("L"))
    if world.shape[:2] != collision.shape[:2]:
        raise ValueError("world.png and collision.png dimensions differ")
    return world, collision


def quantize(world):
    image = Image.fromarray(world, "RGB")
    indexed_image = image.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    raw = indexed_image.getpalette()[:255 * 3]
    palette = [0]
    for i in range(0, len(raw), 3):
        r, g, b = raw[i:i + 3]
        palette.append((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) | 0x8000)
    palette.extend([0] * (256 - len(palette)))
    indexed = np.array(indexed_image, dtype=np.uint8) + 1
    indexed[(world[:, :, 0] < 5) & (world[:, :, 1] < 5) & (world[:, :, 2] < 5)] = 0
    return palette, indexed


def tiles_from_image(indexed, tiles, tile_ids):
    h, w = indexed.shape
    if w % TILE or h % TILE:
        raise ValueError("tile image bounds must be multiples of 8 pixels")
    result = np.zeros((h // TILE, w // TILE), dtype=np.uint16)
    for ty in range(h // TILE):
        for tx in range(w // TILE):
            data = bytes(indexed[ty * TILE:(ty + 1) * TILE,
                                 tx * TILE:(tx + 1) * TILE].reshape(-1))
            tile_id = tile_ids.get(data)
            if tile_id is None:
                tile_id = len(tiles)
                tile_ids[data] = tile_id
                tiles.append(data)
            result[ty, tx] = tile_id
    return result


def floor_collision(collision, y0, period_px, width):
    grid = np.zeros((period_px // CELL, width // CELL), dtype=np.uint8)
    for cy in range(grid.shape[0]):
        for cx in range(grid.shape[1]):
            cell = collision[y0 + cy * CELL:y0 + (cy + 1) * CELL,
                             cx * CELL:(cx + 1) * CELL]
            # The lab uses white for walkable floor; match bake_arena.py's 40% rule.
            grid[cy, cx] = 0 if np.mean(cell >= 128) > 0.40 else 3
    # The strip spec reserves 16 px at each edge for the two boundary walls.
    wall_cells = 16 // CELL
    grid[:, :wall_cells] = 3
    grid[:, -wall_cells:] = 3
    grid[:, wall_cells:-wall_cells] = 0
    return grid


def packed_collision(grid):
    flat = grid.reshape(-1)
    if flat.size % 4:
        flat = np.pad(flat, (0, 4 - flat.size % 4))
    return (flat[0::4] | (flat[1::4] << 2) |
            (flat[2::4] << 4) | (flat[3::4] << 6)).astype(np.uint8)


def stamp_rect(block, padding):
    x0, y0, x1, y1 = block["rect"]
    # Includes the projected cap and face (0.5 m ~= 17 image px) plus tile margins.
    left, top, right, bottom = padding
    return ((x0 - left) // TILE * TILE, (y0 - top) // TILE * TILE,
            ((x1 + right + TILE - 1) // TILE) * TILE,
            ((y1 + bottom + TILE - 1) // TILE) * TILE)


def build(package=DEFAULT_PACKAGE, output=OUTPUT):
    data = json.loads(SPEC.read_text(encoding="utf-8"))
    arena = next(a for a in data["kits"] if a["name"] == "strip_kit")
    kit_spec = data["strip_kit"]
    floor_h_tiles = int(kit_spec["floor_h_tiles"])
    if floor_h_tiles not in (2, 4, 8, 16) or 16 % floor_h_tiles:
        raise ValueError("floor_h_tiles must be one of 2, 4, 8, 16")

    world, collision = load_images(Path(package))
    height, width, _ = world.shape
    if width != 512 or height < floor_h_tiles * TILE * 2:
        raise ValueError("strip package must be 512 px wide and contain two floor periods")
    period_px = floor_h_tiles * TILE
    # The first period must repeat one period later. The lab render carries +-1 colour noise,
    # so the check allows a tiny per-channel difference instead of exact equality.
    diff = np.abs(world[:period_px].astype(int) - world[period_px:2 * period_px].astype(int))
    if diff.max() > 16 or diff.mean() > 0.1:
        raise ValueError("floor period does not join cleanly: the first two periods differ")

    palette, indexed = quantize(world)
    blank = bytes(TILE * TILE)
    tiles = [blank]
    tile_ids = {blank: 0}
    floor_map = tiles_from_image(indexed[:period_px, :512], tiles, tile_ids)
    collision_grid = floor_collision(collision, 0, period_px, 512)

    stamps = []
    for block in arena["blocks"]:
        name = block.get("strip_stamp")
        if not name:
            continue
        x0, y0, x1, y1 = stamp_rect(block, kit_spec["stamp_crop_padding"])
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            raise ValueError(f"stamp {name} crop falls outside the package")
        stamp_tiles = tiles_from_image(indexed[y0:y1, x0:x1], tiles, tile_ids)
        phase_row = (y0 // TILE) % floor_h_tiles
        for ty in range(stamp_tiles.shape[0]):
            for tx in range(stamp_tiles.shape[1]):
                tid = int(stamp_tiles[ty, tx])
                floor_tid = int(floor_map[(phase_row + ty) % floor_h_tiles,
                                          (x0 // TILE + tx) % 64])
                if tiles[tid] == tiles[floor_tid]:
                    stamp_tiles[ty, tx] = 0

        bx0, by0, bx1, by1 = block["rect"]
        if any(v % CELL for v in (bx0, by0, bx1, by1)):
            raise ValueError(f"stamp {name} footprint is not aligned to the 4 px collision grid")
        block_collision = collision[by0:by1, bx0:bx1]
        occupied = np.zeros(((by1 - by0) // CELL, (bx1 - bx0) // CELL), dtype=bool)
        for cy in range(occupied.shape[0]):
            for cx in range(occupied.shape[1]):
                cell = block_collision[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL]
                occupied[cy, cx] = np.mean(cell >= 128) <= 0.40
        ys, xs = np.where(occupied)
        if not len(xs):
            raise ValueError(f"collision.png has no blocked cells for stamp {name}")
        foot_x = (bx0 - x0) // CELL + int(xs.min())
        foot_y = (by0 - y0) // CELL + int(ys.min())
        foot_w = int(xs.max() - xs.min() + 1)
        foot_h = int(ys.max() - ys.min() + 1)
        if foot_x < 0 or foot_y < 0 or foot_x + foot_w > stamp_tiles.shape[1] * 2 or foot_y + foot_h > stamp_tiles.shape[0] * 2:
            raise ValueError(f"stamp {name} footprint falls outside its tile block")
        stamps.append({"name": name, "w": stamp_tiles.shape[1], "h": stamp_tiles.shape[0],
                       "phase": phase_row, "foot_x": foot_x, "foot_y": foot_y,
                       "foot_w": foot_w, "foot_h": foot_h, "tiles": stamp_tiles})

    if not 2 <= len(stamps) <= 4:
        raise ValueError("strip_kit must define 2 to 4 low pillar stamps")
    if len(tiles) > 400:
        raise ValueError(f"tile count {len(tiles)} exceeds the 400 tile strip budget")

    packed = packed_collision(collision_grid)
    lines = ["// Generated by tools/bake_strip_kit.py. Do not edit.\n",
             '#include "strip_kit.h"\n\n',
             f"static const uint16_t s_palette[256] __attribute__((aligned(4))) = {{\n"]
    for i in range(0, 256, 16):
        lines.append("    " + ", ".join(f"0x{v:04X}" for v in palette[i:i + 16]) + ",\n")
    lines += ["};\n\n", f"static const uint8_t s_tiles[{len(tiles)}][64] __attribute__((aligned(4))) = {{\n"]
    for tile in tiles:
        lines.append("    { " + ", ".join(str(v) for v in tile) + " },\n")
    lines += ["};\n\n", f"static const uint16_t s_floor_map[{floor_map.size}] __attribute__((aligned(4))) = {{\n"]
    for row in floor_map:
        lines.append("    " + ", ".join(str(int(v)) for v in row) + ",\n")
    lines += ["};\n\n", f"static const uint8_t s_floor_collision[{len(packed)}] = {{\n"]
    for i in range(0, len(packed), 32):
        lines.append("    " + ", ".join(f"0x{int(v):02X}" for v in packed[i:i + 32]) + ",\n")
    lines += ["};\n\n"]
    for i, stamp in enumerate(stamps):
        flat = stamp["tiles"].reshape(-1)
        lines.append(f"static const uint16_t s_stamp_{i}_tiles[{flat.size}] = {{\n")
        for j in range(0, flat.size, 16):
            lines.append("    " + ", ".join(str(int(v)) for v in flat[j:j + 16]) + ",\n")
        lines.append("};\n")
    lines.append("\nstatic const StripStamp s_stamps[] = {\n")
    for i, stamp in enumerate(stamps):
        lines.append(f"    {{ {stamp['w']}, {stamp['h']}, {stamp['phase']}, "
                     f"{stamp['foot_x']}, {stamp['foot_y']}, {stamp['foot_w']}, {stamp['foot_h']}, "
                     f"1, s_stamp_{i}_tiles }}, // {stamp['name']}\n")
    lines += ["};\n\n", "const StripKit g_strip_kit = {\n",
              "    .palette = s_palette,\n", "    .tiles = s_tiles,\n",
              f"    .num_tiles = {len(tiles)},\n", f"    .map_h_tiles = {floor_h_tiles},\n",
              f"    .floor_h_tiles = {floor_h_tiles},\n",
              "    .floor_map = s_floor_map,\n", "    .floor_collision = s_floor_collision,\n",
              f"    .num_stamps = {len(stamps)},\n", "    .stamps = s_stamps,\n", "};\n"]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
    return len(tiles), floor_h_tiles, stamps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    count, period, stamps = build(args.package, args.output)
    print(f"strip kit: {count} tiles, period {period} tiles")
    for stamp in stamps:
        print(f"  {stamp['name']}: {stamp['w']}x{stamp['h']} tiles, "
              f"footprint {stamp['foot_w']}x{stamp['foot_h']} cells, phase {stamp['phase']}")


if __name__ == "__main__":
    main()
